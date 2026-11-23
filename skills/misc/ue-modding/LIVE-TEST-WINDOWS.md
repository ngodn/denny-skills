# Scripted live test windows

Use this when an agent launches the user's game by itself to test a build: a scripted run that stages
files, drives the game, records, restores and reports, with nobody at the keyboard. A window is
expensive (minutes of the user's machine, a visible game) and a failed one teaches little, so almost
all of the work happens before the launch.

## Before the launch

- **Rehearse the whole script offline against the real mod code.** Build a fake host that answers the
  bridge calls the script makes, load the real extension or script code against it, and run every mode
  end to end. Two windows in a row failed on things a rehearsal catches in seconds: a command sent as
  a service action when it had to go inside another call, and a control the game refused as read-only.
- **Every action reads its effect back.** Set a value, read it; press play, read the playing state; wear
  an outfit, read the mesh. An action with no readback is a hope, and the take recorded after it shows
  something else.
- **Check that the test can fail.** A pass message that reads "impacts off: property is missing" is a
  pass on a body that never had the feature. Each mode asserts its precondition (the asset under test is
  the one loaded, the property exists) before it measures.
- **Modes are independent.** A failed mode is logged and skipped; the others still run. One mode's time
  limit must not cut another mode's takes.
- **Stage by hash, snapshot first.** Record every file the window replaces, with hashes, and refuse to
  launch when free disk is under the snapshot's needs. The newest dependency (core DLL, shared pack) is
  staged together with the asset that requires it.
- **The machine is free.** Check for the user's own game or app and for the workspace or monitor the
  window will use, right before launch, not when the script was written.

## During the window

- No fixing inside a window. A wrong result ends the mode; the fix happens offline, followed by a new
  rehearsal. At most one launch per hour keeps this honest.
- Record the game window only, never the desktop. Keep the game on the monitor and workspace the user
  agreed to and move nothing between monitors.
- Background work freezes for the length of the window, and for the first start after new packs are
  installed: that start can run the full shader compile (17 minutes for 22,000 shaders in one case; the
  second start skipped it). Background load during that compile multiplies it and looks like a broken
  install to the user.

## After the window

- **Restore, then verify by count and hash**, then free devices and delete staging. A restore must keep
  caches the game grew during the run (a pipeline or shader cache): throwing the grown cache away makes
  the user's next start recompile everything.
- **Captures must show the subject.** Run an automatic check (subject in frame, large enough, lit) and
  build a frame sheet per take; the agent looks at the sheet before calling a take usable. A recording
  of a tiny dark figure passes every script check and proves nothing.
- A check that fails good takes is a bug in the check: fix it before the next window, or real failures
  hide among the false ones.
- What passed is installed for the user by hash with a rollback set (the replaced files, a manifest and
  a restore script), confirmed by one start that reaches the title. What did not pass stays a candidate.
- Report in the user's terms: what was seen, what failed and why, what is installed now, how to undo it.
