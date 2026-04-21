---
name: llm-wiki
description: 'Use when working with the LLM Wiki — ingesting raw documents (/wiki-ingest, /wiki-ingest <file>, /wiki-ingest --from <folder> --to <folder>), querying the knowledge base (/wiki-query <question>), health-checking for broken links and orphans (/wiki-lint), building the interactive knowledge graph (/wiki-graph), listing ingest history (/wiki-sources), updating an ingested source (/wiki-update <slug>), deleting an ingested source (/wiki-delete <slug>), creating or editing the project ontology (/wiki-ontology-init), showing the current ontology (/wiki-ontology-show), or validating instances against the ontology (/wiki-ontology-validate). Also triggers on natural language like "ingest raw/...", "ingest all files in raw/", "query: ...", "lint the wiki", "build the knowledge graph", "show ingest history", "update wiki source", "delete wiki source", "set up an ontology", "build a schema for this project", "validate the ontology".'
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
raw/          # Drop zone for unprocessed docs — files are copied out after ingest (originals remain)
wiki/
  index.md         # Catalog of all pages — update on every ingest
  log.md           # Append-only chronological record
  overview.md      # Living synthesis across all sources
  history.json     # Registry of all ingested sources (create/update/delete)
  ontology.yaml    # (OPTIONAL) Project ontology schema — created by /wiki-ontology-init
  ontology-guide.md  # (OPTIONAL) Human-readable ontology summary — auto-generated
  originals/       # Full source docs preserved after ingest (read-only archive)
  sources/         # One summary page per source doc
  entities/        # People, companies, projects, products
  concepts/        # Ideas, frameworks, methods, theories
  syntheses/       # Saved query answers
