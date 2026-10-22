"""Write corpus/COMPARISON.md: each corpus SVG in Chromium, resvg, WeasyPrint alone and WeasyPrint with weasysvg.

Usage: comparison.py

Run it through make comparison: the bench writes the PDFs of WeasyPrint and weasysvg first. The PDFs of
Chromium are printed here, as make references prints them, when tools/visual/out/chromium lacks them or
holds one that no longer prints its reference. This
script rasterizes the PDFs at SCALE times 96 dpi, and renders resvg on a page like the one of the
references, at SCALE times the width of the page and with the fonts Chromium picks.

Every panel is cropped to the same box: the ink of the Chromium reference, without a margin. The panels
go into corpus/render as lossless WebP, sharp at a zoom of SCALE. The page is Markdown, so GitHub shows it
in the repository.
"""

from __future__ import annotations

import asyncio
import html
import importlib.metadata
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import resvg_py
from fontTools.ttLib import TTFont
from imaging import METRIC_DPI, ink_box, raster
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"
INDEX = CORPUS / "index.json"
PAGE = CORPUS / "COMPARISON.md"
# The interactive page, for GitHub Pages: the template next to this script, with the data put in
HTML_PAGE = CORPUS / "comparison.html"
HTML_TEMPLATE = Path(__file__).with_name("comparison.html")
WIDTH = 200  # px of each panel on the page; a click opens the full image
SCALE = 2  # the panels have this many pixels per CSS px
GROUPS = {
    "diagrams": "Diagrams from kroki and mermaid.ink",
    "drawio": "draw.io",
    "fo": "foreignObject",
    "pdf-exporter": "SBB pdf-exporter",
    "real": "Wikimedia Commons",
    "resvg": "resvg feature tests",
    "text": "Text written for this corpus",
}
# Each verdict compares a rendering with the reference of its SVG
VERDICTS = ("better", "same", "close", "differs")
LABELS = {"better": "better than the reference", "same": "matches the reference", "close": "close to the reference", "differs": "differs from the reference"}
ICONS = {"better": "⬆️", "same": "✅", "close": "🟡", "differs": "❌"}
# The reference of an SVG: the renderer, or both, judged right for it
REFERENCES = {"chromium": "Chromium", "resvg": "resvg", "both": "Chromium and resvg"}
COLUMNS = (("Chromium", "render/chromium"), ("resvg", "render/resvg"), ("WeasyPrint", "render/weasyprint"), ("weasysvg", "render/weasysvg"))
# The PDFs of each rendering: make references prints Chromium, make comparison runs the bench
VISUAL = ROOT / "tools" / "visual" / "out"
PDFS = {"chromium": VISUAL / "chromium", "weasyprint": VISUAL / "native" / "pdf", "weasysvg": VISUAL / "weasysvg" / "pdf"}
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
    """The page of the SVG through resvg, on white, at SCALE times the width of the page; or why there is none."""
    image = resvg_image(item, SCALE)
    if isinstance(image, str):
        return image
    # The <img> of the references sits at the top left of a white page
    size = item.get("page_size")
    page = Image.new("RGB", (SCALE * size[0], SCALE * size[1]) if size else image.size, "white")
    page.paste(image, (0, 0), mask=image.getchannel("A"))
    return page


