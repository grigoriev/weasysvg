"""SVG text: font-size keywords, nested text, dominant-baseline and text-decoration."""

from __future__ import annotations

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
