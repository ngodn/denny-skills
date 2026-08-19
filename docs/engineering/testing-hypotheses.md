## What it does

`testing-hypotheses` is the discipline for deciding whether an effect is real, for any empirical claim: an A/B test, a candidate feature, a performance improvement, a proposed rule. The defining constraint is that a refutation has to come from a run, not from arguing the idea away, and that a result clearing one statistical control is not the same as it clearing enough of them.

It supplies a verdict vocabulary, applied consistently, so a pile of individual experiments turns into a scannable ledger instead of a set of one-off conclusions that live only in whoever ran them. The vocabulary is meant to be written down: call the Skill tool with `research-log` for where the verdicts actually get recorded so they survive a context reset.

## When to reach for it

Type `/testing-hypotheses`, or the agent reaches for it automatically when the task fits.

| The situation | Reach for |
|---|---|
| A proposed filter, rule, or feature needs to be tested, not argued about | `testing-hypotheses` |
| A result looks strong on a small or already-filtered sample | `testing-hypotheses`, before it's trusted at scale |
| Two candidate rules might be correlated with each other | `testing-hypotheses`'s confounded-gates trap |
| An offline result needs to be checked against how it will actually run in production | `testing-hypotheses`'s train/serve skew and coarse-timing traps |
| The verdict on a tested idea needs to be written down for future sessions | [research-log](../productivity/research-log.md) |
| The claim is a single fact, not an effect to be validated statistically | [verifying-claims](../engineering/verifying-claims.md) |

## Controls, and why one isn't enough

A permutation control, shuffling the label and comparing the real result to the permuted distribution, is the default null check and nothing gets believed before it clears one. But a permutation control can itself produce a false positive at small n, so a second, independent control (a random-skip or a held-out split) exists specifically to catch a filter that only "wins" because it silently shrank the sample or cherry-picked a subpopulation. A result can pass the first control and fail the second, and both have to be checked at the largest sample actually available before either verdict is trusted.

## The verdict vocabulary

Six words, applied consistently, each with a recorded reason: **adopted**, **refuted**, **marginal**, **inconclusive**, **not-adopted** (tested positive but not shipped, for non-statistical reasons), and **irreducible** (structurally can't be fixed at this decision point). A closed verdict, adopted, refuted, or irreducible, carries an explicit do-not-re-test note. When a whole family of approaches has been exhausted with only marginal results left, mark it **saturated** rather than continuing to hunt inside it. A rigorous, controlled absence of an effect is treated as a positive result in its own right, worth writing up, not an unfinished search.

## Common questions

**My permutation control passed. Am I done?**

No. A permutation control checks whether the effect beats noise. It does not check whether the effect is just your filter quietly discarding part of the sample. Run a second, independent control, a random-skip or a holdout, that specifically tests that. A finding that passes the first and fails the second is a real and common outcome.

**It works beautifully on the subset I care about. What's wrong with that?**

That is the trap this skill exists for. A result derived from a small favourable slice can not only weaken at scale, it can invert, so the case that looked safe turns out to be the worse one. Confirm at the largest sample available before building anything on it.

**The effect was strong at a few hundred observations and gone at tens of thousands. Which do I believe?**

The larger one, and record the smaller one as refuted with the sample sizes attached. A permutation control can itself produce a false positive at small n, which is why validating at scale is a separate step rather than a formality.

**My model discriminates well but the outcome hasn't improved. Is the model wrong?**

Not necessarily. Predictability and usefulness are different properties, and something can score strongly on the first while losing on the metric that actually matters. It is also worth checking whether the effect lives in the tail rather than the mean, and whether an existing control already captures it.

**How do I know when to stop looking?**

When a whole family of approaches has been tried and only marginal or redundant results remain, record the family as saturated and change levers. A rigorously established absence is a result, not a failure to find one, and writing it up is what stops the next session repeating it.

## It's working if

- Every tested idea in the project has one of the six verdict words attached, not a vague "didn't really work out".
- A result that looked good on a small sample gets re-checked at the largest sample available before it's adopted.
- A closed, refuted idea has a do-not-re-test note that stops it from being re-proposed next session.
- An idea that failed as a hard gate gets a second look as a model feature (or vice versa) before it's discarded outright.

## Where it fits

`testing-hypotheses` is a **reach-for-it-anytime standalone**, most useful wherever empirical claims get made: feature search, A/B tests, performance work, model iteration. Its tightest neighbor is [research-log](../productivity/research-log.md), which is where its verdicts and do-not-re-test notes actually live once a project spans more than one session. [verifying-claims](../engineering/verifying-claims.md) sits beside it for the narrower question of a single fact rather than a statistical effect. For the whole map, [ask-denny](../engineering/ask-denny.md) routes you.
