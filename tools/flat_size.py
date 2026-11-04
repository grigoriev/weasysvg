"""The size of the flat SVG of each corpus file and how far it strays from the PDF, for a few widths of an opacity level.

Run in the test image: the flat SVG needs pdftocairo, the comparison librsvg. The comparison is that of
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


def main(out: str) -> None:
    weasysvg.install()
    rows = []
    for folder in FOLDERS:
        for path in sorted((CORPUS / folder).glob("*.svg")):
            name = f"{folder}/{path.name}"
            document = path.read_bytes()
            try:
                width = round(size_px(document, 96, 96)[0] * SCALE)
                expected = reference(document, width)
            except (ConvertError, ValueError) as error:
                print(f"{name}: {error}", file=sys.stderr)
                continue
            for band in BANDS:
                start = time.perf_counter()
                try:
                    flat = to_svg(document, band_px=band)
                except ConvertError as error:
                    print(f"{name} {band}: {error}", file=sys.stderr)
                    continue
                seconds = time.perf_counter() - start
                try:
                    actual = drawn(flat, expected.size)
                except subprocess.CalledProcessError as error:
                    # librsvg refuses some drawings, a very large one among them
                    print(f"{name} {band}: librsvg: {error.stderr.decode(errors='replace').strip()}", file=sys.stderr)
                    mean, peak = -1.0, -1
                else:
                    difference = ImageChops.difference(expected.filter(ImageFilter.GaussianBlur(BLUR)), actual.filter(ImageFilter.GaussianBlur(BLUR))).convert("L")
                    mean, peak = ImageStat.Stat(difference).mean[0], cast("tuple[int, int]", difference.getextrema())[1]
                rows.append({"name": name, "band_px": band, "bytes": len(flat), "clips": len(re.findall(rb"<clipPath", flat)), "seconds": round(seconds, 2), "mean": round(mean, 3), "peak": peak})
                print(rows[-1], file=sys.stderr)
    with open(out, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1])
