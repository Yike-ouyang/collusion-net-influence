#!/usr/bin/env python3
"""Export exact suffix candidates and prequential scores from a chronological GCG checkpoint."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--run", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    record = json.loads(args.input.read_text())
    run = record.get("runs", {}).get(str(args.run))
    if run is None:
        raise SystemExit(f"run {args.run} is not yet present in {args.input}")
    rows: list[dict[str, Any]] = []
    candidates = []
    for block in run.get("blocks", []):
        future = block.get("next_block_prequential")
        item = {
            "model": record.get("model"), "run": args.run,
            "block": int(block["block_index"]),
            "trained_rounds": block.get("rounds_in_new_block"),
            "evaluated_rounds": future.get("rounds") if future else None,
            "suffix_before": block.get("suffix_before"),
            "suffix_after": block.get("suffix_after"),
            "token_ids_after": block.get("suffix_token_ids_after"),
            "training_gain_vs_empty_bits": block.get("block_gain_vs_empty_bits_after"),
            "next_block_gain_vs_empty_bits": future.get("gain_bits_vs_empty") if future else None,
            "next_block_empty_kl_nats": future.get("empty_suffix_mean_kl_nats") if future else None,
            "next_block_suffix_kl_nats": future.get("updated_suffix_mean_kl_nats") if future else None,
        }
        rows.append(item)
        candidates.append({
            "label": f"run{args.run}_after_block{item['block']}",
            "suffix": item["suffix_after"],
            "token_ids_qwen": item["token_ids_after"],
            "trained_rounds": item["trained_rounds"],
            "prospective_rounds": item["evaluated_rounds"],
            "next_block_gain_vs_empty_bits": item["next_block_gain_vs_empty_bits"],
            "selection_status": "exploratory_per_run_candidate",
        })

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "candidates.json").write_text(json.dumps({
        "source_checkpoint": str(args.input), "checkpoint_status": record.get("status"),
        "model": record.get("model"), "initial_suffix": record.get("initial_suffix"),
        "run": args.run, "candidates": candidates,
        "note": "Candidate strings and token IDs are exact. A suffix after block 5 is tested prospectively on block 6; the block-6 suffix has no future block in this run.",
    }, indent=2, ensure_ascii=False))
    with (args.out / "candidate_path.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["run", "block"])
        writer.writeheader()
        writer.writerows(rows)
    report = ["# Chronological GCG candidate path", "",
              f"Checkpoint status: **{record.get('status')}**. Run: {args.run}.", "",
              "| Block | Training rounds | Suffix after update | Qwen token IDs | Training gain vs empty (bits) | Next rounds | Next-block gain (bits) |",
              "|---:|---|---|---|---:|---|---:|"]
    for r in rows:
        fr = r["evaluated_rounds"]
        report.append(f"| {r['block']} | {r['trained_rounds']} | `{r['suffix_after']}` | `{r['token_ids_after']}` | "
                      f"{r['training_gain_vs_empty_bits']} | {fr if fr else '—'} | {r['next_block_gain_vs_empty_bits'] if fr else '—'} |")
    report += ["", "Training gain is measured on the block used to choose a candidate. The next-block gain is the more informative chronological transfer diagnostic, but these are still replayed archived prompts, not new games."]
    (args.out / "REPORT.md").write_text("\n".join(report) + "\n")
    print(f"Wrote {args.out / 'REPORT.md'} and {args.out / 'candidates.json'}")


if __name__ == "__main__":
    main()
