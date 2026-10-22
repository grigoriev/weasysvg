"""Each SVG image is one Form XObject: its BBox is the viewport, the page places it with Do."""

from __future__ import annotations

import base64
import re
from typing import Any

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
import pytest
import weasyprint
from helpers import close, pixel, streams, svg

from weasysvg import xobject

RED, WHITE = (255, 0, 0), (255, 255, 255)
DIAGRAM = svg('<rect x="10" y="10" width="180" height="80" fill="red"/>')
# Content past the viewport on every side
OVERFLOWING = svg('<rect x="-40" y="-40" width="300" height="200" fill="red"/>')


def data_url(document: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(document.encode()).decode()


def html(body: str, **options: Any) -> bytes:
    page = f"<!DOCTYPE html><html><head><style>@page{{size:600px 600px;margin:0}} body{{margin:0}} img,svg{{display:block}}</style></head><body>{body}</body></html>"
    pdf: bytes = weasyprint.HTML(string=page).write_pdf(uncompressed_pdf=True, **options)
    return pdf


def form_objects(pdf: bytes) -> list[tuple[str, str]]:
    """The dictionary and the content of each SVG form: a Form XObject that is no transparency group."""
    found = []
    for match in re.finditer(rb"\d+ 0 obj\s*<<(.*?)>>\s*stream\r?\n(.*?)\r?\nendstream", pdf, re.S):
        dictionary, content = (part.decode("latin-1") for part in match.groups())
        if "/Subtype /Form" in dictionary and "/Group" not in dictionary:
            found.append((dictionary, content))
    return found


def forms(pdf: bytes) -> list[str]:
    return [dictionary for dictionary, _ in form_objects(pdf)]


def bbox(form: str) -> list[float]:
    match = re.search(r"/BBox \[([^\]]*)\]", form)
    assert match is not None
    return [float(value) for value in match.group(1).split()]


def placements(pdf: bytes) -> list[tuple[float, ...]]:
    """The matrix of each form object PDFium finds on the first page, in page space, outermost first."""
    document = pdfium.PdfDocument(pdf)
    page = document[0]
    try:
        return [tuple(round(value, 3) for value in item.get_matrix().get()) for item in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_FORM])]
    finally:
        close(page, document)


def test_img_is_one_form_with_the_viewport_as_box() -> None:
    pdf = html(f'<img style="margin:10px 0 0 20px" src="{data_url(DIAGRAM)}">')
    found = forms(pdf)
    assert len(found) == 1
    assert bbox(found[0]) == [0, 0, 200, 100]
    # 0.75 pt per CSS px, y down from the top of the 450 pt page, moved to the place of the image
    assert placements(pdf) == [(0.75, 0, 0, -0.75, 15, 442.5)]
    # The form holds the drawing, the page only paints it
    [(_, content)] = form_objects(pdf)
    assert "180 80 re" in content
    assert sum("180 80 re" in stream for stream in streams(pdf)) == 1
    assert pixel(pdf, 30, 30) == RED


def test_box_follows_the_css_size() -> None:
    pdf = html(f'<img style="width:300px" src="{data_url(DIAGRAM)}">')
    [form] = forms(pdf)
    assert bbox(form) == [0, 0, 300, 150]


def test_inline_svg_is_one_form() -> None:
    pdf = html(f'<p style="margin:0;height:40px">x</p>{DIAGRAM}')
    found = forms(pdf)
    assert len(found) == 1
    assert bbox(found[0]) == [0, 0, 200, 100]
    assert placements(pdf) == [(0.75, 0, 0, -0.75, 0, 420)]


def test_same_svg_at_the_same_size_is_one_form() -> None:
    url = data_url(DIAGRAM)
    pdf = html(f'<img src="{url}"><img src="{url}"><img style="width:100px" src="{url}">')
    found = forms(pdf)
    # Two sizes, two forms; the first is painted twice
    assert sorted(bbox(form) for form in found) == [[0, 0, 100, 50], [0, 0, 200, 100]]
    assert len(placements(pdf)) == 3


def test_same_svg_on_two_pages_is_one_form() -> None:
    url = data_url(DIAGRAM)
    pdf = html(f'<img src="{url}"><img style="break-before:page" src="{url}">')
    assert len(forms(pdf)) == 1
    assert len(pdfium.PdfDocument(pdf)) == 2


