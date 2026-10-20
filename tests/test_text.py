"""SVG text: font-size keywords, nested text, dominant-baseline and text-decoration."""

from __future__ import annotations

import io
import math
import re
from collections import OrderedDict
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from xml.etree import ElementTree as ET

import pytest
from fontTools.ttLib import TTFont
from helpers import SVG_NS, RecordingStream, content, render, svg, text_of
from weasyprint import svg as wp_svg
from weasyprint.text.fonts import get_hb_object_data

from weasysvg import glyphs as glyph_layout
from weasysvg import ink, text
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
    ("font_size", "ascent", "expected"),
    [
        # Measured in Chromium: Liberation Serif at 24 px, Liberation Sans at 37 px, and a small font
        (24, 21.39, [(2.0, 2.4), (-23.0, 2.4), (-8.2, 2.4)]),
        (37, 33.495, [(2.0, 3.7), (-36.0, 3.7), (-12.85, 3.7)]),
        # At 8 px the line is drawn 1 px thick, but placed by its 0.8
        (8, 7.0, [(1.0, 1.0), (-7.0, 1.0), (-2.733, 1.0)]),
    ],
)
def test_decoration_lines_sit_where_chromium_puts_them(font_size: float, ascent: float, expected: list[tuple[float, float]]) -> None:
    lines = text.chromium_lines(["underline", "overline", "line-through"], font_size, ascent)
    assert lines == [pytest.approx(line, abs=1e-3) for line in expected]


@pytest.mark.parametrize(
    ("font_size", "gap"),
    [
        # Read from the PDF Chromium prints, for Liberation Sans, Liberation Sans Bold, Liberation Serif,
        # Noto Sans and DejaVu Sans alike: the gap follows the thickness of the line, not the font
        (8, 1.0),
        (12, 1.0),
        (18, 1.0),
        (24, 2.0),
        (37, 2.0),
        (60, 3.0),
    ],
)
def test_the_underline_gap_follows_the_line_not_the_font(font_size: float, gap: float) -> None:
    assert text.chromium_lines(["underline"], font_size, font_size * 0.9)[0][0] == gap


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


def line_pieces(pdf: bytes) -> list[tuple[float, float]]:
    """The left and right end of each thin rectangle: the pieces of the decoration lines."""
    found = re.findall(r"([-\d.]+) [-\d.]+ ([-\d.]+) ([-\d.]+) re", content(pdf))
    return sorted((float(x), float(x) + float(width)) for x, width, height in found if 0 < float(height) < 10)


@pytest.mark.parametrize(("decoration", "pieces"), [("underline", 2), ("overline", 1), ("line-through", 1)])
def test_an_underline_skips_the_ink_of_descenders(decoration: str, pieces: int) -> None:
    # "agya": the descenders of g and y cut one gap in the underline, their gaps merged; nothing crosses the
    # overline, and a line-through skips no ink
    pdf = render(svg(f'<text x="10" y="60" font-size="40" text-decoration="{decoration}">agya</text>', height=100))
    assert len(line_pieces(pdf)) == pieces


@pytest.mark.parametrize("body", ['<text x="10" y="50" text-decoration="underline">_</text>', '<path id="p" d="M 10 50 H 200" fill="none"/><text text-decoration="underline"><textPath href="#p">_</textPath></text>'])
def test_a_line_all_under_ink_paints_no_empty_path(body: str) -> None:
    # The underscore crosses the whole underline: nothing is left to fill, and a paint operator needs a path
    lines = content(render(svg(body))).split("\n")
    painted = [lines[index - 1] for index, line in enumerate(lines) if line in ("f", "S", "B")]
    assert all(line.endswith((" re", " l", " c", " m", "h")) for line in painted)


def test_a_line_without_descenders_is_whole() -> None:
    assert len(line_pieces(render(svg('<text x="10" y="60" font-size="40" text-decoration="underline">Decor</text>', height=100)))) == 1


def test_a_gap_clears_the_ink_by_the_thickness_of_the_line() -> None:
    # The gap around the g: its ink in the band of the line, 4 units wider on each side, within its advance
    pdf = render(svg('<text x="10" y="60" font-size="40" text-decoration="underline">ogo</text>', height=100))
    (_, gap_start), (gap_end, _) = line_pieces(pdf)
    assert 8 < gap_end - gap_start < 8 + 0.7 * 40


