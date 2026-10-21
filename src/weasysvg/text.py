"""SVG text.

Touches:
- ``svg.TAGS`` text entries and the global ``svg.text``, with one replacement ``draw_text``:
  font family resolved as Chromium does (fonts.py), dominant-baseline from real font metrics,
  text-decoration placed and sized from the font, as WeasyPrint draws it on HTML text. ``draw_node`` recognizes text nodes by that global, so both change together.
- ``svg.Node.cascade``: font-size keywords. ``size()`` knows none, so "initial" or "medium" gave 0.
  The cascade rewrites the attribute once, so every reader of font-size sees a length.
- a tree pass: a <text> inside a <text> is not rendered, as in browsers.
- a tree pass: a rotate list with a value that is no finite number is dropped, as in Chromium. WeasyPrint
  parses it during the cascade, and one bad value lost the whole SVG.

WeasyPrint lays SVG text out one character at a time: Arabic lost its joining and its order,
ligatures and kerning were gone. A run with one position at most, no rotate and no textLength is laid
out whole instead, by Pango, as Chromium does. letter-spacing goes to Pango too, which leaves cursive
scripts joined (css-text-3, cursive tracking). Other runs keep the layout of WeasyPrint.
"""

from __future__ import annotations

import functools
import math
import re
import sys
import weakref
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from xml.etree import ElementTree as ET

from weasyprint import svg as wp_svg
from weasyprint.css.properties import INITIAL_VALUES
from weasyprint.draw import text as wp_draw_text
from weasyprint.matrix import Matrix
from weasyprint.svg.bounding_box import EMPTY_BOUNDING_BOX, extend_bounding_box, is_valid_bounding_box
from weasyprint.svg.utils import normalize, size
from weasyprint.text.ffi import FROM_UNITS, TO_UNITS, ffi, pango
from weasyprint.text.fonts import FontConfiguration
from weasyprint.text.line_break import Layout

from . import _core, glyphs, paint_order, textpath, vertical
from .conditional import local_name
from .fonts import FALLBACK, resolve_families

TEXT_TAGS = ("a", "text", "textPath", "tspan")
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
# Marks the <tspan> keep_nested_tails makes for the text after a child: it matches no stylesheet rule
TAIL = "{https://github.com/grigoriev/weasysvg}tail"
_NO_RULES = SimpleNamespace(match=lambda _wrapper: [])
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
DRAWN = "_weasysvg_drawn"
FEATURES = {"fonts": True, "baseline": True, "decoration": True}
DEFAULT_FONT_PX = 16.0  # px, the 12pt WeasyPrint draws an SVG with

_ORIGINAL_CASCADE = wp_svg.Node.cascade
_ORIGINAL_TEXT = wp_svg.TAGS["text"]
_ORIGINAL_DRAW_FIRST_LINE = wp_draw_text.draw_first_line


@dataclass
class Drawn:
    """What a decorated node drew: the pieces its lines run over."""

    stream: Any  # a pattern fill draws its own text meanwhile, into a stream of its own
    by_character: bool  # laid out one character at a time, by text() of WeasyPrint
    letters: list[tuple[float, float, float]] = field(default_factory=list)  # left end, advance and baseline of each run


# What draw_first_line places while text() of WeasyPrint draws a decorated node
_RECORDED: ContextVar[Drawn | None] = ContextVar("weasysvg_recorded_glyphs", default=None)


# ---------------- font sizes ----------------


# The font size of a node as computed along the document, in px
FONT_PX = "_weasysvg_font_px"
# Drawn where they are used, with the size of the user: their text inherits from their own ancestors
RESOURCES = frozenset(("clipPath", "mask", "marker", "pattern"))


# The fonts of the SVG being drawn, weakly: its lazy definitions cascade while it draws
_DRAWING_FONTS: ContextVar[Any] = ContextVar("weasysvg_drawing_fonts", default=None)


def note_fonts(svg: Any, _node: Any) -> None:
    """Note the fonts of the SVG that draws, with its @font-face rules, for the cascade to measure ex."""
    if svg.font_config is not None:
        _DRAWING_FONTS.set(weakref.ref(svg.font_config))


@functools.cache
def _system_fonts() -> Any:
    return FontConfiguration()


def _fonts() -> Any:
    """The fonts of the SVG that draws, else, outside a drawing, the fonts of the system."""
    noted = _DRAWING_FONTS.get()
    fonts = noted() if noted is not None else None
    return fonts if fonts is not None else _system_fonts()


def _ex_count(value: str) -> float | None:
    """How many ex value is, or None if it is no size in ex."""
    word = normalize(value).split(" ", 1)[0]
    if not word.endswith("ex"):
        return None
    try:
        return float(word[:-2])
    except ValueError:
        return None


def _resolved_px(parent: Any, value: str, parent_px: float) -> float:
    """A font size value in px, against the size and font of parent: ex is the x-height of that font."""
    if normalize(value).split(" ", 1)[0].endswith("ex"):
        count = _ex_count(value)
        if count is None:
            return parent_px  # a word that ends in ex, which WeasyPrint cannot read either
        x_height = _metrics(SimpleNamespace(font_config=_fonts()), parent, parent_px)[2] or parent_px / 2
        return count * x_height
    return float(size(value, parent_px, parent_px))


