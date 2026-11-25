# Offline-first and sync

The short version for deciding whether and how much offline support an app needs. The full design (transaction envelope, push/pull protocol, conflict rules, exception workbench, testing) lives in the `offline-first-sync` skill: call the Skill tool with `offline-first-sync` once the answer below is "queued or lazy writes".

## Decide first

An offline-first app can do its core work with no network: it shows local data immediately, keeps working through dead zones, and syncs when it can. At minimum it must read offline. Writing offline is the expensive part, so choose a write strategy per kind of data, not one for the whole app.

| Strategy | What happens | Fits |
|---|---|---|
| Online-only | Write goes to the server; local store is updated only on success. UI blocks or disables the action when offline. | Anything that must be decided in real time against shared state (payments against a live balance, booking the last seat). |
| Queued | Write is queued and sent later; losing it is tolerable. | Analytics, logs, non-critical telemetry. |
| Lazy (local first, then sync) | Write lands in the local store first and is queued for the server. Conflicts are possible and must be handled. | Business records users must never lose: field inspections, stock moves, signed forms. |

Source for the three strategies: the Android offline-first guide, https://developer.android.com/topic/architecture/data-layer/offline-first . The guide names "last write wins" as the common mobile conflict rule; for business records that need an audit trail, use a command log with per-operation conflict rules instead (see `offline-first-sync`).

## Rules

1. **The local store is the only thing the UI reads.** Network results go into the local store first; the UI observes the store. This keeps one code path for online and offline.
2. **Hard stops decided locally, everything else deferred.** A rule the device can decide from its own data blocks the user. A rule that needs server-only facts (another device's recent write) is marked "pending server check" and comes back as an exception, never as a silent failure.
3. **Never overwrite or delete on conflict.** A rejected offline write becomes an exception someone resolves, and the resolution is a new record that references the original.
4. **Sync state is always visible.** Pending count, last successful sync, last error, on every screen that matters.
5. **Device time is evidence, not truth.** Record the device's clock and the server's receive time; order by server commit order.

## Traps

- Picking a sync engine before writing down the conflict rule for each kind of write. Row-level CRDTs and last-write-wins are wrong for anything auditable.
- A background job that cannot open the local database because its key requires the user to unlock. Wrap the database key with a device key that does not need user auth, and protect the app with its own session instead.
- Retrying a rejected write forever. Distinguish "network failed" (retry with backoff) from "server said no" (stop, raise an exception).
- Draining the queue in parallel. Per-device order matters; drain sequentially from a persisted queue.

## Checklist

- [ ] Each kind of write has a named strategy (online-only, queued, lazy).
- [ ] UI reads only from the local store; network results land there first.
- [ ] Offline hard stops and deferred checks are listed per operation.
- [ ] Conflicts become exceptions, never overwrites.
- [ ] Sync status is shown and the queue survives app kill and reboot.
- [ ] If any write is lazy, the `offline-first-sync` design has been applied.
