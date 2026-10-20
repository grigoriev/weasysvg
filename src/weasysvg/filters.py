"""Vector rendering of the common filter chains, and of CSS drop-shadow() and blur().

Touches: ``svg.SVG.draw_node`` through the shared wrapper of ``_core``. WeasyPrint only shifts the
element for feOffset and drops the rest, so shadows came out as the element itself, offset.

A chain is evaluated into layers: source (the element, offset, faded or recolored), alpha (its
silhouette in one color) and flood (a rectangle). Supported: feOffset, feGaussianBlur, feFlood,
feDropShadow, feMerge, feBlend normal, feComposite over and in, feColorMatrix, feComponentTransfer.
A chain with any other primitive draws the element unfiltered, with a warning.

feColorMatrix and feComponentTransfer recolor: each color the element paints with goes through the
functions, in linearRGB unless color-interpolation-filters says sRGB. Touches ``svg.color`` and
``svg.defs.color``, which parse the fill, stroke and stop colors, and ``svg.draw_gradient``: a
recolored gradient gets intermediate stops, since the functions do not commute with interpolation.
Images inside keep their colors.

PDF has no blur. A blurred layer is drawn through a soft mask that steps through the Gaussian profile
of its edge: outside, the shape grown by a stroke; inside, bands along the edge (see _blur_mask).
"""

from __future__ import annotations

import logging
import math
import re
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from statistics import NormalDist
from typing import Any, cast

from weasyprint import svg as wp_svg
from weasyprint.svg import defs as wp_defs
from weasyprint.svg import utils as wp_utils
from weasyprint.svg.bounding_box import is_valid_bounding_box
from weasyprint.svg.utils import alpha_value, color, parse_url, size

from . import _core

LOGGER = logging.getLogger("weasysvg")
Region = tuple[float, float, float, float]
RGBA = tuple[float, float, float, float]
Recolor = Callable[[RGBA], RGBA]


class Unsupported(Exception):
    pass


@dataclass(frozen=True)
class Layer:
    kind: str  # source | alpha | flood
    dx: float = 0
    dy: float = 0
    rgba: Any = None
    opacity: float = 1
    blur: tuple[float, float] = (0.0, 0.0)  # standard deviation along x and y
    region: tuple[float, float, float, float] | None = None
    recolor: tuple[Recolor, ...] = ()  # for a source: applied to every color it paints with


@dataclass(frozen=True)
class Plan:
    layers: list[Layer]
    region: tuple[float, float, float, float] | None


UNFILTERED = Plan([Layer("source")], None)


def _add_blur(blur: tuple[float, float], std: tuple[float, float]) -> tuple[float, float]:
    """Two Gaussian blurs in a row are one, with the root of the summed variances."""
    return (math.hypot(blur[0], std[0]), math.hypot(blur[1], std[1]))


def _std(value: str | None, default: str) -> tuple[float, float]:
    numbers = [_num(v, -1) for v in (value or default).replace(",", " ").split()]
    if not numbers or len(numbers) > 2 or any(n < 0 for n in numbers):
        return (0.0, 0.0)  # an invalid or negative value disables the blur
    return (numbers[0], numbers[-1])


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default  # SVG 2: dx/dy are numbers, "10%" is invalid


def _with_alpha(rgba: Any, factor: float) -> Any:
    return rgba.__class__(rgba.space, rgba.coordinates, rgba.alpha * factor)


def _flood(node: Any) -> tuple[Any, float]:
    return color(node.get("flood-color", "black")), alpha_value(node.get("flood-opacity", 1))


def _silhouette(layers: list[Layer], rgba: Any, opacity: float) -> list[Layer]:
    out = []
    for layer in layers:
        if layer.kind == "flood":
            out.append(replace(layer, rgba=rgba, opacity=layer.opacity * opacity))
        else:
            out.append(replace(layer, kind="alpha", rgba=rgba, opacity=layer.opacity * opacity, recolor=()))
    return out


@dataclass
class _Chain:
    """One filter chain while it is evaluated: its named results, the output of the last primitive and the input of the current one."""

    svg: Any
    filter_node: Any
    region: Region
    font_size: float
    # The box that primitiveUnits="objectBoundingBox" refers to; one user unit per unit otherwise
    unit: Region = (0.0, 0.0, 1.0, 1.0)
    results: dict[str, list[Layer]] = field(default_factory=dict)
    last: list[Layer] = field(default_factory=lambda: [Layer("source")])
    source: list[Layer] = field(default_factory=list)

    def scaled(self, x: float, y: float) -> tuple[float, float]:
        """A length pair in user units: offsets and standard deviations."""
        return x * self.unit[2], y * self.unit[3]

    def get(self, name: str | None) -> list[Layer]:
        if name in (None, ""):
            return self.last
        if name == "SourceGraphic":
            return [Layer("source")]
        if name == "SourceAlpha":
            return [Layer("alpha", rgba=color("black"))]
        if name in self.results:
            return self.results[name]
        raise Unsupported(f"input {name}")


