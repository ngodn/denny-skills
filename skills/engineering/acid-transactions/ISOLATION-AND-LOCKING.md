# Isolation and locking

The detail behind the "I" in ACID: which anomalies exist, which isolation level stops which, and the three tools that make concurrent writes to the same row behave as if they ran one at a time.

## The mental model

Every concurrency bug on a balance, counter, or stock level is a variant of: *two transactions read the same value, both decide the write is fine, both write.* Two anomalies to name on demand:

- **Lost update.** T1 reads 100, T2 reads 100, T1 writes 100-30=70, T2 writes 100-40=60. T1's deduction vanished.
- **Double-spend / write skew.** Both check `balance >= amount` against a stale read, both pass, both deduct, balance goes negative. The check was a lie.

Everything below is machinery to rule those out.

## The anomalies

| Anomaly | What happens |
|---|---|
| **Dirty read** | You read another transaction's **uncommitted** data; it rolls back and you read data that never existed. |
| **Non-repeatable read** | You read a row twice in one transaction and get different values (someone committed an UPDATE in between). |
| **Phantom read** | You run the same range query twice and get a different set of rows (someone INSERTed or DELETEd matching rows). |
| **Lost update** | Two transactions read the same value, both compute from it, both write; one update silently overwrites the other. |
| **Write skew** | Two transactions each read a shared state, each is individually valid, but their combination violates an invariant no serial order would allow. |

## Isolation levels

The SQL standard:

| Level | Dirty read | Non-repeatable read | Phantom read |
|---|---|---|---|
| Read Uncommitted | Possible | Possible | Possible |
| Read Committed | Prevented | Possible | Possible |
| Repeatable Read | Prevented | Prevented | Possible (per the standard) |
| Serializable | Prevented | Prevented | Prevented |

Engine reality, which is what trips people up:

| | Dirty read | Non-repeatable read | Phantom read | Write skew |
|---|---|---|---|---|
| PostgreSQL Read Committed (default) | No | Yes | Yes | Yes |
| PostgreSQL Repeatable Read (= snapshot isolation) | No | No | No | **Yes** |
| PostgreSQL Serializable (SSI) | No | No | No | No |

- Postgres defaults to **Read Committed**; MySQL/InnoDB to **Repeatable Read**; Oracle's "Serializable" is snapshot isolation. Always state which engine you mean.
- Postgres Repeatable Read is stronger than the standard (no phantoms) but still allows write skew. Only Serializable, implemented as Serializable Snapshot Isolation with predicate locks, closes it.
- At Repeatable Read and Serializable, a conflicting concurrent write aborts your transaction (`could not serialize access ...`). A **retry loop is mandatory**.

Two implementation families sit under every level:

- **Pessimistic / locking.** Shared locks for reads, exclusive for writes, held until commit. Conflicting transactions block and wait. Simple; risks deadlocks and caps throughput by lock hold time.
- **Optimistic / MVCC.** Writers create a new version of the row; readers see a consistent snapshot as of their start and are never blocked by writers. Conflicts surface at commit and the loser aborts and retries.

## Three tools for a contended row

### 1. The atomic guarded UPDATE (often the best answer)

```sql
UPDATE wallet
   SET balance = balance - :amt
 WHERE id = :id AND balance >= :amt;
-- rows_affected: 1 = success, 0 = insufficient funds (clean reject)
```

Why it is safe: a single UPDATE takes the row write-lock for its duration; `balance = balance - :amt` is read-modify-write inside the engine on the locked current value (no app-side stale read, so no lost update); the guard is evaluated against that same locked row (a racing writer sees the already-decremented balance, so no double-spend). One statement, no explicit `BEGIN` or `FOR UPDATE`.

What it does not cover: invariants spanning more than one row (sum across wallets, cross-account limits); idempotency (a retried request runs it twice); the double-entry ledger, which still has to be written in the same transaction.

### 2. Pessimistic: `SELECT ... FOR UPDATE`

