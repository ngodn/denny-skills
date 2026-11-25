---
name: offline-first-sync
description: Design reference for apps whose users write data while offline and sync later. Use when the user is designing or reviewing a device-side write queue or outbox, a push/pull sync protocol, idempotent replay of offline transactions, conflict rules for offline edits, clock skew between devices and server, a sync status UI, or tests for offline, reconnect, and replay behaviour; or is choosing between a sync engine and a custom command log.
---

# Offline-first sync

The device keeps a **working copy** of the data it needs and a **command log** of what the user did. Sync is two independent streams: push the log, pull the server's changes. The server is authoritative; the device never loses a user action, and a conflict becomes an **exception** someone resolves, never an overwrite.

Read this whole file before designing. Then read [PROTOCOL.md](PROTOCOL.md) when building the push/pull endpoints and server tables, and [TESTING.md](TESTING.md) before calling any of it done. For the server-side transaction rules (idempotency storage, outbox, isolation), call the Skill tool with `acid-transactions`.

## Command log, not row sync

Sync engines that replicate rows (last write wins, row-level CRDTs) are a fine fit for notes, to-do lists and preferences. They are the wrong fit when each write is a business action that needs an audit trail, approvals, and per-action conflict rules (stock moves, inspections, custody transfers, signed forms). For those, every user action is a **transaction record** created on the device and replayed on the server through the same rules. Managed engines can still be a reference: the split of "upload queue to our own API" and "download by checkpoint" is the part worth borrowing.

## The transaction envelope

Every state-changing action becomes one record with these fields:

| Field | Why |
|---|---|
| `txn_id` | UUIDv7 made on the device. The idempotency key end to end: device, server, and any downstream system. |
| `device_id`, `device_seq` | Monotonic per device, never reused. The server applies a device's records in this order and can see gaps. |
| `kind`, `payload`, `schema_version` | The business action and its data, versioned so old app builds keep syncing after a server upgrade. |
| `actor`, `co_signers` | Who did it and who approved it, each with how they authenticated. |
| `occurred_at` | Device wall clock at the moment of the action. |
| `elapsed_since_sync` | Monotonic time since the last server time sync (elapsed realtime, not wall clock), so the server can estimate skew and detect clock changes. |
| `prev_hash`, `hash`, `sig` | Hash chain over this device's records, signed with a hardware-backed device key. Proves the device's history was not edited or reordered. |
| `local_status` | `draft`, `queued`, `sending`, `accepted`, `rejected_needs_action`. Device-only. |

Drafts are not transactions. A draft autosaves on every field change and becomes a transaction only on submit, when it is validated, signed, chained and queued in one local database transaction.

## Validation on the device

The device runs the **same rule code** as the server (a shared module or crate) before queueing. Split every rule into one of two kinds:

- **Hard stop**: decidable from local data (required field missing, item not in this location, quantity over a known limit). Blocks the user.
- **Deferred check**: needs facts only the server has (another device moved the same item an hour ago). Marked "pending server check" and allowed. If it fails on the server, it comes back as an exception.

This resolves the usual requirement tension between "enforce the rules" and "never block offline work".

## Conflict rules per operation kind

Decide per `kind`, in the shared rule module, so device and server classify the same way. Never one generic rule for the app.

| Situation | Typical rule |
|---|---|
| Same `txn_id` arrives twice | Duplicate: no effect, return the original result. |
| Change commutes with what happened since (two scans of the same item at the same place, adding to a set) | Accept and merge. |
| Change was based on a state that a later-accepted transaction already changed (move an item that has since moved elsewhere) | Exception. |
| Two devices claim the same unique thing (same seal, same slot) | First accepted wins; second is an exception. |
| Gap in one device's `device_seq` | Hold later records from that device until the gap fills or an admin releases them. |
| Device time implausible (in the future beyond tolerance, or before its last sync) | Accept, flag for review. Offline work is never thrown away for a bad clock. |

## Exceptions, not overwrites

A rejected transaction is never deleted and never silently overwritten by server state. It goes to an **exception workbench** (on the device and in an admin portal) showing what the user did, what the server had, and why it conflicts. An authorized person resolves it, and the resolution is itself a new transaction that references the original. The audit trail keeps both.

## Push and pull, briefly

- **Push**: queued records in `device_seq` order, in batches; the server answers per record (accepted, duplicate, exception with reason code). The device marks a record done only on a durable server answer.
- **Pull**: changes since a cursor, scoped to what this device may see. Server state wins for the snapshot; the device then **rebases** its still-queued records on top and re-runs validation, so the UI shows the user's pending work on the latest server state.
- **Transport**: a platform background scheduler (WorkManager on Android, BGTaskScheduler on iOS) runs sync on reconnect, as unique work, with exponential backoff and jitter.

Details, server schema and skew estimation: [PROTOCOL.md](PROTOCOL.md).

## Sync status UX

- Every screen that shows synced data shows sync state: pending count, last successful sync time, last error. Use icon plus text, not colour alone.
- Each record shows its own state (draft, waiting, sending, synced, needs action).
- Exceptions are a first-class list with a badge, not a toast that disappears.
- The user can trigger a sync manually and see it run.
- Signing out with unsynced records warns and requires a deliberate choice.

## Local store rules

- Encrypted local database per signed-in profile, opened by one owning layer. Key wrapped by a hardware-backed keystore key that does not require user auth, so background sync can open it.
- Queue, sequence counter, sync cursor and hash chain head live in the same database and change in the same local transaction as the record.
- Survives app kill, reboot and app upgrade; migrations never drop queued records.

## Review checklist

- [ ] Every state-changing action is a transaction record with the envelope above.
- [ ] Device and server run the same rule code; rules are split into hard stops and deferred checks.
- [ ] Conflict rules are written per operation kind.
- [ ] Conflicts become exceptions with a workbench; resolution is a new linked transaction.
- [ ] Push is ordered per device, idempotent on `txn_id`, answered per record.
- [ ] Pull is cursor-based and scoped; queued records are rebased and re-validated after pull.
- [ ] Device time and server time are both stored; ordering uses server commit order.
- [ ] Sync state is visible everywhere it matters.
- [ ] The tests in [TESTING.md](TESTING.md) exist and pass.
