---
"denny-skills": patch
---

Add `agent-comms` (misc): how Claude sessions, Codex exec lanes and sessions, and Antigravity reach each other, with tested delivery facts (`codex queue` never reaches a running exec turn but lands on the next resume; a headless `claude -p` can relay any agent's message into a Claude session), a tab-title session watcher, `run_lane.sh` and `watch_lane.py`, one lane launcher and watcher for Claude, Codex and Antigravity with a chosen model and effort (low, medium, high), and shared-resource ownership rules. `agent-lanes` now points to it for messaging.
