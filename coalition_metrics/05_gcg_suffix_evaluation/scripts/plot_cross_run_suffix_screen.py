#!/usr/bin/env python3
"""Create an English, paper-ready figure for the cross-run GCG suffix screen."""

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
from matplotlib.colors import TwoSlopeNorm


LABELS = {
    "run0_after_block1": "Run 0, block 1 (token 123861)",
    "run0_after_block2": "Run 0, block 2 (token 124140)",
    "run0_after_block3": "Run 0, block 3 (token 74149)",
    "run0_after_block4": "Run 0, block 4 (token 5397)",
    "run0_after_block5": "Run 0, block 5 (token 64684)",
    "run1_after_block5": "Run 1, block 5 (token 6654)",
    "run2_after_block1": "Run 2, block 1 (token 31139)",
    "run2_after_block2": "Run 2, block 2 (token 111638)",
    "run3_after_block5": "Run 3, block 5 (token 3552)",
    "placebo_1": "One-token placebo",
    "neutral": "Neutral wording",
    "counterinstruction": "Anti-channel instruction",
    "bang5": "Initial suffix !!!!!",
}
ORDER = [
    "run0_after_block1", "run0_after_block2", "run0_after_block3", "run0_after_block4",
    "run0_after_block5", "run1_after_block5", "run2_after_block1", "run2_after_block2",
    "run3_after_block5", "placebo_1", "neutral", "counterinstruction", "bang5",
]
CONTROL_COLORS = {"placebo_1": "#009E73", "neutral": "#777777",
                  "counterinstruction": "#D55E00", "bang5": "#CC79A7"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-dir", type=Path, required=True,
                        help="folder containing prompt_context_metrics.csv and prompt_variant_summary.json")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    with (args.analysis_dir / "prompt_context_metrics.csv").open(newline="") as f:
        context_rows = list(csv.DictReader(f))
    summary = json.loads((args.analysis_dir / "prompt_variant_summary.json").read_text())

    by_variant_run: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in context_rows:
        by_variant_run[row["variant"]][int(row["run"])].append(
            float(row["pair_tv_improvement_vs_empty"])
        )
    per_run = {
        variant: {run: float(np.mean(values)) for run, values in runs.items()}
        for variant, runs in by_variant_run.items()
    }
    variants = [v for v in ORDER if v in summary["variant_summaries"]]
    if not variants:
        raise SystemExit("No expected suffix variants found in the analysis summary")

    runs = sorted({run for v in variants for run in per_run.get(v, {})})
    args.out_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9,
        "axes.titlesize": 11, "axes.labelsize": 10,
        "figure.titlesize": 15, "pdf.fonttype": 42, "ps.fonttype": 42,
    })
    fig, (ax_forest, ax_heat) = plt.subplots(
        1, 2, figsize=(16, 9), gridspec_kw={"width_ratios": [2.15, 1]}
    )
    fig.suptitle("Qwen replay of GCG suffixes from independent optimization runs", y=0.98, weight="bold")
    fig.text(
        0.5, 0.947,
        "TV gain = distance(empty optional, no-channel) − distance(variant, no-channel); positive means closer to no-channel.",
        ha="center", va="center", fontsize=9,
    )

    y = np.arange(len(variants))
    for yi, variant in zip(y, variants):
        color = CONTROL_COLORS.get(variant, "#0072B2")
        run_values = per_run.get(variant, {})
        for run_id, value in sorted(run_values.items()):
            if -0.075 <= value <= 0.01:
                jitter = ((run_id * 17) % 11 - 5) * 0.018
                ax_forest.scatter(value, yi + jitter, s=19, color="#9AA0A6",
                                  edgecolor="white", linewidth=0.35, zorder=2)
        stats = summary["variant_summaries"][variant]["pair_product_tv_improvement_vs_empty_bootstrap_by_run"]
        mean = float(stats["mean"])
        low, high = map(float, stats["ci95"])
        ax_forest.errorbar(
            mean, yi, xerr=[[max(0.0, mean - low)], [max(0.0, high - mean)]],
            fmt="o", markersize=5.5, color=color, ecolor=color, elinewidth=1.7,
            capsize=3, zorder=4,
        )

    ax_forest.axvline(0, color="#222222", linestyle="--", linewidth=1)
    ax_forest.set_yticks(y, [LABELS.get(v, v) for v in variants])
    ax_forest.invert_yaxis()
    ax_forest.set_xlim(-0.075, 0.008)
    ax_forest.set_xlabel("Mean pair-product TV gain per run")
    ax_forest.set_title("Mean effect and 95% run-bootstrap interval\nIndividual run means shown in gray")
    ax_forest.grid(axis="x", color="#E5E7EB", linewidth=0.8)
    ax_forest.set_axisbelow(True)

    matrix = np.full((len(variants), len(runs)), np.nan)
    for row_i, variant in enumerate(variants):
        for col_i, run_id in enumerate(runs):
            if run_id in per_run.get(variant, {}):
                matrix[row_i, col_i] = per_run[variant][run_id]
    norm = TwoSlopeNorm(vmin=-0.05, vcenter=0.0, vmax=0.01)
    im = ax_heat.imshow(matrix, aspect="auto", interpolation="nearest", cmap="RdBu", norm=norm)
    ax_heat.set_yticks(y, [LABELS.get(v, v) for v in variants])
    ax_heat.set_xticks(np.arange(len(runs)), [str(r) for r in runs])
    ax_heat.set_xlabel("Archived run ID")
    ax_heat.set_title("Run-by-variant effects\nColor scale clipped for readability")
    for row_i in range(matrix.shape[0]):
        for col_i in range(matrix.shape[1]):
            value = matrix[row_i, col_i]
            if np.isfinite(value) and (value < -0.05 or value > 0.01):
                ax_heat.text(col_i, row_i, f"{value:.2f}", ha="center", va="center",
                             fontsize=6.5, color="white" if value < -0.05 else "black")
    cbar = fig.colorbar(im, ax=ax_heat, fraction=0.05, pad=0.03)
    cbar.set_label("TV gain per run (clipped to [−0.05, 0.01])")

    fig.text(
        0.5, 0.025,
        "11 archived Qwen runs × 4 rounds. Run 9, round 20 drives the large negative cells. Candidates use source block and Qwen token ID; decoded text is in candidates.json. p(A)×p(B) is not observed action CMI.",
        ha="center", va="center", fontsize=8,
    )
    fig.tight_layout(rect=(0.02, 0.055, 0.98, 0.925))
    png = args.out_dir / "qwen_cross_run_suffix_screen.png"
    pdf = args.out_dir / "qwen_cross_run_suffix_screen.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {png}\nWrote {pdf}")


if __name__ == "__main__":
    main()
