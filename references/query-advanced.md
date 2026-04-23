# Query Advanced Reference

Loaded when `/wiki-query` uses structural filters (class:, type:, AND/OR/NOT, dotted field paths).

---

## Structural Filter Syntax

If a query begins with `class:`, `type:`, `tags:`, or any dotted field path, and/or uses `AND`/`OR`/`NOT`, treat it as a structural filter rather than semantic search.

### Grammar

```
expr    := term (('AND' | 'OR') term)*
term    := 'NOT'? (atom | '(' expr ')')
atom    := field op value
field   := IDENT ('.' IDENT)*          e.g. class, context.phase, properties.owner
op      := ':' | '=' | '!=' | '~='     (':' == '='; '~=' is substring/membership)
value   := QUOTED_STRING | BARE_WORD
```

### Semantics

- Field lookup = dotted path on page frontmatter dict. Missing field = never matches.
- `=` on a list (e.g. `tags=draft`) → list contains the value as an element
- `=` on a scalar → case-insensitive equality
- `~=` → substring match (for lists: any element contains the substring)
- `!=` → negation of `=`; pages *without* the field **do** match `!=`

### Examples

```
class:Ticket AND context.phase=alpha
type:source AND tags~=meeting
(class:Risk AND properties.impact=high) OR class:Goal
NOT type=entity
what are the main themes?       # plain natural-language query (unchanged)
```

---

## Option A — Python Script (preferred for structural filters)

```bash
python scripts/query_filter.py "class:Ticket AND context.phase=alpha"
python scripts/query_filter.py --list-fields       # print available frontmatter fields
python scripts/query_filter.py --paths-only "class:Goal"   # pipe-friendly output
```

The script reads every page's frontmatter, runs the parser + evaluator, and prints matching paths. The agent then reads the matched pages and synthesizes an answer (query steps 3–6).

---

## Option B — Agent-Based Structural Query

When `wiki/ontology.yaml` exists and a structural filter is detected:

1. Either invoke `scripts/query_filter.py` (preferred) or parse the expression manually
2. Glob `wiki/entities/` and `wiki/concepts/`; match pages whose frontmatter satisfies the constraints
3. For source pages, match `class:` and `context.*` fields
4. Return matching pages as a structured list with links, then optionally synthesize narrative
5. If no match → *"no instances match"* and suggest relaxing the filter
