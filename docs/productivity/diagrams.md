## What it does

`diagrams` covers building architecture, network, and integration diagrams as mermaid source, rendered to PNG, with drawio as a fallback for pictures auto-layout can't express.

The defining constraint is the render command: every diagram is generated with `-b white`, forcing a white background, because mermaid's default transparent background breaks as soon as the PNG lands in a light-background deck or document. The `.mmd` source stays checked in beside the PNG, and a change means editing the source and regenerating, never touching the raster.

## When to reach for it

Type `/diagrams`, or the agent reaches for it automatically when a task fits.

| Purpose | Reach for |
|---|---|
| Infrastructure topology, integration architecture | A top-to-bottom mermaid flowchart |
| A data model, especially before explaining a migration | A mermaid entity-relationship diagram |
| A picture mermaid's auto-layout genuinely can't express | drawio |
| Enumerable requirements (source, target, port, protocol, direction) | A markdown table instead of a diagram |

## The render pipeline

```
npx -y @mermaid-js/mermaid-cli@latest -i x.mmd -o x.png -b white
```

No local mermaid-cli install is needed; `npx -y` fetches it each time. The `-b white` flag is the one detail worth remembering on its own: skip it and the PNG comes out with a transparent background that reads as broken the moment it's embedded anywhere light.

## Styling as meaning, not decoration

The conventions this skill follows aren't cosmetic. A `subgraph` per trust boundary or deployment zone makes the zone the unit a reader scans for. Explicit `style` lines carry meaning on purpose: one colour for the human actor, one for a public or less-secure path, one for a secure path, so colour is never left to mermaid's arbitrary defaults. Solid labelled arrows are a synchronous call with its protocol and port; dotted arrows are a secondary or discovery-only relationship. A reader should be able to tell what kind of connection they're looking at without reading every label.

## Common questions

**Should this be a diagram or a table?**

If the requirements are enumerable, source, target, port, protocol, direction, reason, a table is faster to read and faster to check for gaps. Reach for a flowchart only when the shape of the connectivity, which zone talks to which, is itself the point being made.

**A reviewer asked for an "updated diagram." Do I need to redraw it?**

Check first whether the architecture actually changed. If the approved change adds no new data flow, the honest answer is that the existing diagram is confirmed unchanged, and reissuing it is the correct response, not producing a new-looking diagram to appear responsive.

## It's working if

- Every `.mmd` file has a matching `.png` regenerated from it, never hand-edited.
- A reader can tell a synchronous call from a secondary relationship by arrow style alone, without reading the label.
- A request for enumerable connectivity facts gets a table, not a flowchart.
- An "updated diagram" request that turns out to need no changes gets an honest "unchanged" answer instead of a redraw.

## Where it fits

`diagrams` is a **reach-for-it-anytime standalone**, used whenever a picture of infrastructure, integration, or data shape is needed, independent of any other chain. Its closest neighbour is [slide-decks](../productivity/slide-decks.md): a diagram produced here is often the thing that gets dropped into a slide built there. When you're unsure which skill fits, [ask-denny](../engineering/ask-denny.md) routes you.
