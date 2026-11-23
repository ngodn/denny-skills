---
"denny-skills": patch
---

`agent-lanes`: add "Leading for hours" (three wake sources and re-arming them, reporting on change, looking at every result before passing it on, approvals that name the invariant, lanes that end their turn when they only wait, freezing background work while the user's game runs) and the rule to queue shared tools on a lock instead of a poll. `agent-comms`: add `mailwake.sh` (wake a cleanly stopped Claude lane when mail arrives, `NOTICE` mail does not wake), `leadwatch.sh` (one event stream for the lead: unit ended, new result files, watched process, low disk, heartbeat) and `resource_lock.sh` (run a command under a named machine-wide lock so editor, cook and GPU jobs from different lanes take turns).
