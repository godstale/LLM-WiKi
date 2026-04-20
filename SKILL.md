---
name: llm-wiki
description: 'Use when working with the LLM Wiki — ingesting raw documents (/wiki-ingest, /wiki-ingest <file>, /wiki-ingest --from <folder> --to <folder>), querying the knowledge base (/wiki-query <question>), health-checking for broken links and orphans (/wiki-lint), or building the interactive knowledge graph (/wiki-graph). Also triggers on natural language like "ingest raw/...", "ingest all files in raw/", "query: ...", "lint the wiki", "build the knowledge graph".'
---

# LLM Wiki

Agent-maintained personal knowledge base: ingest → query → lint → graph.

## Installation

Copy this `llm-wiki/` folder to your skills directory:

```bash
# Personal (Claude Code)
cp -r llm-wiki ~/.claude/skills/llm-wiki

# Project-level
cp -r llm-wiki .agents/skills/llm-wiki
```

Install Python dependencies (optional, for `build_graph.py` and `lint.py`):

```bash
pip install -r ~/.claude/skills/llm-wiki/scripts/requirements.txt
```

## Project Directory Layout

Set up once in your wiki project:

```
raw/          # Drop zone for unprocessed docs — files are moved out after ingest
wiki/
  index.md    # Catalog of all pages — update on every ingest
  log.md      # Append-only chronological record
  overview.md # Living synthesis across all sources
  originals/  # Full source docs preserved after ingest (read-only archive)
  sources/    # One summary page per source doc
  entities/   # People, companies, projects, products
  concepts/   # Ideas, frameworks, methods, theories
  syntheses/  # Saved query answers
graph/        # Auto-generated graph data (graph.json, graph.html)
```

## Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Source slug | `kebab-case` matching filename (no ext) | `my-article` |
| Source page | `wiki/sources/kebab-case.md` | `wiki/sources/my-article.md` |
| Entity page | `wiki/entities/TitleCase.md` | `wiki/entities/OpenAI.md` |
| Concept page | `wiki/concepts/TitleCase.md` | `wiki/concepts/RAG.md` |
| Synthesis page | `wiki/syntheses/kebab-case.md` | `wiki/syntheses/main-themes.md` |

## Page Frontmatter

Every wiki page requires:

```yaml
---
title: "Page Title"
type: source | entity | concept | synthesis
tags: []
sources: []       # list of source slugs
source_file: wiki/originals/<slug>.md   # source pages only — path to original doc
last_updated: YYYY-MM-DD
---
```

Use `[[PageName]]` wikilinks to reference other wiki pages.

---

## /wiki-ingest

**$ARGUMENTS** (all optional):
- No arguments → batch-ingest all files in `raw/`
- `<file>` → ingest a single file (e.g. `raw/papers/my-article.md`)
- `--from <folder>` → use `<folder>` as the source instead of `raw/`
- `--to <folder>` → move originals to `<folder>` instead of `wiki/originals/`

**Argument parsing rules:**
- If the argument is a file path (has an extension or resolves to a file), treat it as a single-file ingest from that path.
- If the argument is a folder path (no extension, resolves to a directory), treat it as `--from <folder>`.
- `--from` and `--to` flags can be combined with a single file path.
- When no `--to` is specified, originals always go to `wiki/originals/`.

### Batch Mode (no arguments or `--from <folder>`)

When no specific file is given, process **all** files in the source folder (`raw/` by default, or the folder specified with `--from`):

1. Glob all files in the source folder (non-recursively first; include subdirectories only if the folder is explicitly specified with `--from`)
2. Filter out already-processed files (files present in `wiki/originals/` or the `--to` destination)
3. Process each file in sequence following the single-file ingest steps below
4. Print a summary: files processed, pages created/updated, files moved

### Destination Folder Rules (`--to <folder>`)

When a custom destination is specified with `--to`, apply the PARA folder structure from `references/folder-managing.md`:

1. **Determine the PARA category** based on the destination path or context:
   - `00_Inbox` — unsorted / unclear category
   - `01_Projects` — active project with a deadline
   - `02_Areas` — ongoing responsibility (no deadline)
   - `03_Resources` — reference material / reading notes
   - `04_Archives` — completed or inactive material
   If the `--to` path already starts with a PARA prefix (`00_`–`04_`), use it as-is.
   Otherwise, ask the user which category applies before proceeding (or infer from content if confident).

2. **Create the folder** under the destination using the PARA file-naming convention:
   - Format: `YYYYMMDD_<SourceSlug>_<ShortDescription>`
   - Example: `03_Resources/20260420_my-article_Reading-Notes/`
   - Use today's date for `YYYYMMDD`.

