"""Where the glyphs of a run cross a decoration line, so an underline or overline skips their ink.

Chromium skips the ink of glyphs under an underline or an overline (text-decoration-skip-ink: auto),
not under a line-through. Each glyph that crosses the band of the line cuts it, widened on both sides by
the thickness of the line, 13 CSS px at most (kDecorationClipMaxDilation in Blink).

The outlines come from the font file of each Pango run, read with fontTools.
"""

from __future__ import annotations

import functools
import hashlib
import io
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from weasyprint.text.ffi import FROM_UNITS, ffi, harfbuzz, pango
from weasyprint.text.fonts import get_hb_object_data, get_pango_font_hb_face, get_pango_font_key

MAX_DILATION = 13.0  # CSS px
CURVE_STEPS = 8  # straight pieces per curve segment
MAX_FONTS = 32  # font files kept at once: a long-running service sees fonts come and go


@dataclass(frozen=True)
class Glyph:
    """One glyph of a run: its outline, the left end of its baseline, and user units per font unit."""

    font: str  # key into _FONTS
    index: int  # the glyph id in the font
    x: float
    y: float  # down from the baseline of the run
    scale: float


# The font file of each key, and the key of each Pango font: reading and hashing a file costs its size
_FONTS: OrderedDict[str, tuple[bytes, int, int]] = OrderedDict()
_FACES: OrderedDict[tuple[int, int], str] = OrderedDict()


def _remember(cache: OrderedDict[Any, Any], key: Any, value: Any) -> None:
    """Keep value under key, the oldest entry dropped past MAX_FONTS."""
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > MAX_FONTS:
        cache.popitem(last=False)


def _font_key(pango_font: Any, description: int) -> str:
    """The key of the font file of a Pango font, its file read and hashed once.

    A Pango font is known by its address and the hash of its description: the address alone can come
    back for another font once the first is freed.
    """
    identity = (int(ffi.cast("uintptr_t", pango_font)), description)
    key = _FACES.get(identity)
    if key is None or key not in _FONTS:
        face = get_pango_font_hb_face(pango_font)
        data = get_hb_object_data(face)
        key = hashlib.sha1(data, usedforsecurity=False).hexdigest()
        _remember(_FONTS, key, (data, harfbuzz.hb_face_get_index(face), harfbuzz.hb_face_get_upem(face)))
        _remember(_FACES, identity, key)
    return key


def run_glyphs(line: Any, x: float) -> list[Glyph]:
    """The glyphs of a Pango line whose baseline starts at x, as draw_first_line of WeasyPrint places them."""
    out = []
    run = line.runs[0] if line.runs != ffi.NULL else ffi.NULL
    while run != ffi.NULL:
        glyph_item = run.data
        run = run.next
        pango_font = glyph_item.item.analysis.font
        description, _, font_size = get_pango_font_key(pango_font)
        key = _font_key(pango_font, description)
        scale = font_size / _FONTS[key][2]
        glyph_string = glyph_item.glyphs
        for info in glyph_string.glyphs[0 : glyph_string.num_glyphs]:
            geometry = info.geometry
            if info.glyph != pango.PANGO_GLYPH_EMPTY and not info.glyph & pango.PANGO_GLYPH_UNKNOWN_FLAG:
                out.append(Glyph(key, info.glyph, x + geometry.x_offset * FROM_UNITS, geometry.y_offset * FROM_UNITS, scale))
            x += geometry.width * FROM_UNITS
    return out


@functools.lru_cache(maxsize=16)
def _font(key: str) -> Any:
    data, index, _ = _FONTS[key]
    return TTFont(io.BytesIO(data), fontNumber=index, lazy=True)


class _BandPen(BasePen):  # type: ignore[misc]  # fontTools ships no type information
    """The left and right ends of an outline within a horizontal band, in font units, y up."""

    def __init__(self, glyph_set: Any, low: float, high: float) -> None:
        super().__init__(glyph_set)
        self.low, self.high = low, high
        self.left, self.right = float("inf"), float("-inf")
        self.start = self.point = (0.0, 0.0)

    def _segment(self, end: tuple[float, float]) -> None:
        (x0, y0), (x1, y1) = self.point, end
        self.point = end
        if max(y0, y1) < self.low or min(y0, y1) > self.high:
            return
        if y0 == y1:
            xs = [x0, x1]
        else:
            # The part of the segment inside the band
            t0, t1 = sorted(((self.low - y0) / (y1 - y0), (self.high - y0) / (y1 - y0)))
            xs = [x0 + (x1 - x0) * max(t0, 0.0), x0 + (x1 - x0) * min(t1, 1.0)]
        self.left, self.right = min(self.left, *xs), max(self.right, *xs)

    def _moveTo(self, point: tuple[float, float]) -> None:  # noqa: N802  the pen protocol of fontTools
        self.start = self.point = point

    def _lineTo(self, point: tuple[float, float]) -> None:  # noqa: N802
        self._segment(point)

    def _curveToOne(self, p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float]) -> None:  # noqa: N802
        p0 = self.point
        for step in range(1, CURVE_STEPS + 1):
            t = step / CURVE_STEPS
            u = 1 - t
            self._segment(
                (
                    u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
                )
            )

    def _qCurveToOne(self, p1: tuple[float, float], p2: tuple[float, float]) -> None:  # noqa: N802
        p0 = self.point
        for step in range(1, CURVE_STEPS + 1):
            t = step / CURVE_STEPS
            u = 1 - t
            self._segment((u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0], u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]))

    def _closePath(self) -> None:  # noqa: N802
        self._segment(self.start)


@functools.lru_cache(maxsize=4096)
def _extent(key: str, glyph: int, low: float, high: float) -> tuple[float, float] | None:
    """Where the outline of glyph lies within the band from low to high, in font units, y up."""
    if key not in _FONTS:
        return None  # dropped from the cache since the run was laid out
    font = _font(key)
    if not any(table in font for table in ("glyf", "CFF ", "CFF2")):
        return None  # bitmap glyphs only (CBDT, sbix): no outline to skip
    glyph_set = font.getGlyphSet()
    name = font.getGlyphOrder()[glyph] if glyph < len(font.getGlyphOrder()) else None
    if name is None or name not in glyph_set:
        return None
    pen = _BandPen(glyph_set, low, high)
    glyph_set[name].draw(pen)
    return (pen.left, pen.right) if pen.left <= pen.right else None


def intercepts(glyphs: list[Glyph], top: float, bottom: float) -> list[tuple[float, float]]:
    """Where the glyphs cross the band from top to bottom, below the baseline positive, in user units."""
    out = []
    for glyph in glyphs:
        # The band in the font units of the glyph, y up from its own baseline
        low, high = (glyph.y - bottom) / glyph.scale, (glyph.y - top) / glyph.scale
        extent = _extent(glyph.font, glyph.index, round(low, 3), round(high, 3))
        if extent is not None:
            out.append((glyph.x + extent[0] * glyph.scale, glyph.x + extent[1] * glyph.scale))
    return out


def skipped(start: float, end: float, cuts: list[tuple[float, float]], dilation: float) -> list[tuple[float, float]]:
    """The pieces of the line from start to end outside the cuts, each widened by dilation."""
    pieces, position = [], start
    for low, high in sorted((low - dilation, high + dilation) for low, high in cuts):
        if low > position:
            pieces.append((position, min(low, end)))
        position = max(position, high)
    if position < end:
        pieces.append((position, end))
    return [(low, high) for low, high in pieces if high > low]
