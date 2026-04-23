---
name: llm-wiki
description: 'Use when working with the LLM Wiki: /wiki-ingest [<file>|--from <folder>] [--to <folder>], /wiki-query <question>, /wiki-lint, /wiki-graph, /wiki-sources, /wiki-update <slug>, /wiki-delete <slug>, /wiki-ontology-init, /wiki-ontology-show, /wiki-ontology-validate. Also triggers on: "ingest raw/", "query:", "lint the wiki", "build the knowledge graph", "show ingest history", "update/delete wiki source", "set up ontology", "validate the ontology".'
---

# LLM Wiki

Agent-maintained personal knowledge base: ingest → query → lint → graph.

**Ontology is opt-in.** If `wiki/ontology.yaml` does not exist, all commands work exactly as described below. Ontology features are additive — see `references/ontology-commands.md`.

## Project Layout

```
raw/          # Drop zone for unprocessed docs (originals stay after ingest)
wiki/
  index.md        # Catalog of all pages — update on every ingest
  log.md          # Append-only chronological record
  overview.md     # Living synthesis
  history.json    # Registry of all ingested sources
  ontology.yaml   # (OPTIONAL) project ontology schema
  originals/      # Read-only archive of source docs
  sources/        # One summary page per source (kebab-case.md)
  entities/       # People, companies, projects, products (TitleCase.md)
  concepts/       # Ideas, frameworks, methods, theories (TitleCase.md)
  syntheses/      # Saved query answers (kebab-case.md)
graph/            # graph.json + graph.html
```

Page templates and frontmatter schema → see `references/templates.md`. Wikilinks are **case-sensitive**: `[[PageName]]`.

---

## /wiki-ingest

**Arguments** (all optional):
- *(none)* → batch-ingest all files in `raw/`
- `<file>` → single file (e.g. `raw/my-article.md`)
- `--from <folder>` → use custom source folder instead of `raw/`
- `--to <folder>` → copy originals to PARA-structured subfolder (not `wiki/originals/`)
- `--no-copy` → skip copying originals; incompatible with `--to`
- `--force-new` → always create new entry (date-suffix slug if duplicate); mutually exclusive with `--force-update`
- `--force-update` → always overwrite existing entry; mutually exclusive with `--force-new`
- `--no-interview` → skip ontology Context Interview
- `--batch-defaults` → reuse first file's interview answers as defaults for the rest
- `--summary-only` → extract summary + metadata only; skip full-text conversion

**For batch mode, `--to` PARA rules, file pre-processing (pdf/docx/pptx/xlsx), summary-only strategy, Context Interview → read `references/ingest-advanced.md`**

### Ingest Strategy (quick reference)

| Condition | Strategy |
|-----------|----------|
| `--summary-only` flag | summary-only |
| `.xlsx` / `.xls` | summary-only |
| `.pptx` / `.ppt` | summary-only |
| `.pdf` > 30 pages | summary-only |
| Everything else | full |

### Duplicate Detection

Check `wiki/history.json` for the candidate slug before ingesting:
- **`--force-new`**: append today's date (e.g. `my-article-20260421`); proceed
- **`--force-update`**: overwrite existing entry; proceed
- **Active slug, no flag**: pause and ask — Update / New entry (`<slug-YYYYMMDD>`) / Cancel
- **Deleted slug**: treat as fresh ingest (reuse slug, set `status: "active"`)

### Agent-Based Ingest (full strategy)

1. Read the source file in full
2. Read `wiki/index.md` and `wiki/overview.md`. If `wiki/ontology.yaml` exists, run Context Interview (see `references/ingest-advanced.md`) unless `--no-interview`
3. Derive slug from filename (kebab-case, no extension)
4. Select template → see `references/templates.md`
5. Write `wiki/sources/<slug>.md` with `source_file: wiki/originals/<slug>.md`
6. Copy original to `wiki/originals/<slug>.md` (skip if `--no-copy`; apply PARA rules if `--to`)
7. Update `wiki/index.md` — add entry: `- [Title](sources/slug.md) — one-line summary`
8. Update `wiki/overview.md` — revise living synthesis if warranted
9. Create/update entity pages in `wiki/entities/EntityName.md`
10. Create/update concept pages in `wiki/concepts/ConceptName.md`
11. Flag any contradictions with existing wiki content
12. Update `wiki/history.json` — **always use Write tool** (read existing → merge entry → overwrite). Schema → see `references/ingest-advanced.md`
13. Append to `wiki/log.md`: `## [YYYY-MM-DD] ingest | <Title>`
14. Post-ingest: check broken `[[wikilinks]]`, verify all new pages in index, print change summary

---

## /wiki-query

**$ARGUMENTS** = the question to answer

**For structural filters** (`class:`, `type:`, `AND/OR/NOT`, dotted field paths like `context.phase`) → read `references/query-advanced.md`

