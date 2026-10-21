"""SVG path data as segments: parsing, tangents, length and points along the path.

markers.py takes the tangents of each segment, text.py the points along the path for textPath.
Coordinates are user units, as in the d attribute.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

Point = tuple[float, float]

COMMANDS = frozenset("MmLlHhVvCcSsQqTtAaZz")
_SPACES = " \t\n\r\f"
_DIGITS = "0123456789"
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
    # A radius whose square underflows to 0 draws the line a zero radius draws
    if not rx * rx or not ry * ry:
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
    """Commands, numbers and flags of path data, read left to right without backtracking."""

    def __init__(self, data: str) -> None:
        self.data, self.position = data, 0

    def _peek(self) -> str:
        return self.data[self.position] if self.position < len(self.data) else ""

    def _skip(self) -> None:
        """Spaces, at most one comma, spaces."""
        while self._peek() and self._peek() in _SPACES:
            self.position += 1
        if self._peek() == ",":
            self.position += 1
            while self._peek() and self._peek() in _SPACES:
                self.position += 1

    def _digits(self) -> int:
        start = self.position
        while self._peek() and self._peek() in _DIGITS:
            self.position += 1
        return self.position - start

    def command(self) -> str | None:
        self._skip()
        character = self._peek()
        if character not in COMMANDS:
            return None
        self.position += 1
        return character

    def at_number(self) -> bool:
        self._skip()
        return bool(self._peek()) and self._peek() in "+-." + _DIGITS

    def number(self) -> float:
        self._skip()
        start = self.position
        if self._peek() in ("+", "-"):
            self.position += 1
        digits = self._digits()
        if self._peek() == ".":
            self.position += 1
            digits += self._digits()
        if not digits:
            raise ValueError("number expected")
        exponent = self.position
        if self._peek() in ("e", "E"):
            self.position += 1
            if self._peek() in ("+", "-"):
                self.position += 1
            if not self._digits():
                self.position = exponent  # an e without digits ends the number
        return float(self.data[start : self.position])

    def flag(self) -> bool:
        self._skip()
        character = self._peek()
        if character not in ("0", "1"):
            raise ValueError("flag expected")
        self.position += 1
        return character == "1"


def _arguments(scanner: _Scanner, command: str) -> list[float]:
    if command.upper() != "A":
        return [scanner.number() for _ in range(_ARGUMENTS[command.upper()])]
    rx, ry, angle = scanner.number(), scanner.number(), scanner.number()
    large, sweep = scanner.flag(), scanner.flag()
    return [rx, ry, angle, float(large), float(sweep), scanner.number(), scanner.number()]


@dataclass(frozen=True)
class _Arguments:
    """The numbers of one command, and the origin its coordinates count from."""

    values: list[float]
    origin: Point

    def point(self, index: int) -> Point:
        return self.values[index] + self.origin[0], self.values[index + 1] + self.origin[1]


class _Builder:
    """The state of the parse: current point, subpath start and the last control point."""

    def __init__(self) -> None:
        self.segments: list[Segment] = []
        self.current: Point = (0.0, 0.0)
        self.start: Point = (0.0, 0.0)
        self.control: Point | None = None  # for S and T
        self.previous = ""

    def add(self, command: str, values: list[float]) -> None:
        upper = command.upper()
        _HANDLERS[upper](self, _Arguments(values, self.current if command.islower() else (0.0, 0.0)))
        self.previous = upper

    def segment(self, segment: Segment, control: Point | None = None) -> None:
        self.segments.append(segment)
        self.current, self.control = segment.end, control

    def reflected(self, kinds: str) -> Point:
        if self.previous in kinds and self.control is not None:
            return 2 * self.current[0] - self.control[0], 2 * self.current[1] - self.control[1]
        return self.current

    def quad(self, control: Point, end: Point) -> None:
        (x0, y0), (qx, qy) = self.current, control
        c1 = x0 + 2 / 3 * (qx - x0), y0 + 2 / 3 * (qy - y0)
        c2 = end[0] + 2 / 3 * (qx - end[0]), end[1] + 2 / 3 * (qy - end[1])
        self.segment(Segment("cubic", (self.current, c1, c2, end)), control)


def _move(builder: _Builder, arguments: _Arguments) -> None:
    end = arguments.point(0)
    builder.segment(Segment("move", (builder.current, end)))
    builder.start = end


def _line(builder: _Builder, arguments: _Arguments) -> None:
    builder.segment(Segment("line", (builder.current, arguments.point(0))))


def _horizontal(builder: _Builder, arguments: _Arguments) -> None:
    end = (arguments.values[0] + arguments.origin[0], builder.current[1])
    builder.segment(Segment("line", (builder.current, end)))


def _vertical(builder: _Builder, arguments: _Arguments) -> None:
    end = (builder.current[0], arguments.values[0] + arguments.origin[1])
    builder.segment(Segment("line", (builder.current, end)))


def _cubic(builder: _Builder, arguments: _Arguments) -> None:
    c1, c2, end = arguments.point(0), arguments.point(2), arguments.point(4)
    builder.segment(Segment("cubic", (builder.current, c1, c2, end)), c2)


def _smooth_cubic(builder: _Builder, arguments: _Arguments) -> None:
    c1, c2, end = builder.reflected("CS"), arguments.point(0), arguments.point(2)
    builder.segment(Segment("cubic", (builder.current, c1, c2, end)), c2)


def _quadratic(builder: _Builder, arguments: _Arguments) -> None:
    builder.quad(arguments.point(0), arguments.point(2))


def _smooth_quadratic(builder: _Builder, arguments: _Arguments) -> None:
    builder.quad(builder.reflected("QT"), arguments.point(0))


def _elliptical_arc(builder: _Builder, arguments: _Arguments) -> None:
    end = arguments.point(5)
    if end == builder.current:
        return  # an arc to its own start is omitted
    rx, ry, angle, large, sweep = arguments.values[:5]
    builder.segment(_arc(builder.current, end, rx, ry, angle, bool(large), bool(sweep)))


def _close(builder: _Builder, _arguments: _Arguments) -> None:
    builder.segment(Segment("close", (builder.current, builder.start)))


_HANDLERS: dict[str, Callable[[_Builder, _Arguments], None]] = {
    "M": _move,
    "L": _line,
    "H": _horizontal,
    "V": _vertical,
    "C": _cubic,
    "S": _smooth_cubic,
    "Q": _quadratic,
    "T": _smooth_quadratic,
    "A": _elliptical_arc,
    "Z": _close,
}


def _read(data: str | None) -> tuple[list[tuple[str, list[float]]], int, str | None]:
    """The commands of path data with their numbers, up to the first error, as SVG renders a path in error.

    Also where reading stopped and the command in force there.
    """
    scanner = _Scanner(data or "")
    commands: list[tuple[str, list[float]]] = []
    command = None
    mark = 0
    try:
        while True:
            mark = scanner.position
            if command is None or command in "Zz" or not scanner.at_number():
                token = scanner.command()
                if token is None or (command is None and token not in "Mm"):
                    break
                command = token
                if command in "Zz":
                    commands.append((command, []))
                    continue
            commands.append((command, _arguments(scanner, command)))
            # Pairs after a moveto are linetos
            command = {"M": "L", "m": "l"}.get(command, command)
    except ValueError:
        pass
    return commands, mark, command


def parse(data: str | None) -> list[Segment]:
    """The segments of a d attribute, up to the first error, as SVG renders a path in error."""
    builder = _Builder()
    for command, values in _read(data)[0]:
        builder.add(command, values)
    return builder.segments


def _number(value: float) -> str:
    """A number as path data, written exactly."""
    text = repr(value)
    return text[:-2] if text.endswith(".0") else text


def _zero_radius(name: str, values: list[float]) -> bool:
    return name in "Aa" and (not values[0] or not values[1])


def _as_line(name: str, values: list[float], current: Point, smooth_next: bool) -> str | None:
    """The line an arc of a zero radius draws, None where it ends at the current point.

    Before a smooth curve it stays, as a line of no length: S and T reflect no control point past it.
    """
    origin = current if name == "a" else (0.0, 0.0)
    if (values[5] + origin[0], values[6] + origin[1]) == current and not smooth_next:
        return None
    return f"{'L' if name == 'A' else 'l'}{_number(values[5])} {_number(values[6])}"


def _tail(data: str, mark: int, command: str | None) -> list[str]:
    """The data past an error, as it is, with the command its leading numbers belong to."""
    tail = data[mark:].strip()
    if tail and command and tail[0] not in COMMANDS:
        tail = command + tail
    return [tail] if tail else []


# The path data as written, kept by paint.fix_arcs for the markers: the curves of a rewritten arc add
# vertices a marker must not see
ORIGINAL_D = "{https://github.com/grigoriev/weasysvg}d"
# An arc spanning more than this is split into curves of no more than it: one cubic Bezier strays from a
# circle by 0.03 % of its radius over 90 degrees, by 1.8 % over 180
ARC_PIECE = math.pi / 2


def _wide_arc(segment: Segment) -> bool:
    return segment.kind == "arc" and segment.arc is not None and abs(segment.arc[6]) > ARC_PIECE + 1e-9


def _as_curves(segment: Segment, smooth_next: bool) -> list[str]:
    """An elliptical arc as cubic Bezier curves of at most ARC_PIECE each, absolute.

    Before a smooth curve a line of no length follows: S and T reflect no control point of an arc.
    """
    assert segment.arc is not None
    cx, cy, rx, ry, phi, theta1, dtheta = segment.arc
    count = math.ceil(abs(dtheta) / ARC_PIECE - 1e-9)
    step = dtheta / count
    alpha = 4 / 3 * math.tan(step / 4)
    cos, sin = math.cos(phi), math.sin(phi)

    def point(theta: float) -> Point:
        x, y = rx * math.cos(theta), ry * math.sin(theta)
        return cx + cos * x - sin * y, cy + sin * x + cos * y

    def slope(theta: float) -> Point:
        x, y = -rx * math.sin(theta), ry * math.cos(theta)
        return cos * x - sin * y, sin * x + cos * y

    curves = []
    for index in range(count):
        start, end = theta1 + index * step, theta1 + (index + 1) * step
        (x0, y0), (dx0, dy0) = point(start), slope(start)
        (x3, y3), (dx3, dy3) = point(end), slope(end)
        if index == count - 1:
            x3, y3 = segment.points[-1]  # the end point as written, not as computed
        numbers = (x0 + alpha * dx0, y0 + alpha * dy0, x3 - alpha * dx3, y3 - alpha * dy3, x3, y3)
        curves.append("C" + " ".join(_number(value) for value in numbers))
    if smooth_next:
        curves.append(f"L{_number(segment.points[-1][0])} {_number(segment.points[-1][1])}")
    return curves


def rewritten_arcs(data: str | None) -> str | None:
    """The path data with the arcs WeasyPrint draws wrong written out, None when it has none.

    - An arc of a zero radius is the line to its end, as SVG says, and is omitted where it ends at the
      current point. WeasyPrint 70 writes it as a relative line to the absolute end point, so the line runs
      off by the current point: Highcharts closes every slice of a pie with one.
    - An arc wider than ARC_PIECE becomes curves of ARC_PIECE at most. WeasyPrint draws an arc of up to 180
      degrees as one curve, which bulges by 1.8 % of its radius: the band of the flag of Brazil.

    Data past an error stays as it is, for WeasyPrint to stop at.
    """
    commands, mark, command = _read(data)
    builder = _Builder()
    written: list[str] = []
    changed = False
    for index, (name, values) in enumerate(commands):
        smooth_next = index + 1 < len(commands) and commands[index + 1][0] in "SsTt"
        if _zero_radius(name, values):
            changed = True
            line = _as_line(name, values, builder.current, smooth_next)
            written.extend([line] if line else [])
            builder.add(name, values)
            continue
        count = len(builder.segments)
        builder.add(name, values)
        # An arc that ends where it starts adds no segment: the last one is still the one before
        if name in "Aa" and len(builder.segments) > count and _wide_arc(builder.segments[-1]):
            changed = True
            written.extend(_as_curves(builder.segments[-1], smooth_next))
        else:
            written.append(name + " ".join(_number(value) for value in values))
    return " ".join(written + _tail(data or "", mark, command)) if changed else None


class Polyline:
    """A path flattened to chords, for points and tangents at a distance along it."""

    def __init__(self, segments: list[Segment], transform: Callable[[float, float], Point] | None = None) -> None:
        self.points: list[Point] = []
        self.lengths: list[float] = []
        for segment in segments:
            if segment.kind != "move":
                for point in segment.polyline():
                    self._add(transform(*point) if transform else point)

    def _add(self, point: Point) -> None:
        if not self.points:
            self.points.append(point)
            self.lengths.append(0.0)
        elif point != self.points[-1]:
            (x0, y0), (x1, y1) = self.points[-1], point
            self.lengths.append(self.lengths[-1] + math.hypot(x1 - x0, y1 - y0))
            self.points.append(point)

    @property
    def length(self) -> float:
        return self.lengths[-1] if self.lengths else 0.0

    def at(self, distance: float) -> tuple[Point, float] | None:
        """The point at distance along the path and the angle of the path there, or None off the path."""
        if len(self.points) < 2 or not 0 <= distance <= self.length:
            return None
        low, high = 0, len(self.lengths) - 1
        while high - low > 1:
            middle = (low + high) // 2
            low, high = (middle, high) if self.lengths[middle] <= distance else (low, middle)
        (x0, y0), (x1, y1) = self.points[low], self.points[high]
        span = self.lengths[high] - self.lengths[low]
        t = (distance - self.lengths[low]) / span if span else 0.0
        return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t), math.atan2(y1 - y0, x1 - x0)
