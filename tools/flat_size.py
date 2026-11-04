"""The size of the flat SVG of each corpus file and how far it strays from the PDF, for a few widths of an opacity level.

Run in the test image: the flat SVG needs pdftocairo, the comparison librsvg. It writes CSV to stdout. The comparison is that of
tests/test_convert_visual.py: both drawings at 2x, blurred by 2 px, mean and peak of the difference.
"""

from __future__ import annotations

import csv
import io
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import cast

import pypdfium2 as pdfium
from PIL import Image, ImageChops, ImageFilter, ImageStat

import weasysvg
from weasysvg.convert import ConvertError, size_px, to_pdf, to_svg

CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "svg"
FOLDERS = ("diagrams", "drawio", "pdf-exporter", "real", "fo", "text")
BANDS = (0.0, 0.5, 1.0, 2.0, 4.0)
SCALE = 2
BLUR = 2


def reference(document: bytes, width: int) -> Image.Image:
    pdf = pdfium.PdfDocument(to_pdf(document))
    page = pdf[0]
    bitmap = page.render(scale=width / page.get_width(), fill_color=(255, 255, 255, 255))
    image: Image.Image = bitmap.to_pil().convert("RGB")
    bitmap.close()
    page.close()
    pdf.close()
    return image


def drawn(flat: bytes, size: tuple[int, int]) -> Image.Image:
    width, height = size
    png = subprocess.run(["rsvg-convert", "-w", str(width), "-h", str(height), "-b", "white"], input=flat, capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGB").resize(size)


def difference(expected: Image.Image, flat: bytes) -> tuple[float, int]:
    """Mean and peak of the difference of flat from expected; -1 where librsvg refuses it, a very large one among them."""
    try:
        actual = drawn(flat, expected.size)
    except subprocess.CalledProcessError as error:
        print(f"librsvg: {error.stderr.decode(errors='replace').strip()}", file=sys.stderr)
        return -1.0, -1
    blurred = ImageChops.difference(expected.filter(ImageFilter.GaussianBlur(BLUR)), actual.filter(ImageFilter.GaussianBlur(BLUR))).convert("L")
    return ImageStat.Stat(blurred).mean[0], cast("tuple[int, int]", blurred.getextrema())[1]


def measure(name: str, document: bytes, expected: Image.Image, band: float) -> dict[str, object] | None:
    """One row: the flat SVG of document at band, its size, its clip paths, the time it took and its difference."""
    start = time.perf_counter()
    try:
        flat = to_svg(document, band_px=band)
    except ConvertError as error:
        print(f"{name} {band}: {error}", file=sys.stderr)
        return None
    seconds = time.perf_counter() - start
    mean, peak = difference(expected, flat)
    return {"name": name, "band_px": band, "bytes": len(flat), "clips": len(re.findall(rb"<clipPath", flat)), "seconds": round(seconds, 2), "mean": round(mean, 3), "peak": peak}


def rows_of(name: str, document: bytes) -> list[dict[str, object]]:
    """The rows of one corpus file, one per band; none where it does not render."""
    try:
        expected = reference(document, round(size_px(document, 96, 96)[0] * SCALE))
    except (ConvertError, ValueError) as error:
        print(f"{name}: {error}", file=sys.stderr)
        return []
    rows = [row for band in BANDS if (row := measure(name, document, expected, band)) is not None]
    for row in rows:
        print(row, file=sys.stderr)
    return rows


def main() -> None:
    """Write the rows as CSV to stdout, the progress to stderr."""
    weasysvg.install()
    writer = csv.DictWriter(sys.stdout, fieldnames=["name", "band_px", "bytes", "clips", "seconds", "mean", "peak"])
    writer.writeheader()
    for folder in FOLDERS:
        for path in sorted((CORPUS / folder).glob("*.svg")):
            writer.writerows(rows_of(f"{folder}/{path.name}", path.read_bytes()))


if __name__ == "__main__":
    main()
