"""Gradients, patterns, masks, blending and the opacity group."""

from __future__ import annotations

import re
import threading
from types import SimpleNamespace
from typing import Any
from xml.etree import ElementTree as ET

import pytest
from helpers import SVG_NS, RecordingStream, content, pixel, render, streams, svg

from weasysvg import paint
from weasysvg.paint import GRADIENT_CELL, drop_empty_presentation

RED = (255, 0, 0)
WHITE = (255, 255, 255)


def near(actual: tuple[int, int, int], expected: tuple[int, int, int], tolerance: int = 40) -> bool:
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected, strict=True))


# ---------------- tree pass ----------------


def test_empty_presentation_attributes_are_dropped() -> None:
    root = ET.fromstring(f'<svg xmlns="{SVG_NS}"><rect fill="" stroke=" " id="r" width="1"/></svg>')
    drop_empty_presentation(root)
    assert root[0].attrib == {"id": "r", "width": "1"}


def test_empty_fill_paints_black() -> None:
    pdf = render(svg('<rect width="200" height="100" fill=""/>'))
    assert near(pixel(pdf, 50, 30), (0, 0, 0))


# ---------------- gradients ----------------


def test_gradient_cell_is_large() -> None:
    body = '<defs><linearGradient id="g"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient></defs><rect width="200" height="100" fill="url(#g)"/>'
    pdf = render(svg(body))
    text = pdf.decode("latin-1")
    sizes = [float(value) for value in re.findall(r"/BBox \[\s*[-\d.]+ [-\d.]+ ([-\d.]+)", text)]
    assert any(abs(value - GRADIENT_CELL) < 1 for value in sizes)
    assert near(pixel(pdf, 5, 30), RED, 60)


def test_radial_percentages_use_the_normalized_diagonal() -> None:
    gradient = ET.Element("radialGradient", {"r": "25%", "fr": "10%"})
    node = type("Node", (), {"tag": "radialGradient", "attrib": gradient.attrib, "get": gradient.get})()
    changed = paint._radial_percentages(node)
    assert changed == {"r": "25%", "fr": "10%"}
    assert gradient.attrib == {"r": "0.25", "fr": "0.1"}


def test_radial_percentages_skip_user_space_and_linear() -> None:
    user = ET.Element("radialGradient", {"gradientUnits": "userSpaceOnUse", "r": "50%"})
    node = type("Node", (), {"tag": "radialGradient", "attrib": user.attrib, "get": user.get})()
    assert paint._radial_percentages(node) == {}
    linear = type("Node", (), {"tag": "linearGradient", "attrib": {}, "get": {}.get})()
    assert paint._radial_percentages(linear) == {}


def test_radial_gradient_attributes_are_restored() -> None:
    body = (
        '<defs><radialGradient id="g" r="40%" fr="5%"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="white"/></radialGradient>'
        '<radialGradient id="h" href="#g"/></defs>'
        '<rect width="100" height="100" fill="url(#g)"/><rect x="100" width="100" height="100" fill="url(#h)"/>'
    )
    pdf = render(svg(body))
    assert near(pixel(pdf, 37, 37), RED, 60)
    assert near(pixel(pdf, 112, 37), RED, 60)


@pytest.mark.parametrize("units", ["", ' gradientUnits="userSpaceOnUse" x1="0" x2="200"'])
@pytest.mark.parametrize("opacity", ["1", "0.999"])
def test_rotated_gradient_covers_the_shape(units: str, opacity: str) -> None:
    # WeasyPrint sizes the cell from two corners of the box: rotated by 45 degrees, the cell is a sliver
    gradient = f'<linearGradient id="g"{units} gradientTransform="rotate(45 100 50)"><stop stop-color="red"/><stop offset="1" stop-color="red" stop-opacity="{opacity}"/></linearGradient>'
    pdf = render(svg(f'<defs>{gradient}</defs><rect width="200" height="100" fill="url(#g)"/>'))
    for x, y in ((10, 10), (75, 37), (140, 65)):
        assert near(pixel(pdf, x, y), RED, 30)


def test_degenerate_gradient_transforms() -> None:
    # A singular transform and a shape without a box: no cell, the rendering of WeasyPrint
    gradient = '<linearGradient id="g" gradientTransform="scale(0)"><stop stop-color="red"/><stop offset="1" stop-color="blue"/></linearGradient><linearGradient id="h" gradientTransform="rotate(45)" href="#g"/>'
    render(svg(f'<defs>{gradient}</defs><rect width="200" height="100" fill="url(#g)"/><path d="" fill="url(#h)"/>'))


