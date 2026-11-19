---
"denny-skills": patch
---

`agent-comms`, `agent-lanes`, `desktop-control`: work with Orca (the agent IDE) and across the user's machines. Orca: `list_peers.py` shows each session's Orca state, `mail.py send --orca` types a mail into a peer's Orca terminal at no model cost, `run_lane.sh --orca` starts a lane as a visible Orca tab and watches it (`orca_env.py`, `orca_lane.py`), and question boxes in an Orca terminal are answered through the Orca CLI without the mouse. Other machines: new `remote.py` runs the same scripts on another machine through SSH carried by Tailscale (it dials with `tailscale nc`, so it works with userspace Tailscale beside another VPN), `mail.py send <peer>@<host>` reaches any agent there with the usual delivery flags, `list_peers.py --hosts` lists sessions on every registered machine, `remote.py lane` starts a lane there that reports back to its lead, and `remote.py run`, `push` and `pull` cover commands, screenshots and files.
