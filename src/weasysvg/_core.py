"""The two hooks that several features share, each installed once.

- ``images.SVGImage.__init__``: runs the tree passes on the parsed XML, then wraps the URL fetcher.
- ``svg.SVG.draw_node``: one replacement that combines blend mode, early mask and complex clip
  (paint.py) with vector filters (filters.py), in the compositing order of CSS: filter, then clip and
  mask, then blend. It also draws the opacity group, unbounded: the bounding box of WeasyPrint clips
  shifted text. Before a node draws, each restyler may change its attributes for the duration. A
  clip-path that leads back into a clip path being drawn is ignored, as in Chromium: WeasyPrint
  recursed until the stack ran out, and the whole SVG was lost.
"""

from __future__ import annotations

import importlib
import math
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree as ET

from weasyprint import images as wp_images
from weasyprint import svg as wp_svg
from weasyprint.pdf import stream as wp_stream
from weasyprint.svg.bounding_box import is_valid_bounding_box
from weasyprint.svg.utils import alpha_value, parse_url, size

# The module: weasyprint.svg exports a function of the same name, which hides it from attribute access
wp_bounding_box = importlib.import_module("weasyprint.svg.bounding_box")

TreePass = Callable[[ET.Element], None]
FetcherWrapper = Callable[[object], object]
# Returns the attributes to put back after the node draws, or None when it leaves the node alone
Restyler = Callable[[Any, Any, float], "dict[str, str | None] | None"]

# Tree passes run in the order of their rank: conditional (10), paint (20), foreign_object (30)
_TREE_PASSES: list[tuple[int, str, TreePass]] = []
_FETCHER_WRAPPERS: list[FetcherWrapper] = []
_RESTYLERS: list[Restyler] = []
# Called with the SVG and the node once the node and its children are drawn
AfterDraw = Callable[[Any, Any], None]
_AFTER_DRAW: list[AfterDraw] = []
# Called with the SVG and the node before the node draws
_BEFORE_DRAW: list[AfterDraw] = []
# The clip paths being drawn, per thread and task
_ACTIVE_CLIPS: ContextVar[tuple[Any, ...]] = ContextVar("weasysvg_active_clips", default=())
DRAW_FEATURES = {"filters": False, "masks": False, "blend": False}
# The smallest box a group gets, in user units
MIN_GROUP_EXTENT = 1e4

_ORIGINAL_SVGIMAGE_INIT = wp_images.SVGImage.__init__
_ORIGINAL_DRAW_NODE = wp_svg.SVG.draw_node
_ORIGINAL_ADD_GROUP = wp_stream.Stream.add_group
_ORIGINAL_ADD_PATTERN = wp_stream.Stream.add_pattern


def original_draw_node() -> Callable[..., None]:
    """The draw_node of WeasyPrint itself, before any patch of this package."""
    function: Callable[..., None] = _ORIGINAL_DRAW_NODE
    return function


def add_tree_pass(rank: int, name: str, function: TreePass) -> None:
    if any(existing == name for _, existing, _ in _TREE_PASSES):
        return
    _TREE_PASSES.append((rank, name, function))
    _TREE_PASSES.sort(key=lambda entry: entry[0])
    _install_svgimage_hook()


def add_fetcher_wrapper(function: FetcherWrapper) -> None:
    if function not in _FETCHER_WRAPPERS:
        _FETCHER_WRAPPERS.append(function)
    _install_svgimage_hook()


def _svgimage_init(self: Any, tree: Any, base_url: Any, url_fetcher: Any, context: Any) -> None:
    for _, _, function in _TREE_PASSES:
        function(tree)
    if url_fetcher is not None:
        for wrap in _FETCHER_WRAPPERS:
            url_fetcher = wrap(url_fetcher)
    _ORIGINAL_SVGIMAGE_INIT(self, tree, base_url, url_fetcher, context)


def _install_svgimage_hook() -> None:
    if wp_images.SVGImage.__init__ is not _svgimage_init:
        wp_images.SVGImage.__init__ = _svgimage_init


def add_after_draw(function: AfterDraw) -> None:
    if function not in _AFTER_DRAW:
        _AFTER_DRAW.append(function)


def add_before_draw(function: AfterDraw) -> None:
    if function not in _BEFORE_DRAW:
        _BEFORE_DRAW.append(function)


def add_restyler(function: Restyler) -> None:
    if function not in _RESTYLERS:
        _RESTYLERS.append(function)


def restyle(svg: Any, node: Any, font_size: float, saved: list[dict[str, str | None]]) -> None:
    """Run every restyler on node, adding what to put back to saved as each one finishes."""
    for function in _RESTYLERS:
        changed = function(svg, node, font_size)
        if changed is not None:
            saved.append(changed)


