#!/usr/bin/env python3
"""
Build the knowledge graph from the wiki.

Usage:
    python tools/build_graph.py               # full rebuild
    python tools/build_graph.py --open        # open graph.html in browser after build

Outputs:
    graph/graph.json    — node/edge data
    graph/graph.html    — interactive vis.js visualization

Edge types:
    EXTRACTED   — explicit [[wikilink]] in a page
"""

import re
import json
import argparse
import statistics
import webbrowser
from pathlib import Path
from datetime import date

try:
    import networkx as nx
    from networkx.algorithms import community as nx_community
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    print("Warning: networkx not installed. Community detection disabled. Run: pip install networkx")

REPO_ROOT = Path.cwd()
WIKI_DIR = REPO_ROOT / "wiki"
GRAPH_DIR = REPO_ROOT / "graph"
GRAPH_JSON = GRAPH_DIR / "graph.json"
GRAPH_HTML = GRAPH_DIR / "graph.html"
LOG_FILE = WIKI_DIR / "log.md"

# Node type → color mapping
TYPE_COLORS = {
    "source": "#4CAF50",
    "entity": "#2196F3",
    "concept": "#FF9800",
    "synthesis": "#9C27B0",
    "unknown": "#9E9E9E",
}

EDGE_COLORS = {
    "EXTRACTED": "#555555",
    "INFERRED": "#FF5722",
    "AMBIGUOUS": "#BDBDBD",
}


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


def all_wiki_pages() -> list[Path]:
    return [p for p in WIKI_DIR.rglob("*.md")
            if p.name not in ("index.md", "log.md", "lint-report.md")]


def extract_wikilinks(content: str) -> list[str]:
    return list(set(re.findall(r'\[\[([^\]]+)\]\]', content)))


def extract_frontmatter_type(content: str) -> str:
    match = re.search(r'^type:\s*(\S+)', content, re.MULTILINE)
    return match.group(1).strip('"\'') if match else "unknown"


def page_id(path: Path) -> str:
    return path.relative_to(WIKI_DIR).as_posix().replace(".md", "")


def edge_id(src: str, target: str, edge_type: str) -> str:
    return f"{src}->{target}:{edge_type}"


def build_nodes(pages: list[Path]) -> list[dict]:
    nodes = []
    for p in pages:
        content = read_file(p)
        node_type = extract_frontmatter_type(content)
        title_match = re.search(r'^title:\s*"?([^"\n]+)"?', content, re.MULTILINE)
        label = title_match.group(1).strip() if title_match else p.stem
        body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
        preview_lines = [line.strip() for line in body.splitlines() if line.strip()]
        preview = " ".join(preview_lines[:3])[:220]
        nodes.append({
            "id": page_id(p),
            "label": label,
            "type": node_type,
            "color": TYPE_COLORS.get(node_type, TYPE_COLORS["unknown"]),
            "path": str(p.relative_to(REPO_ROOT)),
            "markdown": content,
            "preview": preview,
        })
    return nodes


def build_extracted_edges(pages: list[Path]) -> list[dict]:
    """Pass 1: deterministic wikilink edges."""
    # Build a map from stem (lower) -> page_id for resolution
    stem_map = {p.stem.lower(): page_id(p) for p in pages}
    edges = []
    seen = set()
    for p in pages:
        content = read_file(p)
        src = page_id(p)
        for link in extract_wikilinks(content):
            target = stem_map.get(link.lower())
            if target and target != src:
                key = (src, target)
                if key not in seen:
                    seen.add(key)
                    edges.append({
                        "id": edge_id(src, target, "EXTRACTED"),
                        "from": src,
                        "to": target,
                        "type": "EXTRACTED",
                        "color": EDGE_COLORS["EXTRACTED"],
                        "confidence": 1.0,
                    })
    return edges


def deduplicate_edges(edges: list[dict]) -> list[dict]:
    """Merge duplicate and bidirectional edges, keeping highest confidence."""
    best = {}  # (min(a,b), max(a,b)) -> edge
    for e in edges:
        a, b = e["from"], e["to"]
        key = (min(a, b), max(a, b))
        existing = best.get(key)
        if not existing or e.get("confidence", 0) > existing.get("confidence", 0):
            best[key] = e
    deduped = []
    for edge in best.values():
        rel_type = edge.get("type", "INFERRED")
        edge["id"] = edge.get("id", edge_id(edge["from"], edge["to"], rel_type))
        edge["color"] = edge.get("color", EDGE_COLORS.get(rel_type, EDGE_COLORS["INFERRED"]))
        edge["confidence"] = float(edge.get("confidence", 0.7 if rel_type != "EXTRACTED" else 1.0))
        edge.setdefault("title", "")
        edge.setdefault("label", "")
        deduped.append(edge)
    return deduped


