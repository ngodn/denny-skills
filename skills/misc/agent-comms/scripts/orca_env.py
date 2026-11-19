#!/usr/bin/env python3
"""Orca (Stably AI's agent IDE) glue for the agent-comms scripts. Everything here degrades to
"not in Orca" when the CLI or its runtime is missing, so callers never need their own check.

  orca_env.py status              is this shell inside Orca, is the runtime reachable
  orca_env.py agents [--json]     every agent Orca hosts: state, pane, terminal handle, workspace
  orca_env.py send <handle|pane|title> <text...> [--wait SEC]
                                  type one line into an Orca terminal and press Enter
"""
import json
import os
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True

PANE_VARS = ("ORCA_AGENT_PANE", "ORCA_PANE_KEY")


def orca_bin():
    cand = os.environ.get("ORCA_CLI_COMMAND")
    if cand and os.access(cand, os.X_OK):
        return cand
    found = shutil.which("orca")
    if found:
        return found
    # A process Orca did not start as a terminal (a plugin worker, a service) has no shim on PATH.
    for cand in ("~/.config/orca/linux-orca-cli-shim/orca", "/usr/local/bin/orca", "/usr/bin/orca"):
        cand = os.path.expanduser(cand)
        if os.access(cand, os.X_OK):
            return cand
    return None


def in_orca():
    """True when this process runs under an Orca terminal pane."""
    return bool(os.environ.get("ORCA_TERMINAL_HANDLE") or os.environ.get("ORCA_AGENT_PANE"))


def orca_json(*args, timeout=20):
    """Run `orca <args> --json`; return (result, error). Never raises."""
    exe = orca_bin()
    if not exe:
        return None, {"code": "no_cli", "message": "orca CLI not found"}
    try:
        res = subprocess.run([exe, *args, "--json"], capture_output=True, text=True, timeout=timeout)
        d = json.loads(res.stdout or "{}")
    except subprocess.TimeoutExpired:
        return None, {"code": "timeout", "message": f"orca {' '.join(args[:2])} timed out"}
    except Exception as e:
        return None, {"code": "bad_output", "message": str(e)}
    if d.get("ok"):
        return d.get("result"), None
    return None, d.get("error") or {"code": "unknown", "message": (res.stderr or "").strip()[:200]}


def runtime_ready():
    res, _ = orca_json("status", timeout=8)
    return bool(res and (res.get("runtime") or {}).get("reachable"))


def proc_pane(pid):
    """The Orca pane key (<tabId>:<leafId>) a process was started under, or None."""
    try:
        raw = open(f"/proc/{pid}/environ", "rb").read()
    except Exception:
        return None
    env = {}
    for item in raw.split(b"\0"):
        k, _, v = item.partition(b"=")
        if k.startswith(b"ORCA_"):
            env[k.decode()] = v.decode("utf-8", "replace")
    for var in PANE_VARS:
        if env.get(var):
            return env[var]
    return None


def parent_pid(pid):
    try:
        stat = open(f"/proc/{pid}/stat").read()
        return int(stat.rsplit(")", 1)[1].split()[1])
    except Exception:
        return 0


def snapshot():
    """Every agent pane Orca knows, keyed by pane key. Empty when Orca is not running.
    Terminal handles are reissued when Orca restarts, so they are looked up fresh each call."""
    ps, err = orca_json("worktree", "ps")
    if err or not ps:
        return {}
    terms, _ = orca_json("terminal", "list")
    handle_by_pane = {}
    title_by_pane = {}
    for t in (terms or {}).get("terminals", []):
        key = f"{t.get('tabId')}:{t.get('leafId')}"
        handle_by_pane[key] = t.get("handle")
        title_by_pane[key] = t.get("title")
        # A terminal whose tab Orca has not drawn yet (launched while its workspace is not on
        # screen) has "pty:..." tab and leaf ids; the agent's pane key is in recordedPaneKey.
        rec = t.get("recordedPaneKey")
        if rec:
            handle_by_pane[rec] = t.get("handle")
            title_by_pane[rec] = t.get("title")
    panes = {}
    for wt in ps.get("worktrees", []):
        for a in wt.get("agents", []):
            key = a.get("paneKey")
            if not key:
                continue
            panes[key] = {
                "pane": key,
                "handle": handle_by_pane.get(key),
                "state": (a.get("mainAgent") or {}).get("state") or a.get("state"),
                "agent": a.get("agentType"),
                "title": a.get("conversationName") or a.get("displayName") or title_by_pane.get(key) or "",
                "tool": a.get("toolName"),
                "last_message": a.get("lastAssistantMessage"),
                "workspace": wt.get("displayName") or wt.get("path"),
                "workspace_path": wt.get("path"),
                "worktree_id": wt.get("worktreeId"),
                "host": wt.get("hostId"),
            }
    return panes


