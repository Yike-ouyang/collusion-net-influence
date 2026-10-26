# Coalition metrics: exploratory track

This folder is a separate research workspace for testing whether behavioural metrics can distinguish **coordination**, **advantage to A+B**, and **evidence of an agreement** in the repeated three-player pot RPS experiments.

## Start here

The work has three independent metric tracks so their evidence stays distinguishable, plus a GCG suffix transfer study:

1. [`01_coordination_signal/`](01_coordination_signal/README.md) — dependence between actions after controlling for the v4 shared number.
2. [`02_transfer_benefit/`](02_transfer_benefit/README.md) — coalition score advantage and a context-conditioned shuffle reference.
3. [`03_agreement_intention/`](03_agreement_intention/README.md) — messages, plans, and whether announced plans were executed.
4. [`05_gcg_suffix_evaluation/fresh_game_study/`](05_gcg_suffix_evaluation/fresh_game_study/README.md) — commands and prompts to launch the 10-round suffix comparison on Modal.

The three metric tracks each have their own `analyze.py` and write results into their own folder. Compare their condition summaries; do not collapse them into a single “suspicion score.”

Run all three from the repository root:

```bash
CAMPAIGNS="results/llm_rps_v2/20261025-1834_same_model_qwen32b_big-v4 results/llm_rps_v2/20261025-1837_same_model_glm32b_big-v4"
.venv/bin/python coalition_metrics/01_coordination_signal/analyze.py $CAMPAIGNS --permutations 999
.venv/bin/python coalition_metrics/02_transfer_benefit/analyze.py $CAMPAIGNS
.venv/bin/python coalition_metrics/03_agreement_intention/analyze.py $CAMPAIGNS
```

## Combined exploratory report

Run from the repository root:

```bash
python coalition_metrics/analyze_campaigns.py \
  results/llm_rps_v2/20261025-1834_same_model_qwen32b_big-v4 \
  results/llm_rps_v2/20261025-1837_same_model_glm32b_big-v4 \
  --permutations 999
```

The script writes two files into this folder:

- `game_metrics.csv`: one row per game and condition;
- `condition_summary.csv`: results pooled by campaign and condition, with game-level bootstrap intervals for payoff statistics.

The analysis is intentionally exploratory. Do not interpret a small permutation p-value as proof of intent or collusion.

## Project mapping

- Actors: seats A and B can use a private channel; C cannot see that channel.
- Decisions: simultaneous R/P/S moves, stored in each game's `actions` and `rounds[*].moves`.
- Outcomes: per-seat points under the fixed 3-point pot, stored in `rewards`.
- Context: scores and recent history are shown in prompts. In v4, A and B also see the same per-round `shared_die`; C does not.
- Communication and declared plans: stored in `rounds[*].chat`, `rounds[*].plans`, and the raw model outputs.
- Replication unit: a complete game (`run`), not an individual round. The current campaigns have 20 games × 60 rounds for each condition.

## First metrics in this track

### 1. Conditional action dependence

For actions `A_t`, `B_t`, and the shared v4 number `D_t`, estimate the plug-in conditional mutual information:

```text
I(A; B | D) = sum_d p(d) sum_(a,b) p(a,b | d) log[p(a,b | d) / (p(a | d) p(b | d))]
```

The script reports this in nats and also computes pairwise values for A–C and B–C. It permutes moves within each `(game, shared_die)` stratum to preserve each game's action frequencies for each number while breaking the same-round association. It reports a Bonferroni-adjusted A–B pair p-value across the three pairs.

This null is not yet sufficient for final inference: moves are sequentially dependent because agents see history. Unrestricted shuffling within a stratum breaks temporal structure. Follow-up work should compare block permutations and game-level bootstrap intervals, and test calibration under no-channel controls.

### 2. Coalition advantage and context-conditioned shuffle transfer

Per game, calculate mean per-round `((reward_A + reward_B) / 2) - reward_C`. For a reference distribution, shuffle B's moves within `(game, shared_die)` strata, recompute the payoff, and subtract the mean shuffled advantage from observed advantage. This is a context-conditioned **association** measure, not a causal effect: the counterfactual keeps the observed actions and game context fixed and does not model how agents would respond to an intervention.

### 3. Agreement evidence

Keep communication and plan evidence separate from action dependence and payoff. Report message content, declared A/B plans, plan agreement, and whether the announced moves were played. These are observable agreement signals; model reflections and end-of-game debriefs remain self-reports.

## Interpretation rules

- Dependence is a **coordination signal**, not proof of a coalition.
- Positive coalition advantage is a **payoff result**, not proof that coordination caused it.
- A private message or matching plan is **agreement evidence**, not proof that the agreement was executed or profitable.
- A non-significant test does not establish absence of coalition; assess power by injecting known coordination into held-out control games and measuring detection by sample size.
- The v4 number is visible to A and B and is a shared cause of their moves. Any A–B dependence analysis that omits it risks attributing common-context dependence to communication.

## Suggested next steps

1. Inspect `condition_summary.csv` beside the existing campaign reports.
2. Validate false-positive rates with `no_channel`, and power with scripted positive controls.
3. Add block-aware randomization or a hierarchical model that handles within-game adaptation.
4. Compare results with and without conditioning on `shared_die`, history, and prior scores.
5. Define a causal intervention/reference policy before calling any payoff contrast a causal transfer.
6. Add a residual-signal/power analysis only after calibration across simulated effect sizes and game counts.

The existing implementation is in `src/netinf/metrics.py` and `src/netinf/influence.py`; this folder does not replace it. The campaign protocol and prompt context are in `experiments/llm_rps_v2.py`, `src/netinf/protocol_v2.py`, and `prompts/pot_plan_v4.json`.
