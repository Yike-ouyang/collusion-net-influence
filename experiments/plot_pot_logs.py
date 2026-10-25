"""Plot one pot_modal log folder as small multiples, one panel per run.

Each run block has two axes sharing the round axis:
  * top: cumulative score of A, B and C over the episode;
  * bottom: each agent's move trajectory, with y ordered Rock / Paper / Scissors.

Input is a pot_modal log directory containing `manifest.json` and `llm_calls/*.jsonl`.
Move calls are recognised by `max_tokens == 16` (or the move prompt), and the run is
recovered from the seed with the same formula as `llm_rps.play`:

    hash((run + seed_offset, round_index, player_index)) % 2**31

Usage:
    python experiments/plot_pot_logs.py logs/pot_channel_1runs_20261024T223435Z
    python experiments/plot_pot_logs.py logs/                 # one PNG per log folder
    python experiments/plot_pot_logs.py <log_dir> --out /tmp/trajectories.png
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator

from netinf.games.rps import BEATS
from netinf.games.rps_pot import payoff_pot

PLAYERS = ("A", "B", "C")
COLORS = {"A": "#1f77b4", "B": "#ff7f0e", "C": "#2ca02c"}
MOVE_LABELS = ("Rock", "Paper", "Scissors")
MOVE_OFFSETS = (-0.12, 0.0, 0.12)  # vertical jitter so coincident choices stay visible
MOVE_RE = re.compile(r"\b(R|P|S|ROCK|PAPER|SCISSORS)\b")
PLAYER_RE = re.compile(r"You are Player ([ABC])")
ROUND_RE = re.compile(r"(?m)^\s*Round\s+(\d+)\.")


def parse_move(text: str) -> int | None:
    match = MOVE_RE.search((text or "").upper())
    return None if match is None else "RPS".index(match.group(1)[0])


def load_manifest(log_dir: Path) -> dict:
    path = log_dir / "manifest.json"
    if not path.exists():
        raise SystemExit(f"missing manifest.json in {log_dir}")
    return json.loads(path.read_text())


def seed_to_run_maps(manifest: dict) -> dict[tuple[int, int], dict[int, int]]:
    """For each (round, player), map seed -> run index for the whole campaign."""
    runs = int(manifest.get("runs", 1))
    seed_offset = int(manifest.get("seed_offset", 0))
    rounds = int(manifest.get("rounds", 0))
    return {
        (t, k): {
            hash((run + seed_offset, t, k)) % 2**31: run
            for run in range(runs)
        }
        for t in range(rounds)
        for k in range(3)
    }


def iter_records(log_dir: Path):
    for path in sorted((log_dir / "llm_calls").glob("*.jsonl")):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def parse_episodes(log_dir: Path, manifest: dict) -> dict[int, np.ndarray]:
    """Reconstruct one actions array (rounds x 3) per run from llm_calls JSONL."""
    runs = int(manifest.get("runs", 1))
    seed_maps = seed_to_run_maps(manifest)

    cells: dict[int, dict[tuple[int, int], int]] = {}
    bad_runs: set[int] = set()
    dropped = 0
    seed_misses = 0
    conflicts = 0

    for record in iter_records(log_dir):
        prompt = record.get("prompt", "")
        if "Reply with exactly one letter" not in prompt and record.get("max_tokens") != 16:
            continue  # private message calls are not moves

        player_match = PLAYER_RE.search(record.get("system", ""))
        round_match = ROUND_RE.search(prompt)
        move = parse_move(record.get("response", ""))
        if player_match is None or round_match is None or move is None:
            dropped += 1
            continue

        t = int(round_match.group(1)) - 1
        k = "ABC".index(player_match.group(1))
        if t < 0 or k not in (0, 1, 2):
            dropped += 1
            continue

        run = seed_maps.get((t, k), {}).get(record.get("seed"))
        if run is None and runs == 1:
            run = 0  # single-run logs are unambiguous even if the hash differs
        if run is None:
            seed_misses += 1
            continue

        run_cells = cells.setdefault(run, {})
        key = (t, k)
        if key in run_cells:
            if run_cells[key] != move:
                conflicts += 1
                bad_runs.add(run)
            continue
        run_cells[key] = move

    rounds = int(manifest.get("rounds", 0))
    if rounds <= 0:
        rounds = max((t + 1 for c in cells.values() for t, _ in c), default=0)
    if rounds <= 0:
        raise SystemExit(f"no move calls found in {log_dir}")

    episodes: dict[int, np.ndarray] = {}
    for run, run_cells in sorted(cells.items()):
        if run in bad_runs:
            print(f"  warning: run {run} has conflicting move records; skipped")
            continue
        missing = [(t, k) for t in range(rounds) for k in range(3) if (t, k) not in run_cells]
        if missing:
            print(f"  warning: run {run} is incomplete ({len(missing)} missing moves); skipped")
            continue
        episodes[run] = np.array([[run_cells[(t, k)] for k in range(3)] for t in range(rounds)])

    if dropped or seed_misses:
        print(f"  warning: dropped {dropped} malformed/parse-failed move records, "
              f"{seed_misses} records had no matching seed")
    if conflicts:
        print(f"  warning: {conflicts} conflicting duplicate records")
    if not episodes:
        raise SystemExit(f"no complete run reconstructed from {log_dir}")
    return episodes


def parse_result_episodes(results_dir: Path, manifest: dict) -> dict[int, np.ndarray]:
    """Optional fallback/override: read complete actions from run JSON files."""
    condition = manifest.get("condition")
    model = manifest.get("model")
    episodes: dict[int, np.ndarray] = {}
    for path in sorted(results_dir.glob("*/*_run*.json")):
        try:
            game = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if condition and game.get("condition") != condition:
            continue
        if model and game.get("model") != model:
            continue
        if game.get("rules") not in (None, "pot3"):
            continue
        actions = np.asarray(game.get("actions", []))
        if actions.ndim == 2 and actions.shape[1] == 3 and "run" in game:
            episodes[int(game["run"])] = actions
    return episodes


def cumulative_scores(actions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rewards = np.array([payoff_pot(row) for row in actions])
    cumulative = np.vstack([np.zeros(3), np.cumsum(rewards, axis=0)])
    return rewards, cumulative


def episode_metrics(actions: np.ndarray) -> dict:
    beats = np.vectorize(BEATS.get)
    b_to_a = actions[:, 1] == beats(actions[:, 0])
    a_to_b = actions[:, 0] == beats(actions[:, 1])
    directions = np.where(b_to_a, 1, np.where(a_to_b, -1, 0))
    assist_dirs = directions[directions != 0]
    switches = int(np.sum(assist_dirs[1:] != assist_dirs[:-1])) if len(assist_dirs) > 1 else 0
    alternation = switches / (len(assist_dirs) - 1) if len(assist_dirs) > 1 else 0.0
    return {
        "assist_any": float((b_to_a | a_to_b).mean()),
        "alternation_rate": float(alternation),
    }


def plot_log_folder(log_dir: Path, out: Path, max_runs: int = 20,
                    selected_runs: set[int] | None = None, dpi: int = 150,
                    title: str | None = None, results_dir: Path | None = None) -> None:
    manifest = load_manifest(log_dir)
    try:
        episodes = parse_episodes(log_dir, manifest)
    except SystemExit:
        if results_dir is None:
            raise
        episodes = {}
    if results_dir is not None:
        result_episodes = parse_result_episodes(results_dir, manifest)
        if result_episodes:
            episodes.update(result_episodes)
            print(f"  using {len(result_episodes)} complete run JSON(s) from {results_dir}")

    run_ids = sorted(episodes)
    if selected_runs is not None:
        run_ids = [r for r in run_ids if r in selected_runs]
    if not run_ids:
        raise SystemExit(f"no runs selected in {log_dir}")
    if len(run_ids) > max_runs:
        print(f"  {len(run_ids)} runs found; plotting the first {max_runs} (use --max-runs/--runs)")
        run_ids = run_ids[:max_runs]

    n = len(run_ids)
    cols = min(5, n)
    rows = (n + cols - 1) // cols
    fig = plt.figure(figsize=(max(7.0, 4.2 * cols), max(4.8, 3.6 * rows)), constrained_layout=True)
    outer = fig.add_gridspec(rows, cols, hspace=0.45, wspace=0.35)

    handles = [Line2D([0], [0], color=COLORS[p], lw=2, label=f"Agent {p}") for p in PLAYERS]
    condition = manifest.get("condition", "?")
    model = manifest.get("model", "?")
    suptitle = title or f"{condition} — {model} — {log_dir.name}"
    fig.suptitle(suptitle, fontsize=12)

    for idx, run in enumerate(run_ids):
        row, col = divmod(idx, cols)
        inner = outer[row, col].subgridspec(2, 1, height_ratios=[1.0, 1.7], hspace=0.06)
        ax_score = fig.add_subplot(inner[0])
        ax_move = fig.add_subplot(inner[1], sharex=ax_score)

        actions = episodes[run]
        rounds = len(actions)
        _, cumulative = cumulative_scores(actions)
        metrics = episode_metrics(actions)
        x_moves = np.arange(1, rounds + 1)
        x_score = np.arange(0, rounds + 1)

        score_span = max(1.0, float(cumulative.max() - cumulative.min()))
        score_step = max(0.2, 0.01 * score_span)
        score_offsets = (-score_step, 0.0, score_step)
        score_plot = cumulative + np.array(score_offsets)

        for k, player in enumerate(PLAYERS):
            ax_score.plot(x_score, score_plot[:, k], color=COLORS[player], lw=1.5)
            ax_move.step(x_moves, actions[:, k] + MOVE_OFFSETS[k], where="post",
                         color=COLORS[player], lw=1.1, marker="o", markersize=2.2)

        ax_score.set_title(
            f"Run {run:02d}   any={metrics['assist_any']:.2f}  alt={metrics['alternation_rate']:.2f}",
            fontsize=8, pad=2,
        )
        ax_score.set_ylabel("Cumulative score", fontsize=8)
        ax_score.tick_params(axis="x", labelbottom=False, labelsize=7)
        ax_score.tick_params(axis="y", labelsize=7)
        ax_score.grid(alpha=0.25)
        ax_score.margins(x=0)
        ax_score.set_ylim(bottom=min(0.0, float(score_plot.min())))

        ax_move.set_ylim(2.5, -0.5)  # Rock at the top
        ax_move.set_yticks([0, 1, 2], MOVE_LABELS, fontsize=8)
        ax_move.set_xlim(0, rounds)
        ax_move.set_xlabel("Round", fontsize=8)
        ax_move.tick_params(axis="x", labelsize=7)
        ax_move.tick_params(axis="y", labelsize=8)
        ax_move.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
        ax_move.grid(axis="y", alpha=0.25)
        if col != 0:
            ax_score.set_ylabel("")
            ax_move.set_ylabel("")
        else:
            ax_move.set_ylabel("Move", fontsize=8)

    fig.legend(handles=handles, loc="outside lower center", ncol=3, frameon=False, fontsize=9)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  plotted {n} run(s) -> {out}")


def log_folders(path: Path) -> list[Path]:
    if (path / "manifest.json").exists() or (path / "llm_calls").exists():
        return [path]
    return [d for d in sorted(path.iterdir())
            if d.is_dir() and ((d / "manifest.json").exists() or (d / "llm_calls").exists())]


def parse_run_list(text: str | None) -> set[int] | None:
    if not text:
        return None
    return {int(x) for x in text.split(",") if x.strip()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("log_dir", type=Path, help="one pot_modal log directory, or a parent of such directories")
    ap.add_argument("--out", type=Path, help="output PNG (single log dir) or output directory (multiple)")
    ap.add_argument("--max-runs", type=int, default=20)
    ap.add_argument("--runs", help="comma-separated run indices to plot, e.g. 0,2,5")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--title", help="override the figure title")
    ap.add_argument("--results", type=Path,
                    help="optional results directory with *_run*.json; overrides/fills actions from logs")
    args = ap.parse_args()

    if not args.log_dir.exists():
        raise SystemExit(f"no such path: {args.log_dir}")
    folders = log_folders(args.log_dir)
    if not folders:
        raise SystemExit(f"no pot_modal log folder found under {args.log_dir}")

    selected = parse_run_list(args.runs)
    multiple = len(folders) > 1
    if multiple and args.out and args.out.suffix:
        raise SystemExit("--out must be a directory when plotting multiple log folders")
    out_is_dir = bool(args.out) and (multiple or args.out.suffix == "" or args.out.is_dir())

    failures = 0
    for folder in folders:
        if out_is_dir:
            out = args.out / f"{folder.name}_trajectories.png"
        else:
            out = args.out or folder / "trajectories.png"
        try:
            print(f"{folder}:")
            results_dir = args.results if (not multiple and args.results) else folder / "results"
            if not results_dir.exists():
                results_dir = None
            plot_log_folder(folder, out, max_runs=args.max_runs, selected_runs=selected,
                            dpi=args.dpi, title=args.title, results_dir=results_dir)
        except SystemExit as exc:
            print(f"  error: {exc}")
            failures += 1
        except Exception as exc:  # keep processing the other folders
            print(f"  error: {type(exc).__name__}: {exc}")
            failures += 1

    if failures == len(folders):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
