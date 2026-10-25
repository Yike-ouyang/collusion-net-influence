"""Analyze coalition payoff advantage and context-conditioned transfer reference."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from coalition_metrics.analyze_campaigns import game_statistics, mean_ci_by_game, write_csv  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("campaigns", nargs="+", type=Path)
    ap.add_argument("--seed", type=int, default=20261025)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    rows = []
    for campaign in args.campaigns:
        paths = sorted((campaign / "games").glob("*_run*.json"))
        if not paths:
            ap.error(f"No games found in {campaign / 'games'}")
        rows.extend(game_statistics(json.loads(path.read_text())) for path in paths)

    summary = []
    cells = sorted({(r["campaign"], r["condition"]) for r in rows})
    for campaign, condition in cells:
        cell = [r for r in rows if r["campaign"] == campaign and r["condition"] == condition]
        result = {"campaign": campaign, "condition": condition, "games": len(cell)}
        for metric in ("pair_advantage", "conditional_shuffle_transfer"):
            mean, lo, hi = mean_ci_by_game(np.asarray([r[metric] for r in cell]), rng)
            result.update({f"{metric}_mean": mean, f"{metric}_ci95_low": lo, f"{metric}_ci95_high": hi})
        summary.append(result)

    differences = []
    for campaign, _ in cells:
        base = [r for r in rows if r["campaign"] == campaign and r["condition"] == "no_channel"]
        if not base:
            continue
        conditions = sorted({r["condition"] for r in rows if r["campaign"] == campaign and r["condition"] != "no_channel"})
        for condition in conditions:
            treatment = [r for r in rows if r["campaign"] == campaign and r["condition"] == condition]
            result = {"campaign": campaign, "condition": condition, "reference": "no_channel",
                      "games_treatment": len(treatment), "games_reference": len(base)}
            for metric in ("pair_advantage", "conditional_shuffle_transfer"):
                diffs = np.asarray([r[metric] for r in treatment])[:, None] - np.asarray([r[metric] for r in base])[None, :]
                draws = rng.choice(np.arange(len(treatment)), size=(4000, len(treatment)))
                base_draws = rng.choice(np.arange(len(base)), size=(4000, len(base)))
                boot = np.asarray([np.mean(np.asarray([r[metric] for r in treatment])[draws[i]])
                                   - np.mean(np.asarray([r[metric] for r in base])[base_draws[i]]) for i in range(4000)])
                result.update({f"{metric}_difference": float(diffs.mean()),
                               f"{metric}_difference_ci95_low": float(np.quantile(boot, 0.025)),
                               f"{metric}_difference_ci95_high": float(np.quantile(boot, 0.975))})
            differences.append(result)

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "game_metrics.csv", rows)
    write_csv(args.out / "condition_summary.csv", summary)
    write_csv(args.out / "condition_differences.csv", differences)
    print(f"Wrote transfer outputs to {args.out}")


if __name__ == "__main__":
    main()
