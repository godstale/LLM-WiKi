#!/usr/bin/env python3
from __future__ import annotations

"""
Structural filter for /wiki-query — filter wiki pages by frontmatter fields
before semantic synthesis.

Usage:
    python scripts/query_filter.py "class:Ticket AND context.phase=alpha"
    python scripts/query_filter.py "type:source AND NOT tags~=draft"
    python scripts/query_filter.py --list-fields    # print available fields

Grammar (informal):
    expr    := term (('AND' | 'OR') term)*
    term    := 'NOT'? (atom | '(' expr ')')
    atom    := field op value
    field   := IDENT ('.' IDENT)*          e.g. class, context.phase, properties.owner
    op      := ':' | '=' | '!=' | '~='     (':' == '='; '~=' is substring/membership)
    value   := QUOTED_STRING | BARE_WORD    (bare words may not contain space, paren, or op chars)

Semantics:
    - Field lookup uses dotted path on the frontmatter dict. Missing = never matches.
    - `=`  on list field  → list contains value (exact element).
    - `=`  on scalar      → scalar equals value (string equality, case-insensitive).
    - `~=` on list        → any element contains the value as substring.
    - `~=` on scalar      → scalar contains the value as substring (case-insensitive).
    - `!=` is negation of `=`.

Returns the list of matching page paths (one per line).
"""

import argparse
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path.cwd()
WIKI_DIR = REPO_ROOT / "wiki"
FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


# ── Tokenizer ───────────────────────────────────────────────────────

class Token:
    __slots__ = ("kind", "value", "pos")
    def __init__(self, kind, value, pos):
        self.kind, self.value, self.pos = kind, value, pos
    def __repr__(self):
        return f"Token({self.kind}, {self.value!r})"


KEYWORDS = {"AND", "OR", "NOT"}
_OPERATORS = (":", "=", "!=", "~=")


def tokenize(src: str) -> list[Token]:
    """Emit tokens: LPAREN, RPAREN, AND, OR, NOT, FIELD, OP, VALUE, EOF."""
    tokens: list[Token] = []
    i, n = 0, len(src)

    while i < n:
        c = src[i]

        if c.isspace():
            i += 1
            continue

        if c == "(":
            tokens.append(Token("LPAREN", "(", i)); i += 1; continue
        if c == ")":
            tokens.append(Token("RPAREN", ")", i)); i += 1; continue

        # Operators — check 2-char ops first
        if src.startswith("!=", i):
            tokens.append(Token("OP", "!=", i)); i += 2; continue
        if src.startswith("~=", i):
            tokens.append(Token("OP", "~=", i)); i += 2; continue
        if c in (":", "="):
            tokens.append(Token("OP", "=" if c == ":" else c, i)); i += 1; continue

        # Quoted string — VALUE
        if c in ("'", '"'):
            quote = c
            j = i + 1
            buf = []
            while j < n and src[j] != quote:
                if src[j] == "\\" and j + 1 < n:
                    buf.append(src[j + 1]); j += 2
                else:
                    buf.append(src[j]); j += 1
            if j >= n:
                raise ValueError(f"Unterminated string at {i}")
            tokens.append(Token("VALUE", "".join(buf), i)); i = j + 1; continue

        # Bare word — FIELD (if followed by op or dot) or VALUE (otherwise)
        if c.isalnum() or c in "_-.":
            j = i
            while j < n and (src[j].isalnum() or src[j] in "_-.@/"):
                j += 1
            word = src[i:j]
            upper = word.upper()
            if upper in KEYWORDS:
                tokens.append(Token(upper, upper, i))
            else:
                # Decide FIELD vs VALUE by peeking at the next non-space char
                k = j
                while k < n and src[k].isspace():
                    k += 1
                if k < n and (src[k] in ":=" or src.startswith("!=", k) or src.startswith("~=", k)):
                    tokens.append(Token("FIELD", word, i))
                else:
                    tokens.append(Token("VALUE", word, i))
            i = j
            continue

        raise ValueError(f"Unexpected character {c!r} at position {i}")

    tokens.append(Token("EOF", "", n))
    return tokens


# ── AST nodes ───────────────────────────────────────────────────────

class Node: pass

class Cmp(Node):
    def __init__(self, field: str, op: str, value: str):
        self.field, self.op, self.value = field, op, value
    def __repr__(self): return f"Cmp({self.field!r} {self.op} {self.value!r})"

class Not(Node):
    def __init__(self, child: Node): self.child = child
    def __repr__(self): return f"Not({self.child!r})"

class And(Node):
    def __init__(self, children: list[Node]): self.children = children
    def __repr__(self): return f"And({self.children!r})"

class Or(Node):
    def __init__(self, children: list[Node]): self.children = children
    def __repr__(self): return f"Or({self.children!r})"