def _font_px(node: Any) -> float:
    """The computed font size of node: noted by the cascade, or of the root, against the 12pt of WeasyPrint.

    The root has no parent: its own font measures its ex, as ex_restyle draws it.
    """
    noted = getattr(node, FONT_PX, None)
    if noted is None:
        noted = _resolved_px(node, node.attrib.get("font-size", "1em"), DEFAULT_FONT_PX)
        setattr(node, FONT_PX, noted)
    return float(noted)


def _cascade_without_rules(self: Any, child: Any) -> None:
    """The cascade of WeasyPrint with no stylesheet rule: the text after a child is no element in a browser."""
    style = self._style
    self._style = (_NO_RULES, _NO_RULES)
    try:
        _ORIGINAL_CASCADE(self, child)
    finally:
        self._style = style


def cascade(self: Any, child: Any) -> None:
    """Cascade the attributes to child, with the font size inherited as computed, not as written.

    WeasyPrint copies the font-size of the parent to the child as text: a relative size such as "2em" then
    applies again to the size it made. Without it the child takes "1em", the computed size of the parent.
    A resource gets its computed size written out: it draws with the size of the element that uses it,
    and its text must still inherit from its own ancestors. A size in ex is written out too, from the
    x-height of the font of the parent as CSS says: code that reads the size before the element draws
    then reads the same size.
    """
    parent = self.attrib.pop("font-size", None) if self is not child else None
    try:
        if TAIL in child.attrib:
            _cascade_without_rules(self, child)
        else:
            _ORIGINAL_CASCADE(self, child)
    finally:
        if parent is not None:
            self.attrib["font-size"] = parent
    value = child.attrib.get("font-size")
    keyword = (value or "").strip().lower()
    if keyword in ("unset", "revert", "revert-layer"):
        del child.attrib["font-size"]
    elif keyword in FONT_SIZE_KEYWORDS:
        child.attrib["font-size"] = FONT_SIZE_KEYWORDS[keyword]
    if self is child:
        return
    parent_px = _font_px(self)
    own = child.attrib.get("font-size", "1em")
    setattr(child, FONT_PX, _resolved_px(self, own, parent_px))
    if child.tag in RESOURCES or normalize(own).split(" ", 1)[0].endswith("ex"):
        child.attrib["font-size"] = f"{getattr(child, FONT_PX)}px"


def ex_restyle(svg: Any, node: Any, font_size: float) -> dict[str, str | None] | None:
    """A font-size in ex becomes px: one ex is the x-height of the font, as in Chromium, not half the em.

    The cascade writes out every size in ex but the one of the root <svg>, which it never reaches.
    """
    count = _ex_count(node.attrib.get("font-size", ""))
    if count is None:
        return None
    saved = {"font-size": node.attrib["font-size"]}
    # A font with no ink for "x" has no x-height: CSS then takes half an em
    x_height = _metrics(svg, node, font_size)[2] or font_size / 2
    node.attrib["font-size"] = f"{count * x_height}px"
    return saved


# ---------------- nested text ----------------


def drop_nested_text(root: ET.Element) -> None:
    """A <text> inside a <text> is not rendered."""
    for outer in [element for element in root.iter() if local_name(element.tag) == "text"]:
        for parent in list(outer.iter()):
            for child in list(parent):
                if local_name(child.tag) == "text":
                    parent.remove(child)


def _drawn_text(element: ET.Element, outer: ET.Element, parents: dict[ET.Element, ET.Element]) -> bool:
    """Whether element and every element between it and the <text> outer hold text that is drawn."""
    while element is not outer:
        if local_name(element.tag) not in TEXT_TAGS:
            return False
        element = parents[element]
    return True


def _split_tails(parent: ET.Element) -> None:
    """Give the text after each child of parent a <tspan> of its own, marked as a tail."""
    namespace = parent.tag.rpartition("}")[0] + "}" if "}" in parent.tag else ""
    # From the end, so an insertion moves no child still to come
    for index, child in reversed(list(enumerate(parent))):
        if child.tail:
            tspan = ET.Element(namespace + "tspan", {TAIL: ""})
            # WeasyPrint reads the xml:space of a nested element from its own attributes alone
            if (space := parent.get(XML_SPACE)) is not None:
                tspan.set(XML_SPACE, space)
            tspan.text, child.tail = child.tail, None
            parent.insert(index + 1, tspan)


def keep_nested_tails(root: ET.Element) -> None:
    """The text after a child of a <tspan> becomes a <tspan> of its own.

    WeasyPrint makes such an anonymous <tspan> for the children of a <text> and drops the text after the
    children of a <tspan>: Polarion writes <wbr/> into the labels of its charts, "Don<wbr/>e". The new
    <tspan> is no element in a browser, so cascade matches no stylesheet rule against it.
    """
    for outer in [element for element in root.iter() if local_name(element.tag) == "text"]:
        parents = {child: parent for parent in outer.iter() for child in parent}
        # Only the children of a <tspan>: WeasyPrint draws those of a <textPath> or <a>, and trims the last.
        # Only where the text is drawn: the text of a <desc> or an unknown element stays hidden
        for parent in [element for element in outer.iter() if local_name(element.tag) == "tspan" and _drawn_text(element, outer, parents)]:
            _split_tails(parent)


def _text_pieces(element: ET.Element, owner: ET.Element) -> list[tuple[ET.Element, str]]:
    """The text of element and of its drawn descendants in document order, as the node and "text" or "tail".

    A tail belongs to the parent of its node: owner is the element whose text it is.
    """
    pieces = [(element, "text")]
    for child in element:
        if local_name(child.tag) in TEXT_TAGS:
            pieces += _text_pieces(child, child)
        pieces.append((child, "tail"))
    return pieces