def detect_communities(nodes: list[dict], edges: list[dict]) -> dict[str, int]:
    """Assign community IDs to nodes using Louvain algorithm."""
    if not HAS_NETWORKX:
        return {}

    G = nx.Graph()
    for n in nodes:
        G.add_node(n["id"])
    for e in edges:
        G.add_edge(e["from"], e["to"])

    if G.number_of_edges() == 0:
        return {}

    try:
        communities = nx_community.louvain_communities(G, seed=42)
        node_to_community = {}
        for i, comm in enumerate(communities):
            for node in comm:
                node_to_community[node] = i
        return node_to_community
    except Exception:
        return {}


def generate_report(nodes: list[dict], edges: list[dict], communities: dict[str, int]) -> str:
    """Generate a structured graph health report.

    Analyzes the graph for orphan nodes, hub pages (god nodes),
    fragile inter-community bridges, and overall connectivity health.
    """
    today = date.today().isoformat()
    n_nodes = len(nodes)
    n_edges = len(edges)

    if n_nodes == 0:
        return f"# Graph Insights Report — {today}\n\nWiki is empty — nothing to report.\n"

    # Build NetworkX graph for analysis
    G = nx.Graph()
    for n in nodes:
        G.add_node(n["id"])
    for e in edges:
        G.add_edge(e["from"], e["to"])

    # --- Metrics ---
    degrees = dict(G.degree())
    edges_per_node = n_edges / n_nodes if n_nodes else 0
    density = nx.density(G)

    # Health rating
    if edges_per_node >= 2.0:
        health = "✅ healthy"
    elif edges_per_node >= 1.0:
        health = "⚠️ warning"
    else:
        health = "🔴 critical"

    # Orphans: degree == 0
    orphans = sorted([n for n, d in degrees.items() if d == 0])
    orphan_count = len(orphans)
    orphan_pct = (orphan_count / n_nodes * 100) if n_nodes else 0

    # God nodes: degree > mean + 2*std
    deg_values = list(degrees.values())
    mean_deg = statistics.mean(deg_values) if deg_values else 0
    std_deg = statistics.stdev(deg_values) if len(deg_values) > 1 else 0
    god_threshold = mean_deg + 2 * std_deg
    god_nodes = sorted(
        [(n, d) for n, d in degrees.items() if d > god_threshold],
        key=lambda x: x[1],
        reverse=True,
    )

    # Community stats
    community_count = len(set(communities.values())) if communities else 0
    comm_members: dict[int, list[str]] = {}
    for node_id, comm_id in communities.items():
        comm_members.setdefault(comm_id, []).append(node_id)

    # Fragile bridges: community pairs connected by exactly 1 edge
    cross_comm_edges: dict[tuple[int, int], list[dict]] = {}
    for e in edges:
        ca = communities.get(e["from"], -1)
        cb = communities.get(e["to"], -1)
        if ca >= 0 and cb >= 0 and ca != cb:
            key = (min(ca, cb), max(ca, cb))
            cross_comm_edges.setdefault(key, []).append(e)
    fragile_bridges = [
        (pair, edge_list[0])
        for pair, edge_list in sorted(cross_comm_edges.items())
        if len(edge_list) == 1
    ]

    # --- Build report ---
    lines = [
        f"# Graph Insights Report — {today}",
        "",
        "## Health Summary",
        f"- **{n_nodes}** nodes, **{n_edges}** edges ({edges_per_node:.2f} edges/node — {health})",
        f"- **{orphan_count}** orphan nodes ({orphan_pct:.1f}%) — target: <10%",
        f"- **{community_count}** communities",
        f"- Link density: {density:.4f}",
        "",
    ]

    # Orphan section
    lines.append(f"## 🔴 Orphan Nodes ({orphan_count} pages, {orphan_pct:.1f}%)")
    if orphans:
        lines.append("These pages have zero graph connections. Consider adding [[wikilinks]]:")
        for o in orphans:
            lines.append(f"- `{o}`")
    else:
        lines.append("No orphan nodes — excellent!")
    lines.append("")

    # God nodes section
    lines.append("## 🟡 God Nodes (Hub Pages)")
    if god_nodes:
        lines.append("These nodes carry disproportionate connectivity (degree > μ+2σ). Verify they are comprehensive:")
        lines.append("")
        lines.append("| Node | Degree | % of Edges | Community |")
        lines.append("|---|---|---|---|")
        for node_id, deg in god_nodes:
            edge_pct = (deg / (2 * n_edges) * 100) if n_edges else 0
            comm = communities.get(node_id, -1)
            lines.append(f"| `{node_id}` | {deg} | {edge_pct:.1f}% | {comm} |")
    else:
        lines.append("No god nodes detected — degree distribution is balanced.")
    lines.append("")

    # Fragile bridges section
    lines.append("## 🟡 Fragile Bridges")
    if fragile_bridges:
        lines.append("Community pairs connected by only 1 edge — one deleted link breaks them:")
        for (ca, cb), edge in fragile_bridges:
            lines.append(f"- Community {ca} ↔ Community {cb} via `{edge['from']}` → `{edge['to']}`")
    else:
        lines.append("No fragile bridges — all community connections are redundant.")
    lines.append("")

    # Community overview
    lines.append("## 🟢 Community Overview")
    if comm_members:
        lines.append("")
        lines.append("| Community | Nodes | Key Members |")
        lines.append("|---|---|---|")
        for comm_id in sorted(comm_members.keys()):
            members = comm_members[comm_id]
            # Sort by degree descending to show key members first
            members_sorted = sorted(members, key=lambda m: degrees.get(m, 0), reverse=True)
            key_members = ", ".join(members_sorted[:5])
            if len(members_sorted) > 5:
                key_members += ", …"
            lines.append(f"| {comm_id} | {len(members)} | {key_members} |")
    else:
        lines.append("No communities detected.")
    lines.append("")

    # Suggested actions
    lines.append("## Suggested Actions")
    actions = []
    if orphans:
        actions.append(f"1. Add wikilinks to top orphan pages (highest potential impact: {orphans[0]})")
    if god_nodes:
        actions.append(f"{len(actions)+1}. Review god nodes for stub content vs. genuine hubs")
    if fragile_bridges:
        actions.append(f"{len(actions)+1}. Strengthen fragile bridges with cross-references")
    if not actions:
        actions.append("1. Graph is in good shape — maintain current linking practices")
    lines.extend(actions)
    lines.append("")

    return "\n".join(lines)


