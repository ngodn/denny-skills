"""Stream a lane started by run_lane.sh as Monitor events, for any vendor (claude, codex, agy):
its messages, failed commands, a 10-minute heartbeat with the current step, a stall warning after
15 quiet minutes, and the exit. Usage: watch_lane.py <run dir> [label] [--from-end]"""
import json, os, re, sys, time
args = [a for a in sys.argv[1:] if not a.startswith('--')]
run = args[0]; label = (args[1] if len(args) > 1 else os.path.basename(run).rsplit('-', 2)[0]).upper()
ev, pidf, vf = (os.path.join(run, f) for f in ('events.jsonl', 'pid.txt', 'vendor.txt'))
while not all(os.path.exists(f) for f in (ev, pidf, vf)):
    time.sleep(1)
pid, vendor = int(open(pidf).read()), open(vf).read().strip()
pos = os.path.getsize(ev) if '--from-end' in sys.argv else 0
last_event = last_beat = time.time(); current = ''
READS = ('cat ', 'sed ', 'ls ', 'rg ', 'grep', 'find', 'head', 'tail', 'jq ', 'wc ')
agy_text = {}  # agy streams a reply in pieces per step

def alive():
    try: os.kill(pid, 0); return True
    except OSError: return False

def say(s): print(f'{label} ' + s[:400].replace('\n', ' '), flush=True)

def failed(cmd, code):
    # A search or listing that matched nothing exits non-zero; that is noise, not a failure.
    if code in (0, None) or any(w in cmd.split('-lc', 1)[-1][:12] for w in READS):
        return
    say(f'command failed (exit {code}): {cmd[-160:]}')

def codex(e):
    global current
    it = e.get('item', {}); t = it.get('type')
    if t == 'command_execution':
        current = it.get('command', '')[-160:]
        if e.get('type') == 'item.completed': failed(current, it.get('exit_code'))
    elif t == 'agent_message' and e.get('type') == 'item.completed':
        say('says: ' + it.get('text', ''))
    elif e.get('type') in ('turn.failed', 'error'):
        say('ERROR: ' + json.dumps(e)[:300])

def claude(e):
    global current
    t = e.get('type')
    if t == 'assistant':
        for c in e.get('message', {}).get('content', []):
            if c.get('type') == 'text' and c.get('text', '').strip(): say('says: ' + c['text'])
            elif c.get('type') == 'tool_use':
                i = c.get('input', {}); current = str(i.get('command') or json.dumps(i))[:160]
    elif t == 'user':
        for c in e.get('message', {}).get('content', []) or []:
            if isinstance(c, dict) and c.get('type') == 'tool_result' and c.get('is_error'):
                failed(current, 'error')
    elif t == 'result' and e.get('is_error'):
        say('ERROR: ' + str(e.get('result', ''))[:300])

def agy(e):
    global current
    if e.get('event') == 'result':
        r = e.get('result', {})
        if r.get('status') != 'SUCCESS': say('ERROR: ' + json.dumps(r)[:300])
        return
    s = e.get('step_update') or {}
    if s.get('step_type') == 'tool':
        info = s.get('tool_info', {}); params = info.get('parameters', {})
        current = str(params.get('CommandLine') or json.dumps(params))[:160]
        m = re.match(r'Command exited with code (\d+)', info.get('output', '') or '')
        if s.get('state') == 'DONE' and m: failed(current, int(m.group(1)))
    elif s.get('step_type') == 'agent_response':
        i = s.get('step_index'); agy_text[i] = agy_text.get(i, '') + (s.get('text_delta') or '')
        if s.get('state') == 'DONE' and agy_text.get(i, '').strip(): say('says: ' + agy_text.pop(i))

handle = {'codex': codex, 'claude': claude, 'agy': agy}[vendor]
while True:
    with open(ev) as f:
        f.seek(pos); lines = f.readlines(); pos = f.tell()
    for l in lines:
        try: e = json.loads(l)
        except Exception: continue
        last_event = time.time(); handle(e)
    now = time.time()
    if now - last_beat > 600: say(f'heartbeat: running, current step: {current}'); last_beat = now
    if now - last_event > 900: say('STALL: no events for 15 min'); last_event = now
    if not alive():
        time.sleep(2); xf = os.path.join(run, 'exit.txt')
        say(f"finished, exit {open(xf).read().strip() if os.path.exists(xf) else '?'}"); break
    time.sleep(5)
