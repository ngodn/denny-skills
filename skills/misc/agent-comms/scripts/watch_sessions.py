"""Watch live Claude Code sessions and print one line per event worth reporting: a question waiting
on the user, a turn ending (with its last message), a session appearing or exiting. Lines are
labelled with the chat title the user sees on the tab. Run under the Monitor tool.
Usage: watch_sessions.py [cwd] [--stall-minutes N]
  cwd               only sessions whose working directory is cwd (default: all others)
  --stall-minutes N also print a STALL line when a session has been idle N minutes with no
                    work process running under it (it said "I'll do X later" and nothing is
                    scheduled). Flags once per idle stretch."""
import glob, json, os, subprocess, sys, time
SESS = os.path.expanduser("~/.claude/sessions")
_args = [a for a in sys.argv[1:]]
STALL = None
if "--stall-minutes" in _args:
    i = _args.index("--stall-minutes"); STALL = float(_args[i + 1]) * 60; del _args[i:i + 2]
CWD = os.path.abspath(os.path.expanduser(_args[0])) if _args else None
# Long-lived helpers every session has; they are not "work".
IDLE_HELPERS = ("mcp-for-blender", "chrome-devtools-mcp", "rea-agents", "mcp", "uv tool", "npm exec", "npx")

def busy_descendants(pid):
    """Work processes under a session: anything in its tree except its standing MCP helpers."""
    kids, todo = [], [pid]
    while todo:
        p = todo.pop()
        try:
            children = open(f"/proc/{p}/task/{p}/children").read().split()
        except Exception:
            continue
        for c in children:
            todo.append(int(c))
            try:
                cmd = open(f"/proc/{c}/cmdline").read().replace("\0", " ")
            except Exception:
                continue
            if cmd and not any(h in cmd for h in IDLE_HELPERS):
                kids.append(cmd[:80])
    return kids

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
        if STALL and new == "idle":
            s.setdefault("idle_since", time.time())
            if not s.get("stall_flagged") and time.time() - s["idle_since"] > STALL and not busy_descendants(pid):
                s["stall_flagged"] = True
                say(f"[{label(s)}] STALL? idle {int((time.time()-s['idle_since'])/60)} min with nothing running. Last said: {clip(s['last_text'], 300)}")
        elif new != "idle":
            s.pop("idle_since", None); s.pop("stall_flagged", None)
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
