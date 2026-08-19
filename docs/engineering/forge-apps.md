## What it does

`forge-apps` is a reference and discipline for building an Atlassian Forge app that does real work, especially one that reads or writes JSM Assets data. It covers the runtime limits, the continuation pattern for work that outruns those limits, run locking, the retry adapter a flaky platform requires, storage philosophy, a virtual-schema pattern for building a rich data model on top of a small number of real object types, a granular permission layer, custom fields, and the impersonation nuance for web triggers.

The defining constraint the whole skill runs on: async event consumers and scheduled triggers carry no user context at all, and the Assets API has no app-context path around that. Every architectural decision in the skill either follows directly from that fact or is a separate, independently load-bearing gotcha.

## When to reach for it

Type `/forge-apps`, or the agent reaches for it automatically when the task fits.

Reach for it when designing a Forge app's resolver/queue/scheduled-trigger split, the moment an async event or scheduled trigger throws an auth error trying to touch Assets, when a job needs to outrun the 900-second async ceiling, when choosing between Forge's key-value store and an Assets-backed data model, when writing a retry adapter around `requestJira`, when building a custom field or a web trigger, or when a Forge deploy doesn't seem to have changed what users see.

| The situation | Reach for |
|---|---|
| An async consumer or scheduled trigger fails with `401 AUTH_TYPE_UNAVAILABLE` | `forge-apps` |
| A job needs more than 900 seconds of work | `forge-apps`, continuation pattern |
| Deciding where app state should live (KVS vs. a backbone schema) | `forge-apps` |
| Building a permission layer finer than the platform's native roles | `forge-apps`, [PERMISSIONS.md](../../skills/engineering/forge-apps/PERMISSIONS.md) |
| A web trigger needs to act as a specific user | `forge-apps`, [IMPERSONATION.md](../../skills/engineering/forge-apps/IMPERSONATION.md) |
| The Assets-specific limits the app's code has to respect | [jsm-assets](../engineering/jsm-assets.md) |

## The load-bearing fact and its consequences

Async event consumers and scheduled triggers have no user context. Any `asUser()` call from one fails with `401 AUTH_TYPE_UNAVAILABLE`, and separately `asApp()` against Assets scopes is rejected outright: there is no app-context path to the Assets API from Forge at all. This forces every Assets read and write into a user-triggered resolver invocation, forces every user of an Assets-touching app to hold the right licence and a native role on the schema, and rules out an unattended background job as an architecture for any feature that touches Assets. A feature that looks like "sync overnight" has to be restructured as client-driven paging during real user sessions instead.

Three sibling files carry the rest of the depth. [VIRTUAL-SCHEMA.md](../../skills/engineering/forge-apps/VIRTUAL-SCHEMA.md) covers building an app-defined object model on top of a small number of real Assets object types, the cold-start cost on a large backbone, and the value-level encryption pattern for what it stores. [PERMISSIONS.md](../../skills/engineering/forge-apps/PERMISSIONS.md) covers a granular grant model (principal by function by scope, deny-by-default, most-specific-wins) enforced centrally, with read-denied fields stripped server-side and write-denied fields preserved rather than overwritten. [IMPERSONATION.md](../../skills/engineering/forge-apps/IMPERSONATION.md) covers the single most valuable non-obvious fact in the skill: a user-context call inside a web trigger handler does work if the app already has the target account id, contrary to how the platform's own documentation reads on a first pass.

## Common questions

**The docs say web triggers have no user context. Why does `asUser()` work in one anyway?**

Because the app already had the target account id from an independent source before making the call, and the manifest declares impersonation. The documentation's blanket statement describes the case where the trigger has no way to know who the user is; it doesn't describe the case where the app already knows and only needs to act as them. See [IMPERSONATION.md](../../skills/engineering/forge-apps/IMPERSONATION.md) for the full precondition checklist.

**My retry logic checks the response status code, but a call is still failing without ever hitting the retry branch. Why?**

The `requestJira` fetch wrapper can throw instead of returning a response object when the platform's proxy drops a call before it reaches the target service. A status-code-based retry branch never sees a throw. Wrap the call in try/catch and retry a throw the same way as a transient 5xx.

**I redeployed to production and nothing changed for users. What's wrong?**

Check which environment the install is actually bound to. An installed app can be bound to the development environment even on a real, production site, which makes a `-e production` deploy a no-op relative to what users see until the install itself is pointed at production.

**Why did a scheduled trigger's continuation job just vanish instead of running again?**

A consumer cannot re-enqueue itself; that push is rejected by the platform. Continuations need to be driven by a separate scheduled heartbeat trigger, not by the consumer trying to chain into itself.

## It's working if

- Nothing in the codebase calls `asUser()` or the Assets API from an async event consumer or a scheduled trigger.
- A long-running job persists `{jobKey, offset, runningTotals}` and re-enqueues a continuation well before the 900-second kill deadline, not right up against it.
- Every `requestJira` call site is wrapped so a thrown platform error retries the same way a 5xx would.
- Application state that matters lives in the backbone schema; the key-value store holds only caches that can be rebuilt if lost.
- A permission check runs from every resolver touching protected data, not just from the frontend hiding denied buttons.
- The permission-precedence test matrix is exhaustive, not a handful of spot checks.

## Where it fits

`forge-apps` is a **reach-for-it-anytime standalone** for anyone building or reviewing a Forge app, most load-bearing on apps that touch JSM Assets. Its closest neighbour is [jsm-assets](../engineering/jsm-assets.md), which this skill assumes: every Assets-specific limit lives there, while this skill covers the Forge runtime around it. [acid-transactions](../engineering/acid-transactions.md) is relevant wherever the app's write path needs a version-counter compare-and-set or an idempotent upsert. For the whole map, ask [ask-denny](../engineering/ask-denny.md).
