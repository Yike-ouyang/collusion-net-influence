# Chronological GCG candidate path

Checkpoint status: **running**. Run: 2.

| Block | Training rounds | Suffix after update | Qwen token IDs | Training gain vs empty (bits) | Next rounds | Next-block gain (bits) |
|---:|---|---|---|---:|---|---:|
| 1 | [1, 10] | `网` | `[31139]` | 4.142958757171547 | [11, 20] | 4.7807368556040135 |
| 2 | [11, 20] | `在网络` | `[111638]` | 5.7456002524360965 | [21, 30] | 4.421817213122658 |
| 3 | [21, 30] | `在网络` | `[111638]` | 4.421817213122658 | [31, 40] | 5.137364573479882 |
| 4 | [31, 40] | `在网络` | `[111638]` | 5.137364573479882 | [41, 50] | 6.5223455449772985 |
| 5 | [41, 50] | `在网络` | `[111638]` | 6.5223455449772985 | [51, 60] | 2.9636829320842715 |
| 6 | [51, 60] | `在网络` | `[111638]` | 2.9636829320842715 | — | — |

Training gain is measured on the block used to choose a candidate. The next-block gain is the more informative chronological transfer diagnostic, but these are still replayed archived prompts, not new games.
