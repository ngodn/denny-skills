#!/usr/bin/env python3
"""Shared file-based mailbox for Claude Code, Codex, and Antigravity (agy).

Usage:
  mail.py send <to> <text...> [--from ID] [--harness H] [--model M] [--reply-to MSG_ID]
                              [--deliver] [--claude-relay] [--resume]
  mail.py read <me> [--keep] [--json]
  mail.py watch <me> [--once] [--ack] [--from-now] [--timeout SEC] [--interval SEC]
"""
import datetime
import glob
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import list_peers  # noqa: E402

HOME = os.path.expanduser("~")
MAILBOX_ROOT = os.environ.get("AGENT_MAILBOX_DIR", os.path.join(HOME, ".agent-mailbox"))


def sanitize_box(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip()).strip("_") or "default"


def resolve_recipient(raw_target):
    """Resolve <to> or <me> into (box_name, harness, session_id, peer_address).
    Covers:
      - explicit prefix: claude:<x>, codex:<x>, agy:<x>
      - Claude Code peer names (peer-01), session UUIDs, tab titles
      - Codex thread UUIDs or 8+ hex prefixes
      - agy conversation UUIDs or 8+ hex prefixes or titles
      - named daemon/alias mailboxes in ~/.agent-mailbox/<name>
    """
    target = raw_target.strip()
    explicit_harness = None
    if ":" in target:
        pfx, rest = target.split(":", 1)
        if pfx in ("claude", "codex", "agy", "agy-ide"):
            explicit_harness = "agy" if pfx == "agy-ide" else pfx
            target = rest.strip()

    # Check if there is an existing mailbox folder with daemon.json
    cand_box = sanitize_box(target)
    daemon_meta = os.path.join(MAILBOX_ROOT, cand_box, "daemon.json")
    if os.path.exists(daemon_meta):
        try:
            d = json.load(open(daemon_meta))
            return cand_box, d.get("harness", explicit_harness or "agy"), d.get("conversation_id", target), cand_box
        except Exception:
            pass

    # Check Claude sessions (live + recent)
    if explicit_harness in (None, "claude"):
        for p in list_peers.list_claude_sessions(recent=20):
            if (
                target == p["address"]
                or target == p["id"]
                or (len(target) >= 8 and p["id"].startswith(target))
                or (p["title"] and target.lower() == p["title"].lower())
            ):
                box = sanitize_box(p["address"] or p["id"])
                return box, "claude", p["id"], p["address"]

    # Check agy conversations (live + on-disk UUID/prefix/title)
    if explicit_harness in (None, "agy"):
        for p in list_peers.list_agy_sessions(recent=30):
            if (
                target == p["id"]
                or (len(target) >= 8 and re.match(r"^[0-9a-f-]+$", target) and p["id"].startswith(target))
                or (p["title"] and target.lower() == p["title"].lower())
            ):
                return p["id"], "agy", p["id"], p["id"]
        if re.match(r"^[0-9a-f]{8}(-[0-9a-f]{4,12})*$", target):
            for sub in ("antigravity-cli", "antigravity"):
                matches = glob.glob(os.path.join(HOME, ".gemini", sub, "conversations", f"{target}*.db"))
                if matches:
                    cid = os.path.basename(matches[0])[:-3]
                    return cid, "agy", cid, cid

    # Check Codex sessions (live + on-disk rollout UUID/prefix)
    if explicit_harness in (None, "codex"):
        for p in list_peers.list_codex_sessions(recent=30):
            if (
                target == p["id"]
                or (len(target) >= 8 and re.match(r"^[0-9a-f-]+$", target) and p["id"].startswith(target))
                or (p["title"] and target.lower() == p["title"].lower())
            ):
                return p["id"], "codex", p["id"], p["id"]
        if re.match(r"^[0-9a-f]{8}(-[0-9a-f]{4,12})*$", target):
            matches = glob.glob(os.path.join(HOME, ".codex", "sessions", "*", "*", "*", f"*{target}*.jsonl"))
            if matches:
                m = re.search(
                    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
                    os.path.basename(matches[-1]),
                )
                if m:
                    cid = m.group(1)
                    return cid, "codex", cid, cid

    return cand_box, explicit_harness or "unknown", target, target