3. **Move the original file(s)** into that folder.
   - Update `source_file` frontmatter in the wiki source page to point to the new path instead of `wiki/originals/`.

4. **Do NOT create or modify `wiki/originals/`** when `--to` is specified.

### Pre-processing: Convert non-text files

If the source file is not already `.md` or `.txt` (e.g. `.docx`, `.pptx`, `.xlsx`, `.pdf`, `.doc`, `.ppt`, `.xls`):

1. **Try agent tools first** — invoke the appropriate skill for the file type:
   - `.docx` / `.doc` → `docx` skill
   - `.pptx` / `.ppt` → `pptx` skill
   - `.xlsx` / `.xls` → `xlsx` skill
   - `.pdf` → `pdf` skill
   Use the skill to extract the text content and save it as `<original-name>.md` in the same `raw/` directory.

2. **Fallback: `file_to_markdown.py`** — if the agent tool is unavailable or conversion fails, run:
   ```bash
   python tools/file_to_markdown.py --input_dir raw/
   ```
   This converts all non-markdown files in `raw/` to `.md`. Re-run the ingest with the generated `.md` file.

Once a `.md` file is available, proceed with the steps below.

### Agent-Based Ingest

1. Read the source file in full
2. Read `wiki/index.md` and `wiki/overview.md` for current context
3. Determine source slug from filename (kebab-case, no extension)
4. Select template → see `references/templates.md` (Default Source / Diary / Meeting)
5. Write `wiki/sources/<slug>.md` — set `source_file: wiki/originals/<slug>.md` in frontmatter
6. **Move original files to the destination folder:**
   - **Default (no `--to`):** move to `wiki/originals/` (create if it doesn't exist):
     - `.md` source: `<source>/<name>.md` → `wiki/originals/<slug>.md`
     - Matching binary original (`.ppt`, `.pdf`, `.docx`, etc.) → `wiki/originals/<slug>.<ext>`
   - **Custom destination (`--to <folder>`):** apply PARA folder rules (see *Destination Folder Rules* above):
     - Create `<folder>/YYYYMMDD_<slug>_<ShortDescription>/` if it doesn't exist
     - Move all related files into that subfolder
     - Set `source_file` frontmatter to the new path
   - After moving, the source folder should contain only files not yet processed
7. Update `wiki/index.md` — add entry under Sources section
8. Update `wiki/overview.md` — revise living synthesis if warranted
9. Create/update entity pages (`wiki/entities/EntityName.md`) for key people, companies, projects
10. Create/update concept pages (`wiki/concepts/ConceptName.md`) for key ideas and frameworks
11. Flag any contradictions with existing wiki content
12. Append to `wiki/log.md`: `## [YYYY-MM-DD] ingest | <Title>`
13. **Post-ingest validation:** check for broken `[[wikilinks]]`, verify all new pages in `wiki/index.md`, print change summary

**`wiki/originals/` folder:** stores full source documents after ingestion. This folder lives inside the wiki (Obsidian vault) so its contents are searchable and linkable within Obsidian. Files here are read-only archives — do not modify them.

### Index Entry Format

```markdown
- [Source Title](sources/slug.md) — one-line summary
- [Entity Name](entities/EntityName.md) — one-line description
- [Concept Name](concepts/ConceptName.md) — one-line description
```

---

## /wiki-query

**$ARGUMENTS** = the question to answer

### Agent-Based Query

1. Read `wiki/index.md` to identify most relevant pages
2. Read those pages (up to ~10 most relevant)
3. **Assess detail sufficiency:** if the summary pages lack enough detail to fully answer the question, check each relevant source page's `source_file` frontmatter field and read the original document from `wiki/originals/` for richer content
4. Synthesize a thorough markdown answer with `[[PageName]]` wikilink citations throughout
5. Include a `## Sources` section listing every page drawn from; if you read an original file, note it as `wiki/originals/<slug>.md`
6. Ask: "Would you like this answer saved as a synthesis page?"
   - If yes: write to `wiki/syntheses/<slug>.md` → see Synthesis template in `references/templates.md`
   - Append to `wiki/log.md`: `## [YYYY-MM-DD] query | <question summary>`

**When to read originals:** read `wiki/originals/` when the question asks for specific details (numbers, exact steps, precise definitions) not present in the summary, or when the user explicitly asks for original content. Skip if summary pages already provide sufficient detail.

**Empty wiki:** If `wiki/index.md` has no entries → respond: *"The wiki is empty. Run `/wiki-ingest <file>` to add your first source."*

---

## /wiki-lint

### Option A — Python Script (structural + graph-aware checks)

```bash
python tools/lint.py
python tools/lint.py --save   # save to wiki/lint-report.md
```

### Option B — Agent-Based Lint

Run all checks using Grep, Glob, and Read tools. Output a structured markdown report.

**Structural Checks (fast)**

**1. Orphan pages** — pages with no inbound `[[PageName]]` links:
```bash
grep -r "\[\[" wiki/ --include="*.md" -h
```
Pages not referenced by any wikilink = orphans.

**2. Broken links** — `[[WikiLinks]]` pointing to non-existent pages.
For each `[[PageName]]`: check if file exists in `wiki/entities/`, `wiki/concepts/`, or `wiki/sources/`. If none → broken link.

**3. Missing entity pages** — entity names mentioned in 3+ pages but lacking a `wiki/entities/` page.

**Semantic Checks (slower)**

**4. Contradictions** — read pages with `## Contradictions` sections; cross-check flagged claims; report confirmed conflicts.

**5. Stale summaries** — source pages where `last_updated` is earlier than concept/entity pages they inform.

**6. Data gaps** — questions the wiki cannot answer; for each, suggest a specific source type to fill it.

### Lint Report Format

```markdown
# Wiki Lint Report — YYYY-MM-DD

## Orphan Pages (N found)
- `wiki/path/page.md` — no inbound links

## Broken Links (N found)
- `[[PageName]]` in `wiki/sources/slug.md` — page does not exist

## Missing Entity Pages (N found)
- "Entity Name" — mentioned in N pages, no dedicated page

## Contradictions (N found)
- `wiki/sources/a.md` contradicts `wiki/sources/b.md` on: <topic>

## Stale Summaries (N found)
- `wiki/sources/slug.md` — last updated YYYY-MM-DD, related concept pages updated later

## Data Gaps
- Cannot answer: <question>
  Suggested source: <type>
```

After report, ask: "Would you like this saved to `wiki/lint-report.md`?"
Append to `wiki/log.md`: `## [YYYY-MM-DD] lint | Wiki health check`

---

## /wiki-graph

### Option A — Python Script (preferred)

```bash
python tools/build_graph.py --open

# With health report
python tools/build_graph.py --report --save
```

Outputs `graph/graph.json` and `graph/graph.html`, then opens browser.

### Option B — Agent-Based Graph Build (fallback when Python unavailable)

**1. Extract nodes** — Glob every `.md` in `wiki/`. Read frontmatter for `title` and `type`. Build nodes:

```json
{ "id": "wiki/sources/slug.md", "label": "Source Title", "type": "source", "color": "#4CAF50" }
```

Type → color: `source` #4CAF50 · `entity` #2196F3 · `concept` #FF9800 · `synthesis` #9C27B0 · unknown #9E9E9E

**2. Extract edges (EXTRACTED)** — Grep all `[[wikilinks]]`:
```bash
grep -rn "\[\[" wiki/ --include="*.md"
```
Source file → target page. Resolve target to node id.

**3. Infer edges (INFERRED)** — Topically related pages without explicit links. Include `confidence` score. If < 0.5 → type `AMBIGUOUS`, color `#BDBDBD`.

**4. Write `graph/graph.json`**:
```json
{ "nodes": [...], "edges": [...], "built": "YYYY-MM-DD" }
```

**5. Write `graph/graph.html`** — Use the self-contained vis.js template in `references/graph-html.md`. Inline graph.json content directly into the HTML.

**6. Summary** — Report total nodes by type, total edges by type, top 5 most-connected hubs.

Append to `wiki/log.md`: `## [YYYY-MM-DD] graph | Knowledge graph rebuilt`

---

## Other Utilities

**Convert PDFs, Word docs, etc. to Markdown before ingesting:**

```bash
python tools/file_to_markdown.py --input_dir raw/pdfs/
```

---

## Gotchas

- **`raw/` is a drop zone, not a permanent store** — files are moved out after ingest (to `wiki/originals/` or a custom `--to` folder); only unprocessed files remain
- **`--from <folder>` overrides `raw/`** — all files in the specified folder are treated as ingest candidates
- **`--to <folder>` overrides `wiki/originals/`** — a PARA-structured subfolder is created inside the destination; `source_file` frontmatter reflects the new path
- **Never modify files in `wiki/originals/`** — they are read-only archives of the original source documents
- **Always update `wiki/index.md`** on every ingest — stale index breaks wiki-query
- **Wikilinks are case-sensitive** — `[[OpenAI]]` ≠ `[[Openai]]`; match the exact filename
- **Source slugs must match filenames** — the slug in frontmatter `sources:` must equal the source `.md` filename without extension
- **`wiki/log.md` is append-only** — never edit past entries, only append new ones
- **All scripts run from the project root** — `Path.cwd()` must be your wiki project directory
- **graph.html is self-contained** — the Python script inlines the JSON; the agent-based fallback must do the same
