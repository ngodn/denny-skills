#!/usr/bin/env python3
"""Reach the agents on the user's other machines, over SSH carried by Tailscale.

  remote.py hosts [--json]                      known machines and whether each answers
  remote.py add <name> <user>@<host> [alias...] [--one-way]
                                                register a machine (and this one on it)
  remote.py remove <name>
  remote.py self                                the name other machines address this one by
  remote.py peers [<host>...] [--json] [--quota]   agent sessions on the other machines
  remote.py run <host> <command...>             run a shell command there (quoted like ssh)
  remote.py push <host> <local> <remote>        copy a file there
  remote.py pull <host> <remote> <local>        copy a file back
  remote.py lane <host> [--orca] <vendor> <model> <effort> <root> <lane> <local brief.md>
                                                start a lane there, led from here

<host> in `add` is the machine's Tailscale name (`tailscale status`). Every command runs the
same scripts on the other machine, so both need this skill installed. In a `run` command,
$AC is the other machine's agent-comms scripts folder and $DC its desktop-control one; single-quote
the command so they expand there. The registry is ~/.config/agent-comms/hosts.json.
"""
import getpass
import json
import os
import shlex
import socket
import subprocess
import sys
sys.dont_write_bytecode = True
import time
from concurrent.futures import ThreadPoolExecutor

HOME = os.path.expanduser("~")
CONFIG = os.environ.get("AGENT_HOSTS_FILE", os.path.join(HOME, ".config", "agent-comms", "hosts.json"))

# Runs first in every remote command. A non-interactive SSH shell has a short PATH and no desktop
# variables, so add where the agent CLIs live and point at the running Hyprland session.
PRELUDE = (
    'export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:'
    '$HOME/.config/orca/linux-orca-cli-shim:$HOME/.cargo/bin:$PATH"; '
    ': "${XDG_RUNTIME_DIR:=/run/user/$(id -u)}"; export XDG_RUNTIME_DIR; '
    'if [ -z "$HYPRLAND_INSTANCE_SIGNATURE" ]; then _s=$(ls -t "$XDG_RUNTIME_DIR/hypr" 2>/dev/null | head -1); '
    '[ -n "$_s" ] && export HYPRLAND_INSTANCE_SIGNATURE="$_s"; fi; '
    'for _d in "$HOME/.claude/skills" "$HOME/.agents/skills" "$HOME/.codex/skills"; do '
    '[ -z "$AC" ] && [ -d "$_d/agent-comms/scripts" ] && AC="$_d/agent-comms/scripts"; '
    '[ -z "$DC" ] && [ -d "$_d/desktop-control/scripts" ] && DC="$_d/desktop-control/scripts"; done; '
    'export AC DC; '
)

_tailnet = None


def tailnet():
    """{'self': name, 'peers': {name: online}} from Tailscale, or None when it is not running."""
    global _tailnet
    if _tailnet is None:
        _tailnet = False
        try:
            out = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=8)
            d = json.loads(out.stdout)
            # A node's DNS label is what `tailscale status` shows; HostName can differ ("iPad Pro").
            label = lambda n: (n.get("DNSName") or "").split(".")[0].lower() or (n.get("HostName") or "").lower()
            peers = {}
            for p in (d.get("Peer") or {}).values():
                peers[label(p)] = peers[(p.get("HostName") or "").lower()] = bool(p.get("Online"))
            _tailnet = {"self": label(d.get("Self") or {}), "peers": peers}
        except Exception:
            pass
    return _tailnet or None


def self_name():
    t = tailnet()
    return (t and t["self"]) or socket.gethostname().lower()


def is_self(name):
    return name.lower() in {self_name(), socket.gethostname().lower(), "localhost"}


def load():
    try:
        return json.load(open(CONFIG)).get("hosts", {})
    except Exception:
        return {}


def save(hosts):
    os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
    tmp = CONFIG + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"hosts": hosts}, f, indent=2)
        f.write("\n")
    os.replace(tmp, CONFIG)


def find(name):
    """A registered machine by its name, Tailscale host name or alias: (name, entry) or None."""
    n = name.lower()
    for key, h in load().items():
        if n in {key.lower(), h.get("host", "").lower(), *[a.lower() for a in h.get("aliases", [])]}:
            return key, h
    return None


def unregistered_tailnet_host(name):
    t = tailnet()
    return bool(t and name.lower() in t["peers"] and not find(name))


def ssh_options(h):
    opts = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", f"HostKeyAlias={h['host']}",
            "-o", "StrictHostKeyChecking=accept-new", "-o", "ControlMaster=auto",
            "-o", f"ControlPath={HOME}/.ssh/agent-comms-%C", "-o", "ControlPersist=300"]
    t = tailnet()
    if t and h["host"].lower() in t["peers"]:
        # Tailscale's own dialer: it also works when tailscaled runs in userspace mode (no tailscale0
        # device, as beside another VPN) and when MagicDNS names do not resolve on this machine.
        opts += ["-o", "ProxyCommand=tailscale nc %h %p"]
    return opts


