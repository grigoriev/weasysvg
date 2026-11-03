"""A command line converter from SVG to PDF, PNG or a flat SVG, compatible with the options of ``rsvg-convert`` that pandoc uses.

pandoc calls ``rsvg-convert`` by name: ``-f pdf ... -o out.pdf in.svg`` for a PDF through LaTeX, and
``-f png ...`` from stdin to stdout for the PNG fallback of an SVG in DOCX. Installed under that name,
this converter draws the SVG with WeasyPrint and weasysvg instead of librsvg, so ``<foreignObject>``,
filters and masks render. The PDF stays vector. The PNG is the PDF rasterized by PDFium.

``-f svg`` is not an option of rsvg-convert. It flattens the SVG for Word and LibreOffice: see to_svg().

The size follows ``rsvg-convert``: the ``width`` and ``height`` of the root, in pixels at the given
DPI, or the ``viewBox`` when they are missing or relative. A PDF page is that size at 72 points per
DPI pixels, a PNG has that many pixels.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import math
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from typing import IO, cast

import weasyprint
from weasyprint.urls import URLFetcher

import weasysvg

DEFAULT_DPI = 96.0
# The CSS units an absolute length of the root can carry, in inches
UNIT_INCHES = {"in": 1.0, "cm": 1 / 2.54, "mm": 1 / 25.4, "pt": 1 / 72, "pc": 1 / 6}
# What rsvg takes for a font-relative length on the root, in pixels at 96 DPI
FONT_PX = {"em": 16.0, "ex": 8.0}
LENGTH = re.compile(r"\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Z%]*)\s*$")
VIEWBOX_PARTS = 4
# The largest PNG drawn from an untrusted SVG: one side, and its pixels. The limits of pandoc-service for Chromium
MAX_PNG_SIDE = 10_000
MAX_PNG_PIXELS = 50_000_000
# How long pdftocairo may read back one PDF, in seconds
PDFTOCAIRO_TIMEOUT = 60


class ConvertError(Exception):
    """The SVG cannot be converted."""


def root_attributes(svg: bytes) -> dict[str, str]:
    """The attributes of the root element. The whole document is parsed: WeasyPrint draws nothing for a broken one, silently."""
    parser: ET.XMLPullParser[ET.Element] = ET.XMLPullParser(events=("start",))
    try:
        parser.feed(svg)
        parser.close()
    except ET.ParseError as error:
        raise ConvertError(f"not an SVG document: {error}") from error
    # A parsed document has a root, and its "start" event comes first
    _, root = next(cast("Iterator[tuple[str, ET.Element]]", parser.read_events()))
    return dict(root.attrib)


def length_px(value: str | None, dpi: float) -> float | None:
    """A length of the root in pixels at dpi, or None when it is missing, relative or invalid."""
    if not value:
        return None
    match = LENGTH.match(value)
    if not match:
        return None
    number, unit = float(match.group(1)), match.group(2).lower()
    if unit in ("", "px"):
        return number
    if unit in UNIT_INCHES:
        return number * UNIT_INCHES[unit] * dpi
    if unit in FONT_PX:
        return number * FONT_PX[unit] * dpi / DEFAULT_DPI
    return None


def size_px(svg: bytes, dpi_x: float, dpi_y: float) -> tuple[float, float]:
    """The size of the SVG in pixels, as rsvg-convert computes it."""
    attributes = root_attributes(svg)
    width = length_px(attributes.get("width"), dpi_x)
    height = length_px(attributes.get("height"), dpi_y)
    try:
        box = [float(part) for part in re.split(r"[\s,]+", attributes.get("viewBox", "").strip()) if part]
    except ValueError:
        box = []  # an invalid viewBox is ignored, as in Chromium
    if len(box) == VIEWBOX_PARTS and box[2] > 0 and box[3] > 0:
        if width is None and height is None:
            width, height = box[2], box[3]
        elif width is None:
            width = height * box[2] / box[3]  # type: ignore[operator]
        elif height is None:
            height = width * box[3] / box[2]
    if not width or not height or width <= 0 or height <= 0:
        raise ConvertError("the SVG has no size: no width and height, and no viewBox")
    return width, height


def page_html(svg: bytes, width_pt: float, height_pt: float) -> str:
    """One page of exactly the SVG's size, with the SVG as its only content."""
    data = base64.b64encode(svg).decode("ascii")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
        f"@page{{size:{width_pt}pt {height_pt}pt;margin:0}}"
        "html,body{margin:0;padding:0}"
        f"img{{display:block;width:{width_pt}pt;height:{height_pt}pt}}"
        f'</style></head><body><img src="data:image/svg+xml;base64,{data}"></body></html>'
    )


def to_pdf(svg: bytes, dpi_x: float = DEFAULT_DPI, dpi_y: float = DEFAULT_DPI, *, portable: bool = False) -> bytes:
    """The SVG as a one-page vector PDF. Only data: URLs are fetched, as rsvg-convert fetches no remote file.

    portable draws without soft masks and blend modes where weasysvg can, see weasysvg.portable().
    """
    width, height = size_px(svg, dpi_x, dpi_y)
    html = page_html(svg, width * 72 / dpi_x, height * 72 / dpi_y)
    document = weasyprint.HTML(string=html, url_fetcher=URLFetcher(allowed_protocols={"data"}))
    with weasysvg.portable() if portable else contextlib.nullcontext():
        pdf: bytes = document.write_pdf()
    return pdf


