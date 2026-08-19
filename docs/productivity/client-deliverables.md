## What it does

`client-deliverables` is the editorial discipline for anything a consulting or vendor engagement sends outside the building: a client-facing report, comparison, workbook, or deck. It states what belongs in a customer document versus an internal one, how to source facts without inventing them, and the writing style client-bound prose should hold to. The defining constraint is that customer-facing and internal content are never the same file behind an audience flag, they are separate directories and separate generators, because a flag leaves internal text one boolean away from a customer document.

## When to reach for it

Type `/client-deliverables`, or the agent reaches for it automatically when a task fits.

Reach for it whenever you're writing or generating something a client, customer, or external reviewer will actually see: a comparison document, a scope section, a compliance mapping, a status report, or right before any send. For the mechanics of actually generating the `.docx`/`.xlsx`/`.pptx` file, see [office-docs](../engineering/office-docs.md) instead, this skill covers what the content should say, not how the file gets built.

## The pre-send sweep

The core habit is a grep pass over the customer-facing tree before anything ships, and it has to cover generated spreadsheet cell text, not just markdown source, since it's easy to grep the `.md` and forget the generated content carries the same tells.

| Category | What it catches |
|---|---|
| Internal process language | "SOW", "out of scope", "scope conflict", "governance incident" |
| Talking about the client in third person | phrasing that describes the client's own situation back to them instead of addressing them directly |
| Persuasion / reassurance / negotiation framing | "why choose us," manufactured urgency, arguing for a conclusion instead of stating a fact |
| Formatting tells | em dashes, en dashes as a clause separator, `->` as "leads to" |

A capability or comparison document written for a customer is facts only: what each thing is and does, with all positioning, objection-handling, and the actual recommendation moved to a separate internal document instead.

## Common questions

**Why not just add an `audience` flag to the generator instead of maintaining two outputs?**

Because it doesn't hold up. The pattern surfaces repeatedly: a shared generator with an audience toggle is one missed branch away from internal language landing in a customer document. Two directories or two generators reading from the same underlying data is the version that survives review.

**How do I decide if a paragraph belongs in the internal notes or the customer document?**

The working test is concrete: would you actually attach this file to the email you send the client? Anything that wouldn't survive being read by the client directly, justification narrative, internal timeline commentary, unresolved scope debate, belongs in the internal document instead, cross-referenced but not merged back in.

**A client asked about a compliance or regulatory requirement. Does that push out the timeline?**

No. A regulatory or compliance finding becomes a line item in the client's own preparation checklist. It is never grounds for extending the supplier's own project duration, phase count, or scope, those are two different questions and conflating them is a recurring mistake worth checking for explicitly.

**The client didn't specify a count, vendor list, or breakdown. What do I write?**

Never fill the gap with a plausible-sounding guess. Source every number from an actual project document, and where the source is silent, write an explicit to-be-confirmed placeholder tied to the task or id that will close it. An invented number that turns out wrong costs far more trust than an honest placeholder.

## It's working if

- Every customer-facing artifact lives in its own directory or generator, with no `if audience ==` branch anywhere near it.
- A grep for the internal-voice tells table turns up nothing, in both markdown and generated spreadsheet cell text.
- Every count, vendor name, and breakdown in a client document traces to an actual project document or carries an explicit to-be-confirmed placeholder.
- A regulatory finding shows up as a line in the client's own checklist, never as a line in the supplier's own timeline.

## Where it fits

`client-deliverables` is a **reach-for-it-anytime standalone**, the editorial half of producing something client-bound rather than a step in a fixed chain. Its closest neighbour is [office-docs](../engineering/office-docs.md): that skill is the "how" of generating the `.docx`/`.xlsx`/`.pptx` file itself, this one is the "what belongs in it" once the file is headed to a client. When you're unsure which skill or flow fits, [ask-denny](../engineering/ask-denny.md) routes you.
