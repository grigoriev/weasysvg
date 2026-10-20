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

from weasyprint.svg import utils as wp_utils

from . import glyphs
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


def _extent(svg: Any, texts: list[tuple[Any, float]], advances: Any) -> tuple[float, float]:
    """The top and bottom of all characters, relative to the start of the run, y and dy included as draw places them."""
    first = _numbers(texts[0][0], "y", texts[0][1], svg.inner_height)
    origin = first[0] if first else svg.cursor_position[1]
    y, low, high = origin, origin, origin
    for text, size in texts:
        spacing = svg.length(text.get("letter-spacing"), size)
        ys, dys = _numbers(text, "y", size, svg.inner_height), _numbers(text, "dy", size, svg.inner_height)
        for index, (character, width) in enumerate(advances(svg, text, size)):
            y = (ys[index] if index < len(ys) else y) + (dys[index] if index < len(dys) else 0)
            # letter-spacing belongs to the advance of each character, the last one included
            step = advance(character, width, size) + spacing
            low, high = min(low, y), max(high, y + step)
            y += step
    return low - origin, high - origin


def start(svg: Any, node: Any, texts: list[tuple[Any, float]], advances: Any) -> _Run:
    """Begin a vertical <text>: measure all its text for text-anchor.

    Chromium anchors the extent of the characters, so a dy that moves one past the start moves the run.
    """
    low, high = _extent(svg, texts, advances)
    anchor = node.get(ANCHOR) or node.get("text-anchor", "start")
    shift = {"middle": -(low + high) / 2, "end": -high}.get(anchor, -low)
    run = _Run({id(text) for text, _ in texts}, shift)
    CURRENT.set(run)
    return run


def current(node: Any) -> _Run | None:
    run = CURRENT.get()
    return run if run is not None and id(node) in run.nodes else None


def _numbers(node: Any, name: str, font_size: float, reference: float) -> list[float]:
    return [wp_utils.size(value, font_size, reference) for value in wp_utils.normalize(node.get(name, "")).split()]


def _place(character: str, width: float, x: float, y: float, angle: float) -> glyphs.Place:
    """Upright: the top of the em box at y, centered on x. Sideways: turned clockwise, the middle of
    the em box on x, the start of the glyph at y."""

    def place(height: float, baseline: float) -> tuple[tuple[float, float], float]:
        if upright(character):
            return (x - width / 2, y + baseline), angle
        descent = height - baseline
        return (x - (baseline - descent) / 2, y), angle + math.pi / 2

    return place


def draw(svg: Any, node: Any, font_size: float, run: _Run, style: Any, advances: list[tuple[str, float]]) -> None:
    """Draw each character of node down the y axis."""
    xs, ys = _numbers(node, "x", font_size, svg.inner_width), _numbers(node, "y", font_size, svg.inner_height)
    dxs, dys = _numbers(node, "dx", font_size, svg.inner_width), _numbers(node, "dy", font_size, svg.inner_height)
    rotations = [math.radians(float(value)) for value in wp_utils.normalize(node.get("rotate", "")).split()]
    spacing = svg.length(node.get("letter-spacing"), font_size)
    x, y = svg.cursor_position
    items = []
    for index, (character, width) in enumerate(advances):
        x = (xs[index] if index < len(xs) else x) + (dxs[index] if index < len(dxs) else 0)
        y = (ys[index] if index < len(ys) else y) + (dys[index] if index < len(dys) else 0)
        if character.strip():
            angle = rotations[min(index, len(rotations) - 1)] if rotations else 0.0
            items.append((character, _place(character, width, x, y + run.shift, angle)))
        y += advance(character, width, font_size) + spacing
    svg.cursor_position = x, y
    if not items:
        return
    svg.stream.push_state()
    try:
        fill, stroke = svg.set_graphical_state(node, font_size)
        glyphs.show(svg, style, fill, stroke, items)
    finally:
        svg.stream.pop_state()
