# Game input and screenshots without taking focus

Use this reference for authorized live gameplay checks while the user works in
another application. Prefer input addressed to the game window over foreground
activation. Existing permission to test the game remains valid; this technique
does not grant permission to control an unrelated application.

## Linux, Wine/Proton and XWayland

`xdotool` can address a specific X11 window. This worked for aim and primary/
secondary fire in a Proton Unreal game, including while an editor or browser
held desktop focus. It is a tested route to try first, not a guarantee for every
game, native Wayland window, Wine build or input binding.

1. Resolve the current shipping-game process from its executable identity. Find
   visible windows for that PID with `xdotool search --onlyvisible --pid PID`.
   Inspect the window identity if there is more than one match. Launchers and
   helper windows can share the same Steam application class.
2. Validate `xdotool getwindowpid WINDOW_ID` against that process before sending
   input. Re-discover after a process/window restart. X11 window IDs, compositor
   addresses, Linux PIDs and engine object handles are different identifiers.
3. Send every press **and release** with an explicit `--window WINDOW_ID`:

   ```text
   xdotool keydown --window WINDOW_ID Control_L
   xdotool keyup --window WINDOW_ID Control_L
   xdotool mousedown --window WINDOW_ID 1
   xdotool mouseup --window WINDOW_ID 1
   ```

   Button 1 is left, 3 is right, and 2 is middle. Establish the game's actual
   bindings before choosing keys or buttons. Bound the hold duration and release
   owned input in `finally`, including assertion failures and interruption.
   Keep cleanup addressed to the same validated game window. If its process has
   exited, do not send cleanup to another application's foreground window.
4. Read the game's key state or action state, then check the intended effect:
   drawn/stowed socket, weapon visibility, action interruption, resource use or
   projectile lifecycle. Record each separately. A focus transition can release
   input; an unaccepted press is an inconclusive probe, not a weapon defect.

This route does not need `windowactivate`, compositor focus commands, pointer
warping or `--clearmodifiers`. Leave those out so the user's typing and pointer
stay with their work. Record desktop focus before/after the first smoke check.
The user can change focus independently; do not force an old window back over
their newer choice. If targeted input is rejected, retain that result and choose
another authorized route instead of silently switching to global input.

The [xdotool upstream manual](https://github.com/jordansissel/xdotool/blob/master/xdotool.pod)
documents window targeting and its SendEvent caveats. Mouse events use the
current pointer coordinates, so a gameplay binding that works in the background
does not prove that coordinate-sensitive UI clicks will work the same way.

## Screenshots

Prefer the engine's native screenshot command through an already verified
runtime bridge. For Unreal, discover the installed signature of
`KismetSystemLibrary.ExecuteConsoleCommand`, resolve the current world/controller,
and invoke `shot showui` when that game supports it. Find the actual output path
under the game's Saved/Screenshots directory, including the Proton prefix when
applicable. Do not assume every title uses the same folder or platform name.

Record the directory contents before requesting a capture, wait with a timeout
for a new completed image, and archive it beside the request and runtime state.
Verify freshness and inspect the image. This avoids desktop screenshots that
include unrelated work. A verified Steam capture route is another option, but
its notification can appear in recordings.

## Keep the test honest

Capture the current loadout, appearance, relevant settings and resources before
mutation. Restore owned changes through the game's normal APIs and compare
readback afterward. Preserve newer user state. Normal autosaves can run during
testing; a preflight save backup does not make gameplay a transaction.

Check active cheats before interpreting a resource measurement. A periodic
refill can conceal a shot's cost. If necessary, temporarily disable only the
relevant refill, verify its state, and restore it afterward. Allow weapon-specific
draw/wind-up time; a too-short click is not evidence that a weapon cannot fire.
Snapshot animation/visibility and firing separately. Resource expenditure alone
does not establish projectile impact or damage to an enemy.

Keep game builds, object paths, bindings, concrete scripts and failed attempts
in the project's evidence log. Use that accepted fixture on later visits instead
of rediscovering the input route or copying stale process/window identifiers.
