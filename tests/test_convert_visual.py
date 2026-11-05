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

import base64
import io
import os
import re
import shutil
import subprocess
from pathlib import Path
from statistics import NormalDist
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
    # Clip paths a soft mask drew before: a <use> as in Tux, children that turn opposite ways, a hole
    "clip-use": svg(
        '<defs><path id="p" d="M20 10 C120 -20 220 40 120 90 L30 80 Z"/><clipPath id="c"><use href="#p"/></clipPath></defs>'
        '<g clip-path="url(#c)"><rect width="200" height="100" fill="#f8cecc"/><circle cx="100" cy="50" r="30" fill="#b85450"/></g>'
    ),
    "clip-union": svg(
        '<defs><clipPath id="c"><rect x="20" y="20" width="100" height="60"/><path d="M60 10 V90 H150 V10 Z"/><circle cx="170" cy="50" r="20"/></clipPath></defs><rect width="200" height="100" fill="teal" clip-path="url(#c)"/>'
    ),
    "clip-hole": svg(
        '<defs><clipPath id="c" clipPathUnits="objectBoundingBox"><path d="M0 0H1V1H0Z M0.3 0.3H0.7V0.7H0.3Z" clip-rule="evenodd"/></clipPath></defs><rect x="20" y="10" width="160" height="80" fill="purple" clip-path="url(#c)"/>'
    ),
    # The glare of Tux: a <use> of a shape filled with a gradient, blurred
    "blur-use-gradient": svg(
        '<defs><radialGradient id="g"><stop stop-color="white"/><stop offset="1" stop-color="gold"/></radialGradient><filter id="f"><feGaussianBlur stdDeviation="3"/></filter>'
        '<path id="p" d="M10 10 C60 0 90 30 70 60 L20 50 Z"/></defs><rect width="200" height="100" fill="#335"/><use href="#p" x="15" y="20" fill="url(#g)" filter="url(#f)"/>'
    ),
    # A mask a clip cannot draw: a gray shape
    "mask-gray": svg('<defs><mask id="m"><rect x="20" y="10" width="160" height="80" rx="12" fill="#999"/></mask></defs><rect width="200" height="100" fill="navy" mask="url(#m)"/>'),
    "binary-mask": svg(
        '<defs><mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="200" height="100"><rect width="200" height="100" fill="white"/>'
        '<rect x="70" y="40" width="60" height="20" fill="black"/><circle cx="40" cy="50" r="10" fill="black"/></mask></defs>'
        '<path d="M10 50 H190 M100 10 V90" stroke="navy" stroke-width="4" mask="url(#m)"/>'
    ),
}


# What a blur looks like in an SVG: an feGaussianBlur, an feDropShadow, a CSS blur() or drop-shadow()
BLURS = re.compile(rb"feGaussianBlur|feDropShadow|blur\(|drop-shadow\(")


def png_url(picture: Image.Image) -> str:
    out = io.BytesIO()
    picture.save(out, format="PNG")
    return "data:image/png;base64," + base64.b64encode(out.getvalue()).decode()


