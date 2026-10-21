"""paint-order, with the colors Chromium 156 paints (measured with Playwright, scaled 2x here)."""

from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any
from xml.etree import ElementTree as ET

import pytest
from helpers import content, pixel, render, svg

from weasysvg import _core, paint_order

BLUE, GREEN, ORANGE, WHITE, RED = (0, 0, 255), (0, 128, 0), (255, 165, 0), (255, 255, 255), (255, 0, 0)
# A square from 40 to 160 with a stroke 40 wide: its outer half spans 20 to 40, its inner half 40 to 60
RECT = '<rect x="40" y="40" width="120" height="120" fill="green" stroke="blue" stroke-width="40" {}/>'
# CSS px 30, 50 and 100 at 72 dpi
OUTER, INNER, MIDDLE = 22, 37, 75


def near(actual: tuple[int, int, int], expected: tuple[int, int, int], tolerance: int = 3) -> bool:
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected, strict=True))


def square(body: str) -> bytes:
    return render(svg(body, 200, 200))


def halves(pdf: bytes) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """The color of the outer and of the inner half of the stroke, on the left edge."""
    return pixel(pdf, OUTER, MIDDLE), pixel(pdf, INNER, MIDDLE)


# ---------------- values ----------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ("fill", "stroke", "markers")),
        ("normal", ("fill", "stroke", "markers")),
        ("initial", ("fill", "stroke", "markers")),
        ("stroke", ("stroke", "fill", "markers")),
        ("Markers  STROKE", ("markers", "stroke", "fill")),
        ("fill markers", ("fill", "markers", "stroke")),
        ("markers stroke fill", ("markers", "stroke", "fill")),
        ("stroke stroke", None),
        ("stroke normal", None),
        ("bogus", None),
        ("fill stroke markers fill", None),
    ],
)
def test_parse(value: str | None, expected: tuple[str, ...] | None) -> None:
    assert paint_order.parse(value) == expected


def test_invalid_values_are_dropped_before_the_cascade() -> None:
    root = ET.fromstring('<svg><g paint-order="bogus"/><g paint-order="inherit"/><g style="fill:red; paint-order: stroke stroke;stroke:blue !important"/><g style="paint-order:stroke"/><g style="fill:red"/></svg>')
    paint_order.drop_invalid(root)
    assert [dict(element.attrib) for element in root] == [{}, {"paint-order": "inherit"}, {"style": "fill:red;stroke:blue !important"}, {"style": "paint-order:stroke"}, {"style": "fill:red"}]


# ---------------- shapes ----------------


def test_normal_paints_the_stroke_over_the_fill() -> None:
    assert halves(square(RECT.format(""))) == (BLUE, BLUE)


@pytest.mark.parametrize(
    "body",
    [
        RECT.format('paint-order="stroke"'),
        RECT.format('style="paint-order: stroke fill"'),
        f'<g paint-order="stroke">{RECT.format("")}</g>',
        # The boxes of the OSI model on Wikimedia
        f'<g style="paint-order:stroke">{RECT.format("")}</g>',
        # An invalid value is ignored: the value of the parent inherits
        '<g paint-order="stroke">' + RECT.format('paint-order="bogus"') + "</g>",
        '<g paint-order="stroke">' + RECT.format('style="paint-order: fill fill"') + "</g>",
        "<defs>" + RECT.format('id="r"') + '</defs><use href="#r" paint-order="stroke"/>',
        # A child without paint leaves q and Q after the path
        RECT.format('paint-order="stroke"').replace("/>", "><title>box</title></rect>"),
    ],
)
def test_stroke_first_shows_the_outer_half_only(body: str) -> None:
    pdf = square(body)
    assert halves(pdf) == (BLUE, GREEN)
    # One path for each paint, in one graphics state
    assert re.search(r" re\nS\n[\d. ]+ re\nf\n", content(pdf))


@pytest.mark.parametrize(
    "body",
    [
        RECT.format('paint-order="stroke stroke"'),
        '<g paint-order="stroke">' + RECT.format('paint-order="normal"') + "</g>",
        RECT.format('paint-order="fill"'),
        # Only one paint: there is nothing to order
        RECT.format('paint-order="stroke" fill="none"').replace('fill="green" ', ""),
    ],
)
def test_stroke_last(body: str) -> None:
    assert halves(square(body))[1] in (BLUE, WHITE)


