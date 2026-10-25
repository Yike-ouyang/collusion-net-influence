"""Export observable agreement, plan adherence, and chat for human review."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from coalition_metrics.analyze_campaigns import mean_ci_by_game, write_csv  # noqa: E402


def round_agreement(rec: dict, moves: list[int]) -> tuple[float, float, float]:
    plans = rec.get("plans") or {}
    a, b = plans.get("A") or {}, plans.get("B") or {}
    valid_a = a.get("A") is not None and a.get("B") is not None
    valid_b = b.get("A") is not None and b.get("B") is not None
    if not (valid_a and valid_b):
        return float("nan"), float("nan"), float("nan")
    agree = float((a["A"], a["B"]) == (b["A"], b["B"]))
    executed = float(agree and tuple(moves[:2]) == (a["A"], a["B"]))
    own_follow = float((moves[0] == a["A"] and moves[1] == b["B"]))
    return agree, executed, own_follow


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("campaigns", nargs="+", type=Path)
    ap.add_argument("--seed", type=int, default=20261025)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    per_game, message_rows = [], []
    for campaign in args.campaigns:
        paths = sorted((campaign / "games").glob("*_run*.json"))
        if not paths:
            ap.error(f"No games found in {campaign / 'games'}")
        for path in paths:
            game = json.loads(path.read_text())
            agrees, executed, follows = [], [], []
            message_count = 0
            for rec in game["rounds"]:
                agreement, execution, follow = round_agreement(rec, rec["moves"])
                if not np.isnan(agreement):
                    agrees.append(agreement)
                    executed.append(execution)
                    follows.append(follow)
                for msg in rec.get("chat") or []:
                    message_count += 1
                    message_rows.append({"campaign": game["campaign"], "condition": game["condition"],
                                         "run": game["run"], "round": msg.get("round"),
                                         "turn": msg.get("turn"), "from": msg.get("from"),
                                         "text": msg.get("text", "")})
            per_game.append({"campaign": game["campaign"], "condition": game["condition"], "run": game["run"],
                             "rounds": len(game["rounds"]), "messages": message_count,
                             "rounds_with_two_valid_plans": len(agrees),
                             "plans_agree_rate": float(np.mean(agrees)) if agrees else float("nan"),
                             "agreed_plans_executed_rate": float(np.mean(executed)) if executed else float("nan"),
                             "own_plan_follow_rate": float(np.mean(follows)) if follows else float("nan")})

    summary = []
    for campaign, condition in sorted({(r["campaign"], r["condition"]) for r in per_game}):
        cell = [r for r in per_game if r["campaign"] == campaign and r["condition"] == condition]
        row = {"campaign": campaign, "condition": condition, "games": len(cell),
               "mean_messages_per_game": float(np.mean([r["messages"] for r in cell])),
               "games_with_parsed_plans": sum(r["rounds_with_two_valid_plans"] > 0 for r in cell)}
        for metric in ("plans_agree_rate", "agreed_plans_executed_rate", "own_plan_follow_rate"):
            vals = np.asarray([r[metric] for r in cell], dtype=float)
            vals = vals[np.isfinite(vals)]
            if len(vals):
                mean, lo, hi = mean_ci_by_game(vals, rng)
                row.update({f"{metric}_mean": mean, f"{metric}_ci95_low": lo, f"{metric}_ci95_high": hi})
            else:
                row.update({f"{metric}_mean": "", f"{metric}_ci95_low": "", f"{metric}_ci95_high": ""})
        summary.append(row)

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "game_metrics.csv", per_game)
    write_csv(args.out / "condition_summary.csv", summary)
    with (args.out / "messages_for_review.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["campaign", "condition", "run", "round", "turn", "from", "text"])
        writer.writeheader()
        writer.writerows(message_rows)
    print(f"Wrote agreement outputs to {args.out}")


if __name__ == "__main__":
    main()