def ssh(h, command, stdin=None, timeout=None, stream=False):
    """Run a shell command on the machine. Returns (exit code, stdout, stderr); with stream, the
    output goes straight to this process's own and both strings are empty."""
    cmd = ["ssh", *ssh_options(h), f"{h['user']}@{h['host']}", PRELUDE + command]
    os.makedirs(os.path.join(HOME, ".ssh"), exist_ok=True)
    try:
        if stream:
            return subprocess.run(cmd, input=stdin, text=True, timeout=timeout).returncode, "", ""
        r = subprocess.run(cmd, input=stdin, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"no answer from {h['host']} within {timeout}s"


def script(h, name, args, stdin=None, timeout=60):
    """Run one of this skill's scripts on the machine."""
    return ssh(h, 'python3 -I "$AC"/' + name + " " + shlex.join(args), stdin=stdin, timeout=timeout)


def need(name):
    found = find(name)
    if not found:
        hint = " It is on the tailnet; register it with `remote.py add`." if unregistered_tailnet_host(name) else ""
        sys.exit(f"remote.py: no machine named '{name}'.{hint} Known: {', '.join(load()) or 'none'}")
    return found


def peers(names=None, quota=False, recent=0):
    """Sessions on the other machines: (peers each tagged with 'host', {host: error})."""
    hosts = load()
    chosen = [need(n) for n in names] if names else list(hosts.items())
    args = ["--json"] + (["--quota"] if quota else []) + (["--recent", str(recent)] if recent else [])

    def one(item):
        key, h = item
        code, out, err = script(h, "list_peers.py", args, timeout=45)
        try:
            return key, json.loads(out), None
        except Exception:
            return key, None, (err.strip().splitlines() or [f"exit {code}"])[-1]

    found, errors, quotas = [], {}, {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for key, data, err in pool.map(one, chosen):
            if err:
                errors[key] = err
                continue
            for p in data.get("peers", []):
                p["host"] = key
                found.append(p)
            if data.get("quotas"):
                quotas[key] = data["quotas"]
    return found, errors, quotas


def cmd_hosts(args):
    hosts = load()
    t = tailnet() or {"peers": {}}
    rows = []

    def one(item):
        key, h = item
        start = time.time()
        code, out, err = ssh(h, 'echo "$AC"', timeout=25)
        return {"name": key, "host": h["host"], "user": h["user"], "aliases": h.get("aliases", []),
                "tailnet_online": t["peers"].get(h["host"].lower()),
                "reachable": code == 0, "skill_installed": code == 0 and bool(out.strip()),
                "seconds": round(time.time() - start, 1),
                "error": None if code == 0 else (err.strip().splitlines() or [f"exit {code}"])[-1]}

    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(one, hosts.items()))
    if "--json" in args:
        print(json.dumps({"self": self_name(), "hosts": rows}, indent=2))
        return
    print(f"this machine: {self_name()}")
    if not rows:
        print("No other machines registered. Add one: remote.py add <name> <user>@<tailscale host>")
    for r in rows:
        state = "ok" if r["reachable"] and r["skill_installed"] else (
            "reachable, agent-comms skill missing" if r["reachable"] else f"NO ANSWER ({r['error']})")
        also = f" (also: {', '.join(r['aliases'])})" if r["aliases"] else ""
        print(f"{r['name']:<12} {r['user']}@{r['host']:<24} {state}  {r['seconds']}s{also}")


def cmd_add(args):
    one_way = "--one-way" in args
    pos = [a for a in args if not a.startswith("--")]
    if len(pos) < 2 or "@" not in pos[1]:
        sys.exit("Usage: remote.py add <name> <user>@<tailscale host> [alias...] [--one-way]")
    name, (user, host), aliases = pos[0], pos[1].split("@", 1), pos[2:]
    if is_self(host):
        sys.exit("remote.py: that is this machine")
    h = {"host": host, "user": user, "aliases": aliases}
    code, out, err = ssh(h, 'echo "$AC"', timeout=30)
    if code != 0:
        sys.exit(f"remote.py: cannot reach {user}@{host} over SSH ({err.strip().splitlines()[-1] if err.strip() else code}). "
                 "Check that it is online on the tailnet, sshd runs there, and this machine's key is in its "
                 "~/.ssh/authorized_keys. Nothing was saved.")
    hosts = load()
    hosts[name] = h
    save(hosts)
    print(f"added {name}: {user}@{host}")
    if not out.strip():
        print("warning: the agent-comms skill is not installed there, so mail and peer listing will not work yet")
        return
    if one_way:
        return
    # Replies come back by the same route, so the other machine needs this one in its registry.
    me = self_name()
    code, out, err = script(h, "remote.py", ["add", me, f"{getpass.getuser()}@{me}", "--one-way"], timeout=60)
    print(f"on {name}: " + ((out or err).strip().splitlines() or ["no output"])[-1])
    if code != 0:
        print(f"warning: {name} cannot reach this machine yet, so agents there cannot write back. "
              f"Fix SSH from {name} to {getpass.getuser()}@{me}, then run this again.")


def cmd_remove(args):
    hosts = load()
    found = find(args[0]) if args else None
    if not found:
        sys.exit("remote.py: no such machine")
    del hosts[found[0]]
    save(hosts)
    print(f"removed {found[0]}")


def cmd_peers(args):
    names = [a for a in args if not a.startswith("--")]
    found, errors, quotas = peers(names, quota="--quota" in args)
    if "--json" in args:
        print(json.dumps({"peers": found, "errors": errors, "quotas": quotas}, indent=2))
        return
    import list_peers
    list_peers.print_table(found)
    for host, q in quotas.items():
        print(f"\n=== QUOTA REMAINING on {host} ===")
        list_peers.print_quotas(q)
    for host, err in errors.items():
        print(f"{host}: no answer ({err})", file=sys.stderr)


def cmd_run(args):
    if len(args) < 2:
        sys.exit("Usage: remote.py run <host> <command...>")
    _, h = need(args[0])
    command = " ".join(a for a in args[1:] if a != "--")
    sys.exit(ssh(h, command, stream=True)[0])


def copy(args, to_remote):
    if len(args) != 3:
        sys.exit("Usage: remote.py push <host> <local> <remote>  |  remote.py pull <host> <remote> <local>")
    _, h = need(args[0])
    there = f"{h['user']}@{h['host']}:"
    src, dst = (args[1], there + args[2]) if to_remote else (there + args[1], args[2])
    sys.exit(subprocess.run(["scp", "-q", *ssh_options(h), src, dst]).returncode)


def cmd_lane(args):
    orca = "--orca" in args
    pos = [a for a in args if a != "--orca"]
    if len(pos) != 7:
        sys.exit("Usage: remote.py lane <host> [--orca] <vendor> <model> <effort> <root> <lane> <local brief.md>")
    name, vendor, model, effort, root, lane, brief = pos
    key, h = need(name)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import mail
    lead = mail.detect_sender()
    lead_addr = f"{lead['harness']}:{lead['id']}@{self_name()}"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    there = f".agent-mailbox/.remote-briefs/{mail.sanitize_box(lane)}-{stamp}"
    code, _, err = ssh(h, f"mkdir -p ~/{there}", timeout=30)
    if code == 0:
        code = subprocess.run(["scp", "-q", *ssh_options(h), brief, f"{h['user']}@{h['host']}:{there}/brief.md"]).returncode
    if code != 0:
        sys.exit(f"remote.py: could not copy the brief to {key} ({err.strip()})")
    extra = (f"Your lead is {lead_addr}, an agent on another machine ({self_name()}). It cannot see your files, "
             f"so put what it needs into your messages. Report to it with: python3 $AC/mail.py send "
             f"{lead_addr} \"<text>\" --deliver. It writes to you at {lane}@{key}, which lands in the "
             f"mailbox you already check.")
    # Started detached so the lane outlives this SSH call; the first line of the log is its run folder.
    start = (f'B="$HOME/{there}"; cd {shlex.quote(root)} || exit 2; '
             f'EXTRA={shlex.quote(extra)}; EXTRA="${{EXTRA//\\$AC/$AC}}"; '
             f'setsid nohup bash "$AC"/run_lane.sh {"--orca " if orca else ""}'
             f'{shlex.join([vendor, model, effort, root, lane])} "$B/brief.md" "$EXTRA" '
             f'> "$B/lane.log" 2>&1 < /dev/null & '
             f'for i in $(seq 1 40); do [ -s "$B/lane.log" ] && break; sleep 0.25; done; '
             f'echo "log: $B/lane.log"; head -1 "$B/lane.log"')
    code, out, err = ssh(h, start, timeout=60)
    lines = out.strip().splitlines()
    print(out.strip() or err.strip())
    if code == 0 and len(lines) >= 2:
        log, run = lines[0][5:], lines[1]
        if orca:
            print(f"watch: remote.py run {key} 'tail -n +2 -f {log}'")
        else:
            print(f"watch: remote.py run {key} 'python3 -I $AC/watch_lane.py {run} {lane}'")
        print(f"write to it: mail.py send {lane}@{key} \"<text>\"")
    sys.exit(code)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return
    sub, rest = sys.argv[1], sys.argv[2:]
    if sub == "hosts":
        cmd_hosts(rest)
    elif sub == "add":
        cmd_add(rest)
    elif sub == "remove":
        cmd_remove(rest)
    elif sub == "self":
        print(self_name())
    elif sub == "peers":
        cmd_peers(rest)
    elif sub == "run":
        cmd_run(rest)
    elif sub == "push":
        copy(rest, True)
    elif sub == "pull":
        copy(rest, False)
    elif sub == "lane":
        cmd_lane(rest)
    else:
        sys.exit(f"Unknown subcommand: {sub}")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
