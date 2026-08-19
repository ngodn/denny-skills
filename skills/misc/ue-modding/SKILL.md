---
name: ue-modding
description: Modding and reverse-engineering a shipped, cooked Unreal Engine game with no editor or engine source access. Use when the user is extracting or patching pak/IoStore assets, authoring a UE4SS or LogicMods mod, editing a cooked DataTable, cross-compiling a native mod DLL, probing a game's runtime reflection surface, installing a native inline hook, or debugging a crash in a running game mod.
---

# UE Modding

Reverse-engineering and modding a shipped Unreal Engine game from outside the engine: no editor, no engine source, usually no debug symbols. The one constraint that shapes everything here: nothing is documented, so every technique substitutes some form of measurement, a runtime probe, a byte-identical round trip, a live prologue check, for the documentation you don't have. Treat a static conclusion (from strings, from extracted assets) as a hypothesis until a live check confirms it.

## Toolchain and mod anatomy

Packaging is pak/IoStore (`.utoc`/`.ucas`/`.pak`); check whether the title uses AES encryption before attempting extraction. Three places a mod can live, ranked by capability:

| Location | Capability |
|---|---|
| `Content/Paks/~mods/` | Static asset/DataTable override only, no runtime logic |
| `Content/Paks/LogicMods/` | Cooked Blueprint injection via the mod loader, needs a matching editor build to author |
| `Binaries/<Platform>/ue4ss/Mods/` | Lua/C++ with full runtime reflection and hooks |

**Extraction recipe and its single biggest gotcha**: symlink `pakchunkN.{utoc,ucas,pak}` *and* `global.{utoc,ucas}` into one directory before converting an asset. A missing global container makes every conversion fail, with an error that doesn't obviously point at the missing symlink.

**Mappings** (`.usmap`) are needed to resolve property names in a stripped cook. Source one from a community mapping repo for that title, or dump one live from the running game via the reflection framework's own mapping-generation call.

**Mod anatomy**: an `enabled.txt` marker file in the mod's folder is enough to load it without touching the framework's own mod list. `scripts/main.lua` (or equivalent) is the entry point. A generated SDK dump, a full header dump of every reflected class, enum, and function, is the primary reference for "does X exist" instead of guessing from memory.

**No hot reload.** Reloading scripts live can crash the game outright. Design the dev loop, and the time budget, around edit-then-restart rather than assuming safe hot reload; verify this per engine/game rather than assuming it.

## Patching cooked DataTables without an editor

Patch cooked `.uasset` DataTables directly through a binary-asset library, and keep the JSON round trip byte-identical as the correctness gate before trusting any edit: load, re-export unchanged, diff against the original bytes. When attaching new behaviour to a table, prefer attaching it to a row *already referenced* by the target actor over adding and attaching a new row, whenever the attach step itself can't be independently verified (a read-back API that's broken or unreliable in that framework build).

## Load order is not simple priority

A naming convention meant to sort a mod's pak last (a prefix chosen to alphabetize after everything else) is not a safe assumption about actual load order. Other installed mods editing the same tables can still win. Plan to merge with conflicting mods rather than rely on out-ordering them.

## Cross-compiling a native mod DLL from Linux

Two routes, pick by ABI requirement:

| Route | When |
|---|---|
| `zig cc -target x86_64-windows-gnu` | A plain C DLL exporting simple entry points; no MSVC toolchain or engine headers needed |
| `clang-cl` in MSVC-ABI mode, against a fetched Windows SDK | Calling convention or C++ standard-library ABI compatibility with the engine or host process is required |

## Reimplementing an unsupported binary sub-format

When a community parsing library handles an asset's property header but not a trailing binary block (compressed animation data is a common case), read the actual engine source for the exact version's serializer and reimplement the read (and, carefully, the write) side field by field, citing file and line as you go. Validate with three checks, in order: a byte-identical round trip (load, re-save unchanged, diff), the smallest possible single-field edit so the resulting diff is mechanically checkable, and decode-then-re-encode equality for any codec involved. Never print plausible-looking output on a misparse; fail loudly on a bounds or sanity check instead.

## Framework architecture

Split logic by where it can afford to run:

- **Logic belongs in the compiled core.** State machines, timers, and physics math live in native code, ticking off the native layer's own hook (see [NATIVE-HOOKING.md](NATIVE-HOOKING.md)).
- **The scripting layer is reflection and content only.** Its job is resolving handles, offsets, and names via reflection, easy there, hard to reimplement in native code, plus small declarative content.
- **Dev tools are triggers, not logic.** Anything under a dev-tools directory pokes the running system; it never contains behaviour the shipped mod depends on.

Why: hook cost through a scripting framework's hook API is global and roughly constant regardless of hook count (see [NATIVE-HOOKING.md](NATIVE-HOOKING.md)), so anything that must run every frame has to live in the cheap native path. The scripting layer earns its keep purely because runtime reflection is dramatically easier there than reimplementing a reflection walker in native code.

**Boot completely passive.** Hold no state and do no work until explicitly armed. This makes an early boot crash trivially attributable: mod present, game still crashes on boot before being armed, therefore not the mod.

**Communicate between layers over a polled file protocol** when the framework's own event or keybind API is unreliable under a compatibility layer (Proton/Wine, for instance): each control surface is a small text file one side writes and the other polls.

## Going deeper

- **Runtime probing** (incremental probes, reflection budgeting, the arity oracle, argument marshalling risk): see [RUNTIME-PROBING.md](RUNTIME-PROBING.md).
- **Native inline hooking** (hook cost, offset re-derivation, write-race, thread discipline): see [NATIVE-HOOKING.md](NATIVE-HOOKING.md).
- **Crash-safety rules** for any code touching live engine state: see [CRASH-SAFETY.md](CRASH-SAFETY.md).
- **Animation and skeleton engineering** (bone registries, pose forcing, spring-bone physics, procedural motion): see [ANIMATION.md](ANIMATION.md).
