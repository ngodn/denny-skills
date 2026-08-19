---
name: client-deliverables
description: Editorial discipline for anything a consulting or vendor engagement sends outside the building, a client-facing document, workbook, or deck. Use when the user is writing or generating a customer-facing report, comparison, or tracker, preparing something for a client send, deciding what belongs in an internal versus customer document, sourcing scope facts (counts, vendor lists, breakdowns) for a client deliverable, or citing a regulatory/compliance finding in client-bound material.
---

# Client deliverables

The editorial discipline for anything that leaves the building on a consulting or vendor engagement. The one constraint that shapes everything below: customer-facing and internal are never the same file behind an audience flag. They are separate directories and separate generators, because a flag leaves internal text one boolean away from a customer document.

## Two directories, never one flag

Structure the repo so the split is physical, not conditional: a directory (or generator module) that gets zipped and sent, and a separate one that never leaves. Where the same underlying content needs an internal and a customer variant (a full multi-vendor breakdown internally, an approved-subset view for the client), write two outputs from the shared data, not one output with an `if audience == "customer"` branch threaded through it. The branch is where the internal sentence eventually leaks.

## The pre-send sweep

Before anything ships, grep the customer-facing tree for internal voice, and check **generated spreadsheet cell text**, not just markdown source, it's easy to grep the `.md` and forget the generated content carries the same tells.

| Category | Grep for |
|---|---|
| Internal process language | "SOW", "scope of work", "out of scope", "not yet approved", "scope conflict", "governance incident", "contentious" |
| Talking about the client in third person | phrases that describe the client's own sector or situation back to them, rather than addressing them directly |
| Persuasion / reassurance / negotiation framing | "why choose us", justifications for why work is necessary, urgency narrative not grounded in an actual decision or request |
| Commentary on the client's own process | remarks on how long their internal approvals take, or that their signed contract is wrong |
| Formatting tells | em dashes, en dashes used as a clause separator, `->` used as "leads to" |

Prefer "Information needed" framing over "open items for [client]" when addressing the client directly: the first asks for something, the second implies they're behind.

## A capability or comparison document is facts only

Comparing a vendor tool against an incumbent, or describing what a product does, for a customer audience: strip all positioning. No "why choose us," no scope-control or auditability reassurance, no framing that argues for a conclusion. State only what each thing is and does. Positioning, objection-handling, and the actual recommendation go in a separate internal document, cross-referenced but never merged back into the customer-facing one.

## Never invent scope facts

A device count, a vendor list, a breakdown by class or domain: source every one from an actual project document (a signed scope document, a design spec, the generator's own task data), never from a plausible-sounding guess. Where the source doesn't answer it, write an explicit to-be-confirmed placeholder and tie it to the task or id that will close the gap, rather than filling the space with something that reads confidently but isn't grounded.

## Regulatory findings feed the customer's checklist, not your timeline

A regulatory or compliance finding becomes a line item in the customer's own preparation checklist. It never becomes a justification for the supplier's own project duration, phase count, or scope. A rule requiring an internal risk assessment before a new tool gets network access is one row in the customer's own phase-0 task list, not a reason the engagement timeline gets longer.

## Flag unverified facts, don't guess

State a fact even when you can't fully verify it, but flag it visibly (e.g. "confirm") rather than asserting it as settled, whenever it couldn't be checked against a live, rendered source. When the source needs JavaScript to render, use a real browser (not a plain HTTP fetch) to actually open and read it before writing the fact down.

## Writing style

No em dashes. Short declarative sentences. Bullets and tables over prose wherever there's a branch or an enumerable list. Write like a senior practitioner leaving a colleague a clear note, not like generated copy: no hedging, no "it's worth noting," no persuasive framing dressed up as fact.

## Spec before generator code

For a new deliverable set, write a short design spec first: objective, audience, locked assumptions and engagement context. Get it explicitly approved before writing any generator code. This is cheap to redo when wrong and expensive to redo once code and content are already tangled together.

## Two co-shipped deliverables, one source of truth

A narrative document (layered: an executive summary for management, technical detail underneath) plus a live tracker workbook, cross-referenced by id rather than duplicated by hand. Every claim in the narrative traces to a row in the tracker; the tracker is the thing that gets checked off, the narrative is the thing that gets read once. Generate both from the same data module so they can never drift apart.

## Package by channel constraint

Match delivery format to the channel it travels through, not to authoring convenience. A markdown reference document destined for a client gets rendered to `.docx` before delivery. A script destined for a client stays in its native format during development, then a renamed `.txt` copy is what actually gets sent, because mail filters commonly strip or block executable script attachments (`.ps1`, `.sh`).

## Propagate a changed constraint everywhere

When an engagement constraint changes (a new item comes into scope, a class gets client approval, a policy gets clarified), propagate the change across every artifact that encodes it, not just the one that was pointed at. A protocol newly in scope belongs in the README prose, the relevant config, and the tracker workbook, all three, not only in whichever file someone happened to be looking at when the change was raised. Treat a partial propagation as the failure mode it is, and check the other artifacts every time, not just when reminded.
