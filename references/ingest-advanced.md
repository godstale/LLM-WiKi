# Ingest Advanced Reference

Loaded by the agent when `/wiki-ingest` is called with non-default flags or non-markdown input files.

---

## Batch Mode

When no specific file is given (or `--from <folder>`):

1. Glob all files in source folder (non-recursive for `raw/`; recursive when `--from` is explicit)
2. For each file, compute slug and check `wiki/history.json`:
   - **`--force-new`**: date-suffix slug (e.g. `my-article-20260421`); skip prompt. If that slug also exists, increment counter (`-20260421-2`, etc.)
   - **`--force-update`**: overwrite existing entry; skip prompt
   - **Neither flag**: skip files with existing active slug; log warning listing skipped files
3. Process each non-skipped file in sequence (single-file ingest steps)
4. Print summary: files processed / pages created / files skipped (with reason) / files copied

**`--batch-defaults`**: interview only the first file fully; reuse its answers as defaults for subsequent files, asking "use same defaults?" (yes/edit/skip) per file.

---

## Destination Folder Rules (`--to <folder>`)

Applies PARA folder structure from `references/folder-managing.md`:

1. Determine PARA category from destination path or content:
   - `00_Inbox` · `01_Projects` · `02_Areas` · `03_Resources` · `04_Archives`
   - If `--to` path already starts with `00_`–`04_`, use as-is
   - Otherwise ask the user which category applies (or infer from content if confident)

2. Create subfolder: `YYYYMMDD_<slug>_<ShortDescription>/` inside the destination
   - Example: `03_Resources/20260420_my-article_Reading-Notes/`
   - Use today's date for `YYYYMMDD`

3. Copy original file(s) into that subfolder; set `source_file` frontmatter to the new path

4. Do NOT create or modify `wiki/originals/` when `--to` is specified

---

## Ingest Strategy Selection

| Priority | Condition | Strategy |
|----------|-----------|----------|
| 1 | `--summary-only` flag | summary-only |
| 2 | `.xlsx` or `.xls` | summary-only |
| 3 | `.pptx` or `.ppt` | summary-only |
| 4 | `.pdf` and page count > 30 | summary-only |
| 5 | Everything else | full |

Announce before proceeding: *"Using summary-only strategy for `<filename>` (reason: <reason>)."*

---

## Full Strategy: Convert Non-text Files

1. **Agent tools first** — invoke the appropriate skill:
   - `.docx` / `.doc` → `docx` skill
   - `.pptx` / `.ppt` → `pptx` skill
   - `.xlsx` / `.xls` → `xlsx` skill
   - `.pdf` → `pdf` skill
   Save extracted text as `<original-name>.md` in the same `raw/` directory.

2. **Fallback:** `python tools/file_to_markdown.py --input_dir raw/`

Proceed with Agent-Based Ingest once `.md` is available.

---

## Summary-Only Ingest

For dense spreadsheets, large PDFs, presentation decks where raw content is not meaningful as prose.

1. **Read the file directly** with the appropriate skill (do not save a converted `.md`):
   - `.xlsx` / `.xls` → `xlsx` skill (sheet names, headers, row counts, key values)
   - `.pptx` / `.ppt` → `pptx` skill (slide titles, section headers, speaker notes)
   - `.pdf` → `pdf` skill (first 3 pages + TOC if present)

2. **Extract metadata:**

   | Field | Source |
   |-------|--------|
   | `title` | File name, title slide, or first heading |
   | `purpose` | Inferred from content type / section headers |
   | `content_type` | `spreadsheet` / `presentation` / `spec` / `report` / `other` |
   | `author` / `team` | Author field, metadata, path context |
   | `created_at` | File metadata, header date, or filename date pattern |
   | `scope` | What the document covers (subject, time period, teams, systems) |
   | `sheet_names` | (spreadsheets) list of sheet names |
   | `slide_count` | (presentations) number of slides |
   | `sections` | Top-level headings or sheet names as bullet list |
   | `key_values` | Up to 5 important data points visible without deep reading |