def drop_trailing_space(root: ET.Element) -> None:
    """The white space that ends the content of a <text> is dropped, as xml:space="default" says.

    WeasyPrint drops it from the text after the last child of a <text> only: a space at the end of the last
    <tspan> stayed, and text-anchor counted it, "Rational thoughts " of a Mermaid note moved by half a space.
    """
    for outer in [element for element in root.iter() if local_name(element.tag) == "text"]:
        if outer.get(XML_SPACE) == "preserve":
            continue
        for node, kind in reversed(_text_pieces(outer, outer)):
            if kind == "text" and node.get(XML_SPACE) == "preserve":
                break
            value = getattr(node, kind) or ""
            setattr(node, kind, value.rstrip(" \t\r\n") or None)
            if value.strip():
                break


def drop_invalid_rotate(root: ET.Element) -> None:
    for element in root.iter():
        value = element.get("rotate")
        if value is None or local_name(element.tag) not in TEXT_TAGS:
            continue
        try:
            valid = all(math.isfinite(float(number)) for number in normalize(value).split())
        except ValueError:
            valid = False
        if not valid:
            del element.attrib["rotate"]


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
    ink = ffi.new(PANGO_RECTANGLE)
    logical = ffi.new(PANGO_RECTANGLE)
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


# ---------------- text chunks ----------------

CHUNK_BOX = "_weasysvg_chunk_box"
TEXT_TAGS_WITH_CHUNKS = frozenset(("text", "tspan", "a"))
# The text chunk started last in the <text> being drawn: the text after it belongs to it, until the next one
LAST_CHUNK: ContextVar[Any] = ContextVar("weasysvg_last_chunk", default=None)


def _holds(node: Any, target: Any) -> bool:
    return node is target or any(_holds(child, target) for child in node)


def anchored(node: Any, box: Any) -> Any:
    """The box of a text or a text chunk where its text-anchor moved it: WeasyPrint keeps the box from before."""
    anchor, direction = node.get("text-anchor", "start"), node.get("direction", "ltr")
    if (anchor, direction) in (("start", "ltr"), ("end", "rtl")) or not is_valid_bounding_box(box):
        return box
    x, y, width, height = box
    return (x - (width / 2 if anchor == "middle" else width), y, width, height)


def starts_chunk(node: Any) -> bool:
    return node.tag in TEXT_TAGS_WITH_CHUNKS and node.tag != "text" and ("x" in node.attrib or "y" in node.attrib)


def chunk_started(_svg: Any, node: Any) -> None:
    """Note the chunk a node starts, or that a <text> starts with none, before the node draws."""
    if node.tag == "text":
        LAST_CHUNK.set(None)
    elif starts_chunk(node):
        LAST_CHUNK.set(node)


def chunk_boxes(_svg: Any, node: Any) -> None:
    """Keep the box of a text chunk out of the anchor of its parent, and give it back afterwards.

    A tspan with its own x or y starts a text chunk, which text-anchor places on its own. WeasyPrint draws it
    so, but then adds its box to the box of the parent, which anchors its own chunk by the width of both.
    The box of a chunk is hidden and passed up until the <text> or an enclosing chunk is drawn, then added
    back to it: a gradient or a filter of the text still spans every chunk. A tspan that starts no chunk
    passes the boxes on, since WeasyPrint merges its own box into the anchor of the chunk around it.
    The box of the text and of each chunk ends where text-anchor drew it, so effects see the text as drawn.
    Text after a chunk, the white space between the tspans included, belongs to that chunk: its box is
    hidden as the box of the chunk is. Text inside the chunk started last is left to WeasyPrint, which
    merges it into that chunk.
    """
    if node.tag not in TEXT_TAGS_WITH_CHUNKS or _planned(node) is not None:
        return
    hidden = [entry for child in node for entry in child.__dict__.pop(CHUNK_BOX, ())]
    box = getattr(node, "text_bounding_box", None)
    starts = starts_chunk(node) and is_valid_bounding_box(box)
    last = LAST_CHUNK.get()
    if node.tag != "text" and not starts and last is not None and not _holds(node, last) and not _holds(last, node) and is_valid_bounding_box(box):
        # Drawn after a chunk and holding none: its text continues that chunk
        hidden.append((node, box))
        node.text_bounding_box = EMPTY_BOUNDING_BOX
    if node.tag == "text" or starts:
        # The width WeasyPrint anchored by: the chunks below are not in it, they moved on their own
        node.text_bounding_box = anchored(node, node.text_bounding_box)
        for owner, box in hidden:
            owner.text_bounding_box = box
            x, y, width, height = box
            node.text_bounding_box = extend_bounding_box(node.text_bounding_box, ((x, y), (x + width, y + height)))
        hidden = []
    if starts:
        hidden = [(node, node.text_bounding_box)]
        node.text_bounding_box = EMPTY_BOUNDING_BOX
    if node.tag == "text":
        LAST_CHUNK.set(None)
    if hidden:
        node.__dict__[CHUNK_BOX] = hidden


