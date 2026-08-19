## What it does

`cmdb-sync` is a design reference for building a sync from an external inventory or CMDB into a target CMDB, product-agnostic. It covers persisting identity instead of a target-system key, the sync-rule and reference-resolution shapes, relocation and reconciliation handling, resumable long-running syncs, and asset key and hierarchy design.

The defining constraint: a target-system object key is scoped to one site, not a portable identity, so a sync that persists a captured key instead of resolving it at read time will work until the first migration or second environment, then break silently.

## When to reach for it

Type `/cmdb-sync`, or the agent reaches for it automatically when the task fits.

| Situation | Reach for |
|---|---|
| Designing a sync engine or connector from an external source into a CMDB | `cmdb-sync` |
| Debugging duplicate records, dropped human edits, or a resync gone wrong | `cmdb-sync` |
| Deciding how a long-running sync survives a platform time limit | `cmdb-sync` (its resumability file) |
| The source is specifically Device42 | [device42](../engineering/device42.md) for the discovery and DOQL side |
| The sync's own writes need transactional guarantees | [acid-transactions](../engineering/acid-transactions.md) |

## Persist identity, not key

The rule the skill leads with: store the source system's own primary key or a content hash for anything you reference across runs, and resolve it to the current target key at read time. A captured target key baked into stored state stops being valid the moment the rule runs against a different site, or the target system migrates, and a backup taken before the fix stays wrong forever.

Two sibling files carry the rest: [RESUMABILITY.md](../../skills/engineering/cmdb-sync/RESUMABILITY.md) for paging, wall-clock budgets, run locking, and why at-least-once delivery makes dedupe and loop detection launch requirements; [ASSET-KEYS-AND-SEEDING.md](../../skills/engineering/cmdb-sync/ASSET-KEYS-AND-SEEDING.md) for canonical key design, hierarchy placement, and seeder script conventions.

## Common questions

**Why does a relocation show up as a duplicate in my run history?**

Because most target systems reject changing an object's type in place, so a move has to be delete-and-recreate. If that count isn't tracked separately from `created`, it reads as a duplicate-creation bug. Give relocation its own count.

**My resync deleted data a human entered by hand.**

That's what a naive delete-and-recreate resync does: it destroys exactly the data that took the most effort to collect. Match by identity first, then explicitly carry the human-filled fields over onto the refreshed record, rather than replacing the record wholesale.

**A scheduled sync rule stopped running after one bad run, and nobody noticed for a week.**

Likely cause: a run that wrote nothing and failed every row still stamped the last-run timestamp. Treat a wrote-nothing run the same as a stopped run, no stamp, so a transient failure retries on the next tick instead of parking the rule for a full period.

**Why are there duplicate tickets from my sync's automation rule?**

At-least-once delivery is the platform norm, not exactly-once. It's harmless for a plain upsert but not for anything that creates a ticket or triggers an action. Dedupe keys and loop detection need to be designed in before the feature ships, not added after the first incident.

## It's working if

- Every stored reference resolves through a source-system identity, never a captured target-system key.
- A relocation, a reconciled human edit, and a stopped run each show up as their own distinct outcome in the run history, not folded into `created`/`updated`/`failed`.
- A long-running sync persists its offset and re-enqueues under the same job key well before the platform's kill deadline, not at it.
- Anything that creates a ticket or triggers a downstream action carries a dedupe key and has loop detection, not just idempotent upserts.

## Where it fits

`cmdb-sync` is a **reach-for-it-anytime standalone** for the sync-design problem itself, independent of which source or target CMDB is involved. [device42](../engineering/device42.md) is the natural source-side neighbour when Device42 is the external inventory. [acid-transactions](../engineering/acid-transactions.md) covers the sync's own write guarantees once data lands in a relational store. For the whole map, [ask-denny](../engineering/ask-denny.md).
