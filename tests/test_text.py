"""SVG text: font-size keywords, nested text, dominant-baseline and text-decoration."""

from __future__ import annotations

import math
import re
from types import SimpleNamespace
from typing import Any
from xml.etree import ElementTree as ET

import pytest
from helpers import SVG_NS, RecordingStream, content, render, svg, text_of
from weasyprint import svg as wp_svg

from weasysvg import text
from weasysvg.text import baseline_shift, drop_nested_text


def font_sizes(pdf: bytes) -> list[float]:
    return [float(value) for value in re.findall(r" ([\d.]+) Tf", content(pdf))]


def text_matrix_y(pdf: bytes) -> list[float]:
    return [float(value) for value in re.findall(r"1 0 0 -1 [-\d.]+ ([-\d.]+) Tm", content(pdf))]


def rectangles(pdf: bytes) -> int:
    """The filled rectangles: the clip rectangles of the SVG viewport are followed by W."""
    return len(re.findall(r" re\n(?!W)", content(pdf)))


# ---------------- font-size keywords ----------------


@pytest.mark.parametrize(("keyword", "expected"), [("medium", 16), ("large", 18), ("initial", 16), ("xx-small", 9), ("larger", 24), ("smaller", 16.666)])
def test_font_size_keywords(keyword: str, expected: float) -> None:
    pdf = render(svg(f'<g font-size="20px"><text x="10" y="50" font-size="{keyword}">Size</text></g>'))
    assert font_sizes(pdf) == [pytest.approx(expected, abs=0.01)]


def test_font_size_unset_takes_the_parent() -> None:
    pdf = render(svg('<g font-size="20px"><text x="10" y="50" font-size="unset">A</text></g><text x="100" y="50" font-size="revert">B</text>'))
    # B has no parent size: it falls back to the 12pt default of WeasyPrint
    assert font_sizes(pdf) == [20, 16]


