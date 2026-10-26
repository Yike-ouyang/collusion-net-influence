#!/usr/bin/env python3
"""Plot the completed archived-prompt Qwen suffix screen."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


LABELS = {
    "run0_after_block5": "GCG suffix (run 0, block 5)",
    "placebo_1": "One-token placebo",
    "neutral": "Neutral wording",
    "counterinstruction": "Anti-channel instruction",
    "bang5": "Initial suffix !!!!!",
}
COLORS = {
    "run0_after_block5": "#0072B2",
    "placebo_1": "#009E73",
    "neutral": "#777777",
    "counterinstruction": "#D55E00",
    "bang5": "#CC79A7",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, required=True,
                        help="folder containing prompt_context_metrics.csv and prompt_variant_summary.json")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    csv_path = args.analysis_dir / "prompt_context_metrics.csv"
    summary_path = args.analysis_dir / "prompt_variant_summary.json"
    rows = list(csv.DictReader(csv_path.open(newline="")))
    summary = json.loads(summary_path.read_text())

    per_run: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        per_run[row["variant"]][int(row["run"])].append(float(row["pair_tv_improvement_vs_empty"]))
    run_means = {
        variant: {run: float(np.mean(values)) for run, values in by_run.items()}
        for variant, by_run in per_run.items()
    }

    order = ["run0_after_block5", "placebo_1", "neutral", "counterinstruction", "bang5"]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "figure.titlesize": 15,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    fig, (ax_all, ax_zoom) = plt.subplots(
        1, 2, figsize=(13.2, 6.4), gridspec_kw={"width_ratios": [1.2, 1]}
    )
    fig.suptitle("Qwen replay: suffix effects on archived move policies", y=0.98, weight="bold")
    fig.text(
        0.5, 0.925,
        "TV gain = distance(empty optional, no-channel) − distance(variant, no-channel); positive means closer to no-channel.",
        ha="center", va="center", fontsize=9,
    )

    # Panel A: all variants, the full range preserves the influential run 9.
    y_positions = np.arange(len(order))
    for y, variant in zip(y_positions, order):
        color = COLORS[variant]
        values = run_means.get(variant, {})
        ids = sorted(values)
        for j, run_id in enumerate(ids):
            jitter = (j - (len(ids) - 1) / 2) * 0.018
            ax_all.scatter(
                values[run_id], y + jitter, s=22,
                color="#D55E00" if run_id == 9 else "#9AA0A6",
                edgecolor="white", linewidth=0.35, zorder=2,
                label="Run 9" if run_id == 9 and y == 0 else None,
            )
        stats = summary["variant_summaries"][variant]["pair_product_tv_improvement_vs_empty_bootstrap_by_run"]
        mean = float(stats["mean"])
        low, high = map(float, stats["ci95"])
        ax_all.errorbar(
            mean, y, xerr=[[max(0.0, mean - low)], [max(0.0, high - mean)]],
            fmt="o", markersize=6, color=color, ecolor=color, elinewidth=2,
            capsize=3, zorder=4,
        )
    ax_all.axvline(0, color="#222222", linewidth=1, linestyle="--", zorder=1)
    ax_all.set_yticks(y_positions, [LABELS[x] for x in order])
    ax_all.invert_yaxis()
    ax_all.set_xlim(-0.28, 0.008)
    ax_all.set_xlabel("Mean TV gain per run")
    ax_all.set_title(
        "All variants · full scale\n"
        "Gray: run means · color: mean and 95% CI · orange: run 9",
        fontsize=9,
    )
    ax_all.grid(axis="x", color="#E5E7EB", linewidth=0.8)
    ax_all.set_axisbelow(True)

    # Panel B: zoom on the learned suffix and placebo; individual run means are paired.
    zoom_variants = ["run0_after_block5", "placebo_1"]
    x_positions = np.arange(len(zoom_variants))
    for x, variant in zip(x_positions, zoom_variants):
        values = run_means.get(variant, {})
        for run_id, value in sorted(values.items()):
            jitter = ((run_id * 17) % 11 - 5) * 0.018
            ax_zoom.scatter(
                x + jitter, value, s=30,
                color="#D55E00" if run_id == 5 else COLORS[variant],
                alpha=0.85, edgecolor="white", linewidth=0.4, zorder=3,
            )
            if variant == "run0_after_block5" and run_id == 5:
                ax_zoom.annotate("run 5", (x + jitter, value), xytext=(7, 5),
                                 textcoords="offset points", fontsize=8)
        stats = summary["variant_summaries"][variant]["pair_product_tv_improvement_vs_empty_bootstrap_by_run"]
        mean = float(stats["mean"])
        low, high = map(float, stats["ci95"])
        ax_zoom.errorbar(
            x, mean, yerr=[[max(0.0, mean - low)], [max(0.0, high - mean)]],
            fmt="D", markersize=6, color="#111827", ecolor="#111827",
            elinewidth=1.5, capsize=4, zorder=4,
        )
    ax_zoom.axhline(0, color="#222222", linewidth=1, linestyle="--")
    ax_zoom.set_xticks(x_positions, [LABELS[x] for x in zoom_variants], rotation=8, ha="right")
    ax_zoom.set_ylim(-0.00012, 0.0032)
    ax_zoom.set_ylabel("Mean TV gain per run")
    ax_zoom.set_title("Zoom: GCG suffix and placebo")
    ax_zoom.grid(axis="y", color="#E5E7EB", linewidth=0.8)
    ax_zoom.set_axisbelow(True)
    ax_zoom.text(
        0.02, 0.98,
        "Diamonds: mean and 95% run-bootstrap CI\nDots: per-run means",
        transform=ax_zoom.transAxes, ha="left", va="top", fontsize=8,
        bbox={"boxstyle": "round,pad=0.35", "facecolor": "white", "edgecolor": "#D1D5DB"},
    )

    fig.text(
        0.5, 0.035,
        "Replay of 11 archived Qwen runs, up to 4 rounds per run. p(A)×p(B) is a policy proxy, not observed CMI.",
        ha="center", va="center", fontsize=8,
    )
    fig.tight_layout(rect=(0.02, 0.08, 0.98, 0.90))
    png = args.out_dir / "qwen_replay_tv_gain.png"
    pdf = args.out_dir / "qwen_replay_tv_gain.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {png}\nWrote {pdf}")


if __name__ == "__main__":
    main()
