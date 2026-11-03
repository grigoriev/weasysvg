"""The level sets of a sampled field as polygons, and the opacities that stack them into its profile.

A portable PDF has no soft mask (_core.portable). A blur there is drawn as the regions where the blurred
coverage reaches each level, one inside the next, each painted with a constant opacity: painted in order,
they add up to the coverage of the blur within one step. Each region is the inside of its contours,
traced through the grid by marching squares, and filled even-odd.
"""

from __future__ import annotations

import bisect
import math
import re
from typing import TYPE_CHECKING

from PIL import ImageChops, ImageOps

if TYPE_CHECKING:
    from PIL import Image

Point = tuple[float, float]
Ring = list[Point]
# A cell side, as horizontal ("h", i, j) from sample (i, j) to (i + 1, j) or vertical ("v", i, j) to (i, j + 1)
Edge = tuple[str, int, int]

# The steps of the final opacity: a level per 1/64 of it
OPACITY_STEPS = 64
# How far a simplified contour may stray from the traced one, in cells
SIMPLIFY_CELLS = 1 / 8
# A run of cells whose corners differ
_CHANGING = re.compile(rb"[^\x00]+")


def thresholds(opacity: float) -> list[tuple[float, float]]:
    """The levels of a field from 0 to 1 painted at most opacity: (threshold, opacity to paint it at).

    Level k of n holds the points whose value reaches (k - 0.5) / n, and stacked over the levels before it
    brings them to opacity * k / n. Painted over an opacity T, an opacity a gives T + a (1 - T).
    """
    steps = max(1, math.ceil(OPACITY_STEPS * opacity))
    out = []
    below = 0.0
    for k in range(1, steps + 1):
        target = opacity * k / steps
        out.append(((k - 0.5) / steps, (target - below) / (1 - below)))
        below = target
    return out


def contours(values: Image.Image, levels: list[float]) -> dict[float, list[Ring]]:
    """The closed contours of each level of values, a field in grayscale 0 to 255 read as 0 to 1.

    Points are in sample coordinates: sample (i, j) sits at (i, j). Beyond the field it is 0, so every
    contour closes. A saddle cell joins its corners as their mean says. Only the cells whose corners differ
    are visited: Pillow finds them, so the flat inside and outside of a large shape cost nothing here.
    """
    padded = ImageOps.expand(values, border=1, fill=0)
    width, height = padded.width - 1, padded.height - 1
    corners = [padded.crop(box) for box in ((0, 0, width, height), (1, 0, width + 1, height), (1, 1, width + 1, height + 1), (0, 1, width, height + 1))]
    high = ImageChops.lighter(ImageChops.lighter(corners[0], corners[1]), ImageChops.lighter(corners[2], corners[3]))
    low = ImageChops.darker(ImageChops.darker(corners[0], corners[1]), ImageChops.darker(corners[2], corners[3]))
    tops, rights, bottoms, lefts = (corner.tobytes() for corner in corners)
    highs, lows = high.tobytes(), low.tobytes()
    scaled = sorted(level * 255 for level in levels)
    links: dict[float, list[tuple[Edge, Edge]]] = {level: [] for level in scaled}
    points: dict[float, dict[Edge, Point]] = {level: {} for level in scaled}
    for run in _CHANGING.finditer(ImageChops.subtract(high, low).tobytes()):
        for index in range(run.start(), run.end()):
            j, i = divmod(index, width)
            # The levels t with low < t <= high: some corners reach t, some do not
            for level in scaled[bisect.bisect_right(scaled, lows[index]) : bisect.bisect_right(scaled, highs[index])]:
                _cell(i, j, (tops[index], rights[index], bottoms[index], lefts[index]), level, links[level], points[level])
    out: dict[float, list[Ring]] = {}
    for level in levels:
        key = level * 255
        rings = _rings(links[key], points[key])
        out[level] = [[(x - 1, y - 1) for x, y in ring] for ring in rings]
    return out