@pytest.mark.parametrize(
    ("cuts", "expected"),
    [
        ([(40, 50)], [(0, 36), (54, 100)]),
        # Gaps that meet merge; a gap past an end leaves no piece there
        ([(40, 50), (55, 60), (98, 120)], [(0, 36), (64, 94)]),
        ([(-10, 120)], []),
        ([], [(0, 100)]),
    ],
)
def test_skipped_pieces(cuts: list[tuple[float, float]], expected: list[tuple[float, float]]) -> None:
    assert ink.skipped(0, 100, cuts, 4) == expected


def test_the_band_of_a_cubic_curve() -> None:
    # A CFF font draws cubic curves: the curve and the closing line cross y = 0 near x = 50
    pen = ink._BandPen(None, -10, 10)
    pen.moveTo((0, -50))
    pen.curveTo((0, 0), (100, 0), (100, 50))
    pen.closePath()
    assert 30 < pen.left < pen.right < 70


def test_a_glyph_outside_its_font_has_no_ink() -> None:
    path = Path(__file__).resolve().parents[1] / "corpus" / "fonts" / "NotoSans-Regular.ttf"
    ink._FONTS["test"] = (path.read_bytes(), 0, 1000)
    assert ink._extent("test", 10**6, 0, 1) is None


def test_a_font_without_outlines_has_no_ink() -> None:
    # A color emoji font holds bitmaps only (CBDT, sbix): no glyf, CFF or CFF2 table to read outlines from
    font = TTFont(Path(__file__).resolve().parents[1] / "corpus" / "fonts" / "NotoSans-Regular.ttf")
    del font["glyf"], font["loca"]
    data = io.BytesIO()
    font.save(data)
    ink._FONTS["bitmaps"] = (data.getvalue(), 0, 1000)
    assert ink._extent("bitmaps", 10, 0, 1) is None


def test_a_character_no_font_has_cuts_nothing() -> None:
    # The .notdef box of an unknown character is no glyph of the run: the underline stays whole
    pdf = render(svg('<text x="10" y="60" font-size="40" text-decoration="underline">\U0010fffd</text>', height=100))
    assert len(line_pieces(pdf)) == 1


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
        text._draw_lines(fake, node, 12, [(0, 5, 10, 1)])
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


@pytest.mark.parametrize("effect", ['clip-path="url(#c)"', 'filter="url(#f)"'])
def test_an_effect_on_a_tspan_keeps_its_place_on_the_path(effect: str) -> None:
    # The tspan is measured before its effect: that draw must not move the text along the path
    defs = f'{WAVE}<clipPath id="c"><rect width="440" height="160"/></clipPath><filter id="f"><feOffset/></filter>'
    plain = f'<defs>{defs}</defs><text font-size="12"><textPath href="#w">ab <tspan>cd</tspan> ef</textPath></text>'
    pdf = render(svg(plain.replace("<tspan>", f"<tspan {effect}>"), width=440, height=160))
    assert glyph_matrices(pdf) == glyph_matrices(render(svg(plain, width=440, height=160)))


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


@pytest.mark.parametrize(("dy", "anchor", "first"), [("-10", "start", 90), ("50", "end", 110), ("50", "middle", 130)])
def test_vertical_text_anchor_starts_at_the_first_character(dy: str, anchor: str, first: float) -> None:
    # The anchor point is where the first character lands, after its dy
    body = f'<text x="50" y="100" dy="{dy}" writing-mode="vertical-rl" text-anchor="{anchor}" font-size="20" letter-spacing="0">日本</text>'
    matrices = glyph_matrices(render(svg(body, height=300)))
    assert first < matrices[0][5] < first + 20


def test_each_vertical_text_chunk_is_anchored_alone() -> None:
    # y="100 200" starts two chunks: each ends at its own y
    body = '<text x="50" y="100 200" writing-mode="vertical-rl" text-anchor="end" font-size="20" letter-spacing="0">日本</text>'
    matrices = glyph_matrices(render(svg(body, height=300)))
    assert 80 < matrices[0][5] < 100
    assert 180 < matrices[1][5] < 200


def test_a_backward_advance_counts_in_the_extent() -> None:
    # letter-spacing -30 makes each advance -10: the run spans 80 to 100, its end is the start of the first
    body = '<text x="50" y="100" writing-mode="vertical-rl" text-anchor="end" font-size="20" letter-spacing="-30">日本</text>'
    matrices = glyph_matrices(render(svg(body, height=300)))
    assert 100 < matrices[0][5] < 120


