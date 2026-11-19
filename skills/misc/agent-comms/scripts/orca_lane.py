#!/usr/bin/env python3
"""Run a lane as a visible agent tab in Orca instead of a headless process, and watch it.
Called by `run_lane.sh --orca`; the run folder and prompt.md already exist.

  orca_lane.py start  <run dir> <vendor> <model> <effort> <root> <lane>
  orca_lane.py resume <run dir> <handle> <lane>      type prompt.md into a lane's terminal, watch
  orca_lane.py attach <run dir> <handle> <lane>      watch only (after answering its question)

Prints one line per event, so it works as a tracked background run or under the Monitor tool:
what the lane says, a question or permission box it is stuck on, a 10-minute heartbeat, the end.
Exit: 0 the lane finished its turn, 1 launch failed or the terminal went away, 3 the lane has
waited on a question for LANE_WAIT_EXIT_SEC (default 120) and needs an answer, 124 LANE_TIMEOUT_MIN
passed. Exit 2 from `start` means Orca cannot host this lane and nothing was started.
"""
import json
import os
import subprocess
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import orca_env  # noqa: E402

AGENT_IDS = {"claude": "claude", "codex": "codex"}
POLL = 4


def put(run, name, text):
    with open(os.path.join(run, name), "w") as f:
        f.write(str(text).rstrip("\n") + "\n")


