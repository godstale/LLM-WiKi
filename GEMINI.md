# GEMINI.md - LLM Wiki Project Context

This file provides instructional context for AI agents working within the **LLM Wiki** project.

## Project Overview

**LLM Wiki** is an agent-maintained personal knowledge base framework designed for **Claude Code**. It automates the lifecycle of personal knowledge management: **Ingest → Query → Lint → Graph**.

- **Purpose:** To transform raw documents (PDFs, Word docs, Markdown, etc.) into a structured, searchable, and visualized wiki.
- **Core Workflow:**
  1. **Ingest:** Convert and summarize raw files into `wiki/sources/`, extracting `entities` and `concepts`.
  2. **Query:** Use the agent to synthesize answers across multiple wiki pages with citations.
  3. **Lint:** Perform structural and semantic health checks (broken links, orphans, contradictions).
  4. **Graph:** Generate an interactive HTML visualization of the knowledge network.

## Key Components

- **`SKILL.md`**: Defines the agent's behavior and slash commands (`/wiki-ingest`, `/wiki-query`, `/wiki-synthesize`, `/wiki-lint`, `/wiki-graph`).
- **`scripts/`**: Python utilities for complex tasks:
  - `lint.py`: Structural and graph-aware wiki health checks.
  - `build_graph.py`: Generates `graph/graph.json` and `graph/graph.html`.
  - `file_to_markdown.py`: Batch converts non-markdown files to `.md`.
- **`wiki/`**: The core knowledge base:
  - `sources/`: Summaries of individual documents.
  - `entities/`: Hub pages for people, projects, and organizations (TitleCase).
  - `concepts/`: Hub pages for ideas, frameworks, and theories (TitleCase).
  - `originals/`: Read-only archive of the original source files.
- **`references/`**: Technical documentation and templates (`templates.md`, `folder-managing.md`).

## Setup & Commands

### Prerequisites
- **Python 3.10+** (optional but recommended for scripts).
- **Claude Code** with the `llm-wiki` skill installed.

### Installation
```bash
# Install the skill to Claude Code
npx skills add godstale/llm-wiki

# Install Python dependencies for scripts
pip install -r scripts/requirements.txt
```

### Key Commands
- **Ingest:** `/wiki-ingest raw/document.pdf` (or use natural language: "ingest this file").
- **Query:** `/wiki-query "What are the core themes of X?"`
- **Synthesize:** `/wiki-synthesize` — save the most recent query answer to `wiki/syntheses/`. Run after `/wiki-query`.
- **Lint:** `python scripts/lint.py --save` or `/wiki-lint`.
- **Graph:** `python scripts/build_graph.py --open` or `/wiki-graph`.

## Development Conventions

### Wiki Page Format
Every markdown file in the `wiki/` directory MUST have YAML frontmatter:
```yaml
---
title: "Page Title"
type: source | entity | concept | synthesis
tags: []
sources: [slug1, slug2]
last_updated: YYYY-MM-DD
---
```
Use `[[WikiLinks]]` for internal navigation. Links are case-sensitive and should match the filename (without extension).

### Naming Conventions
- **Sources & Syntheses:** `kebab-case.md` (e.g., `market-research-2024.md`).
- **Entities & Concepts:** `TitleCase.md` (e.g., `OpenAI.md`, `MachineLearning.md`).

### Folder Management (PARA)
When moving original files using the `--to` flag in `/wiki-ingest`, follow the PARA structure defined in `references/folder-managing.md`:
- `00_Inbox`, `01_Projects`, `02_Areas`, `03_Resources`, `04_Archives`.
- Filename format: `YYYYMMDD_Slug_Description`.

## Usage Guidelines for Agents
- **Maintain Integrity:** Never modify files in `wiki/originals/`.
- **Update the Index:** Always update `wiki/index.md` after an ingestion.
- **Audit Links:** Regularly run `/wiki-lint` to fix broken `[[WikiLinks]]`.
- **Be Concise:** Wiki summaries should be 2–4 sentences, focusing on key claims and connections.
