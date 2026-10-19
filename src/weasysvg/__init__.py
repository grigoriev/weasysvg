"""Native SVG features for WeasyPrint, so that SVG needs no browser.

Call ``install()`` once, before the first rendering. It patches WeasyPrint in place, for the process.
Each feature lives in its own submodule; ``_core`` holds the two hooks that several of them share.
The package targets WeasyPrint 70.x and warns on any other version.
"""

from __future__ import annotations

import warnings

import weasyprint

from . import conditional as _conditional
from . import fetch as _fetch
from . import filters as _filters
from . import fonts as _fonts
from . import foreign_object as _foreign_object
from . import paint as _paint
from . import raster as _raster
from . import text as _text
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
    raster_filters: bool = True,
    raster_scale: float = 2.0,
    paint: bool = True,
    blend: bool = True,
    text: bool = True,
    fonts: bool = True,
    fetch_cache: bool = True,
) -> frozenset[str]:
    """Install the selected features and return all features installed so far.

    Idempotent: a feature installed before is skipped. A later call can add features, never remove them.
    ``fonts`` resolves font families as Chromium does, in SVG text and inside foreignObject.
    ``raster_filters`` lets resvg render the filters PDF cannot express, at ``raster_scale`` times the CSS px size.
    """
    _check_version()
    wanted = {
        "conditional": conditional_processing,
        "paint": paint,
        "blend": paint and blend,
        "text": text,
        "fonts": fonts,
        "fetch": fetch_cache,
        "filters": filters,
        "foreign_object": foreign_object,
    }

    def _install_filters() -> None:
        _raster.install(scale=raster_scale, enabled=raster_filters)
        _filters.install()

    def _install_fonts() -> None:
        _fonts.install()
        # The text feature may have been installed earlier with fonts off
        _text.FEATURES["fonts"] = True

    installers = {
        "conditional": _conditional.install,
        "paint": lambda: _paint.install(blend=False),
        "blend": lambda: _paint.install(blend=True),
        # fonts installed by an earlier call stays on: a later call only adds
        "text": lambda: _text.install(fonts=fonts or "fonts" in _INSTALLED),
        "fonts": _install_fonts,
        "fetch": _fetch.install,
        "filters": _install_filters,
        "foreign_object": _foreign_object.install,
    }
    for name, enabled in wanted.items():
        if enabled and name not in _INSTALLED:
            installers[name]()
            _INSTALLED.add(name)
    return frozenset(_INSTALLED)


def installed() -> frozenset[str]:
    return frozenset(_INSTALLED)