def unrestyle(node: Any, saved: list[dict[str, str | None]]) -> None:
    """Put back what the restylers changed, the last first."""
    for changed in reversed(saved):
        for key, value in changed.items():
            if value is None:
                node.attrib.pop(key, None)
            else:
                node.attrib[key] = value


def enable_draw_feature(name: str) -> None:
    DRAW_FEATURES[name] = True
    if wp_svg.SVG.draw_node is not _draw_node:
        wp_svg.SVG.draw_node = _draw_node
    wp_bounding_box.BOUNDING_BOX_METHODS.setdefault("a", bounding_box_a)


def bounding_box_a(svg: Any, node: Any, font_size: float) -> Any:
    """The box of an <a>, which WeasyPrint leaves empty: its own text and its children, as for a <g>."""
    text, children = getattr(node, "text_bounding_box", None), wp_bounding_box.bounding_box_g(svg, node, font_size)
    if not is_valid_bounding_box(text):
        return children
    if not is_valid_bounding_box(children):
        return text
    x, y, width, height = children
    return wp_bounding_box.extend_bounding_box(text, ((x, y), (x + width, y + height)))


def _group_opacity(node: Any) -> float | None:
    """The opacity this wrapper groups itself, or None where WeasyPrint draws no opacity group."""
    opacity: float = alpha_value(node.get("opacity", 1))
    return opacity if 0 <= opacity < 1 else None


@dataclass(frozen=True)
class _Effects:
    """What this wrapper applies itself around the original draw_node; None where it applies nothing."""

    font_size: float  # the font size of the node, for its transform, mask and filter
    blend: str | None
    mask: Any
    clip: Any
    plan: Any
    opacity: float | None

    def without_blend(self) -> _Effects:
        return _Effects(self.font_size, None, self.mask, self.clip, self.plan, self.opacity)

    def empty(self) -> bool:
        return self.blend is None and self.mask is None and self.clip is None and self.plan is None and self.opacity is None

    def applied_keys(self) -> list[str]:
        """What this wrapper applies itself leaves the node, so the original does not apply it twice."""
        keys = ["transform"]
        if self.mask is not None:
            keys.append("mask")
        if self.clip is not None:
            keys.append("clip-path")
        if self.plan is not None:
            keys += ["filter", "opacity"]
        if self.opacity is not None:
            keys.append("opacity")
        return keys


def _effects(svg: Any, node: Any, font_size: float) -> _Effects:
    # Imported here: paint and filters import this module
    from . import filters, paint

    blend = paint.blend_mode(node) if DRAW_FEATURES["blend"] else None
    mask = paint.early_mask(svg, node) if DRAW_FEATURES["masks"] else None
    clip = paint.complex_clip(svg, node) if DRAW_FEATURES["masks"] else None
    local_font_size = size(node.get("font-size", "1em"), font_size, font_size)
    plan = filters.plan(svg, node, local_font_size) if DRAW_FEATURES["filters"] else None
    opacity = _group_opacity(node) if plan is None else None
    return _Effects(local_font_size, blend, mask, clip, plan, opacity)


def _clip_of(svg: Any, node: Any) -> Any:
    value = node.get("clip-path")
    if not value or not value.strip().startswith("url("):
        return None
    return svg.paths.get(parse_url(value).fragment)


def _is_clip_path(svg: Any, node: Any) -> bool:
    """Whether node is the content of a clip path being drawn: WeasyPrint and paint.py tag it <g> then."""
    identifier = node.get("id")
    return bool(identifier) and svg.paths.get(identifier) is node


def _draw_node(self: Any, node: Any, font_size: float, fill_stroke: bool = True, context: Any = None) -> None:
    # A clip path counts as active while its own content draws: a reference back to it from there
    # closes a cycle. A child that reuses the clip of its parent closes none.
    active = (*_ACTIVE_CLIPS.get(), node) if _is_clip_path(self, node) else _ACTIVE_CLIPS.get()
    token = _ACTIVE_CLIPS.set(active)
    saved_clip = None
    restyled: list[dict[str, str | None]] = []
    try:
        clip = _clip_of(self, node)
        if clip is not None and any(clip is item for item in active):
            saved_clip = node.attrib.pop("clip-path")
        # A blur mask being built draws its shapes grown, a clip mask draws them filled
        if fill_stroke:
            restyle(self, node, font_size, restyled)
        for function in _BEFORE_DRAW:
            function(self, node)
        _draw_with_effects(self, node, font_size, fill_stroke, context)
        for function in _AFTER_DRAW:
            function(self, node)
    finally:
        unrestyle(node, restyled)
        _ACTIVE_CLIPS.reset(token)
        if saved_clip is not None:
            node.attrib["clip-path"] = saved_clip