def test_stroke_opacity_shows_through_the_outer_half_only() -> None:
    body = '<rect x="40" y="40" width="120" height="120" fill="red" stroke="#000" stroke-opacity=".4" stroke-width="40" {}/>'
    outer, inner = halves(square(body.format('paint-order="stroke"')))
    assert near(outer, (153, 153, 153))
    assert inner == RED
    outer, inner = halves(square(body.format("")))
    assert near(outer, (153, 153, 153))
    assert near(inner, (153, 0, 0))


@pytest.mark.parametrize(
    ("stroke", "inner"),
    [
        ('stroke="rgba(0,0,255,.4)"', (0, 77, 102)),
        ('stroke="url(#g)"', (0, 64, 127)),
    ],
)
def test_translucent_stroke_shows_the_fill_under_it(stroke: str, inner: tuple[int, int, int]) -> None:
    """B paints fill and stroke as one knockout object: the stroke showed the white under the fill."""
    gradient = '<linearGradient id="g"><stop stop-color="blue" stop-opacity=".5"/><stop offset="1" stop-color="blue" stop-opacity=".5"/></linearGradient>'
    pdf = square(gradient + RECT.format("").replace('stroke="blue"', stroke))
    assert near(pixel(pdf, INNER, MIDDLE), inner)
    assert re.search(r" re\nf\n[\d. ]+ re\nS\n", content(pdf))


def test_group_opacity_applies_once_to_both_paints() -> None:
    outer, inner = halves(square(RECT.format('opacity=".5" paint-order="stroke"')))
    assert near(outer, (127, 127, 255))
    assert near(inner, (127, 191, 127))


def test_fill_opacity_shows_the_stroke_under_the_fill() -> None:
    outer, inner = halves(square(RECT.format('fill-opacity=".5" paint-order="stroke"')))
    assert outer == BLUE
    assert near(inner, (0, 64, 127))


def test_clip_is_not_part_of_the_path() -> None:
    clip = '<clipPath id="c"><rect width="100" height="200"/></clipPath>'
    pdf = square(clip + RECT.format('paint-order="stroke" clip-path="url(#c)"'))
    assert halves(pdf) == (BLUE, GREEN)
    assert pixel(pdf, 150 - OUTER, MIDDLE) == WHITE


def test_dashed_stroke_under_the_fill() -> None:
    pdf = square(RECT.format('stroke-dasharray="20 20" paint-order="stroke"'))
    # Up the left edge, the last of the outline: a gap at y 50, a dash at y 70
    assert pixel(pdf, OUTER, 37) == WHITE
    assert pixel(pdf, OUTER, 52) == BLUE
    assert pixel(pdf, INNER, 37) == GREEN
    assert pixel(pdf, INNER, 52) == GREEN


def test_gradient_stroke_under_the_fill() -> None:
    gradient = '<linearGradient id="g"><stop offset="0" stop-color="blue"/><stop offset="1" stop-color="red"/></linearGradient>'
    body = gradient + RECT.format("{}").replace('stroke="blue"', 'stroke="url(#g)"')
    pdf, normal = square(body.format('paint-order="stroke"')), square(body.format(""))
    # The gradient runs over the same box: the outer half keeps its colors
    assert pixel(pdf, OUTER, MIDDLE) == pixel(normal, OUTER, MIDDLE)
    assert pixel(pdf, INNER, MIDDLE) == GREEN
    assert pixel(pdf, 150 - OUTER, MIDDLE) == pixel(normal, 150 - OUTER, MIDDLE)
    assert pixel(pdf, 150 - INNER, MIDDLE) == GREEN


def test_pattern_fill_over_the_stroke() -> None:
    pattern = '<pattern id="p" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="green"/></pattern>'
    pdf = square(pattern + RECT.format('paint-order="stroke"').replace('fill="green"', 'fill="url(#p)"'))
    assert halves(pdf) == (BLUE, GREEN)


# ---------------- markers ----------------

