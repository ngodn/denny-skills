---
name: desktop-control
description: See and drive the user's real Hyprland (Wayland) desktop from a shell, with screenshots plus mouse clicks, scrolls and typing, when no computer-use tool is available. Use when asked to click, pick an option, switch a tab or window, or check what is on screen in a desktop app, including answering a question box in another agent session's IDE panel.
---

# Desktop control on Hyprland

Three pieces, none of which need installing beyond what Hyprland setups usually have:

- **See:** `grim` screenshots, via `scripts/shot.sh` in this skill's folder.
- **Point:** Hyprland moves the cursor; a short-lived uinput mouse clicks or scrolls. Both are in `scripts/pointer.py`.
- **Type:** `wtype` sends text to the focused window. It has not been exercised on this setup yet, so check the screenshot after the first use.

Run the scripts in place with `python3 -I` / `bash`; they take paths and coordinates as arguments.

For work inside Google Chrome, call the Skill tool with "office-browser" instead: it acts inside the page without touching the user's mouse or focus.

## Before touching anything

1. Confirm the tools: `command -v grim hyprctl wtype`, and that `/dev/uinput` is writable by this user (`getfacl /dev/uinput`). With no write access, the clicker fails; tell the user rather than reaching for root.
2. Tell the user in one line that you are taking the pointer. The mouse is shared with them, and a click while they are moving it lands somewhere else.
3. Every choice you click must be one the user made. When a box holds a question they have not answered (multi-tab question boxes often do), stop and ask them, then come back.

## The loop

Each action is one turn of: locate, screenshot, act, screenshot. An action is done only when a fresh screenshot shows the expected change (tab active, radio filled, dialog gone). A click with no visible change is a miss, not a success.

1. **Locate.** `hyprctl monitors -j` gives each monitor's `name`, `x`, `y`, `width`, `height`, `scale`. `hyprctl clients -j` gives each window's `class`, `title`, `monitor`, `at`, `size`. The target's monitor tells you which output to capture.
2. **Screenshot.** `scripts/shot.sh OUT.png MONITOR 0.6` for a whole monitor at 60% (cheap to view), or `scripts/shot.sh OUT.png -g "X,Y WxH"` for a full-size crop of a region in global layout pixels. Read the PNG to see it.
3. **Convert coordinates.** Screenshot pixels are not layout pixels. Measure the factor from the image itself rather than trusting the scale flag, since monitor scaling changes it:
   - whole monitor: `f = image_width / (monitor.width / monitor.scale)`, then `X = monitor.x + px / f`, `Y = monitor.y + py / f`
   - region crop: `f = image_width / W`, then `X = region_x + px / f`, `Y = region_y + py / f`
4. **Act.** `scripts/pointer.py click X Y` (also `--button right`, `--double`), `scripts/pointer.py scroll X Y N` (positive scrolls up, negative down), `scripts/pointer.py move X Y`. For text, click the field first, then `WAYLAND_DISPLAY=<socket shot.sh reported> wtype 'text'`.
5. **Verify.** Screenshot again, a tight region crop around the target is enough. Zoom in with a crop when a small control (radio button, checkbox) is ambiguous at 60%.

When done, park the cursor where it was (`hyprctl cursorpos` before you start) and, if you switched the user's tab or window, switch it back.

## Gotchas

- **Wrong Wayland socket.** The shell's `WAYLAND_DISPLAY` can point at a nested compositor, and grim then fails with "compositor doesn't support the screen capture protocol". `shot.sh` tries every `wayland-N` socket under `$XDG_RUNTIME_DIR` and prints the one that worked; reuse that socket for `wtype`.
- **Hyprland dispatch syntax.** Hyprland 0.56+ takes Lua: `hyprctl dispatch 'hl.dsp.cursor.move({x=100,y=200})'`. The old `movecursor 100 200` form errors there. `pointer.py` tries Lua first, falls back, and checks `hyprctl cursorpos` either way.
- **`wtype` drops characters.** Typing into a VS Code chat box lost every hyphen together with the letter before it, and apostrophes too (`msii-a8` came out as `msia8`, `don't` as `dont`). Plain words came through fine. For names, paths or punctuation, put the text on the clipboard with `wl-copy` and paste it (`wtype -M ctrl v -m ctrl`; the paste route is not yet verified here), then check it in a screenshot before submitting.
- **grim region format** is `"X,Y WxH"` (comma, space, `x`). Anything else is "invalid geometry".
- **uinput device warm-up.** A new virtual mouse needs about half a second before the compositor routes its events; `pointer.py` waits. Events sent sooner vanish.
- **Claude Code question boxes in VS Code.** A queued cross-session message is not read until the receiving session's open question box is answered, so clicking the box is the only way to unblock it. Picking an option on one question tab auto-advances to the next tab; **Submit answers** turns active only once every tab has a choice. Confirm afterwards in the session's transcript (`~/.claude/projects/<dir>/<session>.jsonl`, last `tool_result`) that the answers recorded match what the user chose.