def _draw_with_effects(self: Any, node: Any, font_size: float, fill_stroke: bool, context: Any) -> None:
    original: Callable[..., None] = _ORIGINAL_DRAW_NODE
    if not fill_stroke or node.tag == "defs":
        return original(self, node, font_size, fill_stroke, context)
    if any(node.attrib.get(key) not in (None, "", "none") for key in BOX_EFFECTS):
        measure_text(self, node, font_size)
    effects = _effects(self, node, font_size)
    if effects.empty():
        return original(self, node, font_size, fill_stroke, context)

    from . import paint

    saved = {key: node.attrib.pop(key) for key in effects.applied_keys() if key in node.attrib}
    self.stream.push_state()
    try:
        if "transform" in saved:
            node.attrib["transform"] = saved["transform"]
            self.transform(node, effects.font_size)
            del node.attrib["transform"]
        if effects.mask is not None:
            paint.paint_mask(self, node, effects.mask, effects.font_size)
        if effects.clip is None:
            _draw_grouped(self, original, node, font_size, fill_stroke, context, effects, saved.get("opacity", 1))
        else:
            _draw_clipped(self, original, node, font_size, fill_stroke, context, effects, saved.get("opacity", 1))
    finally:
        self.stream.pop_state()
        node.attrib.update(saved)


# The effects whose region or units follow the bounding box of the element
BOX_EFFECTS = ("filter", "mask", "clip-path")
TEXT_TAGS = frozenset(("text", "tspan", "textPath"))
# The nodes being measured: a restyler may set an effect again while one draws, which must not measure it twice
_MEASURING: ContextVar[tuple[Any, ...]] = ContextVar("weasysvg_measuring", default=())


def _unmeasured_text(node: Any) -> bool:
    """Whether node is or holds a text whose box WeasyPrint does not know yet: another shape may give a box."""
    # WeasyPrint draws an <a> as text: in a <text> it holds text of its own, around shapes it holds none
    if node.tag in TEXT_TAGS or (node.tag == "a" and (node.text or "").strip()):
        return not is_valid_bounding_box(getattr(node, "text_bounding_box", None))
    return any(_unmeasured_text(child) for child in node)


def measure_text(svg: Any, node: Any, font_size: float) -> None:
    """Draw node once into a scratch group, without its effects, when its box needs text.

    WeasyPrint knows the box of a text only once the text is drawn, but a filter region, a mask or a clip in
    objectBoundingBox units needs the box before. The scratch group is dropped from the resources: only
    the boxes it left on the nodes remain.
    """
    measuring = _MEASURING.get()
    if any(node is item for item in measuring) or not _unmeasured_text(node):
        return
    outer = svg.stream
    scratch = outer.add_group(0, 0, 0, 0)
    saved = {key: node.attrib.pop(key) for key in (*BOX_EFFECTS, "opacity", "mix-blend-mode") if key in node.attrib}
    from . import text, textpath

    # Text moves the current text position, the position along a <textPath> and the last text chunk:
    # the real drawing starts where the scratch one did
    cursor, shift = svg.cursor_position, list(svg.cursor_d_position)
    chunk = text.LAST_CHUNK.set(text.LAST_CHUNK.get())
    path = textpath.CURRENT.get()
    along = (path, path.distance, path.shift) if path is not None else None
    token = _MEASURING.set((*measuring, node))
    try:
        svg.stream = scratch
        svg.draw_node(node, font_size)
    finally:
        svg.stream = outer
        svg.cursor_position, svg.cursor_d_position = cursor, shift
        text.LAST_CHUNK.reset(chunk)
        if along is not None:
            along[0].distance, along[0].shift = along[1:]
        _MEASURING.reset(token)
        # A box cached before the text was measured lacks it
        node.bounding_box = None
        node.attrib.update(saved)
        outer._resources["XObject"].pop(scratch.id, None)


def _draw_clipped(self: Any, original: Callable[..., None], node: Any, font_size: float, fill_stroke: bool, context: Any, effects: _Effects, filter_opacity: Any) -> None:
    """The node in a group whose soft mask is its clip: the mask of the node keeps the graphics state."""
    from . import paint

    outer = self.stream
    box = group_box(self, node, font_size)
    group = outer.add_group(*box)
    # The content draws in a group of its own: a filter or gradient inside sets a soft mask, which would
    # replace the clip in the graphics state
    content = group.add_group(*box)
    self.stream = group
    try:
        paint.paint_clip(self, node, effects.clip, effects.font_size)
        self.stream = content
        # The clipped group blends with what lies under it: inside it there is nothing to blend with
        _draw_grouped(self, original, node, font_size, fill_stroke, context, effects.without_blend(), filter_opacity)
    finally:
        self.stream = outer
        group.draw_x_object(content.id)
        if effects.blend is not None:
            outer.set_blend_mode(effects.blend)
        outer.draw_x_object(group.id)


