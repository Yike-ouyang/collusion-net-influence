"""Plot llm_rps_v2 campaign trajectories as small multiples, one figure per condition.

Each run panel has two axes sharing the round axis:
  * top: cumulative score of A, B and C over the episode;
  * bottom: each agent's move trajectory, with y ordered Rock / Paper / Scissors.

Input is an llm_rps_v2 campaign directory containing config.json and games/*.json.
The figure style matches experiments/plot_pot_logs.py.

Usage:
    python experiments/plot_v2_trajectories.py results/llm_rps_v2/<campaign>
    python experiments/plot_v2_trajectories.py results/llm_rps_v2/<campaign> --out logs/v2
    python experiments/plot_v2_trajectories.py results/llm_rps_v2/<campaign> --conditions channel_forced
"""

from __future__ import annotations

import argparse
import json
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

from netinf.games.rps import ACTIONS, BEATS
from netinf.games.rps_pot import payoff_pot

PLAYERS = ("A", "B", "C")
COLORS = {"A": "#1f77b4", "B": "#ff7f0e", "C": "#2ca02c"}
MOVE_LABELS = ("Rock", "Paper", "Scissors")
MOVE_OFFSETS = (-0.12, 0.0, 0.12)
CONDITION_ORDER = (
    "no_channel",
    "channel_optional",
    "channel_optional_hint",
    "channel_forced",
    "channel_forced_strategy",
)


