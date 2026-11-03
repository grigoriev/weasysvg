"""The flat SVG of weasysvg-convert, drawn by another renderer, against the PDF weasysvg draws itself.

The flat SVG goes to Word, which draws no soft mask and no filter. Each diagram of the corpus and a few
cases of each feature the portable PDF changes are flattened, drawn by librsvg (rsvg-convert), and
compared with the default PDF in PDFium, soft masks and all. Both are blurred by 2 px first: PDFium snaps
thin strokes to whole pixels and librsvg does not, which moves a line by a pixel. A shape, a label or a
shadow the flattening loses stays a blot after the blur. resvg drew no stroke painted by a pattern and
faded a gradient inside one, where librsvg, Chromium and Word draw them as PDFium does.

A failing case writes the reference, the flat drawing and their difference next to the test run. With
WEASYSVG_VISUAL_OUT set to a directory, every case writes them there, to look at by eye.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import cast

import pypdfium2 as pdfium
import pytest
from helpers import close, svg
from PIL import Image, ImageChops, ImageFilter, ImageStat
from test_filters import PORTABLE_BLURS
from test_paint import KNOCKOUT

from weasysvg.convert import size_px, to_pdf, to_svg

RSVG = shutil.which("rsvg-convert")
pytestmark = pytest.mark.skipif(RSVG is None, reason="needs rsvg-convert of librsvg (Dockerfile.test and CI install it)")

CORPUS = Path(__file__).resolve().parent.parent / "corpus" / "svg"
# Pixels per CSS px of both drawings
SCALE = 2
BLUR = 2
# The worst case is 1.2 on average and 42 at most: PDFium and librsvg smooth curves and text a little differently
MAX_MEAN = 2.0
MAX_PEAK = 64

SHADOW = ' x="-50%" y="-50%" width="200%" height="200%"'
FEATURES = {
    # The shadow draw.io writes for a shape with "shadow=1"
    "drawio-shadow": svg(
        '<defs><filter id="dropShadow"><feGaussianBlur in="SourceAlpha" stdDeviation="1.7" result="blur"/><feOffset in="blur" dx="3" dy="3" result="offsetBlur"/>'
        '<feFlood flood-color="#3D4574" flood-opacity="0.4" result="offsetColor"/><feComposite in="offsetColor" in2="offsetBlur" operator="in" result="offsetBlur"/>'
        '<feBlend in="SourceGraphic" in2="offsetBlur"/></filter></defs>'
        '<g filter="url(#dropShadow)"><rect x="20" y="20" width="100" height="60" rx="9" fill="#dae8fc" stroke="#6c8ebf"/></g>'
        '<g filter="url(#dropShadow)"><ellipse cx="160" cy="50" rx="25" ry="20" fill="#d5e8d4" stroke="#82b366"/></g>',
        height=110,
    ),
    "css-drop-shadow": svg('<rect x="20" y="20" width="80" height="50" fill="#ECECFF" stroke="#9370DB" style="filter:drop-shadow(2px 2px 2px rgba(0,0,0,0.4))"/>', height=100),
    "blur": svg(f'<defs><filter id="f"{SHADOW}><feGaussianBlur stdDeviation="4"/></filter></defs><path d="M30 20 L120 40 L60 90 Z" fill="crimson" filter="url(#f)"/>', height=110),
    "group-opacity": svg('<g opacity="0.5"><rect x="20" y="20" width="60" height="60" fill="red"/><rect x="50" y="40" width="60" height="60" fill="blue"/></g>', height=110),
    # The masks the portable PDF draws as clips: holes, a union of white areas, content in bounding box units
    "mask-knockout": svg(KNOCKOUT),
    "mask-hole-circle": svg(
        '<defs><mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="200" height="100"><rect width="200" height="100" fill="white"/><circle cx="100" cy="50" r="30" fill="black"/>'
        '<ellipse cx="160" cy="50" rx="20" ry="12" fill="black"/></mask></defs><rect width="200" height="100" fill="teal" mask="url(#m)"/>'
    ),
    "mask-union": svg(
        '<defs><mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="200" height="100"><rect width="60" height="100" fill="white"/><circle cx="150" cy="50" r="40" fill="#fff"/></mask></defs>'
        '<rect width="200" height="100" fill="orange" mask="url(#m)"/>'
    ),
    "mask-bounding-box": svg(
        '<defs><mask id="m" maskContentUnits="objectBoundingBox"><rect width="1" height="1" fill="white"/><rect x="0.4" width="0.2" height="1" fill="black"/></mask></defs>'
        '<g mask="url(#m)"><rect x="20" y="10" width="160" height="80" fill="purple"/></g>'
    ),
    # Gradients with transparent stops and faded fills, linear and radial: draw.io writes them with fillOpacity
    "gradient-linear": svg(
        '<defs><linearGradient id="g" x2="0" y2="1"><stop stop-color="#dae8fc"/><stop offset="1" stop-color="#7ea6e0" stop-opacity="0.3"/></linearGradient></defs>'
        '<rect x="20" y="10" width="160" height="80" rx="8" fill="url(#g)" stroke="#6c8ebf"/>'
    ),
    "gradient-faded": svg(
        '<defs><linearGradient id="g"><stop stop-color="#f8cecc"/><stop offset="1" stop-color="#ea6b66"/></linearGradient></defs><ellipse cx="100" cy="50" rx="80" ry="40" fill="url(#g)" fill-opacity="0.6" stroke="#b85450"/>'
    ),
    "gradient-radial": svg(
        '<defs><radialGradient id="g" fx="0.35" fy="0.35"><stop stop-color="white" stop-opacity="0.9"/><stop offset="0.6" stop-color="gold"/><stop offset="1" stop-color="orange" stop-opacity="0"/></radialGradient></defs>'
        '<rect width="200" height="100" fill="#eef"/><circle cx="100" cy="50" r="45" fill="url(#g)"/>'
    ),
    "gradient-stroke": svg(
        '<defs><linearGradient id="g" gradientTransform="rotate(20)"><stop stop-color="green" stop-opacity="0.2"/><stop offset="1" stop-color="green"/></linearGradient></defs>'
        '<path d="M20 80 C60 0 140 100 180 20" fill="none" stroke="url(#g)" stroke-width="10"/>'
    ),
    "binary-mask": svg(
        '<defs><mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="200" height="100"><rect width="200" height="100" fill="white"/>'
        '<rect x="70" y="40" width="60" height="20" fill="black"/><circle cx="40" cy="50" r="10" fill="black"/></mask></defs>'
        '<path d="M10 50 H190 M100 10 V90" stroke="navy" stroke-width="4" mask="url(#m)"/>'
    ),
}


def corpus_cases() -> list[str]:
    return sorted(str(path.relative_to(CORPUS)) for folder in ("drawio", "diagrams") for path in (CORPUS / folder).glob("*.svg"))


def reference(document: bytes, width: int) -> Image.Image:
    """The default PDF of weasysvg, soft masks and all, in PDFium at width pixels."""
    pdf = pdfium.PdfDocument(to_pdf(document))
    page = pdf[0]
    bitmap = page.render(scale=width / page.get_width(), fill_color=(255, 255, 255, 255))
    try:
        image: Image.Image = bitmap.to_pil().convert("RGB")
        return image
    finally:
        close(bitmap, page, pdf)


def drawn(flat: bytes, size: tuple[int, int]) -> Image.Image:
    """The flat SVG in librsvg at size, on white."""
    width, height = size
    png = subprocess.run([cast(str, RSVG), "-w", str(width), "-h", str(height), "-b", "white"], input=flat, capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGB").resize(size)


def check(name: str, document: bytes, tmp_path: Path) -> None:
    flat = to_svg(document)
    text = flat.decode()
    # cairo keeps the alpha of a raster image in a mask through a filter: any other filter is one Word does not draw
    assert 'filter="url(' not in re.sub(r"<mask\b.*?</mask>", "", text, flags=re.DOTALL), "a filter: Word draws none"
    # cairo writes the alpha of a raster image as a mask over that image: any other mask is a soft mask
    assert text.count("<mask") <= text.count("<image") <= document.count(b"<image") + document.count(b"data:image") * 2
    width = round(size_px(document, 96, 96)[0] * SCALE)
    expected = reference(document, width)
    actual = drawn(flat, expected.size)
    difference = ImageChops.difference(expected.filter(ImageFilter.GaussianBlur(BLUR)), actual.filter(ImageFilter.GaussianBlur(BLUR))).convert("L")
    mean, peak = ImageStat.Stat(difference).mean[0], cast("tuple[int, int]", difference.getextrema())[1]
    failed = mean > MAX_MEAN or peak > MAX_PEAK
    out = os.environ.get("WEASYSVG_VISUAL_OUT")
    if failed or out:
        folder = tmp_path if failed or not out else Path(out)
        folder.mkdir(parents=True, exist_ok=True)
        stem = folder / name.replace("/", "-")
        expected.save(f"{stem}-reference.png")
        actual.save(f"{stem}-flat.png")
        difference.point(lambda value: min(255, value * 4)).save(f"{stem}-difference.png")
        Path(f"{stem}.svg").write_bytes(flat)
    if failed:
        pytest.fail(f"{name}: the flat SVG differs from the PDF by {mean:.2f} on average and {peak} at most; see {stem}-*.png")


@pytest.mark.parametrize("name", corpus_cases())
def test_flat_svg_of_a_diagram_looks_like_the_pdf(name: str, tmp_path: Path) -> None:
    check(name, (CORPUS / name).read_bytes(), tmp_path)


@pytest.mark.parametrize("name", FEATURES)
def test_flat_svg_of_a_feature_looks_like_the_pdf(name: str, tmp_path: Path) -> None:
    check(name, FEATURES[name].encode(), tmp_path)


@pytest.mark.parametrize("name", PORTABLE_BLURS)
def test_flat_svg_of_a_blur_looks_like_the_pdf(name: str, tmp_path: Path) -> None:
    # Every blur the unit tests draw in a portable PDF, through the flat SVG to another renderer
    check(f"blur-{name}", PORTABLE_BLURS[name].encode(), tmp_path)


def test_a_lost_label_fails_the_comparison(tmp_path: Path) -> None:
    # The check sees a label the flattening would lose: a box without its text is a blot after the blur
    labeled = svg('<rect x="20" y="20" width="160" height="60" fill="none" stroke="black"/><text x="40" y="60" font-size="24">Label</text>').encode()
    flat = to_svg(labeled.replace(b">Label<", b"><"))
    width = round(size_px(labeled, 96, 96)[0] * SCALE)
    expected = reference(labeled, width)
    difference = ImageChops.difference(expected.filter(ImageFilter.GaussianBlur(BLUR)), drawn(flat, expected.size).filter(ImageFilter.GaussianBlur(BLUR))).convert("L")
    assert cast("tuple[int, int]", difference.getextrema())[1] > MAX_PEAK