def detect_sender():
    """Walk parent PIDs to auto-detect which harness/session/model called mail.py."""
    pid = os.getpid()
    visited = set()
    while pid > 1 and pid not in visited:
        visited.add(pid)
        # 1. Check Claude session
        cc_sess = os.path.join(HOME, ".claude", "sessions", f"{pid}.json")
        if os.path.exists(cc_sess):
            try:
                d = json.load(open(cc_sess))
                sid = d.get("sessionId", "")
                name = d.get("name", sid)
                tr = list_peers.claude_transcript_path(d.get("cwd", ""), sid)
                _, model = list_peers.claude_meta_from_transcript(tr)
                return {"id": name or sid, "session_id": sid, "harness": "claude", "model": model or "claude"}
            except Exception:
                pass
        # 2. Check agy presence lock in /proc/<pid>/fd
        try:
            for fd in os.listdir(f"/proc/{pid}/fd"):
                t = os.readlink(f"/proc/{pid}/fd/{fd}")
                if "/presence/" in t and t.endswith(".lock"):
                    cid = os.path.basename(t)[:-5]
                    app_dir = os.path.dirname(os.path.dirname(t))
                    model = list_peers.agy_model_for_conv(app_dir, cid, pid=pid)
                    return {"id": cid, "session_id": cid, "harness": "agy", "model": model}
        except Exception:
            pass
        # 3. Check Codex process
        argv = list_peers.read_cmdline(pid)
        if argv and os.path.basename(argv[0]) in ("codex", "codex-linux-x64"):
            for p in list_peers.list_codex_sessions(recent=5):
                if p.get("pid") == pid:
                    return {"id": p["id"], "session_id": p["id"], "harness": "codex", "model": p["model"]}
            return {"id": f"pid-{pid}", "session_id": f"pid-{pid}", "harness": "codex", "model": "codex"}
        try:
            stat = open(f"/proc/{pid}/stat").read()
            pid = int(stat.rsplit(")", 1)[1].split()[1])
        except Exception:
            break
    return {"id": "cli", "session_id": "cli", "harness": "shell", "model": "none"}


def write_message_atomic(box, header, body):
    box_dir = os.path.join(MAILBOX_ROOT, box)
    os.makedirs(box_dir, exist_ok=True)
    os.makedirs(os.path.join(box_dir, "read"), exist_ok=True)
    ts_ms = int(time.time() * 1000)
    msg_id = header["id"]
    tmp_path = os.path.join(box_dir, f".tmp-{os.getpid()}-{msg_id}")
    final_path = os.path.join(box_dir, f"{ts_ms}-{msg_id}.msg")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(header, ensure_ascii=False) + "\n\n" + body.rstrip("\n") + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, final_path)
    return final_path


