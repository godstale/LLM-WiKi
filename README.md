# llm-wiki

An agent-maintained personal knowledge base for Claude Code. Drop in source documents, and Claude ingests, queries, lints, and visualizes your knowledge — no API key or Python scripts required.

```
ingest → query → lint → graph
```

---

## Installation

### Using npx (recommended)

```bash
npx skills add godstale/llm-wiki
```

This installs the skill to your global Claude Code skills directory (`~/.claude/skills/llm-wiki`).

To install at project level instead:

```bash
npx skills add godstale/llm-wiki --project
```

### Manual installation

```bash
# Global (available in all projects)
cp -r llm-wiki ~/.claude/skills/llm-wiki

# Project-level
cp -r llm-wiki .agents/skills/llm-wiki
```

### Python dependencies (optional)

Required only for the `lint.py` and `build_graph.py` scripts. The agent-based fallback works without them.

```bash
pip install -r ~/.claude/skills/llm-wiki/scripts/requirements.txt
```

---

## Project Setup

Create this directory structure once in your wiki project:

```
raw/              # Drop zone — place source documents here before ingesting
wiki/
  index.md        # Catalog of all pages (auto-maintained)
  log.md          # Append-only change log (auto-maintained)
  overview.md     # Living synthesis across all sources (auto-maintained)
  originals/      # Full source docs after ingest — read-only archive
  sources/        # One summary page per source document
  entities/       # People, companies, projects, products
  concepts/       # Ideas, frameworks, methods, theories
  syntheses/      # Saved query answers
graph/            # Auto-generated graph data (graph.json, graph.html)
```

You only need to create `raw/` and `wiki/` to start. Subdirectories are created automatically during ingest.

---

## Usage

All commands work as slash commands or natural language in Claude Code.

### Ingest a document

```
/wiki-ingest raw/my-article.md
```

- Reads the source file
- Creates a summary page in `wiki/sources/`
- Extracts and creates entity and concept pages
- Moves the original to `wiki/originals/`
- Updates `wiki/index.md` and `wiki/overview.md`

**Supported file types:** `.md`, `.txt`. For `.pdf`, `.docx`, `.pptx`, `.xlsx` — place the file in `raw/` and Claude will convert it automatically (requires the `pdf`, `docx`, `pptx`, or `xlsx` skill, or the `file_to_markdown.py` script as fallback).

### Query the knowledge base

```
/wiki-query what are the main themes across all sources?
```

- Reads the index to find relevant pages
- Synthesizes a markdown answer with `[[wikilink]]` citations
- Offers to save the answer as a synthesis page in `wiki/syntheses/`

### Lint the wiki

```
/wiki-lint
```

Checks for:
- Orphan pages (no inbound links)
- Broken `[[wikilinks]]`
- Missing entity pages (mentioned 3+ times, no dedicated page)
- Contradictions between sources
- Stale summaries
- Data gaps

Option A — Python script (structural + graph-aware):
```bash
python scripts/lint.py
python scripts/lint.py --save   # save report to wiki/lint-report.md
```

Option B — Agent-based (no Python needed): just run `/wiki-lint`.

### Build the knowledge graph

```
/wiki-graph
```

Generates an interactive HTML visualization of all wiki pages and their wikilink connections.

Option A — Python script (preferred):
```bash
python scripts/build_graph.py --open
python scripts/build_graph.py --report --save
```

Outputs `graph/graph.json` and `graph/graph.html`, then opens in the browser.

Option B — Agent-based fallback: runs automatically when Python is unavailable.

---

## Page Format

Every wiki page uses this frontmatter:

```yaml
---
title: "Page Title"
type: source | entity | concept | synthesis
tags: []
sources: []            # list of source slugs that inform this page
last_updated: YYYY-MM-DD
---
```

Use `[[PageName]]` wikilinks to link to other wiki pages.

### Naming conventions

| Type | File location | Naming |
|------|--------------|--------|
| Source | `wiki/sources/` | `kebab-case.md` |
| Entity | `wiki/entities/` | `TitleCase.md` |
| Concept | `wiki/concepts/` | `TitleCase.md` |
| Synthesis | `wiki/syntheses/` | `kebab-case.md` |

---

## Natural language triggers

You don't have to use slash commands. Claude also responds to:

- *"ingest raw/my-article.md"*
- *"query: what are the main themes?"*
- *"lint the wiki"*
- *"build the knowledge graph"*

---

## Utilities

Convert non-markdown files to `.md` before ingesting:

```bash
python scripts/file_to_markdown.py --input_dir raw/
```

---

## Gotchas

- **`raw/` is a drop zone** — files are moved to `wiki/originals/` after ingest; only unprocessed files remain
- **Never modify `wiki/originals/`** — read-only archive of source documents
- **Always keep `wiki/index.md` up to date** — stale index breaks `/wiki-query`
- **Wikilinks are case-sensitive** — `[[OpenAI]]` ≠ `[[Openai]]`
- **Source slugs must match filenames** — the slug in `sources:` frontmatter must equal the source `.md` filename without extension
- **`wiki/log.md` is append-only** — never edit past entries
- **Scripts run from project root** — `python scripts/build_graph.py` must be run from your wiki project directory

---

## License

MIT
