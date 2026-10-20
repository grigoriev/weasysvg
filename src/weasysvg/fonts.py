"""Font selection as Chromium on Linux does it, one resolver for SVG text and foreignObject content.

Touches:
- nothing for SVG text by itself: ``text.py`` calls ``resolve_families()`` before ``text()`` draws.
- ``css.computed_values.COMPUTER_FUNCTIONS['font_family']``, inside a foreignObject only.

Chromium maps generic names to its defaults (serif to Times New Roman, sans-serif to Arial) and takes
the first family of a list that fontconfig finds, by name or as a metric equivalent (Skia kFontEquivMap).
A list where nothing matches falls back to Times New Roman. WeasyPrint hands the whole list to Pango,
where fontconfig picks DejaVu Sans for any unknown name. Measured in Chromium: 46 of 47 lists match.

A character the family lacks comes from the font fontconfig picks for it with no family, which is the
sans-serif list (gfx::GetFallbackFontForChar). Pango falls back within the family it gets, so serif
text took Arabic from FreeSerif: after the family Pango gets FALLBACK.

No fontconfig file is needed: the resolver hands Pango one concrete family, so the strong aliases and the
emoji rule of the earlier fonts.conf changed no pixel of the corpus, with or without it.
"""

from __future__ import annotations

from collections.abc import Iterable
from contextvars import ContextVar
from typing import Any

from weasyprint.css.computed_values import COMPUTER_FUNCTIONS
from weasyprint.text.ffi import ffi, fontconfig

# ---------------- the resolver ----------------

# Chromium draws with it when no family of a list matches
STANDARD = "Times New Roman"
# Where Chromium finds a character the family lacks: fontconfig with no family asks for sans-serif
FALLBACK = "sans-serif"
# Lowercase keys of the equivalence and alternate tables
COURIER_NEW = "courier new"
TIMES_NEW_ROMAN = "times new roman"
# Chromium default font settings on Linux (the names it looks up through fontconfig)
GENERIC = {
    "serif": STANDARD,
    "sans-serif": "Arial",
    "monospace": "Monospace",
    "cursive": "Comic Sans MS",
    "fantasy": "Impact",
    "system-ui": "sans",
    "ui-sans-serif": "Arial",
    "ui-serif": STANDARD,
    "ui-monospace": "Monospace",
}
# Skia accepts these fontconfig matches without a family name match (IsFallbackFontAllowed)
FALLBACK_ALLOWED = frozenset(("sans", "serif", "monospace"))
# Skia kFontEquivMap (Latin part): metric-compatible replacements Chromium accepts
EQUIVALENT = (
    ("arial", "arimo", "liberation sans"),
    ("arial narrow", "liberation sans narrow"),
    ("calibri", "carlito"),
    ("cambria", "caladea"),
    (COURIER_NEW, "cousine", "liberation mono"),
    ("georgia", "gelasio"),
    (TIMES_NEW_ROMAN, "tinos", "liberation serif"),
)
# Blink FontCache AlternateFamilyName: retried when the first name finds nothing
ALTERNATE = {"courier": COURIER_NEW, COURIER_NEW: "courier", "times": TIMES_NEW_ROMAN, TIMES_NEW_ROMAN: "times", "arial": "helvetica", "helvetica": "arial"}
FC_MATCH_PATTERN = 0
_NULL_CACHE: dict[str, str | None] = {}


def _acceptable(family: str, name: str) -> bool:
    family, name = family.lower(), name.lower()
    return family == name or any(family in group and name in group for group in EQUIVALENT)


def _get(pattern: Any, key: bytes, n: int = 0) -> str | None:
    value = ffi.new("FcChar8 **")
    if fontconfig.FcPatternGetString(pattern, key, n, value) != 0:  # FcResultMatch == 0
        return None
    text: str = ffi.string(value[0]).decode("utf-8", "replace")
    return text


def _match(family: str, config: Any) -> str | None:
    """The family fontconfig gives for a name, or None when Chromium would reject the match."""
    pattern = fontconfig.FcPatternCreate()
    try:
        fontconfig.FcPatternAddString(pattern, b"family", family.encode())
        fontconfig.FcConfigSubstitute(config, pattern, FC_MATCH_PATTERN)
        fontconfig.FcDefaultSubstitute(pattern)
        result = ffi.new("FcResult *")
        match = fontconfig.FcFontMatch(config, pattern, result)
        if match == ffi.NULL:
            return None
        try:
            names = []
            n = 0
            while (name := _get(match, b"family", n)) is not None:
                names.append(name)
                n += 1
        finally:
            fontconfig.FcPatternDestroy(match)
    finally:
        fontconfig.FcPatternDestroy(pattern)
    if names and (family.lower() in FALLBACK_ALLOWED or any(_acceptable(family, name) for name in names)):
        return names[0]
    return None


def _lookup(family: str, config: Any, cache: dict[str, str | None]) -> str | None:
    key = family.lower()
    if key not in cache:
        resolved = _match(family, config)
        if resolved is None and (alternate := ALTERNATE.get(key)):
            resolved = _match(alternate, config)
        cache[key] = resolved
    return cache[key]


def resolve_families(families: str | Iterable[str], font_config: Any = None) -> str:
    """The one family Chromium draws a CSS family list with. Missing glyphs still fall back through fontconfig.

    font_config is the FontConfiguration of the document: its FcConfig also holds the @font-face fonts.
    """
    cache: dict[str, str | None]
    if font_config is None:
        config, cache = ffi.NULL, _NULL_CACHE
    else:
        config = font_config._config
        cache = font_config.__dict__.setdefault("_svg_ext_family_cache", {})
    if isinstance(families, str):
        families = families.split(",")
    for family in (part.strip().strip("\"'") for part in families):
        if family and (resolved := _lookup(GENERIC.get(family.lower(), family), config, cache)):
            return resolved
    return _lookup(STANDARD, config, cache) or "serif"


# ---------------- foreignObject content ----------------

IN_FOREIGN_OBJECT: ContextVar[bool] = ContextVar("in_foreign_object", default=False)
_ORIGINAL_FAMILY_COMPUTER = COMPUTER_FUNCTIONS.get("font_family")


def _computed_families(style: Any, name: str, value: Any) -> Any:
    families = _ORIGINAL_FAMILY_COMPUTER(style, name, value) if _ORIGINAL_FAMILY_COMPUTER else value
    if not IN_FOREIGN_OBJECT.get() or style.font_config is None:
        return families
    return (resolve_families(families, style.font_config), FALLBACK)


def install() -> None:
    COMPUTER_FUNCTIONS["font_family"] = _computed_families
