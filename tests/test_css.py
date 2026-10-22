"""The CSS of SVG as Chromium 156 reads it, printing in the light color scheme (measured with Playwright)."""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

import pytest
import tinycss2
from helpers import SVG_NS, XHTML_NS, pixel, render, svg, text_of
from tinycss2.color5 import parse_color
from weasyprint.svg import SVG
from weasyprint.svg.utils import color

from weasysvg import css, text

SQUARE = '<rect id="r" width="20" height="20" {}/>'
STROKED = '<rect id="r" x="5" y="5" width="10" height="10" fill="none" stroke-width="20" {}/>'


def cascaded(document: str) -> dict[str, Any]:
    """Each node with an id, after the cascade of WeasyPrint as weasysvg patches it."""
    tree = SVG(ET.fromstring(document), "", None)
    nodes = {"root": tree.tree}
    pending = [tree.tree]
    while pending:
        node = pending.pop()
        for child in node:
            if child.get("id"):
                nodes[child.get("id")] = child
            pending.append(child)
    return nodes


def resolved(document: str, key: str = "fill", node: str = "r") -> str | None:
    """The value of key on the node, as the cascade leaves it: a color name for a color, None when unset."""
    value: str | None = cascaded(svg(document, 20, 20))[node].get(key)
    if value is None or value == "none":
        return value
    parsed = parse_color(value)
    for name in ("lime", "red", "blue", "black"):
        if parsed is not None and parsed == parse_color(name):
            return name
    return str(value)


def styled(rules: str, body: str) -> str:
    return f"<style>{rules}</style>{body}"


# ---------------- light-dark() ----------------


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (SQUARE.format('fill="light-dark(lime, red)"'), "lime"),
        (SQUARE.format('style="fill: light-dark(lime, red)"'), "lime"),
        (SQUARE.format('style="fill: light-dark(light-dark(lime, red), red)"'), "lime"),
        (SQUARE.format('style="color: light-dark(lime, red); fill: currentColor"'), "lime"),
        (SQUARE.format('style="color: lime; fill: light-dark(currentColor, red)"'), "lime"),
        (SQUARE.format('style="fill: url(#nope) light-dark(lime, red)"'), "url(#nope) lime"),
    ],
)
def test_light_dark_takes_the_light_color(body: str, expected: str) -> None:
    assert resolved(body) == expected


def test_light_dark_in_every_color_property() -> None:
    gradient = '<linearGradient id="g"><stop id="s" offset="0" style="stop-color: light-dark(lime, red)"/></linearGradient>'
    flood = '<filter id="f"><feFlood id="fl" flood-color="light-dark(lime, red)"/><feDiffuseLighting id="dl" style="lighting-color: light-dark(lime, red)"/></filter>'
    assert resolved(gradient, "stop-color", "s") == "lime"
    assert resolved(flood, "flood-color", "fl") == "lime"
    assert resolved(flood, "lighting-color", "dl") == "lime"
    assert resolved(STROKED.format('style="stroke: light-dark(lime, red)"'), "stroke") == "lime"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("light-dark(lime, red)", "lime"),
        ("LIGHT-DARK( #fff , #000 )", "#fff"),
        ("url(#a) light-dark(rgb(0, 0, 0), white)", "url(#a) rgb(0, 0, 0)"),
        ("light-dark(lime)", "light-dark(lime)"),
        ("lime", "lime"),
    ],
)
def test_light(value: str, expected: str) -> None:
    assert css.light(value) == expected


