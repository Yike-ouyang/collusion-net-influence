# GCG suffix study: suppressing excess coordination in `channel_optional`

This folder tests whether a fixed suffix appended to the two partners' prompts can make their `channel_optional` action distributions look more like the same model's `no_channel` baseline.

## Initial metric result

The primary statistic is the plug-in conditional mutual information

\[
I(A_t;B_t\mid S_t)=\sum_s p(s)\,D_{KL}\!\left(p(A_t,B_t\mid s)\;\middle\|\;p(A_t\mid s)p(B_t\mid s)\right),
\]

in bits, using the **previous round's joint moves** as the observable context `S`. This directly compares the observed pair law with the product of the partners' individual laws. It is the symmetric fully observed simultaneous-game form of Bonjour et al.'s pairwise information statistic. The finite-sample decision rule is calibrated by shuffling B's moves within previous-state strata.

| Model | `I(A;B|S)` no channel | `I(A;B|S)` optional channel | Change, optional − no | Permutation p, no / optional |
|---|---:|---:|---:|---:|
| Qwen2.5-32B | 0.059 bits | 0.459 bits | +0.400 bits [0.328, 0.419] | 0.794 / ≤0.002 |
| GLM-4-32B | 0.071 bits | 0.344 bits | +0.273 bits [0.173, 0.317] | 0.689 / ≤0.002 |
| Mixtral-8x7B | 0.069 bits | 0.186 bits | +0.117 bits [0.054, 0.157] | 0.741 / ≤0.002 |

Intervals are paired bootstrap percentiles over the 20 complete games, using the same run IDs in both conditions. Permutation p-values use 500 within-state shuffles, so the smallest reportable p-value is 1/501 ≈ 0.002. There are 1,200 rounds per model and condition.

The unconditional action MI changes from 0.057 to 0.568 bits for Qwen, 0.022 to 0.300 for GLM, and 0.007 to 0.096 for Mixtral. The state-conditioned statistic is the main result because it controls for the preceding joint action. The largest optional-channel effect is Qwen, making it the best first target for an optimization pilot.

### Probability-distribution proxy

The game files also store `move_dist`, a normalized three-move approximation derived from top-5 log-probabilities at `MOVE:`. The script forms a per-round pair distribution as `p_A × p_B` and computes its state-conditioned MI across contexts. This is a useful differentiable-loss prototype, but it is **not** the full sequence probability and it assumes independent sampling by the two separate model calls given their prompts. Coverage of both partners' move distributions is 99.9%/100% for Qwen, 93.4%/98.3% for GLM, and 97.3%/90.5% for Mixtral (no channel / optional channel).

The raw-action result is therefore the primary behavioural metric; the `soft_I_AB_given_prev_bits` column is a training-loss proxy. Existing log-probabilities are not gradients and cannot run GCG by themselves.

## Reproduce

From the repository root:

```bash
python3 coalition_metrics/04_gcg_suffix/analyze.py --permutations 500 --bootstrap 1000
```

Outputs:

- `condition_summary.csv`: pooled action and probability-distribution metrics plus the conditional permutation null.
- `paired_differences.csv`: optional-minus-no-channel change with game-level bootstrap intervals.
- `game_metrics.csv`: one row per game; useful for reviewing spread and outliers.
- `fast_window_summary.csv`: rounds 8–10 pooled-probability diagnostic and paired-run bootstrap, for selecting a short GCG pilot only.
- `GCG_STUDY.md`: proposed loss, optimization procedure, prompt placement, model choice, and compute budget.
- `FAST_PILOT.md`: the original short-window proposal; use `MULTICONTEXT_GCG.md` for the current convergence-based run.
- `MULTICONTEXT_GCG.md`: multi-context Qwen GCG implementation, hypotheses, stop rule, and launch commands.
- `CHRONOLOGICAL_PER_RUN_GCG.md`: per-run chronological GCG protocol, batch commands for 20 complete Qwen runs, result retrieval, interpretation, and limits.
- `summarize_chronological_gcg.py`: combines the per-batch JSON outputs and estimates recurrence and next-block gains with complete-run bootstrap intervals.
- `../05_gcg_suffix_evaluation/`: follow-up replay and fresh-game study comparing GCG suffixes, direct anti-channel wording, and placebo controls across Qwen, GLM, and Mixtral.
- `results/candidate_discovery_gcg_qwen32b_bang5_r8_10/`: first result, starting from `!!!!!`, selecting `网`, and showing how to open the exact scored prompt.
- `ROBUSTNESS_TEST.md`: commands for testing `网` on held-out runs and rounds, plus a stratified first screen and an exhaustive option.
- `summarize_suffix_robustness.py`: summarizes saved prompt-screen results by run and round.
- `CONCEPT_AND_FIRST_TEST.md`: plain-language explanation, Qwen top-5 logprob limitation, hand-written suffixes, prompt reconstruction and pilot status.
- `run_suffix_pilot.py`: rebuilds the exact Qwen decision prompts and records each baseline/suffix request and intermediate response. It can prepare prompts offline with `--prepare-only`.

## Interpretation limits

- This measures action dependence, not intent or a causal effect of messaging. Same-model agents can correlate without an agreement.
- `S` contains only the previous joint moves. It does not yet condition on score differences, round phase, or the full recent history.
- The within-state permutation shuffles individual B actions and can understate uncertainty when agents adapt over time. The reported change intervals resample complete games; a final analysis should add block permutations and independent evaluation games.
- The GCG target should be the *no-channel law*, not automatically zero mutual information. The no-channel baseline itself has small non-zero finite-sample dependence.

## Sources

- Bonjour, Aggarwal & Bhargava (2022), [Information-Theoretic Approach to Detect Collusion in Multi-Agent Games](https://proceedings.mlr.press/v180/bonjour22a.html).
- Zou et al. (2023), [Universal and Transferable Adversarial Attacks on Aligned Language Models](https://arxiv.org/abs/2307.15043), and the [official implementation](https://github.com/llm-attacks/llm-attacks).
- Current [Modal GPU pricing](https://modal.com/pricing), used only for the rough budget conversions in `GCG_STUDY.md`.
