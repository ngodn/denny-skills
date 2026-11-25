# Caching

A cache is a copy with a staleness budget. Before adding one, write down three things: what the source of truth is, how stale the copy may be, and what invalidates it. A cache without those three answers is a bug with a delay.

## Where caches live

| Layer | Good for | Watch out for |
|---|---|---|
| On-device local store | Everything the app reads offline. In an offline-first app this is not a cache but the working copy (see OFFLINE-AND-SYNC.md). | Wiping it on user change; schema migrations on upgrade. |
| HTTP caching (`Cache-Control`, `ETag`) | Reference data and static assets. Conditional requests (`If-None-Match`, answered with `304`) save bandwidth without serving stale data. | Never let a shared cache store per-user responses: mark them `private` or `no-store`. |
| In-process memory | Small, hot, read-mostly values: signing key sets, config, feature flags, lookup tables. | Each replica has its own copy, so invalidation is per replica. Bound the size. |
| Shared cache (Redis and similar) | Values expensive to compute and shared across replicas; sessions; rate-limit counters. | It is a network dependency that can fail; the app must work, slower, without it. |
| Image and file caches | Thumbnails and attachments on mobile. | Generate thumbnails at capture time and downsample to view size. |

## Rules

1. **Never serve a cached value on a path that decides something irreversible.** Balance checks, stock checks and confirmation screens read from the primary. Read-your-writes on a lagging replica or a stale cache is how double-spends happen (see `acid-transactions`).
2. **Prefer versioned keys to deletes.** Put a version or content hash in the key, so a new value gets a new key and old entries age out, instead of racing an invalidation.
3. **Protect against stampedes.** When a hot key expires, let one caller recompute while others wait or get the stale value (single-flight, or serve stale while revalidating). Add jitter to TTLs so keys do not all expire together.
4. **Refresh on a schedule and on miss, with a rate limit on the miss path.** The signing key set for token validation is the classic case: refresh every few hours, refresh on an unknown key id, but at most once a minute.
5. **Swap whole values atomically.** For a single value read by many threads, an atomic pointer swap beats a lock and beats a general cache library.
6. **Cache failures differently from successes.** A short negative TTL for "not found" stops repeated lookups; never cache errors from a dependency that is briefly down.
7. **Measure before and after.** A cache that does not change a measured latency or load is complexity with no payoff.

## Traps

- Per-user API responses cached by a CDN or shared proxy because the response lacked `Cache-Control: private`.
- Invalidation by delete racing a concurrent write that re-populates the old value.
- A shared cache treated as durable storage, then evicted under memory pressure.
- Caching authorization decisions longer than your revocation promise.

## Checklist

- [ ] Each cache names its source of truth, staleness budget and invalidation trigger.
- [ ] Irreversible decisions read from the primary, not a cache or replica.
- [ ] Hot keys have stampede protection and jittered TTLs.
- [ ] Per-user HTTP responses are `private` or `no-store`.
- [ ] The app degrades, not fails, when a shared cache is down.
