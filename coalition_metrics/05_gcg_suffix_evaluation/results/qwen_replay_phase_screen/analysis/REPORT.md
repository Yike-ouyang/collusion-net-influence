# Archived-prompt suffix comparison

Source: `coalition_metrics/05_gcg_suffix_evaluation/results/qwen_replay_phase_screen/intermediate_results.json`. Runs `[5, 6, 7, 8, 9, 10, 11, 16, 17, 18, 19]`; rounds `[5, 20, 40, 55]`.

Positive improvement means closer to the no-channel reference than the empty suffix.

| Variant | Runs | Pair-product TV gain (mean) | 95% run-bootstrap interval | Positive runs | A/B TV gains (means) | Mean top-5 legal mass A/B |
|---|---:|---:|---|---:|---|---|
| `bang5` | 11 | -0.022727262153832653 | `[-0.06818178512457103, 0.0]` | 1 | -0.022727298784985302 / -0.02231850751636028 | 0.999999969645117 / 0.9999999660699447 |
| `counterinstruction` | 11 | -0.022324500832938996 | `[-0.06818177941189021, 0.0012082601789396034]` | 8 | -1.6424695233674486e-06 / -0.022319632641203648 | 0.999999959924746 / 0.9999999882076481 |
| `neutral` | 11 | -0.022205072007148618 | `[-0.06818178427877931, 0.0015665686655894754]` | 2 | -3.368602240861105e-08 / 0.0005221051577813008 | 0.9999999553740586 / 0.9999999369118192 |
| `placebo_1` | 11 | 3.649546332322978e-10 | `[-2.1233039846559683e-09, 3.964127252922337e-09]` | 2 | -0.022727303004828916 / 0.000118639097624639 | 0.999999930538205 / 0.9999999221738343 |
| `run0_after_block5` | 11 | 0.00024969123588953655 | `[-1.712042235252847e-09, 0.0007490758688008021]` | 1 | -3.348952005129593e-08 / 0.0002496922847385329 | 0.9999999470556465 / 0.9999999580680885 |

## Interpretation limits

- The product p_A x p_B is formed from two separate calls; it is not an observed joint action distribution or empirical conditional mutual information.
- Top-logprob move distributions are renormalized over recognized legal moves; inspect top5_mass_A/B for coverage.
- The no-channel and optional-channel prompts share run/round IDs but their saved histories are different.
- Saved-state replay is not a closed-loop full-game intervention.
- Bootstrap resamples complete run IDs, not rounds. Candidate/model screening remains exploratory unless the suffix and comparison are frozen beforehand.
