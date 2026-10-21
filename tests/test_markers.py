"""Path data parsing and marker orientation."""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest
from helpers import pixel, render, svg

from weasysvg import markers, pathdata
from weasysvg.pathdata import Segment

MARKER = '<marker id="m" refX="10" refY="10" markerWidth="20" markerHeight="20" orient="auto" markerUnits="userSpaceOnUse"><path d="M 20 10 L 10 16 V 4 Z" fill="blue"/></marker>'
BLUE = (0, 0, 255)


def near(actual: tuple[float, ...], expected: tuple[float, ...], tolerance: float = 1e-6) -> bool:
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected, strict=True))


# ---------------- path data ----------------


def kinds(data: str) -> list[str]:
    return [segment.kind for segment in pathdata.parse(data)]


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ("M0 0 10 0 10 10", ["move", "line", "line"]),
        ("m1 1h5v5H0V0z", ["move", "line", "line", "line", "line", "close"]),
        ("M0,0C1,1,2,2,3,3S5,5,6,6", ["move", "cubic", "cubic"]),
        ("M0 0Q5 5 10 0T20 0q5 5 10 0t10 0", ["move", "cubic", "cubic", "cubic", "cubic"]),
        ("M0 0a5 5 0 011 1", ["move", "arc"]),
        ("M0 0A0 5 0 0 1 10 10", ["move", "line"]),
        ("M0 0A5 5 0 0 1 0 0", ["move"]),
        ("M0 0 L10 0 Z 5", ["move", "line", "close"]),
        ("L10 0", []),
        ("M0 0 L10", ["move"]),
        ("M0 0 A5 5 0 2 1 10 10", ["move"]),
        ("M0 0 L 1e1 0 .5.5", ["move", "line", "line"]),
        ("M0 0 L 1e-1, 2E+1 , 3 4", ["move", "line", "line"]),
        ("M0 0 L 1e 2", ["move"]),
        (None, []),
    ],
)
def test_parse(data: str | None, expected: list[str]) -> None:
    assert [segment.kind for segment in pathdata.parse(data)] == expected


def test_relative_and_smooth_coordinates() -> None:
    segments = pathdata.parse("m10 10 l5 0 c0 5 5 5 5 0 s5 -5 5 0 Q40 0 50 10 T70 10 Z")
    assert segments[1].end == (15, 10)
    assert segments[2].points == ((15, 10), (15, 15), (20, 15), (20, 10))
    # S reflects the second control point of the cubic before it
    assert segments[3].points[1] == (20, 5)
    # T reflects the quadratic control point: (50, 10) - (40, 0) gives (60, 20)
    assert near(segments[5].points[1], (50 + 2 / 3 * 10, 10 + 2 / 3 * 10))
    assert segments[6].end == (10, 10)
    # A smooth curve after a line uses the current point as its first control point
    assert pathdata.parse("M0 0 L10 0 S20 10 30 0")[2].points[1] == (10, 0)


def test_slopes_skip_coincident_points() -> None:
    cubic = Segment("cubic", ((0, 0), (0, 0), (10, 10), (10, 10)))
    assert cubic.out_slope() == (10, 10)
    assert cubic.in_slope() == (10, 10)
    assert Segment("line", ((1, 1), (1, 1))).out_slope() == (0.0, 0.0)
    assert Segment("line", ((1, 1), (1, 1))).in_slope() == (0.0, 0.0)


def test_arc_geometry() -> None:
    # A half circle from (0, 0) to (20, 0), sweeping clockwise on screen (y down) through (10, -10)
    arc = pathdata.parse("M0 0 A10 10 0 0 1 20 0")[1]
    assert near(arc.at(0.5), (10, -10))
    assert near(arc.out_slope(), (0, -10))
    assert near(arc.in_slope(), (0, 10))
    # Radii too small for the endpoints are scaled up
    small = pathdata.parse("M0 0 A1 1 0 0 0 20 0")[1]
    assert near(small.at(0.5), (10, 10))
    assert len(small.polyline()) == pathdata.FLATTEN_STEPS + 1
    assert Segment("line", ((0, 0), (4, 2))).polyline() == [(0, 0), (4, 2)]
    assert near(Segment("cubic", ((0, 0), (0, 10), (10, 10), (10, 0))).at(0.5), (5, 7.5))
    assert Segment("line", ((0, 0), (4, 2))).at(0.5) == (2, 1)
    # Counterclockwise on screen: the arc passes below, through (10, 10)
    below = pathdata.parse("M0 0 A10 10 0 0 0 20 0")[1]
    assert near(below.at(0.5), (10, 10))
    assert below.arc is not None
    assert below.arc[6] < 0
    # The large arc against the sweep: atan2 gives +90 degrees, the arc runs -270 through (-7.07, -7.07)
    large = pathdata.parse("M10 0 A10 10 0 1 0 0 10")[1]
    assert large.arc is not None
    assert large.arc[6] == pytest.approx(-1.5 * math.pi)
    assert near(large.at(0.5), (-10 / math.sqrt(2), -10 / math.sqrt(2)))


# ---------------- marker positions ----------------


def angles(data: str) -> list[float]:
    return [round(angle, 6) for _, angle in markers.positions(pathdata.parse(data))]


def test_angles_bisect_with_wrapping() -> None:
    # Up into the vertex, down out of it: 270 and 90 degrees, so the marker points left, as in Chromium
    # 156 and the resvg suite
    assert angles("M 40 155 C 95 140 100 105 100 40 C 100 105 105 140 160 160")[1] == 180
    # Down into the vertex, up out of it: the same bisector
    assert angles("M 0 0 L 0 10 L 0 0")[1] == 180
    # Across 0 degrees: 350 and 10 bisect at 0
    assert angles("M0 0 L10 -1.763270 L20 0")[1] == pytest.approx(0, abs=1e-4)
    assert angles("M0 0 L10 0 L10 10") == [0, 45, 90]


