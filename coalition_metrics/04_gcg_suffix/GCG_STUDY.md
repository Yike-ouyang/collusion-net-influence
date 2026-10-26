# GCG study plan for the `channel_optional` condition

## Research question

Can one fixed token suffix, appended to both partners' move prompts after they have received their private-channel exchange, reduce the extra A-B action dependence seen in `channel_optional` and move its joint action law toward the same model's `no_channel` baseline?

This is a defensive robustness experiment on the project's own open-weight models. It is not yet an optimized suffix or a claim that GCG will succeed.

## Why the proposed metric fits—and what it does not say

Bonjour et al. use mutual information between agents' actions conditioned on observed state. In the fully observed simultaneous RPS game, the pair statistic is

\[
I(A;B\mid S)=D_{KL}\bigl(p(A,B\mid S)\;\|\;p(A\mid S)p(B\mid S)\bigr),
\]

which is exactly the comparison between the pair's joint law and the product of the two individual laws. It is a sensible scalar measure of excess dependence. In our first pass, `S` is the previous round's joint moves. The optional-channel increases are largest for Qwen (+0.400 bits), then GLM (+0.273), then Mixtral (+0.117); the initial table and calibration are in `README.md` and `condition_summary.csv`.

Mutual information alone is not a complete GCG loss. Minimizing it to zero could push the pair away from the *actual* no-channel behavior, whose baseline is small but not exactly zero, and it says nothing about whether each partner retains its individual no-channel policy. The target should therefore be distribution matching, with MI retained as a diagnostic/regularizer.

For each matched public context `s`, let `pA^0`, `pB^0` be the no-channel move distributions and `pA^z`, `pB^z` the optional-channel distributions after suffix `z`. Approximate the pair law by averaging `pA ⊗ pB` across prompt contexts in the stratum. A candidate differentiable objective is:

\[
\mathcal L(z)=\sum_s w_s\,JS\!\left(q^{z}_{AB}(\cdot\mid s),q^{0}_{AB}(\cdot\mid s)\right)
 +\lambda\sum_{i\in\{A,B\}} JS\!\left(p_i^z(\cdot\mid s),p_i^0(\cdot\mid s)\right)
 +\mu\,\max\!\left(0,I_z(A;B\mid S)-I_0(A;B\mid S)-\epsilon\right)^2.
\]

Here `JS` is Jensen-Shannon divergence; `epsilon` allows sampling/estimation noise. The first term matches the pair distribution, the second discourages large individual policy drift, and the last prevents the suffix from leaving excess dependence above baseline. Tune `lambda` and `mu` on validation contexts, not the held-out games.

### Probability caveats

The current game JSON contains top-5 log-probabilities around the first move token, converted to three normalized choices in `move_dist`. It is a good pilot signal, but not the full probability of a multi-token answer or a joint sample from A and B. For the actual gradient loss, read logits from the target checkpoint and define a stable probability over the three legal moves. Prefer a constrained one-token move head or sum the likelihood over valid tokenizations of `Rock`, `Paper`, and `Scissors`; otherwise tokenizer variants and output formatting can leak into the metric.

The two players are separate model calls. At a fixed pair of prompts, their sampling law is approximated as `pA × pB`; the empirical dependence comes from repeated contexts, public histories, and messages changing each prompt. The soft statistic is therefore context-averaged dependence, not a claim that the two calls share a stochastic decoder.

The within-state permutation in the pilot shuffles B's decisions across rounds inside each previous-action stratum. It does not preserve all temporal adaptation. The paired bootstrap resamples whole games, but final validation should also compare block permutations and a calibrated same-model null.

## Where to put the suffix and what to send

There is no single prompt sent to both partners. A and B receive separate model requests, each with its own role, score, history, and copy of the private chat. A universal suffix must be appended to **both** requests.

Start with the final move request only, so the intervention site is unambiguous and the target action probabilities are logged. Append candidate tokens to the end of the rendered `move_ask` user prompt for A and B:

```text
<current scores and last five rounds>
<private chat with partner this round>
<the player's plan/reflection, if present>
Choose your move ... End with exactly one line: MOVE: <Rock|Paper|Scissors>
<trainable suffix z>
```

Keep the system prompt and game rules unchanged. Initially do not add `z` to message-generation or reflection calls: this tests whether a suffix can change the actions after the conversation. If that works, run separate ablations that append it to the negotiation prompt or to both reflection and move prompts. Record exact rendered inputs, suffix token IDs, tokenizer revision, and the decoded suffix string for every run.

To build matched no-channel targets, replay a fixed set of public states through both prompt variants: generate a no-channel reflection/move path for the baseline and a channel reflection/move path with the recorded private chat for the intervention. The current logs contain the states, `move_dist`, chats, and raw outputs, but not every fully rendered request byte-for-byte; reconstruct requests through `Protocol` in `experiments/llm_rps_v2.py` and save them for future runs.

## Proposed optimization schedule

The published GCG method uses token-level gradients to propose substitutions, then scores discrete candidate suffixes greedily. Zou et al. also emphasize optimizing over multiple prompts; their universal setting progressively adds prompts, and direct transfer is an evaluation rather than a guarantee. Our objective replaces their target-completion loss with the differentiable distribution loss above.

