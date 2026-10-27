---
name: ue-modding
description: Set up and use Unreal Engine modding toolchains, including CUE4Parse extraction and patches, Blender asset authoring, compatible Unreal editors and cooking, pak/IoStore packaging, and UE4SS Lua/C++ runtime mods. Use for shipped-game asset replacement, character ports, animation/physics work, runtime investigation, and gameplay testing or screenshots without taking desktop focus.
---

# UE Modding

Start from the game's actual format and the available tools. A shipped game
usually does not include its original editable project. That does not prevent
using a compatible Unreal editor, licensed engine source, Blender, an extractor,
or a purpose-built authoring project to create replacement assets.

## Recover the working pipeline first

Read the project's current status, accepted build recipes and relevant earlier
work before inventing a replacement workflow. Treat old agent notes as leads:
check their source, artifact or reproduction before carrying a claim forward.
Keep known-good inputs and the user's selected source assets distinct from
rejected trials.

Identify the game build/platform, engine branch or custom version, container
format, mappings, installed loader fork and existing tool revisions. Consult
maintainer documentation for setup and compatibility. Inspect local manifests,
patches and executable versions to establish what is actually available.

When asked to set up tools, perform the setup and a representative smoke test
within the user's authorization. A failed importer or missing dependency is a
specific problem to diagnose, not evidence that modding the game is impossible.
Ask only for genuinely unavailable inputs or human-only access steps.

## Choose the path that produces the requested change

| Work | Starting path |
| --- | --- |
| Inspect or extract cooked assets | CUE4Parse/FModel or a verified game-specific reader; supply the required containers and mappings |
| Fit outfits, edit geometry, retarget motion | Blender plus the verified importer/exporter; preserve original bind transforms separately |
| Create meshes, materials, rigs or animations | Compatible UE authoring project, import, save/reload, target-platform cook |
| Change supported cooked properties | Format-aware asset editor with an unchanged roundtrip before modification |
| Change gameplay or live customization | The installed loader's supported Lua, Blueprint or C++ extension points |
| Implement missing parser support | Small version-scoped patch against the serializer and sample assets |

For setup, extraction, Blender, editor and packaging work, read
[TOOLCHAIN.md](TOOLCHAIN.md). It includes how to preserve a patched CUE4Parse
checkout, distinguish editor support from target-platform cooking support,
trim and relocate cooked packages, and keep materials drawing after a game patch
(gray materials).

For character fitting, body shape sliders, retargeting, facial playback or secondary motion, read
[ANIMATION.md](ANIMATION.md). Extracted geometry, authored behavior, cooked data
and game appearance are separate verification stages.

For live reflection, read [RUNTIME-PROBING.md](RUNTIME-PROBING.md) and
[CRASH-SAFETY.md](CRASH-SAFETY.md). Use [NATIVE-HOOKING.md](NATIVE-HOOKING.md)
when a native hook is actually needed. Lua and Blueprint are valid production
choices; choose C++ for demonstrated requirements, not a blanket language rule.

For live gameplay input or screenshots while the user works in another window,
read [GAME-CONTROL.md](GAME-CONTROL.md). Prefer verified input addressed to the
game window and native game captures before taking desktop focus.

## Reload and installation are mechanism-specific

Distinguish editor Live Coding, script reload, a custom core-DLL loader and
mounted asset replacement. Success with one proves nothing about another.
Use a documented or locally verified reload path with its teardown and state
restoration contract. Otherwise restart for that change. Check the process's
loaded code and actual behavior, not just the file timestamp or loader message.

For an established project, preserve its tested reload workflow and its stated
limits. For example, a stationary core-DLL reload test does not establish safe
reload during animation-worker execution. A core reload also does not replace
already mounted cooked packages. Follow the asset installer's game-state check.

## Evidence and delivery

Separate upstream capabilities, local observations and hypotheses. Record exact
inputs, tool revisions/patches, commands, outputs and the scope of each result.
Successful parsing or cooking does not establish correct fit, shading, physics
or game behavior. Verify the final container's references and the installed
result appropriate to the change.

Reuse reproducible staging areas instead of copying entire projects per attempt.
Retain sources, accepted artifacts and required rollback; remove accounted-for
superseded outputs under the project's cleanup rules. Keep game-specific paths,
offsets, versions and trial history in project docs, not universal skill rules.
