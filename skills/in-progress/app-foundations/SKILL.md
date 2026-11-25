---
name: app-foundations
description: Review checklist and rules for the foundations of a mobile or web app and its backend. Use when the user is designing, building, or reviewing an app's architecture, frontend state, API or backend logic, database and local storage, auth and permissions, row-level security, rate limiting, caching, logging, error tracking or audit logs, or availability, backups and recovery; or asks what a new app needs before it ships.
---

# App foundations

The parts every serious app needs, whatever the stack: a UI that reads from local state, an API that is safe to retry, a database that holds the invariants, auth checked on the server, limits, caches with a clear owner, telemetry that is not the audit trail, and a plan for when a node dies. Each topic below has its own file with the rules that matter, the traps that cost real time, and a review checklist.

## How to use this

1. Name the topics the task touches. A new app touches all of them; a change usually touches two or three.
2. Read the file for each topic touched, and apply its rules to the design or the diff.
3. Finish on the checklist at the end of each file read. The work is done when every item on those checklists is either satisfied or written down as a known gap with a reason.

| Topic | File | Read it when |
|---|---|---|
| Offline-first and sync | [OFFLINE-AND-SYNC.md](OFFLINE-AND-SYNC.md) | The app must work with no network, or writes are queued on the device. |
| Frontend and UI architecture | [FRONTEND.md](FRONTEND.md) | Screens, state, lists, forms, design system, accessibility, hardware input. |
| API design and backend logic | [API-AND-BACKEND.md](API-AND-BACKEND.md) | Endpoints, domain rules, crate or module layout, outbound integrations. |
| Database and storage | [DATA-AND-STORAGE.md](DATA-AND-STORAGE.md) | Schema, migrations, ids, time, pools, on-device storage, files. |
| Auth and permissions | [AUTH-AND-PERMISSIONS.md](AUTH-AND-PERMISSIONS.md) | Sign-in, token validation, roles, shared devices, second-person approval. |
| Security and row-level security | [SECURITY-AND-RLS.md](SECURITY-AND-RLS.md) | Secrets, multi-tenant data, RLS policies, supply chain, hardening. |
| Rate limiting and backpressure | [RATE-LIMITING.md](RATE-LIMITING.md) | Protecting your API, or calling someone else's that has limits. |
| Caching | [CACHING.md](CACHING.md) | Adding any cache: HTTP, in-process, shared, or on-device. |
| Error tracking, logging, audit | [OBSERVABILITY-AND-AUDIT.md](OBSERVABILITY-AND-AUDIT.md) | Logs, traces, metrics, crash reports, audit trails. |
| Availability and recovery | [AVAILABILITY-AND-RECOVERY.md](AVAILABILITY-AND-RECOVERY.md) | Deploys, probes, shutdown, overload, backups, disaster recovery. |

## Related skills

- Anything that writes inside a database transaction, moves a balance, or coordinates writes across services: call the Skill tool with `acid-transactions`. These files link to it instead of repeating it.
- Designing the device-side queue, sync protocol and conflict handling in depth: call the Skill tool with `offline-first-sync`.
- Sharing one Rust core between a server and Android or iOS apps: call the Skill tool with `rust-mobile-core`.

## Rules that cut across every topic

1. **One rule set, one home.** A business rule lives in one module (or crate) that the server, and the device if it validates offline, both call. Rules copied into a second language drift.
2. **The server decides.** Client checks are for fast feedback. Every rule that matters is checked again on the server, on every write, including writes replayed from an offline queue.
3. **Every write is safe to retry.** Networks time out after the work is done. A client-made idempotency key and a unique constraint turn a retry into a no-op.
4. **Invariants live in the schema.** If a `CHECK`, `UNIQUE`, foreign key or grant can hold it, it does not live only in application code.
5. **Bounded everything.** Queues, request bodies, batch sizes, timeouts, pool waits and retries all have a stated limit. Unbounded is how a slow dependency becomes an outage.
6. **Telemetry is lossy, audit is not.** Logs and traces may drop a batch. The audit record is written in the same transaction as the change it describes.
7. **Pin what you verified, date what you pinned.** Versions, limits and vendor behaviour change. Write the date next to any number you copy from a vendor page, and re-check before a release.
