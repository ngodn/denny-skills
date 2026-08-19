Native inline hooking for [ue-modding](SKILL.md): moving per-frame work out of a scripting framework's reflection hooks and into a native DLL, once hook cost itself becomes the constraint.

## Hook cost is global, not per-hook

Installing a hook through a scripting framework's own hook API, on any function, switches on interception of the engine's entire function-dispatch path, not just the one function you hooked. The overhead is global and roughly constant, not proportional to hook count or to how often a given hook fires. Measured in one project: 9 hooks installed this way froze the loading screen; 48 hooks dropped the game to 1-3 fps. A single hook installed the same way would have cost about the same as either. Counting how often a hook fires tells you nothing about whether it's cheap; the cost is paid on every function call in the whole game, hooked or not, the moment any hook exists. Measure actual cost (frame time, load time) directly, never infer it from fire count. This is the reason to move genuinely per-frame work into a native inline hook instead.

## Centralise every version-specific address

Keep every game-version-specific address in one file, expressed as an RVA (an offset from the module's preferred load base, logged separately if the executable doesn't load at that base), with a short expected prologue byte sequence recorded alongside each address. Before every patch, re-check the live bytes at that address against the recorded prologue. A mismatch means the game updated: skip the hook rather than patch blindly, which would corrupt memory in an unpredictable way. Never loosen the check to make a hook "still work" after a mismatch; re-derive the address instead.

## Re-deriving an address after a game update

1. Launch the updated game once with the reflection framework's own logging layer active.
2. Read the target function's resolved address straight out of the framework's startup log; most reflection frameworks log the address of key dispatch functions on every boot.
3. Subtract the module's load base to get the new RVA.
4. Re-verify the expected prologue bytes at the new address with a disassembler.
5. Update the offset table and rebuild.

A hook whose feature has been superseded can be left un-re-derived deliberately, as long as hook-install order is structured so a stale, optional address can never block a required primary hook from installing.

## Winning the write race against a self-reasserting engine

An engine subsystem that rewrites its own driving state every tick, an animation graph re-evaluating its own variables every frame, for example, will silently overwrite a value set from an independent timer or thread, because that external write lands before the subsystem's own rewrite runs. The fix is to hook the dispatch function itself and re-apply the desired write *after* calling through to the original implementation, so the mod's write is provably the last one applied each frame, deterministically, rather than racing the engine's own tick order.

## DllMain and thread discipline

Do no real initialisation inside a DLL's entry point on process-attach. It runs under the OS loader lock, where most interesting APIs, including anything allocation-heavy or synchronising, can deadlock. Spawn a plain worker thread from the entry point and do all real setup there; disable further thread-attach/detach notifications for the module once running, since they're not needed after startup.

Keep every engine-memory write on the game thread, and only there, inside the hook's own tick. Any other thread in the mod (an IPC/command-polling thread, for instance) should only ever flip lightweight scalar flags, an interlocked exchange on a mode or teardown flag, never write engine memory directly.

Order teardown explicitly and deliberately: restore each driven channel, restore camera or view-target state, zero shared state, then null the hook's own gate flag last. Nulling the gate is what stops the hook from ticking again, so it has to be the final step; reversed or interrupted teardown order is a direct, reproducible cause of stuck state, a frozen pose or an orphaned camera view that outlives the mod's own cleanup code.

## A stripped function can still be a command channel

A shipping build can compile out a console-dispatchable function's entire body while the "exec thunk" the game's own console parser calls into survives stripping intact. Hooking that surviving thunk and reading the still-unparsed arguments directly off the calling stack frame gives a free, already-wired command channel into native code, with no new console-command registration required. The general lesson: a stripped or hollowed-out function can still be a legitimate injection point if its calling convention and dispatch path survive stripping, even when its body doesn't.
