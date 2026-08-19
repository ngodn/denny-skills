Crash-safety rules for [ue-modding](SKILL.md): rules for any code, scripting or native, that reads or writes live engine state from outside the engine. Each one names a failure mode a generic exception guard does not catch, so treat this as a checklist to run over a change before trying it live, not just background reading.

## Enumerate, never guess

Reading a property that doesn't exist on a given object, or calling a function by a speculative or half-remembered name, crashes past a generic exception guard rather than erroring gracefully. Always discover real names through the framework's own enumeration API, or a full SDK dump, before reading a property or calling a function.

## Wrap name-typed values in the engine's interned name type

An API that expects an interned or name-pool type (rather than a plain string) for lookups like bone or socket names will crash on a raw string instead of failing cleanly. Always construct the engine's own name type first, never pass a plain string where a name type is expected.

## Never cache handles into per-frame graph state

References into a live animation-graph or per-node object can go stale between ticks. Re-resolve every tick rather than caching a handle into that per-frame state, while still caching the *stable* owning object (the instance itself, which doesn't move) plus any fixed offsets into it.

## Never cache actors across a level boundary

A cached actor or object reference held across a level-streaming transition can end up pointing at a freed object. Re-fetch the live handle on every use, deliberately never caching one across a span of time in which a level transition might occur.

## Capture the true original before mutating a shared asset

A shared engine asset edited at runtime, a blend space or a data table, is process-global, not per-actor: editing it in place affects every user of that asset for the rest of the process, and nothing resets it automatically. Any such edit must capture the true original value exactly once, keyed by identity, before the first modification, and restore it explicitly on stop, unload, or level change. Guard against re-arming while the asset is already in a modified state, which would capture the modified state as if it were the original, a distinct and recurring failure class worth naming and watching for on its own.

## Absolute and additive animation data are not interchangeable

Writing absolute (non-additive) animation data into a slot that composites additively deforms the result violently. A large measured change in some metric, bone displacement, for instance, can look like a spectacular success while actually being corrupted geometry. Cross-check any such metric against a sane baseline magnitude; "it changed a lot" is not the same as "it worked."

## An exception guard has real limits

Wrapping a reflected call in an exception guard protects against some failure classes, a missing property, a thrown exception, but not out-of-bounds memory writes or some marshalling errors, which crash straight past the guard regardless of whether it's present.

## Do a cheap safety check before anything that could put the player somewhere dangerous

Before an automated action that could move the player into danger, an automated dodge near a ledge, for example, run a cheap synchronous safety check first (a short ring of downward line traces is a common shape), and treat any uncertain or failed check result as unsafe, falling back to a strictly safer default action rather than the risky one. Fail-safe by construction: if the check's own dependency is unavailable or throws, the default answer is "unsafe," never "proceed."

## Two mods hooking the same function fight over the last write

When two independent mods each install a hook on the same target function and both write the same output, the result is nondeterministic, last writer wins, per call. The durable fix is to merge the two into one mod that owns the single hook and arbitrates internally, rather than trying to make two independent hooks coexist. A hookable extension point in someone else's framework is often, in practice, a singleton resource.
