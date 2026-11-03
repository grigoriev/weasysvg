"""Gradients, patterns, masks, blending and the opacity group."""

from __future__ import annotations

import math
import re
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from xml.etree import ElementTree as ET

import pytest
from helpers import SVG_NS, RecordingStream, content, pixel, rasterize, render, streams, svg
from PIL import ImageChops, ImageStat

import weasysvg
from weasysvg import paint
from weasysvg.paint import GRADIENT_CELL, drop_empty_presentation

RED = (255, 0, 0)
WHITE = (255, 255, 255)


def near(actual: tuple[int, int, int], expected: tuple[int, int, int], tolerance: int = 40) -> bool:
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected, strict=True))


# ---------------- tree pass ----------------


def test_empty_presentation_attributes_are_dropped() -> None:
    root = ET.fromstring(f'<svg xmlns="{SVG_NS}"><rect fill="" stroke=" " id="r" width="1"/></svg>')
    drop_empty_presentation(root)
    assert root[0].attrib == {"id": "r", "width": "1"}


def test_empty_fill_paints_black() -> None:
    pdf = render(svg('<rect width="200" height="100" fill=""/>'))
    assert near(pixel(pdf, 50, 30), (0, 0, 0))


# ---------------- gradients ----------------


def test_gradient_cell_is_large() -> None:
    body = '<defs><linearGradient id="g"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient></defs><rect width="200" height="100" fill="url(#g)"/>'
    pdf = render(svg(body))
    text = pdf.decode("latin-1")
    sizes = [float(value) for value in re.findall(r"/BBox \[\s*[-\d.]+ [-\d.]+ ([-\d.]+)", text)]
    assert any(abs(value - GRADIENT_CELL) < 1 for value in sizes)
    assert near(pixel(pdf, 5, 30), RED, 60)


def test_radial_percentages_use_the_normalized_diagonal() -> None:
    gradient = ET.Element("radialGradient", {"r": "25%", "fr": "10%"})
    node = type("Node", (), {"tag": "radialGradient", "attrib": gradient.attrib, "get": gradient.get})()
    changed = paint._radial_percentages(node)
    assert changed == {"r": "25%", "fr": "10%"}
    assert gradient.attrib == {"r": "0.25", "fr": "0.1"}


def test_radial_percentages_skip_user_space_and_linear() -> None:
    user = ET.Element("radialGradient", {"gradientUnits": "userSpaceOnUse", "r": "50%"})
    node = type("Node", (), {"tag": "radialGradient", "attrib": user.attrib, "get": user.get})()
    assert paint._radial_percentages(node) == {}
    linear = type("Node", (), {"tag": "linearGradient", "attrib": {}, "get": {}.get})()
    assert paint._radial_percentages(linear) == {}


def test_radial_gradient_attributes_are_restored() -> None:
    body = (
        '<defs><radialGradient id="g" r="40%" fr="5%"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="white"/></radialGradient>'
        '<radialGradient id="h" href="#g"/></defs>'
        '<rect width="100" height="100" fill="url(#g)"/><rect x="100" width="100" height="100" fill="url(#h)"/>'
    )
    pdf = render(svg(body))
    assert near(pixel(pdf, 37, 37), RED, 60)
    assert near(pixel(pdf, 112, 37), RED, 60)


@pytest.mark.parametrize("units", ["", ' gradientUnits="userSpaceOnUse" x1="0" x2="200"'])
@pytest.mark.parametrize("opacity", ["1", "0.999"])
def test_rotated_gradient_covers_the_shape(units: str, opacity: str) -> None:
    # WeasyPrint sizes the cell from two corners of the box: rotated by 45 degrees, the cell is a sliver
    gradient = f'<linearGradient id="g"{units} gradientTransform="rotate(45 100 50)"><stop stop-color="red"/><stop offset="1" stop-color="red" stop-opacity="{opacity}"/></linearGradient>'
    pdf = render(svg(f'<defs>{gradient}</defs><rect width="200" height="100" fill="url(#g)"/>'))
    for x, y in ((10, 10), (75, 37), (140, 65)):
        assert near(pixel(pdf, x, y), RED, 30)


def test_degenerate_gradient_transforms() -> None:
    # A singular transform and a shape without a box: no cell, the rendering of WeasyPrint
    gradient = '<linearGradient id="g" gradientTransform="scale(0)"><stop stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient><linearGradient id="h" gradientTransform="rotate(45)" href="#g"/>'
    render(svg(f'<defs>{gradient}</defs><rect width="200" height="100" fill="url(#g)"/><path d="" fill="url(#h)"/>'))


def test_gradient_cell_needs_a_box() -> None:
    gradient = SimpleNamespace(attrib={"gradientTransform": "rotate(45)"}, get={"gradientTransform": "rotate(45)"}.get)
    fake = SimpleNamespace(calculate_bounding_box=lambda *_args: None)
    assert paint._gradient_cell(fake, object(), gradient, 12, False) is None


@pytest.mark.parametrize("box", [(0.0, 50.0, 200.0, 0.0), (50.0, 0.0, 0.0, 200.0)])
def test_a_blurred_flat_box_leaves_the_cell_to_weasyprint(box: tuple[float, float, float, float]) -> None:
    # The region a blur paints, in units of a box of no height or width, divided by zero. WeasyPrint 70
    # gives a fill no such box, but a box from elsewhere must not stop the render
    gradient = SimpleNamespace(attrib={}, get={}.get)
    node = object()
    fake = SimpleNamespace(calculate_bounding_box=lambda *_args: box)
    token = paint.BOXED.set((node, (0.0, 0.0, 200.0, 200.0)))
    try:
        assert paint._gradient_cell(fake, node, gradient, 12, False) is None
    finally:
        paint.BOXED.reset(token)


def test_gradient_interpolates_unpremultiplied() -> None:
    # Chromium mixes transparent white and black into half transparent gray: 0.75 over white, not 0.5
    gradient = '<linearGradient id="g"><stop stop-color="white" stop-opacity="0"/><stop offset="1" stop-color="black"/></linearGradient>'
    mask = '<mask id="m"><rect width="200" height="100" fill="url(#g)"/></mask>'
    pdf = render(svg(f'<defs>{gradient}{mask}</defs><rect width="200" height="50" fill="url(#g)"/><rect y="50" width="200" height="50" fill="red" mask="url(#m)"/>'))
    assert near(pixel(pdf, 75, 18), (191, 191, 191), 12)
    # In a mask the gray of the middle shows, so the red does too
    assert pixel(pdf, 75, 55) != WHITE


def test_gradient_stops_via_href_used_twice() -> None:
    body = (
        '<defs><linearGradient id="base"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="red"/></linearGradient>'
        '<linearGradient id="a" xlink:href="#base"/><linearGradient id="b" xlink:href="#base" x1="1" x2="0"/></defs>'
        '<rect width="100" height="100" fill="url(#a)"/><rect x="100" width="100" height="100" fill="url(#b)"/>'
    )
    pdf = render(svg(body))
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 120, 30), RED)


@pytest.mark.parametrize("paint_server", ['<linearGradient id="p"><stop stop-color="red"/><stop offset="1" stop-color="red"/></linearGradient>', '<pattern id="p" width="1" height="1"><rect width="200" height="200" fill="red"/></pattern>'])
def test_paint_server_stroke_has_its_width(paint_server: str) -> None:
    # The stroke spans 10 to 30 user units around the left edge at x=20
    pdf = render(svg(f'<defs>{paint_server}</defs><rect x="20" y="20" width="100" height="60" fill="none" stroke="url(#p)" stroke-width="20"/>'))
    assert near(pixel(pdf, 9, 37), RED, 60)


# ---------------- patterns ----------------


def test_pattern_x_moves_the_tile_in_user_space() -> None:
    body = '<defs><pattern id="p" patternUnits="userSpaceOnUse" x="50" y="0" width="100" height="100"><rect width="50" height="100" fill="red"/></pattern></defs><rect width="200" height="100" fill="url(#p)"/>'
    pdf = render(svg(body))
    # The tile starts at x=50: red from 50 to 100 CSS px, white from 0 to 50
    assert near(pixel(pdf, 15, 30), WHITE)
    assert near(pixel(pdf, 55, 30), RED)