graph/             # Auto-generated graph data (graph.json, graph.html)
```

**Ontology is opt-in.** If `wiki/ontology.yaml` does not exist, the skill operates exactly as before. When it exists, ingest/query/graph/lint become ontology-aware and gain structural-query, typed-edge, and validation features.

## history.json Schema

`wiki/history.json` is the authoritative record of every ingested source. Created on first ingest, updated on every ingest/update/delete.

```json
{
  "<slug>": {
    "slug": "<slug>",
    "title": "Page Title",
    "ingested_at": "YYYY-MM-DDTHH:MM:SS",
    "last_updated": "YYYY-MM-DDTHH:MM:SS",
    "source_file": "wiki/originals/<slug>.md",
    "pages_created": ["sources/<slug>.md"],
    "entities_created": ["entities/EntityName.md"],
    "concepts_created": ["concepts/ConceptName.md"],
    "status": "active"
  }
}
```

| Field | Description |
|-------|-------------|
| `slug` | kebab-case filename without extension |
| `title` | Human-readable title from page frontmatter |
| `ingested_at` | ISO 8601 timestamp of first ingest |
| `last_updated` | ISO 8601 timestamp of last update |
| `source_file` | Path to the archived original document |
| `pages_created` | Source pages created for this slug (relative to `wiki/`) |
| `entities_created` | Entity pages first created during this ingest |
| `concepts_created` | Concept pages first created during this ingest |
| `status` | `active` or `deleted` |

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
- `--to <folder>` → copy originals to `<folder>` instead of `wiki/originals/`
- `--no-copy` → analyze and create wiki pages only; skip copying originals to `wiki/originals/`
- `--force-new` → always create a new entry (suffix slug with date if duplicate exists, e.g. `my-article-20260421`)
- `--force-update` → always overwrite the existing entry without prompting (equivalent to `/wiki-update` but driven by the source file)
- `--no-interview` → skip the ontology Context Interview (use auto-inferred values only). No-op if ontology is absent.
- `--batch-defaults` → in batch mode, reuse the first file's interview answers as defaults for the rest (confirm-only per file)
- `--summary-only` → extract only summary + metadata; do not attempt full-text conversion. Overrides the auto-strategy for the file. Useful for dense spreadsheets, large binary specs, or files whose raw content is not meaningful as prose.

**Argument parsing rules:**
- If the argument is a file path (has an extension or resolves to a file), treat it as a single-file ingest from that path.
- If the argument is a folder path (no extension, resolves to a directory), treat it as `--from <folder>`.
- `--from` and `--to` flags can be combined with a single file path.
- `--no-copy` is incompatible with `--to` — if both are given, warn the user and abort.
- `--force-new` and `--force-update` are mutually exclusive — if both are given, warn the user and abort.
- `--summary-only` is compatible with all other flags.
- When no `--to` is specified and `--no-copy` is not set, originals always go to `wiki/originals/`.

### Batch Mode (no arguments or `--from <folder>`)

When no specific file is given, process **all** files in the source folder (`raw/` by default, or the folder specified with `--from`):

1. Glob all files in the source folder (non-recursively first; include subdirectories only if the folder is explicitly specified with `--from`)
2. For each file, determine the slug and check `wiki/history.json` for duplicates:
   - **`--force-new`**: always create with a date-suffixed slug (e.g. `my-article-20260421`); skip prompt
   - **`--force-update`**: always overwrite existing entry; skip prompt
   - **Neither flag**: skip files with an existing active slug in this batch (log a warning listing skipped files) — the user can re-run with a flag or target the file individually to resolve
3. Process each non-skipped file in sequence following the single-file ingest steps below
4. Print a summary: files processed, pages created/updated, files skipped (with reason), files copied

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

3. **Copy the original file(s)** into that folder.
   - Update `source_file` frontmatter in the wiki source page to point to the new path instead of `wiki/originals/`.

4. **Do NOT create or modify `wiki/originals/`** when `--to` is specified.

### Pre-processing: Convert non-text files

#### Ingest Strategy Selection

Before converting, determine the ingest strategy for the file. Two strategies exist:

| Strategy | Behavior | When applied |
|----------|----------|--------------|
| **full** | Full-text conversion → ingest entire content | `.md`, `.txt`, narrative `.pdf`, `.docx` under ~30 pages |
| **summary-only** | Read file directly → extract summary + metadata only; skip full conversion | `.xlsx`/`.xls`, `.pptx`/`.ppt` over ~20 slides, `.pdf` over ~30 pages, any file with `--summary-only` flag |

**Selection rules (in priority order):**
1. If `--summary-only` flag is set → always use **summary-only** strategy.
2. Else if the file is `.xlsx` or `.xls` → **summary-only** (spreadsheet content converts poorly to prose).
3. Else if the file is `.pptx` or `.ppt` → **summary-only** (slide decks are better represented by outline + metadata).
4. Else if the file is `.pdf` and page count > 30 → **summary-only**.
5. Otherwise → **full**.

Announce the chosen strategy before proceeding: *"Using summary-only strategy for `<filename>` (reason: <reason>)."* For full strategy, proceed to conversion below. For summary-only, skip conversion and go directly to **Summary-Only Ingest**.

#### Full Strategy: Convert non-text files

If strategy is **full** and the file is not already `.md` or `.txt`:

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

Once a `.md` file is available, proceed with **Agent-Based Ingest** below.

#### Summary-Only Ingest

Used when the file's raw content is not meaningful as prose (dense spreadsheets, large specs, presentation decks).

1. **Read the file directly** using the appropriate agent tool (do not save a converted `.md`):
   - `.xlsx` / `.xls` → `xlsx` skill (read sheet names, headers, row counts, key values)
   - `.pptx` / `.ppt` → `pptx` skill (read slide titles, section headers, speaker notes)
   - `.pdf` → `pdf` skill (read first 3 pages + TOC if present)
   - Others → read what is accessible

2. **Extract the following metadata** from file content and any available context (filename, path, date modified):

   | Field | Source |
   |-------|--------|
   | `title` | File name, title slide, or first heading |
   | `purpose` | Inferred from content type and section headers |
   | `content_type` | `spreadsheet` / `presentation` / `spec` / `report` / `other` |
   | `author` / `team` | Author field, metadata, path context (e.g. `/finance/`) |
   | `created_at` | File metadata, header date, or filename date pattern |
   | `scope` | What the document covers (e.g. "Q2 budget for 3 teams") |
   | `sheet_names` | (spreadsheets) list of sheet names |
   | `slide_count` | (presentations) number of slides |
   | `sections` | Top-level headings or sheet names as a bullet list |
   | `key_values` | Up to 5 important data points visible without deep reading |

3. **Write `wiki/sources/<slug>.md`** using the summary-only template:

   ```yaml
   ---
   title: "<Title>"
   type: source
   ingest_mode: summary-only
   content_type: <spreadsheet|presentation|spec|report|other>
   source_file: wiki/originals/<slug>.<ext>
   created_at: <YYYY-MM-DD or blank>
   author: <name or blank>
   team: <team or blank>
   tags: []
   sources: []
   last_updated: <YYYY-MM-DD>
   ---

   ## Purpose
   <One paragraph: what this document is for and who uses it.>

   ## Scope
   <What the document covers: subject, time period, teams, systems.>

   ## Structure
   <Bullet list of sheets / sections / slides with one-line descriptions.>

   ## Key Values
   <Up to 5 important data points, figures, or decisions visible at a glance.>

   ## How to Use
   Load the original file at `<source_file>` for full data.
   ```

4. **Skip deep entity/concept extraction** — only create entity/concept pages when a name is explicit and prominent (e.g. a team name in the filename or title). Do not enumerate every cell reference.

5. Continue from **step 6** of Agent-Based Ingest (copy original, update index, log).

**When `/wiki-query` loads a summary-only source:**
- The source page answers "what is this file and where is it."
- If the query requires actual data from the file, the agent reads `source_file` on demand and answers from the raw content — then optionally offers to update the source page with the newly surfaced data.

### Duplicate Detection (single-file ingest)

Before ingesting, resolve whether the slug already exists in `wiki/history.json`:

1. Read `wiki/history.json` (or treat as `{}` if missing).
2. Compute the candidate slug from the filename.
3. If the slug exists with `status: "active"`:
   - **`--force-new`**: append today's date to make a unique slug (e.g. `my-article-20260421`). If that slug also exists, keep incrementing a counter suffix (`-20260421-2`, etc.). Proceed with the new slug.
   - **`--force-update`**: treat this ingest as an update — overwrite `wiki/sources/<slug>.md`, merge entity/concept pages, and update `wiki/history.json`. Skip steps 5–6 of the copy logic (original is already archived). Proceed directly to step 1 of Agent-Based Ingest.
   - **Neither flag**: **pause and ask the user:**
     > "`<slug>` already exists in the wiki (ingested on `<ingested_at>`). What would you like to do?
     > 1. Update existing entry (overwrite the summary page, merge entities/concepts)
     > 2. Add as a new entry (slug will be `<slug-YYYYMMDD>`)
     > 3. Cancel"
     - Choice 1 → proceed as `--force-update`
     - Choice 2 → proceed as `--force-new`
     - Choice 3 → abort and print: *"Ingest cancelled."*
4. If the slug exists with `status: "deleted"`: treat as a fresh ingest (the previous entry was deleted; reuse the slug and set `status: "active"`).
5. If the slug does not exist: proceed normally.

### Agent-Based Ingest

*(Full strategy only — for summary-only strategy, see Summary-Only Ingest above)*

1. Read the source file in full
2. Read `wiki/index.md` and `wiki/overview.md` for current context
2a. **Load ontology (if present):** read `wiki/ontology.yaml`. If absent, skip steps 2b and any ontology-aware operations below — the ingest proceeds with the legacy behavior.
2b. **Context Interview** (skip if `--no-interview` or ontology absent): see *Context Interview* section below. Collect `context:` block values for the source frontmatter.
3. Determine source slug from filename (kebab-case, no extension)
4. Select template → see `references/templates.md` (Default Source / Diary / Meeting). When ontology is active, also include the optional `class:` and `context:` blocks.
5. Write `wiki/sources/<slug>.md` — set `source_file: wiki/originals/<slug>.md` in frontmatter. Include `class:` and `context:` blocks when ontology is active.
6. **Copy original files to the destination folder (skip if `--no-copy`):**
   - **If `--no-copy` is set:** skip this step entirely; leave `source_file` frontmatter pointing to the original path (e.g. `raw/<name>.md`)
   - **Default (no `--to`):** copy to `wiki/originals/` (create if it doesn't exist):
     - `.md` source: `<source>/<name>.md` → `wiki/originals/<slug>.md`
     - Matching binary original (`.ppt`, `.pdf`, `.docx`, etc.) → `wiki/originals/<slug>.<ext>`
   - **Custom destination (`--to <folder>`):** apply PARA folder rules (see *Destination Folder Rules* above):
     - Create `<folder>/YYYYMMDD_<slug>_<ShortDescription>/` if it doesn't exist
     - Copy all related files into that subfolder
     - Set `source_file` frontmatter to the new path
   - Original files in the source folder are kept in place after copying
7. Update `wiki/index.md` — add entry under Sources section
8. Update `wiki/overview.md` — revise living synthesis if warranted
9. Create/update entity pages (`wiki/entities/EntityName.md`) for key people, companies, projects. When ontology is active: tag each entity with `class:` if it matches an ontology class; record `relations:` when the document explicitly asserts them (e.g. "Alice leads TeamAlpha" → `{predicate: leads, target: TeamAlpha}` on the Alice page). Entities that match no ontology class are still created — the `class:` field is simply omitted.
10. Create/update concept pages (`wiki/concepts/ConceptName.md`) for key ideas and frameworks. Same ontology rules as entities — tag with `class:` when it matches (e.g. Goal, Risk, Domain).
11. Flag any contradictions with existing wiki content. When ontology is active, also flag predicate/domain mismatches (e.g. a `produces` relation where the source is not an Activity).
12. **Update `wiki/history.json`** — read existing file if present (or start with `{}`), then write/replace the entry for this slug:
    - Set `ingested_at` only on first ingest (field absent); update `last_updated` always
    - `pages_created` = `["sources/<slug>.md"]`
    - `entities_created` = list of entity page paths written in step 9
    - `concepts_created` = list of concept page paths written in step 10
    - `ingest_mode` = `"full"` or `"summary-only"` depending on the strategy used
    - `status` = `"active"`
    - Use the **Write tool** to save (never shell echo — `|` in JSON is safe in Write but not in shell)
13. Append to `wiki/log.md`: `## [YYYY-MM-DD] ingest | <Title>`
14. **Post-ingest validation:** check for broken `[[wikilinks]]`, verify all new pages in `wiki/index.md`, print change summary

