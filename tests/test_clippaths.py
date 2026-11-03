from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from weasysvg import clippaths
from weasysvg.clippaths import Fill, Subpath
from weasysvg.coverage import Unsupported
from weasysvg.shapeblur import signed_area


def content(operators: str, states: dict[str, Any] | None = None) -> Any:
    """A stand-in for a scratch group: its operators and its graphics states."""
    return SimpleNamespace(stream=[operators], _resources={"ExtGState": states or {}})


def square(x: float, y: float, size: float, turn: int = 1) -> Subpath:
    corners = [(x, y), (x + size, y), (x + size, y + size), (x, y + size)]
    if turn < 0:
        corners = [corners[0], *corners[:0:-1]]
    return Subpath(corners[0], [(corner,) for corner in [*corners[1:], corners[0]]])


def area(subpath: Subpath) -> float:
    return signed_area(subpath.ring(0.01))


def test_read_applies_the_transforms_of_each_fill() -> None:
    fills = clippaths.read(content("q 2 0 0 2 10 0 cm 0 0 m 5 0 l 5 5 l h f Q 0 0 1 1 re f*"))
    assert [fill.even_odd for fill in fills] == [False, True]
    assert fills[0].subpaths[0].points() == [(10, 0), (20, 0), (20, 10), (10, 0)]
    assert fills[1].subpaths[0].points() == [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]


def test_read_turns_v_and_y_into_curves() -> None:
    fills = clippaths.read(content("0 0 m 1 1 2 0 v 3 1 4 0 y 5 1 5 3 4 4 c f"))
    segments = fills[0].subpaths[0].segments
    assert segments[0] == ((0, 0), (1, 1), (2, 0))
    assert segments[1] == ((3, 1), (4, 0), (4, 0))
    assert segments[2] == ((5, 1), (5, 3), (4, 4))
    assert segments[-1] == ((0, 0),)


def test_read_starts_a_subpath_after_a_close_and_at_a_move() -> None:
    fills = clippaths.read(content("0 0 m 4 0 l 4 4 l h 6 0 l 6 4 l 10 10 m 12 10 l 12 12 l f"))
    assert [subpath.start for subpath in fills[0].subpaths] == [(0, 0), (0, 0), (10, 10)]


def test_read_drops_a_path_that_is_not_painted_and_a_lone_point() -> None:
    assert clippaths.read(content("0 0 m 4 0 l 4 4 l n 5 5 m f")) == [Fill([], False)]


def test_read_closes_a_subpath_back_at_its_start_once() -> None:
    fills = clippaths.read(content("0 0 m 4 0 l 4 4 l 0 0 l h f"))
    assert fills[0].subpaths[0].points() == [(0, 0), (4, 0), (4, 4), (0, 0)]


@pytest.mark.parametrize("operators", ["4 0 l f", "1 1 2 2 v f"])
def test_read_needs_a_current_point(operators: str) -> None:
    with pytest.raises(Unsupported, match="current point"):
        clippaths.read(content(operators))


@pytest.mark.parametrize("operators", ["BT /F1 12 Tf (x) Tj ET", "0 0 1 1 re W n", "/x0 Do", "/sh0 sh"])
def test_read_takes_fills_alone(operators: str) -> None:
    with pytest.raises(Unsupported):
        clippaths.read(content(operators))


def test_read_ignores_colors_and_lines() -> None:
    fills = clippaths.read(content("/a0 gs 1 0 0 rg 0 g 2 w 0 J 0 j 4 M [] 0 d /P0 cs /P0 scn 0 0 1 1 re f", {"a0": {"Type": "/ExtGState", "ca": 1, "CA": 1}}))
    assert len(fills) == 1


@pytest.mark.parametrize("state", [{"ca": 0.5}, {"BM": "/Multiply"}, {"SMask": "<< >>"}, {"LW": 2}])
def test_read_takes_a_plain_graphics_state_only(state: dict[str, Any]) -> None:
    with pytest.raises(Unsupported, match="graphics state"):
        clippaths.read(content("/a0 gs 0 0 1 1 re f", {"a0": state}))


def test_plain_graphics_states() -> None:
    clippaths._plain_state({"Type": "/ExtGState", "BM": "/Normal", "SMask": "/None", "ca": 1.0})
    clippaths._plain_state({"BM": "/Compatible"})


