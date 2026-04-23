# Ontology Commands Reference

Loaded when running `/wiki-ontology-init`, `/wiki-ontology-show`, `/wiki-ontology-validate`,
or when ontology-aware checks are needed in `/wiki-lint` or `/wiki-graph`.

---

## /wiki-ontology-init

Interactive ontology builder. Produces `wiki/ontology.yaml` + `wiki/ontology-guide.md`.

**Arguments:**
- *(none)* → full interview (Stages 0–8)
- `--edit <stage>` → revisit one stage (`project`, `actor`, `activity`, `artifact`, `objective`, `resource`, `context`, `workflow`, `relations`)
- `--regen-guide` → only rewrite `wiki/ontology-guide.md` from existing `wiki/ontology.yaml`
- `--from-template` → copy `references/ontology-template.yaml` verbatim; skip interview

**Flow:**

1. Read `references/ontology-template.yaml` (skeleton) and `references/ontology-interview.md` (full interview script — follow it precisely)
2. If `wiki/ontology.yaml` exists and no flags → ask: *(a) edit a stage, (b) full re-interview (overwrites), (c) cancel*
3. Run interview per `references/ontology-interview.md`:
   - Stage 0: Project Profiling (type, name, description, period)
   - Stage 1: Actor Axis
   - Stage 2: Activity Axis + workflow phases
   - Stage 3: Artifact Axis
   - Stage 4: Objective Axis
   - Stage 5: Resource Axis (off by default)
   - Stage 6: Context Axis (off by default)
   - Stage 7: Relations Confirmation
   - Stage 8: Review & Save
4. Write `wiki/ontology.yaml` (Write tool — never shell echo) and `wiki/ontology-guide.md`
5. Append to `wiki/log.md`: `## [YYYY-MM-DD] ontology-init | <N> classes, <M> relations, workflow=<phase_count>`
6. Offer to create stub entity/concept pages for named instances given during interview

**Output:**
```
✅ Ontology saved to wiki/ontology.yaml
✅ Guide saved to wiki/ontology-guide.md
Active axes: Actor, Activity, Artifact, Objective
Classes: 14 | Relations: 11 | Phases: 5
Next: /wiki-ingest | /wiki-ontology-validate | /wiki-ontology-init --edit <stage>
```

---

## /wiki-ontology-show

1. If `wiki/ontology.yaml` absent → *"No ontology configured. Run `/wiki-ontology-init` to create one (optional — the wiki works without it)."*
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

3. Tail with instance counts: *"14 entities, 6 concepts currently tagged with a class."*
4. No `wiki/log.md` append (read-only command).

---

## /wiki-ontology-validate

Checks all existing instances against `wiki/ontology.yaml`.

**Option A — Python Script (preferred):**
```bash
python scripts/ontology_validate.py
python scripts/ontology_validate.py --save    # save to wiki/ontology-validation-report.md
python scripts/ontology_validate.py --json    # machine-readable JSON on stdout
```

**Option B — Agent-based:**

1. If `wiki/ontology.yaml` absent → *"No ontology configured. Nothing to validate."*
2. Load the ontology
3. Glob every `.md` in `wiki/sources/`, `wiki/entities/`, `wiki/concepts/`, `wiki/syntheses/`. For each page, run checks at two severity levels:

   **ERROR** (schema contract broken — must fix):
   - `class:` is not declared in any axis's `default_classes`
   - `relations[].predicate` is not declared in `relations:` block
   - `context.phase` is not in `workflow.phases[].id`
   - Domain/range mismatch on a declared predicate

   **WARNING** (data gap — should fix):
   - Properties listed in the class's `properties:` array are absent from the page frontmatter
   - Activity instances with no `context.phase` when phases are declared

4. Produce violation report grouped by severity (see format below)
5. Ask: *"Save to `wiki/ontology-validation-report.md`?"*
6. Append to `wiki/log.md`: `## [YYYY-MM-DD] ontology-validate | <N> errors, <M> warnings`

---

## Ontology Checks for /wiki-lint (checks 7–12)

Run only when `wiki/ontology.yaml` exists. Add to the lint report after standard checks 1–6.

**7. Unknown class** *(ERROR)* — `class:` values not in any axis's `default_classes`
**8. Unknown predicate** *(ERROR)* — `relations[].predicate` not declared in `relations:` block
**9. Unknown phase** *(ERROR)* — `context.phase` not in `workflow.phases[].id`
**10. Domain/range violation** *(ERROR)* — source class not in predicate's `domain`, or target class not in `range`
   - Example: `{predicate: produces}` on `class: Document` — `produces` expects `domain: [Activity]`
**11. Missing required properties** *(WARNING)* — instances with a declared `class:` that are missing properties listed in that class's `properties:` array. Report each missing field by name (e.g. "Task `wiki/entities/TaskX.md` missing: owner, deadline").
**12. Workflow gaps** *(WARNING)* — Activity instances with no `context.phase`, or phases with zero instances

### Ontology Violations Report Format

```markdown
## Ontology Violations

### Errors (N) — schema contract broken
- Unknown class `ClassName` in `wiki/entities/Foo.md`
- Unknown predicate `custom_relation` in `wiki/sources/bar.md`
- Unknown phase `Shipping` in `wiki/sources/baz.md` (declared phases: Discover, Build, Validate)
- Domain violation: `{predicate: produces}` on `wiki/entities/TeamAlpha.md` (class: Team) — expects domain [Activity]

### Warnings (M) — data gaps
- Missing property `owner` on Task instance `wiki/entities/TaskX.md`
- Missing property `deadline` on Task instance `wiki/entities/TaskX.md`
- Phase `Validate` has no associated Activity instances
```

