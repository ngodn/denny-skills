#!/usr/bin/env bash
# Screenshot the real Hyprland desktop, whichever Wayland socket it is on.
#   shot.sh OUT.png [MONITOR] [SCALE]     whole monitor, e.g. shot.sh s.png DP-1 0.6
#   shot.sh OUT.png -g "X,Y WxH"          a region in global layout pixels, full size
set -euo pipefail
out="$1"; shift
if [ "${1:-}" = "-g" ]; then args=(-g "$2"); else args=(${1:+-o "$1"} -s "${2:-0.6}"); fi
# The shell's own WAYLAND_DISPLAY can be a nested compositor that refuses
# capture, so try each socket until grim succeeds.
for sock in "${WAYLAND_DISPLAY:-}" $(ls "$XDG_RUNTIME_DIR" | grep -E '^wayland-[0-9]+$'); do
  [ -n "$sock" ] || continue
  if WAYLAND_DISPLAY="$sock" grim "${args[@]}" "$out" 2>/dev/null; then
    echo "$out (WAYLAND_DISPLAY=$sock)"; exit 0
  fi
done
echo "no Wayland socket allowed capture" >&2; exit 1