def resvg_image(item: dict[str, Any], scale: int = 1) -> Image.Image | str:
    """The SVG through resvg at scale times the width of the page, transparent; or why there is none."""
    svg = inside(CORPUS / "svg" / item["source"])
    try:
        # The families Chromium resolves the generic names to, in the visual image
        png = bytes(
            resvg_py.svg_to_bytes(
                svg_string=in_px(svg.read_text()),
                resources_dir=str(svg.parent),
                # resvg reads no fontconfig: it gets the fonts of the corpus by their directory
                font_dirs=[str(CORPUS / "fonts")],
                width=int(item["width"]) * scale if item.get("width") else None,
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
    return Image.open(io.BytesIO(png)).convert("RGBA")


def stale(item: dict[str, Any]) -> bool:
    """Whether the Chromium PDF of item is missing or no longer prints its reference.

    tools/visual/out is a local cache: a PDF printed before the references changed would crop the old
    drawing to the new box. The reference comes from the same PDFium at METRIC_DPI, so it matches byte for byte.
    """
    rendered = raster(PDFS["chromium"] / f"{item['name']}.pdf")
    if rendered is None:
        return True
    reference = Image.open(CORPUS / "reference" / "chromium" / f"{item['name']}.png").convert("RGB")
    return rendered.crop(tuple(item["reference_box"])).tobytes() != reference.tobytes()


def save(image: Image.Image, folder: str, name: str) -> None:
    # Lossless: a lossy panel would show artifacts no renderer drew; method 6 packs it tightest
    image.save(CORPUS / folder / f"{name}.webp", "WEBP", lossless=True, quality=100, method=6)


def panels(item: dict[str, Any]) -> tuple[str | None, list[str]]:
    """Write the four panels of item, each cropped to the ink of the Chromium reference.

    Returns a resvg failure and the renderings whose PDF is missing.
    """
    name, box = item["name"], item.get("reference_box")
    inside(CORPUS / "render" / f"{name}.webp")  # a name with a path in it would write elsewhere
    for _, folder in COLUMNS:
        (CORPUS / folder / f"{name}.webp").unlink(missing_ok=True)
    if not box:
        return None, []
    reference = Image.open(CORPUS / "reference" / "chromium" / f"{name}.png").convert("RGB")
    ink: Box = ink_box([reference]) or (0, 0, *reference.size)
    # The box of the Chromium panel on the page, at SCALE
    absolute = (SCALE * (box[0] + ink[0]), SCALE * (box[1] + ink[1]), SCALE * (box[0] + ink[2]), SCALE * (box[1] + ink[3]))
    missing = []
    for key, pdfs in PDFS.items():
        rendered = raster(pdfs / f"{name}.pdf", METRIC_DPI * SCALE)
        if rendered is None:
            missing.append(key)
        else:
            save(rendered.crop(absolute), f"render/{key}", name)
    page = render_resvg(item)
    if isinstance(page, str):
        return page, missing
    resvg = page.crop(absolute)
    if ink_box([resvg]) is None:
        return "resvg draws nothing", missing
    save(resvg, "render/resvg", name)
    return None, missing


def anchor(title: str) -> str:
    """The anchor GitHub gives a heading: lowercase, spaces to hyphens, punctuation dropped."""
    return "".join(c for c in title.lower().replace(" ", "-") if c.isalnum() or c in "-_")


def cell(name: str, label: str, folder: str, missing: str) -> str:
    path = f"{folder}/{name}.webp"
    if not (CORPUS / path).exists():
        return html.escape(missing)
    return f'<a href="{path}"><img src="{path}" width="{WIDTH}" alt="{name} in {label}"></a>'


def judged(icon: str, who: str, status: str, what: str | None) -> str:
    """One row of the verdict table of an SVG: an icon, the renderer, its verdict and what differs."""
    # A | inside a cell would end it
    note = html.escape(what or "").replace("|", "\\|")
    return f"| {icon} | {who} | {status} | {note} |"


def entry(item: dict[str, Any], verdict: dict[str, Any], resvg_error: str | None) -> str:
    name = item["name"]
    ours, native = verdict.get("verdict") or "", verdict.get("native_verdict") or ""
    rows = [
        "| | Renderer | Verdict | What |",
        "|---|---|---|---|",
        judged("📌", "Reference", REFERENCES.get(verdict.get("reference") or "", "n/a"), verdict.get("reference_why")),
        judged(ICONS.get(ours, ""), "weasysvg", f"**{LABELS.get(ours, 'n/a')}**", verdict.get("what")),
        judged(ICONS.get(native, ""), "WeasyPrint", f"**{LABELS.get(native, 'n/a')}**", verdict.get("native_what")),
    ]
    header = "| " + " | ".join(label for label, _ in COLUMNS) + " |"
    row = "| " + " | ".join(cell(name, label, folder, (resvg_error if label == "resvg" else None) or "n/a") for label, folder in COLUMNS) + " |"
    source = f"[`{item['source']}`](svg/{item['source']})"
    return f"### {name}\n\n{source}\n\n" + "\n".join(rows) + f"\n\n{header}\n|---|---|---|---|\n{row}\n"


def summary(verdicts: list[dict[str, Any]], version: str) -> str:
    native, ours = Counter(v.get("native_verdict") for v in verdicts), Counter(v.get("verdict") for v in verdicts)
    lines = [f"| Verdict | WeasyPrint {version} | WeasyPrint {version} with weasysvg |", "|---|---|---|"]
    lines += [f"| {ICONS[key]} {LABELS[key]} | {native[key]} | {ours[key]} |" for key in VERDICTS]
    references = Counter(v.get("reference") for v in verdicts)
    lines += ["", "References: " + ", ".join(f"{label} {references[key]}" for key, label in REFERENCES.items()) + "."]
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
        f"Each SVG of the corpus in four renderings: Chromium; resvg (resvg-py {resvg_version}); "
        f"WeasyPrint {version} alone; and WeasyPrint {version} with weasysvg. The Chromium and WeasyPrint panels are "
        f"PDFium rasterizations at {METRIC_DPI * SCALE} dpi, {SCALE}x the CSS px; resvg renders the SVG at {SCALE}x the width of the page. Every panel is cropped to the "
        "ink of the Chromium panel, so the four line up pixel for pixel. Each SVG has a reference: Chromium, resvg or both. "
        "The verdicts compare weasysvg and WeasyPrint with that "
        "reference; they come from a visual review at full size, see "
        "[`verdicts.json`](verdicts.json). Click a panel for its full size. The interactive page, with large "
        "panels, your own browser and a swipe between renderers: <https://grigoriev.github.io/weasysvg/corpus/comparison.html>.\n\n"
    )
    return intro + summary(list(verdicts.values()), version) + "\n\n" + contents + "\n\n" + "\n".join(sections)


def corpus_fonts() -> list[dict[str, Any]]:
    """The fonts of corpus/fonts for the live panel: the page puts each into the SVGs that name its family.

    An SVG in an <img> sees no font of the page, only the fonts in it, so the page adds @font-face rules
    with the font as a data URL to a copy of the SVG.
    """
    out = []
    for path in sorted((CORPUS / "fonts").glob("*.ttf")):
        font = TTFont(path, lazy=True)
        names = font["name"]
        family = names.getDebugName(16) or names.getDebugName(1)
        italic = bool(font["OS/2"].fsSelection & 1)
        out.append({"family": family, "weight": font["OS/2"].usWeightClass, "style": "italic" if italic else "normal", "file": f"fonts/{path.name}"})
    return out


def browser_crop(item: dict[str, Any]) -> dict[str, Any] | None:
    """Where the Chromium panel sits on the page of the references, and the size of the <img> there.

    The browser panel draws the SVG itself and crops it there. resvg gives the height of the <img> at the
    width of the page, as a browser sizes the SVG.
    """
    reference = CORPUS / "reference" / "chromium" / f"{item['name']}.png"
    box = item.get("reference_box")
    if not box or not reference.exists():
        return None
    ink = ink_box([Image.open(reference).convert("RGB")])
    drawn = resvg_image(item)
    if ink is None or not isinstance(drawn, Image.Image):
        return None
    return {"x": box[0] + ink[0], "y": box[1] + ink[1], "page": item["width"], "pageHeight": drawn.height}


def html_page(resvg_errors: dict[str, str]) -> str:
    """The interactive page: the template with the panels, verdicts and notes of every SVG as JSON."""
    verdicts = {v["name"]: v for v in json.loads((CORPUS / "verdicts.json").read_text())}
    version = json.loads((CORPUS / "baseline.json").read_text()).get("weasyprint", "")
    counts = Counter(v.get("verdict") for v in verdicts.values())
    items = []
    for item in json.loads((INDEX).read_text()):
        name, verdict = item["name"], verdicts.get(item["name"], {})
        found = {label.lower(): f"{folder}/{name}.webp" for label, folder in COLUMNS if (CORPUS / folder / f"{name}.webp").exists()}
        # The page lays the panels out in CSS px, SCALE pixels each
        size = Image.open(CORPUS / found["chromium"]).size if "chromium" in found else (0, 0)
        size = (size[0] // SCALE, size[1] // SCALE)
        crop = browser_crop(item)
        items.append(
            {
                "name": name,
                "group": item["group"],
                "source": item["source"],
                "reference": verdict.get("reference"),
                "referenceWhy": verdict.get("reference_why") or "",
                "verdict": verdict.get("verdict"),
                "what": verdict.get("what") or "",
                "native": verdict.get("native_verdict"),
                "nativeWhat": verdict.get("native_what") or "",
                "width": size[0],
                "height": size[1],
                "panels": {label.lower(): found.get(label.lower()) for label, _ in COLUMNS} | {"browser": f"svg/{item['source']}" if crop else None},
                "crop": crop,
                "errors": {"resvg": resvg_errors[name]} if name in resvg_errors else {},
            }
        )
    data = {
        "intro": (
            f"Each SVG of the corpus in Chromium; resvg (resvg-py {importlib.metadata.version('resvg-py')}); "
            f"WeasyPrint {version} alone; and WeasyPrint {version} with weasysvg. The browser panel is the SVG itself, drawn by "
            "the browser you read this page in. Every panel is cropped to the ink of the Chromium reference, so they line up "
            "pixel for pixel. The verdicts compare weasysvg and WeasyPrint with the reference of each SVG, marked on its panel. "
            "Click a panel to swipe between two renderers at full size."
        ),
        # The browser panel comes second, next to the other browser
        "renderers": {"chromium": "Chromium", "browser": "This browser"} | {label.lower(): label for label, _ in COLUMNS[1:]},
        "groups": GROUPS,
        "labels": LABELS,
        "fonts": corpus_fonts(),
        "references": REFERENCES,
        # Every verdict, those no SVG has included: the filter lists them all
        "counts": {key: counts[key] for key in VERDICTS},
        "items": items,
    }
    # "</" inside the JSON would end the script element
    return HTML_TEMPLATE.read_text().replace("/*DATA*/", json.dumps(data).replace("</", "<\\/"))


def main() -> int:
    for _, folder in COLUMNS:
        (CORPUS / folder).mkdir(parents=True, exist_ok=True)
    index = json.loads((INDEX).read_text())
    unprinted = [item for item in index if item.get("reference_box") and stale(item)]
    if unprinted:
        from make_references import print_pdfs

        asyncio.run(print_pdfs(unprinted))
    errors, failed = {}, False
    for item in index:
        error, missing = panels(item)
        if error:
            errors[item["name"]] = error
            print(f"{item['name']}: {error}")
        if missing:
            failed = True
            print(f"{item['name']}: no PDF for {', '.join(missing)}")
    PAGE.write_text(page(errors))
    HTML_PAGE.write_text(html_page(errors))
    print(f"wrote {PAGE.relative_to(ROOT)} and {HTML_PAGE.relative_to(ROOT)}")
    # A rendering error would leave the page without a panel
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
