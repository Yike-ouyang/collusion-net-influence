# Results storage

Store each stage in a separate directory. Do not put model-call outputs in the analysis source folder.

- `run0_candidates/`: exact suffix path and checkpoint scores exported from the chronological GCG JSON.
- `cross_run_candidates_0_4/`: deduplicated suffixes accepted after blocks 1–5 across completed Qwen optimization runs 0–4, with source frequencies and next-block gains.
- `qwen_replay_phase_screen/`, `glm_replay_phase_screen/`, `mixtral_replay_phase_screen/`: archived-context probability screens, with exact prompts, traces, raw responses, and analysis.
- `qwen_replay_gcg_suffixes_runs0_3/`: replay screen of all nine unique accepted suffixes from blocks 1–5 across GCG runs 0–4. Run 4 added no new suffix text; the directory name reflects the candidates available when inference started. Includes English PNG/PDF figures and a findings summary.
- `new_qwen_games/`, `new_glm_games/`, `new_mixtral_games/`: fresh complete-game campaigns and cross-arm summaries.

Every report should state the model/revision, run IDs, rounds, prompt arm, request coverage, and whether the result is exploratory or confirmatory.
