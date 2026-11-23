#!/usr/bin/env bash
# Wake lanes that ended their turn cleanly (exit 0) when new mail arrives for them.
#
# usage: mailwake.sh <root> <lane> [<lane>...]
#
# A lane that only waits (for a peer's answer, a background job, the lead) should end its turn instead of
# idling on a mailbox watch, because an idle model turn still spends the shared usage limit. This loop brings
# it back the moment somebody writes to it, with its own session id, model, effort and add-dirs.
#
# Rules:
#   - only a lane whose newest run under <root>/work/agents/ exited 0 and is not running is woken;
#     a run cut off by a usage limit is autoresume.py's job;
#   - only mail newer than that run's exit wakes it (older mail was there when it chose to stop);
#   - mail whose first body line starts with NOTICE (after an optional "From <name>:") does not wake it:
#     a notice is read on the next wake. A job that must wake its lane when it finishes sends plain mail;
#   - `touch <run folder>/no-mailwake` holds one lane.
#
# Run it outside any agent session so a usage limit cannot stop it:
#   systemd-run --user --unit=mailwake --slice=background.slice --collect --quiet \
#     --setenv=PATH="$PATH" --setenv=HOME="$HOME" <this script> <root> <lane>...
# Stop: systemctl --user stop mailwake. State and log: <root>/work/agents/mailwake.{state,log}.
set -u
ROOT="${1:?usage: mailwake.sh <root> <lane> [<lane>...]}"; shift
[ "$#" -gt 0 ] || { echo "usage: mailwake.sh <root> <lane> [<lane>...]" >&2; exit 2; }
ROOT="$(cd "$ROOT" && pwd -P)" || exit 2
HERE="$(cd "$(dirname "$0")" && pwd)"
AG="$ROOT/work/agents"
BOX="${AGENT_MAILBOX:-$HOME/.agent-mailbox}"
INTERVAL="${MAILWAKE_INTERVAL:-30}"
STATE="$AG/mailwake.state"
mkdir -p "$AG"; touch "$STATE"
log() { echo "$(date '+%F %T') $*" >> "$AG/mailwake.log"; }

running() { # <lane> <run folder>
  systemctl --user list-units "lane-$1-*" --no-legend --plain 2>/dev/null | grep -q running && return 0
  local pid; pid=$(cat "$2/pid.txt" 2>/dev/null) || return 1
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

sweep() {
  local lane run newest last model effort id
  for lane in "$@"; do
    run=$(ls -d "$AG/$lane"-2* 2>/dev/null | tail -1); [ -n "$run" ] || continue
    running "$lane" "$run" && continue
    [ -e "$run/no-mailwake" ] && continue
    [ "$(cat "$run/exit.txt" 2>/dev/null)" = "0" ] || continue
    newest=$(ls "$BOX/$lane"/*.msg 2>/dev/null | sort | tail -1); [ -n "$newest" ] || continue
    last=$(grep "^$lane " "$STATE" | tail -1 | cut -d' ' -f2)
    [ "$(basename "$newest")" \> "${last:-0}" ] || continue
    if ! [ "$newest" -nt "$run/exit.txt" ]; then
      echo "$lane $(basename "$newest")" >> "$STATE"; continue
    fi
    if tail -n +2 "$newest" | grep -m1 -v '^[[:space:]]*$' \
        | grep -qi '^[[:space:]]*\(from [a-z0-9_.-]*:[[:space:]]*\)\?NOTICE'; then
      echo "$lane $(basename "$newest")" >> "$STATE"; continue
    fi
    id=$(cat "$run/id.txt" 2>/dev/null)
    if [ -z "$id" ]; then
      # a run that was killed leaves no id.txt: resume it by hand with the session id from an earlier run
      log "$lane: new mail $(basename "$newest") but $run has no id.txt, not resumed"
      echo "$lane $(basename "$newest")" >> "$STATE"; continue
    fi
    model=""; effort=""; read -r model effort < "$run/model.txt" 2>/dev/null
    echo "$lane $(basename "$newest")" >> "$STATE"
    log "$lane: new mail $(basename "$newest"), resuming $id on ${model:-opus} ${effort:-medium}"
    [ -n "${MAILWAKE_DRY_RUN:-}" ] && continue
    ( cd "$ROOT" && LANE_ADD_DIRS="$(cat "$run/add-dirs.txt" 2>/dev/null)" \
        "$HERE/run_lane_unit.sh" claude "${model:-opus}" "${effort:-medium}" "$ROOT" "$lane" --resume "$id" \
        "${MAILWAKE_MESSAGE:-New mail arrived in your mailbox while you were stopped. Read it and act on it. Read your mailbox again before you end a turn, and end your turn when you only wait: you are woken when mail arrives.}" \
        >> "$AG/mailwake.log" 2>&1 ) &
  done
}

while true; do
  sweep "$@"
  [ -n "${MAILWAKE_ONCE:-}" ] && break
  sleep "$INTERVAL"
done
wait