**`wiki/originals/` folder:** stores full source documents after ingestion. This folder lives inside the wiki (Obsidian vault) so its contents are searchable and linkable within Obsidian. Files here are read-only archives — do not modify them.

### Index Entry Format

```markdown
- [Source Title](sources/slug.md) — one-line summary
- [Entity Name](entities/EntityName.md) — one-line description
- [Concept Name](concepts/ConceptName.md) — one-line description
```

### Context Interview (ontology-aware)

**When run:** after loading ontology.yaml (step 2a) and before writing the source page (step 5). Skipped when `wiki/ontology.yaml` does not exist or `--no-interview` is passed.

**Procedure:**

1. **Scan the document** for automatically-inferable context fields:
   - `artifact_type`: match file patterns and content cues (e.g. "retrospective" → Meeting, "decision doc" → Decision, default → Document)
   - `authored_at`: extract from a date header, frontmatter, or filename
   - `authored_by`: extract from explicit author line, email signature, or git metadata if available
   - `relates_to` candidates: entities/concepts mentioned 2+ times that are in the wiki or the ontology

2. **Present the inferred values and the gaps:**

   ```
   🔍 Document Context Interview — raw/<filename>

   Auto-detected (confirm or correct):
     ✓ artifact_type : Meeting           (keyword match: "retrospective")
     ✓ authored_at   : 2026-04-18        (from document header)
     ? authored_by   : ?                 (not detected)
     ? phase         : ?                 (ontology phases: Discover / Build / Validate)
     ? relates_to    : detected mentions: TeamAlpha, SprintGoal-Q2

   Please clarify (answer all or skip any):
     Q1. 작성자는 누구인가요? Actor 인스턴스 — [Alice, Bob, Carol] 또는 +new
     Q2. 어느 phase와 연관됩니까? [Discover / Build / Validate]
     Q3. 어떤 Activity 인스턴스의 산출물/기록인가요? 예: sprint-12, design-review-01
     Q4. 감지된 mentions의 관계는?
         - TeamAlpha       → [part_of / owned_by / authored_by / skip]
         - SprintGoal-Q2   → [achieves / references / part_of / skip]
   ```