def _fe_offset(chain: _Chain, child: Any) -> list[Layer]:
    dx, dy = chain.scaled(_num(child.get("dx")), _num(child.get("dy")))
    return [replace(layer, dx=layer.dx + dx, dy=layer.dy + dy) for layer in chain.source]


def _fe_gaussian_blur(chain: _Chain, child: Any) -> list[Layer]:
    std = chain.scaled(*_std(child.get("stdDeviation"), "0"))
    return [replace(layer, blur=_add_blur(layer.blur, std)) for layer in chain.source]


def _fe_flood(chain: _Chain, child: Any) -> list[Layer]:
    rgba, opacity = _flood(child)
    sub = chain.region
    if any(child.get(key) is not None for key in ("x", "y", "width", "height")):
        svg, font_size = chain.svg, chain.font_size
        rx, ry, rw, rh = chain.region
        ux, uy, uw, uh = chain.unit
        relative = chain.unit != (0.0, 0.0, 1.0, 1.0)
        width, height = (1, 1) if relative else (svg.inner_width, svg.inner_height)
        x, y = child.get("x"), child.get("y")
        sub = (
            ux + size(x, font_size, width) * uw if x is not None else rx,
            uy + size(y, font_size, height) * uh if y is not None else ry,
            size(child.get("width"), font_size, width) * uw if child.get("width") is not None else rw,
            size(child.get("height"), font_size, height) * uh if child.get("height") is not None else rh,
        )
    return [Layer("flood", rgba=rgba, opacity=opacity, region=sub)]


def _fe_drop_shadow(chain: _Chain, child: Any) -> list[Layer]:
    rgba, opacity = _flood(child)
    dx, dy = chain.scaled(_num(child.get("dx"), 2), _num(child.get("dy"), 2))
    std = chain.scaled(*_std(child.get("stdDeviation"), "2"))
    shadow = [replace(layer, dx=layer.dx + dx, dy=layer.dy + dy, blur=_add_blur(layer.blur, std)) for layer in _silhouette(chain.source, rgba, opacity)]
    return shadow + list(chain.source)


def _fe_merge(chain: _Chain, child: Any) -> list[Layer]:
    out: list[Layer] = []
    for merge_node in child:
        if merge_node.tag == "feMergeNode":
            out += chain.get(merge_node.get("in"))
    return out


def _fe_blend(chain: _Chain, child: Any) -> list[Layer]:
    if child.get("mode", "normal") != "normal":
        raise Unsupported("feBlend mode")
    return list(chain.get(child.get("in2"))) + list(chain.source)


def _fe_composite(chain: _Chain, child: Any) -> list[Layer]:
    operator = child.get("operator", "over")
    backdrop = chain.get(child.get("in2"))
    if operator == "over":
        return list(backdrop) + list(chain.source)
    if operator == "in" and len(chain.source) == 1 and chain.source[0].kind == "flood":
        # Colorize a silhouette: the common shadow idiom
        return _silhouette(backdrop, chain.source[0].rgba, chain.source[0].opacity)
    raise Unsupported(f"feComposite {operator}")


# ---------------- recoloring ----------------


def _to_linear(value: float) -> float:
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _to_srgb(value: float) -> float:
    return value * 12.92 if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055


def _clamp(value: float) -> float:
    return min(max(value, 0.0), 1.0)


def _in_space(function: Recolor, chain: _Chain, child: Any) -> Recolor:
    """The function, run in linearRGB unless color-interpolation-filters says sRGB."""
    space = (child.get("color-interpolation-filters") or chain.filter_node.get("color-interpolation-filters") or "linearRGB").lower()
    if space == "srgb":
        return function

    def linear(rgba: RGBA) -> RGBA:
        r, g, b, a = function((_to_linear(rgba[0]), _to_linear(rgba[1]), _to_linear(rgba[2]), rgba[3]))
        return _to_srgb(r), _to_srgb(g), _to_srgb(b), a

    return linear


