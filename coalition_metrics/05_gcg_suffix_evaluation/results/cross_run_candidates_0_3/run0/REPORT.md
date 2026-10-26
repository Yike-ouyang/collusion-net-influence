# Chronological GCG candidate path

Checkpoint status: **running**. Run: 0.

| Block | Training rounds | Suffix after update | Qwen token IDs | Training gain vs empty (bits) | Next rounds | Next-block gain (bits) |
|---:|---|---|---|---:|---|---:|
| 1 | [1, 10] | `ない` | `[123861]` | 2.296577936185891 | [11, 20] | 3.9732927563457996 |
| 2 | [11, 20] | `ある` | `[124140]` | 5.829607173248779 | [21, 30] | 4.987750276858283 |
| 3 | [21, 30] | ` quoi` | `[74149]` | 6.432975573247731 | [31, 40] | -0.6883456508935677 |
| 4 | [31, 40] | `és` | `[5397]` | -0.4364996692632578 | [41, 50] | -0.7606629969829966 |
| 5 | [41, 50] | `ื่` | `[64684]` | 11.392309908602812 | [51, 60] | 5.054017574314056 |
| 6 | [51, 60] | `ื่` | `[64684]` | 5.054017574314056 | — | — |

Training gain is measured on the block used to choose a candidate. The next-block gain is the more informative chronological transfer diagnostic, but these are still replayed archived prompts, not new games.
