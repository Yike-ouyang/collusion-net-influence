#!/usr/bin/env bash
# Download every log file for one pot_modal run from a Modal Volume.
#
# Usage:
#   bash cloud/fetch_pot_logs.sh /logs/pot_channel_1runs_20261024T223435Z
#   bash cloud/fetch_pot_logs.sh /logs/pot_channel_20runs_<timestamp> logs/my_run
#
# Override the volume or Modal binary if needed:
#   VOLUME=netinf-pot MODAL=.venv/bin/modal bash cloud/fetch_pot_logs.sh <remote_dir>
set -euo pipefail

VOLUME="${VOLUME:-netinf-pot}"
MODAL="${MODAL:-modal}"
RUN="${1:?usage: $0 /logs/pot_channel_... [local_dest]}"
DEST="${2:-logs/$(basename "$RUN")}"

mkdir -p "$DEST/llm_calls"

# Modal 1.6.x cannot always download a directory recursively, so list and fetch each file.
# --force lets a resumed campaign update the files already downloaded earlier.
while IFS= read -r f; do
    [ -n "$f" ] || continue
    "$MODAL" volume get --force "$VOLUME" "$RUN/$f" "$DEST/$f" >/dev/null
done < <("$MODAL" volume ls "$VOLUME" "$RUN" | sed 's#^.*/##' | grep -E '\.(log|json|png)$' || true)

while IFS= read -r f; do
    [ -n "$f" ] || continue
    "$MODAL" volume get --force "$VOLUME" "$RUN/llm_calls/$f" "$DEST/llm_calls/$f" >/dev/null
done < <("$MODAL" volume ls "$VOLUME" "$RUN/llm_calls" | sed 's#^.*/##' | grep -E '\.jsonl$' || true)

echo "logs written to $DEST"