COMMUNITY_COLORS = [
    "#E91E63", "#00BCD4", "#8BC34A", "#FF5722", "#673AB7",
    "#FFC107", "#009688", "#F44336", "#3F51B5", "#CDDC39",
]


def render_html(nodes: list[dict], edges: list[dict]) -> str:
    """Generate self-contained vis.js HTML with interactive filtering."""
    nodes_json = json.dumps(nodes, indent=2, ensure_ascii=False)
    edges_json = json.dumps(edges, indent=2, ensure_ascii=False)

    legend_items = "".join(
        f'<span style="background:{color};padding:3px 8px;margin:2px;border-radius:3px;font-size:12px">{t}</span>'
        for t, color in TYPE_COLORS.items() if t != "unknown"
    )

    n_extracted = len([e for e in edges if e.get('type') == 'EXTRACTED'])
    n_inferred = len([e for e in edges if e.get('type') == 'INFERRED'])
    n_ambiguous = len([e for e in edges if e.get('type') == 'AMBIGUOUS'])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>LLM Wiki — Knowledge Graph</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  body {{ margin: 0; background: #1a1a2e; font-family: 'Inter', sans-serif; color: #eee; }}
  #graph {{ width: 100vw; height: 100vh; }}
  #controls {{
    position: fixed; top: 10px; left: 10px; background: rgba(10,10,30,0.88);
    padding: 14px; border-radius: 10px; z-index: 10; max-width: 280px;
    backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.08);
  }}
  #controls h3 {{ margin: 0 0 10px; font-size: 15px; letter-spacing: 0.5px; }}
  #search {{ width: 100%; padding: 6px 8px; margin-bottom: 10px; background: #222; color: #eee; border: 1px solid #444; border-radius: 6px; font-size: 13px; }}
  #controls p {{ margin: 10px 0 0; font-size: 11px; color: #9ea3b0; line-height: 1.5; }}
  .filter-group {{ margin-top: 10px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.1); }}
  .filter-group label {{ display: block; font-size: 12px; color: #bbb; margin-bottom: 4px; }}
  .slider-row {{ display: flex; align-items: center; gap: 8px; margin-top: 4px; }}
  .slider-row input[type=range] {{ flex: 1; accent-color: #FF5722; }}
  .slider-val {{ font-size: 12px; color: #FF5722; min-width: 28px; text-align: right; font-weight: bold; }}
  .cb-row {{ display: flex; align-items: center; gap: 6px; font-size: 12px; margin: 3px 0; cursor: pointer; }}
  .cb-row input {{ accent-color: #FF5722; }}
  #drawer {{
    position: fixed; top: 0; right: 0; width: clamp(480px, 33vw, 720px); max-width: 100vw; height: 100vh;
    background: rgba(7, 10, 24, 0.96); border-left: 1px solid rgba(255,255,255,0.08);
    box-shadow: -18px 0 36px rgba(0,0,0,0.35); z-index: 20; display: none;
    flex-direction: column; backdrop-filter: blur(10px);
  }}
  #drawer.open {{ display: flex; }}
  #drawer-header {{
    padding: 18px 18px 12px; border-bottom: 1px solid rgba(255,255,255,0.08);
  }}
  #drawer-topline {{
    display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
  }}
  #drawer-title {{ margin: 0; font-size: 20px; line-height: 1.2; }}
  #drawer-close {{
    background: transparent; color: #9ea3b0; border: 0; font-size: 24px; line-height: 1;
    cursor: pointer; padding: 0;
  }}
  #drawer-meta {{ margin-top: 8px; font-size: 12px; color: #9ea3b0; }}
  #drawer-path {{ margin-top: 6px; font-size: 12px; color: #72788a; word-break: break-all; }}
  #drawer-preview {{
    margin-top: 12px; font-size: 13px; color: #d7d9e0; line-height: 1.6;
  }}
  #drawer-related {{
    padding: 12px 18px 0; font-size: 12px; color: #9ea3b0;
  }}
  #drawer-related-list {{
    display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px;
  }}
  .related-chip {{
    background: rgba(255,255,255,0.08); color: #f1f2f7; border: 1px solid rgba(255,255,255,0.08);
    border-radius: 999px; font-size: 12px; padding: 5px 10px; cursor: pointer;
  }}
  #drawer-content {{
    flex: 1; min-height: 0; padding: 14px 18px 18px; overflow: auto;
  }}
  #drawer-markdown {{
    color: #e6e8ef; font-size: 13px; line-height: 1.72;
  }}
  #drawer-markdown h1, #drawer-markdown h2, #drawer-markdown h3,
  #drawer-markdown h4, #drawer-markdown h5, #drawer-markdown h6 {{
    margin: 1.2em 0 0.55em; line-height: 1.3; color: #fff;
  }}
  #drawer-markdown h1 {{ font-size: 24px; }}
  #drawer-markdown h2 {{ font-size: 20px; }}
  #drawer-markdown h3 {{ font-size: 17px; }}
  #drawer-markdown p {{ margin: 0 0 0.95em; }}
  #drawer-markdown ul, #drawer-markdown ol {{ margin: 0 0 1em 1.35em; padding: 0; }}
  #drawer-markdown li {{ margin: 0.35em 0; }}
  #drawer-markdown hr {{ border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 1.2em 0; }}
  #drawer-markdown blockquote {{
    margin: 0 0 1em; padding: 0.85em 1em; border-left: 3px solid rgba(101, 181, 255, 0.8);
    background: rgba(255,255,255,0.04); color: #d7d9e0; border-radius: 0 10px 10px 0;
  }}
  #drawer-markdown pre {{
    margin: 0 0 1em; white-space: pre-wrap; word-break: break-word; line-height: 1.55;
    font-size: 12px; color: #e6e8ef; background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 16px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  }}
  #drawer-markdown code {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 0.92em; background: rgba(255,255,255,0.08); padding: 0.16em 0.38em;
    border-radius: 6px; color: #ffde91;
  }}
  #drawer-markdown pre code {{ background: transparent; padding: 0; color: inherit; border-radius: 0; }}
  #drawer-markdown .wikilink {{ color: #86c8ff; font-weight: 600; }}
  @media (max-width: 960px) {{
    #drawer {{ width: 100vw; }}
  }}
  #stats {{
    position: fixed; top: 10px; right: 10px; background: rgba(10,10,30,0.88);
    padding: 10px 14px; border-radius: 10px; font-size: 12px;
    backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.08);
  }}
