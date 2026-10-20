"""WeasyPrint alone: render an SVG, read pixels, text and operators back, and report a fixed gap."""

from __future__ import annotations

import base64
import logging
import re
from typing import Any, cast

import pypdfium2 as pdfium
import weasyprint
from PIL import Image

SVG_NS = "http://www.w3.org/2000/svg"
RED = (255, 0, 0)
WHITE = (255, 255, 255)


def svg(body: str, width: int = 200, height: int = 100) -> str:
    return f'<svg xmlns="{SVG_NS}" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}">{body}</svg>'


class _Errors(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.ERROR)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def render(document: str, url_fetcher: Any = None) -> tuple[bytes, list[str]]:
    """The PDF, streams uncompressed, and the errors WeasyPrint logged while rendering."""
    data = base64.b64encode(document.encode()).decode()
    html = f"<style>@page{{size:600px 600px;margin:0}}body{{margin:0}}img{{display:block}}</style><img src='data:image/svg+xml;base64,{data}'>"
    errors = _Errors()
    logger = logging.getLogger("weasyprint")
    logger.addHandler(errors)
    try:
        options = {"url_fetcher": url_fetcher} if url_fetcher else {}
        pdf: bytes = weasyprint.HTML(string=html, **options).write_pdf(uncompressed_pdf=True)
    finally:
        logger.removeHandler(errors)
    return pdf, errors.messages


def lost(errors: list[str]) -> bool:
    """WeasyPrint gave up on the whole SVG."""
    return any("Failed to render SVG image" in message for message in errors)


def pixel(pdf: bytes, x: int, y: int) -> tuple[int, int, int]:
    """One pixel at 72 dpi: CSS px times 0.75."""
    document = pdfium.PdfDocument(pdf)
    page = document[0]
    bitmap = page.render(scale=1, fill_color=(255, 255, 255, 255))
    try:
        image: Image.Image = bitmap.to_pil().convert("RGB")
        return cast("tuple[int, int, int]", image.getpixel((x, y)))
    finally:
        for item in (bitmap, page, document):
            item.close()


def near(actual: tuple[int, int, int], expected: tuple[int, int, int], tolerance: int = 40) -> bool:
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected, strict=True))


def content(pdf: bytes) -> str:
    return "\n".join(match.decode("latin-1") for match in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", pdf, re.S))


def text_matrices(pdf: bytes) -> list[tuple[float, ...]]:
    return [tuple(float(value) for value in match) for match in re.findall(r"([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) Tm", content(pdf))]


def still_broken(broken: bool, what: str, patch: str) -> None:
    """Fail when WeasyPrint has fixed the gap: the patch that covers it has to go."""
    assert broken, f"WeasyPrint {weasyprint.__version__} fixed {what}: remove {patch} and its tests"
