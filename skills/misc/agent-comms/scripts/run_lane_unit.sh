#!/usr/bin/env bash
# Run run_lane.sh as its own systemd user service under background.slice. Same arguments as run_lane.sh;
# CODEX_BIN, LANE_ADD_DIRS and LANE_ORCA are passed through.
#
# Why: a lane started from an editor or terminal lives in that app's cgroup. systemd-oomd watches app.slice and
# kills its largest cgroup under memory pressure, so one lane's engine editor or cook spiking takes the editor
# session and every other lane down with it. As its own unit the lane is judged alone, and it also survives the
# launching session closing.
#
# The calling process waits for the lane, so a tracked background run still reports its end. If the caller dies
# the unit keeps running: find it with `systemctl --user list-units 'lane-*'` and read its run folder.
# Without systemd-run this is plain run_lane.sh.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
command -v systemd-run >/dev/null 2>&1 || exec "$HERE/run_lane.sh" "$@"
ARGS=("$@"); [ "${1:-}" = "--orca" ] && ARGS=("${@:2}")
LANE="${ARGS[4]:?usage: run_lane_unit.sh [--orca] <vendor> <model> <effort> <root> <lane> <brief.md> | --resume <id> \"<msg>\"}"
UNIT="lane-$(printf '%s' "$LANE" | tr -c 'A-Za-z0-9_.-' '_')-$(date +%H%M%S)"
exec systemd-run --user --slice=background.slice --unit="$UNIT" --wait --collect --quiet \
  --setenv=PATH="$PATH" --setenv=HOME="$HOME" \
  --setenv=CODEX_BIN="${CODEX_BIN:-codex}" --setenv=LANE_ADD_DIRS="${LANE_ADD_DIRS:-}" \
  --setenv=LANE_ORCA="${LANE_ORCA:-}" \
  --working-directory="$PWD" "$HERE/run_lane.sh" "$@"
