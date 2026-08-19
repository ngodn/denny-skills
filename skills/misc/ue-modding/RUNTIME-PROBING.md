Runtime reflection probing for [ue-modding](SKILL.md): how to establish, safely and incrementally, what a shipped Unreal Engine build actually does at runtime versus what static analysis merely suggests it might do.

## Static analysis is a hypothesis, not a fact

`strings` on the shipping executable, plus statically extracted DataTables, gives every *name* that exists in the cooked build: class names, enum values, table fields. It never tells you which of those names are reachable from reflection at runtime, or whether the logic behind a name still does anything in a stripped shipping build. Treat every static conclusion as something a live probe still has to confirm; both "this has no gameplay logic" and "this is the right signal to hook" are the kind of conclusion that has been wrong until measured.

## Build numbered, incremental probes

Rather than one large script, build a numbered sequence of probes where each one's header states what the previous probe established and what this one specifically tests. Record every negative result as load-bearing, a "do not retry" entry, not something you let fall out of memory between sessions. This is the core method that keeps a reverse-engineering effort spanning many sessions from re-litigating the same dead end twice.

## Budget reflection work per frame

Doing a full class, property, or function dump inside a single game-thread call can freeze the game outright. The tell that it's specifically the game thread hanging, not the whole process: audio keeps playing while the game or render thread is stuck. Fix: spread the dump across ticks under a fixed wall-clock budget per tick (a few milliseconds), batch log writes rather than flushing per entry, and drop redundant global sweeps once static analysis has already given you the names to look for.

## Object-array scans are full scans

Enumeration calls that find "every live object of class X" walk the entire live object table. Calling one every tick, or every probe iteration, can hang a real session, especially once many assets are loaded. Resolve the target object once, cache it, and refresh on a slow timer (every second or two) or only when the cached handle goes invalid. Never call a full-scan enumeration in a per-tick or per-poll hot path; this exact mistake tends to recur in both a probe script and a shipped mod's own polling code, and the fix is identical both times.

## Record which class chain each name came from

A reflection dump that spans multiple related classes (an actor and a separate controller object driving it, for instance) must keep the class-chain context attached to each discovered name. Flattening the list, sorting and deduplicating names across chains, loses that context and can send a later search down the wrong chain entirely, costing a full probe generation before the mistake is caught.

## The startup player object may be a placeholder

An object resolved once at process or level start under a name like "the player" can latch onto a lobby or title-screen stand-in actor and never get re-resolved once the real gameplay level loads, silently describing the wrong object for the rest of the session. Either wait for an explicit level-loaded signal before resolving it, or avoid depending on a cached reference across a level transition at all.

## The arity oracle

When a function's parameter count can't be read directly (property enumeration doesn't always work on function objects themselves), call it via reflection with a deliberately implausible number of dummy arguments, large enough that no real function in the game could plausibly match that arity. Argument marshalling happens before the call actually executes, so the framework reports the true expected parameter count in its own "expected N, received M" error, and the call never fires. Using a *plausible* dummy count instead risks accidentally matching a real function's arity and executing it with garbage-typed arguments, which can crash the game.

## Arguments are marshalled without type checking

Getting the argument count right via the arity oracle is necessary but not sufficient. The right count with wrong argument types does not error; it corrupts memory. Get the types right from a real signature, an SDK header dump, not guesswork, before calling anything with side effects.

## Write and flush before a risky call

If a reflected call crashes the process, an unflushed log line gives you nothing to diagnose from afterward. Write and flush the identifying context, "about to call function X with arguments Y", immediately before making any reflected call that might crash, not after the call returns.

## A call that doesn't throw proves nothing

Framework-level "call accepted" (no exception) says nothing about whether a stateful, game-visible effect actually happened. The reliable test is self-verifying: perform the state-changing call, then independently read back a property the call should have affected, rather than trusting the absence of an error or a human watching the screen.

## Validate the measuring instrument itself

Several classes of lost work trace back to a broken *reading*, not a broken effect: a position reading stuck at exactly zero, a query whose control case itself silently failed, a check that was circular by construction. Every verification needs a negative control, a case expected to fail, and if the control doesn't fail as expected, the whole measurement is suspect, not just the positive result.

## Don't generalise a negative result across categories

A finding that one specific mechanism doesn't fire (network-replicated RPCs in an offline session, for example) does not extend to a related-but-distinct mechanism (plain native function hooks, which can fire fine offline). Test each category on its own terms; an over-generalised negative result can redirect hours of work down the wrong path.

See [NATIVE-HOOKING.md](NATIVE-HOOKING.md) for what to do once a reflection-based hook's cost becomes the bottleneck, and [CRASH-SAFETY.md](CRASH-SAFETY.md) for the rules that keep a probe from crashing the game outright.