def test_pattern_in_bounding_box_units_used_twice() -> None:
    body = '<defs><pattern id="p" x="0.25" y="0" width="0.5" height="1"><rect width="50" height="100" fill="red"/></pattern></defs><rect width="200" height="100" fill="url(#p)"/><rect y="100" width="200" height="100" fill="url(#p)"/>'
    pdf = render(svg(body, height=200))
    assert near(pixel(pdf, 50, 30), RED)
    assert near(pixel(pdf, 50, 105), RED)
    assert near(pixel(pdf, 15, 30), WHITE)


def test_user_space_pattern_starts_at_the_user_origin() -> None:
    # The tiles start at x=0 of the user space, not at the box of the shape: 50 to 100 is white
    body = '<defs><pattern id="p" patternUnits="userSpaceOnUse" width="100" height="100"><rect width="50" height="100" fill="red"/></pattern></defs><rect x="50" width="150" height="100" fill="url(#p)"/>'
    pdf = render(svg(body))
    assert near(pixel(pdf, 45, 30), WHITE)
    assert near(pixel(pdf, 80, 30), RED)


def test_pattern_transform_applies_to_the_tile_origin() -> None:
    # The box origin x=50 lies in pattern space: scale(2) moves the tiles to 100, 200 and so on
    body = '<defs><pattern id="p" width="0.5" height="1" patternContentUnits="userSpaceOnUse" patternTransform="scale(2)"><rect width="25" height="100" fill="red"/></pattern></defs><rect x="50" width="100" height="50" fill="url(#p)"/>'
    pdf = render(svg(body, width=400))
    assert near(pixel(pdf, 60, 15), WHITE)
    assert near(pixel(pdf, 80, 15), RED)


def test_pattern_on_a_shape_without_box() -> None:
    body = '<defs><pattern id="p" x="0.1" width="1" height="1"><rect width="10" height="10" fill="red"/></pattern></defs><g fill="url(#p)"><path d=""/></g>'
    render(svg(body))


# ---------------- masks ----------------


def test_mask_is_set_before_the_path() -> None:
    body = '<defs><mask id="m"><rect width="100" height="100" fill="white"/></mask></defs><rect width="200" height="100" fill="red" mask="url(#m)"/>'
    pdf = render(svg(body))
    # The form of the SVG draws the rect
    drawing = next(stream for stream in streams(pdf) if "0 0 200 100 re\nf" in stream)
    # The soft mask comes first, then the path: no path construction between them
    assert re.search(r"/s\d+ gs\n(?:(?!.* re\n).*\n)*?0 0 200 100 re\nf", drawing)
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 120, 30), WHITE)


def test_mask_on_a_group_and_content_units() -> None:
    body = '<defs><mask id="m" maskContentUnits="objectBoundingBox"><rect width="0.5" height="1" fill="white"/></mask></defs><g mask="url(#m)"><rect width="200" height="100" fill="red"/></g>'
    pdf = render(svg(body))
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 120, 30), WHITE)


def test_mask_in_user_space() -> None:
    body = '<defs><mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="50" height="100"><rect width="200" height="100" fill="white"/></mask></defs><rect width="200" height="100" fill="red" mask="url(#m)"/>'
    pdf = render(svg(body))
    assert near(pixel(pdf, 20, 30), RED)
    assert near(pixel(pdf, 60, 30), WHITE)


def test_mask_that_references_itself() -> None:
    body = '<defs><mask id="m"><rect width="100" height="100" fill="white" mask="url(#m)"/></mask></defs><rect width="200" height="100" fill="red" mask="url(#m)"/>'
    pdf = render(svg(body))
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 120, 30), WHITE)


@pytest.mark.parametrize("cycle", [False, True])
def test_mask_attribute_on_a_mask_is_ignored(cycle: bool) -> None:
    # Chromium ignores mask on a <mask>: the black half of b would hide the whole left half otherwise
    other = ' mask="url(#a)"' if cycle else ""
    defs = f'<mask id="a" mask="url(#b)"><rect width="200" height="100" fill="white"/></mask><mask id="b"{other}><rect width="100" height="100" fill="black"/></mask>'
    pdf = render(svg(f'<defs>{defs}</defs><rect width="200" height="100" fill="red" mask="url(#a)"/>'))
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 120, 30), RED)


# ---------------- gradient opacity in a portable PDF ----------------


def linear(*stops: tuple[float, float]) -> dict[str, Any]:
    """The opacity of stops at their offsets as WeasyPrint writes it: a stitching function of linear pieces."""
    functions = [{"FunctionType": 2, "C0": [a0], "C1": [a1]} for (_, a0), (_, a1) in zip(stops, stops[1:], strict=False)]
    return {"FunctionType": 3, "Bounds": [offset for offset, _ in stops[1:-1]], "Encode": [0, 1] * len(functions), "Functions": functions}


def test_levels_of_a_rising_opacity_nest() -> None:
    found = paint.levels(linear((0, 0.0), (1, 1.0)), (0, 1), False)
    assert len(found) == 64
    # Each level starts later and reaches the end: one inside the next
    starts = [intervals[0][0] for _, intervals in found]
    assert starts == sorted(starts)
    assert all(intervals == [(intervals[0][0], 1)] for _, intervals in found)


def test_levels_of_a_peak_are_one_interval_each() -> None:
    found = paint.levels(linear((0, 0.0), (0.5, 1.0), (1, 0.0)), (0, 1), False)
    assert all(len(intervals) == 1 for _, intervals in found)
    # Symmetric around the peak
    assert all(low == pytest.approx(1 - high) for _, [(low, high)] in found)


def test_levels_of_a_valley_split_in_two() -> None:
    found = paint.levels(linear((0, 1.0), (0.5, 0.0), (1, 1.0)), (0, 1), True)
    # Above the valley floor a level holds both sides, open at either end
    low, high = found[-1][1]
    assert low[0] == -math.inf
    assert high[1] == math.inf


def test_levels_skip_a_clear_piece() -> None:
    # Clear up to the middle, then rising: no level reaches into the clear half
    found = paint.levels(linear((0, 0.0), (0.5, 0.0), (1, 1.0)), (0, 1), True)
    assert all(low >= 0.5 and high == math.inf for _, [(low, high)] in found)


def test_levels_of_one_opacity_are_one_coat() -> None:
    found = paint.levels(linear((0, 0.4), (1, 0.4)), (0, 1), True)
    assert len(found) == 1
    opacity, intervals = found[0]
    assert opacity == pytest.approx(0.4)
    assert intervals == [(-math.inf, math.inf)]


def test_levels_of_no_opacity() -> None:
    assert paint.levels(linear((0, 0.0), (1, 0.0)), (0, 1), False) == []
    assert paint.levels({"FunctionType": 2, "C0": [0.0], "C1": [0.0]}, (0, 1), False) == []


SQUARE = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]


def test_reach_of_an_axis_of_no_length() -> None:
    assert paint._reach(2, [0.5, 0.5, 0.5, 0.5], SQUARE) is None


def test_reach_of_an_axis_covers_the_corners() -> None:
    low, high, half_width = cast("tuple[float, float, float]", paint._reach(2, [0.25, 0.0, 0.75, 0.0], SQUARE))
    # The corners project on -0.5 and 1.5 of the axis, and lie 1 from it at most; a margin on each
    assert (low, high) == (-1.5, 2.5)
    assert half_width >= 1


def test_reach_of_circles_that_never_hold_a_corner() -> None:
    # The focal point lies on the end circle: the circles grow as fast as they move, away from a point behind them
    assert paint._reach(3, [0.0, 0.0, 0.0, 1.0, 0.0, 1.0], [(-1.0, 0.0)]) is None
    assert paint._reach(3, [0.0, 0.0, 0.0, 1.0, 0.0, 1.0], [(2.0, 0.0)]) == (-math.inf, 2.0, 0.0)
    assert paint._reach(3, [0.0, 0.0, 0.0, 1.0, 0.0, 1.0], [(0.5, 0.0)]) == (-math.inf, 2.0, 0.0)
    # The end circle does not hold the focal one
    assert paint._reach(3, [0.0, 0.0, 0.5, 2.0, 0.0, 0.6], SQUARE) is None


