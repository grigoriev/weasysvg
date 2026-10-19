"""The resvg fallback: the standalone document, the pixel size, failures and the cache."""

from __future__ import annotations

import io
import sys
from typing import Any, cast
from xml.etree import ElementTree as ET

import helpers
import pytest
from helpers import render, svg
from PIL import Image

from weasysvg import raster

BLUR = '<filter id="f"><feGaussianBlur stdDeviation="2"/></filter>'


class Recorder:
    """A resvg stand-in: records each document and returns a red PNG of the asked size."""

    def __init__(self) -> None:
        self.documents: list[str] = []
        self.sizes: list[tuple[int, int]] = []

    def svg_to_bytes(self, svg_string: str, width: int, height: int, **options: Any) -> bytes:
        self.documents.append(svg_string)
        self.sizes.append((width, height))
        png = io.BytesIO()
        Image.new("RGBA", (width, height), (255, 0, 0, 255)).save(png, "PNG")
        return png.getvalue()


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    fake = Recorder()
    monkeypatch.setattr(raster, "_RESVG", fake)
    return fake


def parse(document: str) -> ET.Element:
    return ET.fromstring(document)


def local(element: ET.Element) -> list[str]:
    return [raster._local(child.tag) for child in element.iter()]


# ---------------- availability ----------------