def _matrix(values: list[float]) -> Recolor:
    """A 4 x 5 color matrix on unpremultiplied RGBA."""

    def apply(rgba: RGBA) -> RGBA:
        vector = (*rgba, 1.0)
        r, g, b, a = (_clamp(sum(values[row * 5 + column] * vector[column] for column in range(5))) for row in range(4))
        return r, g, b, a

    return apply


def _color_matrix_values(child: Any) -> list[float]:
    kind = child.get("type", "matrix")
    numbers = [_num(value, math.nan) for value in (child.get("values") or "").replace(",", " ").split()]
    if any(math.isnan(number) for number in numbers):
        numbers = []
    if kind == "saturate":
        s = numbers[0] if len(numbers) == 1 else 1.0
        return [
            *(0.213 + 0.787 * s, 0.715 - 0.715 * s, 0.072 - 0.072 * s, 0, 0),
            *(0.213 - 0.213 * s, 0.715 + 0.285 * s, 0.072 - 0.072 * s, 0, 0),
            *(0.213 - 0.213 * s, 0.715 - 0.715 * s, 0.072 + 0.928 * s, 0, 0),
            *(0, 0, 0, 1, 0),
        ]
    if kind == "hueRotate":
        angle = math.radians(numbers[0] if len(numbers) == 1 else 0.0)
        c, s = math.cos(angle), math.sin(angle)
        return [
            *(0.213 + c * 0.787 - s * 0.213, 0.715 - c * 0.715 - s * 0.715, 0.072 - c * 0.072 + s * 0.928, 0, 0),
            *(0.213 - c * 0.213 + s * 0.143, 0.715 + c * 0.285 + s * 0.140, 0.072 - c * 0.072 - s * 0.283, 0, 0),
            *(0.213 - c * 0.213 - s * 0.787, 0.715 - c * 0.715 + s * 0.715, 0.072 + c * 0.928 + s * 0.072, 0, 0),
            *(0, 0, 0, 1, 0),
        ]
    if kind == "luminanceToAlpha":
        return [*(0,) * 15, 0.2125, 0.7154, 0.0721, 0, 0]
    if kind != "matrix":
        raise Unsupported(f"feColorMatrix {kind}")
    # A missing or wrong count of values is the identity
    return numbers if len(numbers) == 20 else [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0]


def _identity(value: float) -> float:
    return value


def _transfer(function: Any) -> Callable[[float], float]:
    """One feFunc: identity, table, discrete, linear or gamma."""
    kind = function.get("type", "identity")
    table = [_num(value) for value in (function.get("tableValues") or "").replace(",", " ").split()]
    if kind == "table" and table:
        n = len(table) - 1
        return lambda c: table[n] if n == 0 or c >= 1 else table[int(c * n)] + (c * n - int(c * n)) * (table[int(c * n) + 1] - table[int(c * n)])
    if kind == "discrete" and table:
        return lambda c: table[min(int(c * len(table)), len(table) - 1)]
    if kind == "linear":
        slope, intercept = _num(function.get("slope"), 1), _num(function.get("intercept"))
        return lambda c: slope * c + intercept
    if kind == "gamma":
        amplitude, exponent, offset = _num(function.get("amplitude"), 1), _num(function.get("exponent"), 1), _num(function.get("offset"))
        return lambda c: amplitude * c**exponent + offset
    return _identity


def _component_transfer(child: Any) -> Recolor:
    channels: dict[str, Callable[[float], float]] = {}
    for function in child:
        if function.tag in ("feFuncR", "feFuncG", "feFuncB", "feFuncA"):
            channels[function.tag[-1]] = _transfer(function)
    r, g, b, a = (channels.get(name, _identity) for name in "RGBA")

    def apply(rgba: RGBA) -> RGBA:
        return _clamp(r(rgba[0])), _clamp(g(rgba[1])), _clamp(b(rgba[2])), _clamp(a(rgba[3]))

    return apply


def recolored(rgba: Any, functions: tuple[Recolor, ...]) -> Any:
    """A parsed color after the functions, in sRGB."""
    red, green, blue = rgba.to("srgb").coordinates
    value: RGBA = (_clamp(red), _clamp(green), _clamp(blue), rgba.alpha)
    for function in functions:
        value = function(value)
    return rgba.__class__("srgb", value[:3], value[3])


def _recolor_layers(layers: list[Layer], function: Recolor) -> list[Layer]:
    out = []
    for layer in layers:
        if layer.kind == "source":
            out.append(replace(layer, recolor=(*layer.recolor, function)))
        else:
            # A flood or a silhouette has one color: recolor it now
            out.append(replace(layer, rgba=recolored(_with_alpha(layer.rgba, layer.opacity), (function,)), opacity=1))
    return out


