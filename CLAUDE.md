# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

**llm-wiki** is a Claude Code skill — not a runnable app. It ships as `SKILL.md` (the agent instruction file) plus supporting Python scripts and reference files. Users install it into their Claude skills directory and invoke it via slash commands in their own wiki projects.

The repo itself is the **skill distribution package**, not a wiki.

## Slash Commands (Skill Entry Points)

All commands are defined in `SKILL.md`:

| Command | Purpose |
|---------|---------|
| `/wiki-ingest [file\|--from <folder>] [--to <folder>]` | Ingest raw docs into the wiki |
| `/wiki-query <question>` | Query the wiki and present the answer |
| `/wiki-synthesize [slug]` | Save the most recent query answer as a synthesis |
| `/wiki-lint` | Health-check for broken links, orphans, contradictions |
| `/wiki-graph` | Build interactive vis.js knowledge graph |

## Python Scripts

Run from the **project root** of the user's wiki project (not from this repo):

```bash
# Lint
python scripts/lint.py
python scripts/lint.py --save          # save report to wiki/lint-report.md

# Build graph
python scripts/build_graph.py --open   # rebuild + open browser
python scripts/build_graph.py --report --save

# Convert non-markdown files to .md before ingesting
python scripts/file_to_markdown.py --input_dir raw/
```

Install dependencies:
```bash
pip install -r scripts/requirements.txt   # networkx, markitdown, tqdm
```

## Architecture

```
SKILL.md          ← agent instruction file (the actual skill)
scripts/
  build_graph.py  ← outputs graph/graph.json + graph/graph.html (vis.js)
  lint.py         ← structural + graph-aware health checks
  file_to_markdown.py  ← converts pdf/docx/pptx/xlsx → .md
  requirements.txt
references/
  templates.md         ← page frontmatter templates (source/entity/concept/synthesis)
  folder-managing.md   ← PARA method rules used by --to flag
  graph-html.md        ← self-contained vis.js HTML template
  wiki-hub/            ← WiKi-Hub extension (separate skill)
```

The scripts fall back gracefully: `networkx` is optional in `build_graph.py`; agent-based fallbacks for all commands are defined in `SKILL.md` so Python is never required.

## Wiki Directory Layout (User's Project)

When deployed, the skill manages this structure in the user's wiki project:

```
raw/              # Drop zone — files moved out after ingest
wiki/
  index.md        # Catalog (updated every ingest)
  log.md          # Append-only change log
  overview.md     # Living synthesis
  originals/      # Read-only archive of source docs
  sources/        # kebab-case.md — one summary per source
  entities/       # TitleCase.md — people, orgs, products
  concepts/       # TitleCase.md — ideas, frameworks, theories
  syntheses/      # kebab-case.md — saved query answers
graph/            # graph.json + graph.html
```

## Key Invariants

- `wiki/log.md` is **append-only** — never edit past entries
- `wiki/originals/` is **read-only** after ingest — never modify archived files
- `wiki/index.md` must be updated on every ingest — stale index breaks `/wiki-query`
- Wikilinks are **case-sensitive**: `[[OpenAI]]` ≠ `[[Openai]]`
- Source slugs in frontmatter `sources:` must exactly match the source filename without extension
- `graph/graph.html` is self-contained — JSON is inlined, not loaded from disk
- All scripts use `Path.cwd()` as the repo root — run from the wiki project root, not from the scripts directory

## Claude API Integration — Prompt Caching

When automating wiki workflows via the Claude API (e.g. batch ingestion scripts, CI pipelines), apply **prompt caching** to the skill content to avoid re-tokenizing on every call:

```python
import anthropic

skill_content = open("SKILL.md").read()

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    system=[
        {
            "type": "text",
            "text": skill_content,
            "cache_control": {"type": "ephemeral"}  # cache for up to 5 min
        }
    ],
    messages=[{"role": "user", "content": "/wiki-ingest raw/my-doc.md"}]
)
```

**When to include reference files in the cache block:** only load the reference files that the current operation needs (e.g. add `references/ingest-advanced.md` content to the cached block for batch ingest jobs). Loading all reference files unconditionally wastes the cache budget.

**Cache TTL:** 5 minutes. For long-running batch jobs, re-create the client or re-send the system block before TTL expires to keep the cache warm.

See [Anthropic prompt caching docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) for full details.

---

## PARA Folder Structure (`--to` flag)

When `/wiki-ingest --to <folder>` is used, the skill applies PARA categorization:
- `00_Inbox` / `01_Projects` / `02_Areas` / `03_Resources` / `04_Archives`
- Creates subfolder: `YYYYMMDD_<slug>_<ShortDescription>/`
- Updates `source_file` frontmatter to point to new path instead of `wiki/originals/`
