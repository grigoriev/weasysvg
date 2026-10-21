"""The blur of a filled shape from its coverage, sampled on a grid of a third of a deviation.

The levels of filters._blur_mask grow and shrink the shape by its distance to the nearest edge. That
is the blur of a half plane: a shape thinner than a few deviations comes out far too dark and sharp, a
small dot keeps a dark core. Each level is one flat gray, so the tail shows rings. Chromium blurs the
coverage itself.

Here the outline WeasyPrint draws for the shape is recorded, its coverage sampled on a grid of a third
of a deviation and blurred with Pillow. filters.py writes the grid as a mesh of Gouraud shaded
triangles: the viewer interpolates between the samples, at any resolution, with no step. A blur has
nothing finer than its deviation: a third of it holds the profile. Pillow blurs in three box passes, as
Skia does, within some 3 levels of 255 of the exact Gaussian.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from PIL import Image, ImageChops, ImageDraw, ImageFilter

Point = tuple[float, float]
Ring = list[Point]

CELLS_PER_SIGMA = 3  # grid cells per standard deviation
SUPERSAMPLE = 8  # coverage samples per cell along each axis
MARGIN = 3.5  # deviations around the shape: the blurred coverage is below 1 / 4000 past it
MAX_CELLS = 160_000  # a larger grid falls back to the levels of the nearest edge
MAX_SIDE = 65_536  # samples along one side: the mesh writes grid indices as 16 bit coordinates
SHAPES = frozenset(("path", "circle", "ellipse", "rect", "polygon", "polyline"))
MARKERS = ("marker", "marker-start", "marker-mid", "marker-end")


class _Recorder:
    """A stand-in for the stream WeasyPrint draws a shape into: keeps the subpaths, curves flattened."""

    def __init__(self, flatness: float) -> None:
        self.flatness = flatness
        self.rings: list[Ring] = []
        self.current: Ring = []

    def move_to(self, x: float, y: float) -> None:
        self.current = [(x, y)]
        self.rings.append(self.current)

    def line_to(self, x: float, y: float) -> None:
        if not self.current:
            self.move_to(x, y)
        else:
            self.current.append((x, y))

    def curve_to(self, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float) -> None:
        if not self.current:
            self.move_to(x1, y1)
        x0, y0 = self.current[-1]
        reach = math.dist((x0, y0), (x1, y1)) + math.dist((x1, y1), (x2, y2)) + math.dist((x2, y2), (x3, y3))
        steps = max(2, min(64, math.ceil(reach / self.flatness)))
        for i in range(1, steps + 1):
            t = i / steps
            u = 1 - t
            a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
            self.current.append((a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3))

    def close(self) -> None:
        if self.current:
            self.current = [self.current[0]]
            self.rings.append(self.current)

    def rectangle(self, x: float, y: float, width: float, height: float) -> None:
        self.move_to(x, y)
        for point in ((x + width, y), (x + width, y + height), (x, y + height)):
            self.line_to(*point)
        self.close()


def eligible(node: Any) -> bool:
    """Whether node is one filled shape without stroke or markers: its outline is all it paints."""
    if node.tag not in SHAPES or node.get("fill", "black") == "none":
        return False
    if node.get("stroke", "none") != "none" and node.get("stroke-width", "1").strip() not in ("0", "0px"):
        return False
    return not any(node.get(name) not in (None, "", "none") for name in MARKERS)


def outline(svg: Any, node: Any, font_size: float, draw: Callable[[Any, Any, float], Any], flatness: float) -> list[Ring]:
    """The subpaths draw records for node, in user units, flattened to within about flatness."""
    recorder = _Recorder(flatness)
    # Drawing a shape adds to its vertices, a deque the markers read later: put the same one back as it was
    stream, vertices = svg.stream, node.vertices
    saved = list(vertices)
    svg.stream = recorder
    try:
        draw(svg, node, font_size)
    finally:
        svg.stream = stream
        vertices.clear()
        vertices.extend(saved)
        node.vertices = vertices
    return [ring for ring in recorder.rings if len(ring) > 2]


def _signed_area(ring: Ring) -> float:
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1], strict=True)) / 2


def _inside(rings: list[list[Point]], signs: list[int], even_odd: bool, big: tuple[int, int]) -> Image.Image:
    """The samples inside the rings, already in sample coordinates: 255 inside, 0 outside.

    Nonzero counts each subpath by its direction, which is the winding number wherever no subpath
    crosses itself.
    """
    counts = {1: Image.new("L", big), -1: Image.new("L", big)}
    for points, sign in zip(rings, signs, strict=True):
        # Each subpath is drawn in its own box only: a path may hold hundreds of them
        left, top = max(math.floor(min(x for x, _ in points)) - 1, 0), max(math.floor(min(y for _, y in points)) - 1, 0)
        right, bottom = min(math.ceil(max(x for x, _ in points)) + 2, big[0]), min(math.ceil(max(y for _, y in points)) + 2, big[1])
        if right <= left or bottom <= top:
            continue  # a clip may lie beside the samples it is cut to
        layer = Image.new("L", (right - left, bottom - top))
        ImageDraw.Draw(layer).polygon([(x - left, y - top) for x, y in points], fill=1)
        box = (left, top, right, bottom)
        counts[sign].paste(ImageChops.add(counts[sign].crop(box), layer), box)
    winding = ImageChops.difference(counts[1], counts[-1])
    inside: Callable[[int], int] = (lambda value: value % 2) if even_odd else (lambda value: value)
    return winding.point(lambda value: 255 if inside(value) else 0)


def _coverage(rings: list[Ring], even_odd: bool, size: tuple[int, int], to_grid: Callable[[Point], Point]) -> Image.Image:
    """The share of each cell the shape covers, 0 to 255, from SUPERSAMPLE squared samples per cell.

    Pillow fills a sample where the outline enters a row or column even when its center lies outside:
    the shape grows by one sample on its left and top, a 24th of the deviation, which moved the blurred
    edge by 4 levels. Drawn once more turned by 180 degrees it grows on the other sides: the samples both
    fill are those whose center lies inside.
    """
    big = (size[0] * SUPERSAMPLE, size[1] * SUPERSAMPLE)
    signs = [1 if even_odd or _signed_area(ring) >= 0 else -1 for ring in rings]
    return samples([to_samples(ring, to_grid) for ring in rings], signs, even_odd, big).reduce(SUPERSAMPLE)


def to_samples(ring: Ring, to_grid: Callable[[Point], Point], left: int = 0, top: int = 0) -> list[Point]:
    """ring in sample coordinates, the sample (left, top) at the origin."""
    # Pillow puts integer coordinates on the centers of its pixels
    return [(x * SUPERSAMPLE - 0.5 - left, y * SUPERSAMPLE - 0.5 - top) for x, y in map(to_grid, ring)]


def samples(rings: list[list[Point]], signs: list[int], even_odd: bool, size: tuple[int, int]) -> Image.Image:
    """The samples whose center lies inside the rings, 255 inside, 0 outside (see _coverage)."""
    turned = [[(size[0] - 1 - x, size[1] - 1 - y) for x, y in ring] for ring in rings]
    return ImageChops.darker(_inside(rings, signs, even_odd, size), _inside(turned, signs, even_odd, size).transpose(Image.Transpose.ROTATE_180))


class Field:
    """The blurred coverage of a shape on a grid in user units."""

    def __init__(self, rings: list[Ring], even_odd: bool, blur: tuple[float, float]) -> None:
        sx, sy = blur
        self.cell = (sx / CELLS_PER_SIGMA, sy / CELLS_PER_SIGMA)
        xs, ys = [x for ring in rings for x, _ in ring], [y for ring in rings for _, y in ring]
        # One cell of border beyond the margin: the mesh fades to nothing on every side
        self.origin = (min(xs) - MARGIN * sx - self.cell[0], min(ys) - MARGIN * sy - self.cell[1])
        self.width = math.ceil((max(xs) - min(xs) + 2 * MARGIN * sx) / self.cell[0]) + 3
        self.height = math.ceil((max(ys) - min(ys) + 2 * MARGIN * sy) / self.cell[1]) + 3
        self.rings, self.even_odd = rings, even_odd

    @property
    def cells(self) -> int:
        return self.width * self.height

    def to_grid(self, point: Point) -> Point:
        """Grid coordinates where cell i spans [i, i + 1): the sample of cell i sits at i + 0.5."""
        return (point[0] - self.origin[0]) / self.cell[0], (point[1] - self.origin[1]) / self.cell[1]

    @property
    def first(self) -> Point:
        """The center of the first cell, in user units: sample (i, j) sits at first + (i, j) * cell."""
        return self.origin[0] + self.cell[0] / 2, self.origin[1] + self.cell[1] / 2

    def blurred(self) -> Image.Image:
        """The blurred coverage at the center of each cell, 0 to 255."""
        coverage = _coverage(self.rings, self.even_odd, (self.width, self.height), self.to_grid)
        return coverage.filter(ImageFilter.GaussianBlur(CELLS_PER_SIGMA))