3. **Batch mode:**
   - Default: interview each file in order.
   - `--batch-defaults`: interview only the first file fully; reuse its answers as defaults for subsequent files, asking "use same defaults?" (yes/edit/skip) per file.
   - `--no-interview`: skip entirely; record only auto-inferred values. Missing fields stay absent from `context:` block (no placeholder).

4. **Validation during interview:**
   - `phase` values not in `workflow.phases[].id` — warn, allow to add (user can expand workflow later via `/wiki-ontology-init --edit workflow`).
   - `class` / `predicate` values not in ontology — warn, allow (surfaces in `/wiki-ontology-validate`).
   - Target names that don't exist yet — offer: *"`<name>` is new. Create a stub page? (yes/no)"* — on yes, create `wiki/entities/<name>.md` or `wiki/concepts/<name>.md` with a minimal frontmatter and "TODO" body.

5. **Write the answers to source frontmatter** under a `context:` block — schema per `references/templates.md` (Ontology-Extended Fields section).

6. **Propagate to entities/concepts (step 9/10):**
   - For each `relates_to` entry, write the inverse predicate on the target page when defined:
     e.g. source has `{predicate: achieves, target: SprintGoal-Q2}` → on `wiki/concepts/SprintGoal-Q2.md`, add nothing (achieves has no declared inverse); but `owns` → `owned_by`, `part_of` → `contains` are written bidirectionally.

---

## /wiki-query

**$ARGUMENTS** = the question to answer, optionally prefixed by a structural filter.

**Structural filter syntax (ontology-aware):** if the query begins with `class:`, `type:`, `tags:`, or any dotted field path, and/or uses `AND`/`OR`/`NOT`, treat it as a structural filter rather than semantic search.

Filter grammar (formal):

