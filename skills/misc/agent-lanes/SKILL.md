---
name: agent-lanes
description: Run helper agents (Codex exec lanes, Gemini, research subagents) from a lead session without stalling the main task. Use when briefing, launching, watching, correcting or stopping a lane, sharing a GPU or other machine resource with a lane or with the user's own app, or sending agents to do web research.
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
