---
name: forge-apps
description: Reference and discipline for building an Atlassian Forge app that does real work, especially one touching JSM Assets. Use when the user is designing a Forge app's resolver/queue/scheduled-trigger split, hitting an auth error from an async event or scheduled trigger, building a long-running or bulk job on Forge, choosing between Forge storage and an Assets-backed data model, designing a retry adapter for `requestJira`, building a custom field or a web trigger, or debugging why a Forge deploy didn't change what users see.
---

# Forge Apps

Building a Forge app that does real work means designing around a small set of hard platform limits rather than discovering them one at a time in production. The one fact that changes the whole architecture: **async events and scheduled triggers carry no user context.** Everything else here either follows from that or is a separate, equally load-bearing gotcha.

## Runtime limits

| Context | Timeout | Payload |
|---|---|---|
| Sync resolver invocation | 25s | 500 KB request, 5 MB response |
| Async queue consumer | 900s (15 min) | none |
| Scheduled trigger | 900s (15 min) | none |

## The load-bearing fact: no user context outside a resolver

Any `asUser()` call, or any Assets-API call at all, made from an async event consumer or a scheduled trigger fails:

```
401 AUTH_TYPE_UNAVAILABLE
```

Separately, `asApp()` against `cmdb-*` scopes is rejected. The Assets API is user-context only from Forge, full stop, no app-context path around it. Treat this as a platform gap you design around, not a bug you can fix locally.

Consequences that follow directly:

- **All Assets input and output must happen inside a user-triggered resolver invocation.** A background job cannot touch the Assets API at all, which forces client-driven paging for large loads: the browser session pumps paged resolver calls, not a queue consumer running unattended.
- **Every user of an Assets-touching app needs the right licence and a native role** on whatever schema the app uses, because every Assets call runs as that user.
- Design the resolver/queue split around this early. A feature that looks like "sync N objects overnight" is not buildable as a scheduled trigger if it touches Assets; it has to be client-driven or restructured as append-only writes gathered during real user sessions.

## Long-running work: page, budget, persist, continue

For work that would exceed 900s even from an async consumer:

1. Page the source in a bounded batch size, tuned against real timing (batch size is a real lever: too small burns time on overhead per page, too large risks not finishing a page inside the budget).
2. Hold a wall-clock budget well inside the platform kill deadline, not right up against it. Example: stop at 8 minutes under a 900s ceiling, leaving real headroom for the last write and the re-enqueue call.
3. On hitting the budget, persist `{jobKey, offset, runningTotals}` and stop.
4. Re-enqueue a continuation carrying the same `jobKey` via the async queue.

A consumer cannot re-enqueue itself; that push is rejected by the platform. Drive continuations with a scheduled heartbeat trigger at the finest interval Forge offers (5 minutes), which does double duty: enqueue cadence-due work and drive any paused job's next continuation.

A run that finishes having written nothing and failed every row should not be marked as a completed run. Treat it like a paused run instead: no completion stamp, resume point intact. Stamping it as done on a transient failure (a missing scope, an unreachable source) silently parks a recurring job until its next scheduled cadence instead of retrying promptly.

## Run locking

Hold a single lock record (in the backbone schema, not Forge KVS, per the storage discipline below) with a stale-lock check: a lock left behind by a hard-killed invocation should be treated as idle after a bounded age, so the UI never shows a phantom "running" state forever and the next scheduled run can take over.

When a second run hits an active, non-stale lock, do not throw. Throwing burns a finite retry budget and can drop the job outright. Re-enqueue the same job with a delay instead, for a soft, effectively indefinite retry that waits its turn.

## Queue rejection mid-run

`Queue.push()` can be rejected mid-run, for instance when the app version changes under a running job (the publish target is version-scoped). Treat a rejected push as a hard stop: close the run out as partial at the row it reached, rather than letting the job die silently with no record of how far it got.

## The retry adapter

The `requestJira` fetch wrapper can **throw** instead of returning a response object (a platform proxy dropping the call before it reaches the target service). A status-code-based retry branch never sees a throw, so it never retries this failure class. Wrap every call in try/catch and retry a throw exactly like a transient 5xx; this is safe when writes are upserts, since a retried write just repeats the same effect.

Standard shape: bounded retry count, exponential backoff with jitter, retry on 5xx and on the thrown-platform-error case, never retry a 4xx. Track request, retry, rate-limit, and wait counters per run so a run report can show whether the platform is throttling (429s) or just slow.

On the scripting side (a Python seeder or backfill script calling the same APIs outside Forge), the transient-fault set is wider than the obvious network-error class. Large responses drop mid-read and surface as several different exception types, not just a connection error; catch broadly for transient faults rather than narrowly for one exception class, or a mid-read failure aborts the whole run instead of retrying.

## Storage: backbone schema, not the key-value store

