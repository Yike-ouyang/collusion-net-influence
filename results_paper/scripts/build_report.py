#!/usr/bin/env python3
"""Rebuild paper-facing summary tables and English figures from archived results."""
from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results_paper"
DATA = OUT / "data"
FIG = OUT / "figures"
GCG = DATA / "gcg_qwen_pilot"

MODEL_DIRS = {
    "Qwen2.5-32B": ROOT / "results/llm_rps_v2/20261025-1834_same_model_qwen32b_big-v4",
    "GLM-4-32B": ROOT / "results/llm_rps_v2/20261025-1837_same_model_glm32b_big-v4",
    "Mixtral-8x7B": ROOT / "results/llm_rps_v2/20261025-1853_same_model_mixtral8x7b_big-v4",
}
COLORS = {
    "Qwen2.5-32B": "#3478bf",
    "GLM-4-32B": "#e07a27",
    "Mixtral-8x7B": "#3a9d73",
}
CONDITION_LABELS = {
    "no_channel": "No channel",
    "channel_optional": "Optional channel",
    "channel_optional_hint": "Optional + hint",
    "channel_forced": "Forced channel",
    "channel_forced_strategy": "Forced strategy",
}


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def save_figure(fig, stem: str):
    fig.savefig(FIG / f"{stem}.png", dpi=220, bbox_inches="tight")
    fig.savefig(FIG / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def collect_game_summary():
    rows = []
    for model, folder in MODEL_DIRS.items():
        for row in read_csv(folder / "summary.csv"):
            # Expected form: +0.20 [+0.14, +0.25]
            value = row["A+B vs C /round"]
            mean_text, ci_text = value.split("[", 1)
            mean = float(mean_text.strip())
            lo, hi = [float(x.strip().replace("+", "")) for x in ci_text.rstrip("] ").split(",")]
            rows.append({
                "model": model,
                "condition": row["condition"],
                "games": row["games"],
                "pair_advantage_per_round": mean,
                "ci95_low": lo,
                "ci95_high": hi,
                "CS_AB": row["CS_AB"],
                "channel_use_A_B": row["channel use A / B"],
                "same_move": row["same move"],
                "plan_executed": row["plan executed"],
            })
    write_csv(DATA / "game_condition_summary.csv", rows, list(rows[0]))
    return rows


def plot_game_summary(rows):
    conditions = list(CONDITION_LABELS)
    x = np.arange(len(conditions))
    offsets = [-0.23, 0.0, 0.23]
    fig, ax = plt.subplots(figsize=(12.3, 5.6))
    for (model, _), offset in zip(MODEL_DIRS.items(), offsets):
        by_condition = {r["condition"]: r for r in rows if r["model"] == model}
        ys = [by_condition[c]["pair_advantage_per_round"] for c in conditions]
        los = [ys[i] - by_condition[c]["ci95_low"] for i, c in enumerate(conditions)]
        his = [by_condition[c]["ci95_high"] - ys[i] for i, c in enumerate(conditions)]
        ax.errorbar(x + offset, ys, yerr=[los, his], fmt="o", capsize=3,
                    color=COLORS[model], label=model, linewidth=1.5, markersize=6)
    ax.axhline(0, color="#555555", linewidth=1, linestyle="--")
    ax.set_xticks(x, [CONDITION_LABELS[c] for c in conditions], rotation=12, ha="right")
    ax.set_ylabel("Pair advantage per round: (A + B)/2 − C")
    ax.set_title("Game outcomes across communication and strategy conditions")
    ax.legend(frameon=False, ncol=3, loc="upper left")
    ax.grid(axis="y", alpha=.2)
    ax.text(.01, -.29, "20 complete 60-round games per model and condition. Bars show the reported 95% intervals.",
            transform=ax.transAxes, fontsize=9, color="#555555")
    fig.subplots_adjust(bottom=.28)
    save_figure(fig, "fig01_pair_advantage")


def collect_cmi():
    src = DATA / "action_dependence_summary.csv"
    rows = read_csv(src)
    fields = list(rows[0])
    write_csv(DATA / "action_dependence_summary.csv", rows, fields)
    return rows


def plot_cmi(rows):
    models = list(MODEL_DIRS)
    fig, ax = plt.subplots(figsize=(10.6, 5.3))
    offsets = [-.19, .19]
    for group, model in enumerate(models):
        mrows = [r for r in rows if r["model"] == model]
        mrows.sort(key=lambda r: 0 if r["condition"] == "no_channel" else 1)
        vals = [float(r["I_AB_given_prev_joint_action_bits"]) for r in mrows]
        null95 = [float(r["permutation_null_q95_bits"]) for r in mrows]
        ps = [float(r["permutation_p"]) for r in mrows]
        xlocs = [group + offsets[0], group + offsets[1]]
        colors = ["#9aa6b2", COLORS[model]]
        ax.bar(xlocs, vals, color=colors, width=.31, zorder=2)
        for xloc, val, q95, p in zip(xlocs, vals, null95, ps):
            ax.hlines(q95, xloc - .155, xloc + .155, color="#262626", linestyle=":", linewidth=1.6, zorder=3)
            ax.text(xloc, val + .013, f"{val:.3f}\np={p:.3f}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(range(len(models)), models)
    ax.set_ylabel("I(A; B | previous joint actions), bits")
    ax.set_title("State-conditioned action dependence")
    ax.grid(axis="y", alpha=.2, zorder=0)
    ax.set_ylim(0, .60)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#9aa6b2", label="No channel"), Patch(color=COLORS[models[0]], label="Optional channel")],
              frameon=False, ncol=2, loc="upper left")
    fig.text(.5, .01, "Dotted marks: condition-specific 95th percentile of the permutation null. 500 permutations; p-values use the same null.",
             ha="center", fontsize=9, color="#555555")
    fig.subplots_adjust(bottom=.17, top=.87)
    save_figure(fig, "fig02_action_dependence")


def plot_initial_gcg():
    # The small first GCG pilot's exact aggregate scores, copied from its audit report.
    rows = [
        {"split": "Training", "prompt": "Empty suffix", "kl_nats": 34.726},
        {"split": "Training", "prompt": "!!!!!", "kl_nats": 35.078},
        {"split": "Training", "prompt": "Learned `网`", "kl_nats": 31.658},
        {"split": "Validation", "prompt": "Empty suffix", "kl_nats": 41.407},
        {"split": "Validation", "prompt": "!!!!!", "kl_nats": 42.343},
        {"split": "Validation", "prompt": "Learned `网`", "kl_nats": 39.620},
    ]
    write_csv(DATA / "first_gcg_pilot_kl.csv", rows, list(rows[0]))
    splits = ["Training", "Validation"]
    prompts = ["Empty suffix", "!!!!!", "Learned `网`"]
    colors = ["#9aa6b2", "#d5a441", "#3478bf"]
    x = np.arange(len(splits))
    width = .22
    fig, ax = plt.subplots(figsize=(8.5, 5.1))
    for j, (prompt, color) in enumerate(zip(prompts, colors)):
        vals = [next(r["kl_nats"] for r in rows if r["split"] == s and r["prompt"] == prompt) for s in splits]
        ax.bar(x + (j - 1) * width, vals, width, label=prompt, color=color)
        for xx, yy in zip(x + (j - 1) * width, vals):
            ax.text(xx, yy + .35, f"{yy:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x, splits)
    ax.set_ylabel("Mean objective KL (nats; lower is better)")
    ax.set_title("First GCG pilot: learned token lowers the proxy loss")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=.2)
    ax.text(.01, -.22, "5 training games; 4 validation games (12–15). The candidate was selected using this small validation set; it is not an untouched test set.",
            transform=ax.transAxes, fontsize=9, color="#555555")
    fig.subplots_adjust(bottom=.26)
    save_figure(fig, "fig03_first_gcg_objective")


def collect_chronological_gcg():
    files = [GCG / "qwen32b_chronological_bang5_runs_0_4.json",
             GCG / "qwen32b_chronological_bang5_runs_5_9.json"]
    rows = []
    candidate_counts = Counter()
    by_block = defaultdict(set)
    run_meta = {}
    for path in files:
        d = json.loads(path.read_text(encoding="utf-8"))
        for rid, run in d["runs"].items():
            is_complete = len(run.get("blocks", [])) == 6 and bool(run.get("final_suffix_after_round_60"))
            run_meta[int(rid)] = is_complete
            for block in run.get("blocks", []):
                b = block["block_index"]
                suffix = block.get("suffix_after", "")
                changed = suffix != block.get("suffix_before", "")
                tok_ids = block.get("suffix_token_ids_after", [])
                preq = block.get("next_block_prequential") or {}
                gain = preq.get("gain_bits_vs_empty")
                rows.append({
                    "run": int(rid), "complete_run": int(is_complete), "block": b,
                    "rounds_updated_on": "{}-{}".format(*block.get("rounds_in_new_block", [None, None])),
                    "suffix_after_update": suffix,
                    "changed_from_previous_block": int(changed),
                    "token_ids": " ".join(str(x) for x in tok_ids),
                    "next_block_gain_bits_vs_empty": "" if gain is None else f"{gain:.9g}",
                    "next_block_rounds": "" if not preq else "{}-{}".format(*preq.get("rounds", [None, None])),
                })
                if changed:
                    candidate_counts[(b, suffix)] += 1
                    by_block[b].add(suffix)
    write_csv(DATA / "chronological_gcg_paths.csv", rows, list(rows[0]))

    completed_ids = {rid for rid, complete in run_meta.items() if complete}
    recurrence = []
    for (block, suffix), count in candidate_counts.items():
        runs = {int(r["run"]) for r in rows if r["block"] == block and r["suffix_after_update"] == suffix and r["changed_from_previous_block"] == 1 and int(r["run"]) in completed_ids}
        partial_runs = sorted({int(r["run"]) for r in rows if r["block"] == block and r["suffix_after_update"] == suffix and r["changed_from_previous_block"] == 1 and int(r["run"]) not in completed_ids})
        recurrence.append({
            "block": block, "suffix": suffix, "distinct_complete_runs": len(runs),
            "complete_run_ids": " ".join(map(str, sorted(runs))),
            "partial_run_ids": " ".join(map(str, partial_runs)),
            "complete_runs_available": len(completed_ids),
        })
    recurrence.sort(key=lambda r: (r["block"], -r["distinct_complete_runs"], r["suffix"]))
    write_csv(DATA / "chronological_gcg_recurrence.csv", recurrence, list(recurrence[0]))
    gain_rows = []
    for block in range(1, 7):
        selected = [r for r in rows if int(r["block"]) == block and r["next_block_gain_bits_vs_empty"]]
        values = [float(r["next_block_gain_bits_vs_empty"]) for r in selected]
        gain_rows.append({
            "block": block,
            "next_block_rounds": "" if not selected else selected[0]["next_block_rounds"],
            "n_run_contexts": len(values),
            "mean_gain_bits": "" if not values else f"{np.mean(values):.6f}",
            "median_gain_bits": "" if not values else f"{np.median(values):.6f}",
            "positive_gains": sum(v > 0 for v in values),
            "run_ids": " ".join(str(r["run"]) for r in selected),
        })
    write_csv(DATA / "chronological_gcg_prequential_summary.csv", gain_rows, list(gain_rows[0]))
    return rows, recurrence, sorted(completed_ids), sorted(rid for rid, complete in run_meta.items() if not complete)


def plot_gcg_paths(rows, recurrence, complete_ids, partial_ids):
    run_ids = complete_ids + partial_ids
    blocks = range(1, 7)
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(12.4, 7.2), gridspec_kw={"height_ratios": [2.2, 1]})
    mapping = {(int(r["run"]), int(r["block"])): r for r in rows}
    for i, rid in enumerate(run_ids):
        for block in blocks:
            row = mapping.get((rid, block))
            if row is None:
                continue
            suffix = row["suffix_after_update"].strip()
            ax.text(block - .5, i, suffix if len(suffix) < 17 else suffix[:15] + "…",
                    ha="center", va="center", fontsize=7,
                    bbox={"boxstyle": "round,pad=.23", "facecolor": "#dce8f5" if rid in complete_ids else "#f4e5c8", "edgecolor": "none"})
    ax.set_xlim(0, 6)
    ax.set_ylim(len(run_ids) - .5, -.5)
    ax.set_xticks(np.arange(6) + .5, [f"Block {i}\nR{(i-1)*10+1}–{i*10}" for i in range(1, 7)])
    ax.set_yticks(range(len(run_ids)), [f"Run {r}" + (" (partial)" if r in partial_ids else "") for r in run_ids])
    ax.set_title("Accepted suffix by chronological update block (starting from `!!!!!`)")
    ax.grid(axis="x", color="white", linewidth=1.5)
    ax.set_axisbelow(True)

    gains_by_block = defaultdict(list)
    for r in rows:
        g = r["next_block_gain_bits_vs_empty"]
        if g:
            gains_by_block[int(r["block"])].append((int(r["run"]), float(g)))
    for b in blocks:
        pairs = gains_by_block[b]
        vals = [v for _, v in pairs]
        xx = np.full(len(vals), b) + np.linspace(-.13, .13, len(vals)) if vals else []
        ax2.scatter(xx, vals, color="#3478bf" if b <= 5 else "#8f8f8f", alpha=.75, s=30)
        if vals:
            ax2.plot([b - .22, b + .22], [np.mean(vals)] * 2, color="#222222", linewidth=2)
            ax2.text(b, np.mean(vals) + .2, f"mean {np.mean(vals):.2f}", ha="center", fontsize=7)
    ax2.axhline(0, color="#555555", linestyle="--", linewidth=1)
    ax2.set_xticks(list(blocks), [f"{b} → {b+1}" if b < 6 else "6 (final)" for b in blocks])
    ax2.set_xlabel("Suffix learned on the first block, evaluated on the next block")
    ax2.set_ylabel("KL reduction vs empty (bits)")
    ax2.set_title("Next-block prequential objective gain")
    ax2.grid(axis="y", alpha=.2)
    fig.text(.5, .005, f"{len(complete_ids)} full runs; run(s) {', '.join(map(str, partial_ids))} are incomplete. Objective gains are policy-distribution KL, not CMI or game score.",
             ha="center", fontsize=9, color="#555555")
    fig.tight_layout(rect=[0, .03, 1, 1])
    save_figure(fig, "fig04_chronological_gcg")


