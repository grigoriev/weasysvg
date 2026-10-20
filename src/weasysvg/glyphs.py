"""Characters drawn one at a time, each at its own origin and angle, for textpath.py and vertical.py."""

from __future__ import annotations

import math
import unicodedata
from collections.abc import Callable
from typing import Any

from weasyprint.matrix import Matrix

Point = tuple[float, float]
# Where a character goes, from the height and baseline of its line: origin of the baseline, angle
Place = Callable[[float, float], tuple[Point, float]]

ZWJ = "\u200d"
# Joining types of Arabic (ArabicShaping.txt of Unicode): right-joining letters join the letter before them
# only, hamza joins nothing, marks are transparent, tatweel and ZWJ join both sides, other letters are dual
ARABIC_LETTERS = ((0x0620, 0x064A), (0x066E, 0x06D3), (0x06D5, 0x06D5), (0x06EE, 0x06EF), (0x06FA, 0x06FC), (0x06FF, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08C9))
RIGHT_JOINING = frozenset(
    chr(code)
    for code in (
        *(0x0622, 0x0623, 0x0624, 0x0625, 0x0627, 0x0629, 0x062F, 0x0630, 0x0631, 0x0632, 0x0648, 0x0671, 0x0672, 0x0673, 0x0675, 0x0676, 0x0677),
        *range(0x0688, 0x069A),
        *(0x06C0, *range(0x06C3, 0x06CC), 0x06CD, 0x06CF, 0x06D2, 0x06D3, 0x06D5, 0x06EE, 0x06EF),
        *(0x0759, 0x075A, 0x075B, 0x076B, 0x076C, 0x0771, 0x0773, 0x0774, 0x0778, 0x0779),
        *(0x08AA, 0x08AB, 0x08AC, 0x08AE, 0x08B1, 0x08B2, 0x08B9),
    )
)
NON_JOINING = frozenset("\u0621\u0674")
JOIN_CAUSING = frozenset("\u0640" + ZWJ)


def _joining(character: str) -> str:
    """The joining type of character: D dual, R right, C join causing, T transparent, U none."""
    if character in JOIN_CAUSING:
        return "C"
    if unicodedata.category(character) in ("Mn", "Me"):
        return "T"
    if character in RIGHT_JOINING:
        return "R"
    code = ord(character)
    if character not in NON_JOINING and any(low <= code <= high for low, high in ARABIC_LETTERS):
        return "D"
    return "U"


def _neighbor(text: str, index: int, step: int) -> str:
    """The joining type of the letter next to text[index] in direction step, marks skipped."""
    index += step
    while 0 <= index < len(text) and _joining(text[index]) == "T":
        index += step
    return _joining(text[index]) if 0 <= index < len(text) else "U"


def in_context(text: str, index: int) -> str:
    """The character at index, with a ZWJ on each side where it joins a neighbor.

    A character laid out alone takes its isolated form: Arabic would fall apart. The joiners make the
    shaper pick the initial, medial or final form the whole word gives it, and they draw nothing.
    """
    character = text[index]
    kind = _joining(character)
    if kind not in ("D", "R"):
        return character
    before = ZWJ if _neighbor(text, index, -1) in ("D", "C") else ""
    after = ZWJ if kind == "D" and _neighbor(text, index, 1) in ("D", "R", "C") else ""
    return before + character + after


DIGITS = ("EN", "AN")


def _nearest_strong(classes: list[str]) -> list[str | None]:
    """The bidi class of the nearest strong letter before each index, None before the first."""
    out: list[str | None] = []
    last = None
    for kind in classes:
        out.append(last)
        last = kind if kind in ("L", "R", "AL") else last
    return out


def _right_to_left(classes: list[str]) -> list[bool]:
    """Whether each character belongs to a right-to-left run."""
    before = _nearest_strong(classes)
    after = _nearest_strong(classes[::-1])[::-1]
    rtl = [False] * len(classes)
    for index, kind in enumerate(classes):
        if kind in ("R", "AL"):
            rtl[index] = True
        elif kind == "NSM" and index:
            rtl[index] = rtl[index - 1]
        elif kind != "L":
            rtl[index] = before[index] in ("R", "AL") and after[index] in ("R", "AL")
    return rtl


def rtl_runs(text: str) -> list[tuple[int, int]]:
    """The right-to-left runs of text, start and end indices, for a left-to-right line.

    A simple form of the bidi algorithm: strong Arabic and Hebrew letters make a run, with the marks after
    them and the neutrals and numbers between two of them.
    """
    rtl = _right_to_left([unicodedata.bidirectional(character) for character in text])
    runs: list[tuple[int, int]] = []
    for index, inside in enumerate(rtl):
        if not inside:
            continue
        if runs and runs[-1][1] == index:
            runs[-1] = (runs[-1][0], index + 1)
        else:
            runs.append((index, index + 1))
    return runs


def _in_number(text: str, index: int) -> bool:
    """Whether text[index] is a digit, or a separator between two digits, as 1.5 or 1,000."""
    kind = unicodedata.bidirectional(text[index])
    if kind in DIGITS:
        return True
    inside = 0 < index < len(text) - 1
    return kind in ("CS", "ES", "ET") and inside and unicodedata.bidirectional(text[index - 1]) in DIGITS and unicodedata.bidirectional(text[index + 1]) in DIGITS


def reversed_clusters(text: str, start: int, end: int) -> list[int]:
    """The indices from start to end in visual order: clusters reversed, a mark kept after its letter, and a
    number kept whole, left to right."""
    clusters: list[list[int]] = []
    for index in range(start, end):
        joins = unicodedata.bidirectional(text[index]) == "NSM" or (_in_number(text, index) and index > start and _in_number(text, index - 1))
        if joins and clusters:
            clusters[-1].append(index)
        else:
            clusters.append([index])
    return [index for cluster in reversed(clusters) for index in cluster]


def visual_order(text: str) -> list[int]:
    """The indices of text in visual order, left to right: each right-to-left run reversed by clusters."""
    order = list(range(len(text)))
    for start, end in rtl_runs(text):
        order[start:end] = reversed_clusters(text, start, end)
    return order


def base(shaped: str) -> str:
    """The character of a string from in_context."""
    return shaped.strip(ZWJ) or shaped


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
