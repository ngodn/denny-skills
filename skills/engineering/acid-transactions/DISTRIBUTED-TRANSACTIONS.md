# Distributed transactions

What replaces ACID when one business operation spans several databases, shards, or services: sagas, the transactional outbox, idempotency, and why not two-phase commit.

## Frame the problem first

Each service (or shard) owns its own database. One operation, "transfer 1,000 from Alice to Bob", touches several of them, and you cannot wrap them in one `BEGIN ... COMMIT`. Two sub-problems fall out:

1. **The dual-write problem.** A service must atomically (a) update its database and (b) publish an event to the next service. Database plus message broker is not one atomic unit. Solved by the **outbox pattern**.
2. **The coordination problem.** Sequence the multi-service workflow and undo on failure. Solved by the **saga pattern**.

**Idempotency** is the glue that makes every retry safe in both.

## Saga

A saga is a sequence of **local transactions**. Each commits atomically in one service's database, then triggers the next via an event or command. There is no global rollback: if step N fails, run **compensating transactions** for steps N-1 down to 1 to *semantically* undo them.

A saga keeps A, C, and D per local transaction and **gives up isolation across services**. That is the key insight, and it is why the anomalies and countermeasures below exist.

Vocabulary:

- **Compensatable** step: can be undone by an opposite-effect transaction (`reserve` and `release`, `debit` and `credit`).
- **Pivot** step: the point of no return. Once it commits the saga must go forward; earlier compensations no longer apply. In a transfer, posting the irreversible ledger entry or crediting the recipient is the pivot.
- **Retryable** step: after the pivot, idempotent, guaranteed to eventually succeed through retries (notify, update a read model).

Orchestration vs choreography:

| | Choreography | Orchestration |
|---|---|---|
| Coordination | No central brain; services emit events, peers react | A central **orchestrator** sends commands and tracks a state machine |
| Visibility | Hard ("who reacts to what?") | Easy; one place shows the saga's state, good for audit |
| Single point of failure | None | The orchestrator (make it highly available and persistent) |
| Best for | Simple flows, few steps | Complex flows, conditional logic, money |

Recommendation: **orchestrate the money path** (one auditable "where is transfer T-123 right now" state machine with explicit compensation control) and **choreograph the side effects** (emit `TransferCompleted`, let notifications and analytics consume it).

Failure scenarios:

- **Failure before the pivot** (credit fails after debit): orchestrator moves to `COMPENSATING`, runs the refund, net zero.
- **Failure after the pivot** (ledger posted, notification fails): do not compensate; you cannot un-pay. The step is retryable, so retry with backoff.
- **The compensation itself fails** (wallet service down during refund): the dangerous case. Make compensations idempotent and retryable (persist them as commands, retry with backoff), dead-letter plus alerting after N retries, and keep an out-of-band **reconciliation** process as the backstop. Money systems always have one.

Lost isolation causes lost updates, dirty reads (reading a value about to be compensated), and non-repeatable reads across the saga. Countermeasures:

- **Semantic lock.** An application-level flag (mark the debit row `PENDING`) released by the completing or compensating transaction. The most important one for balances.
- **Commutative updates.** Design debit and credit so order does not matter.
- **Pessimistic view.** Reorder steps so risky reads happen in retryable, post-pivot steps.
- **Reread value.** Re-read and verify unchanged before writing (a version check).

## Transactional outbox

`db.commit()` then `broker.publish()`: a crash between them leaves the database updated and the event lost (the saga stalls). Publish then commit: an event for a change that never happened. There is no atomicity across a database and a broker.

Fix: in **one local transaction**, write the business change and an `outbox` row.

```sql
BEGIN;
  UPDATE wallets SET balance = balance - 1000 WHERE id = 'alice';
  INSERT INTO outbox (id, aggregate_id, type, payload, created_at)
    VALUES (:uuid, 'T-123', 'WalletDebited', '{...}', now());
COMMIT;
```

A relay publishes outbox rows to the broker and marks them sent. Two ways to drain it: a **polling publisher** (`SELECT ... WHERE published = false`; simple, adds latency and load) or **change data capture** (a tool such as Debezium tails the database's transaction log, WAL or binlog, and streams outbox inserts in near real time; preferred).

The outbox gives **at-least-once**, not exactly-once: the relay can crash after publishing and before marking sent, then republish. **Consumers must be idempotent.**

## Idempotency

Idempotency means calling the same operation N times has the same effect as once. Networks fail *after* the server did the work and *before* the client saw the reply, so clients retry; without idempotency a retry is a double charge.

The client generates a unique key per logical operation and sends it on every attempt, including retries. The server deduplicates on it and returns the stored response. **The unique constraint is the load-bearing detail.**

```sql
CREATE TABLE idempotency_keys (
  key                 TEXT PRIMARY KEY,   -- the unique constraint is the enforcement
  request_fingerprint TEXT,               -- hash(method + path + body)
  status              TEXT,               -- IN_PROGRESS | COMPLETED
  response_code       INT,
  response_body       JSONB,
  created_at          TIMESTAMPTZ DEFAULT now()
);
```

Flow:

1. `INSERT ... ON CONFLICT (key) DO NOTHING`.
2. New key: mark `IN_PROGRESS`, run the business logic, save the response, set `COMPLETED`, return.
3. Conflict and `COMPLETED`: return the stored response, do not re-execute. Conflict and `IN_PROGRESS`: a duplicate is mid-flight; return 409 so the client backs off.
4. Same key, different body: reject as key misuse.

Save the response **in the same transaction as the business effect**; otherwise a crash between "charged" and "key saved" lets a retry double-charge.

The honest framing: true exactly-once delivery is impossible over an unreliable network. You build at-least-once delivery plus idempotent processing, which is effectively-once processing. Retry hygiene: exponential backoff with jitter; retry only on indeterminate outcomes (timeouts, 5xx, 429), never on deterministic 4xx.

## Why not two-phase commit

2PC: a coordinator runs *prepare* (every participant locks and votes) then *commit* or *abort*. It gives true distributed atomicity, but:

- **It blocks on coordinator failure.** If the coordinator dies after prepare, participants hold their locks indefinitely, unable to safely commit or abort. A system-wide stall.
- **Locks are held across the whole global transaction**, network round-trips included, which kills throughput.
- **All participants must be up at once**, and many components (brokers, REST/gRPC services, many stores) do not speak XA at all.

| | 2PC | Saga |
|---|---|---|
| Atomicity | True distributed ACID | Per local transaction; eventual via compensation |
| Isolation | Yes (locks) | No; needs countermeasures |
| Locks | Held across the global transaction | Per local transaction only |
| Failure mode | Blocks if the coordinator dies | Non-blocking; forward or backward recovery |
| Fit for services | Rare | Default |

2PC is acceptable only with few participants, a reliable network, all XA-capable resources, one datacenter, and atomicity valued over availability.

## Partition consistency by invariant

Do not pick strong or eventual consistency globally:

- **Hard invariants** (no negative balance, debits equal credits) get **strong consistency inside a single aggregate and a single database**, where ACID applies: row lock, guarded UPDATE, or optimistic version.
- **Cross-service workflow state** gets **eventual consistency via the saga**, made safe with idempotency, semantic locks, and an authoritative append-only ledger as the source of truth.
- The append-only ledger makes inconsistency **detectable and reconcilable**, which is what makes eventual consistency across services tolerable at all.

Strong is correct but less available and slower (CP); eventual is available and fast but transiently stale (AP). Money: strong for the balance constraint, eventual for orchestration, reconciliation as the safety net.
