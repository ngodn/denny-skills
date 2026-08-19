---
name: verifying-claims
description: Verification discipline for any conclusion about system state, a vendor call's outcome, or a fact going into a document. Use when the user is about to state that something succeeded, is healthy, or changed state; when a deploy or restart just happened and health needs checking; when a number or competitive claim is about to go into a doc; when an external API or SDK's behavior needs to be asserted; when a live check and a computed metric disagree; or when diagnosing whether a process is wedged or just slow.
---

# Verifying Claims

Do not state a conclusion until you can show it. Plausible is not proof, and the gap between the two is where most wrong conclusions live.

## Find the ground-truth source first

Before concluding anything from a log, journal, or internal record, identify which source is authoritative. An internal journal or application log can mis-bucket events; the external system of record (the exchange, the payment processor, the vendor's own account history) is ground truth. Cross-check by id, never conclude from the internal record alone.

## Weak signals that get mistaken for proof

| You want to know | Weak signal (not proof) | Actual proof |
|---|---|---|
| Is the service healthy after a deploy or restart | `docker ps` / systemd showing "active (running)" | The service's own logs, checked for every affected component |
| Did the vendor call succeed | The SDK or API returning a success response | The vendor's own backend log, or the artifact the call was supposed to produce |
| Did the state actually change | No exception was thrown | Independently reading back the property the call should have affected |
| Is a process wedged or correctly waiting | Flat CPU usage over a few seconds | A symbolized native stack trace |

"Up" and "running" describe the container or the process, not the thing running inside it. Read the logs.

## Make the test self-verifying

"No error thrown" proves nothing about a state change. A call can return cleanly and still have done nothing. Perform the change, then independently read back a property it should have affected, rather than trusting the absence of an exception. If the read-back can't be done independently of the code path that made the change, the test isn't verifying anything.

## Validate the instrument before trusting the measurement

Before trusting any measurement, run a control case that is expected to fail. If the control does not fail as expected, the whole measurement is suspect, not just the one result you were checking. A broken reading reported as a real finding (a value stuck at a constant, a query whose control row itself fails, a circular check) costs more time than the control would have.

## Research real behavior, don't assert it from memory

Before stating how an external API or SDK behaves, fetch the actual response or cite the documentation. Describing behavior from memory produces claims that sound plausible and are wrong in a specific, checkable way. This applies to library versions, response shapes, error codes, and rate limits alike.

## When a live check disagrees with a computed metric, the live check wins

If a visual or live inspection contradicts a number the system produced, trust what you saw, not what was computed. Then write the conflict down. If the metric goes untrusted silently, the next person re-trusts it and repeats the mistake; the fix is a recorded note, not a private correction.

## Don't generalize a negative result across categories

One tested category failing does not mean an adjacent, untested category fails too. A finding like "X never works in situation A" is true only for A until it's tested elsewhere; over-generalizing it to "X never works" redirects effort away from something that would have worked fine.

## Two checks before a number or claim goes into a document

Every number or competitive claim needs both of these before it's written down:

1. **Does it match what the code or system actually does**, with any roadmap dependency stated rather than hidden. A capability that's planned but not shipped is a roadmap item, not a present-tense claim.
2. **Is there a live, citable source recorded** (a fetched page, a doc, a repo), rather than a claim from general knowledge of how similar things tend to work.

If a claim came from parametric memory rather than the repo or a fetched source, it does not go in. Keep the source next to the claim (a `## Sources` section works) so the next editor can re-check it instead of re-trusting it.

**Banned pattern:** a hedge range where a single sourced figure belongs. A range lets a reader compute a worst case from it that can contradict your own conclusion. Cite the one number you actually verified instead.

## Diagnosing a wedged process

A symbolized native stack trace is proof of where a process is stuck. Flat CPU usage is not proof of anything by itself: it's also exactly what a process correctly blocked on a syscall looks like. Get the stack trace before concluding the process is hung.
