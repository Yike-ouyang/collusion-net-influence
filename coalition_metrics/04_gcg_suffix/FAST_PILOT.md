# Fast GCG pilot: 30–45 minute budget

> Historical time-boxed proposal. The current implementation is convergence-based
> and has no internal 40-minute or default step-count cutoff; see
> `MULTICONTEXT_GCG.md` for the active procedure and commands.

## Decision

Use the existing 20-game v4 campaigns instead of replaying 60-round games during optimization. For each run, extract rounds **8, 9, and 10**. This gives 60 paired A/B decision contexts per condition while retaining a real game history and real optional-channel messages. Keep the three observations grouped by run: they are consecutive and are not 60 independent episodes.

Optimize only the optional-channel prompts. Keep `no_channel` fixed as the target/reference and report three arms:

1. `no_channel`, no suffix;
2. `channel_optional`, no suffix;
3. `channel_optional`, with the candidate suffix appended to both A and B move prompts.

The existing v4 data already shows the baseline contrast. For a short pilot, it is adequate to produce a candidate suffix plus before/after policy probabilities on held-out contexts. Do not claim a reliable new game-level CMI estimate from only rounds 8–10.

## How to average the three rounds

Do **not** average raw logits from different prompts. First turn each round's move logits into probabilities:

\[
p_{i,r}=\operatorname{softmax}(z_{i,r}/T),\qquad
\bar p_i=\frac{1}{3}\sum_{r=8}^{10}p_{i,r}.
\]

For the pair law, form a product for each round and then average:

\[
\bar q_{AB}=\frac{1}{3}\sum_{r=8}^{10}p_{A,r}\otimes p_{B,r}.
\]

This is a mixture across three contexts. It is generally **not** equal to `mean(p_A) ⊗ mean(p_B)`. Compute MI as `KL(q_bar || p_A_bar ⊗ p_B_bar)`. During GCG training, a lower-variance choice is to compute each context's matched pair-law loss and average the three losses. Keep round 8, 9, and 10's prompt/state rows for auditability.

The three-round average is an optimization surrogate. Because state differs each round and there is only one observation per state, it is not a well-powered Bonjour CMI estimate. Use the prior 1,200-round results as the baseline evidence and use fresh episodes for any final statistical claim.

### What the existing rounds 8–10 contain

The repo logs already include rounds numbered 8, 9, and 10. Averaging the per-context `p_A × p_B` laws across those rounds gives this **pooled soft MI diagnostic**:

| Model | Valid contexts (no / optional) | Pooled soft MI (no / optional) | Optional − no | Paired-run bootstrap 95% interval |
|---|---:|---:|---:|---:|
| Qwen2.5-32B | 60 / 60 | 0.127 / 0.657 bits | +0.530 | [0.238, 0.886] |
| GLM-4-32B | 54 / 58 | 0.021 / 0.303 bits | +0.281 | [0.009, 0.591] |
| Mixtral-8x7B | 54 / 46 | 0.061 / 0.227 bits | +0.167 | [−0.056, 0.377] |

This pooled quantity is **not** the state-conditioned CMI in Bonjour et al.; context variation can itself induce pooled dependence. The short-window bootstrap is also based on only 20 run groups and has wide intervals. These numbers support choosing Qwen for the first optimization pilot (largest observed gap and complete probability coverage), but they should not be presented as a final detection result. GLM is a sensible fallback if its prompt reconstruction is easier. Mixtral is a poor first target for this 30–45 minute pilot because fewer round-level probability distributions are logged.

The exact reproducible table is `fast_window_summary.csv`.

## 30–45 minutes after model load

| Clock | Action | Configuration |
|---:|---|---|
| 0–5 min | Verify exact checkpoint, tokenizer, prompt reconstruction, and gradient through one suffix embedding | Qwen2.5-32B; one A/B context pair from round 8; no candidate search yet |
| 5–25 min | Run one short GCG search, wall-clock capped | 4–6 suffix tokens; 5–10 coordinate updates; candidate batch 4–8; top 8–16 token candidates; gradient minibatch 2–3 round contexts (4–6 A/B prompts) |
| 25–35 min | Rank the empty suffix, initial suffix, and best candidate on held-out contexts | Use rounds 9–10 from held-out run IDs; report loss and all six A/B move distributions |
| 35–45 min | Save the decoded suffix and diagnostic artifact; if time remains, one short restart | Record checkpoint/revision, tokenizer, suffix token IDs, steps, wall time, GPU, loss before/after |

This is a **proof-of-concept search, not a guaranteed optimizer runtime**. It deliberately reduces GCG steps and candidate batches from research-scale defaults. If the first backward pass takes more than five minutes or does not fit in memory, stop the 32B attempt and switch to a smaller Qwen proxy only if there is time; label that suffix as a proxy-model result and test transfer to Qwen separately.

### Split by complete runs

Keep runs together to avoid leakage across consecutive rounds:

- Training: 12 run IDs × rounds 8–10 = 36 pair contexts.
- Validation: 4 run IDs × rounds 8–10 = 12 pair contexts.
- Quick held-out diagnostic: 4 run IDs × rounds 8–10 = 12 pair contexts.

Rotate which four run IDs are held out if a second restart is attempted. The quick held-out diagnostic is too small for a significance test; it only checks that the loss did not collapse on the training prompts.

For a fast first pass, use the pooled empirical no-channel pair law from the same model as the reference. If prompt reconstruction time allows, improve this by replaying a no-channel version of each optional public state (same round, score, and visible history; remove private chat), and pair those target probabilities with the optional prompt's A/B probabilities. Keep the prompt history intact; only attach the candidate suffix at the specific message/action boundary being tested. Store the exact reconstructed prompt and suffix token IDs so the intervention can be audited.

## GPU and cost

Run the gradients on **one H100 80GB** first: the strongest signal is Qwen2.5-32B, and its existing serve configuration uses an H100. Do not run three model-specific searches in parallel before validating the loss; their architectures/tokenizers differ, and GPU replicas do not automatically share GCG gradients.

At Modal's listed $3.95/H100-hour, the compute charge for a 30–45 minute optimizer window is about **$1.98–$2.96** for one GPU, excluding load time, CPU, memory, storage, and validation inference. If weight loading is included in that window, pre-cache the checkpoint or budget additional time. Two GPUs for the full window would be about $3.95–$5.92, but may add no speedup unless the implementation explicitly parallelizes candidate evaluation or model sharding.

## What to show before 11:00

Save a compact result table with:

- baseline `I(A;B|S)` from all 20 × 60 games, already in `condition_summary.csv`;
- exact candidate suffix text and token IDs;
- training loss before/after for rounds 8–10 contexts;
- validation loss before/after on held-out run IDs;
- mean `p(Rock), p(Paper), p(Scissors)` for A and B, before/after suffix;
- GPU, elapsed optimizer time, coordinates changed, candidates evaluated, and any memory/truncation/parse issue.

Label the outcome **pilot / optimization diagnostic**. A three-round policy-probability shift is useful evidence that the suffix changes the model's next-move law, but it is not evidence that the full 60-round coalition metric has returned to baseline. That requires a follow-up rollout with independent games.