def test_gradient_cell_needs_a_box() -> None:
    gradient = SimpleNamespace(attrib={"gradientTransform": "rotate(45)"}, get={"gradientTransform": "rotate(45)"}.get)
    fake = SimpleNamespace(calculate_bounding_box=lambda *_args: None)
    assert paint._gradient_cell(fake, object(), gradient, 12, False) is None


def test_gradient_stops_via_href_used_twice() -> None:
    body = (
        '<defs><linearGradient id="base"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="red"/></linearGradient>'
        '<linearGradient id="a" xlink:href="#base"/><linearGradient id="b" xlink:href="#base" x1="1" x2="0"/></defs>'
        '<rect width="100" height="100" fill="url(#a)"/><rect x="100" width="100" height="100" fill="url(#b)"/>'
    )
    pdf = render(svg(body))
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 120, 30), RED)


@pytest.mark.parametrize("paint_server", ['<linearGradient id="p"><stop stop-color="red"/><stop offset="1" stop-color="red"/></linearGradient>', '<pattern id="p" width="1" height="1"><rect width="200" height="200" fill="red"/></pattern>'])
def test_paint_server_stroke_has_its_width(paint_server: str) -> None:
    # The stroke spans 10 to 30 user units around the left edge at x=20
    pdf = render(svg(f'<defs>{paint_server}</defs><rect x="20" y="20" width="100" height="60" fill="none" stroke="url(#p)" stroke-width="20"/>'))
    assert near(pixel(pdf, 9, 37), RED, 60)


# ---------------- patterns ----------------


def test_pattern_x_moves_the_tile_in_user_space() -> None:
    body = '<defs><pattern id="p" patternUnits="userSpaceOnUse" x="50" y="0" width="100" height="100"><rect width="50" height="100" fill="red"/></pattern></defs><rect width="200" height="100" fill="url(#p)"/>'
    pdf = render(svg(body))
    # The tile starts at x=50: red from 50 to 100 CSS px, white from 0 to 50
    assert near(pixel(pdf, 15, 30), WHITE)
    assert near(pixel(pdf, 55, 30), RED)


def test_pattern_in_bounding_box_units_used_twice() -> None:
    body = '<defs><pattern id="p" x="0.25" y="0" width="0.5" height="1"><rect width="50" height="100" fill="red"/></pattern></defs><rect width="200" height="100" fill="url(#p)"/><rect y="100" width="200" height="100" fill="url(#p)"/>'
    pdf = render(svg(body, height=200))
    assert near(pixel(pdf, 50, 30), RED)
    assert near(pixel(pdf, 50, 105), RED)
    assert near(pixel(pdf, 15, 30), WHITE)


def test_user_space_pattern_starts_at_the_user_origin() -> None:
    # The tiles start at x=0 of the user space, not at the box of the shape: 50 to 100 is white
    body = '<defs><pattern id="p" patternUnits="userSpaceOnUse" width="100" height="100"><rect width="50" height="100" fill="red"/></pattern></defs><rect x="50" width="150" height="100" fill="url(#p)"/>'
    pdf = render(svg(body))
    assert near(pixel(pdf, 45, 30), WHITE)
    assert near(pixel(pdf, 80, 30), RED)


def test_pattern_transform_applies_to_the_tile_origin() -> None:
    # The box origin x=50 lies in pattern space: scale(2) moves the tiles to 100, 200 and so on
    body = '<defs><pattern id="p" width="0.5" height="1" patternContentUnits="userSpaceOnUse" patternTransform="scale(2)"><rect width="25" height="100" fill="red"/></pattern></defs><rect x="50" width="100" height="50" fill="url(#p)"/>'
    pdf = render(svg(body, width=400))
    assert near(pixel(pdf, 60, 15), WHITE)
    assert near(pixel(pdf, 80, 15), RED)


def test_pattern_on_a_shape_without_box() -> None:
    body = '<defs><pattern id="p" x="0.1" width="1" height="1"><rect width="10" height="10" fill="red"/></pattern></defs><g fill="url(#p)"><path d=""/></g>'
    render(svg(body))


# ---------------- masks ----------------


