"""The dash that runs through the start point of a closed subpath, drawn as one dash.

Touches nothing by itself: ``paint_order.fill_stroke`` strokes the patches of ``closing_patches`` with
the path, after the fill.

A closed subpath starts its dash pattern at its start point and ends it there. When a dash runs through
that point, Chromium draws one dash with the line join in it: Skia (SkDashPath) skips the first dash
of a closed contour and draws it at the end, joined to the last one. A PDF viewer draws two dashes that
end at the start point. PDFium leaves a light seam across the dash and a notch on its outer edge, and
no line join at a corner.

The patch is a short open subpath along the path, from inside the last dash through the start point
into the first dash. Drawn in the same stroke, it adds the join and nothing else: every subpath starts
at the dash phase, inside the first dash, and the patch is shorter than that dash, so the pattern keeps
it whole. No dash moves. A move of the start point into a gap would move them: the pattern repeats along
a closed path only when its length is a multiple of the period.

A square cap needs no patch: the caps of both dashes reach over the start point. The patch is left out
of the fill: closed by the fill, it would add a sliver, a hole under the even-odd rule.
"""

from __future__ import annotations

import math
from typing import Any

from . import paint

Point = tuple[float, float]
Segment = tuple[Point, ...]  # two points for a line, four for a cubic Bezier
Patch = tuple[str, tuple[float, ...]]  # a method of the stream and its arguments

SHORTEST_RUN = 1e-3  # of the dash period: a shorter piece of dash at the start point gets no patch
LENGTH_STEPS = 16  # intervals of Gauss-Legendre quadrature for the length of a Bezier
BISECTIONS = 48  # steps of the search for the parameter at a length along a Bezier
# Gauss-Legendre with five nodes, mapped to [0, 1]: nodes and weights
_GAUSS = tuple(
    ((1 + node) / 2, weight / 2)
    for node, weight in (
        (-0.906179845938664, 0.2369268850561891),
        (-0.5384693101056831, 0.4786286704993665),
        (0.0, 0.5688888888888889),
        (0.5384693101056831, 0.4786286704993665),
        (0.906179845938664, 0.2369268850561891),
    )
)


def dash_pattern(svg: Any, node: Any, font_size: float) -> tuple[tuple[float, ...], float] | None:
    """The dashes of the stroke of node as the PDF draws them, even in number, and the phase in their period."""
    values = paint.dash_values(svg, node, font_size)
    if values is None:
        return None
    dashes, offset = values
    if paint.zero_dashes_painted(node, dashes):
        dashes = paint.no_zero_dashes(dashes, svg.length(node.get("stroke-width", "1px"), font_size))
    elif len(dashes) % 2:
        dashes *= 2
    return dashes, offset % sum(dashes)


def _dash_after(dashes: tuple[float, ...], position: float) -> float:
    """The length of the dash that runs on from position, in [0, period); 0 in a gap."""
    start = 0.0
    for index, value in enumerate(dashes):
        if not index % 2 and start <= position < start + value:
            return start + value - position
        start += value
    return 0.0


def _dash_before(dashes: tuple[float, ...], position: float) -> float:
    """The length of the dash that runs up to position, in (0, period]; 0 in a gap."""
    start = 0.0
    for index, value in enumerate(dashes):
        if not index % 2 and start < position <= start + value:
            return position - start
        start += value
    return 0.0


def closing_patches(svg: Any, node: Any, font_size: float, path: list[bytes]) -> list[Patch]:
    """The patches that join the dashes through the start point of each closed subpath of path."""
    if node.get("stroke-linecap", "butt") == "square" or (pattern := dash_pattern(svg, node, font_size)) is None:
        return []
    dashes, phase = pattern
    period = sum(dashes)
    first = _dash_after(dashes, phase)
    # Without a gap the stroke is solid: no dash ends at the start point
    if not any(dashes[1::2]) or first <= period * SHORTEST_RUN:
        return []
    patches: list[Patch] = []
    for segments in closed_subpaths(path):
        lengths = [length(segment) for segment in segments]
        total = sum(lengths)
        last = _dash_before(dashes, (phase + total) % period or period)
        if last > period * SHORTEST_RUN:
            # A quarter of the shorter piece: the patch stays well inside both dashes
            patches += _patch(segments, lengths, min(first, last) / 4)
    return patches


