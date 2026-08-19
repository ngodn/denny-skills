## What it does

`research-log` sets up two documents for a research or investigation project that will outlive a single session: a status doc that says where things stand right now, and an index that says what must never be re-derived. The defining constraint is that nothing substantive is allowed to exist only in a chat transcript. A finding either gets a file and a row in the index, or it doesn't count as settled, no matter how thoroughly it was argued through in the conversation that produced it.

It is not a place to log routine progress. It exists because a context reset, or a fresh agent picking up the project three weeks later, cannot see the transcript where an approach got eliminated, only the files. If the elimination isn't written down somewhere the next session actually loads, the next session re-proposes it.

## When to reach for it

Type `/research-log`, or the agent reaches for it automatically when a task fits.

Reach for it as soon as a research or investigation effort looks like it will span more than one session: reverse-engineering a system, an open-ended feature or performance search, anything with a real chance of getting picked up again after a context reset. It's also what a research-heavy session reaches for on its way out, to write the handoff that lets the next session start working instead of re-deriving direction.

| The situation | Reach for |
|---|---|
| Starting a multi-session research or investigation effort | `research-log`, to set up the two documents from the start |
| Picking a research project back up after a context reset | `research-log`'s index, read first, before anything else |
| A research-heavy session is ending | `research-log`'s session handoff shape |
| Deciding whether a specific result is real | [testing-hypotheses](../engineering/testing-hypotheses.md), which supplies the verdict vocabulary this skill's index entries use |

## Prerequisites

The skill writes into the project's own tree: a status doc (for example `docs/STATUS.md`) and an index (for example `research/INDEX.md`), plus a fixed folder for saved research artifacts. There's no separate setup step; the first session that uses the skill creates them where the project already keeps this kind of note, or in a sensible new location if there is none yet.

## The two documents, and why they're not interchangeable

The status doc is dated and session-numbered at the top, and it answers "where do things stand right now": a settled architecture section, per-capability tables of what's proven versus still untested, and an explicit pointer to what's next. Superseded sections stay in the file, marked superseded, rather than being deleted, because a later session sometimes needs to see what was tried before the pivot.

The index answers a different question: "what must never be re-derived." It's read first, before the status doc, after every context reset, and it carries a standing section of hard-won findings plus a standing list of banned approaches, dead ends, and known crashes. One row per research artifact, a one-line takeaway and a path, nothing more. See [TEMPLATES.md](../../skills/productivity/research-log/TEMPLATES.md) for concrete skeletons of both.

## Refutations sit next to what works

A refuted approach gets the same visibility as an adopted one: what was tried, the one-line reason it failed, and what test or measurement established that. It sits beside the "what works" table, not buried a few commits back in git history, because a reader scanning only the wins will happily re-propose a loss. The same goes for reference material pulled in during research (a cloned repo, a downloaded spec): it gets committed into the project's own tree rather than left as a local clone nobody else can find.

## Common questions

**Isn't this what git history and commit messages are for?**

Git records what changed. It does not record what was tried and rejected, why, or what established it. The approaches that never became a commit are exactly the ones that get re-proposed six weeks later, and they are invisible in history.

**Why two documents instead of one?**

They answer different questions and decay at different rates. The status doc answers "where are we now" and is rewritten constantly. The index answers "what do we already know" and only ever grows. Merging them means the durable findings get churned every time the status changes.

**The agent wrote an excellent analysis in the conversation. Isn't that enough?**

No, and this is the rule that does the most work. Anything substantive gets saved to a file and given a row in the index. Material that exists only in a transcript is material that will be re-derived, because nobody finds it again, including the next agent.

**Do I need this for a two-day investigation?**

No. It earns its keep when the work spans multiple sessions or multiple people, and especially across context resets. Below that it is overhead.

**I wrote the rule down and it got ignored anyway.**

Check whether the file is reachable from whatever gets loaded automatically. A finding recorded in a file that nothing points at is a finding that silently stops being honored. The index line matters as much as the file.

## It's working if

- A fresh session, or a fresh agent, can read the index and know what's settled without asking you.
- Nobody re-proposes an approach that a previous session already refuted.
- The status doc's "what's next" line is never more than one session out of date.
- Raw research output (probe logs, agent reports, benchmark dumps) is on disk somewhere the index points to, not only in a transcript.

## Where it fits

`research-log` is a **reach-for-it-anytime standalone** for any project doing sustained, multi-session investigation, rather than a step in a fixed chain. Its closest neighbor is [testing-hypotheses](../engineering/testing-hypotheses.md): that skill decides whether a given result is real and hands back a verdict, and `research-log` is where that verdict gets written down so it survives a reset. For a one-off writeup of a single question, [research](../engineering/research.md) is the lighter tool: it spins up a background agent to answer one question into one file, without the ongoing status doc and index this skill maintains. When you're unsure which skill fits, [ask-denny](../engineering/ask-denny.md) routes you.
