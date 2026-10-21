"""<switch>, requiredExtensions and systemLanguage, on plain XML and in a rendering."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pytest
import weasyprint
from helpers import SVG_NS, XHTML_NS, render, svg, text_of

import weasysvg
from weasysvg import conditional
from weasysvg.conditional import apply_conditionals, local_name, passes


def tree(body: str) -> ET.Element:
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    return ET.fromstring(f'<svg xmlns="{SVG_NS}">{body}</svg>', parser=parser)


def ids(root: ET.Element) -> list[str]:
    return [element.get("id", "") for element in root.iter() if element.get("id")]


@pytest.mark.parametrize(
    ("attributes", "expected"),
    [
        ({}, True),
        ({"requiredExtensions": XHTML_NS}, True),
        ({"requiredExtensions": f"{XHTML_NS} {XHTML_NS}"}, True),
        ({"requiredExtensions": ""}, False),
        ({"requiredExtensions": "http://example.com/ext"}, False),
        ({"systemLanguage": "en"}, True),
        ({"systemLanguage": "de, en-US"}, True),
        ({"systemLanguage": " EN-gb "}, True),
        ({"systemLanguage": "de,fr"}, False),
        ({"systemLanguage": "english"}, False),
        ({"systemLanguage": ""}, False),
        ({"requiredFeatures": "http://www.w3.org/TR/SVG11/feature#Shape"}, True),
    ],
)
def test_passes(attributes: dict[str, str], expected: bool) -> None:
    assert passes(ET.Element("rect", attributes)) is expected


def test_local_name() -> None:
    assert local_name(f"{{{SVG_NS}}}switch") == "switch"
    assert local_name("rect") == "rect"
    assert local_name(ET.Comment) is None


def test_switch_keeps_the_first_child_that_passes() -> None:
    root = tree('<switch><!-- note --><rect id="de" systemLanguage="de"/><rect id="en" systemLanguage="en"/><rect id="any"/></switch>')
    apply_conditionals(root)
    assert ids(root) == ["en"]
    switch = root[0]
    # Comments are left alone
    assert len(switch) == 2


def test_switch_with_foreign_object_drops_the_fallback() -> None:
    root = tree(f'<switch><foreignObject id="fo" requiredExtensions="{XHTML_NS}"/><text id="fallback">x</text></switch>')
    apply_conditionals(root)
    assert ids(root) == ["fo"]


def test_switch_without_a_passing_child_is_empty() -> None:
    root = tree('<switch><rect id="a" systemLanguage="fr"/></switch>')
    apply_conditionals(root)
    assert ids(root) == []


def test_attributes_outside_a_switch_hide_elements() -> None:
    root = tree('<g id="g"><rect id="hidden" systemLanguage="fr"/><rect id="shown" systemLanguage="en"/></g>')
    apply_conditionals(root)
    assert ids(root) == ["g", "shown"]


def test_referenced_elements_ignore_the_attributes() -> None:
    root = tree('<defs id="d" systemLanguage="fr"><clipPath id="c" systemLanguage="fr"/><mask id="m" requiredExtensions="x"/></defs>')
    apply_conditionals(root)
    assert ids(root) == ["d", "c", "m"]


def test_the_root_is_never_removed() -> None:
    root = ET.fromstring(f'<svg xmlns="{SVG_NS}" systemLanguage="fr"><rect id="r"/></svg>')
    apply_conditionals(root)
    assert ids(root) == ["r"]


def test_switch_renders_one_branch() -> None:
    pdf = render(svg('<switch><text x="10" y="40" systemLanguage="de">Hallo</text><text x="10" y="40">Hello</text></switch>'))
    assert text_of(pdf).strip() == "Hello"


def test_draw_io_label_renders_once() -> None:
    body = f'<switch><foreignObject x="0" y="0" width="150" height="40" requiredExtensions="{XHTML_NS}"><div xmlns="{XHTML_NS}">Label</div></foreignObject><text x="10" y="30">Fallback</text></switch>'
    text = text_of(render(svg(body)))
    assert "Label" in text
    assert "Fallback" not in text


def test_without_foreign_object_the_fallback_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    # install(foreign_object=False): nothing would draw the foreignObject, so the switch must keep the fallback
    monkeypatch.setattr(conditional, "SUPPORTED_EXTENSIONS", set())
    assert passes(ET.Element("foreignObject", {"requiredExtensions": XHTML_NS})) is False
    root = tree(f'<switch><foreignObject id="fo" requiredExtensions="{XHTML_NS}"/><text id="fallback">x</text></switch>')
    apply_conditionals(root)
    assert ids(root) == ["fallback"]


# ---------------- the language of the reader ----------------

GREETING = svg('<switch><text x="10" y="40" systemLanguage="de">Hallo</text><text x="10" y="40" systemLanguage="ru">Privet</text><text x="10" y="40" systemLanguage="en">Hello</text></switch>')


def page(body: str, lang: str = "", **options: Any) -> bytes:
    attribute = f' lang="{lang}"' if lang else ""
    html = f"<!DOCTYPE html><html{attribute}><head><style>@page{{size:400px 600px;margin:0}} body{{margin:0}} img{{display:block}}</style></head><body>{body}</body></html>"
    pdf: bytes = weasyprint.HTML(string=html).write_pdf(**options)
    return pdf


def image(document: str, lang: str = "") -> str:
    attribute = f' lang="{lang}"' if lang else ""
    return f'<p{attribute}><img src="data:image/svg+xml;base64,{base64.b64encode(document.encode()).decode()}"></p>'


@pytest.mark.parametrize(
    ("language", "codes", "expected"),
    [
        ("de", "de", True),
        ("de", "de-AT", True),
        ("de-CH", "de", True),
        ("de-CH", "de-ch", True),
        ("de-CH", "en", False),
        ("RU", "ru", True),
        ("ru", "rus", False),
    ],
)
def test_the_language_of_the_reader(language: str, codes: str, expected: bool) -> None:
    # As Blink with the Accept-Language list a browser sends for the language: "de-CH" sends "de-CH,de"
    token = conditional.LANGUAGE.set(language)
    try:
        assert passes(ET.Element("text", {"systemLanguage": codes})) is expected
    finally:
        conditional.LANGUAGE.reset(token)


def test_an_image_takes_the_language_of_its_document() -> None:
    assert text_of(page(image(GREETING))).strip() == "Hello"
    assert text_of(page(image(GREETING), lang="de")).strip() == "Hallo"


def test_one_image_in_two_languages() -> None:
    # The same URL in two languages: each takes its own, the cache of images keeps them apart
    text = text_of(page(image(GREETING, "ru") + image(GREETING, "de"))).split()
    assert text == ["Privet", "Hallo"]


def test_an_inline_svg_takes_the_language_of_its_document() -> None:
    assert text_of(page(GREETING, lang="ru")).strip() == "Privet"


def test_install_sets_the_language_without_one_in_the_document(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(conditional, "DEFAULT_LANGUAGE", conditional.DEFAULT_LANGUAGE)
    weasysvg.install(language="ru")
    assert text_of(page(image(GREETING))).strip() == "Privet"
    # The document wins
    assert text_of(page(image(GREETING), lang="de")).strip() == "Hallo"


def test_one_image_in_two_languages_in_a_cache_on_disk(tmp_path: Path) -> None:
    text = text_of(page(image(GREETING, "ru") + image(GREETING, "de"), cache=tmp_path)).split()
    assert text == ["Privet", "Hallo"]


def test_a_shared_cache_follows_the_language_of_install(monkeypatch: pytest.MonkeyPatch) -> None:
    # A cache kept across documents: an image built under one language is not reused under another
    monkeypatch.setattr(conditional, "DEFAULT_LANGUAGE", conditional.DEFAULT_LANGUAGE)
    cache: dict[Any, Any] = {}
    weasysvg.install(language="ru")
    assert text_of(page(image(GREETING), cache=cache)).strip() == "Privet"
    weasysvg.install(language="de")
    assert text_of(page(image(GREETING), cache=cache)).strip() == "Hallo"


def test_a_background_reads_the_language_of_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(conditional, "DEFAULT_LANGUAGE", conditional.DEFAULT_LANGUAGE)
    data = base64.b64encode(GREETING.encode()).decode()
    body = f'<div lang="de" style="width:200px;height:100px;background:url(data:image/svg+xml;base64,{data}) no-repeat"></div>'
    weasysvg.install(language="ru")
    assert text_of(page(body)).strip() == "Privet"


def test_a_nested_svg_takes_the_language_of_the_document() -> None:
    # An <image> of an SVG is built while the outer SVG draws, after handle_element is done
    inner = base64.b64encode(GREETING.encode()).decode()
    outer = svg(f'<image width="200" height="100" href="data:image/svg+xml;base64,{inner}"/>')
    assert text_of(page(image(outer), lang="de")).strip() == "Hallo"


def test_an_svg_inside_a_foreign_object_takes_the_language_of_the_document() -> None:
    inner = base64.b64encode(GREETING.encode()).decode()
    outer = svg(f'<foreignObject width="200" height="100"><div xmlns="{XHTML_NS}"><img src="data:image/svg+xml;base64,{inner}"/></div></foreignObject>')
    assert text_of(page(image(outer), lang="ru")).strip() == "Privet"


@pytest.mark.parametrize("language", ["", "  "])
def test_an_empty_language_is_refused(monkeypatch: pytest.MonkeyPatch, language: str) -> None:
    # An empty language would match no systemLanguage at all
    monkeypatch.setattr(conditional, "DEFAULT_LANGUAGE", conditional.DEFAULT_LANGUAGE)
    with pytest.raises(ValueError, match="language"):
        weasysvg.install(language=language)
    assert conditional.DEFAULT_LANGUAGE == "en"
