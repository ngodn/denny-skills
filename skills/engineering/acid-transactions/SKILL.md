---
name: acid-transactions
description: Reference and discipline for transactional integrity. Use when the user is designing or reviewing code that writes to a database inside a transaction, moves money, inventory, or any balance, picks an isolation level or a lock, debugs a race condition, lost update, or double-spend, chooses between ACID and eventually consistent stores, or coordinates a change across services (sagas, outbox, idempotency).
---

# ACID Transactions

A **transaction** is a group of reads and writes the database treats as one indivisible unit of work. **ACID** is the four promises it makes about that unit. Use this vocabulary and these rules wherever code touches a transaction, and treat every anomaly named here as a bug you have to rule out, not a curiosity.

## The four promises

| Letter | Property | Promise in one line | Who enforces it |
|---|---|---|---|
| **A** | **Atomicity** | All steps happen, or none do. | The engine (undo log, rollback). |
| **C** | **Consistency** | Every committed transaction moves the DB from one valid state to another. | A partnership: the engine enforces the constraints **you** declared. |
| **I** | **Isolation** | Concurrent transactions do not see each other's half-done work; the result is *as if* they ran one at a time. | The engine (locks or MVCC), at the isolation level you chose. |
| **D** | **Durability** | Once committed, it survives crashes, power loss, and reboots. | The engine (write-ahead log, fsync, replication). |

**Anchor: the bank transfer.** Move 100 from Alice to Bob: `Alice -= 100`, `Bob += 100`.
- Atomicity: both writes or neither. Never "Alice debited, Bob not credited".
- Consistency: the invariant "total money in the system is unchanged" holds after commit.
- Isolation: a concurrent reader never sees 100 missing from the system.
- Durability: after "done", a crash one millisecond later must not lose it.

## Vocabulary

Use these terms exactly.

**Transaction** - the unit of work between `BEGIN` and `COMMIT`/`ROLLBACK`. _Avoid_: "operation", "request" (a request may run several transactions).

**Invariant** - a rule that must hold after every commit (`balance >= 0`, debits equal credits). Consistency means the invariants you declared hold; the engine cannot know an invariant you never encoded.

**Anomaly** - a specific way concurrent transactions produce a result no serial order could. Name the one you mean: **dirty read**, **non-repeatable read**, **phantom read**, **lost update**, **write skew**. _Avoid_: "race condition" on its own; it does not say which anomaly.

**Isolation level** - the engine's dial between throughput and which anomalies it prevents: Read Uncommitted, Read Committed, Repeatable Read, Serializable.

**MVCC** - multi-version concurrency control: writers create a new row version, readers see a consistent snapshot as of their start and are never blocked by writers. How Postgres, Oracle and most modern engines give non-blocking reads.

**WAL** - write-ahead log: changes are appended to a sequential log and fsync'd **before** commit is acknowledged. Undo info gives atomicity, redo info gives durability, ordering supports isolation. If you can explain WAL you can explain why a single-node relational database is ACID.

**Idempotency** - the same logical operation applied N times has the effect of once. A separate property from atomicity: atomicity makes one attempt all-or-nothing, idempotency makes a *retry* safe.

**ACID consistency vs CAP consistency** - two different words. ACID-C: declared invariants hold. CAP-C: linearizability, every read sees the latest committed write system-wide. "Strong consistency" for a ledger almost always means the CAP sense. Say which one you mean.

## Rules

Apply these when writing or reviewing transactional code.

1. **Keep the transaction to the write set.** Open it late, commit fast. Never do network I/O (call another service, a payment provider, send an email) while a transaction or a row lock is open. Lock hold time is your throughput ceiling and your deadlock risk.

2. **Never rely on the isolation level alone for a money move.** Pair it with an explicit lock or a single atomic statement. For a single-row balance change the **atomic guarded UPDATE** is usually the best answer:
   ```sql
   UPDATE wallet SET balance = balance - :amt
    WHERE id = :id AND balance >= :amt;   -- guard in the same statement
   -- rows_affected: 1 = success, 0 = insufficient funds
   ```
   One statement kills both lost update and double-spend on that row. Reach for `SELECT ... FOR UPDATE` when business logic must read-decide before writing; reach for optimistic version/CAS when the read-decide gap is long or crosses services; reach for `SERIALIZABLE` plus a retry loop for a multi-row invariant you cannot fold into one statement. Details and the decision table: [ISOLATION-AND-LOCKING.md](ISOLATION-AND-LOCKING.md).

3. **Know your engine's default and what it really means.** Postgres defaults to Read Committed; MySQL/InnoDB to Repeatable Read. Postgres Repeatable Read is snapshot isolation: it blocks phantoms but still allows **write skew**; only Serializable closes it. Serializable and Repeatable Read can abort your transaction on conflict, so a **retry loop is mandatory** there.

4. **Encode the invariants in the schema.** `NOT NULL`, `CHECK (balance >= 0)`, `UNIQUE`, foreign keys, and a double-entry ledger where money is involved. Consistency the engine cannot see is consistency you do not have. `balance` is a derived cache; the ledger is the source of truth; move both in the same transaction.

