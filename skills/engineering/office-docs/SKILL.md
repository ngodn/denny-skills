---
name: office-docs
description: Generate Word, Excel and PowerPoint deliverables programmatically with python-docx, openpyxl and python-pptx. Use when the user wants to build a document/workbook/deck generator in Python, style docx tables or headings via raw OOXML, add dropdown validation or conditional formatting to a spreadsheet, edit an existing pptx deck surgically, or validate structured data before generating a report from it.
---

# Office docs

The mechanics of generating Word, Excel and PowerPoint deliverables with code instead of a template or hand-editing. The constraint that shapes everything here: python-docx, openpyxl and python-pptx expose thin public styling APIs, so most of the real work is either dropping to raw OOXML or working around what setting `.text` silently throws away.

## Generator package shape

- One module per artifact type: `word_generator.py`, `excel_generator.py`, a pptx equivalent. Each exposes one `build(output_path)` entrypoint and nothing else public.
- One private `_add_<section>(doc)` function per document section (cover, executive summary, scope, RACI, timeline, glossary, ...). `build()` is just the ordered list of calls plus `doc.save()`. This keeps the document's structure readable as a single function body, and reordering sections is a one-line change.
- Content lives in separate data modules (`tasks_data.py`, `calendar_data.py`), imported by every generator that needs it. When a Word narrative and an Excel tracker both describe the same tasks, they import the same data module so the two deliverables never drift out of sync.
- Build a shared `_common.py` theme module from day one: palette hex constants, font pairing, a `title()`/`header_row()`/`status_colours()` helper set, and shared dropdown vocabularies. Copy-pasting these constants into every generator file works for the first artifact and stops working at the second; refactor into `_common.py` before that happens, not after.

## python-docx

**Cell and paragraph shading has no public API.** Drop to OOXML:

```python
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def _set_cell_shading(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_color)
    tcPr.append(shd)
```

Same pattern on a paragraph via `paragraph._p.get_or_add_pPr()` instead of `get_or_add_tcPr()`. Use it for table header fills and zebra-striped body rows.

