import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments"))
import plot_pot_logs as plot  # noqa: E402


def _record(t: int, k: int, move: str, run: int, seed_offset: int = 0) -> dict:
    return {
        "model": "fake",
        "system": f"You are Player {'ABC'[k]} in a fake game.",
        "prompt": f"Round {t + 1}. Your total score: 0.\nReply with exactly one letter: R, P or S.",
        "temperature": 1.0,
        "seed": hash((run + seed_offset, t, k)) % 2**31,
        "max_tokens": 16,
        "response": move,
        "cached": False,
    }


def _write_log(tmp_path: Path, records: list[dict], runs: int, rounds: int) -> Path:
    log_dir = tmp_path / "pot_channel_test"
    (log_dir / "llm_calls").mkdir(parents=True)
    (log_dir / "manifest.json").write_text(json.dumps({
        "runs": runs, "seed_offset": 0, "rounds": rounds,
        "condition": "channel", "model": "fake-model",
    }))
    with open(log_dir / "llm_calls" / "trace.jsonl", "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    return log_dir


def test_parse_episodes_groups_interleaved_runs_by_seed(tmp_path):
    moves = {
        0: [["R", "S", "S"], ["P", "R", "R"]],
        1: [["S", "P", "P"], ["R", "S", "S"]],
    }
    records = []
    for t in range(2):
        for k in range(3):
            for run in (0, 1):
                records.append(_record(t, k, moves[run][t][k], run))
    # Deliberately interleave the runs.
    records = records[::2] + records[1::2]
    log_dir = _write_log(tmp_path, records, runs=2, rounds=2)

    episodes = plot.parse_episodes(log_dir, plot.load_manifest(log_dir))
    assert sorted(episodes) == [0, 1]
    assert episodes[0].tolist() == [[0, 2, 2], [1, 0, 0]]
    assert episodes[1].tolist() == [[2, 1, 1], [0, 2, 2]]


def test_plot_log_folder_writes_png(tmp_path):
    records = [
        _record(t, k, move, run=0)
        for t, row in enumerate([["R", "S", "S"], ["P", "R", "R"]])
        for k, move in enumerate(row)
    ]
    log_dir = _write_log(tmp_path, records, runs=1, rounds=2)
    out = tmp_path / "trajectories.png"
    plot.plot_log_folder(log_dir, out, max_runs=10)

    assert out.exists()
    assert out.stat().st_size > 0
    assert np.array_equal(plot.parse_episodes(log_dir, plot.load_manifest(log_dir))[0],
                          np.array([[0, 2, 2], [1, 0, 0]]))
