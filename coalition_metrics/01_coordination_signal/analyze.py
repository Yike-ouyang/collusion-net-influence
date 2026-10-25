"""Analyze context-conditioned action dependence in v2 RPS campaigns."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from coalition_metrics.analyze_campaigns import (  # noqa: E402
    PAIR_NAMES, PAIRS, conditional_mi, mean_ci_by_game, pair_mis, permute_columns, strata, write_csv,
)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("campaigns", nargs="+", type=Path)
    ap.add_argument("--permutations", type=int, default=999)
    ap.add_argument("--seed", type=int, default=20261025)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    games = []
    for campaign in args.campaigns:
        paths = sorted((campaign / "games").glob("*_run*.json"))
        if not paths:
            ap.error(f"No games found in {campaign / 'games'}")
        games.extend(json.loads(path.read_text()) for path in paths)

    per_game = []
    summary = []
    for game in games:
        actions = np.asarray(game["actions"], dtype=int)
        die = np.asarray([r["shared_die"] for r in game["rounds"]], dtype=int)
        gamma = pair_mis(actions, die)
        gamma_by_pair = dict(zip(PAIR_NAMES, gamma))
        per_game.append({
            "campaign": game["campaign"], "condition": game["condition"], "run": game["run"],
            **{f"cmi_{name}_given_die": float(gamma_by_pair[name]) for name in PAIR_NAMES},
            "net_A_to_B": float(gamma_by_pair["AB"] - gamma_by_pair["BC"]),
            "net_B_to_A": float(gamma_by_pair["AB"] - gamma_by_pair["AC"]),
        })

    cells = sorted({(g["campaign"], g["condition"]) for g in games})
    for campaign, condition in cells:
        selected = [g for g in games if g["campaign"] == campaign and g["condition"] == condition]
        actions = np.concatenate([np.asarray(g["actions"], dtype=int) for g in selected])
        die = np.concatenate([[r["shared_die"] for r in g["rounds"]] for g in selected]).astype(int)
        game_ids = np.concatenate([np.full(len(g["actions"]), i, dtype=int) for i, g in enumerate(selected)])
        groups = strata(game_ids, die)
        observed = pair_mis(actions, die)
        exceed = np.zeros(len(PAIRS), dtype=int)
        for _ in range(args.permutations):
            exceed += pair_mis(permute_columns(actions, groups, rng), die) >= observed
        p = (1 + exceed) / (args.permutations + 1)
        cell = [r for r in per_game if r["campaign"] == campaign and r["condition"] == condition]
        row = {"campaign": campaign, "condition": condition, "games": len(cell)}
        for name in (*[f"cmi_{p}_given_die" for p in PAIR_NAMES], "net_A_to_B", "net_B_to_A"):
            mean, lo, hi = mean_ci_by_game(np.asarray([r[name] for r in cell]), rng)
            row.update({f"{name}_mean": mean, f"{name}_ci95_low": lo, f"{name}_ci95_high": hi})
        for k, name in enumerate(PAIR_NAMES):
            row[f"{name}_p_raw"] = float(p[k])
            row[f"{name}_p_bonferroni"] = float(min(1.0, 3 * p[k]))
        summary.append(row)

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "game_metrics.csv", per_game)
    write_csv(args.out / "condition_summary.csv", summary)
    print(f"Wrote coordination outputs to {args.out}")


if __name__ == "__main__":
    main()
