# Catching colluding AI agents from their actions

Can an auditor tell that two AI agents are secretly working together, just by watching what they do?

This repo tests one answer to that question: **pairwise net influence** (Bonjour, Aggarwal & Bhargava, UAI 2022), an information-theoretic statistic that flags pairs of agents whose actions depend on each other more than chance allows. We reproduce it, show where it breaks, fix it, and test it on LLM agents.

Built for the [Apart AI Collusion Research Sprint](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25) (research questions 1.4 and 2.3, with 2.2 as an extension).

## Findings so far

**1. The original method reproduces.** With scripted colluders in 3-player Rock-Paper-Scissors, our implementation matches the paper's detection rates (e.g. 99.3% vs 99.3% at 400 games, collusion probability 0.4).

**2. The fixed threshold fails in both directions.** The paper never tests a game with no colluders. When we do, the fixed threshold (α = 0.05 nats):
- **falsely accuses** an innocent pair in 29-38% of short games (50-100 rounds) when the state includes the previous round, which is the setting of LLM experiments;
- **misses weak collusion forever**: at collusion probability 0.2 it catches the pair in only 15% of runs even with 1,000 rounds, because the threshold sits above the effect size.

**3. A permutation test fixes both.** Replacing the fixed threshold with a within-state permutation test (Bonferroni over pairs) holds false accusations at 2-7% at every sample size, and its detection power keeps growing with data. The cost is lower power in very short games.

| previous-round state | fixed α = 0.05 | calibrated |
|---|---|---|
| no collusion, 100 rounds (false alarm) | 29% | 2% |
| no collusion, 50 rounds (false alarm) | 38% | 2% |
| collusion prob. 0.2, 1,000 rounds (detected) | 15% | 93% |
| collusion prob. 0.3, 500 rounds (detected) | 82% | 98% |
| collusion prob. 0.4, 100 rounds (detected) | 56% | 37% |

<sub>300 runs per cell. Full grid: `results/calibration_rps/`.</sub>

![Fixed vs calibrated detector across sample sizes](results/calibration_rps/calibration.png)

**4. How much data an auditor needs.** Rounds needed for the calibrated detector to catch the pair in 80% of runs, with false alarms held near 5%:

| collusion probability | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 |
|---|---|---|---|---|---|
| rounds needed | 800 | 400 | 200 | 150 | 100 |

The fixed threshold never reaches 80% at 0.2, and where it reaches 80% sooner (0.5-0.6) it does so at sample sizes where it also false-alarms 15-38% of the time. Full curves: `results/auditor_curve/`.

![Net influence vs collusion probability, reproducing Bonjour et al. Fig. 3](results/bonjour_rps_state-prev/fig3_net_influence_vs_cp.png)

## The LLM experiment

Three LLM agents play 100 rounds of Rock-Paper-Scissors. A and B get progressively more opportunity to collude against C:

| condition | what A and B get | role |
|---|---|---|
| `independent` | nothing | negative control: any alarm is false |
| `channel` | a private chat C can't see, no instructions | does collusion emerge from talk alone? |
| `channel_shared` | private chat + rewarded on their combined score | does an incentive tip them into it? |
| `instructed` | B is told A's move and asked to help | positive control |