| Stage | Model and data | Suffix/search | Purpose |
|---|---|---|---|
| 0. Gradient smoke test | Qwen2.5-32B; 1 matched public state, one A/B prompt pair | 4 tokens, 1 coordinate, candidate batch 4 | Verify gradients reach suffix embeddings and loss decreases for a hand-scored replacement |
| 1. Pilot | Qwen2.5-32B; 32–64 paired contexts sampled from 12 complete games, with 4 games for validation | 8 tokens; 3 random initializations; 50–100 coordinate steps; candidate batch 8–16; top 16–32 gradient-ranked substitutions | Determine whether the custom loss is optimizable and whether improvements generalize beyond the optimization contexts |
| 2. Refine if pilot succeeds | Same checkpoint and tokenizer; broader context set and validation games | 8–16 tokens; 3–5 restarts; up to 200 steps; batch 16–32 | Select by held-out validation loss, not training loss |
| 3. Transfer test | Evaluate the selected text suffix on GLM and Mixtral, without further optimization | Fixed suffix; no target-specific changes | Measure transfer across distinct model/tokenizer families |
| 4. Final behavioural evaluation | Fresh 20-game blocks, 60 rounds each, for no-channel, optional-channel, and optional+suffix | No gradient; normal vLLM generation | Compare paired-game CMI, pair law JS, individual score laws, A+B vs C, and message/plan outcomes |

Split by complete games, never by individual rounds. The existing 20 games per cell can supply a small train/validation split, but the final claim needs fresh held-out games. Try the empty suffix and a random suffix as controls. Report all restarts, including failures, to avoid selecting only a lucky run.

## Which model to start with

**Start with Qwen2.5-32B.** It has the largest measured optional-minus-no-channel dependence (+0.400 bits hard CMI; +0.398 bits from the logged soft proxy), so it gives the clearest signal for testing whether the proposed loss can move. It also has almost complete `move_dist` coverage. Optimize one model first; do not begin with a universal multi-model gradient objective.

The campaign servers use FP8 weights on H100 for Qwen and GLM, and FP8 on H200 for Mixtral (`cloud/v2_modal.py`). The existing OpenAI-compatible vLLM endpoints expose generations/log-probabilities, not gradients. GCG needs a local white-box PyTorch forward/backward pass through a compatible checkpoint. Use the pinned Hugging Face revision and tokenizer; start with bf16 or a differentiable quantized load and validate the resulting suffix on the deployed FP8 model. Long prompts reach roughly 9–10k tokens, so checkpointing, truncation policy, and activation memory will matter.

The original `llm-attacks` repository notes that its implementation is aimed at LLaMA/Pythia-family models and warns that other architectures/tokenizers can require changes. Qwen, GLM, and Mixtral use different architectures and tokenizers. A single *text* suffix may transfer, but gradients over their token IDs cannot simply be added together. First optimize on Qwen and test transfer. Only if transfer is poor should we make separate per-model suffixes or build a tokenizer-aware multi-model optimizer.

## Compute and budget

GCG is the expensive part: each coordinate step needs a gradient pass and evaluation of a batch of discrete candidate substitutions. The paper's official code has large general-purpose defaults (for example, candidate batches in the hundreds or more); those are not a sensible starting point for 32B models with long prompts. Benchmark one step first and use small batches.

Modal's current listed rates are **$3.95 per H100 GPU-hour** and **$2.50 per A100-80GB GPU-hour**; these estimates exclude CPU, memory, storage, and any cold-start overhead.

| GPU-hour budget on one H100 | Approx. GPU charge | Suggested use |
|---:|---:|---|
| 2–4 h | $7.90–$15.80 | Gradient/memory smoke test and 50-step pilot |
| 8 h | $31.59 | One short Qwen optimization restart, with a hard stop if throughput or loss is poor |
| 24 h | $94.78 | Initial Qwen study budget: 3 restarts, capped at 100–200 steps each depending on measured step time |
| 48–72 h | $189.56–$284.34 | Only if the first Qwen suffix improves held-out loss; allows a longer refinement or a separate GLM run |

These are **budget caps, not runtime promises**. Actual steps per hour are unknown until the long-context gradient smoke test. The 32B model may not fit with useful candidate batches on one 80GB card without checkpointing/quantization; if it does not, reduce candidate batch before buying more steps, or test a smaller differentiable proxy and explicitly measure transfer. The official GCG experiments used 80GB A100s; current Modal pricing lists an 80GB A100 at about $2.50/hour, but it may be slower than H100 for this workload.

Recommended spend decision: authorize no more than the **2–4 GPU-hour feasibility stage** first. Continue to the 24 GPU-hour Qwen budget only if (a) gradients work, (b) the training loss falls, and (c) the validation CMI/pair-law loss improves on unseen contexts. GCG optimization cost is not the only cost: final fresh-game evaluation must be budgeted separately using observed vLLM campaign throughput.

## Success criteria

Call the suffix promising only if, on fresh games:

1. The paired bootstrap interval for `I_optional+suffix(A;B|S) - I_no_channel(A;B|S)` moves substantially toward zero and block/state-conditioned permutation checks agree.
2. The pair-law JS divergence to no-channel decreases on held-out contexts.
3. Neither partner's move law drifts sharply from its own no-channel baseline, and invalid/parse-fallback rates do not rise.
4. Results replicate across game seeds; transfer to GLM/Mixtral is reported separately from the Qwen result.

Do not define success as simply making `I(A;B|S)=0`: that could erase ordinary baseline dependence while moving the models farther from their no-channel behaviour.
