# v2 campaigns: fresh_gcg_transfer_10r3g_screen_v2_20261026_glm32b_no_channel

Analysed 2026-10-26 11:00, 3 games.

## Coalition, plans and detection

| design | condition | games | final A / B / C | A+B vs C /round | CS_AB | plan executed | channel use A / B | same move | assist | 6-cycle played | die table played | table followed A / B | betrayal | C per round (0.5 if table followed) | H(a) A/B/C | H(a|s) A/B/C | net-inf fixed / calib. | P(move played) A/B/C | intended = top-1 at MOVE | truncated / parse fails | longest prompt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| same_model | no_channel | 3 | 8.5 / 3.0 / 6.5 | -0.08 [-0.68, +0.30] | -0.05 [-0.54, +0.31] | - | - / - | 37% | 63% | 3% | 7% | 17% / 40% | 43% | 0.65 | 1.53 / 1.41 / 1.43 | 0.07 / 0.15 / 0.22 | 0 / 0 of 3 | 99% / 93% / 100% | 69% | 4 / 1 | 1096 |

## Reflection (pooled statements; n in brackets)

| design | condition | player | intention = action | accounting errors | optimism (says ahead/level, is behind) | pessimism | predicts others | change if 'not working' | change if 'working' | change if correctly behind | change if wrongly behind |
|---|---|---|---|---|---|---|---|---|---|---|---|
| same_model | no_channel | A+B | 63% (60) | 2% (40) | 4% (26) | 9% (34) | 33% (91) | 70% (10) | 75% (4) | 69% (13) | 100% (1) |
| same_model | no_channel | C | 72% (29) | 6% (18) | 23% (13) | 0% (17) | 36% (45) | 67% (3) | 0% (3) | 75% (4) | - |

## Debrief understanding (correct / readable claims)

| design | condition | own strategy right (A+B / C) | who benefited right (A+B / C) | 'partner kept plan' right | C suspicion right | C suspects A-B |
|---|---|---|---|---|---|---|
| same_model | no_channel | 5/5 / 3/3 | 4/4 / 2/2 | - | 0/2 | 2/2 |

## Per model and seat

| model | seat | games | mean final score | H(a) | intention = action | optimism | move parse failures |
|---|---|---|---|---|---|---|---|
| zai-org/GLM-4-32B-0414 | A | 3 | 8.5 | 1.53 | 63% | 0% | 1 |
| zai-org/GLM-4-32B-0414 | B | 3 | 3.0 | 1.41 | 63% | 6% | 1 |
| zai-org/GLM-4-32B-0414 | C | 3 | 6.5 | 1.43 | 72% | 23% | 1 |

## False alarms in no_channel

| design | games | rate [95% CI] |
|---|---|---|
| same_model | 0/3 | 0% [0, 56] |

![coalition](coalition_by_condition.png)
