# Graph HTML Template

Self-contained vis.js page for `graph/graph.html`. Replace `/* GRAPH_JSON_PLACEHOLDER */` with the actual `graph.json` content inlined as a JavaScript object.

```html
<!DOCTYPE html>
<html>
<head>
  <title>LLM Wiki Knowledge Graph</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    body { margin: 0; font-family: sans-serif; background: #1a1a1a; color: #eee; }
    #graph { width: 100vw; height: 95vh; border: none; }
    #controls { padding: 8px; background: #222; display: flex; gap: 12px; align-items: center; }
    input { background: #333; color: #eee; border: 1px solid #555; padding: 4px 8px; border-radius: 4px; }
    .legend { display: flex; gap: 10px; font-size: 13px; }
    .legend span { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
  </style>
</head>
<body>
<div id="controls">
  <input id="search" placeholder="Search nodes..." oninput="filterNodes(this.value)" />
  <div class="legend">
    <span style="background:#4CAF50"></span>source
    <span style="background:#2196F3"></span>entity
    <span style="background:#FF9800"></span>concept
    <span style="background:#9C27B0"></span>synthesis
  </div>
</div>
<div id="graph"></div>
<script>
const graphData = /* GRAPH_JSON_PLACEHOLDER */;
const nodes = new vis.DataSet(graphData.nodes.map(n => ({
  id: n.id, label: n.label,
  color: { background: n.color || '#9E9E9E', border: '#fff' },
  font: { color: '#eee' }
})));
const edges = new vis.DataSet(graphData.edges.map(e => ({
  from: e.from, to: e.to,
  color: { color: e.color || '#555' },
  dashes: e.type === 'INFERRED' || e.type === 'AMBIGUOUS',
  title: e.type + (e.confidence ? ' (' + e.confidence + ')' : '')
})));
const network = new vis.Network(
  document.getElementById('graph'),
  { nodes, edges },
  { physics: { stabilization: false }, interaction: { hover: true } }
);
function filterNodes(q) {
  const lower = q.toLowerCase();
  nodes.forEach(n => {
    nodes.update({ id: n.id, hidden: !!(q && !n.label.toLowerCase().includes(lower)) });
  });
}
</script>
</body>
</html>
```