def test_missing_resvg_warns_once(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setattr(raster, "_RESVG", None)
    monkeypatch.setitem(sys.modules, "resvg_py", None)
    assert raster.available() is False
    assert raster.available() is False
    assert caplog.text.count("resvg_py is not installed") == 1


def test_real_resvg_is_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(raster, "_RESVG", None)
    assert raster.available() is True


def test_install_can_disable_the_raster(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(raster, "_RESVG", None)
    monkeypatch.setitem(raster.SETTINGS, "scale", raster.SETTINGS["scale"])
    raster.install(scale=3.0, enabled=False)
    assert raster.SETTINGS["scale"] == 3.0
    assert raster.available() is False


# ---------------- the standalone document ----------------


def test_document_keeps_ancestors_without_their_effects(recorder: Recorder) -> None:
    body = (
        "<style>.a{fill:red}</style>"
        f"<defs>{BLUR}</defs>"
        '<g id="outer" class="o" transform="translate(5 5)" opacity="0.9" style="opacity:0.9;stroke:blue"><style>.b{}</style>'
        '<rect id="sibling" width="5" height="5"/><linearGradient id="g"/>'
        '<g id="holder"><linearGradient id="inner"/></g>'
        '<svg x="10" y="10" width="50" height="50" viewBox="0 0 10 10"><rect id="target" class="a" width="8" height="8" fill="url(#inner)" style="opacity:0.5" filter="url(#f)"/></svg>'
        "</g>"
    )
    render(svg(body, extra=' font-family="Arial" style="color:red"'))
    document = parse(recorder.documents[0])
    assert document.get("font-family") == "Arial"
    assert document.get("style") is None
    tags = local(document)
    assert tags.count("style") == 2
    target = next(element for element in document.iter() if element.get("id") == "target")
    assert "filter:url(#__svg_ext_filter)" in (target.get("style") or "")
    assert "opacity:0.5" not in (target.get("style") or "")
    outer = next(element for element in document.iter() if element.get("id") == "outer")
    assert outer.get("transform") is None
    assert "stroke:blue" in (outer.get("style") or "")
    ids = [element.get("id") for element in document.iter() if element.get("id")]
    # The referenced gradient comes with its holder; an unrelated sibling shape does not
    assert "inner" in ids
    assert "sibling" not in ids


def test_document_for_the_root(recorder: Recorder) -> None:
    body = f'<defs>{BLUR}</defs><style>rect{{fill:red}}</style><rect x="20" y="20" width="60" height="40"/>'
    render(svg(body, extra=' filter="url(#f)" class="root" viewBox="0 0 200 100"'))
    document = parse(recorder.documents[0])
    wrapper = document[1]
    assert raster._local(wrapper.tag) == "g"
    assert wrapper.get("class") == "root"
    assert "filter:url(#f)" in (wrapper[0].get("style") or "")
    assert "style" not in [raster._local(child.tag) for child in wrapper[0]]


class FakeNode:
    def __init__(self, element: ET.Element, inherited: dict[str, str]) -> None:
        self._etree_node = element
        self._inherited = inherited

    def get(self, key: str, default: Any = None) -> Any:
        return self._inherited.get(key, default)


class FakeSVG:
    def __init__(self, root: ET.Element) -> None:
        self.tree = FakeNode(root, {})


def test_document_for_an_element_outside_the_tree() -> None:
    root = ET.fromstring(f'<svg xmlns="{raster.SVG_NS}"><linearGradient id="g" href="#base"/><linearGradient id="base"/></svg>')
    element = ET.fromstring(f'<rect xmlns="{raster.SVG_NS}" fill="url(#g)" stroke="blue"/>')
    node = FakeNode(element, {"stroke-width": "3", "stroke": "red", "fill": "url(#g)"})
    document = parse(raster.build_document(FakeSVG(root), node, (0, 0, 10, 10), (20, 20), "url(#f)"))
    shape = document[-1]
    # The cascade of WeasyPrint stands in for the ancestors, the own attributes win
    assert shape.get("stroke-width") == "3"
    assert shape.get("stroke") == "blue"
    ids = [element.get("id") for element in document.iter() if element.get("id")]
    assert sorted(str(name) for name in ids) == ["base", "g"]


def test_same_element_twice_is_rendered_once(recorder: Recorder) -> None:
    body = f'<defs>{BLUR}<rect id="shape" width="40" height="40" fill="red" filter="url(#f)"/></defs><use href="#shape"/><use href="#shape"/>'
    render(svg(body))
    assert len(recorder.documents) == 1


def test_references_in_styles() -> None:
    element = ET.fromstring('<g xmlns:xlink="http://www.w3.org/1999/xlink"><use xlink:href="#a"/><style>.x{fill:url(#b)}</style><rect fill="url(\'#c\')" href="other"/></g>')
    assert raster._references(element) == {"a", "b", "c"}
    ids = {"a": ET.fromstring('<rect fill="url(#a)"/>')}
    assert len(raster._referenced({"a", "missing"}, ids)) == 1


def test_shallow_strips_style() -> None:
    element = ET.Element("g", {"style": "opacity:0.5;fill:red", "opacity": "1"})
    copy = raster._shallow(element, drop=("opacity",))
    assert copy.attrib == {"style": "fill:red"}
    assert raster._shallow(ET.Element("g", {"style": "opacity:1"}), drop=("opacity",)).attrib == {}


# ---------------- pixel size ----------------


def test_raster_inside_a_group_counts_the_root_scale(recorder: Recorder) -> None:
    body = f'<defs>{BLUR}</defs><g opacity="0.5"><rect x="10" y="10" width="40" height="40" fill="red" filter="url(#f)"/></g>'
    render(svg(body, extra=' viewBox="0 0 100 50"'))
    # 48 user units of filter region, 2 px per unit of the viewBox scale, times the raster scale of 2
    assert recorder.sizes[0] == (192, 192)


def test_raster_is_capped(recorder: Recorder, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setitem(raster.SETTINGS, "max_side", 50)
    render(svg(f'<defs>{BLUR}</defs><rect x="10" y="10" width="40" height="40" fill="red" filter="url(#f)"/>'))
    assert max(recorder.sizes[0]) == 50
    assert "exceeds the cap" in caplog.text


def test_empty_region_is_not_rendered(recorder: Recorder) -> None:
    assert raster.render(object(), object(), (0, 0, 0, 10), "url(#x)") is None
    assert recorder.documents == []


def test_interrupt_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    def interrupt(*args: Any, **kwargs: Any) -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr(raster, "_RESVG", Recorder())
    monkeypatch.setattr(raster, "build_document", interrupt)
    stream = type("Stream", (), {"ctm": type("Matrix", (), {"determinant": 1.0})()})()
    fake = type("SVG", (), {"stream": stream, "_svg_ext_base": (stream, 1.0)})()
    node = FakeNode(ET.Element("rect"), {})
    with pytest.raises(KeyboardInterrupt):
        raster.render(fake, node, (0, 0, 10, 10), "url(#f)")


# ---------------- elements drawn through <use> ----------------

WIDE_BLUR = '<filter id="b" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2"/></filter>'


def colors_of(pdf: bytes) -> set[tuple[int, int, int]]:
    """The strongly colored pixels of the first page, reduced to their dominant channel."""
    image = helpers.rasterize(pdf, 2)
    found = set()
    pixels = cast("list[tuple[int, int, int]]", list(image.get_flattened_data()))
    for red, green, blue in pixels:
        if max(red, green, blue) - min(red, green, blue) > 150:
            found.add((int(red > 128), int(green > 128), int(blue > 128)))
    return found


def test_a_filtered_element_in_defs_is_drawn_through_use() -> None:
    # resvg draws nothing inside <defs>: the element must leave it, or it vanishes from the PDF
    document = svg(f'<defs>{WIDE_BLUR}<rect id="r" width="60" height="40" fill="red" filter="url(#b)"/></defs><use href="#r" x="20" y="20"/>', height=100)
    assert (1, 0, 0) in colors_of(render(document))


def test_each_use_keeps_the_paint_it_passes_down() -> None:
    # One target, two fills from two <use>: the cache must not hand the first image to the second
    defs = f'<defs>{WIDE_BLUR}<rect id="r" width="60" height="40" filter="url(#b)"/></defs>'
    document = svg(f'{defs}<use href="#r" x="10" y="20" fill="red"/><use href="#r" x="110" y="20" fill="blue"/>', height=100)
    assert {(1, 0, 0), (0, 0, 1)} <= colors_of(render(document))
