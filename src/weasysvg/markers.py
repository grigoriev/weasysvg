"""Marker orientation as Chromium computes it.

Touches: ``svg.TAGS`` for path, line, polyline and polygon. After WeasyPrint draws the shape,
``node.vertices`` is rebuilt from pathdata.py. WeasyPrint averaged the angles at a vertex without
wrapping them and took the tangents of curves and arcs from the wrong points, so orient="auto" turned
markers the wrong way.

Chromium (SVGMarkerData): a start marker follows the first segment out, an end marker the last one in,
a mid marker bisects both, with 360 degrees added to the incoming angle when the two lie more than 180
apart. A moveto counts as a line from the current point. A closed subpath turns its first and closing
vertex to bisect the closing segment and the first segment.
"""

from __future__ import annotations

import math
import re
from collections import deque
from collections.abc import Callable
from typing import Any

from weasyprint import svg as wp_svg

from . import pathdata
from .pathdata import Point, Segment

SHAPES = ("path", "line", "polyline", "polygon")
MARKER_ATTRIBUTES = ("marker", "marker-start", "marker-mid", "marker-end")
_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _angle(slope: Point) -> float:
    return math.degrees(math.atan2(slope[1], slope[0]))


def _bisect(incoming: Point, outgoing: Point) -> float:
    in_angle, out_angle = _angle(incoming), _angle(outgoing)
    if abs(in_angle - out_angle) > 180:
        in_angle += 360
    return (in_angle + out_angle) / 2


def positions(segments: list[Segment]) -> list[tuple[Point, float]]:
    """Each marker vertex of the path with its angle in degrees: start, mids, end."""
    if len(segments) < 2 or segments[0].kind != "move":
        return []
    elements = segments[1:]
    out: list[tuple[Point, float]] = [(segments[0].end, _angle(elements[0].out_slope()))]
    subpath_vertex, subpath_out = 0, elements[0].out_slope()
    for index, element in enumerate(elements):
        following = elements[index + 1] if index + 1 < len(elements) else None
        if element.kind == "close":
            angle = _bisect(element.in_slope(), subpath_out)
            out[subpath_vertex] = (out[subpath_vertex][0], angle)
            if following is not None and following.kind != "move":
                angle = _bisect(element.in_slope(), following.out_slope())
        elif following is None:
            angle = _angle(element.in_slope())
        else:
            angle = _bisect(element.in_slope(), following.out_slope())
        out.append((element.end, angle))
        if element.kind == "move" or (element.kind == "close" and following is not None and following.kind != "move"):
            subpath_vertex = len(out) - 1
            subpath_out = following.out_slope() if following is not None else (0.0, 0.0)
    return out


def vertices(marks: list[tuple[Point, float]]) -> deque[Any]:
    """The vertices in the form draw_markers of WeasyPrint reads: point, (pi - out, in), point and so on.

    draw_markers turns a start by pi - a1, a mid by the mean of the previous a2 and pi - a1, an end by the
    last a2: with a2 and pi - a1 both set to the angle of the vertex, each marker gets exactly that angle.
    """
    out: deque[Any] = deque()
    for index, (point, angle) in enumerate(marks):
        out.append(point)
        if index + 1 < len(marks):
            out.append((math.pi - math.radians(angle), math.radians(marks[index + 1][1])))
    return out


def _points(node: Any) -> list[Point]:
    numbers = [float(value) for value in _NUMBER.findall(node.get("points") or "")]
    return list(zip(numbers[::2], numbers[1::2], strict=False))


def segments_of(svg: Any, node: Any, font_size: float) -> list[Segment]:
    """The segments of a path, line, polyline or polygon."""
    if node.tag == "path":
        return pathdata.parse(node.get("d"))
    if node.tag == "line":
        x1, y1 = svg.point(node.get("x1"), node.get("y1"), font_size)
        x2, y2 = svg.point(node.get("x2"), node.get("y2"), font_size)
        points = [(x1, y1), (x2, y2)]
    else:
        points = _points(node)
    if not points:
        return []
    out = [Segment("move", ((0.0, 0.0), points[0]))]
    out += [Segment("line", (a, b)) for a, b in zip(points, points[1:], strict=False)]
    if node.tag == "polygon":
        out.append(Segment("close", (points[-1], points[0])))
    return out


def _with_markers(draw: Callable[..., Any]) -> Callable[..., Any]:
    def shape(svg: Any, node: Any, font_size: float) -> Any:
        result = draw(svg, node, font_size)
        if any(node.get(name) for name in MARKER_ATTRIBUTES):
            node.vertices = vertices(positions(segments_of(svg, node, font_size)))
        return result

    return shape


def install() -> None:
    for tag in SHAPES:
        wp_svg.TAGS[tag] = _with_markers(wp_svg.TAGS[tag])