def test_mask_is_set_before_the_path() -> None:
    body = '<defs><mask id="m"><rect width="100" height="100" fill="white"/></mask></defs><rect width="200" height="100" fill="red" mask="url(#m)"/>'
    pdf = render(svg(body))
    page = streams(pdf)[0]
    # The soft mask comes first, then the path: no path construction between them
    assert re.search(r"/s\d+ gs\n(?:(?!.* re\n).*\n)*?0 0 200 100 re\nf", page)
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 120, 30), WHITE)


def test_mask_on_a_group_and_content_units() -> None:
    body = '<defs><mask id="m" maskContentUnits="objectBoundingBox"><rect width="0.5" height="1" fill="white"/></mask></defs><g mask="url(#m)"><rect width="200" height="100" fill="red"/></g>'
    pdf = render(svg(body))
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 120, 30), WHITE)


def test_mask_in_user_space() -> None:
    body = '<defs><mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="50" height="100"><rect width="200" height="100" fill="white"/></mask></defs><rect width="200" height="100" fill="red" mask="url(#m)"/>'
    pdf = render(svg(body))
    assert near(pixel(pdf, 20, 30), RED)
    assert near(pixel(pdf, 60, 30), WHITE)


def test_mask_that_references_itself() -> None:
    body = '<defs><mask id="m"><rect width="100" height="100" fill="white" mask="url(#m)"/></mask></defs><rect width="200" height="100" fill="red" mask="url(#m)"/>'
    pdf = render(svg(body))
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 120, 30), WHITE)


@pytest.mark.parametrize("cycle", [False, True])
def test_mask_attribute_on_a_mask_is_ignored(cycle: bool) -> None:
    # Chromium ignores mask on a <mask>: the black half of b would hide the whole left half otherwise
    other = ' mask="url(#a)"' if cycle else ""
    defs = f'<mask id="a" mask="url(#b)"><rect width="200" height="100" fill="white"/></mask><mask id="b"{other}><rect width="100" height="100" fill="black"/></mask>'
    pdf = render(svg(f'<defs>{defs}</defs><rect width="200" height="100" fill="red" mask="url(#a)"/>'))
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 120, 30), RED)


# ---------------- clip paths ----------------


def test_clip_rule_evenodd_leaves_a_hole() -> None:
    clip = '<clipPath id="c"><path d="M0 0H200V100H0Z M50 25H150V75H50Z" clip-rule="evenodd"/></clipPath>'
    pdf = render(svg(f'<defs>{clip}</defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/>'))
    assert near(pixel(pdf, 15, 10), RED)
    assert near(pixel(pdf, 75, 37), WHITE)


def test_clip_children_keep_their_own_clip_paths() -> None:
    clip = '<clipPath id="c"><rect width="50" height="50"/><rect x="100" width="100" height="100" clip-path="url(#d)"/></clipPath><clipPath id="d"><circle cx="150" cy="50" r="30"/></clipPath>'
    pdf = render(svg(f'<defs>{clip}</defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/>'))
    assert near(pixel(pdf, 15, 15), RED)
    assert near(pixel(pdf, 112, 37), RED)
    assert near(pixel(pdf, 80, 5), WHITE)
    assert near(pixel(pdf, 60, 60), WHITE)


def test_clip_ignores_opacity_and_paint_of_its_content() -> None:
    clip = '<clipPath id="c"><use href="#r" style="opacity:.25;fill:none"/></clipPath>'
    defs = f'<rect id="r" width="100" height="100" fill="none"/>{clip}'
    pdf = render(svg(f'<defs>{defs}</defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/>'))
    assert near(pixel(pdf, 30, 30), RED, 5)
    assert near(pixel(pdf, 120, 30), WHITE)


def test_text_in_a_clip_path_clips() -> None:
    clip = '<clipPath id="c"><text x="10" y="80" font-size="80" font-weight="bold">II</text></clipPath>'
    pdf = render(svg(f'<defs>{clip}</defs><rect width="200" height="100" fill="red" clip-path="url(#c)"/>'))
    colors = {pixel(pdf, x, 40) for x in range(0, 150, 2)}
    assert any(near(color, RED) for color in colors)
    assert not any(near(color, (0, 0, 0), 60) for color in colors)


def test_complex_clip_in_bounding_box_units_with_a_mask() -> None:
    clip = '<clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/><text y="1" font-size="0.5">x</text></clipPath>'
    mask = '<mask id="m"><rect width="200" height="50" fill="white"/></mask>'
    pdf = render(svg(f'<defs>{clip}{mask}</defs><rect x="100" width="100" height="100" fill="red" clip-path="url(#c)" mask="url(#m)"/>'))
    assert near(pixel(pdf, 80, 15), RED)
    assert near(pixel(pdf, 130, 15), WHITE)
    assert near(pixel(pdf, 80, 60), WHITE)