# ---------------- chunk plans ----------------
#
# The groups of WeasyPrint anchor the text of one element with its descendants: text after a positioned
# <tspan> stayed in the chunk of the <text>, "<tspan x="150">AAA</tspan>BBB" drew BBB off the left edge.
# A chunk runs from a character with an absolute x or y to the next one, across elements, and takes the
# anchor of the element of its first character (SVG 2, text chunks). A text with more than one chunk is
# laid out once first, into a scratch group: each piece draw_first_line places is noted with its chunk.
# Then WeasyPrint anchors nothing, and each node draws moved by the shift of its own chunk.


@dataclass
class _Piece:
    """What one call of draw_first_line placed: a character, or a whole run."""

    node: Any
    start: float
    end: float
    absolute: bool  # whether its first character has an absolute x or y: it starts a chunk
    shift: float = 0.0


@dataclass
class ChunkPlan:
    """The chunks of one <text>: recorded by a scratch layout, then applied while the text draws."""

    text: Any
    recording: bool = True
    nodes: dict[int, Any] = field(default_factory=dict)  # the text and the text elements inside it
    pieces: list[_Piece] = field(default_factory=list)
    pending: bool = False  # a node with x or y and no text: its position goes to the next character

    def of(self, node: Any) -> list[_Piece]:
        return [piece for piece in self.pieces if piece.node is node]

    def place(self) -> None:
        """Give each piece the shift text-anchor gives its chunk."""
        chunks: list[list[_Piece]] = []
        for piece in self.pieces:
            if piece.absolute or not chunks:
                chunks.append([])
            chunks[-1].append(piece)
        for chunk in chunks:
            anchor, direction = _anchor(chunk[0].node)
            width = max(piece.end for piece in chunk) - min(piece.start for piece in chunk)
            factor = {"middle": 0.5, "end": 0.0 if direction == "rtl" else 1.0}.get(anchor, 1.0 if direction == "rtl" else 0.0)
            for piece in chunk:
                piece.shift = -width * factor


@dataclass
class _Drawing:
    """The node draw_text is drawing inside a planned text, and how many pieces it placed so far."""

    plan: ChunkPlan
    node: Any
    absolute: list[bool]  # recording: whether each piece starts with an absolute position
    offsets: list[float]  # applying: how far each piece moves past the shift of the whole node
    stream: Any  # the node draws here: a pattern of its fill draws text of its own in another stream
    index: int = 0

    def place(self, matrix: Any) -> Any:
        """The matrix of the next piece, moved by its offset."""
        offset = self.offsets[self.index] if self.index < len(self.offsets) else 0.0
        self.index += 1
        return matrix @ Matrix(e=offset) if offset else matrix

    def record(self, textbox: Any, matrix: Any) -> None:
        absolute = self.index < len(self.absolute) and self.absolute[self.index]
        start = matrix[2][0]
        advance = _line_width(textbox.pango_layout) * math.hypot(matrix[0][0], matrix[1][0])
        self.plan.pieces.append(_Piece(self.node, start, start + advance, absolute or self.plan.pending))
        self.plan.pending = False
        self.index += 1


# The plans of the texts being drawn, the innermost last
_PLANS: ContextVar[tuple[ChunkPlan, ...]] = ContextVar("weasysvg_chunk_plans", default=())
_DRAWING: ContextVar[_Drawing | None] = ContextVar("weasysvg_chunk_drawing", default=None)


def _planned(node: Any) -> ChunkPlan | None:
    """The plan of the text being drawn, if node lies in it."""
    plans = _PLANS.get()
    return plans[-1] if plans and id(node) in plans[-1].nodes else None


def _anchor(node: Any) -> tuple[str, str]:
    return node.get("text-anchor", "start"), node.get("direction", "ltr")


def _shifting(node: Any) -> bool:
    return _anchor(node) not in (("start", "ltr"), ("end", "rtl"))


def _count(node: Any, name: str) -> int:
    return len(normalize(node.attrib.get(name, "")).split())


def _text_nodes(node: Any) -> Iterator[Any]:
    yield node
    for child in node:
        if child.tag in TEXT_TAGS_WITH_CHUNKS:
            yield from _text_nodes(child)


def needs_plan(node: Any) -> bool:
    """Whether a <text> holds a chunk WeasyPrint anchors wrong: more than one, or one anchored by a descendant.

    A text of one chunk anchored by the <text> itself is right already, and spared a second layout.
    """
    if _laid_out(node):
        return False
    nodes = list(_text_nodes(node))
    if not any(_shifting(item) for item in nodes):
        return False
    own = _anchor(node)
    return any(max(_count(item, "x"), _count(item, "y")) > 1 or (item is not node and (starts_chunk(item) or _anchor(item) != own)) for item in nodes)


def _record(svg: Any, node: Any, font_size: float) -> ChunkPlan:
    """Lay the text out into a scratch group, unanchored, and plan the shift of each piece."""
    # The children cascade the original anchor here, before chunk_restyle changes it
    plan = ChunkPlan(node, nodes={id(item): item for item in _text_nodes(node)})
    outer = svg.stream
    scratch = outer.add_group(0, 0, 0, 0)
    cursor, shift = svg.cursor_position, list(svg.cursor_d_position)
    token = _PLANS.set((*_PLANS.get(), plan))
    chunk = LAST_CHUNK.set(LAST_CHUNK.get())
    saved = {key: item.bounding_box for key, item in plan.nodes.items()}
    try:
        svg.stream = scratch
        # Without fill_stroke: no restyler, no effect, the anchor groups of WeasyPrint stay in the scratch group
        svg.draw_node(node, font_size, fill_stroke=False)
    finally:
        svg.stream = outer
        svg.cursor_position, svg.cursor_d_position = cursor, shift
        _PLANS.reset(token)
        LAST_CHUNK.reset(chunk)
        outer._resources["XObject"].pop(scratch.id, None)
        # The boxes of the scratch layout lie where no anchor put them: effects measure the text as drawn
        for item in plan.nodes.values():
            item.__dict__.pop("text_bounding_box", None)
            item.bounding_box = saved[id(item)]
    plan.recording = False
    plan.place()
    return plan


