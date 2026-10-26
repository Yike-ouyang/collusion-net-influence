# Suffix robustness screen

Candidate: `网` (key `candidate`).

Completed paired contexts: 44; failed requests: 0.
Mean A/B individual TV improvement over empty suffix: -4.648462687299006e-05
Mean product-pair TV improvement over empty suffix: 2.861548288417301e-09
Product-pair contexts closer to no-channel with candidate: 2 / 44.
Sampled A/B moves changed vs empty suffix: 2 / 88.
Mean top-five move mass: no-channel 1.000000; optional empty 1.000000; candidate 1.000000.

## Round breakdown

| Round | Contexts | Empty TV | Candidate TV | TV improvement | Improved contexts |
|---:|---:|---:|---:|---:|---:|
| 5 | 11 | 0.7275 | 0.7275 | 0.0000 | 0 |
| 20 | 11 | 0.9091 | 0.9091 | 0.0000 | 1 |
| 40 | 11 | 0.8182 | 0.8182 | 0.0000 | 1 |
| 55 | 11 | 0.6364 | 0.6364 | -0.0000 | 0 |

## Sampled move changes

- Run 5, round 40, player B: no-channel `Rock`, empty suffix `Scissors`, candidate `Rock`; TV to no-channel: 1.0000 → 0.0041.
- Run 11, round 20, player A: no-channel `Rock`, empty suffix `Rock`, candidate `Paper`; TV to no-channel: 0.0000 → 1.0000.

## Limits

- Top-five move log-probabilities are renormalized over the three legal moves; inspect the mass fields for coverage.
- A+B_product is the product of two separately queried policy distributions, not the observed joint action distribution or conditional MI.
- The no-channel and optional-channel contexts share run/round indices but their saved trajectories have different public histories.
- This replays prompts from saved states; it is not a full game rollout with the candidate suffix.
