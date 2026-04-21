#!/usr/bin/env python3
from __future__ import annotations

"""
Validate wiki pages against wiki/ontology.yaml.

Usage:
    python scripts/ontology_validate.py
    python scripts/ontology_validate.py --save   # save report to wiki/ontology-validation-report.md
    python scripts/ontology_validate.py --json   # emit machine-readable JSON on stdout

Checks (corresponding to /wiki-lint checks 7–12):
  7.  Unknown `class:` not defined under any axis
  8.  Unknown `relations[].predicate` not in ontology
  9.  Unknown `context.phase` not in workflow.phases
  10. Domain/range violation on typed relations
  11. Missing required properties declared on the class
  12. Workflow gaps (Activity instances missing phase; phases with no instances)

Graceful degradation:
  - Exits quietly if wiki/ontology.yaml is absent (ontology is opt-in).
  - Exits with an instruction if PyYAML is not installed.
"""

import re
import json
import argparse
import sys
from pathlib import Path
from collections import defaultdict
from datetime import date

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO_ROOT = Path.cwd()
WIKI_DIR = REPO_ROOT / "wiki"
ONTOLOGY_FILE = WIKI_DIR / "ontology.yaml"
LOG_FILE = WIKI_DIR / "log.md"
REPORT_FILE = WIKI_DIR / "ontology-validation-report.md"


# ── IO helpers ──────────────────────────────────────────────────────

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
    skip = {"index.md", "log.md", "lint-report.md",
            "ontology-validation-report.md", "overview.md",
            "ontology-guide.md"}
    return [p for p in WIKI_DIR.rglob("*.md") if p.name not in skip]


def load_yaml(path: Path):
    try:
        import yaml
    except ImportError:
        print("Error: PyYAML is required. Install with: pip install pyyaml")
        sys.exit(2)
    return yaml.safe_load(read_file(path))


# ── Frontmatter parsing ─────────────────────────────────────────────

FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from a markdown file. Returns {} if none."""
    m = FM_RE.match(content)
    if not m:
        return {}
    try:
        import yaml
        data = yaml.safe_load(m.group(1))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# ── Ontology index ──────────────────────────────────────────────────

class Ontology:
    """Parsed ontology.yaml with lookup helpers."""

    def __init__(self, data: dict):
        self.raw = data or {}
        self.classes: dict[str, dict] = {}           # class_name → {axis, folder, properties}
        self.axis_of_class: dict[str, str] = {}
        self.relations: dict[str, dict] = {}         # predicate → {domain, range, ...}
        self.phase_ids: set[str] = set()
        self._build_indexes()

    def _build_indexes(self):
        axes = self.raw.get("axes", {}) or {}
        for axis_name, axis_def in axes.items():
            if not axis_def or axis_def.get("active") is False:
                continue
            for cls_name, cls_def in (axis_def.get("default_classes") or {}).items():
                self.classes[cls_name] = {
                    "axis": axis_name,
                    "folder": (cls_def or {}).get("folder"),
                    "properties": (cls_def or {}).get("properties") or [],
                }
                self.axis_of_class[cls_name] = axis_name

        self.relations = self.raw.get("relations", {}) or {}

        wf = self.raw.get("workflow", {}) or {}
        for ph in wf.get("phases") or []:
            if isinstance(ph, dict) and "id" in ph:
                self.phase_ids.add(ph["id"])

    def axis_of(self, class_name: str) -> str | None:
        return self.axis_of_class.get(class_name)

    def class_matches_slot(self, class_name: str, slot: list | str) -> bool:
        """slot may be list[str] or str; entries are axis names, class names, or 'any'."""
        if slot == "any":
            return True
        if isinstance(slot, str):
            slot = [slot]
        for s in slot or []:
            if s == "any":
                return True
            if s == class_name:
                return True
            if s == self.axis_of(class_name):
                return True
        return False


# ── Page records ────────────────────────────────────────────────────

class PageRecord:
    def __init__(self, path: Path, fm: dict):
        self.path = path
        self.rel = path.relative_to(REPO_ROOT).as_posix()
        self.fm = fm or {}
        self.page_type = self.fm.get("type")
        self.class_name = self.fm.get("class")
        self.relations = self.fm.get("relations") or []
        self.context = self.fm.get("context") or {}
        self.properties = self.fm.get("properties") or {}


def class_of_target(target_name: str, pages_by_stem: dict[str, PageRecord]) -> str | None:
    """Look up the class of a page referenced by a relation target name."""
    rec = pages_by_stem.get(target_name) or pages_by_stem.get(target_name.lower())
    return rec.class_name if rec else None


# ── Checks ──────────────────────────────────────────────────────────

def check_all(pages: list[PageRecord], ont: Ontology) -> dict:
    by_stem = {p.path.stem: p for p in pages}
    # case-insensitive fallback
    by_stem.update({p.path.stem.lower(): p for p in pages})

    unknown_class = []        # [(rel, class_name)]
    unknown_predicate = []    # [(rel, predicate)]
    unknown_phase = []        # [(rel, phase)]
    domain_violations = []    # [(rel, predicate, subject_class, expected_domain)]
    range_violations = []     # [(rel, predicate, target, target_class, expected_range)]
    missing_required = []     # [(rel, class_name, missing_prop)]
    activity_missing_phase = []   # [rel]
    phases_with_no_instances = []  # [phase_id]

    activity_phase_counts: dict[str, int] = defaultdict(int)

    for p in pages:
        # 7. Unknown class
        if p.class_name and p.class_name not in ont.classes:
            unknown_class.append((p.rel, p.class_name))

        # 11. Missing required properties (best-effort: all listed properties are "suggested")
        if p.class_name and p.class_name in ont.classes:
            expected_props = ont.classes[p.class_name]["properties"]
            for prop in expected_props:
                if prop not in p.properties and prop not in p.fm:
                    missing_required.append((p.rel, p.class_name, prop))

        # 8. Unknown predicates + 10. domain/range violations
        subject_class = p.class_name
        for rel in p.relations or []:
            if not isinstance(rel, dict):
                continue
            pred = rel.get("predicate")
            target = rel.get("target")
            if not pred:
                continue
            if pred not in ont.relations:
                unknown_predicate.append((p.rel, pred))
                continue
            pdef = ont.relations[pred] or {}
            # domain: subject must satisfy
            domain = pdef.get("domain", "any")
            if subject_class and not ont.class_matches_slot(subject_class, domain):
                domain_violations.append(
                    (p.rel, pred, subject_class, domain)
                )
            # range: target's class must satisfy
            if target:
                target_class = class_of_target(str(target), by_stem)
                rng = pdef.get("range", "any")
                if target_class and not ont.class_matches_slot(target_class, rng):
                    range_violations.append(
                        (p.rel, pred, str(target), target_class, rng)
                    )

        # 9. Unknown phase in context
        phase = p.context.get("phase") if isinstance(p.context, dict) else None
        if phase and ont.phase_ids and phase not in ont.phase_ids:
            unknown_phase.append((p.rel, phase))

        # 12. Workflow gaps — Activity instances w/o phase; phase instance counts
        if ont.phase_ids and p.class_name:
            axis = ont.axis_of(p.class_name)
            if axis == "Activity":
                if not phase:
                    activity_missing_phase.append(p.rel)
                else:
                    activity_phase_counts[phase] += 1

    if ont.phase_ids:
        for phase_id in ont.phase_ids:
            if activity_phase_counts.get(phase_id, 0) == 0:
                phases_with_no_instances.append(phase_id)

    return {
        "unknown_class": unknown_class,
        "unknown_predicate": unknown_predicate,
        "unknown_phase": unknown_phase,
        "domain_violations": domain_violations,
        "range_violations": range_violations,
        "missing_required": missing_required,
        "activity_missing_phase": activity_missing_phase,
        "phases_with_no_instances": phases_with_no_instances,
    }


# ── Reporting ───────────────────────────────────────────────────────

def format_report(results: dict, page_count: int) -> str:
    today = date.today().isoformat()
    lines = [
        f"# Ontology Validation Report — {today}",
        "",
        f"Scanned {page_count} pages against `wiki/ontology.yaml`.",
        "",
    ]

    total = sum(len(v) for v in results.values())
    if total == 0:
        lines.append("No ontology violations found.")
        return "\n".join(lines)

    def section(title: str, items: list, render):
        if not items:
            return
        lines.append(f"## {title} ({len(items)} found)")
        for it in items:
            lines.append(render(it))
        lines.append("")

    section("Unknown Classes",
            results["unknown_class"],
            lambda it: f"- `{it[0]}` — class `{it[1]}` not defined in ontology")

    section("Unknown Predicates",
            results["unknown_predicate"],
            lambda it: f"- `{it[0]}` — predicate `{it[1]}` not defined in `relations:`")

    section("Unknown Phases",
            results["unknown_phase"],
            lambda it: f"- `{it[0]}` — context.phase `{it[1]}` not in workflow.phases")

    section("Domain Violations",
            results["domain_violations"],
            lambda it: (f"- `{it[0]}` — predicate `{it[1]}` used by class `{it[2]}`; "
                        f"expected domain {it[3]}"))

    section("Range Violations",
            results["range_violations"],
            lambda it: (f"- `{it[0]}` — `{it[1]} → {it[2]}` has target class `{it[3]}`; "
                        f"expected range {it[4]}"))

    section("Missing Required Properties",
            results["missing_required"],
            lambda it: f"- `{it[0]}` — class `{it[1]}` missing property `{it[2]}`")

    section("Activity Instances Missing Phase",
            results["activity_missing_phase"],
            lambda it: f"- `{it}` — no `context.phase` set")

    section("Phases With No Activity Instances",
            results["phases_with_no_instances"],
            lambda it: f"- `{it}` — zero Activity instances tagged with this phase")

    return "\n".join(lines)


def append_log(entry: str):
    existing = read_file(LOG_FILE)
    LOG_FILE.write_text(entry.strip() + "\n\n" + existing, encoding="utf-8")


# ── Main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate wiki pages against ontology.yaml")
    parser.add_argument("--save", action="store_true",
                        help="Save report to wiki/ontology-validation-report.md")
    parser.add_argument("--json", action="store_true",
                        help="Emit results as JSON on stdout (for tooling)")
    args = parser.parse_args()

    if not ONTOLOGY_FILE.exists():
        print("No ontology.yaml found — ontology is opt-in. Run /wiki-ontology-init to create one.")
        sys.exit(0)

    data = load_yaml(ONTOLOGY_FILE)
    ont = Ontology(data)

    pages: list[PageRecord] = []
    for p in all_wiki_pages():
        fm = parse_frontmatter(read_file(p))
        if fm:
            pages.append(PageRecord(p, fm))

    results = check_all(pages, ont)
    total = sum(len(v) for v in results.values())

    if args.json:
        sys.stdout.reconfigure(encoding="utf-8")
        print(json.dumps({
            "page_count": len(pages),
            "violation_count": total,
            "results": results,
        }, indent=2, default=str))
        return

    report = format_report(results, len(pages))
    sys.stdout.reconfigure(encoding="utf-8")
    print(report)

    if args.save:
        REPORT_FILE.write_text(report, encoding="utf-8")
        print(f"\nSaved: {REPORT_FILE.relative_to(REPO_ROOT)}")

    today = date.today().isoformat()
    append_log(f"## [{today}] ontology-validate | {total} violations\n\n"
               f"Scanned {len(pages)} pages. See ontology-validation-report.md.")


if __name__ == "__main__":
    main()
