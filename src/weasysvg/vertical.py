"""Vertical text: writing-mode tb, tb-rl, vertical-rl and vertical-lr, which WeasyPrint laid out horizontally.

Called by text.py for a <text> in a vertical writing mode and the <tspan> inside it. The run advances
down the y axis. CJK, kana and Hangul stand upright and advance by 1em; other characters lie sideways,
turned 90 degrees clockwise, centered on x by the middle of their em box, and advance by their width,
as in Chromium. x, y, dx and dy apply per character, rotate turns each one further, letter-spacing
adds to each advance, and text-anchor places the run along y.

The text bounding box stays empty and text-anchor reads "start" to WeasyPrint (textpath.anchor_restyle).
"""

from __future__ import annotations

import math
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from weasyprint.matrix import Matrix
from weasyprint.svg import utils as wp_utils

from .textpath import ANCHOR

MODES = frozenset(("tb", "tb-rl", "vertical-rl", "vertical-lr"))
# Upright in vertical text (UAX 50, U): CJK, kana, Hangul, Bopomofo, fullwidth forms
UPRIGHT = (
    (0x1100, 0x11FF),
    (0x2E80, 0x2FDF),
    (0x3000, 0x303F),
    (0x3040, 0x31FF),
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xAC00, 0xD7AF),
    (0xF900, 0xFAFF),
    (0xFF00, 0xFFEF),
    (0x20000, 0x2FFFF),
)


def vertical(node: Any) -> bool:
    return str(node.get("writing-mode", "")).strip().lower() in MODES


def upright(character: str) -> bool:
    code = ord(character)
    return any(low <= code <= high for low, high in UPRIGHT)


@dataclass
class _Run:
    """The vertical run of one <text>: its nodes and the shift text-anchor gives it."""

    nodes: set[int]
    shift: float


CURRENT: ContextVar[_Run | None] = ContextVar("weasysvg_vertical", default=None)


def advance(character: str, width: float, font_size: float) -> float:
    return font_size if upright(character) else width


def start(svg: Any, node: Any, texts: list[tuple[Any, float]], advances: Any) -> _Run:
    """Begin a vertical <text>: measure all its text for text-anchor."""
    total = 0.0
    for text, size in texts:
        spacing = svg.length(text.get("letter-spacing"), size)
        total += sum(advance(character, width, size) + spacing for character, width in advances(svg, text, size))
    anchor = node.get(ANCHOR) or node.get("text-anchor", "start")
    shift = {"middle": -total / 2, "end": -total}.get(anchor, 0.0)
    run = _Run({id(text) for text, _ in texts}, shift)
    CURRENT.set(run)
    return run


def current(node: Any) -> _Run | None:
    run = CURRENT.get()
    return run if run is not None and id(node) in run.nodes else None


def _numbers(node: Any, name: str, font_size: float, reference: float) -> list[float]:
    return [wp_utils.size(value, font_size, reference) for value in wp_utils.normalize(node.get(name, "")).split()]


def draw(svg: Any, node: Any, font_size: float, run: _Run, style: Any, advances: list[tuple[str, float]]) -> None:
    """Draw each character of node down the y axis."""
    from weasyprint.draw.text import draw_first_line
    from weasyprint.svg.text import TextBox
    from weasyprint.text.line_break import split_first_line

    xs, ys = _numbers(node, "x", font_size, svg.inner_width), _numbers(node, "y", font_size, svg.inner_height)
    dxs, dys = _numbers(node, "dx", font_size, svg.inner_width), _numbers(node, "dy", font_size, svg.inner_height)
    rotations = [math.radians(float(value)) for value in wp_utils.normalize(node.get("rotate", "")).split()]
    spacing = svg.length(node.get("letter-spacing"), font_size)
    x, y = svg.cursor_position
    placed = []
    for index, (character, width) in enumerate(advances):
        x = xs[index] if index < len(xs) else x
        y = ys[index] if index < len(ys) else y
        x += dxs[index] if index < len(dxs) else 0
        y += dys[index] if index < len(dys) else 0
        angle = rotations[min(index, len(rotations) - 1)] if rotations else 0.0
        if character.strip():
            placed.append((character, width, x, y + run.shift, angle))
        y += advance(character, width, font_size) + spacing
    svg.cursor_position = x, y
    if not placed:
        return
    svg.stream.push_state()
    try:
        fill, stroke = svg.set_graphical_state(node, font_size)
        svg.stream.begin_text()
        for character, width, gx, gy, angle in placed:
            layout, _, _, _, height, baseline = split_first_line(character, style, svg.context, math.inf, 0)
            layout.reactivate(style)
            svg.fill_stroke(fill, stroke, text=True)
            box = TextBox(layout, style)
            box.baseline = baseline
            descent = height - baseline
            if upright(character):
                # The top of the em box at y, centered on x
                origin, turn = (gx - width / 2, gy + baseline), angle
            else:
                # Turned clockwise: the middle of the em box on x, the start of the glyph at y
                origin, turn = (gx - (baseline - descent) / 2, gy), angle + math.pi / 2
            cos, sin = math.cos(turn), math.sin(turn)
            draw_first_line(svg.stream, box, "none", "none", Matrix(cos, -sin, sin, cos) @ Matrix(d=-1, e=origin[0], f=origin[1]))
        svg.stream.end_text()
    finally:
        svg.stream.pop_state()
