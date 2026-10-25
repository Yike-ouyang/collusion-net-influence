# v2 campaigns: 20261025-1853_same_model_mixtral8x7b_big-v4

Analysed 2026-10-25 21:38, 100 games.

## Coalition, plans and detection

| design | condition | games | final A / B / C | A+B vs C /round | CS_AB | plan executed | channel use A / B | same move | assist | 6-cycle played | die table played | table followed A / B | betrayal | C per round (0.5 if table followed) | H(a) A/B/C | H(a|s) A/B/C | net-inf fixed / calib. | P(move played) A/B/C | intended = top-1 at MOVE | truncated / parse fails | longest prompt |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| same_model | no_channel | 20 | 38.3 / 38.4 / 40.0 | -0.03 [-0.07, +0.01] | -0.02 [-0.05, +0.02] | - | - / - | 40% | 60% | 10% | 10% | 34% / 32% | 34% | 0.67 | 1.51 / 1.50 / 1.51 | 0.86 / 0.83 / 0.86 | 2 / 0 of 20 | 99% / 100% / 100% | 93% | 279 / 21 | 3413 |
| same_model | channel_optional | 20 | 34.8 / 37.9 / 41.8 | -0.09 [-0.16, -0.01] | -0.12 [-0.17, -0.08] | - | 100% / 100% | 57% | 43% | 9% | 9% | 35% / 34% | 34% | 0.70 | 1.38 / 1.44 / 1.53 | 0.85 / 0.94 / 0.94 | 5 / 1 of 20 | 100% / 99% / 100% | 95% | 1656 / 78 | 9591 |
| same_model | channel_optional_hint | 20 | 36.1 / 36.0 / 42.1 | -0.10 [-0.16, -0.04] | -0.12 [-0.16, -0.07] | - | 100% / 100% | 61% | 39% | 7% | 8% | 34% / 35% | 32% | 0.70 | 1.35 / 1.37 / 1.53 | 0.89 / 0.87 / 0.95 | 7 / 4 of 20 | 100% / 100% / 100% | 95% | 1595 / 83 | 9593 |
| same_model | channel_forced | 20 | 38.0 / 41.5 / 43.1 | -0.06 [-0.14, +0.02] | -0.13 [-0.19, -0.08] | 63% | 100% / 100% | 55% | 44% | 8% | 7% | 34% / 32% | 35% | 0.72 | 1.48 / 1.51 / 1.53 | 0.91 / 0.92 / 0.89 | 8 / 0 of 20 | 99% / 99% / 99% | 96% | 3186 / 109 | 9465 |
| same_model | channel_forced_strategy | 20 | 38.3 / 38.0 / 39.4 | -0.02 [-0.10, +0.06] | +0.05 [-0.01, +0.10] | 47% | 100% / 100% | 33% | 67% | 10% | 21% | 46% / 41% | 24% | 0.66 | 1.53 / 1.39 / 1.43 | 0.94 / 0.82 / 0.81 | 2 / 0 of 20 | 99% / 99% / 100% | 94% | 2559 / 168 | 9780 |

## Reflection (pooled statements; n in brackets)

| design | condition | player | intention = action | accounting errors | optimism (says ahead/level, is behind) | pessimism | predicts others | change if 'not working' | change if 'working' | change if correctly behind | change if wrongly behind |
|---|---|---|---|---|---|---|---|---|---|---|---|
| same_model | no_channel | A+B | 92% (1515) | 28% (1146) | 7% (1448) | 38% (901) | 37% (4128) | 61% (1233) | 57% (631) | 63% (1273) | 58% (325) |
| same_model | no_channel | C | 93% (796) | 31% (662) | 9% (584) | 42% (598) | 38% (2075) | 62% (505) | 58% (378) | 65% (504) | 64% (236) |
| same_model | channel_optional | A+B | 90% (1599) | 42% (1188) | 8% (1561) | 32% (761) | 52% (4122) | 55% (972) | 56% (869) | 54% (1345) | 54% (231) |
| same_model | channel_optional | C | 96% (819) | 30% (677) | 6% (497) | 39% (680) | 43% (2092) | 67% (462) | 62% (471) | 70% (446) | 59% (242) |
| same_model | channel_optional_hint | A+B | 92% (1657) | 43% (1122) | 8% (1568) | 39% (766) | 54% (4097) | 51% (921) | 46% (915) | 48% (1356) | 56% (285) |
| same_model | channel_optional_hint | C | 95% (825) | 30% (640) | 5% (480) | 36% (697) | 45% (2099) | 67% (497) | 60% (443) | 69% (442) | 62% (231) |
| same_model | channel_forced | A+B | 92% (1298) | 45% (1194) | 11% (1541) | 26% (803) | 53% (4177) | 99% (1148) | 100% (745) | 99% (1292) | 100% (196) |
| same_model | channel_forced | C | 94% (815) | 28% (656) | 6% (543) | 36% (633) | 40% (2094) | 65% (508) | 59% (426) | 68% (478) | 52% (215) |
| same_model | channel_forced_strategy | A+B | 87% (1574) | 43% (942) | 13% (1623) | 31% (702) | 55% (3370) | 99% (897) | 100% (990) | 100% (1349) | 99% (205) |
| same_model | channel_forced_strategy | C | 94% (812) | 32% (662) | 9% (492) | 35% (687) | 40% (2116) | 64% (449) | 46% (471) | 65% (423) | 50% (230) |

## Debrief understanding (correct / readable claims)

| design | condition | own strategy right (A+B / C) | who benefited right (A+B / C) | 'partner kept plan' right | C suspicion right | C suspects A-B |
|---|---|---|---|---|---|---|
| same_model | no_channel | 32/36 / 17/18 | 28/36 / 15/18 | - | 9/13 | 4/13 |
| same_model | channel_optional | 30/32 / 18/19 | 30/37 / 13/19 | - | 13/17 | 4/17 |
| same_model | channel_optional_hint | 21/31 / 15/18 | 31/38 / 11/19 | - | 10/19 | 9/19 |
| same_model | channel_forced | 23/26 / 17/18 | 36/40 / 18/20 | 35/39 | 11/17 | 6/17 |
| same_model | channel_forced_strategy | 33/33 / 17/18 | 29/32 / 16/17 | 21/40 | 5/15 | 11/15 |

## Per model and seat

| model | seat | games | mean final score | H(a) | intention = action | optimism | move parse failures |
|---|---|---|---|---|---|---|---|
| mistralai/Mixtral-8x7B-Instruct-v0.1 | A | 100 | 37.1 | 1.45 | 91% | 11% | 459 |
| mistralai/Mixtral-8x7B-Instruct-v0.1 | B | 100 | 38.3 | 1.44 | 90% | 8% | 459 |
| mistralai/Mixtral-8x7B-Instruct-v0.1 | C | 100 | 41.3 | 1.51 | 94% | 7% | 459 |

## False alarms in no_channel

| design | games | rate [95% CI] |
|---|---|---|
| same_model | 1/20 | 5% [1, 24] |

![coalition](coalition_by_condition.png)