def test_reach_of_circles_that_move_away_from_a_corner() -> None:
    # The focal point near the left edge: the near corners wait for circles far larger than the end one
    _, high, _ = cast("tuple[float, float, float]", paint._reach(3, [0.001, 0.5, 0.0, 0.5, 0.5, 0.5], SQUARE))
    assert high > 11


@pytest.mark.parametrize(
    "gradient",
    [
        '<linearGradient id="g"><stop stop-color="red"/><stop offset="1" stop-color="blue" stop-opacity="0.2"/></linearGradient>',
        '<linearGradient id="g" x2="0" y2="1"><stop stop-color="red" stop-opacity="0"/><stop offset="0.5" stop-color="green"/><stop offset="1" stop-color="blue" stop-opacity="0"/></linearGradient>',
        '<linearGradient id="g" gradientTransform="rotate(30)"><stop stop-color="red" stop-opacity="0.8"/><stop offset="1" stop-color="blue" stop-opacity="0.1"/></linearGradient>',
        '<linearGradient id="g" x2="0.3" spreadMethod="reflect"><stop stop-color="red"/><stop offset="1" stop-color="blue" stop-opacity="0.3"/></linearGradient>',
        '<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="50" x2="150"><stop stop-color="red"/><stop offset="1" stop-color="blue" stop-opacity="0"/></linearGradient>',
        '<radialGradient id="g"><stop stop-color="red"/><stop offset="1" stop-color="blue" stop-opacity="0.1"/></radialGradient>',
        '<radialGradient id="g" fx="0.4" fy="0.45" r="0.6"><stop stop-color="yellow" stop-opacity="0.2"/><stop offset="0.7" stop-color="red"/><stop offset="1" stop-color="blue" stop-opacity="0.5"/></radialGradient>',
        '<radialGradient id="g" fr="0.2"><stop stop-color="red" stop-opacity="0.5"/><stop offset="1" stop-color="blue" stop-opacity="0"/></radialGradient>',
        # The focal point near an edge: the circles move away from the near corners, which they reach late
        '<radialGradient id="g" fx="0.001" fy="0.5"><stop stop-color="red" stop-opacity="0.5"/><stop offset="1" stop-color="blue" stop-opacity="0.5"/></radialGradient>',
        # Opaque stops faded by the fill opacity: one coat
        '<linearGradient id="g"><stop stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient>',
    ],
)
def test_portable_gradient_opacity_has_no_soft_mask_and_matches(gradient: str) -> None:
    body = f'<defs>{gradient}</defs><rect x="10" y="10" width="180" height="80" fill="url(#g)" fill-opacity="0.7"/><rect x="20" y="40" width="160" height="20" fill="none" stroke="url(#g)" stroke-width="8"/>'
    soft, flat = render(svg(body)), portable_render(body)
    assert "/SMask" in soft.decode("latin-1")
    assert "/SMask" not in flat.decode("latin-1")
    difference = ImageChops.difference(rasterize(soft, 2), rasterize(flat, 2))
    # Within a step of 1/64 of the opacity, and the edges of the levels
    assert max(ImageStat.Stat(difference).mean) < 3
    assert max(high for _, high in cast("list[tuple[int, int]]", difference.getextrema())) < 24


def test_portable_gradient_that_repeats() -> None:
    # The opacity jumps between two cycles: the pixel across the jump takes the color of one side, a line of one
    # pixel the soft mask does not have. The rest matches
    gradient = '<linearGradient id="g" x2="0.3" spreadMethod="repeat"><stop stop-color="red"/><stop offset="1" stop-color="blue" stop-opacity="0.3"/></linearGradient>'
    body = f'<defs>{gradient}</defs><rect x="10" y="10" width="180" height="80" fill="url(#g)"/>'
    soft, flat = render(svg(body)), portable_render(body)
    assert "/SMask" not in flat.decode("latin-1")
    assert max(ImageStat.Stat(ImageChops.difference(rasterize(soft, 2), rasterize(flat, 2))).mean) < 3


def test_portable_gradient_of_circles_outside_each_other_keeps_the_mask() -> None:
    # The focal circle sticks out of the end circle: no circle holds the one before, a band has no ring
    gradient = '<radialGradient id="g" fx="0.05" fy="0.5" fr="0.2" r="0.3"><stop stop-color="red"/><stop offset="1" stop-color="blue" stop-opacity="0.2"/></radialGradient>'
    flat = portable_render(f'<defs>{gradient}</defs><rect x="10" y="10" width="180" height="80" fill="url(#g)"/>')
    assert "/SMask" in flat.decode("latin-1")


def test_portable_gradient_opacity_without_portable_keeps_the_mask() -> None:
    gradient = '<linearGradient id="g"><stop stop-color="red"/><stop offset="1" stop-color="blue" stop-opacity="0.2"/></linearGradient>'
    assert "/SMask" in render(svg(f'<defs>{gradient}</defs><rect width="200" height="100" fill="url(#g)"/>')).decode("latin-1")


# ---------------- binary masks in a portable PDF ----------------

# A red rect of the whole SVG, cut by a mask. Pixels at 72 dpi: x 30 is 40 px, x 75 is 100 px, x 135 is 180 px
KNOCKOUT = (
    '<defs><mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="200" height="100">'
    '<rect width="200" height="100" fill="white"/><rect x="80" y="20" width="40" height="60" fill="black"/></mask></defs>'
    '<rect width="200" height="100" fill="red" mask="url(#m)"/>'
)


def portable_render(body: str) -> bytes:
    with weasysvg.portable():
        return render(svg(body))


def test_portable_binary_mask_is_a_clip() -> None:
    pdf = portable_render(KNOCKOUT)
    assert "/SMask" not in pdf.decode("latin-1")
    assert "h\nW*\nn" in content(pdf)
    assert near(pixel(pdf, 30, 37), RED)
    assert near(pixel(pdf, 75, 37), WHITE)
    assert near(pixel(pdf, 135, 37), RED)


def test_portable_mask_matches_the_soft_mask() -> None:
    soft, clipped = render(svg(KNOCKOUT)), portable_render(KNOCKOUT)
    assert "/SMask" in soft.decode("latin-1")
    for x, y in ((30, 37), (75, 37), (75, 10), (135, 37)):
        assert pixel(soft, x, y) == pixel(clipped, x, y)


def test_portable_resets_after_the_block() -> None:
    portable_render(KNOCKOUT)
    assert "/SMask" in render(svg(KNOCKOUT)).decode("latin-1")


@pytest.mark.parametrize(
    ("shapes", "inside", "outside"),
    [
        # A black circle around 100, 50 px
        ('<rect width="200" height="100" fill="white"/><circle cx="100" cy="50" r="30" fill="#000"/>', (30, 37), (75, 37)),
        ('<rect width="200" height="100" fill="white"/><ellipse cx="100" cy="50" rx="30" ry="20" fill="rgb(0,0,0)"/>', (30, 37), (75, 37)),
        # The union of two white areas, the gap between them hidden
        ('<rect width="60" height="100" fill="white"/><rect x="140" width="60" height="100" fill="#fff"/>', (135, 37), (75, 37)),
        # A white circle alone
        ('<circle cx="100" cy="50" r="30" fill="white"/>', (75, 37), (30, 37)),
        # currentColor is the color it stands for
        ('<rect width="200" height="100" fill="currentColor" color="white"/><rect x="80" width="40" height="100" fill="currentColor"/>', (30, 37), (75, 37)),
    ],
)
def test_portable_binary_shapes(shapes: str, inside: tuple[int, int], outside: tuple[int, int]) -> None:
    body = f'<defs><mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="200" height="100">{shapes}</mask></defs><rect width="200" height="100" fill="red" mask="url(#m)"/>'
    pdf = portable_render(body)
    assert "/SMask" not in pdf.decode("latin-1")
    assert near(pixel(pdf, *inside), RED)
    assert near(pixel(pdf, *outside), WHITE)