MARKER = '<marker id="m" refX="20" refY="20" markerWidth="40" markerHeight="40" markerUnits="userSpaceOnUse"><rect width="40" height="40" fill="orange"/></marker>'
PATH = '<path d="M40 40 H160 V160" fill="green" stroke="blue" stroke-width="20" marker-start="url(#m)" marker-mid="url(#m)" marker-end="url(#m)" {}/>'
# CSS (154, 150), (166, 150), (156, 44), (144, 56), (164, 36) at 72 dpi: the end and the mid marker
PROBES = ((115, 112), (124, 112), (117, 33), (108, 42), (123, 27))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("normal", (ORANGE, ORANGE, ORANGE, ORANGE, ORANGE)),
        ("stroke", (ORANGE, ORANGE, ORANGE, ORANGE, ORANGE)),
        ("markers", (BLUE, BLUE, BLUE, GREEN, BLUE)),
        ("markers stroke", (GREEN, BLUE, GREEN, GREEN, BLUE)),
        ("fill markers", (BLUE, BLUE, BLUE, ORANGE, BLUE)),
        ("stroke markers", (GREEN, ORANGE, GREEN, GREEN, ORANGE)),
    ],
)
def test_markers_in_order(value: str, expected: tuple[tuple[int, int, int], ...]) -> None:
    pdf = square(MARKER + PATH.format(f'paint-order="{value}"'))
    assert tuple(pixel(pdf, x, y) for x, y in PROBES) == expected


# ---------------- text ----------------

GLYPH = '<text x="20" y="180" font-size="160" font-family="DejaVu Sans" font-weight="bold" fill="green" stroke="blue" stroke-width="24" {}>{}</text>'
# CSS (40, 120): inside the stem of the I, in the inner half of its stroke
STEM = (30, 90)


@pytest.mark.parametrize(
    ("attributes", "text"),
    [
        ('paint-order="stroke"', "I"),
        ('paint-order="stroke"', "<tspan>I</tspan>"),
        # One position for each character: WeasyPrint lays them out
        ('paint-order="stroke" rotate="0 0"', "I"),
    ],
)
def test_text_stroke_first_fills_over_its_stroke(attributes: str, text: str) -> None:
    pdf = square(GLYPH.format(attributes, text))
    assert pixel(pdf, *STEM) == GREEN
    page = content(pdf)
    assert "2 Tr" not in page
    assert page.index("1 Tr") < page.index("0 Tr")


def test_text_normal_strokes_over_its_fill() -> None:
    pdf = square(GLYPH.format("", "I"))
    assert pixel(pdf, *STEM) == BLUE
    assert "2 Tr" in content(pdf)


def test_text_translucent_stroke_shows_the_fill_under_it() -> None:
    pdf = square(GLYPH.format('stroke-opacity=".4"', "I"))
    assert near(pixel(pdf, *STEM), (0, 77, 102))
    page = content(pdf)
    assert "2 Tr" not in page
    assert page.index("0 Tr") < page.index("1 Tr")


def test_text_on_a_path_stroke_first() -> None:
    body = '<path id="p" d="M20 180 H400"/><text font-size="160" font-family="DejaVu Sans" font-weight="bold" fill="green" stroke="blue" stroke-width="24" paint-order="stroke"><textPath href="#p">I</textPath></text>'
    pdf = square(body)
    assert pixel(pdf, *STEM) == GREEN


def test_text_decoration_stroke_first() -> None:
    body = '<text x="0" y="120" font-size="80" font-family="DejaVu Sans" fill="green" stroke="blue" stroke-width="12" text-decoration="line-through" paint-order="stroke">__</text>'
    page = content(square(body))
    # The line is a rectangle: stroked, then filled, from the same path
    assert re.search(r"( re\n)S\n[\d. ]+ re\nf\n", page)


def test_text_with_one_paint_keeps_its_mode() -> None:
    pdf = square(GLYPH.replace('stroke="blue"', 'stroke="none"').format('paint-order="stroke"', "I"))
    assert "0 Tr" in content(pdf)
    assert "1 Tr" not in content(pdf)


def test_split_text_waits_for_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(paint_order._ENABLED, "text", False)
    stream = SimpleNamespace(stream=[b"BT", b"2 Tr", b"ET"])
    paint_order.split_text(stream, SimpleNamespace(get=lambda _key: "stroke"), 0)
    assert stream.stream == [b"BT", b"2 Tr", b"ET"]


# ---------------- fill_stroke ----------------


def test_fill_stroke_without_a_path_keeps_the_operator() -> None:
    painted: list[Any] = []
    stream = SimpleNamespace(stream=[b"q", b"Q"], fill_and_stroke=lambda even_odd: painted.append(even_odd))
    node = SimpleNamespace(get=lambda key, default=None: "stroke" if key == "paint-order" else default, vertices=None)
    token = _core._DRAWING.set((node, 16.0))
    try:
        paint_order.fill_stroke(SimpleNamespace(stream=stream), "green", "blue")
    finally:
        _core._DRAWING.reset(token)
    assert painted == [False]
    assert stream.stream == [b"q", b"Q"]