def test_closed_subpaths_bisect_their_first_vertex() -> None:
    assert angles("M0 0 L10 0 L10 10 Z") == [292.5, 45, 157.5, 292.5]
    # A second subpath after the close starts from the same point
    marks = angles("M0 0 L10 0 Z L0 10")
    assert marks[0] == 90
    assert marks[2] == 135
    assert marks[-1] == 90


def test_no_positions_without_segments() -> None:
    assert markers.positions(pathdata.parse("M0 0")) == []
    assert markers.positions([Segment("line", ((0, 0), (1, 1))), Segment("line", ((1, 1), (2, 2)))]) == []


def test_vertices_give_draw_markers_each_angle() -> None:
    marks = [((0.0, 0.0), 10.0), ((5.0, 0.0), 20.0), ((9.0, 0.0), 30.0)]
    out = list(markers.vertices(marks))
    assert out[0] == (0, 0)
    assert out[2] == (5, 0)
    assert out[4] == (9, 0)
    (a1, a2), (b1, b2) = out[1], out[3]
    # draw_markers: start pi - a1, mid the mean of a2 and pi - b1, end b2
    assert math.degrees(math.pi - a1) == pytest.approx(10)
    assert math.degrees((a2 + math.pi - b1) / 2) == pytest.approx(20)
    assert math.degrees(b2) == pytest.approx(30)


def test_segments_of_shapes() -> None:
    fake = SimpleNamespace(point=lambda x, y, _size: (float(x), float(y)))
    line = SimpleNamespace(tag="line", get={"x1": "0", "y1": "0", "x2": "10", "y2": "0"}.get)
    assert [s.kind for s in markers.segments_of(fake, line, 12)] == ["move", "line"]
    polygon = SimpleNamespace(tag="polygon", get={"points": "0,0 10,0 10,10"}.get)
    assert [s.kind for s in markers.segments_of(fake, polygon, 12)] == ["move", "line", "line", "close"]
    assert markers.segments_of(fake, SimpleNamespace(tag="polyline", get={}.get), 12) == []


# ---------------- drawing ----------------


def test_mid_marker_points_left_at_a_cusp() -> None:
    body = f'<defs>{MARKER}</defs><path d="M 20 90 C 60 80 70 60 70 20 C 70 60 80 80 120 90" fill="none" stroke="black" marker-mid="url(#m)"/>'
    pdf = render(svg(body, height=120))
    # The arrow tip lies left of the vertex at (70, 20): 60 to 70 units
    assert pixel(pdf, 48, 15) == BLUE
    assert pixel(pdf, 57, 15) != BLUE


def test_marker_on_a_polyline_and_without_markers() -> None:
    body = f'<defs>{MARKER}</defs><polyline points="20 20 60 20" fill="none" stroke="black" marker-end="url(#m)"/><polyline points="20 60 60 60" fill="none" stroke="black"/>'
    pdf = render(svg(body, height=120))
    assert pixel(pdf, 49, 15) == BLUE


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        # An arc of no radius is a line to its end; uppercase stays absolute, lowercase relative
        ("M 335 97 L 300 50 A 0 0 0 1 0 335 97 Z", "M335 97 L300 50 L335 97 Z"),
        # One that ends where it starts is omitted, as SVG says: a marker sees no vertex there
        ("M 335 97 A 0 0 0 1 0 335 97 Z", "M335 97 Z"),
        ("M10 10 L20 10 a0 5 0 0 1 0 0 L30 10", "M10 10 L20 10 L30 10"),
        # The other numbers are written exactly
        ("M 1000000000001 0.1 A 0 0 0 0 1 1000000000002 0.30000000000000004", "M1000000000001 0.1 L1000000000002 0.30000000000000004"),
        ("M10 10 a0 5 0 0 1 3 4", "M10 10 l3 4"),
        ("M10 10 A 5 0 0 0 1 3 4", "M10 10 L3 4"),
        # A repeated arc keeps its radii, each written out
        ("M0 0 A 0 0 0 0 1 5 5 6 6 0 0 1 7 7", "M0 0 L5 5 A6 6 0 0 1 7 7"),
        # Data past an error is kept as it is, for WeasyPrint to read up to the same error
        ("M0 0 A0 0 0 0 1 5 5 L x", "M0 0 L5 5 L x"),
        # Numbers cut short keep the command they belong to
        ("M0 0 A0 0 0 0 1 5 5 6", "M0 0 L5 5 A6"),
    ],
)
def test_arcs_of_no_radius_become_lines(data: str, expected: str) -> None:
    assert pathdata.without_zero_radius_arcs(data) == expected


@pytest.mark.parametrize("data", ["M0 0 A 5 5 0 0 1 10 0", "M0 0 L10 10", "", "A 0 0 0 0 1 5 5"])
def test_path_data_without_arcs_of_no_radius_stays(data: str) -> None:
    assert pathdata.without_zero_radius_arcs(data) is None


@pytest.mark.parametrize("data", ["M0 0 A1e-200 1 0 0 1 10 10", "M0 0 A1e-200 1 0 0 1 10 10 A0 0 0 0 1 5 5"])
def test_a_radius_whose_square_underflows_is_read(data: str) -> None:
    # rx * rx is 0 for such a radius: the arc is the line it degenerates to, not a division by zero
    assert [segment.kind for segment in pathdata.parse(data)][-1] == "line"
    pathdata.without_zero_radius_arcs(data)
