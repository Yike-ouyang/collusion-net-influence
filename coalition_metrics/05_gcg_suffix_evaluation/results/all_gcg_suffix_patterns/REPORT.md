# GCG accepted suffixes across available Qwen runs

Initial suffix: `!!!!!`. Runs with suffix paths: **6** (0 (complete), 1 (complete), 2 (complete), 3 (complete), 4 (complete), 5 (partial)); accepted path cells: **34**; candidate proposals recorded: **136**; unique suffixes in the complete panel: **85**.

## Checkpoint coverage

| Checkpoint | Status | Run IDs present | Complete run IDs |
|---|---|---|---|
| `qwen32b_chronological_bang5_runs_0_4.json` | `completed` | 0, 1, 2, 3, 4 | 0, 1, 2, 3, 4 |
| `qwen32b_chronological_bang5_runs_5_9.json` | `running` | 5 | — |

## Recurring accepted suffixes across runs

A run can contribute to several block cells when it re-selects a token; this is descriptive recurrence, not an independent-run test.

| Qwen token ID(s) | Decoded suffix | Distinct runs | Accepted run/block cells |
|---|---|---:|---|
| `123861` | `ない` | 3 | r0b1; r1b1; r4b1 |
| `124140` | `ある` | 3 | r0b2; r1b2; r1b3; r4b2 |
| `74149` | ` quoi` | 3 | r0b3; r1b4; r4b3; r4b4; r4b5; r4b6 |
| `111638` | `在网络` | 2 | r2b2; r2b3; r2b4; r2b5; r2b6; r3b4 |
| `31139` | `网` | 2 | r2b1; r3b1; r3b2; r3b3 |

## Recurring token IDs by block

Most frequent accepted token ID(s) at each update stage:

- Block 1: `123861` (3/6).
- Block 2: `124140` (3/6).
- Block 3: `74149` (2/6).
- Block 4: `111638` (2/6), `74149` (2/6).
- Block 5: `111638` (1/5), `3552` (1/5), `64684` (1/5), `6654` (1/5), `74149` (1/5).
- Block 6: `111638` (1/5), `29333` (1/5), `64684` (1/5), `74149` (1/5), `75493` (1/5).

Counts are distinct runs selecting the token after that block. Repeated blocks within one run count once per block, not as independent runs.

| Block | Qwen token ID | Decoded suffix | Runs / available | Run IDs |
|---:|---|---|---:|---|
| 1 | `123861` | `ない` | 3/6 | 0, 1, 4 |
| 1 | `31139` | `网` | 2/6 | 2, 3 |
| 2 | `124140` | `ある` | 3/6 | 0, 1, 4 |
| 3 | `74149` | ` quoi` | 2/6 | 0, 4 |
| 4 | `111638` | `在网络` | 2/6 | 2, 3 |
| 4 | `74149` | ` quoi` | 2/6 | 1, 4 |

## Full accepted suffix path

Block 6 is shown as an accepted final suffix but has no next-block prospective evaluation.

| Run | Block | Qwen token ID(s) | Decoded suffix | Next-block gain (bits) |
|---|---:|---|---|---:|
| 0 (complete) | 1 | `[123861]` | `ない` | 3.973 |
| 0 (complete) | 2 | `[124140]` | `ある` | 4.988 |
| 0 (complete) | 3 | `[74149]` | ` quoi` | -0.688 |
| 0 (complete) | 4 | `[5397]` | `és` | -0.761 |
| 0 (complete) | 5 | `[64684]` | `ื่` | 5.054 |
| 0 (complete) | 6 | `[64684]` | `ื่` | — |
| 1 (complete) | 1 | `[123861]` | `ない` | 4.351 |
| 1 (complete) | 2 | `[124140]` | `ある` | 3.353 |
| 1 (complete) | 3 | `[124140]` | `ある` | 5.376 |
| 1 (complete) | 4 | `[74149]` | ` quoi` | -0.977 |
| 1 (complete) | 5 | `[6654]` | `ú` | -0.176 |
| 1 (complete) | 6 | `[29333]` | ` �` | — |
| 2 (complete) | 1 | `[31139]` | `网` | 4.781 |
| 2 (complete) | 2 | `[111638]` | `在网络` | 4.422 |
| 2 (complete) | 3 | `[111638]` | `在网络` | 5.137 |
| 2 (complete) | 4 | `[111638]` | `在网络` | 6.522 |
| 2 (complete) | 5 | `[111638]` | `在网络` | 2.964 |
| 2 (complete) | 6 | `[111638]` | `在网络` | — |
| 3 (complete) | 1 | `[31139]` | `网` | 3.752 |
| 3 (complete) | 2 | `[31139]` | `网` | 6.085 |
| 3 (complete) | 3 | `[31139]` | `网` | 5.031 |
| 3 (complete) | 4 | `[111638]` | `在网络` | 1.135 |
| 3 (complete) | 5 | `[3552]` | ` password` | 1.551 |
| 3 (complete) | 6 | `[75493]` | ` passphrase` | — |
| 4 (complete) | 1 | `[123861]` | `ない` | 2.359 |
| 4 (complete) | 2 | `[124140]` | `ある` | 2.443 |
| 4 (complete) | 3 | `[74149]` | ` quoi` | 3.376 |
| 4 (complete) | 4 | `[74149]` | ` quoi` | 4.365 |
| 4 (complete) | 5 | `[74149]` | ` quoi` | 2.444 |
| 4 (complete) | 6 | `[74149]` | ` quoi` | — |
| 5 (partial) | 1 | `[76269]` | ` EINVAL` | 1.331 |
| 5 (partial) | 2 | `[21374]` | ` IllegalArgumentException` | 4.986 |
| 5 (partial) | 3 | `[21374]` | ` IllegalArgumentException` | 8.218 |
| 5 (partial) | 4 | `[21374]` | ` IllegalArgumentException` | 1.526 |

## Pattern reading

Among complete trajectories, **5 distinct terminal suffix token IDs** appear across **5 runs**. The strongest repeated choices are stage-specific; recurrence at different blocks within the same run does not mean the optimizer converged to the same final suffix.
The decoded strings include fragments from multiple writing systems and code-like text. Treat the pattern as token-level optimizer recurrence that may reflect the model tokenizer or context, not as a shared natural-language anti-collusion instruction.

## Interpretation

A repeated token within the same chronological block is a descriptive recurrence pattern, not evidence of a universal suffix or a statistical significance test. Next-block gains measure the GCG KL objective against the empty suffix, not empirical action CMI or game performance.
The block-5 suffix is the prospective candidate for rounds 51–60. Block-6 suffixes are in-sample final updates and must not be reported as prospectively validated.
Exact text, token IDs, full accepted paths, every candidate proposed by GCG, and a deduplicated panel of all proposed/accepted suffixes are preserved in the CSV files beside this report.
