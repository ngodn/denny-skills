# Snippets

Longer code referenced from [SKILL.md](SKILL.md). Each one is the reusable core of a helper function; adapt names and fonts to your own `_common.py`.

## Heading trick

`doc.add_heading()` attaches the built-in `Heading N` style so Word's Table of Contents field can find it, but the auto-generated run doesn't reliably take explicit font styling across Word versions. Strip it and add a fresh run instead:

```python
from docx.oxml.ns import qn

def _style_heading(paragraph, text, level):
    try:
        paragraph.style = f"Heading {level}"
    except Exception:
        pass

    # Clear the auto-generated runs.
    for run in paragraph.runs:
        run.text = ""
    p = paragraph._p
    for r in p.findall(qn('w:r')):
        p.remove(r)

    # Add a fresh run and style it explicitly.
    run = paragraph.add_run(text)
    if level == 1:
        run.font.name = "Montserrat"
        run.font.bold = True
        run.font.size = Pt(18)
        run.font.color.rgb = COLOR_WHITE
        _set_paragraph_shading(paragraph, "0891B2")
    elif level == 2:
        run.font.name = "Montserrat"
        run.font.bold = True
        run.font.size = Pt(13)
        run.font.color.rgb = COLOR_TEAL


def _add_h1(doc, text):
    p = doc.add_heading(text, level=1)
    _style_heading(p, text, 1)
    return p
```

Call `_add_h1(doc, "Executive Summary")` instead of `doc.add_heading` directly, everywhere in the generator.

## Cell restyle

`cell.text = "..."` (or filling a table header via plain string assignment) creates a run with no explicit font. Walk every paragraph/run afterward and re-apply styling, creating a run if `cell.text` left none:

```python
def _style_table_header(table):
    hdr_row = table.rows[0]
    for cell in hdr_row.cells:
        _set_cell_shading(cell, "0891B2")
        for para in cell.paragraphs:
            for run in para.runs:
                run.font.name = "Montserrat"
                run.font.bold = True
                run.font.size = Pt(10)
                run.font.color.rgb = COLOR_WHITE
            # cell.text left no runs at all: create one.
            if not para.runs and para.text:
                txt = para.text
                para.clear()
                r = para.add_run(txt)
                r.font.name = "Montserrat"
                r.font.bold = True
                r.font.size = Pt(10)
                r.font.color.rgb = COLOR_WHITE
```

The same shape applies to data rows (drop `bold`, swap the header fill for a zebra-stripe fill on every other row) and to python-pptx table cells.

## Validate before build

`validators.py` is a set of pure functions, each returning a list of human-readable issue strings (empty list means clean):

```python
from collections import defaultdict
from datetime import date

def validate_unique_ids(tasks: list[dict]) -> list[str]:
    seen: set[str] = set()
    dupes: list[str] = []
    for t in tasks:
        if t["id"] in seen:
            dupes.append(f"duplicate id: {t['id']}")
        seen.add(t["id"])
    return dupes


def validate_no_cycles(tasks: list[dict]) -> list[str]:
    graph: dict[str, list[str]] = defaultdict(list)
    for t in tasks:
        for dep in t["depends_on"]:
            graph[t["id"]].append(dep)
    WHITE, GRAY, BLACK = 0, 1, 2
    colour: dict[str, int] = defaultdict(int)
    issues: list[str] = []

    def dfs(node: str, path: list[str]) -> None:
        colour[node] = GRAY
        for nxt in graph.get(node, []):
            if colour[nxt] == GRAY:
                issues.append(f"cycle: {' -> '.join(path + [nxt])}")
            elif colour[nxt] == WHITE:
                dfs(nxt, path + [nxt])
        colour[node] = BLACK

    for t in tasks:
        if colour[t["id"]] == WHITE:
            dfs(t["id"], [t["id"]])
    return issues


def run_all(tasks: list[dict], domains) -> list[str]:
    issues: list[str] = []
    issues += validate_unique_ids(tasks)
    issues += validate_dependencies_exist(tasks)
    issues += validate_no_cycles(tasks)
    issues += validate_dates_are_working_days(tasks)
    issues += validate_start_not_after_due(tasks)
    issues += validate_domains_covered(tasks, domains)
    issues += validate_categories_valid(tasks)
    issues += validate_owners_valid(tasks)
    return issues
```

The build entrypoint aborts on any issue rather than writing a partial or wrong deliverable:

```python
def main() -> int:
    issues = run_all(tasks_data.TASKS, tasks_data.DOMAINS)
    if issues:
        print("Validation failed:")
        for i in issues:
            print(f"  - {i}")
        return 1
    excel_generator.build(xlsx_path)
    word_generator.build(docx_path)
    return 0
```

Pair this with a test file that imports the *real* shipped data module and asserts each validator returns `[]` against it, e.g. `assert validate_unique_ids(tasks_data.TASKS) == []`. Testing the validator against synthetic fixtures only proves the validator works; testing it against the live dataset proves the deliverable is actually clean.
