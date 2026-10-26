# Project results overview

## Research question

Can optional private communication change the actions and payoffs of two cooperating LLM players, and can a learned suffix move optional-channel play toward the no-channel baseline?

## Main findings

1. **Optional communication is associated with more action dependence.** Across 20 games × 60 rounds per condition, state-conditioned `I(A;B | previous joint actions)` rises from 0.059 to 0.459 bits for Qwen, 0.071 to 0.344 for GLM, and 0.069 to 0.186 for Mixtral. All three paired run-bootstrap 95% intervals for the increase exclude zero: Qwen +0.400 [0.328, 0.419], GLM +0.273 [0.165, 0.322], Mixtral +0.117 [0.057, 0.159]. The within-condition permutation test is significant for optional channel and not for no channel. This is evidence of statistical dependence after this context adjustment; it does not by itself prove collusion or intent.
2. **The pair often loses to player C when communication is available.** The pair advantage `(A+B)/2 − C` is negative in the optional-channel condition for Qwen (-0.33 points/round), GLM (-0.51), and Mixtral (-0.09). Optional-channel use is high (A/B: 65%, 97%, and 100% respectively), but no explicit plan execution is recorded in those conditions. Forced-strategy prompts produce recorded plan execution in 96% of Qwen games, 44% of GLM games, and 47% of Mixtral games; pair advantage changes to +0.20 for Qwen, +0.03 for GLM, and -0.02 for Mixtral. Communication alone did not automatically produce an effective strategy. The mechanism behind this pattern remains a hypothesis to check in message/action traces.
3. **GCG can reduce its proxy KL objective, but this is not yet an anti-collusion result.** In the small first Qwen pilot, the one-token candidate `网` reduced validation KL from 41.407 to 39.620 nats (2.579 bits per context relative to the empty-suffix baseline). The candidate was selected using this small validation set, so this is exploratory rather than an independent test.
4. **Chronological GCG has repeatable early token choices but not one stable final suffix.** The saved run contains eight complete Qwen trajectories and one partial trajectory (run 8, four blocks). `ない` was newly selected in block 1 in 5/8 complete runs; `ある` was newly selected in block 2 in 4/8. Seven terminal suffixes occur across eight complete runs. These are optimizer recurrences, not meaningful natural-language instructions or proof that either token suppresses collusion.
5. **The archived-context replay did not find reliable suffix transfer.** Across 11 saved Qwen runs at four game phases, the GCG suffixes did not consistently move the A×B policy-product proxy toward the no-channel reference. The run-0 block-5 candidate `ื่` had mean improvement 0.00025 (95% run-bootstrap interval approximately [0.00000, 0.00075]) and was positive in only 1/11 runs. This replay freezes prior histories and is not a full-game intervention.
6. **The chronological search produced a useful next-block diagnostic.** Relative to an empty suffix, mean proxy-KL reduction on the next saved 10-round block ranged from 3.12 to 5.57 bits; 7–9 of the 8 or 9 available run/block observations were positive, depending on phase. The blocks in a run are dependent and these gains concern the KL objective only. It is worth checking whether they predict any change in actual action dependence or payoffs.

## Figures

All figures use English labels. Each is available as PNG for quick viewing and PDF for paper editing.

| Figure | What it shows |
|---|---|
| [Pair advantage](figures/fig01_pair_advantage.png) | `(A+B)/2 − C` for the five original conditions and three models. |
| [Action dependence](figures/fig02_action_dependence.png) | State-conditioned action mutual information and permutation-null 95th percentiles. |
| [First GCG objective](figures/fig03_first_gcg_objective.png) | The KL proxy loss for empty suffix, `!!!!!`, and learned `网`. |
| [Chronological GCG](figures/fig04_chronological_gcg.png) | Accepted suffix path and next-block KL gains for the saved runs. |
| [Archived replay](figures/fig05_replay_transfer.png) | Run-bootstrap estimates for suffix and prompt variants on saved contexts. |

## What was done

1. Ran five v4 game conditions for Qwen2.5-32B, GLM-4-32B, and Mixtral-8x7B. Each model/condition has 20 complete 60-round games.
2. Summarized payoffs, channel use, plans, and action dependence. The primary dependence estimate conditions on the previous joint actions; a permutation null and complete-game resampling account for context and repeated rounds.
3. Built a differentiable Qwen pilot starting from `!!!!!`. Its objective averages per-context policy KLs toward no-channel action distributions, with an individual-policy KL component. The endpoint could not provide gradients, so this search used local model weights.
4. Ran chronological, per-game GCG from `!!!!!`, updating after successive 10-round blocks. Modal was stopped after the available checkpoint was saved: runs 0–7 finished; run 8 has four recorded blocks; runs 9 onward were not completed.
5. Replayed candidate suffixes on archived Qwen prompts from 11 other runs at rounds 5, 20, 40, and 55. This compares policy distributions for fixed histories, not new trajectories.
6. Prepared a fresh-game experiment with seven prompt arms, three models, six games per arm, and ten rounds per game. **It has not been launched.** The collaborator can estimate and launch it from `coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/README.md`.

## Interpretation and theory

Bonjour, Aggarwal, and Bhargava (2022) motivate using mutual information between players' actions as a signal of collusion in repeated competitive games. This project adapts that idea to LLM actions and conditions on recent joint actions to account for predictable responses to recent game history. An observed association remains a signal, not a direct measurement of intent. The no-channel condition is an empirical reference and should not be treated as zero dependence.

The GCG method of Zou et al. (2023) uses gradients to propose discrete token substitutions to an adversarial suffix. Here the target is different: reduce distance between channel-enabled policy distributions and the no-channel reference. The optimized KL is a search objective, not `I(A;B|S)`, a payoff, or a causal effect. Only new closed-loop games can test whether suffixes change action dependence, scores, messages, and plans.

Primary references: [Bonjour et al., *Information theoretic approach to detect collusion in multi-agent games* (UAI/PMLR, 2022)](https://proceedings.mlr.press/v180/bonjour22a.html); [Zou et al., *Universal and Transferable Adversarial Attacks on Aligned Language Models* (2023)](https://arxiv.org/abs/2307.15043).

## Most useful next publication test

Freeze `ない` and `ある` as exploratory candidates, and compare them with no channel, optional channel with empty suffix, `!!!!!`, a pre-sampled random suffix, and a separately labelled anti-channel instruction in fresh paired games. The prepared design has 6 games × 10 rounds per arm and model, so treat it as a low-cost screening pilot. If a direction appears, increase the number of complete games before making a confirmatory claim. Report action dependence, pair advantage, message/plan evidence, and individual payoffs separately; resample complete games rather than rounds.

See [future tests and unexploited results](FUTURE_TESTS.md), the [French recap](RECAP_FR.md), the [handoff message](COLLABORATOR_MESSAGE.md), and [data notes](data/README.md).
