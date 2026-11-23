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

## Retargeting between rigs with different joint counts

A chain mapped end to end (three source trunk bones onto five target spine joints, one neck bone onto
two) leaves the target joints with no partner at zero in every clip. The whole bend then lands on the
joints that line up, and the skin folds there: a kinked neck base, a chest that hinges in one place
under the ribcage. Audit before judging the mesh:

- Per clip and joint, the 95th percentile angle against the bind pose. A joint at 0.0 in every clip is
  dropped by the mapping, not unused by the performer. Confirm in the source: if the source rig has the
  motion and the output lacks it, repair the mapping; if the source never had it, add a rule.
- For each chain, the share of the bend taken by one joint. One joint carrying over 60 % of a bend
  larger than 15 degrees is a kink. Sharing the bend over the chain took kinked frames from 53 % to 3 %.

Share the bend along the chain with the end of the chain held in world space (the head keeps its
orientation so the gaze is unchanged, the chest keeps its orientation so the arms do not move). Share
over the upper spine only: sharing over the whole spine moved the chest 3 to 5 cm and broke hand
contacts, the upper three joints moved it under 1 cm. Check afterwards that the end of the chain sits
within about 1 cm of where the source had it, and re-solve any contact that hangs off it (a mouth or a
head resting on something) after the share, with the contact winning.

Other faults the same audit finds:

- **Shoulder rhythm.** Motion from rigs that raise the arm from the shoulder joint alone stretches the
  armpit and deltoid skin. A real shoulder girdle rises about 0.3 degrees per degree of arm elevation
  above 30. Ease the clavicle toward that, ease an unexplained shrug back down when the arm is low, then
  re-solve the arm with two-bone IK to the original hand position and rotation, bending the elbow toward
  its original side so a straight arm cannot flip.
- **Wrist roll.** Measure the hand's roll about the forearm axis against the bind pose, not the hand's
  full local rotation (a bind pose with the hand already rolled makes the second measure wrong and the
  fix worse). Drive the forearm and upper-arm twist bones (one third, two thirds) when the mesh weights
  them. A mesh with unweighted twist bones can only spread roll between elbow and wrist: move a share
  onto the forearm as a stopgap and treat the weights as the real fix.
- **Pose or mesh?** Fix the pose first and render the same frame again. A crease that survives a natural
  pose is skin weighting and goes to whoever owns the mesh, with the before and after pictures.

Review pairs use the same frame before and after, from the front and the side, and from the camera the
viewer will actually have. Numbers pick the worst frames; pictures decide.

## Hands on another body

Order matters, and each step fails in its own recognisable way:

1. **Resting or gripping.** Decide per frame from the source pose: a palm sunk well into the surface is
   a grip, a palm at the surface is a rest. Keep the decision through smoothing, or a later lift step
   puts every grip back at resting depth.
2. **Palm first.** Fit the palm to the local surface (palm plane along the surface tangent, knuckle line
   just inside the skin, wrist free by IK). A palm that touches at one point leaves the knuckles 3 to 4 cm
   off the surface, and no finger solve can close that: the result is a claw.
3. **Then the fingers.** Per finger, place pad targets along the surface from the knuckle outwards,
   spaced by the segment lengths, thumb opposing. Solve inside natural joint ranges, the end joint never
   more bent than the middle one. Smooth the targets and then solve; solving and then smoothing lets the
   fingertips sink.
4. **Limit each point by what the surface under it can give.** Soft tissue takes centimetres, skin over
   bone a millimetre. A single depth allowance per hand lets a fingertip on firm skin go as deep as the
   palm on soft tissue.
5. **Then the deformer.** Collision capsules follow the bent finger (several per finger, tip measured on
   the mesh; one straight capsule per finger misses the tips by a centimetre). Whatever is still inside
   after the dent and its smoothing needs a final clearance step: a smoothed dent never fully clears.

A hand that holds a moving body is judged against that body while it touches, and against the recording
otherwise. A free hand at rest curls in a cascade (index least, little finger most); equal curl on every
finger reads as a paddle.

A runtime deformer absorbs a few centimetres. Fix larger overlaps in the pose (separation, a wider
stance with the feet re-planted) before the deformer, and render a reference of the intended result
before any live test, so a failed live test can be told from a wrong target.

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

Check that each slider moves the region its name promises before shipping. Artist
morphs are often named for several regions ("booty & thighs") and two sliders built
from sibling morphs can end up as one shape twice. For every unit delta, measure
where its displacement lands by dominant bone weight (thigh, pelvis, glute, spine)
and the girth change at a few heights along the limb. Then least-squares fit each
slider's delta from the others: a slider that another reproduces within a few
millimetres is a duplicate, whatever its label says. Fix by masking the artist delta
to its region (bone-weight mask with a smoothed falloff) and filling the rest of the
limb with a smooth radial growth that tapers to the next joint. Generic measurement
targets (circumference "measure" targets) can transfer lumpy near joints; render
them before trusting the numbers.

Changing a released slider changes every preset that uses it. Refit those presets
with bounded least squares over the slider values, bounding unrelated sliders to
their old values so the fit cannot trade one region for another. Report the largest
and the RMS surface difference per preset, name any preset that hits a slider limit,
and show before/after renders. When a shape route (a choice that swaps which morph a
slider drives) exists, run ornament and contact clearance for every option across
the endpoints and every changed preset, not only the default option.

## Facial motion and acceptance

Discover morph names and graph/curve bindings using a verified reader or reflected
API. Validate object lifetime and container layout before reading raw arrays.
Test eyes and facial motion alongside body playback, interruption and restoration.

Captured or generated face curves read as overacted long before they read as wrong. Gains on single
curves (brows doubled, a wider mouth) stack into extremes when several fire together. For a natural
default: no per-curve gains, left and right kept symmetric unless the source is clearly not, temporal
smoothing, and a cap on how many curves may sit near their limit at once. Offer strength as one control
that scales every curve around the neutral face, `v = neutral + S * (v - neutral)`, with a calm default.
Check eyes on close frames: a gaze that misses its target by a few degrees reads as vacant.

Keep the scope of evidence explicit: an offline transform or strain check is not
visual acceptance. Review the garment in the editor and target game at useful
viewing scale, including any supported doubles/alternate appearances. Keep
unrelated source assets and already accepted behaviors intact.
