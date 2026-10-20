"""Write corpus/COMPARISON.md: each corpus SVG in Chromium, WeasyPrint alone and WeasyPrint with weasysvg, and resvg.

Usage: comparison.py

Run it through make comparison: it renders the panels of WeasyPrint and weasysvg with the bench first
(bench.py --panels), into corpus/render. The Chromium and resvg panels are the references in
corpus/reference; only the resvg feature tests have a resvg reference. The page is Markdown, so GitHub
shows it in the repository.
"""

from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"
PAGE = CORPUS / "COMPARISON.md"
WIDTH = 200  # px of each panel on the page; a click opens the full image
GROUPS = {
    "diagrams": "Diagrams from kroki and mermaid.ink",
    "drawio": "draw.io",
    "fo": "foreignObject",
    "real": "Wikimedia Commons",
    "resvg": "resvg feature tests",
}
VERDICTS = ("same", "minor", "font", "broken")
LABELS = {"same": "same as Chromium", "minor": "minor difference", "font": "other font only", "broken": "broken"}
COLUMNS = (("Chromium", "reference/chromium"), ("resvg", "reference/resvg"), ("WeasyPrint", "render/weasyprint"), ("weasysvg", "render/weasysvg"))


def anchor(title: str) -> str:
    """The anchor GitHub gives a heading: lowercase, spaces to hyphens, punctuation dropped."""
    return "".join(c for c in title.lower().replace(" ", "-") if c.isalnum() or c in "-_")


def cell(name: str, label: str, folder: str) -> str:
    path = f"{folder}/{name}.png"
    if not (CORPUS / path).exists():
        return "n/a"
    return f'<a href="{path}"><img src="{path}" width="{WIDTH}" alt="{name} in {label}"></a>'


def entry(item: dict[str, Any], verdict: dict[str, Any]) -> str:
    name = item["name"]
    what = verdict.get("what") or ""
    note = f" {html.escape(what)}" if what else ""
    header = "| " + " | ".join(label for label, _ in COLUMNS) + " |"
    row = "| " + " | ".join(cell(name, label, folder) for label, folder in COLUMNS) + " |"
    source = f"[`{item['source']}`](svg/{item['source']})"
    return f"### {name}\n\n{source}. WeasyPrint: {verdict.get('native_verdict', 'n/a')}, weasysvg: **{verdict.get('verdict', 'n/a')}**.{note}\n\n{header}\n|---|---|---|---|\n{row}\n"


def summary(verdicts: list[dict[str, Any]], version: str) -> str:
    native, ours = Counter(v.get("native_verdict") for v in verdicts), Counter(v.get("verdict") for v in verdicts)
    lines = [f"| Verdict | WeasyPrint {version} | WeasyPrint {version} with weasysvg |", "|---|---|---|"]
    lines += [f"| {LABELS[key]} | {native[key]} | {ours[key]} |" for key in VERDICTS]
    return "\n".join(lines)


def page() -> str:
    index = json.loads((CORPUS / "index.json").read_text())
    verdicts = {v["name"]: v for v in json.loads((CORPUS / "verdicts.json").read_text())}
    version = json.loads((CORPUS / "baseline.json").read_text()).get("weasyprint", "")
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in index:
        groups.setdefault(item["group"], []).append(item)
    contents = "\n".join(f"- [{GROUPS.get(group, group)}](#{anchor(GROUPS.get(group, group))}) ({len(items)})" for group, items in groups.items())
    sections = []
    for group, items in groups.items():
        sections.append(f"## {GROUPS.get(group, group)}\n")
        sections += [entry(item, verdicts.get(item["name"], {})) for item in items]
    intro = (
        "# Corpus comparison\n\n"
        "<!-- Written by make comparison (tools/visual/comparison.py). Do not edit by hand. -->\n\n"
        f"Each SVG of the corpus in Chromium, the reference; WeasyPrint {version} alone; and WeasyPrint {version} "
        "with weasysvg. The resvg feature tests also show the resvg reference. The WeasyPrint panels are PDFium rasterizations at 96 dpi over "
        "the box of the Chromium panel. The verdicts come from a visual review, see "
        "[`verdicts.json`](verdicts.json). Click a panel for its full size.\n\n"
    )
    return intro + summary(list(verdicts.values()), version) + "\n\n" + contents + "\n\n" + "\n".join(sections)


def main() -> None:
    PAGE.write_text(page())
    print(f"wrote {PAGE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
