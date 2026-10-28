"""Watch live Claude Code sessions and print one line per event worth reporting: a question waiting
on the user, a turn ending (with its last message), a session appearing or exiting. Lines are
labelled with the chat title the user sees on the tab. Run under the Monitor tool.
Usage: watch_sessions.py [cwd]   only sessions whose working directory is cwd (default: all others)"""
import glob, json, os, subprocess, sys, time
SESS = os.path.expanduser("~/.claude/sessions")
CWD = os.path.abspath(os.path.expanduser(sys.argv[1])) if len(sys.argv) > 1 else None

def own_session_pid():
    # The Claude process that launched this watcher, so it never reports on itself.
    p = os.getpid()
    while p > 1:
        if os.path.exists(f"{SESS}/{p}.json"):
            return p
        try:
            p = int(open(f"/proc/{p}/stat").read().rsplit(")", 1)[1].split()[1])
        except Exception:
            return None
    return None

ME = own_session_pid()

def transcript(d):
    proj = d.get("cwd", "").replace("/", "-").replace(".", "-")
    return os.path.expanduser(f"~/.claude/projects/{proj}/{d.get('sessionId')}.jsonl")
st = {}  # pid -> {name, file, pos, status, last_text}

def clip(s, n=700):
    s = " / ".join(l.strip() for l in s.splitlines() if l.strip())
    return s if len(s) <= n else s[:n] + "..."

def title_of(tr):
    # The VS Code tab shows the custom title if one was set, else the latest AI title.
    try:
        out = subprocess.run(["grep", "-E", '"type":"(custom-title|ai-title)"', tr], capture_output=True, text=True).stdout
    except Exception:
        return None
    custom = ai = None
    for line in out.splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("type") == "custom-title": custom = r.get("customTitle")
        else: ai = r.get("aiTitle")
    return custom or ai, bool(custom)

def label(s):
    t = s.get("title")
    return f'"{t}" ({s["name"]})' if t and t != s["name"] else s["name"]

def say(msg):
    print(msg, flush=True)

def scan():
    alive = set()
    for f in glob.glob(f"{SESS}/*.json"):
        try:
            pid = int(os.path.basename(f).split(".")[0]); d = json.load(open(f))
        except Exception:
            continue
        if pid == ME or not os.path.exists(f"/proc/{pid}") or (CWD and d.get("cwd", "") != CWD):
            continue
        alive.add(pid)
        tr = transcript(d)
        s = st.get(pid)
        if s is None:
            s = st[pid] = {"name": d.get("name", str(pid)), "file": tr, "status": d.get("status"),
                           "pos": os.path.getsize(tr) if os.path.exists(tr) else 0, "last_text": ""}
            s["title"], s["custom"] = title_of(tr) or (None, False)
            if len(st) > 0 and started:
                say(f"[{label(s)}] new session appeared ({s['status']})")
        if tr != s["file"]:
            s["file"], s["pos"] = tr, 0
        read_new(s)
        new = d.get("status")
        if new != s["status"]:
            if new == "idle" and s["last_text"]:
                say(f"[{label(s)}] finished a turn: {clip(s['last_text'])}")
            elif new == "waiting":
                say(f"[{label(s)}] is WAITING (question or permission prompt open)")
            s["status"] = new
    for pid in list(st):
        if pid not in alive:
            say(f"[{label(st[pid])}] session process exited")
            del st[pid]

def read_new(s):
    try:
        with open(s["file"], "rb") as fh:
            fh.seek(s["pos"]); data = fh.read()
    except FileNotFoundError:
        return
    end = data.rfind(b"\n")
    if end < 0:
        return
    s["pos"] += end + 1
    for line in data[:end].splitlines():
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("type") == "custom-title":
            s["title"], s["custom"] = r.get("customTitle") or s.get("title"), True
        elif r.get("type") == "ai-title" and not s.get("custom"):
            s["title"] = r.get("aiTitle") or s.get("title")
        if r.get("type") != "assistant":
            continue
        for c in (r.get("message") or {}).get("content") or []:
            if c.get("type") == "text" and c.get("text", "").strip():
                s["last_text"] = c["text"]
            elif c.get("type") == "tool_use" and c.get("name") == "AskUserQuestion":
                qs = c.get("input", {}).get("questions", [])
                for q in qs:
                    opts = " | ".join(o.get("label", "") for o in q.get("options", []))
                    say(f"[{label(s)}] ASKS YOU: {clip(q.get('question',''), 500)} OPTIONS: {opts}")

started = False
scan(); started = True
say("watching: " + ", ".join(f"{label(v)} ({v['status']})" for v in st.values()))
while True:
    time.sleep(5)
    try:
        scan()
    except Exception as e:
        say(f"watcher error: {e}")
