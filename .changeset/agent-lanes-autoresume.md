---
"denny-skills": patch
---

`agent-comms`: add `scripts/autoresume.py`, a watcher outside any agent session that resumes Claude lanes cut off by a usage limit once the limit resets (`show`, `once`, `watch`, `service install|status|remove`, `selftest`), and `scripts/run_lane_unit.sh`, which runs a lane as its own systemd user unit so systemd-oomd cannot kill it together with the editor session. `run_lane.sh` now records `add-dirs.txt` in the run folder. `agent-lanes`: new section "Lanes that keep going without the lead".
