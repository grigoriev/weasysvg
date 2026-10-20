"""Write corpus/COMPARISON.md: each corpus SVG in Chromium, resvg, WeasyPrint alone and WeasyPrint with weasysvg.

Usage: comparison.py

Run it through make comparison: the bench renders WeasyPrint and weasysvg first (bench.py --panels), over
the box of the Chromium reference, into tools/visual/out/panels. This script renders resvg on a page like
the one of the references, at the width of the page and with the fonts Chromium picks.

Every panel is cropped to the same box: the ink of the Chromium reference, without a margin. The panels
go into corpus/render. The page is Markdown, so GitHub shows it in the repository.
"""

from __future__ import annotations

import html
import importlib.metadata
import io
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import resvg_py
from imaging import ink_box
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"
INDEX = CORPUS / "index.json"
PAGE = CORPUS / "COMPARISON.md"
# The interactive page, for GitHub Pages: the template next to this script, with the data put in
HTML_PAGE = CORPUS / "comparison.html"
HTML_TEMPLATE = Path(__file__).with_name("comparison.html")
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
COLUMNS = (("Chromium", "render/chromium"), ("resvg", "render/resvg"), ("WeasyPrint", "render/weasyprint"), ("weasysvg", "render/weasysvg"))
# The panels of the bench, over the box of the Chromium reference, as make comparison writes them
BENCH_PANELS = ROOT / "tools" / "visual" / "out" / "panels"
Box = tuple[int, int, int, int]


UNITS = {"pt": 4 / 3, "pc": 16, "mm": 96 / 25.4, "cm": 96 / 2.54, "in": 96}
ROOT_SIZE = re.compile(r'(<svg\b[^>]*?\s(?:width|height)=")([\d.]+)(pt|pc|mm|cm|in)(")')


def in_px(svg: str) -> str:
    """The root width and height in px: resvg-py 0.5 refuses a root sized in absolute units ("invalid size")."""
    for _ in range(2):
        svg = ROOT_SIZE.sub(lambda m: f"{m[1]}{float(m[2]) * UNITS[m[3]]:g}{m[4]}", svg, count=1)
    return svg


def inside(path: Path) -> Path:
    """The path, resolved, if it lies inside the corpus: the names in index.json never lead out of it."""
    resolved = path.resolve()
    if not resolved.is_relative_to(CORPUS.resolve()):
        raise SystemExit(f"{path} lies outside {CORPUS}")
    return resolved


def render_resvg(item: dict[str, Any]) -> Image.Image | str:
    """The page of the SVG through resvg, on white, at the width of the page; or why there is none."""
    svg = inside(CORPUS / "svg" / item["source"])
    try:
        # The families Chromium resolves the generic names to, in the visual image
        png = bytes(
            resvg_py.svg_to_bytes(
                svg_string=in_px(svg.read_text()),
                resources_dir=str(svg.parent),
                width=int(item["width"]) if item.get("width") else None,
                font_family="Liberation Serif",
                serif_family="Liberation Serif",
                sans_serif_family="Liberation Sans",
                monospace_family="DejaVu Sans Mono",
            )
        )
    except BaseException as error:  # noqa: BLE001  a resvg panic surfaces as a BaseException
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        return f"resvg error: {error}"[:200]
    image = Image.open(io.BytesIO(png)).convert("RGBA")
    # The <img> of the references sits at the top left of a white page
    page = Image.new("RGB", tuple(item.get("page_size") or image.size), "white")
    page.paste(image, (0, 0), mask=image.getchannel("A"))
    return page


def panels(item: dict[str, Any]) -> str | None:
    """Write the four panels of item, each cropped to the ink of the Chromium reference. Returns a resvg failure."""
    name, box = item["name"], item.get("reference_box")
    inside(CORPUS / "render" / f"{name}.png")  # a name with a path in it would write elsewhere
    for _, folder in COLUMNS:
        (CORPUS / folder / f"{name}.png").unlink(missing_ok=True)
    if not box:
        return None
    reference = Image.open(CORPUS / "reference" / "chromium" / f"{name}.png").convert("RGB")
    ink: Box = ink_box([reference]) or (0, 0, *reference.size)
    reference.crop(ink).save(CORPUS / "render" / "chromium" / f"{name}.png", optimize=True)
    for mode in ("weasyprint", "weasysvg"):
        source = BENCH_PANELS / mode / f"{name}.png"
        if source.exists():
            Image.open(source).crop(ink).save(CORPUS / "render" / mode / f"{name}.png", optimize=True)
    page = render_resvg(item)
    if isinstance(page, str):
        return page
    absolute = (box[0] + ink[0], box[1] + ink[1], box[0] + ink[2], box[1] + ink[3])
    resvg = page.crop(absolute)
    if ink_box([resvg]) is None:
        return "resvg draws nothing"
    resvg.save(CORPUS / "render" / "resvg" / f"{name}.png", optimize=True)
    return None


def anchor(title: str) -> str:
    """The anchor GitHub gives a heading: lowercase, spaces to hyphens, punctuation dropped."""
    return "".join(c for c in title.lower().replace(" ", "-") if c.isalnum() or c in "-_")


def cell(name: str, label: str, folder: str, missing: str) -> str:
    path = f"{folder}/{name}.png"
    if not (CORPUS / path).exists():
        return html.escape(missing)
    return f'<a href="{path}"><img src="{path}" width="{WIDTH}" alt="{name} in {label}"></a>'


