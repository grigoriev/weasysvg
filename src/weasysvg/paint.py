"""Paint servers, masks and blending.

Touches:
- ``svg.defs.draw_gradient``: a gradient cell of about 1000 units, since Splash and Quartz drop a 1 x 1
  cell, that covers the box under any gradientTransform, or the whole box a blur paints (``BOXED``); r
  and fr percentages of a radial gradient refer to the normalized diagonal; colors interpolate
  unpremultiplied, as Chromium does for SVG.
- ``svg.SVG.set_graphical_state``: a gradient or pattern stroke gets its stroke-width, not 1.
- ``svg.defs.draw_pattern``: the tile origin in pattern space, x and y included; attributes and tag are
  restored after each use.
- ``svg.defs.paint_mask``: replaced. Region of an objectBoundingBox mask, maskContentUnits, a cycle
  through mask="..." is broken, mask="..." on the <mask> itself is ignored as in Chromium, and the tag
  of the <mask> is restored, else the walk draws it as a <g>. In a portable PDF a mask of opaque white and
  black shapes is a clip, and a mask of one gray or translucent shape an opacity of the element.
- a complex clip path, through ``_core``: one in objectBoundingBox units, or whose children carry
  clip-path, clip-rule="evenodd", text or <use>, or with several children. It becomes one path of all its
  fills where that holds them (``clippaths.py``), else an alpha soft mask, each child filled by its
  clip-rule. WeasyPrint dropped such children, ignored clip-rule, painted clip text in black and cut a
  hole where two children turn opposite ways.
- ``svg.Node.override_iter``: a list instead of a one-shot iterator, so a node can be walked twice.
- ``svg.SVG.draw_node``, through ``_core``: mix-blend-mode as an isolated group, and a mask on a container
  is set before its children are drawn. ``svg.NOT_INHERITED_ATTRIBUTES`` gains mix-blend-mode.
- a tree pass: an empty presentation attribute (fill="") is ignored, as browsers do.
- a tree pass: an arc of a zero radius in path data becomes the line SVG draws for it, and an arc wider
  than 90 degrees curves of 90 degrees. WeasyPrint wrote a relative line to the end of the first, which
  broke every slice of a Highcharts pie, and drew the second as one curve, which bulged.
- ``svg.SVG.fill_stroke``, through ``paint_order``: a dash through the start point of a closed subpath
  is joined into one dash (``dashes.py``).
- ``svg.TAGS['circle']`` and ``svg.TAGS['ellipse']``: each quarter is a Bezier with the arc constant
  4 (sqrt(2) - 1) / 3. WeasyPrint uses 1 / sqrt(pi), a longer outline that moves the dashes along it.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from xml.etree import ElementTree as ET

from weasyprint import svg as wp_svg
from weasyprint.matrix import Matrix
from weasyprint.pdf import stream as wp_stream
from weasyprint.svg import defs as wp_defs
from weasyprint.svg import utils as wp_utils

from . import _core, clippaths, coverage, levelsets, pathdata

LOGGER = logging.getLogger("weasysvg")

GRADIENT_CELL = 1000  # pattern units for the longest side of a gradient cell
DASH_FRACTION = 2.5e-5  # of the dash period: the length a dash of length 0 gets, 0.001 units of a period of 40
STROKE_FRACTION = 1e-3  # of the stroke width: the most that length may be
MIN_DASH = 1e-5  # user units: the least that length may be, pydyf writes six decimals
ARC_CONSTANT = 4 * (2**0.5 - 1) / 3  # the control point of a quarter circle in one Bezier, per unit of radius
SHAPES = frozenset(("circle", "ellipse", "line", "path", "polyline", "polygon", "rect"))
BLEND_MODES = {
    "multiply": "Multiply",
    "screen": "Screen",
    "overlay": "Overlay",
    "darken": "Darken",
    "lighten": "Lighten",
    "color-dodge": "ColorDodge",
    "color-burn": "ColorBurn",
    "hard-light": "HardLight",
    "soft-light": "SoftLight",
    "difference": "Difference",
    "exclusion": "Exclusion",
    "hue": "Hue",
    "saturation": "Saturation",
    "color": "Color",
    "luminosity": "Luminosity",
}
PRESENTATION = frozenset(
    (
        "fill",
        "stroke",
        "fill-opacity",
        "stroke-opacity",
        "stroke-width",
        "opacity",
        "font-size",
        "font-family",
        "font-weight",
        "font-style",
        "color",
        "stop-color",
        "stop-opacity",
        "visibility",
        "display",
        "text-anchor",
        "dominant-baseline",
    )
)

# The node a blur paints over a whole box instead of its shape, and that box (filters._paint_box)
BOXED: ContextVar[tuple[Any, tuple[float, float, float, float]] | None] = ContextVar("weasysvg_boxed", default=None)

_ORIGINAL_DRAW_GRADIENT = wp_defs.draw_gradient
_ORIGINAL_DRAW_PATTERN = wp_defs.draw_pattern
_ORIGINAL_SET_GRAPHICAL_STATE = wp_svg.SVG.set_graphical_state


# ---------------- tree pass ----------------


def drop_empty_presentation(root: ET.Element) -> None:
    """An empty presentation attribute is invalid and ignored by browsers; WeasyPrint reads fill="" as none."""
    for element in root.iter():
        for key in [k for k, v in element.attrib.items() if k in PRESENTATION and not v.strip()]:
            del element.attrib[key]


# ---------------- add_pattern overrides ----------------


@contextmanager
def _add_pattern_override(stream: Any, function: Callable[..., Any]) -> Iterator[None]:
    """Replace add_pattern on one stream for the duration of one paint server, then restore what was there."""
    missing = object()
    previous = stream.__dict__.get("add_pattern", missing)
    stream.add_pattern = function
    try:
        yield
    finally:
        if previous is missing:
            del stream.add_pattern
        else:
            stream.add_pattern = previous


def _scaled_add_pattern(stream: Any, cell: tuple[float, float, float, float] | None = None) -> Callable[..., Any]:
    """add_pattern with a cell of about GRADIENT_CELL units: the scale moves into the content, the result is identical.

    cell replaces the cell WeasyPrint computes, for its pattern, its group and the soft mask of its alpha.
    """
    original = type(stream).add_pattern

    def add_pattern(x: float, y: float, width: float, height: float, repeat_width: float, repeat_height: float, matrix: Any) -> Any:
        if cell is not None:
            x, y, width, height = cell
            repeat_width, repeat_height = width, height
        extent = max(abs(width), abs(height))
        k = GRADIENT_CELL / extent if extent else 1
        pattern = original(stream, x * k, y * k, width * k, height * k, repeat_width * k, repeat_height * k, Matrix(a=1 / k, d=1 / k) @ matrix)
        original_group = pattern.add_group

        def add_group(gx: float, gy: float, gwidth: float, gheight: float) -> Any:
            if cell is not None:
                gx, gy, gwidth, gheight = cell
            group = original_group(gx * k, gy * k, gwidth * k, gheight * k)
            group.transform(a=k, d=k)
            # WeasyPrint bends the color between stops of different opacity by a0 / a1, to mimic a
            # premultiplied mix. Chromium mixes SVG gradient colors unpremultiplied: a straight line.
            original_function = group.create_interpolation_function
            group.create_interpolation_function = lambda domain, c0, c1, _n: original_function(domain, c0, c1, 1)
            if cell is not None:
                original_alpha = group.set_alpha_state
                group.set_alpha_state = lambda *_box, **kwargs: original_alpha(*cell, **kwargs)
            return group

        pattern.add_group = add_group
        return pattern

    return add_pattern


def _gradient_cell(svg: Any, node: Any, gradient: Any, font_size: float, stroke: bool) -> tuple[float, float, float, float] | None:
    """The cell of a gradient, None for the one WeasyPrint makes: all four corners mapped back by gradientTransform.

    WeasyPrint maps two corners only: rotated by 45 degrees, its cell is a sliver and the shape stays empty.
    A blur paints a fill over its whole region: the cell is the shape box, and the pattern repeated the
    gradient past it, a hard edge in the shadow. The cell covers that region, where the gradient pads.
    """
    boxed = BOXED.get()
    cover = boxed[1] if boxed is not None and boxed[0] is node and not stroke else None
    if "gradientTransform" not in gradient.attrib and cover is None:
        return None
    box = svg.calculate_bounding_box(node, font_size, stroke)
    if not wp_defs.is_valid_bounding_box(box):
        return None
    if gradient.get("gradientUnits") == "userSpaceOnUse":
        x, y, width, height = cover or box
    elif cover is not None:
        # The region in units of the box of the shape, where an objectBoundingBox gradient lives
        bx, by, bwidth, bheight = box
        if not bwidth or not bheight:
            return None  # a box of no width or height has no units: WeasyPrint paints nothing
        x, y, width, height = (cover[0] - bx) / bwidth, (cover[1] - by) / bheight, cover[2] / bwidth, cover[3] / bheight
    else:
        x, y, width, height = 0, 0, 1, 1
    if "gradientTransform" not in gradient.attrib:
        return x, y, width, height
    matrix = wp_utils.transform(gradient.get("gradientTransform"), "0 0", font_size, svg.normalized_diagonal)
    if not matrix.determinant:
        return None
    inverse = matrix.invert
    points = [inverse.transform_point(px, py) for px in (x, x + width) for py in (y, y + height)]
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


# ---------------- gradients ----------------


def _radial_percentages(gradient: Any) -> dict[str, str | None]:
    """Percentages of r and fr refer to the normalized diagonal, hypot(w, h) / sqrt(2), not hypot(w, h)."""
    changed: dict[str, str | None] = {}
    if gradient.tag != "radialGradient" or gradient.get("gradientUnits") == "userSpaceOnUse":
        return changed
    for name, default in (("r", "50%"), ("fr", "0")):
        value = str(gradient.get(name, default)).strip()
        if value.endswith("%"):
            changed[name] = gradient.attrib.get(name)
            gradient.attrib[name] = str(float(value[:-1]) / 100)
    return changed


@dataclass(frozen=True)
class _Stop:
    attrib: dict[str, str]

    def get(self, key: str, default: Any = None) -> Any:
        return self.attrib.get(key, default)


def _focal_ring(gradient: Any, font_size: float, reference: float) -> list[_Stop] | None:
    """The stops of a padded radial gradient whose focal circle is concentric, rewritten for fr = 0.

    PDFium paints the center of a shading with an inner radius white. Without one, the first color
    fills the focal circle and the stops move out to it: offset k + o (1 - k), with k = fr / r.
    """
    if gradient.tag != "radialGradient" or gradient.get("spreadMethod", "pad") != "pad":
        return None
    if any(gradient.get(name) not in (None, gradient.get(center, "50%")) for name, center in (("fx", "cx"), ("fy", "cy"))):
        return None
    radius, focal = (wp_utils.size(gradient.get(name, default), font_size, reference) for name, default in (("r", "50%"), ("fr", "0")))
    stops = list(gradient)
    if not stops or not 0 < focal < radius:
        return None
    ring = focal / radius
    out = [_Stop({**stops[0].attrib, "offset": "0"})]
    previous = 0.0
    for stop in stops:
        previous = max(previous, wp_utils.size(stop.get("offset", "0"), font_size, 1))
        out.append(_Stop({**stop.attrib, "offset": str(ring + min(previous, 1.0) * (1 - ring))}))
    return out


# A stop of opacity 0 gets this one instead: WeasyPrint gives a transparent stop the color of its
# neighbor, the premultiplied mix again, while Chromium keeps its own color
TRANSPARENT_STOP = "1e-9"


def _visible_stops(gradient: Any, changed: list[tuple[Any, str]]) -> None:
    """Give each fully transparent stop a tiny opacity, and an invalid one 1, as Chromium reads it.

    Each stop goes into changed before it changes, so that a failure leaves nothing changed behind.
    """
    for stop in gradient:
        value = stop.get("stop-opacity")
        if value is None:
            continue
        try:
            replacement = TRANSPARENT_STOP if wp_utils.alpha_value(value) == 0 else None
        except ValueError:
            replacement = "1"  # WeasyPrint raised ValueError and lost the whole SVG
        if replacement is not None:
            changed.append((stop, value))
            stop.attrib["stop-opacity"] = replacement


def draw_gradient(svg: Any, node: Any, gradient: Any, font_size: float, opacity: float, stroke: bool) -> Any:
    stream = svg.stream
    changed: dict[str, str | None] = {}
    stops: list[tuple[Any, str]] = []
    try:
        changed = _radial_percentages(gradient)
        _visible_stops(gradient, stops)
        cell = _gradient_cell(svg, node, gradient, font_size, stroke)
        reference = svg.normalized_diagonal if gradient.get("gradientUnits") == "userSpaceOnUse" else 1
        ring = _focal_ring(gradient, font_size, reference)
        cls = gradient.__class__
        if ring is not None:
            changed.setdefault("fr", gradient.attrib.get("fr"))
            gradient.attrib["fr"] = "0"
            gradient.__class__ = type(cls.__name__, (cls,), {"__iter__": lambda _: iter(ring)})
        # In a portable PDF the opacity of the stops paints in bands, not through a soft mask
        capture = _GRADIENT_ALPHA.set(_AlphaCapture()) if _core.PORTABLE.get() else None
        try:
            with _add_pattern_override(stream, _scaled_add_pattern(stream, cell)):
                return _ORIGINAL_DRAW_GRADIENT(svg, node, gradient, font_size, opacity, stroke)
        finally:
            if capture is not None:
                _GRADIENT_ALPHA.reset(capture)
            if ring is not None:
                gradient.__class__ = cls
    finally:
        for stop, stop_opacity in stops:
            stop.attrib["stop-opacity"] = stop_opacity
        for name, value in changed.items():
            if value is None:
                gradient.attrib.pop(name, None)
            else:
                gradient.attrib[name] = value


def _materialized_override_iter(self: Any, iterator: Any) -> None:
    """A list of children: href'd gradient stops and <use> trees are walked more than once."""
    children = list(iterator)
    self.__class__ = type("Node", (wp_svg.Node,), {"__iter__": lambda _: iter(children)})


