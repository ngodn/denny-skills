#!/usr/bin/env python3
"""List live agent sessions across all three harnesses (Claude Code, Codex, Antigravity)
with session id, model, cwd, title, and busy/idle/waiting state, plus optional quota readout.

Usage:
  list_peers.py [--json] [--quota] [--recent N] [--no-orca]

When Orca (the agent IDE) is running, each session hosted in an Orca pane also gets its Orca
state and terminal handle, and agents only Orca knows are appended. --no-orca skips that.
"""
import glob
import json
import os
import re
import sqlite3
import subprocess
import sys
sys.dont_write_bytecode = True
import time
from urllib.parse import unquote, urlparse

HOME = os.path.expanduser("~")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
IDLE_HELPERS = (
    "mcp-for-blender",
    "chrome-devtools-mcp",
    "rea-agents",
    "codex-code-mode-host",
    "mcp",
    "uv tool",
    "npm exec",
    "npx",
)


def read_cmdline(pid):
    try:
        raw = open(f"/proc/{pid}/cmdline", "rb").read()
        return [a.decode("utf-8", "replace") for a in raw.split(b"\0") if a]
    except Exception:
        return []


def proc_alive(pid):
    return os.path.exists(f"/proc/{pid}")


def busy_descendants(pid):
    kids, todo = [], [pid]
    seen = {pid}
    while todo:
        p = todo.pop()
        try:
            children = open(f"/proc/{p}/task/{p}/children").read().split()
        except Exception:
            continue
        for c in children:
            cpid = int(c)
            if cpid in seen:
                continue
            seen.add(cpid)
            todo.append(cpid)
            cmd = " ".join(read_cmdline(cpid))
            if cmd and not any(h in cmd for h in IDLE_HELPERS):
                kids.append(cmd[:80])
    return kids


# --- 1. Claude Code ---

def claude_transcript_path(cwd, session_id):
    proj = cwd.replace("/", "-").replace(".", "-")
    return os.path.join(HOME, ".claude", "projects", proj, f"{session_id}.jsonl")


def claude_meta_from_transcript(tr_path):
    if not tr_path or not os.path.exists(tr_path):
        return None, None
    title = custom = model = None
    try:
        with open(tr_path, "rb") as f:
            data = f.read()
        for line in data.splitlines():
            if b'"custom-title"' in line or b'"ai-title"' in line or b'"model"' in line:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                t = r.get("type")
                if t == "custom-title":
                    custom = r.get("customTitle") or custom
                elif t == "ai-title" and not custom:
                    title = r.get("aiTitle") or title
                msg = r.get("message")
                if isinstance(msg, dict) and msg.get("model"):
                    model = msg.get("model")
    except Exception:
        pass
    return custom or title, model


def list_claude_sessions(recent=0):
    peers = []
    seen_ids = set()
    sess_dir = os.path.join(HOME, ".claude", "sessions")
    for path in sorted(glob.glob(f"{sess_dir}/*.json")):
        try:
            pid = int(os.path.basename(path).split(".")[0])
            d = json.load(open(path))
        except Exception:
            continue
        if not proc_alive(pid):
            continue
        sid = d.get("sessionId", "")
        seen_ids.add(sid)
        cwd = d.get("cwd", "")
        name = d.get("name", str(pid))
        status = d.get("status", "unknown")
        tr = claude_transcript_path(cwd, sid)
        title, model = claude_meta_from_transcript(tr)
        if not model:
            argv = read_cmdline(pid)
            if "--model" in argv:
                idx = argv.index("--model")
                if idx + 1 < len(argv):
                    model = argv[idx + 1]
        if status == "idle" and busy_descendants(pid):
            status = "busy"
        peers.append({
            "harness": "claude",
            "id": sid,
            "address": name,
            "pid": pid,
            "model": model or "default",
            "status": status,
            "cwd": cwd,
            "title": title or name,
            "live": True,
        })
    if recent > 0:
        proj_glob = os.path.join(HOME, ".claude", "projects", "*", "*.jsonl")
        files = sorted(glob.glob(proj_glob), key=os.path.getmtime, reverse=True)
        added = 0
        for tr in files:
            if added >= recent:
                break
            sid = os.path.splitext(os.path.basename(tr))[0]
            if sid in seen_ids:
                continue
            title, model = claude_meta_from_transcript(tr)
            peers.append({
                "harness": "claude",
                "id": sid,
                "address": sid,
                "pid": None,
                "model": model or "unknown",
                "status": "stopped",
                "cwd": "",
                "title": title or sid[:8],
                "live": False,
            })
            added += 1
    return peers


