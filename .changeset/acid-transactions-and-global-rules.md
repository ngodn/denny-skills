---
"denny-skills": minor
---

Add `acid-transactions`, a model-invoked engineering reference for transactional integrity: the four ACID promises, the five anomalies, isolation levels per engine, the atomic guarded UPDATE vs `SELECT FOR UPDATE` vs optimistic CAS, hot-row handling, and what replaces ACID across services (saga, transactional outbox, idempotency, why not 2PC), plus a review checklist. Docs page, README, plugin manifest, and the `ask-denny` router updated.

Add `templates/CLAUDE.global.md`, the team's shareable global instructions file (writing style without em dashes, ask when in doubt, research online first, confirm language and version via whatever version manager the machine has, OS-appropriate privilege escalation, reading past sessions, pointer to `acid-transactions`). README gains an "Adopt the working rules" step.
