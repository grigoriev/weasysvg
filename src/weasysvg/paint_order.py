"""paint-order: the fill, the stroke and the markers of a shape or a text, in the order the property gives.

Touches:
- ``svg.SVG.fill_stroke``: when the order of a shape differs from fill, stroke, markers, or its stroke is
  translucent, the path it built is taken out of the stream and put back once per paint, each with its
  own paint operator (f, S), and ``svg.SVG.draw_markers`` draws the markers in between. That call
  empties ``node.vertices``, so the call of draw_node after it draws nothing. The decoration lines of a
  text take the same way.
- text: ``text.draw_text`` hands what it drew to ``split_text``. A text object drawn with fill and stroke
  (``2 Tr``) becomes two copies: stroke only (``1 Tr``) and fill only (``0 Tr``), in the order to paint.
- a tree pass: an invalid paint-order, attribute or declaration in ``style``, is dropped. The value of
  the parent then inherits, as in Chromium.

WeasyPrint ignores paint-order: B paints the fill and then the stroke, the markers come after. Chromium
(measured, 156) paints in the given order, the missing keywords after it in the default order: "stroke"
is stroke, fill, markers; "markers stroke" is markers, stroke, fill. A text paints its whole stroke
before its whole fill. The passes share one graphics state: dashes, line width, stroke and fill
opacity, gradient and pattern paints. Opacity, mask, filter, clip and blend wrap the node once, around
all passes, and no attribute changes, so every bounding box stays the same.
"""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

from weasyprint import svg as wp_svg
from weasyprint.svg.css import parse_declarations
from weasyprint.svg.utils import alpha_value, color, size

from . import _core
from .markers import MARKER_ATTRIBUTES

PROPERTY = "paint-order"
DEFAULT = ("fill", "stroke", "markers")
# Values that are valid whatever paint-order holds: WeasyPrint resolves inherit in its cascade
KEYWORDS = frozenset(("normal", "initial", "inherit"))
PATH_OPERATORS = frozenset((b"m", b"l", b"c", b"v", b"y", b"re", b"h"))
STATE_OPERATORS = frozenset((b"q", b"Q"))
FILL_AND_STROKE, STROKE_ONLY, FILL_ONLY = b"2 Tr", b"1 Tr", b"0 Tr"

_ORIGINAL_FILL_STROKE = wp_svg.SVG.fill_stroke
_ENABLED = {"text": False}


def parse(value: str | None) -> tuple[str, ...] | None:
    """The three paints in the order value gives them; None for an invalid value."""
    tokens = (value or "normal").lower().split()
    if tokens in (["normal"], ["initial"]):
        return DEFAULT
    if not tokens or len(set(tokens)) != len(tokens) or not set(tokens) <= set(DEFAULT):
        return None
    return (*tokens, *(name for name in DEFAULT if name not in tokens))


def order(node: Any) -> tuple[str, ...]:
    return parse(node.get(PROPERTY)) or DEFAULT


def _valid(value: str) -> bool:
    return value.strip().lower() in KEYWORDS or parse(value) is not None


def _valid_style(style: str) -> str | None:
    """The style without its invalid paint-order declarations, as WeasyPrint reads it; None when it has none."""
    normal, important = parse_declarations(style)
    kept = [(name, value, "") for name, value in normal] + [(name, value, " !important") for name, value in important]
    valid = [(name, value, flag) for name, value, flag in kept if name != PROPERTY or _valid(value)]
    if len(valid) == len(kept):
        return None
    return ";".join(f"{name}:{value}{flag}" for name, value, flag in valid)


def drop_invalid(root: ET.Element) -> None:
    """Drop each invalid paint-order: Chromium ignores the declaration, the cascade keeps the inherited value."""
    for element in root.iter():
        value = element.get(PROPERTY)
        if value is not None and not _valid(value):
            del element.attrib[PROPERTY]
        style = element.get("style")
        if style and PROPERTY in style.lower() and (kept := _valid_style(style)) is not None:
            element.set("style", kept)


