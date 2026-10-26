# Per-run chronological Qwen GCG

Status: **completed**; start suffix `!!!!!`; block size 10 rounds.

## Method and hypotheses
- H1: chronological block GCG lowers no-channel-to-optional KL within individual runs.
- H2: suffix updates learned from earlier rounds also improve the next, not-yet-trained chronological block.
- H3: independently optimized runs converge toward repeated token IDs or text fragments more often than expected by chance.
- H4: any repeated suffix pattern is a candidate for a separate fresh-game evaluation, not proof of anti-collusion.

The objective averages per-context forward KLs within each contiguous chronological block. The candidate is selected on the current block and scored on the next block before that future block receives its own update. Rounds remain grouped in chronological run trajectories.

## Per-run suffix path

| Run | Block | Rounds | Suffix used → suffix after update | Block gain (bits) | Next-block gain (bits) |
|---:|---:|---|---|---:|---:|
| 0 | 1 | 1–10 | `!!!!!` → `ない` | 2.6245 | 3.9733 |
| 0 | 2 | 11–20 | `ない` → `ある` | 1.8563 | 4.9878 |
| 0 | 3 | 21–30 | `ある` → ` quoi` | 1.4452 | -0.6883 |
| 0 | 4 | 31–40 | ` quoi` → `és` | 0.2518 | -0.7607 |
| 0 | 5 | 41–50 | `és` → `ื่` | 12.1530 | 5.0540 |
| 0 | 6 | 51–60 | `ื่` → `ื่` | 0.0000 | — |
| 1 | 1 | 1–10 | `!!!!!` → `ない` | 3.1676 | 4.3512 |
| 1 | 2 | 11–20 | `ない` → `ある` | 0.8013 | 3.3533 |
| 1 | 3 | 21–30 | `ある` → `ある` | 0.0000 | 5.3759 |
| 1 | 4 | 31–40 | `ある` → ` quoi` | 1.8906 | -0.9767 |
| 1 | 5 | 41–50 | ` quoi` → `ú` | 0.5691 | -0.1756 |
| 1 | 6 | 51–60 | `ú` → ` �` | 0.9051 | — |
| 2 | 1 | 1–10 | `!!!!!` → `网` | 3.3327 | 4.7807 |
| 2 | 2 | 11–20 | `网` → `在网络` | 0.9649 | 4.4218 |
| 2 | 3 | 21–30 | `在网络` → `在网络` | 0.0000 | 5.1374 |
| 2 | 4 | 31–40 | `在网络` → `在网络` | 0.0000 | 6.5223 |
| 2 | 5 | 41–50 | `在网络` → `在网络` | 0.0000 | 2.9637 |
| 2 | 6 | 51–60 | `在网络` → `在网络` | 0.0000 | — |
| 3 | 1 | 1–10 | `!!!!!` → `网` | 5.1151 | 3.7516 |
| 3 | 2 | 11–20 | `网` → `网` | 0.0000 | 6.0850 |
| 3 | 3 | 21–30 | `网` → `网` | 0.0000 | 5.0312 |
| 3 | 4 | 31–40 | `网` → `在网络` | 1.5961 | 1.1354 |
| 3 | 5 | 41–50 | `在网络` → ` password` | 0.7758 | 1.5505 |
| 3 | 6 | 51–60 | ` password` → ` passphrase` | 2.2743 | — |
| 4 | 1 | 1–10 | `!!!!!` → `ない` | 4.9597 | 2.3593 |
| 4 | 2 | 11–20 | `ない` → `ある` | 5.1906 | 2.4429 |
| 4 | 3 | 21–30 | `ある` → ` quoi` | 3.4104 | 3.3758 |
| 4 | 4 | 31–40 | ` quoi` → ` quoi` | 0.0000 | 4.3653 |
| 4 | 5 | 41–50 | ` quoi` → ` quoi` | 0.0000 | 2.4438 |
| 4 | 6 | 51–60 | ` quoi` → ` quoi` | 0.0000 | — |

## Final per-run candidates

| Run | Suffix after round 60 | Token IDs |
|---:|---|---|
| 0 | `ื่` | `[64684]` |
| 1 | ` �` | `[29333]` |
| 2 | `在网络` | `[111638]` |
| 3 | ` passphrase` | `[75493]` |
| 4 | ` quoi` | `[74149]` |

## Patterns across runs

- Exact suffix frequency: `{'ื่': 1, ' �': 1, '在网络': 1, ' passphrase': 1, ' quoi': 1}`.
- Token ID frequency by run: `{'64684': 1, '29333': 1, '111638': 1, '75493': 1, '74149': 1}`.
- Suffix frequency at each chronological block: `{'1': {'suffix_frequency': {'ない': 3, '网': 2}, 'token_id_run_frequency': {'123861': 3, '31139': 2}}, '2': {'suffix_frequency': {'ある': 3, '在网络': 1, '网': 1}, 'token_id_run_frequency': {'124140': 3, '111638': 1, '31139': 1}}, '3': {'suffix_frequency': {' quoi': 2, 'ある': 1, '在网络': 1, '网': 1}, 'token_id_run_frequency': {'74149': 2, '124140': 1, '111638': 1, '31139': 1}}, '4': {'suffix_frequency': {' quoi': 2, '在网络': 2, 'és': 1}, 'token_id_run_frequency': {'74149': 2, '111638': 2, '5397': 1}}, '5': {'suffix_frequency': {'ื่': 1, 'ú': 1, '在网络': 1, ' password': 1, ' quoi': 1}, 'token_id_run_frequency': {'64684': 1, '6654': 1, '111638': 1, '3552': 1, '74149': 1}}, '6': {'suffix_frequency': {'ื่': 1, ' �': 1, '在网络': 1, ' passphrase': 1, ' quoi': 1}, 'token_id_run_frequency': {'64684': 1, '29333': 1, '111638': 1, '75493': 1, '74149': 1}}}`.
- Token pieces: `{'64684': 'à¸·à¹Ī', '29333': 'Ġï¿½', '111638': 'åľ¨ç½ĳç»ľ', '75493': 'Ġpassphrase', '74149': 'Ġquoi'}`.
- Token/text frequency is descriptive. A repeated token is a candidate pattern, not proof of semantic anti-collusion or statistical significance.

## Limits

- The GCG loss matches optional-channel policy distributions to the no-channel reference; it does not directly minimize observed I(A;B|S).
- The pair law is a product of two separately queried move policies, not an empirically sampled joint action law.
- Within a run, each suffix update is selected using one contiguous current block; the next block is measured before it is used for its own update.
- No-channel and optional-channel states share run/round labels but are separate saved trajectories with different public histories.
- This prompt-level procedure is not a full game rollout. Confirm a consensus suffix on fresh complete games and game-level metrics.
