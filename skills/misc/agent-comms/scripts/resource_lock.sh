#!/usr/bin/env bash
# Run a command while holding a named machine-wide lock, so jobs from different sessions and lanes that
# need the same single-instance tool (an engine editor, a cook, the GPU) run one at a time, in turn.
#
# usage: resource_lock.sh <name> [--wait SECONDS] [--busy REGEX]... -- <command> [args...]
#        resource_lock.sh --who <name>
#
#   <name>          the resource, agreed between the sessions ("editor", "cook", "gpu")
#   --wait SECONDS  give up after this long (exit 75); default: wait as long as it takes
#   --busy REGEX    after taking the lock, also wait while a process matching REGEX (against `ps -eo args`)
#                   runs, for holders that do not use this script (the user's game, a hand-started editor)
#   --who           print who holds the lock now
#
# Why not poll for "no editor process": a polling job never gets a slot while others start runs back to
# back, and two polling jobs both start in the same free gap. A lock gives each waiter its turn.
set -u
DIR="${AGENT_LOCK_DIR:-${AGENT_MAILBOX:-$HOME/.agent-mailbox}/.locks}"
mkdir -p "$DIR"
if [ "${1:-}" = "--who" ]; then
  f="$DIR/${2:?usage: resource_lock.sh --who <name>}.lock"
  if [ -e "$f" ] && ! flock -n "$f" true 2>/dev/null; then cat "$f.owner" 2>/dev/null || echo "held"; else echo "free"; fi
  exit 0
fi
NAME="${1:?usage: resource_lock.sh <name> [--wait SECONDS] [--busy REGEX]... -- <command> [args...]}"; shift
WAIT=""; BUSY=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --wait) WAIT="$2"; shift 2 ;;
    --busy) BUSY+=("$2"); shift 2 ;;
    --) shift; break ;;
    *) echo "resource_lock.sh: unknown argument $1 (put the command after --)" >&2; exit 2 ;;
  esac
done
[ "$#" -gt 0 ] || { echo "resource_lock.sh: no command" >&2; exit 2; }
LOCK="$DIR/$NAME.lock"
exec 9>>"$LOCK"
if [ -n "$WAIT" ]; then flock -w "$WAIT" 9 || { echo "resource_lock.sh: $NAME still held after ${WAIT}s" >&2; exit 75; }
else flock 9; fi
echo "pid $$ since $(date '+%F %T'): $*" > "$LOCK.owner"
for r in "${BUSY[@]}"; do
  while ps -eo args | grep -v 'resource_lock.sh' | grep -qE -- "$r"; do sleep 10; done
done
"$@" 9>&-
rc=$?
rm -f "$LOCK.owner"
exit $rc
