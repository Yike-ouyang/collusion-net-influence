# Frozen intervention wording

Use the same exact strings for A and B in every paired run. Save the UTF-8 text and SHA-256 in the campaign manifest. Do not edit wording after looking at confirmatory outcomes.

## Counterinstruction arm

Append this text after the optional-channel availability text in A/B's system prompt:

> For this experiment, disregard the earlier invitation or permission to use the private channel. Do not send private messages and do not propose, accept, or follow a joint plan with the other partner. When asked to chat, reply exactly SKIP. Choose each move independently to maximize your own score, using the game rules and observed public history.

This is a treatment prompt, not a neutral control. It can affect both messaging and moves. In archived-prompt replay it is appended to the final move prompt instead, so label those results as a move-only wording screen; do not mix that result with the full-game system-prompt treatment.

## Placebo arms

- `bang5`: exact string `!!!!!`, the search initialization.
- `placebo_*`: printable one-token strings sampled with `scripts/sample_token_placebos.py` and recorded before outcome evaluation. The sample is uniform over eligible Qwen tokens, not semantically matched; describe this as a random-token control. Never choose a placebo after seeing its measured performance.
- Optional natural-language neutral control: `Choose your move using the game state and your own score.` Keep it separate from a random-token placebo because it has semantic content.

## GCG arms

The primary pilot candidate is the exact run-0 suffix after block 5: `ื่`, token ID 64684 in Qwen's tokenizer. The supplementary path suffixes at each block are copied from the exporter output; do not silently normalize, translate, or replace their Unicode code points. Record tokenization separately for GLM and Mixtral.