@pytest.mark.parametrize("hidden", ['display="none"', 'visibility="hidden"'])
def test_a_hidden_vertical_tspan_keeps_the_shifts_of_the_rest(hidden: str) -> None:
    # The chunk of 本 ends at 200 whether or not the <tspan> before it draws
    body = f'<text x="50" y="100" writing-mode="vertical-rl" text-anchor="end" font-size="20" letter-spacing="0">日<tspan {hidden}>月</tspan><tspan y="200">本</tspan></text>'
    matrices = glyph_matrices(render(svg(body, height=300)))
    assert 180 < matrices[-1][5] < 200


def test_vertical_text_anchor_counts_absolute_y() -> None:
    # The second character starts anew at 200 and moves up 60: the run spans 100 to 160
    body = '<text x="50" y="100 200" dy="0 -60" writing-mode="vertical-rl" text-anchor="start" font-size="20" letter-spacing="0">日本</text>'
    matrices = glyph_matrices(render(svg(body, height=300)))
    assert 100 < matrices[0][5] < 120
    assert 140 < matrices[1][5] < 160


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


# ---------------- text chunks ----------------


@pytest.mark.parametrize("anchor", ["middle", "end"])
@pytest.mark.parametrize(
    "inner",
    [
        '<tspan>1</tspan><tspan x="50" dy="25">H</tspan>',
        # The chunk one level down, in a tspan that starts none: its box still stays out of the anchor of "1"
        '<tspan>1<tspan x="50" dy="25">H</tspan></tspan>',
    ],
)
def test_each_text_chunk_is_anchored_by_its_own_width(anchor: str, inner: str) -> None:
    # A tspan with its own x starts a chunk: "1" is anchored by its width alone, "H" by its own
    body = f'<text x="50" y="40" font-size="20" text-anchor="{anchor}">{inner}</text>'
    single = f'<text x="50" y="40" font-size="20" text-anchor="{anchor}">1</text><text x="50" y="65" font-size="20" text-anchor="{anchor}">H</text>'
    shifts = re.findall(r"1 0 0 1 (-[\d.]+) 0 cm", content(render(svg(body, height=120))))
    expected = re.findall(r"1 0 0 1 (-[\d.]+) 0 cm", content(render(svg(single, height=120))))
    assert sorted(shifts) == sorted(expected)


class TextNode(list[Any]):
    """A text node as chunk_boxes sees it: tag, attributes, children and the box WeasyPrint drew."""

    def __init__(self, tag: str, box: tuple[float, float, float, float] | None, children: tuple[Any, ...] = (), attrib: dict[str, str] | None = None) -> None:
        super().__init__(children)
        self.tag, self.attrib, self.text_bounding_box = tag, attrib or {}, box

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.attrib.get(key, default)


@pytest.mark.parametrize("extra", ["", '<tspan x="150" font-size="10pt" dy="16">and more</tspan>'])
def test_the_space_after_a_chunk_belongs_to_that_chunk(extra: str) -> None:
    # The white space between the tspans of a chunk, after it, must not widen the chunk before it: the
    # title is anchored alike with one line under it or two
    def title_shift(lines: tuple[str, ...]) -> str:
        body = '<text y="40" x="150" text-anchor="middle">\n  ' + "\n  ".join(lines) + "\n</text>"
        return str(re.findall(r"1 0 0 1 (-[\d.]+) 0 cm", content(render(svg(body, width=300, height=120))))[-1])

    two = ("<tspan>Transport</tspan>", '<tspan x="150" font-size="10pt" dy="16">End-to-End</tspan>')
    assert title_shift((*two, extra) if extra else two) == title_shift(two[:1] + ('<tspan x="150" font-size="10pt" dy="16">End</tspan>',))


def test_text_nested_in_a_later_chunk_belongs_to_that_chunk() -> None:
    # The bold tspan and the tail " end" lie inside the second chunk: the first chunk, drawn before, must
    # not take them, or the second line is anchored by "two " alone
    def shifts(first: str) -> list[str]:
        body = f'<text y="40" x="150" text-anchor="middle">{first}<tspan x="150" dy="16">two <tspan font-weight="bold">bold</tspan> end</tspan></text>'
        return re.findall(r"1 0 0 1 (-[\d.]+) 0 cm", content(render(svg(body, width=300, height=120))))

    assert shifts('<tspan x="150">one</tspan>')[-1] == shifts("")[-1]


