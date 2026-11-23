---
"denny-skills": patch
---

`ue-modding`: `ANIMATION.md` gains retargeting between rigs with different joint counts (idle joints from end-to-end chain mapping, sharing a bend along the chain with the chain end held, shoulder rhythm, wrist roll and twist bones, pose-or-mesh test), the order of work for a hand on another body (rest or grip, palm, fingers, per-point limits, deformer and clearance) and natural face curve strength. New `LIVE-TEST-WINDOWS.md` for unattended scripted game tests: offline rehearsal against the real mod code, readback after every action, preconditions so a test can fail, restore that keeps grown caches, captures that show the subject, install by hash with a rollback set. `TOOLCHAIN.md` gains finding the cook route that reproduces released bytes before adding to a shipped mesh, and bridges that drop array arguments silently.
