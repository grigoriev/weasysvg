"""SVG text.

Touches:
- ``svg.TAGS`` text entries and the global ``svg.text``, with one replacement ``draw_text``:
  font family resolved as Chromium does (fonts.py), dominant-baseline from real font metrics,
  text-decoration from the font. ``draw_node`` recognizes text nodes by that global, so both change together.
- ``svg.Node.cascade``: font-size keywords. ``size()`` knows none, so "initial" or "medium" gave 0.
  The cascade rewrites the attribute once, so every reader of font-size sees a length.
- a tree pass: a <text> inside a <text> is not rendered, as in browsers.
"""

from __future__ import annotations

import sys
from typing import Any
from xml.etree import ElementTree as ET

from weasyprint import svg as wp_svg
from weasyprint.css.properties import INITIAL_VALUES
from weasyprint.svg.bounding_box import is_valid_bounding_box
from weasyprint.svg.utils import normalize
from weasyprint.text.ffi import FROM_UNITS, ffi, pango
from weasyprint.text.line_break import Layout

from . import _core
from .conditional import local_name
from .fonts import resolve_families

TEXT_TAGS = ("a", "text", "textPath", "tspan")
# font-size keywords, as CSS defines them (medium = 16px)
FONT_SIZE_KEYWORDS = {
    "xx-small": "9px",
    "x-small": "10px",
    "small": "13px",
    "medium": "16px",
    "large": "18px",
    "x-large": "24px",
    "xx-large": "32px",
    "xxx-large": "48px",
    "initial": "16px",
    "larger": "1.2em",
    "smaller": "0.8333em",
}
SHIFTED = frozenset(("central", "middle", "hanging", "text-before-edge", "text-after-edge", "ideographic", "mathematical"))
DECORATION_LINES = ("underline", "overline", "line-through")
FEATURES = {"fonts": True, "baseline": True, "decoration": True}

_ORIGINAL_CASCADE = wp_svg.Node.cascade
_ORIGINAL_TEXT = wp_svg.TAGS["text"]


# ---------------- font-size keywords ----------------


def cascade(self: Any, child: Any) -> None:
    _ORIGINAL_CASCADE(self, child)
    value = child.attrib.get("font-size")
    if value is None:
        return
    keyword = value.strip().lower()
    if keyword in ("unset", "revert", "revert-layer"):
        parent = self.attrib.get("font-size") if self is not child else None
        if parent is None:
            del child.attrib["font-size"]
        else:
            child.attrib["font-size"] = parent
    elif keyword in FONT_SIZE_KEYWORDS:
        child.attrib["font-size"] = FONT_SIZE_KEYWORDS[keyword]


# ---------------- nested text ----------------


def drop_nested_text(root: ET.Element) -> None:
    """A <text> inside a <text> is not rendered."""
    for outer in [element for element in root.iter() if local_name(element.tag) == "text"]:
        for parent in list(outer.iter()):
            for child in list(parent):
                if local_name(child.tag) == "text":
                    parent.remove(child)


# ---------------- font metrics ----------------


def _style(svg: Any, node: Any, font_size: float) -> Any:
    """The same dummy style text() builds."""
    style = sys.modules["weasyprint.svg.text"].Style()
    style.update(INITIAL_VALUES)
    style.font_config = svg.font_config
    style["font_family"] = [font.strip("\"'") for font in node.get("font-family", "sans-serif").split(",")]
    style["font_style"] = node.get("font-style", "normal")
    weight = node.get("font-weight", 400)
    weight = {"normal": 400, "bold": 700}.get(weight, weight)
    try:
        style["font_weight"] = int(weight)
    except ValueError:
        style["font_weight"] = 400
    style["font_size"] = font_size
    return style


def _metrics(svg: Any, node: Any, font_size: float) -> tuple[float, float, float]:
    """Ascent, descent and x-height of the font Pango picks for the text."""
    layout = Layout(_style(svg, node, font_size))
    layout.set_text("x")
    line, _ = layout.get_first_line()
    ink = ffi.new("PangoRectangle *")
    logical = ffi.new("PangoRectangle *")
    pango.pango_layout_line_get_extents(line, ink, logical)
    ascent: float = -logical.y * FROM_UNITS
    descent: float = (logical.height + logical.y) * FROM_UNITS
    x_height: float = -ink.y * FROM_UNITS
    layout.deactivate()
    return ascent, descent, x_height