def test_measuring_a_text_keeps_the_last_chunk() -> None:
    # The scratch draw before a filter meets the chunks of the text: the real draw must start where it did
    from weasysvg import _core

    group = SimpleNamespace(id="scratch")
    stream = SimpleNamespace(add_group=lambda *_: group, _resources={"XObject": {}})
    drawn = TextNode("tspan", (0, 0, 0, 0), attrib={"x": "1"})
    scratch = SimpleNamespace(stream=stream, cursor_position=(0, 0), cursor_d_position=[0, 0], draw_node=lambda node, _: text.LAST_CHUNK.set(drawn))
    before = TextNode("tspan", (0, 0, 0, 0), attrib={"x": "0"})
    token = text.LAST_CHUNK.set(before)
    try:
        _core.measure_text(scratch, TextNode("tspan", None, (drawn,)), 16)
        assert text.LAST_CHUNK.get() is before
    finally:
        text.LAST_CHUNK.reset(token)


def test_a_chunked_text_keeps_the_box_of_all_its_chunks() -> None:
    # Drawn inside out: the chunk "H" one level down, the tspan around it, then the text
    chunk = TextNode("tspan", (90, 45, 20, 25), attrib={"x": "90"})
    middle = TextNode("tspan", (10, 20, 10, 25), (chunk,))
    root = TextNode("text", (10, 20, 10, 25), (middle,))
    for node in (chunk, middle, root):
        text.chunk_boxes(None, node)
    # The text spans both chunks again, the chunk has its own box back, the tspan between never had it
    assert root.text_bounding_box == (10, 20, 100, 50)
    assert chunk.text_bounding_box == (90, 45, 20, 25)
    assert middle.text_bounding_box == (10, 20, 10, 25)
    assert all(text.CHUNK_BOX not in vars(node) for node in (chunk, middle, root))


@pytest.mark.parametrize(("anchor", "direction", "x"), [("start", "ltr", 50), ("middle", "ltr", 40), ("end", "ltr", 30), ("start", "rtl", 30), ("end", "rtl", 50)])
def test_the_box_of_a_text_lies_where_its_anchor_puts_it(anchor: str, direction: str, x: float) -> None:
    # WeasyPrint keeps the box before the anchor shift: effects of the text need the box as drawn
    node = TextNode("text", (50, 20, 20, 25), attrib={"text-anchor": anchor, "direction": direction})
    text.chunk_boxes(None, node)
    assert node.text_bounding_box == (x, 20, 20, 25)


# ---------------- leading shifts ----------------


class TextStream:
    """The part of the PDF stream draw_first_line writes text with."""

    def __init__(self) -> None:
        self.stream: list[bytes] = []

    def show_text(self, text: str) -> None:
        self.stream.append(b"[" + text.encode() + b"] TJ")

    def set_font_size(self, font: str, size: float) -> None:
        self.stream.append(f"/{font} {size} Tf".encode())

    def set_text_rise(self, rise: float) -> None:
        self.stream.append(f"{rise} Ts".encode())


def test_a_leading_shift_moves_to_the_end_of_the_array_before() -> None:
    stream = TextStream()
    with text.carried_shifts(stream):
        stream.set_font_size("f1", 18)
        stream.show_text("<0001>")
        stream.show_text("<>-284.5<0003>-271")
        # Another font of another size: the shift is scaled to the size of the array before
        stream.set_font_size("f2", 9)
        stream.show_text("-100<0004>")
        stream.set_text_rise(2)
        # Not right after an array: the shift stays
        stream.show_text("<>-50<0005>")
    assert stream.stream == [b"/f1 18 Tf", b"[<0001> -284.5] TJ", b"[<0003>-271 -50.0] TJ", b"/f2 9 Tf", b"[<0004>] TJ", b"2 Ts", b"[<>-50<0005>] TJ"]


def test_a_first_leading_shift_stays() -> None:
    stream = TextStream()
    with text.carried_shifts(stream):
        stream.show_text("<>-10<0001>")
    assert stream.stream == [b"[<>-10<0001>] TJ"]
    # The methods of the stream are its own again
    assert "show_text" not in vars(stream)


