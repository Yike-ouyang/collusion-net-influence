#!/usr/bin/env python3
"""Build a deduplicated manifest of accepted chronological GCG suffixes."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="chronological GCG checkpoint JSON")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-block", type=int, default=5,
                        help="exclude later blocks without a prospective next-block evaluation")
    args = parser.parse_args()

    checkpoint = json.loads(args.input.read_text())
    complete_runs = {
        int(run_id): run for run_id, run in checkpoint.get("runs", {}).items()
        if "final_suffix" in run
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run_id, run in sorted(complete_runs.items()):
        for block in run.get("blocks", []):
            block_id = int(block["block_index"])
            if block_id > args.max_block:
                continue
            suffix = block.get("suffix_after")
            if not isinstance(suffix, str):
                continue
            future = block.get("next_block_prequential") or {}
            grouped[suffix].append({
                "run": run_id,
                "block": block_id,
                "trained_rounds": block.get("rounds_in_new_block"),
                "prospective_rounds": future.get("rounds"),
                "token_ids_qwen": block.get("suffix_token_ids_after"),
                "next_block_gain_vs_empty_bits": future.get("gain_bits_vs_empty"),
            })

    args.out.mkdir(parents=True, exist_ok=True)
    candidates = []
    source_rows = []
    for index, (suffix, sources) in enumerate(grouped.items(), start=1):
        first = sources[0]
        label = f"run{first['run']}_after_block{first['block']}"
        candidates.append({
            "label": label,
            "suffix": suffix,
            "token_ids_qwen": first["token_ids_qwen"],
            "sources": sources,
            "distinct_source_runs": sorted({source["run"] for source in sources}),
            "selection_status": "exploratory_unique_accepted_suffix",
        })
        for source in sources:
            source_rows.append({"suffix_label": label, "suffix": suffix, **source})

    manifest = {
        "source_checkpoint": str(args.input),
        "checkpoint_status": checkpoint.get("status"),
        "model": checkpoint.get("model"),
        "available_complete_runs": sorted(complete_runs),
        "max_block_included": args.max_block,
        "selection_rule": "Deduplicate exact accepted suffix text across complete runs; include blocks 1 through max_block only. Block 6 is excluded because it has no future block for prospective evaluation.",
        "candidates": candidates,
    }
    (args.out / "candidates.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    with (args.out / "suffix_recurrence.csv").open("w", newline="") as f:
        fields = ["suffix_label", "suffix", "run", "block", "trained_rounds", "prospective_rounds",
                  "token_ids_qwen", "next_block_gain_vs_empty_bits"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(source_rows)

    lines = [
        "# Candidate suffixes from completed chronological GCG runs", "",
        f"Checkpoint status: **{checkpoint.get('status')}**. Complete runs available: `{sorted(complete_runs)}`.",
        f"Unique accepted suffixes included: **{len(candidates)}** (blocks 1–{args.max_block}).", "",
        "Suffixes are deduplicated by exact decoded text. Source rows and next-block gains are in `suffix_recurrence.csv`.",
        "The screening is exploratory; the checkpoint may still be incomplete.", "",
        "| Label | Exact suffix | Source runs | Source blocks | Next-block gains (bits) |",
        "|---|---|---|---|---|",
    ]
    for item in candidates:
        runs = ", ".join(map(str, item["distinct_source_runs"]))
        blocks = ", ".join(f"r{s['run']}b{s['block']}" for s in item["sources"])
        gains = ", ".join(
            "—" if s["next_block_gain_vs_empty_bits"] is None else f"{s['next_block_gain_vs_empty_bits']:.3f}"
            for s in item["sources"]
        )
        lines.append(f"| `{item['label']}` | `{item['suffix']}` | {runs} | {blocks} | {gains} |")
    (args.out / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(f"Wrote {args.out / 'candidates.json'} with {len(candidates)} unique suffixes from runs {sorted(complete_runs)}")


if __name__ == "__main__":
    main()
