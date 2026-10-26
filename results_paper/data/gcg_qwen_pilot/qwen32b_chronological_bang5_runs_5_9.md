# Per-run chronological Qwen GCG

Status: **running**; start suffix `!!!!!`; block size 10 rounds.

## Method and hypotheses
- H1: chronological block GCG lowers no-channel-to-optional KL within individual runs.
- H2: suffix updates learned from earlier rounds also improve the next, not-yet-trained chronological block.
- H3: independently optimized runs converge toward repeated token IDs or text fragments more often than expected by chance.
- H4: any repeated suffix pattern is a candidate for a separate fresh-game evaluation, not proof of anti-collusion.

The objective averages per-context forward KLs within each contiguous chronological block. The candidate is selected on the current block and scored on the next block before that future block receives its own update. Rounds remain grouped in chronological run trajectories.

## Per-run suffix path

| Run | Block | Rounds | Suffix used → suffix after update | Block gain (bits) | Next-block gain (bits) |
|---:|---:|---|---|---:|---:|
| 5 | 1 | 1–10 | `!!!!!` → ` EINVAL` | 1.4537 | 1.3311 |
| 5 | 2 | 11–20 | ` EINVAL` → ` IllegalArgumentException` | 4.2382 | 4.9862 |
| 5 | 3 | 21–30 | ` IllegalArgumentException` → ` IllegalArgumentException` | 0.0000 | 8.2179 |
| 5 | 4 | 31–40 | ` IllegalArgumentException` → ` IllegalArgumentException` | 0.0000 | 1.5264 |
| 5 | 5 | 41–50 | ` IllegalArgumentException` → ` IllegalArgumentException` | 0.0000 | 4.9328 |
| 5 | 6 | 51–60 | ` IllegalArgumentException` → ` IllegalArgumentException` | 0.0000 | — |
| 6 | 1 | 1–10 | `!!!!!` → `ない` | 2.7484 | 3.9023 |
| 6 | 2 | 11–20 | `ない` → `いい` | 2.1095 | 3.3417 |
| 6 | 3 | 21–30 | `いい` → `オ` | 0.1739 | 4.6179 |
| 6 | 4 | 31–40 | `オ` → `オ` | 0.0000 | 5.4237 |
| 6 | 5 | 41–50 | `オ` → `オ` | 0.0000 | 5.5756 |
| 6 | 6 | 51–60 | `オ` → `オ` | 0.0000 | — |
| 7 | 1 | 1–10 | `!!!!!` → `ない` | 3.7672 | 3.1989 |
| 7 | 2 | 11–20 | `ない` → `ある` | 2.9401 | 5.2760 |
| 7 | 3 | 21–30 | `ある` → ` quoi` | 1.1170 | 11.3972 |
| 7 | 4 | 31–40 | ` quoi` → ` quoi` | 0.0000 | 4.5379 |
| 7 | 5 | 41–50 | ` quoi` → ` quoi` | 0.0000 | 2.6332 |
| 7 | 6 | 51–60 | ` quoi` → ` quoi` | 0.0000 | — |
| 8 | 1 | 1–10 | `!!!!!` → `令` | 6.8466 | 9.3872 |
| 8 | 2 | 11–20 | `令` → `令` | 0.0000 | 6.1581 |
| 8 | 3 | 21–30 | `令` → `令` | 0.0000 | 7.6684 |
| 8 | 4 | 31–40 | `令` → `令` | 0.0000 | 9.8634 |

## Final per-run candidates

| Run | Suffix after round 60 | Token IDs |
|---:|---|---|
| 5 | ` IllegalArgumentException` | `[21374]` |
| 6 | `オ` | `[89862]` |
| 7 | ` quoi` | `[74149]` |

## Limits

- The GCG loss matches optional-channel policy distributions to the no-channel reference; it does not directly minimize observed I(A;B|S).
- The pair law is a product of two separately queried move policies, not an empirically sampled joint action law.
- Within a run, each suffix update is selected using one contiguous current block; the next block is measured before it is used for its own update.
- No-channel and optional-channel states share run/round labels but are separate saved trajectories with different public histories.
- This prompt-level procedure is not a full game rollout. Confirm a consensus suffix on fresh complete games and game-level metrics.