def chunk_restyle(svg: Any, node: Any, font_size: float) -> dict[str, str | None] | None:
    """Plan the chunks of a <text> before it draws; text-anchor then reads start to WeasyPrint inside it."""
    plans = _PLANS.get()
    if node.tag == "text":
        if plans and plans[-1].text is node:
            plan = plans[-1]  # drawn again inside its own drawing: measured for an effect, or blurred
        elif needs_plan(node):
            plan = _record(svg, node, font_size)
        else:
            return None
        _PLANS.set((*plans, plan))
    elif _planned(node) is None:
        return None
    # The children cascade the original anchor first: they keep their own copy of it
    list(node)
    saved = {"text-anchor": node.attrib.get("text-anchor")}
    node.attrib["text-anchor"] = "end" if node.get("direction") == "rtl" else "start"
    return saved


def chunk_done(_svg: Any, node: Any) -> None:
    """End the plan of a <text> once it is drawn."""
    plans = _PLANS.get()
    if node.tag == "text" and plans and plans[-1].text is node and not plans[-1].recording:
        _PLANS.set(plans[:-1])


def _absolute(node: Any) -> list[bool]:
    """Whether each piece the node draws starts with an absolute x or y: a whole run is one piece."""
    if _whole_run(node):
        return ["x" in node.attrib or "y" in node.attrib]
    count = max(_count(node, "x"), _count(node, "y"))
    return [index < count for index in range(len(node.text or ""))]


def _draw_planned(svg: Any, node: Any, font_size: float, plan: ChunkPlan) -> Any:
    """Draw a node of a planned text: noted piece by piece, or moved by the shift of its chunk."""
    if plan.recording:
        token = _DRAWING.set(_Drawing(plan, node, _absolute(node), [], svg.stream))
        count = len(plan.pieces)
        try:
            return _draw_text(svg, node, font_size)
        finally:
            _DRAWING.reset(token)
            if len(plan.pieces) > count:
                # The text after the node goes on from the cursor: its last piece ends there, past the
                # letter-spacing the extents of Pango leave out
                plan.pieces[-1].end = svg.cursor_position[0] + svg.cursor_d_position[0]
            if not node.text and ("x" in node.attrib or "y" in node.attrib):
                plan.pending = True
    pieces = plan.of(node)
    if not pieces:
        return _draw_text(svg, node, font_size)
    shift = pieces[0].shift
    token = _DRAWING.set(_Drawing(plan, node, [], [piece.shift - shift for piece in pieces], svg.stream))
    svg.stream.push_state()
    try:
        svg.stream.transform(e=shift)
        result = _draw_text(svg, node, font_size)
    finally:
        svg.stream.pop_state()
        _DRAWING.reset(token)
    # A node that placed pieces has a box: where WeasyPrint laid it out, before the shifts
    x, y, width, height = node.text_bounding_box
    if all(piece.shift == shift for piece in pieces):
        left, right = x + shift, x + width + shift
    else:
        left, right = min(piece.start + piece.shift for piece in pieces), max(piece.end + piece.shift for piece in pieces)
    node.text_bounding_box = (left, y, right - left, height)
    return result


# ---------------- leading shifts ----------------

# A TJ array that starts with a shift: an empty string first, or none
_LEADING_SHIFT = re.compile(r"^(?:<>)?(-?\d+(?:\.\d+)?(?:e-?\d+)?)(?=<)")


@contextmanager
def carried_shifts(stream: Any) -> Iterator[None]:
    """Move a shift at the start of a TJ array to the end of the array before it, while text is drawn.

    PDFium drops a shift at the start of an array, so a letter-spacing Pango puts before a glyph got
    lost. At the end of the array before, in the same text object, the shift is the same. Only a font
    change may lie between: its size scales the shift.
    """
    state: dict[str, Any] = {"size": None, "last": None}
    show_text, set_font_size = stream.show_text, stream.set_font_size

    def sized(font: Any, size: float) -> None:
        state["size"] = size
        set_font_size(font, size)

    def show(text: str) -> None:
        match = _LEADING_SHIFT.match(text)
        last = state["last"]
        if match and last is not None and all(entry.endswith(b" Tf") for entry in stream.stream[last[0] + 1 :]):
            index, size = last
            value = match[1] if size == state["size"] else str(float(match[1]) * state["size"] / size)
            stream.stream[index] = stream.stream[index][: -len(b"] TJ")] + f" {value}] TJ".encode()
            text = text[match.end() :]
        show_text(text)
        state["last"] = (len(stream.stream) - 1, state["size"])

    # An override of the stream that another patch set stays: it comes back afterwards
    missing = object()
    previous = {name: stream.__dict__.get(name, missing) for name in ("show_text", "set_font_size")}
    stream.show_text, stream.set_font_size = show, sized
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is missing:
                del stream.__dict__[name]
            else:
                setattr(stream, name, value)


# ---------------- text-decoration ----------------


