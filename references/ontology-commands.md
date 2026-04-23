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
3. Glob every `.md` in `wiki/sources/`, `wiki/entities/`, `wiki/concepts/`, `wiki/syntheses/`. For each:
   - Check `class:` is declared in some axis's `default_classes`
   - Check every `relations[].predicate` is declared in `relations:` block
   - Check domain/range match the predicate declaration
   - Check `context.phase` is in `workflow.phases[].id`
   - Flag missing properties listed in class's `properties:` array
4. Produce violation report (see format below)
5. Ask: *"Save to `wiki/ontology-validation-report.md`?"*
6. Append to `wiki/log.md`: `## [YYYY-MM-DD] ontology-validate | <N> violations`

---

## Ontology Checks for /wiki-lint (checks 7–12)

Run only when `wiki/ontology.yaml` exists. Add to the lint report after standard checks 1–6.

**7. Unknown class** — `class:` values not in any axis's `default_classes`
**8. Unknown predicate** — `relations[].predicate` not declared in `relations:` block
**9. Unknown phase** — `context.phase` not in `workflow.phases[].id`
**10. Domain/range violation** — source class not in predicate's `domain`, or target class not in `range`
   - Example: `{predicate: produces}` on `class: Document` — `produces` expects `domain: [Activity]`
**11. Cardinality anomalies** (best-effort) — instances missing properties suggested by the class (e.g. Task needs `owner`). Flagged as "potential gap," not error.
**12. Workflow gaps** — Activity instances with no `context.phase`, or phases with zero instances

### Ontology Violations Report Section

```markdown
## Ontology Violations (N found)
- Unknown class `ClassName` in `wiki/entities/Foo.md`
- Unknown predicate `custom_relation` in `wiki/sources/bar.md`
- Unknown phase `Shipping` in `wiki/sources/baz.md` (declared phases: Discover, Build, Validate)
- Domain violation: `{predicate: produces}` on `wiki/entities/TeamAlpha.md` (class: Team) — expects domain [Activity]
- Missing required property `owner` on Task instance `wiki/entities/TaskX.md`
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
- **Unknown classes/predicates do not block ingest** — they surface in `/wiki-ontology-validate`; ingest remains uninterrupted
- **Context Interview answers belong in `context:`, not in the page body** — do not duplicate into narrative sections
- **`--summary-only` sources are read on demand by `/wiki-query`** — original file is the authoritative data source