def test_portable_mask_in_bounding_box_units() -> None:
    mask = '<mask id="m" maskContentUnits="objectBoundingBox"><rect width="1" height="1" fill="white"/><rect x="0.4" width="0.2" height="1" fill="black"/></mask>'
    pdf = portable_render(f'<defs>{mask}</defs><g mask="url(#m)"><rect width="200" height="100" fill="red"/></g>')
    assert "/SMask" not in pdf.decode("latin-1")
    assert near(pixel(pdf, 30, 37), RED)
    assert near(pixel(pdf, 75, 37), WHITE)
    assert near(pixel(pdf, 135, 37), RED)


@pytest.mark.parametrize(
    "white",
    [
        '<rect width="0" height="100" fill="white"/>',
        '<circle cx="100" cy="50" r="0" fill="white"/>',
        "",
        '<rect width="200" height="100" fill="black"/>',
        # A rect without a size, black by default: the resvg test of an invalid child
        "<rect/>",
    ],
)
def test_portable_mask_without_white_area_hides_the_element(white: str) -> None:
    body = f'<defs><mask id="m">{white}</mask></defs><rect width="200" height="100" fill="red" mask="url(#m)"/>'
    pdf = portable_render(body)
    assert "/SMask" not in pdf.decode("latin-1")
    assert near(pixel(pdf, 75, 37), WHITE)


@pytest.mark.parametrize(
    "shapes",
    [
        '<rect width="200" height="100" fill="gray"/>',
        '<rect width="200" height="100" fill="white" fill-opacity="0.5"/>',
        '<rect width="200" height="100" fill="white" opacity="0.5"/>',
        '<rect width="200" height="100" fill="white" stroke="black"/>',
        '<rect width="200" height="100" fill="white" transform="scale(0.5)"/>',
        '<rect width="200" height="100" fill="white" rx="5"/>',
        '<rect width="200" height="100" fill="url(#g)"/>',
        '<rect width="200" height="100" fill="rgba(255,255,255,0.5)"/>',
        '<rect width="200" height="100" fill="white" display="none"/>',
        '<path d="M0 0H200V100H0Z" fill="white"/>',
        '<g><rect width="200" height="100" fill="white"/></g>',
        # White over black needs more than one clip
        '<rect width="200" height="100" fill="black"/><rect width="100" height="100" fill="white"/>',
        '<rect width="200" height="100" fill="white"/><rect width="10" height="10" fill="black"/><rect width="5" height="5" fill="white"/>',
    ],
)
def test_portable_keeps_the_soft_mask_of_other_masks(shapes: str) -> None:
    gradient = '<linearGradient id="g"><stop offset="0" stop-color="white"/><stop offset="1" stop-color="black"/></linearGradient>'
    body = f'<defs>{gradient}<mask id="m">{shapes}</mask></defs><rect width="200" height="100" fill="red" mask="url(#m)"/>'
    assert "/SMask" in portable_render(body).decode("latin-1")


def test_portable_bounding_box_units_keep_percentages_soft() -> None:
    mask = '<mask id="m" maskContentUnits="objectBoundingBox"><rect width="100%" height="1" fill="white"/></mask>'
    pdf = portable_render(f'<defs>{mask}</defs><rect width="200" height="100" fill="red" mask="url(#m)"/>')
    assert "/SMask" in pdf.decode("latin-1")


# ---------------- clip paths as one path ----------------

PATH_CLIPS = {
    # Tux and the Inkscape logo clip to the outline of a shape they draw elsewhere
    "use": '<path id="p" d="M20 10 C120 -20 220 40 120 90 L30 80 Z"/><clipPath id="c"><use href="#p"/></clipPath>',
    "use-moved": '<path id="p" d="M20 10 H90 V60 Z"/><clipPath id="c"><use href="#p" x="80" y="20"/></clipPath>',
    "use-of-a-group": '<g id="p"><rect x="10" y="10" width="60" height="60"/><circle cx="140" cy="50" r="30"/></g><clipPath id="c"><use href="#p"/></clipPath>',
    # Two shapes overlap and turn opposite ways: nonzero of both as written is a hole where they meet
    "opposite-turns": '<clipPath id="c"><use href="#a"/><path d="M60 10 V90 H150 V10 Z"/></clipPath><rect id="a" x="20" y="20" width="100" height="60"/>',
    "evenodd": '<clipPath id="c"><path d="M10 10H190V90H10Z M60 30H140V70H60Z" clip-rule="evenodd"/><rect x="90" y="40" width="80" height="50"/></clipPath>',
    # The same turns, nonzero: the inner square adds to the outer one, no hole
    "nonzero-same-turns": '<clipPath id="c"><path d="M10 10H190V90H10Z M60 30H140V70H60Z"/><rect x="2" y="40" width="6" height="20"/></clipPath>',
    # A hole as nonzero writes it, with a shape over part of it
    "nonzero-hole": '<clipPath id="c"><path d="M10 10H190V90H10Z M60 30V70H140V30Z"/><circle cx="60" cy="50" r="15"/></clipPath>',
    "nested-islands": '<clipPath id="c"><path d="M10 10H190V90H10Z M30 20V80H170V20Z M60 35H140V65H60Z" clip-rule="evenodd"/></clipPath>',
    "transformed": '<clipPath id="c" transform="rotate(10 100 50)"><rect x="30" y="20" width="60" height="50" transform="skewX(20)"/><polygon points="120,10 190,50 120,90"/></clipPath>',
    "bounding-box": '<clipPath id="c" clipPathUnits="objectBoundingBox"><circle cx="0.5" cy="0.5" r="0.4"/><rect width="0.2" height="0.2"/></clipPath>',
    "curves": '<clipPath id="c"><ellipse cx="70" cy="50" rx="60" ry="35"/><path d="M100 50 Q150 -20 190 50 T100 50" clip-rule="evenodd"/></clipPath>',
}


