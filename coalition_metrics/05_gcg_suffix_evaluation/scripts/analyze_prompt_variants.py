#!/usr/bin/env python3
"""Compare multiple replayed prompt suffixes against the no-channel policy reference."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


MOVES = ("Rock", "Paper", "Scissors")


def dist(row: dict[str, Any] | None) -> list[float] | None:
    if not row or row.get("status") != "ok":
        return None
    value = row.get("recomputed_move_dist_top5")
    if not value:
        return None
    return [float(value.get(m, 0.0)) for m in MOVES]


def tv(p: list[float], q: list[float]) -> float:
    return 0.5 * sum(abs(a - b) for a, b in zip(p, q))


def pair_product(a: list[float], b: list[float]) -> list[float]:
    return [x * y for x in a for y in b]


def bootstrap_by_run(values: dict[int, list[float]], seed: int = 20261026, n_boot: int = 10000) -> dict[str, Any]:
    means = {r: sum(v) / len(v) for r, v in values.items() if v}
    xs = list(means.values())
    if not xs:
        return {"runs": 0, "mean": None, "ci95": None, "positive_runs": 0}
    rng = random.Random(seed)
    boot = sorted(sum(rng.choice(xs) for _ in xs) / len(xs) for _ in range(n_boot))
    return {"runs": len(xs), "mean": sum(xs) / len(xs),
            "ci95": [boot[int(.025*n_boot)], boot[min(n_boot-1, int(.975*n_boot))]],
            "positive_runs": sum(x > 0 for x in xs), "per_run_mean": {str(k): v for k, v in means.items()}}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True, help="intermediate_results.json from run_suffix_pilot.py")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    raw = json.loads(args.input.read_text())
    rows = {}
    failures = []
    for row in raw:
        key = (row.get("condition"), int(row.get("run", -1)), int(row.get("round", -1)),
               row.get("seat"), row.get("suffix_name"))
        rows[key] = row
        if row.get("status") != "ok":
            failures.append({"key": list(key), "error": row.get("error")})
    variants = sorted({key[4] for key in rows if key[0] == "channel_optional" and key[4] != "empty"})
    runs = sorted({key[1] for key in rows})
    rounds = sorted({key[2] for key in rows})
    context_rows = []
    by_variant_run: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))

    for run in runs:
        for rnd in rounds:
            ref = [dist(rows.get(("no_channel", run, rnd, s, "empty"))) for s in ("A", "B")]
            empty = [dist(rows.get(("channel_optional", run, rnd, s, "empty"))) for s in ("A", "B")]
            if any(x is None for x in ref + empty):
                continue
            ref_pair = pair_product(ref[0], ref[1])  # type: ignore[arg-type]
            empty_pair = pair_product(empty[0], empty[1])  # type: ignore[arg-type]
            empty_pair_tv = tv(empty_pair, ref_pair)
            for variant in variants:
                candidate = [dist(rows.get(("channel_optional", run, rnd, s, variant))) for s in ("A", "B")]
                if any(x is None for x in candidate):
                    continue
                candidate_pair = pair_product(candidate[0], candidate[1])  # type: ignore[arg-type]
                pair_improvement = empty_pair_tv - tv(candidate_pair, ref_pair)
                by_variant_run[variant][run].append(pair_improvement)
                context_rows.append({
                    "variant": variant, "run": run, "round": rnd,
                    "pair_tv_empty_to_no_channel": empty_pair_tv,
                    "pair_tv_variant_to_no_channel": tv(candidate_pair, ref_pair),
                    "pair_tv_improvement_vs_empty": pair_improvement,
                    "A_tv_improvement_vs_empty": tv(empty[0], ref[0]) - tv(candidate[0], ref[0]),  # type: ignore[arg-type]
                    "B_tv_improvement_vs_empty": tv(empty[1], ref[1]) - tv(candidate[1], ref[1]),  # type: ignore[arg-type]
                    "top5_mass_A": (rows[("channel_optional", run, rnd, "A", variant)].get("recomputed_move_dist_top5") or {}).get("mass"),
                    "top5_mass_B": (rows[("channel_optional", run, rnd, "B", variant)].get("recomputed_move_dist_top5") or {}).get("mass"),
                })

    summaries = {}
    for variant in variants:
        summaries[variant] = {
            "pair_product_tv_improvement_vs_empty_bootstrap_by_run": bootstrap_by_run(by_variant_run[variant]),
            "complete_run_round_contexts": sum(len(v) for v in by_variant_run[variant].values()),
        }
    # Separate A/B run means accurately for reporting.
    for variant in variants:
        for seat, key_name in (("A", "A"), ("B", "B")):
            values: dict[int, list[float]] = defaultdict(list)
            for row in context_rows:
                if row["variant"] == variant:
                    values[int(row["run"])].append(float(row[f"{seat}_tv_improvement_vs_empty"]))
            summaries[variant][f"{key_name}_tv_improvement_vs_empty_bootstrap_by_run"] = bootstrap_by_run(
                values, seed=20261027 if seat == "A" else 20261028)
        for seat in ("A", "B"):
            masses = [float(r[f"top5_mass_{seat}"]) for r in context_rows
                      if r["variant"] == variant and r.get(f"top5_mass_{seat}") is not None]
            summaries[variant][f"mean_top5_legal_move_mass_{seat}"] = sum(masses) / len(masses) if masses else None

    args.out.mkdir(parents=True, exist_ok=True)
    fields = list(context_rows[0]) if context_rows else ["variant", "run", "round"]
    with (args.out / "prompt_context_metrics.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(context_rows)
    summary = {
        "input": str(args.input), "variants": variants, "runs": runs, "rounds": rounds,
        "successful_variant_contexts": {v: sum(len(x) for x in by_variant_run[v].values()) for v in variants},
        "failures": failures, "variant_summaries": summaries,
        "estimand_note": "Positive TV improvement means the candidate product distribution is closer to the no-channel product reference than the empty-suffix optional-channel distribution.",
        "limitations": [
            "The product p_A x p_B is formed from two separate calls; it is not an observed joint action distribution or empirical conditional mutual information.",
            "Top-logprob move distributions are renormalized over recognized legal moves; inspect top5_mass_A/B for coverage.",
            "The no-channel and optional-channel prompts share run/round IDs but their saved histories are different.",
            "Saved-state replay is not a closed-loop full-game intervention.",
            "Bootstrap resamples complete run IDs, not rounds. Candidate/model screening remains exploratory unless the suffix and comparison are frozen beforehand.",
        ],
    }
    (args.out / "prompt_variant_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    report = ["# Archived-prompt suffix comparison", "",
              f"Source: `{args.input}`. Runs `{runs}`; rounds `{rounds}`.", "",
              "Positive improvement means closer to the no-channel reference than the empty suffix.", "",
              "| Variant | Runs | Pair-product TV gain (mean) | 95% run-bootstrap interval | Positive runs | A/B TV gains (means) | Mean top-5 legal mass A/B |",
              "|---|---:|---:|---|---:|---|---|"]
    for v in variants:
        s = summaries[v]
        b = s["pair_product_tv_improvement_vs_empty_bootstrap_by_run"]
        ci = b["ci95"]
        a = s["A_tv_improvement_vs_empty_bootstrap_by_run"]["mean"]
        bb = s["B_tv_improvement_vs_empty_bootstrap_by_run"]["mean"]
        ma, mb = s["mean_top5_legal_move_mass_A"], s["mean_top5_legal_move_mass_B"]
        report.append(f"| `{v}` | {b['runs']} | {b['mean']} | `{ci}` | {b['positive_runs']} | {a} / {bb} | {ma} / {mb} |")
    report += ["", "## Interpretation limits", "", *[f"- {x}" for x in summary["limitations"]]]
    (args.out / "REPORT.md").write_text("\n".join(report) + "\n")
    print(f"Wrote {args.out / 'REPORT.md'} and {args.out / 'prompt_context_metrics.csv'}")


if __name__ == "__main__":
    main()
