"""<foreignObject>: the XHTML inside is laid out by WeasyPrint and drawn into the SVG."""

from __future__ import annotations

import io
from types import SimpleNamespace
from typing import Any
from xml.etree import ElementTree as ET

import pytest
import weasyprint
from helpers import SVG_NS, XHTML_NS, RecordingStream, close, content, page_html, rasterize, render, svg, text_of
from PIL import Image, ImageChops
from weasyprint.urls import URLFetcher, URLFetcherResponse

from weasysvg import foreign_object
from weasysvg.foreign_object import STASH, stash_foreign_objects


def fo(html: str, x: int = 0, y: int = 0, width: int = 160, height: int = 60, extra: str = "") -> str:
    return f'<foreignObject x="{x}" y="{y}" width="{width}" height="{height}"{extra}><div xmlns="{XHTML_NS}">{html}</div></foreignObject>'


# ---------------- the tree pass ----------------


def stashed(body: str) -> ET.Element:
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    root = ET.fromstring(f'<svg xmlns="{SVG_NS}">{body}</svg>', parser=parser)
    stash_foreign_objects(root)
    element = next(e for e in root.iter() if e.tag.endswith("foreignObject"))
    return element


def test_stash_serializes_the_xhtml() -> None:
    element = stashed(
        '<style>.x{color:red}</style><g class="node" id="n1"><a><foreignObject width="10" height="10">'
        f'<div xmlns="{XHTML_NS}" xmlns:o="urn:o" style="justify-content: unsafe center" title="a&quot;b">'
        'one<br/>two<!-- c -->tail<img src="x.png"/>&amp;</div></foreignObject></a></g>'
    )
    html = element.get(STASH) or ""
    assert len(element) == 0
    assert element.text is None
    assert '<div class="wp-fo-anc"><g class="wp-fo-anc node" id="n1"><div class="wp-fo-anc">' in html
    assert 'style="justify-content: center"' in html
    assert 'title="a&quot;b"' in html
    assert "xmlns" not in html
    assert "one<br>two" in html
    assert "tail" in html
    assert '<img src="x.png">&amp;</div>' in html
    assert html.endswith("</foreignobject></div></g></div>")
    assert element.get(STASH + "-css") == ".x{color:red}"


def test_wrapper_tags() -> None:
    assert foreign_object._wrapper_tag(ET.Element(f"{{{SVG_NS}}}switch")) == "div"
    assert foreign_object._wrapper_tag(ET.Element(f"{{{SVG_NS}}}g")) == "g"
    assert foreign_object._wrapper_tag(ET.Element("Rect")) == "rect"


# ---------------- rendering ----------------


def test_label_text_is_drawn() -> None:
    pdf = render(svg(fo("Hello <b>label</b>")))
    assert text_of(pdf).split() == ["Hello", "label"]
    # Clipped to the object box, offset to its position
    assert "0 0 160 60 re\nW\nn" in content(pdf)


def test_overflow_visible_is_not_clipped() -> None:
    pdf = render(svg(fo("Wide label", x=5, y=5, extra=' overflow="visible"')))
    assert "Wide label" in text_of(pdf)
    assert "0 0 160 60 re\nW" not in content(pdf)


def test_empty_or_zero_sized_objects_draw_nothing() -> None:
    body = f'<foreignObject width="0" height="20"><div xmlns="{XHTML_NS}">Zero</div></foreignObject><foreignObject width="10" height="10"/>'
    assert text_of(render(svg(body))).strip() == ""