Do not use Forge's key-value store for application state that matters. It carries a per-value size cap (240 KiB) and per-tenant isolation quirks that make it a poor system of record.

Store application state instead as objects in a dedicated, hidden JSM Assets schema, using the platform itself as the app's database. This has no comparable size cap: chunk a large payload across several long-text attributes instead of hitting one field's limit. It survives a reinstall or site migration legibly, and stays inspectable and backup-able through the normal Assets UI, unlike an opaque key-value blob.

Keep the key-value store for what it is good at: derived, rebuildable caches only, never a system of record. If losing the KVS entry would lose data rather than just cost a rebuild, it belongs in the backbone schema instead.

## Backbone naming

Give the backbone schema a static, memorable name and key, identical across every install, and locate it at runtime by that name rather than by a stored id. That way a support tool or a fresh install can always find the right schema without carrying install-specific state.

Give secret-bearing config rows inside the backbone deliberately mundane, non-descriptive labels rather than names that announce what they hold. A label like "master key" or "connection settings" is a target; a mundane label is not, for anyone who has ordinary read access to the backbone schema without needing to see its secrets.

The virtual-schema pattern for building an app-defined object model on top of native Assets types, the cold-start problem on a large backbone, and the value-level encryption pattern used to protect what the backbone stores are covered in [VIRTUAL-SCHEMA.md](VIRTUAL-SCHEMA.md).

## Permission layer

A platform offering only coarse native roles needs its own granular permission layer for anything beyond "can see the schema at all." The grant model, precedence rules, and enforcement discipline are covered in [PERMISSIONS.md](PERMISSIONS.md).

## Custom field pattern

Pair the custom field type module with the UI modifications module, bridged only through the same-app events channel; there is no other way for UI modifications to write into a Forge custom field. Form-based request types (built on the platform's forms feature) cannot host an app-defined field at all. Only plain portal request forms can.

## Build and CSP

- Bundle everything; zero external egress by default.
- Use a relative base path in the bundler config so code splitting resolves correctly; an absolute base path breaks chunk loading once the app is installed under a real site path.
- Deduplicate shared dependencies (for example a UI framework) across bundles in the same app to avoid duplicate runtime copies causing runtime errors.
- Inline-style relaxation in the content security policy is sometimes unavoidable for runtime-computed styles (a virtualized table, a positioned popover). Treat it as an explicitly accepted and documented risk, not a silently suppressed warning.
- Never cache tenant data in module scope in resolver code. Forge containers are shared and reused across tenants; module-level state leaks between customers.

## Error envelope

Every resolver returns a uniform `{code, message, retriable}` shape. The frontend maps codes to inline error states by code, never by parsing the message string, which is free to change wording without warning callers.

Use compare-and-set on a version counter for write conflicts: on a mismatch, show a conflict dialog with a reload option rather than silently overwriting the other write. Crypto failures fail closed: a bad key or a corrupt blob marks the object unreadable, never returns partial or garbage plaintext.

## Egress

Forge's outbound egress allowlist is domain-based, not address-based. An app cannot reach a raw IP address even when it knows exactly which one it needs, which breaks direct integration with any internal system whose public domain path is unreliable while its address is directly reachable from elsewhere.

Workaround: run a small authenticated forwarder outside the platform, on a machine that has network access to the target. Keep the target system's credentials only on that machine, never in Forge storage. Make the connection mode (forwarder versus direct) a config value behind one client interface, so switching back to a direct call once the target becomes reachable is a config edit, not a redeploy.

## Impersonation

Web triggers carry no user context by default, but there is a real exception worth knowing before assuming it is impossible. Covered in [IMPERSONATION.md](IMPERSONATION.md), along with the security checklist for an external service calling into a web trigger.

## Testing

- Unit tests for the crypto round trip, the chunking logic, and the query planner.
- An exhaustive table-driven test matrix specifically for permission precedence. This is exactly the kind of logic that silently breaks on refactor, so give it its own matrix rather than folding it into general unit tests.
- Resolver-level integration tests against a real development site, not just mocks.
- A repeatable, seeded performance benchmark, tracked over time so a regression shows up as a trend rather than a surprise.
- A manual test matrix for every UI surface that cannot be meaningfully unit-tested (a create dialog, an issue-view panel, a portal form).

## The deploy trap

An installed app can be bound to the development environment even on a real, production site. In that state, a production deploy is a no-op relative to what users actually see: the install was never pointed at the production environment, so publishing a new production version changes nothing visible. Verify which environment an install is actually bound to before assuming a deploy changed anything live.

Separately, the Forge runtime's clock can lag the wall clock by a meaningful amount. When validating freshly written data, check it against the live data itself, not against a timestamp computed locally; a locally computed "should be recent" check can fail against a genuinely fresh write.
