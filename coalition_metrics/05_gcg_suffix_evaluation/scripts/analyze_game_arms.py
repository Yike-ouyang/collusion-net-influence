#!/usr/bin/env python3
"""Summarize complete-game intervention campaigns with game-level paired bootstrap CIs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def action_cmi(actions: list[list[int]]) -> float:
    """Plug-in I(A_t;B_t | previous round's full A/B/C action), in bits."""
    groups: dict[tuple[int, int, int], Counter[tuple[int, int]]] = defaultdict(Counter)
    previous = (-1, -1, -1)
    for row in actions:
        if len(row) < 3:
            continue
        a, b, c = map(int, row[:3])
        groups[previous][(a, b)] += 1
        previous = (a, b, c)
    n = sum(sum(c.values()) for c in groups.values())
    if not n:
        return float("nan")
    value = 0.0
    for counts in groups.values():
        ns = sum(counts.values())
        pa, pb = Counter(), Counter()
        for (a, b), count in counts.items():
            pa[a] += count; pb[b] += count
        for (a, b), count in counts.items():
            value += count / n * math.log2(count * ns / (pa[a] * pb[b]))
    return value


def mean_ci(values: list[float], seed: int = 20261026, n_boot: int = 10000) -> dict[str, Any]:
    xs = [float(x) for x in values if math.isfinite(float(x))]
    if not xs:
        return {"n": 0, "mean": None, "ci95": None}
    rng = random.Random(seed)
    boot = sorted(sum(rng.choice(xs) for _ in xs) / len(xs) for _ in range(n_boot))
    return {"n": len(xs), "mean": sum(xs) / len(xs),
            "ci95": [boot[int(.025*n_boot)], boot[min(n_boot-1, int(.975*n_boot))]]}


def load_arm(path: Path, label: str) -> dict[int, dict[str, Any]]:
    games_dir = path / "games" if (path / "games").is_dir() else path
    files = sorted(games_dir.glob("*.json"))
    out = {}
    for fp in files:
        try:
            game = json.loads(fp.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        # Each arm path should contain one pre-specified condition. Ignore unrelated report/cache JSONs.
        if "rounds" not in game or "actions" not in game:
            continue
        run = int(game.get("run", -1))
        metrics = game.get("metrics") or {}
        scores = game.get("final_scores") or [None, None, None]
        usage = metrics.get("channel_usage") or {}
        out[run] = {
            "arm": label, "campaign": game.get("campaign", path.name), "condition": game.get("condition"),
            "run": run, "rounds": len(game["actions"]), "cmi_ab_given_prev_joint_action_bits": action_cmi(game["actions"]),
            "pair_advantage": metrics.get("pair_advantage"), "cs_ab_net_transfer": metrics.get("net_transfer"),
            "channel_usage_A": usage.get("A"), "channel_usage_B": usage.get("B"),
            "score_A": scores[0] if len(scores) > 0 else None,
            "score_B": scores[1] if len(scores) > 1 else None,
            "score_C": scores[2] if len(scores) > 2 else None,
            "plan_executed_agreement": metrics.get("executed_agreement"),
        }
    return out


def paired_bootstrap(base: dict[int, dict[str, Any]], treatment: dict[int, dict[str, Any]],
                     field: str, seed: int) -> dict[str, Any]:
    ids = sorted(set(base) & set(treatment))
    diffs = []
    per_run = {}
    for run in ids:
        x, y = base[run].get(field), treatment[run].get(field)
        if x is None or y is None:
            continue
        try:
            delta = float(y) - float(x)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(delta):
            continue
        diffs.append(delta); per_run[str(run)] = delta
    ci = mean_ci(diffs, seed)
    ci.update({"paired_runs": len(diffs), "per_run_treatment_minus_base": per_run,
               "positive_differences": sum(x > 0 for x in diffs)})
    return ci


def paired_cmi_distance(reference: dict[int, dict[str, Any]], optional_empty: dict[int, dict[str, Any]],
                        treatment: dict[int, dict[str, Any]], seed: int) -> dict[str, Any]:
    ids = sorted(set(reference) & set(optional_empty) & set(treatment))
    diffs = []
    per_run = {}
    field = "cmi_ab_given_prev_joint_action_bits"
    for run in ids:
        try:
            ref = float(reference[run][field])
            base = float(optional_empty[run][field])
            candidate = float(treatment[run][field])
        except (TypeError, ValueError, KeyError):
            continue
        if not all(math.isfinite(x) for x in (ref, base, candidate)):
            continue
        delta = abs(candidate - ref) - abs(base - ref)
        diffs.append(delta); per_run[str(run)] = delta
    ci = mean_ci(diffs, seed)
    ci.update({"paired_runs": len(diffs), "per_run_distance_change_vs_empty": per_run,
               "negative_means_closer_to_no_channel": True})
    return ci


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--arm", action="append", required=True, metavar="LABEL=CAMPAIGN_DIR",
                   help="repeat for each arm; e.g. --arm optional_gcg=results/.../campaign")
    p.add_argument("--baseline", default="optional_empty", help="arm used as paired baseline")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    arms: dict[str, dict[int, dict[str, Any]]] = {}
    for item in args.arm:
        label, sep, value = item.partition("=")
        if not sep or not label or label in arms:
            p.error(f"--arm expects unique LABEL=CAMPAIGN_DIR; got {item!r}")
        arms[label] = load_arm(Path(value), label)
    if args.baseline not in arms:
        p.error(f"baseline {args.baseline!r} is not among arms: {sorted(arms)}")

    args.out.mkdir(parents=True, exist_ok=True)
    rows = [row for arm in arms.values() for row in arm.values()]
    fields = list(rows[0]) if rows else ["arm", "run"]
    with (args.out / "game_level_metrics.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

    baseline = arms[args.baseline]
    metric_fields = ("cmi_ab_given_prev_joint_action_bits", "pair_advantage", "cs_ab_net_transfer",
                     "score_A", "score_B", "score_C", "channel_usage_A", "channel_usage_B")
    summary = {"baseline": args.baseline, "arms": {}, "interpretation": {
        "positive_cmi_difference": "more action dependence than baseline; negative means less",
        "pair_advantage": "(A+B)/2 minus C per round; report separately from action dependence",
        "bootstrap_unit": "complete game/run; paired by the same run ID across arms",
        "cmi_context": "previous round's joint action of A, B, and C; first round is its own start state",
    }}
    for label, arm in arms.items():
        summary["arms"][label] = {
            "runs": sorted(arm), "n_games": len(arm),
            "metrics": {field: mean_ci([float(r[field]) for r in arm.values()
                                        if r.get(field) is not None and math.isfinite(float(r[field]))],
                                       seed=20261026 + i)
                        for i, field in enumerate(metric_fields)},
        }
        if label != args.baseline:
            summary["arms"][label]["paired_difference_vs_baseline"] = {
                field: paired_bootstrap(baseline, arm, field, 20300101 + i)
                for i, field in enumerate(metric_fields)
            }
            if label != "no_channel" and "no_channel" in arms:
                summary["arms"][label]["paired_cmi_distance_to_no_channel_vs_empty"] = paired_cmi_distance(
                    arms["no_channel"], baseline, arm, 20400101)
    (args.out / "game_arm_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    lines = ["# Complete-game intervention comparison", "",
             f"Paired baseline: `{args.baseline}`.", "",
             "## Per-arm game-cluster means and 95% bootstrap intervals", "",
             "| Arm | N games | CMI A/B given previous joint action (bits) | Pair advantage | CS_AB / net transfer | Mean channel use A/B |",
             "|---|---:|---|---|---|---|"]
    for label, data in summary["arms"].items():
        met = data["metrics"]
        fmt = lambda x: f"{x['mean']:.4f} [{x['ci95'][0]:.4f}, {x['ci95'][1]:.4f}]" if x["mean"] is not None else "—"
        lines.append(f"| `{label}` | {data['n_games']} | {fmt(met['cmi_ab_given_prev_joint_action_bits'])} | "
                     f"{fmt(met['pair_advantage'])} | {fmt(met['cs_ab_net_transfer'])} | "
                     f"{fmt(met['channel_usage_A'])} / {fmt(met['channel_usage_B'])} |")
    lines += ["", "## Paired treatment-minus-baseline differences", "",
              "For CMI, a negative difference means lower dependence than the selected baseline.", "",
              "| Arm | Outcome | Mean difference [95% paired run-bootstrap CI] | Paired runs |",
              "|---|---|---:|---:|"]
    for label, data in summary["arms"].items():
        if label == args.baseline:
            continue
        for field in metric_fields:
            x = data["paired_difference_vs_baseline"][field]
            val = f"{x['mean']:.4f} [{x['ci95'][0]:.4f}, {x['ci95'][1]:.4f}]" if x["mean"] is not None else "—"
            lines.append(f"| `{label}` | `{field}` | {val} | {x['paired_runs']} |")
    if "no_channel" in arms:
        lines += ["", "## Does treatment CMI move toward the no-channel reference?", "",
                  "This is the treatment's absolute CMI distance to no-channel minus the empty optional-channel arm's distance; negative means closer.", "",
                  "| Arm | Mean paired distance change [95% CI] | Paired runs |",
                  "|---|---:|---:|"]
        for label, data in summary["arms"].items():
            metric = data.get("paired_cmi_distance_to_no_channel_vs_empty")
            if metric:
                val = f"{metric['mean']:.4f} [{metric['ci95'][0]:.4f}, {metric['ci95'][1]:.4f}]" if metric["mean"] is not None else "—"
                lines.append(f"| `{label}` | {val} | {metric['paired_runs']} |")
    lines += ["", "## Limitations", "",
              "- Confidence intervals resample complete games, not rounds.",
              "- The plug-in CMI is estimated from only 60 rounds per game and can be noisy; include block/permutation sensitivity analyses.",
              "- `CS_AB/net_transfer`, pair advantage, and CMI answer different questions; interpret them separately.",
              "- Use matched run IDs and seed offsets across arms. If IDs or seeds differ, report the comparison as unpaired."]
    (args.out / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote {args.out / 'REPORT.md'} and {args.out / 'game_level_metrics.csv'}")


if __name__ == "__main__":
    main()