1. Read `wiki/index.md` to identify the most relevant pages
2. Read up to ~10 most relevant pages
3. If summaries lack sufficient detail, read the original from the page's `source_file` field
4. Synthesize a markdown answer with `[[PageName]]` wikilink citations throughout
5. Include `## Sources` listing every page drawn from
6. Ask: "Would you like this saved as a synthesis page?"
   - Yes → write `wiki/syntheses/<slug>.md` (template: `references/templates.md`)
   - Append to `wiki/log.md`: `## [YYYY-MM-DD] query | <question summary>`

**Empty wiki:** *"The wiki is empty. Run `/wiki-ingest <file>` to add your first source."*

---

## /wiki-lint

```bash
python tools/lint.py
python tools/lint.py --save   # save to wiki/lint-report.md
```

**Agent-based checks:**

1. **Orphan pages** — pages with no inbound `[[PageName]]` links
2. **Broken links** — `[[WikiLinks]]` pointing to non-existent pages
3. **Missing entity pages** — names mentioned in 3+ pages but no `wiki/entities/` page
4. **Contradictions** — read `## Contradictions` sections; cross-check flagged claims
5. **Stale summaries** — source pages where `last_updated` < related concept/entity pages
6. **Data gaps** — questions the wiki can't answer; suggest source type to fill

**Ontology checks (7–12), when `wiki/ontology.yaml` exists → read `references/ontology-commands.md`**

After report, ask: "Save to `wiki/lint-report.md`?"
Append to `wiki/log.md`: `## [YYYY-MM-DD] lint | Wiki health check`

---

## /wiki-graph

```bash
python tools/build_graph.py --open
python tools/build_graph.py --report --save
```

**Agent-based fallback:**

1. Glob every `.md` in `wiki/`. Build one node per page:
   `{ "id": "wiki/...", "label": "Title", "type": "source|entity|concept|synthesis", "color": "<hex>" }`
   Colors: `source` #4CAF50 · `entity` #2196F3 · `concept` #FF9800 · `synthesis` #9C27B0
2. Grep `[[wikilinks]]`; resolve each to a node id and create an edge
3. Write `graph/graph.json`; inline its contents into `graph/graph.html` (template: `references/graph-html.md`)

**Ontology-aware coloring, typed edges, and phase lanes → read `references/ontology-commands.md`**

Append to `wiki/log.md`: `## [YYYY-MM-DD] graph | Knowledge graph rebuilt`

---

## /wiki-sources

1. Read `wiki/history.json` (if missing → *"No sources ingested yet. Run `/wiki-ingest <file>`."*)
2. Print table sorted by `last_updated` desc:

   | Slug | Title | Ingested | Last Updated | Status |
   |------|-------|----------|--------------|--------|

3. For each active source, list `pages_created`, `entities_created`, `concepts_created`

---

## /wiki-update `<slug>`

1. Read `wiki/history.json`; error if slug absent or `status: "deleted"`
2. Find original at `source_file`; error if missing
3. Re-run Agent-Based Ingest steps 1–14 (update mode: do not re-archive original; overwrite source page; merge entity/concept pages)
4. Update `wiki/history.json`: set `last_updated`, refresh entity/concept lists
5. Append to `wiki/log.md`: `## [YYYY-MM-DD] wiki-update | <slug>`
6. Output: `✅ Updated source: <slug>. Run /wiki-graph to regenerate the knowledge graph.`

---

## /wiki-delete `<slug>`

1. Read `wiki/history.json`; error if absent or already `"deleted"`
2. Show what will be deleted and ask for confirmation:
   - `wiki/sources/<slug>.md`, `source_file` archive, orphaned entity/concept pages
3. After confirmation: delete source page, archive, and entity/concept pages not referenced by any other source. Update `wiki/index.md` and `wiki/overview.md`.
4. Set `"status": "deleted"` in `wiki/history.json` (preserve entry for audit trail)
5. Append to `wiki/log.md`: `## [YYYY-MM-DD] wiki-delete | <slug>`
6. Output: `✅ Deleted source: <slug>. Run /wiki-lint to check for remaining broken links.`

---

## /wiki-ontology-* commands

Full flow for `/wiki-ontology-init`, `/wiki-ontology-show`, `/wiki-ontology-validate` → **read `references/ontology-commands.md`**

---

## Key Gotchas

- **`wiki/originals/`** is read-only — never modify archived files
- **`wiki/index.md`** must be updated every ingest — stale index breaks `/wiki-query`
- **`wiki/log.md`** is append-only — never edit past entries
- **`wiki/history.json`**: always use Write tool — read existing first, merge, then overwrite
- **`/wiki-delete`** never removes shared pages — cross-check references before deleting entity/concept pages
- **Source slugs** in `sources:` frontmatter must exactly match the source filename without extension
- **All scripts** run from the wiki project root (`python tools/...`, not from the scripts directory)
