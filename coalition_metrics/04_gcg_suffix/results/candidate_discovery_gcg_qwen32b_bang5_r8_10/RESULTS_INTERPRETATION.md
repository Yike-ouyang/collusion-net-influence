# Interpretation of the first multi-context GCG run

## Result

- Model: Qwen2.5-32B-Instruct, pinned revision `5ede1c97bbab6ce5cda5812749b4c0bdf79b18dd`, 8-bit frozen weights on one H100 80 GB.
- Split: 5 training games (runs 0–4, rounds 8–10; 15 contexts) and 4 validation games (runs 12–15, rounds 8–10; 12 contexts).
- Start suffix: `!!!!!`, one tokenizer token `[69800]`.
- Selected suffix: `网` (one token, ID `[31139]`). This is the literal optimizer output. Although it means “net/network” in Chinese, do not assume the optimizer found that semantic meaning useful; it may be an arbitrary adversarial token.
- Search stopped after three coordinate steps: the best validation suffix appeared on step 1, and the next two steps did not improve it.
- Elapsed time: 18 min 06 s including model load; peak allocated memory: 64.9 GiB.

## KL result

The objective is the average of per-context forward KLs, with a 0.25 weighted individual-policy KL term. The reported “gain” is the reduction in that objective relative to the optional-channel prompt with no suffix, expressed in bits per context. It is **not mutual information gained**.

| Split | Empty suffix KL | `!!!!!` KL | `网` KL | `网` gain vs empty |
|---|---:|---:|---:|---:|
| Training | 34.726 nats | 35.078 nats | 31.658 nats | 4.426 bits (8.83%) |
| Validation | 41.407 nats | 42.343 nats | 39.620 nats | 2.579 bits (4.32%) |

The initial `!!!!!` suffix made the loss slightly worse than the empty suffix on both splits. The learned token then improved on the empty baseline. On validation, the per-game gains were `-0.687`, `+3.894`, `+1.295`, and `+2.648` nats for runs 12–15: three of four runs improved. The run-cluster bootstrap interval was `[0.147, 3.271]` nats (about `[0.212, 4.719]` bits), based on only four games, so treat it as preliminary.

Validation KL improved on all three rounds: about `1.170` bits at round 8, `5.256` bits at round 9, and `1.311` bits at round 10. The larger round-9 effect deserves a separate check on new games.

The average individual KL also decreased for both players: A from `20.022` to `19.434` nats and B from `13.104` to `12.262` nats. This supports the claim that the pair-law loss did not improve solely by changing one player's aggregate distribution; it still does not prove coalition behavior changed.

## What this does and does not show

This is a promising first result for **matching action distributions**: the one-token suffix reduced the objective on held-out contexts. The pooled soft MI diagnostic was effectively unchanged (`0.904573` to `0.904572` bits). That is expected to be possible: the optimized KL matches each player's and the pair's move law to the no-channel reference; it does not directly minimize mutual information or measure within-context coordination.

The policies were sampled from saved run/round prompts. No complete game was replayed with `网`, the optional and no-channel trajectories do not have identical visible histories, and the validation games were used to select the suffix. So this is not yet evidence of improved game score or reduced `I(A;B|S)`. Use fresh complete games for that claim.

## Suggested next experiment

Before expanding GCG, run a small full-game comparison with the exact selected suffix `网`, suffix empty, and the no-channel reference. Use fresh seed/run IDs not used in optimization or validation, keep the same Qwen revision and game settings, and compare complete-game score advantage, action `I(A;B|S)`, and messages/plans separately. If the suffix's game-level effect is absent, do not spend more search budget on this loss without changing the objective or context matching.

## Audit files

- `qwen32b_gcg_bang5_r8_10_runs0_4_val12_15.json`: all baselines, candidate strings, per-context move probabilities and losses, gradients, and stopping record.
- `qwen32b_gcg_bang5_r8_10_runs0_4_val12_15.md`: Modal-generated step-by-step report.
