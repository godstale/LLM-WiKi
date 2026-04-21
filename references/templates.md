# LLM Wiki Page Templates

## Source Templates

### Default Source

Use for articles, papers, reports, book chapters, research summaries.

```markdown
---
title: "Source Title"
type: source
tags: []
date: YYYY-MM-DD
source_file: raw/...
sources: []
last_updated: YYYY-MM-DD
---

## Summary
2–4 sentence summary.

## Key Claims
- Claim 1
- Claim 2

## Key Quotes
> "Quote here" — context

## Connections
- [[EntityName]] — how they relate
- [[ConceptName]] — how it connects

## Contradictions
- Contradicts [[OtherPage]] on: ...
```

### Diary / Journal

Use when source is a personal diary or journal entry.

```markdown
---
title: "YYYY-MM-DD Diary"
type: source
tags: [diary]
date: YYYY-MM-DD
source_file: raw/...
sources: []
last_updated: YYYY-MM-DD
---

## Event Summary

## Key Decisions

## Energy & Mood

## Connections

## Shifts & Contradictions
```

### Meeting Notes

Use when source is meeting notes or a transcript.

```markdown
---
title: "Meeting Title"
type: source
tags: [meeting]
date: YYYY-MM-DD
source_file: raw/...
sources: []
last_updated: YYYY-MM-DD
---

## Goal

## Key Discussions

## Decisions Made

## Action Items
```

---

## Entity Page

`wiki/entities/EntityName.md` — TitleCase filename

```markdown
---
title: "Entity Name"
type: entity
tags: []
sources: [slug1, slug2]
last_updated: YYYY-MM-DD
---

One-paragraph description.

## Appearances
- [[source-slug]] — context of appearance
```

---

## Concept Page

`wiki/concepts/ConceptName.md` — TitleCase filename

```markdown
---
title: "Concept Name"
type: concept
tags: []
sources: [slug1, slug2]
last_updated: YYYY-MM-DD
---

One-paragraph definition.

## Discussed In
- [[source-slug]] — how it appears
```

---

## Synthesis Page

`wiki/syntheses/kebab-case-slug.md` — slug derived from the query question

```markdown
---
title: "Query: <short question title>"
type: synthesis
tags: []
sources: [slug1, slug2]
last_updated: YYYY-MM-DD
---

## Question
<original question>

## Answer
<synthesized answer with [[wikilink]] citations>

## Sources
- [[PageName]] — what it contributed
```

---

## Ontology-Extended Fields (Optional)

These fields are added only when `wiki/ontology.yaml` exists. Pages without them still work unchanged.

### Source page — `context:` block

Added by `/wiki-ingest` during the Context Interview. Records the document's position in the project workflow and provenance.

```yaml
---
title: "Sprint 12 Retrospective"
type: source
class: Meeting                   # ontology class name (optional)
tags: [meeting]
date: 2026-04-18
source_file: wiki/originals/sprint12-retro.md
sources: []
last_updated: 2026-04-18
context:
  authored_by: Alice             # Actor instance (wikilink target)
  authored_at: 2026-04-18
  phase: Build                   # workflow phase id
  activity: sprint-12            # Activity instance
  artifact_type: Meeting         # class from Artifact or Activity axis
  relates_to:
    - {target: TeamAlpha,    predicate: part_of}
    - {target: SprintGoal-Q2, predicate: achieves}
---
```

### Entity page — `class:` and `relations:` blocks

```yaml
---
title: "TeamAlpha"
type: entity
class: Team                      # ontology class name (optional)
tags: []
sources: [sprint12-retro, design-doc-v2]
last_updated: 2026-04-18
properties:                      # properties from ontology class definition
  lead: Alice
  domain: backend-services
relations:
  - {predicate: owns,    target: TaskX}
  - {predicate: part_of, target: ProjectAlpha}
---

One-paragraph description.

## Appearances
- [[sprint12-retro]] — attended
```

### Concept page — same extension pattern

Concept pages use the same `class:` / `properties:` / `relations:` fields when the concept maps to an ontology class (typically from `Objective` or `Context` axes — e.g. `Goal`, `Risk`, `Domain`).

```yaml
---
title: "SprintGoal-Q2"
type: concept
class: Goal
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

- All ontology fields are **optional**. Omitting them degrades gracefully to the non-ontology behavior.
- `class:` must match a class name defined in `wiki/ontology.yaml` under some axis's `default_classes`.
- `relations[].predicate` must match a key under `relations:` in `wiki/ontology.yaml`.
- `relations[].target` is an entity/concept name — `[[wikilinks]]` style, case-sensitive, filename-matching.
- `context.phase` must match a `workflow.phases[].id` when phases are defined.
- Unknown class / predicate / phase values are not an ingest-time error — they are surfaced by `/wiki-ontology-validate` as warnings.