def test_cascade_on_itself_is_harmless(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(text, "_ORIGINAL_CASCADE", lambda self, child: None)
    node = type("Node", (), {"attrib": {"font-size": "unset"}})()
    text.cascade(node, node)
    assert node.attrib == {}


# ---------------- nested text ----------------


def test_nested_text_is_dropped() -> None:
    root = ET.fromstring(f'<svg xmlns="{SVG_NS}"><text>Outer<tspan>Span<text>Inner</text></tspan></text><g><text>Other</text></g></svg>')
    drop_nested_text(root)
    assert [element.text for element in root.iter() if element.tag.endswith("text")] == ["Outer", "Other"]


def test_nested_text_is_not_rendered() -> None:
    pdf = render(svg('<text x="10" y="50">Outer<text x="10" y="80">Inner</text></text>'))
    assert "Inner" not in text_of(pdf)
    assert "Outer" in text_of(pdf)


# ---------------- dominant-baseline ----------------


def test_baseline_shift_values() -> None:
    assert baseline_shift("central", 10, 2, 5) == 4
    assert baseline_shift("middle", 10, 2, 5) == 2.5
    assert baseline_shift("hanging", 10, 2, 5) == 8
    assert baseline_shift("text-before-edge", 10, 2, 5) == 10
    assert baseline_shift("text-after-edge", 10, 2, 5) == -2
    assert baseline_shift("ideographic", 10, 2, 5) == -2
    assert baseline_shift("mathematical", 10, 2, 5) == 5
    assert baseline_shift("text-top", 10, 2, 5) == 0


def baseline(attributes: str, tag: str = "text") -> float:
    body = f'<text x="10" y="50" font-size="20" {attributes}>Xx</text>' if tag == "text" else f'<text x="10" y="50" font-size="20"><tspan {attributes}>Xx</tspan></text>'
    pdf = render(svg(body))
    matrices = re.findall(r"1 0 0 1 0 ([-\d.]+) cm", content(pdf))
    shifts = [float(value) for value in matrices if float(value) != 0]
    return shifts[0] if shifts else 0.0


def test_central_shifts_down_by_the_font_metrics() -> None:
    assert 4 < baseline('dominant-baseline="central"') < 10
    assert 4 < baseline('dominant-baseline="middle"') < 10
    assert baseline('dominant-baseline="hanging"') > 10
    assert baseline('dominant-baseline="alphabetic"') == 0


def test_tspan_alignment_baseline() -> None:
    assert baseline('alignment-baseline="central"', tag="tspan") > 4


def test_attributes_are_restored_after_drawing() -> None:
    pdf = render(svg('<defs><text id="t" dominant-baseline="central">Twice</text></defs><use href="#t" x="10" y="30"/><use href="#t" x="10" y="70"/>'))
    assert text_of(pdf).split() == ["Twice", "Twice"]


def test_display_anchor_and_empty_text_keep_weasyprint() -> None:
    pdf = render(svg('<text x="10" y="50" display-anchor="middle" dominant-baseline="central">A</text><text x="10" y="80" dominant-baseline="central"></text>'))
    assert "A" in text_of(pdf)


def test_features_can_be_turned_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(text.FEATURES, "baseline", False)
    monkeypatch.setitem(text.FEATURES, "fonts", False)
    monkeypatch.setitem(text.FEATURES, "decoration", False)
    pdf = render(svg('<text x="10" y="50" dominant-baseline="central" text-decoration="underline">Off</text>'))
    assert "Off" in text_of(pdf)
    assert rectangles(pdf) == 0


# ---------------- text-decoration ----------------


@pytest.mark.parametrize(("value", "lines"), [("underline", 1), ("overline", 1), ("line-through", 1), ("underline line-through", 2), ("none", 0)])
def test_decoration_lines(value: str, lines: int) -> None:
    pdf = render(svg(f'<text x="10" y="50" font-size="20" text-decoration="{value}">Decor</text>'))
    assert rectangles(pdf) == lines


@pytest.mark.parametrize(
    ("font_size", "ascent", "underline_position", "underline_thickness", "expected"),
    [
        # Measured in Chromium: Liberation Serif at 24 px, Liberation Sans at 37 px
        (24, 21.39, -1.441, 1.172, [(2.0, 2.4), (-23.0, 2.4), (-8.2, 2.4)]),
        (37, 33.495, -1.210, 2.710, [(2.0, 3.7), (-36.0, 3.7), (-12.85, 3.7)]),
        # A font without an underline position: a gap of half the thickness, one at least
        (8, 7.0, 0.0, 0.5, [(1.0, 1.0), (-8.0, 1.0), (-2.833, 1.0)]),
    ],
)
def test_decoration_lines_sit_where_chromium_puts_them(font_size: float, ascent: float, underline_position: float, underline_thickness: float, expected: list[tuple[float, float]]) -> None:
    lines = text.chromium_lines(["underline", "overline", "line-through"], font_size, ascent, underline_position, underline_thickness)
    assert lines == [pytest.approx(line, abs=1e-3) for line in expected]


def test_decoration_lines_are_a_tenth_of_the_font_size() -> None:
    pdf = render(svg('<text x="10" y="50" font-size="30" text-decoration="underline">Decor</text>'))
    heights = [float(height) for height in re.findall(r"[-\d.]+ [-\d.]+ [-\d.]+ ([-\d.]+) re", content(pdf))]
    # The decoration is the one thin rectangle: the others are backgrounds
    assert [height for height in heights if height < 10] == [pytest.approx(3.0)]


@pytest.mark.parametrize("decoration", ["underline", "overline", "line-through"])
def test_decoration_lines_follow_the_scale_of_the_svg(decoration: str) -> None:
    # Chromium applies its rules in CSS px: font-size 3 at ten px per unit draws as font-size 30 at one
    def lines(body: str, extra: str = "") -> list[float]:
        found = re.findall(r"([-\d.]+) ([-\d.]+) [-\d.]+ ([-\d.]+) re", content(render(svg(body, extra=extra))))
        return [float(value) for line in found for value in (line[1], line[2]) if abs(float(line[2])) < 10]

    plain = lines(f'<text x="10" y="50" font-size="30" text-decoration="{decoration}">Decor</text>')
    scaled = lines(f'<text x="1" y="5" font-size="3" text-decoration="{decoration}">Decor</text>', ' viewBox="0 0 20 10"')
    assert plain
    assert scaled == [pytest.approx(value / 10, abs=1e-3) for value in plain]


def test_decoration_skips_positioned_glyphs_and_blank_runs() -> None:
    pdf = render(svg('<text x="10" y="50 60" text-decoration="underline">AB</text><text x="10" y="80" dy="1 2" text-decoration="underline">CD</text><text x="10" y="90" text-decoration="underline"> </text>'))
    assert rectangles(pdf) == 0


def test_font_weight_values() -> None:
    pdf = render(
        svg(
            '<text x="10" y="30" font-weight="bold" text-decoration="underline">B</text><text x="10" y="60" font-weight="bolder" text-decoration="underline">C</text><text x="10" y="90" font-weight="300" dominant-baseline="central">D</text>'
        )
    )
    assert rectangles(pdf) == 2


def test_install_again_keeps_the_replacement() -> None:
    text.install()
    assert wp_svg.TAGS["tspan"] is text.draw_text
    assert wp_svg.text is text.draw_text


def test_failing_decoration_lines_restore_the_state() -> None:
    stream = RecordingStream()

    def failing(*_args: Any) -> Any:
        raise RuntimeError("paint failed")

    fake, node = SimpleNamespace(stream=stream, set_graphical_state=failing, fill_stroke=failing), SimpleNamespace()
    with pytest.raises(RuntimeError):
        text._draw_lines(fake, node, 12, 0, 10, [(5, 1)])
    assert stream.depth == 0


def test_each_use_keeps_its_own_font_family() -> None:
    # One <text> drawn through two <use>: the family the first resolves must not stick to the node
    body = '<defs><text id="t" x="10" y="30">Hi</text></defs><use href="#t" font-family="Liberation Mono"/><use href="#t" y="40" font-family="DejaVu Serif"/>'
    pdf = render(svg(body, height=100))
    assert b"Liberation-Mono" in pdf
    assert b"DejaVu-Serif" in pdf


# ---------------- whole runs ----------------


def glyphs(pdf: bytes) -> list[str]:
    """The glyph ids the PDF shows, in order: a joined Arabic letter has another glyph than a lone one."""
    shown = "".join(re.findall(r"\[([^\]]*)\] TJ", content(pdf)))
    return re.findall(r"[0-9a-f]{4}", "".join(re.findall(r"<([0-9a-f]+)>", shown)))


def test_simple_runs_are_laid_out_whole(monkeypatch: pytest.MonkeyPatch) -> None:
    runs: list[str] = []
    original = text._draw_run

    def spy(svg_: Any, node: Any, size: float) -> None:
        runs.append(node.text)
        original(svg_, node, size)

    monkeypatch.setattr(text, "_draw_run", spy)
    body = '<text x="10" y="30" dx="2" dy="1" direction="rtl">whole</text><text x="10 20" y="60">split</text><text x="10" y="90" rotate="10">turned</text><text y="20" letter-spacing="3">spaced</text>'
    pdf = render(svg(body, height=100))
    assert runs == ["whole", "spaced"]
    assert "whole" in text_of(pdf)


def test_cursive_text_keeps_its_letters_joined() -> None:
    arabic = "بعض النص الطويل"
    plain = glyphs(render(svg(f'<text x="10" y="50" font-size="18">{arabic}</text>', width=300)))
    spaced = glyphs(render(svg(f'<text x="10" y="50" font-size="18" letter-spacing="10">{arabic}</text>', width=300)))
    # The spaces may go to runs of their own
    assert [glyph for glyph in spaced if glyph != "0003"] == [glyph for glyph in plain if glyph != "0003"]


def test_letter_spacing_reaches_the_spaces_only() -> None:
    # Two spaces between three Arabic words: 20 px wider, not 10 per letter
    style = text._style(SimpleNamespace(font_config=None), SimpleNamespace(get={"font-family": "DejaVu Sans"}.get), 18)
    from weasyprint.text.fonts import FontConfiguration
    from weasyprint.text.line_break import split_first_line

    style.font_config = FontConfiguration()
    layout, _, _, width, _, _ = split_first_line("بعض النص الطويل", style, None, float("inf"), 0)
    layout.reactivate(style)
    assert abs(text._track(layout, 10) - width - 20) < 3
    layout.deactivate()


def test_missing_glyphs_fall_back_to_sans_serif() -> None:
    # Chromium takes a character the family lacks from the sans-serif list: DejaVu Sans, not FreeSerif
    pdf = render(svg('<text x="10" y="50" font-family="serif">a بعض</text>', width=300))
    assert b"DejaVu-Sans" in pdf


# ---------------- textPath ----------------

WAVE = '<path id="w" d="M 20 80 C 60 20 140 20 180 80 S 300 140 420 60"/>'


def glyph_matrices(pdf: bytes) -> list[tuple[float, ...]]:
    return [tuple(float(value) for value in match) for match in re.findall(r"([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) Tm", content(pdf))]


def test_text_follows_its_path() -> None:
    pdf = render(svg(f'<defs>{WAVE}</defs><text><textPath href="#w">Wave</textPath></text>', width=440, height=160))
    matrices = glyph_matrices(pdf)
    assert len(matrices) == 4
    # The path climbs at the start: the first character is turned, counterclockwise on screen
    a, b = matrices[0][:2]
    assert a < 0.95
    assert b < -0.2
    assert "Wave" in text_of(pdf).replace("\r\n", "").replace(" ", "")


def test_text_path_offsets_anchors_and_tspans() -> None:
    body = f'<defs>{WAVE}</defs><text fill="blue" font-size="12"><textPath href="#w" startOffset="50%" text-anchor="middle" dx="1" dy="-2" letter-spacing="1">ab <tspan fill="red" dy="1">cd</tspan> ef</textPath></text>'
    pdf = render(svg(body, width=440, height=160))
    xs = [matrix[4] for matrix in glyph_matrices(pdf)]
    assert len(xs) == 6
    # The middle of the run sits near the middle of the path, about 230 units along it
    assert 180 < sum(xs) / len(xs) < 240


def test_text_path_from_the_path_attribute_and_a_transform() -> None:
    body = '<defs><path id="t" d="M 0 0 H 100" transform="translate(20 50)"/></defs><text><textPath href="#t">A</textPath></text><text><textPath path="M 20 90 H 120">B</textPath></text>'
    pdf = render(svg(body, height=120))
    matrices = glyph_matrices(pdf)
    assert [round(matrix[1], 3) for matrix in matrices] == [0, 0]
    assert sorted(round(matrix[5]) for matrix in matrices) == [50, 90]


@pytest.mark.parametrize("reference", ['path="q" href="w"', 'href="#nowhere"', 'href="#r"', ""])
def test_unresolvable_text_path_draws_nothing(reference: str) -> None:
    body = f'<defs>{WAVE}<rect id="r" width="1" height="1"/></defs><text><textPath {reference}>Gone <tspan>too</tspan></textPath></text>'
    pdf = render(svg(body, width=440, height=160))
    assert glyph_matrices(pdf) == []


def test_text_path_characters_off_the_path_are_not_drawn() -> None:
    body = '<text><textPath path="M 10 50 H 40">A long run of text</textPath></text>'
    assert 0 < len(glyph_matrices(render(svg(body)))) < 5


@pytest.mark.parametrize("decoration", ["underline", "overline", "line-through"])
def test_text_path_decorations(decoration: str) -> None:
    body = f'<text text-decoration="{decoration}" letter-spacing="2"><textPath path="M 10 50 H 190">a b</textPath></text>'
    pdf = render(svg(body))
    # One rectangle per character, the space included, each a closed path of four corners
    assert len(re.findall(r" l\n[-\d. ]+ l\n[-\d. ]+ l\nh", content(pdf))) == 3


def test_anchor_restyle_skips_plain_text() -> None:
    node_with = type("Node", (), {"tag": "text", "attrib": {}, "get": lambda self, *args: self.attrib.get(*args), "__iter__": lambda self: iter(())})()
    assert text.anchor_restyle(None, node_with, 12) is None
    assert text.anchor_restyle(None, SimpleNamespace(tag="g"), 12) is None


def test_text_path_anchored_at_its_end() -> None:
    # No direct text and a child that is no text: the <tspan> alone ends at the end of the path
    body = '<text text-anchor="end"><textPath path="M 10 50 H 190" startOffset="100%"><desc>note</desc><tspan>end</tspan></textPath></text>'
    xs = [matrix[4] for matrix in glyph_matrices(render(svg(body)))]
    assert len(xs) == 3
    assert 150 < min(xs) < 190


# ---------------- vertical text ----------------


def test_vertical_text_runs_down() -> None:
    body = '<text x="50" y="20" writing-mode="tb" font-size="20">AB<tspan fill="red">日</tspan></text>'
    matrices = glyph_matrices(render(svg(body, height=120)))
    assert len(matrices) == 3
    (a1, b1, *_rest1, ya), (_a2, _b2, *_rest2, yb), (a3, b3, *_rest3, yc) = matrices
    # Latin lies sideways, turned clockwise; the CJK character stands upright below it
    assert round(a1, 3) == 0
    assert round(b1, 3) == 1
    assert (round(a3, 3), round(b3, 3)) == (1, 0)
    assert ya < yb < yc


@pytest.mark.parametrize(("anchor", "first"), [("start", 100), ("middle", 80), ("end", 60)])
def test_vertical_text_anchor(anchor: str, first: float) -> None:
    body = f'<text x="50" y="100" writing-mode="vertical-rl" text-anchor="{anchor}" font-size="20" letter-spacing="0">日本</text>'
    matrices = glyph_matrices(render(svg(body, height=200)))
    # Upright: the baseline of the first character lies its ascent below the top of its em box
    assert first < matrices[0][5] < first + 20


@pytest.mark.parametrize(("anchor", "first"), [("start", 140), ("middle", 110), ("end", 80)])
def test_vertical_text_anchor_spans_the_glyphs_after_dy(anchor: str, first: float) -> None:
    # The second character moves up past the first: the run spans from its top to the end of the first
    body = f'<text x="50" y="100" dy="0 -60" writing-mode="vertical-rl" text-anchor="{anchor}" font-size="20" letter-spacing="0">日本</text>'
    matrices = glyph_matrices(render(svg(body, height=200)))
    assert first < matrices[0][5] < first + 20


def test_vertical_text_positions_and_rotation() -> None:
    body = '<text x="50 80" y="30" dx="1" dy="2" rotate="30" writing-mode="tb" font-size="20">A B</text>'
    matrices = glyph_matrices(render(svg(body, height=120)))
    assert matrices[1][4] > matrices[0][4] + 20
    # Sideways and turned 30 degrees further: 120 degrees in all
    assert round(math.degrees(math.atan2(matrices[0][1], matrices[0][0]))) == 120
    assert glyph_matrices(render(svg('<text x="50" y="30" writing-mode="tb">   </text>'))) == []


@pytest.mark.parametrize("value", ["10 abc", "10 inf", "nan"])
@pytest.mark.parametrize("mode", ["", ' writing-mode="tb"'])
def test_a_broken_rotate_is_ignored(mode: str, value: str) -> None:
    # WeasyPrint parses rotate during the cascade and turns by it: "abc" or "inf" lost the whole SVG
    matrices = glyph_matrices(render(svg(f'<text x="50 60" y="30"{mode} rotate="{value}">AB</text><g rotate="x"/>')))
    assert len(matrices) == 2
    assert [round(matrix[1], 3) for matrix in matrices] == ([1, 1] if mode else [0, 0])
