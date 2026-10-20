"""Vertical text: writing-mode tb, tb-rl, vertical-rl and vertical-lr, which WeasyPrint laid out horizontally.

Called by text.py for a <text> in a vertical writing mode and the <tspan> inside it. The run advances
down the y axis. CJK, kana and Hangul stand upright and advance by 1em; other characters lie sideways,
turned 90 degrees clockwise, centered on x by the middle of their em box, and advance by their width,
as in Chromium. x, y, dx and dy apply per character, rotate turns each one further, letter-spacing
adds to each advance, and text-anchor places each text chunk along y.

The text bounding box stays empty and text-anchor reads "start" to WeasyPrint (textpath.anchor_restyle).
"""

from __future__ import annotations

import math
from contextvars import ContextVar
from dataclasses import dataclass, field
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
    code = ord(glyphs.base(character))
    return any(low <= code <= high for low, high in UPRIGHT)


@dataclass
class _Run:
    """The vertical run of one <text>: its nodes, and the shift text-anchor gives each of their characters."""

    nodes: set[int]
    # By node id and character index: a node that draws twice, or not at all, moves no other one
    shifts: dict[tuple[int, int], float]

    def shift(self, node: Any, index: int) -> float:
        return self.shifts.get((id(node), index), 0.0)


CURRENT: ContextVar[_Run | None] = ContextVar("weasysvg_vertical", default=None)


def advance(character: str, width: float, font_size: float) -> float:
    return font_size if upright(character) else width


@dataclass
class _Chunk:
    """One text chunk: it starts at an absolute position, and text-anchor applies to each chunk alone."""

    first: float
    low: float = math.inf
    high: float = -math.inf
    characters: list[tuple[int, int]] = field(default_factory=list)  # node id and index of each character


def _chunks(svg: Any, texts: list[tuple[Any, float]], advances: Any) -> list[_Chunk]:
    """The chunks of the run, each character placed as draw places it, as in SVG 2 "apply anchoring".

    A chunk spans its characters, both ends of each advance, after x, y and dy. Its anchor point is the
    position of its first character.
    """
    y = svg.cursor_position[1]
    chunks: list[_Chunk] = []
    for text, size in texts:
        spacing = svg.length(text.get("letter-spacing"), size)
        xs, ys = _numbers(text, "x", size, svg.inner_width), _numbers(text, "y", size, svg.inner_height)
        dys = _numbers(text, "dy", size, svg.inner_height)
        for index, (character, width) in enumerate(advances(svg, text, size)):
            y = (ys[index] if index < len(ys) else y) + (dys[index] if index < len(dys) else 0)
            if not chunks or index < len(xs) or index < len(ys):
                chunks.append(_Chunk(y))
            chunk = chunks[-1]
            # letter-spacing belongs to the advance of each character, the last one included
            step = advance(character, width, size) + spacing
            chunk.low, chunk.high = min(chunk.low, y, y + step), max(chunk.high, y, y + step)
            chunk.characters.append((id(text), index))
            y += step
    return chunks


def start(svg: Any, node: Any, texts: list[tuple[Any, float]], advances: Any) -> _Run:
    """Begin a vertical <text>: measure each chunk of its text for text-anchor."""
    anchor = node.get(ANCHOR) or node.get("text-anchor", "start")
    shifts = {}
    for chunk in _chunks(svg, texts, advances):
        point = {"middle": (chunk.low + chunk.high) / 2, "end": chunk.high}.get(anchor, chunk.low)
        shifts.update(dict.fromkeys(chunk.characters, chunk.first - point))
    run = _Run({id(text) for text, _ in texts}, shifts)
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
    # Positions and advances in logical order, as the attributes give them
    places = []
    for index, (character, width) in enumerate(advances):
        x = (xs[index] if index < len(xs) else x) + (dxs[index] if index < len(dxs) else 0)
        y = (ys[index] if index < len(ys) else y) + (dys[index] if index < len(dys) else 0)
        step = advance(character, width, font_size) + spacing
        places.append([x, y, step])
        y += step
    svg.cursor_position = x, y
    # A right-to-left run turned sideways fills its span from its end: its last letter at the top
    text = "".join(glyphs.base(character) for character, _ in advances)
    for start, end in glyphs.rtl_runs(text):
        top = places[start][1]
        for index in glyphs.reversed_clusters(text, start, end):
            places[index][1] = top
            top += places[index][2]
    items = []
    for index, (character, width) in enumerate(advances):
        if character.strip():
            angle = rotations[min(index, len(rotations) - 1)] if rotations else 0.0
            items.append((character, _place(character, width, places[index][0], places[index][1] + run.shift(node, index), angle)))
    if not items:
        return
    svg.stream.push_state()
    try:
        fill, stroke = svg.set_graphical_state(node, font_size)
        glyphs.show(svg, style, fill, stroke, items)
    finally:
        svg.stream.pop_state()
