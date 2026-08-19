## What it does

`office-docs` is the mechanics of generating Word, Excel and PowerPoint deliverables with code instead of a template or hand-editing. It covers the generator package shape, the python-docx/openpyxl/python-pptx techniques that make the output look styled rather than default, and the validate-before-build discipline that keeps a generator from shipping broken data. The defining constraint is that all three libraries expose thin public styling APIs, so most of the real work is either dropping to raw OOXML or working around what setting `.text` silently throws away.

## When to reach for it

Type `/office-docs`, or the agent reaches for it automatically when a task fits.

Reach for it when you're building or extending a Python generator for a `.docx`, `.xlsx`, or `.pptx` file: a report, a tracker workbook, a deck edit. It is a reference for the mechanics of generation, not for what the generated content should say to a client audience, that's a separate concern.

| The problem | The skill |
|---|---|
| How to shade a table cell, style a heading, add a dropdown column, cross-check a pptx table | `office-docs` |
| What belongs in a customer-facing document versus an internal one, how to write client-bound prose | [client-deliverables](../productivity/client-deliverables.md) |

## The generator shape

Three things repeat across every generator worth keeping: one `build(output_path)` entrypoint per artifact type, one private `_add_<section>` function per document section so `build()` reads as an ordered table of contents, and a shared `_common.py` theme module (palette, fonts, header/status helpers) built before the second generator file exists, not after the palette constants have already been copy-pasted twice.

The other leading idea is **validate before generate**: a pure-function validator module runs structural checks (unique ids, resolvable references, no cycles, real working days, valid enums) against the data before either generator touches it, and the build entrypoint aborts on any issue rather than writing a partial or wrong file. Pair it with a test that asserts the *real, shipped* dataset passes every rule, not just synthetic fixtures, since a validator nobody runs against production data catches nothing.

Where a library's public API falls short, the skill's own SKILL.md carries the exact snippet (the `w:shd` OOXML shading helper, the heading-style-then-strip-then-restyle trick, the `DataValidation` plus `FormulaRule` pairing for a column that stays editable after delivery), and pushes the longer function bodies into a sibling [SNIPPETS.md](../../skills/engineering/office-docs/SNIPPETS.md).

## Common questions

**I attached the Heading style but Word's Table of Contents is still empty.**

Two separate things have to both be true. python-docx's `add_heading()` (or manually setting `paragraph.style = "Heading N"`) is what makes Word's TOC *field* able to find the heading at all, but python-docx never inserts the TOC field itself. That last step is a human action: Insert > Table of Contents in Word, with "update field on open" if you want it to stay current. A generator that produces styled headings but no visible TOC hasn't necessarily done anything wrong.

**I filled table cells with `cell.text = "..."` and the font/colour styling I set is gone.**

`cell.text` (and the equivalent shortcut assignment on a paragraph) creates a run with no explicit font. Any styling applied at the table or theme level doesn't reach a run that was never touched. The fix is a re-style pass after filling cells: walk every paragraph and run, apply the font explicitly, and create a run from scratch when `cell.text` left none behind.

**A slide/tracker I generated looks almost empty when I read it back, but I know it has content.**

Check whether the content is inside a table. Common pptx-reading tools and CLI extractors render only text frames placed directly on the slide, and silently skip anything inside a table cell. Cross-check with python-pptx directly, iterating `shape.has_table` and walking `shape.table.cell(r, c).text`, before concluding a slide is actually empty.

**Someone hand-edited the generated `.xlsx`/`.docx` directly. Can I just regenerate?**

Regenerating without checking will silently discard the hand-edit, since the generator is the only source of truth the next run respects. Before regenerating for real, diff the live file against a fresh regeneration written to a temp path, so you know exactly what the hand-edit changed and can decide whether it needs to go into the generator itself.

## It's working if

- A new document section is a new `_add_<section>` function and a one-line addition to `build()`'s call order, not a scattered edit across the file.
- The palette, fonts and shared helpers live in one `_common.py`, not duplicated at the top of every generator file.
- `build()` refuses to write output when the validator returns any issue, and the validator's own tests run against the real shipped data.
- Generated cell, slide, and document text has no em dashes, en dashes, or `->` arrows left in it.

## Where it fits

`office-docs` is a **reach-for-it-anytime standalone**, a reference for the generation mechanics rather than a step in any chain. Its closest neighbour is [client-deliverables](../productivity/client-deliverables.md): this skill is the "how" of producing a styled `.docx`/`.xlsx`/`.pptx`, that one is the "what belongs in it" when the file is headed to a client. The two are usually wanted together on a real engagement. When you're unsure which skill or flow fits, [ask-denny](../engineering/ask-denny.md) routes you.
