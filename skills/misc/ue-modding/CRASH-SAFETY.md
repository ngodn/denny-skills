# Live-state ownership and restoration

Apply these checks from [ue-modding](SKILL.md) to the live state being touched.
They supplement the installed framework's contract; they do not describe every
Unreal binding as having the same crash behavior.

## Types and lifetime

Resolve real properties and signatures before access. Use the binding's supported
name, string, array and object types. Native memory corruption may bypass script
exception guards, so a guarded speculative call is still speculative.

Cache identities through supported weak/object handles or validated lifecycle
tracking. Raw pointers, property offsets and animation-node references need a
known layout and lifetime. Re-resolve after mesh/AnimInstance replacement, world
transition, destruction or reload. The owning AnimInstance is not permanently
stable either. A non-null address is not proof that its former object is alive.

Schedule changes on the owning thread and phase. Game-thread execution alone
does not make writes to concurrently evaluated animation data safe. Use the
engine/framework's synchronization or an established input handoff.

## Shared state and restoration

Capture a shared asset's true original once per identity before mutation; avoid
recapturing a modified value as its original. Keep restoration data separate from
current user intent. If the user changes a setting during temporary playback,
restoring an earlier playback snapshot must not overwrite that newer choice.

Define teardown before enabling callbacks: stop new work, drain or synchronize
in-flight work, restore owned state while its owner is valid, unregister hooks,
then release code/resources. The exact order depends on the loader and whether
restoration needs a game-thread callback. Verify it rather than assuming a single
gate flag solves unloading. Restore only state this mod owns.

## Compatibility and scope

Check skeleton, pose space and additive mode before animation replacement.
Large deformations are not successful motion merely because a metric changed.

Other mods can write the same state or hook the same function. Inspect hook-chain
support, ordering and ownership before choosing coordination, consolidation or
incompatibility detection. Multiple hooks are not inherently unworkable, and a
single merged mod is not the only possible solution.

For automated gameplay checks, stay within the authorized interaction and preserve
settings. Use safe scenes for movement tests; do not assume a trace proves every
hazard absent. Prefer offline or stationary inspection when that answers the
question without gameplay input.
