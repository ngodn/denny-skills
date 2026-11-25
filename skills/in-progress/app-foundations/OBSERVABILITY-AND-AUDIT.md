# Error tracking, logging and audit logs

Three different things with different guarantees:

| | Purpose | Loss tolerance | Where it lives |
|---|---|---|---|
| Telemetry (logs, traces, metrics) | Debug and operate the system. | A dropped batch is fine. | Observability backend, often several. |
| Error and crash tracking | Find and fix failures in clients and servers. | Best effort, but symbolicated. | A crash reporting service. |
| Audit trail | Prove who did what, when, on which device, with whose approval. | **None.** | The primary database, written in the same transaction as the change; copies go elsewhere. |

The most common mistake is treating the audit trail as a kind of log.

## Telemetry

1. **Structured logs only**, with stable field names. Every line carries a request id and, where known, the actor id and device id.
2. **Propagate trace context end to end**: device to API to workers to outbound calls. A sync request should be one trace from the phone to the vendor API.
3. **Emit a vendor-neutral protocol (OpenTelemetry/OTLP) to a collector you run**, and let the collector fan out to each backend (cloud monitor, SIEM). The app then never changes when a backend does. Run the collector with more than one replica; a single managed sidecar with a small in-memory buffer is a weak link.
4. **Telemetry SDKs that are still 0.x move together.** Upgrade the whole family in one change, and keep telemetry setup in one module.
5. **Flush on shutdown.** Shut down the exporters during graceful shutdown or lose the last seconds of telemetry, which are the ones you want after a crash.
6. **Metrics for the things you will page on:** request rate, error rate, latency percentiles, queue depth, outbox age of the oldest pending row, sync lag per device.

## Error and crash tracking

- Clients report crashes, ANRs and native crashes. For native code, keep the unstripped libraries (or split debug info) per release and upload symbols, or native stack traces are useless.
- Servers report unhandled errors and contained panics with the request id.
- Decide where crash payloads may live before choosing a service; they can contain user data. Self-hosting keeps data in your own tenancy at the cost of running it.
- Scrub tokens, passwords and payloads from crash reports and breadcrumbs.

## Audit trail

1. **Written in the same transaction as the business change.** If the change commits, the audit record exists.
2. **Append-only by grant and trigger**; corrections are new records that reference the original.
3. **Record both times**: when it happened on the device and when the server received it, plus the device's estimated clock skew.
4. **Record every actor**: requester, any approver, and how each authenticated.
5. **Tamper evidence**: hash chain plus signed checkpoints exported outside the database (see SECURITY-AND-RLS.md).
6. **Failed and denied actions are audit events too**: lockouts, permission denials, rejected sync items, exception resolutions.
7. Copy audit events to the SIEM for searching, but the database copy is the authoritative one.

## Traps

- Logging full request bodies "for debugging" and leaking personal data or tokens.
- Audit records produced by a log pipeline that can drop batches.
- Device timestamps used as the order of events in an audit report.
- Release builds with stripped native libraries and no archived symbols.

## Checklist

- [ ] Logs are structured and carry request, actor and device ids.
- [ ] Trace context propagates from client to server to outbound calls.
- [ ] Telemetry goes through a collector; exporters flush on shutdown.
- [ ] Crash reporting covers native code with symbols archived per release.
- [ ] Audit records are written in the business transaction, append-only, with both times and all actors.
- [ ] Denials and failures are audited.
