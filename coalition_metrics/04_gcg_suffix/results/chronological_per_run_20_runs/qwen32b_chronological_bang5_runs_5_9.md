# Per-run chronological Qwen GCG

Status: **running**; start suffix `!!!!!`; block size 10 rounds.

## Method and hypotheses
- H1: chronological block GCG lowers no-channel-to-optional KL within individual runs.
- H2: suffix updates learned from earlier rounds also improve the next, not-yet-trained chronological block.
- H3: independently optimized runs converge toward repeated token IDs or text fragments more often than expected by chance.
- H4: any repeated suffix pattern is a candidate for a separate fresh-game evaluation, not proof of anti-collusion.

The objective averages per-context forward KLs within each contiguous chronological block. The candidate is selected on the current block and scored on the next block before that future block receives its own update. Rounds remain grouped in chronological run trajectories.

## Per-run suffix path

| Run | Block | Rounds | Suffix used → suffix after update | Block gain (bits) | Next-block gain (bits) |
|---:|---:|---|---|---:|---:|

## Final per-run candidates

| Run | Suffix after round 60 | Token IDs |
|---:|---|---|

## Limits

- The GCG loss matches optional-channel policy distributions to the no-channel reference; it does not directly minimize observed I(A;B|S).
- The pair law is a product of two separately queried move policies, not an empirically sampled joint action law.
- Within a run, each suffix update is selected using one contiguous current block; the next block is measured before it is used for its own update.
- No-channel and optional-channel states share run/round labels but are separate saved trajectories with different public histories.
- This prompt-level procedure is not a full game rollout. Confirm a consensus suffix on fresh complete games and game-level metrics.
