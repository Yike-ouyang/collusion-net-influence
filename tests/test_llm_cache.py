import json

from netinf.llm import CachedChat


def test_cache_replays_without_api_call(tmp_path, monkeypatch):
    llm = CachedChat(model="fake-model", cache_path=tmp_path / "c.sqlite")
    calls = []
    monkeypatch.setattr(llm, "_call", lambda req: calls.append(req) or f"reply-{req['seed']}")

    assert llm.generate("hi", seed=1) == "reply-1"
    assert llm.generate("hi", seed=1) == "reply-1"
    assert llm.generate("hi", seed=2) == "reply-2"
    assert len(calls) == 2
    assert llm.usage.cache_hits == 1

    # cache persists across instances
    llm2 = CachedChat(model="fake-model", cache_path=tmp_path / "c.sqlite")
    monkeypatch.setattr(llm2, "_call", lambda req: (_ for _ in ()).throw(AssertionError("should hit cache")))
    assert llm2.generate("hi", seed=2) == "reply-2"


def test_trace_logs_requests_responses_and_cache_hits(tmp_path, monkeypatch):
    monkeypatch.setenv("NETINF_TRACE_DIR", str(tmp_path / "trace"))
    llm = CachedChat(model="fake-model", cache_path=tmp_path / "c.sqlite")
    monkeypatch.setattr(llm, "_call", lambda req: "reply")

    assert llm.generate("hi", seed=1) == "reply"
    assert llm.generate("hi", seed=1) == "reply"

    files = list((tmp_path / "trace").glob("*.jsonl"))
    assert len(files) == 1
    rows = [json.loads(line) for line in files[0].read_text().splitlines()]
    assert [r["cached"] for r in rows] == [False, True]
    assert all(r["response"] == "reply" and r["prompt"] == "hi" for r in rows)


def test_generate_full_caches_logs_revision_and_keys_by_revision(tmp_path, monkeypatch):
    monkeypatch.setenv("NETINF_TRACE_DIR", str(tmp_path / "trace"))
    out = {"text": "MOVE: Rock", "finish_reason": "length", "tokens": [{"token": "Rock", "top": [["Rock", -0.1]]}],
           "prompt_tokens": 50, "completion_tokens": 3}
    llm = CachedChat(model="m", revision="abc123", cache_path=tmp_path / "c.sqlite")
    calls = []
    monkeypatch.setattr(llm, "_call_full", lambda req: calls.append(req) or out)
    assert llm.generate_full("hi", seed=1, top_logprobs=5) == out
    assert llm.generate_full("hi", seed=1, top_logprobs=5) == out  # replayed from cache
    assert len(calls) == 1 and calls[0]["top_logprobs"] == 5
    other = CachedChat(model="m", revision="def456", cache_path=tmp_path / "c.sqlite")
    monkeypatch.setattr(other, "_call_full", lambda req: calls.append(req) or out)
    other.generate_full("hi", seed=1, top_logprobs=5)
    assert len(calls) == 2  # another revision is another cache entry
    rows = [json.loads(x) for f in (tmp_path / "trace").glob("*.jsonl") for x in f.read_text().splitlines()]
    assert {r["revision"] for r in rows} == {"abc123", "def456"}
    assert all(r["finish_reason"] == "length" for r in rows)


def test_plain_generate_keys_are_unchanged_without_revision(tmp_path, monkeypatch):
    llm = CachedChat(model="fake-model", cache_path=tmp_path / "c.sqlite")
    monkeypatch.setattr(llm, "_call", lambda req: "x")
    llm.generate("hi", seed=1)
    keys = [r[0] for r in llm._db.execute("SELECT request FROM calls")]
    assert "revision" not in json.loads(keys[0])  # older caches keep matching


def test_system_as_user_merges_the_system_prompt_for_templates_without_system_role():
    plain = CachedChat._body({"model": "m", "system": "RULES", "prompt": "ROUND 1", "temperature": 1.0, "seed": 0,
                              "max_tokens": 5})
    merged = CachedChat._body({"model": "m", "system": "RULES", "prompt": "ROUND 1", "temperature": 1.0, "seed": 0,
                               "max_tokens": 5, "system_as_user": True})
    assert [m["role"] for m in plain["messages"]] == ["system", "user"]
    assert merged["messages"] == [{"role": "user", "content": "RULES\n\nROUND 1"}]