# ---------------- custom properties and var() ----------------


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        # A presentation attribute takes var() too
        (svg(SQUARE.format('fill="var(--c)"'), extra=' style="--c: lime"'), "lime"),
        (svg(SQUARE.format('fill="var(--u, lime)"')), "lime"),
        (svg(SQUARE.format('style="fill: light-dark(var(--g), red)"'), extra=' style="--g: lime"'), "lime"),
        (svg(SQUARE.format('style="fill: var(--u, var(--g, red))"'), extra=' style="--g: lime"'), "lime"),
        (svg(SQUARE.format('style="fill: VAR(--g)"'), extra=' style="--g: lime"'), "lime"),
        # Names are case-sensitive
        (svg(SQUARE.format('fill="red" style="fill: var(--G, lime)"'), extra=' style="--g: red"'), "lime"),
        (svg(SQUARE.format('style="color: lime; --p: currentcolor; fill: var(--p)"')), "lime"),
        (svg('<g style="--t: light-dark(lime, red)">' + SQUARE.format('style="color: var(--t); fill: currentColor"') + "</g>"), "lime"),
        (svg(styled("svg { --g: lime !important }", SQUARE.format('style="fill: var(--g)"')), extra=' style="--g: red"'), "lime"),
        # A cycle makes both properties invalid: the fallback applies
        (svg(SQUARE.format('fill="red" style="--a: var(--b); --b: var(--a); fill: var(--a, lime)"')), "lime"),
        (svg(SQUARE.format('style="--a: var(--a); fill: var(--a, lime)"')), "lime"),
    ],
)
def test_var_substitutes(body: str, expected: str) -> None:
    tree = cascaded(body.replace('width="200" height="100"', 'width="20" height="20"'))
    assert color(tree["r"].get("fill")) == color(expected)


def test_draw_io_theme_resolves_to_the_light_background() -> None:
    """draw.io 29: the background of the shapes is a custom property set in @supports on the root."""
    rules = "@supports (color: light-dark(#000, #fff)) { #ge { --ge-adaptive-bg: light-dark(#ffffff, var(--ge-dark-color, #121212)); } }"
    shape = SQUARE.format('fill="#ffffff" stroke="#000000" style="fill: var(--ge-adaptive-bg, #ffffff); stroke: light-dark(rgb(0, 0, 0), rgb(255, 255, 255));"')
    tree = cascaded(svg(styled(rules, f"<g>{shape}</g>"), 20, 20, ' id="ge" style="color-scheme: light dark"'))
    assert color(tree["r"].get("fill")) == color("white")
    assert color(tree["r"].get("stroke")) == color("black")
    assert tree["root"].get("--ge-adaptive-bg") == "light-dark(#ffffff, #121212)"


def test_custom_properties_inherit_and_override() -> None:
    body = '<g id="g" style="--c: red; --d: blue">' + SQUARE.format('style="--c: lime"') + "</g>"
    tree = cascaded(svg(body, 20, 20, ' style="--e: var(--c, black)"'))
    assert (tree["g"].get("--c"), tree["r"].get("--c"), tree["r"].get("--d"), tree["r"].get("--e")) == ("red", "lime", "blue", "black")


def test_monospace_default_size_reads_the_substituted_family() -> None:
    """text.cascade wraps this cascade: the generic monospace through var() takes its 13px default too."""
    tree = cascaded(svg('<text id="t" style="--f: monospace; font-family: var(--f)">A</text>', 20, 20))
    assert tree["t"].get("font-family") == "monospace"
    assert getattr(tree["t"], text.FONT_PX) == 13


def test_var_inside_blocks() -> None:
    tree = cascaded(svg('<g id="g" style="--a: [var(--b)] (var(--b))"/>', 20, 20, ' style="--b: x"'))
    assert tree["g"].get("--a") == "[x] (x)"


@pytest.mark.parametrize(
    ("body", "key", "expected"),
    [
        # Invalid at computed-value time: unset, the inherited value or the initial one; never the attribute
        (SQUARE.format('fill="lime" style="fill: var(--u)"'), "fill", None),
        ('<g style="fill: blue">' + SQUARE.format('fill="lime" style="fill: var(--u)"') + "</g>", "fill", "blue"),
        ('<g fill="blue">' + SQUARE.format('fill="lime" style="fill: var(--u)"') + "</g>", "fill", "blue"),
        ('<g style="fill: blue">' + SQUARE.format('fill="red" style="--c: foo; fill: var(--c)"') + "</g>", "fill", "blue"),
        # Even in the dark color, which is never used
        ('<g style="fill: blue">' + SQUARE.format('fill="red" style="fill: light-dark(lime, var(--u))"') + "</g>", "fill", "blue"),
        ('<g fill="blue">' + SQUARE.format('fill="var(--u)"') + "</g>", "fill", "blue"),
        (STROKED.format('stroke="red" style="stroke: var(--u)"'), "stroke", None),
        ('<g stroke-width="3">' + SQUARE.format('style="stroke-width: var(--u)"') + "</g>", "stroke-width", "3"),
        (SQUARE.format('opacity="0.5" style="opacity: var(--u)"'), "opacity", None),
        # A var() without a custom property name, or with more than a fallback after it, is invalid
        ('<g fill="blue">' + SQUARE.format('style="fill: var(foo)"') + "</g>", "fill", "blue"),
        ('<g fill="blue">' + SQUARE.format('style="fill: var(--u foo)"') + "</g>", "fill", "blue"),
    ],
)
def test_invalid_at_computed_value_time_is_unset(body: str, key: str, expected: str | None) -> None:
    assert resolved(body, key) == expected