def set_graphical_state(self: Any, node: Any, font_size: float, context: Any = None) -> tuple[Any, Any]:
    """WeasyPrint sets the line width for a plain color only: a gradient or pattern stroke drew 1 unit wide."""
    fill, stroke = _ORIGINAL_SET_GRAPHICAL_STATE(self, node, font_size, context=context)
    if stroke:
        self.stream.set_line_width(self.length(node.get("stroke-width", "1px"), font_size))
    _reset_dashes(self, node, font_size)
    return fill, stroke


def _reset_dashes(svg: Any, node: Any, font_size: float) -> None:
    """Set the dashes WeasyPrint set again where they are wrong: no dash of length 0, the whole period.

    PDFium moves a dash of length 0 (no_zero_dashes). Only a round or square cap paints one: under a butt
    cap a tiny dash would show as a sliver. An odd array repeats, so its period is twice its sum, and a
    negative offset counts back from that period: WeasyPrint counts back from the sum alone.
    """
    values = dash_values(svg, node, font_size)
    if values is None:
        return
    dashes, offset = values
    zero = zero_dashes_painted(node, dashes)
    if not zero and not (offset < 0 and len(dashes) % 2):
        return
    # Without a dash of length 0 only an odd array with a negative offset is here: repeated, it has its period
    fixed = no_zero_dashes(dashes, svg.length(node.get("stroke-width", "1px"), font_size)) if zero else dashes * 2
    if offset < 0:
        offset = sum(fixed) - abs(offset) % sum(fixed)
    svg.stream.set_dash(fixed, offset)


