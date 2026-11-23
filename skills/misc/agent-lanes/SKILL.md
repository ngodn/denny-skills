---
name: agent-lanes
description: Run helper agents (Codex exec lanes, Gemini, research subagents) from a lead session without stalling the main task. Use when briefing, launching, watching, correcting or stopping a lane, sharing a GPU or other machine resource with a lane or with the user's own app, keeping lanes working through a usage limit, or sending agents to do web research.
---

# Agent lanes

The lead owns the goal; a lane is a helper on one slice of it. The user's real target keeps moving no
matter what a lane is doing.

## Lead rules

- **The real target first.** A lane's test material (a neutral sample clip, a fixture) is for testing the
  lane's own code. The lead works on the actual input in parallel, never after the lane finishes.
- **Fill the gap yourself.** When a lane cannot do part of the work (it declines the content, lacks a
  tool, is blocked), the lead does that part right away instead of waiting or re-briefing around it.
- **Blocked on a resource?** Do the CPU-side work on the real target (setup, decoding, cropping,
  scripts, docs) and start the blocked stage the moment the resource frees. Check the resource yourself
  rather than waiting to be told.
- **Never sit in a foreground wait.** The lead's own builds, test suites, stagings and watch loops run
  as tracked background runs with a hard timeout, and the lead keeps working; a live probe gets a short
  timeout and fails fast. A two-minute foreground wait looks to the user like nothing is happening, and
  a broken script wastes the whole wait.
- **Shared tools are queued, not raced.** A single-instance tool other sessions also use (an engine
  editor, a GPU job) gets a background job that waits for it to be free. Run a build that depends on a
  lane's output after the lane finishes, so it runs once.
- **Queue on a lock, not on a poll.** A job that polls for "no editor process" starves while other lanes
  start runs back to back (one waited 37 minutes behind a chain of two-minute cooks), and two polling
  jobs both start in the same free gap. Have every lane run the tool through `resource_lock.sh <name>`
  (call the Skill tool with "agent-comms"), and when one job blocks the user's next step, tell the other
  lanes to hold theirs until it is through.

## Brief

- Say plainly what the product is and what the lane's part is. A lane that sees only neutral engineering
  is told so, with the reason, never a cover story.
- Put resource rules in the brief before launch: which GPU work is allowed and when (a game or editor the
  user is using always wins), no installs outside its own vendor folder, where outputs go, what it must
  never touch.
- Put a budget in the brief: expected case count and wall time (cases x seconds per case / free cores),
  worked out before launch. A blanket rule ("render every case over 1 cm", "every slider at every step")
  multiplies across the grid, so state a cap instead: a coarse grid with bisection for thresholds, renders
  limited to what a person will look at.
