import os
import subprocess
import sys
from pathlib import Path

from netinf.seeding import legacy_seed, stable_seed

SRC = str(Path(__file__).resolve().parents[1] / "src")


def _seed_in_new_process(hash_seed: str, expr: str) -> str:
    env = {**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": SRC}
    code = f"from netinf.seeding import legacy_seed, stable_seed; print({expr})"
    return subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=True).stdout


def test_stable_seed_is_identical_across_processes():
    # Two processes with different string-hash salts: hash() of a string differs, stable_seed does not.
    expr = "stable_seed(3, 0, 7, 1, 'msg', 0), legacy_seed(3, 7, 1, 'reflect')"
    assert _seed_in_new_process("1", expr) == _seed_in_new_process("2", expr)
    assert _seed_in_new_process("1", "hash('msg')") != _seed_in_new_process("2", "hash('msg')")


def test_legacy_seed_keeps_historical_int_seeds():
    # all-int keys must match the seeds already logged by past campaigns (plot_pot_logs.py relies on it)
    assert legacy_seed(1005, 12, 2) == hash((1005, 12, 2)) % 2**31
    assert 0 <= stable_seed("x") < 2**31
    assert stable_seed(1, "a") != stable_seed(1, "b")
