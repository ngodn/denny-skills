## What it does

`acid-transactions` fixes the words and the rules for code that writes inside a database transaction: the four promises (**atomicity**, **consistency**, **isolation**, **durability**), the five anomalies you name on demand (dirty read, non-repeatable read, phantom, lost update, write skew), the isolation levels and what each engine really does at them, and the three tools for a contended row (the atomic guarded UPDATE, `SELECT ... FOR UPDATE`, optimistic version/CAS). Two supporting files carry the depth: one on isolation and locking, one on what replaces ACID across services (saga, outbox, idempotency, why not two-phase commit).

It is a reference and a review checklist, not a process. It runs no loop and produces no artifact; it gives the agent the discipline to apply while it designs, writes, or reviews the code in front of it. Its one hard line is that an isolation level on its own is never enough for a money move: pair it with an explicit lock or a single atomic statement.

## When to reach for it

Type `/acid-transactions`, or the agent reaches for it automatically when the task fits.

| The situation | Reach for |
|---|---|
| Writing or reviewing code that moves money, stock, seats, or any balance | `acid-transactions` |
| Picking an isolation level, a lock, or a retry strategy | `acid-transactions` |
| Debugging a "sometimes the count is wrong" bug: lost update, double-spend, write skew | `acid-transactions`, then [diagnosing-bugs](../engineering/diagnosing-bugs.md) to run the loop |
| One operation spans services or shards and someone said "distributed transaction" | `acid-transactions` (its distributed file) |
| Choosing between a relational store and an eventually consistent one for a system of record | `acid-transactions` |
| The shape of the module around the transaction (where the seam goes) | [codebase-design](../engineering/codebase-design.md) |
| The domain words themselves ("account" means three things) | [domain-modeling](../engineering/domain-modeling.md) |

## The vocabulary

The skill's leading words, each defined against the others:

| Term | What it means | Don't say |
|---|---|---|
| **Transaction** | The unit of work between `BEGIN` and `COMMIT`/`ROLLBACK`. | operation, request |
| **Invariant** | A rule that must hold after every commit. Consistency means the ones *you declared* hold. | business rule (too loose) |
| **Anomaly** | A specific way concurrency produces a result no serial order could. Name which. | race condition (on its own) |
| **Isolation level** | The engine's dial between throughput and which anomalies it prevents. | |
| **MVCC** | Writers make new row versions; readers see a snapshot and never block on writers. | |
| **WAL** | The write-ahead log, fsync'd before commit is acknowledged. Explains atomicity and durability in one mechanism. | |
| **Idempotency** | Same logical operation N times has the effect of once. Makes a *retry* safe; atomicity does not. | exactly-once |

## Common questions

**Is Repeatable Read enough for a balance check?**

No. On Postgres, Repeatable Read is snapshot isolation: it stops phantoms but still allows write skew, so two transactions can each pass `balance >= amount` and together overdraw. Either fold the check into the UPDATE's `WHERE`, take `FOR UPDATE`, or go Serializable with a retry loop.

**Why does the skill keep saying "retry loop"?**

Because at Repeatable Read and Serializable a conflicting write aborts your transaction, and a deadlock aborts one victim. Code that cannot retry there is code that fails under load in a way it never fails in tests.

**Does it cover Kotlin / Java / Go / whatever?**

The skill is language-agnostic on purpose. SQL is the example language because it is universal; the rules apply to any client. Ask for the language and version before it writes code, as usual.

**Isn't ACID "consistency" the same as strong consistency?**

No, and the skill makes the agent say which one it means. ACID-C is "declared invariants hold"; CAP-C is linearizable reads system-wide. "Strong consistency" for a ledger almost always means the CAP sense.

## It's working if

- Transactions in the diff are short and contain no network calls; locks are taken late and released at commit.
- Balance moves are one guarded statement, or a `FOR UPDATE` read followed by the write in the same transaction, never a plain read-then-write.
- Anywhere the isolation level or a lock can abort, there is a bounded retry.
- Retried request paths carry an idempotency key backed by a unique constraint, saved in the same transaction as the effect.
- Cross-service work is written as a saga with an outbox, and nobody proposes two-phase commit.
- Reviews of transactional code name the anomaly they are worried about, not just "race condition".

## Where it fits

`acid-transactions` is a **vocabulary layer that runs underneath**, beside [codebase-design](../engineering/codebase-design.md) and [domain-modeling](../engineering/domain-modeling.md): the other skills speak it rather than route to it. [tdd](../engineering/tdd.md) uses it to decide which anomaly a test should force; [code-review](../engineering/code-review.md) uses its checklist on any diff that touches a transaction; [diagnosing-bugs](../engineering/diagnosing-bugs.md) uses its anomaly names when the symptom is a wrong count. For the whole map, ask [ask-denny](../engineering/ask-denny.md).