def _fe_component_transfer(chain: _Chain, child: Any) -> list[Layer]:
    funcs = [f for f in child if f.tag in ("feFuncR", "feFuncG", "feFuncB", "feFuncA")]
    if all(f.tag == "feFuncA" and f.get("type") == "linear" and _num(f.get("intercept")) == 0 for f in funcs):
        # An alpha slope fades the whole layer, images included
        slope = _num(funcs[0].get("slope"), 1) if funcs else 1
        return [replace(layer, opacity=layer.opacity * slope) for layer in chain.source]
    return _recolor_layers(chain.source, _in_space(_component_transfer(child), chain, child))


def _fe_color_matrix(chain: _Chain, child: Any) -> list[Layer]:
    values = _color_matrix_values(child)
    if values == [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0]:
        return chain.source
    return _recolor_layers(chain.source, _in_space(_matrix(values), chain, child))


_PRIMITIVES: dict[str, Callable[[_Chain, Any], list[Layer]]] = {
    "feOffset": _fe_offset,
    "feGaussianBlur": _fe_gaussian_blur,
    "feFlood": _fe_flood,
    "feDropShadow": _fe_drop_shadow,
    "feMerge": _fe_merge,
    "feBlend": _fe_blend,
    "feComposite": _fe_composite,
    "feComponentTransfer": _fe_component_transfer,
    "feColorMatrix": _fe_color_matrix,
}


def _evaluate(svg: Any, filter_node: Any, region: tuple[float, float, float, float], font_size: float, unit: Region) -> list[Layer]:
    chain = _Chain(svg, filter_node, region, font_size, unit)
    for child in filter_node:
        chain.source = chain.get(child.get("in"))
        primitive = _PRIMITIVES.get(child.tag)
        if primitive is None:
            raise Unsupported(child.tag)
        out = primitive(chain, child)
        chain.last = out
        if child.get("result"):
            chain.results[child.get("result")] = out
    return chain.last


# The largest filter region coordinate, in user units
MAX_REGION = 1e7


def _region(svg: Any, node: Any, filter_node: Any, font_size: float) -> tuple[float, float, float, float]:
    region = _region_values(svg, node, filter_node, font_size)
    # width="1e999" sizes to inf, 1e308 overflows once scaled: no clip can follow such a
    # region, the element draws unfiltered
    if not all(math.isfinite(value) and abs(value) <= MAX_REGION for value in region):
        raise Unsupported("region out of range")
    return region


def _region_values(svg: Any, node: Any, filter_node: Any, font_size: float) -> tuple[float, float, float, float]:
    if filter_node.get("filterUnits") == "userSpaceOnUse":
        return (
            size(filter_node.get("x", "-10%"), font_size, svg.inner_width),
            size(filter_node.get("y", "-10%"), font_size, svg.inner_height),
            size(filter_node.get("width", "120%"), font_size, svg.inner_width),
            size(filter_node.get("height", "120%"), font_size, svg.inner_height),
        )
    box = svg.calculate_bounding_box(node, font_size, stroke=False)
    if not is_valid_bounding_box(box) and node is svg.tree:
        # WeasyPrint has no box for the root: its viewBox stands in
        box = node.get_viewbox() or (0, 0, svg.inner_width, svg.inner_height)
    if not is_valid_bounding_box(box):
        raise Unsupported("bounding box")
    bx, by, bw, bh = box
    return (
        bx + size(filter_node.get("x", "-10%"), font_size, 1) * bw,
        by + size(filter_node.get("y", "-10%"), font_size, 1) * bh,
        size(filter_node.get("width", "120%"), font_size, 1) * bw,
        size(filter_node.get("height", "120%"), font_size, 1) * bh,
    )


_LENGTH = r"-?[\d.]+(?:px)?"
_DROP_SHADOW = re.compile(rf"^drop-shadow\(\s*(?:(?P<c1>[^\d\s-][^)]*?\)?)\s+)?(?P<dx>{_LENGTH})\s+(?P<dy>{_LENGTH})(?:\s+(?P<blur>{_LENGTH}))?(?:\s+(?P<c2>.+?))?\s*\)$")


def _px(value: str | None) -> float:
    return float(value.removesuffix("px")) if value else 0.0


