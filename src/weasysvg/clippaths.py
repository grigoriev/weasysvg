"""A clip path as one PDF clip, for a portable PDF: Word draws no soft mask.

WeasyPrint clips to one W for a simple clip path only; weasysvg draws the others as the soft mask of
their alpha (paint.paint_clip): a <use>, the union of several children, text. Here the children are drawn
into a scratch group and read back: the exact path of each fill, its transforms applied.

One path filled nonzero is the union of several fills when the winding of each fill is 0 or 1 everywhere.
Each subpath turns the way that gives it that, from the faces it bounds: the inside of a subpath is filled
or not by the rule of its fill, and the subpath adds the step from its parent face to its own. That needs
the subpaths of a fill to cross neither themselves nor each other, checked on their flattened outline.
Anything else (text, an image, a clip of a child, a crossing) keeps the soft mask.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, cast

from . import coverage, shapeblur
from .coverage import Matrix, Unsupported
from .shapeblur import Point, Ring

# The control points after the current point: one for a line, three for a curve
Segment = tuple[Point, ...]
# Segments one fill may hold once flattened: the crossing check compares them in pairs
MAX_SEGMENTS = 4000
# The flatness of the crossing check, a share of the size of the fill
FLATNESS = 1e-3
# Operators that change nothing a clip takes: colors, lines, marked content
_STYLE = frozenset((b"g", b"G", b"rg", b"RG", b"k", b"K", b"cs", b"CS", b"sc", b"SC", b"scn", b"SCN", b"w", b"J", b"j", b"M", b"d", b"i", b"ri", b"BDC", b"BMC", b"EMC", b"MP", b"DP"))


@dataclass
class Subpath:
    """A closed subpath: its start and its segments, the last one ending at the start."""

    start: Point
    segments: list[Segment]

    def points(self) -> list[Point]:
        return [self.start, *(segment[-1] for segment in self.segments)]

    def reversed(self) -> Subpath:
        """The same subpath turning the other way."""
        points = self.points()
        # A curve from p to q with controls c1, c2 runs back from q to p with c2, c1
        segments = [(*self.segments[index][-2::-1], points[index]) for index in range(len(self.segments) - 1, -1, -1)]
        return Subpath(points[-1], segments)

    def ring(self, flatness: float) -> Ring:
        """The outline, curves flattened to within about flatness."""
        ring = [self.start]
        for segment in self.segments:
            if len(segment) == 1:
                ring.append(segment[0])
            else:
                ring.extend(coverage._flattened(ring[-1], list(segment), flatness))
        # The last point is the start again
        return ring[:-1]


@dataclass
class Fill:
    subpaths: list[Subpath]
    even_odd: bool


class _Path:
    """The subpaths of the path being built, in the space of the scratch group."""

    def __init__(self) -> None:
        self.subpaths: list[Subpath] = []
        self.open: Subpath | None = None

    def move(self, point: Point) -> None:
        self.close()
        self.open = Subpath(point, [])

    def current(self) -> Point:
        if self.open is None:
            raise Unsupported("a path without a current point")
        return self.open.segments[-1][-1] if self.open.segments else self.open.start

    def add(self, segment: Segment) -> None:
        self.current()
        cast(Subpath, self.open).segments.append(segment)

    def close(self) -> None:
        """Close the open subpath with a line back to its start; the next segment starts there."""
        if self.open is None:
            return
        subpath = self.open
        if not subpath.segments or subpath.segments[-1][-1] != subpath.start:
            subpath.segments.append((subpath.start,))
        if len(subpath.segments) > 1:
            self.subpaths.append(subpath)
        self.open = Subpath(subpath.start, [])

    def done(self) -> list[Subpath]:
        self.close()
        return self.subpaths


def _construct(path: _Path, token: bytes, numbers: list[float], ctm: Matrix) -> None:
    points = [coverage._apply(ctm, numbers[index], numbers[index + 1]) for index in range(0, len(numbers) - 1, 2)]
    if token == b"m":
        path.move(points[0])
    elif token == b"l":
        path.add((points[0],))
    elif token == b"c":
        path.add((points[0], points[1], points[2]))
    elif token == b"v":
        path.add((path.current(), points[0], points[1]))
    elif token == b"y":
        path.add((points[0], points[1], points[1]))
    elif token == b"h":
        path.close()
    else:  # re
        x, y, width, height = numbers
        corners = [coverage._apply(ctm, px, py) for px, py in ((x, y), (x + width, y), (x + width, y + height), (x, y + height))]
        path.move(corners[0])
        for corner in corners[1:]:
            path.add((corner,))
        path.close()


def read(stream: Any) -> list[Fill]:
    """The fills drawn in stream, in its space; Unsupported for anything a clip path cannot take."""
    fills: list[Fill] = []
    stack: list[Matrix] = []
    ctm = coverage.IDENTITY
    path = _Path()
    operands: list[bytes] = []
    for token in coverage._tokens(stream):
        if coverage._is_operand(token):
            operands.append(token)
            continue
        numbers = [float(value) for value in operands if value[:1] not in b"/[]"]
        if token == b"q":
            stack.append(ctm)
        elif token == b"Q":
            ctm = stack.pop()
        elif token == b"cm":
            ctm = coverage._concat(coverage._matrix(numbers), ctm)
        elif token in (b"m", b"l", b"c", b"v", b"y", b"h", b"re"):
            _construct(path, token, numbers, ctm)
        elif token in (b"f", b"F", b"f*"):
            fills.append(Fill(path.done(), token == b"f*"))
            path = _Path()
        elif token == b"n":
            path = _Path()
        elif token == b"gs":
            _plain_state(stream._resources["ExtGState"][operands[0][1:].decode()])
        elif token not in _STYLE:
            raise Unsupported(token.decode("latin-1"))
        operands = []
    return fills


def _plain_state(values: Any) -> None:
    """A graphics state the fills of a clip path may set: opaque, without a soft mask or blend mode."""
    for key, value in values.items():
        if key in ("ca", "CA") and float(value) == 1:
            continue
        if not (key == "Type" or (key == "BM" and value in ("/Normal", "/Compatible")) or (key == "SMask" and value == "/None")):
            raise Unsupported(f"graphics state {key}")


def union(fills: list[Fill]) -> list[Subpath]:
    """The subpaths of one path whose nonzero fill is the union of fills."""
    return [subpath for fill in fills for subpath in _oriented(fill)]


def _oriented(fill: Fill) -> list[Subpath]:
    """The subpaths of fill, each turned so that the winding is 1 inside the fill and 0 outside it."""
    subpaths = fill.subpaths
    if not subpaths:
        return []
    points = [point for subpath in subpaths for point in subpath.points()]
    size = math.dist((min(x for x, _ in points), min(y for _, y in points)), (max(x for x, _ in points), max(y for _, y in points)))
    rings = [subpath.ring(max(size * FLATNESS, 1e-9)) for subpath in subpaths]
    drawn = [(subpath, ring) for subpath, ring in zip(subpaths, rings, strict=True) if len(ring) > 2]
    if sum(len(ring) for _, ring in drawn) > MAX_SEGMENTS:
        raise Unsupported("a clip path of too many segments")
    if _crossing([ring for _, ring in drawn]):
        raise Unsupported("a clip path whose subpaths cross")
    # A subpath that crosses nothing and has no area is a line there and back: it fills nothing
    kept = [(subpath, ring, area) for subpath, ring in drawn if (area := shapeblur.signed_area(ring))]
    # The subpaths that hold each one: they do not cross, so one point tells
    holders = [[other for other in range(len(kept)) if other != index and _winding(kept[other][1], kept[index][1][0])] for index in range(len(kept))]

    def filled(index: int) -> bool:
        winding = sum(1 if kept[holder][2] > 0 else -1 for holder in (index, *holders[index]))
        return winding % 2 == 1 if fill.even_odd else winding != 0

    out = []
    for index, (subpath, _, area) in enumerate(kept):
        # The parent face is the inside of the smallest holder, or the outside of all
        parent = min(holders[index], key=lambda holder: abs(kept[holder][2]), default=None)
        step = int(filled(index)) - (int(filled(parent)) if parent is not None else 0)
        if step:
            out.append(subpath if (step > 0) == (area > 0) else subpath.reversed())
    return out


def _winding(ring: Ring, point: Point) -> int:
    """The winding number of ring around point."""
    x, y = point
    winding = 0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1], strict=True):
        side = (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0)
        if y0 <= y < y1 and side > 0:
            winding += 1
        elif y1 <= y < y0 and side < 0:
            winding -= 1
    return winding


def _crossing(rings: list[Ring]) -> bool:
    """Whether two edges of rings meet anywhere but at the point two neighbors share."""
    edges = []
    for number, ring in enumerate(rings):
        count = len(ring)
        for index in range(count):
            start, end = ring[index], ring[(index + 1) % count]
            edges.append((min(start[0], end[0]), max(start[0], end[0]), start, end, number, index, count))
    edges.sort()
    for position, (_, right, start, end, number, index, count) in enumerate(edges):
        for other_left, _, other_start, other_end, other_number, other_index, _ in edges[position + 1 :]:
            if other_left > right:
                break
            if other_number == number and (other_index - index) % count in (1, count - 1):
                continue  # neighbors share a point
            if _meet(start, end, other_start, other_end):
                return True
    return False


def _side(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _meet(a: Point, b: Point, c: Point, d: Point) -> bool:
    """Whether segments ab and cd share a point, touching included."""
    if max(a[1], b[1]) < min(c[1], d[1]) or max(c[1], d[1]) < min(a[1], b[1]):
        return False
    d1, d2, d3, d4 = _side(c, d, a), _side(c, d, b), _side(a, b, c), _side(a, b, d)
    if ((d1 > 0) != (d2 > 0) and d1 and d2) and ((d3 > 0) != (d4 > 0) and d3 and d4):
        return True

    def on(p: Point, q: Point, r: Point, side: float) -> bool:
        return side == 0 and min(p[0], q[0]) <= r[0] <= max(p[0], q[0]) and min(p[1], q[1]) <= r[1] <= max(p[1], q[1])

    return on(c, d, a, d1) or on(c, d, b, d2) or on(a, b, c, d3) or on(a, b, d, d4)


def add(stream: Any, subpaths: list[Subpath]) -> None:
    """Add subpaths to the path of stream."""
    for subpath in subpaths:
        stream.move_to(*subpath.start)
        for segment in subpath.segments:
            if len(segment) == 1:
                stream.line_to(*segment[0])
            else:
                stream.curve_to(*segment[0], *segment[1], *segment[2])
        stream.close()
