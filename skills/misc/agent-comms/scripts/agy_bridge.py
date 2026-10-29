#!/usr/bin/env python3
"""Antigravity (agy) delivery bridge and long-lived stream-json inbox daemon.

Modes:
  1. Deliver unread mailbox messages to an agy session (daemon FIFO, interactive wakeup, or headless --conversation):
     agy_bridge.py deliver <target> [--model MODEL] [--timeout SEC]

  2. Manage a long-lived headless agy inbox (--input-format stream-json):
     agy_bridge.py daemon start <name> [--model MODEL] [--cwd DIR] [--conversation CID]
     agy_bridge.py daemon status <name>
     agy_bridge.py daemon stop <name>
"""
import glob
import json
import os
import re
import signal
import subprocess
import sys
sys.dont_write_bytecode = True
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import list_peers  # noqa: E402
import mail  # noqa: E402

HOME = os.path.expanduser("~")
MAIL_PY = os.path.join(SCRIPT_DIR, "mail.py")

MODEL_SHORT = {
    "argon": "gemini-4-argon-high",
    "argon-low": "gemini-4-argon-low",
    "argon-medium": "gemini-4-argon-medium",
    "argon-high": "gemini-4-argon-high",
    "flash": "gemini-3.8-flash-low",
    "flash-low": "gemini-3.8-flash-low",
    "flash-medium": "gemini-3.8-flash-medium",
    "flash-high": "gemini-3.8-flash-high",
    "agy-opus": "claude-opus-5-5-high",
    "agy-opus-low": "claude-opus-5-5-low",
    "agy-opus-medium": "claude-opus-5-5-medium",
    "agy-opus-high": "claude-opus-5-5-high",
    "agy-sonnet": "claude-sonnet-5-5-low",
    "agy-sonnet-low": "claude-sonnet-5-5-low",
    "agy-sonnet-medium": "claude-sonnet-5-5-medium",
    "agy-sonnet-high": "claude-sonnet-5-5-high",
    "gpt-oss": "gpt-oss-120b-medium",
    "gpt-oss-120b": "gpt-oss-120b-medium",
}


def normalize_agy_model(m):
    if not m or m == "unknown":
        return "gemini-3.8-flash-low"
    if m in MODEL_SHORT:
        return MODEL_SHORT[m]
    # Map human labels from cli.log back to model ids
    low = m.lower()
    for base, label in (
        ("gemini-4-argon", "gemini 4 argon"),
        ("gemini-3.8-flash", "gemini 3.8 flash"),
        ("claude-opus-5-5", "claude opus 5.5"),
        ("claude-sonnet-5-5", "claude sonnet 5.5"),
        ("gpt-oss-120b", "gpt-oss 120b"),
    ):
        if label in low or m == base:
            if base == "gpt-oss-120b":
                return "gpt-oss-120b-medium"
            for eff in ("low", "medium", "high"):
                if f"({eff})" in low:
                    return f"{base}-{eff}"
            return f"{base}-low"
    return m


def find_live_lock_holder(cid):
    for pdir in glob.glob("/proc/[0-9]*"):
        try:
            pid = int(os.path.basename(pdir))
            for fd in os.listdir(f"{pdir}/fd"):
                t = os.readlink(f"{pdir}/fd/{fd}")
                if t.endswith(f"/presence/{cid}.lock"):
                    return pid, os.path.dirname(os.path.dirname(t))
        except Exception:
            continue
    return None, None


