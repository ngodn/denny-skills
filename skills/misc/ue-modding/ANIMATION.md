# Skeletons, animation and secondary motion

Use this branch of [ue-modding](SKILL.md) for authored assets and live character
behavior. Recover the project's accepted skeleton, fitting and physics recipes
before changing them. Use [TOOLCHAIN.md](TOOLCHAIN.md) for import/cook details.

## Establish the actual skeleton contract

Compare bone names, parents, local reference transforms, root motion, retarget
settings and weighted/helper bones. Matching names or bone counts alone does not
establish compatibility. Preserve the mesh bind pose separately from the shared
skeleton asset. Resolve mesh-local indices when the mesh changes; naming patterns
can help discovery, but explicit validated mappings are appropriate for retargeting.

Verify same-skeleton playback before retargeting. For cross-skeleton work, use
the game's established retarget/export path and inspect representative moving
poses, hands, feet, attachments and facial curves. Compare decoded source motion,
authored output and runtime output to locate the first divergence.

## Find the owner of each motion

For gait-specific trembling, changing limb lengths or a knee that appears to
flip, read [LOCOMOTION-DIAGNOSIS.md](LOCOMOTION-DIAGNOSIS.md). It covers gait
verification, solver initialization, control recordings and ornament clearance.

Inspect the main AnimBP, linked layers, post-process graph, Control Rig, physics
asset, cloth and any runtime override. Track which one evaluates and which one
writes each affected region. Apparent doubled motion is a hypothesis until the
active owners and their inputs demonstrate it.

Route modifications through supported graph inputs, animation APIs or the
project's verified adapter. Direct writes to evaluated pose buffers require
proven ownership, evaluation timing and synchronization; a persistent-looking
write in one frame is not a reliable animation integration.

Blend-space sample replacement mutates a shared asset and may affect other
characters. Prefer scoped playback where available. If the project deliberately
uses shared replacement, capture originals by asset identity, check skeleton and
additive compatibility, and restore through the lifecycle contract in
[CRASH-SAFETY.md](CRASH-SAFETY.md).

## Diagnose physics by implementation

Identify the real solver and units before interpreting parameters. SpringBone,
AnimDynamics, KawaiiPhysics, rigid bodies, cloth and custom Control Rig programs
are not interchangeable. Similar parameter names do not prove compatible values.
A physical mass-spring-damper model is useful only if the implementation follows
it; stiffness/damping sliders may be normalized or use a different integration.

Check incoming animation, parent/component motion, gravity, external forces,
collision, timestep/substeps, reset behavior and displacement limits. A static
base pose removes one source of excitation, but gravity, wind or other forces
can still move a simulated region. Absence of a component physics asset does
not establish absence of all secondary-motion systems.

For presets, verify the UI value, saved value, public input and actual active rig
value. Check restoration after animation replacement, mesh swaps and world
transitions. Reuse an accepted older response as a measured comparison, then
change only the demonstrated cause. Keep runtime control propagation distinct
from the solver's actual motion limits.

## Cloth and dynamic body fit

Check simulation topology, skin weights, fixed particles, render-to-simulation
mapping, collision bodies, backstops, self-collision and body-shape deformation.
Cloth and rigidly skinned garments need different fitting checks. Compare the
same captured animated pose when isolating a constraint; report variation between
runs instead of treating a noisy pass as a reliable repair.

Disabling collision can identify a conflict without being a shippable fix.
Check both stretch and penetration, including the actual visible garment.
Preserve accepted body proportions, geometry, UVs and material assignments unless
the task calls for changing them. Evaluate neutral fit, supported body controls
and moving poses before accepting a replacement.

## Body shape morphs

Sliders read natural when their deltas come from artist sculpts transferred onto
the target body (non-rigid fit, barycentric binding), and boxy when they come
from procedural growth or inflation. Learn a character's proportions by measuring
game meshes, and keep the measurement separate from the shipped geometry.
Combine distinct sculpted morphs at their authored weight rather than pushing one
past it; a range beyond 1 is cleaner as extra stage morphs driven from the slider.
Review every candidate visually in the target game before calling it done.

## Facial motion and acceptance

Discover morph names and graph/curve bindings using a verified reader or reflected
API. Validate object lifetime and container layout before reading raw arrays.
Test eyes and facial motion alongside body playback, interruption and restoration.

Keep the scope of evidence explicit: an offline transform or strain check is not
visual acceptance. Review the garment in the editor and target game at useful
viewing scale, including any supported doubles/alternate appearances. Keep
unrelated source assets and already accepted behaviors intact.
