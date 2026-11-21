#!/usr/bin/env python3
"""Resume headless Claude Code lanes that a usage limit cut off, with nobody at the keyboard.

A lane started by run_lane.sh ends with a non-zero exit and "You've hit your 5-hour limit · resets
6:40am (Asia/Kuala_Lumpur)" as its last message when the account runs out of quota. Until someone
resumes it, nothing happens. This watcher is plain Python outside any agent session, so the limit
cannot stop it: it finds those runs, waits for the reset time and resumes each lane from its own
session id, model, effort and extra folders.

    autoresume.py show    <root>...     what it sees for every lane and what it would do
    autoresume.py once    <root>...     one sweep, resume what is due
    autoresume.py watch   <root>...     sweep every --interval seconds until stopped
    autoresume.py service install <root>... [watch options]   a systemd user service that survives reboot
    autoresume.py service status | remove
    autoresume.py selftest

<root> is a lane root: runs live in <root>/work/agents/<lane>-<stamp>/, as run_lane.sh writes them.

A lane is resumed when its NEWEST run: is a Claude run, has exit.txt with a non-zero code, ends on a
usage-limit message, ended less than --max-age-hours ago, has no `no-autoresume` file in it, and the
reset time has passed. A run that ended with exit 0 is finished work and is never touched: the lead
decides what comes next. A limit message with no readable reset time is retried every
--retry-minutes (a still-limited CLI exits at once and costs nothing).

To keep a lane stopped after a limit hit, `touch <run folder>/no-autoresume`.
"""
import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None

HERE = Path(__file__).resolve().parent
UNIT = "agent-autoresume.service"
STAMP = re.compile(r"^(?P<lane>.+)-(?P<stamp>\d{8}-\d{6})$")
LIMIT = re.compile(r"(?:hit|reached)\s+your\s+[^\n]{0,40}?limit", re.I)
RESET = re.compile(
    r"resets?\s+(?:at\s+)?"
    r"(?:(?P<mon>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(?P<day>\d{1,2}),?\s+(?:at\s+)?)?"
    r"(?P<h>\d{1,2})(?::(?P<m>\d{2}))?\s*(?P<ap>[ap]m)"
    r"(?:\s*\((?P<tz>[A-Za-z_]+/[A-Za-z0-9_/+-]+)\))?", re.I)
MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
MESSAGE = ("The usage limit cut you off; it has reset. Continue from where you stopped: read your report file and "
           "your brief, check what is on disk first, then carry on. Keep your report current as you go.")


