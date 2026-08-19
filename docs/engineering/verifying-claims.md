## What it does

`verifying-claims` is a checklist against stating a conclusion you haven't gone and looked at. It covers the ordinary places a conclusion sneaks past verification: trusting an internal log over the external system of record, trusting process status over the process's own output, trusting "no error thrown" as proof a state actually changed, trusting a number from memory instead of a fetched source.

The defining constraint is that plausible is not proof, and the fix is always the same shape: find the thing that would actually show the answer, and look at it. A vendor's own success message, a container marked "running", an SDK call that returned cleanly, none of these are that thing.

## When to reach for it

Type `/verifying-claims`, or the agent reaches for it automatically when the task fits.

| The situation | Reach for |
|---|---|
| About to state that a deploy, restart, or vendor call succeeded | `verifying-claims` |
| A test needs to confirm a state change actually happened | `verifying-claims`, for the self-verifying-test rule |
| A number or competitive claim is going into a document | `verifying-claims`'s two-check rule |
| An external API or SDK's behavior needs describing | `verifying-claims`, before writing it from memory |
| A process looks stuck and you need to know if it's actually hung | `verifying-claims`'s wedged-process section |
| The result itself, not just the claim about it, needs statistical scrutiny | [testing-hypotheses](../engineering/testing-hypotheses.md) |

## Weak signals versus proof

The skill's core move is a table of things that look like evidence and aren't: `docker ps` showing a container running, an SDK returning success, an exception not being thrown, flat CPU usage on a process. Each has a specific replacement: the service's own logs, the vendor's backend log or the artifact it should have produced, an independent read-back of the property the call should have changed, a symbolized stack trace. None of the weak signals are wrong to look at, they just don't answer the question being asked of them.

## The two-check rule for anything written down

Before a number or a competitive claim goes into a document, it has to clear two checks: does it match what the code or system actually does right now, with any roadmap dependency stated rather than folded into a present-tense claim, and is there a live, citable source recorded next to it. A claim built from general knowledge of how similar things tend to work doesn't clear the second check, no matter how confident it sounds. One banned pattern falls out of this directly: a hedge range in place of a single sourced figure, because a range lets a reader compute a worst case that can contradict your own stated conclusion.

## Common questions

**The deploy succeeded and the service shows as running. Isn't that enough?**

No. A container reporting "Up" says the container started, not that the process inside is doing its job. Read the service's own logs for every affected component. This is the most common way a broken deploy gets reported as a good one.

**The call returned without throwing. Doesn't that prove it worked?**

No, and this one is expensive. A call can be accepted, marshalled, and executed while the state it was supposed to change never moves. The fix is a self-verifying test: make the change, then independently read back a property that change should have affected. Absence of an error is not evidence of an effect.

**How do I know my measurement is measuring anything?**

Run a control case you expect to fail. If it does not fail, the instrument is broken and every reading through it is suspect. Several rounds of work have been lost to a reading that looked plausible and was structurally impossible, a position pinned at exactly zero, a query whose control row also failed, a check that was circular.

**Two sources disagree about what happened. Which one wins?**

The external system of record, every time. An internal journal or log is written by the same code whose behaviour is in question, and it mis-buckets under exactly the conditions you are investigating. Cross-check by id rather than by summary.

**The tool printed a success message. Why would I doubt it?**

Because a real one has silently downloaded the wrong architecture, failed to move files into the directory that mattered, and still reported success. Inspect the artifact it claims to have produced.

## It's working if

- A "the deploy succeeded" or "the service is healthy" claim comes with a log line, not a process-status screenshot.
- A test that asserts a state change reads the changed property back independently, rather than asserting on the absence of an exception.
- Every number in a document you can point at has a source next to it, and no hedge ranges sit where a single figure belongs.
- A "this API does X" claim traces to a fetched response or a doc link, not to memory.

## Where it fits

`verifying-claims` is a **reach-for-it-anytime standalone**, most often pulled in mid-task rather than run as its own session. It pairs naturally with [diagnosing-bugs](../engineering/diagnosing-bugs.md), whose feedback-loop discipline is itself an application of "don't trust it until you can show it", and with [code-review](../engineering/code-review.md), where its two-check rule applies to any number or claim landing in the diff. For deciding whether an *effect*, not just a single fact, is real, use [testing-hypotheses](../engineering/testing-hypotheses.md) instead. For the whole map, [ask-denny](../engineering/ask-denny.md) routes you.