def count_results(events_path):
    if not os.path.exists(events_path):
        return 0, None
    cnt = 0
    last = None
    with open(events_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"event":"result"' in line:
                try:
                    obj = json.loads(line)
                    if obj.get("event") == "result":
                        cnt += 1
                        last = obj.get("result")
                except Exception:
                    pass
    return cnt, last


def format_delivery_prompt(messages):
    lines = []
    for h, b in messages:
        frm = h.get("from") or {}
        sender = f"{frm.get('harness', 'agent')}:{frm.get('id', 'unknown')}"
        model = frm.get("model", "unknown")
        mid = h.get("id", "")
        rep = f" (reply_to={h.get('reply_to')})" if h.get("reply_to") else ""
        lines.append(
            f"[Incoming Mail id={mid} from={sender} model={model}{rep}]\n"
            f"{b}\n"
            f"To reply to sender, run: python3 {MAIL_PY} send {sender} --reply-to {mid} \"<your reply>\"\n"
        )
    return "\n".join(lines)


def cmd_deliver(args):
    model_override = None
    timeout = 90.0
    pos = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--model" and i + 1 < len(args):
            model_override = args[i + 1]; i += 2
        elif a == "--timeout" and i + 1 < len(args):
            timeout = float(args[i + 1]); i += 2
        else:
            pos.append(a); i += 1

    if not pos:
        sys.stderr.write("Usage: agy_bridge.py deliver <target> [--model MODEL]\n")
        sys.exit(2)

    box, _, target_sid, _ = mail.resolve_recipient(pos[0])
    box_dir = os.path.join(mail.MAILBOX_ROOT, box)
    daemon_meta_path = os.path.join(box_dir, "daemon.json")

    # 1. Check if a stream-json daemon is active for this mailbox
    if os.path.exists(daemon_meta_path):
        try:
            dmeta = json.load(open(daemon_meta_path))
            dpid = dmeta.get("pid")
            if dpid and list_peers.proc_alive(dpid):
                files = mail.list_unread_files(box)
                if not files:
                    print(json.dumps({"mode": "stream-json-daemon", "note": "no unread messages"}))
                    return
                msgs = []
                for f in files:
                    msgs.append(mail.parse_message_file(f))
                    mail.mark_read(f)
                prompt = format_delivery_prompt(msgs)
                events_path = dmeta["events_path"]
                feed_path = dmeta["feed_path"]
                before_cnt, _ = count_results(events_path)
                payload = {"event": "user", "message": {"content": prompt}}
                with open(feed_path, "a", encoding="utf-8") as ff:
                    ff.write(json.dumps(payload, ensure_ascii=False) + "\n")
                    ff.flush()
                t0 = time.time()
                while time.time() - t0 < timeout:
                    now_cnt, last_res = count_results(events_path)
                    if now_cnt > before_cnt:
                        print(json.dumps({
                            "mode": "stream-json-daemon",
                            "conversation_id": dmeta.get("conversation_id"),
                            "model": dmeta.get("model"),
                            "result": last_res,
                        }))
                        return
                    time.sleep(0.5)
                print(json.dumps({"mode": "stream-json-daemon", "error": "timeout waiting for turn result"}))
                sys.exit(1)
        except Exception as e:
            sys.stderr.write(f"daemon delivery check error: {e}\n")

    # 2. Check if target_sid has a live interactive lock holder
    pid, app_dir = find_live_lock_holder(target_sid)
    if pid:
        # Leave unread in mailbox so the interactive session's `mail.py watch --once` wakes it
        print(json.dumps({
            "mode": "interactive-mailbox-wakeup",
            "conversation_id": target_sid,
            "pid": pid,
            "mailbox": box,
            "note": "left unread in mailbox for live session wakeup",
        }))
        return

    # 3. Idle conversation on disk: resume headlessly with `agy -p --conversation <cid>`
    files = mail.list_unread_files(box)
    if not files:
        print(json.dumps({"mode": "headless-resume", "note": "no unread messages"}))
        return
    msgs = []
    for f in files:
        msgs.append(mail.parse_message_file(f))
        mail.mark_read(f)
    prompt = format_delivery_prompt(msgs)

    app_dir = os.path.join(HOME, ".gemini", "antigravity-cli")
    model = normalize_agy_model(model_override or list_peers.agy_model_for_conv(app_dir, target_sid))
    _, cwd, _, _ = list_peers.agy_summary_for_conv(app_dir, target_sid)
    run_cwd = cwd if (cwd and os.path.isdir(cwd)) else HOME

    cmd = [
        "agy", "-p", prompt,
        "--model", model,
        "--dangerously-skip-permissions",
        "--output-format", "json",
        "--add-dir", run_cwd,
        "--add-dir", SCRIPT_DIR,
        "--add-dir", mail.MAILBOX_ROOT,
    ]
    if re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", target_sid):
        conv_db = os.path.join(app_dir, "conversations", f"{target_sid}.db")
        if os.path.exists(conv_db):
            cmd += ["--conversation", target_sid]

    res = subprocess.run(cmd, cwd=run_cwd, capture_output=True, text=True, timeout=timeout)
    try:
        out_json = json.loads(res.stdout)
    except Exception:
        out_json = {"raw_stdout": res.stdout[:500], "raw_stderr": res.stderr[:500]}
    print(json.dumps({
        "mode": "headless-resume",
        "conversation_id": out_json.get("conversation_id", target_sid),
        "model": model,
        "exit": res.returncode,
        "response": out_json.get("response", "").strip(),
    }))


def cmd_daemon(args):
    if len(args) < 2:
        sys.stderr.write("Usage: agy_bridge.py daemon <start|status|stop> <name> [options]\n")
        sys.exit(2)
    action = args[0]
    rest_all = args[1:]
    name_raw = None
    rest = []
    i = 0
    while i < len(rest_all):
        a = rest_all[i]
        if a in ("--id", "--name") and i + 1 < len(rest_all):
            name_raw = rest_all[i + 1]; i += 2
        elif name_raw is None and not a.startswith("-"):
            name_raw = a; i += 1
        else:
            rest.append(a); i += 1
    if not name_raw:
        sys.stderr.write("Usage: agy_bridge.py daemon <start|status|stop> <name> [options]\n")
        sys.exit(2)
    name = mail.sanitize_box(name_raw)
    box_dir = os.path.join(mail.MAILBOX_ROOT, name)
    meta_path = os.path.join(box_dir, "daemon.json")

    if action == "status":
        if not os.path.exists(meta_path):
            print(json.dumps({"name": name, "status": "stopped"}))
            return
        d = json.load(open(meta_path))
        alive = list_peers.proc_alive(d.get("pid", -1))
        d["status"] = "running" if alive else "stopped"
        print(json.dumps(d, indent=2))
        return

    if action == "stop":
        if not os.path.exists(meta_path):
            print(json.dumps({"name": name, "status": "already_stopped"}))
            return
        d = json.load(open(meta_path))
        for k in ("tail_pid", "pid"):
            p = d.get(k)
            if p and list_peers.proc_alive(p):
                try:
                    os.kill(p, signal.SIGTERM)
                except OSError:
                    pass
        print(json.dumps({"name": name, "status": "stopped", "conversation_id": d.get("conversation_id")}))
        return

    if action == "start":
        model = "gemini-3.8-flash-low"
        effort_override = None
        cwd = os.getcwd()
        conv_id = None
        i = 0
        while i < len(rest):
            a = rest[i]
            if a == "--model" and i + 1 < len(rest):
                model = normalize_agy_model(rest[i + 1]); i += 2
            elif a == "--effort" and i + 1 < len(rest):
                effort_override = rest[i + 1]; i += 2
            elif a == "--cwd" and i + 1 < len(rest):
                cwd = os.path.abspath(rest[i + 1]); i += 2
            elif a == "--conversation" and i + 1 < len(rest):
                conv_id = rest[i + 1]; i += 2
            else:
                i += 1
        if effort_override in ("low", "medium", "high") and not model.startswith("gpt-oss-120b"):
            base_m = re.sub(r"-(low|medium|high)$", "", model)
            model = f"{base_m}-{effort_override}"

        os.makedirs(box_dir, exist_ok=True)
        # Ensure the shared OAuth token is fresh via the ~/.local/bin/agy lock wrapper
        # before starting the long-lived daemon (which must not hold invocation.lock for hours).
        subprocess.run(
            ["agy", "-p", "/usage", "--output-format", "json"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )
        feed_path = os.path.join(box_dir, "feed.jsonl")
        events_path = os.path.join(box_dir, "events.jsonl")
        stderr_path = os.path.join(box_dir, "stderr.log")
        open(feed_path, "w").close()
        open(events_path, "w").close()

        tail_proc = subprocess.Popen(
            ["tail", "-f", "-n", "+1", feed_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        agy_cmd = [
            "agy", "-p=",
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--model", model,
            "--dangerously-skip-permissions",
            "--add-dir", cwd,
            "--add-dir", SCRIPT_DIR,
            "--add-dir", mail.MAILBOX_ROOT,
        ]
        if conv_id:
            agy_cmd += ["--conversation", conv_id]

        ev_out = open(events_path, "a", encoding="utf-8")
        err_out = open(stderr_path, "a", encoding="utf-8")
        agy_proc = subprocess.Popen(
            agy_cmd,
            cwd=cwd,
            stdin=tail_proc.stdout,
            stdout=ev_out,
            stderr=err_out,
            start_new_session=True,
        )
        tail_proc.stdout.close()

        cid = conv_id
        for _ in range(40):
            if os.path.exists(events_path):
                with open(events_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if '"event":"init"' in line:
                            try:
                                cid = json.loads(line).get("conversation_id") or cid
                            except Exception:
                                pass
            if cid:
                break
            time.sleep(0.25)

        meta = {
            "name": name,
            "harness": "agy",
            "model": model,
            "cwd": cwd,
            "pid": agy_proc.pid,
            "tail_pid": tail_proc.pid,
            "conversation_id": cid or "",
            "feed_path": feed_path,
            "events_path": events_path,
            "stderr_path": stderr_path,
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # Also link ~/.agent-mailbox/<cid> -> box_dir so addressing by conversation_id works
        if cid and cid != name:
            cid_link = os.path.join(mail.MAILBOX_ROOT, cid)
            if not os.path.exists(cid_link):
                try:
                    os.symlink(box_dir, cid_link)
                except OSError:
                    pass

        print(json.dumps(meta))
        return

    sys.stderr.write(f"Unknown daemon action: {action}\n")
    sys.exit(2)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__.strip())
        sys.exit(0)
    sub = sys.argv[1]
    rest = sys.argv[2:]
    if sub == "deliver":
        cmd_deliver(rest)
    elif sub == "daemon":
        cmd_daemon(rest)
    else:
        sys.stderr.write(f"Unknown subcommand: {sub}\n")
        sys.exit(2)


if __name__ == "__main__":
    main()
