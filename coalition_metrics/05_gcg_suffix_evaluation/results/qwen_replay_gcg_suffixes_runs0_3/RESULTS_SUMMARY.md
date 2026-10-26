# Cross-run Qwen suffix replay: preliminary findings

## Design

- GCG checkpoint: completed optimization runs 0–4; nine unique accepted suffixes from blocks 1–5 after deduplicating exact text.
- Archived replay: Qwen runs 5–11 and 16–19, rounds 5, 20, 40, and 55; 1,320 responses, all successful.
- Variants: empty optional channel, the nine GCG suffixes, `!!!!!`, a one-token placebo, neutral wording, and an explicit anti-channel instruction; no-channel prompts provide the reference.
- The checkpoint's block-6 suffixes were excluded because they have no future block for prospective evaluation.

## Main observation

No suffix showed a stable positive transfer toward the no-channel reference on these archived prompts.

- The run-0 block-5 candidate (Qwen token 64684) had mean pair-product TV gain **0.00025**, with a 95% run-bootstrap interval of approximately **[0.00000, 0.00075]**; only 1 of 11 run means was positive. This is close to zero and similar to the placebo.
- The other GCG suffixes had negative mean TV gains, generally around **−0.0226**, with intervals crossing zero. These means are driven by a large context-level change in run 9 at round 20; inspect that context before drawing conclusions.
- The mean top-5 legal-move mass was approximately 1.0, so the recognized legal moves were fully covered in the returned top-logprob mass.

Positive TV gain means the variant's product of separate A and B move distributions is closer to the no-channel reference than the empty optional-channel distributions. This product is a policy proxy, not observed joint behaviour or `I(A;B|S)`.

## Interpretation

This screening does not identify a suffix that reliably transfers across saved Qwen contexts. It is a fixed-history replay, not a closed-loop game intervention, and it cannot establish a change in action dependence, scores, or collusion. A fresh-game pilot is warranted only as an exploratory test of whether closed-loop dynamics differ from this replay result.

## Reproducible outputs

- `analysis/REPORT.md`: numerical table and limitations.
- `analysis/prompt_context_metrics.csv`: per-variant, per-run, per-round measurements.
- `figures/qwen_cross_run_suffix_screen.png` and `.pdf`: English paper figure.
- `run.log`, `intermediate_results.json`, and `traces/`: execution log, complete responses, and request traces.
