#!/usr/bin/env python3
"""Sample and freeze printable one-token placebo strings from a model tokenizer."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import unicodedata
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default="Qwen/Qwen2.5-32B-Instruct")
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--token-count", type=int, default=1)
    p.add_argument("--seed", type=int, default=20261026)
    p.add_argument("--exclude", action="append", default=[], help="exact suffix text to exclude; repeatable")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.token_count != 1:
        p.error("this pilot helper currently supports one-token controls only")
    try:
        from transformers import AutoTokenizer
    except ImportError as e:
        raise SystemExit("Install/use the project's transformers environment to load the tokenizer only.") from e

    tokenizer = AutoTokenizer.from_pretrained(args.model, use_fast=True)
    excluded = set(args.exclude)
    special = set(tokenizer.all_special_ids)
    eligible = []
    for token_id in range(len(tokenizer)):
        if token_id in special:
            continue
        text = tokenizer.decode([token_id], skip_special_tokens=False,
                                clean_up_tokenization_spaces=False)
        if not text or text in excluded or "\ufffd" in text or "\n" in text or "\r" in text:
            continue
        if any(unicodedata.category(ch).startswith("C") for ch in text):
            continue
        if tokenizer.encode(text, add_special_tokens=False) != [token_id]:
            continue
        eligible.append((token_id, text))
    if len(eligible) < args.count:
        raise SystemExit(f"only {len(eligible)} eligible tokens; cannot sample {args.count}")
    rng = random.Random(args.seed)
    selected = rng.sample(eligible, args.count)
    placebo_rows = [{
        "label": f"placebo_{i+1}", "suffix": text, "token_ids": [token_id],
        "token_piece": tokenizer.convert_ids_to_tokens(token_id),
        "utf8_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    } for i, (token_id, text) in enumerate(selected)]
    result = {"model_tokenizer": args.model, "seed": args.seed, "token_count": args.token_count,
              "sampling": "uniform sample without replacement from printable, round-trip-stable, non-special tokens",
              "placebos": placebo_rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {args.out}; freeze these placebo strings before inspecting outcome metrics.")


if __name__ == "__main__":
    main()
