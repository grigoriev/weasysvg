"""Gradients, patterns, masks, blending and the opacity group."""

from __future__ import annotations

import re
import threading
from types import SimpleNamespace
from typing import Any, cast
from xml.etree import ElementTree as ET

import pytest
from helpers import SVG_NS, RecordingStream, content, pixel, rasterize, render, streams, svg

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


def test_gradient_interpolates_unpremultiplied() -> None:
    # Chromium mixes transparent white and black into half transparent gray: 0.75 over white, not 0.5
    gradient = '<linearGradient id="g"><stop stop-color="white" stop-opacity="0"/><stop offset="1" stop-color="black"/></linearGradient>'
    mask = '<mask id="m"><rect width="200" height="100" fill="url(#g)"/></mask>'
    pdf = render(svg(f'<defs>{gradient}{mask}</defs><rect width="200" height="50" fill="url(#g)"/><rect y="50" width="200" height="50" fill="red" mask="url(#m)"/>'))
    assert near(pixel(pdf, 75, 18), (191, 191, 191), 12)
    # In a mask the gray of the middle shows, so the red does too
    assert pixel(pdf, 75, 55) != WHITE


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


@pytest.mark.parametrize("complex_clip", ["", "<text>x</text>"])
def test_clip_cycles_are_ignored(complex_clip: str) -> None:
    # Chromium ignores the reference that closes a cycle; WeasyPrint recursed until the SVG was lost
    clips = (
        f'<clipPath id="c"><rect width="50" height="50" clip-path="url(#c)"/>{complex_clip}</clipPath>'
        '<clipPath id="d"><rect x="100" width="50" height="100" clip-path="url(#e)"/></clipPath>'
        '<clipPath id="e"><rect x="100" width="100" height="50" clip-path="url(#d)"/></clipPath>'
        '<clipPath id="f" clip-path="url(#f)"><rect y="60" width="50" height="40"/></clipPath>'
    )
    body = f'<defs>{clips}</defs><rect width="100" height="100" fill="red" clip-path="url(#c)"/><rect x="100" width="100" height="100" fill="red" clip-path="url(#d)"/><rect width="100" height="100" fill="red" clip-path="url(#f)"/>'
    pdf = render(svg(body))
    assert near(pixel(pdf, 15, 15), RED)
    assert near(pixel(pdf, 85, 15), RED)
    assert near(pixel(pdf, 85, 60), WHITE)
    assert near(pixel(pdf, 15, 60), RED)
    assert near(pixel(pdf, 60, 30), WHITE)


@pytest.mark.parametrize("complex_clip", ["", "<text>x</text>"])
def test_a_clip_reused_by_children_is_no_cycle(complex_clip: str) -> None:
    # The left half of each box: the group keeps 0..100, the children 0..50 and 100..150, so 50..200 is empty
    clip = f'<clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/>{complex_clip}</clipPath>'
    body = f'<defs>{clip}</defs><g clip-path="url(#c)"><rect width="100" height="100" fill="red" clip-path="url(#c)"/><rect x="100" width="100" height="100" fill="red" clip-path="url(#c)"/></g>'
    pdf = render(svg(body))
    assert near(pixel(pdf, 15, 30), RED)
    assert near(pixel(pdf, 56, 30), WHITE)


def test_missing_and_foreign_clip_references() -> None:
    references = ("url(#m)", "url(#nowhere)", "inset(1px)")
    body = "<defs><mask id='m'/></defs>" + "".join(f'<rect x="{20 * i}" width="10" height="10" fill="red" clip-path="{value}"/>' for i, value in enumerate(references))
    render(svg(body))


def test_complex_clip_in_bounding_box_units_without_a_box() -> None:
    clip = '<clipPath id="c" clipPathUnits="objectBoundingBox"><text>x</text></clipPath>'
    render(svg(f'<defs>{clip}</defs><g clip-path="url(#c)"/>'))


@pytest.mark.parametrize("shape", ['<g clip-path="url(#c)"><rect width="200" height="100" fill="red"/></g>', '<circle cx="100" cy="50" r="50" fill="red" clip-path="url(#c)"/>'])
def test_bounding_box_clip_on_any_element(shape: str) -> None:
    # The left half of the box, for a group or a circle as for a rect
    pdf = render(svg(f'<defs><clipPath id="c" clipPathUnits="objectBoundingBox"><rect width="0.5" height="1"/></clipPath></defs>{shape}'))
    assert near(pixel(pdf, 56, 30), RED)
    assert near(pixel(pdf, 90, 30), WHITE)


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


