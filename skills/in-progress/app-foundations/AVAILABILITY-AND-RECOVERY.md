# Availability and recovery

Start from two numbers agreed with whoever owns the business: **RPO** (how much committed data you may lose) and **RTO** (how long you may be down). Every choice below is sized against them. An offline-first client buys you RTO for reads and queued writes, but not for anything online-only.

## Running

1. **At least two replicas of anything on the request path**, no scale to zero for the API. Background workers that take leases can run two safely.
2. **Three probes, three meanings.**
   - Liveness: the process is alive. No dependency checks, or a database blip restarts every replica at once.
   - Readiness: can serve now (pool can acquire a connection quickly, migrations at the expected version, key sets loaded, not shutting down).
   - Startup: covers slow warm-up so liveness does not kill it.
3. **Graceful shutdown inside the platform's grace period.** On SIGTERM: fail readiness, stop taking new leases or jobs, finish in-flight requests, flush telemetry, close the pool. Keep the drain budget well under the platform's termination grace period (check its default; 30 seconds is common).
4. **Contain failures per request.** A panic or unhandled exception in one handler returns a 500; it does not kill the process and every other in-flight request. In Rust that means keeping `panic = "unwind"` on servers.
5. **Backpressure everywhere.** Request body limits, per-route timeouts, a global concurrency limit with load shedding, a short pool acquire timeout (a few seconds) so overload returns 503 instead of piling up, and bounded channels and queues.
6. **Workers recover from their own crashes.** Leased work (outbox rows, jobs) has a lease expiry and a sweeper that returns expired leases to pending. Every job is idempotent so a re-run is safe.
7. **Migrations before traffic.** Run them as a one-off job, keep them backward compatible with the running version (expand, deploy, contract), and never run them from every replica at start-up.

## Data protection

1. **Managed database with zone-redundant HA, point-in-time recovery, and geo-redundant backups** if the RPO and RTO call for it.
2. **Restore drills on a schedule.** A backup you have never restored is a hope. Time the restore and compare against the RTO.
3. **Know what a restore loses.** After a point-in-time restore, devices may hold records the server no longer has. An idempotent sync protocol with client-made ids lets devices re-push them; make sure your design allows that.
4. **Audit and tamper evidence survive a restore.** Signed checkpoints stored outside the database let you prove what the chain looked like before the incident.
5. **Secrets and keys are recoverable.** Key vault soft-delete and purge protection on, and a documented path to restore a signing key.

## Deploys

- Pin images by digest; roll out with revisions or canaries; keep the previous revision ready to take traffic.
- Health-gate the rollout on readiness and error rate, not on "container started".
- Client and server versions overlap in the field for weeks on mobile. The server accepts the previous wire format version until every device has moved on.

## Traps

- Liveness probes that check the database, turning a database failover into a restart storm.
- A shutdown that exceeds the grace period, so the platform kills the process mid-request and the telemetry for it is lost.
- `panic = "abort"` (or the equivalent) on a server, so one bad request kills every request on that replica.
- Backups configured, restores never tested.
- A single-replica telemetry collector or worker that becomes the outage.

## Checklist

- [ ] RPO and RTO are written down and the design meets them.
- [ ] Two or more replicas on the request path.
- [ ] Liveness, readiness and startup probes have distinct checks.
- [ ] Graceful shutdown drains within the platform grace period and flushes telemetry.
- [ ] Body limits, timeouts, concurrency limit, load shedding, short pool acquire timeout, bounded queues.
- [ ] Leased work has expiry and a sweeper; jobs are idempotent.
- [ ] Restore drill done and timed in the last quarter.
- [ ] Server accepts the previous client wire version.
