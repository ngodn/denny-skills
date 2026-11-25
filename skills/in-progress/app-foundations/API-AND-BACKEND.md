# API design and backend logic

For anything inside a database transaction (isolation, locks, outbox, sagas, idempotency storage), call the Skill tool with `acid-transactions`. This file covers the shape around it.

## Layout

- **Domain module with no IO.** Types, state machines, validation and conflict rules. No HTTP client, no database driver, no async runtime. Enforce it in CI by checking the dependency tree of that module. This is the module a mobile client can also compile.
- **Ports and adapters.** The application layer defines traits or interfaces (event store, outbox, clock, external gateway); adapters implement them; tests swap in in-memory versions.
- **Time is a port.** Domain code takes a clock, never calls "now" itself, so replays and tests are deterministic.
- **Parse, don't validate.** Shape checks (length, format, range) at the HTTP edge; business invariants enforced by constructors that return a result, so an invalid value cannot exist past the edge.
- **Typed errors in libraries, catch-all errors only in binaries.** A caller that must branch on an error gets an enum, not a string.

## API rules

1. **Version the wire format and generate the spec from code.** Publish the OpenAPI (or equivalent) document as a build artifact and diff it on every pull request so breaking changes are seen, not discovered.
2. **Every mutating endpoint is idempotent.** Device-created records carry their own id (UUIDv7 works offline and indexes well). Other callers send an `Idempotency-Key` header; store `(caller, key, request_hash, response)` under a unique constraint. Same key with a different request hash is a 422, not a replay.
3. **Batch endpoints answer per item.** For a batch of commands, return one result per item: accepted, duplicate (with the original result), conflict (with the reason and current state), rejected (validation). Never fail the whole batch for one bad item unless order demands it.
4. **Order within a stream, not across devices.** Process each device's or client's commands in its own sequence; order across clients by server commit order. Device clocks never order anything.
5. **Optimistic concurrency by expected version.** A command states the version it read; the write uses `version = expected + 1` under a unique constraint; a violation is a conflict the domain classifies (commutes, or real conflict).
6. **Outbound integrations go through an outbox.** Write the outbox row in the same transaction as the change; a relay delivers it later with retries. No HTTP call inside a transaction.
7. **Deliver per aggregate in order.** The relay picks only the oldest pending row per aggregate, so the receiver never sees an older state after a newer one. This is the classic outbox bug; property-test it.
8. **Every outbound call has a connect timeout, a total timeout, a retry policy with jittered backoff, and a rate limiter per destination.** If the receiver has no idempotency support, send absolute state ("set X to V as of version N"), never deltas ("increment X").

## Traps

- A handler that panics or throws and takes the whole process with it. Contain failures per request (unwinding panics, a catch-panic middleware, a top-level handler) and return a 500 with a logged error.
- `anyhow`-style catch-all errors leaking into library APIs, so callers string-match messages.
- SQL assembled with string formatting. Use parameterised or compile-time checked queries and make the escape hatch greppable.
- An outbox relay that holds a transaction open while calling the destination.
- Relay retries capped per message, so a long outage silently drops deliveries. Retry forever with growing delay, and park poison messages as `dead` with an alert.

## Checklist

- [ ] Domain module has no IO dependencies, checked in CI.
- [ ] Clock is injected; no "now" in domain code.
- [ ] Every mutating endpoint is idempotent by id or key with a stored response.
- [ ] Batch endpoints return a result per item.
- [ ] API spec is generated from code and diffed in CI.
- [ ] Outbound calls go through an outbox, with timeouts, backoff, a limiter, and per-aggregate ordering.
- [ ] No network IO inside a transaction (see `acid-transactions`).