5. **Make retries safe with an idempotency key backed by a unique constraint**, and save the response in the same transaction as the business effect. A timeout is ambiguous (never arrived, done but reply lost, still running); the client retries with the same key and gets the stored result. Never claim exactly-once delivery: at-least-once delivery plus idempotent processing is what you build.

6. **Lock in a deterministic order.** For a transfer A to B, lock `min(id)` first. Deadlocks are detected and one side is aborted, so a retry loop is needed here too.

7. **Durability is a knob, not a boolean.** `fsync` on commit survives a crash on that node; surviving disk or machine loss needs synchronous replication to a quorum before ack. Turning fsync off (`synchronous_commit = off` and friends) trades the last fraction of a second of commits for speed. Say so explicitly if you do it.

8. **Across service or shard boundaries there is no native ACID.** Do not reach for two-phase commit; use a **saga** with compensating transactions, a **transactional outbox** for the dual-write problem, and idempotent consumers. A saga gives up cross-service isolation, so it needs countermeasures (semantic locks, commutative updates). Details: [DISTRIBUTED-TRANSACTIONS.md](DISTRIBUTED-TRANSACTIONS.md).

9. **Partition consistency by invariant, not globally.** Hard invariants (no negative balance, money conserved) get strong consistency inside one aggregate and one database. Cross-service workflow state can be eventually consistent through the saga, with an append-only ledger and reconciliation as the backstop that makes inconsistency detectable.

## Designing a system with a mutable balance

Before drawing tables, state the invariant out loud: "money is conserved, every debit has an equal opposite credit, balance never goes negative." Use that sentence as the test for every candidate design, not just the schema. A design that lets the invariant break under some interleaving is the wrong design, not an edge case to patch later.

**Ledger over column, with the schema.** Rule 4 already says the ledger is the source of truth and the balance column a derived cache; this is the shape that holds up in practice:

```
accounts(account_id, owner_id, owner_type, account_kind, currency,
         cached_balance, version, status)
transactions(txn_id, txn_type, idempotency_key UNIQUE, status, amount)
ledger_entries(entry_id, txn_id, account_id, direction, amount CHECK (amount > 0),
                created_at)
```

Every transaction posts at least two ledger entries that sum to zero. That makes leakage mechanically detectable (sum the entries; they should net to zero) and gives an audit trail for free. `ledger_entries` carries no `updated_at`: a correction is a new, compensating transaction, never a mutation of a posted entry.

**Expiring value as FIFO lots.** For a balance that expires (points, credits, cashback), don't model it as one number with an expiry date. Give each grant its own row with its own expiry clock. A spend consumes the soonest-expiring active lot first. An expiry sweeper posts a reversal transaction for the lot rather than silently deleting it, so the ledger stays balanced and the expiry itself is auditable.

**Multi-source deduction.** When a spend can draw from more than one funding source in priority order (a wallet, then a gift card, then a credit line), model each source as a strategy object exposing `available()`, `deduct()`, `refund()`, and iterate by a priority that's data, not a branch in the deduction loop, so adding a source needs no change to the loop. Check total availability across every source before mutating any of them: an all-or-nothing check up front avoids partially deducting one source only to fail on a later one.

## Choosing a store

| Need | Reach for | Why |
|---|---|---|
| A system of record where a stale read is unrecoverable (money, inventory, seats) | Single-primary SQL (PostgreSQL, MySQL/InnoDB, Aurora) | Full ACID, well understood; one primary handles thousands of writes per second with short transactions, pooling, and read replicas for non-critical reads. |
| The same, but writes exceed one primary, multi-region active-active, or data residency | Distributed SQL (Spanner, CockroachDB, TiDB, YugabyteDB) | ACID across nodes via consensus; you pay per-transaction latency instead of app-level sharding. Check the default isolation (some default to snapshot isolation). |
| Adjacent data where temporary staleness is harmless (caches, feeds, counters, sessions, idempotency keys, analytics) | NoSQL / eventually consistent stores | Availability and scale dominate; their transactions exist but have narrow cross-partition scope, so keep them off the ledger. |

**ACID vs BASE.** BASE (Basically Available, Soft state, Eventually consistent) is the deliberate opposite trade: stay up under a partition and converge later. Under CAP you keep consistency or availability during a partition, not both. Declining a payment is recoverable; letting two people spend the same money is not, so a ledger picks CP. Justify a store with the consistency requirement and the numbers, never with taste.

**Read-your-writes.** Never read a just-written balance from a lagging replica on the confirm path; read from the primary there.

## Review checklist

When reviewing a diff that touches transactions, look for these in order:

- Network I/O or slow work inside `BEGIN ... COMMIT` or under a row lock.
- A read-then-write on a balance, counter, or stock level with no lock, no guard, and no version check (lost update waiting to happen).
- A "check then act" against a shared limit across rows at Read Committed or Repeatable Read (write skew).
- Retry logic missing where the isolation level or lock can abort (serialization failure, deadlock victim).
- A retried request path with no idempotency key, or a key stored in a different transaction from the effect.
- An invariant enforced only in application code that a `CHECK` or `UNIQUE` could hold.
- A publish-after-commit (or commit-after-publish) with no outbox.
- Cross-shard or cross-service work wrapped in what looks like one transaction.
