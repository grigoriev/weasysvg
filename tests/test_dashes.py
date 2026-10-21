"""The dash through the start point of a closed subpath: one dash, as Chromium draws it."""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from helpers import content, rasterize, render, svg
from PIL import Image, ImageChops
from weasyprint.svg.utils import size

from weasysvg import dashes, paint_order

CIRCLE = Path(__file__).resolve().parents[1] / "corpus" / "svg" / "resvg" / "painting-stroke-dasharray--odd-count.svg"
UNIT = 4  # pixels per user unit
SCALE = UNIT / 0.75
# A square from 40 to 160 with a stroke 20 wide. The outline is 480 long, 3 periods of 130 and 90: the
# last dash runs 90 into its period, through the corner at 40 40 where the outline starts
SQUARE = '<rect x="40" y="40" width="120" height="120" fill="none" stroke="green" stroke-width="20" stroke-dasharray="100 30" {}/>'


def _image(pdf: bytes) -> Image.Image:
    return rasterize(pdf, SCALE)


def _red(image: Image.Image, x: float, y: float) -> int:
    """The red channel at user units x, y: 0 on the green stroke, 255 on the white page."""
    return cast("tuple[int, int, int]", image.getpixel((round(x * UNIT), round(y * UNIT))))[0]


def _without_patches(monkeypatch: pytest.MonkeyPatch, document: str) -> bytes:
    with monkeypatch.context() as patched:
        patched.setitem(paint_order._ENABLED, "dashes", False)
        return render(document, 200)


def _patches(pdf: bytes) -> int:
    """The patches of the stroked path: the subpaths after its last closed one, before its S."""
    page = content(pdf)
    lines = page[: page.index("\nS\n")].rsplit(" d\n", 1)[1].splitlines()
    closing = max((index for index, line in enumerate(lines) if line == "h" or line.endswith(" re")), default=len(lines))
    return sum(line.endswith(" m") for line in lines[closing:])


def test_a_dash_through_the_start_of_a_circle_has_no_seam() -> None:
    # The circle starts at 170 100. Its dashes, 10 20 30 repeated, put the start point 9.8 into a dash of
    # 20: PDFium drew two dashes there, with a light seam across the stroke at y 100
    image = _image(render(CIRCLE.read_text(), 200))
    across = [_red(image, x / 4, 100) for x in range(166 * 4, 174 * 4 + 1)]
    assert max(across) <= 4


def test_the_patch_moves_no_dash(monkeypatch: pytest.MonkeyPatch) -> None:
    document = CIRCLE.read_text()
    patched, plain = _image(render(document, 200)), _image(_without_patches(monkeypatch, document))
    box = ImageChops.difference(patched, plain).getbbox()
    # Only the seam at the start point changes: the stroke spans 165 to 175, the patch 2.5 units around y 100
    assert box is not None
    left, top, right, bottom = box
    assert left >= 164 * UNIT and right <= 176 * UNIT
    assert top >= 97 * UNIT and bottom <= 103 * UNIT


@pytest.mark.parametrize("cap", ["butt", "round"])
def test_a_dash_through_a_corner_gets_its_join(monkeypatch: pytest.MonkeyPatch, cap: str) -> None:
    # Chromium draws one dash around the corner, with a miter: its tip at 30 30. Two butt ends leave the
    # corner square out, two round ends cut it round
    document = svg(SQUARE.format(f'stroke-linecap="{cap}"'), 200, 200)
    assert _red(_image(render(document, 200)), 31, 31) <= 4
    assert _red(_image(_without_patches(monkeypatch, document)), 31, 31) == 255


def test_square_caps_reach_over_the_start_point() -> None:
    pdf = render(svg(SQUARE.format('stroke-linecap="square"'), 200, 200), 200)
    assert _patches(pdf) == 0
    assert _red(_image(pdf), 31, 31) <= 4


@pytest.mark.parametrize(
    "dasharray",
    [
        # 480 is 12 periods of 40: the outline ends at the end of a gap
        "20 20",
        # No gap: a solid stroke
        "100 0",
    ],
)
def test_no_patch_without_a_dash_through_the_start_point(dasharray: str) -> None:
    pdf = render(svg(SQUARE.format("").replace("100 30", dasharray), 200, 200), 200)
    assert _patches(pdf) == 0
    assert re.search(r" re\nS\n", content(pdf))


def test_the_fill_gets_no_patch() -> None:
    # Closed by the fill, the patch would add a sliver: a hole under even-odd
    document = CIRCLE.read_text().replace('fill="none"', 'fill="red" fill-rule="evenodd"')
    page = content(render(document, 200))
    fill = re.search(r"((?:(?:[-\d. ]+ )?[mch]\n)+)f\*\n((?:(?:[-\d. ]+ )?[mch]\n)+)S\n", page)
    assert fill is not None
    assert fill.group(1).count(" m\n") == 1
    assert fill.group(2).count(" m\n") == 2


