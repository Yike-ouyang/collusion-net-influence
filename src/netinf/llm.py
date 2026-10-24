"""Chat client for any OpenAI-compatible endpoint, with an on-disk response cache.

Works with (set NETINF_BASE_URL, NETINF_MODEL, and NETINF_API_KEY if needed):
  - Ollama, local:      http://localhost:11434/v1                                  (no key)
  - Kaggle notebook:    Ollama or vLLM inside the notebook, same URL style          (no key)
  - Gemini free tier:   https://generativelanguage.googleapis.com/v1beta/openai/   (key from AI Studio)

Every call is keyed by the full request. Re-running with the same seeds replays cached responses,
so results are reproducible and reruns are free.

Set NETINF_TRACE_DIR to log every request and response (including cache hits) as JSONL, one file
per model and process. Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Usage:
    calls: int = 0
    cache_hits: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class CachedChat:
    model: str = field(default_factory=lambda: os.environ.get("NETINF_MODEL", ""))
    base_url: str = field(default_factory=lambda: os.environ.get("NETINF_BASE_URL", "http://localhost:11434/v1"))
    api_key: str = field(default_factory=lambda: os.environ.get("NETINF_API_KEY", ""), repr=False)
    cache_path: Path = Path("cache/llm.sqlite")
    max_retries: int = 5
    timeout: float = 120.0
    usage: Usage = field(default_factory=Usage)

    def __post_init__(self):
        if not self.model:
            raise ValueError("set a model name, e.g. CachedChat(model=...) or NETINF_MODEL env var")
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.cache_path, check_same_thread=False, timeout=60)  # several processes may share it
        self._lock = threading.Lock()  # one connection shared by worker threads
        self._db.execute("CREATE TABLE IF NOT EXISTS calls (key TEXT PRIMARY KEY, request TEXT, response TEXT)")
        self._trace_path = None
        trace_dir = os.environ.get("NETINF_TRACE_DIR")
        if trace_dir:  # optional: log every request/response, including cache hits
            trace_root = Path(trace_dir)
            trace_root.mkdir(parents=True, exist_ok=True)
            safe_model = "".join(c if c.isalnum() or c in "-._" else "_" for c in self.model)
            self._trace_path = trace_root / f"{safe_model}_{os.getpid()}.jsonl"

    def generate(self, prompt: str, system: str = "", temperature: float = 1.0, seed: int = 0,
                 max_tokens: int = 512) -> str:
        request = {"model": self.model, "system": system, "prompt": prompt, "temperature": temperature,
                   "seed": seed, "max_tokens": max_tokens}
        key = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        with self._lock:
            row = self._db.execute("SELECT response FROM calls WHERE key = ?", (key,)).fetchone()
        if row:
            self.usage.cache_hits += 1
            self._trace(request, row[0], cached=True)
            return row[0]

        text = self._call(request)
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO calls VALUES (?, ?, ?)", (key, json.dumps(request), text))
            self._db.commit()
        self._trace(request, text, cached=False)
        return text

    def _trace(self, request: dict, response: str, cached: bool) -> None:
        if self._trace_path is None:
            return
        record = {**request, "response": response, "cached": cached}
        with self._lock:
            with open(self._trace_path, "a") as f:
                f.write(json.dumps(record) + "\n")

    def _call(self, req: dict) -> str:
        messages = ([{"role": "system", "content": req["system"]}] if req["system"] else []) + [
            {"role": "user", "content": req["prompt"]}]
        body = json.dumps({"model": req["model"], "messages": messages, "temperature": req["temperature"],
                           "seed": req["seed"], "max_tokens": req["max_tokens"]}).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        http = urllib.request.Request(self.base_url.rstrip("/") + "/chat/completions", body, headers)

        for attempt in range(self.max_retries):
            try:
                with urllib.request.urlopen(http, timeout=self.timeout) as r:
                    resp = json.load(r)
                break
            except urllib.error.HTTPError as e:
                if e.code not in (429, 500, 502, 503, 504) or attempt == self.max_retries - 1:
                    raise
            except (urllib.error.URLError, TimeoutError):
                if attempt == self.max_retries - 1:
                    raise
            time.sleep(2**attempt)  # rate limit / transient error: back off

        self.usage.calls += 1
        u = resp.get("usage") or {}
        self.usage.input_tokens += u.get("prompt_tokens", 0)
        self.usage.output_tokens += u.get("completion_tokens", 0)
        return resp["choices"][0]["message"]["content"] or ""