def test_a_failing_restyler_puts_back_what_others_changed(monkeypatch: pytest.MonkeyPatch) -> None:
    from weasysvg import _core

    def first(_svg: Any, node: Any, _size: float) -> dict[str, str | None]:
        node.attrib["fill"] = "blue"
        return {"fill": "red"}

    def second(*_args: Any) -> None:
        raise RuntimeError("restyler failed")

    monkeypatch.setattr(_core, "_RESTYLERS", [first, second])
    node = SimpleNamespace(attrib={"fill": "red"}, get=lambda *_args: None, tag="rect")
    fake = SimpleNamespace(paths={})
    with pytest.raises(RuntimeError):
        _core._draw_node(fake, node, 12)
    assert node.attrib == {"fill": "red"}
    assert _core._ACTIVE_CLIPS.get() == ()


def test_invalid_stop_opacity_counts_as_opaque() -> None:
    # WeasyPrint raised ValueError on it and lost the whole SVG; Chromium takes 1
    gradient = '<linearGradient id="g"><stop stop-color="red" stop-opacity="0"/><stop offset="0.01" stop-color="red" stop-opacity="abc"/><stop offset="1" stop-color="red" stop-opacity="abc"/></linearGradient>'
    pdf = render(svg(f'<defs>{gradient}</defs><rect width="200" height="100" fill="url(#g)"/><rect y="50" width="200" height="50" fill="url(#g)"/>'))
    assert near(pixel(pdf, 75, 30), RED)
    assert near(pixel(pdf, 75, 60), RED)


def test_blend_mode_with_a_complex_clip_blends_with_the_backdrop() -> None:
    # Blue multiplied over red is black; inside the isolated clip group it blended with nothing
    clip = '<clipPath id="c"><path d="M0 0H200V100H0Z" clip-rule="evenodd"/></clipPath>'
    body = f'<defs>{clip}</defs><rect width="200" height="100" fill="red"/><rect width="200" height="100" fill="blue" style="mix-blend-mode:multiply" clip-path="url(#c)"/>'
    assert near(pixel(render(svg(body)), 30, 30), (0, 0, 0), 20)


@pytest.mark.parametrize("fr", ["0.2", "20%"])
def test_a_concentric_focal_radius_leaves_no_hole(fr: str) -> None:
    # PDFium paints the center of a shading whose inner circle has a radius white
    gradient = f'<radialGradient id="g" fr="{fr}"><stop offset="0" stop-color="black"/><stop offset="1" stop-color="white"/></radialGradient>'
    pdf = render(svg(f'<defs>{gradient}</defs><rect x="20" y="20" width="160" height="160" fill="url(#g)"/>', height=200))
    coords = [[float(value) for value in found.split()] for found in re.findall(r"/Coords \[([^\]]*)\]", pdf.decode("latin-1"))]
    assert coords
    assert all(values[2] == 0 for values in coords)
    gray = rasterize(pdf, 96 / 72).convert("L")
    assert gray.getpixel((100, 100)) == 0
    # Black up to the focal radius, then the ramp to white at r
    assert cast(int, gray.getpixel((100 + 25, 100))) < 8
    assert 60 < cast(int, gray.getpixel((100 + 56, 100))) < 200


@pytest.mark.parametrize("attributes", ['fx="0.3"', 'fr="0.6"'])
def test_other_focal_circles_keep_their_radius(attributes: str) -> None:
    # An off-center focus, a repeated spread, or fr past r: the shading keeps its own circles
    extra = "" if "fr=" in attributes else ' fr="0.2"'
    gradient = f'<radialGradient id="g"{extra} {attributes}><stop offset="0" stop-color="black"/><stop offset="1" stop-color="white"/></radialGradient>'
    pdf = render(svg(f'<defs>{gradient}</defs><rect x="20" y="20" width="160" height="160" fill="url(#g)"/>', height=200))
    coords = [[float(value) for value in found.split()] for found in re.findall(r"/Coords \[([^\]]*)\]", pdf.decode("latin-1"))]
    assert any(values[2] != 0 for values in coords)


def test_a_repeated_radial_spread_keeps_its_focal_circle() -> None:
    attributes = {"spreadMethod": "reflect", "fr": "0.2"}
    gradient = SimpleNamespace(tag="radialGradient", get=lambda key, default=None: attributes.get(key, default))
    assert paint._focal_ring(gradient, 16, 1) is None