def _function_layers(value: str) -> list[Layer]:
    """CSS filter functions: drop-shadow() (Mermaid neo look, draw.io) and blur()."""
    value = value.strip()
    if value.startswith("blur("):
        argument = value[len("blur(") : -1].strip()
        if not re.fullmatch(_LENGTH, argument or "0"):
            raise Unsupported(value)  # one length only
        std = _px(argument)
        return [Layer("source", blur=(std, std))]
    match = _DROP_SHADOW.match(value)
    if not match or "," in re.sub(r"\([^()]*\)", "", value[len("drop-shadow(") : -1]):
        raise Unsupported(value)  # commas between arguments are invalid
    rgba = color(match["c1"] or match["c2"] or "black")
    std = _px(match["blur"]) / 2  # the blur radius of CSS is twice the standard deviation
    return [Layer("alpha", dx=_px(match["dx"]), dy=_px(match["dy"]), blur=(std, std), rgba=rgba), Layer("source")]


def _function_plan(value: str) -> Plan:
    """The plan of a CSS filter function list."""
    try:
        return Plan(_function_layers(value), None)
    except Unsupported:
        return UNFILTERED  # an invalid function list: browsers draw the element unfiltered


def _unit(svg: Any, node: Any, filter_node: Any, font_size: float) -> Region:
    if filter_node.get("primitiveUnits") != "objectBoundingBox":
        return (0.0, 0.0, 1.0, 1.0)
    box = svg.calculate_bounding_box(node, font_size, stroke=False)
    if not is_valid_bounding_box(box):
        raise Unsupported("primitiveUnits without a bounding box")
    return cast(Region, tuple(box))


def _reference_plan(svg: Any, node: Any, font_size: float, fragment: str) -> Plan:
    """The plan of a filter element: its vector layers, or the element unfiltered."""
    filter_node = svg.filters.get(fragment)
    if filter_node is None:
        return UNFILTERED
    try:
        region = _region(svg, node, filter_node, font_size)
        return Plan(_evaluate(svg, filter_node, region, font_size, _unit(svg, node, filter_node, font_size)), region)
    except Unsupported as error:
        LOGGER.warning("SVG filter %r is drawn unfiltered: %s is not supported", fragment, error)
        return UNFILTERED


def plan(svg: Any, node: Any, font_size: float) -> Plan | None:
    """The layers for the filter of node, or None when the node keeps the behavior of WeasyPrint."""
    value = node.get("filter")
    if not value or value == "none" or (node.tag == "svg" and node is not svg.tree):
        return None
    fragment = parse_url(value).fragment if value.startswith("url(") else None
    if not fragment:
        return _function_plan(value)
    return _reference_plan(svg, node, font_size, fragment)


# ---------------- vector blur ----------------

# Profile steps on each side of the edge: about six per CSS px of the standard deviation, so no
# step shows at print resolution
MIN_STEPS, MAX_STEPS, STEPS_PER_PX = 4, 16, 6
_GAUSS = NormalDist()
RESTYLED = frozenset(("circle", "ellipse", "line", "path", "polyline", "polygon", "rect", "text", "tspan", "textPath"))


@dataclass(frozen=True)
class Restyle:
    """How the shapes are drawn while a blur mask is built.

    level: the set where the blurred alpha reaches threshold. A filled shape grows by radius, or hides
    above 0.5, where the bands take over. A stroke widens or narrows to the level of a blurred line.
    fills: the filled shapes as they are. band: what lies within radius of the edge of a filled shape.
    grow: the colored source, grown to the widest level.
    """

    kind: str
    sigma: float
    threshold: float = 0.0
    radius: float = 0.0


RESTYLE: ContextVar[Restyle | None] = ContextVar("weasysvg_restyle", default=None)
# The recoloring of the source being drawn: every parsed color goes through it
RECOLOR: ContextVar[tuple[Recolor, ...]] = ContextVar("weasysvg_recolor", default=())
HIDDEN = {"fill": "none", "stroke": "none"}


def line_reach(width: float, sigma: float, threshold: float) -> float | None:
    """How far from its center a blurred line of width keeps alpha threshold; None where it never does."""

    def alpha(distance: float) -> float:
        return _GAUSS.cdf((width / 2 - distance) / sigma) + _GAUSS.cdf((width / 2 + distance) / sigma) - 1

    if alpha(0) <= threshold:
        return None
    low, high = 0.0, width / 2 + 6 * sigma
    for _ in range(40):
        middle = (low + high) / 2
        low, high = (middle, high) if alpha(middle) > threshold else (low, middle)
    return low


