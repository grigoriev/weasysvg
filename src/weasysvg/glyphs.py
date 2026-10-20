"""Characters drawn one at a time, each at its own origin and angle, for textpath.py and vertical.py."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from weasyprint.matrix import Matrix

Point = tuple[float, float]
# Where a character goes, from the height and baseline of its line: origin of the baseline, angle
Place = Callable[[float, float], tuple[Point, float]]


def show(svg: Any, style: Any, fill: Any, stroke: Any, items: list[tuple[str, Place]]) -> None:
    """Draw each character in one text object. The caller has set the graphical state."""
    from weasyprint.draw.text import draw_first_line
    from weasyprint.svg.text import TextBox
    from weasyprint.text.line_break import split_first_line

    svg.stream.begin_text()
    for character, place in items:
        layout, _, _, _, height, baseline = split_first_line(character, style, svg.context, math.inf, 0)
        layout.reactivate(style)
        svg.fill_stroke(fill, stroke, text=True)
        box = TextBox(layout, style)
        box.baseline = baseline
        (x, y), angle = place(height, baseline)
        cos, sin = math.cos(angle), math.sin(angle)
        draw_first_line(svg.stream, box, "none", "none", Matrix(cos, -sin, sin, cos) @ Matrix(d=-1, e=x, f=y))
    svg.stream.end_text()