def test_each_closed_subpath_gets_its_patch() -> None:
    # Outlines of 560 and 320: the start points lie 40 and 60 into a dash of 100
    path = '<path d="M 30 30 H 170 V 170 H 30 Z M 60 60 H 140 V 140 H 60 Z" fill="none" stroke="green" stroke-width="10" stroke-dasharray="100 30"/>'
    assert _patches(render(svg(path, 200, 200), 200)) == 2


def test_an_open_subpath_gets_no_patch() -> None:
    path = '<path d="M 40 40 H 160 V 160 H 40 V 40" fill="none" stroke="green" stroke-width="20" stroke-dasharray="100 30"/>'
    assert _patches(render(svg(path, 200, 200), 200)) == 0


def test_the_paint_order_keeps_the_patch() -> None:
    pdf = render(svg(SQUARE.format('paint-order="stroke"').replace('fill="none"', 'fill="blue"'), 200, 200), 200)
    assert re.search(r" re\n[-\d. ]+ m\n[-\d. ]+ l\n[-\d. ]+ l\nS\n[-\d. ]+ re\nf\n", content(pdf))


@pytest.mark.parametrize(
    ("dasharray", "offset", "cap"),
    [
        ("10 20 30", "0", "butt"),
        ("20 10", "45", "butt"),
        ("20 10", "-7", "butt"),
        ("10 5 3", "-5", "butt"),
        ("0 10 5", "-5", "round"),
    ],
)
def test_the_dash_pattern_is_the_one_of_the_pdf(dasharray: str, offset: str, cap: str) -> None:
    style = f'fill="none" stroke="green" stroke-width="2" stroke-dasharray="{dasharray}" stroke-dashoffset="{offset}" stroke-linecap="{cap}"'
    written = re.findall(r"\[([-\d. e]*)\] ([-\d.]+) d", content(render(svg(f'<path d="M 0 50 H 200" {style}/>'))))[-1]
    array = tuple(float(value) for value in written[0].split())
    array = array * 2 if len(array) % 2 else array
    node = {"stroke-dasharray": dasharray, "stroke-dashoffset": offset, "stroke-linecap": cap, "stroke-width": "2"}
    pattern = dashes.dash_pattern(SimpleNamespace(length=lambda value, font_size: size(value, font_size, 100)), node, 16)
    assert pattern is not None
    assert pattern[0] == pytest.approx(array, abs=1e-6)
    assert pattern[1] == pytest.approx(float(written[1]) % sum(array))


def test_a_solid_stroke_has_no_dash_pattern() -> None:
    node = {"stroke-dasharray": "none"}
    assert dashes.dash_pattern(SimpleNamespace(length=lambda value, font_size: size(value, font_size, 100)), node, 16) is None


def test_closed_subpaths() -> None:
    # A segment after h starts a new subpath at the start point of the closed one
    path = [b"0 0 m", b"10 0 l", b"h", b"0 10 l", b"h", b"5 5 m", b"6 6 l"]
    assert dashes.closed_subpaths(path) == [[((0, 0), (10, 0)), ((10, 0), (0, 0))], [((0, 0), (0, 10)), ((0, 10), (0, 0))]]


def test_an_unknown_operator_gives_no_subpath() -> None:
    # WeasyPrint writes no v or y: a path with one is left alone
    assert dashes.closed_subpaths([b"0 0 m", b"1 1 2 2 v", b"h"]) == []


def test_a_subpath_of_no_length_gets_no_patch() -> None:
    assert dashes._patch([((5.0, 5.0), (5.0, 5.0))], [0.0], 1.0) == []


def test_the_length_of_a_quarter_circle() -> None:
    k = 4 * (2**0.5 - 1) / 3
    quarter: Any = ((1.0, 0.0), (1.0, k), (k, 1.0), (0.0, 1.0))
    assert dashes.length(quarter) == pytest.approx(1.5708, abs=1e-3)
    assert dashes.length(quarter, 0.5) == pytest.approx(dashes.length(quarter) / 2, abs=1e-9)


def test_without_the_paint_order_feature_the_order_stays(monkeypatch: pytest.MonkeyPatch) -> None:
    # The paint feature installs fill_stroke for the patches alone: paint-order then has no effect
    monkeypatch.setitem(paint_order._ENABLED, "order", False)
    pdf = render(svg(SQUARE.format('paint-order="stroke"').replace('fill="none"', 'fill="blue"'), 200, 200), 200)
    assert re.search(r" re\nf\n[-\d. ]+ re\n[-\d. ]+ m\n[-\d. ]+ l\n[-\d. ]+ l\nS\n", content(pdf))
    pdf = render(svg(SQUARE.format('paint-order="stroke"').replace("100 30", "20 20").replace('fill="none"', 'fill="blue"'), 200, 200), 200)
    assert re.search(r" re\nB\n", content(pdf))