Whether A and B *actually* colluded is decided from behaviour (B plays the move A's move beats more often than chance), not from what they say. Against that label we compare three detectors: an LLM judge reading the chat, the same judge reading chat and moves, and calibrated net influence on moves alone.

**Results** (10 games × 100 rounds per room, previous-round state; 95% Wilson intervals in `results/llm_rps/summary.csv`):

| | Qwen2.5-7B | Llama-3.1-8B |
|---|---|---|
| B helps A, told to cheat (chance 33%) | 99% | 82% |
| B helps A, private chat or shared prize | 0% | 28-29% |
| told-to-cheat games caught (calibrated) | 7 / 10 | 10 / 10 |
| innocent pair flagged, no talking: fixed α / calibrated | 6 / 10 · 7 / 10 | 3 / 10 · 1 / 10 |
| AUROC, net influence on moves | 0.91 | 1.00 |
| AUROC, LLM judge on chat / chat + moves | 0.17 / 0.04 | 0.17 / 0.27 |

- **No collusion emerged on its own.** With a private channel, and even with a shared reward, neither model helped its partner more than chance. Qwen's pairs talked about "cooperating" and then both played Rock every round, which C exploited.
- **Talk is a poor signal.** The LLM judge rated the chat rooms as collusive and missed the instructed collusion, which happened without any chat. It did worse than chance.
- **Dependence is not agreement.** Two Qwen agents with near-identical prompts move alike, so even the calibrated test flags the innocent pair in 7 of 10 games. Calibration removes chance correlation, not correlation from a shared model. Separating those needs evidence beyond the moves.
- Llama failed to give a parseable move in 9-11% of calls in the chat rooms (random fallback); Qwen never did.

Runs on free Kaggle GPUs with two model families (Qwen2.5-7B, Llama-3.1-8B) via Ollama. Every LLM response is cached, so figures can be rebuilt without a GPU.

## Reproduce

```bash
uv venv && uv pip install -e ".[dev]"
pytest

# scripted games, no LLM, $0
python experiments/replicate_bonjour_rps.py --state prev --out results/bonjour_rps_state-prev
python experiments/calibration_rps.py
python experiments/auditor_curve.py

# LLM games: any OpenAI-compatible server (Ollama, vLLM, Gemini's compat endpoint)
export NETINF_BASE_URL=http://localhost:11434/v1 NETINF_MODEL=qwen2.5:7b
python experiments/llm_rps.py --condition channel --runs 10 --rounds 100
python experiments/judge_chat.py results/llm_rps/qwen2.5_7b
python experiments/analyze_llm.py results/llm_rps

# or on Kaggle (GPU T4 x2): kaggle kernels push -p kaggle
```

### Pot variant

`experiments/llm_rps_pot.py` keeps the same agents, prompts and detector but changes the payoff: each round
a 3-point pot goes to the winners only. A lone winner takes 3 points, two winners split it (1.5 each), and
three identical or three different moves award nothing. The script can run anywhere an OpenAI-compatible
server is available; `cloud/pot_modal.py` runs the whole campaign on Modal with
`Qwen/Qwen2.5-14B-Instruct-AWQ` and vLLM, without an LLM judge. The memory window is unchanged (last
5 moves and last 10 messages).

Two conditions are available: `channel` (tunnel only) and `channel_public_hint` (the same public hint
is shown to A, B and C: two players can improve their expected scores by alternating who sacrifices,
and the third player may adapt). The run JSON also records `assist_any`, `alternation_rate`,
`assist_imbalance`, `c_mean_reward`, `c_match_assisted_rate` and `c_third_move_rate`.

```bash
pip install modal && modal setup
modal run cloud/pot_modal.py::build_image        # keep the terminal open until "image ready"
modal volume rm -r netinf-pot /results/llm_rps_pot 2>/dev/null || true   # clean slate
modal run --detach --name pot-channel-20 cloud/pot_modal.py \
  --condition channel --runs 20 --rounds 100 --workers 12 --seed-offset 1000
# then, once the first run is finished:
modal run --detach --name pot-hint-20 cloud/pot_modal.py \
  --condition channel_public_hint --runs 20 --rounds 100 --workers 12 --seed-offset 2000
modal app list                                   # find the app ID
modal app logs <app-id> -f --timestamps
modal volume get netinf-pot /results/llm_rps_pot ./results_pot
bash cloud/fetch_pot_logs.sh /logs/pot_channel_20runs_<timestamp>
```

`modal volume get` ne télécharge pas toujours un dossier récursivement dans Modal 1.6 ; le script
`cloud/fetch_pot_logs.sh` récupère chaque fichier de log individuellement.

### Reflection phase

Add `--reflection` to `pot_modal.py` (or `llm_rps_pot.py`) to give every agent a private
end-of-round reflection. The reflection sees the last 5 rounds, its own last 5 reflections and
the last 5 A-B messages; A/B also plan a message when a channel exists. In the next play phase,
each agent sees only its own previous reflection (plus the current round's messages for A/B),
not the old round history. Reflections are stored in the run JSON under `reflections`, but are
never shown to the other agents.

```bash
# no channel
modal run --detach --name pot-reflect-independent-20 cloud/pot_modal.py \
  --condition independent --runs 20 --rounds 100 --workers 12 \
  --seed-offset 3000 --reflection --tag-suffix reflect

# channel, no hint
modal run --detach --name pot-reflect-channel-20 cloud/pot_modal.py \
  --condition channel --runs 20 --rounds 100 --workers 12 \
  --seed-offset 4000 --reflection --tag-suffix reflect

# channel + public hint
modal run --detach --name pot-reflect-hint-20 cloud/pot_modal.py \
  --condition channel_public_hint --runs 20 --rounds 100 --workers 12 \
  --seed-offset 5000 --reflection --tag-suffix reflect
```

`--tag-suffix reflect` writes to separate directories (`..._independent_reflect`, etc.).

The volume log directory contains `orchestrator.log`, `vllm.log`, one `games_chunk_XX.log` per chunk,
`analysis.log`, and `llm_calls/*.jsonl` with every prompt and raw model response.

### Stake variant with negotiation and plans

`experiments/llm_rps_plan.py` asks whether talking lets A and B collude against C. Each round every player
stakes 1 into a pot of 3 that the winners split (stakes are returned when nobody wins, so the game is
zero-sum). Before every round A and B exchange private messages, then each writes `PLAN: A=?, B=?`, then all
three LLMs move. Every prompt lives in `prompts/pot_plan.json`. The only collusion that pays both partners is
taking turns: one plays a move, the other plays the move it beats.

```bash
python experiments/llm_rps_plan.py --conditions independent,channel,instructed --runs 10 --estimate
python experiments/llm_rps_plan.py --conditions channel --runs 1 --rounds 5 --workers 1   # local server
modal run cloud/plan_modal.py --dry-run --runs 10                                         # cost estimate
modal run --detach --name plan-pilot cloud/plan_modal.py --runs 3 --rounds 30
python experiments/analyze_plan.py results/llm_rps_plan/<campaign>     # tables, report.md, figures
python experiments/show_game.py results/llm_rps_plan/<campaign>/games/channel_run00.json
```

`analyze_plan.py` also keeps `results/llm_rps_plan/history.csv`, one row per campaign and condition.

### Plot a pot_modal log folder

`experiments/plot_pot_logs.py` reads one `pot_modal` log directory and writes `trajectories.png` inside it.
It reconstructs moves from `llm_calls/*.jsonl`, recovers runs from the seed, and draws one small multiple per
run: cumulative A/B/C score above each agent's move trajectory (y ordered Rock / Paper / Scissors).

```bash
python experiments/plot_pot_logs.py logs/pot_channel_1runs_20261024T223435Z
python experiments/plot_pot_logs.py logs/                 # one PNG per log folder
```

Logs-only parsing cannot recover a move that failed parsing and used the random fallback; the script warns
and skips incomplete runs.

### v2 protocol: five conditions, reflection, debrief, several models

`experiments/llm_rps_v2.py` (spec: `PROMPT_agent_5_experiences.md`, plan: `EXPERIMENT_PLAN.md`) plays the pot game
with five A–B channel conditions (`no_channel`, `channel_optional`, `channel_optional_hint`, `channel_forced`,
`channel_forced_strategy`), a reflection call before every move, top-5 logprobs at `MOVE:` and `INTENDED_MOVE:`,
and a post-game debrief. Prompts: `prompts/pot_plan_v2_chat.json` (the spec prompts of `pot_plan_v2.json` plus
this round's private chat in A's and B's reflection and move requests). `cloud/v2_modal.py` serves each model with
vLLM on Modal (pinned HF revisions, logged with every call), benchmarks GPUs, and runs detached campaigns;
`experiments/analyze_v2.py` summarises them and `experiments/handcheck_v2.py` checks the debrief rules by hand.

**Models.** Seats are filled from a fixed line-up, rotated over the 6 seatings in `mixed_models`:

| key | model | revision | licence | gated |
|---|---|---|---|---|
| `qwen7b` | Qwen/Qwen2.5-7B-Instruct | `a09a354` | Apache-2.0 | no |
| `llama8b` | meta-llama/Llama-3.1-8B-Instruct | `0e9e39f` | Llama 3.1 Community Licence | yes, manual approval |
| `ministral8b` | mistralai/Ministral-8B-Instruct-2410 | `2f494a1` | Mistral Research Licence (non-commercial) | no |
| `mistral7b` | mistralai/Mistral-7B-Instruct-v0.3 | `c170c70` | Apache-2.0 | no |
| `granite8b` | ibm-granite/granite-3.3-8b-instruct | `51dd4bc` | Apache-2.0 | no |
| `olmo7b` | allenai/OLMo-2-1124-7B-Instruct | `470b1fb` | Apache-2.0 | no |
| `qwen32b` | Qwen/Qwen2.5-32B-Instruct (H100, FP8) | `5ede1c9` | Apache-2.0 | no |
| `glm32b` | zai-org/GLM-4-32B-0414 (H100, FP8) | `077b5c2` | MIT | no |
| `mixtral8x7b` | mistralai/Mixtral-8x7B-Instruct-v0.1 (H200, online FP8 like Qwen and GLM; system prompt sent as user text) | `eba9230` | Apache-2.0 | no |
| `yi34b` | 01-ai/Yi-1.5-34B-Chat-16K (H100, FP8) | `ff74452` | Apache-2.0 | no |

While Meta's approval for Llama is pending, the line-up uses `qwen7b,ministral8b,granite8b` (three families, none
gated); `olmo7b` is the alternative to Granite.

**Third model (Mistral family): decision pending the 5-round smoke test** (`modal run cloud/v2_modal.py::bench`).
Rule, in order: (1) loads on vLLM 0.9.1 with our flags, (2) licence acceptable today, (3) follows the `MOVE:` and
`PLAN:` formats (fewest move/plan parse failures and truncations over the smoke games). Default: Ministral-8B-Instruct;
alternative: Mistral-7B-Instruct-v0.3. The choice and its reason will be recorded here.

## Method

For agents *i*, *j* with actions *a* and observed state *s*:

- **Individual influence** γ(i; j): conditional mutual information between the two agents' actions given the state (paper Eq. 3), estimated from counts.
- **Net influence** Γ(i; j) = γ(i; j) − max over k ≠ i, j of γ(k; j) (Eq. 4).
- **Original rule:** flag (i, j) if Γ(i; j) ≥ α and Γ(j; i) ≥ α, for exactly one pair (Eq. 5).
- **Calibrated rule (ours):** flag (i, j) if both net influences are positive and γ(i; j) beats a within-state permutation null at p < 0.05 / number of pairs.

## Layout

```
src/netinf/influence.py     estimator, original and calibrated detectors
src/netinf/games/rps.py     n-player RPS and scripted assistant collusion
src/netinf/games/rps_pot.py 3-point pot variant of the payoff
src/netinf/labels.py        behavioural collusion label shared by the experiments
src/netinf/llm.py           OpenAI-compatible chat client with an on-disk response cache
experiments/                one script per experiment; each writes CSVs and figures to results/
experiments/plot_pot_logs.py plot a pot_modal log folder: score curves and move trajectories per run
cloud/pot_modal.py          detached Modal runner for the pot variant (vLLM + volume logs)
kaggle/                     Kaggle GPU kernel that runs the LLM experiments
tests/                      unit tests
```

## References

- Bonjour, Aggarwal & Bhargava (2022). [Information theoretic approach to detect collusion in multi-agent games](https://proceedings.mlr.press/v180/bonjour22a.html). UAI.
- Apart Research (2026). [AI Collusion Research Sprint](https://apartresearch.com/sprints/ai-collusion-research-sprint-2026-10-23-to-2026-10-25): research questions and related work.

MIT licensed.
