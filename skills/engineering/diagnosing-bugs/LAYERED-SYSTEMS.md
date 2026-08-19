# Layered systems

Detail behind the layered-systems note in the main skill: how to walk a fault across independent layers, and the extra discipline a live system in active use demands.

## Walk the layers in order, live

When a fault could be in any of several independent layers (a driver, a service, a container, the app on top), verify each layer in order with a real probe, not a guess. Don't skip a layer because it worked last time: which layer is actually broken can move between incidents. A worked example, checked live in order:

1. Is the process actually running?
2. Are the low-level events reaching the device (a custom probe beats trusting an OS control panel, which can fail to show this class of device at all)?
3. Is a second, unwanted instance stealing the input (check an identifying id in the device list)?
4. Does the downstream consumer see the device at all?
5. Did the device exist before the consumer started (hotplug detection is unreliable in some setups)?
6. Does focus actually sit where you think it does?
7. Does the runtime underneath actually deliver the input (verify with a poller run inside that runtime, not assumed from outside it)?

Fix only the first failing layer, then re-verify from the top. Don't assume a fix at layer 2 cascades to fix what looked broken at layer 5; go back and check.

## One variable at a time, on a live system

Change one thing, then confirm the change actually took effect against the live system's current state before touching the next thing. Stacking unverified fixes on a system someone is actively using produces compounding, hard-to-untangle symptoms, and by the third change nobody, including you, can say which one did what. State what you changed and why before the next change, especially when a fix requires killing or restarting something the user depends on.

## Same bug or new bug: use a stable signal

A change that moves the symptom doesn't by itself tell you whether you fixed the bug or uncovered a different one. Use a signal that stays meaningful across a real fix: a crash offset that moves after a swap proves the swap took effect; a crash at the same relative offset afterward means the cause sits upstream of what was swapped, not inside it. Don't conclude "different bug" just because the surface symptom changed.

## A vendor's success message is not evidence

A UI reporting success, an install wizard's checkmark, a deploy tool's green output: none of it proves the underlying operation did what it claims. Read the actual backend log. Inspect the artifact directly (file type, binary architecture, directory contents) rather than trusting the message that claims it's there and correct.

## Spinning, idle, and blocked look identical from outside

A process pegged at 0% CPU could be idle, could be deadlocked, or could be correctly blocked on a syscall waiting for legitimate work. CPU usage alone can't tell them apart. A symbolized native stack trace can (`eu-stack`, escalated with `pkexec` for a privileged process). Don't conclude "hung" from a flat CPU graph.

## Confirm the thing you think restarted, actually restarted

"I restarted it and it's still broken" often means the visible frontend restarted while a stale backend process is still squatting the port it needs. Every fresh start then fails to bind and dies silently, and the frontend looks fine because it never touches the part that's actually down. Check for a leftover process (the port's listener, or a journal line noting a stale PID that failed to die on signal) before trusting that a restart happened at the layer that matters.

## Check whether the thing already wraps itself

Before forcing a compatibility layer or runtime onto something, check whether it already invokes that layer internally. Something that already runs its own compatibility wrapper, forced into a second one from outside, is double-wrapped, and double-wrapping is its own failure mode, independent of whatever the original bug was.