def dash_values(svg: Any, node: Any, font_size: float) -> tuple[tuple[float, ...], float] | None:
    """The stroke-dasharray and stroke-dashoffset of node in user units; None for a solid stroke, as WeasyPrint reads them."""
    dashes = tuple(svg.length(value, font_size) for value in wp_utils.normalize(node.get("stroke-dasharray")).split() if value != "none")
    if not any(dashes) or min(dashes) < 0:
        return None
    return dashes, svg.length(node.get("stroke-dashoffset"), font_size)


def zero_dashes_painted(node: Any, dashes: tuple[float, ...]) -> bool:
    """Whether a dash of length 0 paints: only under a round or a square cap."""
    return 0 in dashes and node.get("stroke-linecap", "butt") in ("round", "square")


def no_zero_dashes(dashes: tuple[float, ...], stroke_width: float = math.inf) -> tuple[float, ...]:
    """The dash array with each dash of length 0 lengthened a little, taken from the gap after it.

    PDFium moves a dash of length 0 along the path, about 1 unit each 240: the dots of a dotted line
    drifted. The period stays the same. A gap of 0 stays: a tiny gap could show as a hairline.
    """
    # An odd array repeats to an even one: dashes and gaps alternate
    out = list(dashes * 2 if len(dashes) % 2 else dashes)
    # A share of the period, not a length in user units: a viewBox of one unit drawn large would show
    # 0.001 units. A share of the stroke as well: a long period would stretch a dot of a thin stroke.
    # And no shorter than the PDF writes: six decimals
    epsilon = max(min(sum(out) * DASH_FRACTION, stroke_width * STROKE_FRACTION), MIN_DASH)
    for index in range(0, len(out), 2):
        if out[index] == 0 and out[index + 1] > epsilon:
            out[index], out[index + 1] = epsilon, out[index + 1] - epsilon
    return tuple(out)


# ---------------- patterns ----------------


def draw_pattern(svg: Any, node: Any, pattern: Any, font_size: float, opacity: float, stroke: bool) -> Any:
    saved = dict(pattern.attrib)
    tag = pattern._etree_node.tag
    # The finally covers the pops of x and y too: the pattern node is shared by every element that uses it
    try:
        origin = _pattern_origin(svg, node, pattern, font_size, stroke)
        pattern_transform = wp_utils.transform(pattern.get("patternTransform", ""), "0 0", font_size, svg.inner_diagonal)
        stream = svg.stream
        original_add_pattern = stream.add_pattern

        def add_pattern(x: float, y: float, width: float, height: float, repeat_width: float, repeat_height: float, _matrix: Any) -> Any:
            # WeasyPrint starts the tiles at the box of the shape, after patternTransform. The tile origin
            # lies in pattern space: patternTransform moves it too.
            matrix = Matrix(e=origin[0], f=origin[1]) @ pattern_transform @ stream.ctm
            return original_add_pattern(x, y, width, height, repeat_width, repeat_height, matrix)

        with _add_pattern_override(stream, add_pattern):
            return _ORIGINAL_DRAW_PATTERN(svg, node, pattern, font_size, opacity, stroke)
    finally:
        # draw_pattern pops width and height and renames the tag to svg: the next user needs them back
        pattern.attrib.clear()
        pattern.attrib.update(saved)
        pattern._etree_node.tag = tag


def _pattern_origin(svg: Any, node: Any, pattern: Any, font_size: float, stroke: bool) -> tuple[float, float]:
    """Take x and y off the pattern and return the tile origin in pattern space."""
    px, py = pattern.attrib.pop("x", 0), pattern.attrib.pop("y", 0)
    if pattern.get("patternUnits") == "userSpaceOnUse":
        x, y = svg.point(px, py, font_size)
        return x, y
    box = svg.calculate_bounding_box(node, font_size, stroke)
    if not wp_defs.is_valid_bounding_box(box):
        return 0.0, 0.0
    return box[0] + wp_utils.size(px, font_size, 1) * box[2], box[1] + wp_utils.size(py, font_size, 1) * box[3]


# ---------------- gradient opacity in bands, for a portable PDF ----------------


@dataclass
class _AlphaCapture:
    """The soft mask WeasyPrint sets for the stop opacities of one gradient, kept instead of set."""

    shading: tuple[int, Any, Any, bool, Any, Reach] | None = None
    painted: bool = False


_GRADIENT_ALPHA: ContextVar[_AlphaCapture | None] = ContextVar("weasysvg_gradient_alpha", default=None)
_ORIGINAL_SET_ALPHA_STATE = wp_stream.Stream.set_alpha_state
_ORIGINAL_PAINT_SHADING = wp_stream.Stream.paint_shading


