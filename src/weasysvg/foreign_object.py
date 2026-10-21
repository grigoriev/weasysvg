"""<foreignObject>: the XHTML inside is laid out by WeasyPrint and drawn into the SVG stream.

Touches:
- a tree pass in ``images.SVGImage.__init__``: the XHTML is serialized into an attribute, with
  wrappers for the SVG ancestors so that the selectors of the SVG stylesheet still match;
- ``svg.TAGS['foreignObject']``: all objects of one SVG are laid out in one document, one page each;
- ``layout.block.table_layout``: inside a foreignObject a table taller than its rows gives the
  extra height to the rows, as browsers do (Mermaid centers its labels that way);
- a UA stylesheet for the sub-document: what Chromium does differently in an SVG used as an image;
- ``formatting_structure.build.element_to_box``: inside a foreignObject an inline box with nothing in it and
  nothing drawn is dropped, so the white space around it collapses as CSS says and Chromium does (Mermaid
  writes icons whose font never loads);
- ``formatting_structure.build.marker_to_box``: inside a foreignObject an outside disc, circle or square
  marker is the shape Chromium paints, sized and placed from the ascent of the font, not a glyph.
"""

from __future__ import annotations

import html
from typing import Any
from xml.etree import ElementTree as ET

import weasyprint
from weasyprint import svg as wp_svg
from weasyprint.css.properties import Dimension
from weasyprint.draw import draw_page
from weasyprint.formatting_structure import boxes as wp_boxes
from weasyprint.formatting_structure import build as wp_build
from weasyprint.layout import block as wp_block
from weasyprint.layout import table as wp_table
from weasyprint.layout.table import add_top_padding
from weasyprint.svg.utils import size as wp_size
from weasyprint.text.ffi import FROM_UNITS, ffi, pango
from weasyprint.text.line_break import Layout

from . import _core, conditional
from .conditional import local_name
from .fonts import IN_FOREIGN_OBJECT