# WeasyPrint draws a page in pt: one CSS px is 0.75 pt
PX_PER_PT = 4 / 3


def _add_group(self: Any, *args: Any, **kwargs: Any) -> Any:
    group = _ORIGINAL_ADD_GROUP(self, *args, **kwargs)
    # A group starts with an identity matrix: it keeps the absolute matrix of its parent
    group.weasysvg_base = absolute_matrix(self)
    return group


def _add_pattern(self: Any, x: float, y: float, width: float, height: float, repeat_width: float, repeat_height: float, matrix: Any) -> Any:
    pattern = _ORIGINAL_ADD_PATTERN(self, x, y, width, height, repeat_width, repeat_height, matrix)
    # The pattern matrix maps the tile to the default space of the stream that paints with it
    base = getattr(self, "weasysvg_base", None)
    pattern.weasysvg_base = matrix @ base if base is not None else matrix
    return pattern


def absolute_matrix(stream: Any) -> Any:
    """The matrix from the user space of stream to the page, through the groups and patterns it lies in."""
    base = getattr(stream, "weasysvg_base", None)
    return stream.ctm @ base if base is not None else stream.ctm


def track_groups() -> None:
    if wp_stream.Stream.add_group is not _add_group:
        wp_stream.Stream.add_group = _add_group
    if wp_stream.Stream.add_pattern is not _add_pattern:
        wp_stream.Stream.add_pattern = _add_pattern


def text_scale(svg: Any) -> float:
    """The factor Chromium scales SVG text by, in CSS px per user unit: the mean square of the two axes.

    Chromium lays out SVG text at the font size times this factor (CalculateScreenFontSizeScalingFactor).
    """
    try:
        (a, b, _), (c, d, _), _ = absolute_matrix(svg.stream)
        return math.sqrt((a * a + b * b + c * c + d * d) / 2) * PX_PER_PT or 1.0
    except (AttributeError, TypeError, ValueError):
        return 1.0


def px_per_unit(svg: Any) -> float:
    """How many CSS px one user unit spans, through every transform and group."""
    try:
        return math.sqrt(abs(absolute_matrix(svg.stream).determinant)) * PX_PER_PT or 1.0
    except (AttributeError, TypeError):
        return 1.0


def group_box(svg: Any, node: Any, font_size: float) -> tuple[float, float, float, float]:
    """The box of an opacity, blend or filter group: it must contain the content, it must not clip it.

    It spans the root viewport and the element, each with a margin of its own size, and at least
    MIN_GROUP_EXTENT around the origin: map and CAD exports draw far from the origin. A plain huge box
    would do the same, but PDF/A-1 limits real numbers to 32767.
    """
    x0, y0, x1, y1 = -MIN_GROUP_EXTENT, -MIN_GROUP_EXTENT, MIN_GROUP_EXTENT, MIN_GROUP_EXTENT
    boxes = [svg.tree.get_viewbox(), svg.calculate_bounding_box(node, font_size, stroke=True)]
    for box in boxes:
        if not box or len(box) != 4 or not all(math.isfinite(value) for value in box):
            continue
        bx, by, bw, bh = box
        margin = max(abs(bw), abs(bh))
        x0, y0 = min(x0, bx - margin), min(y0, by - margin)
        x1, y1 = max(x1, bx + bw + margin), max(y1, by + bh + margin)
    return x0, y0, x1 - x0, y1 - y0


def _draw_grouped(self: Any, original: Callable[..., None], node: Any, font_size: float, fill_stroke: bool, context: Any, effects: _Effects, filter_opacity: Any) -> None:
    """The node inside its blend group and its opacity group, through its filter plan if it has one."""
    from . import filters

    outer = self.stream
    if effects.blend is not None:
        # The element blends as one isolated group: its own parts must not blend with each other
        self.stream = outer.add_group(*group_box(self, node, font_size))
    blended = self.stream
    if effects.opacity is not None:
        # WeasyPrint bounds its opacity group by the bounding box of the element, which misses the shift
        # of text-anchor, markers and wide strokes: the Mermaid gantt dates lost their first half
        self.stream = blended.add_group(*group_box(self, node, font_size))
    try:
        if effects.plan is not None:
            filters.draw(self, original, node, font_size, context, effects.plan, filter_opacity)
        else:
            original(self, node, font_size, fill_stroke, context)
    finally:
        if effects.opacity is not None:
            group, self.stream = self.stream, blended
            blended.push_state()
            blended.set_alpha(effects.opacity, stroke=True, fill=True)
            blended.draw_x_object(group.id)
            blended.pop_state()
        if effects.blend is not None:
            group, self.stream = self.stream, outer
            outer.set_blend_mode(effects.blend)
            outer.draw_x_object(group.id)