# A gray ramp, black on the left and white on the right, and a red and a translucent picture
RAMP = png_url(Image.linear_gradient("L").rotate(90).resize((64, 64)))
RED_PNG = png_url(Image.new("RGB", (64, 64), (220, 40, 40)))
TRANSLUCENT_PNG = png_url(Image.new("RGBA", (64, 64), (40, 40, 220, 180)))
STRIPES = Image.new("RGB", (64, 32), (220, 40, 40))
STRIPES.paste((40, 160, 40), (0, 16, 64, 32))
STRIPES_PNG = png_url(STRIPES)
REMOVE_COLOR = '<filter id="remove" x="0%" y="0%" width="100%" height="100%"><feColorMatrix color-interpolation-filters="sRGB" values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 1 0"/></filter>'
COLOR_TO_ALPHA = '<filter id="c2a" x="0%" y="0%" width="100%" height="100%"><feColorMatrix color-interpolation-filters="sRGB" values="0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0.2126 0.7152 0.0722 0 0"/></filter>'
PLACED = 'width="160" height="80" x="20" y="10" preserveAspectRatio="none"'
RAMP_MASK = f'<mask id="m"><image {PLACED} href="{RAMP}"/></mask>'
BACKDROP = '<rect width="200" height="100" fill="#cfe"/>'
# What weasysvg draws with an image or under a mask, each against librsvg, which draws it as Chromium does
IMAGES = {
    "masked image": svg(f'{BACKDROP}<defs>{RAMP_MASK}</defs><image {PLACED} mask="url(#m)" href="{RED_PNG}"/>'),
    "masked group of an image": svg(f'{BACKDROP}<defs>{RAMP_MASK}</defs><g mask="url(#m)"><image {PLACED} href="{RED_PNG}"/></g>'),
    "masked use of an image": svg(f'{BACKDROP}<defs>{RAMP_MASK}<image id="r" {PLACED} href="{RED_PNG}"/></defs><g mask="url(#m)"><use href="#r"/></g>'),
    # In PDF the soft mask of an image with alpha replaces the one of the graphics state
    "masked translucent image": svg(f'{BACKDROP}<defs>{RAMP_MASK}</defs><image {PLACED} mask="url(#m)" href="{TRANSLUCENT_PNG}"/>'),
    # The alpha of an image as cairo writes it: the gray of its alpha, through two filters, as the mask of its colors
    "cairo image alpha": svg(
        f'{BACKDROP}<defs>{REMOVE_COLOR}{COLOR_TO_ALPHA}<image id="a" width="64" height="64" href="{RAMP}"/><image id="c" width="64" height="64" href="{RED_PNG}"/>'
        '<mask id="m"><g filter="url(#remove)"><use href="#a" filter="url(#c2a)" transform="matrix(2.5,0,0,1.25,20,10)"/></g></mask></defs>'
        '<g mask="url(#m)"><use href="#c" transform="matrix(2.5,0,0,1.25,20,10)"/></g>'
    ),
    # A soft mask of a group as cairo writes it: the group turned white, its alpha kept, here a masked image
    "cairo group mask": svg(
        f'{BACKDROP}<defs>{REMOVE_COLOR}{COLOR_TO_ALPHA}<image id="a" width="64" height="64" href="{RAMP}"/><image id="k" width="64" height="64" href="{png_url(Image.new("RGB", (64, 64)))}"/>'
        '<mask id="inner"><g filter="url(#remove)"><use href="#a" filter="url(#c2a)" transform="matrix(2.5,0,0,1.25,20,10)"/></g></mask>'
        '<g id="grp"><g mask="url(#inner)"><use href="#k" transform="matrix(2.5,0,0,1.25,20,10)"/></g></g>'
        '<mask id="outer"><g filter="url(#remove)"><use href="#grp"/></g></mask></defs>'
        '<rect x="20" y="10" width="160" height="80" fill="rgb(220,40,40)" mask="url(#outer)"/>'
    ),
    # A color matrix recolors the pixels of an image as the paint of a shape: red and blue swap
    "recolored image": svg(f'<defs><filter id="swap" color-interpolation-filters="sRGB"><feColorMatrix values="0 0 1 0 0 0 1 0 0 0 1 0 0 0 0 0 0 0 1 0"/></filter></defs><g filter="url(#swap)"><image {PLACED} href="{STRIPES_PNG}"/></g>'),
    "recolored translucent image": svg(f'{BACKDROP}<g filter="url(#remove)"><defs>{REMOVE_COLOR}</defs><image {PLACED} href="{TRANSLUCENT_PNG}"/></g>'),
    # A fill or a stroke through a pattern under a soft mask: PDFium and Poppler applied the mask again inside the
    # cell of the pattern, a gradient faded twice and an SVG pattern vanished
    "masked linear gradient": svg(
        f'{BACKDROP}<defs>{RAMP_MASK}<linearGradient id="g"><stop stop-color="crimson"/><stop offset="1" stop-color="navy"/></linearGradient></defs><rect x="20" y="10" width="160" height="80" fill="url(#g)" mask="url(#m)"/>'
    ),
    "masked radial gradient": svg(
        f'{BACKDROP}<defs>{RAMP_MASK}<radialGradient id="g" gradientUnits="userSpaceOnUse" cx="100" cy="50" r="90"><stop stop-color="gold"/><stop offset="1" stop-color="crimson"/></radialGradient></defs>'
        f'<g mask="url(#m)"><circle cx="100" cy="50" r="45" fill="url(#g)"/><rect x="20" y="70" width="160" height="15" fill="none" stroke="url(#g)" stroke-width="6"/></g>'
    ),
    "masked svg pattern": svg(
        f'{BACKDROP}<defs>{RAMP_MASK}<pattern id="p" width="20" height="20" patternUnits="userSpaceOnUse"><rect width="10" height="20" fill="crimson"/><rect x="10" width="10" height="20" fill="navy"/></pattern></defs>'
        f'<rect x="20" y="10" width="160" height="80" fill="url(#p)" mask="url(#m)"/>'
    ),
    # The element blends with what lies under it as one group, after its mask
    "masked blended gradient": svg(
        f'{BACKDROP}<defs>{RAMP_MASK}<linearGradient id="g"><stop stop-color="crimson"/><stop offset="1" stop-color="navy"/></linearGradient></defs>'
        f'<rect x="20" y="10" width="160" height="80" fill="url(#g)" mask="url(#m)" style="mix-blend-mode:multiply"/>'
    ),
    # The box of an image in object bounding box units: its attributes, its own size. librsvg sizes an image of one side
    # as SVG 1.1 did, not by its ratio as Chromium: test_paint covers that one
    "image box": svg(
        f'<defs><clipPath id="h" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/></clipPath></defs><image x="20" y="10" width="160" height="80" preserveAspectRatio="none" clip-path="url(#h)" href="{RED_PNG}"/>'
    ),
    "image box of its size": svg(f'<defs><mask id="h" maskContentUnits="objectBoundingBox"><rect width="0.5" height="1" fill="white"/></mask></defs><image x="20" y="10" mask="url(#h)" href="{STRIPES_PNG}"/>'),
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
    assert text.count("<mask") <= text.count("<image")
    if not BLURS.search(document):
        # An image of its own only for a blur, which Word draws smooth as an image and in rings as levels
        assert text.count("<image") <= document.count(b"<image") + document.count(b"data:image") * 2
    width = round(size_px(document, 96, 96)[0] * SCALE)
    expected = reference(document, width)
    compare(name, expected, drawn(flat, expected.size), flat, tmp_path, "the flat SVG differs from the PDF")


def compare(name: str, expected: Image.Image, actual: Image.Image, source: bytes, tmp_path: Path, what: str) -> None:
    """Fail when actual strays from expected, both blurred by BLUR, past MAX_MEAN on average or MAX_PEAK at most."""
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
        Path(f"{stem}.svg").write_bytes(source)
    if failed:
        pytest.fail(f"{name}: {what} by {mean:.2f} on average and {peak} at most; see {stem}-*.png")


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


def test_flat_svg_of_the_inkscape_logo_looks_like_the_pdf(tmp_path: Path) -> None:
    # Its strokes fade one color through a pattern: Poppler drew levels filled in that color there washed out, over
    # everything after them, so a stroke keeps the shading in each level
    check("real/wm-Inkscape_Logo.svg", (CORPUS / "real" / "wm-Inkscape_Logo.svg").read_bytes(), tmp_path)


@pytest.mark.parametrize("name", ["drop shadow", "gradient", "group of colors", "faded colors side by side"])
def test_weasysvg_draws_its_own_flat_svg_of_a_blur(name: str) -> None:
    # pandoc draws the SVG of a DOCX with weasysvg-convert: the flat SVG of a blur holds an image under a mask cairo
    # writes through filters, which weasysvg drew opaque
    document = PORTABLE_BLURS[name].encode()
    width = round(size_px(document, 96, 96)[0] * SCALE)
    expected = reference(document, width)
    actual = reference(to_svg(document), width)
    difference = ImageChops.difference(expected.filter(ImageFilter.GaussianBlur(BLUR)), actual.filter(ImageFilter.GaussianBlur(BLUR))).convert("L")
    assert ImageStat.Stat(difference).mean[0] <= MAX_MEAN
    assert cast("tuple[int, int]", difference.getextrema())[1] <= MAX_PEAK


@pytest.mark.parametrize("name", IMAGES)
def test_weasysvg_draws_as_librsvg(name: str, tmp_path: Path) -> None:
    document = IMAGES[name].encode()
    expected = drawn(document, (round(size_px(document, 96, 96)[0] * SCALE), round(size_px(document, 96, 96)[1] * SCALE)))
    compare(name, expected, reference(document, expected.size[0]), document, tmp_path, "weasysvg differs from librsvg")


@pytest.mark.parametrize("name", ["real/wm-Tux.svg", "real/wm-Openstreetmap_logo.svg"])
def test_weasysvg_draws_a_flat_svg_as_librsvg(name: str, tmp_path: Path) -> None:
    # pandoc draws the SVG of a DOCX with weasysvg-convert: its blurs are images under masks cairo writes through filters
    flat = to_svg((CORPUS / name).read_bytes())
    width, height = (round(side * SCALE) for side in size_px(flat, 96, 96))
    compare(name, drawn(flat, (width, height)), reference(flat, width), flat, tmp_path, "weasysvg differs from librsvg")


def test_flat_svg_of_a_blur_follows_the_gaussian() -> None:
    # The image of the exact blur of a rect, interpolated between the centers of its cells: Phi at the center of each pixel
    flat = to_svg(svg('<filter id="f"><feGaussianBlur stdDeviation="5"/></filter><rect x="40" y="40" width="120" height="120" fill="black" filter="url(#f)"/>', 200, 200).encode())
    image = drawn(flat, (800, 800)).convert("L")
    for y in range(30, 50, 2):
        # 4 pixels per px: the center of px y is pixel 4 y + 2
        assert 1 - cast(int, image.getpixel((400, 4 * y + 2))) / 255 == pytest.approx(NormalDist().cdf((y + 0.5 - 40) / 5), abs=0.02)


def test_a_lost_label_fails_the_comparison(tmp_path: Path) -> None:
    # The check sees a label the flattening would lose: a box without its text is a blot after the blur
    labeled = svg('<rect x="20" y="20" width="160" height="60" fill="none" stroke="black"/><text x="40" y="60" font-size="24">Label</text>').encode()
    flat = to_svg(labeled.replace(b">Label<", b"><"))
    width = round(size_px(labeled, 96, 96)[0] * SCALE)
    expected = reference(labeled, width)
    difference = ImageChops.difference(expected.filter(ImageFilter.GaussianBlur(BLUR)), drawn(flat, expected.size).filter(ImageFilter.GaussianBlur(BLUR))).convert("L")
    assert cast("tuple[int, int]", difference.getextrema())[1] > MAX_PEAK
