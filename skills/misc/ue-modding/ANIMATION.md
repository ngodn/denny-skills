Animation and skeleton engineering for [ue-modding](SKILL.md): generalisable technique for driving character animation and secondary motion in a live, running game, with no editor and no engine source access beyond what you can read for a specific serializer.

## Bone registry keyed by naming pattern

Build a cached registry of every bone on a character, keyed by a naming pattern (a chain prefix, a family name) rather than by hardcoded literal bone names. A pattern-keyed registry survives an asset or body-mesh swap that changes the underlying mesh but keeps the same naming convention; a registry of hardcoded names breaks the moment the mesh changes.

## The evaluated pose buffer is read-only for your purposes

The live, already-evaluated per-bone component-space transform array can be located and read for measurement or diagnostics. Writing to it directly is a dead end: the animation worker recomputes and overwrites that buffer after the point where an external write could take effect. Drive an actual pose change through the animation graph's own nodes, a bone-modifier node, for instance, rather than racing the pose buffer with a direct write.

## Forcing a pose by overwriting blend-space samples

A blend space normally samples between several animation sequences by parameters like speed or direction. Overwriting every sample's animation pointer with the same target sequence forces that one animation out regardless of the blend parameters, with no hooks and no input synthesis needed. Two hard gotchas: it mutates a shared asset, so the capture-before-mutate rule in crash safety applies in full, and only same-skeleton swaps are safe; a skeleton mismatch that the editor would normally reject at author time has no equivalent safety guard at runtime, and will crash.

## A static base pose starves everything downstream

Physics-driven secondary motion, spring-bone or soft-tissue chains, only reacts to upstream animation motion; it has no independent drive of its own. Swapping in a static pose instead of a live idle animation silently kills all downstream secondary motion, along with breathing and natural limb sway, because there's no upstream signal left for it to react to. When downstream physics "isn't working," check whether the upstream animation driver is actually moving before assuming the physics system itself is broken.

## Spring-bone chains are a mass-spring-damper family

A built-in spring-bone node and most third-party secondary-motion plugins solve the same mass-spring-damper system, so reason about either one with the same three numbers: stiffness `k`, damping `c`, and the damping ratio they derive, `ζ = c / (2·sqrt(k))`. If a character has no physics asset at all, confirmed by the physics-asset accessor returning nil, any "rigid body impulse" style API is a guaranteed no-op on it; that class of technique can be ruled out immediately, in favour of driving the spring-bone node's own tunable fields (max displacement, stiffness, damping) directly, or building an independent spring-damper simulation when the built-in node's evaluation budget can't cover the needed set of bones.

## Enumerate morph target names, don't read the raw array

Reading a morph-target array directly, rather than through the framework's enumeration API, is a known crash risk. Enumerate the available names first, then drive expression by calling the standard "set value by name" function with the name obtained that way.

## Procedural motion design principles

- Let phase lag between primary and secondary motion emerge from the spring-damper's own dynamics rather than hand-authoring a fixed offset per bone; an authored offset reads as mechanical where an emergent one doesn't.
- Ramp frequency and amplitude on separate curves and never couple them (frequency ramping early, amplitude ramping late is a reasonable default), so the motion doesn't read as a metronome.
- Add small per-cycle randomisation to timing and easing so repeated cycles don't look identical.
