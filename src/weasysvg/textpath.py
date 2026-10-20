"""Text on a path: <textPath>, which WeasyPrint drew as plain text on the baseline.

Called by text.py for a <textPath> and for the <tspan> inside one. SVG 2: the path comes from the path
attribute, else from href to an element with d, under the transform of that element. An unresolvable
path draws nothing, as in Chromium. Each character sits with its middle on the path, turned to the
tangent there; a character whose middle falls off the path is not drawn. startOffset and text-anchor
place the run, letter-spacing and dx move along the path, dy across it. Decoration lines are drawn
under each character.

The text bounding box stays empty, and text-anchor reads "start" to draw_node of WeasyPrint while a
<text> with a <textPath> draws (text.anchor_restyle): its anchor group, bounded by that box, would clip
the run away, or shift it once more. ANCHOR keeps the value for start().
"""

from __future__ import annotations

import math
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from weasyprint.svg import utils as wp_utils

from . import glyphs, ink, pathdata
from .pathdata import Polyline

XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
ANCHOR = "weasysvg-text-anchor"
DECORATION_LINES = ("underline", "overline", "line-through")


@dataclass
class _State:
    """The path being followed and how far along it the next character starts."""

    nodes: set[int]  # the ids of the nodes inside the <textPath>, anonymous tail text included
    polyline: Polyline
    distance: float
    shift: float = 0.0  # dy, across the path


CURRENT: ContextVar[_State | None] = ContextVar("weasysvg_text_path", default=None)


def _referenced(svg: Any, node: Any, font_size: float) -> Polyline | None:
    data = node.get("path")
    if data is not None and len(segments := pathdata.parse(data)) > 1:
        return Polyline(segments)
    href = node.get(XLINK_HREF) or node.get("href")
    if not href or not href.startswith("#"):
        return None
    element = next((item for item in svg.tree._etree_node.iter() if item.get("id") == href[1:]), None)
    if element is None or element.get("d") is None:
        return None
    transform = element.get("transform")
    matrix = wp_utils.transform(transform, "0 0", font_size, svg.normalized_diagonal) if transform else None
    return Polyline(pathdata.parse(element.get("d")), matrix.transform_point if matrix else None)


def _texts(node: Any, font_size: float) -> list[tuple[Any, float]]:
    """The node and the text nodes inside it, each with its font size, in document order."""
    out = [(node, font_size)]
    for child in node:
        if child.tag in ("tspan", "a"):
            out += _texts(child, wp_utils.size(child.get("font-size", "1em"), font_size, font_size))
    return out


def _numbers(node: Any, name: str, font_size: float, reference: float) -> list[float]:
    return [wp_utils.size(value, font_size, reference) for value in wp_utils.normalize(node.get(name, "")).split()]


def start(svg: Any, node: Any, font_size: float, advances: Any) -> _State:
    """Begin a <textPath>: resolve its path and place the start of its run."""
    # An unresolvable path still makes a state: its text and the text of its <tspan> draw nowhere
    polyline = _referenced(svg, node, font_size) or Polyline([])
    offset = node.get("startOffset", "0")
    distance = wp_utils.size(offset, font_size, polyline.length)
    total = sum(sum(width for _, width in advances(svg, text, size)) for text, size in _texts(node, font_size))
    anchor = node.get(ANCHOR) or node.get("text-anchor", "start")
    if anchor == "middle":
        distance -= total / 2
    elif anchor == "end":
        distance -= total
    state = _State({id(text) for text, _ in _texts(node, font_size)}, polyline, distance)
    CURRENT.set(state)
    return state


def current(node: Any) -> _State | None:
    """The path a <tspan> continues on, when it lies inside the <textPath> being drawn."""
    state = CURRENT.get()
    return state if state is not None and id(node) in state.nodes else None


def _turned_rectangle(stream: Any, origin: tuple[float, float], cos: float, sin: float, box: tuple[float, float, float, float]) -> None:
    """A rectangle in the frame of a character, as a path: no state change may sit inside a path."""
    x, y, width, height = box
    corners = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
    points = [(origin[0] + cos * u - sin * v, origin[1] + sin * u + cos * v) for u, v in corners]
    stream.move_to(*points[0])
    for point in points[1:]:
        stream.line_to(*point)
    stream.close()


Placed = tuple[str, float, tuple[float, float], float, float]  # character, width, origin, cos, sin


def _place(svg: Any, node: Any, font_size: float, state: _State, advances: list[tuple[str, float]]) -> list[Placed]:
    """Each character whose middle lies on the path: the left end of its baseline, moved across by dy."""
    dx = _numbers(node, "dx", font_size, svg.inner_width)
    dy = _numbers(node, "dy", font_size, svg.inner_height)
    letter_spacing = svg.length(node.get("letter-spacing"), font_size)
    placed = []
    # Along the path in visual order: a right-to-left run runs right to left, its letters joining as they should
    for index in glyphs.visual_order("".join(glyphs.base(character) for character, _ in advances)):
        character, width = advances[index]
        state.distance += dx[index] if index < len(dx) else 0
        state.shift += dy[index] if index < len(dy) else 0
        position = state.polyline.at(state.distance + width / 2)
        if position is not None:
            (x, y), angle = position
            cos, sin = math.cos(angle), math.sin(angle)
            placed.append((character, width, (x - cos * width / 2 - sin * state.shift, y - sin * width / 2 + cos * state.shift), cos, sin))
        state.distance += width + letter_spacing
    return placed


Decoration = tuple[float, float, float | None]  # top, thickness, how far it skips ink or None


def _decorate(svg: Any, placed: list[Placed], letter_spacing: float, decorations: list[Decoration], characters: dict[str, list[ink.Glyph]]) -> bool:
    """Add the pieces of the decoration lines to the path; return whether there was any."""
    drawn = False
    for index, (character, width, origin, cos, sin) in enumerate(placed):
        # The line runs on under the letter-spacing, up to the next character
        length = width + (letter_spacing if index + 1 < len(placed) else 0)
        for top, thickness, dilation in decorations:
            # Each character skips its own ink, in its own frame
            cuts = ink.intercepts(characters.get(character, []), top, top + thickness) if dilation is not None else []
            for left, right in ink.skipped(0, length, cuts, dilation or 0):
                _turned_rectangle(svg.stream, origin, cos, sin, (left, top, right - left, thickness))
                drawn = True
    return drawn


def draw(svg: Any, node: Any, font_size: float, state: _State, style: Any, advances: list[tuple[str, float]], decorations: list[Decoration], characters: dict[str, list[ink.Glyph]]) -> None:
    """Draw each character of node on the path, with its decoration lines."""
    placed = _place(svg, node, font_size, state, advances)
    if not placed:
        return
    # A space shows no glyph, yet it carries the decoration lines
    items = [(character, _fixed(origin, math.atan2(sin, cos))) for character, _, origin, cos, sin in placed if character.strip()]
    svg.stream.push_state()
    try:
        fill, stroke = svg.set_graphical_state(node, font_size)
        glyphs.show(svg, style, fill, stroke, items)
        # Every piece may lie under ink: a paint operator needs a path before it
        if decorations and _decorate(svg, placed, svg.length(node.get("letter-spacing"), font_size), decorations, characters):
            svg.fill_stroke(fill, stroke)
    finally:
        svg.stream.pop_state()


def _fixed(origin: tuple[float, float], angle: float) -> glyphs.Place:
    return lambda _height, _baseline: (origin, angle)
