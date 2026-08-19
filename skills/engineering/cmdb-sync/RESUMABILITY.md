# Resumability, locking, and delivery guarantees

## Paging with a wall-clock budget

Page the source. Track a wall-clock budget inside the run and stop well before the platform's kill deadline, not at it: leave real headroom. On hitting the budget, persist the offset and the running totals, then re-enqueue a continuation carrying the same job key.

Report a stopped run with its own status, distinct from success, partial, and failed, so the UI never shows a stopped run as done. A run that stops mid-page is not a failure and is not a success; showing either misleads whoever is watching the run history.

## Run locking

Hold a single run-state row (not a cache) with the running flag, the job key, the start time, and progress. Add a stale-lock check: a lock left behind by a hard-killed run should be treated as idle after some bound, so a phantom "running" state does not block every future run forever.

When a second job hits an active, non-stale lock, re-enqueue the same job with a short delay rather than throwing. Throwing burns a finite retry budget and can drop the job outright; a delayed re-enqueue is a soft, effectively indefinite retry that costs nothing if the first run finishes on time.

## Don't stamp last-run on a run that wrote nothing

A run that finishes but writes nothing and fails every row must not stamp the last-run timestamp. Stamping it anyway means a transient failure, a missing scope, an unreachable source, parks a scheduled rule for a full period instead of retrying on the next tick. Treat a wrote-nothing-failed-everything run the same as a stopped run: no stamp, resume point intact.

## At-least-once delivery is the norm, plan for it before shipping

Expect at-least-once delivery from the underlying platform, not exactly-once. For a plain upsert this is harmless: a duplicate upsert is a no-op. For anything that creates a ticket or triggers a downstream action, at-least-once delivery means duplicate tickets are possible, and an action that changes the condition that triggered it can refire itself into a loop.

Design a dedupe key for anything that creates an artifact, and design loop detection for any chained action, before shipping the feature. Retrofitting either after the fact usually means retrofitting it after a duplicate-ticket or infinite-loop incident, not before one.
