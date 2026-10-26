# Preliminary reading of the live chronological checkpoint

This is an exploratory snapshot of `qwen32b_chronological_bang5_runs_0_4.json`, taken while the five-run Modal batch was still running. At that snapshot, run 0 had completed and run 1 had completed only block 1. This is not a final analysis.

## Run 0 suffix path

| Update block | Suffix after update | Trained rounds | Next-block rounds | Next-block gain vs empty (bits) |
|---:|---|---|---|---:|
| 1 | `ない` | 1–10 | 11–20 | +3.9733 |
| 2 | `ある` | 11–20 | 21–30 | +4.9878 |
| 3 | ` quoi` | 21–30 | 31–40 | −0.6883 |
| 4 | `és` | 31–40 | 41–50 | −0.7607 |
| 5 | `ื่` | 41–50 | 51–60 | +5.0540 |
| 6 | `ื่` | 51–60 | — | no future block |

The frozen candidate for the first transfer check is `ื่`, selected on rounds 41–50 and measured on rounds 51–60. Its Qwen tokenizer ID is `64684`. The suffix path changes considerably across blocks; that points to context sensitivity, not yet to a stable phrase. At the checkpoint snapshot, run 1 independently selected `ない` after its first block, matching run 0's first-block result. Two runs are far too few to claim recurrence.

## What the gains mean

`next-block gain` is the change in the model's distribution-matching loss on the next block relative to an empty suffix. Positive means the two separately queried optional-channel move distributions are closer to their no-channel references under the pilot loss. It is a prequential, saved-context diagnostic.

It does **not** mean that empirical action CMI, the pair's game score, or the outsider's score fell. The old histories stay fixed, the pair distribution is formed as `p_A × p_B`, and no suffix-controlled complete game has been played in this checkpoint.

## Immediate follow-up

Use the exporter to preserve all suffix strings, token IDs, training gains, and next-block scores. For the first screen, compare all run-0 block suffixes plus `!!!!!`, empty suffix, the explicit counterinstruction, and pre-registered placebo strings on held-out runs. Freeze any candidate before launching fresh complete-game arms.
