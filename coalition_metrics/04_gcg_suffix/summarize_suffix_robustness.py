#!/usr/bin/env python3
"""Summarize a custom-suffix prompt screen against no-channel and empty suffix."""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


MOVES = ("Rock", "Paper", "Scissors")


def _dist(row: dict[str, Any]) -> dict[str, float] | None:
    value = row.get("recomputed_move_dist_top5")
    if not value:
        return None
    return {move: float(value.get(move, 0.0)) for move in MOVES}


def _tv(a: dict[str, float], b: dict[str, float]) -> float:
    return 0.5 * sum(abs(a[m] - b[m]) for m in MOVES)


def _pair_tv(a: list[dict[str, float]], b: list[dict[str, float]]) -> float:
    return 0.5 * sum(
        abs(a[0][x] * a[1][y] - b[0][x] * b[1][y])
        for x in MOVES for y in MOVES
    )


def _generated_move(row: dict[str, Any]) -> str | None:
    text = (row.get("response") or {}).get("text", "")
    found = re.findall(r"(?im)^\s*MOVE\s*[:=]\s*\**\s*(Rock|Paper|Scissors)\b", text)
    return found[-1].capitalize() if found else None


def _bootstrap_by_run(rows: list[dict[str, Any]], n_boot: int = 2000) -> dict[str, Any]:
    by_run: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        by_run[int(row["run"])].append(float(row["tv_improvement_candidate_vs_empty"]))
    run_means = {run: sum(vals) / len(vals) for run, vals in by_run.items()}
    values = list(run_means.values())
    if not values:
        return {"run_count": 0, "ci95": None}
    rng = random.Random(20261026)
    samples = sorted(sum(rng.choice(values) for _ in values) / len(values) for _ in range(n_boot))
    return {
        "run_count": len(values),
        "mean_run_improvement": sum(values) / len(values),
        "ci95": [samples[int(0.025 * n_boot)], samples[min(n_boot - 1, int(0.975 * n_boot))]],
        "per_run_mean_improvement": {str(k): v for k, v in sorted(run_means.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="intermediate_results.json from run_suffix_pilot.py")
    parser.add_argument("--out", type=Path, required=True, help="directory for CSV and report outputs")
    parser.add_argument("--candidate-key", default="candidate")
    parser.add_argument("--candidate-text", required=True)
    args = parser.parse_args()

    data = json.loads(args.input.read_text())
    indexed = {}
    errors = []
    for row in data:
        key = (row.get("condition"), int(row.get("run", -1)), int(row.get("round", -1)),
               row.get("seat"), row.get("suffix_name"))
        indexed[key] = row
        if row.get("status") != "ok":
            errors.append({"key": key, "error": row.get("error")})

    runs = sorted({int(r["run"]) for r in data})
    rounds = sorted({int(r["round"]) for r in data})
    rows = []
    for run in runs:
        for round_no in rounds:
            vectors = {condition: [] for condition in ("no_channel", "channel_optional_empty", "candidate")}
            sources = {condition: [] for condition in vectors}
            complete = True
            for seat in ("A", "B"):
                keys = {
                    "no_channel": ("no_channel", run, round_no, seat, "empty"),
                    "channel_optional_empty": ("channel_optional", run, round_no, seat, "empty"),
                    "candidate": ("channel_optional", run, round_no, seat, args.candidate_key),
                }
                for name, key in keys.items():
                    source = indexed.get(key)
                    p = _dist(source) if source else None
                    if p is None:
                        complete = False
                        break
                    vectors[name].append(p)
                    sources[name].append(source)
                if not complete:
                    break
            if not complete:
                continue
            for seat_idx, seat in enumerate(("A", "B")):
                n, e, c = (vectors[k][seat_idx] for k in ("no_channel", "channel_optional_empty", "candidate"))
                rows.append({
                    "run": run, "round": round_no, "unit": seat,
                    "tv_empty_to_no_channel": _tv(e, n),
                    "tv_candidate_to_no_channel": _tv(c, n),
                    "tv_improvement_candidate_vs_empty": _tv(e, n) - _tv(c, n),
                    "tv_candidate_vs_empty": _tv(c, e),
                    "generated_move_no_channel": _generated_move(sources["no_channel"][seat_idx]),
                    "generated_move_empty": _generated_move(sources["channel_optional_empty"][seat_idx]),
                    "generated_move_candidate": _generated_move(sources["candidate"][seat_idx]),
                    "no_channel_top5_move_mass": (sources["no_channel"][seat_idx].get("recomputed_move_dist_top5") or {}).get("mass"),
                    "empty_top5_move_mass": (sources["channel_optional_empty"][seat_idx].get("recomputed_move_dist_top5") or {}).get("mass"),
                    "candidate_top5_move_mass": (sources["candidate"][seat_idx].get("recomputed_move_dist_top5") or {}).get("mass"),
                })
            pair_empty = _pair_tv(vectors["channel_optional_empty"], vectors["no_channel"])
            pair_candidate = _pair_tv(vectors["candidate"], vectors["no_channel"])
            rows.append({
                "run": run, "round": round_no, "unit": "A+B_product",
                "tv_empty_to_no_channel": pair_empty,
                "tv_candidate_to_no_channel": pair_candidate,
                "tv_improvement_candidate_vs_empty": pair_empty - pair_candidate,
                "tv_candidate_vs_empty": _pair_tv(vectors["candidate"], vectors["channel_optional_empty"]),
                "generated_move_no_channel": None, "generated_move_empty": None,
                "generated_move_candidate": None,
                "no_channel_top5_move_mass": None, "empty_top5_move_mass": None,
                "candidate_top5_move_mass": None,
            })

    args.out.mkdir(parents=True, exist_ok=True)
    csv_path = args.out / "robustness_by_run_round.csv"
    fields = list(rows[0]) if rows else ["run", "round", "unit"]
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    player_rows = [r for r in rows if r["unit"] in ("A", "B")]
    pair_rows = [r for r in rows if r["unit"] == "A+B_product"]
    changed_moves = [r for r in player_rows if r["generated_move_empty"] != r["generated_move_candidate"]]
    mean_mass = lambda key: (sum(float(r[key]) for r in player_rows if r.get(key) is not None) /
                             sum(1 for r in player_rows if r.get(key) is not None))
    round_summary = []
    for rnd in rounds:
        subset = [r for r in pair_rows if int(r["round"]) == rnd]
        if subset:
            round_summary.append({
                "round": rnd, "contexts": len(subset),
                "mean_pair_product_tv_empty": sum(r["tv_empty_to_no_channel"] for r in subset) / len(subset),
                "mean_pair_product_tv_candidate": sum(r["tv_candidate_to_no_channel"] for r in subset) / len(subset),
                "mean_pair_product_tv_improvement": sum(r["tv_improvement_candidate_vs_empty"] for r in subset) / len(subset),
                "contexts_improved": sum(r["tv_improvement_candidate_vs_empty"] > 1e-12 for r in subset),
            })
    with (args.out / "robustness_by_round.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(round_summary[0]) if round_summary else ["round"])
        writer.writeheader()
        writer.writerows(round_summary)

    mean = lambda key, subset: sum(float(r[key]) for r in subset) / len(subset) if subset else None
    summary = {
        "candidate_key": args.candidate_key,
        "candidate_text": args.candidate_text,
        "runs": runs,
        "rounds": rounds,
        "successful_contexts": len(pair_rows),
        "player_context_rows": len(player_rows),
        "failed_requests": errors,
        "mean_player_tv_improvement_candidate_vs_empty": mean("tv_improvement_candidate_vs_empty", player_rows),
        "mean_pair_product_tv_improvement_candidate_vs_empty": mean("tv_improvement_candidate_vs_empty", pair_rows),
        "pair_product_contexts_improved": sum(r["tv_improvement_candidate_vs_empty"] > 1e-12 for r in pair_rows),
        "sampled_player_moves_changed_vs_empty": len(changed_moves),
        "sampled_player_move_changes": [{k: r[k] for k in ("run", "round", "unit", "generated_move_no_channel",
                                                              "generated_move_empty", "generated_move_candidate",
                                                              "tv_empty_to_no_channel", "tv_candidate_to_no_channel")}
                                        for r in changed_moves],
        "mean_top5_move_mass": {
            "no_channel": mean_mass("no_channel_top5_move_mass"),
            "optional_empty": mean_mass("empty_top5_move_mass"),
            "optional_candidate": mean_mass("candidate_top5_move_mass"),
        },
        "pair_product_run_cluster_bootstrap": _bootstrap_by_run(pair_rows),
        "round_summary": round_summary,
        "limitations": [
            "Top-five move log-probabilities are renormalized over the three legal moves; inspect the mass fields for coverage.",
            "A+B_product is the product of two separately queried policy distributions, not the observed joint action distribution or conditional MI.",
            "The no-channel and optional-channel contexts share run/round indices but their saved trajectories have different public histories.",
            "This replays prompts from saved states; it is not a full game rollout with the candidate suffix.",
        ],
    }
    summary_path = args.out / "robustness_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    report = [
        "# Suffix robustness screen", "",
        f"Candidate: `{args.candidate_text}` (key `{args.candidate_key}`).", "",
        f"Completed paired contexts: {len(pair_rows)}; failed requests: {len(errors)}.",
        f"Mean A/B individual TV improvement over empty suffix: {summary['mean_player_tv_improvement_candidate_vs_empty']}",
        f"Mean product-pair TV improvement over empty suffix: {summary['mean_pair_product_tv_improvement_candidate_vs_empty']}",
        f"Product-pair contexts closer to no-channel with candidate: {summary['pair_product_contexts_improved']} / {len(pair_rows)}.",
        f"Sampled A/B moves changed vs empty suffix: {len(changed_moves)} / {len(player_rows)}.",
        f"Mean top-five move mass: no-channel {summary['mean_top5_move_mass']['no_channel']:.6f}; "
        f"optional empty {summary['mean_top5_move_mass']['optional_empty']:.6f}; "
        f"candidate {summary['mean_top5_move_mass']['optional_candidate']:.6f}.",
        "", "## Round breakdown", "",
        "| Round | Contexts | Empty TV | Candidate TV | TV improvement | Improved contexts |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in round_summary:
        report.append(f"| {row['round']} | {row['contexts']} | {row['mean_pair_product_tv_empty']:.4f} | "
                      f"{row['mean_pair_product_tv_candidate']:.4f} | "
                      f"{row['mean_pair_product_tv_improvement']:.4f} | {row['contexts_improved']} |")
    report += ["", "## Sampled move changes", ""]
    if changed_moves:
        for row in changed_moves:
            report.append(f"- Run {row['run']}, round {row['round']}, player {row['unit']}: "
                          f"no-channel `{row['generated_move_no_channel']}`, empty suffix "
                          f"`{row['generated_move_empty']}`, candidate `{row['generated_move_candidate']}`; "
                          f"TV to no-channel: {row['tv_empty_to_no_channel']:.4f} → "
                          f"{row['tv_candidate_to_no_channel']:.4f}.")
    else:
        report.append("- No sampled move changed.")
    report += ["", "## Limits", ""] + [f"- {x}" for x in summary["limitations"]]
    (args.out / "REPORT.md").write_text("\n".join(report) + "\n")
    print(json.dumps({"summary": summary_path.as_posix(), "report": (args.out / 'REPORT.md').as_posix(),
                      "rows": csv_path.as_posix()}, indent=2))


if __name__ == "__main__":
    main()