- On a shared machine, low-priority workers starve. Before a lane raises its priority, check what else
  runs (another session's game test or frame-time measurement wins) and settle it with the user.
- Give the lane its own build directory and its own output folder; two writers in one build tree
  corrupt it. A full build can outlast the lane's per-command time limit (it is killed with exit 130):
  brief the lane to build incrementally and to run long builds with output to a log it then reads.
- End with done criteria, a report path and a short fixed-size summary, then "stop".

## Launch and watch

- Launch with the harness's background-run option so its exit notifies the lead; a detached `nohup` run
  finishes unseen.
- Point the watcher at the exact run folder once it exists. A watcher that snapshots "current runs" and
  waits for a new one races the launch: if the run folder appears first, it waits forever and the lane
  runs unwatched.
- Arm a watcher on the lane's event stream for its messages, failed commands, stalls and exit; re-arm it
  when it expires. Relay to the user only what changes the plan; a failed `grep`/`rg` that matched
  nothing is noise, so check before reporting it.
- Before reporting a lane's state, read its latest output.
- A job that waits for "finished" in a log must count only lines written after it starts (record the line
  count first) and also check that the process has exited. Logs keep earlier runs' "ALL DONE" lines; a
  plain `grep` fired a release flag seven hours early and other sessions nearly launched a game on it.
- Detect a running game by its executable path in the first argv field
  (`ps -eo args | grep -qE '^[^ ]*Game-Win64-Shipping\.exe'`). The process can rename itself (Mortal
  Shell II shows as `GameThread`), so `pgrep -x` misses it, and `pgrep -f` also matches shells that only
  mention the name.

## Lanes that keep going without the lead

A usage limit stops every lane and the lead in the same minute, and by default nothing moves again until the user returns and says "continue". Set a long job up so that only the lead waits:

- **Each lane in its own unit, with auto-resume watching the root.** Start heavy lanes with `run_lane_unit.sh` and install `autoresume.py service install <root>` once per machine (call the Skill tool with "agent-comms" for both). A lane cut off by the limit then restarts by itself a few minutes after the reset.
- **State on disk, always.** Brief every lane to keep its report file current as it works (done, running, next, open, and the command that continues a batch). A resumed lane starts from that file, and so does a lead that comes back hours later.
- **Machine work runs through the limit.** A solve, render or build that needs no model for hours goes into its own unit (`systemd-run --user --slice=background.slice --unit=<name> ...`) with a log and a state file. As a child of the lane it dies with the lane's session; as a unit it is still running when the lane is resumed, and the lane's first step back is to check on it.
- **Chain the work in the brief.** The lead cannot hand out the next job while it is itself cut off, so a lane's brief names what follows each finished stage. A lane that exits 0 is finished and stays stopped until the lead returns.
- **Fewer, cheaper lanes last longer.** Four high-effort lanes on the top model emptied a five-hour window in ninety minutes. Give each lane the cheapest model and effort that does its job, and say in the brief why a lane needs more.
- **A deliberate stop stays stopped:** `touch <run folder>/no-autoresume` before or after stopping a lane the limit already cut off.

## Leading for hours

The user should never have to ask where things stand. Over a long job the lead's work is a loop: an event
arrives, the lead looks, decides, hands out the next job, and says what changed.

- **Three wake sources, all armed.** `leadwatch.sh` under Monitor (a lane unit ended, a result file
  appeared, the game started or closed, disk is low, a heartbeat), `mail.py watch <lead> --ack` under
  Monitor for lane mail, and a recurring scheduled prompt in the lead's own session (cron, every 30
  minutes) that runs the same checks. A Monitor expires after 30 minutes: re-arm both on every expiry
  notice. The scheduled prompt is what brings the lead back after a usage limit stopped it together
  with the lanes; without it the lead slept through a night of finished lanes.
- **Report on change, in the user's terms.** After each event tell the user what they can now see or
  decide, with the file to open. Nothing changed is one line. Lane names, run ids and tool names stay out.
- **Look before you pass on.** Open every render, sheet or recording a lane calls finished. If it does not
  read as the intended thing at first glance, send it back with what you see first, in order, and what
  would make it pass. Lanes grade their own work kindly; a lane that writes "not ready, here is why" is
  doing it right and gets a decision, not a nudge.
- **Answer at once, with the invariant.** A lane's question is answered in the same turn. An approval names
  what must still hold afterwards (contacts stay put, hands do not move, the released file is untouched)
  and the check that proves it, so the lane does not optimise one number and break another.
- **Ask where a fault comes from before accepting a rule that hides it.** "The joint never moves" can be
  the source data or our own conversion dropping it. One cheap look at the source decides whether the
  fix is a repaired mapping or a synthetic rule.
- **Lanes end their turn when they only wait.** An idle turn on a mailbox watch still spends the shared
  limit. Run `mailwake.sh` (call the Skill tool with "agent-comms") so mail wakes a stopped lane, and brief
  lanes to read their mailbox before ending a turn. Mail whose first line starts with `NOTICE` informs
  without waking; a job that must wake its lane on completion sends plain mail, or the lead wakes the lane.
- **A lane that ignores mail or is about to do harm:** kill its exact agent pid and resume it with the
  order. A killed run leaves no `id.txt`, so resume with the session id from an earlier run folder.
- **Freeze background work while the user's game or app runs.** `systemctl --user kill -s STOP <unit>`
  pauses a solver or render unit without losing it, `-s CONT` continues it. Long jobs check for the game
  themselves every few seconds; a shader compile ran three times longer under a full background load.
- **Record the user's decisions where lanes read them** (the product's decision table), numbered, with the
  user's own words. Then relay each to the lanes it changes. A decision that lives only in the chat is
  lost at the next context reset.
- **What "do whatever you recommend" covers:** choices inside the goal. It does not cover launching the
  user's game while they use the machine, publishing, or deleting their data; those keep their own rule.

## Lanes the user can see (Orca)

