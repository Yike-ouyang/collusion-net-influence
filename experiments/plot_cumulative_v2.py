"""Plot cumulative scores for each game in v2 LLM RPS campaigns.

Usage:
    python experiments/plot_cumulative_v2.py results/llm_rps_v2/<campaign>

Writes cumulative_scores.png into the campaign folder. Each condition panel
shows every game's cumulative A/B/C scores (thin lines) and the across-game
mean (thick lines).
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

PLAYERS = ("A", "B", "C")
COLORS = {"A": "#2878b5", "B": "#e17c05", "C": "#2b8c56"}
CONDITION_ORDER = (
    "no_channel",
    "channel_optional",
    "channel_optional_hint",
    "channel_forced",
    "channel_forced_strategy",
)
CONDITION_LABELS = {
    "no_channel": "No channel",
    "channel_optional": "Optional channel",
    "channel_optional_hint": "Optional + hint",
    "channel_forced": "Forced channel",
    "channel_forced_strategy": "Forced strategy",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--out", type=Path, help="output image (default: campaign/cumulative_scores.png)")
    args = parser.parse_args()

    grouped: dict[str, list[tuple[str, np.ndarray]]] = defaultdict(list)
    for path in sorted((args.campaign / "games").glob("*_run*.json")):
        game = json.loads(path.read_text())
        rewards = np.asarray(game["rewards"], dtype=float)
        if rewards.ndim != 2 or rewards.shape[1] != 3:
            raise ValueError(f"Expected per-round rewards with shape (rounds, 3): {path}")
        grouped[game["condition"]].append((path.stem, np.vstack([np.zeros(3), np.cumsum(rewards, axis=0)])))

    if not grouped:
        raise SystemExit(f"No game JSON files found in {args.campaign / 'games'}")

    present = [condition for condition in CONDITION_ORDER if condition in grouped]
    fig, axes = plt.subplots(1, len(present), figsize=(5.2 * len(present), 4.6), sharey=True)
    if len(present) == 1:
        axes = [axes]
    for ax, condition in zip(axes, present):
        games = grouped[condition]
        rounds = games[0][1].shape[0] - 1
        if any(scores.shape[0] != rounds + 1 for _, scores in games):
            raise ValueError(f"Inconsistent round counts for condition {condition}")
        for player_idx, player in enumerate(PLAYERS):
            curves = np.stack([scores[:, player_idx] for _, scores in games])
            for curve in curves:
                ax.plot(np.arange(rounds + 1), curve, color=COLORS[player], alpha=0.17, linewidth=0.8)
            ax.plot(np.arange(rounds + 1), curves.mean(axis=0), color=COLORS[player], linewidth=2.6,
                    label=f"{player} mean (n={len(games)})")
        ax.set_title(f"{CONDITION_LABELS.get(condition, condition)}\n{len(games)} games × {rounds} rounds")
        ax.set_xlabel("Round")
        ax.grid(True, alpha=0.22)
        ax.set_xlim(0, rounds)
    axes[0].set_ylabel("Cumulative points")
    axes[-1].legend(frameon=False, loc="upper left")
    fig.suptitle(f"Cumulative scores by player — {args.campaign.name}", y=1.03, fontsize=14)
    fig.tight_layout()
    out = args.out or (args.campaign / "cumulative_scores.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    print(out)


if __name__ == "__main__":
    main()