@dataclass
class _AlphaSink:
    """What set_alpha_state returns while a gradient of a portable PDF draws: it keeps the alpha shading.

    A shading the bands cannot follow goes to a real soft mask after all, made then on the group.
    """

    group: Any
    box: tuple[float, float, float, float]
    capture: _AlphaCapture
    real: Any = None
    stream: Any = field(default=None)

    def add_shading(self, shading_type: int, domain: Any, coords: Any, extend: bool, function: Any, color_space: str | None = None) -> Any:
        reach = _reach(shading_type, [float(value) for value in coords], _corners(self.group))
        if reach is not None:
            self.capture.shading = (shading_type, domain, coords, extend, function, reach)
            # WeasyPrint names it in the stream of the alpha group, which nothing draws
            return SimpleNamespace(id="weasysvg-bands")
        self.real = _ORIGINAL_SET_ALPHA_STATE(self.group, *self.box)
        return self.real.add_shading(shading_type, domain, coords, extend, function, color_space)

    def __setattr__(self, name: str, value: Any) -> None:
        # WeasyPrint writes the operators of the alpha group into its stream
        if name == "stream" and getattr(self, "real", None) is not None:
            self.real.stream = value
        object.__setattr__(self, name, value)


def _set_alpha_state(self: Any, x: float, y: float, width: float, height: float, mode: str = "luminosity") -> Any:
    capture = _GRADIENT_ALPHA.get()
    if capture is None or capture.shading is not None or mode != "luminosity":
        return _ORIGINAL_SET_ALPHA_STATE(self, x, y, width, height, mode)
    return _AlphaSink(self, (x, y, width, height), capture)


def _paint_shading(self: Any, name: str) -> None:
    capture = _GRADIENT_ALPHA.get()
    if capture is None or capture.shading is None or capture.painted:
        _ORIGINAL_PAINT_SHADING(self, name)
        return
    capture.painted = True
    _paint_in_bands(self, name, capture.shading)


# The shares of the axis a level needs to span to cover the group, low and high, and for an axis the half width
Reach = tuple[float, float, float]


def _corners(stream: Any) -> list[tuple[float, float]]:
    """The corners of the box of a group in the space of its shading: the cell of a gradient is about 1000 units."""
    left, top, right, bottom = (float(value) for value in stream.extra["BBox"])
    inverse = stream.ctm.invert
    return [inverse.transform_point(x, y) for x in (left, right) for y in (top, bottom)]


def _reach(shading_type: int, coords: list[float], corners: list[tuple[float, float]]) -> Reach | None:
    """How far the levels of a shading must reach to cover corners; None where bands cannot follow it.

    Reaching that far and no farther keeps the coordinates of the levels small enough for the precision of a viewer.
    """
    if shading_type == 2:
        return _axis_reach(coords, corners)
    return _ring_reach(coords, corners)


def _axis_reach(coords: list[float], corners: list[tuple[float, float]]) -> Reach | None:
    """The shares of a linear axis the corners project on, and their farthest distance from it, with a margin."""
    x1, y1, x2, y2 = coords
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if not length:
        return None
    shares = [((x - x1) * dx + (y - y1) * dy) / length**2 for x, y in corners]
    widths = [abs((x - x1) * dy - (y - y1) * dx) / length for x, y in corners]
    return min(shares) - 1, max(shares) + 1, max(widths) + length


def _ring_reach(coords: list[float], corners: list[tuple[float, float]]) -> Reach | None:
    """The share at which the circles of a radial shading hold every corner, with a margin; None where they never do.

    The circle of share s has its center f + s (c - f) and its radius fr + s (r - fr). It holds a point q from f
    once |q - s d| <= fr + s dr, a quadratic in s; with the end circle around the focal one (|d| <= dr) the
    circles grow faster than they move, and each later circle holds the point too.
    """
    fx, fy, fr, cx, cy, r = coords
    d, dr = (cx - fx, cy - fy), r - fr
    if dr <= 0 or math.hypot(*d) > dr:
        return None
    needed = 1.0
    for x, y in corners:
        q = (x - fx, y - fy)
        a = d[0] ** 2 + d[1] ** 2 - dr**2
        b = -2 * (q[0] * d[0] + q[1] * d[1] + fr * dr)
        c = q[0] ** 2 + q[1] ** 2 - fr**2
        if a == 0:
            # The circles touch the focal point on one side: they reach a point at -c / b, or never
            if b >= 0 and c > 0:
                return None
            share = -c / b if b < 0 else -math.inf
        else:
            # Real roots always: at s = -fr / dr the circle has no size, and no point lies inside it. Rounding aside
            root = math.sqrt(max(b * b - 4 * a * c, 0.0))
            share = max((-b + root) / (2 * a), (-b - root) / (2 * a))
        needed = max(needed, share)
    return -math.inf, needed + 1, 0.0


def _alpha_pieces(function: Any, domain: Any) -> list[tuple[float, float, float, float]]:
    """The pieces of the alpha function: start and end offset, start and end opacity, each linear."""
    start, end = float(domain[0]), float(domain[1])
    if int(function["FunctionType"]) == 2:
        return [(start, end, float(function["C0"][0]), float(function["C1"][0]))]
    bounds = [start, *(float(bound) for bound in function["Bounds"]), end]
    encode = [float(value) for value in function["Encode"]]
    out = []
    for index, piece in enumerate(function["Functions"]):
        c0, c1 = float(piece["C0"][0]), float(piece["C1"][0])
        e0, e1 = encode[2 * index], encode[2 * index + 1]
        # Encode maps the piece onto its own domain: the opacity at its ends
        out.append((bounds[index], bounds[index + 1], c0 + (c1 - c0) * e0, c0 + (c1 - c0) * e1))
    return out


Interval = tuple[float, float]


def _above(start: float, end: float, a0: float, a1: float, level: float) -> Interval | None:
    """The offsets of one linear piece where its opacity reaches level, or None."""
    if a0 >= level and a1 >= level:
        return start, end
    if a0 < level and a1 < level:
        return None
    cross = start + (level - a0) / (a1 - a0) * (end - start)
    return (start, cross) if a0 >= level else (cross, end)


def _level(pieces: list[tuple[float, float, float, float]], level: float, extend: bool) -> list[Interval]:
    """The offsets where the opacity of the pieces reaches level, neighbors joined, open at an end with extend."""
    intervals: list[Interval] = []
    for index, piece in enumerate(pieces):
        found = _above(*piece, level)
        if found is None:
            continue
        low, high = found
        if extend and index == 0 and low == piece[0]:
            low = -math.inf
        if extend and index == len(pieces) - 1 and high == piece[1]:
            high = math.inf
        if intervals and math.isclose(intervals[-1][1], low):
            intervals[-1] = (intervals[-1][0], high)
        else:
            intervals.append((low, high))
    return intervals


