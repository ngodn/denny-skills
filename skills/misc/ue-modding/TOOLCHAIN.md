# Extraction, authoring and packaging

Use this branch of [ue-modding](SKILL.md) when setting up tools or changing
assets. Prefer the project's verified pipeline and adapt the failed stage.

## Establish the tool contract

Record the source game and target game separately for a port. Inspect actual
container headers and build metadata; a `.pak` extension alone does not identify
Unreal's format. Record the required engine/custom versions, target platform,
mapping file, loader fork, SDK and compiler ABI.

Check installed editors, project scripts, tool manifests and local patches
before downloading or rebuilding tools. Verify the relevant language manager
and runtime versions. Host Python, Blender's Python and Unreal's Python can be
different environments. Use the one declared by the working recipe.

Upstream source and game-community guides supply candidate workflows. Check
their supported game/build and OS. For example, the Stellar Blade modding team's
[tool guide](https://github.com/Stellar-Blade-Modding-Team/Stellar-Blade-Modding-Guide/wiki/Tools-%26-Plugins)
lists Blender import/export addons, Unreal 4.26 and game-specific exporter
fixes. Its [model import guide](https://github.com/Stellar-Blade-Modding-Team/Stellar-Blade-Modding-Guide/wiki/Custom-Model-Import-Guide)
provides an authoring path. These are reasons to investigate that toolchain,
not to assume every listed plugin/version is already installed or validated.

## CUE4Parse and game-specific patches

[CUE4Parse](https://github.com/FabianFG/CUE4Parse) is a parsing library with
conversion support, not a universal cooked-asset writer. Establish which wrapper
or CLI the project uses and inspect its help/source before constructing commands.

Preserve the checkout revision, submodules, working diff, dependency pins and
built binary identity. Replacing a patched checkout with an upstream package can
silently remove required game support. Prefer a separate checkout for comparisons.

Mount the complete required input set. For IoStore, provide companion container
and bulk files, referenced base packages and global metadata where that format
requires it. Configure the verified game/version selector, mappings and authorized
encryption keys if needed. Missing imports, an unresolved skeleton or an empty
export may indicate incomplete reader inputs rather than broken source assets.

Before bulk extraction, decode one representative mesh with its skeleton,
materials and textures, plus an animation if relevant. Verify nonempty finite
geometry, hierarchy, reference transforms and dependency resolution. Inspect the
result. A zero exit code or a created file alone does not prove successful decode.

When parsing fails, locate the failing asset, field and byte offset. Distinguish
decompression, mapping, custom-version, dependency and serializer failures.
Compare the relevant engine version's serializer or the game's verified format
before patching. Keep the change narrowly scoped and retain a regression sample.
Require bounds checks and alignment to subsequent fields; validate decoded values
against an independent source. An unchanged binary roundtrip applies to writers,
not to an extractor that intentionally exports a different representation.

## Blender import, fit and export

Choose a supported route such as UEFormat, PSK/PSA, glTF, FBX or the project's
custom schema. Verify the addon's exact Blender and asset-format support. For
example, [Blender Uasset Addon](https://github.com/matyalatte/Blender-Uasset-Addon)
documents different import and injection support by engine/game version. Its
ability to import an asset is not proof that it can write that asset back.

Retain original bone names, parents, local bind transforms, weights, morphs,
material sections and UVs separately from the imported scene. Check units,
handedness, triangle winding and bone axes with a known reference. A plausible
neutral pose can conceal an incorrect bind transform that fails during movement.

For clothing, use the accepted target body and earlier successful fitting method.
Fit the whole assembly, transfer weights deliberately and preserve seam/trim
relationships. Inspect neutral, representative motion and supported body-shape
extremes. A global scale or shrinkwrap alone does not establish a usable fit.
Prioritize visible defects; respect the user's tolerance for minor clipping.

Use Blender's own Python runtime for `bpy` scripts, or a verified compatible
`bpy` environment. In unattended commands, set a nonzero `--python-exit-code`
and inspect both the process result and the output. Argument order matters in
the [Blender CLI](https://docs.blender.org/manual/en/3.6/advanced/command_line/arguments.html);
check the installed version's help before adapting a recipe.

## Unreal editor and cook

Use a compatible authoring project even when the original game project is absent.
Choose the editor/plugin versions from game-specific evidence and the existing
recipe. Engine source can clarify serialization and permit custom commandlets;
matching a public engine version does not prove identity with a game's fork.

Reconstruct or import editable assets when needed. Epic's
[cooked-content documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-cooked-content-in-the-unreal-engine?application_version=5.6)
describes limited, read-only cooked-content use in the editor. It does not promise
recovery of original material graphs or Blueprint authoring data.

Prove import and fresh-process reload before a large cook. Validate the target
skeleton, morphs, sections, materials, physics/cloth bindings and animation
references. Editor stand-ins can resolve authoring dependencies, but exclude them
from shipping when the accepted runtime dependency must remain in use.

Cook for the game's platform and shader formats. A Linux editor starting or
saving assets does not prove Windows shader compilation support. Verify the
actual target toolchain, or use the project's established Windows cook environment.
An asset-only cooker that preserves existing cooked materials has a narrower
capability than a full material/shader cook. Inspect receipts and outputs to tell
which path ran. Scope cook workarounds to the reproduced failure.

## Package and verify

Use a packer/converter verified for the target container revision. Check mount
paths, package/object names, IDs, imports and dependencies. Preserve the game's
required companion files. Source-game shaders, rigs and plugin classes do not
automatically become valid target-game assets during conversion.

Confirm which package wins when multiple mods override the same asset. File
names alone do not establish effective load order. Use the loader's documented
layout and observed mounted assets rather than treating `~mods`, `LogicMods` or
an enable marker as universal installation rules.

Read the finished package back against the required base containers. Compare
intended payload changes and verify preservation of accepted dependencies.
Where the format allows it, unchanged roundtrips catch writer/converter defects.
Verify shader data when adding materials, and cooked bindings when adding cloth.

Install the concrete candidate through the project's established process, then
check the game behaviors affected by the change. Record authored, cooked,
packaged, installed and user-accepted states separately. Neither a Blender
preview nor a successful cook closes the runtime checks.