def test_several_objects_are_laid_out_in_one_document(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    original = foreign_object._render

    def counting(svg_: Any, html: str) -> Any:
        calls.append(html)
        return original(svg_, html)

    monkeypatch.setattr(foreign_object, "_render", counting)
    body = fo("First", y=0) + fo("Second", y=40) + fo("Zero", width=0) + f"<defs>{fo('Hidden')}</defs>"
    text = text_of(render(svg(body, height=120)))
    assert "First" in text
    assert "Second" in text
    assert "Hidden" not in text
    assert len(calls) == 1


def test_batch_falls_back_when_an_object_breaks_its_page(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    original = foreign_object._render

    def counting(svg_: Any, html: str) -> Any:
        calls.append(html)
        return original(svg_, html)

    monkeypatch.setattr(foreign_object, "_render", counting)
    body = fo('A<div style="break-before:page">B</div>') + fo("C", y=60)
    text = text_of(render(svg(body, height=140)))
    assert "C" in text
    # One batch that came back with an extra page, then one document per object
    assert len(calls) == 3


def test_single_object_without_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(foreign_object, "BATCH", False)
    pdf = render(svg(fo("One") + fo("Two", y=60), height=140))
    assert text_of(pdf).split() == ["One", "Two"]


def test_svg_styles_and_inherited_properties_reach_the_html() -> None:
    body = f'<style>.node .label{{color:#ff0000}}</style><g class="node" font-size="30px" fill="blue"><foreignObject width="200" height="60"><span xmlns="{XHTML_NS}" class="label">Red</span></foreignObject></g>'
    pdf = render(svg(body))
    assert "1 0 0 rg" in content(pdf)
    assert "/F" in pdf.decode("latin-1") or "Tf" in content(pdf)
    assert " 30 Tf" in content(pdf) or "22.5 Tf" in content(pdf)


def test_links_are_not_blue_and_th_is_centered() -> None:
    body = fo('<a href="https://example.com">link</a><table width="160"><tr><th>H</th></tr></table>', height=80)
    pdf = render(svg(body))
    assert "link" in text_of(pdf)
    assert "0 0 1 rg" not in content(pdf)


def test_fetches_shared_resources_once() -> None:
    png = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(png, "PNG")
    calls: list[str] = []

    default = URLFetcher()

    def fetcher(url: str) -> Any:
        if url.startswith("data:"):
            return default(url)
        calls.append(url)
        return URLFetcherResponse(url, png.getvalue(), {"Content-Type": "image/png"}, 200)

    image = '<img src="https://example.com/x.png" style="width:4px"/>'
    body = fo(image) + fo(image, y=60)
    weasyprint.HTML(string=page_html(svg(body, height=140)), url_fetcher=fetcher).write_pdf()
    assert calls.count("https://example.com/x.png") == 1


# ---------------- table height ----------------


def table(height: int, rows: str, head: str = "") -> str:
    return fo(f'<table style="height:{height}px;border-spacing:0" cellpadding="0">{head}<tbody>{rows}</tbody></table>', height=height + 20)


def text_y(pdf: bytes, word: str) -> float:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(pdf)
    page = document[0]
    textpage = page.get_textpage()
    searcher = textpage.search(word)
    try:
        found = searcher.get_next()
        assert found is not None, word
        left, bottom, right, top = textpage.get_charbox(found[0])
        return float(page.get_height() - top)
    finally:
        close(searcher, textpage, page, document)


def test_table_rows_share_the_extra_height() -> None:
    rows = '<tr><td style="vertical-align:middle">Mid</td></tr><tr><td style="vertical-align:bottom">Bot</td><td>Top</td></tr>'
    pdf = render(svg(table(200, rows), height=240))
    # In pt: the table is 150 pt tall. The first row grows to half of it and centers its label
    assert 25 < text_y(pdf, "Mid") < 50
    assert text_y(pdf, "Bot") > 120
    assert text_y(pdf, "Top") < text_y(pdf, "Bot")


def test_table_with_header_rowspan_and_columns() -> None:
    head = "<colgroup><col/><col/></colgroup><thead><tr><th>Head</th></tr></thead>"
    rows = '<tr><td rowspan="2">Span</td><td>A</td></tr><tr><td>B</td></tr>'
    pdf = render(svg(table(160, rows, head), height=200))
    text = text_of(pdf)
    assert "Head" in text
    assert "Span" in text


def test_table_that_fits_is_unchanged() -> None:
    pdf = render(svg(fo('<table style="height:5px"><tr><td>Fit</td></tr></table>') + fo("<table style='height:30px'></table>", y=60), height=140))
    assert "Fit" in text_of(pdf)


def test_serialize_skips_namespace_declarations() -> None:
    element = ET.Element(f"{{{XHTML_NS}}}span", {"{http://www.w3.org/2000/xmlns/}o": "urn:o", "class": "c"})
    element.text = "x"
    assert foreign_object._serialize(element) == '<span class="c">x</span>'


def test_hidden_group_and_unstashed_object() -> None:
    body = f'<g display="none">{fo("Hidden")}</g>' + fo("Shown", y=60) + fo("Also", y=100)
    text = text_of(render(svg(body, height=160)))
    assert "Hidden" not in text
    node = type("Node", (), {"get": {}.get})()
    # An object the tree pass never saw has nothing to draw: the call must not touch the SVG
    foreign_object.foreign_object(object(), node, 16)


def test_top_aligned_cell_grows_at_the_bottom() -> None:
    rows = '<tr><td style="vertical-align:top">Top</td></tr>'
    pdf = render(svg(table(100, rows), height=140))
    assert text_y(pdf, "Top") < 20


def test_install_twice_keeps_one_sheet() -> None:
    sheet = foreign_object._UA_EXTRA_SHEET
    foreign_object.install()
    assert foreign_object._UA_EXTRA_SHEET is sheet


def test_object_without_pages_draws_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(foreign_object, "BATCH", False)
    monkeypatch.setattr(foreign_object, "_render", lambda svg_, html: type("Document", (), {"pages": []})())
    assert text_of(render(svg(fo("Nothing")))).strip() == ""


def test_inherited_style_lands_on_the_object_not_an_ancestor() -> None:
    # Ancestor class and id values may contain "style"; the inherited declarations must not land in them
    root = ET.fromstring(f'<svg xmlns="{SVG_NS}"><g class="node-style" id="style-3"><foreignObject width="50" height="20"><div xmlns="{XHTML_NS}">Label</div></foreignObject></g></svg>')
    stash_foreign_objects(root)
    element = next(element for element in root.iter() if element.tag.endswith("foreignObject"))

    class Node:
        def get(self, name: str) -> str | None:
            return element.get(name)

    html = foreign_object._object_html(Node(), 50, 20, "font-size:30px;")
    assert 'class="wp-fo-anc node-style" id="style-3"' in html
    assert '<foreignobject class="wp-fo-anc" style="font-size:30px;">' in html


def test_a_failing_page_draw_restores_the_state(monkeypatch: pytest.MonkeyPatch) -> None:
    # A failure in draw_page must not leave the shift and the clip of the object on the rest of the page
    stream = RecordingStream()

    class Node:
        _etree_node = object()

        def get(self, name: str) -> str | None:
            return "<div>x</div>" if name == STASH else None

    node = Node()
    fake = SimpleNamespace(stream=stream, _fo_batch={id(node._etree_node): SimpleNamespace(_page_box=None)})
    monkeypatch.setattr(foreign_object, "_object_geometry", lambda *_args: (0, 0, 10, 10, False, ""))

    def failing(*_args: Any) -> None:
        raise RuntimeError("draw failed")

    monkeypatch.setattr(foreign_object, "draw_page", failing)
    with pytest.raises(RuntimeError):
        foreign_object.foreign_object(fake, node, 12)
    assert stream.depth == 0


def test_style_text_stays_raw() -> None:
    # <style> is raw text in HTML: entities are not decoded there, so quotes and > must stay as they are
    style = ET.Element(f"{{{XHTML_NS}}}style")
    style.text = 'p{font-family:"Open Sans"} .a > .b{color:red} </style><b>'
    html = foreign_object._serialize(style)
    assert 'font-family:"Open Sans"' in html
    assert ".a > .b" in html
    # Only a closing tag inside the text is defused
    assert html.count("</style>") == 1


def test_svg_stylesheet_cannot_close_the_html_style() -> None:
    # A comment or a string in the SVG stylesheet may hold </style>: the sub-document keeps one stylesheet
    document = foreign_object._document("p{color:red} /* </style><p>injected</p> */", "", "<p>body</p>")
    assert document.count("</style>") == 1
    assert "<p>injected</p>" not in document.split("</style>", 1)[1]


# ---------------- list markers ----------------

MARKER_SCALE = 8  # px per CSS px


def ink_box(image: Image.Image, color: tuple[int, int, int], columns: slice) -> tuple[float, float, float, float]:
    """The box of the pixels near color within columns, in CSS px: left, top, right, bottom.

    PIL only: numpy is no dependency of the tests before Python 3.12.
    """
    start = columns.start or 0
    part = image.crop((start, 0, columns.stop if columns.stop is not None else image.width, image.height))
    red, green, blue = ImageChops.difference(part, Image.new("RGB", part.size, color)).split()
    near = ImageChops.lighter(ImageChops.lighter(red, green), blue).point(lambda value: 255 if value < 100 else 0)
    box = near.getbbox()
    assert box is not None, f"no pixel near {color}"
    return ((start + box[0]) / MARKER_SCALE, box[1] / MARKER_SCALE, (start + box[2]) / MARKER_SCALE, box[3] / MARKER_SCALE)


def marker_and_text(style: str, item: str = "I") -> tuple[tuple[float, ...], tuple[float, ...], Image.Image]:
    html = f"<ul style=\"margin:0;padding-left:40px;font:16px 'DejaVu Sans';color:#0000ff;{style}\"><li>{item}</li></ul>"
    image = rasterize(render(svg(fo(html, width=200, height=40), width=200, height=40)), MARKER_SCALE / 0.75)
    left = int(image.width * 0)  # the page starts at the SVG
    text = ink_box(image, (0, 0, 255), slice(left + 38 * MARKER_SCALE, None))
    marker = ink_box(image, (0, 0, 255), slice(left, left + 38 * MARKER_SCALE))
    return marker, text, image


def test_a_disc_marker_is_the_shape_of_chromium() -> None:
    # Measured in Chromium with DejaVu Sans at 16px, ascent 15: a disc 5 px wide, 18.5 px left of the I and
    # 8 px above its baseline. WeasyPrint draws the bullet glyph 9 px from the text instead
    marker, text, _ = marker_and_text("")
    assert marker[0] == pytest.approx(text[0] - 18.5, abs=0.25)
    assert marker[2] - marker[0] == pytest.approx(5, abs=0.25)
    assert marker[1] == pytest.approx(text[3] - 8, abs=0.25)
    assert marker[3] - marker[1] == pytest.approx(5, abs=0.25)


@pytest.mark.parametrize(("kind", "hollow"), [("circle", True), ("square", False)])
def test_circle_and_square_markers_are_shapes(kind: str, hollow: bool) -> None:
    marker, text, image = marker_and_text(f"list-style-type:{kind}")
    assert marker[0] == pytest.approx(text[0] - 18.5, abs=0.25)
    center = image.getpixel((int((marker[0] + marker[2]) / 2 * MARKER_SCALE), int((marker[1] + marker[3]) / 2 * MARKER_SCALE)))
    assert (center == (255, 255, 255)) == hollow


@pytest.mark.parametrize("style", ["list-style-type:decimal", "list-style-position:inside"])
def test_other_markers_stay_text(style: str) -> None:
    pdf = render(svg(fo(f'<ul style="{style}"><li>Item</li></ul>', width=200, height=40), width=200, height=40))
    assert "Item" in text_of(pdf)
    assert "1." in text_of(pdf) or "\u2022" in text_of(pdf)


def test_the_type_of_the_marker_itself_decides() -> None:
    # A ::marker of its own type wins over the type of the item: a number stays a number
    body = "<style>li::marker{list-style-type:decimal}</style>" + fo("<ul><li>Item</li></ul>", width=200, height=40)
    assert "1." in text_of(render(svg(body, width=200, height=40)))


def test_a_marker_of_a_right_to_left_list_is_mirrored() -> None:
    # Measured in Chromium: the disc lies 1 px inside the outer edge of its box, 13.625 px right of the I
    html = "<ul style=\"margin:0;padding:0 40px 0 0;direction:rtl;font:16px 'DejaVu Sans';color:#0000ff\"><li>I</li></ul>"
    image = rasterize(render(svg(fo(html, width=200, height=40), width=200, height=40)), MARKER_SCALE / 0.75)
    text = ink_box(image, (0, 0, 255), slice(0, 160 * MARKER_SCALE))
    marker = ink_box(image, (0, 0, 255), slice(160 * MARKER_SCALE, None))
    assert marker[0] == pytest.approx(text[2] + 13.625, abs=0.25)
    assert marker[2] - marker[0] == pytest.approx(5, abs=0.25)


@pytest.mark.parametrize(("content", "shaped"), [("normal", True), ([("string", "-")], False)])
def test_a_marker_with_content_stays_its_content(monkeypatch: pytest.MonkeyPatch, content: Any, shaped: bool) -> None:
    # Through the hook alone: WeasyPrint 70 itself fails to lay out a ::marker with content
    from weasyprint.formatting_structure import boxes

    from weasysvg.fonts import IN_FOREIGN_OBJECT

    glyph = object.__new__(boxes.TextBox)
    marker = SimpleNamespace(is_outside_marker=True, children=[glyph])
    monkeypatch.setattr(foreign_object, "_ORIGINAL_MARKER_TO_BOX", lambda *_args: iter([marker]))
    shapes: list[Any] = []
    monkeypatch.setattr(foreign_object, "_symbol_marker", lambda box, kind: shapes.append(kind))
    style = {"content": content, "list_style_type": "disc"}
    token = IN_FOREIGN_OBJECT.set(True)
    try:
        assert list(foreign_object._marker_to_box(None, None, style, lambda *_args: style)) == [marker]
    finally:
        IN_FOREIGN_OBJECT.reset(token)
    assert shapes == (["disc"] if shaped else [])


def test_a_marker_image_stays_an_image() -> None:
    # list-style-image draws the image: red here, where a disc would take the blue of the text
    square = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='6' height='6'%3E%3Crect width='6' height='6' fill='red'/%3E%3C/svg%3E"
    html = f"<ul style=\"margin:0;padding-left:40px;font:16px 'DejaVu Sans';color:#0000ff;list-style-image:url(&quot;{square}&quot;)\"><li>I</li></ul>"
    image = rasterize(render(svg(fo(html, width=200, height=40), width=200, height=40)), MARKER_SCALE / 0.75)
    assert ink_box(image, (255, 0, 0), slice(0, 38 * MARKER_SCALE))


def first_character_x(body: str) -> float:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(render(svg(fo(body, width=200, height=40), width=200, height=40)))
    page = document[0]
    textpage = page.get_textpage()
    try:
        boxes = [textpage.get_charbox(index) for index in range(textpage.count_chars()) if textpage.get_text_range(index, 1).strip()]
        return float(boxes[0][0])
    finally:
        close(textpage, page, document)


@pytest.mark.parametrize("icon", ['<i class="fa fa-car"></i>', "<i></i><b></b>", "<span><i></i></span>"])
def test_a_space_after_an_empty_inline_starts_no_line(icon: str) -> None:
    # Mermaid writes an icon its font never loads: Chromium drops the space after it at the start of the line
    style = "margin:0;font:16px 'DejaVu Sans'"
    assert first_character_x(f'<p style="{style}">{icon} Car</p>') == pytest.approx(first_character_x(f'<p style="{style}">Car</p>'))


def test_a_label_sized_to_its_content_ignores_the_space_too() -> None:
    # Mermaid sizes its labels by a table cell: its width, from the content, must not count the space either
    def label(inner: str) -> str:
        return f'<div style="display: table-cell; white-space: nowrap; text-align: center; font:16px \'DejaVu Sans\'"><p style="margin:0">{inner}</p></div>'

    assert first_character_x(label("<i></i> Car")) == pytest.approx(first_character_x(label("Car")))


def test_an_empty_inline_with_auto_margins_is_dropped_too() -> None:
    style = "margin:0;font:16px 'DejaVu Sans'"
    assert first_character_x(f'<p style="{style}"><i style="margin-left:auto"></i> Car</p>') == pytest.approx(first_character_x(f'<p style="{style}">Car</p>'))


def first_character_top(body: str) -> float:
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(render(svg(fo(body, width=200, height=80), width=200, height=80)))
    page = document[0]
    textpage = page.get_textpage()
    try:
        return float(textpage.get_charbox(next(index for index in range(textpage.count_chars()) if textpage.get_text_range(index, 1).strip()))[3])
    finally:
        close(textpage, page, document)


def test_an_empty_inline_that_sizes_the_line_stays() -> None:
    # Its larger font makes the line taller, in Chromium too: the text moves down
    style = "margin:0;font:16px 'DejaVu Sans'"
    assert first_character_top(f'<p style="{style}"><i style="font-size:40px"></i>Car</p>') < first_character_top(f'<p style="{style}">Car</p>') - 5


@pytest.mark.parametrize("own", ["padding-left:4px", "padding-top:4px", "border-bottom:1px solid red", "outline:2px solid red", "box-shadow:2px 2px 0 4px red", "font-family:'Liberation Serif'"])
def test_an_empty_inline_that_shows_keeps_the_space(own: str) -> None:
    # A box drawn, or with a font of its own that sets the line metrics, stays: the space after it too
    style = "margin:0;font:16px 'DejaVu Sans'"
    assert first_character_x(f'<p style="{style}"><i style="{own}"></i> Car</p>') > first_character_x(f'<p style="{style}">Car</p>') + 3
