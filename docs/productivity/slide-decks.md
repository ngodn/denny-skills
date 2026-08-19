## What it does

`slide-decks` covers producing a slide deck two ways: a markdown slide spec fed to an AI design tool for new content, or a direct python-pptx edit for a small precise change to a deck that already exists.

The defining constraint is the slide-spec rule: a spec carries the deck's visual identity plus plain content, and nothing else. No named layout templates, no per-slide layout or badge directives, no ASCII diagrams of hierarchies or workflows, no table row caps, no icon bans. Every one of those constrains the design tool and makes its output worse, a rule that only stuck after two failed attempts at writing specs the more prescriptive way.

## When to reach for it

Type `/slide-decks`, or the agent reaches for it automatically when a task fits.

| Situation | Reach for |
|---|---|
| New content, a new section, a deck built from a blank spec | The markdown-spec-to-design-tool path |
| A small precise change to slides that already exist | The direct python-pptx-edit path |
| The audience just needs a link, not a pptx file | A hosted single-file HTML deck, a separate hosting concern from deck production |

## Prerequisites

python-pptx must be installed to extract a deck's visual identity or to make a direct edit. The markdown-spec path needs no local tooling beyond the design tool itself.

## The identity-plus-content rule

Every spec starts by reading the real pptx and pulling out its visual identity: canvas size and background per slide type, a typography table, a palette as named tokens, a semantic colour table for status badges, and a short writing-rules block. Content goes on top of that, as plain prose and plain tables. No ASCII trees, no chevron-chain workflow diagrams, no layout keywords. Each of those reads to the tool as a literal instruction rather than as illustrative structure, and the output gets worse the more of them a spec carries.

## Deck identity discipline

A deck's repo tends to accumulate variants: an old version, a current one, a heavily annotated review copy. Before citing a slide number or extending a deck, confirm which file is actually current, by slide count and date, not by filename. Getting this wrong once means every citation in a review points at the wrong deck.

## Common questions

**Why did the design tool produce something worse after I gave it a detailed spec?**

Almost always because the spec carried layout directives, named templates, or ASCII diagrams instead of plain content. The tool reads an ASCII tree meant to illustrate "add a field here" as a literal schema to reproduce, and a chevron-chain workflow as a diagram to copy rather than a sequence to lay out itself. The fix is prose and tables, not more detail.

**A slide looks almost empty when I check it with a pptx reader. Is it actually blank?**

Not necessarily. Common pptx text extractors only render text frames placed directly on the slide; they show nothing for text sitting inside a table cell. A form-fields or data-reference slide built as a table can be fully populated and still read as empty through that tool. Cross-check with python-pptx directly before assuming a slide needs content.

**Which pptx file is the one I should be editing or citing?**

Whichever one is actually current, confirmed by slide count and date, never by filename pattern. A repo with a "final" and a "final-v2" and a heavily annotated review copy makes this an easy trap, and getting it wrong once means redoing every citation in a review.

## It's working if

- A slide spec reads as content someone could paste into any design tool, with no layout keywords or ASCII diagrams in it.
- A workflow in the spec is a table of states plus a branches list, never a chevron chain.
- Every colour and font in a generated slide traces back to a token in the extracted visual identity, not an invented one.
- A review revision touches only the slide that was flagged, not the ones next to it.
- Nobody has to ask "wait, which pptx is this?" partway through a review.

## Where it fits

`slide-decks` is a **reach-for-it-anytime standalone**: there's no chain it belongs to, you reach for it whenever a deck needs building, extending, or a precise edit. Its closest neighbour is [diagrams](../productivity/diagrams.md), for when a slide needs an architecture or network picture rather than prose and tables, produced separately and then dropped into the deck. When you're unsure which skill fits, [ask-denny](../engineering/ask-denny.md) routes you.
