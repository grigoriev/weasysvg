"""The coverage of drawn content: its operators read back, strokes outlined, colors composited."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pydyf
import pytest
from PIL import Image

from weasysvg import coverage, shapeblur
from weasysvg.coverage import BEVEL, BUTT, MITER, ROUND, SQUARE, Group, Shape, Unsupported


def stream(*operators: str, resources: dict[str, Any] | None = None, extra: dict[str, Any] | None = None) -> Any:
    """A stand-in for a content stream: its operators, one per item, and its resources."""
    return SimpleNamespace(stream=[operator.encode() for operator in operators], _resources=resources or {"ExtGState": {}, "XObject": {}}, extra=extra)


def shapes(*operators: str, **kwargs: Any) -> list[Shape]:
    return list(coverage.read(stream(*operators, **kwargs), 0.01).shapes())


def extent(shape: Shape) -> tuple[float, float, float, float]:
    xs, ys = [x for ring in shape.rings for x, _ in ring], [y for ring in shape.rings for _, y in ring]
    return min(xs), min(ys), max(xs), max(ys)


def test_operators_split_into_tokens() -> None:
    # Brackets and delimiters stand alone, a name ends at a delimiter, numbers take a sign, a leading or
    # trailing dot and an exponent, and an operator ends where a number starts
    content = SimpleNamespace(stream=[b"/a0 gs [1 2.5]0 d -.5 +3. 1e-05 2E+3cm 0.5g T* ' \" (x) <ab> -", "/n[ 7."])
    assert list(coverage._tokens(content)) == [
        *(b"/a0", b"gs", b"[", b"1", b"2.5", b"]", b"0", b"d", b"-.5", b"+3.", b"1e-05", b"2E+3", b"cm", b"0.5", b"g"),
        *(b"T*", b"'", b'"', b"(", b"x", b")", b"<", b"ab", b">", b"-", b"/n", b"[", b"7."),
    ]


def test_paths_are_read_in_content_space() -> None:
    # cm moves the path, q and Q restore it; v and y repeat a control point; h then l starts a new subpath
    found = shapes("q", "1 0 0 2 10 0 cm", "0 0 m", "10 0 l", "10 10 l", "h", "0 10 l", "f", "Q", "0 0 m", "5 0 5 5 v", "0 5 0 0 y", "f*")
    assert extent(found[0]) == (10, 0, 20, 20)
    assert len(found[0].rings) == 1  # the second subpath, 0 10 back to the start, has no area
    assert found[1].rule == "evenodd"
    assert extent(found[1]) == pytest.approx((0, 0, 5, 5), abs=0.3)


def test_colors_and_opacities_are_read() -> None:
    resources = {"ExtGState": {"a": pydyf.Dictionary({"ca": 0.5, "CA": 0.25, "Type": "/ExtGState", "BM": "/Normal"})}, "XObject": {}}
    found = shapes("0.5 g", "1 0 0 RG", "/a gs", "2 w", "0 0 10 10 re", "B", resources=resources)
    assert [(shape.color, shape.alpha, shape.rule) for shape in found] == [((0.5, 0.5, 0.5), 0.5, "nonzero"), ((1, 0, 0), 0.25, "union")]
    found = shapes("0 1 0 rg", "0 0 1 RG", "0 0 10 10 re", "F", "0 0 m", "10 0 l", "10 10 l", "s", "0 0 m", "10 0 l", "10 10 l", "b*")
    assert [shape.color for shape in found] == [(0, 1, 0), (0, 0, 1), (0, 1, 0), (0, 0, 1)]
    assert found[2].rule == "evenodd"


def test_nothing_painted_leaves_nothing() -> None:
    resources = {"ExtGState": {"a": pydyf.Dictionary({"ca": 0, "CA": 0})}, "XObject": {}}
    assert shapes("/a gs", "0 0 10 10 re", "B", resources=resources) == []
    # A line has no inside, a moveto alone no stroke; a stroke of no width paints nothing
    assert shapes("0 0 m", "10 10 l", "f", "0 0 m", "S", "0 w", "0 0 m", "10 0 l", "S") == []
    # An empty group adds nothing, marked content changes nothing
    empty = stream(extra={"Subtype": "/Form", "BBox": [0, 0, 1, 1]})
    assert shapes("/P BMC", "/x Do", "EMC", resources={"ExtGState": {}, "XObject": {"x": empty}}) == []


def test_clips_cut_what_follows() -> None:
    found = shapes("0 0 5 5 re", "W* n", "0 0 10 10 re", "f", "0 0 1 1 re", "W", "f")
    assert found[0].clips == ((([(0, 0), (5, 0), (5, 5), (0, 5)],), "evenodd"),)
    assert len(found[1].clips) == 1  # W f fills, then clips what comes after


def test_a_group_takes_its_matrix_box_and_opacity() -> None:
    inner = stream("0 0 10 10 re", "f", extra={"Subtype": "/Form", "BBox": [0, 0, 5, 5], "Matrix": [2, 0, 0, 2, 0, 0], "Group": {"S": "/Transparency"}})
    resources = {"ExtGState": {"a": {"ca": 0.5}}, "XObject": {"x": inner}}
    content = coverage.read(stream("/a gs", "/x Do", resources=resources), 0.01)
    group = content.items[0]
    assert isinstance(group, Group)
    assert group.alpha == 0.5
    assert group.clips[0][0][0] == [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert extent(group.items[0]) == (0, 0, 20, 20)  # type: ignore[arg-type]


def test_a_form_without_group_paints_in_place() -> None:
    # The form of an SVG image: its shapes join the content around it, each with the opacity in force,
    # clipped to the box of the form
    inner = stream("0 0 10 10 re", "f", extra={"Subtype": "/Form", "BBox": [0, 0, 5, 5], "Matrix": [2, 0, 0, 2, 0, 0]})
    resources = {"ExtGState": {"a": {"ca": 0.5}}, "XObject": {"x": inner}}
    content = coverage.read(stream("/a gs", "/x Do", "0 0 1 1 re", "f", resources=resources), 0.01)
    first, second = content.items
    assert isinstance(first, Shape)
    assert first.alpha == 0.5
    assert first.clips[0][0][0] == [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert extent(first) == (0, 0, 20, 20)
    # The clip of the form ends with it
    assert isinstance(second, Shape)
    assert second.clips == ()


def test_an_empty_group_leaves_nothing() -> None:
    inner = stream(extra={"Subtype": "/Form", "BBox": [0, 0, 5, 5], "Group": {"S": "/Transparency"}})
    assert coverage.read(stream("/x Do", resources={"ExtGState": {}, "XObject": {"x": inner}}), 0.01).items == []


@pytest.mark.parametrize(
    ("operators", "resources"),
    [
        (("BT", "ET"), None),
        (("10 0 l",), None),
        (("/x Do",), {"ExtGState": {}, "XObject": {"x": None}}),
        (("/s gs",), {"ExtGState": {"s": {"SMask": "/None"}}, "XObject": {}}),
        (("/s gs",), {"ExtGState": {"s": {"BM": "/Multiply"}}, "XObject": {}}),
        (("[2 1] 0 d", "0 0 m", "10 0 l", "S"), None),
    ],
)
def test_what_the_coverage_cannot_take_is_refused(operators: tuple[str, ...], resources: dict[str, Any] | None) -> None:
    with pytest.raises(Unsupported):
        shapes(*operators, resources=resources)


def test_no_dashes_are_no_dashes() -> None:
    assert len(shapes("[] 0 d", "0 0 m", "10 0 l", "S")) == 1


def stroke_extent(*operators: str) -> tuple[float, float, float, float]:
    return extent(shapes("2 w", *operators)[0])


def test_caps() -> None:
    assert stroke_extent(f"{BUTT} J", "0 0 m", "10 0 l", "S") == pytest.approx((0, -1, 10, 1))
    assert stroke_extent(f"{SQUARE} J", "0 0 m", "10 0 l", "S") == pytest.approx((-1, -1, 11, 1))
    assert stroke_extent(f"{ROUND} J", "0 0 m", "10 0 l", "S") == pytest.approx((-1, -1, 11, 1), abs=0.01)
    # A subpath of no length paints its caps alone
    assert stroke_extent(f"{SQUARE} J", "5 5 m", "5 5 l", "S") == pytest.approx((4, 4, 6, 6))
    assert stroke_extent(f"{ROUND} J", "5 5 m", "5 5 l", "S") == pytest.approx((4, 4, 6, 6), abs=0.01)
    assert shapes("2 w", f"{BUTT} J", "5 5 m", "5 5 l", "S") == []


def reach(*operators: str) -> float:
    """How far the stroke of a right angle at the origin reaches out of its outer corner."""
    return max(x - y for ring in shapes("2 w", *operators)[0].rings for x, y in ring)


def test_joins() -> None:
    corner = ("-10 0 m", "0 0 l", "0 10 l", "S")
    assert reach(f"{MITER} j", "4 M", *corner) == pytest.approx(2)
    assert reach(f"{MITER} j", "1.2 M", *corner) == pytest.approx(1)  # past the limit: a bevel
    assert reach(f"{BEVEL} j", *corner) == pytest.approx(1)
    assert reach(f"{ROUND} j", *corner) == pytest.approx(2**0.5, abs=0.01)
    # Straight on, and turned back: no miter
    assert stroke_extent(f"{MITER} j", "0 0 m", "5 0 l", "10 0 l", "S") == pytest.approx((0, -1, 10, 1))
    assert stroke_extent(f"{MITER} j", "0 0 m", "10 0 l", "0 0 l", "S") == pytest.approx((0, -1, 10, 1))
    # A closed path joins at every corner and has no caps
    assert stroke_extent(f"{MITER} j", f"{SQUARE} J", "0 0 10 10 re", "S") == pytest.approx((-1, -1, 11, 11))
    # Closed back onto its start, it joins there as well
    assert stroke_extent(f"{MITER} j", "0 0 m", "10 0 l", "10 10 l", "0 10 l", "0 0 l", "h", "S") == pytest.approx((-1, -1, 11, 11))


def test_a_curve_turns_without_corners() -> None:
    # Its flattened points join by bevels: the outline stays within half the width of the curve
    found = shapes("2 w", f"{MITER} j", "0 0 m", "0 10 10 10 10 0 c", "S")
    assert extent(found[0])[3] == pytest.approx(8.5, abs=0.05)


def raster(content: Group) -> tuple[Image.Image, dict[Any, Image.Image]]:
    rings = [ring for shape in content.shapes() for ring in shape.rings]
    return coverage.Raster(content, shapeblur.Field(rings, False, (3.0, 3.0))).coverage()


def test_a_clip_beside_the_shape_hides_it() -> None:
    clip = (([(100.0, 100.0), (101.0, 100.0), (101.0, 101.0)],), "nonzero")
    total, shares = raster(Group([Shape([[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]], "nonzero", 1.0, (0, 0, 0), (clip,))]))
    assert total.getextrema() == (0, 0)


def test_later_shapes_cover_earlier_ones() -> None:
    square = [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]]
    total, shares = raster(Group([Shape(square, "nonzero", 1.0, (1, 0, 0)), Shape(square, "nonzero", 0.5, (0, 0, 1))]))
    middle = (total.width // 2, total.height // 2)
    assert total.getpixel(middle) == 255
    assert shares[(1, 0, 0)].getpixel(middle) == pytest.approx(128, abs=1)
    assert shares[(0, 0, 1)].getpixel(middle) == pytest.approx(128, abs=1)


def test_ratios_mix_in_order() -> None:
    first, second = Image.new("L", (2, 1)), Image.new("L", (2, 1))
    first.putpixel((0, 0), 100)
    second.putpixel((0, 0), 100)
    ratios = coverage.ratios([first, second])
    assert [ratio.getpixel((0, 0)) for ratio in ratios] == [255, 128]
    assert [ratio.getpixel((1, 0)) for ratio in ratios] == [0, 0]
