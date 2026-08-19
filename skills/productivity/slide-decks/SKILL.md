---
name: slide-decks
description: Producing a slide deck, whether through an AI design tool fed a markdown spec or through direct python-pptx edits to an existing file. Use when the user wants to build or extend a slide deck, write a slide-spec markdown file for a design tool, make a precise edit to specific slides in an existing pptx, or extract a deck's visual identity before writing new content.
---

# Slide Decks

Two ways to produce a slide deck: hand a markdown spec to an AI design tool for new content, or edit an existing pptx directly with python-pptx for a small precise change. The rule that makes either one work: a slide spec carries the deck's visual identity plus plain content, and nothing else. No layout templates, no per-slide directives, no diagrams. Every constraint added to a spec makes the tool's output worse, not better.

## Two paths

| Situation | Path |
|---|---|
| New content, a new section, a deck built from a blank spec | A markdown slide spec fed to an AI design tool |
| A small precise change to slides that already exist (fix a number, restyle one badge, add a row) | Direct python-pptx edit |

The python-pptx toolchain: `pptx.Presentation`, `pptx.util.{Inches,Pt,Emu}`, `pptx.dml.color.RGBColor`, `pptx.enum.text.{PP_ALIGN,MSO_ANCHOR}`, and small helper functions (`add_textbox`, `add_colored_rect`, `add_rounded_rect` via `MSO_SHAPE`). Reach for this path when the change is surgical, not when it's new content that needs a design pass.

## The slide-spec rule

Learned through two failed attempts: give the tool only the deck's visual identity plus plain content. Nothing else.

Don't add:

- named reusable layout templates ("L1 divider, L2 card row...")
- per-slide `Layout:` or `Badges:` directives
- ASCII-art diagrams of hierarchies or workflows
- table row caps
- icon bans

Each of these constrains the tool and makes the output worse, not better.

### Concrete traps

- An ASCII tree meant to say "add an attribute here" gets read as a literal schema diagram. Describe the change in prose instead ("add a field to object type X"), never as a tree.
- A workflow drawn as an ASCII chevron chain misleads the tool. Give an ordered table of states plus a branches list, and let the tool render it visually.

## Extracting the deck's visual identity

Before writing any spec, read the real pptx with python-pptx and pull out: canvas size and background colour per slide type, a typography table (role, font, pt size, weight, colour), a core palette as named tokens, a semantic colour table for status and risk badges, and a short writing-rules block. This is Part 1 of every spec, extracted from the actual file, never from memory. See [VISUAL-IDENTITY.md](VISUAL-IDENTITY.md) for the reusable template.

## Deck structure conventions

- Plan the slide count up front, in the spec header.
- Give each slide a two-part title: the topic, then a lighter second clause that reads as a running breadcrumb, a "you are here" without a separate section indicator.
- Decks are living documents, extended per phase. Append a new section at the end rather than rebuilding the deck.

## Deck identity discipline

A repo accumulates pptx variants: an old version, a current one, a heavily annotated review copy. Before citing a slide number or extending a deck, confirm which file is actually current and authoritative. Check the slide count and the date; don't pattern-match on the filename. Getting this wrong once means every citation points at the wrong deck and the whole review has to be redone.

## The pptx table-read gotcha

Common pptx extractors only render text frames placed directly on the slide. They show nothing for text inside table cells. A slide that looks almost empty through one of those tools can be fully populated via a table.

Cross-check any sparse-looking slide directly with python-pptx:

```python
from pptx import Presentation
prs = Presentation(path)
for sh in prs.slides[N - 1].shapes:
    if sh.has_table:
        for r in range(len(sh.table.rows)):
            for c in range(len(sh.table.columns)):
                print(r, c, sh.table.cell(r, c).text)
```

When editing a table cell, clear its paragraphs and add a styled run rather than assigning `.text` directly, to keep formatting consistent.

## Review loop

Review is conversational and incremental. Revisions are scoped to exactly what was flagged. Don't rewrite adjacent content that wasn't called out, even if it looks improvable while you're in there.

## Standing instructions in the deck source

A deck's own source markdown can carry standing instructions for whatever tool renders it: research online first rather than answering from memory, verify every figure before it goes on a slide, no AI-sounding phrasing, ask when in doubt. See [PREAMBLE.md](PREAMBLE.md) for the reusable block.

## When the deliverable is a link, not a file

A hosted single-file HTML deck is a valid alternative to pptx when the audience just needs a link to open, not a file to download. Serving it (static hosting, access control, caching) is a separate concern from producing the deck, and out of scope here.
