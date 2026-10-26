# Chronological GCG candidate path

Checkpoint status: **running**. Run: 3.

| Block | Training rounds | Suffix after update | Qwen token IDs | Training gain vs empty (bits) | Next rounds | Next-block gain (bits) |
|---:|---|---|---|---:|---|---:|
| 1 | [1, 10] | `网` | `[31139]` | 4.224766630592701 | [11, 20] | 3.7515808126091668 |
| 2 | [11, 20] | `网` | `[31139]` | 3.7515808126091668 | [21, 30] | 6.085006586781151 |
| 3 | [21, 30] | `网` | `[31139]` | 6.085006586781151 | [31, 40] | 5.031227861405717 |
| 4 | [31, 40] | `在网络` | `[111638]` | 6.627375186753931 | [41, 50] | 1.135437197210266 |
| 5 | [41, 50] | ` password` | `[3552]` | 1.9112075437860538 | [51, 60] | 1.5505036726504555 |
| 6 | [51, 60] | ` passphrase` | `[75493]` | 3.82479729455989 | — | — |

Training gain is measured on the block used to choose a candidate. The next-block gain is the more informative chronological transfer diagnostic, but these are still replayed archived prompts, not new games.