# --- 2. Codex ---

def codex_thread_titles():
    titles = {}
    idx_file = os.path.join(HOME, ".codex", "session_index.jsonl")
    if os.path.exists(idx_file):
        try:
            with open(idx_file) as f:
                for line in f:
                    try:
                        r = json.loads(line)
                        if r.get("id") and r.get("thread_name"):
                            titles[r["id"]] = r["thread_name"]
                    except Exception:
                        continue
        except Exception:
            pass
    return titles


def parse_codex_rollout(path, titles):
    sid = model = effort = cwd = first_user = None
    in_turn = False
    try:
        with open(path, "rb") as f:
            for raw in f:
                try:
                    r = json.loads(raw)
                except Exception:
                    continue
                t = r.get("type")
                p = r.get("payload") or {}
                if t == "session_meta":
                    sid = p.get("id") or p.get("session_id") or sid
                    cwd = p.get("cwd") or cwd
                elif t == "turn_context":
                    model = p.get("model") or model
                    effort = p.get("effort") or effort
                    cwd = p.get("cwd") or cwd
                elif t == "event_msg":
                    pt = p.get("type")
                    if pt == "task_started":
                        in_turn = True
                    elif pt in ("task_complete", "turn_aborted", "error"):
                        in_turn = False
                elif t == "response_item" and p.get("type") == "message" and p.get("role") == "user":
                    for c in p.get("content") or []:
                        txt = c.get("text", "").strip()
                        if (
                            txt
                            and not txt.startswith("# AGENTS.md")
                            and not txt.startswith("<environment_context>")
                            and not txt.startswith("<permissions")
                            and not txt.startswith("<INSTRUCTIONS>")
                            and not first_user
                        ):
                            first_user = " ".join(txt.splitlines())[:80]
    except Exception:
        pass
    if not sid:
        m = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", os.path.basename(path))
        if m:
            sid = m.group(1)
    full_model = f"{model} ({effort})" if model and effort else (model or "unknown")
    title = titles.get(sid) or first_user or (sid[:8] if sid else "codex")
    return {
        "id": sid or "",
        "model": full_model,
        "cwd": cwd or "",
        "title": title,
        "in_turn": in_turn,
        "mtime": os.path.getmtime(path) if os.path.exists(path) else 0,
    }


def codex_subcommand(argv):
    """First positional argument, skipping global options such as `-c key=value`."""
    i = 1
    while i < len(argv):
        a = argv[i]
        if a in ("-c", "--config", "-m", "--model", "-p", "--profile", "-C", "--cd"):
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        return a
    return ""