Assume conflict is likely. Take an exclusive row lock when you read, hold it until commit; other lockers and writers on that row wait.

```sql
BEGIN;
SELECT balance FROM wallet WHERE id = :id FOR UPDATE;   -- lock held till COMMIT
-- business logic decides
UPDATE wallet SET balance = balance - :amt WHERE id = :id;
INSERT INTO ledger (wallet_id, amount, type) VALUES (:id, -:amt, 'debit');
COMMIT;
```

Because the lock spans read, check, and write, lost update and double-spend are structurally impossible on that row.

Variants: `FOR SHARE` (many readers, blocks writers; pins a row that must not change), `FOR UPDATE NOWAIT` (fail instantly instead of waiting), `FOR UPDATE SKIP LOCKED` (skip locked rows; the pattern for job-queue and claim tables).

Use when: high contention on a known row, short transaction, correctness over throughput, and business logic must run between read and write.

Traps: **deadlocks** (T1 locks A then B, T2 locks B then A; fix by always locking in a deterministic order, ascending id, and retry the aborted victim); **lock hold time is the throughput ceiling** (no network I/O under the lock; lock late, commit fast); does not span shards or regions.

### 3. Optimistic: version column / compare-and-set

Assume conflict is rare. No lock on read; read the value plus a `version`, make the write conditional on the version being unchanged, and retry the whole cycle when zero rows match.

```sql
SELECT balance, version FROM wallet WHERE id = :id;      -- balance=100, version=42
-- app computes new_balance
UPDATE wallet
   SET balance = :new_balance, version = version + 1
 WHERE id = :id AND version = 42;                        -- CAS guard
-- rows_affected = 0 -> someone won the race -> retry from SELECT (bounded, with backoff)
```

Use when: low to moderate contention, read-heavy, long think time between read and write (a user editing a form), or stateless and distributed services where holding physical locks across nodes is costly.

Trap: under high contention retries storm and throughput collapses exactly when you need it. Bound the retries, add backoff, and pair with an idempotency key.

## Decision table

| | High contention (hot account, hot merchant) | Low contention (typical row) |
|---|---|---|
| Conflict probability | High | Low |
| Pick | Pessimistic `FOR UPDATE`, or the atomic guarded UPDATE | Optimistic version/CAS, or the atomic guarded UPDATE |
| Why | Optimistic retries thrash; pessimistic queues writers with one wait | Conflicts are rare so retry cost is near zero; avoids lock contention; works across nodes |

For a single-row balance move prefer the atomic guarded UPDATE: simpler and faster than either. Use `SELECT FOR UPDATE` when you must read-decide with business logic before writing, optimistic CAS when the read-decide gap is long or spans services, and Serializable plus a retry loop for a multi-row invariant you cannot fold into one statement. Never rely on the isolation level alone.

## Hot rows and throughput

Row locks serialize writers regardless of cluster size, so one very hot row is a bottleneck no amount of horizontal scaling fixes. Know several fixes:

- **Connection pooling** in front of the database (PgBouncer in transaction mode for Postgres); the cheapest big win, since server connections are expensive.
- **Read replicas** for non-critical reads (history, dashboards). Never read a just-written balance from a lagging replica on the confirm path; use read-your-writes from the primary there.
- **Vertical first, then shard.** One primary comfortably handles thousands of writes per second with short transactions. Shard by a stable high-cardinality key (`wallet_id` hashed), or move to distributed SQL that auto-shards. Cross-shard transfers become a saga plus outbox, not cross-shard two-phase commit.
- **Balance/counter sharding.** Split the hot row into N sub-rows; each write hits a random one; the true value is `SUM(shards)`.
- **Write coalescing.** Buffer increments and flush an aggregated `+sum` periodically instead of one UPDATE per event.
- **Append-only ledger.** Turn credits into INSERTs (which do not contend on one row) and materialize the balance asynchronously. Removes the hotspot entirely.
