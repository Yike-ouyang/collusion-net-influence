#!/usr/bin/env python3
"""Extract all accepted GCG suffix paths and plot cross-run recurrence."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap


def token_key(token_ids: Any, suffix: str) -> str:
    if token_ids:
        return ",".join(str(int(x)) for x in token_ids)
    return f"text:{suffix}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", nargs="+", type=Path, required=True, help="GCG checkpoint JSON files")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    runs: dict[int, dict[str, Any]] = {}
    checkpoint_rows = []
    initial_suffixes = set()
    for path in args.inputs:
        checkpoint = json.loads(path.read_text())
        initial_suffixes.add(checkpoint.get("initial_suffix", ""))
        ids = sorted(int(x) for x in checkpoint.get("runs", {}))
        complete = [rid for rid, run in checkpoint.get("runs", {}).items() if "final_suffix" in run]
        checkpoint_rows.append({
            "file": path.name,
            "status": checkpoint.get("status"),
            "run_ids": ids,
            "complete_run_ids": sorted(map(int, complete)),
        })
        for run_id, run in checkpoint.get("runs", {}).items():
            rid = int(run_id)
            if rid in runs:
                raise ValueError(f"duplicate run ID {rid} in {path}")
            runs[rid] = {**run, "_checkpoint_status": checkpoint.get("status"), "_checkpoint_file": path.name}

    if len(initial_suffixes) > 1:
        raise ValueError(f"multiple initial suffixes across checkpoints: {initial_suffixes}")
    initial_suffix = next(iter(initial_suffixes), "")

    path_rows: list[dict[str, Any]] = []
    proposal_rows: list[dict[str, Any]] = []
    per_block_token_runs: dict[int, dict[str, set[int]]] = defaultdict(lambda: defaultdict(set))
    token_text: dict[str, str] = {}
    token_ids_by_key: dict[str, list[int] | None] = {}
    token_path_sources: dict[str, list[tuple[int, int]]] = defaultdict(list)
    token_gains: dict[str, list[float]] = defaultdict(list)
    available_runs_by_block: Counter[int] = Counter()
    proposal_count: Counter[str] = Counter()
    proposal_runs: dict[str, set[int]] = defaultdict(set)
    proposal_blocks: dict[str, set[int]] = defaultdict(set)

    for run_id, run in sorted(runs.items()):
        run_complete = "final_suffix" in run
        blocks = run.get("blocks", [])
        for block in blocks:
            block_id = int(block["block_index"])
            suffix = str(block.get("suffix_after", ""))
            token_ids = block.get("suffix_token_ids_after")
            key = token_key(token_ids, suffix)
            future = block.get("next_block_prequential") or {}
            next_gain = future.get("gain_bits_vs_empty")
            rounds = block.get("rounds_in_new_block") or [None, None]
            next_rounds = future.get("rounds") or [None, None]
            row = {
                "run": run_id,
                "run_status": "complete" if run_complete else "partial",
                "checkpoint_status": run.get("_checkpoint_status"),
                "checkpoint_file": run.get("_checkpoint_file"),
                "block": block_id,
                "trained_round_start": rounds[0],
                "trained_round_end": rounds[1],
                "suffix": suffix,
                "token_ids": json.dumps(token_ids, ensure_ascii=False),
                "token_key": key,
                "has_next_block_validation": bool(next_rounds[0] is not None),
                "next_round_start": next_rounds[0],
                "next_round_end": next_rounds[1],
                "next_block_gain_bits_vs_empty": next_gain,
            }
            path_rows.append(row)
            available_runs_by_block[block_id] += 1
            per_block_token_runs[block_id][key].add(run_id)
            token_text[key] = suffix
            token_ids_by_key[key] = token_ids
            token_path_sources[key].append((run_id, block_id))
            if next_gain is not None:
                token_gains[key].append(float(next_gain))

            accepted = block.get("accepted_candidate") or {}
            accepted_ids = accepted.get("token_ids")
            accepted_suffix = accepted.get("suffix")
            for candidate_rank, candidate in enumerate(block.get("candidates", []), start=1):
                cand_ids = candidate.get("token_ids")
                cand_suffix = str(candidate.get("suffix", ""))
                cand_key = token_key(cand_ids, cand_suffix)
                token_text[cand_key] = cand_suffix
                token_ids_by_key[cand_key] = cand_ids
                proposal_count[cand_key] += 1
                proposal_runs[cand_key].add(run_id)
                proposal_blocks[cand_key].add(block_id)
                proposal_rows.append({
                    "run": run_id,
                    "block": block_id,
                    "candidate_rank": candidate_rank,
                    "candidate_suffix": cand_suffix,
                    "token_ids": json.dumps(cand_ids, ensure_ascii=False),
                    "token_key": cand_key,
                    "changed_token_id": candidate.get("changed_token_id"),
                    "block_mean_kl_bits": candidate.get("block_mean_kl_bits"),
                    "gain_vs_empty_block_bits": candidate.get("gain_vs_empty_block_bits"),
                    "accepted_candidate": cand_suffix == accepted_suffix and cand_ids == accepted_ids,
                })

    args.out_dir.mkdir(parents=True, exist_ok=True)
    path_fields = list(path_rows[0]) if path_rows else ["run", "block"]
    with (args.out_dir / "suffix_path_by_run_block.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=path_fields)
        writer.writeheader(); writer.writerows(path_rows)
    proposal_fields = list(proposal_rows[0]) if proposal_rows else ["run", "block", "candidate_rank"]
    with (args.out_dir / "candidate_proposals.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=proposal_fields)
        writer.writeheader(); writer.writerows(proposal_rows)

    unique_rows = []
    for key, sources in sorted(token_path_sources.items(), key=lambda kv: (-len({r for r, _ in kv[1]}), kv[0])):
        distinct_runs = sorted({run_id for run_id, _ in sources})
        unique_rows.append({
            "token_key": key,
            "token_ids": json.dumps(token_ids_by_key[key], ensure_ascii=False),
            "decoded_suffix": token_text[key],
            "accepted_path_cells": len(sources),
            "distinct_runs": len(distinct_runs),
            "run_ids": ",".join(map(str, distinct_runs)),
            "run_block_sources": ";".join(f"r{r}b{b}" for r, b in sources),
            "mean_next_block_gain_bits": (sum(token_gains[key]) / len(token_gains[key]) if token_gains[key] else None),
            "validated_next_blocks": len(token_gains[key]),
        })
    with (args.out_dir / "unique_suffix_panel.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(unique_rows[0]) if unique_rows else ["token_key"])
        writer.writeheader(); writer.writerows(unique_rows)

    # Deduplicated inventory includes every proposed and accepted suffix.
    full_panel_rows = []
    for key in sorted(token_text):
        accepted_sources = token_path_sources.get(key, [])
        accepted_runs = sorted({run_id for run_id, _ in accepted_sources})
        full_panel_rows.append({
            "token_key": key,
            "token_ids": json.dumps(token_ids_by_key.get(key), ensure_ascii=False),
            "decoded_suffix": token_text.get(key, ""),
            "proposal_count": proposal_count[key],
            "proposal_runs": len(proposal_runs[key]),
            "proposed_in_blocks": ",".join(map(str, sorted(proposal_blocks[key]))),
            "accepted_path_count": len(accepted_sources),
            "accepted_runs": len(accepted_runs),
            "accepted_run_ids": ",".join(map(str, accepted_runs)),
            "accepted_run_block_sources": ";".join(f"r{r}b{b}" for r, b in accepted_sources),
        })
    full_panel_rows.sort(key=lambda row: (-row["accepted_runs"], -row["proposal_runs"], -row["proposal_count"], row["token_key"]))
    with (args.out_dir / "all_suffixes_panel.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(full_panel_rows[0]) if full_panel_rows else ["token_key"])
        writer.writeheader(); writer.writerows(full_panel_rows)

    recurrence_rows = []
    for block_id in sorted(available_runs_by_block):
        n_available = available_runs_by_block[block_id]
        for key, selected_runs in sorted(per_block_token_runs[block_id].items(), key=lambda kv: (-len(kv[1]), kv[0])):
            recurrence_rows.append({
                "block": block_id,
                "available_runs": n_available,
                "token_key": key,
                "token_ids": json.dumps(token_ids_by_key[key], ensure_ascii=False),
                "decoded_suffix": token_text[key],
                "distinct_run_count": len(selected_runs),
                "run_ids": ",".join(map(str, sorted(selected_runs))),
            })
    with (args.out_dir / "token_recurrence_by_block.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(recurrence_rows[0]) if recurrence_rows else ["block", "token_key"])
        writer.writeheader(); writer.writerows(recurrence_rows)

    checkpoint_summary = [
        f"| `{r['file']}` | `{r['status']}` | {', '.join(map(str, r['run_ids'])) or '—'} | {', '.join(map(str, r['complete_run_ids'])) or '—'} |"
        for r in checkpoint_rows
    ]
    recurring = []
    for block_id in sorted(per_block_token_runs):
        ordered = sorted(per_block_token_runs[block_id].items(), key=lambda kv: (-len(kv[1]), kv[0]))
        for key, selected_runs in ordered:
            if len(selected_runs) >= 2:
                recurrent = token_text[key].replace("|", "\\|").replace("\n", " ")
                recurring.append(
                    f"| {block_id} | `{key}` | `{recurrent}` | {len(selected_runs)}/{available_runs_by_block[block_id]} | "
                    f"{', '.join(map(str, sorted(selected_runs)))} |"
                )

    path_report = []
    for row in path_rows:
        gain = "—" if row["next_block_gain_bits_vs_empty"] is None else f"{float(row['next_block_gain_bits_vs_empty']):.3f}"
        suffix_display = row["suffix"].replace("|", "\\|").replace("\n", " ")
        path_report.append(
            f"| {row['run']} ({row['run_status']}) | {row['block']} | `{row['token_ids']}` | "
            f"`{suffix_display}` | {gain} |"
        )

    run_coverage = ", ".join(
        f"{r} ({'complete' if 'final_suffix' in run else 'partial'})" for r, run in sorted(runs.items())
    )
    top_recurrence = sorted(
        ((key, len({r for r, _ in sources}), sources) for key, sources in token_path_sources.items()),
        key=lambda x: (-x[1], x[0]),
    )
    top_recurrence_lines = []
    for key, n_runs, sources in top_recurrence:
        if n_runs < 2:
            continue
        safe_suffix = token_text[key].replace("|", "\\|").replace("\n", " ")
        source_text = "; ".join(f"r{r}b{b}" for r, b in sources)
        top_recurrence_lines.append(
            f"| `{key}` | `{safe_suffix}` | {n_runs} | {source_text} |"
        )

    block_leaders = []
    for block_id in sorted(per_block_token_runs):
        ordered = sorted(per_block_token_runs[block_id].items(), key=lambda kv: (-len(kv[1]), kv[0]))
        if not ordered:
            continue
        top_count = len(ordered[0][1])
        leaders = [key for key, selected_runs in ordered if len(selected_runs) == top_count]
        leader_text = ", ".join(f"`{key}` ({len(per_block_token_runs[block_id][key])}/{available_runs_by_block[block_id]})" for key in leaders)
        block_leaders.append(f"- Block {block_id}: {leader_text}.")

    complete_final_keys = []
    for run in runs.values():
        if "final_suffix" not in run or not run.get("blocks"):
            continue
        last_block = run["blocks"][-1]
        complete_final_keys.append(token_key(last_block.get("suffix_token_ids_after"), str(last_block.get("suffix_after", ""))))
    n_distinct_complete_finals = len(set(complete_final_keys))

    report = [
        "# GCG accepted suffixes across available Qwen runs", "",
        f"Initial suffix: `{initial_suffix}`. Runs with suffix paths: **{len(runs)}** ({run_coverage}); accepted path cells: **{len(path_rows)}**; candidate proposals recorded: **{len(proposal_rows)}**; unique suffixes in the complete panel: **{len(full_panel_rows)}**.",
        "", "## Checkpoint coverage", "", "| Checkpoint | Status | Run IDs present | Complete run IDs |", "|---|---|---|---|",
        *checkpoint_summary,
        "", "## Recurring accepted suffixes across runs", "",
        "A run can contribute to several block cells when it re-selects a token; this is descriptive recurrence, not an independent-run test.",
        "", "| Qwen token ID(s) | Decoded suffix | Distinct runs | Accepted run/block cells |", "|---|---|---:|---|",
        *(top_recurrence_lines or ["| — | No suffix selected in multiple runs yet | — | — |"]),
        "", "## Recurring token IDs by block", "",
        "Most frequent accepted token ID(s) at each update stage:", "", *block_leaders,
        "",
        "Counts are distinct runs selecting the token after that block. Repeated blocks within one run count once per block, not as independent runs.",
        "", "| Block | Qwen token ID | Decoded suffix | Runs / available | Run IDs |", "|---:|---|---|---:|---|",
        *(recurring or ["| — | No token selected in multiple runs within a block yet | — | — | — |"]),
        "", "## Full accepted suffix path", "", "Block 6 is shown as an accepted final suffix but has no next-block prospective evaluation.",
        "", "| Run | Block | Qwen token ID(s) | Decoded suffix | Next-block gain (bits) |", "|---|---:|---|---|---:|",
        *path_report,
        "", "## Pattern reading", "",
        f"Among complete trajectories, **{n_distinct_complete_finals} distinct terminal suffix token IDs** appear across **{len(complete_final_keys)} runs**. The strongest repeated choices are stage-specific; recurrence at different blocks within the same run does not mean the optimizer converged to the same final suffix.",
        "The decoded strings include fragments from multiple writing systems and code-like text. Treat the pattern as token-level optimizer recurrence that may reflect the model tokenizer or context, not as a shared natural-language anti-collusion instruction.",
        "", "## Interpretation", "",
        "A repeated token within the same chronological block is a descriptive recurrence pattern, not evidence of a universal suffix or a statistical significance test. Next-block gains measure the GCG KL objective against the empty suffix, not empirical action CMI or game performance.",
        "The block-5 suffix is the prospective candidate for rounds 51–60. Block-6 suffixes are in-sample final updates and must not be reported as prospectively validated.",
        "Exact text, token IDs, full accepted paths, every candidate proposed by GCG, and a deduplicated panel of all proposed/accepted suffixes are preserved in the CSV files beside this report.",
    ]
    (args.out_dir / "REPORT.md").write_text("\n".join(report) + "\n")

    # English figure: accepted path (left), distinct-run recurrence by block (right).
    run_ids = sorted(runs)
    blocks = sorted({int(row["block"]) for row in path_rows})
    token_keys = sorted(token_path_sources, key=lambda k: (-sum(len(per_block_token_runs[b].get(k, set())) for b in blocks), k))
    token_index = {key: i for i, key in enumerate(token_keys)}
    token_cmap = plt.get_cmap("tab20", max(1, len(token_keys)))
    path_matrix = np.full((len(run_ids), len(blocks)), np.nan)
    lookup = {(row["run"], int(row["block"])): row for row in path_rows}
    for ri, run_id in enumerate(run_ids):
        for bi, block_id in enumerate(blocks):
            row = lookup.get((run_id, block_id))
            if row:
                path_matrix[ri, bi] = token_index[row["token_key"]]

    count_matrix = np.zeros((len(token_keys), len(blocks)), dtype=float)
    for ti, key in enumerate(token_keys):
        for bi, block_id in enumerate(blocks):
            count_matrix[ti, bi] = len(per_block_token_runs[block_id].get(key, set()))

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "axes.titlesize": 11, "figure.titlesize": 15,
                         "pdf.fonttype": 42, "ps.fonttype": 42})
    fig, (ax_path, ax_recur) = plt.subplots(
        1, 2, figsize=(15, max(6.5, 0.40 * max(len(run_ids), len(token_keys)) + 3)),
        gridspec_kw={"width_ratios": [1.05, 1.35]},
    )
    fig.suptitle("GCG suffix paths and cross-run recurrence", y=0.995, weight="bold")
    fig.text(0.5, 0.94,
             "Cell text is the Qwen token ID; decoded suffix strings are listed in the companion CSV panel.",
             ha="center", va="center", fontsize=9)

    path_cmap = ListedColormap([token_cmap(i) for i in range(len(token_keys))])
    path_norm = BoundaryNorm(np.arange(-0.5, len(token_keys) + 0.5, 1), path_cmap.N)
    ax_path.imshow(path_matrix, aspect="auto", interpolation="nearest", cmap=path_cmap, norm=path_norm)
    ax_path.set_xticks(np.arange(len(blocks)), [f"Block {b}" for b in blocks])
    ax_path.set_yticks(np.arange(len(run_ids)), [f"Run {r}" + (" *" if not ("final_suffix" in runs[r]) else "") for r in run_ids])
    ax_path.set_title("Accepted suffix path by optimization run")
    ax_path.set_xlabel("Chronological update block (10 rounds each)")
    ax_path.set_ylabel("GCG run (* partial checkpoint)")
    ax_path.set_xticks(np.arange(-0.5, len(blocks), 1), minor=True)
    ax_path.set_yticks(np.arange(-0.5, len(run_ids), 1), minor=True)
    ax_path.grid(which="minor", color="white", linewidth=2)
    ax_path.tick_params(which="minor", bottom=False, left=False)
    for ri, run_id in enumerate(run_ids):
        for bi, block_id in enumerate(blocks):
            row = lookup.get((run_id, block_id))
            if row:
                ids = json.loads(row["token_ids"])
                label = ",".join(str(int(x)) for x in ids) if ids else "text"
                ax_path.text(bi, ri, label, ha="center", va="center", fontsize=7,
                             color="white" if token_index[row["token_key"]] in (0, 1, 4, 5, 8, 9, 12) else "black")
            else:
                ax_path.text(bi, ri, "—", ha="center", va="center", fontsize=9, color="#9CA3AF")

    im = ax_recur.imshow(count_matrix, aspect="auto", interpolation="nearest", cmap="Blues",
                         vmin=0, vmax=max(3, max((int(x) for x in count_matrix.flat), default=1)))
    ax_recur.set_xticks(np.arange(len(blocks)), [f"Block {b}\n(n={available_runs_by_block[b]})" for b in blocks])
    ax_recur.set_yticks(np.arange(len(token_keys)), [f"Token {json.loads(json.dumps(token_ids_by_key[k]))}" if token_ids_by_key[k] else k for k in token_keys])
    ax_recur.set_title("Number of distinct runs selecting each token")
    ax_recur.set_xlabel("Block (n = runs with a recorded block)")
    ax_recur.set_ylabel("Qwen token ID")
    ax_recur.set_xticks(np.arange(-0.5, len(blocks), 1), minor=True)
    ax_recur.set_yticks(np.arange(-0.5, len(token_keys), 1), minor=True)
    ax_recur.grid(which="minor", color="white", linewidth=1.5)
    ax_recur.tick_params(which="minor", bottom=False, left=False)
    for ti in range(len(token_keys)):
        for bi, block_id in enumerate(blocks):
            count = int(count_matrix[ti, bi])
            if count:
                ax_recur.text(bi, ti, str(count), ha="center", va="center", fontsize=8,
                              color="white" if count >= 2 else "#1F2937", weight="bold" if count >= 2 else "normal")
    cbar = fig.colorbar(im, ax=ax_recur, fraction=0.046, pad=0.03)
    cbar.set_label("Distinct optimization runs")
    fig.text(0.5, 0.025,
             "Block 6 has no future block for prospective validation. Asterisks mark incomplete checkpoint runs. Recurrence is descriptive, not a significance test.",
             ha="center", va="center", fontsize=8)
    fig.tight_layout(rect=(0.02, 0.055, 0.98, 0.91))
    png = args.out_dir / "all_gcg_suffix_paths_and_recurrence.png"
    pdf = args.out_dir / "all_gcg_suffix_paths_and_recurrence.pdf"
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Wrote {args.out_dir / 'REPORT.md'}")
    print(f"Wrote {png}")
    print(f"Wrote {pdf}")


if __name__ == "__main__":
    main()