def font_lines(lines: list[str], layout: Any) -> list[tuple[float, float]]:
    """Top, below the baseline, and thickness of each decoration line, as WeasyPrint draws them on HTML text.

    draw_text of WeasyPrint reads them from the metrics Pango gives for the font (post and OS/2 tables):
    the underline from its position and thickness, the overline from the ascent down, as thick as the
    underline, the line-through centered on its position with its own thickness. SVG text and HTML text of
    one PDF so get the same lines. Chromium draws font-size / 10 instead; resvg and Firefox read the font
    too, and text-decoration-thickness: auto allows both.
    """
    out = []
    if "underline" in lines:
        out.append((-layout.underline_position, layout.underline_thickness))
    if "overline" in lines:
        out.append((-layout.ascent, layout.underline_thickness))
    if "line-through" in lines:
        out.append((-layout.strikethrough_position - layout.strikethrough_thickness / 2, layout.strikethrough_thickness))
    return out


def _lines(node: Any) -> list[str]:
    return [line for line in DECORATION_LINES if line in (node.get("text-decoration") or "").split()]


def _line_width(layout: Any) -> float:
    line, _ = layout.get_first_line()
    logical = ffi.new(PANGO_RECTANGLE)
    pango.pango_layout_line_get_extents(line, ffi.NULL, logical)
    width: float = logical.width * FROM_UNITS
    return width


def _spacing(svg: Any, node: Any, font_size: float, width: float) -> float:
    """The letter-spacing text() of WeasyPrint puts after each character, before textLength adds its room.

    lengthAdjust="spacingAndGlyphs" scales it with the glyphs, as text() does, from the width of the whole text.
    """
    spacing = float(svg.length(node.get("letter-spacing"), font_size))
    text_length = svg.length(node.get("textLength"), font_size)
    if spacing and text_length and normalize(node.attrib.get("lengthAdjust")) == "spacingAndGlyphs":
        spacing *= text_length / (width + (len(node.text) - 1) * spacing)
    return spacing


