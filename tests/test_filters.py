"""Filter chains: vector layers, the vector blur, recoloring, and CSS filter functions."""

from __future__ import annotations

import logging
import math
import re
from statistics import NormalDist
from types import SimpleNamespace
from typing import Any, cast

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
import pytest
import weasyprint
from helpers import RecordingStream, content, page_html, pixel, rasterize, render, svg
from PIL import ImageStat

from weasysvg import filters, shapeblur, turbulence
from weasysvg.filters import HIDDEN, Layer, Restyle, Unsupported

RED = (255, 0, 0)
WHITE = (255, 255, 255)


def near(actual: tuple[int, int, int], expected: tuple[int, int, int], tolerance: int = 40) -> bool:
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected, strict=True))


def faint(actual: tuple[int, int, int]) -> bool:
    """Some ink, but far from the full color: the blurred edge outside a shape."""
    return 0 < 255 * 3 - sum(actual) < 255 * 2


def filtered(primitives: str, attributes: str = "", target: str = '<rect x="20" y="20" width="60" height="40" fill="red" filter="url(#f)"/>') -> str:
    return svg(f'<defs><filter id="f"{attributes}>{primitives}</filter></defs>{target}', height=120)


def images(pdf: bytes) -> int:
    """The color images of the PDF, without their alpha soft masks."""
    return len(re.findall(r"<<[^\n]*/Subtype /Image[^\n]*/DeviceRGB", pdf.decode("latin-1")))


# ---------------- helpers ----------------


def test_std_and_num() -> None:
    assert filters._std("2", "0") == (2.0, 2.0)
    assert filters._std("1,3", "0") == (1.0, 3.0)
    assert filters._std(None, "2") == (2.0, 2.0)
    assert filters._std("-1", "0") == (0.0, 0.0)
    assert filters._std("1 2 3", "0") == (0.0, 0.0)
    assert filters._std("", "") == (0.0, 0.0)
    assert filters._num("10%") == 0.0
    assert filters._num(None, 2) == 2
    assert filters._add_blur((3.0, 0.0), (4.0, 0.0)) == (5.0, 0.0)


@pytest.mark.parametrize(
    ("value", "kinds", "blur"),
    [
        ("blur(4px)", ["source"], (4.0, 4.0)),
        ("blur()", ["source"], (0.0, 0.0)),
        ("drop-shadow(2px 3px 4px red)", ["alpha", "source"], (2.0, 2.0)),
        ("drop-shadow(rgba(0, 0, 0, 0.5) 2px 3px)", ["alpha", "source"], (0.0, 0.0)),
    ],
)
def test_function_layers(value: str, kinds: list[str], blur: tuple[float, float]) -> None:
    layers = filters._function_layers(value)
    assert [layer.kind for layer in layers] == kinds
    assert layers[0].blur == blur


@pytest.mark.parametrize("value", ["blur(1px 2px)", "drop-shadow(2px, 3px)", "drop-shadow(red)", "sepia(1)"])
def test_function_layers_reject(value: str) -> None:
    with pytest.raises(Unsupported):
        filters._function_layers(value)


# ---------------- vector chains ----------------


def test_offset_flood_merge_shadow_is_vector() -> None:
    pdf = render(
        filtered(
            '<feFlood flood-color="blue" flood-opacity="0.5" result="f"/><feComposite in="f" in2="SourceAlpha" operator="in" result="shadow"/>'
            '<feOffset in="shadow" dx="10" dy="10" result="moved"/><feMerge><feMergeNode in="moved"/><feMergeNode in="SourceGraphic"/><desc/></feMerge>',
        )
    )
    assert images(pdf) == 0
    assert "/SMask" in pdf.decode("latin-1")
    # The shadow shows below and right of the red rectangle
    assert near(pixel(pdf, 60, 45), (128, 128, 255), 60)
    assert near(pixel(pdf, 30, 30), RED)


def test_drop_shadow_primitive_and_blend() -> None:
    pdf = render(filtered('<feDropShadow dx="5" dy="5" stdDeviation="0" flood-color="black"/><feBlend in2="SourceGraphic"/>'))
    assert images(pdf) == 0
    assert near(pixel(pdf, 63, 47), (0, 0, 0), 60)


def test_flood_subregion_and_composite_over() -> None:
    pdf = render(filtered('<feFlood x="0" y="0" width="10" height="10" flood-color="lime" result="f"/><feComposite in="SourceGraphic" in2="f" operator="over"/>', ' filterUnits="userSpaceOnUse" x="0" y="0" width="200" height="120"'))
    assert near(pixel(pdf, 3, 3), (0, 255, 0))
    assert near(pixel(pdf, 30, 30), RED)


def test_component_transfer_fades() -> None:
    pdf = render(filtered('<feComponentTransfer><feFuncA type="linear" slope="0.5" intercept="0"/></feComponentTransfer>'))
    assert "/x" in content(pdf)
    assert near(pixel(pdf, 30, 30), (255, 128, 128), 40)


def test_empty_component_transfer_and_saturate() -> None:
    pdf = render(filtered('<feComponentTransfer/><feColorMatrix type="saturate" values="1"/>'))
    assert near(pixel(pdf, 30, 30), RED)


def test_filter_with_opacity_and_mask() -> None:
    target = '<defs><mask id="m"><rect width="200" height="120" fill="white"/></mask></defs><rect x="20" y="20" width="60" height="40" fill="red" opacity="0.5" mask="url(#m)" filter="url(#f)"/>'
    pdf = render(filtered('<feOffset dx="0" dy="0"/>', target=target))
    assert near(pixel(pdf, 30, 30), (255, 128, 128), 40)


def test_drop_shadow_of_a_flood() -> None:
    pdf = render(
        filtered(
            '<feFlood flood-color="red" x="20" y="20" width="60" height="40" result="f"/><feDropShadow in="f" dx="5" dy="5" stdDeviation="0" flood-color="black"/>',
            ' filterUnits="userSpaceOnUse" x="0" y="0" width="200" height="120"',
        )
    )
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 63, 47), (0, 0, 0), 60)


def test_primitive_units_in_the_bounding_box() -> None:
    # dx="0.5" is half the 60 units of the box: the rectangle moves to 50..110
    pdf = render(filtered('<feOffset dx="0.5"/>', ' primitiveUnits="objectBoundingBox" x="-1" width="3"'))
    assert near(pixel(pdf, 22, 30), WHITE)
    assert near(pixel(pdf, 75, 30), RED)
    pdf = render(filtered('<feFlood x="0" width="0.5" flood-color="lime"/>', ' primitiveUnits="objectBoundingBox"'))
    assert near(pixel(pdf, 20, 30), (0, 255, 0))
    assert near(pixel(pdf, 55, 30), WHITE)


def test_primitive_units_without_a_box_draw_unfiltered(caplog: pytest.LogCaptureFixture) -> None:
    target = '<g filter="url(#f)"/><rect x="20" y="20" width="60" height="40" fill="red"/>'
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        pdf = render(filtered('<feOffset dx="0.5"/>', ' primitiveUnits="objectBoundingBox" filterUnits="userSpaceOnUse"', target=target))
    assert near(pixel(pdf, 30, 30), RED)
    assert "without a bounding box" in caplog.text


def test_bad_references() -> None:
    pdf = render(svg('<rect x="20" y="20" width="60" height="40" fill="red" filter="url(#missing)"/><g filter="url(#f)"/><defs><filter id="f"/></defs>'))
    assert near(pixel(pdf, 30, 30), RED)


# ---------------- unsupported ----------------