def test_invalid_stop_color_is_initial() -> None:
    gradient = '<linearGradient id="g" style="stop-color: red"><stop id="s" offset="0" stop-color="red" style="stop-color: var(--u)"/></linearGradient>'
    assert resolved(gradient, "stop-color", "s") is None


# ---------------- invalid values at parse time ----------------


@pytest.mark.parametrize(
    ("body", "key", "expected"),
    [
        # An invalid declaration is dropped: the attribute stays
        (SQUARE.format('fill="lime" style="fill: foo"'), "fill", "lime"),
        (SQUARE.format('fill="lime" style="fill: light-dark(lime, foo)"'), "fill", "lime"),
        (SQUARE.format('fill="lime" style="fill:"'), "fill", "lime"),
        (styled(".a { fill: nonsense }", SQUARE.format('class="a" fill="lime"')), "fill", "lime"),
        (styled(".a { fill: lime } .b { fill: nonsense }", SQUARE.format('class="a b" fill="red"')), "fill", "lime"),
        # An invalid attribute is ignored: the value of the parent inherits
        ('<g fill="blue">' + SQUARE.format('fill="foo"') + "</g>", "fill", "blue"),
        (STROKED.format('stroke="foo"'), "stroke", None),
        (SQUARE.format('color="lime" fill="currentcolor"'), "fill", "lime"),
        (SQUARE.format('fill="url(#a) none"'), "fill", "url(#a) none"),
        (SQUARE.format("style=\"fill: url('#a') lime\""), "fill", 'url("#a") lime'),
        (SQUARE.format('fill="context-stroke"'), "fill", "context-stroke"),
        (SQUARE.format('fill="url(#a) foo"'), "fill", None),
        (SQUARE.format('fill="lime red"'), "fill", None),
        (SQUARE.format('fill="#ff0000" style="fill: inherit"'), "fill", None),
    ],
)
def test_invalid_declarations_and_attributes(body: str, key: str, expected: str | None) -> None:
    assert resolved(body, key) == expected


@pytest.mark.parametrize(
    ("body", "key", "expected"),
    [
        ('<g stroke="red">' + STROKED.format('style="stroke: initial"') + "</g>", "stroke", None),
        ('<g fill="blue">' + SQUARE.format('fill="red" style="fill: unset"') + "</g>", "fill", "blue"),
        ('<g fill="blue">' + SQUARE.format('fill="red" style="fill: revert"') + "</g>", "fill", "blue"),
        ('<linearGradient id="g" stop-color="red"><stop id="r" offset="0" style="stop-color: unset"/></linearGradient>', "stop-color", None),
        ('<g color="blue">' + SQUARE.format('style="color: currentColor; fill: currentcolor"') + "</g>", "fill", "blue"),
    ],
)
def test_wide_keywords(body: str, key: str, expected: str | None) -> None:
    assert resolved(body, key) == expected


def test_parse_declarations_keeps_custom_properties() -> None:
    normal, important = css.parse_declarations("--Name: a b ; -webkit-x: 1; fill: lime; stroke: foo; --e:; color: red !important")
    assert normal == [("--Name", "a b"), ("fill", "lime"), ("--e", "")]
    assert important == [("color", "red")]


