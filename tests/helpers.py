"""Shared helpers: install weasysvg once, render an SVG through WeasyPrint, read the PDF back."""

from __future__ import annotations

import base64
import re
from typing import Any

import pypdfium2 as pdfium
import weasyprint

import weasysvg

FEATURES = weasysvg.install()

SVG_NS = "http://www.w3.org/2000/svg"
XHTML_NS = "http://www.w3.org/1999/xhtml"
PATH_OPERATORS = frozenset(("m", "l", "c", "v", "y", "re", "h"))
PAINT_OPERATORS = frozenset(("f", "f*", "F", "S", "s", "B", "B*", "b", "b*", "n"))


def svg(body: str, width: int = 200, height: int = 100, extra: str = "") -> str:
    """A standalone SVG document around body."""
    return f'<svg xmlns="{SVG_NS}" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}"{extra}>{body}</svg>'


def page_html(document: str, width: float | None = None) -> str:
    """The page of the visual bench: one <img> with a data URL."""
    data = base64.b64encode(document.encode()).decode()
    style = f' style="width:{width}px"' if width else ""
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><style>@page{{size:600px 600px;margin:0}} body{{margin:0}} img{{display:block}}</style></head><body><img{style} src=\"data:image/svg+xml;base64,{data}\"></body></html>"


def render(document: str, width: float | None = None, **options: Any) -> bytes:
    """The PDF of the SVG, streams uncompressed so the operators can be read. Fails on a state change inside a path."""
    pdf: bytes = weasyprint.HTML(string=page_html(document, width)).write_pdf(uncompressed_pdf=True, **options)
    for stream in streams(pdf):
        assert_no_state_inside_path(stream)
    return pdf


def text_of(pdf: bytes) -> str:
    """The text PDFium extracts from the first page."""
    document = pdfium.PdfDocument(pdf)
    try:
        text: str = document[0].get_textpage().get_text_range()
        return text
    finally:
        document.close()


def streams(pdf: bytes) -> list[str]:
    """Every stream of the PDF as text: the page, its groups, patterns and soft masks."""
    return [match.decode("latin-1") for match in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", pdf, re.S)]


def content(pdf: bytes) -> str:
    """All streams in one text, for operator searches."""
    return "\n".join(streams(pdf))


def assert_no_state_inside_path(stream: str) -> None:
    """A gs operator between path construction and its paint is invalid PDF: viewers ignore it."""
    in_path = False
    for line in stream.splitlines():
        operator = line.rsplit(" ", 1)[-1] if " " in line else line
        if operator in PATH_OPERATORS:
            in_path = True
        elif operator in PAINT_OPERATORS:
            in_path = False
        elif operator == "gs":
            assert not in_path, f"graphics state set inside path construction: {line}"


def ink(pdf: bytes, scale: float = 1.0) -> tuple[int, int, int] | None:
    """The darkest pixel of the first page, rasterized by PDFium, or None for a blank page."""
    document = pdfium.PdfDocument(pdf)
    try:
        image = document[0].render(scale=scale, fill_color=(255, 255, 255, 255)).to_pil().convert("RGB")
    finally:
        document.close()
    box = image.point(lambda value: 255 if value < 250 else 0).getbbox()
    if box is None:
        return None
    pixels = list(image.crop(box).getdata())
    darkest: tuple[int, int, int] = min(pixels, key=sum)
    return darkest


def pixel(pdf: bytes, x: int, y: int) -> tuple[int, int, int]:
    """One pixel of the first page at 72 dpi, in CSS px times 0.75."""
    document = pdfium.PdfDocument(pdf)
    try:
        image = document[0].render(scale=1, fill_color=(255, 255, 255, 255)).to_pil().convert("RGB")
    finally:
        document.close()
    value: tuple[int, int, int] = image.getpixel((x, y))
    return value