def _restyled(mode: Restyle, fill: str, stroke_width: float, fill_opacity: str) -> dict[str, str]:
    """The attributes of one shape in mode: stroke_width is 0 for a shape without stroke."""
    round_ = {"stroke-linejoin": "round", "stroke-linecap": "round"}
    if fill == "none":
        # A line: its blurred profile has its own levels
        if mode.kind in ("fills", "band"):
            return HIDDEN
        threshold = mode.threshold if mode.kind == "level" else 0.5 / MAX_STEPS
        reach = line_reach(stroke_width, mode.sigma, threshold)
        return HIDDEN if reach is None else {**round_, "stroke-width": str(2 * reach)}
    if mode.kind == "fills":
        return {}
    if mode.kind == "level" and mode.threshold >= 0.5:
        return HIDDEN
    grown = {**round_, "stroke-width": str(stroke_width + 2 * mode.radius)}
    if not stroke_width:
        grown.update({"stroke": fill, "stroke-opacity": fill_opacity, "stroke-dasharray": "none"})
    return {**grown, "fill": "none"} if mode.kind == "band" else grown


def _coverage(attributes: dict[str, str], fill: str, stroked: bool) -> dict[str, str]:
    """The mask levels take the shape, not its paint: opaque black wherever the shape paints."""
    out = {**attributes, "fill-opacity": "1", "stroke-opacity": "1", "opacity": "1"}
    if attributes.get("fill", fill) != "none":
        out["fill"] = "black"
    if attributes.get("stroke", "black" if stroked else "none") != "none":
        out["stroke"] = "black"
    return out


def restyle(svg: Any, node: Any, font_size: float) -> dict[str, str | None] | None:
    """Restyle a shape for the blur mask being built; return the attributes to put back, or None."""
    mode = RESTYLE.get()
    if mode is None or node.tag not in RESTYLED:
        return None
    # The children cascade the original style first: they keep their own copy of it
    list(node)
    # A line has no inside to fill
    fill = "none" if node.tag == "line" else node.get("fill", "black")
    stroke = node.get("stroke", "none")
    local = size(node.get("font-size", "1em"), font_size, font_size)
    width = svg.length(node.get("stroke-width", "1px"), local) if stroke != "none" else 0
    if fill == "none" and not width:
        return None
    new = _restyled(mode, fill, width, node.get("fill-opacity", "1"))
    if mode.kind != "grow" and new is not HIDDEN:
        new = _coverage(new, fill, bool(width))
    saved = {key: node.attrib.get(key) for key in new}
    node.attrib.update(new)
    return saved


def unrestyle(node: Any, saved: dict[str, str | None]) -> None:
    for key, value in saved.items():
        if value is None:
            node.attrib.pop(key, None)
        else:
            node.attrib[key] = value


def _sigma(layer: Layer) -> float:
    """One standard deviation for both axes: a stroke grows a shape evenly."""
    return (layer.blur[0] + layer.blur[1]) / 2


def _px_per_unit(svg: Any) -> float:
    """About how many CSS px one user unit spans: the scale of the root viewBox and of the stream."""
    try:
        local = math.sqrt(abs(svg.stream.ctm.determinant)) or 1.0
        viewbox = svg.tree.get_viewbox()
        root = svg.concrete_width / viewbox[2] if viewbox and viewbox[2] else 1.0
        return float(local * root)
    except (AttributeError, TypeError, ZeroDivisionError):
        return 1.0


def levels(sigma: float, steps: int) -> list[Restyle]:
    """The levels of the blurred edge. Level k of 2n holds alpha (k - 0.5) / 2n and is painted k / 2n.

    The blurred alpha at distance d outside a straight edge is Phi(-d / sigma): a filled shape reaches
    the threshold t grown by -sigma * Phi^-1(t).
    """
    delta = 1 / (2 * steps)
    out = []
    for k in range(1, 2 * steps + 1):
        threshold = (k - 0.5) * delta
        out.append(Restyle("level", sigma, threshold, max(-sigma * _GAUSS.inv_cdf(threshold), 0.0)))
    return out


def bands(sigma: float, steps: int) -> list[tuple[Restyle, float]]:
    """The bands inside the edge, widest first, with the gray that 1 loses there.

    At depth d inside the edge the blurred alpha is Phi(d / sigma). 1 minus it, painted widest first, is
    the gray of the narrowest band that still covers the point.
    """
    delta = 1 / (2 * steps)
    return [(Restyle("band", sigma, radius=sigma * _GAUSS.inv_cdf((k - 0.5) * delta)), (2 * steps - k + 1) * delta) for k in range(2 * steps, steps, -1)]


