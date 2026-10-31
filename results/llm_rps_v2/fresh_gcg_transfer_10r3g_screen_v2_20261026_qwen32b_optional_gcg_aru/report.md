# v2 campaigns: fresh_gcg_transfer_10r3g_screen_v2_20261026_qwen32b_optional_gcg_aru

Analysed 2026-10-26 11:17, 3 games.

## Coalition, plans and detection

| design | condition | games | final A / B / C | A+B vs C /round | CS_AB | plan executed | channel use A / B | same move | assist | 6-cycle played | die table played | table followed A / B | betrayal | C per round (0.5 if table followed) | H(a) A/B/C | H(a|s) A/B/C | net-inf fixed / calib. | P(move played) A/B/C | intended = top-1 at MOVE | truncated / parse fails | longest prompt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| same_model | channel_optional | 3 | 3.5 / 3.5 / 12.0 | -0.85 [-1.20, -0.60] | -0.44 [-0.74, -0.07] | - | 70% / 70% | 80% | 20% | 3% | 3% | 33% / 23% | 40% | 1.20 | 1.36 / 1.46 / 1.25 | 0.40 / 0.32 / 0.40 | 1 / 0 of 3 | 100% / 100% / 99% | 91% | 0 / 0 | 3494 |

## Reflection (pooled statements; n in brackets)

| design | condition | player | intention = action | accounting errors | optimism (says ahead/level, is behind) | pessimism | predicts others | change if 'not working' | change if 'working' | change if correctly behind | change if wrongly behind |
|---|---|---|---|---|---|---|---|---|---|---|---|
| same_model | channel_optional | A+B | 98% (60) | 37% (27) | 4% (50) | 11% (9) | 78% (94) | 73% (11) | 71% (7) | 65% (31) | 0% (1) |
| same_model | channel_optional | C | 77% (30) | 11% (18) | - | 0% (30) | 38% (48) | 100% (1) | 12% (8) | - | - |

## Debrief understanding (correct / readable claims)

| design | condition | own strategy right (A+B / C) | who benefited right (A+B / C) | 'partner kept plan' right | C suspicion right | C suspects A-B |
|---|---|---|---|---|---|---|
| same_model | channel_optional | 4/4 / 0/3 | 6/6 / 3/3 | - | - | - |

## Per model and seat

| model | seat | games | mean final score | H(a) | intention = action | optimism | move parse failures |
|---|---|---|---|---|---|---|---|
| Qwen/Qwen2.5-32B-Instruct | A | 3 | 3.5 | 1.36 | 97% | 4% | 0 |
| Qwen/Qwen2.5-32B-Instruct | B | 3 | 3.5 | 1.46 | 100% | 4% | 0 |
| Qwen/Qwen2.5-32B-Instruct | C | 3 | 12.0 | 1.25 | 77% | - | 0 |

![coalition](coalition_by_condition.png)
