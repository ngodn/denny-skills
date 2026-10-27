# Diagnose locomotion on a fitted character

Use this reference when a replacement body trembles, stretches or appears to
break at a joint during a specific gait. Keep concrete game paths, selectors,
scripts, thresholds and recordings in the project's evidence directory.

## Reproduce the requested gait

Record the active gait or locomotion state during every measured frame. Low
speed alone does not prove walking: full-input jog can be slow against an
obstacle. Where the game exposes a supported force-walk function, pair it with
bounded scripted movement and verify the resulting state. Describe scripted
walk as scripted walk; matching the gait does not establish identical physical
controller input. Use [GAME-CONTROL.md](GAME-CONTROL.md) for background input.

Capture appearance, morph values, saved animation choices, terrain, camera,
position and rig inputs. Restore owned changes and input in `finally`, including
failure paths. A saved selector may need the game's request channel rather than
a similarly named customization service; verify the active clip/state as well
as the saved choice. Restore each outfit's original choice separately.

## Separate bone motion from skin deformation

Measure joint-to-joint lengths in component space using the actual chain bones,
not twist helpers. Record local child translation, component scale, reference
length and knee flexion on both sides. State sample times and units. Report a
60 Hz angular step only for samples that support that time interval, and flag
gaps rather than treating delayed samples as one frame.

A knee-plane normal becomes unstable near full extension. Inspect flexion and
the video around a sign change before calling it a visible knee flip. Locate
peaks in the walk cycle so a clip's normal swing is not mistaken for a pop.

Run the same fixture on a visually accepted control body. Use that comparison
and the agreed visual gate to interpret solver residuals; an arbitrary numeric
threshold is not a universal animation standard. Preserve both measurements
and any acceptance change in the report.

## Isolate the pose writer

With identical movement, vary one owner at a time: all Control Rigs, the body
post-process rig, an outfit stance correction, then native foot IK. Restore each
switch immediately after its recording. Turning an owner off is a diagnostic,
not proof that removing its function is an acceptable fix.

If stretch survives all rigs being disabled, inspect source clips for keyed
translations and blends of clips with different segment lengths. If it follows
one rig, inspect that rig's initial transforms and cached solver state before
changing skin weights or copying another body's axes.

In UE 5.6.1, `FAnimNode_ControlRig::bSetRefPoseFromSkeleton` overrides initial
transforms from the mesh component. The PBIK unit builds its solver bones from
`InitialGlobal` transforms during initialization; its automatic change hash
tracks effector and bone-setting names, not those transforms. Updating the
hierarchy alone can therefore leave old lengths cached. Check the matching
engine source and the rig's supported reinitialization lifecycle. Verify both
the flag and the resulting motion after reinitialization. Reinitializing every
frame would reset state and is not the intended repair.

Source locations in that version: ControlRig's `Public/AnimNode_ControlRig.h`
and FullBodyIK's `Source/PBIK/Private/RigUnit_PBIK.cpp`. The flag is also described
in Epic's [ControlRig node API](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/ControlRig/FAnimNode_ControlRig).
Recheck other engine versions instead of carrying offsets or cache assumptions
across builds.

Keep native terrain grounding active in the final configuration. Blend a
standing-only barefoot correction out during movement. Verify outfit switching
and restoration so a body-specific repair cannot affect stock bodies or NPCs.

## Verify contact separately

For finger/ornament interference, replay captured transforms and worn morphs
against the exported surfaces. Measure point-to-triangle distances; nearest
vertices can miss a collision with a broad triangle. State whether the probe
covers fingertip points or the full finger volume. Test the proposed ornament
adjustment on every affected gait before packaging, then repeat on the installed
revision. Retain topology correspondence when applying index-based edits.

For attacks passing through a body, inspect both the mesh PhysicsAsset and any
component override. A player capsule does not prove skeletal hit shapes exist.
Fit donor primitives and constraint anchors to the replacement bind pose and
verify the cooked reference after restart. Component ray queries establish
query coverage; they do not establish enemy attack handling. Preserve an
intentional invulnerability setting and distinguish contact from damage loss.
