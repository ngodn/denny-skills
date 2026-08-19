---
name: testing-hypotheses
description: Discipline for deciding whether an effect is real, for any empirical work, A/B tests, feature search, model work, or a performance claim. Use when the user proposes a filter, rule, or feature and wants to know if it actually works; when a result looks strong on a small or filtered sample; when two candidate rules might be correlated with each other; when a promising result was computed at a coarse resolution or on a training/serving split; or when deciding whether to keep searching a family of approaches or stop.
---

# Testing Hypotheses

State a falsifiable hypothesis, then build and test it for real. A refutation has to come from a run, not a plausibility argument. Arguing an idea away is not the same as testing it, and it leaves the door open for someone to re-propose it later with nothing new.

## Controls, in order

**Permutation control** is the default null-hypothesis check for "does this filter or feature actually discriminate." Shuffle the label or the signal, recompute the statistic, and compare the real result against the permuted distribution. Nothing gets believed before it clears this.

**A second, independent control** (random-skip, or a held-out split) catches a filter that only "wins" because it silently reduces the sample size or cherry-picks a subpopulation, rather than adding real information. A result can pass the permutation control and still fail this one: a filter can look like it's finding signal when it's really just betting on fewer, easier cases.

## Validate at the largest available sample

A permutation control can itself produce a false positive at small n. The concrete shape of this failure: a result that looks strong at a few hundred events goes flat once checked against tens of thousands. Don't trust a result until it's been checked at the largest sample you can actually get, not the sample that happened to be convenient.

## Traps that produce a false "it works"

| Trap | What happens |
|---|---|
| Small-sample-on-a-favourable-subset | A filter looks good on a small, favourable slice of the data. At full scale the result can **invert**: the case that looked safe turns out to be the worse one. |
| Confounded gates | A rule looks real purely because it correlates with, and proxies for, a different rule you already adopted. It carries no independent information. |
| Train/serve skew | A feature is computed differently, or over different data availability, at training time versus live inference. This is its own class of bug, distinct from a modelling mistake. Check for it explicitly; don't assume a correct offline result survives contact with live serving. |
| Coarse-timing artifact | A promising result computed at a coarse time resolution can be an artifact of that resolution rather than a real effect. Re-validate any aggregate-level finding at the resolution the system actually operates at before adopting it. |

## Predictability is not usefulness

Strong discriminative power (a good AUC, a clean separation) can still lose on the metric that actually matters once costs are accounted for. Treat "the model can tell these apart" and "this makes more money / breaks fewer things" as two separate questions, and answer both before adopting anything.

## Test the tail, not just the mean

An effect can be null on average and still be a strong predictor of the tail: the rare blowup case, the outlier failure. Check tail behavior specifically, not just an averaged win rate or mean error. A tail effect may already be captured by an existing control, which is itself a useful thing to establish before claiming a new one.

## Feature versus gate

Distinguish a **feature** (something a model may learn from, weighted alongside everything else) from a **gate** (a hard rule that vetoes or forces a decision on its own). An idea that fails as a standalone gate can still ship as a model feature, and the reverse also happens: something real as a decision trigger even though it has no value as a general-purpose predictor. Don't discard an idea just because it failed in the wrong role. Retest it in the other one before writing it off entirely.

## Verdict vocabulary

Apply one of these to every finding, consistently, and record the reason:

| Verdict | Meaning |
|---|---|
| **Adopted** | Cleared the controls, shipped. |
| **Refuted** | Tested, failed a specific control at a specific n or threshold. Record which control, and the number. |
| **Marginal** | Real but too small to act on alone. |
| **Inconclusive** | The test couldn't distinguish signal from noise at the sample available. Not the same as refuted; leave it open rather than closing it on a shrug. |
| **Not-adopted** | Tested positive but not yet shipped, for reasons outside the statistics (priority, risk, scope). |
| **Irreducible** | Structurally can't be fixed at this decision point, after real attempts. |

A closed verdict (adopted, refuted, irreducible) gets an explicit **do-not-re-test** note stating the reason, so nobody spends a session re-deriving a result that already exists. Call the Skill tool with "research-log" for where these verdicts get written down so they survive a context reset.

## Knowing when to stop

When every variant within a family of approaches has been tried and only marginal or redundant results remain, mark the family **saturated** and switch to a different lever rather than continuing to search inside it. A rigorous, controlled absence of an effect is a positive result. Write it up as one, not as an unfinished search.
