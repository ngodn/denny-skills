# Native hooks and loader integration

Use this branch of [ue-modding](SKILL.md) when a supported callback cannot meet
the requirement, or a measured bottleneck justifies a native implementation.

## Measure the hook implementation

Hook cost depends on framework version, interception path, callback frequency and
work per callback. Inspect the installed implementation and compare matched
no-hook, minimal-hook and intended-work cases. Record frame/loading times and
variance. Do not infer universal constant overhead or failure from an old game's
hook count. Avoid unverified performance numbers.

UE4SS provides documented [RegisterHook](https://docs.ue4ss.com/dev/lua-api/global-functions/registerhook.html)
and [UnregisterHook](https://docs.ue4ss.com/dev/lua-api/global-functions/unregisterhook.html)
APIs. Their callback timing and available targets have constraints. Match the
installed release/fork rather than assuming the current development docs describe
an older binary. Keep registration identities for cleanup.

## Derive and guard native targets

Record executable identity, module base, RVA, expected instructions and the
calling convention. Establish a target from symbols, reflection resolution or
disassembly plus cross-references. Startup logs are useful when they expose the
specific address; they do not expose every native target.

Before patching, verify live bytes and instruction boundaries and use a hook
implementation that handles relocation/trampolines correctly. Skip an unverified
target on mismatch. Re-derive it for the new build rather than relaxing a check.
Keep optional targets from blocking unrelated validated features.

Choose the actual ownership/evaluation phase. A ProcessEvent post-hook does not
guarantee the last write of a frame, especially with animation workers. Establish
ordering and synchronization or use a supported input path. Confirm that a hook
preserves original behavior when its feature is disabled.

## ABI, initialization and unload

Build against the installed loader's SDK/ABI. A plain C export boundary and a
C++ interface crossing MSVC STL/class layouts have different requirements.
Verify compiler, runtime linkage and dependencies from the project's working
recipe and the loader's [C++ guide](https://docs.ue4ss.com/dev/guides/creating-a-c%2B%2B-mod.html).
An arbitrary Windows-targeting compiler is not automatically ABI-compatible.

Keep `DllMain` minimal and prefer the loader's post-load lifecycle entry point
for initialization. Microsoft's [DLL guidance](https://learn.microsoft.com/en-us/windows/win32/Dlls/dynamic-link-library-best-practices)
explains the loader-lock constraints. Spawning a worker inside `DllMain` is not
a universal fix, and waiting for it can deadlock.

Pass IPC requests to the appropriate engine thread through a supported mechanism.
UE4SS's [game-thread API](https://docs.ue4ss.com/dev/lua-api/global-functions/executeingamethread.html)
is one version-dependent option. Synchronize animation/render work separately
where required. Follow [CRASH-SAFETY.md](CRASH-SAFETY.md) for restoration and
unload. Verify callbacks are detached and in-flight calls are finished before
unmapping code. Validate each custom hot-reload contract on the target setup.
