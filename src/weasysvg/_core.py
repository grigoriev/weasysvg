"""The two hooks that several features share, each installed once.

- ``images.SVGImage.__init__``: runs the tree passes on the parsed XML, then wraps the URL fetcher.
- ``svg.SVG.draw_node``: one replacement that combines blend mode and early mask (paint.py)
  with vector filters (filters.py), in the compositing order of CSS: filter, then mask, then blend.
  It also draws the opacity group, unbounded: the bounding box of WeasyPrint clips shifted text.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from xml.etree import ElementTree as ET

from weasyprint import images as wp_images
from weasyprint import svg as wp_svg
from weasyprint.svg.utils import alpha_value, size

TreePass = Callable[[ET.Element], None]
FetcherWrapper = Callable[[object], object]

# Tree passes run in the order of their rank: conditional (10), paint (20), foreign_object (30)
_TREE_PASSES: list[tuple[int, str, TreePass]] = []
_FETCHER_WRAPPERS: list[FetcherWrapper] = []
DRAW_FEATURES = {"filters": False, "masks": False, "blend": False}
# The smallest box a group gets, in user units
MIN_GROUP_EXTENT = 1e4

_ORIGINAL_SVGIMAGE_INIT = wp_images.SVGImage.__init__
_ORIGINAL_DRAW_NODE = wp_svg.SVG.draw_node


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


def enable_draw_feature(name: str) -> None:
    DRAW_FEATURES[name] = True
    if wp_svg.SVG.draw_node is not _draw_node:
        wp_svg.SVG.draw_node = _draw_node


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
    plan: Any
    opacity: float | None

    def empty(self) -> bool:
        return self.blend is None and self.mask is None and self.plan is None and self.opacity is None

    def applied_keys(self) -> list[str]:
        """What this wrapper applies itself leaves the node, so the original does not apply it twice."""
        keys = ["transform"]
        if self.mask is not None:
            keys.append("mask")
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
    local_font_size = size(node.get("font-size", "1em"), font_size, font_size)
    plan = filters.plan(svg, node, local_font_size) if DRAW_FEATURES["filters"] else None
    opacity = _group_opacity(node) if plan is None else None
    return _Effects(local_font_size, blend, mask, plan, opacity)


def _draw_node(self: Any, node: Any, font_size: float, fill_stroke: bool = True, context: Any = None) -> None:
    original: Callable[..., None] = _ORIGINAL_DRAW_NODE
    if not fill_stroke or node.tag == "defs":
        return original(self, node, font_size, fill_stroke, context)
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
        _draw_grouped(self, original, node, font_size, fill_stroke, context, effects, saved.get("opacity", 1))
    finally:
        self.stream.pop_state()
        node.attrib.update(saved)


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
            filters.draw(self, original, node, font_size, context, effects.plan, filter_opacity, strip_mask=effects.mask is not None)
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