def parse_message_file(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    parts = content.split("\n\n", 1)
    header = json.loads(parts[0].splitlines()[0])
    body = parts[1].rstrip("\n") if len(parts) > 1 else ""
    return header, body


def list_unread_files(box):
    box_dir = os.path.join(MAILBOX_ROOT, box)
    if not os.path.exists(box_dir):
        return []
    return sorted(glob.glob(os.path.join(box_dir, "*.msg")))


def mark_read(path):
    box_dir = os.path.dirname(path)
    read_dir = os.path.join(box_dir, "read")
    os.makedirs(read_dir, exist_ok=True)
    dst = os.path.join(read_dir, os.path.basename(path))
    try:
        os.replace(path, dst)
    except FileNotFoundError:
        pass
    return dst


def format_one_line(header, body):
    frm = header.get("from") or {}
    f_str = f"{frm.get('harness', '?')}:{frm.get('id', '?')} ({frm.get('model', '?')})"
    rep = f" reply_to={header.get('reply_to')}" if header.get("reply_to") else ""
    flat_body = " / ".join(l.strip() for l in body.splitlines() if l.strip())
    return f"[MAIL id={header.get('id')} from={f_str}{rep}] {flat_body}"


def deliver_message(box, harness, session_id, peer_addr, header, body, claude_relay=False, resume=False, model_override=None):
    frm = header.get("from") or {}
    sender_addr = f"{frm.get('harness', 'agent')}:{frm.get('id', 'unknown')}"
    reply_hint = (
        f"Reply with: python3 {os.path.abspath(__file__)} send {sender_addr} "
        f"--reply-to {header['id']} \"<your reply>\" --deliver"
    )

    if harness == "agy":
        bridge = os.path.join(SCRIPT_DIR, "agy_bridge.py")
        cmd = [sys.executable, bridge, "deliver", box]
        if model_override:
            cmd += ["--model", model_override]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"bridge": "agy_bridge", "exit": res.returncode, "stdout": res.stdout.strip(), "stderr": res.stderr.strip()}

    if harness == "codex":
        msg_text = f"[Mail {header['id']} from {sender_addr} ({frm.get('model', '')})] {body}\n({reply_hint})"
        q_res = subprocess.run(
            ["codex", "queue", "--thread", session_id, "--message", msg_text],
            capture_output=True,
            text=True,
        )
        out = {"bridge": "codex_queue", "queue_exit": q_res.returncode, "queue_out": (q_res.stdout + q_res.stderr).strip()}
        if resume:
            r_cmd = [
                "codex", "exec", "--dangerously-bypass-approvals-and-sandbox",
                "--skip-git-repo-check", "--json", "resume", session_id,
                f"Check your queued message / mailbox ({box}) and respond. {reply_hint}",
            ]
            if model_override:
                r_cmd[2:2] = ["-m", model_override]
            r_res = subprocess.run(r_cmd, capture_output=True, text=True)
            out["resume_exit"] = r_res.returncode
        return out

    if harness == "claude":
        if claude_relay:
            relay_prompt = (
                f"Use the SendMessage tool to send this exact text to the session named {peer_addr}: "
                f"'[Mail {header['id']} from {sender_addr} ({frm.get('model', '')})] {body} -- {reply_hint}'. "
                f"Reply SENT or the error."
            )
            c_res = subprocess.run(
                ["claude", "-p", "--model", "haiku", "--effort", "low", "--dangerously-skip-permissions"],
                input=relay_prompt,
                capture_output=True,
                text=True,
            )
            return {"bridge": "claude_relay", "exit": c_res.returncode, "stdout": c_res.stdout.strip()}
        return {"bridge": "mailbox_only", "note": f"queued in {box} for zero-token Monitor/read pickup"}

    return {"bridge": "mailbox_only", "note": f"stored in {box}"}


