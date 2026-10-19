"""<foreignObject>: the XHTML inside is laid out by WeasyPrint and drawn into the SVG."""

from __future__ import annotations

import io
from typing import Any
from xml.etree import ElementTree as ET

import pytest
import weasyprint
from helpers import SVG_NS, XHTML_NS, content, page_html, render, svg, text_of
from PIL import Image
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
    try:
        page = document[0]
        textpage = page.get_textpage()
        searcher = textpage.search(word)
        found = searcher.get_next()
        assert found is not None, word
        left, bottom, right, top = textpage.get_charbox(found[0])
        return float(page.get_height() - top)
    finally:
        document.close()


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