def test_mask_on_an_empty_group_is_skipped() -> None:
    body = (
        '<defs><mask id="m"><rect width="1" height="1" fill="white"/></mask><mask id="c" maskContentUnits="objectBoundingBox"><rect width="1" height="1"/></mask></defs>'
        '<g mask="url(#m)"/><g mask="url(#c)"/><rect width="10" height="10" mask="url(#missing)"/>'
    )
    render(svg(body))


def test_mask_tag_is_restored_after_drawing() -> None:
    body = '<mask id="m"><rect width="100" height="100" fill="white"/></mask><rect width="200" height="100" fill="red" mask="url(#m)"/>'
    pdf = render(svg(body))
    # The <mask> outside <defs> is not drawn as a group of its own
    assert near(pixel(pdf, 120, 30), WHITE)


# ---------------- blending and opacity ----------------


def test_blend_mode_is_an_isolated_group() -> None:
    body = '<rect width="200" height="100" fill="yellow"/><g style="mix-blend-mode:multiply"><rect width="100" height="100" fill="cyan"/><rect width="50" height="100" fill="cyan"/></g>'
    pdf = render(svg(body))
    assert "/BM /Multiply" in pdf.decode("latin-1")
    assert near(pixel(pdf, 20, 30), (0, 255, 0))


def test_blend_mode_values() -> None:
    node = type("Node", (), {"get": {"mix-blend-mode": " Screen "}.get})()
    assert paint.blend_mode(node) == "Screen"
    assert paint.blend_mode(type("Node", (), {"get": {"mix-blend-mode": "normal"}.get})()) is None


def test_blend_mode_is_not_inherited() -> None:
    body = '<g style="mix-blend-mode:screen"><g><rect width="10" height="10"/></g></g>'
    pdf = render(svg(body))
    assert pdf.decode("latin-1").count("/BM /Screen") == 1


def test_opacity_group_is_unbounded() -> None:
    body = '<g opacity="0.5"><text x="100" y="50" text-anchor="end" font-size="30">Shifted</text></g>'
    pdf = render(svg(body))
    assert "/A0.5 gs" in content(pdf) or "/a0.5 gs" in content(pdf)
    assert "/BBox [-10000 -10000 10000 10000]" in pdf.decode("latin-1")


def test_transform_with_mask_and_opacity() -> None:
    body = (
        '<defs><mask id="m"><rect width="50" height="100" fill="white"/></mask></defs>'
        '<rect transform="translate(100 0)" width="100" height="100" fill="red" mask="url(#m)"/>'
        '<rect transform="translate(0 0)" width="50" height="100" fill="red" opacity="0.5"/>'
    )
    pdf = render(svg(body))
    assert near(pixel(pdf, 80, 30), RED)
    assert near(pixel(pdf, 130, 30), WHITE)
    assert near(pixel(pdf, 20, 30), (255, 128, 128))


def test_mask_with_transform_and_content_units_on_an_empty_group() -> None:
    body = (
        '<defs><mask id="m" maskContentUnits="objectBoundingBox" transform="translate(0 0)"><rect width="0.5" height="1" fill="white"/></mask>'
        '<mask id="e" maskUnits="userSpaceOnUse" maskContentUnits="objectBoundingBox"><rect width="1" height="1" fill="white"/></mask></defs>'
        '<rect width="200" height="100" fill="red" mask="url(#m)"/><g mask="url(#e)"/>'
    )
    pdf = render(svg(body))
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 120, 30), WHITE)


def test_radial_gradient_with_default_and_absolute_radius() -> None:
    body = (
        '<defs><radialGradient id="a"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="white"/></radialGradient>'
        '<radialGradient id="b" r="0.4"><stop offset="0" stop-color="red"/><stop offset="1" stop-color="white"/></radialGradient></defs>'
        '<rect width="100" height="100" fill="url(#a)"/><rect x="100" width="100" height="100" fill="url(#b)"/>'
    )
    pdf = render(svg(body))
    assert near(pixel(pdf, 37, 37), RED, 60)
    assert near(pixel(pdf, 112, 37), RED, 60)


