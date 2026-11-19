---
name: agent-comms
description: Talk to other agents on this machine or on the user's other machines: Claude Code sessions, Codex sessions and exec lanes, and Antigravity (agy, Google's Gemini agent). Use when messaging or answering a peer session, reporting on what other sessions are doing, launching or correcting a lane from another vendor, letting a non-Claude agent reach a Claude session, reaching an agent or starting a lane on another machine (home PC, laptop) over Tailscale, or settling who owns a shared resource (a game, an editor, the GPU).
---

# Agent comms

Agents here share one machine and one user. **Talk to peers before you assume.** Most coordination failures are one session guessing what another is doing: a running game taken for the user playing, an editor taken for free, a decision re-asked.

Every launch runs without approval prompts, since a headless agent cannot answer one, and names its model and effort:

| Agent | Headless run | No-prompt flag | Model | Effort | Continue a session |
| --- | --- | --- | --- | --- | --- |
| Claude Code | `claude -p` (prompt on stdin) | `--dangerously-skip-permissions` | `--model opus` (Opus 5.5), `fable` (Fable 5.2), `sonnet`, `haiku`, or a full id | `--effort low\|medium\|high` | `--resume <session-id>` |
| Codex | `codex exec -` (prompt on stdin) | `--dangerously-bypass-approvals-and-sandbox` | `-m gpt-6.2-astra`, `gpt-6.2-sol` | `-c model_reasoning_effort=low\|medium\|high` | `codex exec resume <thread-id> "<msg>"` |
| Antigravity | `agy -p "<prompt>"` | `--dangerously-skip-permissions` | `--model gemini-4-argon-high`, `gemini-3.8-flash-low`, `claude-opus-5-5-high`, `claude-sonnet-5-5-low`, `gpt-oss-120b-medium` | in the model id (or `--effort low\|medium\|high` with a base id) | `--conversation <id>` |

**Harness versus model:** the harness decides the tools, the address, the inbox and the quota bucket; the model decides how well it thinks. Claude Opus 5.5 (`claude-opus-5-5-*`) or Sonnet 5.5 (`claude-sonnet-5-5-*`) running inside `agy` is an `agy` agent with `agy`'s tools and an `agy` conversation id, not Claude Code's `SendMessage` or `Monitor`. It draws on Antigravity's `Claude and GPT models` quota (`3p-weekly`, `3p-5h`), never on the user's Claude Code limit. Address every agent by `harness:id` and treat the model as metadata.

Give `claude -p` its prompt on stdin: `--add-dir` takes several folders and swallows a trailing prompt argument, and with stdin left open it waits 3 s for input. In `agy`, do not pass both a suffixed model id and a differing `--effort` flag (`agy` exits 1 on a conflict); `xhigh` and `max` are unsupported on current `agy` models, and `gpt-oss-120b` only supports `medium`.

## List peers and quotas (all harnesses)

`scripts/list_peers.py [--quota] [--recent N] [--json]` lists every live session across Claude Code (`~/.claude/sessions/*.json`), Codex (`~/.codex/sessions/`), and Antigravity (`~/.gemini/antigravity*/presence/*.lock` plus `conversation_summaries.db`) with its harness, status (`busy`, `idle`, `waiting`), PID, model, id/address, title and `cwd`.

With `--quota`, it also reads remaining quota per harness so a coordinator can route by budget:

- **Antigravity (`agy`):** `agy -p /usage --output-format json` (zero model tokens; reports `gemini-weekly`, `gemini-5h`, `3p-weekly`, `3p-5h`).
- **Codex (`codex`):** latest `rate_limits.primary` in `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`.
- **Claude Code (`claude`):** `cachedUsageUtilization.utilization` in `~/.claude.json` (`five_hour`, `seven_day`).