---

## Ontology-Aware Graph Building (/wiki-graph)

When `wiki/ontology.yaml` exists, override type-based node coloring with axis-based colors:

| Axis | Color |
|------|-------|
| Actor | #1976D2 |
| Activity | #388E3C |
| Artifact | #F57C00 |
| Objective | #7B1FA2 |
| Resource | #5D4037 |
| Context | #546E7A |

- Set `group` = axis name (enables vis.js clustering by axis)
- Add `phase` to the node (for phase-labeled lane positioning when workflow is declared)

**Typed edges** (from `relations:` and `context.relates_to` frontmatter arrays):
```json
{ "from": "<source id>", "to": "<target id>", "type": "typed", "predicate": "owns", "label": "owns" }
```
When a predicate has a declared `inverse`, draw a single directed edge — do not create a duplicate reverse edge.

**graph.json extended format when ontology is active:**
```json
{ "nodes": [...], "edges": [...], "ontology_active": true, "phases": ["Discover","Build","Validate"], "built": "YYYY-MM-DD" }
```

---

## Ontology-Specific Gotchas

- **Ontology is opt-in** — every command works without `wiki/ontology.yaml`; ontology features are additive
- **Never edit `wiki/ontology.yaml` silently** — only `/wiki-ontology-init` and `--edit` may modify it
- **`ontology-guide.md` is derived** — regenerated from `ontology.yaml`; direct edits are lost on `--regen-guide`
- **Unknown classes/predicates do not block ingest** — printed as inline `⚠ Schema warnings` at end of ingest; full report at `/wiki-ontology-validate`
- **Context Interview answers belong in `context:`, not in the page body** — do not duplicate into narrative sections
- **`--summary-only` sources are read on demand by `/wiki-query`** — original file is the authoritative data source
- **Entity/concept frontmatter is derived from the ontology, not from fixed templates** — field names must match the class's `properties:` array in `wiki/ontology.yaml`

---

## Schema Migration

When you change `wiki/ontology.yaml` (rename a class, remove a property, change predicate domain/range, modify phase ids):

1. Increment `project.schema_version` in `wiki/ontology.yaml`
2. Run `/wiki-ontology-validate` — it lists all pages that now violate the updated schema
3. For each ERROR: update the page frontmatter, or run `/wiki-update <slug>` to re-derive from the original source
4. For each WARNING: fill missing properties directly on the page, or leave for later
5. Append to `wiki/log.md`: `## [YYYY-MM-DD] schema-migration | v<N> → v<N+1>: <what changed>`

**Breaking changes** (must migrate): class rename or removal, property rename or removal, predicate rename or removal, phase id change.
**Non-breaking changes** (no migration needed): adding a new class, property, predicate, or phase; changing descriptions.

---

## Page Frontmatter with Ontology

When `wiki/ontology.yaml` is active, the ontology class definition is the **authoritative schema** for entity and concept pages. Derive field names from `axes.<Axis>.default_classes.<ClassName>.properties` — do not invent fields not declared there.

### Source page — `context:` block

Added by `/wiki-ingest` during the Context Interview:

```yaml
---
title: "Sprint 12 Retrospective"
type: source
class: Meeting                   # ontology class name
tags: [meeting]
date: 2026-04-18
source_file: wiki/originals/sprint12-retro.md
sources: []
last_updated: 2026-04-18
context:
  authored_by: Alice             # Actor instance name (must match entity page)
  authored_at: 2026-04-18
  phase: Build                   # workflow.phases[].id value
  activity: sprint-12            # Activity instance name
  artifact_type: Meeting         # class from Artifact or Activity axis
  relates_to:
    - {target: TeamAlpha,     predicate: part_of}
    - {target: SprintGoal-Q2, predicate: achieves}
---
```

### Entity page — `class:` and `relations:` blocks

```yaml
---
title: "TeamAlpha"
type: entity
class: Team                      # must match a class in wiki/ontology.yaml
tags: []
sources: [sprint12-retro, design-doc-v2]
last_updated: 2026-04-18
properties:                      # fields from class's properties: array
  lead: Alice
  domain: backend-services
relations:
  - {predicate: owns,    target: TaskX}
  - {predicate: part_of, target: ProjectAlpha}
---
```

### Concept page — same extension pattern

```yaml
---
title: "SprintGoal-Q2"
type: concept
class: Goal                      # typically from Objective or Context axis
sources: [sprint12-retro]
last_updated: 2026-04-18
properties:
  parent_goal: YearlyOKR-2026
  target_date: 2026-06-30
  metric: "<measurable target>"
  status: on-track
relations:
  - {predicate: part_of, target: YearlyOKR-2026}
---
```

### Field rules

- `class:` must match a class name declared in `wiki/ontology.yaml` under some axis's `default_classes`.
- `relations[].predicate` must match a key under `relations:` in `wiki/ontology.yaml`.
- `relations[].target` is an entity/concept name — case-sensitive, must match the page filename without extension.
- `context.phase` must match a `workflow.phases[].id` when phases are declared.
- All ontology fields are optional — omitting them degrades gracefully to non-ontology behavior.
- Unknown values are not an ingest-time error; they produce inline `⚠ Schema warnings` and are fully reported by `/wiki-ontology-validate`.