def test_carried_shifts_restores_an_override_of_the_stream() -> None:
    # Another patch replaced show_text on this stream first: it is back afterwards, not deleted
    stream = TextStream()
    shown: list[str] = []
    vars(stream)["show_text"] = shown.append
    with text.carried_shifts(stream):
        stream.show_text("<0001>")
    stream.show_text("<0002>")
    assert shown == ["<0001>", "<0002>"]
    assert "set_font_size" not in vars(stream)


def test_arabic_letter_spacing_needs_no_leading_shift() -> None:
    body = '<text x="38" y="100" font-size="18" letter-spacing="10">بعض النص الطويل</text>'
    arrays = re.findall(r"\[([^\]]*)\] TJ", content(render(svg(body, height=200))))
    assert len(arrays) > 1
    assert not any(re.match(r"(<>)?-?[\d.]", array) for array in arrays[1:])


def test_text_without_underline_or_overline_reads_no_glyphs(monkeypatch: pytest.MonkeyPatch) -> None:
    # Only a line that skips ink needs the glyphs: other text pays nothing for it
    calls: list[Any] = []

    def recording(*args: Any) -> list[ink.Glyph]:
        calls.append(args)
        return []

    monkeypatch.setattr(ink, "run_glyphs", recording)
    pdf = render(svg('<text x="10" y="50">plain</text><text x="10" y="80" text-decoration="line-through">struck</text>'))
    assert "plain" in text_of(pdf)
    assert calls == []


def test_a_font_file_is_read_once(monkeypatch: pytest.MonkeyPatch) -> None:
    # Each run of each text reads the same font, at five sizes: its file is read and hashed once
    reads: list[Any] = []

    def recording(face: Any) -> Any:
        reads.append(face)
        return get_hb_object_data(face)

    monkeypatch.setattr(ink, "get_hb_object_data", recording)
    ink._FACES.clear()
    lines = "".join(f'<text x="10" y="{20 + 15 * index}" font-size="{12 + index}" text-decoration="underline">line {index}</text>' for index in range(5))
    render(svg(lines, height=100))
    assert len(reads) == 1


def test_a_glyph_of_a_dropped_font_has_no_ink_until_it_comes_back() -> None:
    # The run was laid out, then its font left the bounded cache: the line keeps its piece. Once the font
    # is read again, its glyphs cut the line again
    path = Path(__file__).resolve().parents[1] / "corpus" / "fonts" / "NotoSans-Regular.ttf"
    font = TTFont(path)
    glyph = ink.Glyph("dropped", font.getGlyphID("p"), 0, 0, 0.01)
    ink._FONTS.pop("dropped", None)
    assert ink.intercepts([glyph], 0, 1) == []
    ink._FONTS["dropped"] = (path.read_bytes(), 0, 1000)
    assert len(ink.intercepts([glyph], 0, 1)) == 1