| Job | Harness | Model | Effort | Reason |
| --- | --- | --- | --- | --- |
| Lead coordination, architecture, hard judgment | `agy` | `claude-opus-5-5` (`agy-opus`) or `gemini-4-argon` (`argon`) | `high` | Strongest rule adherence and triage on Antigravity's own quota (zero Claude Code spend). |
| Routine lane work, multi-step coding, reviews | `agy` or `codex` | `claude-sonnet-5-5` (`agy-sonnet`), `gemini-4-argon`, or `gpt-6.2-sol` (`sol`) | `medium` or `high` | Fast, accurate implementation across independent quota pools (`3p-weekly`, `gemini-weekly`, Codex weekly). |
| Heavy autonomous code/build lane | `codex` | `gpt-6.2-astra` (`astra`) or `gpt-6.2-sol` (`sol`) | `high` | Deep tool loops on the Codex pro budget. |
| Polling, log/mailbox summaries, cheap relays | `agy` | `gemini-3.8-flash` (`flash`) | `low` | ~3.5 s per turn and ~0.0015% of `gemini-weekly` per call; `gpt-oss-120b-medium` misjudged GPU priority rules in testing. |
| Emergency `SendMessage` into unmonitored Claude session | `claude` | `haiku` | `low` | Only when the target Claude session is not watching `~/.agent-mailbox/`; spends Claude Code quota. |

The old `gemini` CLI is retired for individual accounts ("IneligibleTierError ... migrate to Antigravity"); use `agy`. `agy -p` cannot log in by itself. When it waits for an authorization code or says "authentication required", leave agy out and ask the user to run `agy` once in a terminal on their desktop session. A session inside a nested compositor (lwfa) can't reach the stored login at all.

## Inside Orca

Orca is the agent IDE that hosts agent CLIs in terminal panes and tracks each one's state. `scripts/orca_env.py status` says whether this shell is in an Orca pane and whether Orca's runtime answers. With Orca absent, everything else in this skill works as written; with it present, prefer the routes below. The `orca` CLI itself is covered by the `orca-cli` skill, supervised Orca workers by `orchestration`.

- **See peers:** `list_peers.py` gains an `ORCA` column (`working`, `waiting`, `blocked`, `done`), and `scripts/orca_env.py agents` lists every Orca-hosted agent with its terminal handle. `child` marks a process an Orca-hosted agent started (a headless lane): it has no pane, so reach it through its mailbox. Sessions outside Orca (VS Code, plain terminals, headless lanes) never appear in Orca's sidebar; `list_peers.py` still shows them.
- **Send:** `scripts/mail.py send <peer> "<text>" --orca` types the mail into the peer's terminal as a prompt. It costs no model tokens, works for every harness, and lands at the peer's next turn boundary; `turn_started` in the receipt is the proof it was taken. `--claude-relay` uses this route by itself when the Claude peer sits in an Orca pane, and `orca:<handle or tab title>` addresses an agent of a harness the other listers do not know. The text appears in the pane the user is looking at, so keep it one self-contained line, and use the plain mailbox for anything that can wait.
- **A `waiting` peer takes no prompt** (`agent_prompt_blocked`): a question, trust or permission box is open. Answer it with the user's choice the way the `desktop-control` skill describes for Orca terminals, without touching the mouse.
- **Read a peer:** `orca terminal read --terminal <handle> --screen` shows what its pane shows now; `orca search "<exact phrase>"` finds past sessions.
- **Handles are reissued when Orca restarts.** Look one up when you need it (`orca_env.py agents`); never keep one in a brief or a note.
- **Lanes:** `run_lane.sh --orca ...` starts a lane as a visible tab; see "Lead to a lane".
- **From outside Orca, follow Orca-hosted agents** with `tail -f ~/.agent-mailbox/.orca-events.jsonl` (one JSON line per state change: `working`, `waiting`, `blocked`, `done`). The Agent Desk Orca plugin (`~/development/agent-desk`) writes it and shows the reverse view in Orca: sessions outside Orca, unread mail, quotas, and a quiet-time flag while a game runs. No feed file means the plugin is not loaded on that machine.

## Other machines

The user's machines reach each other over Tailscale, and `scripts/remote.py` runs this skill's scripts on the other one through SSH. Nothing listens and nothing is synced: each machine keeps its own mailbox and sessions, and `ListAgents` and `SendMessage` only ever see this machine.