@pytest.mark.parametrize("name", PATH_CLIPS)
def test_clip_is_one_path_and_matches_its_mask(name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    body = f'<defs>{PATH_CLIPS[name]}</defs><g clip-path="url(#c)"><rect width="200" height="100" fill="red"/><rect x="40" width="40" height="100" fill="blue" opacity="0.5"/></g>'
    flat = render(svg(body))
    assert "/SMask" not in flat.decode("latin-1")
    monkeypatch.setattr(paint, "_clip_as_path", lambda *_: False)
    soft = render(svg(body))
    assert "/SMask" in soft.decode("latin-1")
    difference = ImageChops.difference(rasterize(soft, 2), rasterize(flat, 2))
    assert max(ImageStat.Stat(difference).mean) < 0.5
    assert max(high for _, high in cast("list[tuple[int, int]]", difference.getextrema())) < 64


@pytest.mark.parametrize(
    "clip",
    [
        '<clipPath id="c"><rect width="0" height="100"/></clipPath>',
        '<clipPath id="c"><use href="#nowhere"/><rect width="10" height="100" display="none"/></clipPath>',
        '<clipPath id="c" clipPathUnits="objectBoundingBox"><use href="#nowhere"/></clipPath>',
    ],
)
def test_clip_of_nothing_hides_the_element(clip: str) -> None:
    pdf = render(svg(f'<defs>{clip}</defs><rect x="10" y="10" width="180" height="80" fill="red" clip-path="url(#c)"/>'))
    assert "/SMask" not in pdf.decode("latin-1")
    assert near(pixel(pdf, 75, 37), WHITE)


def test_clip_in_box_units_without_a_box_hides_the_element() -> None:
    clip = '<clipPath id="c" clipPathUnits="objectBoundingBox"><circle cx="0.5" cy="0.5" r="0.5"/></clipPath>'
    pdf = render(svg(f'<defs>{clip}</defs><g clip-path="url(#c)"/><g clip-path="url(#c)"><rect width="0" height="10"/></g>'))
    assert "/SMask" not in pdf.decode("latin-1")


@pytest.mark.parametrize(
    "clip",
    [
        '<clipPath id="c"><text x="10" y="80" font-size="80">II</text></clipPath>',
        # A child clipped by a clip of its own: the union of two intersections
        '<clipPath id="c"><rect width="100" height="100" clip-path="url(#d)"/><use href="#r"/></clipPath><clipPath id="d"><circle cx="50" cy="50" r="40"/></clipPath>',
        # A star crosses itself
        '<clipPath id="c"><path d="M100 5 L130 95 L50 35 H150 L70 95 Z"/><use href="#r"/></clipPath>',
        # A symbol clips to its viewport
        '<symbol id="s" viewBox="0 0 10 10"><rect width="10" height="10"/></symbol><clipPath id="c"><use href="#s" width="50" height="50"/><use href="#r"/></clipPath>',
        '<clipPath id="c"><image width="50" height="50" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22/%3E"/><use href="#r"/></clipPath>',
    ],
)
def test_other_clips_keep_the_soft_mask(clip: str) -> None:
    body = f'<defs><rect id="r" x="150" width="50" height="50"/>{clip}</defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/>'
    assert "/SMask" in render(svg(body)).decode("latin-1")


def test_clip_children_that_turn_opposite_ways_unite() -> None:
    # Chromium fills the union of the children; WeasyPrint added both to one nonzero path, a hole where they meet
    clip = '<clipPath id="c"><rect x="20" y="20" width="100" height="60"/><path d="M60 10 V90 H150 V10 Z"/></clipPath>'
    pdf = render(svg(f'<defs>{clip}</defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/>'))
    assert near(pixel(pdf, 67, 37), RED)
    assert near(pixel(pdf, 30, 37), RED)
    assert near(pixel(pdf, 120, 37), WHITE)


# ---------------- clip paths ----------------


def test_clip_rule_evenodd_leaves_a_hole() -> None:
    clip = '<clipPath id="c"><path d="M0 0H200V100H0Z M50 25H150V75H50Z" clip-rule="evenodd"/></clipPath>'
    pdf = render(svg(f'<defs>{clip}</defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/>'))
    assert near(pixel(pdf, 15, 10), RED)
    assert near(pixel(pdf, 75, 37), WHITE)


def test_clip_children_keep_their_own_clip_paths() -> None:
    clip = '<clipPath id="c"><rect width="50" height="50"/><rect x="100" width="100" height="100" clip-path="url(#d)"/></clipPath><clipPath id="d"><circle cx="150" cy="50" r="30"/></clipPath>'
    pdf = render(svg(f'<defs>{clip}</defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/>'))
    assert near(pixel(pdf, 15, 15), RED)
    assert near(pixel(pdf, 112, 37), RED)
    assert near(pixel(pdf, 80, 5), WHITE)
    assert near(pixel(pdf, 60, 60), WHITE)


def test_clip_ignores_opacity_and_paint_of_its_content() -> None:
    clip = '<clipPath id="c"><use href="#r" style="opacity:.25;fill:none"/></clipPath>'
    defs = f'<rect id="r" width="100" height="100" fill="none"/>{clip}'
    pdf = render(svg(f'<defs>{defs}</defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/>'))
    assert near(pixel(pdf, 30, 30), RED, 5)
    assert near(pixel(pdf, 120, 30), WHITE)


@pytest.mark.parametrize("complex_clip", ["", "<text>x</text>"])
def test_clip_cycles_are_ignored(complex_clip: str) -> None:
    # Chromium ignores the reference that closes a cycle; WeasyPrint recursed until the SVG was lost
    clips = (
        f'<clipPath id="c"><rect width="50" height="50" clip-path="url(#c)"/>{complex_clip}</clipPath>'
        '<clipPath id="d"><rect x="100" width="50" height="100" clip-path="url(#e)"/></clipPath>'
        '<clipPath id="e"><rect x="100" width="100" height="50" clip-path="url(#d)"/></clipPath>'
        '<clipPath id="f" clip-path="url(#f)"><rect y="60" width="50" height="40"/></clipPath>'
    )
    body = f'<defs>{clips}</defs><rect width="100" height="100" fill="red" clip-path="url(#c)"/><rect x="100" width="100" height="100" fill="red" clip-path="url(#d)"/><rect width="100" height="100" fill="red" clip-path="url(#f)"/>'
    pdf = render(svg(body))
    assert near(pixel(pdf, 15, 15), RED)
    assert near(pixel(pdf, 85, 15), RED)
    assert near(pixel(pdf, 85, 60), WHITE)
    assert near(pixel(pdf, 15, 60), RED)
    assert near(pixel(pdf, 60, 30), WHITE)


@pytest.mark.parametrize("complex_clip", ["", "<text>x</text>"])
def test_a_clip_reused_by_children_is_no_cycle(complex_clip: str) -> None:
    # The left half of each box: the group keeps 0..100, the children 0..50 and 100..150, so 50..200 is empty
    clip = f'<clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/>{complex_clip}</clipPath>'
    body = f'<defs>{clip}</defs><g clip-path="url(#c)"><rect width="100" height="100" fill="red" clip-path="url(#c)"/><rect x="100" width="100" height="100" fill="red" clip-path="url(#c)"/></g>'
    pdf = render(svg(body))
    assert near(pixel(pdf, 15, 30), RED)
    assert near(pixel(pdf, 56, 30), WHITE)


def test_missing_and_foreign_clip_references() -> None:
    references = ("url(#m)", "url(#nowhere)", "inset(1px)")
    body = "<defs><mask id='m'/></defs>" + "".join(f'<rect x="{20 * i}" width="10" height="10" fill="red" clip-path="{value}"/>' for i, value in enumerate(references))
    render(svg(body))


def test_complex_clip_in_bounding_box_units_without_a_box() -> None:
    clip = '<clipPath id="c" clipPathUnits="objectBoundingBox"><text>x</text></clipPath>'
    render(svg(f'<defs>{clip}</defs><g clip-path="url(#c)"/>'))


@pytest.mark.parametrize("shape", ['<g clip-path="url(#c)"><rect width="200" height="100" fill="red"/></g>', '<circle cx="100" cy="50" r="50" fill="red" clip-path="url(#c)"/>'])
def test_bounding_box_clip_on_any_element(shape: str) -> None:
    # The left half of the box, for a group or a circle as for a rect
    pdf = render(svg(f'<defs><clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/></clipPath></defs>{shape}'))
    assert near(pixel(pdf, 56, 30), RED)
    assert near(pixel(pdf, 90, 30), WHITE)


def test_text_in_a_clip_path_clips() -> None:
    clip = '<clipPath id="c"><text x="10" y="80" font-size="80" font-weight="bold">II</text></clipPath>'
    pdf = render(svg(f'<defs>{clip}</defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/>'))
    colors = {pixel(pdf, x, 40) for x in range(0, 150, 2)}
    assert any(near(color, RED) for color in colors)
    assert not any(near(color, (0, 0, 0), 60) for color in colors)


def test_complex_clip_in_bounding_box_units_with_a_mask() -> None:
    clip = '<clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/><text y="1" font-size="0.5">x</text></clipPath>'
    mask = '<mask id="m"><rect width="200" height="50" fill="white"/></mask>'
    pdf = render(svg(f'<defs>{clip}{mask}</defs><rect x="100" width="100" height="100" fill="red" clip-path="url(#c)" mask="url(#m)"/>'))
    assert near(pixel(pdf, 80, 15), RED)
    assert near(pixel(pdf, 130, 15), WHITE)
    assert near(pixel(pdf, 80, 60), WHITE)


def test_mask_on_an_empty_group_is_skipped() -> None:
    body = (
        '<defs><mask id="m"><rect width="1" height="1" fill="white"/></mask><mask id="c" maskContentUnits="objectBoundingBox"><rect width="1" height="1"/></mask></defs>'
        '<g mask="url(#m)"/><g mask="url(#c)"/><rect width="10" height="10" mask="url(#missing)"/>'
    )
    render(svg(body))


def test_mask_tag_is_restored_after_drawing() -> None:
    body = '<mask id="m"><rect width="100" height="100" fill="white"/></mask><rect width="200" height="100" fill="red" mask="url(#m)"/>'
    pdf = render(svg(body))
    # The <mask> outside <defs> is not drawn as a group of its own
    assert near(pixel(pdf, 120, 30), WHITE)


# ---------------- blending and opacity ----------------


def test_blend_mode_is_an_isolated_group() -> None:
    body = '<rect width="200" height="100" fill="yellow"/><g style="mix-blend-mode:multiply"><rect width="100" height="100" fill="cyan"/><rect width="50" height="100" fill="cyan"/></g>'
    pdf = render(svg(body))
    assert "/BM /Multiply" in pdf.decode("latin-1")
    assert near(pixel(pdf, 20, 30), (0, 255, 0))


def test_blend_mode_values() -> None:
    node = type("Node", (), {"get": {"mix-blend-mode": " Screen "}.get})()
    assert paint.blend_mode(node) == "Screen"
    assert paint.blend_mode(type("Node", (), {"get": {"mix-blend-mode": "normal"}.get})()) is None


def test_blend_mode_is_not_inherited() -> None:
    body = '<g style="mix-blend-mode:screen"><g><rect width="10" height="10"/></g></g>'
    pdf = render(svg(body))
    assert pdf.decode("latin-1").count("/BM /Screen") == 1


def test_opacity_group_is_unbounded() -> None:
    body = '<g opacity="0.5"><text x="100" y="50" text-anchor="end" font-size="30">Shifted</text></g>'
    pdf = render(svg(body))
    assert "/A0.5 gs" in content(pdf) or "/a0.5 gs" in content(pdf)
    assert "/BBox [-10000 -10000 10000 10000]" in pdf.decode("latin-1")


def test_transform_with_mask_and_opacity() -> None:
    body = (
        '<defs><mask id="m"><rect width="50" height="100" fill="white"/></mask></defs>'
        '<rect transform="translate(100 0)" width="100" height="100" fill="red" mask="url(#m)"/>'
        '<rect transform="translate(0 0)" width="50" height="100" fill="red" opacity="0.5"/>'
    )
    pdf = render(svg(body))
    assert near(pixel(pdf, 80, 30), RED)
    assert near(pixel(pdf, 130, 30), WHITE)
    assert near(pixel(pdf, 20, 30), (255, 128, 128))


def test_mask_with_transform_and_content_units_on_an_empty_group() -> None:
    body = (
        '<defs><mask id="m" maskContentUnits="objectBoundingBox" transform="translate(0 0)"><rect width="0.5" height="1" fill="white"/></mask>'
        '<mask id="e" maskUnits="userSpaceOnUse" maskContentUnits="objectBoundingBox"><rect width="1" height="1" fill="white"/></mask></defs>'
        '<rect width="200" height="100" fill="red" mask="url(#m)"/><g mask="url(#e)"/>'
    )
    pdf = render(svg(body))
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 120, 30), WHITE)