```
expr    := term (('AND' | 'OR') term)*
term    := 'NOT'? (atom | '(' expr ')')
atom    := field op value
field   := IDENT ('.' IDENT)*          e.g. class, context.phase, properties.owner
op      := ':' | '=' | '!=' | '~='     (':' == '='; '~=' is substring/membership)
value   := QUOTED_STRING | BARE_WORD
```

Semantics:
- Field lookup is a dotted path on the page's frontmatter dict. Missing = never matches.
- `=` on a list (e.g. `tags=draft`) → list contains the value as an element.
- `=` on a scalar → case-insensitive equality.
- `~=` → substring match (for lists: any element contains the substring).
- `!=` → negation of `=` (pages without the field *do* match `!=`).

Examples:
- `class:Ticket AND context.phase=alpha` — all Ticket instances in alpha phase
- `type:source AND tags~=meeting` — source pages tagged with anything containing "meeting"
- `(class:Risk AND properties.impact=high) OR class:Goal` — boolean combination
- `NOT type=entity` — everything that isn't an entity page
- `what are the main themes?` — plain natural-language query (unchanged)

### Option A — Python Script (preferred for structural filters)

```bash
python scripts/query_filter.py "class:Ticket AND context.phase=alpha"
python scripts/query_filter.py --list-fields     # print available fields
python scripts/query_filter.py --paths-only "class:Goal"   # pipe-friendly output
```

The script reads every page's frontmatter, runs the parser + evaluator, and prints matching paths. The agent can then Read the matched pages and synthesize an answer (step 3 onward below).

### Option B — Agent-Based Query

1. Read `wiki/index.md` to identify most relevant pages
2. **If a structural filter is detected** (and `wiki/ontology.yaml` exists):
   - Either invoke `scripts/query_filter.py` (preferred) or parse the expression manually
   - Glob `wiki/entities/` and `wiki/concepts/` for pages whose frontmatter matches the constraints
   - For source pages, match `class:` and `context.*` fields
   - Return the matching pages **before** semantic synthesis — present as a structured list with links, then optionally synthesize narrative
   - If no match: report "no instances match" and suggest relaxing the filter
3. Read those pages (up to ~10 most relevant)
4. **Assess detail sufficiency:** if the summary pages lack enough detail to fully answer the question, check each relevant source page's `source_file` frontmatter field and read the original document from `wiki/originals/` for richer content
5. Synthesize a thorough markdown answer with `[[PageName]]` wikilink citations throughout
6. Include a `## Sources` section listing every page drawn from; if you read an original file, note it as `wiki/originals/<slug>.md`
7. Ask: "Would you like this answer saved as a synthesis page?"
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

**Ontology Checks (skip if `wiki/ontology.yaml` is absent)**

**7. Unknown class** — `class:` values in frontmatter not defined under any axis's `default_classes` in the ontology.

**8. Unknown predicate** — `relations[].predicate` values not declared under `relations:` in the ontology.

**9. Unknown phase** — `context.phase` values not listed under `workflow.phases[].id`.

**10. Domain/range violation** — relations where source class is not in the predicate's `domain` or target class is not in its `range`.
Example: `{predicate: produces, target: TeamAlpha}` on a source where `class: Document` — `produces` expects `domain: [Activity]`, so this is a violation.

**11. Cardinality anomalies** (best-effort) — classes whose properties suggest required fields (e.g. Task needs `owner`, Goal needs `target_date`) that are missing on instances. Flagged as "potential gap" not error.

**12. Workflow gaps** — Activity instances with no `context.phase` tag when workflow is declared, or phases with zero instances.

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

## Ontology Violations (N found, skip if no ontology)
- Unknown class `ClassName` in `wiki/entities/Foo.md`
- Unknown predicate `custom_relation` in `wiki/sources/bar.md`
- Unknown phase `Shipping` in `wiki/sources/baz.md` (declared phases: Discover, Build, Validate)
- Domain violation: `{predicate: produces}` on `wiki/entities/TeamAlpha.md` (class: Team) — expects domain [Activity]
- Missing required property `owner` on Task instance `wiki/entities/TaskX.md`
- Phase `Validate` has no associated Activity instances
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

**1. Extract nodes** — Glob every `.md` in `wiki/`. Read frontmatter for `title`, `type`, and (if ontology active) `class`, `context.phase`. Build nodes:

```json
{ "id": "wiki/sources/slug.md", "label": "Source Title", "type": "source", "class": "Meeting", "phase": "Build", "color": "#4CAF50", "group": "Activity" }
```

Type → color (fallback): `source` #4CAF50 · `entity` #2196F3 · `concept` #FF9800 · `synthesis` #9C27B0 · unknown #9E9E9E