def levels(function: Any, domain: Any, extend: bool, axis_px: float = 0.0) -> list[tuple[float, list[Interval]]]:
    """The level sets of the stop opacity along the gradient: the opacity each adds, and where.

    Level k holds the offsets where the opacity reaches (k - 0.5) / n of its peak, a union of intervals, one
    inside the next as for a blur (levelsets.thresholds). Painted in order they add up to the opacity within
    1/64, rising and falling alike, and each meets the one below with its own edge only: two regions side by
    side would each smooth their shared edge, a light seam in any viewer. Levels over the same offsets merge.
    With extend the ends reach on without end. With axis_px, the length of the axis in CSS px as shown, no level
    is narrower than _core.BAND_PX where the opacity changes most slowly.
    """
    pieces = [piece for piece in _alpha_pieces(function, domain) if piece[1] > piece[0]]
    peak = max((max(piece[2], piece[3]) for piece in pieces), default=0.0)
    most = _most_levels(pieces, peak, float(domain[1]) - float(domain[0]), axis_px)
    out: list[tuple[float, list[Interval]]] = []
    for threshold, opacity in levelsets.thresholds(peak, most) if peak > 0 else []:
        intervals = _level(pieces, threshold * peak, extend)
        # Each level lies below the peak, which reaches it: a level is never empty
        if out and out[-1][1] == intervals:
            # Two coats over the same offsets are one coat of their combined opacity
            out[-1] = (1 - (1 - out[-1][0]) * (1 - opacity), intervals)
        else:
            out.append((opacity, intervals))
    return out


def _most_levels(pieces: list[tuple[float, float, float, float]], peak: float, span: float, axis_px: float) -> int | None:
    """How many levels keep each at least _core.BAND_PX wide where the opacity changes most slowly; None for no limit.

    A piece over w px that changes the opacity by d holds d / peak * n edges of n levels, w * peak / (d * n) px apart.
    """
    band_px = _core.BAND_PX.get()
    if band_px <= 0 or axis_px <= 0 or span <= 0 or peak <= 0:
        return None
    room = [(end - start) / span * axis_px * peak / abs(a1 - a0) for start, end, a0, a1 in pieces if a1 != a0]
    return max(1, math.floor(max(room) / band_px)) if room else None


def _axis_px(stream: Any, shading_type: int, points: list[float]) -> float:
    """The length of the axis of a shading in CSS px as the drawing is shown.

    For a linear shading it is the distance between the lines across its ends. For a radial one it is the growth
    of the radius and the travel of the center, along the direction the transform stretches most: the widest a
    ring gets.
    """
    if shading_type == 2:
        x1, y1, x2, y2 = points
        length = math.hypot(x2 - x1, y2 - y1)
        return length * _core.px_across(stream, (x2 - x1) / length, (y2 - y1) / length) if length else 0.0
    fx, fy, fr, cx, cy, r = points
    return (abs(r - fr) + math.hypot(cx - fx, cy - fy)) * _core.px_most(stream)


def _paint_in_bands(stream: Any, name: str, shading: tuple[int, Any, Any, bool, Any, Reach]) -> None:
    """Paint the color shading once per level of its opacity, clipped to the level and at the opacity it adds."""
    shading_type, domain, coords, extend, function, (lowest, highest, half_width) = shading
    first, last = float(domain[0]), float(domain[1])
    points = [float(value) for value in coords]
    # Where the opacity jumps at one offset, as between two cycles of spreadMethod="repeat", the edge of a level
    # meets the jump of the color: a viewer that takes the color of a shading at the center of each pixel paints
    # the pixel across the edge in the color of the far side, a line of one pixel
    for opacity, intervals in levels(function, domain, extend, _axis_px(stream, shading_type, points)):
        stream.push_state()
        try:
            for low, high in intervals:
                # The offsets as shares of the axis, 0 at its start and 1 at its end, no farther than the group needs
                share = [(value - first) / (last - first) if math.isfinite(value) else math.copysign(math.inf, value) for value in (low, high)]
                share = [max(share[0], lowest), min(share[1], highest)]
                if shading_type == 2:
                    _add_strip(stream, points, share[0], share[1], half_width)
                else:
                    _add_ring(stream, points, share[0], share[1])
            # The intervals do not overlap: even-odd is their union, and a ring is the outer circle less the inner one
            stream.clip(even_odd=True)
            stream.end()
            stream.set_alpha(opacity, stroke=True, fill=True)
            _ORIGINAL_PAINT_SHADING(stream, name)
        finally:
            stream.pop_state()


def _add_strip(stream: Any, coords: list[float], low: float, high: float, half_width: float) -> None:
    """Add the points whose projection on the axis falls between shares low and high of it, half_width to either side."""
    x1, y1, x2, y2 = coords
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    nx, ny = -dy / length * half_width, dx / length * half_width
    a = (x1 + dx * low, y1 + dy * low)
    b = (x1 + dx * high, y1 + dy * high)
    stream.move_to(a[0] + nx, a[1] + ny)
    stream.line_to(b[0] + nx, b[1] + ny)
    stream.line_to(b[0] - nx, b[1] - ny)
    stream.line_to(a[0] - nx, a[1] - ny)
    stream.close()


def _circle_path(stream: Any, cx: float, cy: float, r: float) -> None:
    k = ARC_CONSTANT * r
    stream.move_to(cx + r, cy)
    stream.curve_to(cx + r, cy + k, cx + k, cy + r, cx, cy + r)
    stream.curve_to(cx - k, cy + r, cx - r, cy + k, cx - r, cy)
    stream.curve_to(cx - r, cy - k, cx - k, cy - r, cx, cy - r)
    stream.curve_to(cx + k, cy - r, cx + r, cy - k, cx + r, cy)
    stream.close()


def _add_ring(stream: Any, coords: list[float], low: float, high: float) -> None:
    """Add the circle of share high and the circle of share low: even-odd, the points between them."""
    fx, fy, fr, cx, cy, r = coords

    def circle(share: float) -> tuple[float, float, float]:
        # Before the focal circle a band holds all of its inside: a circle of no size
        share = max(share, 0.0) if fr == 0 else share
        radius = fr + (r - fr) * share
        if radius <= 0:
            return fx, fy, 0.0
        return fx + (cx - fx) * share, fy + (cy - fy) * share, radius

    outer = circle(high)
    _circle_path(stream, *outer)
    inner = circle(low)
    if inner[2] > 0:
        _circle_path(stream, *inner)


# ---------------- masks ----------------

# The masks being drawn, per thread and task: weasyprint-service renders several documents at once
_ACTIVE_MASKS: ContextVar[tuple[Any, ...]] = ContextVar("weasysvg_active_masks", default=())


def _mask_region(svg: Any, node: Any, mask: Any, font_size: float) -> tuple[float, float, float, float] | None:
    size = wp_utils.size
    if mask.get("maskUnits") == "userSpaceOnUse":
        return (
            size(mask.get("x", "-10%"), font_size, svg.inner_width),
            size(mask.get("y", "-10%"), font_size, svg.inner_height),
            size(mask.get("width", "120%"), font_size, svg.inner_width),
            size(mask.get("height", "120%"), font_size, svg.inner_height),
        )
    box = svg.calculate_bounding_box(node, font_size, stroke=False)
    if not box:
        return None
    bx, by, bw, bh = box
    return (
        bx + size(mask.get("x", "-10%"), font_size, 1) * bw,
        by + size(mask.get("y", "-10%"), font_size, 1) * bh,
        size(mask.get("width", "120%"), font_size, 1) * bw,
        size(mask.get("height", "120%"), font_size, 1) * bh,
    )