3. **Write `wiki/sources/<slug>.md`:**

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
   <Subject, time period, teams, systems.>

   ## Structure
   <Bullet list of sheets / sections / slides with one-line descriptions.>

   ## Key Values
   <Up to 5 important data points, figures, or decisions.>

   ## How to Use
   Load the original file at `<source_file>` for full data.
   ```

4. **Skip deep entity/concept extraction** — only create pages when a name is explicit and prominent (e.g. team name in the filename). Do not enumerate every cell reference.

5. Continue from ingest **step 6** (copy original, update index, log).

**When `/wiki-query` loads a summary-only source:** the source page answers "what is this file and where is it." If the query requires actual data, read `source_file` on demand and answer from raw content — then optionally offer to update the source page with newly surfaced data.

---

## Context Interview (ontology-aware)

Run after loading `wiki/ontology.yaml` (step 2a) and before writing the source page (step 5). Skip when `wiki/ontology.yaml` is absent or `--no-interview` is passed.

### Procedure

1. **Scan document** for auto-inferable values:
   - `artifact_type`: match file patterns and content cues (e.g. "retrospective" → Meeting, "decision doc" → Decision, default → Document)
   - `authored_at`: extract from date header, frontmatter, or filename
   - `authored_by`: extract from explicit author line, email signature, or git metadata
   - `relates_to` candidates: entities/concepts mentioned 2+ times that are in the wiki or ontology

2. **Present inferred values and gaps:**

   ```
   🔍 Document Context Interview — raw/<filename>

   Auto-detected (confirm or correct):
     ✓ artifact_type : Meeting           (keyword match: "retrospective")
     ✓ authored_at   : 2026-04-18        (from document header)
     ? authored_by   : ?                 (not detected)
     ? phase         : ?                 (ontology phases: Discover / Build / Validate)
     ? relates_to    : detected mentions: TeamAlpha, SprintGoal-Q2

   Please clarify (answer all or skip any):
     Q1. 작성자는? Actor instance — [Alice, Bob, Carol] 또는 +new
     Q2. Phase? [Discover / Build / Validate]
     Q3. Activity instance? 예: sprint-12, design-review-01
     Q4. 감지된 mentions의 관계?
         - TeamAlpha     → [part_of / owned_by / authored_by / skip]
         - SprintGoal-Q2 → [achieves / references / part_of / skip]
   ```

3. **Inline schema validation — act immediately, do not defer:**
   - Phase not in `workflow.phases[].id` → warn; offer to pick an existing phase or add the new one to the ontology
   - Unknown `class:` → warn; show valid classes from the ontology; offer to correct or proceed as-is
   - Unknown `relations[].predicate` → warn; show valid predicates; offer to correct or proceed as-is
   - Missing required properties for the chosen `class:` (fields listed in `axes.<Axis>.default_classes.<ClassName>.properties`) → list the missing fields; offer to fill now or skip (will appear again in `/wiki-ontology-validate`)
   - New target names → offer: *"`<name>` is new. Create stub page? (yes/no)"* → on yes, create minimal page with "TODO" body
   - Violations do **not** block ingest — all are collected and printed as a `⚠ Schema warnings` block at the end of ingest (step 5)

4. **Write answers to source frontmatter** under `context:` block — schema per `references/ontology-commands.md` (Page Frontmatter with Ontology section)

5. **Ingest-time schema summary:** After writing all pages for this source, if any violations were collected in step 3, print:

   ```
   ⚠ Schema warnings for <slug>:
   - Unknown class `ClassName` — valid classes: [Person, Team, Role, ...]
   - Missing required properties for Task: owner, deadline
   - Unknown predicate `custom_rel` — valid predicates: [owns, produces, achieves, ...]
   Run /wiki-ontology-validate for a full cross-wiki report.
   ```

   Omit this block entirely when there are no warnings.

6. **Propagate to entity/concept pages:** write inverse predicates where declared:
   - `owns` ↔ `owned_by` (bidirectional)
   - `part_of` ↔ `contains` (bidirectional)
   - `achieves` → no declared inverse

---

## Hierarchical Index Management

The wiki uses an N-level hierarchical categorization system for `wiki/index.md`.

### Category Syntax
- Use `/` as a separator for levels (e.g., `Hobby/Travel/SouthAmerica`).
- Case-sensitive; prefer TitleCase or established project terms.

### Default Top-Level Categories (Level 1)
The skill provides these as the foundation. Always try to map new content to one of these first:
- `정치`: 국내외 정치, 행정, 외교.
- `경제/경영`: 금융, 산업, 기업, 재테크.
- `기술/과학`: IT, AI, 기초과학, 우주, 환경.
- `사회`: 교육, 노동, 사건사고, 인구, 지역이슈.
- `문화/생활`: 예술, 여행, 건강, 라이프스타일.
- `기타`: 개인자료, 시스템/에이전트 관련 자료, 기타 미분류 자료.

### Index Markdown Mapping
Map levels to Markdown headers in `wiki/index.md`:
- **Level 1** (`Hobby`) → `## Hobby`
- **Level 2** (`Hobby/Cycling`) → `### Cycling`
- **Level 3** (`Hobby/Travel/SouthAmerica`) → `#### SouthAmerica`
- (and so on)

### Management Rules
1. **Dynamic Creation:** If a specific sub-category (Level 2+) is required by content but doesn't exist, create it under the appropriate parent.
2. **Modification:** If a category path changes, update all entries under that section and move the section header.
3. **Deletion:** If a category section becomes empty after a deletion, remove the header.
4. **Maintenance:** Always maintain entries as `- [Title](sources/slug.md) — mandatory summary` under the most specific matching header.

---

## Argument Parsing Rules

- File path (has extension or resolves to a file) → single-file ingest
- Folder path (no extension, resolves to a directory) → treat as `--from <folder>`
- `--from` and `--to` can be combined with a single file path
- `--no-copy` + `--to` together → warn the user and abort
- `--force-new` + `--force-update` together → warn the user and abort
- `--summary-only` is compatible with all other flags

---

## history.json Entry Schema

Written in step 12 of Agent-Based Ingest. Always use the **Write tool** — read existing file first, merge the entry, then overwrite.

```json
{
  "<slug>": {
    "slug": "<slug>",
    "title": "Page Title",
    "ingested_at": "ISO8601",
    "last_updated": "ISO8601",
    "source_file": "wiki/originals/<slug>.md",
    "pages_created": ["sources/<slug>.md"],
    "entities_created": ["entities/EntityName.md"],
    "concepts_created": ["concepts/ConceptName.md"],
    "ingest_mode": "full|summary-only",
    "status": "active"
  }
}
```

| Field | Description |
|-------|-------------|
| `ingested_at` | Set only on first ingest; never overwritten |
| `last_updated` | Updated on every ingest/update |
| `entities_created` | Paths relative to `wiki/` |
| `status` | `"active"` or `"deleted"` — never remove deleted entries |
