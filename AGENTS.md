# AGENTS.md — LLM Wiki Project Context

Instructions for AI agents (Codex, Copilot, and other general-purpose agents) working in this repository.

## What This Repo Is

**llm-wiki** is an agent skill package — not a runnable application. It ships as `SKILL.md` (the agent instruction file) plus supporting Python scripts and reference files. The repo is the **skill distribution package**; users install it and invoke it via slash commands in their own wiki projects.

## Slash Commands

All commands are defined in `SKILL.md` and executed inside the user's wiki project:

| Command | Purpose |
|---------|---------|
| `/wiki-ingest [file\|--from <folder>] [--to <folder>]` | Ingest raw docs into the wiki |
| `/wiki-query <question>` | Query the wiki and present the answer |
| `/wiki-synthesize [slug]` | Save the most recent query answer as a synthesis |
| `/wiki-lint` | Health-check for broken links, orphans, contradictions |
| `/wiki-graph` | Build interactive vis.js knowledge graph |
| `/wiki-sources` | List all ingested sources |
| `/wiki-update <slug>` | Re-ingest an existing source |
| `/wiki-delete <slug>` | Remove a source and its derived pages |

## Directory Layout (User's Wiki Project)

```
raw/              # Drop zone for unprocessed docs
wiki/
  index.md        # Catalog — updated on every ingest
  log.md          # Append-only change log
  overview.md     # Living synthesis
  history.json    # Registry of all ingested sources
  synthesis-map.md  # Index of saved query syntheses (append-only)
  originals/      # Read-only archive of source docs
  sources/        # kebab-case.md — one summary per source
  entities/       # TitleCase.md — people, orgs, products
  concepts/       # TitleCase.md — ideas, frameworks, theories
  syntheses/      # kebab-case.md — saved query answers
graph/            # graph.json + graph.html
```

## Key Invariants

- `wiki/log.md` — append-only, never edit past entries
- `wiki/synthesis-map.md` — append-only, never edit past entries
- `wiki/originals/` — read-only after ingest, never modify archived files
- `wiki/index.md` — must be updated on every ingest
- `wiki/history.json` — always read → merge → overwrite with Write tool
- Wikilinks are case-sensitive: `[[OpenAI]]` ≠ `[[Openai]]`
- Source slugs in `sources:` frontmatter must exactly match the filename without extension
- All scripts run from the wiki project root (`python scripts/...`)

## Wiki Page Frontmatter

Every `.md` file in `wiki/` requires YAML frontmatter:

```yaml
---
title: "Page Title"
type: source | entity | concept | synthesis
tags: []
sources: [slug1, slug2]
last_updated: YYYY-MM-DD
---
```

## Naming Conventions

- **Sources & Syntheses:** `kebab-case.md`
- **Entities & Concepts:** `TitleCase.md`

## Python Scripts

```bash
python scripts/lint.py --save              # health check → wiki/lint-report.md
python scripts/build_graph.py --open       # rebuild graph + open browser
python scripts/file_to_markdown.py --input_dir raw/   # convert pdf/docx/pptx/xlsx → .md
pip install -r scripts/requirements.txt    # networkx, markitdown, tqdm
```

Python is optional — agent-based fallbacks for all commands are defined in `SKILL.md`.

## Recommended Workflow

```
/wiki-ingest raw/my-doc.md
/wiki-query "What does this say about X?"
/wiki-synthesize          ← save the answer for future queries
/wiki-lint                ← check for broken links after bulk ingests
/wiki-graph               ← rebuild visualization
```

## Reference Files

| File | Purpose |
|------|---------|
| `references/templates.md` | Page frontmatter templates |
| `references/folder-managing.md` | PARA method rules for `--to` flag |
| `references/ingest-advanced.md` | Batch ingest, PARA, Context Interview |
| `references/query-advanced.md` | Structural filters for `/wiki-query` |
| `references/ontology-commands.md` | Ontology feature (opt-in) |
| `references/graph-html.md` | vis.js HTML template |
