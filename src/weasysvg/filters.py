"""Vector rendering of the common filter chains, and of CSS drop-shadow() and blur().

Touches: ``svg.SVG.draw_node`` through the shared wrapper of ``_core``. WeasyPrint only shifts the
element for feOffset and drops the rest, so shadows came out as the element itself, offset.

A chain is evaluated into layers: source (the element, offset, faded or recolored), alpha (its
silhouette in one color), flood (a rectangle) and image (the noise of feTurbulence, see turbulence.py).
Supported: feOffset, feGaussianBlur, feFlood, feDropShadow, feMerge, feBlend normal, feComposite over,
in and arithmetic, feColorMatrix, feComponentTransfer, feTurbulence. A chain with any other primitive
draws the element unfiltered, with a warning.

feComposite arithmetic needs one input to be a flood of the whole region, or both inputs to be the
same layer: the result is then a recolor of the other input, over a flood of its value on nothing.
Where the recolored element is translucent it composites over that flood, which is approximate.

feColorMatrix and feComponentTransfer recolor: each color the element paints with goes through the
functions, in linearRGB unless color-interpolation-filters says sRGB. Touches ``svg.color`` and
``svg.defs.color``, which parse the fill, stroke and stop colors, and ``svg.draw_gradient``: a
recolored gradient gets intermediate stops, since the functions do not commute with interpolation.
Images inside keep their colors.

PDF has no blur. A blurred layer is drawn through a soft mask that steps through the Gaussian profile
of its edge: outside, the shape grown by a stroke; inside, bands along the edge (see _blur_mask).
"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from statistics import NormalDist
from typing import Any, cast

from PIL import Image, ImageFilter
from weasyprint import svg as wp_svg
from weasyprint.images import RasterImage
from weasyprint.svg import defs as wp_defs
from weasyprint.svg import utils as wp_utils
from weasyprint.svg.bounding_box import is_valid_bounding_box
from weasyprint.svg.utils import alpha_value, color, parse_url, size

from . import _core, turbulence

LOGGER = logging.getLogger("weasysvg")
Region = tuple[float, float, float, float]
RGBA = tuple[float, float, float, float]
Recolor = Callable[[RGBA], RGBA]


class Unsupported(Exception):
    pass


@dataclass(frozen=True)
class Layer:
    kind: str  # source | alpha | flood | image
    dx: float = 0
    dy: float = 0
    rgba: Any = None
    opacity: float = 1
    blur: tuple[float, float] = (0.0, 0.0)  # standard deviation along x and y
    region: tuple[float, float, float, float] | None = None
    recolor: tuple[Recolor, ...] = ()  # for a source: applied to every color it paints with
    image: Any = None  # for an image: a Pillow image of straight RGBA pixels over region


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


def _silhouette(svg: Any, layers: list[Layer], rgba: Any, opacity: float) -> list[Layer]:
    out = []
    for layer in layers:
        if layer.kind == "flood":
            out.append(replace(layer, rgba=rgba, opacity=layer.opacity * opacity))
        elif layer.kind == "image":
            out.append(replace(layer, image=_cached_silhouette(svg, layer.image, rgba), opacity=layer.opacity * opacity))
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


def _subregion(chain: _Chain, child: Any) -> Region:
    """The primitive subregion: x, y, width and height of the primitive, the filter region otherwise."""
    if all(child.get(key) is None for key in ("x", "y", "width", "height")):
        return chain.region
    svg, font_size = chain.svg, chain.font_size
    rx, ry, rw, rh = chain.region
    ux, uy, uw, uh = chain.unit
    relative = chain.unit != (0.0, 0.0, 1.0, 1.0)
    width, height = (1, 1) if relative else (svg.inner_width, svg.inner_height)
    x, y = child.get("x"), child.get("y")
    return (
        ux + size(x, font_size, width) * uw if x is not None else rx,
        uy + size(y, font_size, height) * uh if y is not None else ry,
        size(child.get("width"), font_size, width) * uw if child.get("width") is not None else rw,
        size(child.get("height"), font_size, height) * uh if child.get("height") is not None else rh,
    )


def _fe_flood(chain: _Chain, child: Any) -> list[Layer]:
    rgba, opacity = _flood(child)
    return [Layer("flood", rgba=rgba, opacity=opacity, region=_subregion(chain, child))]


def _fe_drop_shadow(chain: _Chain, child: Any) -> list[Layer]:
    rgba, opacity = _flood(child)
    dx, dy = chain.scaled(_num(child.get("dx"), 2), _num(child.get("dy"), 2))
    std = chain.scaled(*_std(child.get("stdDeviation"), "2"))
    shadow = [replace(layer, dx=layer.dx + dx, dy=layer.dy + dy, blur=_add_blur(layer.blur, std)) for layer in _silhouette(chain.svg, chain.source, rgba, opacity)]
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
        return _silhouette(chain.svg, backdrop, chain.source[0].rgba, chain.source[0].opacity)
    if operator == "arithmetic":
        return _arithmetic(chain, child, backdrop)
    raise Unsupported(f"feComposite {operator}")


Coefficients = tuple[tuple[float, float, float], ...]  # per premultiplied channel: of x squared, of x, constant


def _straight(premultiplied: list[float]) -> RGBA:
    alpha = premultiplied[3]
    if alpha <= 0:
        return 0.0, 0.0, 0.0, 0.0
    # A color above its alpha is clamped to it, as Chromium does
    red, green, blue = (min(value, alpha) / alpha for value in premultiplied[:3])
    return red, green, blue, alpha


def _polynomial(coefficients: Coefficients) -> Recolor:
    """A recolor that maps each premultiplied channel x to clamp(a x^2 + b x + c)."""

    def apply(rgba: RGBA) -> RGBA:
        alpha = rgba[3]
        premultiplied = (rgba[0] * alpha, rgba[1] * alpha, rgba[2] * alpha, alpha)
        return _straight([_clamp(a * x * x + b * x + c) for (a, b, c), x in zip(coefficients, premultiplied, strict=True)])

    return apply


def _linear_space(chain: _Chain, child: Any) -> bool:
    return (child.get("color-interpolation-filters") or chain.filter_node.get("color-interpolation-filters") or "linearRGB").lower() != "srgb"


def _premultiplied_flood(chain: _Chain, child: Any, layer: Layer) -> tuple[float, float, float, float]:
    """The color of a flood, premultiplied, in the space of the primitive."""
    rgba = _with_alpha(layer.rgba, layer.opacity)
    channels = [_clamp(value) for value in rgba.to("srgb").coordinates]
    if _linear_space(chain, child):
        channels = [_to_linear(value) for value in channels]
    alpha = rgba.alpha
    return channels[0] * alpha, channels[1] * alpha, channels[2] * alpha, alpha


def _whole(chain: _Chain, layers: list[Layer]) -> bool:
    """One flood over the whole filter region: a constant input."""
    return len(layers) == 1 and layers[0].kind == "flood" and layers[0].region == chain.region and not layers[0].dx and not layers[0].dy


def _arithmetic(chain: _Chain, child: Any, backdrop: list[Layer]) -> list[Layer]:
    """k1 i1 i2 + k2 i1 + k3 i2 + k4, with i1 the input and i2 in2, on premultiplied colors."""
    k1, k2, k3, k4 = (_num(child.get(name)) for name in ("k1", "k2", "k3", "k4"))
    first, second = chain.source, backdrop
    if first == second and len(first) == 1:
        coefficients: Coefficients = ((k1, k2 + k3, k4),) * 4
        other = first
    elif _whole(chain, first):
        flood = _premultiplied_flood(chain, child, first[0])
        coefficients, other = tuple((0.0, k1 * value + k3, k2 * value + k4) for value in flood), second
    elif _whole(chain, second):
        flood = _premultiplied_flood(chain, child, second[0])
        coefficients, other = tuple((0.0, k1 * value + k2, k3 * value + k4) for value in flood), first
    else:
        raise Unsupported("feComposite arithmetic of two variable inputs")
    function = _in_space(_polynomial(coefficients), chain, child)
    recolor = _Recolor(chain.svg, child, function)
    if len(other) != 1 or other[0].blur != (0.0, 0.0) or (other[0].kind == "source" and other[0].opacity < 1):
        raise Unsupported("feComposite arithmetic of a blurred, faded or merged input")
    layer = other[0]
    nothing = function((0.0, 0.0, 0.0, 0.0))
    under = [Layer("flood", rgba=color(_rgba(*nothing)), region=chain.region)] if nothing[3] > 0 else []
    if layer.region == chain.region and layer.kind in ("flood", "image") and not layer.dx and not layer.dy:
        # It covers the region: its transparent pixels map to the value on nothing themselves
        return _recolor_layers(other, recolor)
    if layer.kind == "image" and under:
        raise Unsupported("feComposite arithmetic of a partial image")
    return under + _recolor_layers(other, recolor)


# ---------------- recoloring ----------------


def _to_linear(value: float) -> float:
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _to_srgb(value: float) -> float:
    return value * 12.92 if value <= 0.0031308 else 1.055 * value ** (1 / 2.4) - 0.055


def _clamp(value: float) -> float:
    # nan compares false both ways and would pass through min and max
    return 0.0 if math.isnan(value) else min(max(value, 0.0), 1.0)


def _in_space(function: Recolor, chain: _Chain, child: Any) -> Recolor:
    """The function, run in linearRGB unless color-interpolation-filters says sRGB."""
    if not _linear_space(chain, child):
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


def _table(table: list[float]) -> Callable[[float], float]:
    n = len(table) - 1

    def interpolate(c: float) -> float:
        if n == 0 or c >= 1:
            return table[n]
        k = int(c * n)
        return table[k] + (c * n - k) * (table[k + 1] - table[k])

    return interpolate


def _gamma(amplitude: float, exponent: float, offset: float) -> Callable[[float], float]:
    def gamma(c: float) -> float:
        try:
            value: float = amplitude * c**exponent + offset
            return value
        except (ZeroDivisionError, OverflowError):
            # 0 to a negative power, or a power too large: the clamp that follows takes the infinity
            return math.copysign(math.inf, amplitude) if amplitude else offset

    return gamma


def _transfer(function: Any) -> Callable[[float], float]:
    """One feFunc: identity, table, discrete, linear or gamma."""
    kind = function.get("type", "identity")
    table = [_num(value) for value in (function.get("tableValues") or "").replace(",", " ").split()]
    if kind == "table" and table:
        return _table(table)
    if kind == "discrete" and table:
        return lambda c: table[min(int(c * len(table)), len(table) - 1)]
    if kind == "linear":
        slope, intercept = _num(function.get("slope"), 1), _num(function.get("intercept"))
        return lambda c: slope * c + intercept
    if kind == "gamma":
        return _gamma(_num(function.get("amplitude"), 1), _num(function.get("exponent"), 1), _num(function.get("offset")))
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


# The pure-Python pixel work one SVG may cost: turbulence pixels times octaves, plus recolored pixels
MAX_PIXEL_WORK = 2_000_000


@dataclass
class _Pixels:
    """The images one SVG computed in Python, and the work they cost."""

    images: dict[Any, Image.Image] = field(default_factory=dict)
    inputs: list[Image.Image] = field(default_factory=list)  # keeps the ids in the keys alive
    work: int = 0


def _computed(svg: Any, key: Any, cost: int, compute: Callable[[], Image.Image]) -> Image.Image:
    """The image for key: computed once per SVG, within MAX_PIXEL_WORK."""
    pixels: _Pixels = svg.__dict__.setdefault("_weasysvg_pixels", _Pixels())
    if key not in pixels.images:
        # Each draw of a filtered element evaluates its chain again: only new work counts
        if pixels.work + cost > MAX_PIXEL_WORK:
            raise Unsupported("too much pixel work")
        pixels.work += cost
        pixels.images[key] = compute()
    return pixels.images[key]


@dataclass(frozen=True)
class _Recolor:
    """A recolor function and the primitive it comes from, which identifies it for the image cache."""

    svg: Any
    primitive: Any
    function: Recolor


def _recolor_layers(layers: list[Layer], recolor: _Recolor) -> list[Layer]:
    function = recolor.function
    out = []
    for layer in layers:
        if layer.kind == "source":
            out.append(replace(layer, recolor=(*layer.recolor, function)))
        elif layer.kind == "image":
            # The fade goes into the pixels first: a recolor is not linear in alpha
            out.append(replace(layer, image=_recolored_image(recolor, layer.image, layer.opacity), opacity=1))
        else:
            # A flood or a silhouette has one color: recolor it now
            out.append(replace(layer, rgba=recolored(_with_alpha(layer.rgba, layer.opacity), (function,)), opacity=1))
    return out


def _recolored_image(recolor: _Recolor, picture: Image.Image, opacity: float) -> Image.Image:
    def compute() -> Image.Image:
        recolor.svg.__dict__["_weasysvg_pixels"].inputs.append(picture)
        faded = picture
        if opacity < 1:
            faded = picture.copy()
            faded.putalpha(picture.getchannel("A").point(lambda value: round(value * opacity)))
        return _recolor_image(faded, recolor.function)

    return _computed(recolor.svg, ("recolor", id(recolor.primitive), id(picture), opacity), picture.width * picture.height, compute)


def _recolor_image(picture: Image.Image, function: Recolor) -> Image.Image:
    out = Image.new("RGBA", picture.size)
    data = picture.tobytes()
    pixels = (cast(RGBA, tuple(c / 255 for c in data[i : i + 4])) for i in range(0, len(data), 4))
    out.putdata([tuple(round(_clamp(value) * 255) for value in function(pixel)) for pixel in pixels])
    return out


def _cached_silhouette(svg: Any, picture: Image.Image, rgba: Any) -> Image.Image:
    """The silhouette, the same image on every draw: a recolor after it is cached by its identity."""

    def compute() -> Image.Image:
        svg.__dict__["_weasysvg_pixels"].inputs.append(picture)
        return _image_silhouette(picture, rgba)

    key = ("silhouette", id(picture), tuple(rgba.to("srgb").coordinates), rgba.alpha)
    # Pillow does this work in C: it costs nothing against the budget
    return _computed(svg, key, 0, compute)


def _image_silhouette(picture: Image.Image, rgba: Any) -> Image.Image:
    """The alpha of picture, in the one color rgba."""
    red, green, blue = (round(_clamp(value) * 255) for value in rgba.to("srgb").coordinates)
    out = Image.new("RGBA", picture.size, (red, green, blue, 255))
    out.putalpha(picture.getchannel("A").point(lambda value: round(value * _clamp(rgba.alpha))))
    return out


def _fe_turbulence(chain: _Chain, child: Any) -> list[Layer]:
    numbers = [_num(value, -1) for value in (child.get("baseFrequency") or "0").replace(",", " ").split()]
    if not numbers or len(numbers) > 2 or not all(0 <= number < math.inf for number in numbers):
        numbers = [0.0]  # an invalid, negative or infinite frequency is 0
    region = _subregion(chain, child)
    _checked([Layer("image", region=region)])  # before any pixel is computed
    seed = _num(child.get("seed"))
    spec = turbulence.Turbulence(
        numbers[0] / chain.unit[2],
        numbers[-1] / chain.unit[3],
        int(max(0, min(_num(child.get("numOctaves"), 1), turbulence.MAX_OCTAVES))),
        round(seed) if math.isfinite(seed) else 0,
        child.get("type") == "fractalNoise",  # any other type, an invalid one too, is turbulence
        child.get("stitchTiles") == "stitch",
    )
    if region[2] <= 0 or region[3] <= 0:
        return []
    scale, linear = _core.px_per_unit(chain.svg), _linear_space(chain, child)
    columns, rows = turbulence.size(region, scale)
    image = _computed(chain.svg, ("turbulence", spec, region, scale, linear), columns * rows * max(spec.octaves, 1), lambda: turbulence.image(spec, region, scale, linear))
    return [Layer("image", region=region, image=image)]


def _fe_component_transfer(chain: _Chain, child: Any) -> list[Layer]:
    funcs = [f for f in child if f.tag in ("feFuncR", "feFuncG", "feFuncB", "feFuncA")]
    # An alpha slope in 0..1 fades the layer; outside it the alpha needs the clamp of a recolor
    if all(f.tag == "feFuncA" and f.get("type") == "linear" and _num(f.get("intercept")) == 0 and 0 <= _num(f.get("slope"), 1) <= 1 for f in funcs):
        # An alpha slope fades the whole layer, images included
        slope = _num(funcs[0].get("slope"), 1) if funcs else 1
        return [replace(layer, opacity=layer.opacity * slope) for layer in chain.source]
    return _recolor_layers(chain.source, _Recolor(chain.svg, child, _in_space(_component_transfer(child), chain, child)))


def _fe_color_matrix(chain: _Chain, child: Any) -> list[Layer]:
    values = _color_matrix_values(child)
    if values == [1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0]:
        return chain.source
    return _recolor_layers(chain.source, _Recolor(chain.svg, child, _in_space(_matrix(values), chain, child)))


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
    "feTurbulence": _fe_turbulence,
}


def _evaluate(svg: Any, filter_node: Any, region: tuple[float, float, float, float], font_size: float, unit: Region) -> list[Layer]:
    chain = _Chain(svg, filter_node, region, font_size, unit)
    for child in filter_node:
        chain.source = chain.get(child.get("in"))
        primitive = _PRIMITIVES.get(child.tag)
        if primitive is None:
            raise Unsupported(child.tag)
        out = primitive(chain, child)
        if len(out) > MAX_LAYERS:
            raise Unsupported("too many layers")
        chain.last = out
        if child.get("result"):
            chain.results[child.get("result")] = out
    return chain.last


# The most layers one chain may have: feMerge and feComposite can double them at each primitive
MAX_LAYERS = 64
# The draws of the element that the filters being drawn cost, multiplied along the nesting. A blurred
# layer costs up to 3 * MAX_STEPS + 2 draws, any other one 1.
FAN_OUT: ContextVar[int] = ContextVar("weasysvg_fan_out", default=1)
MAX_DRAWS = 256
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


def _checked(layers: list[Layer]) -> list[Layer]:
    """Refuse lengths no stroke or offset can carry: inf, nan, or beyond MAX_REGION."""
    for layer in layers:
        if min(layer.blur) < 0:
            raise Unsupported("negative blur")  # CSS blur() and drop-shadow() reject it
        if not all(math.isfinite(value) and abs(value) <= MAX_REGION for value in (*layer.blur, layer.dx, layer.dy, *(layer.region or ()))):
            raise Unsupported("length out of range")
    return layers


def _function_plan(value: str) -> Plan:
    """The plan of a CSS filter function list."""
    try:
        return Plan(_checked(_function_layers(value)), None)
    except (Unsupported, ValueError):
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
        return Plan(_checked(_evaluate(svg, filter_node, region, font_size, _unit(svg, node, filter_node, font_size))), region)
    except (Unsupported, ValueError, ArithmeticError) as error:
        # ValueError: a value WeasyPrint cannot parse, such as flood-opacity="abc". ArithmeticError: a
        # number too large for the arithmetic of a primitive
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
# While the passes of a blur draw, a blur inside draws sharp: nested blurs would cost 50 ** depth draws
BLURRING: ContextVar[bool] = ContextVar("weasysvg_blurring", default=False)
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


def recolor_restyle(_svg: Any, node: Any, _font_size: float) -> dict[str, str | None] | None:
    """Fold fill-opacity and stroke-opacity into the colors while a recolor applies.

    WeasyPrint multiplies the opacity in after it parses the color: the recolor would see a color more
    opaque than the pixel it changes in Chromium, and clamp too early.
    """
    if not RECOLOR.get() or node.tag not in RESTYLED:
        return None
    # The children cascade the original style first: they keep their own copy of it
    list(node)
    new = {}
    for paint, opacity, default in (("fill", "fill-opacity", "black"), ("stroke", "stroke-opacity", "none")):
        value = str(node.get(paint, default)).strip()
        if value == "none" or value.startswith(("url(", "context-")):
            continue
        rgba = _ORIGINAL_COLOR(value)
        red, green, blue = (_clamp(c) for c in rgba.to("srgb").coordinates)
        new[paint] = _rgba(red, green, blue, rgba.alpha * alpha_value(node.get(opacity, 1)))
        new[opacity] = "1"
    saved = {key: node.attrib.get(key) for key in new}
    node.attrib.update(new)
    return saved


def _sigma(layer: Layer) -> float:
    """One standard deviation for both axes: a stroke grows a shape evenly."""
    return (layer.blur[0] + layer.blur[1]) / 2


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
    inherited = mode is None
    if inherited:
        # A filtered element inside another keeps the passes and the recolor of the outer one
        mode, recolor = RESTYLE.get(), (*recolor, *RECOLOR.get())
    previous, token, colors = svg.stream, RESTYLE.set(None if inherited else mode), RECOLOR.set(recolor)
    blurring = BLURRING.set(True) if mode is not None else None
    svg.stream = target
    restyled: list[dict[str, str | None]] = []
    try:
        # original is the draw_node of WeasyPrint: the node itself does not pass the wrapper of _core.
        # An inherited pass has grown the node already, in that wrapper: it must not grow twice.
        _core.restyle(svg, node, font_size, restyled)
        RESTYLE.set(mode)
        original(svg, node, font_size, True, context)
    finally:
        _core.unrestyle(node, restyled)
        svg.stream = previous
        RESTYLE.reset(token)
        RECOLOR.reset(colors)
        if blurring is not None:
            BLURRING.reset(blurring)


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
    steps = max(MIN_STEPS, min(MAX_STEPS, math.ceil(STEPS_PER_PX * sigma * _core.px_per_unit(svg))))
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


def _cost(layer: Layer) -> int:
    """The draws of the element one layer makes."""
    blurred = layer.kind not in ("flood", "image") and not BLURRING.get() and _sigma(layer)
    return 3 * MAX_STEPS + 2 if blurred else 1


def _draw_layers(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, plan_: Plan) -> None:
    layers, region = plan_.layers, plan_.region
    stream = svg.stream
    # In a pass of an outer blur the shape grows past this region, as the outer blur spreads past it
    if region and RESTYLE.get() is None:
        stream.rectangle(*region)
        stream.clip()
        stream.end()
    big = region or _core.group_box(svg, node, font_size)
    # Each layer draws the element again, nested filters included: their costs multiply
    fan_out = FAN_OUT.get() * sum(_cost(layer) for layer in layers)
    if fan_out > MAX_DRAWS:
        LOGGER.warning("SVG filter is drawn unfiltered: too many nested layers")
        layers, fan_out = UNFILTERED.layers, FAN_OUT.get()
    token = FAN_OUT.set(fan_out)
    try:
        for layer in layers:
            stream = svg.stream
            stream.push_state()
            # A failure while drawing must leave svg.stream and the state depth as they were
            try:
                _draw_layer(svg, original, node, font_size, context, layer, stream, big)
            finally:
                svg.stream = stream
                stream.pop_state()
    finally:
        FAN_OUT.reset(token)


def _draw_layer(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, layer: Layer, stream: Any, big: Region) -> None:
    stream.transform(e=layer.dx, f=layer.dy)
    sigma = 0.0 if BLURRING.get() else _sigma(layer)
    if layer.kind == "flood":
        stream.set_color(_with_alpha(layer.rgba, layer.opacity))
        stream.rectangle(*cast(Region, layer.region))
        stream.fill()
    elif layer.kind == "image":
        _draw_image(stream, layer, sigma)
    elif layer.kind == "alpha":
        _draw_silhouette(svg, original, node, font_size, context, layer, stream, big, sigma)
    else:
        _draw_source(svg, original, node, font_size, context, layer, stream, big, sigma)


def _draw_image(stream: Any, layer: Layer, sigma: float) -> None:
    """The pixels of an image layer over its region, blurred by Pillow when sigma is set."""
    picture = layer.image
    x, y, width, height = cast(Region, layer.region)
    if sigma:
        # Blur premultiplied, so transparent pixels lend no color
        radius = sigma * picture.width / width
        picture = picture.convert("RGBa").filter(ImageFilter.GaussianBlur(radius)).convert("RGBA")
    if layer.opacity < 1:
        stream.set_alpha(layer.opacity, stroke=True, fill=True)
    stream.transform(e=x, f=y)
    digest = hashlib.sha1(picture.tobytes(), usedforsecurity=False).hexdigest()[:20]
    RasterImage(picture, f"weasysvg{digest}", None).draw(stream, width, height, {"image_rendering": "auto"})


# ---------------- rectangles blurred exactly ----------------

# Samples of the blurred profile across each edge of a rectangle, 4 deviations to each side
EDGE_SAMPLES = 32
EDGE_REACH = 4


def _plain_rect(svg: Any, node: Any, font_size: float) -> Region | None:
    """x, y, width and height of the shape a rect paints, when its blur can draw it exactly.

    That is a rect without rounded corners, with no stroke or a stroke in the paint of its fill: with
    mitered corners such a stroke only widens the rect by half its width on each side.
    """
    if node.tag != "rect" or any(node.get(name) not in (None, "", "0", "auto") for name in ("rx", "ry")):
        return None
    x, y = svg.point(node.get("x"), node.get("y"), font_size)
    width, height = svg.point(node.get("width"), node.get("height"), font_size)
    stroke = node.get("stroke")
    if stroke not in (None, "", "none"):
        same_paint = stroke == node.get("fill") and node.get("stroke-opacity", "1") == node.get("fill-opacity", "1")
        if not same_paint or node.get("stroke-linejoin", "miter") != "miter" or node.get("stroke-dasharray") not in (None, "none"):
            return None
        half = svg.length(node.get("stroke-width", "1"), font_size) / 2
        x, y, width, height = x - half, y - half, width + 2 * half, height + 2 * half
    return (x, y, width, height) if width > 0 and height > 0 else None


def _profile(start: float, end: float, sigma: float, low: float, high: float) -> list[tuple[float, float]]:
    """The blurred coverage of [start, end] along one axis, sampled over [low, high]: Phi((t - start) / s) - Phi((t - end) / s)."""
    points = [low + (high - low) * k / (EDGE_SAMPLES - 1) for k in range(EDGE_SAMPLES)]
    return [(t, _GAUSS.cdf((t - start) / sigma) - _GAUSS.cdf((t - end) / sigma)) for t in points]


def _profile_shading(stream: Any, samples: list[tuple[float, float]], vertical: bool) -> Any:
    """An axial shading in gray along x or y through the samples."""
    (low, _), (high, _) = samples[0], samples[-1]
    pieces = [stream.create_interpolation_function((0, 1), [a], [b], 1) for (_, a), (_, b) in zip(samples, samples[1:], strict=False)]
    function = stream.create_stitching_function((low, high), [0, 1] * len(pieces), [t for t, _ in samples[1:-1]], pieces)
    coords = (0, low, 0, high) if vertical else (low, 0, high, 0)
    return stream.add_shading(2, (low, high), coords, False, function, "DeviceGray")


def _axis_group(stream: Any, start: float, end: float, sigma: float, vertical: bool, box: Region) -> Any:
    """A group over box in gray: the coverage of [start, end] along one axis, constant along the other.

    Each blurred edge is a shading of its own over 4 deviations to each side: PDFium samples a shading
    in 256 steps, which over a whole wide rect would move its edges by whole units.
    """
    group = stream.add_group(*box)
    left, top, width, height = box
    group.set_color(_gray(0))
    group.rectangle(*box)
    group.fill()

    def strip(low: float, high: float) -> Region:
        return (left, low, width, high - low) if vertical else (low, top, high - low, height)

    reach = EDGE_REACH * sigma
    # Where the two edges are close, one shading covers both
    spans = [(start - reach, start + reach), (end - reach, end + reach)] if end - start > 2 * reach else [(start - reach, end + reach)]
    if len(spans) == 2:
        group.set_color(_gray(1))
        group.rectangle(*strip(start + reach, end - reach))
        group.fill()
    for low, high in spans if sigma else []:
        group.push_state()
        group.rectangle(*strip(low, high))
        group.clip()
        group.end()
        group.paint_shading(_profile_shading(group, _profile(start, end, sigma, low, high), vertical).id)
        group.pop_state()
    return group


def _rect_blur_mask(svg: Any, rect: Region, blur: tuple[float, float], box: Region) -> None:
    """Set the blurred rect as the soft mask of svg.stream, exactly: the product of two profiles.

    The blur of a rectangle is separable: its coverage is the profile along x times the profile along y.
    The group of the second axis multiplies the first in a luminosity group. Corners come out round and a
    deviation along one axis only leaves the other edges sharp, as in Chromium.
    """
    x, y, width, height = rect
    mask = svg.stream.set_alpha_state(*box, mode="luminosity")
    mask.draw_x_object(_axis_group(mask, x, x + width, blur[0], False, box).id)
    mask.set_blend_mode("Multiply")
    mask.draw_x_object(_axis_group(mask, y, y + height, blur[1], True, box).id)


def _blurred_mask(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, layer: Layer, sigma: float, box: Region) -> None:
    """The blur mask of node: exact for a plain rect, the levels of _blur_mask for anything else."""
    rect = _plain_rect(svg, node, font_size)
    if rect is not None:
        _rect_blur_mask(svg, rect, layer.blur, box)
    else:
        _blur_mask(svg, original, node, font_size, context, sigma, box)


def _draw_silhouette(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, layer: Layer, stream: Any, big: Region, sigma: float) -> None:
    """The element in one color, blurred when sigma is set."""
    if sigma:
        # The silhouette of the grown element, in one color, under the blurred edge
        _blurred_mask(svg, original, node, font_size, context, layer, sigma, big)
        group = stream.add_group(*big)
        mask = group.set_alpha_state(*big, mode="alpha")
        _draw_into(svg, original, node, font_size, context, mask, _widest(max(sigma, *layer.blur)))
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


def _draw_source(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, layer: Layer, stream: Any, big: Region, sigma: float) -> None:
    """The element in its own paint, faded, recolored or blurred."""
    # A blurred source keeps its colors and spreads them to the widest level of the mask
    grow = None
    if sigma:
        _blurred_mask(svg, original, node, font_size, context, layer, sigma, big)
        # The paint reaches as far as the wider deviation: the mask cuts it to the blur
        grow = _widest(max(sigma, *layer.blur))
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
        try:
            stop_opacity = alpha_value(stop.get("stop-opacity", 1))
        except ValueError:
            stop_opacity = 1.0  # Chromium reads an invalid stop-opacity as 1, as paint._visible_stops does
        parsed.append((offset, (red, green, blue, rgba.alpha * stop_opacity)))
    out = []
    for (start, first), (end, second) in zip(parsed, parsed[1:], strict=False):
        for i in range(GRADIENT_SAMPLES):
            t = i / GRADIENT_SAMPLES
            value = [a + (b - a) * t for a, b in zip(first, second, strict=True)]
            out.append(_stop(start + (end - start) * t, value))
    out.append(_stop(*parsed[-1]))
    return out


def _rgba(red: float, green: float, blue: float, alpha: float) -> str:
    return f"rgb({red * 100}% {green * 100}% {blue * 100}% / {alpha})"


def _stop(offset: float, value: Any) -> _Stop:
    # The opacity goes into the color: the recolor applies to both, as Chromium applies it to the pixel
    return _Stop({"offset": f"{offset}", "stop-color": _rgba(*(min(max(c, 0.0), 1.0) for c in value)), "stop-opacity": "1"})


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
    _core.add_restyler(restyle)
    _core.add_restyler(recolor_restyle)
    _core.enable_draw_feature("filters")
    _core.track_groups()