**Ontology-aware coloring (when `wiki/ontology.yaml` exists):** override the type-based color with axis-based colors for richer visualization:
- Actor #1976D2 · Activity #388E3C · Artifact #F57C00 · Objective #7B1FA2 · Resource #5D4037 · Context #546E7A
- Set `group` to the axis name so vis.js can cluster by axis
- Add `phase` to the node; the HTML template uses it to position nodes in phase-labeled lanes when workflow is declared

**2. Extract edges (EXTRACTED)** — Two sources:

*a. Wikilinks (untyped):* Grep all `[[wikilinks]]`:
```bash
grep -rn "\[\[" wiki/ --include="*.md"
```
Source file → target page. Resolve target to node id. Edge `type: "link"`, no predicate label.

*b. Typed relations (ontology-active only):* Read each page's `relations:` and `context.relates_to` frontmatter arrays. For each entry create an edge with:
```json
{ "from": "<source id>", "to": "<target id>", "type": "typed", "predicate": "owns", "label": "owns" }
```
When a predicate has an `inverse` declared, draw a single edge with an arrowhead (do not duplicate).

**3. Infer edges (INFERRED)** — Topically related pages without explicit links. Include `confidence` score. If < 0.5 → type `AMBIGUOUS`, color `#BDBDBD`. When ontology is active, prefer inferring edges whose predicate exists in `relations:` over free-form inference.

**4. Write `graph/graph.json`**:
```json
{ "nodes": [...], "edges": [...], "ontology_active": true, "phases": ["Discover","Build","Validate"], "built": "YYYY-MM-DD" }
```

**5. Write `graph/graph.html`** — Use the self-contained vis.js template in `references/graph-html.md`. Inline graph.json content directly into the HTML.

**6. Summary** — Report total nodes by type, total edges by type, top 5 most-connected hubs.

Append to `wiki/log.md`: `## [YYYY-MM-DD] graph | Knowledge graph rebuilt`

---

## /wiki-sources

No arguments. Lists all entries in `wiki/history.json`.

1. Read `wiki/history.json` (if missing → respond: *"No sources ingested yet. Run `/wiki-ingest <file>` to add your first source."*)
2. Print a table of all entries sorted by `last_updated` descending:

```
| Slug | Title | Ingested | Last Updated | Status |
|------|-------|----------|--------------|--------|
| my-article | My Article | 2026-04-21 | 2026-04-21 | active |
```

3. For each active source, list its `pages_created`, `entities_created`, `concepts_created`.

---

## /wiki-update

**$ARGUMENTS** = `<slug>` (the kebab-case source slug to re-ingest)

1. Read `wiki/history.json`; if the slug is absent or `status` is `"deleted"` → error: *"No active source with slug '<slug>'. Run `/wiki-sources` to list available sources."*
2. Find the original document at `source_file` (from history entry); if missing → error: *"Original file not found at <source_file>. Cannot update."*
3. Re-run the full **Agent-Based Ingest** flow for this slug (steps 1–14), treating it as an update:
   - **Do not move** the original file again — it is already archived
   - Overwrite `wiki/sources/<slug>.md` (do not create a duplicate)
   - For entity/concept pages, merge new content with existing pages (do not overwrite if only minor changes)
   - Update `wiki/index.md` entry if the title changed
4. In `wiki/history.json`, update `last_updated` to now and refresh `entities_created`/`concepts_created` lists
5. Append to `wiki/log.md`: `## [YYYY-MM-DD] wiki-update | <slug>`
6. Output: `✅ Updated source: <slug>. Run /wiki-graph to regenerate the knowledge graph.`

---

## /wiki-delete

**$ARGUMENTS** = `<slug>` (the kebab-case source slug to remove)

1. Read `wiki/history.json`; if the slug is absent or already `"deleted"` → error: *"No active source with slug '<slug>'. Run `/wiki-sources` to list available sources."*
2. Show the user what will be deleted and ask for confirmation:
   - Source page: `wiki/sources/<slug>.md`
   - Original archive: `source_file` value from history entry
   - Entity/concept pages from `entities_created`/`concepts_created` that are **not referenced by any other source** (check `wiki/index.md` and other source frontmatter `sources:` lists before deleting)
3. After confirmation:
   a. Delete `wiki/sources/<slug>.md`
   b. Delete the original archive at `source_file`
   c. For each entity/concept in `entities_created`: delete only if no other source page references it via `[[WikiLink]]` or `sources:` frontmatter
   d. Remove the entry from `wiki/index.md` (source line and any orphaned entity/concept lines)
   e. Update `wiki/overview.md` — remove references to the deleted source; revise synthesis if needed
4. In `wiki/history.json`, set `"status": "deleted"` and update `last_updated` (do not remove the entry — preserve the audit trail)
5. Append to `wiki/log.md`: `## [YYYY-MM-DD] wiki-delete | <slug>`
6. Output: `✅ Deleted source: <slug>. Run /wiki-lint to check for remaining broken links.`