</style>
</head>
<body>
<div id="controls">
  <h3>LLM Wiki Graph</h3>
  <input id="search" type="text" placeholder="Search nodes..." oninput="searchNodes(this.value)">
  <div>{legend_items}</div>
  <div class="filter-group">
    <label>Edge Types</label>
    <div class="cb-row"><input type="checkbox" id="cb-extracted" checked onchange="applyFilters()"><span style="color:#888">━</span> Extracted ({n_extracted})</div>
    <div class="cb-row"><input type="checkbox" id="cb-inferred" checked onchange="applyFilters()"><span style="color:#FF5722">━</span> Inferred ({n_inferred})</div>
    <div class="cb-row"><input type="checkbox" id="cb-ambiguous" onchange="applyFilters()"><span style="color:#BDBDBD">━</span> Ambiguous ({n_ambiguous})</div>
  </div>
  <div class="filter-group">
    <label>Min Confidence</label>
    <div class="slider-row">
      <input type="range" id="conf-slider" min="0" max="100" value="50" oninput="applyFilters()">
      <span class="slider-val" id="conf-val">0.50</span>
    </div>
  </div>
  <p>Click a node to highlight its connected neighbors and view the markdown on the right. Click the background to restore the full graph.</p>
</div>
<div id="graph"></div>
<aside id="drawer">
  <div id="drawer-header">
    <div id="drawer-topline">
      <h2 id="drawer-title"></h2>
      <button id="drawer-close" onclick="clearSelection()" aria-label="Close drawer">×</button>
    </div>
    <div id="drawer-meta"></div>
    <div id="drawer-path"></div>
    <div id="drawer-preview"></div>
  </div>
  <div id="drawer-related">
    Related nodes
    <div id="drawer-related-list"></div>
  </div>
  <div id="drawer-content">
    <div id="drawer-markdown"></div>
  </div>
