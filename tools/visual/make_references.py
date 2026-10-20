"""Print the corpus with Chromium and turn the PDFs into the reference PNGs, with where each one sits on the page.

Usage: make_references.py [--only TEXT]

Run it through make references: the visual image has the fonts the corpus asks for and the headless
Chromium of Playwright, so the references, weasysvg and resvg see the same fonts.

1. Each SVG is printed by Chromium on the page of the bench (bench.page), in English: a switch with
   systemLanguage picks what an English reader sees.
2. Each PDF is rasterized with PDFium at 96 dpi and cropped to its ink plus a small margin. The crop box
   goes into corpus/index.json, so the bench can put the reference back on a page of the same size.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from bench import page
from imaging import ink_box, padded, raster
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"
PDFS = ROOT / "tools" / "visual" / "out" / "chromium"
PAGE_SIZE = "2000px"


async def print_pdfs(items: list[dict[str, Any]]) -> str:
    """Print every item with Chromium into PDFS; returns the version of Chromium."""
    PDFS.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        context = await browser.new_context(locale="en-US")
        tab = await context.new_page()
        for item in items:
            await tab.set_content(page((CORPUS / "svg" / item["source"]).read_bytes(), item["width"]), wait_until="load")
            await tab.pdf(path=str(PDFS / f"{item['name']}.pdf"), width=PAGE_SIZE, height=PAGE_SIZE, print_background=True)
        version: str = browser.version
        await browser.close()
    return version


def crop(items: list[dict[str, Any]]) -> None:
    """The reference PNG of each item, cropped to its ink, and its box on the page in the index."""
    out = CORPUS / "reference" / "chromium"
    out.mkdir(parents=True, exist_ok=True)
    for item in items:
        image = raster(PDFS / f"{item['name']}.pdf")
        box = ink_box([image]) if image is not None else None
        if image is None or box is None:
            item["reference_box"] = None
            print(f"{item['name']}: no reference")
            continue
        box = padded(box, image.size)
        image.crop(box).save(out / f"{item['name']}.png", optimize=True)
        item["reference_box"] = list(box)
        item["page_size"] = list(image.size)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", default="", help="print only the names that contain this text")
    args = parser.parse_args()
    index_path = CORPUS / "index.json"
    index = json.loads(index_path.read_text())
    items = [item for item in index if args.only in item["name"]]
    version = asyncio.run(print_pdfs(items))
    crop(items)
    index_path.write_text(json.dumps(index, indent=1) + "\n")
    print(f"{len(items)} references, Chromium {version}")


if __name__ == "__main__":
    main()
