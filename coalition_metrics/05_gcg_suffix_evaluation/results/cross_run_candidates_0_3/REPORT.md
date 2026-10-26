# Candidate suffixes from completed chronological GCG runs

Checkpoint status: **running**. Complete runs available: `[0, 1, 2, 3]`.
Unique accepted suffixes included: **9** (blocks 1–5).

Suffixes are deduplicated by exact decoded text. Source rows and next-block gains are in `suffix_recurrence.csv`.
The screening is exploratory; the checkpoint may still be incomplete.

| Label | Exact suffix | Source runs | Source blocks | Next-block gains (bits) |
|---|---|---|---|---|
| `run0_after_block1` | `ない` | 0, 1 | r0b1, r1b1 | 3.973, 4.351 |
| `run0_after_block2` | `ある` | 0, 1 | r0b2, r1b2, r1b3 | 4.988, 3.353, 5.376 |
| `run0_after_block3` | ` quoi` | 0, 1 | r0b3, r1b4 | -0.688, -0.977 |
| `run0_after_block4` | `és` | 0 | r0b4 | -0.761 |
| `run0_after_block5` | `ื่` | 0 | r0b5 | 5.054 |
| `run1_after_block5` | `ú` | 1 | r1b5 | -0.176 |
| `run2_after_block1` | `网` | 2, 3 | r2b1, r3b1, r3b2, r3b3 | 4.781, 3.752, 6.085, 5.031 |
| `run2_after_block2` | `在网络` | 2, 3 | r2b2, r2b3, r2b4, r2b5, r3b4 | 4.422, 5.137, 6.522, 2.964, 1.135 |
| `run3_after_block5` | ` password` | 3 | r3b5 | 1.551 |