def paint_mask(svg: Any, node: Any, mask: Any, font_size: float) -> None:
    """Set mask as the soft mask of the current state. draw_node of WeasyPrint passes the opacity as font_size."""
    # A mask that references itself: ignore the inner reference, as Chromium and resvg do
    if any(mask is active for active in _ACTIVE_MASKS.get()):
        return
    region = _mask_region(svg, node, mask, font_size)
    if region is None:
        return
    box = None
    if mask.get("maskContentUnits") == "objectBoundingBox":
        box = svg.calculate_bounding_box(node, font_size, stroke=False)
        if not box:
            return
    if _core.PORTABLE.get() and (shapes := _binary_shapes(mask, box is not None)) is not None:
        _clip_binary(svg, shapes, font_size, region, box)
        return
    saved_transform = mask.attrib.get("transform")
    # Chromium ignores mask on a <mask> element
    saved_mask = mask.attrib.pop("mask", None)
    tag = mask._etree_node.tag
    token = _ACTIVE_MASKS.set((*_ACTIVE_MASKS.get(), mask))
    styles = _plain_content()
    svg_stream = svg.stream
    try:
        if box is not None:
            mask.attrib["transform"] = f"matrix({box[2]} 0 0 {box[3]} {box[0]} {box[1]})"
        mask._etree_node.tag = "g"
        svg.stream = svg.stream.set_alpha_state(*region)
        svg.draw_node(mask, font_size)
    finally:
        svg.stream = svg_stream
        _ACTIVE_MASKS.reset(token)
        _restore_content(styles)
        # Without this the walk later meets a <g> where the <mask> was, and draws its content
        mask._etree_node.tag = tag
        if saved_mask is not None:
            mask.attrib["mask"] = saved_mask
        if saved_transform is None:
            mask.attrib.pop("transform", None)
        else:
            mask.attrib["transform"] = saved_transform


# ---------------- gray masks as an opacity, for a portable PDF ----------------

# What a luminosity soft mask takes of each channel: DeviceRGB converted to DeviceGray
LUMINANCE = (0.3, 0.59, 0.11)
# Children of a mask that draw nothing
UNDRAWN = frozenset(("defs", "desc", "linearGradient", "metadata", "radialGradient", "style", "title"))


@dataclass
class GrayMask:
    """A mask of one shape in one color: the element in a group, clipped to the shape, at one opacity.

    A gradient mask stays a soft mask. Drawn as nested levels it copied the element once per level, and a
    renderer with 8 bit layers lost the faint levels over light colors: Chromium and librsvg faded too fast.
    """

    region: tuple[float, float, float, float]
    outline: list[clippaths.Subpath]
    opacity: float
    content: Any = None

    def start(self, stream: Any, box: tuple[float, float, float, float]) -> Any:
        """The group to draw the element into."""
        self.content = stream.add_group(*box)
        return self.content

    def draw(self, stream: Any, blend: str | None = None) -> None:
        """Draw the element through the mask onto stream, blended as blend says."""
        if not self.outline or self.opacity <= 0:
            return
        stream.push_state()
        try:
            # The element blends with what lies under it: inside its group there is nothing to blend with
            if blend is not None:
                stream.set_blend_mode(blend)
            stream.rectangle(*self.region)
            stream.clip()
            stream.end()
            clippaths.add(stream, self.outline)
            stream.clip()
            stream.end()
            stream.set_alpha(self.opacity, stroke=True, fill=True)
            stream.draw_x_object(self.content.id)
        finally:
            stream.pop_state()


def gray_mask(svg: Any, node: Any, mask: Any, font_size: float) -> GrayMask | None:
    """The mask of one shape in one color, gray or translucent, in a portable PDF; None for any other mask.

    A clip draws opaque white and black alone (_binary_shapes): those stay clips.
    """
    # Definitions inside the mask draw nothing
    children = [child for child in mask if child.tag not in UNDRAWN]
    if not _core.PORTABLE.get() or len(children) != 1:
        return None
    shape = children[0]
    paint = str(shape.get("fill", "black")).strip()
    if _mask_effects(mask):
        return None
    # Its own transform moves its outline
    if shape.tag not in SHAPES or paint.startswith("url(") or any(shape.get(key) not in (None, "", "none", "0") for key in BINARY_EXCLUDED if key != "transform"):
        return None
    if _binary_shapes(mask, mask.get("maskContentUnits") == "objectBoundingBox") is not None:
        return None
    region = _mask_region(svg, node, mask, font_size)
    if region is None:
        return None
    content = Matrix()
    if mask.get("maskContentUnits") == "objectBoundingBox":
        box = svg.calculate_bounding_box(node, font_size, stroke=False)
        if not wp_defs.is_valid_bounding_box(box):
            return None
        content = Matrix(a=box[2], d=box[3], e=box[0], f=box[1])
    try:
        outline = _shape_outline(svg, shape, font_size, content)
    except coverage.Unsupported:
        return None
    # fill="none" is black for the binary check already: a clip of nothing
    value = wp_utils.color(paint)
    red, green, blue = (min(max(float(channel), 0.0), 1.0) for channel in value.to("srgb").coordinates)
    fade = wp_utils.alpha_value(shape.get("opacity", 1)) * wp_utils.alpha_value(shape.get("fill-opacity", 1)) * wp_utils.alpha_value(mask.get("opacity", 1))
    return GrayMask(region, outline, (LUMINANCE[0] * red + LUMINANCE[1] * green + LUMINANCE[2] * blue) * float(value.alpha) * fade)


def _shape_outline(svg: Any, shape: Any, font_size: float, content: Any) -> list[clippaths.Subpath]:
    """The outline of shape in user space, as one nonzero path."""
    stream = svg.stream
    scratch = stream.add_group(0, 0, 0, 0)
    plain = {"fill": "black", "stroke": "none", "opacity": "1", "fill-opacity": "1"}
    saved = {key: shape.attrib.get(key) for key in plain}
    try:
        scratch.transform(*content.values)
        # The outline alone: an opacity would draw it in a group
        shape.attrib.update(plain)
        svg.stream = scratch
        svg.draw_node(shape, font_size)
    finally:
        svg.stream = stream
        for key, value in saved.items():
            if value is None:
                shape.attrib.pop(key, None)
            else:
                shape.attrib[key] = value
        stream._resources["XObject"].pop(scratch.id, None)
    return clippaths.union(clippaths.read(scratch), _budget(svg))


def _budget(svg: Any) -> Callable[[int], bool]:
    """The charge of work against the budget of the SVG that filters keeps."""
    from . import filters

    return lambda cost: filters._charge(svg, cost)


# ---------------- binary masks as clips, for a portable PDF ----------------