def translucent_stroke(node: Any) -> bool:
    """Whether the stroke of node may let the fill show through: an opacity, a color alpha, a paint server."""
    if alpha_value(node.get("stroke-opacity", 1)) < 1:
        return True
    source, paint = node.get_paint("stroke")
    return bool(source) or (paint is not None and color(paint).alpha < 1)


def _passes(node: Any, fill: Any, stroke: Any) -> list[str] | None:
    """The paints of node in its order; None when one operator of WeasyPrint paints them so.

    B fills and strokes a path as one knockout object (PDF 11.7.4.4): a translucent stroke shows the
    backdrop, not the fill under it. Chromium shows the fill: such a stroke gets a pass of its own.
    """
    present = {"fill": bool(fill), "stroke": bool(stroke), "markers": bool(node.vertices) and any(node.get(name) for name in MARKER_ATTRIBUTES)}
    wanted = [name for name in order(node) if present[name]]
    if wanted != [name for name in DEFAULT if present[name]]:
        return wanted
    return wanted if fill and stroke and translucent_stroke(node) else None


def _path_span(items: list[Any]) -> tuple[int, int]:
    """Where the path being built starts and ends: the path operators at the end of the stream.

    A child without paint, a <title> or a <desc>, leaves q and Q after the path: they stay where they are.
    """
    end = len(items)
    while end and isinstance(items[end - 1], bytes) and items[end - 1] in STATE_OPERATORS:
        end -= 1
    start = end
    while start and isinstance(items[start - 1], bytes) and items[start - 1].rsplit(b" ", 1)[-1] in PATH_OPERATORS:
        start -= 1
    return start, end


def fill_stroke(self: Any, fill: Any, stroke: Any, even_odd: bool = False, text: bool = False) -> None:
    current = None if text else _core.drawing()
    items = self.stream.stream
    if current is None or (passes := _passes(current[0], fill, stroke)) is None or (span := _path_span(items))[0] == span[1]:
        _ORIGINAL_FILL_STROKE(self, fill, stroke, even_odd, text)
        return
    node, font_size = current
    stream, (start, end) = self.stream, span
    # Each paint gets the path again, all of them in the graphics state set_graphical_state left
    path = items[start:end]
    del items[start:end]
    for name in passes:
        if name == "markers":
            self.draw_markers(node, size(node.get("font-size", "1em"), font_size, font_size), True)
            continue
        items.extend(path)
        if name == "fill":
            stream.fill(even_odd)
        else:
            stream.stroke()


def split_text(stream: Any, node: Any, start: int) -> None:
    """Paint the text objects drawn since start in two passes, when one mode 2 object would paint them wrong.

    Text render mode 2 fills and strokes each glyph in turn, as one knockout object like B. Chromium
    paints the whole fill of the text, then its whole stroke, or the stroke first when paint-order says
    so. The copies keep that order across the glyphs too.
    """
    paints = order(node)
    stroke_first = paints.index("stroke") < paints.index("fill")
    if not _ENABLED["text"] or not (stroke_first or translucent_stroke(node)):
        return
    first, second = (STROKE_ONLY, FILL_ONLY) if stroke_first else (FILL_ONLY, STROKE_ONLY)
    items = stream.stream
    index = start
    while (begin := _find(items, b"BT", index)) is not None and (end := _find(items, b"ET", begin)) is not None:
        text_object = items[begin : end + 1]
        if FILL_AND_STROKE not in text_object:
            index = end + 1
            continue
        copies = [first if item == FILL_AND_STROKE else item for item in text_object]
        copies += [second if item == FILL_AND_STROKE else item for item in text_object]
        items[begin : end + 1] = copies
        index = begin + len(copies)


def _find(items: list[Any], operator: bytes, start: int) -> int | None:
    return next((index for index in range(start, len(items)) if items[index] == operator), None)


def install() -> None:
    _core.add_tree_pass(20, "paint_order", drop_invalid)
    wp_svg.SVG.fill_stroke = fill_stroke
    _ENABLED["text"] = True
    # fill_stroke reads the node from draw_node
    _core.enable_draw_feature("paint_order")