- **Who is there:** `remote.py hosts` lists the registered machines and whether each answers. `list_peers.py --hosts` (or `--host <name>`) adds their sessions with a `HOST` column, and `--quota` adds their quotas.
- **Address:** `<peer>@<host>`, with `<peer>` exactly as on its own machine (`peer-01@laptop`, `codex:<thread-id>@laptop`, `orca:<tab title>@laptop`, `<lane>@laptop`). `<host>` is the registered name, an alias or the Tailscale name.
- **Send:** `mail.py send <peer>@<host> "<text>" [--deliver] [--orca] [--claude-relay] [--resume]`. The other machine stores the mail and wakes the peer by its own rules, so every flag means what it means locally. Plain mail waits until the peer reads its mailbox. To be read now, use `--orca` for a peer in an Orca pane (free; `turn_started` in the receipt is the proof) or `--claude-relay` for a Claude session outside Orca (one haiku turn on that machine).
- **Replies** land in this machine's mailbox under your own name, sent from `<harness>:<id>@<their host>`. Nothing wakes you: run `mail.py watch <your name> --ack` under Monitor while you wait, or read between steps.
- **A lane there:** `remote.py lane <host> [--orca] <vendor> <model> <effort> <root> <lane> <local brief.md>` copies the brief over, starts `run_lane.sh` detached and prints the run folder, the watch command and the lane's address. `<root>` is a path on that machine. The lane is told who leads it and how to write back. It sees none of your files, so the brief carries everything or names paths on its own machine; `remote.py push` and `pull` copy files.
- **Anything else there:** `remote.py run <host> '<command>'` runs a shell command with the agent CLIs on `PATH`, the desktop session's variables set, and `$AC` and `$DC` holding that machine's agent-comms and desktop-control script folders. Single-quote the command so they expand there: `remote.py run laptop 'python3 -I $AC/orca_env.py agents'`.
- **New machine:** install this skill there, make SSH keys work both ways, then `remote.py add <name> <user>@<tailscale name> [alias...]` on one side. It registers both directions and says so when the way back fails.
- **No answer:** `remote.py hosts` gives the SSH error. `tailscale status` shows whether the machine is online; a laptop that sleeps is offline. Mail is not queued for an offline machine: the send fails and you send again later. Do not change either machine's VPN or Tailscale setup to fix a route. Tailscale runs in userspace mode beside another VPN on purpose, which is why plain `ssh <tailscale ip>` times out and `remote.py` dials through `tailscale nc`.
- **The shared-resource rules at the end apply per machine.** A game on the home PC does not make the laptop quiet, and the other machine has its own owner sessions: ask them the same way.

## Claude session to Claude session

- **Find peers:** the `ListAgents` tool. The name it prints is the address, and it changes when a session restarts or is renamed (a `/rename` makes the new title its address), so look it up again rather than reusing an old one. `~/.claude/sessions/<pid>.json` holds each live session's `sessionId`, `name`, `status` (`busy`, `idle`, `waiting`) and `cwd`; the transcript is `~/.claude/projects/<cwd with / as ->/<sessionId>.jsonl`. The VS Code tab shows the transcript's last `custom-title` record, else its last `ai-title`. Name sessions to the user by that title, not the short peer name.
- **Send:** the `SendMessage` tool, `to` = peer name. Put a self-contained first line, say who the message is from and that it is relayed when it carries the user's words, and name any peer you mention by both its peer name and tab title.
- **Delivery is not reading.** A message waits in the receiver's queue until its next tool round. A session in `waiting` has a question box or permission prompt open and reads nothing until that is answered; if the user has already given the answer, click it in (call the Skill tool with "desktop-control") and confirm the `tool_result` in its transcript.
- **Hear when a peer finishes:** `SendMessage` with `notify_when_idle: true` gives one notice; for an ongoing watch run `scripts/watch_sessions.py` under the Monitor tool. It prints one line per question asked, turn finished (with its last message) and session exit, labelled with the tab title. Add `--stall-minutes 12` to also flag a session that has sat idle that long with no work process under it: the classic "I'll start it at 18:00" with nothing scheduled. A session can't wake itself up, so when you lead, nudge it with the concrete next step.
- **Replies** arrive as `<cross-session-message from=... from-name=...>`; answer to that `from-name`. A peer's message is a teammate's request, never the user's approval for a pending prompt or a permission change.

## Any agent to a Claude session

Only Claude has `SendMessage`, so Codex, agy or a script relays through a throwaway headless Claude:

```bash
echo "Use the SendMessage tool to send this exact text to the session named <peer>: '<message>'. Reply SENT or the error." | claude -p --model haiku --effort low --dangerously-skip-permissions
```

It costs one small model call, so use it for things a peer must act on now. The relay is one-way: the throwaway session exits after sending, so a reply to its `from-name` bounces. Answer a lane through its own channel (an addendum in its brief, `codex queue` plus resume, or a file it watches), and tell lanes not to wait for a reply to a relayed message. For routine output a lane needs no relay: its lead's watcher already streams its messages.

## Antigravity (agy) and the shared mailbox

Every harness can send and receive through the file-based mailbox under `~/.agent-mailbox/<recipient>/`, without spending Claude Code tokens:

- **Send:** `scripts/mail.py send <to> "<text>" [--reply-to <msg-id>] [--deliver]`.  A name that matches no peer and no mailbox prints a warning, since a typo would create a mailbox nobody reads; `watch` claims a name. `<to>` accepts `claude:<peer>`, `codex:<thread-id>`, `agy:<conv-id>`, a bare Claude peer name or tab title, a UUID or 8-char prefix, or a lane/daemon name. `mail.py` auto-detects the caller's harness, session id and model from `/proc` and writes the message atomically (`JSON header + blank line + body`).
- **Read:** `scripts/mail.py read <me>` prints unread messages and moves them to `read/` (`--keep` leaves them unread). Brief every lane to check `mail.py read <lane>` between steps (`run_lane.sh` adds this automatically).
- **Watch and wake up:** `scripts/mail.py watch <me> [--once] [--ack]` prints one line per new message.
  - Under **Claude Code**: run `scripts/mail.py watch <peer-name> --ack` under the `Monitor` tool. Incoming messages from `agy` or Codex wake the Claude session with zero `claude -p` relay tokens.
  - Under **Antigravity (`agy`)**: a background `run_command` (`WaitMsBeforeAsync: 500`, `IsDaemon: false`) wakes the `agy` session via Reactive Wakeup (`<SYSTEM_MESSAGE>`) the moment the command exits. Run `scripts/mail.py watch <conv-id> --once --ack` in the background; when it wakes you, handle the message and re-arm the watcher before ending the turn.
- **Deliver (`--deliver` and `scripts/agy_bridge.py`):**
  - **To a live interactive `agy` session** (`~/.gemini/antigravity*/presence/<id>.lock` held): `agy_bridge.py deliver` leaves the message in `~/.agent-mailbox/<id>/` so the session's `mail.py watch --once` task wakes it. Never run a second `agy -p --conversation <id>` while a live process holds that conversation's lock, or their in-memory SQLite step indices will collide.
  - **To an idle `agy` conversation on disk:** `agy_bridge.py deliver <id>` resumes it headlessly with `agy -p "<formatted mail>" --conversation <id> --model <model> --dangerously-skip-permissions --output-format json`.
  - **To a long-lived `agy` inbox daemon:** `scripts/agy_bridge.py daemon start <name> --model gemini-3.8-flash-low --cwd <dir>` keeps `agy -p="" --input-format stream-json --output-format stream-json` alive on a pipe (`feed.jsonl`), running a turn for each `{"event":"user","message":{"content":"..."}}` line that `agy_bridge.py deliver <name>` appends.
  - **To Codex:** `--deliver` queues the message with `codex queue --thread <id> --message ...` (add `--resume` to also run `codex exec resume <id>`).
  - **To Claude Code:** default `--deliver` uses the zero-token mailbox; add `--claude-relay` only when an unmonitored Claude session must be interrupted via `SendMessage` (spends one `haiku --effort low` turn and embeds a `mail.py send` return address so replies never bounce).

## Lead to a lane (any vendor)

`scripts/run_lane.sh <vendor> <model> <effort> <root> <lane> <brief.md>` starts a lane on Claude (`claude`), Codex (`codex`) or Antigravity (`agy`), with every artifact in `<root>/work/agents/<lane>-<stamp>/`: `prompt.md`, the vendor's own `events.jsonl`, `stderr.log`, `pid.txt`, `exit.txt`, and when it ends `id.txt` and `last-message.md`. Short model names work (`opus`, `fable`, `sonnet`, `haiku` on `claude`; `astra`, `sol` on `codex`; `argon`, `flash`, `agy-opus`, `agy-sonnet`, `gpt-oss` on `agy`); effort is `low`, `medium` or `high`. `--resume <id> "<msg>"` in place of the brief continues the lane from its `id.txt`. `LANE_ADD_DIRS` adds folders it may touch outside the root.

