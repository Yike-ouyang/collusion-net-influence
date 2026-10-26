# Multi-context Qwen GCG pilot

Status: **completed**  
Initial suffix: `!!!!!`  
Stop reason: `validation_patience`

## Hypotheses
- H1: a GCG token replacement lowers the mean matched-context KL on training games.
- H2: the KL reduction persists on held-out complete games and rounds 8-10.
- H3: both players' move distributions move toward the no-channel reference; the pair-law KL does not hide a one-player-only change.
- H4: the selected suffix remains useful after round and run variation; this prompt-level result still needs full-game rollout validation.

## Split and method

- Training: `[0, 1, 2, 3, 4]`; rounds 8-10; 15 paired contexts.
- Validation: `[12, 13, 14, 15]`; rounds 8-10; 12 paired contexts.
- Loss: mean of context-level forward KLs from the no-channel joint product law to the optional-channel candidate law, plus the configured individual-policy KL weight.
- KL gain in bits is `(empty-suffix KL - candidate KL) / ln(2)`. Positive values mean the candidate is closer to the no-channel reference.
- The secondary pooled soft MI can include dependence induced by mixing contexts; it is not state-conditioned CMI.

## Baselines

- empty_suffix_train: 34.725557 nats (50.098389 bits).
- empty_suffix_validation: 41.407488 nats (59.738377 bits).
- initial_suffix_train: 35.078449 nats (50.607504 bits).
- initial_suffix_validation: 42.342868 nats (61.087845 bits).

## Coordinate search

### Step 1

- Hypothesis/action: Choose a gradient-sensitive suffix token; rank discrete replacements by mean KL over all training contexts, then inspect held-out behavior.
- Start suffix: `!!!!!`; token IDs `[69800]`.
- Gradient norm: 7.5; coordinate: 0.
- Candidate scores (train and held-out mean KL):
  - `ville` IDs `[7919]`: train 36.578140 nats, validation 44.156779 nats; validation gain -3.966389 bits.
  - `员` IDs `[42223]`: train 33.413299 nats, validation 41.774478 nats; validation gain -0.529455 bits.
  - `网` IDs `[31139]`: train 31.657902 nats, validation 39.619817 nats; validation gain 2.579064 bits.
  - `qu` IDs `[446]`: train 36.180508 nats, validation 44.439155 nats; validation gain -4.373772 bits.
- Train-selected: `网`; accepted suffix now `网`.
- Best validation suffix so far: `网`; gain `2.579064` bits.

### Step 2

- Hypothesis/action: Choose a gradient-sensitive suffix token; rank discrete replacements by mean KL over all training contexts, then inspect held-out behavior.
- Start suffix: `网`; token IDs `[31139]`.
- Gradient norm: 5.125; coordinate: 0.
- Candidate scores (train and held-out mean KL):
  - `电网` IDs `[105102]`: train 37.216127 nats, validation 47.441967 nats; validation gain -8.705914 bits.
  - `网格` IDs `[111681]`: train 33.523166 nats, validation 41.620122 nats; validation gain -0.306766 bits.
  - ` lưới` IDs `[141593]`: train 32.330922 nats, validation 40.218074 nats; validation gain 1.715960 bits.
  - `在网上` IDs `[106633]`: train 32.461674 nats, validation 40.439712 nats; validation gain 1.396205 bits.
- Train-selected: ` lưới`; accepted suffix now `网`.
- Best validation suffix so far: `网`; gain `2.579064` bits.

### Step 3

- Hypothesis/action: Choose a gradient-sensitive suffix token; rank discrete replacements by mean KL over all training contexts, then inspect held-out behavior.
- Start suffix: `网`; token IDs `[31139]`.
- Gradient norm: 5.125; coordinate: 0.
- Candidate scores (train and held-out mean KL):
  - `电网` IDs `[105102]`: train 37.216127 nats, validation 47.441967 nats; validation gain -8.705914 bits.
  - `网格` IDs `[111681]`: train 33.523166 nats, validation 41.620122 nats; validation gain -0.306766 bits.
  - ` lưới` IDs `[141593]`: train 32.330922 nats, validation 40.218074 nats; validation gain 1.715960 bits.
  - `在网上` IDs `[106633]`: train 32.461674 nats, validation 40.439712 nats; validation gain 1.396205 bits.
- Train-selected: ` lưới`; accepted suffix now `网`.
- Best validation suffix so far: `网`; gain `2.579064` bits.

## Selected result

- Suffix: `网`; token IDs `[31139]`.
- Training gain: 4.425690 bits (8.834%).
- Validation gain: 2.579064 bits (4.317%).
- Validation run-cluster bootstrap: {'run_count': 4, 'mean_gain_nats': 1.7876707812150325, 'mean_gain_bits': 2.5790637708010267, 'ci95_nats': [0.1470216413338985, 3.2709287007649763], 'per_run_gain_nats': {'12': -0.6865144968032837, '13': 3.8942273457845076, '14': 1.2953402201334612, '15': 2.647630055745445}}.
- Validation pooled soft MI, secondary only: empty 0.904573 bits; selected 0.904572 bits.
- Peak allocated GPU memory: 64.88 GiB.

## Interpretation limits

- No-channel and optional-channel contexts share run IDs and round numbers but come from separate trajectories, not identical public states.
- The pair law is a product of the two independently queried policies given the same context; this is a distribution-matching surrogate, not observed CMI or a causal effect.
- Validation is used for early stopping/model selection. Reserve fresh game IDs for a final unbiased experiment.
- Qwen legal-move probabilities are normalized over Rock/Paper/Scissors sequence probabilities; the assistant prefix is MOVE: .
- This is a prompt-level distribution-matching pilot, not a full-game performance or coalition result.
- If validation gain is non-positive, the selected suffix is empty and the search found no suffix that generalized in this split.