def test_radial_gradient_with_default_and_absolute_radius() -> None:
    body = (
        '<defs><radialGradient id="a"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="white"/></radialGradient>'
        '<radialGradient id="b" r="0.4"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="white"/></radialGradient></defs>'
        '<rect width="100" height="100" fill="url(#a)"/><rect x="100" width="100" height="100" fill="url(#b)"/>'
    )
    pdf = render(svg(body))
    assert near(pixel(pdf, 37, 37), RED, 60)
    assert near(pixel(pdf, 112, 37), RED, 60)


def test_pattern_override_nests() -> None:
    class Stream:
        def add_pattern(self) -> str:
            return "class"

    stream = Stream()
    with paint._add_pattern_override(stream, lambda: "outer"):
        with paint._add_pattern_override(stream, lambda: "inner"):
            assert stream.add_pattern() == "inner"
        assert stream.add_pattern() == "outer"
    assert stream.add_pattern() == "class"
    assert "add_pattern" not in stream.__dict__


# ---------------- state across threads and exceptions ----------------


class FakeMask:
    def __init__(self) -> None:
        self.attrib = {"maskUnits": "userSpaceOnUse", "x": "0", "y": "0", "width": "10", "height": "10"}
        self._etree_node = SimpleNamespace(tag="mask")

    def get(self, name: str, default: Any = None) -> Any:
        return self.attrib.get(name, default)


def mask_svg(draw: Any) -> Any:
    return SimpleNamespace(inner_width=10, inner_height=10, stream=RecordingStream(), draw_node=draw)


def test_a_mask_drawn_in_another_thread_is_not_a_cycle() -> None:
    # weasyprint-service renders in a thread pool: one rendering's open masks must not block another's
    mask = FakeMask()
    inner_draws: list[Any] = []

    def outer_draw(*_args: Any) -> None:
        worker = threading.Thread(target=paint.paint_mask, args=(mask_svg(lambda *a: inner_draws.append(a)), object(), mask, 1))
        worker.start()
        worker.join()

    paint.paint_mask(mask_svg(outer_draw), object(), mask, 1)
    assert len(inner_draws) == 1


def test_a_failing_mask_draw_restores_the_mask() -> None:
    mask = FakeMask()
    mask.attrib["maskContentUnits"] = "objectBoundingBox"

    def failing(*_args: Any) -> None:
        raise RuntimeError("draw failed")

    svg_failing = mask_svg(failing)
    svg_failing.calculate_bounding_box = lambda *_args, **_kwargs: (0, 0, 10, 10)
    with pytest.raises(RuntimeError):
        paint.paint_mask(svg_failing, object(), mask, 1)
    assert "transform" not in mask.attrib
    assert mask._etree_node.tag == "mask"
    drawn: list[Any] = []
    svg_drawing = mask_svg(lambda *a: drawn.append(a))
    svg_drawing.calculate_bounding_box = svg_failing.calculate_bounding_box
    paint.paint_mask(svg_drawing, object(), mask, 1)
    assert len(drawn) == 1


def test_a_failing_pattern_keeps_its_origin() -> None:
    # The shared pattern node must get x and y back even when its geometry raises
    pattern = SimpleNamespace(attrib={"x": "5", "y": "5", "patternUnits": "userSpaceOnUse"}, _etree_node=SimpleNamespace(tag="pattern"))
    pattern.get = pattern.attrib.get

    def failing(*_args: Any) -> Any:
        raise ValueError("bad length")

    fake = SimpleNamespace(point=failing, stream=RecordingStream())
    with pytest.raises(ValueError, match="bad length"):
        paint.draw_pattern(fake, object(), pattern, 12, 1, False)
    assert pattern.attrib == {"x": "5", "y": "5", "patternUnits": "userSpaceOnUse"}


@pytest.mark.parametrize("attribute", ['opacity="0.5"', 'style="mix-blend-mode:multiply"'])
def test_groups_reach_far_coordinates(attribute: str) -> None:
    # Map and CAD exports draw far from the origin: the opacity and blend groups must not clip them
    body = f'<rect x="50010" y="10" width="80" height="80" fill="red" {attribute}/>'
    pdf = render(f'<svg xmlns="{SVG_NS}" width="200" height="100" viewBox="50000 0 200 100">{body}</svg>')
    red, green, blue = pixel(pdf, 40, 40)
    assert red > 200
    assert green < 200
    assert blue < 200


def test_a_mask_on_an_empty_group_is_skipped(caplog: pytest.LogCaptureFixture) -> None:
    # An empty group has the box (inf, inf, 0, 0): an objectBoundingBox mask has no region there
    mask = '<mask id="m" maskContentUnits="objectBoundingBox"><rect width="1" height="1" fill="white"/></mask>'
    pdf = render(svg(f'<defs>{mask}</defs><g mask="url(#m)"/><rect x="10" y="10" width="40" height="40" fill="red"/>'))
    assert "Failed to render SVG image" not in caplog.text
    assert b"inf" not in pdf.lower().replace(b"/info", b"")
    assert near(pixel(pdf, 20, 20), RED)


