---
name: research-log
description: The two-document pattern for a research or investigation project that runs across many sessions and context resets, so a settled question never gets re-argued from scratch. Use when a research, reverse-engineering, or experimentation effort will span multiple sessions, when the user asks to set up a status doc or research index, when a research-heavy session is ending and its findings need to survive it, or when picking a research project back up after a context reset.
---

# Research Log

The single biggest time sink across a long research project is re-proposing an approach that was already eliminated, because the elimination lived only in a previous session's transcript. This skill is two documents plus one rule: nothing substantive is allowed to exist only in a chat transcript. Every finding that matters gets a file, and every file that matters gets a row in the index.

## The two documents

| Document | Read when | Carries |
|---|---|---|
| **Status doc** | You want to know where the project stands right now | Current state, settled architecture, per-capability proof tables, what's next |
| **Index** (the anti-drift map) | First thing after every context reset | Every research artifact, the hard-won findings, the banned/dead-end list |

They are not interchangeable. The status doc says where things currently stand. The index says what must never be re-derived. Read the index first: it is what stops a context reset from re-litigating settled ground.

## The status doc

- A dated, session-numbered header at the top ("Status as of session 14, 2026-08-12"), updated every session.
- A settled **architecture** or **approach** section: the current design, stated as fact, not as history.
- Per-capability tables of what is **proven** versus **still untested**: one row per capability, a status column, an evidence column (which test, which measurement, which session).
- An explicit **what's next** pointer at the end. Never leave the reader to infer direction from the rest of the doc.
- Superseded sections stay below, marked **SUPERSEDED**, rather than being deleted. History is data the next session needs, not clutter to clean up.

## The index (read first after every reset)

- One row per substantive research artifact: a one-line takeaway and a path. Nothing else.
- A standing **"hard-won findings, never re-litigate"** section at the top, listing conclusions that are settled and must not be re-derived.
- A standing **"banned, crashes or dead ends"** list, so a fresh session doesn't spend a cycle re-discovering something that already broke things once.
- Any agent or subagent research output gets saved in full under a fixed folder and given a row here before the session ends. If it's not indexed, it did not happen, from the next session's point of view.

See [TEMPLATES.md](TEMPLATES.md) for concrete skeletons of both documents.

## Refuted approaches are first-class content

A refuted approach sits next to what works, not buried in git history or left implicit in a chat transcript. Each one gets: what was tried, the one-line reason it failed, and what established that (which test, which control, which measurement, which session). Write it right beside the "what works" table so both are visible in the same read. A reader scanning only the wins will re-propose the losses.

Knowing when to stop hunting an entire family of approaches is itself a finding. Mark it saturated, name the fallback direction, and record it in the index's "never re-litigate" section, so nobody reopens the hunt next session on a hunch. Call the Skill tool with "testing-hypotheses" for the verdict vocabulary (adopted, refuted, marginal, inconclusive, not-adopted, irreducible) that this section should use.

## Reference material gets committed

Anything cloned or downloaded during research (a reference repo, a spec, a sample dataset) goes into the project's own tree, never left as a throwaway local clone somewhere else. A future session, possibly a different agent, has to be able to re-read the exact material without re-finding or re-cloning it.

## Distilled notes sit next to raw dumps

Keep the raw output (probe logs, full agent transcripts, benchmark dumps) for re-verification. Write a short, hand-written distillation next to it, and read the distillation day to day. The raw data exists to be re-checked when something is in doubt, not to be re-read as routine.

## Milestone docs for depth

Once a project runs long enough to have phases, number them (`docs/M1.md`, `M2.md`, ...) and keep the status doc as the entry point, with milestone docs as depth-on-demand. State explicitly, in the status doc, that older milestone docs go stale after an architecture pivot: don't trust one without cross-checking the current status doc first. An architecture pivot that isn't cross-checked against every open milestone doc is a drift bug waiting to bite the next session.

## Session handoff

At the end of a research-heavy session, write down: what is proven, what is still open, the exact next two or three steps in order, and where the raw data lives. This is what lets the next session start working instead of re-deriving direction from a transcript it may not even have access to.

## Wire it in, or it silently stops mattering

A preference or a settled finding that is written down but not listed somewhere the next session actually loads (an index row, a memory file that is itself indexed) will drift back within a few sessions. Writing something down once is not the same as it being read. The index line matters as much as the file it points to. A finding with no row is a finding nobody will find.