def _gray(value: float) -> Any:
    percent = f"{min(max(value, 0.0), 1.0) * 100:.4f}%"
    return color(f"rgb({percent},{percent},{percent})")


def _draw_into(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, target: Any, mode: Restyle | None, recolor: tuple[Recolor, ...] = ()) -> None:
    previous, token, colors = svg.stream, RESTYLE.set(mode), RECOLOR.set(recolor)
    svg.stream = target
    # original is the draw_node of WeasyPrint: the node itself does not pass the wrapper of _core
    restyled = restyle(svg, node, font_size)
    try:
        original(svg, node, font_size, True, context)
    finally:
        if restyled is not None:
            unrestyle(node, restyled)
        svg.stream = previous
        RESTYLE.reset(token)
        RECOLOR.reset(colors)


def _fill_through(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, target: Any, mode: Restyle, gray: float, box: Region) -> None:
    """Fill box with gray on target, through the alpha of node restyled by mode."""
    target.push_state()
    try:
        shape = target.set_alpha_state(*box, mode="alpha")
        _draw_into(svg, original, node, font_size, context, shape, mode)
        target.set_color(_gray(gray))
        target.rectangle(*box)
        target.fill()
    finally:
        target.pop_state()


def _blur_mask(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, sigma: float, box: Region) -> None:
    """Set the blurred silhouette of node as the soft mask of svg.stream.

    Every level lightens the mask, so each point keeps the highest level it reaches: the grown shapes and
    the lines outside, white minus the bands inside the filled shapes.
    """
    steps = max(MIN_STEPS, min(MAX_STEPS, math.ceil(STEPS_PER_PX * sigma * _px_per_unit(svg))))
    mask = svg.stream.set_alpha_state(*box, mode="luminosity")
    mask.set_blend_mode("Lighten")
    for k, level in enumerate(levels(sigma, steps), 1):
        _fill_through(svg, original, node, font_size, context, mask, level, k / (2 * steps), box)
    mask.push_state()
    try:
        inside = mask.set_alpha_state(*box, mode="alpha")
        _draw_into(svg, original, node, font_size, context, inside, Restyle("fills", sigma))
        group = mask.add_group(*box)
        group.set_color(_gray(1))
        group.rectangle(*box)
        group.fill()
        edge = group.add_group(*box)
        for band, gray in bands(sigma, steps):
            _fill_through(svg, original, node, font_size, context, edge, band, gray, box)
        group.set_blend_mode("Difference")
        group.draw_x_object(edge.id)
        mask.draw_x_object(group.id)
    finally:
        mask.pop_state()


# ---------------- drawing ----------------


def _draw_layers(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, plan_: Plan) -> None:
    layers, region = plan_.layers, plan_.region
    stream = svg.stream
    if region:
        stream.rectangle(*region)
        stream.clip()
        stream.end()
    big = region or _core.group_box(svg, node, font_size)
    for layer in layers:
        stream = svg.stream
        stream.push_state()
        # A failure while drawing must leave svg.stream and the state depth as they were
        try:
            _draw_layer(svg, original, node, font_size, context, layer, stream, big)
        finally:
            svg.stream = stream
            stream.pop_state()


def _draw_layer(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, layer: Layer, stream: Any, big: Region) -> None:
    stream.transform(e=layer.dx, f=layer.dy)
    sigma = _sigma(layer)
    if layer.kind == "flood":
        stream.set_color(_with_alpha(layer.rgba, layer.opacity))
        stream.rectangle(*cast(Region, layer.region))
        stream.fill()
    elif layer.kind == "alpha":
        if sigma:
            # The silhouette of the grown element, in one color, under the blurred edge
            _blur_mask(svg, original, node, font_size, context, sigma, big)
            group = stream.add_group(*big)
            mask = group.set_alpha_state(*big, mode="alpha")
            _draw_into(svg, original, node, font_size, context, mask, _widest(sigma))
            group.set_color(_with_alpha(layer.rgba, layer.opacity))
            group.rectangle(*big)
            group.fill()
            stream.draw_x_object(group.id)
            return
        mask = stream.set_alpha_state(*big, mode="alpha")
        _draw_into(svg, original, node, font_size, context, mask, None)
        stream.set_color(_with_alpha(layer.rgba, layer.opacity))
        stream.rectangle(*big)
        stream.fill()
    else:
        # A blurred source keeps its colors and spreads them to the widest level of the mask
        grow = None
        if sigma:
            _blur_mask(svg, original, node, font_size, context, sigma, big)
            grow = _widest(sigma)
        # A group under the blur mask: a mask or gradient opacity of the element sets a soft mask of its
        # own, which would replace the blur mask in the graphics state
        target = stream.add_group(*big) if layer.opacity < 1 or sigma else stream
        _draw_into(svg, original, node, font_size, context, target, grow, layer.recolor)
        if target is not stream:
            if layer.opacity < 1:
                stream.set_alpha(layer.opacity, stroke=True, fill=True)
            stream.draw_x_object(target.id)