# ---------------- @supports ----------------


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("(color: light-dark(#000, #fff))", True),
        ("(fill: light-dark(#000, #fff))", True),
        ("(--x: anything at all)", True),
        ("(display: flex)", True),
        ("(foo: bar)", False),
        ("(color: nonsense)", False),
        ("(fill: url(#a) none)", True),
        ("not (foo: bar)", True),
        ("not (display: flex)", False),
        ("(foo: bar) or ((display: flex) and (--x: 1))", True),
        ("(display: flex) and (foo: bar)", False),
        ("(display: flex) and (color: red) and (--x: 1)", True),
        ("(display: flex) and (color: red) or (--x: 1)", False),
        ("selector(:has(a))", True),
        ("selector(a >>> b)", False),
        ("foo(bar)", False),
        ("(foo)", False),
        ("", False),
        ("not", False),
        ("(color: red) (color: red)", False),
        ("((color: red))", True),
        ("(not (foo: bar))", True),
        ("(color: var(--x))", True),
        ("(display:)", False),
        ("(color: red) and foo", False),
        ("((color: red) foo)", False),
    ],
)
def test_supports(condition: str, expected: bool) -> None:
    assert css.supports(tinycss2.parse_component_value_list(condition)) is expected


@pytest.mark.parametrize(
    ("rules", "expected"),
    [
        ("@supports (color: light-dark(#000, #fff)) { .a { fill: lime } }", "lime"),
        ("@supports (foo: bar) { .a { fill: red } }", "blue"),
        ("@supports not (foo: bar) { .a { fill: lime } }", "lime"),
        ("@supports (display: flex) { @supports (--x: 1) { .a { fill: lime } } }", "lime"),
        ("@supports (display: flex) { .a { fill: lime } } .a { stroke: red }", "lime"),
        # Nothing but the color scheme of the page: printing has the light one
        ("@media (prefers-color-scheme: dark) { .a { fill: red } }", "blue"),
    ],
)
def test_supports_rules(rules: str, expected: str) -> None:
    assert resolved(styled(rules, SQUARE.format('class="a" fill="blue"'))) == expected


# ---------------- rendering ----------------


def test_a_symbol_with_a_size_of_numbers_draws() -> None:
    """A <use> of a <symbol> writes its width and height as numbers: the cascade reads only strings for var()."""
    body = '<symbol id="s" transform="skewX(30)"><rect x="20" y="20" width="160" height="60" fill="lime"/></symbol><use href="#s"/>'
    assert pixel(render(svg(body)), 60, 37) == (0, 255, 0)


def test_draw_io_shapes_render_white_with_black_strokes() -> None:
    """The shapes of a draw.io 29 export: Chromium fills them white; WeasyPrint alone filled them black."""
    rules = "@supports (color: light-dark(#000, #fff)) { #ge { --ge-adaptive-bg: light-dark(#ffffff, var(--ge-dark-color, #121212)); } }"
    style = "fill: var(--ge-adaptive-bg, #ffffff); stroke: light-dark(rgb(0, 0, 0), rgb(255, 255, 255));"
    body = f'<style>{rules}</style><rect x="20" y="20" width="160" height="60" fill="#ffffff" stroke="#000000" stroke-width="8" style="{style}"/>'
    pdf = render(svg(body, extra=' id="ge" style="color-scheme: light dark"'))
    # CSS px 100, 50 inside, 20, 50 on the stroke, at 72 dpi
    assert pixel(pdf, 75, 37) == (255, 255, 255)
    assert pixel(pdf, 15, 37) == (0, 0, 0)


@pytest.mark.parametrize("label", ["var(--undefined)", "var(--defined)"])
def test_var_in_html_label_text_stays_literal(label: str) -> None:
    """Chromium shows var() in the text of an HTML label as written: it is text, not a CSS value."""
    body = f'<g style="--defined: lime"><foreignObject width="200" height="100"><div xmlns="{XHTML_NS}">Set {label}</div></foreignObject></g>'
    assert f"Set {label}" in text_of(render(svg(body)))


@pytest.mark.parametrize("name", ["data-label", "aria-label", "content", "{http://example.com/ns}note"])
def test_var_in_non_property_attributes_stays_literal(name: str) -> None:
    """Only CSS properties substitute var(): any other attribute keeps its text."""
    node = ET.fromstring(svg('<rect id="r" width="20" height="20"/>', 20, 20))
    node.find(f"{{{SVG_NS}}}rect").set(name, "var(--undefined)")  # type: ignore[union-attr]
    assert cascaded(ET.tostring(node, encoding="unicode"))["r"].get(name) == "var(--undefined)"