# The shapes a binary mask may hold: each has an outline in the same turning direction, so that nonzero
# fills the union of several
BINARY_SHAPES = frozenset(("rect", "circle", "ellipse"))
# Attributes that make a shape more than an opaque area of one color
BINARY_EXCLUDED = ("transform", "mask", "filter", "clip-path", "stroke")
Point = tuple[float, float]


def _luminance_of(value: str | None) -> bool | None:
    """True for opaque white, False for opaque black, None for any other paint."""
    if value is not None and value.strip().startswith("url("):
        return None
    # The cascade of WeasyPrint gives currentColor as the color it stands for
    rgba = wp_utils.color(value)
    if rgba.alpha != 1:
        return None
    channels = tuple(rgba.to("srgb").coordinates)
    if channels == (1, 1, 1):
        return True
    if channels == (0, 0, 0):
        return False
    return None


def _binary_paint(child: Any, bounding_box_units: bool) -> bool | None:
    """True for a shape of opaque white, False for one of opaque black, None for anything else a clip cannot draw."""
    if child.tag not in BINARY_SHAPES or len(list(child)) > 0:
        return None
    if any(child.get(key) not in (None, "", "none", "0") for key in BINARY_EXCLUDED):
        return None
    # A rounded rect has no outline here
    if child.tag == "rect" and any(child.get(key) not in (None, "", "0") for key in ("rx", "ry")):
        return None
    if child.get("display") == "none" or child.get("visibility") in ("hidden", "collapse"):
        return None
    if any(wp_utils.alpha_value(child.get(key, "1")) != 1 for key in ("opacity", "fill-opacity")):
        return None
    # Percentages of the viewport have no meaning in bounding box units
    if bounding_box_units and any("%" in str(child.get(key, "")) for key in ("x", "y", "width", "height", "cx", "cy", "r", "rx", "ry")):
        return None
    return _luminance_of(child.get("fill", "black"))


def _mask_effects(mask: Any) -> bool:
    """Whether the <mask> itself has an effect a clip cannot draw: a filter, a clip path or a transform."""
    return any(mask.get(key) not in (None, "", "none") for key in ("filter", "clip-path", "transform"))


def _binary_shapes(mask: Any, bounding_box_units: bool) -> list[tuple[Any, bool]] | None:
    """The shapes of a mask that is opaque white areas, then opaque black ones, else None.

    Such a mask shows the union of the white areas less the union of the black ones: a clip path draws
    the same picture without a soft mask. A D2 diagram cuts the edges under its labels this way. Without
    a white area it hides the element.
    """
    # The soft mask draws the <mask> as a group, with its own opacity and effects
    if _mask_effects(mask) or wp_utils.alpha_value(mask.get("opacity", 1)) != 1:
        return None
    shapes: list[tuple[Any, bool]] = []
    for child in mask:
        white = _binary_paint(child, bounding_box_units)
        if white is None or (white and shapes and not shapes[-1][1]):
            return None  # a white area over a black one needs more than one clip
        shapes.append((child, white))
    return shapes


def _outline(svg: Any, node: Any, font_size: float, place: Callable[[float, float], Point]) -> list[list[Point]]:
    """The outline of a rect, circle or ellipse as closed polygons of Bezier control points."""
    if node.tag == "rect":
        x, y = svg.point(node.get("x"), node.get("y"), font_size)
        width, height = svg.point(node.get("width"), node.get("height"), font_size)
        if width <= 0 or height <= 0:
            return []
        return [[place(x, y), place(x + width, y), place(x + width, y + height), place(x, y + height)]]
    if node.tag == "circle":
        rx = ry = svg.length(node.get("r"), font_size)
    else:
        rx, ry = svg.point(node.get("rx"), node.get("ry"), font_size)
    if rx <= 0 or ry <= 0:
        return []
    cx, cy = svg.point(node.get("cx"), node.get("cy"), font_size)
    kx, ky = ARC_CONSTANT * rx, ARC_CONSTANT * ry
    # The quarters of ellipse(), from (cx + rx, cy) toward positive y: the turning direction of the rect
    return [
        [
            place(cx + rx, cy),
            place(cx + rx, cy + ky), place(cx + kx, cy + ry), place(cx, cy + ry),
            place(cx - kx, cy + ry), place(cx - rx, cy + ky), place(cx - rx, cy),
            place(cx - rx, cy - ky), place(cx - kx, cy - ry), place(cx, cy - ry),
            place(cx + kx, cy - ry), place(cx + rx, cy - ky), place(cx + rx, cy),
        ]
    ]  # fmt: skip


def _add_outline(stream: Any, outline: list[Point]) -> None:
    stream.move_to(*outline[0])
    if len(outline) == 4:
        for point in outline[1:]:
            stream.line_to(*point)
    else:
        for index in range(1, len(outline), 3):
            stream.curve_to(*outline[index], *outline[index + 1], *outline[index + 2])
    stream.close()


def _clip_binary(svg: Any, shapes: list[tuple[Any, bool]], font_size: float, region: tuple[float, float, float, float], box: Any) -> None:
    """Clip the current state to the mask region, the union of the white shapes, then out of each black one."""
    stream = svg.stream

    def place(x: float, y: float) -> Point:
        return (box[0] + x * box[2], box[1] + y * box[3]) if box is not None else (x, y)

    stream.rectangle(*region)
    stream.clip()
    stream.end()
    whites = [outline for node, white in shapes if white for outline in _outline(svg, node, font_size, place)]
    if not whites:
        stream.rectangle(region[0], region[1], 0, 0)  # an empty mask hides the element
        stream.clip()
        stream.end()
        return
    for outline in whites:
        _add_outline(stream, outline)
    stream.clip()
    stream.end()
    # The region with the shape inside, even-odd: the region less the shape. Each clip narrows the last
    for node, white in shapes:
        if white:
            continue
        for outline in _outline(svg, node, font_size, place):
            stream.rectangle(*region)
            _add_outline(stream, outline)
            stream.clip(even_odd=True)
            stream.end()


def _plain_content() -> tuple[Any, Any]:
    """Draw mask or clip content as written: a blur pass around it must not grow or recolor it."""
    from . import filters

    return filters.RESTYLE.set(None), filters.RECOLOR.set(())


def _restore_content(tokens: tuple[Any, Any]) -> None:
    from . import filters

    filters.RESTYLE.reset(tokens[0])
    filters.RECOLOR.reset(tokens[1])


# ---------------- complex clip paths ----------------

CLIP_SHAPES = frozenset(("circle", "ellipse", "line", "path", "polyline", "polygon", "rect", "text", "tspan", "textPath"))
_CLIPPING: ContextVar[bool] = ContextVar("weasysvg_clipping", default=False)


def complex_clip(svg: Any, node: Any) -> Any:
    """The clip path of node when one W clip cannot express it, else None."""
    value = node.get("clip-path")
    if not value:
        return None
    clip = svg.paths.get(wp_utils.parse_url(value).fragment)
    # A clip path being drawn is tagged <g>: a cycle back to it ends here
    if clip is None or clip.tag != "clipPath":
        return None
    # WeasyPrint sizes an objectBoundingBox clip by x, y, width and height: right for a <rect> only
    if clip.get("clipPathUnits") == "objectBoundingBox":
        return clip
    children = list(clip)
    # WeasyPrint adds the outlines of several children to one nonzero path: two that turn opposite ways cut a hole
    if len(children) > 1:
        return clip
    for child in children:
        if child.get("clip-path") or child.get("clip-rule") == "evenodd" or child.tag in ("text", "use"):
            return clip
    return None