</aside>
<div id="stats"></div>
<script>
const originalNodes = {nodes_json};
const originalEdges = {edges_json}.map(edge => ({{
  ...edge,
  id: edge.id || `${{edge.from}}->${{edge.to}}:${{edge.type || "INFERRED"}}`,
}}));
const nodes = new vis.DataSet(originalNodes);
const edges = new vis.DataSet(originalEdges);
const adjacency = new Map();
const searchInput = document.getElementById("search");
const stats = document.getElementById("stats");
const controls = {{
  extracted: document.getElementById("cb-extracted"),
  inferred: document.getElementById("cb-inferred"),
  ambiguous: document.getElementById("cb-ambiguous"),
  confSlider: document.getElementById("conf-slider"),
  confValue: document.getElementById("conf-val"),
}};
const nodeMap = new Map(originalNodes.map(node => [node.id, node]));
let activeNodeId = null;

function hexToRgba(color, alpha) {{
  if (!color) return `rgba(255, 255, 255, ${{alpha}})`;
  const normalized = color.replace("#", "");
  const value = normalized.length === 3
    ? normalized.split("").map(ch => ch + ch).join("")
    : normalized;
  const intValue = Number.parseInt(value, 16);
  const r = (intValue >> 16) & 255;
  const g = (intValue >> 8) & 255;
  const b = intValue & 255;
  return `rgba(${{r}}, ${{g}}, ${{b}}, ${{alpha}})`;
}}

function escapeHtml(text) {{
  return (text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}}

function stripFrontmatter(markdown) {{
  return (markdown || "").replace(/^---\\n[\\s\\S]*?\\n---\\n?/, "");
}}

function renderInlineMarkdown(text) {{
  let html = escapeHtml(text);
  html = html.replace(/\\[\\[([^\\]]+)\\]\\]/g, '<span class="wikilink">[[$1]]</span>');
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\\*\\*([^*]+)\\*\\*/g, "<strong>$1</strong>");
  html = html.replace(/\\*([^*]+)\\*/g, "<em>$1</em>");
  return html;
}}