def test_pattern_override_nests() -> None:
    class Stream:
        def add_pattern(self) -> str:
            return "class"

    stream = Stream()
    with paint._add_pattern_override(stream, lambda: "outer"):
        with paint._add_pattern_override(stream, lambda: "inner"):
            assert stream.add_pattern() == "inner"
        assert stream.add_pattern() == "outer"
    assert stream.add_pattern() == "class"
    assert "add_pattern" not in stream.__dict__


# ---------------- state across threads and exceptions ----------------


class FakeMask:
    def __init__(self) -> None:
        self.attrib = {"maskUnits": "userSpaceOnUse", "x": "0", "y": "0", "width": "10", "height": "10"}
        self._etree_node = SimpleNamespace(tag="mask")

    def get(self, name: str, default: Any = None) -> Any:
        return self.attrib.get(name, default)


def mask_svg(draw: Any) -> Any:
    return SimpleNamespace(inner_width=10, inner_height=10, stream=RecordingStream(), draw_node=draw)


def test_a_mask_drawn_in_another_thread_is_not_a_cycle() -> None:
    # weasyprint-service renders in a thread pool: one rendering's open masks must not block another's
    mask = FakeMask()
    inner_draws: list[Any] = []

    def outer_draw(*_args: Any) -> None:
        worker = threading.Thread(target=paint.paint_mask, args=(mask_svg(lambda *a: inner_draws.append(a)), object(), mask, 1))
        worker.start()
        worker.join()

    paint.paint_mask(mask_svg(outer_draw), object(), mask, 1)
    assert len(inner_draws) == 1


def test_a_failing_mask_draw_restores_the_mask() -> None:
    mask = FakeMask()
    mask.attrib["maskContentUnits"] = "objectBoundingBox"

    def failing(*_args: Any) -> None:
        raise RuntimeError("draw failed")

    svg_failing = mask_svg(failing)
    svg_failing.calculate_bounding_box = lambda *_args, **_kwargs: (0, 0, 10, 10)
    with pytest.raises(RuntimeError):
        paint.paint_mask(svg_failing, object(), mask, 1)
    assert "transform" not in mask.attrib
    assert mask._etree_node.tag == "mask"
    drawn: list[Any] = []
    svg_drawing = mask_svg(lambda *a: drawn.append(a))
    svg_drawing.calculate_bounding_box = svg_failing.calculate_bounding_box
    paint.paint_mask(svg_drawing, object(), mask, 1)
    assert len(drawn) == 1


def test_a_failing_pattern_keeps_its_origin() -> None:
    # The shared pattern node must get x and y back even when its geometry raises
    pattern = SimpleNamespace(attrib={"x": "5", "y": "5", "patternUnits": "userSpaceOnUse"}, _etree_node=SimpleNamespace(tag="pattern"))
    pattern.get = pattern.attrib.get

    def failing(*_args: Any) -> Any:
        raise ValueError("bad length")

    fake = SimpleNamespace(point=failing, stream=RecordingStream())
    with pytest.raises(ValueError, match="bad length"):
        paint.draw_pattern(fake, object(), pattern, 12, 1, False)
    assert pattern.attrib == {"x": "5", "y": "5", "patternUnits": "userSpaceOnUse"}


@pytest.mark.parametrize("attribute", ['opacity="0.5"', 'style="mix-blend-mode:multiply"'])
def test_groups_reach_far_coordinates(attribute: str) -> None:
    # Map and CAD exports draw far from the origin: the opacity and blend groups must not clip them
    body = f'<rect x="50010" y="10" width="80" height="80" fill="red" {attribute}/>'
    pdf = render(f'<svg xmlns="{SVG_NS}" width="200" height="100" viewBox="50000 0 200 100">{body}</svg>')
    red, green, blue = pixel(pdf, 40, 40)
    assert red > 200
    assert green < 200
    assert blue < 200


def test_a_mask_on_an_empty_group_is_skipped(caplog: pytest.LogCaptureFixture) -> None:
    # An empty group has the box (inf, inf, 0, 0): an objectBoundingBox mask has no region there
    mask = '<mask id="m" maskContentUnits="objectBoundingBox"><rect width="1" height="1" fill="white"/></mask>'
    pdf = render(svg(f'<defs>{mask}</defs><g mask="url(#m)"/><rect x="10" y="10" width="40" height="40" fill="red"/>'))
    assert "Failed to render SVG image" not in caplog.text
    assert b"inf" not in pdf.lower().replace(b"/info", b"")
    assert near(pixel(pdf, 20, 20), RED)