STASH = "data-weasyprint-foreign-html"
VOID = frozenset(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"])
INHERITED = ("font-family", "font-weight", "font-style", "font-variant", "color", "line-height", "direction", "letter-spacing", "word-spacing", "white-space", "text-align")
# The wrappers that stand for the SVG ancestors carry class and id for the selectors, never a box of their own
WRAPPER_CSS = (
    ".wp-fo-anc{display:block!important;width:100%!important;height:100%!important;margin:0!important;padding:0!important;"
    "border:none!important;background:none!important;box-shadow:none!important;transform:none!important;"
    "position:static!important;opacity:1!important;overflow:visible!important}"
)
# Marks where the inherited style goes. Private use characters, written as escapes: they never occur in
# diagram markup, and a plain "style" would also match the class and id values of the ancestors
FO_STYLE_SLOT = "\ue000style\ue000"
OVERFLOW_ROOM = 2000  # px of page beyond the box, where overflow is visible
# Chromium on Linux, in an SVG used as an image: :link never matches, th is centered, the root font is serif 16px
UA_EXTRA = ":link,:visited{color:inherit;text-decoration:none} th{text-align:center} html{font-family:serif;font-size:16px}"
BATCH = True

_UA_EXTRA_SHEET: weasyprint.CSS | None = None


# ---------------- stash the XHTML ----------------


def _serialize(element: ET.Element) -> str:
    tag = local_name(element.tag)
    if tag is None:  # comment or processing instruction
        return html.escape(element.tail or "")
    attributes = []
    for key, value in element.attrib.items():
        name = local_name(key)
        if key.startswith("{http://www.w3.org/2000/xmlns/}") or name is None:
            continue
        if name == "style":
            # draw.io aligns with "unsafe center", which WeasyPrint does not parse
            value = value.replace("unsafe ", "")
        attributes.append(f'{name}="{html.escape(value, quote=True)}"')
    start = f"<{tag}{' ' if attributes else ''}{' '.join(attributes)}>"
    if tag in VOID:
        return start + html.escape(element.tail or "")
    return f"{start}{_inner(element, tag)}</{tag}>" + html.escape(element.tail or "")


def _inner(element: ET.Element, tag: str) -> str:
    if tag == "style":
        # Raw text in HTML: entities are not decoded there, so only a closing tag is defused
        return (element.text or "").replace("</", "<\\/")
    return html.escape(element.text or "") + "".join(_serialize(child) for child in element)


def _wrapper(element: ET.Element, tag: str) -> str:
    classes = " ".join(filter(None, ["wp-fo-anc", element.get("class")]))
    identifier = element.get("id")
    id_attr = f' id="{html.escape(identifier, quote=True)}"' if identifier else ""
    return f'<{tag} class="{html.escape(classes, quote=True)}"{id_attr}>'


def _wrapper_tag(element: ET.Element) -> str:
    """The HTML tag for an SVG ancestor: its own name for type selectors, unless HTML gives that name a meaning."""
    tag = (local_name(element.tag) or "div").lower()
    return "div" if tag in ("svg", "a", "title", "style", "script", "image", "font", "switch") else tag


def _ancestors(element: ET.Element, parents: dict[ET.Element, ET.Element]) -> list[ET.Element]:
    """The ancestors of element, the outermost first."""
    chain = []
    ancestor = parents.get(element)
    while ancestor is not None:
        chain.append(ancestor)
        ancestor = parents.get(ancestor)
    chain.reverse()
    return chain


def _stash(element: ET.Element, chain: list[ET.Element], styles: str) -> None:
    """Move the XHTML of one foreignObject into an attribute, inside wrappers for its SVG ancestors."""
    opening = [_wrapper(a, _wrapper_tag(a)) for a in chain]
    closing = [f"</{_wrapper_tag(a)}>" for a in reversed(chain)]
    content = html.escape(element.text or "") + "".join(_serialize(child) for child in element)
    body = "".join(opening) + _wrapper(element, "foreignobject").replace(">", FO_STYLE_SLOT + ">", 1) + content + "</foreignobject>" + "".join(closing)
    element.set(STASH, body)
    element.set(STASH + "-css", styles)
    for child in list(element):
        element.remove(child)
    element.text = None


def stash_foreign_objects(root: ET.Element) -> None:
    parents = {child: parent for parent in root.iter() for child in parent}
    styles = "\n".join(el.text or "" for el in root.iter() if local_name(el.tag) == "style")
    for element in list(root.iter()):
        if local_name(element.tag) == "foreignObject":
            _stash(element, _ancestors(element, parents), styles)


# ---------------- lay out and draw ----------------


class _ForeignHTML(weasyprint.HTML):  # type: ignore[misc]  # WeasyPrint ships no type information
    def _ua_stylesheets(self, forms: bool = False) -> list[Any]:
        return [*super()._ua_stylesheets(forms), _UA_EXTRA_SHEET]


def _object_geometry(svg: Any, node: Any, font_size: float) -> tuple[float, float, float, float, bool, str]:
    x, y = svg.point(node.get("x"), node.get("y"), font_size)
    width, height = svg.point(node.get("width"), node.get("height"), font_size)
    visible = node.get("overflow") == "visible"
    # The cascade of the SVG already resolved what the HTML inherits from it. The font size is computed
    # here: the SVG cascade leaves it to each element
    inherited = f"font-size:{font_size}px;" + "".join(f"{name}:{node.get(name)};" for name in INHERITED if node.get(name))
    return x, y, width, height, visible, inherited


def _render(svg: Any, html_string: str) -> Any:
    font_config = svg.context.font_config if svg.context is not None else None
    token = IN_FOREIGN_OBJECT.set(True)
    try:
        return _ForeignHTML(string=html_string, base_url=svg.url, url_fetcher=svg.url_fetcher).render(font_config=font_config, presentational_hints=True)
    finally:
        IN_FOREIGN_OBJECT.reset(token)


def _object_html(node: Any, width: float, height: float, inherited: str, page: str | None = None) -> str:
    page_css = f"page:{page};break-before:page;" if page else ""
    body = node.get(STASH).replace(FO_STYLE_SLOT, f' style="{html.escape(inherited, quote=True)}"', 1)
    return f'<div class="wp-fo-box" style="{page_css}width:{width}px;height:{height}px">{body}</div>'


def _document(css: str, pages_css: str, bodies: str) -> str:
    # The stylesheet of the SVG is raw text here too: a </style> in a comment or a string must not close it
    css = css.replace("</", "<\\/")
    return f"<!DOCTYPE html><html><head><style>{pages_css}html,body{{margin:0;padding:0;background:transparent}}.wp-fo-box{{margin:0;padding:0;overflow:visible}}{css}\n{WRAPPER_CSS}</style></head><body>{bodies}</body></html>"


def _collect(svg: Any, node: Any, font_size: float, found: list[tuple[Any, float]]) -> None:
    if node.tag == "defs":
        return
    font_size = wp_size(node.get("font-size", "1em"), font_size, font_size)
    if node.tag == "foreignObject" and node.get(STASH):
        found.append((node, font_size))
    if node.display:
        for child in node:
            _collect(svg, child, font_size, found)


def _batch(svg: Any) -> dict[int, Any]:
    """Lay out every foreignObject of the SVG in one document, one page per object."""
    found: list[tuple[Any, float]] = []
    _collect(svg, svg.tree, wp_size("12pt"), found)
    if len(found) < 2:
        return {}
    pages_css, bodies, keys = [], [], []
    for i, (node, font_size) in enumerate(found):
        _, _, width, height, visible, inherited = _object_geometry(svg, node, font_size)
        if width <= 0 or height <= 0:
            continue
        room = OVERFLOW_ROOM if visible else 0
        pages_css.append(f"@page fo{i}{{size:{width + room}px {height + room}px;margin:0}}")
        bodies.append(_object_html(node, width, height, inherited, page=f"fo{i}"))
        keys.append(id(node._etree_node))
    css = found[0][0].get(STASH + "-css") or ""
    rendered = _render(svg, _document(css, "@page{size:10px 10px;margin:0}" + "".join(pages_css), "".join(bodies)))
    if len(rendered.pages) != len(keys):
        return {}
    return dict(zip(keys, rendered.pages, strict=True))


def foreign_object(svg: wp_svg.SVG, node: wp_svg.Node, font_size: float) -> None:
    if not node.get(STASH):
        return
    x, y, width, height, visible, inherited = _object_geometry(svg, node, font_size)
    if width <= 0 or height <= 0:
        return
    room = OVERFLOW_ROOM if visible else 0

    page = None
    if BATCH:
        if getattr(svg, "_fo_batch", None) is None:
            svg._fo_batch = _batch(svg)
        page = svg._fo_batch.get(id(node._etree_node))
    if page is None:
        document = _document(node.get(STASH + "-css") or "", f"@page{{size:{width + room}px {height + room}px;margin:0}}", _object_html(node, width, height, inherited))
        rendered = _render(svg, document)
        if not rendered.pages:
            return
        page = rendered.pages[0]

    stream = svg.stream
    stream.push_state()
    # A failure must not leave the shift and the clip of the object on the rest of the page
    try:
        stream.transform(e=x, f=y)
        if not visible:
            stream.rectangle(0, 0, width, height)
            stream.clip()
            stream.end()
        draw_page(page._page_box, stream)
    finally:
        stream.pop_state()


# ---------------- table height distribution ----------------
# WeasyPrint keeps the extra height of a table below its last row (layout.table.table_layout).


def _pad_cell(cell: Any, add: float) -> None:
    """The extra height of a row goes into the padding of a cell, on the side its vertical-align leaves free."""
    if cell.vertical_align == "middle":
        add_top_padding(cell, add / 2)
        cell.padding_bottom += add / 2
    elif cell.vertical_align == "bottom":
        add_top_padding(cell, add)
    else:
        cell.padding_bottom += add


def _grow_row(row: Any, add: float, shift: float) -> None:
    if shift:
        row.translate(dy=shift)
    row.height += add
    for cell in row.children:
        if cell.rowspan == 1:
            _pad_cell(cell, add)


def _grow_columns(table: Any, extra: float) -> None:
    for column_group in table.column_groups:
        column_group.height += extra
        for column in column_group.children:
            column.height += extra


def _distribute_table_height(table: Any) -> None:
    groups = [group for group in table.children if getattr(group, "is_header", False) is False and getattr(group, "is_footer", False) is False]
    rows = [row for group in groups for row in group.children]
    if not rows:
        return
    last = rows[-1]
    used = last.position_y + last.height - rows[0].position_y
    extra = table.height - used - (rows[0].position_y - table.content_box_y()) * 2
    if extra <= 0.01:
        return
    total = sum(row.height for row in rows)
    shift = 0.0
    for group in groups:
        group_shift = shift
        for row in group.children:
            add = extra * (row.height / total if total else 1 / len(rows))
            _grow_row(row, add, shift)
            shift += add
        group.height += shift - group_shift
    _grow_columns(table, extra)


_ORIGINAL_TABLE_LAYOUT = wp_table.table_layout


def _table_layout(*args: Any, **kwargs: Any) -> Any:
    result = _ORIGINAL_TABLE_LAYOUT(*args, **kwargs)
    table, resume_at = result[0], result[1]
    if IN_FOREIGN_OBJECT.get() and table is not None and resume_at is None and table.style["height"] != "auto":
        _distribute_table_height(table)
    return result


# ---------------- empty inline boxes ----------------

_ORIGINAL_ELEMENT_TO_BOX = wp_build.element_to_box
SIDES = ("top", "right", "bottom", "left")
# What an empty inline box brings to the height and baseline of its line, besides the metrics of its font
LINE_SHAPING = ("font_size", "line_height", "vertical_align")
METRIC_TOLERANCE = 0.01  # px


def _plain_empty(box: Any, parent: Any) -> bool:
    """Whether box is an inline box with nothing in it, nothing drawn, and the line box of its parent.

    White space ignores such a box. An auto margin of an inline box is 0. A box with an outline or a shadow is drawn, and
    a box whose font has other metrics, or of another line height or vertical alignment, still shapes the
    line: both stay.
    """
    if type(box) is not wp_boxes.InlineBox or box.children:
        return False
    style = box.style
    drawn = style["outline_width"] or style["box_shadow"] or any(style[f"border_{side}_width"] or style[f"padding_{side}"].value for side in SIDES)
    spaced = any(style[f"margin_{side}"] != "auto" and style[f"margin_{side}"].value for side in SIDES)
    if drawn or spaced or any(style[key] != parent.style[key] for key in LINE_SHAPING):
        return False
    # Another face, of another family or not, may bring other metrics: <i> and <b> mostly do not
    return all(abs(mine - theirs) < METRIC_TOLERANCE for mine, theirs in zip(_line_metrics(style), _line_metrics(parent.style), strict=True))


def _element_to_box(*args: Any, **kwargs: Any) -> Any:
    """element_to_box of WeasyPrint; inside a foreignObject without the empty inline boxes among the children.

    WeasyPrint keeps the space after such a box at the start of a line, in the line and in the width the
    content asks for. The element calls itself for its children: each level drops its own.
    """
    found = _ORIGINAL_ELEMENT_TO_BOX(*args, **kwargs)
    if IN_FOREIGN_OBJECT.get():
        for box in found:
            if isinstance(box, wp_boxes.ParentBox):
                box.children = [child for child in box.children if not _plain_empty(child, box)]
    return found


# ---------------- list markers ----------------

_ORIGINAL_MARKER_TO_BOX = wp_build.marker_to_box
SYMBOL_MARKERS = frozenset(("disc", "circle", "square"))
CORNERS = ("top_left", "top_right", "bottom_right", "bottom_left")
MARKER_PADDING = 7  # px, kCMarkerPaddingPx of Blink


def _line_metrics(style: Any) -> tuple[float, float]:
    """The ascent and descent of the first font of style, in px."""
    layout = Layout(style)
    try:
        layout.set_text("x")
        line, _ = layout.get_first_line()
        logical = ffi.new("PangoRectangle *")
        pango.pango_layout_line_get_extents(line, ffi.NULL, logical)
        return -logical.y * FROM_UNITS, (logical.height + logical.y) * FROM_UNITS
    finally:
        layout.deactivate()


def _ascent(style: Any) -> int:
    """The ascent of the first font of style, in whole px as Chromium counts it."""
    return round(_line_metrics(style)[0])


def _symbol_marker(marker: Any, kind: str) -> None:
    """Give an outside marker the shape Chromium paints for kind, in place of its glyph.

    Blink (ListMarker) works from the ascent A of the font: with offset = A * 2 // 3, the shape is
    (offset + 1) // 2 px wide, 1 px into a box offset + 8 px wide that ends where the text starts, and
    its top lies A - 3 * (A - offset) // 2 px above the baseline.
    """
    ascent = _ascent(marker.style)
    offset = ascent * 2 // 3
    width = (offset + 1) // 2
    shape = wp_boxes.InlineBlockBox.anonymous_from(marker, [])
    # The anonymous style is shared with the line box that will wrap the shape: change a copy
    style = shape.style = shape.style.copy()
    # An inline-block with no line sits on the baseline by its bottom margin edge
    # The shape lies 1 px inside the outer edge of the box: the left one, the right one in a right-to-left list
    outer, inner_side = ("margin_right", "margin_left") if style["direction"] == "rtl" else ("margin_left", "margin_right")
    style[outer] = Dimension(1, "px")
    style[inner_side] = Dimension(offset + MARKER_PADDING + 1 - 1 - width, "px")
    style["margin_bottom"] = Dimension(ascent - 3 * (ascent - offset) // 2 - width, "px")
    inner = width
    if kind == "circle":
        # Chromium strokes the ellipse 1 px wide
        inner = max(width - 2, 0)
        for side in SIDES:
            style[f"border_{side}_width"] = 1
            style[f"border_{side}_style"] = "solid"
            style[f"border_{side}_color"] = style["color"]
    else:
        style["background_color"] = style["color"]
    if kind != "square":
        for corner in CORNERS:
            style[f"border_{corner}_radius"] = (Dimension(50, "%"), Dimension(50, "%"))
    style["width"] = style["height"] = Dimension(inner, "px")
    marker.children = [shape]


def _marker_to_box(element: Any, state: Any, parent_style: Any, style_for: Any, *args: Any) -> Any:
    for marker in _ORIGINAL_MARKER_TO_BOX(element, state, parent_style, style_for, *args):
        # The marker style decides the type, as WeasyPrint reads it when it makes the glyph
        own = style_for(element, "marker")
        kind = (own if own is not None else parent_style)["list_style_type"]
        glyph = len(marker.children) == 1 and isinstance(marker.children[0], wp_boxes.TextBox)
        if IN_FOREIGN_OBJECT.get() and marker.is_outside_marker and kind in SYMBOL_MARKERS and glyph and (own is None or own["content"] in ("normal", "inhibit")):
            _symbol_marker(marker, kind)
        yield marker


def install() -> None:
    global _UA_EXTRA_SHEET
    if _UA_EXTRA_SHEET is None:
        _UA_EXTRA_SHEET = weasyprint.CSS(string=UA_EXTRA)
    _core.add_tree_pass(30, "foreign_object", stash_foreign_objects)
    # A <switch> may now pick its foreignObject over the fallback
    conditional.SUPPORTED_EXTENSIONS.add(conditional.XHTML_NS)
    wp_block.table_layout = _table_layout
    wp_build.marker_to_box = _marker_to_box
    wp_build.element_to_box = _element_to_box
    wp_svg.TAGS["foreignObject"] = foreign_object
