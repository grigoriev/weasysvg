"""The coverage of any drawn content, per color, read back from the PDF operators WeasyPrint wrote for it.

Chromium blurs the pixels of a filtered element: a group, a stroke, several shapes of several colors. The
levels of filters._blur_mask grow each shape by its nearest edge instead: a corner came out mitered, a
stroke stepped, and a stroke thinner than a few deviations far too dark.

Here the element is drawn into a scratch group and its operators are read back: paths, strokes, clips,
constant opacities and transparency groups. A stroke becomes polygons, its joins and caps included. The
shapes are sampled on the grid of shapeblur.Field and composited in order, each color on its own image:
color k ends up with the share of the pixel it paints. Blurred, those shares are the premultiplied blur of
the content. Anything else (text, images, shadings, patterns, soft masks, blend modes, dashes) raises
Unsupported: the levels draw it.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from typing import Any

from PIL import Image, ImageChops

from . import shapeblur
from .shapeblur import Point, Ring

Matrix = tuple[float, float, float, float, float, float]
RGB = tuple[float, float, float]
Box = tuple[int, int, int, int]  # left, top, right, bottom in samples
Clip = tuple[tuple[Ring, ...], str]  # rings in content space, and their rule

IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
MAX_COLORS = 4  # colors one content may paint: each is one more mesh, and 64 bytes a cell while sampled
MIN_ARC_POINTS, MAX_ARC_POINTS = 8, 256
MITER, ROUND, BEVEL = 0, 1, 2  # line joins, as the j operator numbers them
BUTT, SQUARE = 0, 2  # line caps, as the J operator numbers them; 1 is round
# The tokens of a content stream, tried in order: a name, a number, an operator, else one character alone
_NAME = rb"/[^\s/\[\]()<>]+"
_NUMBER = rb"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_OPERATOR = rb"[A-Za-z'\"*]+"
_TOKEN = re.compile(b"|".join((_NAME, _NUMBER, _OPERATOR, rb"\S")))
# Operators that change nothing the coverage reads: marked content, flatness, rendering intent
_IGNORED = frozenset((b"BDC", b"BMC", b"EMC", b"MP", b"DP", b"i", b"ri"))


class Unsupported(Exception):
    """The content holds something its coverage cannot take."""


@dataclass
class Shape:
    """One painted path: its rings in content space, filled by rule (nonzero, evenodd, or union for a stroke)."""

    rings: list[Ring]
    rule: str
    alpha: float
    color: RGB
    clips: tuple[Clip, ...] = ()


@dataclass
class Group:
    """A transparency group, painted at alpha as one, through the clips current where it is painted."""

    items: list[Shape | Group] = field(default_factory=list)
    alpha: float = 1.0
    clips: tuple[Clip, ...] = ()

    def shapes(self) -> Iterator[Shape]:
        for item in self.items:
            if isinstance(item, Group):
                yield from item.shapes()
            else:
                yield item

    def colors(self) -> list[RGB]:
        """The colors, in the order they first paint: the first one lies under all others."""
        return list(dict.fromkeys(shape.color for shape in self.shapes()))


# ---------------- reading the operators ----------------


def _apply(matrix: Matrix, x: float, y: float) -> Point:
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


def _concat(first: Matrix, then: Matrix) -> Matrix:
    """first, then then: the cm operator puts its matrix before the current one."""
    a, b, c, d, e, f = first
    p, q, r, s, t, u = then
    return a * p + b * r, a * q + b * s, c * p + d * r, c * q + d * s, e * p + f * r + t, e * q + f * s + u


@dataclass
class _State:
    ctm: Matrix = IDENTITY
    width: float = 1.0
    cap: int = BUTT
    join: int = MITER
    miter: float = 10.0
    dashed: bool = False
    fill: RGB = (0.0, 0.0, 0.0)
    stroke: RGB = (0.0, 0.0, 0.0)
    fill_alpha: float = 1.0
    stroke_alpha: float = 1.0
    clips: tuple[Clip, ...] = ()

    def in_group(self, ctm: Matrix) -> _State:
        """The state a transparency group starts from, in its matrix: no clip, opacity or blend mode of its own."""
        return _State(ctm, self.width, self.cap, self.join, self.miter, self.dashed, self.fill, self.stroke)

    def in_form(self, ctm: Matrix, clips: tuple[Clip, ...]) -> _State:
        """The state a form without a group starts from: this one, in its matrix, clipped to its box."""
        return _State(ctm, self.width, self.cap, self.join, self.miter, self.dashed, self.fill, self.stroke, self.fill_alpha, self.stroke_alpha, clips)


@dataclass
class _Subpath:
    points: list[Point]
    smooth: list[bool]  # whether the outline turns smoothly at each point, inside a flattened curve
    closed: bool = False


def _tokens(stream: Any) -> Iterator[bytes]:
    for item in stream.stream:
        yield from _TOKEN.findall(item if isinstance(item, bytes) else str(item).encode("latin-1"))


def _is_operand(token: bytes) -> bool:
    """Whether token is a name, an array bracket or a number: what an operator takes, not an operator."""
    return token[:1] in b"/[]-+." or token[:1].isdigit()


def _set_state(state: _State, token: bytes, numbers: list[float]) -> bool:
    """Apply an operator that changes the graphics state alone; False for any other operator."""
    if token == b"cm":
        state.ctm = _concat(_matrix(numbers), state.ctm)
    elif token == b"w":
        state.width = numbers[0]
    elif token == b"J":
        state.cap = int(numbers[0])
    elif token == b"j":
        state.join = int(numbers[0])
    elif token == b"M":
        state.miter = numbers[0]
    elif token == b"d":
        state.dashed = any(numbers[:-1])
    elif token in (b"rg", b"g"):
        state.fill = _rgb(token, numbers)
    elif token in (b"RG", b"G"):
        state.stroke = _rgb(token, numbers)
    else:
        return False
    return True


def _matrix(values: Any) -> Matrix:
    a, b, c, d, e, f = (float(value) for value in values)
    return a, b, c, d, e, f


def _rgb(token: bytes, numbers: list[float]) -> RGB:
    """The color of a gray (g, G) or an RGB (rg, RG) operator."""
    return (numbers[0],) * 3 if token in (b"g", b"G") else (numbers[0], numbers[1], numbers[2])


_CONSTRUCT = frozenset((b"m", b"l", b"c", b"v", b"y", b"h", b"re"))
_PAINT = frozenset((b"n", b"f", b"F", b"f*", b"S", b"s", b"B", b"B*", b"b", b"b*"))


class _Reader:
    """Reads one content stream, and the groups it paints, into a Group."""

    def __init__(self, flatness: float) -> None:
        self.flatness = flatness

    def read_content(self, stream: Any, group: Group, state: _State) -> None:
        resources = stream._resources
        stack: list[_State] = []
        path: list[_Subpath] = []
        clip: str | None = None
        operands: list[bytes] = []
        for token in _tokens(stream):
            if _is_operand(token):
                operands.append(token)
                continue
            numbers = [float(value) for value in operands if value[:1] not in b"/[]"]
            if token == b"q":
                stack.append(replace(state))
            elif token == b"Q":
                state = stack.pop()
            elif token in _CONSTRUCT:
                self.construct(path, token, numbers, state.ctm)
            elif token in (b"W", b"W*"):
                clip = "evenodd" if token == b"W*" else "nonzero"
            elif token in _PAINT:
                self.end_path(group, path, token, state, clip)
                path, clip = [], None
            elif token in (b"gs", b"Do"):
                self.use_resource(group, resources, token, operands[0][1:].decode(), state)
            elif not _set_state(state, token, numbers) and token not in _IGNORED:
                raise Unsupported(token.decode("latin-1"))
            operands = []

    def end_path(self, group: Group, path: list[_Subpath], token: bytes, state: _State, clip: str | None) -> None:
        """Paint path as token says, then clip what follows to it when W or W* came before token."""
        if token in (b"s", b"b", b"b*") and path:
            path[-1].closed = True
        self.paint(group, path, token, state)
        if clip is not None:
            rings = tuple(self.fill_rings(path, state.ctm))
            state.clips = (*state.clips, (rings, clip))

    def construct(self, path: list[_Subpath], token: bytes, numbers: list[float], ctm: Matrix) -> None:
        if token == b"m":
            path.append(_Subpath([(numbers[0], numbers[1])], [False]))
            return
        if token == b"re":
            x, y, width, height = numbers
            path.append(_Subpath([(x, y), (x + width, y), (x + width, y + height), (x, y + height)], [False] * 4, closed=True))
            return
        if not path:
            raise Unsupported("a path without a current point")
        current = path[-1]
        if token == b"h":
            current.closed = True
            return
        if current.closed:
            # After a close the next segment starts a new subpath at the start of the closed one
            current = _Subpath([current.points[0]], [False])
            path.append(current)
        if token == b"l":
            current.points.append((numbers[0], numbers[1]))
            current.smooth.append(False)
            return
        start = current.points[-1]
        if token == b"c":
            controls = [(numbers[0], numbers[1]), (numbers[2], numbers[3]), (numbers[4], numbers[5])]
        elif token == b"v":
            controls = [start, (numbers[0], numbers[1]), (numbers[2], numbers[3])]
        else:
            controls = [(numbers[0], numbers[1]), (numbers[2], numbers[3]), (numbers[2], numbers[3])]
        points = _flattened(start, controls, self.flatness / _scale(ctm))
        current.points.extend(points)
        current.smooth.extend([True] * (len(points) - 1) + [False])

    @staticmethod
    def fill_rings(path: list[_Subpath], ctm: Matrix) -> Iterator[Ring]:
        for subpath in path:
            if len(subpath.points) > 2:
                yield [_apply(ctm, x, y) for x, y in subpath.points]

    def paint(self, group: Group, path: list[_Subpath], token: bytes, state: _State) -> None:
        fills, strokes = token in (b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*"), token in (b"S", b"s", b"B", b"B*", b"b", b"b*")
        if fills and state.fill_alpha > 0:
            rings = list(self.fill_rings(path, state.ctm))
            if rings:
                group.items.append(Shape(rings, "evenodd" if token.endswith(b"*") else "nonzero", state.fill_alpha, state.fill, state.clips))
        if strokes and state.stroke_alpha > 0 and state.width > 0:
            if state.dashed:
                raise Unsupported("dashes")
            outline = [[_apply(state.ctm, x, y) for x, y in polygon] for polygon in _stroked(path, state, self.flatness / _scale(state.ctm))]
            if outline:
                group.items.append(Shape(outline, "union", state.stroke_alpha, state.stroke, state.clips))

    def use_resource(self, group: Group, resources: Any, token: bytes, name: str, state: _State) -> None:
        """Apply the graphics state (gs) or paint the group (Do) that name stands for in resources."""
        if token == b"gs":
            self.graphics_state(resources["ExtGState"][name], state)
        else:
            self.paint_group(group, resources["XObject"].get(name), state)

    @staticmethod
    def graphics_state(values: Any, state: _State) -> None:
        for key, value in values.items():
            if key == "ca":
                state.fill_alpha = float(value)
            elif key == "CA":
                state.stroke_alpha = float(value)
            elif not (key == "Type" or (key == "BM" and value in ("/Normal", "/Compatible"))):
                raise Unsupported(f"graphics state {key}")

    def paint_group(self, group: Group, xobject: Any, state: _State) -> None:
        extra = getattr(xobject, "extra", None) or {}
        if extra.get("Subtype") != "/Form":
            raise Unsupported("an image")
        ctm = _concat(_matrix(extra.get("Matrix", IDENTITY)), state.ctm)
        # The group is clipped to its box
        x0, y0, x1, y1 = (float(value) for value in extra["BBox"])
        box = [_apply(ctm, x, y) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        clips = (*state.clips, ((box,), "nonzero"))
        if "Group" not in extra:
            # A form that is no group paints as if its content stood here: the drawing of an SVG image
            self.read_content(xobject, group, state.in_form(ctm, clips))
            return
        inner = Group(alpha=state.fill_alpha, clips=clips)
        self.read_content(xobject, inner, state.in_group(ctm))
        if inner.items:
            group.items.append(inner)


def read(stream: Any, flatness: float) -> Group:
    """The content drawn in stream, curves flattened to within about flatness in content space."""
    group = Group()
    _Reader(flatness).read_content(stream, group, _State())
    return group


def _scale(matrix: Matrix) -> float:
    """The largest stretch of matrix: a flatness in content space, divided by it, holds in user space."""
    a, b, c, d, _, _ = matrix
    return max(math.hypot(a, b), math.hypot(c, d), 1e-9)


def _flattened(start: Point, controls: list[Point], flatness: float) -> list[Point]:
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = start, *controls
    reach = math.dist((x0, y0), (x1, y1)) + math.dist((x1, y1), (x2, y2)) + math.dist((x2, y2), (x3, y3))
    steps = max(2, min(64, math.ceil(reach / flatness)))
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        u = 1 - t
        a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
        out.append((a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3))
    return out


# ---------------- strokes as polygons ----------------


def _circle(center: Point, radius: float, flatness: float) -> Ring:
    # A chord of an arc of pi / steps sags radius * (1 - cos(pi / steps)): at most flatness
    steps = max(MIN_ARC_POINTS, min(MAX_ARC_POINTS, math.ceil(math.pi / math.acos(1 - min(flatness / radius, 1.0)))))
    return [(center[0] + radius * math.cos(2 * math.pi * k / steps), center[1] + radius * math.sin(2 * math.pi * k / steps)) for k in range(steps)]


def _stroked(path: list[_Subpath], state: _State, flatness: float) -> Iterator[Ring]:
    """The polygons whose union is the stroke of path, in user space: a quad per segment, joins and caps.

    The joins inside a flattened curve are bevels: the curve turns there by a sliver, it has no corner.
    """
    half = state.width / 2
    for subpath in path:
        if len(subpath.points) == 1:
            continue  # a moveto alone paints nothing
        points, smooth, closed = _distinct(subpath)
        if len(points) == 1:
            yield from _dot(points[0], state.cap, half, flatness)
        else:
            yield from _outline(points, smooth, closed, state, half, flatness)


def _distinct(subpath: _Subpath) -> tuple[list[Point], list[bool], bool]:
    """The points of subpath without repeats, their smoothness, and whether it is closed with an inside.

    A closed subpath that ends on its start drops that last point: the join there closes it.
    """
    points, smooth = [subpath.points[0]], [subpath.smooth[0]]
    for point, turn in zip(subpath.points[1:], subpath.smooth[1:], strict=True):
        if point != points[-1]:
            points.append(point)
            smooth.append(turn)
    closed = subpath.closed and len(points) > 2
    if closed and points[-1] == points[0]:
        points.pop()
        smooth.pop()
    return points, smooth, closed


def _dot(point: Point, cap: int, half: float, flatness: float) -> Iterator[Ring]:
    """A subpath of no length paints its caps only, along the x axis."""
    x, y = point
    if cap == SQUARE:
        yield [(x - half, y - half), (x + half, y - half), (x + half, y + half), (x - half, y + half)]
    elif cap != BUTT:
        yield _circle(point, half, flatness)


def _outline(points: list[Point], smooth: list[bool], closed: bool, state: _State, half: float, flatness: float) -> Iterator[Ring]:
    """The stroke of a subpath of two points or more: a quad per segment, its joins, and caps at open ends."""
    count = len(points)
    segments = [(points[i], points[(i + 1) % count]) for i in range(count if closed else count - 1)]
    normals = []
    for (x0, y0), (x1, y1) in segments:
        length = math.dist((x0, y0), (x1, y1))
        normals.append(((y0 - y1) / length * half, (x1 - x0) / length * half))
    for ((x0, y0), (x1, y1)), (nx, ny) in zip(segments, normals, strict=True):
        yield [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)]
    corners = range(count) if closed else range(1, count - 1)
    for i in corners:
        before, after = normals[i - 1], normals[i % len(normals)]
        yield from _join(points[i], before, after, BEVEL if smooth[i] else state.join, state.miter, half, flatness)
    if not closed:
        yield from _cap(points[0], normals[0], -1, state.cap, half, flatness)
        yield from _cap(points[-1], normals[-1], 1, state.cap, half, flatness)


def _join(point: Point, before: Point, after: Point, join: int, limit: float, half: float, flatness: float) -> Iterator[Ring]:
    if join == ROUND:
        yield _circle(point, half, flatness)
        return
    x, y = point
    # The outer side is where the outline turns away from: the normals there point outward
    turn = before[0] * after[1] - before[1] * after[0]
    side = -1 if turn > 0 else 1
    (ax, ay), (bx, by) = (before[0] * side, before[1] * side), (after[0] * side, after[1] * side)
    yield [(x, y), (x + ax, y + ay), (x + bx, y + by)]
    cosine = (ax * bx + ay * by) / (half * half)
    if join != MITER or cosine >= 1:
        return
    # The miter length over the width is 1 / sin(theta / 2), theta the angle between the segments
    if cosine <= -1 or math.sqrt(2 / (1 + cosine)) > limit:
        return
    mx, my = ax + bx, ay + by
    reach = half / math.sqrt((1 + cosine) / 2)
    norm = math.hypot(mx, my)
    yield [(x + ax, y + ay), (x + mx / norm * reach, y + my / norm * reach), (x + bx, y + by), (x, y)]


def _cap(point: Point, normal: Point, direction: int, cap: int, half: float, flatness: float) -> Iterator[Ring]:
    if cap == BUTT:
        return
    if cap != SQUARE:
        yield _circle(point, half, flatness)
        return
    x, y = point
    nx, ny = normal
    # Along the segment, outward: the normal turned back by a quarter
    tx, ty = ny * direction, -nx * direction
    yield [(x + nx, y + ny), (x + nx + tx, y + ny + ty), (x - nx + tx, y - ny + ty), (x - nx, y - ny)]


# ---------------- compositing on the grid ----------------


@dataclass
class _Layers:
    """The composited content over box: its alpha, and the share each color paints of it."""

    box: Box
    total: Image.Image
    colors: dict[RGB, Image.Image]

    @classmethod
    def empty(cls, box: Box) -> _Layers:
        return cls(box, Image.new("L", (box[2] - box[0], box[3] - box[1])), {})

    def over(self, other: _Layers) -> None:
        """Composite other, inside this box, over this content."""
        left, top = other.box[0] - self.box[0], other.box[1] - self.box[1]
        region = (left, top, left + other.total.width, top + other.total.height)
        clear = ImageChops.invert(other.total)
        for share in self.colors.values():
            share.paste(ImageChops.multiply(share.crop(region), clear), region)
        for rgb, share in other.colors.items():
            target = self.colors.setdefault(rgb, Image.new("L", self.total.size))
            target.paste(ImageChops.add(target.crop(region), share), region)
        self.total.paste(ImageChops.screen(self.total.crop(region), other.total), region)

    def scale(self, factor: Image.Image | float) -> None:
        """Multiply the content by a constant opacity, or by the coverage of a clip."""

        def scaled(image: Image.Image) -> Image.Image:
            return ImageChops.multiply(image, factor) if isinstance(factor, Image.Image) else image.point(lambda value: round(value * factor))

        self.total = scaled(self.total)
        self.colors = {rgb: scaled(share) for rgb, share in self.colors.items()}


class Raster:
    """The coverage of a Group on the grid of field, per color."""

    def __init__(self, content: Group, field_: shapeblur.Field) -> None:
        self.content, self.field = content, field_
        self.size = (field_.width * shapeblur.SUPERSAMPLE, field_.height * shapeblur.SUPERSAMPLE)

    def box(self, item: Shape | Group) -> Box:
        """The samples item may paint: the grid holds all of its shapes, a margin around them."""
        shapes = list(item.shapes()) if isinstance(item, Group) else [item]
        points = [shapeblur.to_samples(ring, self.field.to_grid) for shape in shapes for ring in shape.rings]
        xs, ys = [x for ring in points for x, _ in ring], [y for ring in points for _, y in ring]
        return max(math.floor(min(xs)) - 1, 0), max(math.floor(min(ys)) - 1, 0), min(math.ceil(max(xs)) + 2, self.size[0]), min(math.ceil(max(ys)) + 2, self.size[1])

    @property
    def work(self) -> int:
        """The cells the shapes cover, each counted once per shape: what sampling them costs."""
        boxes = [self.box(shape) for shape in self.content.shapes()]
        return sum((right - left) * (bottom - top) for left, top, right, bottom in boxes) // shapeblur.SUPERSAMPLE**2

    def inside(self, rings: list[Ring] | tuple[Ring, ...], rule: str, box: Box) -> Image.Image:
        points = [shapeblur.to_samples(ring, self.field.to_grid, box[0], box[1]) for ring in rings]
        signs = [1 if rule != "nonzero" or shapeblur._signed_area(ring) >= 0 else -1 for ring in points]
        return shapeblur.samples(points, signs, rule == "evenodd", (box[2] - box[0], box[3] - box[1]))

    def clipped(self, layers: _Layers, clips: tuple[Clip, ...]) -> None:
        for rings, rule in clips:
            layers.scale(self.inside(rings, rule, layers.box))

    def layers(self, item: Shape | Group, box: Box) -> _Layers:
        if isinstance(item, Shape):
            alpha = self.inside(item.rings, item.rule, box)
            out = _Layers(box, alpha, {item.color: alpha})
        else:
            out = _Layers.empty(box)
            for child in item.items:
                out.over(self.layers(child, self.box(child)))
        if item.alpha < 1:
            out.scale(item.alpha)
        self.clipped(out, item.clips)
        return out

    def coverage(self) -> tuple[Image.Image, dict[RGB, Image.Image]]:
        """The alpha and the share of each color on each cell, 0 to 255."""
        whole = _Layers.empty((0, 0, *self.size))
        whole.over(self.layers(self.content, self.box(self.content)))
        return whole.total.reduce(shapeblur.SUPERSAMPLE), {rgb: share.reduce(shapeblur.SUPERSAMPLE) for rgb, share in whole.colors.items()}


def ratios(shares: list[Image.Image]) -> list[Image.Image]:
    """The opacity of each color over the colors before it, so painted in order they mix as the shares say.

    Over the first color, flat, color k at B_k / (B_1 + ... + B_k) leaves each color at its share of the
    sum: the paint of a pixel is the premultiplied blur divided by its alpha.
    """
    out = []
    running = [0] * (shares[0].width * shares[0].height)
    for share in shares:
        values = share.tobytes()
        ratio = bytearray(len(values))
        for index, value in enumerate(values):
            running[index] += value
            ratio[index] = (255 * value + running[index] // 2) // running[index] if running[index] else 0
        out.append(Image.frombytes("L", share.size, bytes(ratio)))
    return out
