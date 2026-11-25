# Database and storage

Server database first, then on-device storage. Transaction rules (isolation, locking, ledgers, idempotency storage) are in `acid-transactions`; call the Skill tool with it for any write path that moves a balance or spans services.

## Server database

1. **Ids made where the record is born.** UUIDv7 is time-ordered (good for B-tree indexes) and can be generated offline on a device, so a record keeps one id end to end.
2. **Store instants in UTC; convert only for display and business-day rules.** Use a time library with a clear instant versus zoned-time split. Keep the device-reported time and the server-received time as two columns when clients can be offline.
3. **Append-only where history matters.** An event or ledger table gets `INSERT, SELECT` grants only for the app role, plus a trigger that raises on `UPDATE` or `DELETE`. Corrections are new rows.
4. **Projections update in the same transaction as the event**, or are rebuildable from the log. A projection you cannot rebuild is a second source of truth.
5. **Migrations run as a separate role, before the new version takes traffic.** The app role cannot alter schema. Run migrations as a one-off job, not on app start across many replicas.
6. **Check queries at build time where the stack allows it** (compile-time checked SQL with an offline cache in CI, or generated typed queries).
7. **Size the pool on purpose.** Set max and min connections, acquire timeout, max lifetime and idle timeout explicitly; library defaults are often undocumented. Total connections are replicas times pool max; keep that under the server limit with headroom.
8. **Know what a transaction-mode pooler breaks.** Session features (advisory locks, `LISTEN/NOTIFY`, session `SET`, some prepared statement modes) do not survive transaction pooling. At modest scale, connect directly with the app's own pool.
9. **Tokens as database passwords expire.** If the database accepts short-lived identity tokens, the server checks them only at connect time: refresh the token in the background, feed it to new connections, and keep pool max lifetime below the token lifetime.

## On-device storage

1. **One encrypted database per signed-in profile**, owned by one layer (the data layer, or a shared core). Other layers call it; they never open the file.
2. **Random database key, wrapped by a hardware-backed key.** Generate 256 random bits, encrypt them with a platform keystore key (StrongBox or Secure Enclave when present), store only the wrapped blob. Do not require user authentication on that wrapping key if background sync must open the database; protect the app with its own session timeout instead.
3. **Attachments are files with per-file keys recorded in the database**, not blobs in the database.
4. **Non-secret preferences in a preferences store; secrets never there.**
5. **Wipe on account change.** On a shared device, when the signed-in user changes, the previous user's local data goes.

## Traps

- Room for two encrypted SQLite builds in one app (one from the platform library, one inside a native core). Pick one owner.
- `PAGE_SIZE`-style assumptions in native storage code on devices with larger memory pages (see `rust-mobile-core` for Android 16 KB pages).
- Using a pooler and then wondering why advisory locks "randomly" release.
- Floats for money or quantities. Use integers in minor units or a decimal type.
- Ordering events by `device_time`. Order by server commit sequence.

## Checklist

- [ ] Ids are created at the source and stable end to end.
- [ ] Time is stored as UTC instants; device and server times kept separately where relevant.
- [ ] History tables are append-only by grant and trigger.
- [ ] Migrations run under their own role before traffic shifts.
- [ ] Pool settings are explicit and total connections fit the server limit.
- [ ] Device database is encrypted with a wrapped random key and one owning layer.
- [ ] Local data is wiped on user change on shared devices.