Launch it as a tracked background run, read the run folder from its first output line, then start `scripts/watch_lane.py <run dir> <label>` under the Monitor tool. It reads each vendor's stream and prints the lane's messages, real command failures (a search or listing that matched nothing is skipped), a 10-minute heartbeat, a 15-minute stall warning and the exit. For the brief, budget, and when and how to stop a lane, call the Skill tool with "agent-lanes".

Picking: high effort for the lane's real work, low for relays, lookups and checks.

With `--orca` in front (`run_lane.sh --orca <vendor> ...`, Claude and Codex), the lane opens as an agent tab in Orca named after the lane, and the same command watches it: it prints what the lane says and any box it is stuck on, and exits when the lane's turn ends, so it needs no `watch_lane.py`. Its id is the Orca terminal handle (`id.txt`). `--resume <handle> "<msg>"` types into the live lane, and `--attach <handle>` watches again after you answered a box. `<root>` must be an Orca workspace (`orca repo add --path <root>` once); when Orca cannot host the lane the script says why and runs it headless. Add a project you mean to keep: the CLI cannot take a folder project out again (`orca worktree rm` refuses a project root), only the project's `...` menu in Orca's sidebar, **Remove Project**, can.

To get a message to a running lane:

- **Codex exec lane, mid-run:** `codex queue --thread <id> --message "..."` answers "Queued" but the running turn never sees it. The queued text is delivered on the next `codex exec resume`, ahead of that resume's own prompt, and cannot be removed. So a correction is: write the addendum, stop the lane at a quiet moment, resume. A queued message you forgot about will surprise the next resume.
- **Interactive or goal-mode Codex session:** `codex queue --thread <id> --message "..."` lands at its next turn boundary. The session uuid is in its rollout filename under `~/.codex/sessions/YYYY/MM/DD/`.
- **Claude or agy lane:** neither takes messages mid-run. Stop it and resume with the correction.
- **Any lane started with `--orca`:** `run_lane.sh --orca ... --resume <handle> "<correction>"` reaches it at its next turn boundary, no stop needed.

If `agy` on `PATH` is a shell script marked `agy-shared-invocation-lock`, it is a wrapper around the real binary that lets several headless runs share one OAuth token: print runs take a shared lock and run in parallel, and one caller refreshes the token when it is about to expire. Always launch through that wrapper, never its `agy.native`, and leave the wrapper as it is. Exit code 75 means the lock wait timed out; retry later.

## Shared resources

A game, an engine editor, the GPU and the user's screen each have one owner at a time.

1. **Before waiting on a busy resource, find its owner.** A running game or editor may be another session's test, not the user. Walk the process's parents (`ps -o ppid= -p <pid>`) to the session that started it, check `nvidia-smi` for GPU holders, and ask peers. Never tell the user they are holding something until you have checked.
2. **Claim and release out loud.** When you take a shared resource for a run, tell the peers waiting on it what you hold and your expected release time; when you free it, message them at once. A peer whose job waits on it should start by itself on release (a watcher on the process, not a sleep).
3. **The user sets priority.** When the user ranks one session's work above another's, relay it to the lower one with what to cut: finish only what cannot ship without, defer the rest, release the resource, report what was deferred.
4. **Detect a running game by its executable path, first field only** (`ps -eo args | grep -qE '^[^ ]*Game-Shipping\.exe'`). `pgrep -f` also matches any shell that mentions the name, and a Wine game's process name can change to a thread name such as `GameThread`, so `pgrep -x` misses it.
5. **The game window is quiet time.** While a game runs for a test or an in-game render, nobody else starts CPU- or GPU-heavy work (Blender even under `nice`, an engine editor or cook, builds, heavy lanes), and running ones pause at a clean point until the game's owner says it closed. Background load starves the game: audio drops out, frame times lie, and renders stutter.
6. **Never stop another session's process.** Ask its owner.
