"""Filter chains: vector layers, the vector blur, recoloring, and CSS filter functions."""

from __future__ import annotations

import logging
import math
import re
from types import SimpleNamespace
from typing import Any, cast

import pytest
from helpers import RecordingStream, content, pixel, rasterize, render, svg
from PIL import ImageStat

from weasysvg import filters, turbulence
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
    node = SimpleNamespace(tag="g")
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
    monkeypatch.setattr(filters, "MAX_PIXEL_WORK", 30_000)
    shapes = "".join(f'<rect x="{x}" y="20" width="10" height="10" filter="url(#f)"/>' for x in range(0, 200, 20))
    primitives = '<feTurbulence baseFrequency="0.05"/><feColorMatrix type="saturate" values="0"/>'
    body = f'<defs><filter id="f" filterUnits="userSpaceOnUse" x="0" y="0" width="100" height="60">{primitives}</filter></defs>{shapes}'
    with caplog.at_level(logging.WARNING, logger="weasysvg"):
        render(svg(body, height=120))
    assert "too much pixel work" not in caplog.text