def test_reversed_runs_the_curves_back() -> None:
    subpath = Subpath((0, 0), [((1, 0),), ((1, 1), (0, 2), (-1, 1)), ((0, 0),)])
    back = subpath.reversed()
    assert back.start == (0, 0)
    assert back.segments == [((-1, 1),), ((0, 2), (1, 1), (1, 0)), ((0, 0),)]
    assert back.reversed() == subpath
    assert area(back) == pytest.approx(-area(subpath))


def test_union_turns_every_fill_the_same_way() -> None:
    fills = [Fill([square(0, 0, 10)], False), Fill([square(5, 5, 10, -1)], False)]
    assert all(area(subpath) > 0 for subpath in clippaths.union(fills))


@pytest.mark.parametrize(
    ("turns", "even_odd", "kept"),
    [
        # A hole: the inner square turns the other way, or any way under even-odd
        ((1, -1), False, [1, -1]),
        ((1, 1), True, [1, -1]),
        ((-1, -1), True, [1, -1]),
        # Two turns the same way, nonzero: the inner square adds nothing
        ((1, 1), False, [1]),
        ((-1, -1), False, [1]),
    ],
)
def test_union_of_nested_subpaths(turns: tuple[int, int], even_odd: bool, kept: list[int]) -> None:
    fill = Fill([square(0, 0, 10, turns[0]), square(3, 3, 4, turns[1])], even_odd)
    assert [1 if area(subpath) > 0 else -1 for subpath in clippaths.union([fill])] == kept


def test_union_of_islands_in_a_hole() -> None:
    fill = Fill([square(0, 0, 30), square(5, 5, 20), square(10, 10, 10)], True)
    assert [1 if area(subpath) > 0 else -1 for subpath in clippaths.union([fill])] == [1, -1, 1]


def test_union_drops_a_subpath_without_area() -> None:
    line = Subpath((0, 0), [((5, 0),), ((0, 0),)])
    assert clippaths.union([Fill([line, square(0, 2, 3)], False), Fill([], False)]) == [square(0, 2, 3)]


@pytest.mark.parametrize(
    "subpaths",
    [
        # A bowtie crosses itself
        [Subpath((0, 0), [((10, 10),), ((10, 0),), ((0, 10),), ((0, 0),)])],
        # Two squares overlap, two touch at a corner, two share an edge
        [square(0, 0, 10), square(5, 5, 10)],
        [square(0, 0, 10), square(10, 10, 10)],
        [square(0, 0, 10), square(10, 0, 10)],
    ],
)
def test_union_needs_subpaths_that_do_not_meet(subpaths: list[Subpath]) -> None:
    with pytest.raises(Unsupported, match="cross"):
        clippaths.union([Fill(subpaths, False)])


def test_union_of_too_many_segments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clippaths, "MAX_SEGMENTS", 7)
    with pytest.raises(Unsupported, match="too many"):
        clippaths.union([Fill([square(0, 0, 10), square(2, 2, 2)], False)])


def test_winding() -> None:
    ring = square(0, 0, 10).ring(1)
    assert clippaths._winding(ring, (5, 5)) == 1
    assert clippaths._winding(square(0, 0, 10, -1).ring(1), (5, 5)) == -1
    assert clippaths._winding(ring, (15, 5)) == 0


@pytest.mark.parametrize(
    ("a", "b", "c", "d", "meet"),
    [
        ((0, 0), (10, 10), (0, 10), (10, 0), True),
        ((0, 0), (10, 0), (5, 0), (15, 0), True),
        ((0, 0), (10, 0), (10, 0), (10, 10), True),
        ((0, 0), (10, 0), (0, 1), (10, 1), False),
        ((0, 0), (10, 0), (11, 0), (20, 0), False),
        ((0, 0), (10, 10), (5, 0), (10, 4), False),
        ((0, 0), (0, 10), (1, 20), (1, 30), False),
    ],
)
def test_meet(a: Any, b: Any, c: Any, d: Any, meet: bool) -> None:
    assert clippaths._meet(a, b, c, d) is meet
    assert clippaths._meet(c, d, a, b) is meet


def test_add_writes_lines_and_curves() -> None:
    calls: list[str] = []

    def record(name: str) -> Any:
        return lambda *_: calls.append(name)

    stream = SimpleNamespace(**{name: record(name) for name in ("move_to", "line_to", "curve_to", "close")})
    clippaths.add(stream, [Subpath((0, 0), [((1, 0),), ((1, 1), (0, 2), (-1, 1)), ((0, 0),)])])
    assert calls == ["move_to", "line_to", "curve_to", "line_to", "close"]