def cmd_send(args):
    from_id = harness = model = reply_to = model_override = None
    deliver = claude_relay = resume = False
    pos = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--from" and i + 1 < len(args):
            from_id = args[i + 1]; i += 2
        elif a == "--harness" and i + 1 < len(args):
            harness = args[i + 1]; i += 2
        elif a == "--model" and i + 1 < len(args):
            model = args[i + 1]; model_override = model; i += 2
        elif a == "--reply-to" and i + 1 < len(args):
            reply_to = args[i + 1]; i += 2
        elif a == "--deliver":
            deliver = True; i += 1
        elif a == "--claude-relay":
            claude_relay = True; deliver = True; i += 1
        elif a == "--resume":
            resume = True; deliver = True; i += 1
        else:
            pos.append(a); i += 1

    if len(pos) < 2:
        sys.stderr.write("Usage: mail.py send <to> <text|-> [options]\n")
        sys.exit(2)

    raw_to = pos[0]
    body = sys.stdin.read() if pos[1] == "-" else " ".join(pos[1:])
    sender = detect_sender()
    if from_id:
        sender["id"] = from_id
    if harness:
        sender["harness"] = harness
    if model:
        sender["model"] = model

    box, target_harness, target_sid, target_addr = resolve_recipient(raw_to)
    # A misspelled name would silently create a mailbox nobody reads. Warn when the name
    # matches no live or recent peer and no one has watched or received mail under it.
    warning = None
    if target_harness == "unknown" and not os.path.isdir(os.path.join(MAILBOX_ROOT, box)):
        warning = (f"'{raw_to}' matches no known peer and no existing mailbox; created a new one. "
                   "Fine for a lane name, otherwise check the spelling (list_peers.py shows peers).")
        sys.stderr.write(f"mail.py: warning: {warning}\n")
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    msg_id = f"msg-{stamp}-{secrets.token_hex(2)}"

    header = {
        "id": msg_id,
        "from": {
            "id": sender["id"],
            "harness": sender["harness"],
            "model": sender["model"],
        },
        "to": box,
        "target_harness": target_harness,
        "ts": now_iso,
        "reply_to": reply_to,
    }
    path = write_message_atomic(box, header, body)
    out = {"ok": True, "id": msg_id, "to": box, "target_harness": target_harness, "path": path}
    if warning:
        out["warning"] = warning
    if deliver:
        out["delivery"] = deliver_message(
            box, target_harness, target_sid, target_addr, header, body,
            claude_relay=claude_relay, resume=resume, model_override=model_override,
        )
    print(json.dumps(out))


def cmd_read(args):
    keep = "--keep" in args or "--peek" in args
    as_json = "--json" in args
    pos = [a for a in args if not a.startswith("--")]
    if not pos:
        sender = detect_sender()
        raw_me = sender["id"]
    else:
        raw_me = pos[0]

    box, _, _, _ = resolve_recipient(raw_me)
    files = list_unread_files(box)
    messages = []
    for f in files:
        try:
            h, b = parse_message_file(f)
        except Exception:
            continue
        if not keep:
            mark_read(f)
        messages.append({"header": h, "body": b})

    if as_json:
        print(json.dumps(messages, indent=2))
        return

    if not messages:
        print(f"No unread messages for {box}.")
        return

    for m in messages:
        print(format_one_line(m["header"], m["body"]))


def cmd_watch(args):
    once = "--once" in args
    ack = "--ack" in args
    from_now = "--from-now" in args
    timeout = None
    interval = 1.0
    pos = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--once", "--ack", "--from-now"):
            i += 1
        elif a == "--timeout" and i + 1 < len(args):
            timeout = float(args[i + 1]); i += 2
        elif a == "--interval" and i + 1 < len(args):
            interval = float(args[i + 1]); i += 2
        else:
            pos.append(a); i += 1

    if not pos:
        raw_me = detect_sender()["id"]
    else:
        raw_me = pos[0]

    box, _, _, _ = resolve_recipient(raw_me)
    # Watching claims the name, so senders to it are not warned about a possible typo.
    os.makedirs(os.path.join(MAILBOX_ROOT, box, "read"), exist_ok=True)
    seen = set(list_unread_files(box)) if from_now else set()
    start = time.time()

    while True:
        files = list_unread_files(box)
        printed = 0
        for f in files:
            if f in seen:
                continue
            seen.add(f)
            try:
                h, b = parse_message_file(f)
            except Exception:
                continue
            if ack:
                mark_read(f)
            print(format_one_line(h, b), flush=True)
            printed += 1
        if once and printed > 0:
            sys.exit(0)
        if timeout is not None and (time.time() - start) >= timeout:
            sys.exit(124 if once else 0)
        time.sleep(interval)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__.strip())
        sys.exit(0)
    sub = sys.argv[1]
    rest = sys.argv[2:]
    if sub == "send":
        cmd_send(rest)
    elif sub == "read":
        cmd_read(rest)
    elif sub == "watch":
        cmd_watch(rest)
    else:
        sys.stderr.write(f"Unknown subcommand: {sub}\n")
        sys.exit(2)


if __name__ == "__main__":
    main()
