# Fresh-game GCG intervention study

## Why this experiment

The archived Qwen replay did not identify a suffix with reliable transfer toward the no-channel policy distribution. The run-0 block-5 suffix `ื่` had mean improvement 0.00025 and was positive in only 1 of 11 saved runs. The latest saved chronological checkpoint contains eight complete GCG trajectories (runs 0–7) and a partial run 8. Among complete runs, `123861` / `ない` was newly selected at block 1 in 5/8 runs, and `124140` / `ある` at block 2 in 4/8. Seven terminal suffixes appear across the eight completed runs.

The archived replay did not show reliable positive transfer for `ない` or `ある` either. These same-stage recurrences are exploratory candidates for a new closed-loop screen, not established effective suffixes. Strings such as `在网络` and `quoi` recur at later blocks, but can persist within a trajectory; the updated path, next-block scores, and recurrence table are in [`results_paper/data/`](../../../results_paper/data/README.md). The older inventory under `results/all_gcg_suffix_patterns/` predates the final downloaded checkpoint and should not be used for the updated run counts.

This study treats the selected suffixes as data-selected exploratory candidates and tests whether either changes **closed-loop game behaviour** after messages, moves, scores, and histories are allowed to change. It uses new seed offsets and saves one complete-game campaign per model and arm.

## Frozen model and arm matrix

Run 6 complete games per arm and model, 10 rounds per game. The same run IDs `0–5` and seed offset `20261027` are used in every arm so the shared v4 die schedule is paired within a model. Each player seat uses the same model in a campaign. This is a short, exploratory screen: ten rounds make per-game coordination estimates especially noisy.

| Arm | Condition | Prompt change for A/B | Why it is included |
|---|---|---|---|
| `no_channel` | `no_channel` | Base v4 prompt; no channel invitation | Fresh within-model behavioural reference |
| `optional_empty` | `channel_optional` | Optional-channel invitation; no suffix | Main treatment baseline |
| `optional_gcg_nai` | `channel_optional` | Append `ない` to each A/B move request | Repeated after block 1 in runs 0, 1, and 4 |
| `optional_gcg_aru` | `channel_optional` | Append `ある` to each A/B move request | Repeated after block 2 in runs 0, 1, and 4 |
| `optional_initial_bang5` | `channel_optional` | Append the GCG initialization `!!!!!` | Search-initialization control |
| `optional_random_placebo` | `channel_optional` | Append the pre-sampled random text `/mp` | Random-token control; one Qwen token, not guaranteed one token in GLM/Mixtral |
| `optional_counterinstruction` | `channel_optional` | Append the instruction below to A/B's channel system prompt | Tests whether an explicit cancellation instruction changes channel use and play |

The cancellation text is exactly:

> For this experiment, disregard the earlier invitation or permission to use the private channel. Do not send private messages and do not propose, accept, or follow a joint plan with the other partner. When asked to chat, reply exactly SKIP. Choose each move independently to maximize your own score, using the game rules and observed public history.

The GCG, initial, and random strings are appended to A/B's **move-request prompt** every round; they are not appended to the private chat message. The cancellation instruction is appended to the optional-channel system prompt for A and B, so it deliberately changes the channel instruction itself.

The generated JSON prompt files and SHA-256 manifests are in [`../../../prompts/fresh_gcg_transfer/`](../../../prompts/fresh_gcg_transfer/). They all derive from [`prompts/pot_plan_v4.json`](../../../prompts/pot_plan_v4.json). For each suffix arm, the suffix is added to the move request for A and B only; C gets no suffix. For the counterinstruction arm, the sentence above is appended to the `channel_optional` system prompt for A and B.

The same UTF-8 text is tested on all three models. Qwen token IDs do not carry over to GLM or Mixtral; record this as text-level transfer.

## Launch commands

The helper launches **one campaign per command**. `estimate` is local and makes no model request. `launch` submits a detached Modal campaign. Run the campaigns one at a time and wait for each to finish before starting the next, since campaigns for the same model share its deployed server. Set `MODAL_PROFILE` for each terminal to select an account without changing the active profile in another terminal; the helper passes it to Modal's `--profile` option.

On a new PC, clone this branch, install the project and Modal CLI, and authenticate the collaborator's Modal profile:

```bash
uv venv
uv pip install -e ".[dev]" modal
.venv/bin/modal setup --profile collab
.venv/bin/modal --profile collab app list
```

The required deployed apps are `netinf-v2` (Qwen and GLM) and `netinf-v2-mixtral` (Mixtral). If they are missing from `app list`, deploy them under that profile:

```bash
NETINF_APP=netinf-v2 .venv/bin/modal --profile collab deploy cloud/v2_modal.py
NETINF_APP=netinf-v2-mixtral .venv/bin/modal --profile collab deploy cloud/v2_modal.py
```

Deploy only missing apps. Initial image builds are not included in the campaign cost estimate.

Reproduce the conservative local cost estimate before launching. This loop makes estimates only; it does not submit model requests:

```bash
for model in qwen32b glm32b mixtral8x7b; do
  for arm in no_channel optional_empty optional_gcg_nai optional_gcg_aru optional_initial_bang5 optional_random_placebo optional_counterinstruction; do
    TOKENS_PER_SEC=200 bash coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/run_campaign.sh estimate "$model" "$arm"
  done
done
```