def test_svg_in_an_svg_is_a_form_in_the_form() -> None:
    # An <image> of SVG draws through SVGImage too: its form lies inside the form of the outer SVG,
    # its box its own viewport, placed by the x, y and size of the <image>
    outer = svg(f'<image x="20" y="10" width="100" height="50" href="{data_url(DIAGRAM)}"/>')
    pdf = html(f'<img src="{data_url(outer)}">')
    assert sorted(bbox(form) for form in forms(pdf)) == [[0, 0, 200, 100], [0, 0, 200, 100]]
    outer_matrix, inner_matrix = placements(pdf)
    assert outer_matrix == (0.75, 0, 0, -0.75, 0, 450)
    assert inner_matrix == (0.5, 0, 0, 0.5, 20, 10)
    assert pixel(pdf, 30, 15) == RED


def test_nested_svg_element_is_no_form_of_its_own() -> None:
    # A nested <svg> element is part of the drawing, not an image
    nested = svg('<svg x="10" width="50" height="50"><rect width="100" height="100" fill="red"/></svg>')
    pdf = html(f'<img src="{data_url(nested)}">')
    assert len(forms(pdf)) == 1


def test_img_clips_at_its_viewport() -> None:
    pdf = html(f'<img style="margin:50px;overflow:visible" src="{data_url(OVERFLOWING)}">')
    # Chromium clips an image at its box even with overflow: visible
    assert pixel(pdf, 30, 30) == WHITE
    assert pixel(pdf, 45, 45) == RED


def test_background_clips_at_its_tile() -> None:
    body = f'<div style="width:400px;height:300px;background:url({data_url(OVERFLOWING)}) no-repeat 50px 50px"></div>'
    pdf = html(body)
    [form] = forms(pdf)
    assert bbox(form) == [0, 0, 200, 100]
    assert pixel(pdf, 30, 30) == WHITE
    assert pixel(pdf, 45, 45) == RED


def test_inline_svg_with_visible_overflow_still_overflows() -> None:
    # Chromium draws the overflow of an inline <svg> with overflow: visible: the box grows to let it through
    body = OVERFLOWING.replace("<svg ", '<svg style="margin:50px;overflow:visible" ', 1)
    pdf = html(body)
    [form] = forms(pdf)
    assert bbox(form) == [-10000, -10000, 10200, 10100]
    assert pixel(pdf, 15, 15) == RED
    # The default overflow of an inline <svg> is hidden: the box is the viewport
    pdf = html(OVERFLOWING.replace("<svg ", '<svg style="margin:50px" ', 1))
    assert bbox(forms(pdf)[0]) == [0, 0, 200, 100]
    assert pixel(pdf, 30, 30) == WHITE


@pytest.mark.parametrize("variant", ["pdf/ua-1", "pdf/a-2b", "pdf/a-2a"])
def test_tagged_pdf_marks_the_figure_around_the_form(variant: str) -> None:
    # The Figure of the image marks the Do; the form marks nothing, and the HTML of a foreignObject in it
    # adds no tags of its own: WeasyPrint failed on them, as no box of the page holds them
    body = '<foreignObject width="200" height="50"><p xmlns="http://www.w3.org/1999/xhtml">Hello</p></foreignObject>'
    diagram = svg(body)
    pdf = weasyprint.HTML(string=f'<html lang="en"><head><title>t</title></head><body><img alt="d" src="{data_url(diagram)}">{diagram}</body></html>').write_pdf(uncompressed_pdf=True, pdf_variant=variant)
    assert len(forms(pdf)) == 2
    for stream in streams(pdf):
        if "/x" in stream and " Do" in stream and "BDC" in stream:
            assert re.search(r"/Figure\s*<</MCID \d+>>\s*BDC((?!EMC).)*/x\d+ Do((?!BDC).)*EMC", stream, re.S)
    inside = [stream for stream in streams(pdf) if "Hello" not in stream and "BT" in stream]
    assert all("BDC" not in stream and "/Artifact" not in stream for stream in inside)


def test_form_names_stay_apart_from_reused_resources() -> None:
    # A form reused from a resources dictionary that no longer holds it is built again
    image = type("Image", (), {})()
    calls: list[Any] = []
    stream = pdfium_free_stream()
    xobject.draw_as_form(image, stream, 10, 10, None, calls.append)
    first = calls[-1]
    stream._resources["XObject"].clear()
    xobject.draw_as_form(image, stream, 10, 10, None, calls.append)
    assert calls[-1] is not first
    assert len(calls) == 2


def pdfium_free_stream() -> Any:
    """A WeasyPrint stream of its own, outside any document."""
    from weasyprint.pdf.stream import Stream

    return Stream(fonts={}, page_rectangle=(0, 0, 100, 100), resources={"XObject": {}, "ExtGState": {}, "Pattern": {}, "Shading": {}, "ColorSpace": None}, images={}, tags=None, color_profiles={}, output_intent=None)