def plot_replay_transfer():
    summary_path = DATA / "replay_screen/prompt_variant_summary.json"
    d = json.loads(summary_path.read_text(encoding="utf-8"))
    labels = [
        ("run0_after_block1", "GCG `ない`"),
        ("run0_after_block2", "GCG `ある`"),
        ("run0_after_block5", "GCG token 64684"),
        ("bang5", "Initial `!!!!!`"),
        ("placebo_1", "Random placebo"),
        ("counterinstruction", "Anti-channel instruction"),
    ]
    rows = []
    for variant, label in labels:
        stat = d["variant_summaries"][variant]["pair_product_tv_improvement_vs_empty_bootstrap_by_run"]
        rows.append({"variant": variant, "label": label, "runs": stat["runs"], "mean_gain": stat["mean"],
                     "ci95_low": stat["ci95"][0], "ci95_high": stat["ci95"][1], "positive_runs": stat["positive_runs"]})
    write_csv(DATA / "replay_transfer_summary.csv", rows, list(rows[0]))
    fig, ax = plt.subplots(figsize=(9.5, 5.4))
    y = np.arange(len(rows))
    means = np.array([r["mean_gain"] for r in rows])
    lo = np.array([r["ci95_low"] for r in rows])
    hi = np.array([r["ci95_high"] for r in rows])
    ax.errorbar(means, y, xerr=[means - lo, hi - means], fmt="o", capsize=3, color="#3478bf", markersize=5)
    ax.axvline(0, linestyle="--", linewidth=1, color="#555555")
    ax.set_yticks(y, [r["label"] for r in rows])
    ax.invert_yaxis()
    ax.set_xlabel("Pair-product TV improvement vs empty optional channel\n(positive = closer to no-channel reference)")
    ax.set_title("Archived-prompt replay: no suffix transfers reliably")
    ax.grid(axis="x", alpha=.2)
    ax.text(.01, -.22, "11 saved Qwen runs; 95% bootstrap resamples whole runs. Fixed-history policy proxy, not full-game action dependence.",
            transform=ax.transAxes, fontsize=9, color="#555555")
    fig.subplots_adjust(bottom=.26)
    save_figure(fig, "fig05_replay_transfer")


def main():
    for p in (DATA, FIG):
        p.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "Arial Unicode MS", "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    game = collect_game_summary()
    plot_game_summary(game)
    cmi = collect_cmi()
    plot_cmi(cmi)
    plot_initial_gcg()
    paths, recurrence, complete_ids, partial_ids = collect_chronological_gcg()
    plot_gcg_paths(paths, recurrence, complete_ids, partial_ids)
    plot_replay_transfer()
    print(f"Wrote figures and analysis tables under {OUT}")
    print(f"Chronological GCG: {len(complete_ids)} complete runs, {len(partial_ids)} partial run(s)")


if __name__ == "__main__":
    main()
