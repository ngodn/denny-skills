#!/usr/bin/env bash
# Run a headless agent lane (Claude Code, Codex or Antigravity) on a brief, or resume one, with a
# chosen model and effort, everything logged to a run folder. Every vendor runs with approvals off.
#
#   run_lane.sh <vendor> <model> <effort> <root> <lane> <brief.md> [extra prompt]
#   run_lane.sh <vendor> <model> <effort> <root> <lane> --resume <id> "<message>"
#
#   vendor  claude | codex | agy
#   model   a full model id, or a short name:
#             claude  opus, fable, sonnet, haiku (the CLI's own aliases)
#             codex   astra = gpt-6-astra, sol = gpt-6.1-sol
#             agy     argon = gemini-4-argon, flash = gemini-3.8-flash,
#                     agy-opus = claude-opus-5-5, agy-sonnet = claude-sonnet-5-5,
#                     gpt-oss = gpt-oss-120b-medium
#                     (agy ids carry the effort: gemini-4-argon-high; passing both a
#                     suffixed id and a differing --effort errors, and gpt-oss-120b only
#                     supports medium)
#   effort  low | medium | high
#   id      the session/thread/conversation id from the earlier run's id.txt
#
# Run folder: <root>/work/agents/<lane>-<stamp>/ with prompt.md, events.jsonl (the vendor's own
# stream), stderr.log, pid.txt, exit.txt, id.txt, last-message.md, vendor.txt, model.txt.
# Prints the run folder first, so a watcher (watch_lane.py) can be pointed at it at once.
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENDOR="${1:?vendor}"; MODEL="${2:?model}"; EFFORT="${3:?effort}"
ROOT="$(cd "${4:?root}" && pwd)"; LANE="${5:?lane}"; shift 5
case "$EFFORT" in low|medium|high) ;; *) echo "effort must be low, medium or high" >&2; exit 2 ;; esac

case "$VENDOR" in
  claude) ;;
  codex)
    case "$MODEL" in astra) MODEL=gpt-6-astra ;; sol) MODEL=gpt-6.1-sol ;; esac ;;
  agy)
    case "$MODEL" in
      argon) MODEL=gemini-4-argon ;;
      flash) MODEL=gemini-3.8-flash ;;
      agy-opus|opus) MODEL=claude-opus-5-5 ;;
      agy-sonnet|sonnet) MODEL=claude-sonnet-5-5 ;;
      gpt-oss|gpt-oss-120b|gpt-oss-120b-*) MODEL=gpt-oss-120b-medium; EFFORT=medium ;;
    esac
    case "$MODEL" in *-low|*-medium|*-high) ;; *) MODEL="$MODEL-$EFFORT" ;; esac ;;
  *) echo "vendor must be claude, codex or agy" >&2; exit 2 ;;
esac

RUN="$ROOT/work/agents/$LANE-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$RUN"; echo "$RUN"
echo "$VENDOR" > "$RUN/vendor.txt"; echo "$MODEL $EFFORT" > "$RUN/model.txt"

RESUME=""
if [ "${1:-}" = "--resume" ]; then
  RESUME="${2:?id}"; shift 2; printf '%s\n' "${*:-continue}" > "$RUN/prompt.md"
else
  BRIEF="${1:?brief}"; shift
  { echo "You are the $LANE lane. Your brief is the file $BRIEF. Read it in full first and follow it. The project root is $ROOT. Between steps, check your mailbox with: python3 $SCRIPT_DIR/mail.py read $LANE. Write your final report to the REPORT.md path the brief names and finish with a short summary of what you did, what you measured, what is open, and what you deleted."
    [ -n "${*:-}" ] && printf '\n%s\n' "$*"; } > "$RUN/prompt.md"
fi
PROMPT="$(cat "$RUN/prompt.md")"
EXTRA_DIRS=(); for d in ${LANE_ADD_DIRS:-}; do EXTRA_DIRS+=(--add-dir "$d"); done

cd "$ROOT"
case "$VENDOR" in
  claude)
    # Prompt on stdin: --add-dir takes several folders and would swallow a trailing prompt argument.
    ARGS=(-p --model "$MODEL" --effort "$EFFORT" --dangerously-skip-permissions
          --output-format stream-json --verbose --add-dir "$ROOT" "${EXTRA_DIRS[@]}")
    [ -n "$RESUME" ] && ARGS+=(--resume "$RESUME")
    claude "${ARGS[@]}" < "$RUN/prompt.md" > "$RUN/events.jsonl" 2> "$RUN/stderr.log" & ;;
  codex)
    ARGS=(exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check -C "$ROOT" -m "$MODEL"
          -c model_reasoning_effort="$EFFORT" --json -o "$RUN/last-message.md" "${EXTRA_DIRS[@]}")
    if [ -n "$RESUME" ]; then ARGS+=(resume "$RESUME" "$PROMPT"); else ARGS+=(-); fi
    "${CODEX_BIN:-codex}" "${ARGS[@]}" < "$RUN/prompt.md" > "$RUN/events.jsonl" 2> "$RUN/stderr.log" & ;;
  agy)
    # Always through the `agy` on PATH: it may be a shared-token lock wrapper (see SKILL.md).
    ARGS=(-p "$PROMPT" --model "$MODEL" --dangerously-skip-permissions --output-format stream-json
          --add-dir "$ROOT" "${EXTRA_DIRS[@]}")
    [ -n "$RESUME" ] && ARGS+=(--conversation "$RESUME")
    agy "${ARGS[@]}" </dev/null > "$RUN/events.jsonl" 2> "$RUN/stderr.log" & ;;
esac
echo $! > "$RUN/pid.txt"; wait $!; CODE=$?; echo $CODE > "$RUN/exit.txt"

# One id and one final message per run, whatever the vendor. `fromjson?` skips stray non-JSON
# lines (a version manager can print a notice into stdout).
EV="$RUN/events.jsonl"
pick() { jq -rR "fromjson? | $1" "$EV" 2>/dev/null | tail -1; }
case "$VENDOR" in
  claude) pick 'select(.type=="result") | .session_id // empty' > "$RUN/id.txt"
          jq -rR 'fromjson? | select(.type=="result") | .result // empty' "$EV" > "$RUN/last-message.md" 2>/dev/null ;;
  codex)  grep -m1 -o '"thread_id":"[^"]*"' "$EV" | cut -d'"' -f4 > "$RUN/id.txt" ;;
  agy)    pick 'select(.event=="result") | .result.conversation_id // empty' > "$RUN/id.txt"
          jq -rR 'fromjson? | select(.event=="result") | .result.response // empty' "$EV" > "$RUN/last-message.md" 2>/dev/null ;;
esac
exit $CODE
# Stop a lane with: kill $(cat <run>/pid.txt). Never pkill by name; other sessions share the binaries.
