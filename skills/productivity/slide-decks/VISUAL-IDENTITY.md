# Visual identity template

Part 1 of a slide spec. Extract every section from the real pptx with python-pptx before writing any content; never fill these in from memory or a generic default.

## Canvas

Per slide type (title, section divider, content, closing): exact size in inches or mm, aspect ratio, background colour as hex.

## Typography

A table: role, font, point size, weight, colour.

| Role | Font | Size | Weight | Colour |
|---|---|---|---|---|
| Slide title | Montserrat | 22pt | SemiBold | #1E293B |
| Body text | Inter | 12pt | Regular | #334155 |

(Rows are illustrative. Replace with what the real deck actually uses.)

## Core palette

Named tokens, not raw hex scattered through the spec: something like Ink 900/800/600/500/400, Line, Surface, Accent, Accent dark, whatever names the deck actually uses. Every colour used anywhere in the deck should resolve to one of these tokens.

## Semantic colours

A status or risk badge table. Each state (success, info, warning, alert, critical, or whatever the deck's own vocabulary is) gets a solid text/border colour and a light fill tint.

## Writing rules

A short block of rules that apply to every slide's text: no em dashes, where citations sit relative to the footer, sentence case vs title case, whatever the deck's actual house style is.

---

This whole template is reusable regardless of which deck it's for: extract the identity first, spec the content on top of it, and never let a spec invent chrome the real deck doesn't have.