def baseline_shift(value: str, ascent: float, descent: float, x_height: float) -> float:
    """Shifts measured in Chromium. Everything else, text-top and text-bottom included, is alphabetic."""
    return {
        "central": (ascent - descent) / 2,
        "middle": x_height / 2,
        "hanging": 0.8 * ascent,
        "text-before-edge": ascent,
        "text-after-edge": -descent,
        "ideographic": -descent,
        "mathematical": ascent / 2,
    }.get(value, 0)


# ---------------- text-decoration ----------------


def _decorate(svg: Any, node: Any, font_size: float) -> None:
    """Draw the lines over the run text() just laid out, with the position and thickness of the font.

    Limits: one line per node, and the paint of the node itself, not of the element that declares it.
    """
    lines = [line for line in DECORATION_LINES if line in (node.get("text-decoration") or "").split()]
    if not lines or not node.text or not node.text.strip() or not is_valid_bounding_box(node.text_bounding_box):
        return
    if len(normalize(node.get("y", "")).split()) > 1 or len(normalize(node.get("dy", "")).split()) > 1:
        return
    style = _style(svg, node, font_size)
    style["text_decoration_line"] = set(lines)
    layout = Layout(style)
    layout.set_text(node.text)
    ascent = pango.pango_layout_get_baseline(layout.layout) * FROM_UNITS
    x, y, width, _ = node.text_bounding_box
    baseline = y + ascent
    rects = []
    if "underline" in lines:
        rects.append((baseline - layout.underline_position, layout.underline_thickness))
    if "overline" in lines:
        rects.append((baseline - layout.ascent, layout.underline_thickness))
    if "line-through" in lines:
        rects.append((baseline - layout.strikethrough_position, layout.strikethrough_thickness))
    layout.deactivate()
    svg.stream.push_state()
    fill, stroke = svg.set_graphical_state(node, font_size)
    for top, thickness in rects:
        svg.stream.rectangle(x, top, width, thickness)
    svg.fill_stroke(fill, stroke)
    svg.stream.pop_state()


# ---------------- the text() replacement ----------------


def _draw_decorated(svg: Any, node: Any, font_size: float) -> Any:
    result = _ORIGINAL_TEXT(svg, node, font_size)
    if FEATURES["decoration"]:
        _decorate(svg, node, font_size)
    return result


def draw_text(svg: Any, node: Any, font_size: float) -> Any:
    if FEATURES["fonts"]:
        node.attrib["font-family"] = resolve_families(node.get("font-family") or "", svg.font_config)
    if not FEATURES["baseline"] or node.get("display-anchor"):
        return _draw_decorated(svg, node, font_size)
    # text() knows a fixed ascent of 0.8em only: hide the attribute, shift around the call instead
    value = node.get("alignment-baseline") if node.tag == "tspan" and node.get("alignment-baseline") else node.get("dominant-baseline")
    saved = {key: node.attrib.pop(key) for key in ("dominant-baseline", "alignment-baseline") if key in node.attrib}
    try:
        if value not in SHIFTED or not node.text:
            return _draw_decorated(svg, node, font_size)
        shift = baseline_shift(value, *_metrics(svg, node, font_size))
        svg.stream.push_state()
        svg.stream.transform(f=shift)
        try:
            return _draw_decorated(svg, node, font_size)
        finally:
            svg.stream.pop_state()
    finally:
        node.attrib.update(saved)


def install(*, fonts: bool = True, baseline: bool = True, decoration: bool = True) -> None:
    FEATURES.update(fonts=fonts, baseline=baseline, decoration=decoration)
    wp_svg.Node.cascade = cascade
    _core.add_tree_pass(15, "nested_text", drop_nested_text)
    for tag in TEXT_TAGS:
        if wp_svg.TAGS.get(tag) is _ORIGINAL_TEXT:
            wp_svg.TAGS[tag] = draw_text
    wp_svg.text = draw_text
