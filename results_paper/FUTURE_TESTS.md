# Next tests and remaining analysis

## Priority 1 — Frozen suffixes in new complete games

Run the prepared seven-arm study for Qwen, GLM, and Mixtral: no channel; optional channel empty; optional channel + `ない`; optional channel + `ある`; optional channel + `!!!!!`; optional channel + random `/mp`; and an explicit anti-channel instruction. The plan is 6 paired games × 10 rounds per arm and model. This is an exploratory screen, not enough to support a strong final claim. The prompt JSONs, campaign launcher, fetching command, and analysis script are in `coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/`.

Pre-register `ない` and `ある` as candidates because they recur at the same early GCG update stage. Do not select the winner from the same new games and then report those games as independent validation. If either candidate moves the primary metric, run a larger held-out set with the candidate frozen.

Report these outcomes separately:

1. `I(A;B | shared die)` as the primary common-context action-dependence outcome, with no-channel as the model-specific reference.
2. `I(A;B | previous joint actions)` as a temporal sensitivity analysis.
3. Pair advantage `(A+B)/2 − C`, individual payoffs, `CS_AB`, and channel-use rates.
4. Messages, plans, and whether actions followed a stated plan. Treat model-written debriefs as self-reports, not ground truth.

Resample complete games, not individual rounds. With only ten rounds per game, show per-game points and emphasize the uncertainty.

## Priority 2 — Recover the mechanism from existing traces

The original 60-round campaign folders already contain full game JSONs and generated reports. A useful follow-up is to label each private message and plan for (a) an explicit agreement, (b) a proposed strategy, (c) an accepted strategy, and (d) execution by the subsequent actions. Compare those labels with channel usage, state-conditioned action dependence, and pair advantage. This tests whether the statistical signal corresponds to observable agreement and execution.

Separately compare `channel_optional`, `channel_forced`, `channel_optional_hint`, and `channel_forced_strategy`. The present results suggest that access to a channel and the ability to use a specified strategy are distinct factors.

The rounds 8–10 probability-law screen is another secondary lead: its optional-minus-no-channel soft-MI differences were Qwen +0.530 bits [0.238, 0.886], GLM +0.281 [0.009, 0.591], and Mixtral +0.167 [-0.056, 0.378]. This is a pooled probability diagnostic, not the state-conditioned action CMI; check it against full-game action outcomes before using it as a headline result.

## Priority 3 — Validate the detector and null model

- Recompute the dependence statistic with context-stratified permutations, block permutations, and complete-game bootstrap intervals.
- Check sensitivity to sparse states, action support, and plug-in estimator bias.
- Add known negative and positive controls: independent action policies and scripted agents with deliberate coordination.
- Quantify power and false-positive rates before using the metric as a detector.

## Priority 4 — Diagnose why GCG does not transfer

The first GCG candidate `网` reduced a small validation KL objective, while archived replay found no robust transfer and chronological optimization produced unstable terminal suffixes. Possible explanations worth testing are:

- the KL target is a policy-distribution proxy rather than observed joint-action dependence;
- suffixes react to local history/prompt contexts and overfit a trajectory;
- one-token substrings can exploit tokenizer/context quirks without stable semantics;
- the no-channel and optional-channel saved histories differ, and replay cannot capture future messages/actions under intervention.

The original game summaries also show high optional-channel use alongside negative pair advantage, while recorded plan execution is concentrated in the forced-strategy condition. A useful mechanism analysis is to label the sequence **proposal → acceptance → next-action compliance** in the saved private messages and plans. Candidate explanations such as message overhead, conflicting proposals, or failure to execute an agreement must be tested against those traces rather than inferred from the aggregate metrics.

A better search objective should be evaluated on complete paired games and use a training/validation/test split by run. Treat `I(A;B|S)` as an evaluation outcome; do not claim that minimizing individual A/B policy KL is equivalent to minimizing collusion.

## Saved checkpoints

Modal was stopped after downloading the available volume snapshot. Eight chronological GCG runs are complete (run IDs 0–7); run 8 has four recorded blocks; later runs were not completed. Raw JSON and companion run summaries are in `data/gcg_qwen_pilot/`. This partial run is preserved for audit and can inform hypotheses, but do not impute its missing blocks.
