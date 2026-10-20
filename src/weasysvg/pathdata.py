"""SVG path data as segments: parsing, tangents, length and points along the path.

markers.py takes the tangents of each segment, text.py the points along the path for textPath.
Coordinates are user units, as in the d attribute.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass

Point = tuple[float, float]
PointAt = Callable[[int], Point]

_TOKEN = re.compile(r"\s*,?\s*([MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)")
_FLAG = re.compile(r"\s*,?\s*([01])")
_ARGUMENTS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}
FLATTEN_STEPS = 32  # chords per curve or arc for lengths and points along the path


@dataclass(frozen=True)
class Segment:
    """One piece of a path: move, line, close, cubic or arc. points holds the start, controls and end."""

    kind: str
    points: tuple[Point, ...]
    arc: tuple[float, float, float, float, float, float, float] | None = None  # cx, cy, rx, ry, phi, theta1, dtheta

    @property
    def start(self) -> Point:
        return self.points[0]

    @property
    def end(self) -> Point:
        return self.points[-1]

    def out_slope(self) -> Point:
        """The direction the segment leaves its start with."""
        if self.arc is not None:
            return _arc_tangent(self.arc, self.arc[5])
        return _first_nonzero(self.start, self.points[1:])

    def in_slope(self) -> Point:
        """The direction the segment reaches its end with."""
        if self.arc is not None:
            return _arc_tangent(self.arc, self.arc[5] + self.arc[6])
        return _first_nonzero_back(self.end, self.points[:-1])

    def at(self, t: float) -> Point:
        """The point at parameter t in [0, 1]."""
        if self.arc is not None:
            cx, cy, rx, ry, phi, theta1, dtheta = self.arc
            theta = theta1 + dtheta * t
            x, y = rx * math.cos(theta), ry * math.sin(theta)
            return cx + x * math.cos(phi) - y * math.sin(phi), cy + x * math.sin(phi) + y * math.cos(phi)
        if self.kind == "cubic":
            (x0, y0), (x1, y1), (x2, y2), (x3, y3) = self.points
            u = 1 - t
            return (u**3 * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t**3 * x3, u**3 * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t**3 * y3)
        (x0, y0), (x1, y1) = self.start, self.end
        return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t

    def polyline(self) -> list[Point]:
        if self.kind in ("cubic", "arc"):
            return [self.at(i / FLATTEN_STEPS) for i in range(FLATTEN_STEPS + 1)]
        return [self.start, self.end]


def _first_nonzero(origin: Point, points: tuple[Point, ...]) -> Point:
    for point in points:
        if point != origin:
            return point[0] - origin[0], point[1] - origin[1]
    return 0.0, 0.0


def _first_nonzero_back(end: Point, points: tuple[Point, ...]) -> Point:
    for point in reversed(points):
        if point != end:
            return end[0] - point[0], end[1] - point[1]
    return 0.0, 0.0


def _arc_tangent(arc: tuple[float, ...], theta: float) -> Point:
    _, _, rx, ry, phi, _, dtheta = arc
    dx, dy = -rx * math.sin(theta), ry * math.cos(theta)
    sign = 1 if dtheta >= 0 else -1
    return sign * (dx * math.cos(phi) - dy * math.sin(phi)), sign * (dx * math.sin(phi) + dy * math.cos(phi))


def _arc(start: Point, end: Point, rx: float, ry: float, angle: float, large: bool, sweep: bool) -> Segment:
    """An elliptical arc in center parameterization (SVG implementation notes, F.6.5 and F.6.6)."""
    rx, ry = abs(rx), abs(ry)
    if not rx or not ry:
        return Segment("line", (start, end))
    phi = math.radians(angle % 360)
    (x1, y1), (x2, y2) = start, end
    dx, dy = (x1 - x2) / 2, (y1 - y2) / 2
    xp, yp = math.cos(phi) * dx + math.sin(phi) * dy, -math.sin(phi) * dx + math.cos(phi) * dy
    scale = xp * xp / (rx * rx) + yp * yp / (ry * ry)
    if scale > 1:
        rx, ry = rx * math.sqrt(scale), ry * math.sqrt(scale)
    numerator = rx * rx * ry * ry - rx * rx * yp * yp - ry * ry * xp * xp
    denominator = rx * rx * yp * yp + ry * ry * xp * xp
    factor = math.sqrt(max(numerator, 0) / denominator) if denominator else 0.0
    if large == sweep:
        factor = -factor
    cxp, cyp = factor * rx * yp / ry, -factor * ry * xp / rx
    cx = math.cos(phi) * cxp - math.sin(phi) * cyp + (x1 + x2) / 2
    cy = math.sin(phi) * cxp + math.cos(phi) * cyp + (y1 + y2) / 2
    theta1 = math.atan2((yp - cyp) / ry, (xp - cxp) / rx)
    theta2 = math.atan2((-yp - cyp) / ry, (-xp - cxp) / rx)
    dtheta = theta2 - theta1
    if sweep and dtheta < 0:
        dtheta += 2 * math.pi
    elif not sweep and dtheta > 0:
        dtheta -= 2 * math.pi
    return Segment("arc", (start, end), (cx, cy, rx, ry, phi, theta1, dtheta))


class _Scanner:
    def __init__(self, data: str) -> None:
        self.data, self.position = data, 0

    def token(self) -> str | None:
        match = _TOKEN.match(self.data, self.position)
        if not match:
            return None
        self.position = match.end()
        return match.group(1)

    def peek_number(self) -> bool:
        match = _TOKEN.match(self.data, self.position)
        return bool(match and not match.group(1).isalpha())

    def number(self) -> float:
        token = self.token()
        if token is None or token.isalpha():
            raise ValueError("number expected")
        return float(token)

    def flag(self) -> bool:
        match = _FLAG.match(self.data, self.position)
        if not match:
            raise ValueError("flag expected")
        self.position = match.end()
        return match.group(1) == "1"


def _arguments(scanner: _Scanner, command: str) -> list[float]:
    if command.upper() != "A":
        return [scanner.number() for _ in range(_ARGUMENTS[command.upper()])]
    rx, ry, angle = scanner.number(), scanner.number(), scanner.number()
    large, sweep = scanner.flag(), scanner.flag()
    return [rx, ry, angle, float(large), float(sweep), scanner.number(), scanner.number()]


class _Builder:
    """The state of the parse: current point, subpath start and the last control point."""

    def __init__(self) -> None:
        self.segments: list[Segment] = []
        self.current: Point = (0.0, 0.0)
        self.start: Point = (0.0, 0.0)
        self.control: Point | None = None  # for S and T
        self.previous = ""

    def add(self, command: str, values: list[float]) -> None:
        relative = command.islower()
        upper = command.upper()
        cx, cy = self.current if relative else (0.0, 0.0)

        def point(i: int) -> Point:
            return values[i] + cx, values[i + 1] + cy

        handler = getattr(self, f"_{upper}")
        handler(values, point, relative)
        self.previous = upper

    def _segment(self, segment: Segment, control: Point | None = None) -> None:
        self.segments.append(segment)
        self.current, self.control = segment.end, control

    def _M(self, values: list[float], point: PointAt, relative: bool) -> None:  # noqa: N802
        end = point(0)
        self._segment(Segment("move", (self.current, end)))
        self.start = end

    def _L(self, values: list[float], point: PointAt, relative: bool) -> None:  # noqa: N802
        self._segment(Segment("line", (self.current, point(0))))

    def _H(self, values: list[float], point: PointAt, relative: bool) -> None:  # noqa: N802
        x = values[0] + (self.current[0] if relative else 0)
        self._segment(Segment("line", (self.current, (x, self.current[1]))))

    def _V(self, values: list[float], point: PointAt, relative: bool) -> None:  # noqa: N802
        y = values[0] + (self.current[1] if relative else 0)
        self._segment(Segment("line", (self.current, (self.current[0], y))))

    def _C(self, values: list[float], point: PointAt, relative: bool) -> None:  # noqa: N802
        c1, c2, end = point(0), point(2), point(4)
        self._segment(Segment("cubic", (self.current, c1, c2, end)), c2)

    def _S(self, values: list[float], point: PointAt, relative: bool) -> None:  # noqa: N802
        c1 = self._reflected("CS")
        c2, end = point(0), point(2)
        self._segment(Segment("cubic", (self.current, c1, c2, end)), c2)

    def _Q(self, values: list[float], point: PointAt, relative: bool) -> None:  # noqa: N802
        self._quad(point(0), point(2))

    def _T(self, values: list[float], point: PointAt, relative: bool) -> None:  # noqa: N802
        self._quad(self._reflected("QT"), point(0))

    def _A(self, values: list[float], point: PointAt, relative: bool) -> None:  # noqa: N802
        end = point(5)
        if end == self.current:
            return  # an arc to its own start is omitted
        self._segment(_arc(self.current, end, values[0], values[1], values[2], bool(values[3]), bool(values[4])))

    def _Z(self, values: list[float], point: PointAt, relative: bool) -> None:  # noqa: N802
        self._segment(Segment("close", (self.current, self.start)))

    def _reflected(self, kinds: str) -> Point:
        if self.previous in kinds and self.control is not None:
            return 2 * self.current[0] - self.control[0], 2 * self.current[1] - self.control[1]
        return self.current

    def _quad(self, control: Point, end: Point) -> None:
        (x0, y0), (qx, qy) = self.current, control
        c1 = x0 + 2 / 3 * (qx - x0), y0 + 2 / 3 * (qy - y0)
        c2 = end[0] + 2 / 3 * (qx - end[0]), end[1] + 2 / 3 * (qy - end[1])
        self._segment(Segment("cubic", (self.current, c1, c2, end)), control)


def parse(data: str | None) -> list[Segment]:
    """The segments of a d attribute, up to the first error, as SVG renders a path in error."""
    scanner, builder = _Scanner(data or ""), _Builder()
    command = None
    try:
        while True:
            if command is None or command in "Zz" or not scanner.peek_number():
                token = scanner.token()
                if token is None or not token.isalpha() or (command is None and token not in "Mm"):
                    break
                command = token
                if command in "Zz":
                    builder.add(command, [])
                    continue
            builder.add(command, _arguments(scanner, command))
            # Pairs after a moveto are linetos
            command = {"M": "L", "m": "l"}.get(command, command)
    except ValueError:
        pass
    return builder.segments
