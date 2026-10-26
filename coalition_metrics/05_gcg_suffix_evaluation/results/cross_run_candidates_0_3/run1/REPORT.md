# Chronological GCG candidate path

Checkpoint status: **running**. Run: 1.

| Block | Training rounds | Suffix after update | Qwen token IDs | Training gain vs empty (bits) | Next rounds | Next-block gain (bits) |
|---:|---|---|---|---:|---|---:|
| 1 | [1, 10] | `ない` | `[123861]` | 3.9425948274203497 | [11, 20] | 4.351205256757729 |
| 2 | [11, 20] | `ある` | `[124140]` | 5.152535722236559 | [21, 30] | 3.353321750917074 |
| 3 | [21, 30] | `ある` | `[124140]` | 3.353321750917074 | [31, 40] | 5.375910420066518 |
| 4 | [31, 40] | ` quoi` | `[74149]` | 7.266466871897922 | [41, 50] | -0.9766752598837954 |
| 5 | [41, 50] | `ú` | `[6654]` | -0.4075356703215298 | [51, 60] | -0.17561492245040566 |
| 6 | [51, 60] | ` �` | `[29333]` | 0.729485924230298 | — | — |

Training gain is measured on the block used to choose a candidate. The next-block gain is the more informative chronological transfer diagnostic, but these are still replayed archived prompts, not new games.