def closed_subpaths(path: list[bytes]) -> list[list[Segment]]:
    """The closed subpaths of path operators, each as its segments, the closing line last; none for an unknown operator."""
    out: list[list[Segment]] = []
    segments: list[Segment] = []
    start = current = (0.0, 0.0)
    for item in path:
        *numbers, operator = item.split()
        values = [float(number) for number in numbers]
        points = list(zip(values[::2], values[1::2], strict=False))
        if operator == b"m":
            segments, start, current = [], points[0], points[0]
        elif operator == b"re":
            x, y, width, height = values
            corners = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
            out.append(list(zip(corners, corners[1:] + corners[:1], strict=True)))
            segments, start, current = [], (x, y), (x, y)
        elif operator == b"h":
            out.append([*segments, (current, start)])
            segments, current = [], start
        elif operator in (b"l", b"c"):
            segments.append((current, *points))
            current = points[-1]
        else:
            return []
    return out


def _speed(segment: Segment, t: float) -> float:
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = segment
    u = 1 - t
    dx = 3 * (u * u * (x1 - x0) + 2 * u * t * (x2 - x1) + t * t * (x3 - x2))
    dy = 3 * (u * u * (y1 - y0) + 2 * u * t * (y2 - y1) + t * t * (y3 - y2))
    return math.hypot(dx, dy)


def length(segment: Segment, t: float = 1.0) -> float:
    """The length of segment from its start to parameter t."""
    if len(segment) == 2:
        return math.dist(*segment) * t
    step = t / LENGTH_STEPS
    return sum(weight * step * _speed(segment, step * (index + node)) for index in range(LENGTH_STEPS) for node, weight in _GAUSS)


def _parameter(segment: Segment, distance: float) -> float:
    """The parameter at distance along segment."""
    if len(segment) == 2:
        return distance / math.dist(*segment)
    low, high = 0.0, 1.0
    for _ in range(BISECTIONS):
        middle = (low + high) / 2
        low, high = (middle, high) if length(segment, middle) < distance else (low, middle)
    return (low + high) / 2


def _lerp(a: Point, b: Point, t: float) -> Point:
    return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t


def _split(segment: Segment, t: float) -> tuple[Segment, Segment]:
    """The two parts of segment at parameter t (de Casteljau)."""
    if len(segment) == 2:
        middle = _lerp(*segment, t)
        return (segment[0], middle), (middle, segment[1])
    p0, p1, p2, p3 = segment
    a, b, c = _lerp(p0, p1, t), _lerp(p1, p2, t), _lerp(p2, p3, t)
    d, e = _lerp(a, b, t), _lerp(b, c, t)
    f = _lerp(d, e, t)
    return (p0, a, d, f), (f, e, c, p3)


def _patch(segments: list[Segment], lengths: list[float], reach: float) -> list[Patch]:
    """A subpath from reach before the end of the last drawn segment to reach into the first one."""
    drawn = [(segment, size) for segment, size in zip(segments, lengths, strict=True) if size > 0]
    if not drawn:
        return []
    (last, last_length), (first, first_length) = drawn[-1], drawn[0]
    tail = _split(last, _parameter(last, last_length - min(reach, last_length)))[1]
    head = _split(first, _parameter(first, min(reach, first_length)))[0]
    return [("move_to", tail[0]), _draw(tail), _draw(head)]


def _draw(segment: Segment) -> Patch:
    if len(segment) == 2:
        return "line_to", segment[1]
    return "curve_to", (*segment[1], *segment[2], *segment[3])


def emit(stream: Any, patches: list[Patch]) -> None:
    for method, arguments in patches:
        getattr(stream, method)(*arguments)