@pytest.fixture
def fresh_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Caches of this test alone: fake faces must not stay under addresses a real face can take later."""
    monkeypatch.setattr(ink, "_FACES", OrderedDict())
    monkeypatch.setattr(ink, "_FONTS", OrderedDict())


def test_an_unreadable_font_has_no_ink(fresh_caches: None) -> None:
    # HarfBuzz may take a font fontTools rejects: the line stays whole, the render goes on
    ink._FONTS["unreadable"] = (b"no font at all", 0, 1000)
    assert ink.intercepts([ink.Glyph("unreadable", 1, 0, 0, 0.01)], 0, 1) == []


@pytest.mark.usefixtures("fresh_caches")
def test_the_faces_of_one_collection_have_keys_of_their_own(monkeypatch: pytest.MonkeyPatch) -> None:
    # A .ttc file holds several faces: each face reads its own outlines
    from weasyprint.text.ffi import ffi

    faces = [ffi.new("int *", index) for index in range(2)]
    monkeypatch.setattr(ink, "get_pango_font_hb_face", lambda font: font)
    monkeypatch.setattr(ink, "get_hb_object_data", lambda face: bytes(bytearray(b"one collection")))
    monkeypatch.setattr(ink, "harfbuzz", SimpleNamespace(hb_face_get_index=lambda face: face[0], hb_face_get_upem=lambda face: 1000))
    keys = [ink._font_key(face) for face in faces]
    assert keys[0] != keys[1]
    assert [ink._FONTS[key][1] for key in keys] == [0, 1]
    # One copy of the file serves both faces
    assert ink._FONTS[keys[0]][0] is ink._FONTS[keys[1]][0]


@pytest.mark.usefixtures("fresh_caches")
def test_the_font_caches_are_bounded() -> None:
    for index in range(ink.MAX_FONTS + 10):
        ink._remember(ink._FACES, index, (str(index), None))
    assert len(ink._FACES) == ink.MAX_FONTS
    assert 0 not in ink._FACES


# ---------------- joining scripts laid out one character at a time ----------------

ZWJ = "\u200d"


def test_each_arabic_letter_is_shaped_in_its_joining_context() -> None:
    # "اليابان": alef and the letters after an alef join nothing on their right side
    word = "\u0627\u0644\u064a\u0627\u0628\u0627\u0646"
    expected = ["\u0627", "\u0644" + ZWJ, ZWJ + "\u064a" + ZWJ, ZWJ + "\u0627", "\u0628" + ZWJ, ZWJ + "\u0627", "\u0646"]
    assert [glyph_layout.in_context(word, index) for index in range(len(word))] == expected


def test_marks_and_other_scripts_keep_their_letters_alone() -> None:
    # A mark between two letters does not break their joining; Latin and spaces join nothing
    word = "\u0628\u064e\u0628 ab"
    assert [glyph_layout.in_context(word, index) for index in range(len(word))] == ["\u0628" + ZWJ, "\u064e", ZWJ + "\u0628", " ", "a", "b"]


def test_a_tatweel_joins_both_sides() -> None:
    word = "\u0628\u0640\u0627"
    assert [glyph_layout.in_context(word, index) for index in range(len(word))] == ["\u0628" + ZWJ, "\u0640", ZWJ + "\u0627"]


@pytest.mark.parametrize("body", ['<text x="50" y="20" writing-mode="tb" font-size="20">\u0644\u0644</text>', '<path id="p" d="M 10 50 H 190" fill="none"/><text font-size="20"><textPath href="#p">\u0644\u0644</textPath></text>'])
def test_arabic_letters_laid_out_alone_still_join(body: str) -> None:
    # Two lams: an initial and a final form, two glyphs, where isolated forms would repeat one
    drawn = re.findall(r"\[<([0-9a-f]+)>[^\]]*\] TJ", content(render(svg(body, height=200))))
    assert len(drawn) == 2
    assert drawn[0] != drawn[1]


def test_a_right_to_left_run_is_reversed() -> None:
    # Latin stays, the Arabic run with its inner space turns around by clusters: the mark stays after its letter
    text = "ab \u0627\u064e\u0644 \u062f c"
    assert glyph_layout.visual_order(text) == [0, 1, 2, 7, 6, 5, 3, 4, 8, 9]


def test_a_vertical_arabic_run_keeps_its_place() -> None:
    # Sideways, the right end of a right-to-left run lies at the top: the dal, then the alef, as in Chromium.
    # The y of the text belongs to the alef, the first in logical order: the run starts there all the same
    pdf = render(svg('<text x="50" y="20" writing-mode="tb" font-size="20">\u0627\u062f</text>', height=200))
    placed = re.findall(r"[-\d.]+ ([-\d.]+) Tm\n(?:[^\n]*Tf\n)?\[<([0-9a-f]+)>", content(pdf))
    dal = re.findall(r"\[<([0-9a-f]+)>", content(render(svg('<text x="50" y="20" writing-mode="tb" font-size="20">\u062f</text>', height=200))))[0]
    ys = {glyph: float(y) for y, glyph in placed}
    assert ys[dal] == pytest.approx(20)
    assert min(ys.values()) == pytest.approx(20)
    assert max(ys.values()) > 25


def test_a_positioned_letter_keeps_its_place_in_a_vertical_run() -> None:
    # A y of its own starts a new chunk: the dal stays at 80, below the alef at 20
    pdf = render(svg('<text x="50" y="20 80" writing-mode="tb" font-size="20">\u0627\u062f</text>', height=200))
    dal = re.findall(r"\[<([0-9a-f]+)>", content(render(svg('<text x="50" y="20" writing-mode="tb" font-size="20">\u062f</text>', height=200))))[0]
    ys = {glyph: float(y) for y, glyph in re.findall(r"[-\d.]+ ([-\d.]+) Tm\n(?:[^\n]*Tf\n)?\[<([0-9a-f]+)>", content(pdf))}
    assert ys[dal] == pytest.approx(80)
    assert min(ys.values()) == pytest.approx(20)
