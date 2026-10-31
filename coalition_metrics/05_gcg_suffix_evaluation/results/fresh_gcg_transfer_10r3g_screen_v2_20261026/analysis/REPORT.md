# Fresh-game GCG suffix study

Campaign prefix: `fresh_gcg_transfer_10r3g_screen_v2_20261026`. Complete games found: **36**.

## Per-model and per-arm results

| Model | Arm | Games | I(A;B given shared die), bits | Pair advantage, points/round | Final scores A/B/C | CS_AB conditional shuffle | Channel use A/B |
|---|---|---:|---|---|---|---|---|
| Qwen 2.5 32B | No channel | 3 | 0.5333 [0.2000, 0.8000] | 0.4250 [-0.2250, 0.9000] | 10.0000 [6.0000, 12.0000] / 5.5000 [4.5000, 6.0000] / 3.5000 [0.0000, 7.5000] | -0.0750 [-0.2250, 0.0000] | — / — |
| Qwen 2.5 32B | Optional / empty | 3 | 0.6667 [0.5245, 0.8000] | 0.0250 [-0.1500, 0.2250] | 3.5000 [3.0000, 4.5000] / 8.0000 [6.0000, 9.0000] / 5.5000 [4.5000, 6.0000] | -0.2000 [-0.3375, -0.0937] | 0.6088 [0.5263, 0.6500] / 0.6421 [0.5263, 0.7500] |
| Qwen 2.5 32B | GCG block 1: ない | 3 | 0.3748 [0.1245, 0.8000] | -0.4000 [-0.6000, 0.0000] | 5.5000 [3.0000, 10.5000] / 4.5000 [3.0000, 7.5000] / 9.0000 [9.0000, 9.0000] | -0.1771 [-0.2625, -0.0625] | 0.6667 [0.6000, 0.7500] / 0.6500 [0.5500, 0.7000] |
| Qwen 2.5 32B | GCG block 2: ある | 3 | 0.5082 [0.4000, 0.6000] | -0.8500 [-1.2000, -0.6000] | 3.5000 [1.5000, 6.0000] / 3.5000 [3.0000, 4.5000] / 12.0000 [9.0000, 15.0000] | -0.2604 [-0.5250, 0.0438] | 0.6956 [0.6500, 0.7368] / 0.6956 [0.6500, 0.7368] |
| GLM-4 32B | No channel | 3 | 0.4415 [0.3245, 0.6000] | -0.0750 [-0.6750, 0.3000] | 8.5000 [4.5000, 13.5000] / 3.0000 [0.0000, 4.5000] / 6.5000 [3.0000, 10.5000] | -0.0688 [-0.2625, 0.1125] | — / — |
| GLM-4 32B | Optional / empty | 3 | 0.4415 [0.3245, 0.6000] | -0.3250 [-0.5250, 0.0750] | 7.0000 [3.0000, 9.0000] / 3.5000 [1.5000, 7.5000] / 8.5000 [4.5000, 10.5000] | 0.1812 [-0.0563, 0.4125] | 0.9667 [0.9500, 1.0000] / 1.0000 [1.0000, 1.0000] |
| GLM-4 32B | GCG block 1: ない | 3 | 0.3082 [0.0000, 0.8755] | -0.2500 [-0.7500, 0.0750] | 6.5000 [4.5000, 9.0000] / 6.5000 [4.5000, 7.5000] / 9.0000 [7.5000, 12.0000] | -0.0750 [-0.1500, 0.0000] | 1.0000 [1.0000, 1.0000] / 0.9833 [0.9500, 1.0000] |
| GLM-4 32B | GCG block 2: ある | 3 | 0.3748 [0.1245, 0.6755] | -0.4250 [-1.1250, 0.0000] | 4.0000 [1.5000, 6.0000] / 6.5000 [4.5000, 9.0000] / 9.5000 [6.0000, 16.5000] | -0.0812 [-0.3750, 0.1125] | 0.9667 [0.9000, 1.0000] / 0.9667 [0.9000, 1.0000] |
| Mixtral 8x7B | No channel | 3 | 0.5748 [0.3245, 0.8755] | 0.2750 [0.1500, 0.4500] | 7.5000 [6.0000, 9.0000] / 5.0000 [0.0000, 7.5000] / 3.5000 [3.0000, 4.5000] | 0.1042 [-0.0562, 0.2250] | — / — |
| Mixtral 8x7B | Optional / empty | 3 | 0.1748 [0.0000, 0.3245] | -0.1750 [-0.4500, 0.0000] | 9.0000 [9.0000, 9.0000] / 6.5000 [4.5000, 9.0000] / 9.5000 [7.5000, 12.0000] | 0.0062 [0.0000, 0.0187] | 1.0000 [1.0000, 1.0000] / 1.0000 [1.0000, 1.0000] |
| Mixtral 8x7B | GCG block 1: ない | 3 | 0.0415 [0.0000, 0.1245] | 0.1500 [0.0750, 0.2250] | 5.5000 [4.5000, 7.5000] / 7.5000 [6.0000, 9.0000] / 5.0000 [4.5000, 6.0000] | 0.0625 [-0.0562, 0.1875] | 1.0000 [1.0000, 1.0000] / 1.0000 [1.0000, 1.0000] |
| Mixtral 8x7B | GCG block 2: ある | 3 | 0.3082 [0.0000, 0.8000] | -0.1250 [-0.3750, 0.1500] | 7.5000 [7.5000, 7.5000] / 7.0000 [6.0000, 7.5000] / 8.5000 [6.0000, 10.5000] | -0.0688 [-0.3375, 0.1313] | 1.0000 [1.0000, 1.0000] / 1.0000 [1.0000, 1.0000] |

