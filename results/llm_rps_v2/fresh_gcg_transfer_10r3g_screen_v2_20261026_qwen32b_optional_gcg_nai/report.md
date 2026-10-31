# v2 campaigns: fresh_gcg_transfer_10r3g_screen_v2_20261026_qwen32b_optional_gcg_nai

Analysed 2026-10-26 11:11, 3 games.

## Coalition, plans and detection

| design | condition | games | final A / B / C | A+B vs C /round | CS_AB | plan executed | channel use A / B | same move | assist | 6-cycle played | die table played | table followed A / B | betrayal | C per round (0.5 if table followed) | H(a) A/B/C | H(a|s) A/B/C | net-inf fixed / calib. | P(move played) A/B/C | intended = top-1 at MOVE | truncated / parse fails | longest prompt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| same_model | channel_optional | 3 | 5.5 / 4.5 / 9.0 | -0.40 [-0.60, +0.00] | -0.28 [-0.58, -0.10] | - | 67% / 65% | 83% | 17% | 7% | 3% | 27% / 40% | 30% | 0.90 | 1.23 / 1.30 / 1.40 | 0.40 / 0.32 / 0.18 | 2 / 0 of 3 | 100% / 100% / 100% | 92% | 1 / 0 | 3515 |

## Reflection (pooled statements; n in brackets)

| design | condition | player | intention = action | accounting errors | optimism (says ahead/level, is behind) | pessimism | predicts others | change if 'not working' | change if 'working' | change if correctly behind | change if wrongly behind |
|---|---|---|---|---|---|---|---|---|---|---|---|
| same_model | channel_optional | A+B | 100% (60) | 8% (24) | 8% (25) | 13% (31) | 67% (95) | 25% (4) | 73% (15) | 38% (13) | 50% (2) |
| same_model | channel_optional | C | 77% (30) | 12% (16) | 0% (9) | 5% (21) | 28% (43) | 0% (2) | - | 57% (7) | 100% (1) |

## Debrief understanding (correct / readable claims)

| design | condition | own strategy right (A+B / C) | who benefited right (A+B / C) | 'partner kept plan' right | C suspicion right | C suspects A-B |
|---|---|---|---|---|---|---|
| same_model | channel_optional | 1/4 / 1/3 | 5/6 / 3/3 | - | 1/1 | 0/1 |

## Per model and seat

| model | seat | games | mean final score | H(a) | intention = action | optimism | move parse failures |
|---|---|---|---|---|---|---|---|
| Qwen/Qwen2.5-32B-Instruct | A | 3 | 5.5 | 1.23 | 100% | 10% | 0 |
| Qwen/Qwen2.5-32B-Instruct | B | 3 | 4.5 | 1.30 | 100% | 7% | 0 |
| Qwen/Qwen2.5-32B-Instruct | C | 3 | 9.0 | 1.40 | 77% | 0% | 0 |

![coalition](coalition_by_condition.png)
