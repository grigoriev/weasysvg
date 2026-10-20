"""Paint servers, masks and blending.

Touches:
- ``svg.defs.draw_gradient``: a gradient cell of about 1000 units, since Splash and Quartz drop a 1 x 1
  cell, that covers the box under any gradientTransform; r and fr percentages of a radial gradient
  refer to the normalized diagonal; colors interpolate unpremultiplied, as Chromium does for SVG.
- ``svg.SVG.set_graphical_state``: a gradient or pattern stroke gets its stroke-width, not 1.
- ``svg.defs.draw_pattern``: the tile origin in pattern space, x and y included; attributes and tag are
  restored after each use.
- ``svg.defs.paint_mask``: replaced. Region of an objectBoundingBox mask, maskContentUnits, a cycle
  through mask="..." is broken, mask="..." on the <mask> itself is ignored as in Chromium, and the tag
  of the <mask> is restored, else the walk draws it as a <g>.
- a complex clip path, through ``_core``: one whose children carry clip-path, clip-rule="evenodd",
  text or <use>. One W clip cannot express it: it becomes an alpha soft mask, each child filled by its
  clip-rule. WeasyPrint dropped such children, ignored clip-rule and painted clip text in black.
- ``svg.Node.override_iter``: a list instead of a one-shot iterator, so a node can be walked twice.
- ``svg.SVG.draw_node``, through ``_core``: mix-blend-mode as an isolated group, and a mask on a container
  is set before its children are drawn. ``svg.NOT_INHERITED_ATTRIBUTES`` gains mix-blend-mode.
- a tree pass: an empty presentation attribute (fill="") is ignored, as browsers do.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any
from xml.etree import ElementTree as ET

from weasyprint import svg as wp_svg
from weasyprint.matrix import Matrix
from weasyprint.svg import defs as wp_defs
from weasyprint.svg import utils as wp_utils

from . import _core

GRADIENT_CELL = 1000  # pattern units for the longest side of a gradient cell
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
    """The cell of a transformed gradient: the box of all four corners, mapped back by gradientTransform.

    WeasyPrint maps two corners only: rotated by 45 degrees, its cell is a sliver and the shape stays empty.
    """
    if "gradientTransform" not in gradient.attrib:
        return None
    box = svg.calculate_bounding_box(node, font_size, stroke)
    if not wp_defs.is_valid_bounding_box(box):
        return None
    x, y, width, height = box if gradient.get("gradientUnits") == "userSpaceOnUse" else (0, 0, 1, 1)
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


# A stop of opacity 0 gets this one instead: WeasyPrint gives a transparent stop the color of its
# neighbor, the premultiplied mix again, while Chromium keeps its own color
TRANSPARENT_STOP = "1e-9"


def _visible_stops(gradient: Any) -> list[tuple[Any, str]]:
    """Give each fully transparent stop a tiny opacity; return the stops and values to put back."""
    changed = []
    for stop in gradient:
        value = stop.get("stop-opacity")
        if value is not None and wp_utils.alpha_value(value) == 0:
            changed.append((stop, value))
            stop.attrib["stop-opacity"] = TRANSPARENT_STOP
    return changed


def draw_gradient(svg: Any, node: Any, gradient: Any, font_size: float, opacity: float, stroke: bool) -> Any:
    stream = svg.stream
    changed = _radial_percentages(gradient)
    stops = _visible_stops(gradient)
    try:
        cell = _gradient_cell(svg, node, gradient, font_size, stroke)
        with _add_pattern_override(stream, _scaled_add_pattern(stream, cell)):
            return _ORIGINAL_DRAW_GRADIENT(svg, node, gradient, font_size, opacity, stroke)
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
    return fill, stroke


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
    for child in clip:
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
    """Set clip as the alpha soft mask of the current state, with every child filled."""
    stream = svg.stream
    mask = stream.set_alpha_state(*_core.group_box(svg, node, font_size), mode="alpha")
    if clip.get("clipPathUnits") == "objectBoundingBox":
        box = svg.calculate_bounding_box(node, font_size, stroke=False)
        if not wp_defs.is_valid_bounding_box(box):
            return  # an empty mask: the node is clipped away, as in Chromium
        mask.transform(a=box[2], d=box[3], e=box[0], f=box[1])
    tag = clip._etree_node.tag
    token = _CLIPPING.set(True)
    styles = _plain_content()
    try:
        svg.stream = mask
        clip._etree_node.tag = "g"
        svg.draw_node(clip, font_size)
    finally:
        clip._etree_node.tag = tag
        svg.stream = stream
        _CLIPPING.reset(token)
        _restore_content(styles)


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


def install(*, blend: bool = True) -> None:
    _core.add_tree_pass(20, "empty_presentation", drop_empty_presentation)
    wp_defs.draw_gradient = wp_svg.draw_gradient = draw_gradient
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
