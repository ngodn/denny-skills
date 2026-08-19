---
name: cmdb-sync
description: Design and review a sync from an external inventory or CMDB into a target CMDB. Use when the user designs a sync engine or connector between an external inventory source and a CMDB, debugs duplicate or dropped records after a resync, decides how to persist references or foreign keys across systems, designs a taxonomy or classification engine driven by source data, or needs a resumable long-running sync job with locking and retry semantics.
---

# CMDB Sync

Design reference for a sync that runs against a CMDB from an external inventory source, product-agnostic. The constraint that shapes everything else: a target-system object key is a property of one site, not a stable identity, so persisting a captured key instead of resolving it at read time is the single most common way this class of system breaks.

## Persist by identity, not by key

Store the source system's own primary key, or a content hash, as the join key for any reference, relationship, or graph root you persist. Resolve that identity to the current target-system key at read time, every time. Never bake a captured key into stored state: it stops being valid the moment the same rule runs against a different site (sandbox vs production), or the target system migrates.

This is worth getting right the first time. It was broken and re-fixed three separate times, in a cross-object reference feature, an impact-analysis feature, and a dashboard's graph-root list, before the rule got written down. Backups taken before the fix are not retroactively repairable: a captured key baked into an old backup stays wrong forever.

## Sync rule shape

A rule is data, not code:

```json
{
  "source": { "query": "<source-system query>", "key": "<row identity field>" },
  "target": { "objectType": "<target type>", "keyAttribute": "<upsert key>" },
  "fields": [
    { "source": "<column>", "target": "<attribute>", "transform": "text" }
  ]
}
```

Upsert on `keyAttribute` so re-runs update in place instead of duplicating. Keep the transform vocabulary small and named (`text`, `integer`, `boolean`, `datetime`, `date`); add a case only when a real field needs it.

## Reference resolution

When a synced row references another synced object type (a compute instance referencing its cloud account, for example), build a reference index, source-id to target-key, once per run by scanning the target type.

Cache the in-flight promise of that scan, not its resolved value. If you cache only the resolved value, every concurrent writer that starts before the first scan finishes misses the cache and kicks off its own full scan at the same time, which can burst-load the source or target system hard enough to trigger its own failures. Caching the promise means the first caller builds the index and every concurrent caller awaits that same one.

## References matched by free-text name

Some reference fields only give you a free-text tag or name, not a stable foreign key (a cloud "Environment" tag, for example). Run the field's transform first, then normalise (trim, lowercase, strip spaces), then look the normalised value up in an explicit map to the canonical target value.

A value absent from the map deliberately resolves to no reference, and does not count as "unresolved." That is correct behaviour for genuinely junk or inconsistent source tags: they stay unlinked with their raw text preserved, rather than being fuzzy-guessed into a category they might not belong to.

## Relocation is delete-and-recreate, and gets its own count

An object's correct position in the target tree can change between runs (a grouping field gets filled in later, a classifier reassigns a category). Many target systems reject changing an object's type in place. Model a move as delete-in-old-location plus recreate-in-new-location, and report it as its own `relocated` count, separate from `created` and `updated`. Folded into `created`, it reads as a duplicate-creation bug in the run history.

Track a separate count, too, for human-entered values that had no matching attribute in the destination on a relocation, so a manual edit that would otherwise vanish silently at least leaves a trace.

## Classify and route

Compute a short classification token per row inside the source query, using a `CASE WHEN` expression able to combine several source columns (device type, subtype, hardware model, vendor) that a single-field regex could not express alone. Map that token to a taxonomy path in code, in a separate module.

Splitting the two keeps the query reviewable on its own and the token-to-path mapping diffable on its own. Ship a large generated ruleset versioned with the code, not stored as config: config storage has a size limit a few hundred rules can blow past, and a ruleset in code is reviewable in a diff the way stored config is not. Order extension-based rules (`.jar`, `.whl`) before generic name-based rules, so a language-ecosystem package lands in the right bucket instead of falling through to a generic default.

## An idempotent type-tree builder

Walk a path of type names, creating any missing level along the way, and memoise `(parent, name)` to `id` lookups so repeated calls sharing a path prefix do not repeat API calls. Match an existing type by the `(parent, name)` tuple, not by id alone, so the whole builder is naturally idempotent: safe to re-run against a partially built tree.

## Reconciliation stance

Manually entered data is human-owned. A naive resync must never delete or overwrite it. Delete-and-recreate destroys exactly the data that took the most effort to collect. Match first (by canonical identity, with fallback to name, hostname, serial, or UUID), then explicitly carry the human-filled fields over onto the refreshed record.

## Build order

Storage schema and the editing UI first, execution engine second. Validate the rule shape against a real editing experience before anything executes against it. Building both at once means discovering the rule shape is wrong only after the engine that consumes it already exists.

## Long-running, resumable syncs

See [RESUMABILITY.md](RESUMABILITY.md) for paging and wall-clock budgets, run locking, and why at-least-once delivery means dedupe and loop detection are launch requirements, not follow-ups, for anything that creates a ticket or triggers an action.

## Seeding, backfill, and asset key design

See [ASSET-KEYS-AND-SEEDING.md](ASSET-KEYS-AND-SEEDING.md) for canonical asset key design, hierarchy placement, and seeder script conventions.