def list_codex_sessions(recent=0):
    titles = codex_thread_titles()
    peers = []
    seen_ids = set()
    # Find live codex processes
    codex_procs = {}
    for pdir in glob.glob("/proc/[0-9]*"):
        try:
            pid = int(os.path.basename(pdir))
        except ValueError:
            continue
        argv = read_cmdline(pid)
        if not argv:
            continue
        exe = os.path.basename(argv[0])
        if exe not in ("codex", "codex-linux-x64") or "codex-code-mode-host" in " ".join(argv):
            continue
        sub = codex_subcommand(argv)
        if sub in ("mcp", "mcp-server", "exec-server", "agents", "help"):
            continue
        codex_procs[pid] = argv

    # Map live processes to rollout files via open fds or thread-writer-locks or recent rollouts
    rollout_glob = os.path.join(HOME, ".codex", "sessions", "*", "*", "*", "rollout-*.jsonl")
    all_rollouts = sorted(glob.glob(rollout_glob), key=os.path.getmtime, reverse=True)

    for pid, argv in sorted(codex_procs.items()):
        rollout_path = None
        # An app-server (the VS Code Codex panel) hosts any number of threads, so never
        # guess one for it: list it as the panel and let --recent show the threads.
        app_server = codex_subcommand(argv) == "app-server"
        try:
            for fd in os.listdir(f"/proc/{pid}/fd"):
                target = os.readlink(f"/proc/{pid}/fd/{fd}")
                if "rollout-" in target and target.endswith(".jsonl"):
                    rollout_path = target
                    break
                if "thread-writer-locks/" in target and target.endswith(".lock"):
                    uid = os.path.basename(target)[:-5]
                    for r in all_rollouts:
                        if uid in r:
                            rollout_path = r
                            break
        except Exception:
            pass
        if not rollout_path and all_rollouts:
            # Check if resume <id> is in argv
            for a in argv:
                if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", a):
                    for r in all_rollouts:
                        if a in r:
                            rollout_path = r
                            break

        info = parse_codex_rollout(rollout_path, titles) if rollout_path else {
            "id": "", "model": "unknown", "cwd": "",
            "title": "VS Code Codex panel (app-server)" if app_server else "codex",
            "in_turn": False,
        }
        sid = info["id"]
        if sid:
            seen_ids.add(sid)
        try:
            proc_cwd = os.readlink(f"/proc/{pid}/cwd")
        except Exception:
            proc_cwd = ""
        is_exec = "exec" in argv[1:3]
        status = "busy" if (is_exec or info["in_turn"] or busy_descendants(pid)) else "idle"
        peers.append({
            "harness": "codex",
            "id": sid or f"pid-{pid}",
            "address": sid or f"pid-{pid}",
            "pid": pid,
            "model": info["model"],
            "status": status,
            "cwd": info["cwd"] or proc_cwd,
            "title": info["title"],
            "live": True,
        })

    if recent > 0:
        added = 0
        for r in all_rollouts:
            if added >= recent:
                break
            info = parse_codex_rollout(r, titles)
            sid = info["id"]
            if not sid or sid in seen_ids:
                continue
            seen_ids.add(sid)
            peers.append({
                "harness": "codex",
                "id": sid,
                "address": sid,
                "pid": None,
                "model": info["model"],
                "status": "stopped",
                "cwd": info["cwd"],
                "title": info["title"],
                "live": False,
            })
            added += 1
    return peers


# --- 3. Antigravity (agy CLI + IDE) ---

def parse_workspace_uris(raw_uris):
    try:
        uris = json.loads(raw_uris)
        if uris and isinstance(uris, list):
            p = urlparse(uris[0])
            return unquote(p.path) if p.scheme == "file" else uris[0]
    except Exception:
        pass
    return ""


