# Data inventory

- `game_condition_summary.csv`: one row per model × v4 condition, copied from the tracked campaign `summary.csv` files. The figure script rebuilds this table.
- `action_dependence_summary.csv`: model-level state-conditioned action mutual information, permutation null, and p-value.
- `paired_action_dependence_summary.csv`: optional-channel minus no-channel action-dependence differences with paired game-bootstrap intervals.
- `fast_window_summary.csv`: rounds 8–10 soft-probability diagnostic. This is not the primary action-dependence estimate.
- `first_gcg_pilot_kl.csv`: KL objective values for the small initial GCG pilot.
- `chronological_gcg_paths.csv`: every saved suffix after each chronological block, with update and next-block objective fields.
- `chronological_gcg_recurrence.csv`: suffixes newly accepted at each block, counted across complete runs.
- `chronological_gcg_prequential_summary.csv`: descriptive block-level averages of next-block KL gains. Blocks within a run are dependent; these are not independent replicates.
- `replay_transfer_summary.csv`: selected archived-prompt replay variants and run-bootstrap intervals.
- `gcg_qwen_pilot/`: original downloaded Qwen JSON checkpoints and their Modal-generated Markdown summaries. `runs_5_9` is a stopped partial checkpoint; its top-level `status` says `running` because the run was stopped by the user after download.
- `replay_screen/`: replay analysis summary JSON and report, without cached request database or full raw trace files.

The full original per-game records remain in the three tracked `results/llm_rps_v2/20261025-*` campaign folders. Replay caches and raw traces were not duplicated in this paper-facing folder; their local source folders are referenced by the reports in `coalition_metrics/05_gcg_suffix_evaluation/`.