def test_a_failing_restyler_puts_back_what_others_changed(monkeypatch: pytest.MonkeyPatch) -> None:
    from weasysvg import _core

    def first(_svg: Any, node: Any, _size: float) -> dict[str, str | None]:
        node.attrib["fill"] = "blue"
        return {"fill": "red"}

    def second(*_args: Any) -> None:
        raise RuntimeError("restyler failed")

    monkeypatch.setattr(_core, "_RESTYLERS", [first, second])
    node = SimpleNamespace(attrib={"fill": "red"}, get=lambda *_args: None, tag="rect")
    fake = SimpleNamespace(paths={}, font_config=None)
    with pytest.raises(RuntimeError):
        _core._draw_node(fake, node, 12)
    assert node.attrib == {"fill": "red"}
    assert _core._ACTIVE_CLIPS.get() == ()


def test_invalid_stop_opacity_counts_as_opaque() -> None:
    # WeasyPrint raised ValueError on it and lost the whole SVG; Chromium takes 1
    gradient = '<linearGradient id="g"><stop stop-color="red" stop-opacity="0"/><stop offset="0.01" stop-color="red" stop-opacity="abc"/><stop offset="1" stop-color="red" stop-opacity="abc"/></linearGradient>'
    pdf = render(svg(f'<defs>{gradient}</defs><rect width="200" height="100" fill="url(#g)"/><rect y="50" width="200" height="50" fill="url(#g)"/>'))
    assert near(pixel(pdf, 75, 30), RED)
    assert near(pixel(pdf, 75, 60), RED)


def test_blend_mode_with_a_complex_clip_blends_with_the_backdrop() -> None:
    # Blue multiplied over red is black; inside the isolated clip group it blended with nothing
    clip = '<clipPath id="c"><path d="M0 0H200V100H0Z" clip-rule="evenodd"/></clipPath>'
    body = f'<defs>{clip}</defs><rect width="200" height="100" fill="red"/><rect width="200" height="100" fill="blue" style="mix-blend-mode:multiply" clip-path="url(#c)"/>'
    assert near(pixel(render(svg(body)), 30, 30), (0, 0, 0), 20)


@pytest.mark.parametrize("fr", ["0.2", "20%"])
def test_a_concentric_focal_radius_leaves_no_hole(fr: str) -> None:
    # PDFium paints the center of a shading whose inner circle has a radius white
    gradient = f'<radialGradient id="g" fr="{fr}"><stop offset="0" stop-color="black"/><stop offset="1" stop-color="white"/></radialGradient>'
    pdf = render(svg(f'<defs>{gradient}</defs><rect x="20" y="20" width="160" height="160" fill="url(#g)"/>', height=200))
    coords = [[float(value) for value in found.split()] for found in re.findall(r"/Coords \[([^\]]*)\]", pdf.decode("latin-1"))]
    assert coords
    assert all(values[2] == 0 for values in coords)
    gray = rasterize(pdf, 96 / 72).convert("L")
    assert gray.getpixel((100, 100)) == 0
    # Black up to the focal radius, then the ramp to white at r
    assert cast(int, gray.getpixel((100 + 25, 100))) < 8
    assert 60 < cast(int, gray.getpixel((100 + 56, 100))) < 200


@pytest.mark.parametrize("attributes", ['fx="0.3"', 'fr="0.6"'])
def test_other_focal_circles_keep_their_radius(attributes: str) -> None:
    # An off-center focus, a repeated spread, or fr past r: the shading keeps its own circles
    extra = "" if "fr=" in attributes else ' fr="0.2"'
    gradient = f'<radialGradient id="g"{extra} {attributes}><stop offset="0" stop-color="black"/><stop offset="1" stop-color="white"/></radialGradient>'
    pdf = render(svg(f'<defs>{gradient}</defs><rect x="20" y="20" width="160" height="160" fill="url(#g)"/>', height=200))
    coords = [[float(value) for value in found.split()] for found in re.findall(r"/Coords \[([^\]]*)\]", pdf.decode("latin-1"))]
    assert any(values[2] != 0 for values in coords)


def test_a_repeated_radial_spread_keeps_its_focal_circle() -> None:
    attributes = {"spreadMethod": "reflect", "fr": "0.2"}
    gradient = SimpleNamespace(tag="radialGradient", get=lambda key, default=None: attributes.get(key, default))
    assert paint._focal_ring(gradient, 16, 1) is None


@pytest.mark.parametrize(
    ("shape", "first_curve"),
    [
        # 0.5523 = 4 (sqrt(2) - 1) / 3: a quarter of a circle in one Bezier, as Chromium draws it
        ('<circle cx="100" cy="50" r="40"/>', [140, 72.091, 122.091, 90, 100, 90]),
        ('<ellipse cx="100" cy="50" rx="40" ry="20"/>', [140, 61.046, 122.091, 70, 100, 70]),
    ],
)
def test_a_round_shape_has_the_length_of_its_arc(shape: str, first_curve: list[float]) -> None:
    # A wider control point makes the outline longer: dashes along it drift
    curves = re.findall(r"((?:-?[\d.]+ ){6})c\b", content(render(svg(shape))))
    assert [float(number) for number in curves[0].split()] == pytest.approx(first_curve, abs=0.01)


@pytest.mark.parametrize("shape", ['<circle cx="100" cy="50" r="0"/>', '<ellipse cx="100" cy="50" rx="40" ry="-5"/>', '<circle cx="100" cy="50"/>'])
def test_a_round_shape_without_a_radius_draws_nothing(shape: str) -> None:
    assert not re.search(r"\bc\b", content(render(svg(shape))))


def test_bounding_box_clip_on_text() -> None:
    # The box of a text is known once it is drawn: the clip keeps its left half, not nothing
    clip = '<clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/></clipPath>'
    pdf = render(svg(f'<defs>{clip}</defs><text x="10" y="70" font-size="60" font-weight="bold" fill="red" clip-path="url(#c)">HHHH</text>'))
    left = {pixel(pdf, x, 50) for x in range(10, 60)}
    right = {pixel(pdf, x, 50) for x in range(110, 180)}
    assert any(near(color, RED) for color in left)
    assert not any(near(color, RED) for color in right)


def test_bounding_box_mask_on_text() -> None:
    # maskContentUnits="objectBoundingBox": the left half of the box of the text shows
    mask = '<mask id="m" maskContentUnits="objectBoundingBox"><rect width="0.5" height="1" fill="white"/></mask>'
    pdf = render(svg(f'<defs>{mask}</defs><text x="10" y="70" font-size="60" font-weight="bold" fill="red" mask="url(#m)">HHHH</text>'))
    assert any(near(pixel(pdf, x, 50), RED) for x in range(10, 60))
    assert not any(near(pixel(pdf, x, 50), RED) for x in range(110, 180))


def test_the_scratch_drawing_of_a_text_leaves_nothing_in_the_pdf() -> None:
    # The text is drawn once to measure it: every form left in the PDF is drawn, or is a soft mask
    clip = '<clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/></clipPath>'
    pdf = render(svg(f'<defs>{clip}</defs><text x="100" y="70" font-size="60" text-anchor="middle" clip-path="url(#c)">HHHH</text>'))
    forms = len(re.findall(rb"/Subtype\s*/Form", pdf))
    drawn = len(re.findall(r"/x\d+ Do", content(pdf)))
    masks = len(re.findall(rb"/SMask\s*<<", pdf))
    assert forms == drawn + masks


def test_a_group_with_a_shape_and_text_clips_by_both() -> None:
    # The rect alone gives the group a box: the text must still be measured into it
    clip = '<clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/></clipPath>'
    group = '<g clip-path="url(#c)"><rect x="0" y="20" width="10" height="10" fill="blue"/><text x="60" y="70" font-size="60" font-weight="bold" fill="red">HHHH</text></g>'
    pdf = render(svg(f"<defs>{clip}</defs>{group}"))
    # pixel() reads pt: user units 64 to 88 lie left of the middle of the group, which spans 0 to about 230
    assert any(near(pixel(pdf, x, 37), RED) for x in range(48, 66))


def test_bounding_box_clip_on_a_link_in_text() -> None:
    # An <a> in a text is text too: its box is measured before its clip
    clip = '<clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/></clipPath>'
    pdf = render(svg(f'<defs>{clip}</defs><text x="10" y="70" font-size="60" font-weight="bold" fill="red"><a clip-path="url(#c)">HHHH</a></text>'))
    assert any(near(pixel(pdf, x, 37), RED) for x in range(10, 40))


