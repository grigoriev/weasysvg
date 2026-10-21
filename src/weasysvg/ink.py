"""The glyphs of a Pango run and the font files they come from, for the vertical origin of vertical text.

The font file of each run is read with fontTools.
"""

from __future__ import annotations

import functools
import hashlib
import io
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont
from weasyprint.text.ffi import FROM_UNITS, ffi, harfbuzz, pango
from weasyprint.text.fonts import get_hb_object_data, get_pango_font_hb_face, get_pango_font_key

MAX_FONTS = 32  # font files kept at once: a long-running service sees fonts come and go


@dataclass(frozen=True)
class Glyph:
    """One glyph of a run: its outline, the left end of its baseline, and user units per font unit."""

    font: str  # key into _FONTS
    index: int  # the glyph id in the font
    x: float
    y: float  # down from the baseline of the run
    scale: float


# The font file of each key, and the key of each HarfBuzz face: reading and hashing a file costs its size
_FONTS: OrderedDict[str, tuple[bytes, int, int]] = OrderedDict()
_FACES: OrderedDict[int, tuple[str, Any]] = OrderedDict()


def _remember(cache: OrderedDict[Any, Any], key: Any, value: Any) -> None:
    """Keep value under key, the oldest entry dropped past MAX_FONTS."""
    cache[key] = value
    cache.move_to_end(key)
    while len(cache) > MAX_FONTS:
        cache.popitem(last=False)


def _font_key(pango_font: Any) -> str:
    """The key of the font file of a Pango font, its file read and hashed once per face.

    A face is known by its address. Pango shares it between the sizes of a font, and the cache holds a
    reference to it: its address cannot come back for another face.
    """
    face = get_pango_font_hb_face(pango_font)
    identity = int(ffi.cast("uintptr_t", face))
    found = _FACES.get(identity)
    if found is not None and found[0] in _FONTS:
        return str(found[0])
    data = get_hb_object_data(face)
    digest = hashlib.sha1(data, usedforsecurity=False).hexdigest()
    # The faces of a collection share their file: the index tells them apart, and one copy serves them all
    index = harfbuzz.hb_face_get_index(face)
    key = f"{digest}:{index}"
    data = next((value[0] for other, value in _FONTS.items() if other.startswith(f"{digest}:")), data)
    _remember(_FONTS, key, (data, index, harfbuzz.hb_face_get_upem(face)))
    _remember(_FACES, identity, (key, face))
    return key


def run_glyphs(line: Any, x: float) -> list[Glyph]:
    """The glyphs of a Pango line whose baseline starts at x, as draw_first_line of WeasyPrint places them."""
    out = []
    run = line.runs[0] if line.runs != ffi.NULL else ffi.NULL
    while run != ffi.NULL:
        glyph_item = run.data
        run = run.next
        pango_font = glyph_item.item.analysis.font
        _, _, font_size = get_pango_font_key(pango_font)
        key = _font_key(pango_font)
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


def vertical_origin_in_units(font: Any, name: str) -> float | None:
    """How far above the baseline the vertical origin of a glyph lies, in font units, as HarfBuzz and Chromium take it.

    VORG gives it, else vmtx: the top side bearing over the top of the glyph. None for a font with neither.
    """
    if "VORG" in font:
        table = font["VORG"]
        return float(table.VOriginRecords.get(name, table.defaultVertOriginY))
    if "vmtx" not in font:
        return None
    glyph_set = font.getGlyphSet()
    pen = BoundsPen(glyph_set)
    glyph_set[name].draw(pen)
    top = pen.bounds[3] if pen.bounds else 0  # an empty glyph has its top at the baseline
    return float(font["vmtx"][name][1] + top)


@functools.lru_cache(maxsize=4096)
def _vertical_origin(key: str, glyph: int) -> float | None:
    try:
        font = _font(key)
        order = font.getGlyphOrder()
        return vertical_origin_in_units(font, order[glyph]) if glyph < len(order) else None
    except Exception:  # fontTools raises errors of many kinds on a broken table
        return None


def vertical_origin(line: Any) -> float | None:
    """How far above the baseline the vertical origin of the first glyph of a Pango line lies, in user units."""
    found = run_glyphs(line, 0)
    if not found:
        return None
    units = _vertical_origin(found[0].font, found[0].index)
    return None if units is None else units * found[0].scale
