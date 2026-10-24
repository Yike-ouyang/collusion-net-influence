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
