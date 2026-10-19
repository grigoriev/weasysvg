"""Vector rendering of the common filter chains, and of CSS drop-shadow() and blur().

Touches: ``svg.SVG.draw_node`` through the shared wrapper of ``_core``. WeasyPrint only shifts the
element for feOffset and drops the rest, so shadows came out as the element itself, offset.

A chain is evaluated into layers: source (the element, offset or faded), alpha (its silhouette in one
color), lum (luminanceToAlpha) and flood (a rectangle). Supported: feOffset, feFlood, feDropShadow,
feMerge, feBlend normal, feComposite over and in, feComponentTransfer alpha slope, luminanceToAlpha.
PDF has no blur. A layer with a blur goes raster through resvg (raster.py), the other layers stay
vector. A chain with any other primitive goes raster as a whole. Without resvg, blur is dropped and
other chains draw the element unfiltered.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any, cast

from weasyprint import svg as wp_svg
from weasyprint.svg.bounding_box import is_valid_bounding_box
from weasyprint.svg.utils import alpha_value, color, parse_url, size

from . import _core, raster

Region = tuple[float, float, float, float]


class Unsupported(Exception):
    pass


@dataclass(frozen=True)
class Layer:
    kind: str  # source | alpha | lum | flood
    dx: float = 0
    dy: float = 0
    rgba: Any = None
    opacity: float = 1
    blur: tuple[float, float] = (0.0, 0.0)  # standard deviation along x and y
    region: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class Plan:
    layers: list[Layer]
    region: tuple[float, float, float, float] | None
    whole: bool = False  # the element goes raster as a whole, with its own filter
    filter_node: Any = None


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
        if layer.kind in ("source", "alpha", "lum"):
            out.append(replace(layer, kind="alpha", rgba=rgba, opacity=layer.opacity * opacity))
        elif layer.kind == "flood":
            out.append(replace(layer, rgba=rgba, opacity=layer.opacity * opacity))
    return out


@dataclass
class _Chain:
    """One filter chain while it is evaluated: its named results, the output of the last primitive and the input of the current one."""

    svg: Any
    filter_node: Any
    region: Region
    font_size: float
    results: dict[str, list[Layer]] = field(default_factory=dict)
    last: list[Layer] = field(default_factory=lambda: [Layer("source")])
    source: list[Layer] = field(default_factory=list)

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
    dx, dy = _num(child.get("dx")), _num(child.get("dy"))
    return [replace(layer, dx=layer.dx + dx, dy=layer.dy + dy) for layer in chain.source]


def _fe_gaussian_blur(chain: _Chain, child: Any) -> list[Layer]:
    std = _std(child.get("stdDeviation"), "0")
    return [replace(layer, blur=_add_blur(layer.blur, std)) for layer in chain.source]


def _fe_flood(chain: _Chain, child: Any) -> list[Layer]:
    rgba, opacity = _flood(child)
    sub = chain.region
    if any(child.get(key) is not None for key in ("x", "y", "width", "height")):
        svg, font_size = chain.svg, chain.font_size
        rx, ry, rw, rh = chain.region
        sub = (
            size(child.get("x", rx), font_size, svg.inner_width),
            size(child.get("y", ry), font_size, svg.inner_height),
            size(child.get("width", rw), font_size, svg.inner_width),
            size(child.get("height", rh), font_size, svg.inner_height),
        )
    return [Layer("flood", rgba=rgba, opacity=opacity, region=sub)]


def _fe_drop_shadow(chain: _Chain, child: Any) -> list[Layer]:
    rgba, opacity = _flood(child)
    dx, dy = _num(child.get("dx"), 2), _num(child.get("dy"), 2)
    std = _std(child.get("stdDeviation"), "2")
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


def _fe_component_transfer(chain: _Chain, child: Any) -> list[Layer]:
    funcs = list(child)
    if not all(f.tag == "feFuncA" and f.get("type") == "linear" and _num(f.get("intercept")) == 0 for f in funcs):
        raise Unsupported("feComponentTransfer")
    slope = _num(funcs[0].get("slope"), 1) if funcs else 1
    return [replace(layer, opacity=layer.opacity * slope) for layer in chain.source]


def _fe_color_matrix(chain: _Chain, child: Any) -> list[Layer]:
    kind = child.get("type", "matrix")
    # A soft mask computes luminance in sRGB: exact only when the filter works in sRGB too
    srgb = (child.get("color-interpolation-filters") or chain.filter_node.get("color-interpolation-filters") or "").lower() == "srgb"
    if kind == "luminanceToAlpha" and srgb and all(layer.kind == "source" for layer in chain.source):
        return [replace(layer, kind="lum") for layer in chain.source]
    if kind == "saturate" and _num(child.get("values"), 1) == 1:
        return chain.source
    raise Unsupported(f"feColorMatrix {kind}")


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


def _evaluate(svg: Any, filter_node: Any, region: tuple[float, float, float, float], font_size: float) -> list[Layer]:
    chain = _Chain(svg, filter_node, region, font_size)
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


def _region(svg: Any, node: Any, filter_node: Any, font_size: float) -> tuple[float, float, float, float]:
    region = _region_values(svg, node, filter_node, font_size)
    # width="1e999" sizes to inf: no clip and no raster can follow it, the element draws unfiltered
    if not all(math.isfinite(value) for value in region):
        raise Unsupported("infinite region")
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


def _function_plan(svg: Any, node: Any, value: str) -> Plan | None:
    """The plan of a CSS filter function list. The root keeps the behavior of WeasyPrint."""
    if node is svg.tree:
        return None
    try:
        return Plan(_function_layers(value), None)
    except Unsupported:
        return UNFILTERED  # an invalid function list: browsers draw the element unfiltered


def _reference_plan(svg: Any, node: Any, font_size: float, fragment: str) -> Plan | None:
    """The plan of a filter element: vector layers, or a whole raster when the chain needs one."""
    filter_node = svg.filters.get(fragment)
    if filter_node is None:
        return UNFILTERED
    try:
        region = _region(svg, node, filter_node, font_size)
    except Unsupported:
        return UNFILTERED
    if node is svg.tree:
        # The root draws its viewport inside draw_node: only a whole raster keeps it right
        return Plan([], region, whole=True, filter_node=filter_node) if raster.available() else None
    try:
        if filter_node.get("primitiveUnits") == "objectBoundingBox":
            raise Unsupported("primitiveUnits")
        return Plan(_evaluate(svg, filter_node, region, font_size), region, filter_node=filter_node)
    except Unsupported:
        if raster.available():
            return Plan([], region, whole=True, filter_node=filter_node)
        return UNFILTERED


def plan(svg: Any, node: Any, font_size: float) -> Plan | None:
    """The layers for the filter of node, or None when the node keeps the behavior of WeasyPrint."""
    value = node.get("filter")
    if not value or value == "none" or (node.tag == "svg" and node is not svg.tree):
        return None
    fragment = parse_url(value).fragment if value.startswith("url(") else None
    if not fragment:
        return _function_plan(svg, node, value)
    return _reference_plan(svg, node, font_size, fragment)


# ---------------- raster layers ----------------


def _rgb(rgba: Any, opacity: float) -> tuple[str, float]:
    r, g, b = (min(max(c, 0), 1) * 255 for c in rgba.to("srgb").coordinates)
    return f"rgb({r:.2f},{g:.2f},{b:.2f})", rgba.alpha * opacity


def _layer_filter(layer: Layer, region: tuple[float, float, float, float], filter_node: Any) -> str:
    """A filter that resvg renders for one blurred layer, offset and opacity included."""
    x, y, width, height = region
    interpolation = filter_node.get("color-interpolation-filters") if filter_node is not None else None
    attributes = f'id="{raster.FILTER_ID}" filterUnits="userSpaceOnUse" x="{x}" y="{y}" width="{width}" height="{height}"'
    if interpolation:
        attributes += f' color-interpolation-filters="{interpolation}"'
    blur = f'stdDeviation="{layer.blur[0]} {layer.blur[1]}"'
    offset = f'<feOffset in="blurred" dx="{layer.dx}" dy="{layer.dy}" result="moved"/>'
    if layer.kind == "source":
        body = f'<feGaussianBlur in="SourceGraphic" {blur} result="blurred"/>{offset}'
        if layer.opacity < 1:
            body += f'<feComponentTransfer in="moved"><feFuncA type="linear" slope="{layer.opacity}"/></feComponentTransfer>'
    else:
        if layer.kind == "lum":
            body = f'<feColorMatrix in="SourceGraphic" type="luminanceToAlpha" result="alpha"/><feGaussianBlur in="alpha" {blur} result="blurred"/>'
            color_value, opacity = "black", layer.opacity
        else:
            body = f'<feGaussianBlur in="SourceAlpha" {blur} result="blurred"/>'
            color_value, opacity = _rgb(layer.rgba, layer.opacity)
        body += f'{offset}<feFlood flood-color="{color_value}" flood-opacity="{opacity}"/><feComposite in2="moved" operator="in"/>'
    return f"<filter {attributes}>{body}</filter>"


def _blur_region(svg: Any, node: Any, font_size: float, layers: list[Layer]) -> tuple[float, float, float, float] | None:
    """The region of a CSS filter function: the box, grown by the blur and the offset."""
    box = svg.calculate_bounding_box(node, font_size, stroke=True)
    if not is_valid_bounding_box(box):
        return None
    x, y, width, height = box
    left = top = right = bottom = 0.0
    for layer in layers:
        left = max(left, 3 * layer.blur[0] - layer.dx)
        right = max(right, 3 * layer.blur[0] + layer.dx)
        top = max(top, 3 * layer.blur[1] - layer.dy)
        bottom = max(bottom, 3 * layer.blur[1] + layer.dy)
    return (x - left, y - top, width + left + right, height + top + bottom)


def _draw_layers(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, plan_: Plan, strip_mask: bool) -> None:
    layers, region = plan_.layers, plan_.region
    stream = svg.stream
    if region:
        stream.rectangle(*region)
        stream.clip()
        stream.end()
    big = region or (-1e4, -1e4, 2e4, 2e4)
    for layer in layers:
        if layer.blur != (0.0, 0.0) and layer.kind != "flood" and raster.available():
            layer_region = region or _blur_region(svg, node, font_size, [layer])
            if layer_region is not None:
                image = raster.render(svg, node, layer_region, f"url(#{raster.FILTER_ID})", _layer_filter(layer, layer_region, plan_.filter_node), strip_mask)
                if image is not None:
                    raster.draw(svg, image, layer_region)
                    continue
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
    if layer.kind == "flood":
        stream.set_color(_with_alpha(layer.rgba, layer.opacity))
        stream.rectangle(*cast(Region, layer.region))
        stream.fill()
    elif layer.kind in ("alpha", "lum"):
        svg.stream = stream.set_alpha_state(*big, mode="alpha" if layer.kind == "alpha" else "luminosity")
        original(svg, node, font_size, True, context)
        svg.stream = stream
        rgba = layer.rgba if layer.kind == "alpha" else color("black")
        stream.set_color(_with_alpha(rgba, layer.opacity))
        stream.rectangle(*big)
        stream.fill()
    elif layer.opacity < 1:
        group = stream.add_group(*big)
        svg.stream = group
        original(svg, node, font_size, True, context)
        svg.stream = stream
        stream.set_alpha(layer.opacity, stroke=True, fill=True)
        stream.draw_x_object(group.id)
    else:
        original(svg, node, font_size, True, context)


def _draw_whole(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, plan_: Plan, strip_mask: bool) -> None:
    """The element and its own filter, rendered by resvg; unfiltered when resvg fails."""
    filter_value = f"url(#{plan_.filter_node.get('id')})"
    image = raster.render(svg, node, cast(Region, plan_.region), filter_value, strip_mask=strip_mask)
    if image is None:
        original(svg, node, font_size, True, context)
    else:
        raster.draw(svg, image, cast(Region, plan_.region))


def draw(svg: Any, original: Callable[..., None], node: Any, font_size: float, context: Any, plan_: Plan, opacity_value: Any, strip_mask: bool = False) -> None:
    """Draw node through its plan. The caller already applied the transform and removed filter and opacity."""
    opacity = alpha_value(opacity_value)
    outer = svg.stream
    if opacity < 1:
        svg.stream = outer.add_group(-1e4, -1e4, 2e4, 2e4)
    root = svg.stream if node is svg.tree else None
    try:
        if root is not None:
            # The root draws its own viewport: x, y, viewBox and clip, before its content
            root.push_state()
            wp_svg.TAGS["svg"](svg, node, size(node.get("font-size", "1em"), font_size, font_size))
        if plan_.whole:
            _draw_whole(svg, original, node, font_size, context, plan_, strip_mask)
        else:
            _draw_layers(svg, original, node, font_size, context, plan_, strip_mask)
    finally:
        if root is not None:
            svg.stream = root
            root.pop_state()
        if opacity < 1:
            group = svg.stream
            svg.stream = outer
            outer.set_alpha(opacity, stroke=True, fill=True)
            outer.draw_x_object(group.id)


def install() -> None:
    _core.enable_draw_feature("filters")
