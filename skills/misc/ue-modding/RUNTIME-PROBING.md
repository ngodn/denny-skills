# Runtime probing

Use this branch of [ue-modding](SKILL.md) when runtime evidence is needed. Start
with offline assets, source and existing dumps when they can answer the question.

## Discover signatures before calls

Strings and extracted assets can identify candidate names, not their runtime
availability or behavior. Use the installed framework's reflection metadata,
matching SDK, source or verified disassembly to establish the class, signature,
parameter types and execution context.

Do not invoke an unknown function with dummy arguments to discover its arity.
An assumed marshalling failure is not a safe execution barrier. Validate binding
behavior in a controlled fixture if metadata is incomplete. String-to-FName
conversion, array handling and parameter validation depend on the binding version;
follow its actual API rather than assuming every mismatch either errors or crashes.

Keep class and owner context attached to names in a dump. Resolve the current
world, controller, pawn and mesh before attributing measurements to the player;
startup or preview actors can be different objects.

## Make each probe answer one question

State the hypothesis, inputs, observation and stopping condition. Prefer read-only
captures where sufficient. For mutations, record the original state and verify
restoration. Reuse existing diagnostics instead of growing one-use probes without
closing the earlier question. Keep negative results with their tested version and
scope so a later session neither repeats nor overgeneralizes them.

Bound scans, output and per-frame work. Global object searches may traverse large
tables; inspect the framework implementation and measure their cost before putting
them in a hot path. Cache validated identities with lifecycle invalidation rather
than scanning everything or retaining raw addresses indefinitely.

## Verify the observation

For keyboard/mouse probes and screenshots, use [GAME-CONTROL.md](GAME-CONTROL.md).
Verify input reception and the resulting gameplay state separately; a successful
input command alone does not establish a successful action.

Record process/build identity, object identity, current appearance and relevant
state. Check that the instrument responds to known cases and use a negative
control when a false success is plausible. A call returning without error proves
only that it returned; read back the affected state and inspect the visible
result where relevant. A failure in one hook or RPC category does not establish
failure of other mechanisms.

For crash investigation, flush a small identifying record before the risky step
and retain the crash data. Script exception handling does not catch every native
memory fault. See [CRASH-SAFETY.md](CRASH-SAFETY.md) for lifetime and teardown,
and [NATIVE-HOOKING.md](NATIVE-HOOKING.md) if supported extension points cannot
meet the demonstrated requirement.