---

## /wiki-ontology-init

Interactive ontology builder. Produces `wiki/ontology.yaml` + `wiki/ontology-guide.md` by interviewing the user.

**$ARGUMENTS** (all optional):
- No arguments → full interview from Stage 0 through Stage 8
- `--edit <stage>` → revisit one stage (valid: `project`, `actor`, `activity`, `artifact`, `objective`, `resource`, `context`, `workflow`, `relations`)
- `--regen-guide` → only rewrite `wiki/ontology-guide.md` from the existing `wiki/ontology.yaml`
- `--from-template` → skip the interview, copy `references/ontology-template.yaml` to `wiki/ontology.yaml` verbatim for manual editing

### Flow

1. **Load resources:**
   - Read `references/ontology-template.yaml` — the starting skeleton
   - Read `references/ontology-interview.md` — the full interview script (Stages 0–8 with exact question wording and branching rules). **Follow that script precisely.**
   - If `wiki/ontology.yaml` already exists and no `--edit` / `--regen-guide` flag given: ask *"An ontology already exists. (a) edit a stage, (b) full re-interview (overwrites), (c) cancel."*

2. **Run the interview** (see `references/ontology-interview.md`):
   - Stage 0: Project Profiling (type, name, description, period)
   - Stage 1: Actor Axis
   - Stage 2: Activity Axis + workflow phases
   - Stage 3: Artifact Axis
   - Stage 4: Objective Axis
   - Stage 5: Resource Axis (off by default)
   - Stage 6: Context Axis (off by default)
   - Stage 7: Relations Confirmation
   - Stage 8: Review & Save

3. **Write outputs:**
   - `wiki/ontology.yaml` — the populated schema (Write tool, never shell echo)
   - `wiki/ontology-guide.md` — human-readable summary (template in `references/ontology-interview.md`)
   - Append to `wiki/log.md`: `## [YYYY-MM-DD] ontology-init | <N> classes, <M> relations, workflow=<phase_count>`

4. **Seed instance pages (optional):** if the user provided example instances during Stages 1–4 (e.g. specific teams, goals), offer to create stub pages in `wiki/entities/` or `wiki/concepts/` with `class:` frontmatter and "TODO" bodies.

5. **Output:**
   ```
   ✅ Ontology saved to wiki/ontology.yaml
   ✅ Guide saved to wiki/ontology-guide.md
   Active axes: Actor, Activity, Artifact, Objective
   Classes: 14 | Relations: 11 | Phases: 5
   Next: run /wiki-ingest — new ingests will ask for document context.
        /wiki-ontology-validate — check existing instances against the schema.
        /wiki-ontology-init --edit <stage> — revise a single stage.
   ```

---

## /wiki-ontology-show

No arguments. Prints a concise summary of `wiki/ontology.yaml`.

1. If `wiki/ontology.yaml` is absent → respond: *"No ontology configured. Run `/wiki-ontology-init` to create one (optional — the wiki works without it)."*
2. Read `wiki/ontology.yaml` and render:

   ```
   Project: <name> (<type>) — <description>
   Period: <start> → <end>

   Active Axes & Classes:
     Actor    : Person, Team, Role
     Activity : Task, Phase, Meeting, Decision
     Artifact : Document, Deliverable
     Objective: Goal, Milestone, Risk
     (Resource: off)
     (Context : off)

   Workflow: Discover → Design → Build → Validate → Release

   Relations: owns, produces, consumes, achieves, part_of, precedes, authored_by, based_on
   ```

3. Optionally tail with instance counts: *"14 entities, 6 concepts currently tagged with a class."*
4. No `wiki/log.md` append (read-only command).

---

## /wiki-ontology-validate

Checks that all existing instances conform to `wiki/ontology.yaml`. Essentially the ontology checks from `/wiki-lint` (checks 7–12), run in isolation.

### Option A — Python Script (preferred)

```bash
python scripts/ontology_validate.py                 # print report
python scripts/ontology_validate.py --save          # save to wiki/ontology-validation-report.md
python scripts/ontology_validate.py --json          # machine-readable JSON on stdout
```

Graceful behavior:
- If `wiki/ontology.yaml` is absent, exits immediately with an opt-in message.
- If PyYAML is missing, exits with an install hint.
- Appends `## [YYYY-MM-DD] ontology-validate | <N> violations` to `wiki/log.md`.

### Option B — Agent-Based Fallback