def entry(item: dict[str, Any], verdict: dict[str, Any], resvg_error: str | None) -> str:
    name = item["name"]
    what = verdict.get("what") or ""
    note = f" {html.escape(what)}" if what else ""
    header = "| " + " | ".join(label for label, _ in COLUMNS) + " |"
    row = "| " + " | ".join(cell(name, label, folder, (resvg_error if label == "resvg" else None) or "n/a") for label, folder in COLUMNS) + " |"
    source = f"[`{item['source']}`](svg/{item['source']})"
    return f"### {name}\n\n{source}. WeasyPrint: {verdict.get('native_verdict', 'n/a')}, weasysvg: **{verdict.get('verdict', 'n/a')}**.{note}\n\n{header}\n|---|---|---|---|\n{row}\n"


def summary(verdicts: list[dict[str, Any]], version: str) -> str:
    native, ours = Counter(v.get("native_verdict") for v in verdicts), Counter(v.get("verdict") for v in verdicts)
    lines = [f"| Verdict | WeasyPrint {version} | WeasyPrint {version} with weasysvg |", "|---|---|---|"]
    lines += [f"| {LABELS[key]} | {native[key]} | {ours[key]} |" for key in VERDICTS]
    return "\n".join(lines)


def page(resvg_errors: dict[str, str]) -> str:
    index = json.loads((INDEX).read_text())
    verdicts = {v["name"]: v for v in json.loads((CORPUS / "verdicts.json").read_text())}
    version = json.loads((CORPUS / "baseline.json").read_text()).get("weasyprint", "")
    resvg_version = importlib.metadata.version("resvg-py")
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in index:
        groups.setdefault(item["group"], []).append(item)
    contents = "\n".join(f"- [{GROUPS.get(group, group)}](#{anchor(GROUPS.get(group, group))}) ({len(items)})" for group, items in groups.items())
    sections = []
    for group, items in groups.items():
        sections.append(f"## {GROUPS.get(group, group)}\n")
        sections += [entry(item, verdicts.get(item["name"], {}), resvg_errors.get(item["name"])) for item in items]
    intro = (
        "# Corpus comparison\n\n"
        "<!-- Written by make comparison (tools/visual/comparison.py). Do not edit by hand. -->\n\n"
        f"Each SVG of the corpus in four renderings: Chromium, the reference; resvg (resvg-py {resvg_version}); "
        f"WeasyPrint {version} alone; and WeasyPrint {version} with weasysvg. The WeasyPrint panels are PDFium "
        "rasterizations at 96 dpi; resvg renders the SVG at the width of the page. Every panel is cropped to the "
        "ink of the Chromium reference, so the four line up pixel for pixel. The verdicts come from a visual review, see "
        "[`verdicts.json`](verdicts.json). Click a panel for its full size. The interactive page, with large "
        "panels and a flip between renderers: <https://grigoriev.github.io/weasysvg/corpus/comparison.html>.\n\n"
    )
    return intro + summary(list(verdicts.values()), version) + "\n\n" + contents + "\n\n" + "\n".join(sections)


def html_page(resvg_errors: dict[str, str]) -> str:
    """The interactive page: the template with the panels, verdicts and notes of every SVG as JSON."""
    verdicts = {v["name"]: v for v in json.loads((CORPUS / "verdicts.json").read_text())}
    version = json.loads((CORPUS / "baseline.json").read_text()).get("weasyprint", "")
    counts = Counter(v.get("verdict") for v in verdicts.values())
    items = []
    for item in json.loads((INDEX).read_text()):
        name, verdict = item["name"], verdicts.get(item["name"], {})
        found = {label.lower(): f"{folder}/{name}.png" for label, folder in COLUMNS if (CORPUS / folder / f"{name}.png").exists()}
        size = Image.open(CORPUS / found["chromium"]).size if "chromium" in found else (0, 0)
        items.append(
            {
                "name": name,
                "group": item["group"],
                "source": item["source"],
                "verdict": verdict.get("verdict"),
                "native": verdict.get("native_verdict"),
                "what": verdict.get("what") or "",
                "width": size[0],
                "height": size[1],
                "panels": {label.lower(): found.get(label.lower()) for label, _ in COLUMNS},
                "errors": {"resvg": resvg_errors[name]} if name in resvg_errors else {},
            }
        )
    data = {
        "intro": (
            f"Each SVG of the corpus in Chromium, the reference; resvg (resvg-py {importlib.metadata.version('resvg-py')}); "
            f"WeasyPrint {version} alone; and WeasyPrint {version} with weasysvg. Every panel is cropped to the ink of the "
            "Chromium reference, so the four line up pixel for pixel. Click a panel for its full size."
        ),
        "renderers": {label.lower(): label for label, _ in COLUMNS},
        "groups": GROUPS,
        # Every verdict, those no SVG has included: the filter lists them all
        "counts": {key: counts[key] for key in VERDICTS},
        "items": items,
    }
    # "</" inside the JSON would end the script element
    return HTML_TEMPLATE.read_text().replace("/*DATA*/", json.dumps(data).replace("</", "<\\/"))


def main() -> None:
    for _, folder in COLUMNS:
        (CORPUS / folder).mkdir(parents=True, exist_ok=True)
    errors = {}
    for item in json.loads((INDEX).read_text()):
        error = panels(item)
        if error:
            errors[item["name"]] = error
            print(f"{item['name']}: {error}")
    PAGE.write_text(page(errors))
    HTML_PAGE.write_text(html_page(errors))
    print(f"wrote {PAGE.relative_to(ROOT)} and {HTML_PAGE.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
