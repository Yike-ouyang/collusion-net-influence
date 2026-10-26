#!/usr/bin/env python3
"""Summarize matched fresh-game GCG suffix campaigns and write an English figure."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from coalition_metrics.analyze_campaigns import conditional_mi, expected_advantage_after_conditional_shuffle  # noqa: E402

MODEL_LABELS = {
    "qwen32b": "Qwen 2.5 32B",
    "glm32b": "GLM-4 32B",
    "mixtral8x7b": "Mixtral 8x7B",
}
ARM_ORDER = (
    "no_channel",
    "optional_empty",
    "optional_gcg_nai",
    "optional_gcg_aru",
    "optional_initial_bang5",
    "optional_random_placebo",
    "optional_counterinstruction",
)
ARM_LABELS = {
    "no_channel": "No channel",
    "optional_empty": "Optional / empty",
    "optional_gcg_nai": "GCG block 1: ない",
    "optional_gcg_aru": "GCG block 2: ある",
    "optional_initial_bang5": "Initial / !!!!!",
    "optional_random_placebo": "Random /mp",
    "optional_counterinstruction": "Cancel instruction",
}
ARM_COLORS = {
    "no_channel": "#68707d",
    "optional_empty": "#1f2937",
    "optional_gcg_nai": "#2563eb",
    "optional_gcg_aru": "#0f766e",
    "optional_initial_bang5": "#d97706",
    "optional_random_placebo": "#7c3aed",
    "optional_counterinstruction": "#dc2626",
}


def bootstrap(values: list[float], seed: int, n_boot: int = 10000) -> dict[str, Any]:
    xs = np.asarray([float(x) for x in values if math.isfinite(float(x))], dtype=float)
    if not len(xs):
        return {"n": 0, "mean": None, "ci95_low": None, "ci95_high": None}
    rng = np.random.default_rng(seed)
    draws = rng.choice(xs, size=(n_boot, len(xs)), replace=True).mean(axis=1)
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {"n": int(len(xs)), "mean": float(xs.mean()), "ci95_low": float(lo), "ci95_high": float(hi)}


def game_metrics(game: dict[str, Any], model: str, arm: str) -> dict[str, Any]:
    actions = np.asarray(game["actions"], dtype=int)
    rewards = np.asarray(game["rewards"], dtype=float)
    die = np.asarray([int(r["shared_die"]) for r in game["rounds"]], dtype=int)
    if len(actions) != len(die) or actions.shape[1] < 3:
        raise ValueError(f"bad action/die shape in {game.get('campaign')} run {game.get('run')}")

    cmi_bits = conditional_mi(actions[:, 0], actions[:, 1], die) / math.log(2.0)
    lag_states = np.empty(len(actions), dtype=int)
    if len(actions):
        lag_states[0] = 27  # distinct initial-state category
        if len(actions) > 1:
            lag_states[1:] = actions[:-1, 0] * 9 + actions[:-1, 1] * 3 + actions[:-1, 2]
    cmi_lag_bits = conditional_mi(actions[:, 0], actions[:, 1], lag_states) / math.log(2.0)
    pair_adv = float(np.mean(rewards[:, :2].mean(axis=1) - rewards[:, 2]))
    cs_ab_conditional = pair_adv - expected_advantage_after_conditional_shuffle(actions, die)
    usage = (game.get("metrics") or {}).get("channel_usage") or {}
    usage_a = usage.get("A")
    usage_b = usage.get("B")
    usage_mean = float(np.nanmean([usage_a, usage_b])) if any(
        x is not None and math.isfinite(float(x)) for x in (usage_a, usage_b)
    ) else float("nan")
    scores = game.get("final_scores") or [None, None, None]
    return {
        "model": model,
        "model_label": MODEL_LABELS.get(model, model),
        "arm": arm,
        "arm_label": ARM_LABELS.get(arm, arm),
        "campaign": game.get("campaign"),
        "condition": game.get("condition"),
        "run": int(game.get("run", -1)),
        "rounds": len(actions),
        "cmi_ab_given_shared_die_bits": float(cmi_bits),
        "cmi_ab_given_previous_abc_bits": float(cmi_lag_bits),
        "pair_advantage_ab_minus_c": pair_adv,
        "cs_ab_conditional_shuffle": float(cs_ab_conditional),
        "channel_usage_A": float(usage_a) if usage_a is not None else float("nan"),
        "channel_usage_B": float(usage_b) if usage_b is not None else float("nan"),
        "channel_usage_mean_ab": usage_mean,
        "score_A": scores[0] if len(scores) > 0 else None,
        "score_B": scores[1] if len(scores) > 1 else None,
        "score_C": scores[2] if len(scores) > 2 else None,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def campaign_identity(name: str, prefix: str) -> tuple[str, str]:
    tail = name[len(prefix):].lstrip("_")
    model, sep, arm = tail.partition("_")
    if not sep or not model or not arm:
        raise ValueError(f"expected campaign name {prefix}_<model>_<arm>, got {name!r}")
    return model, arm


def load_campaigns(results_root: Path, prefix: str) -> list[dict[str, Any]]:
    rows = []
    for campaign_dir in sorted(p for p in results_root.iterdir() if p.is_dir() and p.name.startswith(prefix)):
        model, arm = campaign_identity(campaign_dir.name, prefix)
        game_dir = campaign_dir / "games"
        for path in sorted(game_dir.glob("*.json")):
            try:
                game = json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
            if "actions" not in game or "rounds" not in game or "rewards" not in game:
                continue
            rows.append(game_metrics(game, model, arm))
    return rows


def grouped(rows: list[dict[str, Any]]) -> dict[tuple[str, str], dict[int, dict[str, Any]]]:
    out: dict[tuple[str, str], dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key = (row["model"], row["arm"])
        run = int(row["run"])
        if run in out[key]:
            raise ValueError(f"duplicate run {run} in model={key[0]} arm={key[1]}")
        out[key][run] = row
    return out


def summarize(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    data = grouped(rows)
    metrics = (
        "cmi_ab_given_shared_die_bits",
        "cmi_ab_given_previous_abc_bits",
        "pair_advantage_ab_minus_c",
        "cs_ab_conditional_shuffle",
        "channel_usage_mean_ab",
        "channel_usage_A",
        "channel_usage_B",
        "score_A", "score_B", "score_C",
    )
    arm_rows = []
    effects = []
    seed = 701
    models = sorted({model for model, _ in data}, key=lambda m: (list(MODEL_LABELS).index(m) if m in MODEL_LABELS else 99, m))
    for model in models:
        arms = sorted({arm for m, arm in data if m == model}, key=lambda a: (ARM_ORDER.index(a) if a in ARM_ORDER else 99, a))
        for arm in arms:
            games = list(data[(model, arm)].values())
            row: dict[str, Any] = {"model": model, "model_label": MODEL_LABELS.get(model, model),
                                   "arm": arm, "arm_label": ARM_LABELS.get(arm, arm), "n_games": len(games),
                                   "run_ids": ",".join(str(r) for r in sorted(data[(model, arm)]))}
            for metric in metrics:
                res = bootstrap([g[metric] for g in games if g[metric] is not None], seed)
                seed += 1
                row[f"{metric}_mean"] = res["mean"]
                row[f"{metric}_ci95_low"] = res["ci95_low"]
                row[f"{metric}_ci95_high"] = res["ci95_high"]
            arm_rows.append(row)

        baseline = data.get((model, "optional_empty"), {})
        no_channel = data.get((model, "no_channel"), {})
        all_arms = sorted({arm for m, arm in data if m == model}, key=lambda a: (ARM_ORDER.index(a) if a in ARM_ORDER else 99, a))
        for arm in all_arms:
            treatment = data[(model, arm)]
            common = sorted(set(treatment) & set(baseline))
            effect_fields = {
                "delta_cmi_vs_optional_empty": "cmi_ab_given_shared_die_bits",
                "delta_pair_advantage_vs_optional_empty": "pair_advantage_ab_minus_c",
                "delta_cs_ab_vs_optional_empty": "cs_ab_conditional_shuffle",
                "delta_channel_usage_vs_optional_empty": "channel_usage_mean_ab",
            }
            effect_row = {"model": model, "model_label": MODEL_LABELS.get(model, model),
                          "arm": arm, "arm_label": ARM_LABELS.get(arm, arm), "paired_runs_vs_empty": len(common)}
            for name, metric in effect_fields.items():
                diffs = [treatment[r][metric] - baseline[r][metric] for r in common
                         if math.isfinite(float(treatment[r][metric])) and math.isfinite(float(baseline[r][metric]))]
                res = bootstrap(diffs, seed)
                seed += 1
                effect_row[name] = res["mean"]
                effect_row[f"{name}_ci95_low"] = res["ci95_low"]
                effect_row[f"{name}_ci95_high"] = res["ci95_high"]
                effect_row[f"{name}_n"] = res["n"]

            common_ref = sorted(set(treatment) & set(baseline) & set(no_channel))
            dist_diffs = []
            for run in common_ref:
                ref = no_channel[run]["cmi_ab_given_shared_die_bits"]
                base = baseline[run]["cmi_ab_given_shared_die_bits"]
                value = treatment[run]["cmi_ab_given_shared_die_bits"]
                if all(math.isfinite(float(x)) for x in (ref, base, value)):
                    dist_diffs.append(abs(value - ref) - abs(base - ref))
            distance = bootstrap(dist_diffs, seed)
            seed += 1
            effect_row.update({
                "delta_absolute_cmi_distance_to_no_channel_vs_empty": distance["mean"],
                "distance_ci95_low": distance["ci95_low"],
                "distance_ci95_high": distance["ci95_high"],
                "distance_paired_runs": distance["n"],
            })
            effects.append(effect_row)
    return arm_rows, effects


def plot_results(out_dir: Path, arm_rows: list[dict[str, Any]], effects: list[dict[str, Any]]) -> None:
    model_order = [m for m in MODEL_LABELS if any(r["model"] == m for r in arm_rows)]
    metrics = [
        ("cmi_ab_given_shared_die_bits", "I(A;B | shared die) [bits]", "arm"),
        ("delta_absolute_cmi_distance_to_no_channel_vs_empty", "Change in CMI distance to no-channel [bits]", "effect"),
        ("pair_advantage_ab_minus_c", "Pair advantage (A+B)/2 − C [points/round]", "arm"),
        ("channel_usage_mean_ab", "Private-channel use [share of opportunities]", "arm"),
    ]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                         "axes.titlesize": 10, "figure.titlesize": 15,
                         "pdf.fonttype": 42, "ps.fonttype": 42})
    fig, axes = plt.subplots(len(model_order), len(metrics), figsize=(18, max(5.4, 2.7 * len(model_order))), squeeze=False)
    arm_order = [a for a in ARM_ORDER if any(r["arm"] == a for r in arm_rows)]
    for i, model in enumerate(model_order):
        model_arms = {r["arm"]: r for r in arm_rows if r["model"] == model}
        model_effects = {r["arm"]: r for r in effects if r["model"] == model}
        for j, (metric, title, source) in enumerate(metrics):
            ax = axes[i, j]
            visible = [a for a in arm_order if a in (model_arms if source == "arm" else model_effects)]
            if source == "effect":
                visible = [a for a in visible if a not in ("no_channel", "optional_empty")]
            y_positions = np.arange(len(visible))
            for pos, arm in zip(y_positions, visible):
                row = model_arms[arm] if source == "arm" else model_effects[arm]
                if source == "arm":
                    mean = row.get(f"{metric}_mean")
                    low = row.get(f"{metric}_ci95_low")
                    high = row.get(f"{metric}_ci95_high")
                else:
                    mean = row.get(metric)
                    low = row.get("distance_ci95_low")
                    high = row.get("distance_ci95_high")
                if mean is None or low is None or high is None or not all(math.isfinite(float(x)) for x in (mean, low, high)):
                    continue
                color = ARM_COLORS.get(arm, "#2563eb")
                ax.errorbar(float(mean), pos,
                            xerr=[[float(mean) - float(low)], [float(high) - float(mean)]],
                            fmt="o", color=color, ecolor=color, capsize=2.5, markersize=4, linewidth=1.2)
            if j == 1:
                ax.axvline(0, color="#374151", linestyle="--", linewidth=0.8)
            elif j == 2:
                ax.axvline(0, color="#9ca3af", linewidth=0.7)
            ax.set_yticks(y_positions, [ARM_LABELS.get(a, a) for a in visible])
            ax.invert_yaxis()
            ax.grid(axis="x", color="#e5e7eb", linewidth=0.7)
            ax.set_title(title)
            if j == 0:
                ax.set_ylabel(MODEL_LABELS.get(model, model))
            else:
                ax.set_ylabel("")
            if source == "effect":
                ax.text(0.98, 0.02, "negative = closer to no-channel than optional-empty",
                        transform=ax.transAxes, ha="right", va="bottom", fontsize=6.5, color="#4b5563")
    fig.suptitle("Fresh-game GCG intervention results", y=0.995, weight="bold")
    fig.text(0.5, 0.972, "Dots are arm means or paired effects; bars are 95% bootstrap intervals over complete games.",
             ha="center", va="center", fontsize=8)
    fig.tight_layout(rect=(0.02, 0.02, 0.99, 0.95), h_pad=1.6, w_pad=1.4)
    fig.savefig(out_dir / "fresh_game_metrics.png", dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(out_dir / "fresh_game_metrics.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-root", type=Path, default=Path("results/llm_rps_v2"))
    parser.add_argument("--prefix", required=True, help="campaign name prefix used by the launch script")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    rows = load_campaigns(args.campaign_root, args.prefix)
    if not rows:
        parser.error(f"No complete-game JSONs found for prefix {args.prefix!r} in {args.campaign_root}")
    arm_rows, effects = summarize(rows)
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "game_metrics.csv", rows)
    write_csv(args.out / "arm_summary.csv", arm_rows)
    write_csv(args.out / "paired_effects_vs_empty.csv", effects)
    plot_results(args.out, arm_rows, effects)

    lines = [
        "# Fresh-game GCG suffix study", "",
        f"Campaign prefix: `{args.prefix}`. Complete games found: **{len(rows)}**.",
        "", "## Per-model and per-arm results", "",
        "| Model | Arm | Games | I(A;B given shared die), bits | Pair advantage, points/round | CS_AB conditional shuffle | Channel use A/B |",
        "|---|---|---:|---|---|---|---|",
    ]
    for row in arm_rows:
        fmt = lambda key: (f"{row[key + '_mean']:.4f} [{row[key + '_ci95_low']:.4f}, {row[key + '_ci95_high']:.4f}]"
                           if row.get(key + "_mean") is not None else "—")
        usage_a, usage_b = fmt("channel_usage_A"), fmt("channel_usage_B")
        lines.append(f"| {row['model_label']} | {row['arm_label']} | {row['n_games']} | "
                     f"{fmt('cmi_ab_given_shared_die_bits')} | {fmt('pair_advantage_ab_minus_c')} | "
                     f"{fmt('cs_ab_conditional_shuffle')} | {usage_a} / {usage_b} |")
    lines += [
        "", "## Metric interpretation", "",
        "The primary coordination outcome is the per-game plug-in I(A;B | shared die), in bits. The shared die is a common cause visible to A and B, so conditioning on it is necessary. The second panel measures whether a treatment moves this CMI closer to the matched no-channel run than optional-empty; negative values mean closer.",
        "Pair advantage is (A+B)/2 − C and is reported separately from coordination. `CS_AB conditional shuffle` subtracts the expected pair advantage under a within-game, within-die shuffle; it is an association measure, not a causal effect. Channel-use rates help show whether the cancellation instruction actually changes messaging.",
        "A temporal sensitivity metric, I(A;B | previous round's A/B/C actions), is included in the CSV. With 10-round games it is extremely sparse and must be treated as a sensitivity check, not the primary result. Intervals resample complete games, not rounds. With only 6 games per arm in this pilot, intervals may remain wide; do not treat a visible point-estimate difference as confirmation. The CMI estimators are finite-sample and the bootstrap does not correct their bias.",
        "For GLM and Mixtral, the exact Unicode suffix text transfers, but Qwen token IDs and single-token status do not. The placebo `/mp` is one token in the Qwen tokenizer only.",
        "", "## Files", "",
        "- `game_metrics.csv`: one row per complete game.",
        "- `arm_summary.csv`: per-arm means and complete-game bootstrap intervals.",
        "- `paired_effects_vs_empty.csv`: paired changes from optional-empty, plus paired distance to no-channel.",
        "- `fresh_game_metrics.png` and `.pdf`: English multi-model figure.",
    ]
    (args.out / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote fresh-game results to {args.out}")


if __name__ == "__main__":
    main()