When the lead runs inside Orca (`ORCA_TERMINAL_HANDLE` is set), a headless lane is invisible to the user, who uses Orca to see all work in one place. Start lanes there with `run_lane.sh --orca` (call the Skill tool with "agent-comms" for the command) unless the lane needs a vendor stream on disk. Every rule in this skill still applies; what changes:

- **Launch:** the command is launcher and watcher in one. Run it as a tracked background run, or under Monitor to get each line as it happens. Exit 0 is the lane's turn ending, exit 3 is a box nobody answered within two minutes.
- **A new tab in a folder the agent has not been trusted in stops on a trust box** (the home folder asks every session). The watcher prints it; the brief is delivered once it is answered.
- **Correct:** `--resume <handle> "<correction>"` types into the running lane. The addendum, quiet-moment and kill steps below are for headless lanes only.
- **Stop:** `orca terminal send --terminal <handle> --interrupt`, or `orca terminal close --terminal <handle>` to end the tab. `pid.txt` holds the watcher, so killing it leaves the lane running.
- **Show progress where the user looks:** `orca worktree set --worktree active --comment "<state>"` puts one line on the workspace card; update it at each checkpoint.
- **Want Orca to wake you with the result instead of watching?** That is an Orca worker: call the Skill tool with "orchestration". Its rule against polling covers its own mailbox; this watcher only reads agent state.

## A lane on another machine

When the work belongs on the user's other machine (its GPU is free, the repo or the app lives there), start the lane there with `remote.py lane <host> ...` (call the Skill tool with "agent-comms" for the command and for `<lane>@<host>` mail). Every rule in this skill still applies; what changes:

- **The brief travels, your files do not.** The lane sees only its own machine. Name paths that exist there, or copy inputs first with `remote.py push`, and have it send results back in mail or name files for you to `remote.py pull`.
- **Check that machine before you launch:** `list_peers.py --host <host>` for who works there, and `remote.py run <host> 'nvidia-smi'` or a game check for what is busy. Its quiet-time and resource owners are separate from this machine's.
- **Watch** with the command `remote.py lane` prints; it streams over SSH and ends when the lane does. If the link drops, the lane keeps running: run the watch command again.
- **Correct** with `mail.py send <lane>@<host> "<correction>"` for a lane that checks its mailbox between steps, or `--orca` when it was started with `--orca`. **Stop** with `remote.py run <host> 'kill $(cat <run>/pid.txt)'`.

## Correct or stop a running Codex exec lane

Exec lanes do not re-read their brief. One may happen to reopen it and pick up an addendum; treat that as
luck and stop and resume as soon as the addendum is written. To change course:

1. Append "Addendum N" to the brief.
2. Find the thread id: the first `"thread_id"` in the run's `events.jsonl`.
3. Stop at a quiet moment: `codex` keeps permanent children (MCP servers such as `rea mcp`,
   `codex-code-mode-host`), so "no children" never happens. Wait until it has no direct `bash` child for
   about 2 s, then kill the exact `codex` pid. A lane running hour-long tool commands never goes quiet:
   kill the exact `codex` pid anyway. Its job processes keep running; stop only the jobs whose scope
   changed and list the survivors' pids in the resume message so the lane adopts them instead of
   starting duplicates.
4. Resume: `codex exec resume <thread> "Read Addendum N at the end of your brief and follow it."`
   with the same flags, again as a tracked background run with a watcher.

`codex queue` never reaches a running exec turn; how each kind of agent actually receives a message is in
the `agent-comms` skill (call the Skill tool with "agent-comms").

When the lane is about to harm something now (GPU work while the user plays, writing outside its folder),
skip the quiet-moment wait: kill the tool subtree it started (compilers, servers, python), then the
`codex` pid, then resume. Leave other sessions' processes alone: list the lane's process tree
(`pstree -p <pid>`) and kill by exact pid, never `pkill -f` (it matches its own command line).

## Research agents

- Read the settled decisions first. Before researching rights, licences or store and platform rules,
  read the product's decision record (its GOAL.md decisions table) and other sessions' notes; follow a
  settled decision instead of re-researching it.
- WebSearch and WebFetch only. Browser automation tools open pages in the user's own browser.
- Primary sources: repos, LICENSE files, model cards, official policy pages. Read the whole page before
  concluding a plan breaks a rule; policies often hold an exception further down. State a caveat once,
  then follow the owner's decision.
- Each agent writes a cited file and returns a short summary; the lead verifies any fact that changes a
  decision on the source page itself before relaying it.