def to_png(svg: bytes, dpi_x: float = DEFAULT_DPI, dpi_y: float = DEFAULT_DPI) -> bytes:
    """The SVG as a PNG of its size in pixels, on a transparent background."""
    import io

    try:
        import pypdfium2 as pdfium
    except ImportError as error:
        raise ConvertError('PNG output needs the convert extra: pip install "weasysvg[convert]"') from error

    width, height = size_px(svg, dpi_x, dpi_y)
    if max(width, height) > MAX_PNG_SIDE or width * height > MAX_PNG_PIXELS:
        raise ConvertError(f"the PNG would be too large: {width:g} x {height:g} pixels")
    document = pdfium.PdfDocument(to_pdf(svg, dpi_x, dpi_y))
    page = document[0]
    bitmap = page.render(scale=dpi_x / 72, fill_color=(255, 255, 255, 0))
    try:
        image = bitmap.to_pil()
    finally:
        # Children first: see tests/helpers.close
        bitmap.close()
        page.close()
        document.close()
    # The page is width x height pixels at dpi_x: only a different dpi_y or the rounding changes it
    target = (max(1, round(width)), max(1, round(height)))
    if image.size != target:
        image = image.resize(target)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def to_svg(svg: bytes, dpi_x: float = DEFAULT_DPI, dpi_y: float = DEFAULT_DPI) -> bytes:
    """The SVG flattened to paths, clips, gradients and images, which Word draws: the portable PDF read back by pdftocairo of Poppler.

    Word draws no <foreignObject> and no filters, and only some masks. The flat SVG keeps the drawing as
    weasysvg renders it, and its text becomes glyph outlines. It is vector where the portable PDF has no
    soft mask: cairo turns each soft mask into an image.
    """
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "in.pdf")
        svg_path = os.path.join(tmp, "out.svg")
        with open(pdf_path, "wb") as handle:
            handle.write(to_pdf(svg, dpi_x, dpi_y, portable=True))
        try:
            result = subprocess.run(["pdftocairo", "-svg", pdf_path, svg_path], capture_output=True, check=False, timeout=PDFTOCAIRO_TIMEOUT)  # noqa: S603, S607
        except FileNotFoundError as error:
            raise ConvertError("SVG output needs pdftocairo of Poppler on the PATH") from error
        except subprocess.TimeoutExpired as error:
            raise ConvertError(f"pdftocairo took longer than {PDFTOCAIRO_TIMEOUT} s") from error
        if result.returncode != 0:
            raise ConvertError(f"pdftocairo failed: {result.stderr.decode(errors='replace').strip()}")
        with open(svg_path, "rb") as handle:
            flat = handle.read()
    width, height = size_px(svg, dpi_x, dpi_y)
    return sized(flat, width * 72 / dpi_x, height * 72 / dpi_y)


def sized(flat: bytes, width_pt: float, height_pt: float) -> bytes:
    """The flat SVG with the size of its root in points. Poppler 25.03 writes it without a unit, which reads as px."""
    for name, value in ((b"width", width_pt), (b"height", height_pt)):
        attribute = re.compile(rb"(<svg\b[^>]*?\s" + name + rb'=")[^"]*(")')
        flat = attribute.sub(rb"\g<1>" + f"{value:g}pt".encode() + rb"\g<2>", flat, count=1)
    return flat


def positive(text: str) -> float:
    """A DPI: a finite number above 0."""
    try:
        value = float(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"not a number: {text}") from error
    if not 0 < value < math.inf:
        raise argparse.ArgumentTypeError(f"not a positive number: {text}")
    return value


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="weasysvg-convert", description="Convert SVG to PDF, PNG or a flat SVG with WeasyPrint and weasysvg. Accepts the rsvg-convert options pandoc uses.")
    parser.add_argument("-f", "--format", default="png", choices=("png", "pdf", "svg"), help="output format (default: png)")
    parser.add_argument("-o", "--output", help="output file (default: stdout)")
    parser.add_argument("-d", "--dpi-x", type=positive, default=DEFAULT_DPI, help="pixels per inch, horizontal (default: 96)")
    parser.add_argument("-p", "--dpi-y", type=positive, default=DEFAULT_DPI, help="pixels per inch, vertical (default: 96)")
    parser.add_argument("-a", "--keep-aspect-ratio", action="store_true", help="accepted for compatibility: the size is always the SVG's own")
    parser.add_argument("input", nargs="?", default="-", help="input SVG file (default: stdin)")
    return parser.parse_args(argv)


def read_input(name: str, stdin: IO[bytes]) -> bytes:
    if name == "-":
        return stdin.read()
    with open(name, "rb") as handle:
        return handle.read()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    weasysvg.install()
    try:
        svg = read_input(args.input, sys.stdin.buffer)
        converter = {"pdf": to_pdf, "png": to_png, "svg": to_svg}[args.format]
        result = converter(svg, args.dpi_x, args.dpi_y)
        if args.output:
            with open(args.output, "wb") as handle:
                handle.write(result)
        else:
            sys.stdout.buffer.write(result)
    except (ConvertError, OSError) as error:
        print(f"weasysvg-convert: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