def clip_restyle(_svg: Any, node: Any, _font_size: float) -> dict[str, str | None] | None:
    """Inside a clip mask a shape counts by its geometry: filled by its clip-rule, no stroke, no effects."""
    if not _CLIPPING.get():
        return None
    # The children cascade the original style first: they keep their own copy of it
    list(node)
    # A <use> or <g> in a clip path adds no opacity, filter or mask either
    new = {"opacity": "1", "filter": "none", "mask": "none"}
    if node.tag in CLIP_SHAPES:
        new |= {"fill": "black", "fill-rule": node.get("clip-rule", "nonzero"), "fill-opacity": "1", "stroke": "none"}
    saved = {key: node.attrib.get(key) for key in new}
    node.attrib.update(new)
    return saved


def paint_clip(svg: Any, node: Any, clip: Any, font_size: float) -> None:
    """Clip the current state to clip, each child filled by its clip-rule.

    The fills become one path where it can hold them (clippaths.py), else the alpha soft mask of clip: Word
    draws no soft mask, and a printer may rasterize it.
    """
    stream = svg.stream
    box = _core.group_box(svg, node, font_size)
    if _clip_as_path(svg, node, clip, font_size, box):
        return
    _draw_clip_content(svg, node, clip, font_size, stream.set_alpha_state(*box, mode="alpha"))


def _draw_clip_content(svg: Any, node: Any, clip: Any, font_size: float, target: Any) -> bool:
    """Draw the children of clip on target, filled; False when its box units leave nothing to draw."""
    if clip.get("clipPathUnits") == "objectBoundingBox":
        box = svg.calculate_bounding_box(node, font_size, stroke=False)
        if not wp_defs.is_valid_bounding_box(box):
            return False  # an empty mask: the node is clipped away, as in Chromium
        target.transform(a=box[2], d=box[3], e=box[0], f=box[1])
    stream = svg.stream
    tag = clip._etree_node.tag
    token = _CLIPPING.set(True)
    styles = _plain_content()
    try:
        svg.stream = target
        clip._etree_node.tag = "g"
        svg.draw_node(clip, font_size)
    finally:
        clip._etree_node.tag = tag
        svg.stream = stream
        _CLIPPING.reset(token)
        _restore_content(styles)
    return True


def _clip_as_path(svg: Any, node: Any, clip: Any, font_size: float, box: tuple[float, float, float, float]) -> bool:
    """Clip the current state to the fills of clip as one path; False when they need the soft mask."""
    stream = svg.stream
    scratch = stream.add_group(*box)
    try:
        subpaths = clippaths.union(clippaths.read(scratch), _budget(svg)) if _draw_clip_content(svg, node, clip, font_size, scratch) else []
    except coverage.Unsupported as error:
        LOGGER.debug("SVG clip path keeps its soft mask: %s", error)
        return False
    finally:
        stream._resources["XObject"].pop(scratch.id, None)
    if subpaths:
        clippaths.add(stream, subpaths)
    else:
        stream.rectangle(box[0], box[1], 0, 0)  # nothing drawn: the node is clipped away
    stream.clip()
    stream.end()
    return True


# ---------------- draw_node helpers, used by _core ----------------


def blend_mode(node: Any) -> str | None:
    return BLEND_MODES.get(str(node.get("mix-blend-mode", "")).strip().lower())


def early_mask(svg: Any, node: Any) -> Any:
    """The mask of any element, set before it is drawn.

    WeasyPrint sets the mask of a shape after the path is begun. A gs operator inside path construction is
    invalid PDF, and viewers ignore it: a masked shape came out unmasked (the D2 edge labels).
    """
    mask_url = node.get("mask")
    if not mask_url:
        return None
    return svg.masks.get(wp_utils.parse_url(mask_url).fragment)


def ellipse(svg: Any, node: Any, font_size: float) -> None:
    """A circle or an ellipse in four Bezier quarters, from (cx + rx, cy) in the direction of positive y."""
    if node.tag == "circle":
        rx = ry = svg.length(node.get("r"), font_size)
    else:
        rx, ry = svg.point(node.get("rx"), node.get("ry"), font_size)
    if rx <= 0 or ry <= 0:
        return
    cx, cy = svg.point(node.get("cx"), node.get("cy"), font_size)
    kx, ky = ARC_CONSTANT * rx, ARC_CONSTANT * ry
    stream = svg.stream
    stream.move_to(cx + rx, cy)
    stream.curve_to(cx + rx, cy + ky, cx + kx, cy + ry, cx, cy + ry)
    stream.curve_to(cx - kx, cy + ry, cx - rx, cy + ky, cx - rx, cy)
    stream.curve_to(cx - rx, cy - ky, cx - kx, cy - ry, cx, cy - ry)
    stream.curve_to(cx + kx, cy - ry, cx + rx, cy - ky, cx + rx, cy)
    stream.close()


def fix_arcs(root: ET.Element) -> None:
    """Write the arcs of path data WeasyPrint draws wrong as the lines and curves SVG draws for them."""
    for element in root.iter():
        if isinstance(element.tag, str) and element.tag.rpartition("}")[2] == "path" and (fixed := pathdata.rewritten_arcs(element.get("d"))) is not None:
            element.set(pathdata.ORIGINAL_D, element.get("d", ""))
            element.set("d", fixed)


def install(*, blend: bool = True) -> None:
    from . import paint_order

    wp_svg.TAGS["circle"] = wp_svg.TAGS["ellipse"] = ellipse
    paint_order.install_dashes()
    _core.add_tree_pass(20, "empty_presentation", drop_empty_presentation)
    _core.add_tree_pass(20, "arcs", fix_arcs)
    wp_defs.draw_gradient = wp_svg.draw_gradient = draw_gradient
    wp_stream.Stream.set_alpha_state = _set_alpha_state
    wp_stream.Stream.paint_shading = _paint_shading
    wp_defs.draw_pattern = wp_svg.draw_pattern = draw_pattern
    wp_defs.paint_mask = wp_svg.paint_mask = paint_mask
    wp_svg.SVG.set_graphical_state = set_graphical_state
    _core.add_restyler(clip_restyle)
    wp_svg.Node.override_iter = _materialized_override_iter
    _core.enable_draw_feature("masks")
    if blend:
        # mix-blend-mode is not inherited: without this the cascade copies it to every child
        wp_svg.NOT_INHERITED_ATTRIBUTES = wp_svg.NOT_INHERITED_ATTRIBUTES | {"mix-blend-mode", "isolation"}
        _core.enable_draw_feature("blend")