def log(text):
    print(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {text}", flush=True)


def now():
    return dt.datetime.now().astimezone()


def tail(path, size=3000):
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    return data[-size:].decode("utf-8", "replace")


def parse_limit(text, ended):
    """(is a usage limit, reset time or None when the message names no time we can read)."""
    if not LIMIT.search(text):
        return False, None
    m = RESET.search(text)
    if not m:
        return True, None
    zone = None
    if m.group("tz") and ZoneInfo:
        try:
            zone = ZoneInfo(m.group("tz"))
        except Exception:
            zone = None
    base = ended.astimezone(zone) if zone else ended
    hour = int(m.group("h")) % 12 + (12 if m.group("ap").lower() == "pm" else 0)
    reset = base.replace(hour=hour, minute=int(m.group("m") or 0), second=0, microsecond=0)
    if m.group("mon"):
        reset = reset.replace(month=MONTHS[m.group("mon").lower()[:3]], day=int(m.group("day")))
        if reset < base - dt.timedelta(days=1):
            reset = reset.replace(year=reset.year + 1)
    elif reset < base - dt.timedelta(minutes=5):
        reset += dt.timedelta(days=1)
    return True, reset.astimezone()


def newest_runs(root):
    """{lane: [run folders, oldest first]} under <root>/work/agents."""
    lanes = {}
    for run in (Path(root) / "work" / "agents").glob("*"):
        m = STAMP.match(run.name)
        if m and run.is_dir():
            lanes.setdefault(m.group("lane"), []).append(run)
    return {lane: sorted(runs, key=lambda p: p.name) for lane, runs in lanes.items()}


def read(path):
    try:
        return path.read_text(errors="replace").strip()
    except OSError:
        return ""


def session_id(runs):
    """The newest run's session id, else the newest earlier one: every resume keeps the same session."""
    for run in reversed(runs):
        sid = read(run / "id.txt").splitlines()[-1:] or [""]
        if sid[0]:
            return sid[0]
        m = re.search(r'"session_id"\s*:\s*"([0-9a-f-]{36})"', tail(run / "events.jsonl", 200000))
        if m:
            return m.group(1)
    return ""


def add_dirs(runs):
    for run in reversed(runs):
        if (run / "add-dirs.txt").exists():
            return read(run / "add-dirs.txt")
    return ""


def decide(runs, opts, at=None):
    """('skip' | 'wait' | 'resume', reason, reset time) for a lane, from its newest run."""
    at = at or now()
    run = runs[-1]
    if (read(run / "vendor.txt") or "claude") != "claude":
        return "skip", "not a Claude lane", None
    exit_file = run / "exit.txt"
    if not exit_file.exists():
        return "skip", "running, or stopped without an exit code", None
    if read(exit_file) in ("", "0"):
        return "skip", "finished", None
    ended = dt.datetime.fromtimestamp(exit_file.stat().st_mtime).astimezone()
    limited, reset = parse_limit(tail(run / "last-message.md", 800) + "\n" + tail(run / "stderr.log", 800), ended)
    if not limited:
        return "skip", f"failed with exit {read(exit_file)}, not a usage limit", None
    if (run / "no-autoresume").exists():
        return "skip", "held by a no-autoresume file", reset
    if (run / "autoresumed.txt").exists():
        return "skip", "already resumed, new run not visible yet", reset
    if at - ended > dt.timedelta(hours=opts.max_age_hours):
        return "skip", f"cut off more than {opts.max_age_hours:g} h ago", reset
    if reset is None:
        due = ended + dt.timedelta(minutes=opts.retry_minutes)
        return ("resume", "limit with no readable reset time, trying", None) if at >= due else \
               ("wait", f"limit with no readable reset time, next try {due:%H:%M}", due)
    due = reset + dt.timedelta(seconds=opts.margin)
    if at < due:
        return "wait", f"limit resets {reset:%a %H:%M}", due
    return "resume", f"limit reset at {reset:%a %H:%M}", reset


def launcher():
    unit = HERE / "run_lane_unit.sh"
    return unit if unit.exists() and shutil.which("systemd-run") else HERE / "run_lane.sh"


def resume(root, lane, runs, opts):
    run, sid = runs[-1], session_id(runs)
    if not sid:
        log(f"{lane}: no session id in any run folder, cannot resume")
        (run / "no-autoresume").write_text("no session id found\n")
        return
    saved = (read(run / "model.txt") or "opus high").split()
    model, effort = opts.model or saved[0], opts.effort or (saved[1] if len(saved) > 1 else "high")
    env = dict(os.environ, LANE_ADD_DIRS=add_dirs(runs))
    subprocess.Popen([str(launcher()), "claude", model, effort, str(root), lane, "--resume", sid, opts.message],
                     cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    (run / "autoresumed.txt").write_text(f"{now().isoformat()} session {sid} on {model} {effort}\n")
    log(f"{lane}: resumed session {sid} on {model} {effort}")
    if opts.mail:
        subprocess.run([sys.executable, "-I", str(HERE / "mail.py"), "send", opts.mail,
                        f"autoresume: lane {lane} was cut off by the usage limit and is running again "
                        f"(session {sid}, {model} {effort}).", "--from", "autoresume"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def sweep(opts, act, said):
    for root in opts.roots:
        root = Path(root).resolve()
        for lane, runs in sorted(newest_runs(root).items()):
            if opts.only and lane not in opts.only:
                continue
            action, reason, _ = decide(runs, opts)
            if not act:
                print(f"{lane:28} {runs[-1].name[-15:]}  {action:6} {reason}")
            elif action == "resume":
                resume(root, lane, runs, opts)
            elif action == "wait" and said.get(runs[-1]) != reason:
                said[runs[-1]] = reason
                log(f"{lane}: {reason}")


def watch(opts):
    said = {}
    log(f"watching {', '.join(map(str, opts.roots))} every {opts.interval} s")
    while True:
        try:
            sweep(opts, True, said)
        except Exception as error:  # a vanished folder or a half-written file must not end the watcher
            log(f"sweep failed: {error!r}")
        time.sleep(opts.interval)


def service(opts):
    unit_file = Path.home() / ".config/systemd/user" / UNIT
    ctl = ["systemctl", "--user"]
    if opts.verb == "status":
        sys.exit(subprocess.run(ctl + ["status", UNIT, "--no-pager", "-n", "15"]).returncode)
    if opts.verb == "remove":
        subprocess.run(ctl + ["disable", "--now", UNIT])
        unit_file.unlink(missing_ok=True)
        subprocess.run(ctl + ["daemon-reload"])
        return
    if not opts.roots:
        sys.exit("service install needs at least one lane root")
    args = ["watch"] + [str(Path(r).resolve()) for r in opts.roots] + [
        "--interval", str(opts.interval), "--max-age-hours", str(opts.max_age_hours),
        "--retry-minutes", str(opts.retry_minutes), "--margin", str(opts.margin)]
    for flag, value in (("--model", opts.model), ("--effort", opts.effort), ("--mail", opts.mail),
                        ("--only", ",".join(opts.only))):
        if value:
            args += [flag, value]
    quoted = " ".join("'" + a.replace("'", "'\\''") + "'" for a in [sys.executable, str(Path(__file__).resolve())] + args)
    unit_file.parent.mkdir(parents=True, exist_ok=True)
    # The lane needs the agent CLI on PATH; a user service starts with a bare one, so keep this shell's.
    unit_file.write_text(f"""[Unit]
Description=Resume agent lanes cut off by a usage limit

[Service]
Environment=PATH={os.environ.get("PATH", "")}
ExecStart={quoted}
Restart=on-failure
RestartSec=30
Slice=background.slice

[Install]
WantedBy=default.target
""")
    subprocess.run(ctl + ["daemon-reload"], check=True)
    subprocess.run(ctl + ["enable", "--now", UNIT], check=True)
    subprocess.run(ctl + ["restart", UNIT], check=True)
    print(f"installed and started {UNIT}; log: journalctl --user -u {UNIT} -f")


def selftest():
    opts = argparse.Namespace(max_age_hours=24.0, retry_minutes=30.0, margin=180)
    at = dt.datetime(2026, 3, 10, 12, 0).astimezone()
    cases = [
        ("You've hit your 5-hour limit · resets 6:40am (Asia/Kuala_Lumpur)", "2026-03-10T03:00", (True, "03-10 06:40")),
        ("You've hit your 5-hour limit · resets 1:40am", "2026-03-09T23:50", (True, "03-10 01:40")),
        ("You've hit your weekly limit · resets Mar 12, 11am", "2026-03-10T03:00", (True, "03-12 11:00")),
        ("You have reached your usage limit. It resets at 8:20pm.", "2026-03-10T19:00", (True, "03-10 20:20")),
        ("You've hit your limit, try again later", "2026-03-10T03:00", (True, None)),
        ("ordinary failure: file not found", "2026-03-10T03:00", (False, None)),
    ]
    for text, ended, (limited, when) in cases:
        end = dt.datetime.fromisoformat(ended).astimezone()
        if "Kuala_Lumpur" in text and ZoneInfo:
            end = dt.datetime.fromisoformat(ended).replace(tzinfo=ZoneInfo("Asia/Kuala_Lumpur"))
        got, reset = parse_limit(text, end)
        local = reset.astimezone(end.tzinfo).strftime("%m-%d %H:%M") if reset else None
        assert (got, local) == (limited, when), (text, got, local)
    with tempfile.TemporaryDirectory(prefix="autoresume-selftest-") as tmp:
        agents = Path(tmp) / "work" / "agents"

        def run(lane, stamp, exit_code, message, age_h=1.0, vendor="claude", extra=()):
            folder = agents / f"{lane}-{stamp}"
            folder.mkdir(parents=True)
            (folder / "vendor.txt").write_text(vendor + "\n")
            (folder / "model.txt").write_text("opus high\n")
            (folder / "id.txt").write_text("01234567-89ab-cdef-0123-456789abcdef\n")
            (folder / "last-message.md").write_text(message + "\n")
            if exit_code is not None:
                (folder / "exit.txt").write_text(f"{exit_code}\n")
                stamp_s = (at - dt.timedelta(hours=age_h)).timestamp()
                os.utime(folder / "exit.txt", (stamp_s, stamp_s))
            for name in extra:
                (folder / name).write_text("x\n")

        hit = "You've hit your 5-hour limit · resets {}"
        run("due", "20260310-090000", 1, hit.format("11:30am"))
        run("later", "20260310-090000", 1, hit.format("1:15pm"))
        run("done", "20260310-090000", 0, "All finished.")
        run("broken", "20260310-090000", 2, "Traceback: boom")
        run("held", "20260310-090000", 1, hit.format("11:30am"), extra=("no-autoresume",))
        run("stale", "20260308-090000", 1, hit.format("11:30am"), age_h=50)
        run("codex", "20260310-090000", 1, hit.format("11:30am"), vendor="codex")
        run("alive", "20260310-090000", None, "")
        run("twice", "20260310-080000", 1, hit.format("9:00am"), age_h=4)
        run("twice", "20260310-100000", 0, "Finished after the resume.")
        run("notime", "20260310-090000", 1, "You've hit your limit.", age_h=1.0)
        want = {"due": "resume", "later": "wait", "done": "skip", "broken": "skip", "held": "skip", "stale": "skip",
                "codex": "skip", "alive": "skip", "twice": "skip", "notime": "resume"}
        runs = newest_runs(tmp)
        got = {lane: decide(folders, opts, at)[0] for lane, folders in runs.items()}
        assert got == want, got
        assert session_id(runs["due"]) == "01234567-89ab-cdef-0123-456789abcdef"
    print("autoresume selftest: ok")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("roots", nargs="*", help="lane roots (folders holding work/agents/)")
        p.add_argument("--only", default="", help="comma separated lane names; default every lane")
        p.add_argument("--max-age-hours", type=float, default=24.0,
                       help="leave runs cut off longer ago than this alone (default 24)")
        p.add_argument("--retry-minutes", type=float, default=30.0,
                       help="retry spacing when the limit message names no reset time (default 30)")
        p.add_argument("--margin", type=int, default=180, help="seconds to wait past the reset time (default 180)")
        p.add_argument("--interval", type=int, default=300, help="seconds between sweeps (default 300)")
        p.add_argument("--model", default="", help="resume on this model instead of the lane's own")
        p.add_argument("--effort", default="", help="resume at this effort instead of the lane's own")
        p.add_argument("--mail", default="", help="mailbox to tell when a lane is resumed (mail.py name)")
        p.add_argument("--message", default=MESSAGE, help="what the resumed lane is told")

    for name in ("show", "once", "watch"):
        common(sub.add_parser(name))
    svc = sub.add_parser("service")
    svc.add_argument("verb", choices=("install", "status", "remove"))
    common(svc)
    sub.add_parser("selftest")
    opts = parser.parse_args()
    if opts.command == "selftest":
        return selftest()
    opts.only = [x for x in opts.only.split(",") if x]
    if opts.command == "service":
        return service(opts)
    if not opts.roots:
        parser.error("give at least one lane root")
    if opts.command == "watch":
        return watch(opts)
    sweep(opts, opts.command == "once", {})


if __name__ == "__main__":
    main()