def annotate(peers):
    """Add an `orca` dict to each peer that runs in an Orca pane, and append Orca agents no
    other lister knows (other harnesses). A process started by an agent inherits that agent's
    pane, so only the outermost process in a pane owns it; the rest are marked `inherited`
    and get no handle, since typing into the pane would reach the owner instead."""
    panes = snapshot()
    if not panes:
        return peers
    by_pid = {p["pid"]: p for p in peers if p.get("pid")}
    owners = {}
    for pid, p in by_pid.items():
        key = proc_pane(pid)
        if not key:
            continue
        inherited = False
        anc = parent_pid(pid)
        while anc > 1:
            if anc in by_pid and proc_pane(anc) == key:
                inherited = True
                break
            anc = parent_pid(anc)
        info = dict(panes.get(key) or {"pane": key, "handle": None, "state": None})
        if inherited:
            info.update({"inherited": True, "handle": None, "state": None})
        else:
            owners[key] = p
        p["orca"] = info
    for key, info in panes.items():
        if key in owners or info.get("host") not in (None, "local"):
            continue
        peers.append({
            "harness": info.get("agent") or "orca",
            "id": info.get("handle") or key,
            "address": f"orca:{info.get('handle') or key}",
            "pid": None,
            "model": "unknown",
            "status": {"working": "busy", "done": "idle"}.get(info.get("state"), info.get("state") or "unknown"),
            "cwd": info.get("workspace_path") or "",
            "title": info.get("title") or "",
            "live": True,
            "orca": info,
        })
    return peers


def resolve_handle(target):
    """Terminal handle for a handle, pane key, or pane/conversation title. None when no match."""
    target = target.strip()
    if target.startswith("orca:"):
        target = target[5:]
    panes = snapshot()
    for info in panes.values():
        if target in (info.get("handle"), info.get("pane")):
            return info.get("handle")
    hits = [i for i in panes.values() if i.get("title") and i["title"].lower() == target.lower()]
    if len(hits) == 1:
        return hits[0].get("handle")
    if target.startswith("term_"):
        return target
    return None


def send(handle, text, wait=8):
    """Type one line into an Orca terminal and press Enter. Newlines are flattened: a newline
    in a terminal submits early. Returns a small receipt dict; `turn_started` in `stages` is the
    proof an agent took the prompt, `accepted` alone only means the bytes were written."""
    flat = " / ".join(l.strip() for l in text.splitlines() if l.strip())
    args = ["terminal", "send", "--terminal", handle, "--text", flat, "--enter"]
    if wait:
        args += ["--wait-submit", str(int(wait))]
    res, err = orca_json(*args, timeout=(wait or 0) + 20)
    if err:
        # agent_prompt_blocked: the agent shows a permission, trust or question menu. That
        # needs an answer the user chose, not a prompt; see the desktop-control skill.
        return {"ok": False, "code": err.get("code"), "error": err.get("message")}
    s = res.get("send") or {}
    return {
        "ok": bool(s.get("accepted")),
        "handle": s.get("handle"),
        "stages": (s.get("prompt") or {}).get("stages", []),
        "request_id": (s.get("prompt") or {}).get("requestId"),
    }


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return
    if args[0] == "status":
        print(json.dumps({"in_orca": in_orca(), "cli": orca_bin(), "runtime_ready": runtime_ready(),
                          "pane": os.environ.get("ORCA_AGENT_PANE"),
                          "terminal": os.environ.get("ORCA_TERMINAL_HANDLE")}))
    elif args[0] == "agents":
        panes = snapshot()
        if "--json" in args:
            print(json.dumps(list(panes.values()), indent=2))
            return
        if not panes:
            print("No Orca agents (Orca not running, or no agent panes).")
            return
        print(f"{'STATE':<8} {'AGENT':<8} {'HANDLE':<42} {'WORKSPACE':<18} TITLE")
        for i in panes.values():
            print(f"{str(i['state']):<8} {str(i['agent']):<8} {str(i['handle']):<42} "
                  f"{str(i['workspace'])[:17]:<18} {i['title']}")
    elif args[0] == "send" and len(args) >= 3:
        wait = 8
        rest = args[1:]
        if "--wait" in rest:
            i = rest.index("--wait")
            wait = int(rest[i + 1]); del rest[i:i + 2]
        handle = resolve_handle(rest[0])
        if not handle:
            sys.stderr.write(f"orca_env.py: no Orca terminal matches '{rest[0]}'\n")
            sys.exit(1)
        out = send(handle, " ".join(rest[1:]), wait=wait)
        print(json.dumps(out))
        sys.exit(0 if out.get("ok") else 1)
    else:
        sys.stderr.write("Usage: orca_env.py status | agents [--json] | send <target> <text...> [--wait SEC]\n")
        sys.exit(2)


if __name__ == "__main__":
    main()
