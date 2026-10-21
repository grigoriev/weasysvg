"""Compare the renderings of each corpus SVG region by region, at twice the resolution of the references.

Usage: review.py [--only TEXT] [--grid N] [--scale N]

Run make visual-baseline first: it writes the PDFs of weasysvg and of WeasyPrint alone. The PDFs of
Chromium are printed here when tools/visual/out/chromium lacks them, as make references prints them.

Every rendering is drawn at --scale times 96 dpi and cropped to the box of the Chromium panel: Chromium,
WeasyPrint and weasysvg from their PDFs through PDFium, resvg at the scaled width, and for the resvg tests
the expected PNG of the suite, scaled to the page. A difference of a few px in a panel is a difference of
twice as many here, while antialiasing stays one px wide.

For each pair that matters the script measures the mean difference in each cell of an N x N grid, the
least over shifts of one px, and writes:

- out/review/review.json: per SVG and pair, the worst cell and the number of cells that differ, and
  the renderings that are missing;
- out/review/<name>.png: the renderings in a row, each cell where weasysvg differs from the reference of
  corpus/verdicts.json framed in red, and those cells of the reference and weasysvg side by side.

A cell differs when its mean passes CELL_LIMIT, or when one tile of TILE px in it passes TILE_LIMIT: a
small mark, missing in a large cell, barely moves the mean of the cell.

The numbers point at the cells to look at; the verdict comes from looking at them. Chromium and resvg are
one reference ("both") only where they agree in every cell.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
from pathlib import Path
from typing import Any

import numpy as np
import resvg_py
from comparison import in_px, inside
from imaging import ink_box, raster
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"
VISUAL = ROOT / "tools" / "visual" / "out"
OUT = VISUAL / "review"
PDFS = {"chromium": VISUAL / "chromium", "weasysvg": VISUAL / "weasysvg" / "pdf", "weasyprint": VISUAL / "native" / "pdf"}
PAIRS = (("chromium", "resvg"), ("chromium", "suite"), ("resvg", "suite"), ("weasysvg", "chromium"), ("weasysvg", "resvg"), ("weasysvg", "suite"), ("weasyprint", "chromium"), ("weasyprint", "resvg"))
# A cell differs when its mean difference passes this many of 255: antialiasing alone stays below
CELL_LIMIT = 4.0
TILE = 8  # px, tiles overlap by half: a mark of 5 px has 4 x 4 px inside one tile
# A tile differs past this: a glyph hinted apart or an antialiased edge reaches 40, a 5 px mark 64
TILE_LIMIT = 48.0
SHIFT = 1  # px: the offset a cell may have and still match
MAX_ZOOMED = 12


def crop_box(item: dict[str, Any], scale: int) -> tuple[int, int, int, int] | None:
    """The box of the Chromium panel on the page, at scale."""
    box = item.get("reference_box")
    reference = CORPUS / "reference" / "chromium" / f"{item['name']}.png"
    if not box or not reference.exists():
        return None
    image = Image.open(reference).convert("RGB")
    ink = ink_box([image]) or (0, 0, *image.size)
    return (scale * (box[0] + ink[0]), scale * (box[1] + ink[1]), scale * (box[0] + ink[2]), scale * (box[1] + ink[3]))


def from_pdf(key: str, item: dict[str, Any], box: tuple[int, int, int, int], scale: int) -> Image.Image | None:
    page = raster(PDFS[key] / f"{item['name']}.pdf", 96 * scale)
    return page.crop(box) if page is not None else None


def on_page(image: Image.Image, item: dict[str, Any], box: tuple[int, int, int, int], scale: int) -> Image.Image:
    """image placed as the <img> of the reference page, at the top left of a white page, cropped to box."""
    page = Image.new("RGB", (scale * item["page_size"][0], scale * item["page_size"][1]), "white")
    rgba = image.convert("RGBA")
    page.paste(rgba, (0, 0), rgba.getchannel("A"))
    return page.crop(box)


def from_resvg(item: dict[str, Any], box: tuple[int, int, int, int], scale: int) -> Image.Image | None:
    svg = inside(CORPUS / "svg" / item["source"])
    try:
        png = bytes(
            resvg_py.svg_to_bytes(
                svg_string=in_px(svg.read_text()),
                resources_dir=str(svg.parent),
                font_dirs=[str(CORPUS / "fonts")],
                width=int(item["width"]) * scale,
                font_family="Liberation Serif",
                serif_family="Liberation Serif",
                sans_serif_family="Liberation Sans",
                monospace_family="DejaVu Sans Mono",
            )
        )
    except BaseException as error:  # noqa: BLE001  a resvg panic surfaces as a BaseException
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            raise
        return None
    return on_page(Image.open(io.BytesIO(png)), item, box, scale)


def from_suite(item: dict[str, Any], box: tuple[int, int, int, int], scale: int) -> Image.Image | None:
    """The expected PNG of the resvg suite, scaled to the <img> of the reference page."""
    path = CORPUS / "reference" / "resvg" / f"{item['name']}.png"
    if not path.exists():
        return None
    expected = Image.open(path)
    width = int(item["width"]) * scale
    return on_page(expected.resize((width, round(width * expected.height / expected.width)), Image.Resampling.LANCZOS), item, box, scale)


Cell = tuple[float, float, tuple[int, int, int, int]]  # mean, worst tile, box


def tile_peak(parts: list[Any]) -> float:
    """The highest mean difference of the TILE x TILE tiles of a cell, a tile every TILE / 2 px, each at its best shift.

    parts holds the difference of the cell at each shift. A partial tile at the edges counts as whole.
    """
    half = TILE // 2
    height, width = parts[0].shape
    padded = np.zeros((len(parts), -(-height // half) * half, -(-width // half) * half))
    padded[:, :height, :width] = parts
    quarters = padded.reshape(len(parts), padded.shape[1] // half, half, padded.shape[2] // half, half).mean(axis=(2, 4))
    if quarters.shape[1] > 1:
        quarters = (quarters[:, 1:] + quarters[:, :-1]) / 2
    if quarters.shape[2] > 1:
        quarters = (quarters[:, :, 1:] + quarters[:, :, :-1]) / 2
    return float(np.max(np.min(quarters, axis=0)))


def differs(cell: Cell) -> bool:
    return cell[0] > CELL_LIMIT or cell[1] > TILE_LIMIT


def cells(a: Image.Image, b: Image.Image, grid: int) -> list[Cell]:
    """The mean difference and the worst tile of each cell of a grid x grid split, worst mean first, with its box.

    Each cell, and each tile in it, takes the least difference over shifts of b by up to SHIFT px: an edge
    placed a fraction of a pixel apart, which antialiasing spreads over two pixels, is no difference to the eye.
    """
    first, second = np.asarray(a, dtype=np.int16), np.asarray(b, dtype=np.int16)
    height, width = first.shape[:2]
    diffs = [np.abs(first - np.roll(second, (dy, dx), axis=(0, 1))).max(axis=2) for dy in range(-SHIFT, SHIFT + 1) for dx in range(-SHIFT, SHIFT + 1)]
    out = []
    for row in range(grid):
        for column in range(grid):
            box = (column * width // grid, row * height // grid, (column + 1) * width // grid, (row + 1) * height // grid)
            if box[2] > box[0] and box[3] > box[1]:
                parts = [diff[box[1] : box[3], box[0] : box[2]] for diff in diffs]
                out.append((round(min(float(part.mean()) for part in parts), 2), round(tile_peak(parts), 2), box))
    return sorted(out, key=lambda entry: -entry[0])


def sheet(images: dict[str, Image.Image], reference: str, bad: list[tuple[int, int, int, int]], path: Path) -> None:
    """The renderings in a row with the differing cells framed, then those cells of the reference and weasysvg."""
    shown = [key for key in ("chromium", "suite", "resvg", "weasysvg") if key in images]
    width, height = images["chromium"].size
    row = Image.new("RGB", (len(shown) * (width + 10), height + 20), (60, 60, 60))
    draw = ImageDraw.Draw(row)
    for index, key in enumerate(shown):
        x = index * (width + 10)
        row.paste(images[key], (x, 20))
        draw.text((x, 4), key, fill="yellow")
        for box in bad:
            draw.rectangle((x + box[0], 20 + box[1], x + box[2], 20 + box[3]), outline="red")
    tiles = []
    for box in bad[:MAX_ZOOMED]:
        pair = [images[key].crop(box) for key in (reference, "weasysvg")]
        tile = Image.new("RGB", (pair[0].width * 2 + 6, pair[0].height), (200, 0, 0))
        tile.paste(pair[0], (0, 0))
        tile.paste(pair[1], (pair[0].width + 6, 0))
        tiles.append(tile)
    out = Image.new("RGB", (max([row.width] + [tile.width for tile in tiles]), row.height + sum(tile.height + 6 for tile in tiles)), (60, 60, 60))
    out.paste(row, (0, 0))
    y = row.height
    for tile in tiles:
        out.paste(tile, (0, y + 6))
        y += tile.height + 6
    out.save(path)


def references(reference: str, images: dict[str, Image.Image]) -> list[str]:
    """The renderings weasysvg is judged against: both for "both", Chromium for "browser"."""
    keys = {"both": ["chromium", "resvg"], "resvg": ["resvg"]}.get(reference, ["chromium"])
    return [key for key in keys if key in images] or ["chromium"]


def review(item: dict[str, Any], reference: str, grid: int, scale: int) -> dict[str, Any] | None:
    box = crop_box(item, scale)
    if box is None:
        return None
    found = {key: from_pdf(key, item, box, scale) for key in PDFS} | {"resvg": from_resvg(item, box, scale), "suite": from_suite(item, box, scale)}
    images = {key: image for key, image in found.items() if image is not None}
    if "chromium" not in images:
        return None
    pairs = {}
    for a, b in PAIRS:
        if a in images and b in images:
            measured = cells(images[a], images[b], grid)
            pairs[f"{a}~{b}"] = {"worst": measured[0][0], "cells": sum(1 for cell in measured if differs(cell))}
    if "weasysvg" in images:
        keys = references(reference, images)
        bad = list(dict.fromkeys(cell[2] for key in keys for cell in cells(images[key], images["weasysvg"], grid) if differs(cell)))
        sheet(images, keys[0], bad, OUT / f"{item['name']}.png")
    return {"name": item["name"], "pairs": pairs, "missing": sorted(set(found) - set(images))}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", default="", help="review only the names that contain this text")
    parser.add_argument("--grid", type=int, default=8, help="cells per side")
    parser.add_argument("--scale", type=int, default=2, help="times the 96 dpi of the panels")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    items = [item for item in json.loads((CORPUS / "index.json").read_text()) if args.only in item["name"]]
    missing = [item for item in items if not (PDFS["chromium"] / f"{item['name']}.pdf").exists()]
    if missing:
        from make_references import print_pdfs

        asyncio.run(print_pdfs(missing))
    chosen = {verdict["name"]: verdict["reference"] for verdict in json.loads((CORPUS / "verdicts.json").read_text())}
    results = [result for item in items if (result := review(item, chosen.get(item["name"], "chromium"), args.grid, args.scale))]
    (OUT / "review.json").write_text(json.dumps(results, indent=1) + "\n")
    print(f"{len(results)} SVGs reviewed at {args.scale}x into {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
