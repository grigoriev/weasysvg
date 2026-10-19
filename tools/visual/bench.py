"""The visual regression bench: render the corpus with WeasyPrint and weasysvg, compare with Chromium.

Usage: bench.py [--only TEXT] [--out DIR]

1. Each corpus SVG is wrapped in the page the references were made from: an <img> with a data URL,
   sized by the width in corpus/index.json, on a 2000 px page.
2. The PDF is rasterized with PDFium at 96 dpi and compared with the Chromium reference (imaging.mismatch).
3. DIR/report.html shows Chromium, weasysvg and the resvg reference side by side, worst mismatch first.

A dev tool, not a CI gate: the numbers guide the eye, the verdicts in corpus/verdicts.json are the judgment.
Run it through make visual: the visual image has the fonts of the references.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import logging
import time
from pathlib import Path
from typing import Any

import weasyprint
from imaging import METRIC_DPI, ink_box, mismatch, padded, raster
from PIL import Image

import weasysvg

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"
PANEL = 420  # max panel width in the report, px


def page(svg: bytes, width: float | None) -> str:
    """The page of the references, byte for byte: the width as the service computes it."""
    style = f' style="width:{width}px"' if width else ""
    data = base64.b64encode(svg).decode()
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>@page{{size:2000px 2000px;margin:0}} body{{margin:0}} img{{display:block}}</style></head><body><img{style} src=\"data:image/svg+xml;base64,{data}\"></body></html>"


class Warnings(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage()[:200])


def reference(item: dict[str, Any], size: tuple[int, int]) -> Image.Image | None:
    """The Chromium reference, put back on a white page at its crop box."""
    path = CORPUS / "reference" / "chromium" / f"{item['name']}.png"
    box = item.get("reference_box")
    if not path.exists() or not box:
        return None
    canvas = Image.new("RGB", size, "white")
    canvas.paste(Image.open(path).convert("RGB"), (box[0], box[1]))
    return canvas


def panel(image: Image.Image, target: Path) -> str:
    if image.width > PANEL:
        image = image.resize((PANEL, max(1, round(image.height * PANEL / image.width))), Image.Resampling.LANCZOS)
    image.save(target, "WEBP", quality=85)
    return f"img/{target.name}"


def run(item: dict[str, Any], out: Path, handler: Warnings) -> dict[str, Any]:
    name = item["name"]
    handler.messages = []
    pdf = out / "pdf" / f"{name}.pdf"
    start = time.perf_counter()
    error = None
    try:
        pdf.write_bytes(weasyprint.HTML(string=page((CORPUS / "svg" / item["source"]).read_bytes(), item["width"])).write_pdf())
    except Exception as e:  # noqa: BLE001  one broken SVG must not stop the bench
        error = repr(e)[:300]
    row: dict[str, Any] = {"name": name, "group": item["group"], "ms": round((time.perf_counter() - start) * 1000, 1), "error": error, "warnings": handler.messages[:5]}
    ours = raster(pdf) if error is None else None
    ref = reference(item, ours.size) if ours is not None else None
    box = ink_box([image for image in (ours, ref) if image is not None])
    if ours is None or ref is None or box is None:
        row["mismatch"] = None
        return row
    box = padded(box)
    row["mismatch"] = round(mismatch(ref.crop(box), ours.crop(box)), 1)
    row["panels"] = [panel(ref.crop(box), out / "img" / f"{name}.chromium.webp"), panel(ours.crop(box), out / "img" / f"{name}.weasysvg.webp")]
    resvg = CORPUS / "reference" / "resvg" / f"{name}.png"
    if resvg.exists():
        image = Image.open(resvg).convert("RGBA")
        flat = Image.new("RGB", image.size, "white")
        flat.paste(image, mask=image.getchannel("A"))
        row["panels"].append(panel(flat, out / "img" / f"{name}.resvg.webp"))
    return row


STYLE = """
:root{--bg:#fff;--fg:#1d1d1f;--muted:#666;--line:#ddd;--bad:#c62828;--ok:#2e7d32}
@media (prefers-color-scheme:dark){:root{--bg:#161618;--fg:#eee;--muted:#aaa;--line:#333;--bad:#ef5350;--ok:#66bb6a}}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px system-ui,sans-serif}
h1{font-size:20px}section{border-top:1px solid var(--line);padding:12px 0}
.meta{color:var(--muted)}.bad{color:var(--bad)}.ok{color:var(--ok)}
.row{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start}
figure{margin:0}figcaption{color:var(--muted);font-size:12px}img{background:#fff;max-width:100%;border:1px solid var(--line)}
"""


def _status(row: dict[str, Any], verdict: dict[str, Any]) -> str:
    """The CSS class of the verdict: bad for an error or a broken rendering, ok for the same one."""
    if row["error"] or verdict.get("verdict") == "broken":
        return "bad"
    if verdict.get("verdict") == "same":
        return "ok"
    return ""


def report(rows: list[dict[str, Any]], verdicts: dict[str, dict[str, Any]], out: Path) -> None:
    rows = sorted(rows, key=lambda row: -(row["mismatch"] if row["mismatch"] is not None else 101))
    labels = ("Chromium", "weasysvg", "resvg reference")
    sections = []
    for row in rows:
        verdict = verdicts.get(row["name"], {})
        figures = "".join(f'<figure><img src="{src}" alt=""><figcaption>{label}</figcaption></figure>' for src, label in zip(row.get("panels", []), labels, strict=False))
        value = "n/a" if row["mismatch"] is None else f"{row['mismatch']}%"
        status = _status(row, verdict)
        details = html.escape(row["error"] or verdict.get("what") or "")
        sections.append(
            f'<section><h2>{html.escape(row["name"])}</h2><p class="meta">mismatch {value} · {row["ms"]} ms · verdict '
            f'<span class="{status}">{html.escape(str(verdict.get("verdict")))}</span> {details}</p><div class="row">{figures}</div></section>'
        )
    measured = [row["mismatch"] for row in rows if row["mismatch"] is not None]
    summary = f"{len(rows)} SVGs, {sum(1 for row in rows if row['error'])} errors, median mismatch {sorted(measured)[len(measured) // 2] if measured else 'n/a'}%"
    head = f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>weasysvg bench</title><style>{STYLE}</style></head>'
    body = f'<body><h1>weasysvg against Chromium</h1><p class="meta">{summary}. Rasterized with PDFium at {METRIC_DPI} dpi.</p>{"".join(sections)}</body></html>'
    document = head + body
    (out / "report.html").write_text(document)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", default="", help="render only the names that contain this text")
    parser.add_argument("--out", type=Path, default=ROOT / "tools" / "visual" / "out")
    args = parser.parse_args()
    out: Path = args.out
    (out / "pdf").mkdir(parents=True, exist_ok=True)
    (out / "img").mkdir(parents=True, exist_ok=True)
    features = weasysvg.install()
    print("features:", ", ".join(sorted(features)), "| resvg:", weasysvg.raster.available(), flush=True)
    handler = Warnings()
    for logger in ("weasyprint", "weasysvg"):
        logging.getLogger(logger).addHandler(handler)
    index = [item for item in json.loads((CORPUS / "index.json").read_text()) if args.only in item["name"]]
    verdicts = {verdict["name"]: verdict for verdict in json.loads((CORPUS / "verdicts.json").read_text())}
    rows = []
    for item in index:
        row = run(item, out, handler)
        rows.append(row)
        print(f"{row['name']}: mismatch {row['mismatch']} in {row['ms']} ms {row['error'] or ''}", flush=True)
    (out / "rows.json").write_text(json.dumps(rows, indent=1) + "\n")
    report(rows, verdicts, out)
    print(f"{len(rows)} SVGs, report at {out / 'report.html'}")


if __name__ == "__main__":
    main()