def load_games(campaign_dir: Path) -> list[dict]:
    games = []
    for path in sorted((campaign_dir / "games").glob("*.json")):
        try:
            games.append(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  warning: skipped {path.name}: {exc}")
    return games


def campaign_info(campaign_dir: Path) -> tuple[str, str]:
    config_path = campaign_dir / "config.json"
    if not config_path.exists():
        return campaign_dir.name, ""
    config = json.loads(config_path.read_text())
    settings = config.get("settings", {})
    models = []
    for spec in settings.get("agents", "").split(","):
        if "@" in spec:
            models.append(spec.split("@", 1)[0])
    model = models[0] if models and len(set(models)) == 1 else ", ".join(sorted(set(models)))
    return settings.get("campaign", campaign_dir.name), model or settings.get("model", "")


def run_metrics(game: dict) -> tuple[float, float]:
    metrics = game.get("metrics", {})
    assist = metrics.get("assist_rate_sym")
    alternation = metrics.get("alternation")
    if assist is None or alternation is None:
        actions = np.asarray(game["actions"])
        b_to_a = actions[:, 1] == np.vectorize(BEATS.get)(actions[:, 0])
        a_to_b = actions[:, 0] == np.vectorize(BEATS.get)(actions[:, 1])
        assist = float((b_to_a | a_to_b).mean())
        directions = np.where(b_to_a, 1, np.where(a_to_b, -1, 0))
        assist_dirs = directions[directions != 0]
        switches = int(np.sum(assist_dirs[1:] != assist_dirs[:-1])) if len(assist_dirs) > 1 else 0
        alternation = switches / (len(assist_dirs) - 1) if len(assist_dirs) > 1 else 0.0
    return float(assist), float(alternation)


def rewards_for(game: dict) -> np.ndarray:
    rewards = game.get("rewards")
    if rewards is not None:
        return np.asarray(rewards, dtype=float)
    return np.array([payoff_pot(row) for row in game["actions"]])


def plot_condition(games: list[dict], condition: str, model: str, campaign: str,
                   out: Path, max_runs: int = 20, dpi: int = 150,
                   title: str | None = None) -> None:
    games = sorted(games, key=lambda g: int(g.get("run", 0)))[:max_runs]
    n = len(games)
    if n == 0:
        print(f"  no runs for {condition}")
        return

    cols = min(5, n)
    rows = (n + cols - 1) // cols
    fig = plt.figure(figsize=(max(7.0, 4.2 * cols), max(4.8, 3.6 * rows)),
                     constrained_layout=True)
    outer = fig.add_gridspec(rows, cols, hspace=0.45, wspace=0.35)

    handles = [Line2D([0], [0], color=COLORS[p], lw=2, label=f"Agent {p}") for p in PLAYERS]
    suptitle = title or f"{condition} — {model} — {campaign}"
    fig.suptitle(suptitle, fontsize=12)

    for idx, game in enumerate(games):
        row, col = divmod(idx, cols)
        inner = outer[row, col].subgridspec(2, 1, height_ratios=[1.0, 1.7], hspace=0.06)
        ax_score = fig.add_subplot(inner[0])
        ax_move = fig.add_subplot(inner[1], sharex=ax_score)

        actions = np.asarray(game["actions"], dtype=int)
        rounds = len(actions)
        cumulative = np.vstack([np.zeros(3), np.cumsum(rewards_for(game), axis=0)])
        assist, alternation = run_metrics(game)
        x_moves = np.arange(1, rounds + 1)
        x_score = np.arange(0, rounds + 1)

        score_span = max(1.0, float(cumulative.max() - cumulative.min()))
        score_step = max(0.2, 0.01 * score_span)
        score_plot = cumulative + np.array((-score_step, 0.0, score_step))

        for k, player in enumerate(PLAYERS):
            ax_score.plot(x_score, score_plot[:, k], color=COLORS[player], lw=1.5)
            ax_move.step(x_moves, actions[:, k] + MOVE_OFFSETS[k], where="post",
                         color=COLORS[player], lw=1.1, marker="o", markersize=2.2)

        ax_score.set_title(f"Run {int(game.get('run', idx)):02d}   "
                           f"any={assist:.2f}  alt={alternation:.2f}",
                           fontsize=8, pad=2)
        ax_score.set_ylabel("Cumulative score", fontsize=8)
        ax_score.tick_params(axis="x", labelbottom=False, labelsize=7)
        ax_score.tick_params(axis="y", labelsize=7)
        ax_score.grid(alpha=0.25)
        ax_score.margins(x=0)
        ax_score.set_ylim(bottom=min(0.0, float(score_plot.min())))

        ax_move.set_ylim(2.5, -0.5)
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


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("campaign_dir", type=Path,
                    help="llm_rps_v2 campaign directory with config.json and games/*.json")
    ap.add_argument("--out", type=Path,
                    help="output directory (default: <campaign_dir>/trajectories)")
    ap.add_argument("--conditions",
                    help="comma-separated conditions to plot (default: all found)")
    ap.add_argument("--max-runs", type=int, default=20)
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--title", help="override the figure suptitle (single condition only)")
    args = ap.parse_args()

    if not (args.campaign_dir / "games").exists():
        raise SystemExit(f"no games/ directory under {args.campaign_dir}")

    campaign, model = campaign_info(args.campaign_dir)
    games = load_games(args.campaign_dir)
    by_condition: dict[str, list[dict]] = {}
    for game in games:
        by_condition.setdefault(game.get("condition", "?"), []).append(game)

    requested = None
    if args.conditions:
        requested = [c.strip() for c in args.conditions.split(",") if c.strip()]
    ordered = [c for c in CONDITION_ORDER if c in by_condition]
    ordered += sorted(c for c in by_condition if c not in CONDITION_ORDER)
    if requested:
        ordered = [c for c in ordered if c in requested]
    if not ordered:
        raise SystemExit(f"no matching conditions under {args.campaign_dir}")

    out_dir = args.out or (args.campaign_dir / "trajectories")
    if args.title and len(ordered) != 1:
        raise SystemExit("--title requires exactly one condition")
    for condition in ordered:
        out = out_dir / f"{campaign}_{condition}.png"
        print(f"{condition}:")
        plot_condition(by_condition[condition], condition, model, campaign, out,
                       max_runs=args.max_runs, dpi=args.dpi, title=args.title)


if __name__ == "__main__":
    main()