def _cell(i: int, j: int, corners: tuple[int, int, int, int], level: float, links: list[tuple[Edge, Edge]], points: dict[Edge, Point]) -> None:
    """Add the segments of one cell at level: its corners top left, top right, bottom right, bottom left."""
    a, b, c, e = corners
    inside = (a >= level, b >= level, c >= level, e >= level)
    top, right, bottom, left = ("h", i, j), ("v", i + 1, j), ("h", i, j + 1), ("v", i, j)
    sides = (
        (top, (i, j), a, (i + 1, j), b),
        (right, (i + 1, j), b, (i + 1, j + 1), c),
        (bottom, (i, j + 1), e, (i + 1, j + 1), c),
        (left, (i, j), a, (i, j + 1), e),
    )
    crossed = []
    for edge, start, first, end, second in sides:
        if (first >= level) != (second >= level):
            crossed.append(edge)
            if edge not in points:
                share = (level - first) / (second - first)
                points[edge] = (start[0] + share * (end[0] - start[0]), start[1] + share * (end[1] - start[1]))
    if len(crossed) == 2:
        links.append((crossed[0], crossed[1]))
        return
    # A saddle: two opposite corners inside. The mean of the corners says whether the inside joins them
    joined = (a + b + c + e) / 4 >= level
    if inside[0] == joined:
        # The corners top right and bottom left are cut off
        links += [(top, right), (bottom, left)]
    else:
        links += [(top, left), (right, bottom)]


def _rings(links: list[tuple[Edge, Edge]], points: dict[Edge, Point]) -> list[Ring]:
    """Chain the segments into closed rings: every crossed side belongs to two of them."""
    neighbors: dict[Edge, list[Edge]] = {}
    for first, second in links:
        neighbors.setdefault(first, []).append(second)
        neighbors.setdefault(second, []).append(first)
    out = []
    seen: set[Edge] = set()
    for start in neighbors:
        if start in seen:
            continue
        ring, previous, current = [], None, start
        while current not in seen:
            seen.add(current)
            ring.append(points[current])
            following = [edge for edge in neighbors[current] if edge != previous]
            previous, current = current, following[0] if following else current
        # A closed contour on the grid goes around one sample at least: four sides of cells
        out.append(ring)
    return out


def simplified(ring: Ring, tolerance: float) -> Ring:
    """ring with every point dropped that lies within tolerance of the line between the points kept around it.

    The closed ring of Ramer, Douglas and Peucker: split at the point farthest from the first one, then
    each half on its own.
    """
    if len(ring) < 4:
        return ring
    far = max(range(len(ring)), key=lambda index: math.dist(ring[0], ring[index]))
    first, second = ring[: far + 1], [*ring[far:], ring[0]]
    return [*_kept(first, tolerance)[:-1], *_kept(second, tolerance)[:-1]]


def _kept(points: list[Point], tolerance: float) -> list[Point]:
    """The open polyline points, its ends kept and each point between them kept where it strays past tolerance."""
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        if end - start < 2:
            continue
        first, last = points[start], points[end]
        distances = {index: _off_line(points[index], first, last) for index in range(start + 1, end)}
        index = max(distances, key=distances.__getitem__)
        if distances[index] > tolerance:
            keep[index] = True
            stack += [(start, index), (index, end)]
    return [point for point, kept in zip(points, keep, strict=True) if kept]


def _off_line(point: Point, start: Point, end: Point) -> float:
    """The distance of point from the segment from start to end."""
    (x, y), (x0, y0), (x1, y1) = point, start, end
    dx, dy = x1 - x0, y1 - y0
    length = dx * dx + dy * dy
    if not length:
        return math.dist(point, start)
    share = min(1.0, max(0.0, ((x - x0) * dx + (y - y0) * dy) / length))
    return math.dist(point, (x0 + share * dx, y0 + share * dy))
