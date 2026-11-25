# Testing offline sync

Offline bugs hide in timing and order, so most of these tests are about replay, interleaving and clocks. The bar: every scenario below has an automated test, and the airplane-mode script has been run by hand on the real target device.

## Rule tests (shared module, host machine)

- **Duplicates are no-ops**: applying the same record twice gives the same state as once.
- **Replay is deterministic**: applying a device's log from scratch gives the same state every time (needs an injected clock).
- **Interleavings**: property tests that generate several devices' logs and apply them in any order that respects each device's sequence; the final state and the set of exceptions must match the rules, and nothing is lost.
- **Gaps**: a missing `device_seq` holds later records; filling it releases them in order.
- **Conflict table**: one test per row of the per-kind conflict rules.
- **Chain**: verification fails on any single-byte change, on a reordered record, and on a removed record.
- **Golden vectors**: canonical bytes and hashes for fixed records, checked in, run on the server and on device builds (through the FFI if the rules are shared native code).

## Protocol tests (server with a real database)

- Push the same batch twice; second answer is all `duplicate`, no new rows.
- Kill the connection after the server commits but before the response; the device resends and gets `duplicate`.
- Push from two devices that conflict; first accepted wins, second is an exception with a reason code.
- Pull with an old cursor after a large change set; paging is complete and ordered.
- Revoke a user, pull, then try to submit as them offline; the device blocks it after pull, and the server rejects a record queued before the pull.
- Run against a real database in a container, not a mock; the unique constraints are part of what is being tested.

## Clock tests

- Device clock ahead by hours, behind by days, and changed by the user between two actions. Records are accepted, flagged where implausible, and ordered by server commit.
- Skew estimate matches the injected offset within tolerance.
- No security check (token expiry, verifier validity) reads device time.

## Device tests

- Queue survives app kill during `sending`, reboot, and an app upgrade with a schema migration.
- Background sync starts on reconnect with no app in the foreground.
- The database opens in a background worker with the screen locked.
- Sync status on screen matches the queue after each step.

## Airplane-mode script (by hand, on the real device)

Run this on every release candidate. Write the expected result next to each step and tick it off.

1. Online: sign in, pull, confirm data present and status "synced".
2. Turn on airplane mode. Create three actions, one of which will conflict on the server.
3. Kill the app. Reopen. All three still queued; drafts intact.
4. On another device (online), make the change that conflicts with action two.
5. Change the first device's clock forward one hour. Create a fourth action.
6. Turn off airplane mode. Watch sync without touching the app.
7. Expect: actions one, three and four accepted; action two shown as needing action with a readable reason; action four flagged for clock review on the server.
8. Resolve action two in the exception workbench. The resolution syncs as a new linked record.
9. Repeat step 6 while toggling the network on and off mid-sync. Expect no duplicates and no lost records.

## Load and soak

- Many devices reconnecting at once (shift change, after an outage): the server sheds load with 503 and `Retry-After`, devices back off with jitter, and every record eventually lands once.
- A device that was offline for days with hundreds of queued records syncs in bounded batches without timing out.