1. If `wiki/ontology.yaml` is absent → respond: *"No ontology configured. Nothing to validate."*
2. Load the ontology.
3. Glob every `.md` in `wiki/sources/`, `wiki/entities/`, `wiki/concepts/`, `wiki/syntheses/`. For each:
   - Read frontmatter
   - Check `class:` value is declared in some axis's `default_classes`
   - Check every `relations[].predicate` is declared in `relations:` block
   - Check domain/range match the predicate declaration
   - Check every `context.phase` is in `workflow.phases[].id`
   - Flag missing required properties (where "required" means listed in the class's `properties:` array and the property is absent)
4. Produce a report in the format shown under `/wiki-lint` → *Ontology Violations*.
5. Ask: *"Save to `wiki/ontology-validation-report.md`?"*
6. Append to `wiki/log.md`: `## [YYYY-MM-DD] ontology-validate | <N> violations`

---

## Other Utilities

**Convert PDFs, Word docs, etc. to Markdown before ingesting:**

```bash
python tools/file_to_markdown.py --input_dir raw/pdfs/
```

---

## Gotchas

- **`raw/` is a drop zone** — files are copied to `wiki/originals/` or a custom `--to` folder after ingest; originals remain in `raw/` and are not deleted
- **`--from <folder>` overrides `raw/`** — all files in the specified folder are treated as ingest candidates
- **`--to <folder>` overrides `wiki/originals/`** — a PARA-structured subfolder is created inside the destination; `source_file` frontmatter reflects the new path
- **`--force-new` creates a date-suffixed slug** — use when you want a fresh entry for an updated document version (e.g. `my-article-20260421`); the old entry is preserved
- **`--force-update` skips the duplicate prompt** — use in automated/batch pipelines; equivalent to running `/wiki-update` for each duplicate
- **`--force-new` and `--force-update` are mutually exclusive** — specifying both is an error
- **Single-file duplicate prompts only for active entries** — deleted slugs are silently reused; already-archived slugs in batch mode are skipped with a warning rather than prompted interactively
- **Never modify files in `wiki/originals/`** — they are read-only archives of the original source documents
- **Always update `wiki/index.md`** on every ingest — stale index breaks wiki-query
- **Wikilinks are case-sensitive** — `[[OpenAI]]` ≠ `[[Openai]]`; match the exact filename
- **Source slugs must match filenames** — the slug in frontmatter `sources:` must equal the source `.md` filename without extension
- **`wiki/log.md` is append-only** — never edit past entries, only append new ones
- **`wiki/history.json` preserves deleted entries** — set `status: "deleted"` instead of removing the key; this maintains an audit trail
- **`/wiki-delete` never removes shared pages** — entity/concept pages referenced by other sources survive deletion; always cross-check before deleting
- **`/wiki-update` does not re-archive the original** — the original is already in `wiki/originals/`; re-ingest only updates wiki pages
- **Always use the Write tool for `wiki/history.json`** — never shell echo; read the existing file first, merge the entry, then overwrite
- **All scripts run from the project root** — `Path.cwd()` must be your wiki project directory
- **graph.html is self-contained** — the Python script inlines the JSON; the agent-based fallback must do the same
- **Ontology is a hint, not a constraint** — entities/concepts outside the ontology are still accepted; they just lack `class:` tags. Never refuse to ingest content because it doesn't fit the schema.
- **Ontology absence is the baseline** — every command must continue to work when `wiki/ontology.yaml` does not exist. Ontology features layer on top.
- **Never edit `wiki/ontology.yaml` silently** — only `/wiki-ontology-init` and `/wiki-ontology-init --edit` modify it. Other commands read but never write to it.
- **`ontology-guide.md` is derived** — regenerated from `ontology.yaml`. Users editing `ontology-guide.md` directly will lose changes on `--regen-guide`.
- **Unknown classes/predicates surface in validation, not ingest** — `/wiki-ingest` may write unknown values when the user enters them during interview; they get flagged later by `/wiki-ontology-validate` or `/wiki-lint`. This keeps ingest uninterrupted while still catching drift.
- **Context Interview answers belong in `context:`, not in the page body** — do not duplicate interview answers into the narrative sections of the source page.
- **`--summary-only` skips full-text conversion** — the wiki stores only a metadata + summary page; the original file is the authoritative data source. `/wiki-query` loads the original on demand when the answer requires actual data.
- **summary-only is applied automatically to `.xlsx` and `.pptx`** — to force full conversion of these types, explicitly pass `--no-summary` (not yet implemented; request via issue). For now, rename the file to `.md` before ingesting if full text is needed.
- **`ingest_mode` in `history.json` is informational** — `/wiki-update` re-uses the same strategy as the original ingest unless `--summary-only` is explicitly passed or removed.
- **Do not enumerate cell data in summary-only pages** — key values (up to 5) are enough; the original file is always available via `source_file`.