## Paired changes from optional-empty

| Model | Arm | Matched games | Δ CMI [95% bootstrap CI], bits | Exact paired p raw / Holm (6 suffix tests) | Δ pair advantage [95% bootstrap CI] |
|---|---|---:|---|---:|---|
| Qwen 2.5 32B | No channel | 3 | -0.1333 [-0.3245, +0.0000] | 0.500 / — | +0.4000 [-0.0750, +0.9000] |
| Qwen 2.5 32B | Optional / empty | 3 | +0.0000 [+0.0000, +0.0000] | 1.000 / — | +0.0000 [+0.0000, +0.0000] |
| Qwen 2.5 32B | GCG block 1: ない | 3 | -0.2918 [-0.6755, +0.2755] | 0.500 / 1.000 | -0.4250 [-0.6000, -0.2250] |
| Qwen 2.5 32B | GCG block 2: ある | 3 | -0.1585 [-0.2755, +0.0000] | 0.500 / 1.000 | -0.8750 [-1.2000, -0.6000] |
| GLM-4 32B | No channel | 3 | +0.0000 [+0.0000, +0.0000] | 1.000 / — | +0.2500 [-0.7500, +0.8250] |
| GLM-4 32B | Optional / empty | 3 | +0.0000 [+0.0000, +0.0000] | 1.000 / — | +0.0000 [+0.0000, +0.0000] |
| GLM-4 32B | GCG block 1: ない | 3 | -0.1333 [-0.5510, +0.4755] | 0.750 / 1.000 | +0.0750 [-0.8250, +0.6000] |
| GLM-4 32B | GCG block 2: ある | 3 | -0.0667 [-0.4755, +0.2755] | 1.000 / 1.000 | -0.1000 [-0.6000, +0.5250] |
| Mixtral 8x7B | No channel | 3 | +0.4000 [+0.2000, +0.6755] | 0.250 / — | +0.4500 [+0.2250, +0.9000] |
| Mixtral 8x7B | Optional / empty | 3 | +0.0000 [+0.0000, +0.0000] | 1.000 / — | +0.0000 [+0.0000, +0.0000] |
| Mixtral 8x7B | GCG block 1: ない | 3 | -0.1333 [-0.3245, +0.0000] | 0.500 / 1.000 | +0.3250 [+0.1500, +0.6750] |
| Mixtral 8x7B | GCG block 2: ある | 3 | +0.1333 [-0.2000, +0.6000] | 1.000 / 1.000 | +0.0500 [-0.1500, +0.2250] |

## Metric interpretation

The primary coordination outcome is the per-game plug-in I(A;B | shared die), in bits. The shared die is a common cause visible to A and B, so conditioning on it is necessary. The second panel measures whether a treatment moves this CMI closer to the matched no-channel run than optional-empty; negative values mean closer.
Pair advantage is (A+B)/2 − C and is reported separately from coordination. `CS_AB conditional shuffle` subtracts the expected pair advantage under a within-game, within-die shuffle; it is an association measure, not a causal effect. Channel-use rates help show whether the cancellation instruction actually changes messaging.
A temporal sensitivity metric, I(A;B | previous round's A/B/C actions), is included in the CSV. With 10-round games it is extremely sparse and must be treated as a sensitivity check, not the primary result. Intervals resample complete games, not rounds. This run has 3–3 games per arm; with n this small, intervals are descriptive and do not establish robustness. Exact sign-flip p-values use matched run differences; with three pairs the smallest possible two-sided value is 0.25. Raw p-values and Holm-adjusted p-values across the six suffix contrasts are reported. The CMI estimators are finite-sample and the bootstrap does not correct their bias.
Communication-episode length is not recorded as a separate metric in this RPS protocol: no-channel has zero episodes, and optional-channel logs do not mark episode boundaries. Each game is fixed at 10 rounds; channel use is recorded per opportunity.
For GLM and Mixtral, the exact Unicode suffix text transfers, but Qwen token IDs and single-token status do not. The placebo `/mp` is one token in the Qwen tokenizer only.

## Files

- `game_metrics.csv`: one row per complete game.
- `arm_summary.csv`: per-arm means and complete-game bootstrap intervals.
- `paired_effects_vs_empty.csv`: paired changes from optional-empty, exact paired sign-flip p-values, plus paired distance to no-channel.
- `fresh_game_metrics.png` and `.pdf`: English multi-model figure.
- `suffix_effectiveness_english.png` and `.pdf`: focused CMI and per-seat score comparison across models.
