---
name: llm-wiki
description: 'SOP for agent-maintained personal knowledge base: ingest, query, lint, graph, update, and delete knowledge assets. Triggers on: wiki commands (/wiki-ingest, /wiki-query, /wiki-synthesize, /wiki-lint, /wiki-graph, /wiki-sources, /wiki-update, /wiki-delete, /wiki-ontology-*) or natural language intents: "ingest this", "search/query wiki", "lint health check", "rebuild graph", "manage ontology".'
---

# LLM Wiki: Agent SOP

This is the main "Operating Manual" for the LLM Wiki project. It manages the lifecycle of knowledge: **Ingest → Query → Lint → Graph**.

## 🧭 Core Workflow Index

For detailed instructions, refer to the specialized reference files.

| Stage | Action | Reference |
|-------|--------|-----------|
| **Ingest** | `/wiki-ingest [<file>\|--from <dir>]` | `references/ingest-advanced.md` |
| **Query** | `/wiki-query <question>` | `references/query-advanced.md` |
| **Save** | `/wiki-synthesize [slug]` | `SKILL.md#wiki-synthesize` |
| **Maintain** | `/wiki-lint` \| `/wiki-graph` | `SKILL.md#maintenance` |
| **Edit** | `/wiki-update` \| `/wiki-delete` | `SKILL.md#lifecycle` |
| **Ontology** | `/wiki-ontology-*` | `references/ontology-commands.md` |

---

## 🏗️ Project Layout

```
wiki/
  index.md          # Catalog of all pages (Update EVERY ingest)
  log.md            # Chronological record (Append-only)
  history.json      # Ingest registry (Always use Write tool)
  sources/          # Summaries (kebab-case.md)
  entities/         # People/Projects (TitleCase.md)
  concepts/         # Ideas/Theories (TitleCase.md)
  syntheses/        # Saved query answers
  originals/        # Read-only archive
  ontologies/       # (OPTIONAL) Structured YAML data
```
Templates & Schema → `references/templates.md` | Wikilinks: `[[PageName]]` (Case-Sensitive)

---

## 📥 Ingest Process

**Main Goal:** Transform raw input into structured wiki pages and archive the original.

1. **Analysis:** Read source. Determine title/slug.
2. **Strategy:** Select mode (Full vs. Summary-Only).
   - *Summary-Only:* `.xlsx`, `.pptx`, `.pdf` > 30p, or `--summary-only` flag.
3. **Execution:**
   - Write `wiki/sources/<slug>.md`.
   - Update `wiki/index.md` (categorize: 기술/개발, 업무/프로젝트, 개인/생활, 여행, 임시메모).
   - Create/Update `wiki/entities/` and `wiki/concepts/`.
4. **Registration:** Update `wiki/history.json` and append to `wiki/log.md`.

**Advanced flags (`--to`, `--precision`, `--no-interview`, etc.) → `references/ingest-advanced.md`**

---

## 🔍 Query & Synthesis

### /wiki-query
1. Discover relevant pages from `wiki/index.md` and `wiki/synthesis-map.md`.
2. Gather context from `sources/`, `entities/`, `concepts/`, and `ontologies/`.
3. Synthesize answer with `[[PageName]]` citations.
**Structural filters (class:, type:, AND/OR) → `references/query-advanced.md`**

### /wiki-synthesize
Saves the last query answer to `wiki/syntheses/<slug>.md`.
1. Generate slug from question.
2. Update `wiki/synthesis-map.md` (append-only) and `wiki/log.md`.

---

## 🛠️ Maintenance & Lifecycle

### #maintenance
- **/wiki-lint**: Check orphans, broken links, stale summaries. (Report: `wiki/lint-report.md`)
- **/wiki-graph**: Rebuild `graph/graph.json` and `graph/graph.html`.

### #lifecycle
- **/wiki-sources**: List ingested sources from `history.json`.
- **/wiki-update <slug>**: Refresh a source from its original file.
- **/wiki-delete <slug>**: Soft-delete source (keep in history, remove pages).

---

## ⚠️ Gotchas & Critical Rules
- **READ-ONLY:** Never modify `wiki/originals/`.
- **CONSISTENCY:** `wiki/index.md` must be updated on *every* ingest to keep query discovery working.
- **HISTORY:** Always read-merge-write `wiki/history.json`.
- **CLEANUP:** When deleting, check for orphaned entity/concept pages.