# ── Parser (recursive descent) ──────────────────────────────────────

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    def peek(self, offset: int = 0) -> Token:
        return self.tokens[self.pos + offset]

    def eat(self, *kinds: str) -> Token:
        tok = self.peek()
        if tok.kind not in kinds:
            raise ValueError(f"Expected {kinds} at pos {tok.pos}, got {tok.kind} {tok.value!r}")
        self.pos += 1
        return tok

    def parse(self) -> Node:
        node = self.parse_or()
        if self.peek().kind != "EOF":
            raise ValueError(f"Unexpected trailing token at pos {self.peek().pos}: {self.peek().value!r}")
        return node

    def parse_or(self) -> Node:
        left = self.parse_and()
        terms = [left]
        while self.peek().kind == "OR":
            self.eat("OR")
            terms.append(self.parse_and())
        return Or(terms) if len(terms) > 1 else left

    def parse_and(self) -> Node:
        left = self.parse_term()
        terms = [left]
        # AND is the default operator when two terms are juxtaposed, but we require explicit
        # AND here to keep the grammar unambiguous.
        while self.peek().kind == "AND":
            self.eat("AND")
            terms.append(self.parse_term())
        return And(terms) if len(terms) > 1 else left

    def parse_term(self) -> Node:
        if self.peek().kind == "NOT":
            self.eat("NOT")
            return Not(self.parse_term())
        if self.peek().kind == "LPAREN":
            self.eat("LPAREN")
            node = self.parse_or()
            self.eat("RPAREN")
            return node
        return self.parse_atom()

    def parse_atom(self) -> Cmp:
        field_tok = self.eat("FIELD")
        op_tok = self.eat("OP")
        value_tok = self.eat("VALUE")
        return Cmp(field_tok.value, op_tok.value, value_tok.value)


def parse_filter(src: str) -> Node:
    tokens = tokenize(src)
    return Parser(tokens).parse()


# ── Evaluator ───────────────────────────────────────────────────────

def _get_field(data: dict, dotted: str):
    """Follow `a.b.c` through nested dicts. Returns None if any hop is missing."""
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
        if cur is None:
            return None
    return cur


def _norm(x):
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    return str(x)


def _cmp_eq(field_val, target: str) -> bool:
    if field_val is None:
        return False
    if isinstance(field_val, list):
        return any(_norm(v) == target or (_norm(v) or "").lower() == target.lower()
                   for v in field_val)
    v = _norm(field_val)
    return v == target or (v or "").lower() == target.lower()


def _cmp_contains(field_val, target: str) -> bool:
    if field_val is None:
        return False
    t = target.lower()
    if isinstance(field_val, list):
        return any(t in (_norm(v) or "").lower() for v in field_val)
    return t in (_norm(field_val) or "").lower()


def evaluate(node: Node, page_fm: dict) -> bool:
    if isinstance(node, Cmp):
        val = _get_field(page_fm, node.field)
        if node.op == "=":
            return _cmp_eq(val, node.value)
        if node.op == "!=":
            return not _cmp_eq(val, node.value)
        if node.op == "~=":
            return _cmp_contains(val, node.value)
        raise ValueError(f"Unknown operator {node.op!r}")
    if isinstance(node, Not):
        return not evaluate(node.child, page_fm)
    if isinstance(node, And):
        return all(evaluate(c, page_fm) for c in node.children)
    if isinstance(node, Or):
        return any(evaluate(c, page_fm) for c in node.children)
    raise ValueError(f"Unknown node {type(node).__name__}")


# ── Page scanning ───────────────────────────────────────────────────

def read_file(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return path.read_text(encoding="utf-16")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1")


def parse_frontmatter(content: str) -> dict:
    m = FM_RE.match(content)
    if not m:
        return {}
    try:
        import yaml
        data = yaml.safe_load(m.group(1))
        return data if isinstance(data, dict) else {}
    except ImportError:
        print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
        sys.exit(2)
    except Exception:
        return {}


def all_wiki_pages() -> list[Path]:
    skip = {"index.md", "log.md", "lint-report.md",
            "ontology-validation-report.md", "overview.md",
            "ontology-guide.md"}
    return [p for p in WIKI_DIR.rglob("*.md") if p.name not in skip]


def collect_fields(pages: list[Path]) -> set[str]:
    """Flatten all dotted field paths found in all page frontmatters (for --list-fields)."""
    fields: set[str] = set()

    def walk(obj, prefix: str):
        if isinstance(obj, dict):
            for k, v in obj.items():
                path = f"{prefix}.{k}" if prefix else k
                fields.add(path)
                walk(v, path)

    for p in pages:
        fm = parse_frontmatter(read_file(p))
        walk(fm, "")
    return fields


# ── CLI ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Structural filter for /wiki-query")
    ap.add_argument("filter", nargs="?", help="Filter expression (e.g. 'class:Task AND context.phase=build')")
    ap.add_argument("--list-fields", action="store_true",
                    help="List frontmatter fields used across the wiki")
    ap.add_argument("--paths-only", action="store_true",
                    help="Print only matching file paths (no count header)")
    args = ap.parse_args()

    pages = all_wiki_pages()

    if args.list_fields:
        for f in sorted(collect_fields(pages)):
            print(f)
        return

    if not args.filter:
        ap.print_help()
        sys.exit(1)

    try:
        ast = parse_filter(args.filter)
    except ValueError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        sys.exit(2)

    matches: list[Path] = []
    for p in pages:
        fm = parse_frontmatter(read_file(p))
        if not fm:
            continue
        try:
            if evaluate(ast, fm):
                matches.append(p)
        except ValueError as e:
            print(f"Eval error on {p}: {e}", file=sys.stderr)

    if not args.paths_only:
        print(f"# {len(matches)} match(es) for: {args.filter}")
    for p in matches:
        print(p.relative_to(REPO_ROOT).as_posix())


if __name__ == "__main__":
    main()