def _widest(sigma: float) -> Restyle:
    """The element grown to the widest level of the blur mask, in its own paint."""
    return Restyle("grow", sigma, radius=levels(sigma, MAX_STEPS)[0].radius)


def draw(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, plan_: Plan, opacity_value: Any) -> None:
    """Draw node through its plan. The caller already applied the transform and removed filter and opacity."""
    opacity = alpha_value(opacity_value)
    outer = svg.stream
    if opacity < 1:
        svg.stream = outer.add_group(*_core.group_box(svg, node, font_size))
    root = svg.stream if node is svg.tree else None
    tag = node._etree_node.tag if root is not None else None
    try:
        if root is not None:
            # The root draws its viewport once, here: each layer draws it as a plain group
            root.push_state()
            wp_svg.TAGS["svg"](svg, node, size(node.get("font-size", "1em"), font_size, font_size))
            node._etree_node.tag = "g"
        _draw_layers(svg, original, node, font_size, context, plan_)
    finally:
        if root is not None:
            node._etree_node.tag = tag
            svg.stream = root
            root.pop_state()
        if opacity < 1:
            group = svg.stream
            svg.stream = outer
            outer.set_alpha(opacity, stroke=True, fill=True)
            outer.draw_x_object(group.id)


_ORIGINAL_COLOR = wp_utils.color
GRADIENT_SAMPLES = 16  # stops per gradient segment while a recolor is active


def _color(string: str | None) -> Any:
    parsed = _ORIGINAL_COLOR(string)
    functions = RECOLOR.get()
    return recolored(parsed, functions) if functions else parsed


@dataclass(frozen=True)
class _Stop:
    attrib: dict[str, str]

    def get(self, key: str, default: Any = None) -> Any:
        return self.attrib.get(key, default)


def sampled_stops(stops: list[Any], font_size: float) -> list[_Stop]:
    """The stops with GRADIENT_SAMPLES - 1 more in each segment, interpolated in sRGB."""
    parsed: list[tuple[float, tuple[float, float, float, float]]] = []
    for stop in stops:
        offset = size(stop.get("offset"), font_size, 1)
        offset = max(min(offset, 1.0), parsed[-1][0] if parsed else 0.0)
        rgba = _ORIGINAL_COLOR(stop.get("stop-color", "black"))
        red, green, blue = rgba.to("srgb").coordinates
        parsed.append((offset, (red, green, blue, rgba.alpha * alpha_value(stop.get("stop-opacity", 1)))))
    out = []
    for (start, first), (end, second) in zip(parsed, parsed[1:], strict=False):
        for i in range(GRADIENT_SAMPLES):
            t = i / GRADIENT_SAMPLES
            value = [a + (b - a) * t for a, b in zip(first, second, strict=True)]
            out.append(_stop(start + (end - start) * t, value))
    out.append(_stop(*parsed[-1]))
    return out


def _stop(offset: float, value: Any) -> _Stop:
    red, green, blue, alpha = (min(max(c, 0.0), 1.0) for c in value)
    return _Stop({"offset": f"{offset}", "stop-color": f"rgb({red * 100}%,{green * 100}%,{blue * 100}%)", "stop-opacity": f"{alpha}"})


def _recolored_gradient(draw_gradient: Callable[..., Any]) -> Callable[..., Any]:
    def draw(svg: Any, node: Any, gradient: Any, font_size: float, opacity: float, stroke: bool) -> Any:
        stops = list(gradient)
        if not RECOLOR.get() or len(stops) < 2:
            return draw_gradient(svg, node, gradient, font_size, opacity, stroke)
        cls = gradient.__class__
        samples = sampled_stops(stops, font_size)
        gradient.__class__ = type(cls.__name__, (cls,), {"__iter__": lambda _: iter(samples)})
        try:
            return draw_gradient(svg, node, gradient, font_size, opacity, stroke)
        finally:
            gradient.__class__ = cls

    return draw


def install() -> None:
    wp_svg.color = wp_defs.color = _color
    wp_svg.draw_gradient = _recolored_gradient(wp_svg.draw_gradient)
    _core.enable_draw_feature("filters")