**Headings need a two-step trick.** `doc.add_heading(text, level=N)` is the only way to attach the built-in `Heading N` paragraph style, which Word's Table of Contents field scans for. But styling the auto-generated run directly doesn't reliably stick across Word versions, so strip its runs and add a fresh one, styled explicitly. Full code: [SNIPPETS.md#heading-trick](SNIPPETS.md#heading-trick).

**`cell.text = "..."` loses run styling.** It creates a run with no explicit font, so a font set at the table level won't apply. Walk every paragraph/run after filling cells and re-style, falling back to creating a run when `cell.text` left none. Full code: [SNIPPETS.md#cell-restyle](SNIPPETS.md#cell-restyle).

Build every table with `doc.add_table(rows=1, cols=N)` and a built-in table style (`"Light Grid Accent 1"`) as the base, so every table in the document shares a visual baseline before your per-cell overrides run.

**Footer**: `doc.sections[0].footer.paragraphs[0]`, cleared then given one styled run. Applied once for the whole document, since python-docx applies the default section's footer document-wide unless sections are split.

**Page breaks**: end every major section with `doc.add_page_break()` so each one starts fresh. Simple, and consistent when applied everywhere rather than ad hoc.

**No TOC field insertion.** python-docx cannot insert the TOC field XML itself. The `Heading N` styling above is what makes a human's Insert > Table of Contents in Word actually find the headings; the field insertion itself is a manual step, not something to chase in code.

## openpyxl

Two generator shapes cover most workbooks:

1. **Data-driven master workbook.** Content lives entirely in a data module (a list of dicts); the generator iterates and applies styling. Good for a task list, a tracker, anything row-per-record.
2. **Content-as-tuples, rendered by one loop.** Content is a list of `(kind, left, right)` tuples where `kind` is one of `"H1"/"H2"/"P"/"S"` (heading, sub-heading, paragraph, spec row), and a single loop dispatches each kind to its own styling. Content authors edit the tuple list and never touch styling code. Good for a README/how-to sheet.

**Dropdowns and live conditional formatting**, for columns that stay editable after delivery (a status column a client or PM will change later):

```python
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import FormulaRule

dv = DataValidation(type="list", formula1='"Not Started,In Progress,Done,Blocked,N/A"')
ws.add_data_validation(dv)
dv.add(f"G2:G{last_row}")

for value, colour in (("Done", "D1FAE5"), ("Blocked", "FEE2E2")):
    ws.conditional_formatting.add(
        f"G2:G{last_row}",
        FormulaRule(formula=[f'EXACT($G2,"{value}")'], fill=PatternFill("solid", fgColor=colour)),
    )
```

A one-time `PatternFill` applied at generation time is wrong here: it colours the cell once and never updates when the value changes after delivery. Reach for `PatternFill` only when every value is already known at generation time and the sheet won't be edited afterward (a category column, say); reach for `DataValidation` + `FormulaRule` whenever the column is meant to be edited after handoff.

**Grouped/banner header rows**: a group-label row above the real header row, built by walking columns and merging adjacent cells that share the same group label, to visually cluster related columns (e.g. network-prep columns vs host-prep columns) in a wide tracker.

**Freeze panes and autofilter**: `ws.freeze_panes = "A2"` (or `"A3"` with a banner row above the header) and `ws.auto_filter.ref = f"A1:{last_col}{last_row}"` on essentially every generated sheet with more than a handful of rows.

**Print setup for wide sheets**, so a tracker doesn't shed columns across printed pages:

```python
ws.page_setup.orientation = "landscape"
ws.sheet_properties.pageSetUpPr.fitToPage = True
ws.page_setup.fitToWidth = 1        # fit width to one page, height unconstrained
ws.print_title_rows = "1:2"         # repeat header rows on every printed page
```

**The styled-report pattern**: a merged full-width title band, a header row in a contrasting shade, section-band rows that group sub-rows under a parent (light fill, bold text, blank cells in the data columns), and semantic status colours (green/amber/grey for implemented/partial/planned, or your own three-state equivalent). Package the title band, header row and status colouring as small parameterised helpers (`add_sheet(wb, title, subtitle, rows)`, `style_status(cell)`) so a new framework or a new sheet is a new list of rows, not new styling code.

## python-pptx

Reach for python-pptx directly, rather than a design tool, when the change is a small precise edit to an existing deck: `pptx.Presentation`, `pptx.util.{Inches,Pt,Emu}`, `pptx.dml.color.RGBColor`, helper functions like `add_textbox`/`add_colored_rect` built once and reused per edit.

**Table cells are invisible to common text extractors.** A CLI or agent tool that reads pptx text often renders only text frames placed directly on the slide, and silently omits anything inside a table cell. A slide that is fully populated via a table can look empty. When a slide's extracted text looks suspiciously sparse, cross-check directly:

```python
for shape in prs.slides[n].shapes:
    if shape.has_table:
        for r in range(len(shape.table.rows)):
            for c in range(len(shape.table.columns)):
                print(r, c, shape.table.cell(r, c).text)
```

**Editing a cell's text**: clear the cell's paragraphs and add a freshly styled run, rather than assigning `.text` directly, for the same reason as the docx table case above: `.text` throws away run-level styling.

## Validate before generating

A dedicated `validators.py` module runs pure structural checks on the *data* before either generator touches it: unique ids, dependency references resolve, no dependency cycles (3-colour DFS), start date not after due date, every date falls on a real working day, every category and owner is drawn from a fixed enum. The build entrypoint calls `run_all()` first and refuses to write any output if it returns issues. Full `run_all` and the aborting `main()`: [SNIPPETS.md#validate-before-build](SNIPPETS.md#validate-before-build).

This generalises past any one document type: any generated planning artifact (a task list, a RACI, a dependency-laden checklist) benefits from a validator suite run pre-generation. Write unit tests that assert the *real, shipped* dataset passes every rule, not just that the validator logic is correct in isolation. A validator nobody runs against production data catches nothing.

## Regenerate, never hand-edit

The generator is the source of truth. A hand-edit to the output `.xlsx`/`.docx` is silently lost the next time the generator runs, so the rule is: edit the generator, not the file. When a live file genuinely must be hand-edited, diff it against a fresh regeneration written to a temp path before regenerating for real, so the hand-edit isn't silently reverted.

## The dash and arrow sweep

Before saving any generated content, sweep the actual cell/slide/document text for em dashes, en dashes used as a clause separator, and `->` used as a "leads to" connector. Check generated `.xlsx` cell text and `.pptx` shape/table text, not just markdown source, it's easy to grep the markdown and forget the generated content carries the same tells. This is a cheap, fully automatable lint step to run as part of `build()`, not a manual pre-send check.