def agy_model_for_conv(app_dir, cid, pid=None):
    # 1. Check command line flags if process is live
    if pid:
        argv = read_cmdline(pid)
        model_arg = effort_arg = None
        for i, a in enumerate(argv):
            if a == "--model" and i + 1 < len(argv):
                model_arg = argv[i + 1]
            elif a.startswith("--model="):
                model_arg = a.split("=", 1)[1]
            elif a == "--effort" and i + 1 < len(argv):
                effort_arg = argv[i + 1]
            elif a.startswith("--effort="):
                effort_arg = a.split("=", 1)[1]
        if model_arg:
            return f"{model_arg}-{effort_arg}" if effort_arg and not model_arg.endswith(f"-{effort_arg}") else model_arg
        # Check open log file for latest selected model override
        try:
            log_path = os.readlink(f"/proc/{pid}/fd/1")
            if os.path.exists(log_path) and log_path.endswith(".log"):
                with open(log_path, "rb") as f:
                    f.seek(max(0, os.path.getsize(log_path) - 65536))
                    tail = f.read().decode("utf-8", "replace")
                m = re.findall(r'Propagating selected model override to backend: label="([^"]+)"', tail)
                if m:
                    return m[-1]
        except Exception:
            pass
    # 2. Check conversations/<cid>.db gen_metadata
    conv_db = os.path.join(app_dir, "conversations", f"{cid}.db")
    if os.path.exists(conv_db):
        try:
            conn = sqlite3.connect(f"file:{conv_db}?mode=ro", uri=True, timeout=1.0)
            row = conn.execute("SELECT data FROM gen_metadata ORDER BY idx DESC LIMIT 1").fetchone()
            conn.close()
            if row and isinstance(row[0], bytes):
                m = re.search(rb"(gemini-[a-z0-9.-]+|claude-[a-z0-9.-]+|gpt-oss-[a-z0-9.-]+)", row[0])
                if m:
                    return m.group(1).decode("utf-8", "replace")
        except Exception:
            pass
    return "unknown"


def agy_summary_for_conv(app_dir, cid):
    sum_db = os.path.join(app_dir, "conversation_summaries.db")
    title = cwd = status = ""
    not_idle = 0
    if os.path.exists(sum_db):
        try:
            conn = sqlite3.connect(f"file:{sum_db}?mode=ro", uri=True, timeout=1.0)
            row = conn.execute(
                "SELECT title, workspace_uris, status, not_fully_idle FROM conversation_summaries WHERE conversation_id = ?",
                (cid,),
            ).fetchone()
            conn.close()
            if row:
                title, raw_uris, status, not_idle = row
                cwd = parse_workspace_uris(raw_uris)
        except Exception:
            pass
    if not title:
        ann = os.path.join(app_dir, "annotations", f"{cid}.pbtxt")
        if os.path.exists(ann):
            try:
                m = re.search(r'title:\s*"([^"]+)"', open(ann).read())
                if m:
                    title = m.group(1)
            except Exception:
                pass
    return title, cwd, status, bool(not_idle)


def list_agy_sessions(recent=0):
    peers = []
    seen_ids = set()
    # Scan /proc/[0-9]*/fd/* for presence/<cid>.lock
    live_locks = {}  # cid -> (pid, app_dir)
    for pdir in glob.glob("/proc/[0-9]*"):
        try:
            pid = int(os.path.basename(pdir))
            for fd in os.listdir(f"{pdir}/fd"):
                target = os.readlink(f"{pdir}/fd/{fd}")
                if "/presence/" in target and target.endswith(".lock"):
                    cid = os.path.basename(target)[:-5]
                    app_dir = os.path.dirname(os.path.dirname(target))
                    live_locks[cid] = (pid, app_dir)
        except Exception:
            continue

    for cid, (pid, app_dir) in sorted(live_locks.items(), key=lambda x: x[1][0]):
        seen_ids.add(cid)
        title, cwd, raw_status, not_idle = agy_summary_for_conv(app_dir, cid)
        if not cwd:
            try:
                cwd = os.readlink(f"/proc/{pid}/cwd")
            except Exception:
                cwd = ""
        model = agy_model_for_conv(app_dir, cid, pid=pid)
        surface = "agy-ide" if os.path.basename(app_dir) == "antigravity" else "agy"
        busy = (
            "RUNNING" in (raw_status or "")
            or not_idle
            or bool(busy_descendants(pid))
        )
        peers.append({
            "harness": surface,
            "id": cid,
            "address": f"agy:{cid}",
            "pid": pid,
            "model": model,
            "status": "busy" if busy else "idle",
            "cwd": cwd,
            "title": title or cid[:8],
            "live": True,
        })

    if recent > 0:
        for sub in ("antigravity-cli", "antigravity"):
            app_dir = os.path.join(HOME, ".gemini", sub)
            sum_db = os.path.join(app_dir, "conversation_summaries.db")
            if not os.path.exists(sum_db):
                continue
            try:
                conn = sqlite3.connect(f"file:{sum_db}?mode=ro", uri=True, timeout=1.0)
                rows = conn.execute(
                    "SELECT conversation_id, title, workspace_uris FROM conversation_summaries ORDER BY last_modified_time DESC LIMIT ?",
                    (recent + len(seen_ids),),
                ).fetchall()
                conn.close()
            except Exception:
                continue
            added = 0
            for cid, title, raw_uris in rows:
                if added >= recent:
                    break
                if cid in seen_ids:
                    continue
                if not os.path.exists(os.path.join(app_dir, "conversations", f"{cid}.db")):
                    continue
                seen_ids.add(cid)
                peers.append({
                    "harness": "agy-ide" if sub == "antigravity" else "agy",
                    "id": cid,
                    "address": f"agy:{cid}",
                    "pid": None,
                    "model": agy_model_for_conv(app_dir, cid),
                    "status": "stopped",
                    "cwd": parse_workspace_uris(raw_uris),
                    "title": title or cid[:8],
                    "live": False,
                })
                added += 1
    return peers


