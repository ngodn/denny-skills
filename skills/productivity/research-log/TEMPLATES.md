# Templates

Skeletons for the two documents. Adapt headings to the project; keep the sections.

## Status doc (`docs/STATUS.md` or similar)

```markdown
# Status

Session 14, 2026-08-12.

## Current status

One paragraph: what works right now, in plain terms.

## Architecture (settled)

The current design, stated as fact. Not a history of how you got here.

## Proven vs untested

| Capability | Status | Evidence |
|---|---|---|
| X | Proven | Verified live, session 9, see research/probe-12.md |
| Y | Untested | Live-only, no offline check exists |

## What's next

1. Next concrete step.
2. Then this.

---

## Superseded

### Old approach (SUPERSEDED session 11)

Kept for history. Do not follow, see "Architecture" above for the current design.
```

## Index (`research/INDEX.md` or similar)

Read this file first after every context reset.

```markdown
# Research index

Read this FIRST after any context reset.

## Hard-won findings, never re-litigate

- Finding, one line, with what established it and where the full writeup lives.
- Another finding.

## Banned: crashes or dead ends

- Approach X: crashes/breaks under condition Y. Don't retry. See research/probe-07.md.

## Artifacts

| Artifact | Takeaway | Path |
|---|---|---|
| Probe run 12 | Confirms Z under load | research/probe-12.md |
| Reference repo (vendored) | Source for the format's real serializer | research/repos/vendor-lib/ |
| Agent research report | Refutes the caching approach | research/agent-reports/2026-08-10-cache.md |
```

## What belongs in each row

An index row is a pointer, not a summary of the summary. If the takeaway needs more than one line, the artifact itself needs a distillation file (see "Distilled notes sit next to raw dumps" in `SKILL.md`), and the index row points at the distillation, not at the raw dump directly.