@pytest.mark.parametrize(
    "primitives",
    [
        '<feMorphology radius="2"/>',
        '<feBlend mode="multiply" in2="SourceGraphic"/>',
        '<feComposite operator="xor" in2="SourceGraphic"/>',
        '<feColorMatrix type="unknown"/>',
        '<feOffset in="nowhere"/>',
    ],
)
def test_unsupported_chain_draws_the_element(primitives: str, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        pdf = render(filtered(primitives))
    assert images(pdf) == 0
    assert near(pixel(pdf, 30, 30), RED, 60)
    assert "drawn unfiltered" in caplog.text


def test_css_functions() -> None:
    body = '<rect x="20" y="20" width="60" height="40" fill="red" style="filter:drop-shadow(5px 5px 0 black)"/><rect x="120" y="20" width="40" height="40" fill="red" style="filter:sepia(1)"/>'
    pdf = render(svg(body, height=120))
    assert near(pixel(pdf, 63, 47), (0, 0, 0), 60)
    assert near(pixel(pdf, 100, 30), RED)


def test_inner_svg_filter_is_left_to_weasyprint() -> None:
    body = '<defs><filter id="f"><feGaussianBlur stdDeviation="2"/></filter></defs><svg x="10" y="10" width="80" height="80" filter="url(#f)"><rect width="40" height="40" fill="red"/></svg>'
    node = type("Node", (), {"get": {"filter": "url(#f)"}.get, "tag": "svg"})()
    fake = type("SVG", (), {"tree": object()})()
    assert filters.plan(fake, node, 16) is None
    render(svg(body))


# ---------------- vector blur ----------------


def test_blur_spreads_the_shape_in_vector() -> None:
    pdf = render(filtered('<feGaussianBlur stdDeviation="4"/>'))
    assert images(pdf) == 0
    # Inside: the full color. 3 units outside the left edge: about a quarter of it
    assert near(pixel(pdf, 37, 30), RED, 30)
    assert faint(pixel(pdf, 13, 30))
    assert near(pixel(pdf, 3, 30), WHITE, 10)


def test_blurred_shadow_keeps_the_source_vector() -> None:
    pdf = render(filtered('<feDropShadow dx="4" dy="4" stdDeviation="3"/>', ' color-interpolation-filters="sRGB" x="-50%" y="-50%" width="200%" height="200%"'))
    assert images(pdf) == 0
    assert "1 0 0 rg" in content(pdf)
    # The shadow shows beyond the bottom edge, past the shifted rectangle
    assert faint(pixel(pdf, 40, 50))


def test_css_blur_and_drop_shadow() -> None:
    body = '<rect x="20" y="20" width="60" height="40" fill="red" style="filter:blur(2px)"/><rect x="120" y="20" width="40" height="40" fill="red" style="filter:drop-shadow(3px 3px 4px black)"/><g style="filter:blur(2px)"/>'
    pdf = render(svg(body, height=120))
    assert images(pdf) == 0
    assert faint(pixel(pdf, 14, 30))
    assert faint(pixel(pdf, 122, 48))


def test_blur_of_a_gradient_and_a_faded_fill() -> None:
    # A gradient with stop-opacity sets a soft mask of its own: it must not replace the blur mask
    body = (
        '<defs><linearGradient id="g"><stop stop-color="red"/><stop offset="1" stop-color="red" stop-opacity="0.8"/></linearGradient>'
        '<filter id="b"><feGaussianBlur stdDeviation="4"/></filter></defs>'
        '<rect x="20" y="20" width="60" height="40" fill="url(#g)" filter="url(#b)"/>'
        '<rect x="120" y="20" width="60" height="40" fill="red" fill-opacity="0.5" filter="url(#b)"/>'
    )
    pdf = render(svg(body, height=120))
    assert faint(pixel(pdf, 13, 30))
    # The faded fill keeps its own opacity inside, it is not faded twice
    assert near(pixel(pdf, 112, 30), (255, 128, 128), 30)


@pytest.mark.parametrize("line", ['<path d="M20 40 H180" fill="none"', '<line x1="20" y1="40" x2="180" y2="40"'])
def test_blurred_thin_line_is_faint(line: str) -> None:
    # A line 2 units wide blurred by 4 peaks at about a fifth of its color
    # A box of zero height leaves the region of the filter empty: the region is given in user space
    region = ' filterUnits="userSpaceOnUse" x="0" y="0" width="200" height="120"'
    pdf = render(filtered('<feGaussianBlur stdDeviation="4"/>', region, target=f'{line} stroke="black" stroke-width="2" filter="url(#f)"/>'))
    center = pixel(pdf, 75, 30)
    assert 180 < center[0] < 230


def test_blur_on_the_root_is_vector() -> None:
    document = filtered('<feGaussianBlur stdDeviation="2"/>', target='<rect x="20" y="20" width="60" height="40" fill="red"/>')
    pdf = render(document.replace("<svg ", '<svg filter="url(#f)" viewBox="0 0 200 120" ', 1))
    assert images(pdf) == 0
    assert near(pixel(pdf, 37, 30), RED, 30)
    assert faint(pixel(pdf, 14, 30))
    pdf = render(document.replace("<svg ", '<svg style="filter:blur(2px)" ', 1))
    assert faint(pixel(pdf, 14, 30))


@pytest.mark.parametrize(
    ("units", "shape"),
    [
        ("", '<rect x="20" y="20" width="60" height="40"/>'),
        (' clipPathUnits="objectBoundingBox"', '<rect width="1" height="1"/>'),
        # A clip through <use> becomes a soft mask: the blur mask must not replace it
        ("", '<use href="#base"/>'),
    ],
)
def test_clip_path_cuts_the_filter_result(units: str, shape: str) -> None:
    # CSS clips after it filters: the blur stops at the clip, as the handle of the OpenStreetMap logo
    base = '<rect id="base" x="20" y="20" width="60" height="40" fill="none"/>'
    target = f'{base}<clipPath id="c"{units}>{shape}</clipPath><rect x="20" y="20" width="60" height="40" fill="red" clip-path="url(#c)" filter="url(#f)"/>'
    pdf = render(filtered('<feGaussianBlur stdDeviation="4"/>', target=target))
    assert near(pixel(pdf, 13, 30), WHITE, 3)
    # Inside, near the edge, the blur still fades the color
    assert not near(pixel(pdf, 16, 30), RED, 30)


def test_blur_of_a_group_with_text() -> None:
    target = '<g filter="url(#f)"><text x="20" y="60" font-size="40" fill="red">Hi</text><circle cx="150" cy="50" r="20" fill="red" stroke="blue"/></g>'
    pdf = render(filtered('<feGaussianBlur stdDeviation="2"/>', target=target))
    assert images(pdf) == 0
    assert near(pixel(pdf, 112, 37), RED, 60)


def test_levels_and_bands() -> None:
    levels = filters.levels(2.0, 4)
    assert [round(level.threshold, 4) for level in levels] == [0.0625, 0.1875, 0.3125, 0.4375, 0.5625, 0.6875, 0.8125, 0.9375]
    radii = [level.radius for level in levels[:4]]
    assert radii == sorted(radii, reverse=True)
    assert all(level.radius == 0 for level in levels[4:])
    bands = filters.bands(2.0, 4)
    assert [round(gray, 3) for _, gray in bands] == [0.125, 0.25, 0.375, 0.5]
    widths = [band.radius for band, _ in bands]
    assert widths == sorted(widths, reverse=True)


def test_line_reach() -> None:
    assert filters.line_reach(2, 4, 0.5) is None
    reach = filters.line_reach(20, 2, 0.5)
    assert reach is not None
    assert abs(reach - 10) < 0.01


@pytest.mark.parametrize(
    ("mode", "fill", "width", "expected"),
    [
        (Restyle("fills", 2), "none", 2, HIDDEN),
        (Restyle("band", 2, radius=1), "none", 2, HIDDEN),
        (Restyle("level", 2, threshold=0.6), "red", 0, HIDDEN),
        (Restyle("level", 2, threshold=0.99), "none", 2, HIDDEN),
        (Restyle("fills", 2), "red", 0, {}),
        (Restyle("grow", 2, radius=3), "red", 0, {"stroke-linejoin": "round", "stroke-linecap": "round", "stroke-width": "6", "stroke": "red", "stroke-opacity": "1", "stroke-dasharray": "none"}),
        (Restyle("band", 2, radius=3), "red", 2, {"stroke-linejoin": "round", "stroke-linecap": "round", "stroke-width": "8", "fill": "none"}),
    ],
)
def test_restyled(mode: Restyle, fill: str, width: float, expected: dict[str, str]) -> None:
    assert filters._restyled(mode, fill, width, "1") == expected


def test_coverage_paints_black() -> None:
    assert filters._coverage({"stroke": "url(#g)"}, "url(#g)", False) == {"stroke": "black", "fill": "black", "fill-opacity": "1", "stroke-opacity": "1", "opacity": "1"}
    assert filters._coverage({"fill": "none"}, "red", True) == {"fill": "none", "stroke": "black", "fill-opacity": "1", "stroke-opacity": "1", "opacity": "1"}


class Shape:
    """A leaf node without paint."""

    tag = "rect"

    def __init__(self) -> None:
        self.attrib = {"fill": "none", "stroke": "none"}
        self.get = self.attrib.get

    def __iter__(self) -> Any:
        return iter(())


def test_restyle_needs_a_mode_and_a_painted_shape() -> None:
    assert filters.restyle(object(), Shape(), 12) is None
    token = filters.RESTYLE.set(Restyle("fills", 2))
    try:
        assert filters.restyle(object(), SimpleNamespace(tag="g"), 12) is None
        assert filters.restyle(object(), Shape(), 12) is None
    finally:
        filters.RESTYLE.reset(token)


WIDE_BLUR = '<filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2"/></filter>'


def test_a_filtered_element_in_defs_is_drawn_through_use() -> None:
    document = svg(f'<defs>{WIDE_BLUR}<rect id="r" width="60" height="40" fill="red" filter="url(#b)"/></defs><use href="#r" x="20" y="20"/>', height=100)
    assert near(pixel(render(document), 37, 30), RED, 30)


def test_each_use_keeps_the_paint_it_passes_down() -> None:
    defs = f'<defs>{WIDE_BLUR}<rect id="r" width="60" height="40" filter="url(#b)"/></defs>'
    pdf = render(svg(f'{defs}<use href="#r" x="10" y="20" fill="red"/><use href="#r" x="110" y="20" fill="blue"/>', height=100))
    assert near(pixel(pdf, 30, 30), RED, 30)
    assert near(pixel(pdf, 105, 30), (0, 0, 255), 30)


@pytest.mark.parametrize("width", ["1e999", "1e308"])
def test_an_unbounded_filter_region_keeps_the_element(width: str, caplog: pytest.LogCaptureFixture) -> None:
    # inf or a value that overflows once scaled: no clip follows, the element draws unfiltered
    region = f'<filter id="i" filterUnits="userSpaceOnUse" x="0" y="0" width="{width}" height="100"><feGaussianBlur stdDeviation="2"/></filter>'
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        pdf = render(svg(f'<defs>{region}</defs><rect x="20" y="20" width="60" height="40" fill="red" filter="url(#i)"/>', height=100))
    assert near(pixel(pdf, 30, 30), RED)
    assert "region out of range" in caplog.text


def test_a_blurred_image_group() -> None:
    # A region in user space: WeasyPrint computes no bounding box for the group of an <image>
    png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4z8AAAAMBAQDJ/pLvAAAAAElFTkSuQmCC"
    blur = '<filter id="u" filterUnits="userSpaceOnUse" x="0" y="0" width="200" height="100"><feGaussianBlur stdDeviation="1"/></filter>'
    pdf = render(svg(f'<defs>{blur}</defs><g filter="url(#u)"><image x="20" y="20" width="60" height="40" href="data:image/png;base64,{png}"/></g>', height=100))
    assert near(pixel(pdf, 37, 30), RED, 60)


# ---------------- recoloring ----------------


def test_saturate_zero_is_gray() -> None:
    pdf = render(filtered('<feColorMatrix type="saturate" values="0"/>'))
    red, green, blue = pixel(pdf, 30, 30)
    assert abs(red - green) < 4
    assert abs(green - blue) < 4
    assert 100 < red < 160


def test_luminance_to_alpha() -> None:
    # Red has a luminance of 0.2125: black at that alpha
    pdf = render(filtered('<feColorMatrix type="luminanceToAlpha"/>'))
    assert near(pixel(pdf, 30, 30), (201, 201, 201), 6)


def test_hue_rotate_and_srgb() -> None:
    pdf = render(filtered('<feColorMatrix type="hueRotate" values="180"/>', ' color-interpolation-filters="sRGB"'))
    red, green, blue = pixel(pdf, 30, 30)
    assert red < 60
    assert green > 80
    assert blue > 80


def test_component_transfer_recolors() -> None:
    pdf = render(filtered('<feComponentTransfer><desc/><feFuncR type="table" tableValues="0 0"/><feFuncG type="discrete" tableValues="1"/></feComponentTransfer>'))
    assert near(pixel(pdf, 30, 30), (0, 255, 0), 10)


def test_recolor_reaches_floods_and_silhouettes() -> None:
    pdf = render(filtered('<feFlood flood-color="red"/><feColorMatrix type="saturate" values="0"/>'))
    red, green, _ = pixel(pdf, 5, 10)
    assert abs(red - green) < 4
    pdf = render(filtered('<feDropShadow dx="5" dy="5" stdDeviation="0" flood-color="red"/><feColorMatrix type="saturate" values="0"/>'))
    red, green, _ = pixel(pdf, 63, 47)
    assert abs(red - green) < 4


def test_recolored_gradient_is_sampled() -> None:
    body = '<defs><linearGradient id="g"><stop stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient></defs><rect x="20" y="20" width="160" height="40" fill="url(#g)" filter="url(#f)"/>'
    pdf = render(filtered('<feColorMatrix type="saturate" values="0"/>', target=body))
    red, green, blue = pixel(pdf, 75, 30)
    assert abs(red - green) < 4
    assert abs(green - blue) < 4


def test_sampled_stops() -> None:
    stops = [SimpleNamespace(get={"offset": "0", "stop-color": "red"}.get), SimpleNamespace(get={"offset": "150%", "stop-color": "blue", "stop-opacity": "0.5"}.get)]
    samples = filters.sampled_stops(stops, 12)
    assert len(samples) == filters.GRADIENT_SAMPLES + 1
    offsets = [float(sample.get("offset")) for sample in samples]
    assert offsets == sorted(offsets)
    assert offsets[-1] == 1
    # The opacity sits in the color, where the recolor sees it
    assert samples[-1].get("stop-color").endswith("/ 0.5)")
    assert samples[-1].get("stop-opacity") == "1"


@pytest.mark.parametrize(
    ("function", "values"),
    [
        ('<feFuncR type="table" tableValues="0 1 0"/>', [(0.25, 0.5), (1.0, 0.0)]),
        ('<feFuncR type="table" tableValues="0.3"/>', [(0.7, 0.3)]),
        ('<feFuncR type="discrete" tableValues="0 1"/>', [(0.25, 0.0), (0.75, 1.0), (1.0, 1.0)]),
        ('<feFuncR type="linear" slope="2" intercept="0.1"/>', [(0.2, 0.5)]),
        ('<feFuncR type="gamma" amplitude="2" exponent="2" offset="0.1"/>', [(0.5, 0.6)]),
        ('<feFuncR type="table"/>', [(0.4, 0.4)]),
    ],
)
def test_transfer_functions(function: str, values: list[tuple[float, float]]) -> None:
    import xml.etree.ElementTree as ET

    node = ET.fromstring(function)
    transfer = filters._transfer(node)
    for value, expected in values:
        assert abs(transfer(value) - expected) < 1e-9


@pytest.mark.parametrize(
    ("function", "values"),
    [
        ('<feFuncR type="gamma" exponent="-1"/>', [(0.0, math.inf), (0.5, 2.0)]),
        ('<feFuncR type="gamma" amplitude="-1" exponent="-1"/>', [(0.0, -math.inf)]),
        ('<feFuncR type="gamma" amplitude="0" exponent="-1" offset="0.25"/>', [(0.0, 0.25)]),
        ('<feFuncR type="gamma" exponent="1e10"/>', [(2.0, math.inf)]),
    ],
)
def test_gamma_transfer_limits(function: str, values: list[tuple[float, float]]) -> None:
    import xml.etree.ElementTree as ET

    transfer = filters._transfer(ET.fromstring(function))
    for value, expected in values:
        assert transfer(value) == expected


def test_gamma_on_black_draws() -> None:
    pdf = render(filtered('<feComponentTransfer><feFuncR type="gamma" exponent="-1"/></feComponentTransfer>', target='<rect x="20" y="20" width="60" height="40" fill="black" filter="url(#f)"/>'))
    assert near(pixel(pdf, 30, 30), RED)


@pytest.mark.parametrize("primitive", ['<feGaussianBlur stdDeviation="1e300"/>', '<feOffset dx="1e300"/>', '<feGaussianBlur stdDeviation="1e9999"/>', '<feDropShadow dy="1e300"/>'])
def test_unbounded_lengths_draw_unfiltered(primitive: str, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        pdf = render(filtered(primitive))
    assert near(pixel(pdf, 30, 30), RED)
    assert "length out of range" in caplog.text


@pytest.mark.parametrize("value", ["blur(1e300px)", "drop-shadow(1e300px 0 0 red)"])
def test_unbounded_css_function_lengths_draw_unfiltered(value: str) -> None:
    pdf = render(svg(f'<rect x="20" y="20" width="60" height="40" fill="red" style="filter:{value}"/>', height=120))
    assert near(pixel(pdf, 30, 30), RED)


def test_color_matrix_values() -> None:
    node = SimpleNamespace(get={"type": "matrix", "values": "1 2 3"}.get)
    assert filters._color_matrix_values(node)[0] == 1
    node = SimpleNamespace(get={"type": "matrix", "values": "a " * 20}.get)
    assert len(filters._color_matrix_values(node)) == 20


# ---------------- exceptions ----------------


class FakeSvg:
    def __init__(self) -> None:
        self.stream = RecordingStream()
        # No viewBox and no bounding box: the group box falls back to its minimum
        self.tree = SimpleNamespace(get_viewbox=lambda: None)

    def calculate_bounding_box(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def failing_original(*_args: Any) -> None:
    raise RuntimeError("drawing failed")


@pytest.mark.parametrize("layer", [Layer("alpha", opacity=0.5), Layer("alpha", blur=(2, 2)), Layer("source", opacity=0.5), Layer("source", blur=(2, 2))])
@pytest.mark.parametrize("opacity", [1, 0.5])
def test_a_failing_layer_restores_the_stream(layer: Layer, opacity: float) -> None:
    fake = FakeSvg()
    stream = fake.stream
    plan = filters.Plan([layer], None)
    node = SimpleNamespace(tag="g", attrib={})
    with pytest.raises(RuntimeError):
        filters.draw(fake, failing_original, node, 12, None, plan, opacity)
    # Else the caller pops the state of a mask or group stream, and q and Q of the page drift apart
    assert fake.stream is stream
    assert stream.depth == 0
    assert filters.RESTYLE.get() is None
    assert filters.RECOLOR.get() == ()


# ---------------- bounded work ----------------


def test_nested_blurs_draw_their_inner_blur_once(monkeypatch: pytest.MonkeyPatch) -> None:
    # A blur inside a blurred element is drawn sharp in the passes of the outer one: no 50 ** depth draws
    calls = []
    original = filters._blur_mask

    def counted(*args: Any) -> None:
        calls.append(1)
        original(*args)

    monkeypatch.setattr(filters, "_blur_mask", counted)
    blur = '<filter id="b"><feGaussianBlur stdDeviation="2"/></filter>'
    body = f'<defs>{blur}</defs><g filter="url(#b)"><g filter="url(#b)"><g filter="url(#b)"><rect x="20" y="20" width="60" height="40" fill="red"/></g></g></g>'
    pdf = render(svg(body, height=120))
    assert len(calls) == 1
    assert near(pixel(pdf, 37, 30), RED, 40)


def test_layer_fan_out_is_capped(caplog: pytest.LogCaptureFixture) -> None:
    merges = "".join(f'<feMerge result="r"><feMergeNode in="{"r" if i else "SourceGraphic"}"/><feMergeNode in="{"r" if i else "SourceGraphic"}"/></feMerge>' for i in range(8))
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        pdf = render(filtered(merges))
    assert near(pixel(pdf, 30, 30), RED)
    assert "too many layers" in caplog.text


def test_masked_child_of_a_blurred_group_keeps_its_mask() -> None:
    # The mask content must not be grown or turned black by the passes of the blur
    body = (
        '<defs><filter id="b"><feGaussianBlur stdDeviation="2"/></filter>'
        '<mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="200" height="120"><rect width="200" height="120" fill="white"/></mask></defs>'
        '<g filter="url(#b)"><rect x="20" y="20" width="60" height="40" fill="red" mask="url(#m)"/></g>'
    )
    pdf = render(svg(body, height=120))
    assert near(pixel(pdf, 37, 30), RED, 40)


@pytest.mark.parametrize(("slope", "expected"), [("2", RED), ("-1", WHITE)])
def test_alpha_slopes_out_of_range_are_clamped(slope: str, expected: tuple[int, int, int]) -> None:
    target = '<rect x="20" y="20" width="60" height="40" fill="red" fill-opacity="0.5" filter="url(#f)"/>'
    pdf = render(filtered(f'<feComponentTransfer><feFuncA type="linear" slope="{slope}"/></feComponentTransfer>', target=target))
    assert near(pixel(pdf, 30, 30), expected, 10)
    assert not re.search(rb"/ca (-|[2-9])", pdf)


def test_a_failing_restyle_restores_the_draw_state(monkeypatch: pytest.MonkeyPatch) -> None:
    from weasysvg import _core

    def broken(*_args: Any) -> None:
        raise RuntimeError("restyle failed")

    fake = FakeSvg()
    stream = fake.stream
    node, target, mode = SimpleNamespace(tag="rect"), RecordingStream(), Restyle("fills", 2)
    monkeypatch.setattr(_core, "restyle", broken)
    with pytest.raises(RuntimeError):
        filters._draw_into(fake, failing_original, node, 12, None, target, mode)
    assert fake.stream is stream
    assert filters.RESTYLE.get() is None
    assert filters.BLURRING.get() is False


def test_nested_filter_fan_out_is_bounded(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    # Three nested filters of 8 layers: 512 drawings of the innermost element without a budget
    calls = []
    original = filters._draw_layer

    def counted(*args: Any) -> None:
        calls.append(1)
        original(*args)

    monkeypatch.setattr(filters, "_draw_layer", counted)
    merge = "<feMerge>" + '<feMergeNode in="SourceGraphic"/>' * 8 + "</feMerge>"
    body = f'<defs><filter id="m">{merge}</filter></defs><g filter="url(#m)"><g filter="url(#m)"><g filter="url(#m)"><rect x="20" y="20" width="60" height="40" fill="red"/></g></g></g>'
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        pdf = render(svg(body, height=120))
    # 8 outer layers, 64 middle ones, and the innermost element drawn once, unfiltered, in each of those
    assert len(calls) == 8 + 64 + 64
    assert near(pixel(pdf, 30, 30), RED)
    assert "too many nested layers" in caplog.text


def test_nan_in_a_recolor_stays_a_color() -> None:
    pdf = render(filtered('<feComponentTransfer><feFuncR type="linear" slope="nan"/></feComponentTransfer>'))
    assert near(pixel(pdf, 30, 30), (0, 0, 0), 10)
    assert b"nan" not in pdf.lower()


def test_unbounded_flood_region_draws_unfiltered(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        pdf = render(filtered('<feFlood width="1e999" flood-color="blue"/>', ' filterUnits="userSpaceOnUse" x="0" y="0" width="200" height="120"'))
    assert near(pixel(pdf, 30, 30), RED)
    assert "length out of range" in caplog.text


def test_outer_recolor_reaches_a_filtered_child() -> None:
    # The shadow filter of the child must not drop the gray of its parent
    body = '<defs><filter id="f"><feColorMatrix type="saturate" values="0"/></filter><filter id="s"><feOffset dx="0"/></filter></defs><g filter="url(#f)"><rect x="20" y="20" width="60" height="40" fill="red" filter="url(#s)"/></g>'
    red, green, _ = pixel(render(svg(body, height=120)), 30, 30)
    assert abs(red - green) < 4


def test_outer_blur_spreads_a_filtered_child() -> None:
    filters_ = '<filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter><filter id="s"><feOffset dx="0"/></filter>'
    body = f'<defs>{filters_}</defs><g filter="url(#b)"><g filter="url(#s)"><rect x="20" y="20" width="60" height="40" fill="red"/></g></g>'
    assert faint(pixel(render(svg(body, height=120)), 13, 30))


def test_a_filtered_leaf_in_a_blur_grows_once() -> None:
    # The pass of the outer blur restyles the leaf once; its own filter must not grow it again
    def halo(inner: str) -> tuple[int, int, int]:
        defs = '<filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter><filter id="s"><feOffset dx="0"/></filter>'
        body = f'<defs>{defs}</defs><g filter="url(#b)"><rect x="40" y="20" width="60" height="40" fill="red"{inner}/></g>'
        return pixel(render(svg(body, height=120)), 24, 30)

    assert near(halo(' filter="url(#s)"'), halo(""), 6)


def test_invalid_stop_opacity_under_a_recolor_counts_as_opaque() -> None:
    gradient = '<linearGradient id="g"><stop stop-color="red" stop-opacity="abc"/><stop offset="1" stop-color="red"/></linearGradient>'
    target = f'<defs>{gradient}</defs><rect x="20" y="20" width="60" height="40" fill="url(#g)" filter="url(#f)"/>'
    red, green, blue = pixel(render(filtered('<feColorMatrix type="saturate" values="0"/>', target=target)), 30, 30)
    assert red < 200
    assert abs(red - green) < 4


def test_blurred_layers_count_against_the_draw_budget(caplog: pytest.LogCaptureFixture) -> None:
    # Eight blurred layers cost some 400 draws of the element: beyond the budget, the filter is dropped
    merge = "<feMerge>" + '<feMergeNode in="b"/>' * 8 + "</feMerge>"
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        pdf = render(filtered(f'<feGaussianBlur stdDeviation="2" result="b"/>{merge}'))
    assert near(pixel(pdf, 30, 30), RED)
    assert "too many nested layers" in caplog.text


@pytest.mark.parametrize("value", ["blur(-2px)", "blur(1.2.3px)", "drop-shadow(2px 2px -3px red)", "drop-shadow(1..2px 2px red)"])
def test_invalid_css_filter_lengths_draw_unfiltered(value: str) -> None:
    pdf = render(svg(f'<rect x="20" y="20" width="60" height="40" fill="red" style="filter:{value}"/>', height=120))
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 13, 30), WHITE, 3)


@pytest.mark.parametrize("value", ["blur(-2px)", "blur(1.2.3px)", "drop-shadow(2px 2px -3px red)"])
def test_invalid_css_filter_lengths_plan_unfiltered(value: str) -> None:
    node = SimpleNamespace(get={"filter": value}.get, tag="rect")
    fake = SimpleNamespace(tree=object())
    assert filters.plan(fake, node, 12) is filters.UNFILTERED


@pytest.mark.parametrize("primitive", ['<feFlood flood-opacity="abc"/>', '<feDropShadow flood-opacity="x"/>', '<feGaussianBlur stdDeviation="2"/><feFlood flood-color="red" flood-opacity="1e"/>'])
def test_malformed_filter_values_draw_unfiltered(primitive: str, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        pdf = render(filtered(primitive))
    assert near(pixel(pdf, 30, 30), RED)
    assert "drawn unfiltered" in caplog.text


# ---------------- turbulence and arithmetic ----------------


def colors(pdf: bytes, box: tuple[int, int, int, int]) -> set[tuple[int, int, int]]:
    """The distinct colors of the page inside box, in pixels at 72 dpi."""
    found = rasterize(pdf, 1).crop(box).getcolors(1 << 24) or []
    return {cast("tuple[int, int, int]", value) for _, value in found}


def test_turbulence_draws_noise_over_the_filter_region() -> None:
    pdf = render(filtered('<feTurbulence baseFrequency="0.05"/>'))
    assert images(pdf) == 1
    assert len(colors(pdf, (12, 13, 63, 47))) > 50
    assert pixel(pdf, 70, 30) == WHITE


def test_an_invalid_turbulence_type_is_turbulence() -> None:
    plain = rasterize(render(filtered('<feTurbulence baseFrequency="0.05"/>')), 1)
    invalid = rasterize(render(filtered('<feTurbulence baseFrequency="0.05" type="invalid"/>')), 1)
    fractal = rasterize(render(filtered('<feTurbulence baseFrequency="0.05" type="fractalNoise"/>')), 1)
    assert plain.tobytes() == invalid.tobytes()
    assert plain.tobytes() != fractal.tobytes()


@pytest.mark.parametrize("frequency", ["-0.05", "0.1 0.2 0.3", "abc"])
def test_an_invalid_base_frequency_is_zero(frequency: str) -> None:
    # Turbulence of frequency 0 is transparent everywhere
    pdf = render(filtered(f'<feTurbulence baseFrequency="{frequency}"/>'))
    assert colors(pdf, (12, 13, 63, 47)) == {WHITE}


def test_turbulence_values() -> None:
    # Noise is 0 on the lattice: turbulence is 0 there, fractal noise is 0.5
    assert turbulence.value(turbulence.Turbulence(1, 1, 2, 0, False, False), (3, 4), (0, 0, 10, 10)) == (0, 0, 0, 0)
    assert turbulence.value(turbulence.Turbulence(1, 1, 2, -5, True, False), (3, 4), (0, 0, 10, 10)) == (0.5, 0.5, 0.5, 0.5)
    stitched = turbulence.Turbulence(0.13, 0.27, 3, 2, True, True)
    # Stitched noise meets itself across the tile: its right edge continues its left edge
    assert turbulence.value(stitched, (9.9999, 3.3), (0, 0, 10, 10)) == pytest.approx(turbulence.value(stitched, (0.0, 3.3), (0, 0, 10, 10)), abs=1e-3)
    assert turbulence.value(stitched, (3.3, 9.9999), (0, 0, 10, 10)) == pytest.approx(turbulence.value(stitched, (3.3, 0.0), (0, 0, 10, 10)), abs=1e-3)
    assert turbulence.value(turbulence.Turbulence(0.0, 0.0, 1, 0, False, True), (1, 1), (0, 0, 10, 10)) == (0, 0, 0, 0)


def test_stitched_frequencies() -> None:
    # The nearest frequency that fits a whole number of cells into the tile
    assert turbulence._stitched_frequency(0.13, 10) == pytest.approx(0.1)
    assert turbulence._stitched_frequency(0.18, 10) == pytest.approx(0.2)
    assert turbulence._stitched_frequency(0.05, 10) == pytest.approx(0.1)


def test_turbulence_in_srgb_is_darker() -> None:
    linear = render(filtered('<feTurbulence baseFrequency="0.05"/>'))
    srgb = render(filtered('<feTurbulence baseFrequency="0.05"/>', ' color-interpolation-filters="sRGB"'))
    # linearRGB values turned into sRGB come out lighter
    assert sum(ImageStat.Stat(rasterize(srgb, 1).crop((12, 13, 63, 47))).mean) < sum(ImageStat.Stat(rasterize(linear, 1).crop((12, 13, 63, 47))).mean)


def test_turbulence_image_is_capped() -> None:
    picture = turbulence.image(turbulence.Turbulence(0.05, 0.05, 1, 0, False, False), (0, 0, 1000, 1000), 4, True)
    assert picture.width * picture.height <= turbulence.MAX_PIXELS
    assert picture.mode == "RGBA"


def test_turbulence_through_offset_blur_recolor_and_shadow() -> None:
    chains = [
        '<feTurbulence baseFrequency="0.05"/><feOffset dx="5"/><feGaussianBlur stdDeviation="2"/>',
        '<feTurbulence baseFrequency="0.05"/><feColorMatrix type="saturate" values="0"/>',
        '<feTurbulence baseFrequency="0.05" result="t"/><feFlood flood-color="blue"/><feComposite in2="t" operator="in"/>',
        '<feTurbulence baseFrequency="0.05" x="0" y="0" width="0"/>',
        '<feTurbulence baseFrequency="0.05"/><feComponentTransfer><feFuncA type="linear" slope="0.5"/></feComponentTransfer>',
    ]
    gray = colors(render(filtered(chains[1])), (12, 13, 63, 47))
    assert all(abs(red - green) < 4 and abs(green - blue) < 4 for red, green, blue in gray)
    shadow = colors(render(filtered(chains[2])), (12, 13, 63, 47))
    assert all(blue >= red and red == green for red, green, blue in shadow)
    assert colors(render(filtered(chains[3])), (12, 13, 63, 47)) == {WHITE}
    for chain in (chains[0], chains[4]):
        assert len(colors(render(filtered(chain)), (12, 13, 63, 47))) > 50


def test_arithmetic_of_a_flood_and_the_source() -> None:
    target = '<rect x="20" y="20" width="160" height="80" fill="seagreen" filter="url(#f)"/>'
    pdf = render(filtered('<feFlood flood-color="blue"/><feComposite operator="arithmetic" in2="SourceGraphic" k1="0" k2="1.5" k3="3" k4="0"/>', target=target))
    # The flood alone outside the shape, 3 seagreen + 1.5 blue in linearRGB inside it
    assert near(pixel(pdf, 12, 12), (0, 0, 255), 4)
    assert near(pixel(pdf, 75, 45), (81, 228, 255), 4)
    pdf = render(filtered('<feFlood flood-color="blue" result="f"/><feComposite in="SourceGraphic" in2="f" operator="arithmetic" k3="1" k4="0"/>', target=target))
    assert near(pixel(pdf, 75, 45), (0, 0, 255), 4)


@pytest.mark.parametrize(
    ("primitives", "inside", "outside"),
    [
        # k2 + k3 = 1: the source itself
        ('<feComposite operator="arithmetic" in2="SourceGraphic" k2="0.5" k3="0.5"/>', RED, WHITE),
        # k4 adds to each premultiplied channel: half transparent white on nothing
        ('<feComposite operator="arithmetic" in2="SourceGraphic" k2="1" k4="0.5"/>', (255, 128, 128), WHITE),
        # k1 squares the source
        ('<feComposite operator="arithmetic" in2="SourceGraphic" k1="1"/>', RED, WHITE),
    ],
)
def test_arithmetic_of_the_source_with_itself(primitives: str, inside: tuple[int, int, int], outside: tuple[int, int, int]) -> None:
    pdf = render(filtered(primitives, ' color-interpolation-filters="sRGB"'))
    assert near(pixel(pdf, 30, 30), inside, 4)
    assert near(pixel(pdf, 12, 13), outside, 4)


def test_arithmetic_of_floods_and_silhouettes() -> None:
    flood = '<feFlood flood-color="#808080" result="f"/>'
    pdf = render(filtered(f'{flood}<feFlood flood-color="red"/><feComposite in2="f" operator="arithmetic" k1="1"/>', ' color-interpolation-filters="sRGB"'))
    assert near(pixel(pdf, 12, 13), (128, 0, 0), 4)
    partial = '<feFlood flood-color="red" x="0" y="0" width="30" height="30"/>'
    pdf = render(filtered(f'{flood}{partial}<feComposite in2="f" operator="arithmetic" k1="1" k4="0.25"/>', ' color-interpolation-filters="sRGB"'))
    assert near(pixel(pdf, 15, 15), (191, 64, 64), 4)
    assert pixel(pdf, 40, 40) == WHITE
    # Opaque black times gray is opaque black
    pdf = render(filtered(f'{flood}<feComposite in="SourceAlpha" in2="f" operator="arithmetic" k1="1"/>', ' color-interpolation-filters="sRGB"'))
    assert near(pixel(pdf, 30, 30), (0, 0, 0), 4)
    assert pixel(pdf, 12, 13) == WHITE


def test_arithmetic_of_turbulence_and_a_flood() -> None:
    pdf = render(filtered('<feTurbulence baseFrequency="0.05" result="t"/><feFlood flood-color="white"/><feComposite in2="t" operator="arithmetic" k3="1" k4="0.5"/>'))
    assert len(colors(pdf, (12, 13, 63, 47))) > 20
    assert pixel(pdf, 70, 30) == WHITE


@pytest.mark.parametrize(
    "primitives",
    [
        '<feComposite operator="arithmetic" in="SourceAlpha" in2="SourceGraphic" k1="1"/>',
        '<feGaussianBlur stdDeviation="2" result="b"/><feFlood/><feComposite operator="arithmetic" in2="b" k1="1"/>',
        '<feComponentTransfer result="b"><feFuncA type="linear" slope="0.5"/></feComponentTransfer><feFlood/><feComposite operator="arithmetic" in2="b" k1="1"/>',
        '<feMerge result="m"><feMergeNode in="SourceGraphic"/><feMergeNode in="SourceAlpha"/></feMerge><feFlood/><feComposite operator="arithmetic" in2="m" k1="1"/>',
        '<feTurbulence baseFrequency="0.05" x="0" width="50" result="t"/><feFlood/><feComposite operator="arithmetic" in2="t" k1="1" k4="0.5"/>',
        '<feFlood x="0" width="50" result="f"/><feComposite operator="arithmetic" in="SourceGraphic" in2="f" k1="1"/>',
    ],
)
def test_unsupported_arithmetic_draws_the_element(primitives: str, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        pdf = render(filtered(primitives))
    assert near(pixel(pdf, 30, 30), RED, 60)
    assert "drawn unfiltered" in caplog.text


def test_a_negative_seed_follows_the_c_remainder() -> None:
    # C truncates the remainder toward zero: seed -5 is seed 6, seed 0 is seed 1
    assert turbulence._setup_seed(-5) == 6
    assert turbulence._setup_seed(0) == 1
    assert turbulence.lattice(-5) == turbulence.lattice(6)


def test_a_thin_turbulence_region_stays_within_the_pixel_cap() -> None:
    picture = turbulence.image(turbulence.Turbulence(0.05, 0.05, 1, 0, False, False), (0, 0, 1e7, 1e-4), 1, True)
    assert picture.width * picture.height <= turbulence.MAX_PIXELS


@pytest.mark.parametrize(
    "primitives",
    [
        '<feTurbulence baseFrequency="0.05" numOctaves="1e999"/>',
        '<feTurbulence baseFrequency="0.05" seed="1e999"/>',
        '<feTurbulence baseFrequency="1e999"/>',
        '<feTurbulence baseFrequency="0.05" width="1e999"/>',
        '<feTurbulence baseFrequency="0.05" x="1e300" width="1e300"/>',
    ],
)
def test_out_of_range_turbulence_keeps_the_svg(primitives: str) -> None:
    target = '<rect x="100" y="20" width="60" height="40" fill="blue" filter="url(#f)"/><rect x="20" y="20" width="60" height="40" fill="red"/>'
    pdf = render(filtered(primitives, target=target))
    # The rest of the SVG still draws after it
    assert near(pixel(pdf, 30, 30), RED, 4)


def test_a_faded_image_is_faded_before_its_recolor() -> None:
    # The matrix sets alpha to 1: the fade before it must not show
    matrix = '<feColorMatrix type="matrix" values="1 0 0 0 0 0 1 0 0 0 0 0 1 0 0 0 0 0 0 1"/>'
    faded = '<feTurbulence baseFrequency="0.05"/><feComponentTransfer><feFuncA type="linear" slope="0.5"/></feComponentTransfer>'
    opaque = render(filtered(f"{faded}{matrix}", ' color-interpolation-filters="sRGB"'))
    plain = render(filtered(f'<feTurbulence baseFrequency="0.05"/>{matrix}', ' color-interpolation-filters="sRGB"'))
    assert rasterize(opaque, 1).tobytes() == rasterize(plain, 1).tobytes()


def test_arithmetic_of_an_offset_flood_fills_the_uncovered_strip() -> None:
    # The strip the offset uncovers gets k4 on nothing: half transparent white, over a black backdrop
    target = '<rect x="0" y="0" width="200" height="120" fill="black"/><rect x="20" y="20" width="60" height="40" fill="red" filter="url(#f)"/>'
    primitives = '<feFlood flood-color="blue"/><feOffset dx="30" result="m"/><feFlood flood-color="white"/><feComposite in2="m" operator="arithmetic" k3="1" k4="0.5"/>'
    pdf = render(filtered(primitives, ' color-interpolation-filters="sRGB"', target=target))
    assert near(pixel(pdf, 12, 30), (128, 128, 128), 4)


def test_arithmetic_of_an_offset_image_draws_unfiltered(caplog: pytest.LogCaptureFixture) -> None:
    primitives = '<feTurbulence baseFrequency="0.05"/><feOffset dx="30" result="m"/><feFlood/><feComposite in2="m" operator="arithmetic" k3="1" k4="0.5"/>'
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        pdf = render(filtered(primitives))
    assert "partial image" in caplog.text
    assert near(pixel(pdf, 30, 30), RED, 4)


def test_pixel_work_is_bounded_per_svg(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setattr(filters, "MAX_PIXEL_WORK", 30_000)
    noise = "".join(f'<feTurbulence baseFrequency="0.05" seed="{seed}"/>' for seed in range(20))
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        pdf = render(filtered(noise))
    assert "too much pixel work" in caplog.text
    assert near(pixel(pdf, 30, 30), RED, 4)


def test_pixel_work_is_counted_once_per_image(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    # The same noise and recolor in many elements are computed once
    monkeypatch.setattr(filters, "MAX_PIXEL_WORK", 120_000)
    shapes = "".join(f'<rect x="{x}" y="20" width="10" height="10" filter="url(#f)"/>' for x in range(0, 200, 20))
    primitives = '<feTurbulence baseFrequency="0.05"/><feColorMatrix type="saturate" values="0"/>'
    body = f'<defs><filter id="f" filterUnits="userSpaceOnUse" x="0" y="0" width="100" height="60">{primitives}</filter></defs>{shapes}'
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        render(svg(body, height=120))
    assert "too much pixel work" not in caplog.text


def test_a_recolored_silhouette_is_computed_once(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    # Each draw evaluates the chain again: the silhouette must be the same image, or its recolor counts again
    monkeypatch.setattr(filters, "MAX_PIXEL_WORK", 120_000)
    shapes = "".join(f'<rect x="{x}" y="20" width="10" height="10" filter="url(#f)"/>' for x in range(0, 200, 20))
    primitives = '<feTurbulence baseFrequency="0.05" result="t"/><feFlood flood-color="blue"/><feComposite in2="t" operator="in"/><feColorMatrix type="saturate" values="0"/>'
    body = f'<defs><filter id="f" filterUnits="userSpaceOnUse" x="0" y="0" width="100" height="60">{primitives}</filter></defs>{shapes}'
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        render(svg(body, height=120))
    assert "too much pixel work" not in caplog.text


# ---------------- rectangles blurred exactly ----------------


def gray_at(pdf: bytes, x: float, y: float) -> float:
    """The darkness at a point in user units, 0 white to 1 black, on a page of 1 px per unit."""
    image = rasterize(pdf, 96 / 72).convert("L")
    return 1 - cast(int, image.getpixel((round(x), round(y)))) / 255


@pytest.mark.parametrize(
    ("deviation", "points"),
    [
        # Blurred along y only: the left edge stays sharp, the top edge is half dark
        ("0 5", [((52, 100), 1.0), ((48, 100), 0.0), ((148, 100), 1.0), ((152, 100), 0.0), ((100, 50), 0.5)]),
        # Blurred along x only: the bottom edge stays sharp as well
        ("5 0", [((100, 148), 1.0), ((100, 152), 0.0), ((150, 100), 0.5)]),
        # Both: the corner is a quarter dark, the product of two half profiles, not half as a distance gives
        ("5", [((50, 50), 0.25), ((100, 50), 0.5), ((100, 100), 1.0)]),
    ],
)
def test_a_blurred_rectangle_is_the_product_of_two_profiles(deviation: str, points: list[tuple[tuple[int, int], float]]) -> None:
    filters_ = f'<filter id="f" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{deviation}"/></filter>'
    pdf = render(svg(f'<defs>{filters_}</defs><rect x="50" y="50" width="100" height="100" fill="black" filter="url(#f)"/>', height=200))
    for (x, y), expected in points:
        assert gray_at(pdf, x, y) == pytest.approx(expected, abs=0.06)


def test_a_wide_rect_keeps_its_blurred_edges_in_place() -> None:
    # Each edge has a shading of its own: one shading over the whole rect moves the edges by units in PDFium
    filters_ = '<filter id="f" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>'
    pdf = render(svg(f'<defs>{filters_}</defs><rect x="50" y="50" width="500" height="100" fill="black" filter="url(#f)"/>', width=600, height=200))
    # PDFium samples a shading at the corner of a pixel: pixels 50 and 550 sit on the edges, half covered
    assert gray_at(pdf, 550, 100) == pytest.approx(0.5, abs=0.04)
    assert gray_at(pdf, 50, 100) == pytest.approx(0.5, abs=0.04)


def test_a_rect_narrower_than_its_blur_keeps_both_edges_in_one_shading() -> None:
    # 10 units wide, deviation 10 along x: the middle keeps Phi(0.5) - Phi(-0.5) of the color
    filters_ = '<filter id="f" x="-500%" y="-50%" width="1100%" height="200%"><feGaussianBlur stdDeviation="10 0"/></filter>'
    pdf = render(svg(f'<defs>{filters_}</defs><rect x="95" y="20" width="10" height="60" fill="black" filter="url(#f)"/>'))
    assert gray_at(pdf, 100, 50) == pytest.approx(0.383, abs=0.04)


def test_a_wide_horizontal_blur_keeps_its_tail() -> None:
    # stdDeviation 10 0: at 1.5 deviations beyond the right edge 7 percent of the color is left
    filters_ = '<filter id="f" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="10 0"/></filter>'
    pdf = render(svg(f'<defs>{filters_}</defs><rect x="50" y="50" width="100" height="100" fill="black" filter="url(#f)"/>', height=200))
    assert gray_at(pdf, 165, 100) == pytest.approx(0.067, abs=0.04)
    assert gray_at(pdf, 100, 48) == pytest.approx(0, abs=0.04)


@pytest.mark.parametrize(
    ("stroke", "exact"),
    [('stroke="black" stroke-width="10"', True), ('stroke="red"', False), ('stroke="black" stroke-linejoin="round"', False), ('rx="5"', False)],
)
def test_a_rect_in_one_paint_is_blurred_exactly(stroke: str, exact: bool) -> None:
    # A stroke in the paint of the fill widens the rect by half its width: still one rectangle
    filters_ = '<filter id="f" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="5"/></filter>'
    pdf = render(svg(f'<defs>{filters_}</defs><rect x="50" y="50" width="100" height="100" fill="black" {stroke} filter="url(#f)"/>', height=200))
    assert ("/ShadingType 2" in pdf.decode("latin-1")) == exact
    if exact:
        assert gray_at(pdf, 45, 45) == pytest.approx(0.25, abs=0.06)


def test_a_filter_on_anchored_text_covers_the_drawn_text() -> None:
    # The region of a filter on text: the box of the text where text-anchor puts it, plus 10 percent
    flood = '<filter id="f"><feFlood flood-color="black"/></filter>'
    pdf = render(svg(f'<defs>{flood}</defs><text x="100" y="60" font-size="40" text-anchor="middle" filter="url(#f)">HH</text>'))
    # Below the baseline only the flood is black: it spans the text, centered on x=100 as the text is
    image = rasterize(pdf, 96 / 72).convert("L")
    black = [x for x in range(200) if cast(int, image.getpixel((x, 65))) < 26]
    assert black, "the filter is drawn"
    assert abs((black[0] + black[-1]) / 2 - 100) < 3


def test_a_blurred_rect_has_no_seam_where_its_edges_meet_its_middle() -> None:
    # 4 deviations in from each side the shading of an edge meets the flat middle. Side by side, the two
    # left a device pixel unpainted at 192 dpi in PDFium: the shadow of blockdiag had a light line there
    filtered = '<filter id="b" height="1.504" width="1.1575" x="-0.07875" y="-0.252"><feGaussianBlur stdDeviation="4.2"/></filter>'
    body = filtered + '<rect fill="black" stroke="black" style="filter:url(#b);opacity:0.7" x="259" y="46" width="128" height="40"/>'
    scale = 8 / 3  # 192 dpi
    image = rasterize(render(svg(body, width=420, height=120)), scale).convert("L")
    k = scale * 0.75  # device pixels per CSS px
    row = [cast("int", image.getpixel((x, round(80 * k)))) for x in range(round(360 * k), round(380 * k))]
    column = [cast("int", image.getpixel((round(320 * k), y))) for y in range(round(52 * k), round(68 * k))]
    for line in (row, column):
        # The shadow changes smoothly there: no pixel lighter than both of its neighbors
        spikes = [middle - max(before, after) for before, middle, after in zip(line, line[1:], line[2:], strict=False)]
        assert max(spikes) <= 2, line


def test_turbulence_is_computed_at_twice_the_css_resolution() -> None:
    # Noise upscaled from one pixel per CSS px blurs at print resolution
    document = pdfium.PdfDocument(render(filtered('<feTurbulence baseFrequency="0.05"/>')))
    found = document[0].get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE], max_depth=50)
    assert [picture.get_px_size() for picture in found] == [(2 * 72, 2 * 48)]


def test_a_blurred_rect_edge_follows_the_gaussian_to_one_level() -> None:
    # PDFium looks a shading up in 256 steps over its whole axis: one shading over 8 deviations lagged the
    # profile by up to 4 levels, in runs of one slope that showed as bands down the edge. The paint, grown
    # by 2.15 deviations only, cut the tail of the mask off.
    filters_ = '<filter id="f" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="0 5"/></filter>'
    pdf = render(svg(f'<defs>{filters_}</defs><rect x="50" y="40" width="100" height="120" fill="black" filter="url(#f)"/>', height=200))
    image = rasterize(pdf, 8 / 3).convert("L")  # 192 dpi, 2 device pixels per unit
    gauss = NormalDist()
    # PDFium samples a shading at the corner of a device pixel
    errors = [abs(cast(int, image.getpixel((200, row))) - 255 * (1 - gauss.cdf((row / 2 - 40) / 5))) for row in range(40, 120)]
    assert max(errors) <= 1.5, [round(e, 1) for e in errors]


# ---------------- shapes blurred from their coverage ----------------


def blurred_shape(shape: str, deviation: str = "4", defs: str = "", primitive: str = "feGaussianBlur") -> Any:
    """One shape under a blur of deviation, rasterized at 2 device pixels per unit, in gray."""
    filter_ = f'<filter id="f" filterUnits="userSpaceOnUse" x="0" y="0" width="200" height="200"><{primitive} stdDeviation="{deviation}"/></filter>'
    pdf = render(svg(f'<defs>{defs}{filter_}</defs>{shape.removesuffix("/>")} filter="url(#f)"/>', height=200))
    return rasterize(pdf, 8 / 3)


def darkness(image: Any, x: float, y: float) -> float:
    """The darkness at a point in user units, 0 white to 1 black."""
    return 1 - cast(int, image.convert("L").getpixel((round(2 * x), round(2 * y)))) / 255


def test_a_blurred_circle_fades_smoothly() -> None:
    # The levels of the nearest edge were flat grays: rings in the tail, 239 239 239 247 247 247 255
    image = blurred_shape('<circle cx="100" cy="100" r="60" fill="black"/>', "6").convert("L")
    row = [cast(int, image.getpixel((x, 200))) for x in range(320, 400)]
    assert row == sorted(row), row
    steps = [b - a for a, b in zip(row, row[1:], strict=False)]
    assert max(abs(b - a) for a, b in zip(steps, steps[1:], strict=False)) <= 2, row
    # The tail goes on past the paint that was grown by 2.15 deviations
    assert darkness(image, 173.5, 100) > 0.002, row


@pytest.mark.parametrize(
    ("shape", "expected"),
    [
        # A bar 2 units wide: Phi(0.25) - Phi(-0.25) of the color in its middle
        ('<path d="M99 20h2v160h-2z" fill="black"/>', 0.197),
        # A dot of radius 2: 1 - exp(-r^2 / 2 s^2) in its center
        ('<circle cx="100" cy="100" r="2" fill="black"/>', 0.118),
        # A ring from 4 to 8: exp(-a^2 / 2 s^2) - exp(-b^2 / 2 s^2) in its hole, by even-odd and by winding
        ('<path d="M92 100a8 8 0 1 0 16 0a8 8 0 1 0-16 0zM96 100a4 4 0 1 0 8 0a4 4 0 1 0-8 0z" fill="black" fill-rule="evenodd"/>', 0.471),
        ('<path d="M92 100a8 8 0 1 0 16 0a8 8 0 1 0-16 0zM96 100a4 4 0 1 1 8 0a4 4 0 1 1-8 0z" fill="black"/>', 0.471),
    ],
)
def test_a_thin_shape_is_blurred_from_all_of_its_edges(shape: str, expected: float) -> None:
    # Deviation 4. The levels grew and shrank a shape by its nearest edge: one thinner than a few
    # deviations came out dark and sharp, as the lens ring of the OpenStreetMap logo
    assert darkness(blurred_shape(shape), 100, 100) == pytest.approx(expected, abs=0.02)


def test_the_blur_of_a_small_drop_has_no_hole() -> None:
    # The paint, grown by a stroke wider than the drop, left the inside of the stroke unpainted in PDFium:
    # a white glint in the shadow of the Inkscape logo
    image = blurred_shape('<path d="M99.4 98.69c-4.6 4.2.8 8.6 5.3 5.7 1.2-.8-.1-4.7-5.3-5.7z" fill="black"/>', "6")
    around = [darkness(image, 102 + 6 * math.cos(k * math.pi / 16), 101.5 + 6 * math.sin(k * math.pi / 16)) for k in range(32)]
    assert min(around) > 0.05, around


def test_a_blurred_shape_keeps_its_gradient() -> None:
    # The paint covers all the mask, the gradient placed on the box of the shape
    gradient = '<linearGradient id="g"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient>'
    image = blurred_shape('<circle cx="100" cy="100" r="40" fill="url(#g)"/>', "2", defs=gradient)
    left, right = image.getpixel((140, 200)), image.getpixel((260, 200))
    assert left[0] > 200 > left[2], left
    assert right[2] > 200 > right[0], right


def test_the_drop_shadow_of_a_shape_is_its_blurred_coverage() -> None:
    image = blurred_shape('<circle cx="100" cy="100" r="2" fill="red"/>', primitive='feDropShadow dx="0" dy="0" flood-color="black"')
    # Beside the dot only its shadow: a dot of radius 2 blurred by 4, seen 4 from its center
    assert darkness(image, 104, 100) == pytest.approx(0.073, abs=0.015)


def test_a_compressed_mesh_draws_the_same() -> None:
    # Compressed, the rows of the mesh go through the PNG predictor Up
    document = svg('<defs><filter id="f"><feGaussianBlur stdDeviation="4"/></filter></defs><circle cx="100" cy="50" r="20" fill="black" filter="url(#f)"/>')
    compressed = weasyprint.HTML(string=page_html(document)).write_pdf()
    assert b"/Predictor 12" in compressed
    plain, packed = rasterize(render(document), 8 / 3), rasterize(compressed, 8 / 3)
    assert [plain.getpixel((x, 100)) for x in range(100, 300)] == [packed.getpixel((x, 100)) for x in range(100, 300)]


@pytest.mark.parametrize(
    ("shape", "deviation", "limits"),
    [
        ('<circle cx="100" cy="100" r="20" fill="black" stroke="red"/>', "2", {}),
        ('<path d="M80 80h40v40z" fill="black" marker-start="url(#m)"/>', "2", {}),
        ('<circle cx="100" cy="100" r="20" fill="black"/>', "2 0", {}),
        ('<path d="M80 80L120 120" fill="black"/>', "2", {}),
        ('<circle cx="100" cy="100" r="20" fill="black"/>', "2", {"MAX_CELLS": 10}),
        ('<circle cx="100" cy="100" r="20" fill="black"/>', "2", {"MAX_PIXEL_WORK": 10}),
    ],
)
def test_a_shape_the_coverage_cannot_take_keeps_the_levels(shape: str, deviation: str, limits: dict[str, int], monkeypatch: pytest.MonkeyPatch) -> None:
    # A stroke or markers paint more than the outline, a deviation along one axis only has no grid, a path
    # without area has no outline: those, and a grid past its limits, keep the levels of the nearest edge
    for name, value in limits.items():
        monkeypatch.setattr(shapeblur if name == "MAX_CELLS" else filters, name, value)
    calls: list[int] = []
    original = filters._blur_mask

    def counted(*args: Any) -> None:
        calls.append(1)
        original(*args)

    monkeypatch.setattr(filters, "_blur_mask", counted)
    blurred_shape(shape, deviation, defs='<marker id="m"><circle r="1"/></marker>')
    assert calls == [1]


def test_the_recorder_starts_a_subpath_where_the_path_does() -> None:
    # Path data without a moveto starts at its first point; a second close adds nothing
    recorder = shapeblur._Recorder(1.0)
    recorder.line_to(0, 0)
    recorder.line_to(10, 0)
    recorder.close()
    recorder.current = []
    recorder.close()
    recorder.curve_to(0, 10, 10, 10, 10, 20)
    assert recorder.rings[0] == [(0, 0), (10, 0)]
    assert recorder.rings[-1][0] == (0, 10)
    assert recorder.rings[-1][-1] == pytest.approx((10, 20))


def test_a_rect_with_a_stroke_of_no_width_is_blurred_from_its_coverage() -> None:
    # Not a plain rect, as its stroke has another paint, but the stroke paints nothing
    image = blurred_shape('<rect x="99" y="20" width="2" height="160" fill="black" stroke="red" stroke-width="0"/>')
    assert darkness(image, 100, 100) == pytest.approx(0.197, abs=0.02)


def test_the_drop_shadow_of_a_stroked_shape_keeps_the_levels() -> None:
    image = blurred_shape('<circle cx="100" cy="100" r="20" fill="none" stroke="red" stroke-width="4"/>', primitive='feDropShadow dx="0" dy="0" flood-color="black"')
    # The shadow inside the ring, faint
    assert 0.02 < darkness(image, 100, 100 - 12) < 0.6