def event(run, **kw):
    kw["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(os.path.join(run, "events.jsonl"), "a") as f:
        f.write(json.dumps(kw) + "\n")


def screen_tail(handle, rows=7):
    res, _ = orca_env.orca_json("terminal", "read", "--terminal", handle, "--screen")
    tail = ((res or {}).get("terminal") or {}).get("tail") or []
    return [l.rstrip() for l in tail if l.strip()][-rows:]


def launch_call(run, lane, agent, args):
    """`orca agent launch` does not return while the new agent sits on a menu (the trust-this-folder
    box of an untrusted folder; the home folder asks every session), and it drops the prompt if
    the call is cut off. So keep the call open, say what the tab is stuck on, and give up only
    after LANE_WAIT_EXIT_SEC."""
    before = set(orca_env.snapshot())
    proc = subprocess.Popen([orca_env.orca_bin(), *args, "--json"], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True)
    wait_exit = float(os.environ.get("LANE_WAIT_EXIT_SEC", "120"))
    start = time.time()
    stuck = None
    while proc.poll() is None:
        el = time.time() - start
        if not stuck and el > 8:
            new = [i for k, i in orca_env.snapshot().items()
                   if k not in before and i.get("agent") == agent and i.get("state") in ("waiting", "blocked")]
            if new and new[0].get("handle"):
                stuck = new[0]["handle"]
                put(run, "id.txt", stuck)
                put(run, "orca-terminal.txt", stuck)
                print(f"{lane.upper()} needs an answer before it can take its brief (terminal {stuck}): "
                      + " | ".join(screen_tail(stuck)), flush=True)
        if el > wait_exit + 30:
            proc.kill()
            print(f"{lane.upper()} still blocked; the brief was not delivered. Answer the box, then send "
                  f"the brief with: run_lane.sh --orca ... --resume {stuck or '<handle>'} "
                  f"\"<what the first prompt said>\" (it is in {run}/prompt.md)", flush=True)
            put(run, "exit.txt", "waiting")
            return None, {"code": "launch_blocked", "message": "agent blocked on a menu at launch"}
        time.sleep(2)
    try:
        d = json.loads(proc.stdout.read() or "{}")
    except Exception as e:
        return None, {"code": "bad_output", "message": str(e)}
    if d.get("ok"):
        return d.get("result"), None
    return None, d.get("error") or {"code": "unknown", "message": "launch failed"}


def launch(run, vendor, model, effort, root, lane):
    agent = AGENT_IDS.get(vendor)
    if not agent:
        print(f"orca_lane: Orca launch is wired for claude and codex, not {vendor}", file=sys.stderr)
        return None, 2
    if not orca_env.runtime_ready():
        print("orca_lane: Orca is not running here", file=sys.stderr)
        return None, 2
    prompt = open(os.path.join(run, "prompt.md")).read()
    base = ["agent", "launch", "--agent", agent, "--worktree", f"path:{root}", "--surface", "terminal",
            "--prompt", prompt]
    tries = [["--model", model, "--effort", effort], ["--model", model]]
    res = err = None
    for extra in tries:
        res, err = launch_call(run, lane, agent, [*base, *extra])
        # Orca checks model and effort against its own catalog (haiku takes no effort level).
        if not (err and err.get("code") == "invalid_argument" and "effort" in err.get("message", "")):
            break
    if err and err.get("code") == "launch_blocked":
        return None, 3
    if err:
        if err.get("code") == "selector_not_found":
            print(f"orca_lane: {root} is not an Orca workspace. Add it once with "
                  f"`orca repo add --path {root}` (add `--kind folder` for a non-git folder).", file=sys.stderr)
            return None, 2
        if err.get("code") == "invalid_argument":
            # An older Orca lacks a launch flag used here (or does not know the model id).
            print(f"orca_lane: this Orca refused the launch ({err.get('message')}); update Orca "
                  f"or pass a model id it knows with ORCA_MODEL.", file=sys.stderr)
            return None, 2
        print(f"orca_lane: launch failed: {err.get('code')}: {err.get('message')}", file=sys.stderr)
        return None, 1
    out = (res.get("launch") or res).get("outcome") or {}
    handle, pane = out.get("handle"), out.get("paneKey")
    if not handle:
        print(f"orca_lane: launch returned no terminal handle: {json.dumps(res)[:300]}", file=sys.stderr)
        return None, 1
    put(run, "id.txt", handle)
    put(run, "orca-terminal.txt", handle)
    put(run, "orca-pane.txt", pane or "")
    orca_env.orca_json("terminal", "rename", "--terminal", handle, "--title", lane)
    event(run, event="launched", handle=handle, pane=pane)
    return handle, 0


def watch(run, handle, lane):
    label = lane.upper()
    say = lambda s: print(f"{label} " + " ".join(str(s).split())[:400], flush=True)
    wait_exit = float(os.environ.get("LANE_WAIT_EXIT_SEC", "120"))
    timeout = float(os.environ.get("LANE_TIMEOUT_MIN", "0")) * 60
    start = last_beat = time.time()
    last_state = last_msg = None
    waiting_since = None
    missing = 0
    seen_working = False
    while True:
        info = next((i for i in orca_env.snapshot().values() if i.get("handle") == handle), None)
        now = time.time()
        if not info:
            missing += 1
            if missing * POLL >= 20:
                say("terminal is gone (closed, or Orca stopped)")
                put(run, "exit.txt", 1)
                return 1
            time.sleep(POLL)
            continue
        missing = 0
        state, msg = info.get("state"), info.get("last_message")
        if msg and msg != last_msg:
            say("says: " + msg)
            last_msg = msg
            put(run, "last-message.md", msg)
        if state != last_state:
            event(run, event="state", state=state, tool=info.get("tool"))
            last_state = state
            waiting_since = now if state in ("waiting", "blocked") else None
            if waiting_since:
                say(f"needs an answer ({info.get('tool') or state}): " + " | ".join(screen_tail(handle)))
        seen_working = seen_working or state == "working"
        # "done" right after launch is the previous turn of a reused terminal, so require work first
        # (or a few seconds, for a turn too short to catch).
        if state == "done" and (seen_working or now - start > 3 * POLL):
            say("finished")
            put(run, "exit.txt", 0)
            return 0
        if waiting_since and now - waiting_since > wait_exit:
            say(f"still waiting after {int(wait_exit)}s; answer it, then attach again "
                f"(run_lane.sh --orca ... --attach {handle})")
            put(run, "exit.txt", "waiting")
            return 3
        if timeout and now - start > timeout:
            say("TIMEOUT: still running; the lane was not stopped")
            put(run, "exit.txt", 124)
            return 124
        if now - last_beat > 600:
            say(f"heartbeat: {state}, current tool: {info.get('tool')}")
            last_beat = now
        time.sleep(POLL)


def main():
    a = sys.argv[1:]
    if len(a) < 4 or a[0] not in ("start", "resume", "attach"):
        print(__doc__.strip())
        sys.exit(2)
    mode, run = a[0], a[1]
    put(run, "pid.txt", os.getpid())
    if mode == "start":
        vendor, model, effort, root, lane = a[2:7]
        handle, code = launch(run, vendor, model, effort, root, lane)
        if not handle:
            sys.exit(code)
    else:
        handle, lane = a[2], a[3]
        put(run, "id.txt", handle)
        put(run, "orca-terminal.txt", handle)
        if mode == "resume":
            res = orca_env.send(handle, open(os.path.join(run, "prompt.md")).read(), wait=10)
            if not res.get("ok"):
                print(f"orca_lane: could not type into {handle}: {res.get('code')}: {res.get('error')}", file=sys.stderr)
                put(run, "exit.txt", 1)
                sys.exit(1)
    sys.exit(watch(run, handle, lane))


if __name__ == "__main__":
    main()
