"""<switch>, requiredExtensions and systemLanguage, on plain XML and in a rendering."""

from __future__ import annotations

from xml.etree import ElementTree as ET

import pytest
from helpers import SVG_NS, XHTML_NS, render, svg, text_of

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
