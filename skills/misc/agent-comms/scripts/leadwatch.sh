#!/usr/bin/env bash
# Lead's status watch: one line per change the lead should act on or report. Run it under the Monitor tool.
#
# usage: leadwatch.sh [--units GLOB]... [--files DIR]... [--proc NAME=REGEX]... [--disk PATH:GB]...
#                     [--beat SECONDS] [--interval SECONDS]
#
#   --units GLOB       systemd user units to follow (default 'lane-*'); prints "[UNIT ENDED] <units>"
#   --files DIR        a folder where results for the user appear (not recursive); prints "[NEW FILES] <paths>"
#                      for new .png .jpg .mp4 .md files
#   --proc NAME=REGEX  a process to follow, matched against `ps -eo args`; anchor it to the executable path
#                      ('^[^ ]*Game-Win64-Shipping\.exe'); prints "[NAME STARTED]" and "[NAME CLOSED]"
#   --disk PATH:GB     prints "[DISK] <path> <n>G free" on every pass while free space is under GB
#   --beat SECONDS     heartbeat with the running units (default 1200, 0 = none), so the lead reports unasked
#
# The lead looks at each new file before passing it on, gives a lane that ended its next job, and tells the
# user only what changed. A Monitor expires (30 minutes at most): re-arm this watch on every expiry notice.
set -u
UNITS=(); FILES=(); PROCS=(); DISKS=(); BEAT=1200; INTERVAL=30
while [ "$#" -gt 0 ]; do
  case "$1" in
    --units) UNITS+=("$2"); shift 2 ;;
    --files) FILES+=("$2"); shift 2 ;;
    --proc) PROCS+=("$2"); shift 2 ;;
    --disk) DISKS+=("$2"); shift 2 ;;
    --beat) BEAT="$2"; shift 2 ;;
    --interval) INTERVAL="$2"; shift 2 ;;
    -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
    *) echo "leadwatch.sh: unknown argument $1" >&2; exit 2 ;;
  esac
done
[ "${#UNITS[@]}" -gt 0 ] || UNITS=('lane-*')

snap_units() { systemctl --user list-units "${UNITS[@]}" --no-legend --plain 2>/dev/null | awk '{print $1}' | sort; }
snap_files() {
  [ "${#FILES[@]}" -gt 0 ] || return 0
  find -L "${FILES[@]}" -maxdepth 1 -type f \
    \( -name '*.png' -o -name '*.jpg' -o -name '*.mp4' -o -name '*.md' \) 2>/dev/null | sort
}

prev_units=$(snap_units); prev_files=$(snap_files); last_beat=$(date +%s)
declare -A prev_proc
for p in "${PROCS[@]}"; do prev_proc["${p%%=*}"]=0; done

while true; do
  units=$(snap_units)
  gone=$(comm -23 <(echo "$prev_units") <(echo "$units") | tr '\n' ' ')
  [ -n "${gone// /}" ] && echo "[UNIT ENDED] $gone"
  prev_units=$units

  files=$(snap_files)
  added=$(comm -13 <(echo "$prev_files") <(echo "$files") | head -8 | tr '\n' ' ')
  [ -n "${added// /}" ] && echo "[NEW FILES] $added"
  prev_files=$files

  for p in "${PROCS[@]}"; do
    name=${p%%=*}; regex=${p#*=}
    if ps -eo args | grep -qE -- "$regex"; then
      [ "${prev_proc[$name]}" = 0 ] && echo "[$name STARTED]"; prev_proc[$name]=1
    else
      [ "${prev_proc[$name]}" = 1 ] && echo "[$name CLOSED]"; prev_proc[$name]=0
    fi
  done

  for d in "${DISKS[@]}"; do
    path=${d%:*}; min=${d##*:}
    free=$(df --output=avail -BG "$path" 2>/dev/null | tail -1 | tr -dc 0-9)
    [ -n "$free" ] && [ "$free" -lt "$min" ] && echo "[DISK] $path ${free}G free"
  done

  now=$(date +%s)
  if [ "$BEAT" -gt 0 ] && [ $((now - last_beat)) -ge "$BEAT" ]; then
    echo "[HEARTBEAT $(date +%H:%M)] running: $(echo "$units" | tr '\n' ' ')"
    last_beat=$now
  fi
  sleep "$INTERVAL"
done
