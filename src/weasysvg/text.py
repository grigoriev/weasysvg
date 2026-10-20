"""SVG text.

Touches:
- ``svg.TAGS`` text entries and the global ``svg.text``, with one replacement ``draw_text``:
  font family resolved as Chromium does (fonts.py), dominant-baseline from real font metrics,
  text-decoration placed as in Chromium. ``draw_node`` recognizes text nodes by that global, so both change together.
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
from types import SimpleNamespace
from typing import Any
from xml.etree import ElementTree as ET

from weasyprint import svg as wp_svg
from weasyprint.css.properties import INITIAL_VALUES
from weasyprint.matrix import Matrix
from weasyprint.svg.bounding_box import EMPTY_BOUNDING_BOX, extend_bounding_box, is_valid_bounding_box
from weasyprint.svg.utils import normalize, size
from weasyprint.text.ffi import FROM_UNITS, TO_UNITS, ffi, pango
from weasyprint.text.fonts import FontConfiguration
from weasyprint.text.line_break import Layout

from . import _core, glyphs, ink, textpath, vertical
from .conditional import local_name
from .fonts import FALLBACK, resolve_families

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
# The lines that skip the ink of the glyphs they cross, as in Chromium (text-decoration-skip-ink: auto)
SKIP_INK = frozenset(("underline", "overline"))
GLYPHS = "_weasysvg_glyphs"
FEATURES = {"fonts": True, "baseline": True, "decoration": True}
DEFAULT_FONT_PX = 16.0  # px, the 12pt WeasyPrint draws an SVG with

_ORIGINAL_CASCADE = wp_svg.Node.cascade
_ORIGINAL_TEXT = wp_svg.TAGS["text"]


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
    if node.tag not in TEXT_TAGS_WITH_CHUNKS:
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


def chromium_lines(lines: list[str], font_size: float, ascent: float) -> list[tuple[float, float]]:
    """Top, below the baseline, and thickness of each decoration line, as Chromium places them.

    Read from the PDF Chromium prints, for five fonts at sizes from 8 to 60 px: every line is font-size / 10
    thick, one px at least. The places follow font-size / 10 itself, below the minimum too. The underline
    starts below the baseline by half of it, rounded up, whatever underline the font declares. The
    overline ends above the rounded ascent by it, truncated. The line-through is centered a third of the
    rounded ascent up.
    """
    tenth = font_size / 10
    thickness = max(1.0, tenth)
    rounded = math.floor(ascent + 0.5)
    out = []
    if "underline" in lines:
        out.append((float(math.ceil(tenth / 2)), thickness))
    if "overline" in lines:
        out.append((-float(rounded + math.trunc(tenth)), thickness))
    if "line-through" in lines:
        out.append((-rounded / 3 - tenth / 2, thickness))
    return out


def _lines_of(svg: Any, lines: list[str], font_size: float, layout: Any) -> list[tuple[float, float]]:
    """chromium_lines in user units: Chromium applies its minimum and its rounding to the scaled font."""
    scale = _core.text_scale(svg)
    found = chromium_lines(lines, font_size * scale, layout.ascent * scale)
    return [(top / scale, thickness / scale) for top, thickness in found]


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
    found = _lines_of(svg, lines, font_size, layout)
    layout.deactivate()
    # The glyphs _draw_run placed: text WeasyPrint lays out character by character skips no ink
    glyphs = node.__dict__.pop(GLYPHS, [])
    dilation_limit = ink.MAX_DILATION / _core.text_scale(svg)
    rects = []
    for kind, (top, thickness) in zip(lines, found, strict=True):
        cuts = ink.intercepts(glyphs, top, top + thickness) if kind in SKIP_INK else []
        rects += [(left, baseline + top, right - left, thickness) for left, right in ink.skipped(x, x + width, cuts, min(thickness, dilation_limit))]
    _draw_lines(svg, node, font_size, rects)


def _draw_lines(svg: Any, node: Any, font_size: float, rects: list[tuple[float, float, float, float]]) -> None:
    """Fill the rectangles of the lines in the paint of the node."""
    if not rects:
        return  # every piece lies under ink: a paint operator needs a path before it
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
# Cursive scripts take no letter-spacing (css-text-3): Arabic, Syriac, N'Ko, Mandaic, Mongolian,
# Hanifi Rohingya, Adlam and the Arabic presentation forms
CURSIVE = ((0x0600, 0x08FF), (0x1800, 0x18AF), (0x10D00, 0x10D3F), (0x1E900, 0x1E95F), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF))


def _cursive(character: str) -> bool:
    code = ord(character)
    return any(low <= code <= high for low, high in CURSIVE)


def _track(layout: Any, spacing: float) -> float:
    """Letter-spacing on the characters outside cursive scripts only; return the new line width.

    Pango spaces every character alike, which tears Arabic letters apart. Chromium spaces the rest, the
    spaces between Arabic words included.
    """
    attributes = pango.pango_attr_list_new()
    start = 0
    for character in layout.text:
        end = start + len(character.encode())
        if not _cursive(character):
            attribute = pango.pango_attr_letter_spacing_new(int(spacing * TO_UNITS))
            attribute.start_index, attribute.end_index = start, end
            pango.pango_attr_list_change(attributes, attribute)
        start = end
    pango.pango_layout_set_attributes(layout.layout, attributes)
    pango.pango_attr_list_unref(attributes)
    line, _ = layout.get_first_line()
    logical = ffi.new(PANGO_RECTANGLE)
    pango.pango_layout_line_get_extents(line, ffi.NULL, logical)
    width: float = logical.width * FROM_UNITS
    return width


def _whole_run(node: Any) -> bool:
    """A run Pango can lay out whole: per-character positions, rotate and textLength need WeasyPrint."""
    if not node.text or any(node.get(name) for name in ("rotate", "textLength", "display-anchor")):
        return False
    return all(len(normalize(node.attrib.get(name, "")).split()) <= 1 for name in POSITIONS)


def _position(node: Any, name: str, font_size: float, reference: float) -> float | None:
    values = normalize(node.attrib.get(name, "")).split()
    return size(values[0], font_size, reference) if values else None


def _draw_run(svg: Any, node: Any, font_size: float) -> None:
    """The text of the node laid out and drawn as one run, positioned as text() of WeasyPrint does."""
    from weasyprint.draw.text import draw_emojis, draw_first_line
    from weasyprint.text.line_break import split_first_line

    style = _style(svg, node, font_size)
    if node.get("direction") in ("ltr", "rtl"):
        style["direction"] = node.get("direction")
    letter_spacing = svg.length(node.get("letter-spacing"), font_size)
    tracked = bool(letter_spacing) and any(_cursive(character) for character in node.text)
    if letter_spacing and not tracked:
        style["letter_spacing"] = letter_spacing
    layout, _, _, width, height, baseline = split_first_line(node.text, style, svg.context, float("inf"), 0)
    if tracked:
        # split_first_line hands the layout back deactivated
        layout.reactivate(style)
        width = _track(layout, letter_spacing)
        layout.deactivate()

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
        # Where each glyph lies, for a decoration line that skips its ink: only such a line reads them
        if FEATURES["decoration"] and SKIP_INK.intersection((node.get("text-decoration") or "").split()):
            node.__dict__[GLYPHS] = ink.run_glyphs(layout.get_first_line()[0], x_position)
        svg.stream.end_text()
    finally:
        svg.stream.pop_state()
    draw_emojis(svg.stream, style, x, y, emojis)


def _draw_decorated(svg: Any, node: Any, font_size: float) -> Any:
    if _whole_run(node):
        _draw_run(svg, node, font_size)
        result = None
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


def _character_ink(svg: Any, node: Any, font_size: float) -> dict[str, list[ink.Glyph]]:
    """The glyphs of each character of node laid out alone, as textpath.py draws them, its baseline at 0."""
    from weasyprint.text.line_break import split_first_line

    style = _style(svg, node, font_size)
    style["font_family"] = [family.strip() for family in _family(svg, node).split(",")]
    out = {}
    for character in {glyphs.in_context(node.text, index) for index in range(len(node.text or ""))}:
        layout = split_first_line(character, style, svg.context, float("inf"), 0)[0]
        # split_first_line hands the layout back deactivated
        layout.reactivate(style)
        out[character] = ink.run_glyphs(layout.get_first_line()[0], 0)
        layout.deactivate()
    return out


def _path_decorations(svg: Any, node: Any, font_size: float) -> list[tuple[float, float, float | None]]:
    """Top and thickness of each decoration line, below the baseline positive, and how far it skips ink.

    None for a line-through, which skips no ink.
    """
    lines = [line for line in DECORATION_LINES if line in (node.get("text-decoration") or "").split()]
    if not lines:
        return []
    style = _style(svg, node, font_size)
    # Layout measures the lines it is asked for only
    style["text_decoration_line"] = set(lines)
    layout = Layout(style)
    layout.set_text(node.text or "x")
    found = _lines_of(svg, lines, font_size, layout)
    layout.deactivate()
    limit = ink.MAX_DILATION / _core.text_scale(svg)
    return [(top, thickness, min(thickness, limit) if kind in SKIP_INK else None) for kind, (top, thickness) in zip(lines, found, strict=True)]


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
    decorations = _path_decorations(svg, node, font_size)
    skipping = any(dilation is not None for _, _, dilation in decorations)
    characters = _character_ink(svg, node, font_size) if skipping else {}
    textpath.draw(svg, node, font_size, state, _style(svg, node, font_size), _advances(svg, node, font_size), decorations, characters)
    return True


def draw_text(svg: Any, node: Any, font_size: float) -> Any:
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
    _core.add_before_draw(note_fonts)
    _core.add_restyler(ex_restyle)
    _core.add_restyler(anchor_restyle)
    _core.add_before_draw(chunk_started)
    _core.add_after_draw(chunk_boxes)
    for tag in TEXT_TAGS:
        if wp_svg.TAGS.get(tag) is _ORIGINAL_TEXT:
            wp_svg.TAGS[tag] = draw_text
    wp_svg.text = draw_text
    _core.track_groups()
