# ADR Format

ADRs live in `docs/adr/` and use sequential numbering: `0001-slug.md`, `0002-slug.md`, etc.

Create the `docs/adr/` directory lazily: only when the first ADR is needed.

## Template

```md
# {Short title of the decision}

{1-3 sentences: what's the context, what did we decide, and why.}
```

That's it. An ADR can be a single paragraph. The value is in recording *that* a decision was made and *why*, not in filling out sections.

## Optional sections

Only include these when they add genuine value. Most ADRs won't need them.

- **Status** frontmatter (`proposed | accepted | deprecated | superseded by ADR-NNNN`): useful when decisions are revisited
- **Considered Options**: only when the rejected alternatives are worth remembering
- **Consequences**: only when non-obvious downstream effects need to be called out

## Rejected alternative and consequences

A stronger shape than the plain template, proven on a real architecture doc: state the decision, then an explicit **Rejected alternative** naming what you didn't do and why it lost, then **Consequences we accept** naming the downstream cost you're taking on knowingly.

```md
# {Short title of the decision}

{1-3 sentences of context and the decision.}

**Rejected alternative:** {what you didn't do, and why it lost.}

**Consequences we accept:** {the downstream cost you're taking on knowingly.}
```

This is `Considered Options` and `Consequences` made specific: a named alternative with a reason, and a named cost, rather than an inventory of what was on the table. Reach for it whenever a rejected alternative is worth remembering; skip it when the decision was obvious and nothing was really rejected.

## Known limits, decided rather than discovered

Keep a running "Known limits" section (in the architecture doc, or as its own ADR) for limits chosen deliberately rather than hit by accident: a hardware session cap, a numeric tolerance, a deliberately unsupported case. When a limit later gets resolved, don't delete the entry: annotate it as resolved and leave it in place. The reasoning recorded there is still the reason the thing is shaped the way it is, even after the limit itself is gone.

## Numbers carry their measurement

A number in an ADR is only as good as the context it was measured in. Write "measured on X at Y" (an environment, a load, a date), never a bare estimate standing alone. "`lto = fat`, `codegen-units = 1`: measured 10-20% faster on the release profile" is checkable and re-measurable; "should be faster" is not.

## Numbering

Scan `docs/adr/` for the highest existing number and increment by one.

## When to offer an ADR

All three of these must be true:

1. **Hard to reverse**: the cost of changing your mind later is meaningful
2. **Surprising without context**: a future reader will look at the code and wonder "why on earth did they do it this way?"
3. **The result of a real trade-off**: there were genuine alternatives and you picked one for specific reasons

If a decision is easy to reverse, skip it. You'll just reverse it. If it's not surprising, nobody will wonder why. If there was no real alternative, there's nothing to record beyond "we did the obvious thing."

### What qualifies

- **Architectural shape.** "We're using a monorepo." "The write model is event-sourced, the read model is projected into Postgres."
- **Integration patterns between contexts.** "Ordering and Billing communicate via domain events, not synchronous HTTP."
- **Technology choices that carry lock-in.** Database, message bus, auth provider, deployment target. Not every library: just the ones that would take a quarter to swap out.
- **Boundary and scope decisions.** "Customer data is owned by the Customer context; other contexts reference it by ID only." The explicit no-s are as valuable as the yes-s.
- **Deliberate deviations from the obvious path.** "We're using manual SQL instead of an ORM because X." Anything where a reasonable reader would assume the opposite. These stop the next engineer from "fixing" something that was deliberate.
- **Constraints not visible in the code.** "We can't use AWS because of compliance requirements." "Response times must be under 200ms because of the partner API contract."
- **Rejected alternatives when the rejection is non-obvious.** If you considered GraphQL and picked REST for subtle reasons, record it. Otherwise someone will suggest GraphQL again in six months.
