# Rate limiting and backpressure

Two directions: protecting your API from callers, and keeping your workers inside someone else's limits.

## Inbound: protecting your API

1. **Key the limiter on authenticated identity** (user id, device id, API client), taken from the validated token. Behind a load balancer or ingress the peer IP is the proxy; trusting a client-supplied `X-Forwarded-For` is a known bypass. Use IP only for unauthenticated routes, and only the address your own proxy appended.
2. **Use a token bucket or GCRA**, which allows short bursts and enforces a steady rate. Set the limit per route class (sync batch, lookup, admin), not one global number.
3. **Answer `429 Too Many Requests` with `Retry-After`.** Clients then know when to come back instead of hammering.
4. **Global protection is separate from per-caller limits.** A concurrency limit plus load shedding returns `503` fast when the service is saturated, instead of queueing requests until they time out. Add a request body limit and per-route timeouts.
5. **Expect thundering herds.** Many devices syncing at shift change or after an outage all arrive at once. Clients add jitter to their retry and sync schedules; the server sheds load rather than falling over.

## Outbound: calling rate-limited APIs

1. **One limiter per destination**, shared by every worker that calls it, set below the vendor's published steady-state rate.
2. **Treat `Retry-After` as the minimum wait**, then back off exponentially with jitter (for example a random factor between 0.7 and 1.3) and cap the per-pass attempts.
3. **Read the vendor's reason headers** if they send them: a quota limit means pause all calls until reset; a burst limit means slow that endpoint.
4. **A dropped connection is not a status code.** Some platforms drop sockets under sustained load independent of their rate limit; your retry wrapper must catch thrown network errors, not just non-2xx responses.
5. **Long outages are the outbox's job.** Per-call retries are short; the outbox keeps the message and retries with growing delay for as long as it takes.
6. Look up the vendor's current published limits before sizing a batch job; they change.

## Client side

- Retries use exponential backoff with jitter and a cap, and stop on errors that will not fix themselves (401 until credentials change, 4xx validation).
- Background sync uses the platform scheduler's backoff (for example WorkManager on Android) and unique work so only one sync runs at a time.

## Traps

- Rate limiting by IP behind a proxy, so every user shares one bucket, or anyone can spoof their way out of theirs.
- Unbounded in-memory queues in front of a limited destination: the limiter holds, memory does not.
- Retrying in lockstep without jitter, so every client retries at the same second.
- Fixed retry caps per message in an outbox, quietly dropping deliveries during a long vendor outage.

## Checklist

- [ ] Inbound limiter keyed on authenticated identity; proxy headers trusted only from your own proxy.
- [ ] 429 responses carry `Retry-After`.
- [ ] Concurrency limit, load shedding, body limit and timeouts are in place.
- [ ] Each outbound destination has one shared limiter below its published rate.
- [ ] Retries honour `Retry-After`, use jitter, and catch thrown network errors.
- [ ] Client sync schedules are jittered.