# --- 4. Quotas ---

def read_quotas():
    quotas = {}
    # 1. Claude Code cachedUsageUtilization in ~/.claude.json
    cc_file = os.path.join(HOME, ".claude.json")
    if os.path.exists(cc_file):
        try:
            d = json.load(open(cc_file)).get("cachedUsageUtilization", {})
            u = d.get("utilization", {})
            fh = u.get("five_hour") or {}
            sd = u.get("seven_day") or {}
            quotas["claude"] = {
                "five_hour_used_pct": fh.get("utilization"),
                "five_hour_remaining_pct": (100 - fh["utilization"]) if fh.get("utilization") is not None else None,
                "seven_day_used_pct": sd.get("utilization"),
                "seven_day_remaining_pct": (100 - sd["utilization"]) if sd.get("utilization") is not None else None,
                "seven_day_resets_at": sd.get("resets_at"),
            }
        except Exception as e:
            quotas["claude"] = {"error": str(e)}

    # 2. Codex rate_limits in latest rollout
    rollout_glob = os.path.join(HOME, ".codex", "sessions", "*", "*", "*", "rollout-*.jsonl")
    rollouts = sorted(glob.glob(rollout_glob), key=os.path.getmtime, reverse=True)
    for r in rollouts[:5]:
        try:
            with open(r, "rb") as f:
                lines = f.readlines()
            rl = None
            for raw in reversed(lines):
                if b'"rate_limits"' in raw:
                    obj = json.loads(raw)
                    rl = (obj.get("payload") or {}).get("rate_limits")
                    if rl:
                        break
            if rl:
                prim = rl.get("primary") or {}
                used = prim.get("used_percent")
                quotas["codex"] = {
                    "plan_type": rl.get("plan_type"),
                    "weekly_used_pct": used,
                    "weekly_remaining_pct": round(100.0 - used, 2) if used is not None else None,
                    "resets_at_epoch": prim.get("resets_at"),
                }
                break
        except Exception:
            continue

    # 3. Antigravity (/usage)
    try:
        out = subprocess.check_output(
            ["agy", "-p", "/usage", "--output-format", "json"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        groups = json.loads(out).get("command", {}).get("data", {}).get("groups", [])
        agy_q = {}
        for g in groups:
            for b in g.get("buckets", []):
                rem = b.get("remaining_fraction")
                agy_q[b.get("id")] = {
                    "group": g.get("name"),
                    "window": b.get("window"),
                    "remaining_pct": round(rem * 100.0, 2) if rem is not None else None,
                    "reset_time": b.get("reset_time"),
                }
        quotas["agy"] = agy_q
    except Exception as e:
        quotas["agy"] = {"error": str(e)}

    return quotas


def print_table(peers):
    if not peers:
        print("No sessions found.")
        return
    # The ORCA column only appears when some session runs in an Orca pane: its Orca state,
    # or "child" for a process an Orca-hosted agent started (it has no pane of its own).
    # The HOST column only appears when sessions from another machine are listed; such a
    # session's address is <address>@<host>.
    with_orca = any(p.get("orca") for p in peers)
    with_host = any(p.get("host") for p in peers)
    orca_head = f"{'ORCA':<9} " if with_orca else ""
    host_head = f"{'HOST':<12} " if with_host else ""
    print(f"{host_head}{'HARNESS':<8} {'STATUS':<8} {orca_head}{'PID':<8} {'MODEL':<26} {'ID / ADDRESS':<38} {'TITLE':<28} CWD")
    for p in peers:
        pid_s = str(p["pid"]) if p["pid"] else "-"
        addr = p["address"] if p["harness"] == "claude" else p["id"]
        if p.get("host"):
            addr = f"{addr}@{p['host']}"
        orca_s = ""
        if with_orca:
            o = p.get("orca")
            orca_s = f"{('child' if o.get('inherited') else str(o.get('state') or 'pane')) if o else '-':<9} "
        host_s = f"{p.get('host') or 'here':<12} " if with_host else ""
        width = 37 if not p.get("host") else max(37, len(addr))
        print(
            f"{host_s}{p['harness']:<8} {p['status']:<8} {orca_s}{pid_s:<8} "
            f"{str(p['model'])[:25]:<26} {addr[:width]:<38} "
            f"{str(p['title'])[:27]:<28} {p['cwd']}"
        )


def print_quotas(quotas):
    cc = quotas.get("claude", {})
    if "seven_day_remaining_pct" in cc:
        print(
            f"claude : weekly {cc.get('seven_day_remaining_pct')}% remaining "
            f"(5h: {cc.get('five_hour_remaining_pct')}% remaining, resets {cc.get('seven_day_resets_at')})"
        )
    cx = quotas.get("codex", {})
    if "weekly_remaining_pct" in cx:
        print(f"codex  : weekly {cx.get('weekly_remaining_pct')}% remaining (plan: {cx.get('plan_type')})")
    ag = quotas.get("agy", {})
    for bid, b in ag.items():
        if isinstance(b, dict) and "remaining_pct" in b:
            print(f"agy    : {bid:<14} {b['remaining_pct']:>6}% remaining (resets {b.get('reset_time')})")


def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    want_quota = "--quota" in args
    recent = 0
    if "--recent" in args:
        i = args.index("--recent")
        recent = int(args[i + 1]) if i + 1 < len(args) and args[i + 1].isdigit() else 3

    peers = (
        list_claude_sessions(recent=recent)
        + list_codex_sessions(recent=recent)
        + list_agy_sessions(recent=recent)
    )
    if "--no-orca" not in args:
        try:
            import orca_env
            peers = orca_env.annotate(peers)
        except Exception:
            pass
    quotas = read_quotas() if want_quota else None

    # --hosts adds the sessions on every registered machine, --host <name> on one (remote.py).
    host_errors, host_quotas = {}, {}
    names = [args[i + 1] for i, a in enumerate(args) if a == "--host" and i + 1 < len(args)]
    if "--hosts" in args or names:
        import remote
        theirs, host_errors, host_quotas = remote.peers(names, quota=want_quota, recent=recent)
        peers = peers + theirs

    if as_json:
        out = {"peers": peers}
        if quotas is not None:
            out["quotas"] = quotas
        if host_quotas:
            out["host_quotas"] = host_quotas
        if host_errors:
            out["host_errors"] = host_errors
        print(json.dumps(out, indent=2))
        return

    print_table(peers)
    if quotas:
        print("\n=== QUOTA REMAINING ===")
        print_quotas(quotas)
    for host, q in host_quotas.items():
        print(f"\n=== QUOTA REMAINING on {host} ===")
        print_quotas(q)
    for host, err in host_errors.items():
        print(f"{host}: no answer ({err})", file=sys.stderr)


if __name__ == "__main__":
    main()
