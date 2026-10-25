"""Run a llm_rps_plan.py campaign on Modal: vLLM + the games + the analysis, detached-friendly.

Estimate first (local, no GPU, nothing launched):

    modal run cloud/plan_modal.py --dry-run --conditions independent,channel,instructed --runs 10

Launch (from the repository root):

    modal run --detach --name plan-pilot cloud/plan_modal.py \
        --conditions independent,channel,instructed --runs 3 --rounds 30

Any llm_rps_plan.py option goes through --extra, for example:

    --extra "--negotiation-turns 3 --no-plan --prompt hint=@prompts/hint_v2.txt"

(files given with @ must be inside prompts/, which is copied into the container).

Follow and fetch:

    modal app logs plan-pilot -f --timestamps
    modal volume get netinf-plan /results/llm_rps_plan/<campaign> ./results/llm_rps_plan/
    modal volume get netinf-plan /logs/<campaign> ./modal_logs/
    modal app stop plan-pilot
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
import traceback
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import modal

MODEL = "Qwen/Qwen2.5-7B-Instruct"
APP_NAME = VOLUME_NAME = "netinf-plan"
REPO = Path("/repo")
VOL = Path("/vol")
ROOT = Path(__file__).resolve().parents[1]

app = modal.App(APP_NAME)
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)
image = (
    modal.Image.from_registry(
        "vllm/vllm-openai:v0.9.1", setup_dockerfile_commands=["RUN ln -sf $(which python3) /usr/local/bin/python"])
    .entrypoint([])
    .pip_install("matplotlib>=3.8")
    .add_local_dir(str(ROOT / "src"), remote_path="/repo/src", copy=True, ignore=["__pycache__", "*.pyc"])
    .add_local_dir(str(ROOT / "experiments"), remote_path="/repo/experiments", copy=True,
                   ignore=["__pycache__", "*.pyc"])
    .add_local_dir(str(ROOT / "prompts"), remote_path="/repo/prompts", copy=True)
)


def log(fh, message: str) -> None:
    line = f"[{datetime.now(timezone.utc):%H:%M:%S}] {message}"
    print(line, flush=True)
    fh.write(line + "\n")
    fh.flush()


def run_logged(cmd: list[str], log_path: Path, env: dict[str, str]) -> None:
    """Run a child process, streaming every line to Modal logs and to a volume log file."""
    with open(log_path, "a", buffering=1) as fh:
        log(fh, "$ " + shlex.join(cmd))
        proc = subprocess.Popen(cmd, cwd=str(REPO), env=env, text=True, bufsize=1,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for line in proc.stdout:
            log(fh, line.rstrip("\n"))
        if proc.wait() != 0:
            raise RuntimeError(f"command failed with exit code {proc.returncode}")


def wait_for_vllm(proc: subprocess.Popen, fh, timeout: float = 900.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"vLLM exited early with code {proc.returncode}; see vllm.log")
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000/v1/models", timeout=5) as r:
                if r.status == 200:
                    log(fh, "vLLM is ready")
                    return
        except Exception:
            pass
        time.sleep(2)
    raise TimeoutError("vLLM did not start in time; see vllm.log")


def game_args(conditions: str, rounds: int, extra: str) -> list[str]:
    return ["--conditions", conditions, "--rounds", str(rounds), *shlex.split(extra)]


@app.function(image=image, gpu="A10G", timeout=12 * 3600, volumes={"/vol": volume})
def run_campaign(campaign: str, conditions: str, runs: int, rounds: int, workers: int, chunk_size: int,
                 model: str, extra: str) -> str:
    log_dir = VOL / "logs" / campaign
    out = VOL / "results" / "llm_rps_plan"
    log_dir.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "NETINF_BASE_URL": "http://127.0.0.1:8000/v1", "NETINF_MODEL": model,
           "NETINF_TRACE_DIR": str(log_dir / "llm_calls"), "PYTHONPATH": "/repo/src:/repo/experiments",
           "PYTHONUNBUFFERED": "1"}
    orch = open(log_dir / "orchestrator.log", "a", buffering=1)
    vllm_fh = open(log_dir / "vllm.log", "ab", buffering=0)
    vllm = None
    try:
        log(orch, f"campaign {campaign}: {model}, {conditions}, {runs} runs x {rounds} rounds, extra={extra!r}")
        vllm = subprocess.Popen(
            [sys.executable, "-m", "vllm.entrypoints.openai.api_server", "--model", model,
             "--max-model-len", "8192", "--enable-prefix-caching", "--host", "127.0.0.1", "--port", "8000"],
            cwd=str(REPO), env=env, stdout=vllm_fh, stderr=subprocess.STDOUT)
        wait_for_vllm(vllm, orch)
        for i, start in enumerate(range(0, runs, chunk_size)):
            n = min(chunk_size, runs - start)
            cmd = [sys.executable, "experiments/llm_rps_plan.py", *game_args(conditions, rounds, extra),
                   "--runs", str(n), "--run-offset", str(start), "--workers", str(workers),
                   "--out", str(out), "--campaign", campaign, "--cache", str(VOL / "cache" / "llm.sqlite")]
            run_logged(cmd, log_dir / f"games_chunk_{i:02d}.log", env)
            volume.commit()  # results survive even if a later chunk fails
            log(orch, f"chunk {i} (runs {start}-{start + n - 1}) committed")
        run_logged([sys.executable, "experiments/analyze_plan.py", str(out / campaign)], log_dir / "analysis.log", env)
        log(orch, f"done: results in {out / campaign}")
        return str(out / campaign)
    except Exception:
        log(orch, traceback.format_exc())
        raise
    finally:
        if vllm is not None:
            vllm.terminate()
        vllm_fh.close()
        orch.close()
        volume.commit()


@app.local_entrypoint()
def main(conditions: str = "independent,channel,instructed", runs: int = 10, rounds: int = 100,
         workers: int = 16, chunk_size: int = 5, model: str = MODEL, extra: str = "", tag: str = "",
         campaign: str = "", dry_run: bool = False, calls_per_sec: float = 5.0, gpu_price: float = 1.10):
    """calls_per_sec: replace the default guess with the rate printed at the end of a pilot.
    gpu_price: dollars per GPU hour (A10G on Modal; check modal.com/pricing)."""
    estimate = subprocess.run(
        [sys.executable, str(ROOT / "experiments" / "llm_rps_plan.py"), *game_args(conditions, rounds, extra),
         "--runs", str(runs), "--estimate"], capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'experiments'}"})
    if estimate.returncode != 0:
        raise SystemExit(estimate.stderr)
    print(estimate.stdout.strip())
    calls = int(estimate.stdout.rsplit(":", 1)[1])
    hours = calls / calls_per_sec / 3600 + 0.1  # + about 6 minutes to start vLLM
    print(f"rough GPU time {hours:.1f} h at {calls_per_sec:g} calls/s -> about ${hours * gpu_price:.0f}"
          f" (at ${gpu_price:g}/h); measure calls/s with a small pilot")
    if dry_run:
        return
    short = model.split("/")[-1].replace(":", "_")
    campaign = campaign or f"{datetime.now():%Y%m%d-%H%M}_{short}" + (f"_{tag}" if tag else "")
    print(f"launching campaign {campaign}")
    print(run_campaign.remote(campaign, conditions, runs, rounds, workers, chunk_size, model, extra))
