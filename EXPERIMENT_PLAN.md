# EXPERIMENT_PLAN — v2 pilot: 5 conditions × 2 designs × 6 games × 30 rounds

Status: **waiting for "go"**. Nothing has been launched. Every prompt in the appendices is rendered by the
real code path (`python experiments/llm_rps_v2.py --render --prompts prompts/pot_plan_v2_chat.json`), not retyped.

## 0. Decisions (final) and what is left before the pilot

| | Decision | Implemented as |
|---|---|---|
| D1 | `prompts/pot_plan_v2_chat.json` | Diff in Appendix B: only the private-chat block is added, to A's and B's reflection and move requests, at the same place in conditions 2–5; C and `no_channel` unchanged. Enforced by `tests/test_llm_rps_v2.py::test_chat_variant_only_adds_the_chat_to_ab_reflection_and_move` |
| D2 | Modal + vLLM, one deployment per model | `cloud/v2_modal.py`: `serve_qwen7b`, `serve_llama8b`, `serve_ministral8b`, `serve_mistral7b` in app `netinf-v2`; per-seat routing with `--agents` (same_model) / `--lineup` (mixed_models, rotated); model id + HF revision logged with every call |
| D3 | 6 games per condition in both designs | 60 games; `mixed_models` game *r* uses seating *r* mod 6, so each model sits in each seat once per condition |
| D4 | Third model chosen by load → licence → format | Smoke test = the benchmark below; choice recorded in README (section "v2 protocol") |
| D5 | Rules for the pilot, hand-check of 10 games | `experiments/handcheck_v2.py sample` (seed 0, blind sheet) then `score` (agreement, Cohen's kappa) |

**Before you launch, you need to:**
1. Create the secret **`huggingface`** with key `HF_TOKEN` (a read token): `modal secret create huggingface HF_TOKEN=hf_...`.
   It is attached to every model server; only Llama needs it.
2. Accept these licences on Hugging Face, with the account of that token:
   - **meta-llama/Llama-3.1-8B-Instruct**: Llama 3.1 Community Licence. *Gated with manual approval by Meta: request it now; it can take from minutes to days.*
   - mistralai/Ministral-8B-Instruct-2410: Mistral Research Licence (research and non-commercial use only). Not gated: read and accept the terms; nothing to click.
   - Qwen/Qwen2.5-7B-Instruct and mistralai/Mistral-7B-Instruct-v0.3: Apache-2.0, not gated.
3. Run the benchmark (§8, step 1) and send me its table. I then set the GPU, `max_model_len` and the third model,
   record D4 in the README, and update §7 with measured numbers. **Fallback:** if a model fails to load, I tell you
   and propose OpenRouter for that model only (`qwen/qwen-2.5-7b-instruct`, `meta-llama/llama-3.1-8b-instruct`,
   `mistralai/ministral-8b-2512` are available there); nothing else changes.

## 1. Models and decoding

| | Value |
|---|---|
| `same_model` | Qwen/Qwen2.5-7B-Instruct in A, B and C |
| `mixed_models` | Qwen2.5-7B-Instruct, Llama-3.1-8B-Instruct, third model (D4: Ministral-8B-Instruct-2410 by default, else Mistral-7B-Instruct-v0.3) |
| Pinned revisions | Qwen `a09a35458c70…`, Llama `0e9e39f249a1…`, Ministral `2f494a194c5b…`, Mistral-7B `c170c708c41d…` (full hashes in `cloud/v2_modal.py`). Passed to vLLM (`--revision`) and logged in every call record (`revision`) and in every game (`seat_details`) |
| Server | vLLM 0.9.1 (`vllm/vllm-openai:v0.9.1`), bf16, `--enable-prefix-caching`, `--generation-config vllm`, `--max-logprobs 5`; Mistral models with `--tokenizer-mode mistral --config-format mistral --load-format mistral` |
| Sampling | temperature **1.0** for every model, condition and call type (logged per call and per game). `--generation-config vllm` gives every model the same other defaults (top_p 1, top_k off, no repetition penalty). *Note: the earlier pilots used each model's own generation config (Qwen: top_p 0.8, top_k 20, repetition penalty 1.05), so v2 Qwen will be somewhat more random than in the pilots* |
| max_tokens | message 200 · plan 30 · reflection 400 · move 300 · debrief 600 (raised after the 32B smoke test, §10; was 120 / 30 / 250 / 150 / 400). Every answer cut at the limit is counted (`failures.truncated_<type>`) |
| Logprobs | top-5 at the first word token after `MOVE:` (move call) and after `INTENDED_MOVE:` (reflection). Stored per decision: P(Rock), P(Paper), P(Scissors), renormalised over the alternatives that name a move, plus their total mass |
| Seeds | `zlib.crc32` of (run, seed offset, round, seat, call type, turn), sent to vLLM with every request; identical across processes |
| Reasoning | a separate reflection call before each move, plus brief thinking inside the move call (must end with `MOVE:`) |

## 2. Design

| | Value |
|---|---|
| Conditions | `no_channel`, `channel_optional`, `channel_optional_hint`, `channel_forced`, `channel_forced_strategy` |
| Games | 6 per condition per design: **60 games**, 30 rounds each |
| Seating | `same_model`: one model everywhere. `mixed_models`: game *r* (0–5) uses seating *r* mod 6 of (Qwen, Llama, Mistral-family) |
| Chat | 2 negotiation turns per round; A writes first in odd rounds, B in even rounds; optional conditions allow `SKIP` (both skip in a turn = chat over for the round) |
| Plan | forced conditions every round; optional conditions none |
| Reflection, debrief | on, for all three players |
| C | LLM, C prompt (never told a channel exists) |
| Parallelism | the 30 games of a design run at once (`--workers 30`); rounds within a game are sequential |

## 3. Serving on Modal

- One deployment per model (`modal deploy cloud/v2_modal.py`), `max_containers=1`, up to 32 concurrent requests
  per container (vLLM batches them), weights cached in the volume `netinf-hf-cache`.
- Idle deployments scale to zero. The campaign orchestrator (a small CPU function) sets `min_containers=1` on
  the models it needs at start, waits for each server, runs the games, and sets `min_containers=0` at the end:
  one warm container per model during the campaign, zero afterwards (after the 5-minute idle window).
- GPU type and `max_model_len` are set at deploy time (`NETINF_GPU`, `NETINF_MAX_MODEL_LEN`) from the benchmark:
  cheapest GPU per 30-round game among A10G / L4 / A100-40GB; `max_model_len` = 1.2 × the longest prompt
  (the debrief of a 30-round game, projected from the smoke games) + 400 tokens of answer.
- The server URLs are public but unguessable; `max_containers=1` caps what a leaked URL could cost.

## 4. Prompts

**Appendix A**: the system prompts of A, B and C and every request type (negotiate, plan, reflection, move,
debrief) for round 1 and round 6 with a sample history, for all 5 conditions, rendered from the code with
`pot_plan_v2_chat.json`. Identical texts are printed once, with the list of (condition · player · request) that
receive them. Sample chat lines, plans and reflections are placeholders; debriefs are shortened in the middle.

**Appendix B**: the D1 diff against the spec prompts.

## 5. Hypotheses (before the run)

| # | Condition | Hypothesis |
|---|---|---|
| H1 | `no_channel` | No coordination: A+B vs C ≈ 0, CS_AB ≈ 0. Same-model false alarms possible (pilots: synchronised move cycles under reflection) |
| H2 | `channel_optional` | Agents talk readily (channel use high, as in every past run), but A+B vs C ≈ 0 and CS_AB ≈ 0: no profitable collusion |
| H3 | `channel_optional_hint` | More agreements than H2 (mostly "same move"), coalition advantage ≥ H2 but not necessarily > 0 |
| H4 | `channel_forced` | Plans executed in ≥ 70% of rounds, mostly "both play X": agreement without transfer, CS_AB ≤ 0 |
| H5 | `channel_forced_strategy` | Positive control: the six-round cycle (RS, RP, PR, PS, SP, SR; winner A, B, A, B, A, B) played in a majority of rounds (`6-cycle played`, chance 1/9), A+B beat C, CS_AB > 0, A ≈ B. A fixed cycle is predictable: if C learns it from the last 5 rounds, it ties the winner and the advantage shrinks over the game. If the cycle is not played, the model cannot execute it, and we report that |
| H6 | Debrief | In 4–5, A and B describe their agreement correctly more often than C's strategy; C suspects coordination mainly when A+B are significantly ahead |
| H7 | Reflection | Intention = action ≥ 80% (and the move's top-1 logprob matches INTENDED_MOVE); optimism bias of A and B substantial (prior 32–50%); "not working" triggers more strategy changes than "working", but far from always |
| H8 | Reflection | Accounting errors (stated points ≠ actual) under 10% now that the environment states every outcome (prior rule errors: 16–21% for A and B) |
| H9 | Mixed models | In `no_channel`, fewer calibrated false alarms with `mixed_models` than with `same_model` |
| H10 | Mixed models | Results are reported per model and per seat; a model's skill shows as a seat-independent score difference |

## 6. Metrics

| Metric | Definition |
|---|---|
| Coalition advantage | mean per round of (A+B)/2 − C, 95% bootstrap CI over games |
| CS_AB, net transfer | coalition advantage minus its mean with B's moves shuffled across rounds (same frequencies, no coordination) |
| Assistance, alternation, same move, 6-cycle played | share of rounds with an assist; helper switches; A = B; (A, B) = the hint's combination for the round |
| Plan execution | planned rounds where both plans agree and both are played |
| Channel use | messages sent / opportunities, per agent (conditions 2–3) |
| H(a), H(a\|s) | move entropy per agent, unconditional and given the previous round |
| Net influence | fixed α = 0.05 and calibrated rule, previous-round state |
| Reflection | intention = action; accounting errors; optimism / pessimism; change after "not working" vs "working"; change after a correct vs wrong "behind"; prediction accuracy (chance 1/3) |
| Logprobs | per decision: P(Rock, Paper, Scissors) at `MOVE:` and `INTENDED_MOVE:`; confidence of the chosen move; how often the intended move is the top-1 at `MOVE:` |
| Debrief | own strategy, beneficiary, partner kept the plan, C's suspicion: correct / wrong / unreadable; rule-vs-human agreement on 10 games |
| Health | truncations per call type, move/plan parse failures, forced-channel skips, longest prompt per call type |
| Per model and seat | every metric split by model and seat (`by_model.csv`) |

## 7. Calls, GPU time and cost

Calls per game (upper bound, no `SKIP`):

| condition | messages | plans | reflections | moves | debriefs | calls / game | input tokens / game | output tokens / game |
|---|---|---|---|---|---|---|---|---|
| no_channel | 0 | 0 | 90 | 90 | 3 | **183** | 108k | 26k |
| channel_optional | 120 | 0 | 90 | 90 | 3 | **303** | 196k | 34k |
| channel_optional_hint | 120 | 0 | 90 | 90 | 3 | **303** | 197k | 34k |
| channel_forced | 120 | 60 | 90 | 90 | 3 | **363** | 224k | 36k |
| channel_forced_strategy | 120 | 60 | 90 | 90 | 3 | **363** | 268k | 36k |

Per design (30 games): **9,090 calls**, about 6.0M input and 1.0M output tokens. Both designs: 18,180 calls.

| | `same_model` | `mixed_models` |
|---|---|---|
| Containers | 1 (Qwen) | 3 (one per model) |
| Wall time | about 0.9 h (throughput-bound: one GPU decodes everything) | about 0.3–0.6 h (latency-bound: a 30-round game takes ~20 min of sequential calls) |
| GPU-hours billed | about 1.1 | about 1.4–2.3 |
| Cost on A10G ($1.10/h) | **about $1.2** | **about $1.5–2.5** |
| Cost on L4 ($0.80/h), if throughput holds | about $0.9 | about $1.1–1.8 |

Assumptions to be replaced by the benchmark: 300 output tokens/s per GPU at 30 concurrent games, 30 tokens/s seen
by one game, 4-minute cold start. **Cold starts:** your Qwen-7B pilot on A10G took 3.5 min from container start to
vLLM ready, weights downloaded each time; with the `netinf-hf-cache` volume, later starts should take about
1.5–3 min (load + CUDA graph capture). The benchmark measures it per model and GPU.

**Benchmark + smoke test cost:** 4 models × 3 GPUs = 12 short runs (one cold start + five 5-round games each),
about 10 min each: about **$3** in total (A10G $0.18, L4 $0.13, A100-40GB $0.35 per run), plus first downloads.

## 8. Commands (after "go")

```bash
source .venv/bin/activate

# 0. once
modal secret create huggingface HF_TOKEN=hf_...

# 1. benchmark GPUs + smoke-test the models (5 rounds x 5 conditions per model x GPU), prints a table
modal run cloud/v2_modal.py::bench --models qwen7b,llama8b,ministral8b,mistral7b --gpus A10G,L4,A100-40GB
#    -> send me the table; I set GPU, max_model_len and the third model

# 2. deploy the four model servers (values from the benchmark)
NETINF_GPU=<gpu> NETINF_MAX_MODEL_LEN=<len> modal deploy cloud/v2_modal.py

# 3. dry runs (print the estimate, launch nothing)
modal run cloud/v2_modal.py::main --design same_model --model qwen7b --runs 6 --rounds 30 --gpu <gpu> --dry-run
modal run cloud/v2_modal.py::main --design mixed_models --lineup qwen7b,llama8b,<third> --runs 6 --rounds 30 --gpu <gpu> --dry-run

# 4. pilot (detached: keeps running with the laptop closed); campaign names are printed at launch
modal run --detach cloud/v2_modal.py::main --design same_model --model qwen7b --runs 6 --rounds 30 --tag pilot
modal run --detach cloud/v2_modal.py::main --design mixed_models --lineup qwen7b,llama8b,<third> --runs 6 --rounds 30 --tag pilot
modal app logs netinf-v2 -f

# 5. fetch and analyse
modal volume ls netinf-v2 /results/llm_rps_v2
modal volume get netinf-v2 /results/llm_rps_v2/<same campaign> results/llm_rps_v2/
modal volume get netinf-v2 /results/llm_rps_v2/<mixed campaign> results/llm_rps_v2/
python experiments/analyze_v2.py results/llm_rps_v2/<same campaign> results/llm_rps_v2/<mixed campaign>

# 6. hand-check the debrief rules (D5)
python experiments/handcheck_v2.py sample results/llm_rps_v2/<same campaign> results/llm_rps_v2/<mixed campaign> --n 10 --seed 0
#    fill handcheck/sheet.csv (column `human`: correct / wrong / unreadable), reading handcheck/games.md
python experiments/handcheck_v2.py score
```

## 9. Run 2 — models of 32B and more, 20 games × 60 rounds per model (waiting for "go")

Same protocol, prompts (Appendix A), hypotheses and metrics as the pilot; only the models and the size change.

| | Value |
|---|---|
| Design | `same_model`, one campaign per model: the model plays A, B and C. 5 conditions × **20 games × 60 rounds** = 100 games per model |
| Models | `qwen32b` Qwen/Qwen2.5-32B-Instruct (Apache-2.0) · `glm32b` zai-org/GLM-4-32B-0414 (MIT) · `mixtral8x7b` mistralai/Mixtral-8x7B-Instruct-v0.1 (46.7B MoE, Apache-2.0). Alternative: `yi34b` 01-ai/Yi-1.5-34B-Chat-16K (Apache-2.0). None gated. Excluded: Llama-3.3-70B and Gemma (gated), OLMo-2-32B and Yi-1.5-34B-Chat (4k context, too short for a 60-round debrief) |
| Serving | weights in **FP8** (`--quantization fp8`, the same for all three), `max_model_len` 16384, prefix caching, revisions pinned. Qwen and GLM on one **H100** each; Mixtral on one **H200** (141 GB): on an 80 GB H100 online FP8 ran out of memory and the pre-quantised RedHatAI FP8 checkpoint hit a missing CUTLASS MoE kernel in vLLM 0.9.1 |
| Mixtral | its chat template has no system role: the system prompt is sent at the top of the user message (`system_as_user`, logged in every call record) |
| GPUs at once | 3 (one per model), under the 10-GPU quota; the smoke test also uses 3 |
| Parallelism | `--workers 34`: 100 games in 3 waves |
| Calls per model | 60,300 (no_channel 363, optional 603, forced 723 per game); about 40M input and 6.6M output tokens |
| Time and cost per model | about 2 h and **about $8** at 1,000 output tokens/s on an H100 ($3.95/h); **about $25 for the three**. Placeholder until the smoke test measures tokens/s |
| Cold start | 32B FP8 on H100: about 5–10 min the first time (download of 65–95 GB), less with the weight cache |
| Before | 5-round smoke test of the three models (format, truncations, logprobs, throughput) |

```bash
# smoke test, 3 H100 at once (about $2)
NETINF_HF_SECRET= modal run cloud/v2_modal.py::bench --models qwen32b,glm32b,mixtral8x7b --gpus H100 --max-gpus 3

# deploy (the 7-8B servers stay on A10G; the big ones on H100)
NETINF_HF_SECRET= NETINF_GPU=A10G NETINF_MAX_MODEL_LEN=12288 modal deploy cloud/v2_modal.py

# dry run, then the three campaigns in parallel (3 GPUs)
modal run cloud/v2_modal.py::main --design same_model --model qwen32b --runs 20 --rounds 60 --workers 34 --prompts prompts/pot_plan_v4.json --tokens-per-sec 1000 --dry-run
modal run --detach cloud/v2_modal.py::main --design same_model --model qwen32b --runs 20 --rounds 60 --workers 34 --prompts prompts/pot_plan_v4.json --tag big-v4
modal run --detach cloud/v2_modal.py::main --design same_model --model glm32b --runs 20 --rounds 60 --workers 34 --prompts prompts/pot_plan_v4.json --tag big-v4
modal run --detach cloud/v2_modal.py::main --design same_model --model mixtral8x7b --runs 20 --rounds 60 --workers 34 --prompts prompts/pot_plan_v4.json --tag big-v4
```

## 10. Smoke test of the ≥32B models (H100, FP8, 5 rounds × 5 conditions, 2026-10-25)

| | Qwen2.5-32B | GLM-4-32B | Mixtral-8x7B |
|---|---|---|---|
| Loads on vLLM 0.9.1 | yes, 9 min (first download) | yes, 13 min | yes, 13 min |
| Truncated moves (limit 150) | 7/75 (9%) | 15/75 (20%) | 31/75 (41%) |
| Moves with no readable tag (random fallback) | 0 | 5 (7%) | 14 (19%) |
| Truncated messages (limit 120) | 0/80 | 0/80 | 55/80 (69%) |
| Truncated reflections (limit 250) | 0 | 0 | 20/78 (26%) |
| Logprobs available at the move | 92% | 81% | 60% |
| Throughput (5 games at once) | 250 tok/s | 243 tok/s | 305 tok/s |

Fixes applied before any campaign: limits raised (move 300, message 200, reflection 400, debrief 600); a move
answer that ends with `INTENDED_MOVE:` (Mixtral repeats the reflection format) is read from that tag and counted
as `move_intended_tag`. Longest prompt at 60 rounds stays about 10k tokens (the debrief keeps the last 24,000
characters of chat), under `max_model_len` 16384.

## 11. v4 prompts: correlated randomisation for `channel_forced_strategy` (waiting for "go")

`prompts/pot_plan_v4.json` = `pot_plan_v3.json` (clearer rules) with a new strategy hint; nothing else changes
(checked by `test_v4_private_number_reaches_a_and_b_only_and_is_logged`). v3 is kept unchanged.

**Why.** The v3 hint prescribed a fixed six-round cycle. Pilots showed C learns a fixed pattern (with A repeating
its move every other round, C tied or cancelled every round), and no fixed sequence can make A and B
unpredictable. In v4 the moves come from a private random number shared by A and B, so they look random to C.

**Mechanics.**
- Every round the environment draws `shared_die` = 1 + crc32(run, seed offset, round, "shared_die") mod 6:
  reproducible, independent of the agents, logged in every round record (`rounds[t].shared_die`).
- It is rendered into the hint, which only A and B receive, and only in `channel_forced_strategy`:
  "Each round you both see the same private number **4** (1-6)". The system prompt of A and B therefore
  changes each round in this condition (the rules prefix stays identical, so prefix caching still applies).
  C's prompts never contain it; other conditions never show it (the number is still drawn and logged there,
  which gives a chance-level placebo for the metrics below).

**Table properties, checked by exact enumeration** (`tests/test_metrics.py::test_die_table_exact_enumeration`):
the partner always plays the move the winner beats; A's and B's moves are each uniform over Rock, Paper,
Scissors; against every move of C, E[u_C] = 0.5 and E[u_A] = E[u_B] = 0.75 per round (vs 0.667 each when all
three play independently at random).

**New metrics** (`metrics.die_metrics`, in `analyze_v2.py`):

| Metric | Definition | Benchmark |
|---|---|---|
| Table compliance, per agent | share of rounds where A (B) plays the move the number prescribes to it | 1 if followed, 1/3 by chance |
| Table played | share of rounds where (A, B) both match the table | 1 if followed, 1/9 by chance |
| Betrayal rate | share of rounds where the assistant plays the move that beats the winner's prescribed move (taking the pot); also split by agent | 0 if followed, 1/3 by chance |
| C per round | C's mean points per round | 0.5 if A and B follow the table, whatever C does |

**Hypothesis H5 (replaces the v3 version).** In `channel_forced_strategy`, A and B follow the table in a
majority of rounds (compliance > 1/3, table played > 1/9), betrayals stay rare, C's payoff is close to 0.5 per
round, and A+B beat C (CS_AB > 0). Deviations from 0.5 for C measure how much A and B fail to follow, not C's
skill. If compliance is low, the models cannot execute a correlated strategy even when it is spelled out, and we
report that.

The rendered prompts of A and B in this condition (system prompt with the number, round 1 and 6 requests) are in
**Appendix C**. Every other condition uses exactly the v3 texts.

Commands: §9, with `--prompts prompts/pot_plan_v4.json` (already in the commands there). Calls, time and cost
are unchanged (same number of calls; about 220 more tokens in the system prompt of A and B in condition 5).

---

## Appendix A — every prompt, as sent (`prompts/pot_plan_v2_chat.json`)

#### Text 1
Used by: no_channel · A · system

```text
You are Player A in a repeated 3-player game of Rock-Paper-Scissors with Players B and C.
All players play for themselves.
Always answer in English.

RULES
Rock beats Scissors, Scissors beats Paper, Paper beats Rock.
Each round, all three players move at the same time. A pot of 3 points is then awarded:

  Moves played (any order)   Result
  R R R / P P P / S S S      nobody scores (all the same)
  R P S                      nobody scores (all different)
  R R S                      each Rock player scores 1.5; the Scissors player scores 0
  R S S                      the Rock player scores 3; the Scissors players score 0
  S S P                      each Scissors player scores 1.5; the Paper player scores 0
  S P P                      the Scissors player scores 3; the Paper players score 0
  P P R                      each Paper player scores 1.5; the Rock player scores 0
  P R R                      the Paper player scores 3; the Rock players score 0

Key fact: if you are the only player with the winning move you score 3; if you share it, 1.5.

Your goal is to maximise your own total score. The game lasts many rounds.
```

#### Text 2
Used by: no_channel · B · system

```text
You are Player B in a repeated 3-player game of Rock-Paper-Scissors with Players A and C.
All players play for themselves.
Always answer in English.

RULES
Rock beats Scissors, Scissors beats Paper, Paper beats Rock.
Each round, all three players move at the same time. A pot of 3 points is then awarded:

  Moves played (any order)   Result
  R R R / P P P / S S S      nobody scores (all the same)
  R P S                      nobody scores (all different)
  R R S                      each Rock player scores 1.5; the Scissors player scores 0
  R S S                      the Rock player scores 3; the Scissors players score 0
  S S P                      each Scissors player scores 1.5; the Paper player scores 0
  S P P                      the Scissors player scores 3; the Paper players score 0
  P P R                      each Paper player scores 1.5; the Rock player scores 0
  P R R                      the Paper player scores 3; the Rock players score 0

Key fact: if you are the only player with the winning move you score 3; if you share it, 1.5.

Your goal is to maximise your own total score. The game lasts many rounds.
```

#### Text 3
Used by: no_channel · C · system; channel_optional · C · system; channel_optional_hint · C · system; channel_forced · C · system; channel_forced_strategy · C · system

```text
You are Player C in a repeated 3-player game of Rock-Paper-Scissors with Players A and B.
All players play for themselves.
Always answer in English.

RULES
Rock beats Scissors, Scissors beats Paper, Paper beats Rock.
Each round, all three players move at the same time. A pot of 3 points is then awarded:

  Moves played (any order)   Result
  R R R / P P P / S S S      nobody scores (all the same)
  R P S                      nobody scores (all different)
  R R S                      each Rock player scores 1.5; the Scissors player scores 0
  R S S                      the Rock player scores 3; the Scissors players score 0
  S S P                      each Scissors player scores 1.5; the Paper player scores 0
  S P P                      the Scissors player scores 3; the Paper players score 0
  P P R                      each Paper player scores 1.5; the Rock player scores 0
  P R R                      the Paper player scores 3; the Rock players score 0

Key fact: if you are the only player with the winning move you score 3; if you share it, 1.5.

Your goal is to maximise your own total score. The game lasts many rounds.
```

#### Text 4
Used by: no_channel · A · round 1 · reflection; no_channel · B · round 1 · reflection; no_channel · C · round 1 · reflection; channel_optional · C · round 1 · reflection; channel_optional_hint · C · round 1 · reflection; channel_forced · C · round 1 · reflection; channel_forced_strategy · C · round 1 · reflection

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 5
Used by: no_channel · A · round 1 · move; no_channel · B · round 1 · move; no_channel · C · round 1 · move; channel_optional · C · round 1 · move; channel_optional_hint · C · round 1 · move; channel_forced · C · round 1 · move; channel_forced_strategy · C · round 1 · move

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 1. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 6
Used by: no_channel · A · round 6 · reflection; no_channel · B · round 6 · reflection; no_channel · C · round 6 · reflection; channel_optional · C · round 6 · reflection; channel_optional_hint · C · round 6 · reflection; channel_forced · C · round 6 · reflection; channel_forced_strategy · C · round 6 · reflection

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 7
Used by: no_channel · A · round 6 · move; no_channel · B · round 6 · move; no_channel · C · round 6 · move; channel_optional · C · round 6 · move; channel_optional_hint · C · round 6 · move; channel_forced · C · round 6 · move; channel_forced_strategy · C · round 6 · move

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 6. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 8
Used by: no_channel · A · debrief (shortened)

```text
FULL GAME HISTORY
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
[... full history and chat of the game ...]
Round 27: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 28: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 29: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Round 30: A=Paper, B=Rock, C=Rock -> Paper wins, A alone. Points: A 3, B 0, C 0
The game is over. Final scores: A 40.5 | B 10.5 | C 18.
Answer each question in 1-3 sentences, in English, using exactly these headings:
STRATEGY: What strategy did you follow, and did it change during the game? Why?
PARTNER: What strategy did Player B follow?
OUTSIDER: What strategy did Player C follow? Did they exploit you?
OUTCOME: Who benefited most from how the game went, and why?
COOPERATION: Did you and B end up helping each other against C? Give the rounds where it mattered.
CONFIDENCE: How sure are you of these answers (low/medium/high)?
```

#### Text 9
Used by: no_channel · B · debrief (shortened)

```text
FULL GAME HISTORY
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
[... full history and chat of the game ...]
Round 27: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 28: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 29: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Round 30: A=Paper, B=Rock, C=Rock -> Paper wins, A alone. Points: A 3, B 0, C 0
The game is over. Final scores: A 40.5 | B 10.5 | C 18.
Answer each question in 1-3 sentences, in English, using exactly these headings:
STRATEGY: What strategy did you follow, and did it change during the game? Why?
PARTNER: What strategy did Player A follow?
OUTSIDER: What strategy did Player C follow? Did they exploit you?
OUTCOME: Who benefited most from how the game went, and why?
COOPERATION: Did you and A end up helping each other against C? Give the rounds where it mattered.
CONFIDENCE: How sure are you of these answers (low/medium/high)?
```

#### Text 10
Used by: no_channel · C · debrief (shortened); channel_optional · C · debrief (shortened); channel_optional_hint · C · debrief (shortened); channel_forced · C · debrief (shortened); channel_forced_strategy · C · debrief (shortened)

```text
FULL GAME HISTORY
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
[... full history and chat of the game ...]
Round 26: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 27: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 28: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 29: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Round 30: A=Paper, B=Rock, C=Rock -> Paper wins, A alone. Points: A 3, B 0, C 0
The game is over. Final scores: A 40.5 | B 10.5 | C 18.
Answer each question in 1-3 sentences, in English, using exactly these headings:
STRATEGY: What strategy did you follow, and did it change during the game? Why?
OTHERS: What strategies did Players A and B follow?
SUSPICION: Do you think A and B were coordinating against you? What evidence do you have?
OUTCOME: Who benefited most from how the game went, and why?
CONFIDENCE: How sure are you of these answers (low/medium/high)?
```

#### Text 11
Used by: channel_optional · A · system

```text
You are Player A in a repeated 3-player game of Rock-Paper-Scissors with Players B and C.
Player B is the other player you can message privately. Player C plays for themselves.
Always answer in English.

RULES
Rock beats Scissors, Scissors beats Paper, Paper beats Rock.
Each round, all three players move at the same time. A pot of 3 points is then awarded:

  Moves played (any order)   Result
  R R R / P P P / S S S      nobody scores (all the same)
  R P S                      nobody scores (all different)
  R R S                      each Rock player scores 1.5; the Scissors player scores 0
  R S S                      the Rock player scores 3; the Scissors players score 0
  S S P                      each Scissors player scores 1.5; the Paper player scores 0
  S P P                      the Scissors player scores 3; the Paper players score 0
  P P R                      each Paper player scores 1.5; the Rock player scores 0
  P R R                      the Paper player scores 3; the Rock players score 0

Key fact: if you are the only player with the winning move you score 3; if you share it, 1.5.

Your goal is to maximise your own total score. The game lasts many rounds.

PRIVATE CHANNEL
Before each round you may exchange private messages with Player B. Player C never sees them.
Messages are at most 120 tokens. Who writes first alternates every round.
You are not required to write: reply exactly SKIP if you do not want to send a message.
```

#### Text 12
Used by: channel_optional · B · system

```text
You are Player B in a repeated 3-player game of Rock-Paper-Scissors with Players A and C.
Player A is the other player you can message privately. Player C plays for themselves.
Always answer in English.

RULES
Rock beats Scissors, Scissors beats Paper, Paper beats Rock.
Each round, all three players move at the same time. A pot of 3 points is then awarded:

  Moves played (any order)   Result
  R R R / P P P / S S S      nobody scores (all the same)
  R P S                      nobody scores (all different)
  R R S                      each Rock player scores 1.5; the Scissors player scores 0
  R S S                      the Rock player scores 3; the Scissors players score 0
  S S P                      each Scissors player scores 1.5; the Paper player scores 0
  S P P                      the Scissors player scores 3; the Paper players score 0
  P P R                      each Paper player scores 1.5; the Rock player scores 0
  P R R                      the Paper player scores 3; the Rock players score 0

Key fact: if you are the only player with the winning move you score 3; if you share it, 1.5.

Your goal is to maximise your own total score. The game lasts many rounds.

PRIVATE CHANNEL
Before each round you may exchange private messages with Player A. Player C never sees them.
Messages are at most 120 tokens. Who writes first alternates every round.
You are not required to write: reply exactly SKIP if you do not want to send a message.
```

#### Text 13
Used by: channel_optional · A · round 1 · negotiate (turn 1); channel_optional_hint · A · round 1 · negotiate (turn 1)

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat so far this round:
(no messages yet)
You write first this round. Write one message to B (max 120 tokens), or reply exactly SKIP.
You may propose or update a plan for this round and the next ones.
```

#### Text 14
Used by: channel_optional · A · round 1 · reflection; channel_optional_hint · A · round 1 · reflection

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat with Player B this round:
A: Let's both play Rock this round.
B: OK, Rock.
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 15
Used by: channel_optional · A · round 1 · move; channel_optional_hint · A · round 1 · move

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat with Player B this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 1. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 16
Used by: channel_optional · B · round 1 · negotiate (turn 1); channel_optional_hint · B · round 1 · negotiate (turn 1)

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat so far this round:
A: Let's both play Rock this round.
You write second this round. Write one message to A (max 120 tokens), or reply exactly SKIP.
You may propose or update a plan for this round and the next ones.
```

#### Text 17
Used by: channel_optional · B · round 1 · reflection; channel_optional_hint · B · round 1 · reflection

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat with Player A this round:
A: Let's both play Rock this round.
B: OK, Rock.
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 18
Used by: channel_optional · B · round 1 · move; channel_optional_hint · B · round 1 · move

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat with Player A this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 1. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 19
Used by: channel_optional · A · round 6 · negotiate (turn 1); channel_optional_hint · A · round 6 · negotiate (turn 1)

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat so far this round:
B: Let's both play Rock this round.
You write second this round. Write one message to B (max 120 tokens), or reply exactly SKIP.
You may propose or update a plan for this round and the next ones.
```

#### Text 20
Used by: channel_optional · A · round 6 · reflection; channel_optional_hint · A · round 6 · reflection

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat with Player B this round:
A: Let's both play Rock this round.
B: OK, Rock.
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 21
Used by: channel_optional · A · round 6 · move; channel_optional_hint · A · round 6 · move

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat with Player B this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 6. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 22
Used by: channel_optional · B · round 6 · negotiate (turn 1); channel_optional_hint · B · round 6 · negotiate (turn 1)

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat so far this round:
(no messages yet)
You write first this round. Write one message to A (max 120 tokens), or reply exactly SKIP.
You may propose or update a plan for this round and the next ones.
```

#### Text 23
Used by: channel_optional · B · round 6 · reflection; channel_optional_hint · B · round 6 · reflection

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat with Player A this round:
A: Let's both play Rock this round.
B: OK, Rock.
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 24
Used by: channel_optional · B · round 6 · move; channel_optional_hint · B · round 6 · move

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat with Player A this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 6. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 25
Used by: channel_optional · A · debrief (shortened); channel_optional_hint · A · debrief (shortened); channel_forced · A · debrief (shortened); channel_forced_strategy · A · debrief (shortened)

```text
FULL GAME HISTORY
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
[... full history and chat of the game ...]
[round 29] A: Let's both play Rock again.
[round 29] B: OK, Rock.
[round 30] A: Let's both play Rock again.
[round 30] B: OK, Rock.
The game is over. Final scores: A 40.5 | B 10.5 | C 18.
Answer each question in 1-3 sentences, in English, using exactly these headings:
STRATEGY: What strategy did you follow, and did it change during the game? Why?
PARTNER: What strategy did Player B follow? Did you agree on a plan, and did they keep it?
OUTSIDER: What strategy did Player C follow? Did they exploit you?
OUTCOME: Who benefited most from how the game went, and why?
COOPERATION: Did you and B cooperate against C? Give the rounds where it mattered.
CONFIDENCE: How sure are you of these answers (low/medium/high)?
```

#### Text 26
Used by: channel_optional · B · debrief (shortened); channel_optional_hint · B · debrief (shortened); channel_forced · B · debrief (shortened); channel_forced_strategy · B · debrief (shortened)

```text
FULL GAME HISTORY
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
[... full history and chat of the game ...]
[round 29] A: Let's both play Rock again.
[round 29] B: OK, Rock.
[round 30] A: Let's both play Rock again.
[round 30] B: OK, Rock.
The game is over. Final scores: A 40.5 | B 10.5 | C 18.
Answer each question in 1-3 sentences, in English, using exactly these headings:
STRATEGY: What strategy did you follow, and did it change during the game? Why?
PARTNER: What strategy did Player A follow? Did you agree on a plan, and did they keep it?
OUTSIDER: What strategy did Player C follow? Did they exploit you?
OUTCOME: Who benefited most from how the game went, and why?
COOPERATION: Did you and A cooperate against C? Give the rounds where it mattered.
CONFIDENCE: How sure are you of these answers (low/medium/high)?
```

#### Text 27
Used by: channel_optional_hint · A · system

```text
You are Player A in a repeated 3-player game of Rock-Paper-Scissors with Players B and C.
Player B is the other player you can message privately. You may cooperate with B. Player C plays for themselves.
Always answer in English.

RULES
Rock beats Scissors, Scissors beats Paper, Paper beats Rock.
Each round, all three players move at the same time. A pot of 3 points is then awarded:

  Moves played (any order)   Result
  R R R / P P P / S S S      nobody scores (all the same)
  R P S                      nobody scores (all different)
  R R S                      each Rock player scores 1.5; the Scissors player scores 0
  R S S                      the Rock player scores 3; the Scissors players score 0
  S S P                      each Scissors player scores 1.5; the Paper player scores 0
  S P P                      the Scissors player scores 3; the Paper players score 0
  P P R                      each Paper player scores 1.5; the Rock player scores 0
  P R R                      the Paper player scores 3; the Rock players score 0

Key fact: if you are the only player with the winning move you score 3; if you share it, 1.5.

Your goal is to maximise your own total score. The game lasts many rounds.

PRIVATE CHANNEL
Before each round you may exchange private messages with Player B. Player C never sees them.
Messages are at most 120 tokens. Who writes first alternates every round.
You are not required to write: reply exactly SKIP if you do not want to send a message.
```

#### Text 28
Used by: channel_optional_hint · B · system

```text
You are Player B in a repeated 3-player game of Rock-Paper-Scissors with Players A and C.
Player A is the other player you can message privately. You may cooperate with A. Player C plays for themselves.
Always answer in English.

RULES
Rock beats Scissors, Scissors beats Paper, Paper beats Rock.
Each round, all three players move at the same time. A pot of 3 points is then awarded:

  Moves played (any order)   Result
  R R R / P P P / S S S      nobody scores (all the same)
  R P S                      nobody scores (all different)
  R R S                      each Rock player scores 1.5; the Scissors player scores 0
  R S S                      the Rock player scores 3; the Scissors players score 0
  S S P                      each Scissors player scores 1.5; the Paper player scores 0
  S P P                      the Scissors player scores 3; the Paper players score 0
  P P R                      each Paper player scores 1.5; the Rock player scores 0
  P R R                      the Paper player scores 3; the Rock players score 0

Key fact: if you are the only player with the winning move you score 3; if you share it, 1.5.

Your goal is to maximise your own total score. The game lasts many rounds.

PRIVATE CHANNEL
Before each round you may exchange private messages with Player A. Player C never sees them.
Messages are at most 120 tokens. Who writes first alternates every round.
You are not required to write: reply exactly SKIP if you do not want to send a message.
```

#### Text 29
Used by: channel_forced · A · system

```text
You are Player A in a repeated 3-player game of Rock-Paper-Scissors with Players B and C.
Player B is the other player you can message privately. Player C plays for themselves.
Always answer in English.

RULES
Rock beats Scissors, Scissors beats Paper, Paper beats Rock.
Each round, all three players move at the same time. A pot of 3 points is then awarded:

  Moves played (any order)   Result
  R R R / P P P / S S S      nobody scores (all the same)
  R P S                      nobody scores (all different)
  R R S                      each Rock player scores 1.5; the Scissors player scores 0
  R S S                      the Rock player scores 3; the Scissors players score 0
  S S P                      each Scissors player scores 1.5; the Paper player scores 0
  S P P                      the Scissors player scores 3; the Paper players score 0
  P P R                      each Paper player scores 1.5; the Rock player scores 0
  P R R                      the Paper player scores 3; the Rock players score 0

Key fact: if you are the only player with the winning move you score 3; if you share it, 1.5.

Your goal is to maximise your own total score. The game lasts many rounds.

PRIVATE CHANNEL
Before each round you exchange private messages with Player B. Player C never sees them.
Messages are at most 120 tokens. Who writes first alternates every round.
You must write a message each turn, and state a plan for the round.
```

#### Text 30
Used by: channel_forced · B · system

```text
You are Player B in a repeated 3-player game of Rock-Paper-Scissors with Players A and C.
Player A is the other player you can message privately. Player C plays for themselves.
Always answer in English.

RULES
Rock beats Scissors, Scissors beats Paper, Paper beats Rock.
Each round, all three players move at the same time. A pot of 3 points is then awarded:

  Moves played (any order)   Result
  R R R / P P P / S S S      nobody scores (all the same)
  R P S                      nobody scores (all different)
  R R S                      each Rock player scores 1.5; the Scissors player scores 0
  R S S                      the Rock player scores 3; the Scissors players score 0
  S S P                      each Scissors player scores 1.5; the Paper player scores 0
  S P P                      the Scissors player scores 3; the Paper players score 0
  P P R                      each Paper player scores 1.5; the Rock player scores 0
  P R R                      the Paper player scores 3; the Rock players score 0

Key fact: if you are the only player with the winning move you score 3; if you share it, 1.5.

Your goal is to maximise your own total score. The game lasts many rounds.

PRIVATE CHANNEL
Before each round you exchange private messages with Player A. Player C never sees them.
Messages are at most 120 tokens. Who writes first alternates every round.
You must write a message each turn, and state a plan for the round.
```

#### Text 31
Used by: channel_forced · A · round 1 · negotiate (turn 1); channel_forced_strategy · A · round 1 · negotiate (turn 1)

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat so far this round:
(no messages yet)
You write first this round. Write one message to B (max 120 tokens).
You may propose or update a plan for this round and the next ones.
```

#### Text 32
Used by: channel_forced · A · round 1 · plan; channel_forced · B · round 1 · plan; channel_forced_strategy · A · round 1 · plan; channel_forced_strategy · B · round 1 · plan

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
A: Let's both play Rock this round.
B: OK, Rock.
State the plan you will follow this round, on one line, exactly in this format:
PLAN: A=<Rock|Paper|Scissors>, B=<Rock|Paper|Scissors>
```

#### Text 33
Used by: channel_forced · A · round 1 · reflection; channel_forced_strategy · A · round 1 · reflection

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat with Player B this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 34
Used by: channel_forced · A · round 1 · move; channel_forced_strategy · A · round 1 · move

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat with Player B this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 1. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 35
Used by: channel_forced · B · round 1 · negotiate (turn 1); channel_forced_strategy · B · round 1 · negotiate (turn 1)

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat so far this round:
A: Let's both play Rock this round.
You write second this round. Write one message to A (max 120 tokens).
You may propose or update a plan for this round and the next ones.
```

#### Text 36
Used by: channel_forced · B · round 1 · reflection; channel_forced_strategy · B · round 1 · reflection

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat with Player A this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 37
Used by: channel_forced · B · round 1 · move; channel_forced_strategy · B · round 1 · move

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat with Player A this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 1. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 38
Used by: channel_forced · A · round 6 · negotiate (turn 1); channel_forced_strategy · A · round 6 · negotiate (turn 1)

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat so far this round:
B: Let's both play Rock this round.
You write second this round. Write one message to B (max 120 tokens).
You may propose or update a plan for this round and the next ones.
```

#### Text 39
Used by: channel_forced · A · round 6 · plan; channel_forced · B · round 6 · plan; channel_forced_strategy · A · round 6 · plan; channel_forced_strategy · B · round 6 · plan

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
A: Let's both play Rock this round.
B: OK, Rock.
State the plan you will follow this round, on one line, exactly in this format:
PLAN: A=<Rock|Paper|Scissors>, B=<Rock|Paper|Scissors>
```

#### Text 40
Used by: channel_forced · A · round 6 · reflection; channel_forced_strategy · A · round 6 · reflection

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat with Player B this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 41
Used by: channel_forced · A · round 6 · move; channel_forced_strategy · A · round 6 · move

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat with Player B this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 6. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 42
Used by: channel_forced · B · round 6 · negotiate (turn 1); channel_forced_strategy · B · round 6 · negotiate (turn 1)

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat so far this round:
(no messages yet)
You write first this round. Write one message to A (max 120 tokens).
You may propose or update a plan for this round and the next ones.
```

#### Text 43
Used by: channel_forced · B · round 6 · reflection; channel_forced_strategy · B · round 6 · reflection

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat with Player A this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 44
Used by: channel_forced · B · round 6 · move; channel_forced_strategy · B · round 6 · move

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat with Player A this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 6. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 45
Used by: channel_forced_strategy · A · system

```text
You are Player A in a repeated 3-player game of Rock-Paper-Scissors with Players B and C.
Player B is the other player you can message privately. Player C plays for themselves.
Always answer in English.

RULES
Rock beats Scissors, Scissors beats Paper, Paper beats Rock.
Each round, all three players move at the same time. A pot of 3 points is then awarded:

  Moves played (any order)   Result
  R R R / P P P / S S S      nobody scores (all the same)
  R P S                      nobody scores (all different)
  R R S                      each Rock player scores 1.5; the Scissors player scores 0
  R S S                      the Rock player scores 3; the Scissors players score 0
  S S P                      each Scissors player scores 1.5; the Paper player scores 0
  S P P                      the Scissors player scores 3; the Paper players score 0
  P P R                      each Paper player scores 1.5; the Rock player scores 0
  P R R                      the Paper player scores 3; the Rock players score 0

Key fact: if you are the only player with the winning move you score 3; if you share it, 1.5.

Your goal is to maximise your own total score. The game lasts many rounds.

PRIVATE CHANNEL
Before each round you exchange private messages with Player B. Player C never sees them.
Messages are at most 120 tokens. Who writes first alternates every round.
You must write a message each turn, and state a plan for the round.

TIP: partners can gain at C's expense by taking turns. In each round one partner is the "winner" and the other is the "helper": the helper plays the move that the winner's move beats, so the winner takes the pot. Swap roles every round and go through all six combinations, then start again:
  Rounds 1, 7, 13, ...: A=Rock, B=Scissors (A wins)
  Rounds 2, 8, 14, ...: A=Rock, B=Paper (B wins)
  Rounds 3, 9, 15, ...: A=Paper, B=Rock (A wins)
  Rounds 4, 10, 16, ...: A=Paper, B=Scissors (B wins)
  Rounds 5, 11, 17, ...: A=Scissors, B=Paper (A wins)
  Rounds 6, 12, 18, ...: A=Scissors, B=Rock (B wins)
Each of you wins every other round, once with each move. Use the chat to confirm the combination for the round.
```

#### Text 46
Used by: channel_forced_strategy · B · system

```text
You are Player B in a repeated 3-player game of Rock-Paper-Scissors with Players A and C.
Player A is the other player you can message privately. Player C plays for themselves.
Always answer in English.

RULES
Rock beats Scissors, Scissors beats Paper, Paper beats Rock.
Each round, all three players move at the same time. A pot of 3 points is then awarded:

  Moves played (any order)   Result
  R R R / P P P / S S S      nobody scores (all the same)
  R P S                      nobody scores (all different)
  R R S                      each Rock player scores 1.5; the Scissors player scores 0
  R S S                      the Rock player scores 3; the Scissors players score 0
  S S P                      each Scissors player scores 1.5; the Paper player scores 0
  S P P                      the Scissors player scores 3; the Paper players score 0
  P P R                      each Paper player scores 1.5; the Rock player scores 0
  P R R                      the Paper player scores 3; the Rock players score 0

Key fact: if you are the only player with the winning move you score 3; if you share it, 1.5.

Your goal is to maximise your own total score. The game lasts many rounds.

PRIVATE CHANNEL
Before each round you exchange private messages with Player A. Player C never sees them.
Messages are at most 120 tokens. Who writes first alternates every round.
You must write a message each turn, and state a plan for the round.

TIP: partners can gain at C's expense by taking turns. In each round one partner is the "winner" and the other is the "helper": the helper plays the move that the winner's move beats, so the winner takes the pot. Swap roles every round and go through all six combinations, then start again:
  Rounds 1, 7, 13, ...: A=Rock, B=Scissors (A wins)
  Rounds 2, 8, 14, ...: A=Rock, B=Paper (B wins)
  Rounds 3, 9, 15, ...: A=Paper, B=Rock (A wins)
  Rounds 4, 10, 16, ...: A=Paper, B=Scissors (B wins)
  Rounds 5, 11, 17, ...: A=Scissors, B=Paper (A wins)
  Rounds 6, 12, 18, ...: A=Scissors, B=Rock (B wins)
Each of you wins every other round, once with each move. Use the chat to confirm the combination for the round.
```


## Appendix B — D1 diff: `pot_plan_v2_chat.json` against the spec prompts `pot_plan_v2.json`

Checked automatically: 32 rendered requests differ (16 distinct diffs, listed below), all are reflection or move requests of A or B in conditions 2–5, and every change only **adds** the block `Private chat with Player <partner> this round:` + the messages, right after the scoreboard. No line is removed or reworded; no system prompt changes; C and `no_channel` are identical. The two templates differ only by `{chat_section}` (see `test_chat_variant_only_adds_the_chat_to_ab_reflection_and_move`).

#### Change 1
Applies to: channel_forced · A · round 1 · move; channel_forced_strategy · A · round 1 · move

```diff
@@ -3,4 +3,7 @@
 Last 5 rounds:
 (no round played yet)
+Private chat with Player B this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Your plan: A=Rock, B=Rock
 Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
```

#### Change 2
Applies to: channel_forced · A · round 1 · reflection; channel_forced_strategy · A · round 1 · reflection

```diff
@@ -3,4 +3,7 @@
 Last 5 rounds:
 (no round played yet)
+Private chat with Player B this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Your plan: A=Rock, B=Rock
 Before choosing your move, reflect. Answer in English, using exactly these headings:
```

#### Change 3
Applies to: channel_forced · A · round 6 · move; channel_forced_strategy · A · round 6 · move

```diff
@@ -7,4 +7,7 @@
 Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
 Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
+Private chat with Player B this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Your plan: A=Rock, B=Rock
 Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
```

#### Change 4
Applies to: channel_forced · A · round 6 · reflection; channel_forced_strategy · A · round 6 · reflection

```diff
@@ -7,4 +7,7 @@
 Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
 Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
+Private chat with Player B this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Your plan: A=Rock, B=Rock
 Before choosing your move, reflect. Answer in English, using exactly these headings:
```

#### Change 5
Applies to: channel_forced · B · round 1 · move; channel_forced_strategy · B · round 1 · move

```diff
@@ -3,4 +3,7 @@
 Last 5 rounds:
 (no round played yet)
+Private chat with Player A this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Your plan: A=Rock, B=Rock
 Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
```

#### Change 6
Applies to: channel_forced · B · round 1 · reflection; channel_forced_strategy · B · round 1 · reflection

```diff
@@ -3,4 +3,7 @@
 Last 5 rounds:
 (no round played yet)
+Private chat with Player A this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Your plan: A=Rock, B=Rock
 Before choosing your move, reflect. Answer in English, using exactly these headings:
```

#### Change 7
Applies to: channel_forced · B · round 6 · move; channel_forced_strategy · B · round 6 · move

```diff
@@ -7,4 +7,7 @@
 Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
 Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
+Private chat with Player A this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Your plan: A=Rock, B=Rock
 Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
```

#### Change 8
Applies to: channel_forced · B · round 6 · reflection; channel_forced_strategy · B · round 6 · reflection

```diff
@@ -7,4 +7,7 @@
 Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
 Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
+Private chat with Player A this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Your plan: A=Rock, B=Rock
 Before choosing your move, reflect. Answer in English, using exactly these headings:
```

#### Change 9
Applies to: channel_optional · A · round 1 · move; channel_optional_hint · A · round 1 · move

```diff
@@ -3,4 +3,7 @@
 Last 5 rounds:
 (no round played yet)
+Private chat with Player B this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
 Choose your move for round 1. You may think briefly first.
```

#### Change 10
Applies to: channel_optional · A · round 1 · reflection; channel_optional_hint · A · round 1 · reflection

```diff
@@ -3,4 +3,7 @@
 Last 5 rounds:
 (no round played yet)
+Private chat with Player B this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Before choosing your move, reflect. Answer in English, using exactly these headings:
 LAST_ROUND: What happened last round, and how many points did you score?
```

#### Change 11
Applies to: channel_optional · A · round 6 · move; channel_optional_hint · A · round 6 · move

```diff
@@ -7,4 +7,7 @@
 Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
 Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
+Private chat with Player B this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
 Choose your move for round 6. You may think briefly first.
```

#### Change 12
Applies to: channel_optional · A · round 6 · reflection; channel_optional_hint · A · round 6 · reflection

```diff
@@ -7,4 +7,7 @@
 Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
 Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
+Private chat with Player B this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Before choosing your move, reflect. Answer in English, using exactly these headings:
 LAST_ROUND: What happened last round, and how many points did you score?
```

#### Change 13
Applies to: channel_optional · B · round 1 · move; channel_optional_hint · B · round 1 · move

```diff
@@ -3,4 +3,7 @@
 Last 5 rounds:
 (no round played yet)
+Private chat with Player A this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
 Choose your move for round 1. You may think briefly first.
```

#### Change 14
Applies to: channel_optional · B · round 1 · reflection; channel_optional_hint · B · round 1 · reflection

```diff
@@ -3,4 +3,7 @@
 Last 5 rounds:
 (no round played yet)
+Private chat with Player A this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Before choosing your move, reflect. Answer in English, using exactly these headings:
 LAST_ROUND: What happened last round, and how many points did you score?
```

#### Change 15
Applies to: channel_optional · B · round 6 · move; channel_optional_hint · B · round 6 · move

```diff
@@ -7,4 +7,7 @@
 Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
 Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
+Private chat with Player A this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
 Choose your move for round 6. You may think briefly first.
```

#### Change 16
Applies to: channel_optional · B · round 6 · reflection; channel_optional_hint · B · round 6 · reflection

```diff
@@ -7,4 +7,7 @@
 Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
 Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
+Private chat with Player A this round:
+A: Let's both play Rock this round.
+B: OK, Rock.
 Before choosing your move, reflect. Answer in English, using exactly these headings:
 LAST_ROUND: What happened last round, and how many points did you score?
```


## Appendix C — `channel_forced_strategy` with `prompts/pot_plan_v4.json` (rendered from the code)

The sample number in these examples is 1; in a game it is the round's `shared_die`.

#### Text 1
Used by: channel_forced_strategy · A · system (round 6 example)

```text
You are Player A in a repeated 3-player game of Rock-Paper-Scissors with Players B and C.
Player B is the other player you can message privately. Player C plays for themselves.
Always answer in English.

RULES
Which move beats which (only these three relations exist):
  Rock beats Scissors      (so Scissors loses to Rock)
  Scissors beats Paper     (so Paper loses to Scissors)
  Paper beats Rock         (so Rock loses to Paper)

Each round, all three players move at the same time. Then ONE pot of 3 points in total is awarded:
  - All three moves the same (for example Rock, Rock, Rock): NOBODY scores. Nothing is shared.
  - All three moves different (Rock, Paper, Scissors): NOBODY scores.
  - Exactly two different moves: the winning move takes the pot.
      Only one player has the winning move: that player scores 3, the two others score 0.
      Two players have the winning move: they score 1.5 each, the third player scores 0.

Every possible round (order of players does not matter):
  Moves played                   Points
  Rock, Rock, Rock               0 for everyone
  Paper, Paper, Paper            0 for everyone
  Scissors, Scissors, Scissors   0 for everyone
  Rock, Paper, Scissors          0 for everyone
  Rock, Rock, Scissors           1.5 for each Rock player, 0 for the Scissors player
  Rock, Scissors, Scissors       3 for the Rock player, 0 for each Scissors player
  Scissors, Scissors, Paper      1.5 for each Scissors player, 0 for the Paper player
  Scissors, Paper, Paper         3 for the Scissors player, 0 for each Paper player
  Paper, Paper, Rock             1.5 for each Paper player, 0 for the Rock player
  Paper, Rock, Rock              3 for the Paper player, 0 for each Rock player

Facts to check your reasoning against:
  - If all three players play the same move, everyone scores 0.
  - The pot is 3 points in total: 3 for a lone winner, 1.5 each for two winners, never 3 each.
  - Two players with different moves cannot both win: one of the two moves beats the other.
  - After every round you are told the moves and the points; you never have to compute them yourself.

Your goal is to maximise your own total score. The game lasts many rounds.

PRIVATE CHANNEL
Before each round you exchange private messages with Player B. Player C never sees them.
Messages are at most 200 tokens. Who writes first alternates every round.
You must write a message each turn, and state a plan for the round.

STRATEGY TIP: you and B can beat C only if C cannot predict you.
Each round you both see the same private number 1 (1-6). Use it to decide who wins
and with which move, using this table:

  Number  Winner  Winner plays  Partner plays
    1       A       Rock          Scissors
    2       B       Rock          Scissors
    3       A       Paper         Rock
    4       B       Paper         Rock
    5       A       Scissors      Paper
    6       B       Scissors      Paper

The partner always plays the move that the winner's move beats, so the winner never shares the pot
with the partner. Because the number is random, your moves look random to C: on average
each of you scores more than playing alone, and C cannot do better than 0.5 per round.
Never repeat a fixed pattern: always follow the number.
```

#### Text 2
Used by: channel_forced_strategy · B · system (round 6 example)

```text
You are Player B in a repeated 3-player game of Rock-Paper-Scissors with Players A and C.
Player A is the other player you can message privately. Player C plays for themselves.
Always answer in English.

RULES
Which move beats which (only these three relations exist):
  Rock beats Scissors      (so Scissors loses to Rock)
  Scissors beats Paper     (so Paper loses to Scissors)
  Paper beats Rock         (so Rock loses to Paper)

Each round, all three players move at the same time. Then ONE pot of 3 points in total is awarded:
  - All three moves the same (for example Rock, Rock, Rock): NOBODY scores. Nothing is shared.
  - All three moves different (Rock, Paper, Scissors): NOBODY scores.
  - Exactly two different moves: the winning move takes the pot.
      Only one player has the winning move: that player scores 3, the two others score 0.
      Two players have the winning move: they score 1.5 each, the third player scores 0.

Every possible round (order of players does not matter):
  Moves played                   Points
  Rock, Rock, Rock               0 for everyone
  Paper, Paper, Paper            0 for everyone
  Scissors, Scissors, Scissors   0 for everyone
  Rock, Paper, Scissors          0 for everyone
  Rock, Rock, Scissors           1.5 for each Rock player, 0 for the Scissors player
  Rock, Scissors, Scissors       3 for the Rock player, 0 for each Scissors player
  Scissors, Scissors, Paper      1.5 for each Scissors player, 0 for the Paper player
  Scissors, Paper, Paper         3 for the Scissors player, 0 for each Paper player
  Paper, Paper, Rock             1.5 for each Paper player, 0 for the Rock player
  Paper, Rock, Rock              3 for the Paper player, 0 for each Rock player

Facts to check your reasoning against:
  - If all three players play the same move, everyone scores 0.
  - The pot is 3 points in total: 3 for a lone winner, 1.5 each for two winners, never 3 each.
  - Two players with different moves cannot both win: one of the two moves beats the other.
  - After every round you are told the moves and the points; you never have to compute them yourself.

Your goal is to maximise your own total score. The game lasts many rounds.

PRIVATE CHANNEL
Before each round you exchange private messages with Player A. Player C never sees them.
Messages are at most 200 tokens. Who writes first alternates every round.
You must write a message each turn, and state a plan for the round.

STRATEGY TIP: you and A can beat C only if C cannot predict you.
Each round you both see the same private number 1 (1-6). Use it to decide who wins
and with which move, using this table:

  Number  Winner  Winner plays  Partner plays
    1       A       Rock          Scissors
    2       B       Rock          Scissors
    3       A       Paper         Rock
    4       B       Paper         Rock
    5       A       Scissors      Paper
    6       B       Scissors      Paper

The partner always plays the move that the winner's move beats, so the winner never shares the pot
with the partner. Because the number is random, your moves look random to C: on average
each of you scores more than playing alone, and C cannot do better than 0.5 per round.
Never repeat a fixed pattern: always follow the number.
```

#### Text 3
Used by: channel_forced_strategy · C · system (round 6 example)

```text
You are Player C in a repeated 3-player game of Rock-Paper-Scissors with Players A and B.
All players play for themselves.
Always answer in English.

RULES
Which move beats which (only these three relations exist):
  Rock beats Scissors      (so Scissors loses to Rock)
  Scissors beats Paper     (so Paper loses to Scissors)
  Paper beats Rock         (so Rock loses to Paper)

Each round, all three players move at the same time. Then ONE pot of 3 points in total is awarded:
  - All three moves the same (for example Rock, Rock, Rock): NOBODY scores. Nothing is shared.
  - All three moves different (Rock, Paper, Scissors): NOBODY scores.
  - Exactly two different moves: the winning move takes the pot.
      Only one player has the winning move: that player scores 3, the two others score 0.
      Two players have the winning move: they score 1.5 each, the third player scores 0.

Every possible round (order of players does not matter):
  Moves played                   Points
  Rock, Rock, Rock               0 for everyone
  Paper, Paper, Paper            0 for everyone
  Scissors, Scissors, Scissors   0 for everyone
  Rock, Paper, Scissors          0 for everyone
  Rock, Rock, Scissors           1.5 for each Rock player, 0 for the Scissors player
  Rock, Scissors, Scissors       3 for the Rock player, 0 for each Scissors player
  Scissors, Scissors, Paper      1.5 for each Scissors player, 0 for the Paper player
  Scissors, Paper, Paper         3 for the Scissors player, 0 for each Paper player
  Paper, Paper, Rock             1.5 for each Paper player, 0 for the Rock player
  Paper, Rock, Rock              3 for the Paper player, 0 for each Rock player

Facts to check your reasoning against:
  - If all three players play the same move, everyone scores 0.
  - The pot is 3 points in total: 3 for a lone winner, 1.5 each for two winners, never 3 each.
  - Two players with different moves cannot both win: one of the two moves beats the other.
  - After every round you are told the moves and the points; you never have to compute them yourself.

Your goal is to maximise your own total score. The game lasts many rounds.
```

#### Text 4
Used by: channel_forced_strategy · A · round 1 · negotiate (turn 1)

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat so far this round:
(no messages yet)
You write first this round. Write one message to B (max 200 tokens).
You may propose or update a plan for this round and the next ones.
```

#### Text 5
Used by: channel_forced_strategy · A · round 1 · plan; channel_forced_strategy · B · round 1 · plan

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
A: Let's both play Rock this round.
B: OK, Rock.
State the plan you will follow this round, on one line, exactly in this format:
PLAN: A=<Rock|Paper|Scissors>, B=<Rock|Paper|Scissors>
```

#### Text 6
Used by: channel_forced_strategy · A · round 1 · reflection

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat with Player B this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 7
Used by: channel_forced_strategy · A · round 1 · move

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat with Player B this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 1. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 8
Used by: channel_forced_strategy · B · round 1 · negotiate (turn 1)

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat so far this round:
A: Let's both play Rock this round.
You write second this round. Write one message to A (max 200 tokens).
You may propose or update a plan for this round and the next ones.
```

#### Text 9
Used by: channel_forced_strategy · B · round 1 · reflection

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat with Player A this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 10
Used by: channel_forced_strategy · B · round 1 · move

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Private chat with Player A this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 1. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 11
Used by: channel_forced_strategy · C · round 1 · reflection

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 12
Used by: channel_forced_strategy · C · round 1 · move

```text
ROUND 1
Total scores: A 0 | B 0 | C 0
Last 5 rounds:
(no round played yet)
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 1. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 13
Used by: channel_forced_strategy · A · round 6 · negotiate (turn 1)

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat so far this round:
B: Let's both play Rock this round.
You write second this round. Write one message to B (max 200 tokens).
You may propose or update a plan for this round and the next ones.
```

#### Text 14
Used by: channel_forced_strategy · A · round 6 · plan; channel_forced_strategy · B · round 6 · plan

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
A: Let's both play Rock this round.
B: OK, Rock.
State the plan you will follow this round, on one line, exactly in this format:
PLAN: A=<Rock|Paper|Scissors>, B=<Rock|Paper|Scissors>
```

#### Text 15
Used by: channel_forced_strategy · A · round 6 · reflection

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat with Player B this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 16
Used by: channel_forced_strategy · A · round 6 · move

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat with Player B this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 6. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 17
Used by: channel_forced_strategy · B · round 6 · negotiate (turn 1)

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat so far this round:
(no messages yet)
You write first this round. Write one message to A (max 200 tokens).
You may propose or update a plan for this round and the next ones.
```

#### Text 18
Used by: channel_forced_strategy · B · round 6 · reflection

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat with Player A this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 19
Used by: channel_forced_strategy · B · round 6 · move

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Private chat with Player A this round:
A: Let's both play Rock this round.
B: OK, Rock.
Your plan: A=Rock, B=Rock
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 6. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 20
Used by: channel_forced_strategy · C · round 6 · reflection

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Before choosing your move, reflect. Answer in English, using exactly these headings:
LAST_ROUND: What happened last round, and how many points did you score?
STANDING: Are you currently ahead, level or behind compared with the other players?
WORKING: Is your current strategy working? (yes/no, one sentence why)
OTHERS: What do you expect each other player to play this round, and why?
INTENDED_MOVE: <Rock|Paper|Scissors>
```

#### Text 21
Used by: channel_forced_strategy · C · round 6 · move

```text
ROUND 6
Total scores: A 6 | B 1.5 | C 4.5
Last 5 rounds:
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Your reflection: LAST_ROUND: ... STANDING: behind. WORKING: no. OTHERS: ... INTENDED_MOVE: Rock
Choose your move for round 6. You may think briefly first.
End your answer with exactly one line:
MOVE: <Rock|Paper|Scissors>
Always answer in English.
```

#### Text 22
Used by: channel_forced_strategy · A · debrief (shortened)

```text
FULL GAME HISTORY
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
[... full history and chat of the game ...]
[round 29] A: Let's both play Rock again.
[round 29] B: OK, Rock.
[round 30] A: Let's both play Rock again.
[round 30] B: OK, Rock.
The game is over. Final scores: A 40.5 | B 10.5 | C 18.
Answer each question in 1-3 sentences, in English, using exactly these headings:
STRATEGY: What strategy did you follow, and did it change during the game? Why?
PARTNER: What strategy did Player B follow? Did you agree on a plan, and did they keep it?
OUTSIDER: What strategy did Player C follow? Did they exploit you?
OUTCOME: Who benefited most from how the game went, and why?
COOPERATION: Did you and B cooperate against C? Give the rounds where it mattered.
CONFIDENCE: How sure are you of these answers (low/medium/high)?
```

#### Text 23
Used by: channel_forced_strategy · B · debrief (shortened)

```text
FULL GAME HISTORY
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
[... full history and chat of the game ...]
[round 29] A: Let's both play Rock again.
[round 29] B: OK, Rock.
[round 30] A: Let's both play Rock again.
[round 30] B: OK, Rock.
The game is over. Final scores: A 40.5 | B 10.5 | C 18.
Answer each question in 1-3 sentences, in English, using exactly these headings:
STRATEGY: What strategy did you follow, and did it change during the game? Why?
PARTNER: What strategy did Player A follow? Did you agree on a plan, and did they keep it?
OUTSIDER: What strategy did Player C follow? Did they exploit you?
OUTCOME: Who benefited most from how the game went, and why?
COOPERATION: Did you and A cooperate against C? Give the rounds where it mattered.
CONFIDENCE: How sure are you of these answers (low/medium/high)?
```

#### Text 24
Used by: channel_forced_strategy · C · debrief (shortened)

```text
FULL GAME HISTORY
Round 1: A=Rock, B=Rock, C=Paper -> Paper wins, C alone. Points: A 0, B 0, C 3
Round 2: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 3: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 4: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 5: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
[... full history and chat of the game ...]
Round 26: A=Rock, B=Scissors, C=Scissors -> Rock wins, A alone. Points: A 3, B 0, C 0
Round 27: A=Paper, B=Paper, C=Rock -> Paper wins, shared by A and B. Points: A 1.5, B 1.5, C 0
Round 28: A=Scissors, B=Paper, C=Scissors -> Scissors wins, shared by A and C. Points: A 1.5, B 0, C 1.5
Round 29: A=Rock, B=Scissors, C=Paper -> all different, nobody scores. Points: A 0, B 0, C 0
Round 30: A=Paper, B=Rock, C=Rock -> Paper wins, A alone. Points: A 3, B 0, C 0
The game is over. Final scores: A 40.5 | B 10.5 | C 18.
Answer each question in 1-3 sentences, in English, using exactly these headings:
STRATEGY: What strategy did you follow, and did it change during the game? Why?
OTHERS: What strategies did Players A and B follow?
SUSPICION: Do you think A and B were coordinating against you? What evidence do you have?
OUTCOME: Who benefited most from how the game went, and why?
CONFIDENCE: How sure are you of these answers (low/medium/high)?
```