def test_bounding_box_clip_on_a_link_around_a_shape() -> None:
    # An <a> around shapes has the box of its children, as a <g>
    clip = '<clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/></clipPath>'
    pdf = render(svg(f'<defs>{clip}</defs><a clip-path="url(#c)"><rect width="200" height="100" fill="red"/></a>'))
    assert near(pixel(pdf, 56, 30), RED)
    assert near(pixel(pdf, 90, 30), WHITE)


def test_a_link_with_text_and_a_shape_clips_by_both() -> None:
    # The box spans the "H" and the rect: its left half keeps the whole "H", not only its left half
    clip = '<clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/></clipPath>'
    link = '<a clip-path="url(#c)" font-size="60" font-weight="bold" fill="red">H<rect x="150" y="20" width="50" height="60"/></a>'
    pdf = render(svg(f'<defs>{clip}</defs><g transform="translate(10 70)">{link}</g>'))
    # pixel() reads pt: the right stem of the "H" lies at about 38 to 48 user units
    assert any(near(pixel(pdf, x, 37), RED) for x in range(30, 37))


def test_zero_length_dashes_keep_their_place_in_pdfium() -> None:
    # PDFium moves dashes of length 0 along the path, about 1 unit each 240: dots on the bottom edge,
    # drawn right to left from the corner at x=160, sit at 160, 120, 80 and 40
    style = 'fill="none" stroke="green" stroke-width="20" stroke-dasharray="0 40" stroke-linecap="round"'
    pdf = render(svg(f'<rect x="40" y="40" width="120" height="120" {style}/>', height=200))
    image = rasterize(pdf, 96 / 72).convert("RGB")
    row = [cast(tuple[int, int, int], image.getpixel((x, 160))) for x in range(200)]
    green = [x for x, (red, green, _) in enumerate(row) if green > 80 and red < 100]
    dots = [x for x in green if x - 1 not in green]
    assert dots == [30, 70, 110, 150]
    # The period stays 40
    assert re.search(r"\[0\.001 39\.999\] 0 d", content(pdf))


def test_zero_length_dashes_keep_a_negative_offset() -> None:
    # An offset of -10 starts 30 into the period of 40, as WeasyPrint computes it
    style = 'fill="none" stroke="green" stroke-width="2" stroke-dasharray="0 40" stroke-dashoffset="-10" stroke-linecap="round"'
    assert re.search(r"\[0\.001 39\.999\] 30 d", content(render(svg(f'<path d="M 0 50 H 200" {style}/>'))))


@pytest.mark.parametrize(
    ("dashes", "expected"),
    [
        ((0, 40), (0.001, 39.999)),
        # An odd array repeats: its 0 is a dash once and a gap once
        ((0, 10, 5), (0.00075, 9.99925, 5, 0, 10, 5)),
        # A gap of 0 stays, and so does a dash of 0 before it: there is no length to take
        ((40, 0), (40, 0)),
        ((0, 0, 0, 40), (0, 0, 0.001, 39.999)),
    ],
)
def test_no_zero_dashes(dashes: tuple[float, ...], expected: tuple[float, ...]) -> None:
    assert paint.no_zero_dashes(dashes) == pytest.approx(expected)


def test_zero_length_dashes_with_butt_caps_stay() -> None:
    # A dash of length 0 with butt caps paints nothing: no sliver may take its place
    style = 'fill="none" stroke="green" stroke-width="20" stroke-dasharray="0 40"'
    assert re.search(r"\[0 40\] 0 d", content(render(svg(f'<path d="M 0 50 H 200" {style}/>'))))


def test_a_zero_length_dash_grows_with_its_period() -> None:
    # In a viewBox of one unit drawn large, 0.001 units would show: the length follows the period
    assert paint.no_zero_dashes((0, 4)) == pytest.approx((0.0001, 3.9999))


@pytest.mark.parametrize(
    ("dashes", "cap", "expected"),
    [
        # An odd array repeats: its period is 30, and an offset of -5 starts 25 into it
        ("0 10 5", "round", r"\[0\.00075 9\.99925 5 0 10 5\] 25 d"),
        ("10 5 3", "butt", r"\[10 5 3 10 5 3\] 31 d"),
    ],
)
def test_a_negative_offset_of_an_odd_dash_array_uses_its_whole_period(dashes: str, cap: str, expected: str) -> None:
    style = f'fill="none" stroke="green" stroke-width="2" stroke-dasharray="{dashes}" stroke-dashoffset="-5" stroke-linecap="{cap}"'
    assert re.search(expected, content(render(svg(f'<path d="M 0 50 H 200" {style}/>'))))


def test_a_zero_length_dash_stays_short_against_its_stroke() -> None:
    # A long period on a thin stroke: the dot must stay a dot, not a dash of 2.5 units
    assert paint.no_zero_dashes((0, 100000), 1) == pytest.approx((0.001, 99999.999))


def test_a_zero_length_dash_stays_above_what_the_pdf_writes() -> None:
    # pydyf writes six decimals: a dash shorter than 0.000001 would be 0 in the PDF again
    style = 'fill="none" stroke="green" stroke-width="1" stroke-dasharray="0 0.01" stroke-linecap="round"'
    assert re.search(r"\[1e-05 0\.00999\] 0 d|\[0\.00001 0\.00999\] 0 d", content(render(svg(f'<path d="M 0 50 H 200" {style}/>'))))


def test_a_gradient_transform_through_href_applies_once() -> None:
    # The test of the resvg suite: one template used directly, through one href and through two, then
    # overridden by scale(1). The center of the gradient lies 3/4 across the first three squares, 1/2 across the last
    path = Path(__file__).resolve().parents[1] / "corpus" / "svg" / "resvg" / "paint-servers-radialGradient--gradientTransform-via-href.svg"
    image = rasterize(render(path.read_text(), 200), 4).convert("RGB")
    scale = 4 * 0.75

    def center(left: int, top: int) -> float:
        row = [(sum(cast(tuple[int, int, int], image.getpixel((int((left + x / 10) * scale), int((top + 35) * scale))))[:2]), x / 10) for x in range(700)]
        return max(row)[1] / 70

    assert [round(center(left, top), 2) for left, top in ((20, 20), (110, 20), (20, 110), (110, 110))] == [0.76, 0.76, 0.76, 0.5]


@pytest.mark.parametrize("arc", ["A 0 0 0 0 1 60 60", "a 0 0 0 0 1 0 40", "A 0 9 0 0 1 60 60"])
def test_an_arc_of_no_radius_is_a_line_to_its_end(arc: str) -> None:
    # WeasyPrint wrote it as a relative line to the absolute end: the triangle ran out to (120, 80).
    # Highcharts closes every slice of a pie with such an arc.
    pdf = render(svg(f'<path d="M 20 20 L 60 20 {arc} Z" fill="black"/>'))
    assert pixel(pdf, 50 * 3 // 4, 30 * 3 // 4) == (0, 0, 0)
    assert pixel(pdf, 100 * 3 // 4, 64 * 3 // 4) == (255, 255, 255)


@pytest.mark.parametrize("arc", ["A 100 100 0 0 1 250 150", "A 100 100 0 1 1 250 150", "a 100 100 0 0 1 200 0"])
def test_a_half_circle_arc_is_round(arc: str) -> None:
    # WeasyPrint drew an arc of up to 180 degrees as one Bezier curve: half a circle bulged by 1.8 % of
    # its radius at 45 degrees, the band of the flag of Brazil ran thicker at its ends
    image = rasterize(render(svg(f'<path d="M 50 150 {arc} Z" fill="black"/>', width=300, height=200)), 4).convert("L")
    scale = 3  # device pixels per CSS px at 4 x 72 dpi
    for degrees in (30, 45, 60, 120, 135, 150):
        angle = math.radians(degrees)
        inside = [r for r in range(80 * scale, 120 * scale) if cast("int", image.getpixel((round((150 - r / scale * math.cos(angle)) * scale), round((150 - r / scale * math.sin(angle)) * scale)))) < 128]
        assert abs(max(inside) / scale - 100) <= 0.5, degrees
