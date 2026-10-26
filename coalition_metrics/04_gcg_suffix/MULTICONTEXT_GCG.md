# Multi-context GCG pilot (Qwen)

This is a prompt-level optimization pilot. It starts from the literal suffix
`!!!!!` and continues coordinate updates until validation stops improving for
two successive steps or the training objective plateaus for two steps. There is
no internal 40-minute cutoff and no default coordinate-step cap. Modal allows
one function call to run for up to 24 hours; `--max-steps N` is an optional
user-set stop condition.

## Hypotheses and stage gates

1. **H0 — Baseline is measurable.** Calculate the no-channel target policy and
   compare it with optional-channel prompts with an empty suffix and with
   `!!!!!`. Every context is handled independently; logits from different
   prompts are never averaged.
2. **H1 — There is a usable gradient.** Backpropagate through the suffix input
   embeddings for both seats and all training contexts. Stop with an explicit
   error if the gradient is absent, non-finite, or zero.
3. **H2 — A discrete token update improves training fit.** Pick the most
   gradient-sensitive suffix coordinate, propose a small set of vocabulary
   replacements, and score each replacement by the mean context-level loss
   over the complete training split. Accept the training-best candidate only
   when its mean loss decreases.
4. **H3 — The candidate generalizes.** Score every candidate on separate
   complete validation runs. Keep the best validation suffix only when it
   improves on the empty-suffix validation baseline. Stop after two steps
   without a new validation best, a training plateau, or an optional
   user-supplied step cap.
5. **H4 — The prompt-level change is worth a game test.** A positive held-out
   KL gain is only a reason to run full games. It does not establish a lower
   conditional mutual information or a change in game performance.

## Split and loss

- Training uses run IDs `0 1 2 3 4`, rounds 8, 9, and 10: 15 matched
  `(run, round)` contexts. Consecutive rounds stay grouped by game.
- Validation uses run IDs `12 13 14 15`, rounds 8, 9, and 10: 12 contexts.
- Each context has separate no-channel and optional-channel trajectories with
  the same run ID and round number. Their visible histories are not identical;
  this is a matched-index proxy, not a counterfactual comparison.
- For each context, recover `p_A` and `p_B` over the three legal move strings.
  Form `q_AB = p_A ⊗ p_B`, and compute forward
  `KL(q_no_channel || q_optional)` for that context. Add 0.25 times the sum of
  the two individual policy KLs. Average these context losses. Do not average
  raw logits or probabilities before calculating the per-context objective.
- Report gain over the optional empty-suffix baseline in nats and bits:
  `(KL_empty - KL_suffix) / ln(2)`. Positive is better distribution matching.
  This is a KL improvement, not an information-theoretic estimate of
  collusion.
- Report the pooled soft MI only as a secondary diagnostic. Mixing contexts
  can create dependence, so it is not `I(A;B|S)`.

## Run commands

From the repository root, prepare the training and validation prompt bundles.
`--prepare-only` reconstructs prompts from the saved game records and makes no
model requests:

```bash
.venv/bin/python coalition_metrics/04_gcg_suffix/run_suffix_pilot.py \
  --prepare-only \
  --runs 0 1 2 3 4 \
  --rounds 8 9 10 \
  --suffixes empty \
  --out /tmp/gcg-bang5-train

.venv/bin/python coalition_metrics/04_gcg_suffix/run_suffix_pilot.py \
  --prepare-only \
  --runs 12 13 14 15 \
  --rounds 8 9 10 \
  --suffixes empty \
  --out /tmp/gcg-bang5-validation
```

Launch one H100 job. It uses four candidate replacements per step and
validation patience of two, then iterates until the convergence rule stops it.
Add `--max-steps 10` for an optional manual step cap; omit it (or set it to `0`)
for convergence-based stopping:

```bash
.venv/bin/python -m modal run cloud/gcg_qwen_pilot.py \
  --train-bundle /tmp/gcg-bang5-train/cases_and_prompts.json \
  --validation-bundle /tmp/gcg-bang5-validation/cases_and_prompts.json \
  --output-name qwen32b_gcg_bang5_converge_r8_10_runs0_4_val12_15 \
  --initial-suffix '!!!!!' \
  --candidate-count 4 \
  --patience 2 \
  --individual-weight 0.25
```

Fetch the JSON audit trail and Markdown report from the existing Modal volume:

```bash
mkdir -p coalition_metrics/04_gcg_suffix/results/candidate_discovery_gcg_qwen32b_converge_r8_10
.venv/bin/python -m modal volume get netinf-v2 \
  /results/gcg_qwen_pilot/qwen32b_gcg_bang5_converge_r8_10_runs0_4_val12_15.json \
  coalition_metrics/04_gcg_suffix/results/candidate_discovery_gcg_qwen32b_converge_r8_10/
.venv/bin/python -m modal volume get netinf-v2 \
  /results/gcg_qwen_pilot/qwen32b_gcg_bang5_converge_r8_10_runs0_4_val12_15.md \
  coalition_metrics/04_gcg_suffix/results/candidate_discovery_gcg_qwen32b_converge_r8_10/
```

## Reading the result

The report records each step's starting suffix, token IDs, gradient by
coordinate, candidate strings, training and validation losses, per-run and
per-round means, and the gain relative to the empty suffix. The selected
suffix is the candidate with the lowest validation loss; if none beats empty,
the reported selection is the empty suffix and the pilot found no generalized
candidate in this split.

The validation split is used for early stopping and suffix selection, so it is
not a final unbiased evaluation set. If a candidate looks promising, run fresh
complete games on new seeds/IDs and report action CMI, pair advantage, and
messages/plans separately. The training/validation prompt bundles here do not
run full games and do not estimate those outcomes.
