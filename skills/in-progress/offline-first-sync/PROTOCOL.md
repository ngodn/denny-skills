# Sync protocol and server side

The wire format is defined once (in the shared module) and used by both device and server. Version it from day one: field names, payload schemas and the canonical byte layout for hashing all carry a version.

## Push

`POST /sync/push` with a batch of the device's queued records in `device_seq` order. Limit the batch by count and bytes, and enforce the same limits on the server.

Server, per batch:

1. Validate the caller (token) and that the `device_id` belongs to them or to their tenancy.
2. In one database transaction per batch (keep batches small enough that this is short), for each record in order:
   - `txn_id` already stored: return `duplicate` with the stored outcome.
   - `device_seq` is not the next expected for that device: return `gap` and stop processing this device's later records in the batch.
   - Verify the device hash chain link and signature; a broken chain is an exception, never silently accepted.
   - Re-check co-signatures (verifier valid at `occurred_at`, role allowed, approver is not the requester).
   - Run the shared rules against current server state, including deferred checks. Accept and apply, or store as an exception with a reason code.
   - Store the outcome in the same transaction as the effect.
3. Answer per record: `accepted`, `duplicate`, `gap`, or `exception` with reason code and the current server state needed to show the conflict.

The device advances a record to `accepted` (or `rejected_needs_action`) only on that answer. A timeout means "unknown"; the device resends the same records and gets `duplicate` for anything that already landed.

## Pull

`GET /sync/pull?cursor=...` returns reference data and state changes since the cursor, scoped to what this device's user may see (their sites, roles, tenancy), plus a new cursor.

- The cursor is an opaque server value (a global commit sequence, or a token), never a device timestamp.
- Apply a pull page in one local transaction, then move the cursor.
- After applying, rebase still-queued records on the new state and re-run local validation. A record that now fails a hard stop goes to `rejected_needs_action` locally before it is even sent.
- Large initial loads page through the same endpoint; the device is usable once the first pages it needs are in.
- Revocations (users, verifiers, devices) arrive through pull; the device applies them before validating anything else.

## Server tables (sketch)

```sql
CREATE TABLE event (
  global_seq     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  txn_id         uuid NOT NULL UNIQUE,
  stream_id      uuid NOT NULL,            -- the aggregate (item, order, case)
  stream_version bigint NOT NULL,
  device_id      uuid NOT NULL,
  device_seq     bigint NOT NULL,
  occurred_at    timestamptz NOT NULL,     -- device clock, never used for ordering
  received_at    timestamptz NOT NULL DEFAULT now(),
  skew_estimate  interval,
  actor_id       uuid NOT NULL,
  cosigner_id    uuid,
  kind           text NOT NULL,
  schema_version smallint NOT NULL,
  payload        jsonb NOT NULL,
  prev_hash      bytea NOT NULL,
  hash           bytea NOT NULL,
  UNIQUE (stream_id, stream_version),      -- optimistic concurrency
  UNIQUE (device_id, device_seq),          -- per-device order and idempotency
  CHECK (cosigner_id IS NULL OR cosigner_id <> actor_id)
);
```

- App role: `INSERT, SELECT` only; a trigger raises on `UPDATE` or `DELETE`.
- Exceptions live in their own table referencing the original record; resolutions are new events referencing the exception.
- Projections (current state per item) update in the same transaction as the event append.

## Ordering and gaps

- Within a device: strictly by `device_seq`. A gap holds later records until it fills (the device resends) or an admin releases it with an audited decision.
- Across devices: by server commit order (`global_seq`). Device clocks order nothing.
- Per aggregate: optimistic concurrency on `stream_version`. A unique violation means someone else wrote first; the shared rules decide whether the change commutes or conflicts.

## Clock skew

- On each sync the device sends its current wall clock and its elapsed time since the previous server time sync. The server records the offset per device per session.
- With the offset and each record's `elapsed_since_sync`, the server can estimate when the action really happened, and detect a user changing the device clock (wall clock jump with no matching elapsed time).
- Flag implausible times for review; do not reject. Reports and audit show both `occurred_at` and `received_at`.
- Token expiry and every security time check use server time only.

## Hash chain

- Device chain: `hash = H(prev_hash || canonical_bytes(record))`, signed with the device key. The server verifies each link on push.
- Server chain (optional, for the global log): computed inside the insert transaction over `global_seq` order, taking the chain head with a single-row lock. Fine at moderate write rates; shard the chain per stream if it becomes the bottleneck.
- Canonical bytes: an explicit, versioned, length-prefixed layout defined in the shared module. A general JSON serializer is not canonical. Freeze golden vectors and run them on device and server.
- Checkpoints: periodically sign the server chain head with an HSM-held key and export it outside the database.

## Downstream systems

Accepted events often feed other systems. Write outbox rows in the same transaction as the event, deliver with a relay, keep per-aggregate order, and send the `txn_id` downstream as the idempotency token. Details: call the Skill tool with `acid-transactions`.
