"""Run the pot-rule RPS experiment entirely on Modal, detached-friendly.

The remote function starts a vLLM server for Qwen2.5-14B-Instruct-AWQ in its own container, runs
the experiment in chunks, commits results and cache to a Modal Volume, then runs the analysis.
No LLM judge is used. Every LLM request and response is also written to `llm_calls/*.jsonl`.

Build the image once (keep this terminal open until it prints "image ready"):

    modal run cloud/pot_modal.py::build_image

Then launch detached from the repository root:

    modal run --detach --name pot-channel-20 cloud/pot_modal.py \
        --condition channel --runs 20 --rounds 100 --workers 12

Follow logs while it runs (even from another terminal). `modal app list` gives the app ID;
the run name can be used as the description but is not always accepted by `app logs`:

    modal app list
    modal app logs <app-id> -f --timestamps

Fetch the complete logs and results afterwards:

    bash cloud/fetch_pot_logs.sh /logs/pot_channel_20runs_<timestamp>
    modal volume get netinf-pot /results/llm_rps_pot ./results_pot

Reflection runs (three separate commands):

    modal run --detach --name pot-reflect-independent-20 cloud/pot_modal.py \
        --condition independent --runs 20 --rounds 100 --workers 12 \
        --seed-offset 3000 --reflection --tag-suffix reflect
    modal run --detach --name pot-reflect-channel-20 cloud/pot_modal.py \
        --condition channel --runs 20 --rounds 100 --workers 12 \
        --seed-offset 4000 --reflection --tag-suffix reflect
    modal run --detach --name pot-reflect-hint-20 cloud/pot_modal.py \
        --condition channel_public_hint --runs 20 --rounds 100 --workers 12 \
        --seed-offset 5000 --reflection --tag-suffix reflect

Stop a run (use the ID from `modal app list`):

    modal app stop <app-id>
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import modal

MODEL = "Qwen/Qwen2.5-14B-Instruct-AWQ"
APP_NAME = "netinf-pot"
VOLUME_NAME = "netinf-pot"
REPO = Path("/repo")
VOL = Path("/vol")
ROOT = Path(__file__).resolve().parents[1]


def short_model(name: str) -> str:
    return name.split("/")[-1].replace(":", "_")

app = modal.App(APP_NAME)
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.from_registry(
        "vllm/vllm-openai:v0.9.1",
        setup_dockerfile_commands=["RUN ln -sf $(which python3) /usr/local/bin/python"],
    )
    .entrypoint([])
    .pip_install("matplotlib>=3.8")
    .add_local_dir(str(ROOT / "src"), remote_path="/repo/src", copy=True,
                   ignore=["__pycache__", "*.pyc"])
    .add_local_dir(str(ROOT / "experiments"), remote_path="/repo/experiments", copy=True,
                   ignore=["__pycache__", "*.pyc"])
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def log_line(fh, message: str) -> None:
    line = f"[{utc_now()}] {message}"
    print(line, flush=True)
    fh.write(line + "\n")
    fh.flush()


def write_manifest(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2))


def run_logged(cmd: list[str], log_path: Path, env: dict[str, str]) -> None:
    """Run a child process, streaming every line to Modal logs and to a volume log file."""
    with open(log_path, "a", buffering=1) as fh:
        log_line(fh, "$ " + " ".join(cmd))
        proc = subprocess.Popen(
            cmd, cwd=str(REPO), env=env, text=True, bufsize=1,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            log_line(fh, line.rstrip("\n"))
        code = proc.wait()
        if code != 0:
            raise RuntimeError(f"command failed with exit code {code}: {' '.join(cmd)}")


@app.function(image=image, timeout=1800)
def build_image() -> str:
    """Build/cache the image without requesting a GPU.

    Run this once and keep the terminal open until it prints "image ready". Detached runs
    started before the image exists can be cancelled when the local client disconnects
    during the image build.
    """
    print("image ready", flush=True)
    return "ok"


def wait_for_vllm(proc: subprocess.Popen, log_fh, timeout: float = 900.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"vLLM exited early with code {proc.returncode}; see vllm.log")
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/v1/models", timeout=5) as response:
                if response.status == 200:
                    log_line(log_fh, "vLLM is ready")
                    return
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError(f"vLLM did not become ready within {timeout:.0f}s; see vllm.log")


@app.function(image=image, gpu="A10G", timeout=12 * 3600, volumes={"/vol": volume})
def run_channel(condition: str, runs: int, rounds: int, workers: int, chunk_size: int,
                seed_offset: int = 0, reflection: bool = False,
                reflection_max_tokens: int = 300, tag_suffix: str = "") -> str:
    run_stamp = utc_stamp()
    log_dir = VOL / "logs" / f"pot_{condition}_{runs}runs_{run_stamp}"
    results_dir = VOL / "results" / "llm_rps_pot"
    cache_path = VOL / "cache" / "llm.sqlite"
    trace_dir = log_dir / "llm_calls"
    log_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    trace_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "app": APP_NAME,
        "condition": condition,
        "runs": runs,
        "rounds": rounds,
        "workers": workers,
        "chunk_size": chunk_size,
        "seed_offset": seed_offset,
        "reflection": reflection,
        "reflection_max_tokens": reflection_max_tokens,
        "tag_suffix": tag_suffix,
        "model": MODEL,
        "started_at": utc_now(),
        "status": "running",
        "log_dir": str(log_dir),
        "results_dir": str(results_dir),
    }
    manifest_path = log_dir / "manifest.json"
    write_manifest(manifest_path, manifest)

    orch = open(log_dir / "orchestrator.log", "a", buffering=1)
    env = {
        **os.environ,
        "NETINF_BASE_URL": "http://127.0.0.1:8000/v1",
        "NETINF_MODEL": MODEL,
        "NETINF_TRACE_DIR": str(trace_dir),
        "PYTHONPATH": "/repo/src:/repo/experiments",
        "PYTHONUNBUFFERED": "1",
    }
    vllm_proc = None
    vllm_fh = None

    try:
        log_line(orch, f"starting {MODEL} on A10G; condition={condition} runs={runs} rounds={rounds} "
                       f"reflection={reflection} tag_suffix={tag_suffix!r}")
        vllm_fh = open(log_dir / "vllm.log", "ab", buffering=0)
        vllm_proc = subprocess.Popen(
            [sys.executable, "-m", "vllm.entrypoints.openai.api_server",
             "--model", MODEL, "--max-model-len", "4096", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(REPO), env=env, stdout=vllm_fh, stderr=subprocess.STDOUT,
        )
        wait_for_vllm(vllm_proc, orch)

        for chunk_idx, start in enumerate(range(0, runs, chunk_size)):
            n = min(chunk_size, runs - start)
            cmd = [
                sys.executable, "experiments/llm_rps_pot.py",
                "--condition", condition,
                "--runs", str(n),
                "--rounds", str(rounds),
                "--workers", str(min(workers, n)),
                "--run-offset", str(start),
                "--seed-offset", str(seed_offset),
                "--tag", condition + tag_suffix,
                "--out", str(results_dir),
                "--cache", str(cache_path),
            ]
            if reflection:
                cmd += ["--reflection", "--reflection-max-tokens", str(reflection_max_tokens)]
            log_line(orch, f"chunk {chunk_idx}: runs {start}-{start + n - 1}")
            run_logged(cmd, log_dir / f"games_chunk_{chunk_idx:02d}.log", env)
            volume.commit()
            log_line(orch, f"chunk {chunk_idx} committed to volume")

        run_logged([sys.executable, "experiments/analyze_llm.py", str(results_dir)],
                   log_dir / "analysis.log", env)
        manifest.update(status="done", ended_at=utc_now())
        write_manifest(manifest_path, manifest)
        volume.commit()
        log_line(orch, f"done; logs={log_dir} results={results_dir}")
        return str(log_dir)

    except Exception:
        log_line(orch, traceback.format_exc())
        manifest.update(status="failed", ended_at=utc_now())
        write_manifest(manifest_path, manifest)
        volume.commit()
        raise
    finally:
        if vllm_proc is not None:
            vllm_proc.terminate()
            try:
                vllm_proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                vllm_proc.kill()
        if vllm_fh is not None:
            vllm_fh.close()
        orch.close()
        volume.commit()


def _complete_run(path: Path, rounds: int, reflection: bool) -> bool:
    try:
        game = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    if len(game.get("actions", [])) != rounds:
        return False
    if reflection and len(game.get("reflections", [])) != rounds:
        return False
    return True


@app.function(image=image, gpu="A10G", timeout=12 * 3600, volumes={"/vol": volume})
def resume_run(log_dir_str: str, workers: int = 12) -> str:
    """Resume an interrupted campaign, running only missing/incomplete run files."""
    log_dir = Path(log_dir_str)
    if not log_dir.exists():  # accept volume-relative paths such as /logs/...
        log_dir = VOL / log_dir_str.lstrip("/")
    manifest_path = log_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    condition = manifest["condition"]
    runs = int(manifest["runs"])
    rounds = int(manifest["rounds"])
    seed_offset = int(manifest.get("seed_offset", 0))
    reflection = bool(manifest.get("reflection", False))
    reflection_max_tokens = int(manifest.get("reflection_max_tokens", 300))
    tag_suffix = manifest.get("tag_suffix", "")
    model = manifest.get("model", MODEL)
    results_dir = Path(manifest.get("results_dir", "/vol/results/llm_rps_pot"))
    tag = condition + tag_suffix
    model_dir = results_dir / f"{short_model(model)}_{tag}"

    missing = [
        r for r in range(runs)
        if not _complete_run(model_dir / f"{condition}_run{r:02d}.json", rounds, reflection)
    ]
    orch = open(log_dir / "orchestrator.log", "a", buffering=1)
    env = {
        **os.environ,
        "NETINF_BASE_URL": "http://127.0.0.1:8000/v1",
        "NETINF_MODEL": model,
        "NETINF_TRACE_DIR": str(log_dir / "llm_calls"),
        "PYTHONPATH": "/repo/src:/repo/experiments",
        "PYTHONUNBUFFERED": "1",
    }
    vllm_proc = None
    vllm_fh = None
    log_line(orch, f"resume requested: {runs} runs, missing={missing}, model={model}, tag={tag}")

    try:
        manifest.update(status="running", resumed_at=utc_now(), missing_runs=missing)
        write_manifest(manifest_path, manifest)
        volume.commit()

        if missing:
            (log_dir / "llm_calls").mkdir(parents=True, exist_ok=True)
            vllm_fh = open(log_dir / "vllm_resume.log", "ab", buffering=0)
            vllm_proc = subprocess.Popen(
                [sys.executable, "-m", "vllm.entrypoints.openai.api_server",
                 "--model", model, "--max-model-len", "4096", "--host", "127.0.0.1", "--port", "8000"],
                cwd=str(REPO), env=env, stdout=vllm_fh, stderr=subprocess.STDOUT,
            )
            wait_for_vllm(vllm_proc, orch)
            for run in missing:
                cmd = [
                    sys.executable, "experiments/llm_rps_pot.py",
                    "--condition", condition,
                    "--runs", "1",
                    "--rounds", str(rounds),
                    "--workers", "1",
                    "--run-offset", str(run),
                    "--seed-offset", str(seed_offset),
                    "--tag", tag,
                    "--out", str(results_dir),
                    "--cache", "/vol/cache/llm.sqlite",
                ]
                if reflection:
                    cmd += ["--reflection", "--reflection-max-tokens", str(reflection_max_tokens)]
                log_line(orch, f"resume run {run:02d}")
                run_logged(cmd, log_dir / f"games_resume_{run:02d}.log", env)
                volume.commit()
                log_line(orch, f"resume run {run:02d} committed")

        run_logged([sys.executable, "experiments/analyze_llm.py", str(results_dir)],
                   log_dir / "analysis_resume.log", env)
        manifest.update(status="done", ended_at=utc_now(), missing_runs=missing)
        write_manifest(manifest_path, manifest)
        volume.commit()
        log_line(orch, f"resume done; logs={log_dir}")
        return str(log_dir)
    except Exception:
        log_line(orch, traceback.format_exc())
        manifest.update(status="failed", ended_at=utc_now())
        write_manifest(manifest_path, manifest)
        volume.commit()
        raise
    finally:
        if vllm_proc is not None:
            vllm_proc.terminate()
            try:
                vllm_proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                vllm_proc.kill()
        if vllm_fh is not None:
            vllm_fh.close()
        orch.close()
        volume.commit()


@app.local_entrypoint()
def main(condition: str = "channel", runs: int = 20, rounds: int = 100,
         workers: int = 12, chunk_size: int = 5, seed_offset: int = 0,
         reflection: bool = False, reflection_max_tokens: int = 300, tag_suffix: str = "",
         resume_log_dir: str = ""):
    if resume_log_dir:
        print(f"resuming {resume_log_dir}", flush=True)
        log_dir = resume_run.remote(resume_log_dir, workers)
        print(f"resume finished; logs on volume at {log_dir}", flush=True)
        return
    if condition not in ("independent", "channel", "channel_shared", "instructed", "channel_public_hint"):
        raise SystemExit(f"unknown condition: {condition}")
    print(f"launching {condition}: {runs} runs x {rounds} rounds on {MODEL} "
          f"(reflection={reflection}, tag_suffix={tag_suffix!r})", flush=True)
    log_dir = run_channel.remote(condition, runs, rounds, workers, chunk_size, seed_offset,
                                 reflection, reflection_max_tokens, tag_suffix)
    print(f"finished; logs on volume at {log_dir}", flush=True)
