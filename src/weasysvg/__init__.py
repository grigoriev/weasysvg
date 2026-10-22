"""Native SVG features for WeasyPrint, so that SVG needs no browser.

Call ``install()`` once, before the first rendering. It patches WeasyPrint in place, for the process.
Each feature lives in its own submodule; ``_core`` holds the two hooks that several of them share.
The package targets WeasyPrint 70.x and warns on any other version.
"""

from __future__ import annotations

import warnings

import weasyprint

from . import conditional as _conditional
from . import css as _css
from . import fetch as _fetch
from . import filters as _filters
from . import fonts as _fonts
from . import foreign_object as _foreign_object
from . import markers as _markers
from . import paint as _paint
from . import paint_order as _paint_order
from . import text as _text
from . import xobject as _xobject
from .fonts import resolve_families

__all__ = ["SUPPORTED_MAJOR", "install", "installed", "resolve_families"]

SUPPORTED_MAJOR = 70
_INSTALLED: set[str] = set()


def _check_version() -> None:
    version = getattr(weasyprint, "__version__", "")
    if version.split(".", 1)[0] != str(SUPPORTED_MAJOR):
        warnings.warn(
            f"weasysvg targets WeasyPrint {SUPPORTED_MAJOR}.x, found {version or 'unknown'}: the patches may not apply",
            RuntimeWarning,
            stacklevel=3,
        )


def install(
    *,
    conditional_processing: bool = True,
    foreign_object: bool = True,
    filters: bool = True,
    paint: bool = True,
    blend: bool = True,
    text: bool = True,
    fonts: bool = True,
    fetch_cache: bool = True,
    markers: bool = True,
    paint_order: bool = True,
    form_xobject: bool = True,
    css: bool = True,
    language: str | None = None,
) -> frozenset[str]:
    """Install the selected features and return all features installed so far.

    Idempotent: a feature installed before is skipped. A later call can add features, never remove them.
    ``paint_order`` paints fill, stroke and markers in the order of the paint-order property.
    ``fonts`` resolves font families as Chromium does, in SVG text and inside foreignObject.
    ``form_xobject`` draws each SVG image as one Form XObject, its BBox the viewport.
    ``css`` reads @supports, custom properties, var() and light-dark() as Chromium does when it prints,
    in the light color scheme, and drops invalid color values.
    ``language`` is the language systemLanguage reads where the document gives none ("en" by default);
    any call can change it.
    """
    _check_version()
    if language is not None:
        _conditional.set_language(language)
    wanted = {
        "conditional": conditional_processing,
        "paint": paint,
        "blend": paint and blend,
        # Before text: its cascade then wraps this one, and a font size reads its var() substituted
        "css": css,
        "text": text,
        "fonts": fonts,
        "fetch": fetch_cache,
        "filters": filters,
        "foreign_object": foreign_object,
        "markers": markers,
        "paint_order": paint_order,
        "form_xobject": form_xobject,
    }

    def _install_fonts() -> None:
        _fonts.install()
        # The text feature may have been installed earlier with fonts off
        _text.FEATURES["fonts"] = True

    installers = {
        "conditional": _conditional.install,
        "paint": lambda: _paint.install(blend=False),
        "blend": lambda: _paint.install(blend=True),
        "css": _css.install,
        # fonts installed by an earlier call stays on: a later call only adds
        "text": lambda: _text.install(fonts=fonts or "fonts" in _INSTALLED),
        "fonts": _install_fonts,
        "fetch": _fetch.install,
        "filters": _filters.install,
        "foreign_object": _foreign_object.install,
        "markers": _markers.install,
        "paint_order": _paint_order.install,
        "form_xobject": _xobject.install,
    }
    for name, enabled in wanted.items():
        if enabled and name not in _INSTALLED:
            installers[name]()
            _INSTALLED.add(name)
    return frozenset(_INSTALLED)


def installed() -> frozenset[str]:
    return frozenset(_INSTALLED)