function renderMarkdown(markdown) {{
  const lines = stripFrontmatter(markdown).split(/\\r?\\n/);
  const html = [];
  let paragraph = [];
  let listType = null;
  let listItems = [];
  let quoteLines = [];
  let inCodeBlock = false;
  let codeLines = [];

  function flushParagraph() {{
    if (!paragraph.length) return;
    html.push(`<p>${{renderInlineMarkdown(paragraph.join(" "))}}</p>`);
    paragraph = [];
  }}

  function flushList() {{
    if (!listType || !listItems.length) return;
    const items = listItems.map(item => `<li>${{renderInlineMarkdown(item)}}</li>`).join("");
    html.push(`<${{listType}}>${{items}}</${{listType}}>`);
    listType = null;
    listItems = [];
  }}

  function flushQuote() {{
    if (!quoteLines.length) return;
    html.push(`<blockquote>${{quoteLines.map(line => renderInlineMarkdown(line)).join("<br>")}}</blockquote>`);
    quoteLines = [];
  }}

  function flushCode() {{
    if (!codeLines.length) {{
      html.push("<pre><code></code></pre>");
      return;
    }}
    html.push(`<pre><code>${{escapeHtml(codeLines.join("\\n"))}}</code></pre>`);
    codeLines = [];
  }}

  for (const rawLine of lines) {{
    const line = rawLine.replace(/\\t/g, "    ");
    const trimmed = line.trim();

    if (trimmed.startsWith("```")) {{
      flushParagraph();
      flushList();
      flushQuote();
      if (inCodeBlock) {{
        flushCode();
        inCodeBlock = false;
      }} else {{
        inCodeBlock = true;
      }}
      continue;
    }}

    if (inCodeBlock) {{
      codeLines.push(rawLine);
      continue;
    }}

    if (!trimmed) {{
      flushParagraph();
      flushList();
      flushQuote();
      continue;
    }}

    const headingMatch = trimmed.match(/^(#{1,6})\\s+(.+)$/);
    if (headingMatch) {{
      flushParagraph();
      flushList();
      flushQuote();
      const level = headingMatch[1].length;
      html.push(`<h${{level}}>${{renderInlineMarkdown(headingMatch[2])}}</h${{level}}>`);
      continue;
    }}

    if (/^(-{3,}|\\*{3,})$/.test(trimmed)) {{
      flushParagraph();
      flushList();
      flushQuote();
      html.push("<hr>");
      continue;
    }}

    const quoteMatch = trimmed.match(/^>\\s?(.*)$/);
    if (quoteMatch) {{
      flushParagraph();
      flushList();
      quoteLines.push(quoteMatch[1]);
      continue;
    }}
    flushQuote();

    const unorderedMatch = trimmed.match(/^[-*]\\s+(.+)$/);
    if (unorderedMatch) {{
      flushParagraph();
      if (listType && listType !== "ul") flushList();
      listType = "ul";
      listItems.push(unorderedMatch[1]);
      continue;
    }}

    const orderedMatch = trimmed.match(/^\\d+\\.\\s+(.+)$/);
    if (orderedMatch) {{
      flushParagraph();
      if (listType && listType !== "ol") flushList();
      listType = "ol";
      listItems.push(orderedMatch[1]);
      continue;
    }}

    flushList();
    paragraph.push(trimmed);
  }}

  if (inCodeBlock) flushCode();
  flushParagraph();
  flushList();
  flushQuote();
  return html.join("");
}}

function rebuildAdjacency(filteredEdges) {{
  adjacency.clear();
  for (const node of originalNodes) {{
    adjacency.set(node.id, new Set());
  }}
  for (const edge of filteredEdges) {{
    if (!adjacency.has(edge.from)) adjacency.set(edge.from, new Set());
    if (!adjacency.has(edge.to)) adjacency.set(edge.to, new Set());
    adjacency.get(edge.from).add(edge.to);
    adjacency.get(edge.to).add(edge.from);
  }}
}}

function currentEdgeState() {{
  const minConf = parseInt(controls.confSlider.value, 10) / 100;
  controls.confValue.textContent = minConf.toFixed(2);
  return {{
    showExtracted: controls.extracted.checked,
    showInferred: controls.inferred.checked,
    showAmbiguous: controls.ambiguous.checked,
    minConf,
  }};
}}

function passesEdgeFilters(edge, edgeState) {{
  const typeOk = (edge.type === "EXTRACTED" && edgeState.showExtracted)
    || (edge.type === "INFERRED" && edgeState.showInferred)
    || (edge.type === "AMBIGUOUS" && edgeState.showAmbiguous);
  const confOk = (edge.confidence ?? 1.0) >= edgeState.minConf;
  return typeOk && confOk;
}}

function searchNodes(q) {{
  applyFilters(q, activeNodeId);
}}

function clearSelection() {{
  activeNodeId = null;
  closeDrawer();
  applyFilters(searchInput.value, null);
}}

function closeDrawer() {{
  document.getElementById("drawer").classList.remove("open");
}}

function openDrawer(node, relatedIds) {{
  document.getElementById("drawer").classList.add("open");
  document.getElementById("drawer-title").textContent = node.label;
  const communityText = Number.isInteger(node.group) && node.group >= 0 ? ` · community ${{node.group}}` : "";
  document.getElementById("drawer-meta").textContent = `${{node.type}}${{communityText}}`;
  document.getElementById("drawer-path").textContent = node.path;
  document.getElementById("drawer-preview").textContent = node.preview || "";
  document.getElementById("drawer-markdown").innerHTML = renderMarkdown(node.markdown || "");

  const relatedList = document.getElementById("drawer-related-list");
  relatedList.innerHTML = "";
  const relatedNodes = originalNodes
    .filter(item => relatedIds.has(item.id) && item.id !== node.id)
    .sort((a, b) => a.label.localeCompare(b.label));

  if (relatedNodes.length === 0) {{
    const empty = document.createElement("span");
    empty.textContent = "No directly connected nodes";
    relatedList.appendChild(empty);
    return;
  }}

  for (const related of relatedNodes) {{
    const chip = document.createElement("button");
    chip.className = "related-chip";
    chip.textContent = related.label;
    chip.onclick = () => focusNode(related.id);
    relatedList.appendChild(chip);
  }}
}}

function applyFilters(query = searchInput.value, selectedNodeId = activeNodeId) {{
  const lower = (query || "").trim().toLowerCase();
  const edgeState = currentEdgeState();
  const filteredEdges = originalEdges.filter(edge => passesEdgeFilters(edge, edgeState));
  rebuildAdjacency(filteredEdges);

  const relatedIds = selectedNodeId
    ? new Set([selectedNodeId, ...(adjacency.get(selectedNodeId) || [])])
    : null;
  const filteredNodeIds = new Set();
  for (const edge of filteredEdges) {{
    filteredNodeIds.add(edge.from);
    filteredNodeIds.add(edge.to);
  }}

  let visibleNodeCount = 0;
  const nodeUpdates = originalNodes.map(node => {{
    const matchesSearch = !lower || node.label.toLowerCase().includes(lower);
    const isActive = selectedNodeId === node.id;
    const isConnected = filteredNodeIds.has(node.id);
    const isRelated = !relatedIds || relatedIds.has(node.id);
    const hidden = !selectedNodeId && !lower && !isConnected;
    const emphasized = matchesSearch && isRelated && (isConnected || !!lower || isActive);

    if (!hidden) {{
      visibleNodeCount += 1;
    }}

    return {{
      id: node.id,
      hidden,
      color: {{
        background: emphasized ? node.color : hexToRgba(node.color, hidden ? 0.05 : 0.14),
        border: emphasized ? hexToRgba(node.color, 0.96) : hexToRgba(node.color, hidden ? 0.08 : 0.22),
        highlight: {{ background: node.color, border: hexToRgba(node.color, 1) }},
        hover: {{ background: node.color, border: hexToRgba(node.color, 1) }},
      }},
      font: {{
        color: emphasized ? "#f2f3f8" : hidden ? "rgba(242,243,248,0.08)" : "rgba(242,243,248,0.2)",
      }},
      borderWidth: isActive ? 5 : 2,
      size: isActive ? 18 : 12,
    }};
  }});

  const edgeUpdates = originalEdges.map(edge => {{
    const enabled = passesEdgeFilters(edge, edgeState);
    if (!enabled) {{
      return {{ id: edge.id, hidden: true }};
    }}

    const matchesSearch = !lower
      || nodeMap.get(edge.from)?.label.toLowerCase().includes(lower)
      || nodeMap.get(edge.to)?.label.toLowerCase().includes(lower);
    const isRelated = !relatedIds || relatedIds.has(edge.from) || relatedIds.has(edge.to);
    const touchesActive = !!selectedNodeId && (edge.from === selectedNodeId || edge.to === selectedNodeId);
    const emphasized = matchesSearch && isRelated;

    return {{
      id: edge.id,
      hidden: false,
      width: touchesActive ? 2.8 : emphasized ? 1.2 : 0.6,
      color: emphasized ? edge.color : hexToRgba(edge.color, 0.08),
    }};
  }});

  nodes.update(nodeUpdates);
  edges.update(edgeUpdates);

  if (selectedNodeId) {{
    const activeNode = nodeMap.get(selectedNodeId);
    if (activeNode) {{
      openDrawer(activeNode, relatedIds || new Set([selectedNodeId]));
    }}
  }}

  const focusSuffix = selectedNodeId && nodeMap.get(selectedNodeId)
    ? ` · focused: ${{nodeMap.get(selectedNodeId).label}}`
    : "";
  stats.textContent = `${{visibleNodeCount}} nodes · ${{filteredEdges.length}} edges${{focusSuffix}}`;
}}

const container = document.getElementById("graph");

// Adaptive physics based on graph size
const nodeCount = originalNodes.length;
const gravConst = nodeCount > 80 ? -8000 : nodeCount > 30 ? -5000 : -2000;
const springLen = nodeCount > 80 ? 250 : nodeCount > 30 ? 200 : 150;

const network = new vis.Network(container, {{ nodes, edges }}, {{
  nodes: {{
    shape: "dot",
    font: {{ color: "#ddd", size: 12, strokeWidth: 3, strokeColor: "#111" }},
    borderWidth: 1.5,
    scaling: {{
      min: 8,
      max: 40,
      label: {{ enabled: true, min: 10, max: 20, drawThreshold: 6, maxVisible: 24 }},
    }},
  }},
  edges: {{
    width: 0.8,
    smooth: {{ type: "continuous" }},
    arrows: {{ to: {{ enabled: true, scaleFactor: 0.4 }} }},
    color: {{ inherit: false }},
    hoverWidth: 2,
  }},
  physics: {{
    stabilization: {{ iterations: 250, updateInterval: 25, fit: true }},
    barnesHut: {{ gravitationalConstant: gravConst, springLength: springLen, springConstant: 0.02, damping: 0.15 }},
    minVelocity: 0.75,
  }},
  interaction: {{ hover: true, tooltipDelay: 150, hideEdgesOnDrag: true, hideEdgesOnZoom: true }},
}});

// Ensure the graph fits the viewport after physics stabilization
network.once("stabilizationIterationsDone", function () {{
  network.fit({{ animation: {{ duration: 400, easingFunction: "easeInOutQuad" }} }});
}});

function focusNode(nodeId) {{
  activeNodeId = nodeId;
  applyFilters(searchInput.value, nodeId);
  const node = nodeMap.get(nodeId) || nodes.get(nodeId);
  const relatedIds = new Set([nodeId, ...(adjacency.get(nodeId) || [])]);
  openDrawer(node, relatedIds);
  network.focus(nodeId, {{
    scale: 1.1,
    animation: {{ duration: 300, easingFunction: "easeInOutQuad" }},
  }});
}}

network.on("click", params => {{
  if (params.nodes.length > 0) {{
    focusNode(params.nodes[0]);
  }} else {{
    clearSelection();
  }}
}});

applyFilters();
</script>
</body>
</html>"""


def append_log(entry: str):
    log_path = WIKI_DIR / "log.md"
    entry_text = entry.strip()
    if not log_path.exists():
        log_path.write_text(
            "# Wiki Log\n\n"
            "> Records important additions, revisions, and clarifications in the project knowledge layer. Maintained in append-only mode for agent and human traceability.\n\n"
            f"{entry_text}\n",
            encoding="utf-8",
        )
        return

    existing = read_file(log_path).rstrip()
    if not existing:
        existing = (
            "# Wiki Log\n\n"
            "> Records important additions, revisions, and clarifications in the project knowledge layer. Maintained in append-only mode for agent and human traceability."
        )
    log_path.write_text(existing + "\n\n" + entry_text + "\n", encoding="utf-8")


def build_graph(open_browser: bool = False, report: bool = False, save: bool = False):
    pages = all_wiki_pages()
    today = date.today().isoformat()

    if not pages:
        print("Wiki is empty. Ingest some sources first.")
        return

    print(f"Building graph from {len(pages)} wiki pages...")
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)

    # Extract wikilink edges
    print("  Extracting wikilinks...")
    nodes = build_nodes(pages)
    edges = build_extracted_edges(pages)
    print(f"  → {len(edges)} extracted edges")

    # Deduplicate edges
    before_dedup = len(edges)
    edges = deduplicate_edges(edges)
    if before_dedup != len(edges):
        print(f"  dedup: {before_dedup} → {len(edges)} edges")

    # Community detection
    print("  Running Louvain community detection...")
    communities = detect_communities(nodes, edges)
    for node in nodes:
        comm_id = communities.get(node["id"], -1)
        if comm_id >= 0:
            node["color"] = COMMUNITY_COLORS[comm_id % len(COMMUNITY_COLORS)]
        node["group"] = comm_id

    # Compute degree-based node sizing (value) for vis.js scaling
    degree_map: dict[str, int] = {}
    for e in edges:
        degree_map[e["from"]] = degree_map.get(e["from"], 0) + 1
        degree_map[e["to"]] = degree_map.get(e["to"], 0) + 1
    for node in nodes:
        node["value"] = degree_map.get(node["id"], 0) + 1  # +1 so isolated nodes are still visible

    # Save graph.json
    graph_data = {"nodes": nodes, "edges": edges, "built": today}
    GRAPH_JSON.write_text(json.dumps(graph_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  saved: graph/graph.json  ({len(nodes)} nodes, {len(edges)} edges)")

    # Save graph.html
    html = render_html(nodes, edges)
    GRAPH_HTML.write_text(html, encoding="utf-8")
    print(f"  saved: graph/graph.html")

    append_log(f"## [{today}] graph | Knowledge graph rebuilt\n\n{len(nodes)} nodes, {len(edges)} edges ({len(edges)} extracted).")

    # Generate health report
    if report:
        if not HAS_NETWORKX:
            print("Warning: networkx not installed. Cannot generate report.")
        else:
            report_text = generate_report(nodes, edges, communities)
            print("\n" + report_text)
            if save:
                report_path = GRAPH_DIR / "graph-report.md"
                report_path.write_text(report_text, encoding="utf-8")
                print(f"  saved: {report_path.relative_to(REPO_ROOT)}")
            append_log(f"## [{today}] report | Graph health report generated\n\n{len(nodes)} nodes analyzed.")

    if open_browser:
        webbrowser.open(f"file://{GRAPH_HTML.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build LLM Wiki knowledge graph")
    parser.add_argument("--open", action="store_true", help="Open graph.html in browser")
    parser.add_argument("--report", action="store_true", help="Generate graph health report")
    parser.add_argument("--save", action="store_true", help="Save report to graph/graph-report.md")
    args = parser.parse_args()
    build_graph(open_browser=args.open, report=args.report, save=args.save)
