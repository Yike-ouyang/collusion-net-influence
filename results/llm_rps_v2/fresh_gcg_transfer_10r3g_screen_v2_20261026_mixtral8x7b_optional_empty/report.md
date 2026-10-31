# v2 campaigns: fresh_gcg_transfer_10r3g_screen_v2_20261026_mixtral8x7b_optional_empty

Analysed 2026-10-26 11:11, 3 games.

## Coalition, plans and detection

| design | condition | games | final A / B / C | A+B vs C /round | CS_AB | plan executed | channel use A / B | same move | assist | 6-cycle played | die table played | table followed A / B | betrayal | C per round (0.5 if table followed) | H(a) A/B/C | H(a|s) A/B/C | net-inf fixed / calib. | P(move played) A/B/C | intended = top-1 at MOVE | truncated / parse fails | longest prompt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| same_model | channel_optional | 3 | 9.0 / 6.5 / 9.5 | -0.18 [-0.45, +0.00] | -0.13 [-0.19, -0.04] | - | 100% / 100% | 77% | 23% | 3% | 7% | 37% / 33% | 37% | 0.95 | 1.12 / 1.17 / 1.53 | 0.38 / 0.45 / 0.53 | 0 / 0 of 3 | 100% / 100% / 99% | 96% | 35 / 1 | 7104 |

## Reflection (pooled statements; n in brackets)

| design | condition | player | intention = action | accounting errors | optimism (says ahead/level, is behind) | pessimism | predicts others | change if 'not working' | change if 'working' | change if correctly behind | change if wrongly behind |
|---|---|---|---|---|---|---|---|---|---|---|---|
| same_model | channel_optional | A+B | 98% (49) | 40% (30) | 22% (27) | 10% (31) | 57% (93) | 58% (12) | 30% (27) | 29% (7) | 67% (3) |
| same_model | channel_optional | C | 90% (21) | 25% (20) | 30% (10) | 35% (20) | 49% (47) | 86% (7) | 71% (7) | 50% (4) | 83% (6) |

## Debrief understanding (correct / readable claims)

| design | condition | own strategy right (A+B / C) | who benefited right (A+B / C) | 'partner kept plan' right | C suspicion right | C suspects A-B |
|---|---|---|---|---|---|---|
| same_model | channel_optional | 2/5 / 3/3 | 4/4 / 1/2 | - | 2/2 | 0/2 |

## Per model and seat

| model | seat | games | mean final score | H(a) | intention = action | optimism | move parse failures |
|---|---|---|---|---|---|---|---|
| mistralai/Mixtral-8x7B-Instruct-v0.1 | A | 3 | 9.0 | 1.12 | 100% | 20% | 1 |
| mistralai/Mixtral-8x7B-Instruct-v0.1 | B | 3 | 6.5 | 1.17 | 96% | 24% | 1 |
| mistralai/Mixtral-8x7B-Instruct-v0.1 | C | 3 | 9.5 | 1.53 | 90% | 30% | 1 |

![coalition](coalition_by_condition.png)
