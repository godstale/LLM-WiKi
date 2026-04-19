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
