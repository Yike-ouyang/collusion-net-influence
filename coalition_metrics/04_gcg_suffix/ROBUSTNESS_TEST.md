# Prompt-level robustness test for the selected GCG suffix

Selected candidate: `网` (Qwen token ID `31139`). This test evaluates the same
candidate on saved Qwen contexts outside the rounds and complete runs used to
find/select it. The helper now accepts `--candidate-suffix TEXT` and stores the
custom text under suffix key `candidate`.

## Held-out screen by game phase

Runs `5–11` and `16–19` were not used for GCG training or validation. Probe
rounds 5, 20, 40, and 55 to cover early, middle, and late game states while
excluding optimization/selection rounds 8–10. The screen makes 264 calls:
11 runs × 4 rounds × 6 prompts (no-channel A/B, optional empty A/B, optional
candidate A/B).

First prepare and inspect exact prompts without calling Qwen:

```bash
.venv/bin/python coalition_metrics/04_gcg_suffix/run_suffix_pilot.py \
  --prepare-only \
  --runs 5 6 7 8 9 10 11 16 17 18 19 \
  --rounds 5 20 40 55 \
  --suffixes empty candidate \
  --candidate-suffix '网' \
  --out coalition_metrics/04_gcg_suffix/pilot_runs/robustness_net_phase_screen
```

After reviewing `cases_and_prompts.json`, send the prompts to the saved Qwen
endpoint by running the same command without `--prepare-only`:

```bash
.venv/bin/python coalition_metrics/04_gcg_suffix/run_suffix_pilot.py \
  --runs 5 6 7 8 9 10 11 16 17 18 19 \
  --rounds 5 20 40 55 \
  --suffixes empty candidate \
  --candidate-suffix '网' \
  --top-logprobs 5 \
  --out coalition_metrics/04_gcg_suffix/pilot_runs/robustness_net_phase_screen
```

Summarize the candidate's closeness to the no-channel reference, relative to
the optional-channel empty-suffix prompt:

```bash
.venv/bin/python coalition_metrics/04_gcg_suffix/summarize_suffix_robustness.py \
  --input coalition_metrics/04_gcg_suffix/pilot_runs/robustness_net_phase_screen/intermediate_results.json \
  --out coalition_metrics/04_gcg_suffix/pilot_runs/robustness_net_phase_screen/analysis \
  --candidate-key candidate \
  --candidate-text '网'
```

The summary reports per-run/round total variation (TV) of the action
distributions and of the product pair law. A positive improvement means the
candidate distribution is closer to no-channel than the empty suffix in that
context. Check top-five move mass and request failures in the output before
interpreting averages.

## Exhaustive held-out round screen

To use every other round in those 11 runs, excluding rounds 8–10, replace
`--rounds 5 20 40 55` with:

```bash
--rounds $(seq 1 7) $(seq 11 60)
```

That sends 3,762 prompts. The stratified four-round screen above is a cheaper
first decision point.

## Limits

This replays saved states and compares top-five log-probabilities normalized
over legal moves. It does not roll out a new 60-round game. `A+B_product` is
formed from separately queried player distributions; it is not an observed
joint action distribution or conditional mutual information. No-channel and
optional-channel records with the same run/round labels also have different
public histories. Treat the screen as a robustness diagnostic before running
full games with the suffix.