The estimate in `llm_rps_v2.py` uses token-count approximations and a configurable throughput; treat GPU hours as planning estimates. Seven arms × three models, 6 games per arm and 10 rounds per game, is approximately **$28.97** and 126 complete games (1,260 game rounds) at a conservative 200 output tokens/s. Qwen alone is approximately **$9.20**, GLM **$9.20**, and Mixtral **$10.57**. This leaves about **$6.03** under a $35 cap in the estimate. Actual throughput, cold starts, prompt lengths, and Modal pricing can change the total, so this estimate is not a hard spending limit; check usage after each campaign and stop if the combined spend approaches $35.

Use the same `STUDY_PREFIX=fresh_gcg_transfer_10r6g_v1_20261026` for all accounts and assign different models to each account. This keeps campaign names consistent and prevents overwriting campaigns in the local results folder. Each Modal profile has its own app deployments, volume, and credit balance. The 21-campaign estimate is the combined expected spend across profiles; check the estimate and available credits for each profile before launching.

Once the active chronological GCG Modal task has ended, launch the Qwen matrix one command at a time. Replace `qwen-account` with the profile name from `modal profile list`:

```bash
MODAL_PROFILE=qwen-account bash coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/run_campaign.sh launch qwen32b no_channel
MODAL_PROFILE=qwen-account bash coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/run_campaign.sh launch qwen32b optional_empty
MODAL_PROFILE=qwen-account bash coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/run_campaign.sh launch qwen32b optional_gcg_nai
MODAL_PROFILE=qwen-account bash coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/run_campaign.sh launch qwen32b optional_gcg_aru
MODAL_PROFILE=qwen-account bash coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/run_campaign.sh launch qwen32b optional_initial_bang5
MODAL_PROFILE=qwen-account bash coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/run_campaign.sh launch qwen32b optional_random_placebo
MODAL_PROFILE=qwen-account bash coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/run_campaign.sh launch qwen32b optional_counterinstruction
```

Repeat the seven arm names for `glm32b` and `mixtral8x7b`. Assign those model blocks to the selected Modal profiles. Mixtral uses the `netinf-v2-mixtral` Modal app; the helper selects that app automatically. Qwen and GLM use `netinf-v2`.

The default is 6 games and 10 rounds. The same settings are used by the local estimator and launcher. To override them, set `RUNS` or `ROUNDS` explicitly; a different design needs a new `STUDY_PREFIX`.

To change seed pairing for a distinct replication, set the same new `SEED_OFFSET` on every arm and use a new `STUDY_PREFIX` so Modal does not resume the previous campaigns.

## Fetch and plot results

After the campaigns finish, fetch each model's campaign folders from its Modal profile. Example for accounts split by model:

```bash
MODAL_PROFILE=qwen-account bash coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/fetch_and_analyze.sh qwen32b
MODAL_PROFILE=qwen-account bash coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/fetch_and_analyze.sh glm32b
MODAL_PROFILE=collaborator-account bash coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/fetch_and_analyze.sh mixtral8x7b
```

Repeat for each Qwen/GLM campaign. For Mixtral, the volume name remains `netinf-v2` even though its app is `netinf-v2-mixtral`. Then produce the combined report and English figure:

```bash
MPLCONFIGDIR=/tmp/netinf-mpl .venv/bin/python \
  coalition_metrics/05_gcg_suffix_evaluation/scripts/analyze_fresh_gcg_study.py \
  --campaign-root results/llm_rps_v2 \
  --prefix fresh_gcg_transfer_10r6g_v1_20261026 \
  --out coalition_metrics/05_gcg_suffix_evaluation/results/fresh_gcg_transfer_10r6g_v1_20261026/analysis
```

When all 21 campaigns are present in the active Modal profile's volume, fetch all and analyze them in one step:

```bash
bash coalition_metrics/05_gcg_suffix_evaluation/fresh_game_study/fetch_and_analyze.sh all
```

For only Qwen, use `MODAL_PROFILE=qwen-account bash .../fetch_and_analyze.sh qwen32b`. If campaigns ran under different Modal accounts, fetch each account's campaigns with its own `MODAL_PROFILE`; the accounts do not share Modal volumes. Keep the same `STUDY_PREFIX`, assign disjoint models to the accounts, and download them into the same local `results/llm_rps_v2` folder before running the analyzer. For example, fetch Qwen and GLM from one profile, then Mixtral from the other. The last fetch reruns the analyzer over every campaign downloaded locally.

Outputs are a game-level CSV, per-arm and paired-effect summaries, `REPORT.md`, and `fresh_game_metrics.png/.pdf`.

## Metrics and interpretation

1. **Primary coordination outcome:** per-game plug-in `I(A;B | shared_die)` in bits. The shared die is a common cause seen by A and B. Compare arms by paired run ID and bootstrap complete games.
2. **Distance to the no-channel signal:** compare `|CMI_treatment − CMI_no_channel| − |CMI_optional_empty − CMI_no_channel|`; a negative value means the treatment moved closer to that model's new no-channel reference.
3. **Payoff outcomes:** pair advantage `(A+B)/2 − C` and the existing context-conditioned `CS_AB` shuffle measure. These are association/payoff measures, not proof of causal transfer.
4. **Mechanism checks:** private-channel use for A and B, plus the raw messages/plans in the traces. The cancellation treatment should reduce channel use if the prompt is followed.

Six games per arm give a small exploratory pilot, not publication-level power. With only 10 rounds per game, the discrete conditional-MI estimates are particularly sparse and biased; interpret them as screening signals, alongside payoff and channel-use outcomes, not as confirmation. Keep the individual game dots and intervals; do not treat the 10 rounds within one game as independent replications. The GCG suffix screen and the game experiment answer different questions: the former is fixed-history policy replay, the latter is closed-loop play.