def _segments(pieces: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    """The pieces that touch or overlap on one baseline merged into one: the line shows no seam between them."""
    out: list[tuple[float, float, float]] = []
    for left, right, baseline in sorted(pieces, key=lambda piece: (piece[2], piece[0])):
        if out and out[-1][2] == baseline and left <= out[-1][1] + 1e-9 * max(1.0, abs(out[-1][1])):
            out[-1] = (out[-1][0], max(out[-1][1], right), baseline)
        else:
            out.append((left, right, baseline))
    return out


def _pieces(svg: Any, node: Any, font_size: float, drawn: Drawn, width: float) -> list[tuple[float, float, float]]:
    """Where the lines run: under each run, and under the letter-spacing after it.

    Measured in Chromium, which Safari and Firefox match: text laid out one character at a time carries its
    lines character by character, over the advance and the letter-spacing of each. The room textLength, x
    and dx add between characters stays bare. textLength bounds the text, so the last character carries no
    letter-spacing past it.
    """
    if not drawn.by_character:
        return [(left, left + advance, baseline) for left, advance, baseline in drawn.letters]
    spacing = _spacing(svg, node, font_size, width)
    last = len(drawn.letters) - 1 if node.get("textLength") else -1
    return _segments([(left, left + advance + (spacing if index != last else 0), baseline) for index, (left, advance, baseline) in enumerate(drawn.letters)])


def _decorate(svg: Any, node: Any, font_size: float) -> None:
    """Draw the lines over the runs text() just laid out, with the position and thickness of the font.

    The lines run straight through the glyphs: WeasyPrint skips no ink on HTML text, nor does resvg.
    Limits: the paint of the node itself, not of the element that declares the lines.
    """
    drawn: Drawn | None = node.__dict__.pop(DRAWN, None)
    lines = _lines(node)
    if drawn is None or not drawn.letters or not lines or not node.text or not node.text.strip() or not is_valid_bounding_box(node.text_bounding_box):
        return
    style = _style(svg, node, font_size)
    style["text_decoration_line"] = set(lines)
    layout = Layout(style)
    layout.set_text(node.text)
    found = font_lines(lines, layout)
    width = _line_width(layout)
    layout.deactivate()
    pieces = _pieces(svg, node, font_size, drawn, width)
    _draw_lines(svg, node, font_size, [(start, baseline + top, end - start, thickness) for top, thickness in found for start, end, baseline in pieces])


def _draw_lines(svg: Any, node: Any, font_size: float, rects: list[tuple[float, float, float, float]]) -> None:
    """Fill the rectangles of the lines in the paint of the node."""
    svg.stream.push_state()
    try:
        fill, stroke = svg.set_graphical_state(node, font_size)
        for rect in rects:
            svg.stream.rectangle(*rect)
        svg.fill_stroke(fill, stroke)
    finally:
        svg.stream.pop_state()


# ---------------- the text() replacement ----------------


POSITIONS = ("x", "y", "dx", "dy")
PANGO_RECTANGLE = "PangoRectangle *"


def _track(layout: Any, spacing: float) -> float:
    """Letter-spacing on the characters outside cursive scripts only; return the new line width.

    Pango spaces every character alike, which tears Arabic letters apart. Chromium spaces the rest, the
    spaces between Arabic words included.
    """
    attributes = pango.pango_attr_list_new()
    start = 0
    for character in layout.text:
        end = start + len(character.encode())
        if not glyphs.cursive(character):
            attribute = pango.pango_attr_letter_spacing_new(int(spacing * TO_UNITS))
            attribute.start_index, attribute.end_index = start, end
            pango.pango_attr_list_change(attributes, attribute)
        start = end
    pango.pango_layout_set_attributes(layout.layout, attributes)
    pango.pango_attr_list_unref(attributes)
    return _line_width(layout)


def _whole_run(node: Any) -> bool:
    """A run Pango can lay out whole: per-character positions, rotate and textLength need WeasyPrint."""
    if not node.text or any(node.get(name) for name in ("rotate", "textLength", "display-anchor")):
        return False
    return all(len(normalize(node.attrib.get(name, "")).split()) <= 1 for name in POSITIONS)


def _position(node: Any, name: str, font_size: float, reference: float) -> float | None:
    values = normalize(node.attrib.get(name, "")).split()
    return size(values[0], font_size, reference) if values else None


def _advance(svg: Any, node: Any, font_size: float, width: float) -> tuple[float, float]:
    """Where a run of width starts, from x, y, dx and dy of node and the cursor, which moves past it."""
    x, y = _position(node, "x", font_size, svg.inner_width), _position(node, "y", font_size, svg.inner_height)
    if x is not None:
        svg.cursor_d_position[0] = 0
    if y is not None:
        svg.cursor_d_position[1] = 0
    svg.cursor_d_position[0] += _position(node, "dx", font_size, svg.inner_width) or 0
    svg.cursor_d_position[1] += _position(node, "dy", font_size, svg.inner_height) or 0
    x = svg.cursor_position[0] if x is None else x
    y = svg.cursor_position[1] if y is None else y
    svg.cursor_position = x + width, y
    return x, y


def _draw_run(svg: Any, node: Any, font_size: float) -> None:
    """The text of the node laid out and drawn as one run, positioned as text() of WeasyPrint does."""
    from weasyprint.draw.text import draw_emojis, draw_first_line
    from weasyprint.text.line_break import split_first_line

    style = _style(svg, node, font_size)
    if node.get("direction") in ("ltr", "rtl"):
        style["direction"] = node.get("direction")
    letter_spacing = svg.length(node.get("letter-spacing"), font_size)
    tracked = bool(letter_spacing) and any(glyphs.cursive(character) for character in node.text)
    if letter_spacing and not tracked:
        style["letter_spacing"] = letter_spacing
    layout, _, _, width, height, baseline = split_first_line(node.text, style, svg.context, float("inf"), 0)
    if tracked:
        # split_first_line hands the layout back deactivated
        layout.reactivate(style)
        width = _track(layout, letter_spacing)
        layout.deactivate()

    x, y = _advance(svg, node, font_size, width)
    x_position, y_position = x + svg.cursor_d_position[0], y + svg.cursor_d_position[1]
    points = ((x_position, y_position - baseline), (x_position + width, y_position - baseline + height))
    node.text_bounding_box = extend_bounding_box(node.text_bounding_box, points)

    # The state after the bounding box, for gradients and patterns, before drawing
    svg.stream.push_state()
    try:
        fill, stroke = svg.set_graphical_state(node, font_size)
        svg.stream.begin_text()
        layout.reactivate(style)
        if tracked:
            _track(layout, letter_spacing)
        svg.fill_stroke(fill, stroke, text=True)
        text_box = sys.modules["weasyprint.svg.text"].TextBox(layout, style)
        text_box.baseline = baseline
        with carried_shifts(svg.stream):
            emojis = draw_first_line(svg.stream, text_box, "none", "none", Matrix(d=-1, e=x_position, f=y_position))
        # Where the run lies, for its decoration lines
        if FEATURES["decoration"] and _lines(node):
            node.__dict__[DRAWN] = Drawn(svg.stream, False, [(x_position, width, y_position)])
        svg.stream.end_text()
    finally:
        svg.stream.pop_state()
    draw_emojis(svg.stream, style, x, y, emojis)


def recorded_draw_first_line(stream: Any, textbox: Any, text_overflow: Any, block_ellipsis: Any, matrix: Any) -> Any:
    """draw_first_line of WeasyPrint, noting each character it places while a decorated node draws.

    The decoration lines run under each character on its own baseline. A turned character keeps its piece
    level, as in Chromium.
    """
    drawing = _DRAWING.get()
    if drawing is not None and drawing.stream is not stream:
        drawing = None
    if drawing is not None and not drawing.plan.recording:
        matrix = drawing.place(matrix)
    emojis = _ORIGINAL_DRAW_FIRST_LINE(stream, textbox, text_overflow, block_ellipsis, matrix)
    if drawing is not None and drawing.plan.recording:
        drawing.record(textbox, matrix)
    recording = _RECORDED.get()
    if recording is not None and recording.stream is stream:
        x, baseline = matrix[2][0], matrix[2][1]
        # The first column holds the scale of textLength, turned or not
        recording.letters.append((x, _line_width(textbox.pango_layout) * math.hypot(matrix[0][0], matrix[1][0]), baseline))
    return emojis


def _draw_decorated(svg: Any, node: Any, font_size: float) -> Any:
    if _whole_run(node):
        _draw_run(svg, node, font_size)
        result = None
    elif FEATURES["decoration"] and _lines(node):
        # WeasyPrint lays the text out one character at a time: its characters are noted as they are drawn
        drawn = Drawn(svg.stream, True)
        token = _RECORDED.set(drawn)
        try:
            result = _ORIGINAL_TEXT(svg, node, font_size)
            node.__dict__[DRAWN] = drawn
        finally:
            _RECORDED.reset(token)
    else:
        result = _ORIGINAL_TEXT(svg, node, font_size)
    if FEATURES["decoration"]:
        _decorate(svg, node, font_size)
    return result


# ---------------- textPath ----------------


def _family(svg: Any, node: Any) -> str:
    families = node.get("font-family") or ""
    return f"{resolve_families(families, svg.font_config)}, {FALLBACK}" if FEATURES["fonts"] else families


def _advances(svg: Any, node: Any, font_size: float) -> list[tuple[str, float]]:
    """Each character of the node with its advance, laid out one at a time as on a path."""
    from weasyprint.text.line_break import split_first_line

    if not node.text:
        return []
    style = _style(svg, node, font_size)
    # A <tspan> measured ahead of its drawing has its family not resolved yet
    style["font_family"] = [family.strip() for family in _family(svg, node).split(",")]
    # Each character in the joining context of its word: laid out alone, Arabic still joins
    shaped = [glyphs.in_context(node.text, index) for index in range(len(node.text))]
    return [(string, split_first_line(string, style, svg.context, float("inf"), 0)[3]) for string in shaped]


def _path_decorations(svg: Any, node: Any, font_size: float) -> list[tuple[float, float]]:
    """Top and thickness of each decoration line, below the baseline positive."""
    lines = _lines(node)
    if not lines:
        return []
    style = _style(svg, node, font_size)
    # Layout measures the lines it is asked for only
    style["text_decoration_line"] = set(lines)
    layout = Layout(style)
    layout.set_text(node.text or "x")
    found = font_lines(lines, layout)
    layout.deactivate()
    return found


def _laid_out(node: Any) -> bool:
    """A node textpath.py or vertical.py lays out: text-anchor must read start to WeasyPrint."""
    if node.tag == "textPath":
        return True
    if node.tag == "text":
        return vertical.vertical(node) or any(child.tag == "textPath" for child in node)
    return node.tag in ("tspan", "a") and (textpath.current(node) is not None or vertical.current(node) is not None)


def anchor_restyle(_svg: Any, node: Any, _font_size: float) -> dict[str, str | None] | None:
    """text-anchor reads start to WeasyPrint on text this module lays out; ANCHOR keeps the value."""
    if not _laid_out(node):
        return None
    # The children cascade the original anchor first: they keep their own copy of it
    list(node)
    new = {"text-anchor": "start", textpath.ANCHOR: node.get(textpath.ANCHOR) or node.get("text-anchor", "start")}
    saved = {key: node.attrib.get(key) for key in new}
    node.attrib.update(new)
    return saved


def _draw_vertical(svg: Any, node: Any, font_size: float) -> bool:
    """Draw node down the y axis, if it is vertical text; return whether it was."""
    if node.tag == "text":
        if not vertical.vertical(node):
            vertical.CURRENT.set(None)
            return False
        run = vertical.start(svg, node, textpath._texts(node, font_size), _advances)
    else:
        found = vertical.current(node)
        if found is None:
            return False
        run = found
    vertical.draw(svg, node, font_size, run, _style(svg, node, font_size), _advances(svg, node, font_size))
    return True


def _draw_on_path(svg: Any, node: Any, font_size: float) -> bool:
    """Draw node on its text path, if it has one; return whether it had."""
    if node.tag == "text":
        textpath.CURRENT.set(None)
        return False
    if node.tag == "textPath":
        state = textpath.start(svg, node, font_size, _advances)
    else:
        found = textpath.current(node)
        if found is None:
            return False
        state = found
    textpath.draw(svg, node, font_size, state, _style(svg, node, font_size), _advances(svg, node, font_size), _path_decorations(svg, node, font_size))
    return True


def draw_text(svg: Any, node: Any, font_size: float) -> Any:
    # The text objects it draws, painted again in the paint-order of node
    stream, start = svg.stream, len(svg.stream.stream)
    plan = _planned(node)
    result = _draw_text(svg, node, font_size) if plan is None else _draw_planned(svg, node, font_size, plan)
    paint_order.split_text(stream, node, start)
    return result


def _draw_text(svg: Any, node: Any, font_size: float) -> Any:
    if FEATURES["fonts"]:
        node.attrib["font-family"] = f"{resolve_families(node.get('font-family') or '', svg.font_config)}, {FALLBACK}"
    if _draw_vertical(svg, node, font_size) or _draw_on_path(svg, node, font_size):
        return None
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
    _core.add_tree_pass(16, "invalid_rotate", drop_invalid_rotate)
    _core.add_tree_pass(17, "nested_tails", keep_nested_tails)
    _core.add_tree_pass(18, "trailing_space", drop_trailing_space)
    _core.add_before_draw(note_fonts)
    _core.add_restyler(ex_restyle)
    _core.add_restyler(anchor_restyle)
    _core.add_restyler(chunk_restyle)
    _core.add_before_draw(chunk_started)
    _core.add_after_draw(chunk_boxes)
    _core.add_after_draw(chunk_done)
    wp_draw_text.draw_first_line = recorded_draw_first_line
    for tag in TEXT_TAGS:
        if wp_svg.TAGS.get(tag) is _ORIGINAL_TEXT:
            wp_svg.TAGS[tag] = draw_text
    wp_svg.text = draw_text
    _core.track_groups()
