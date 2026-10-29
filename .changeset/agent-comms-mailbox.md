---
"denny-skills": patch
---

`agent-comms`: a shared file mailbox (`mail.py`) that Claude Code, Codex and Antigravity can all send to, read and watch without spending Claude Code tokens; an agy delivery bridge and stream-json inbox daemon (`agy_bridge.py`); a peer and quota lister across all three harnesses (`list_peers.py`); `run_lane.sh` takes every `agy models` id with short names `agy-opus`, `agy-sonnet` and `gpt-oss`; the skill explains harness versus model and gives a routing table. Built and tested by an Antigravity session.
