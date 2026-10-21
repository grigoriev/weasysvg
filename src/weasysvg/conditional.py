"""Conditional processing: <switch>, requiredExtensions, systemLanguage.

Touches: a tree pass in ``images.SVGImage.__init__``, and ``html.handle_element``, which notes the
language of the element an image belongs to. WeasyPrint draws every child of a <switch> and ignores
the conditional attributes, so draw.io drew both its foreignObject and its fallback text.

systemLanguage reads the language of the document, its ``lang`` where the image sits, as a browser reads
the language of its reader. Without one it reads DEFAULT_LANGUAGE, which ``install(language=...)`` sets.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any
from xml.etree import ElementTree as ET

from weasyprint import html as wp_html

from . import _core

XHTML_NS = "http://www.w3.org/1999/xhtml"
# Filled by foreign_object.install(). Without it nothing draws a foreignObject, and a <switch> must keep its fallback
SUPPORTED_EXTENSIONS: set[str] = set()
# A referenced element ignores the attributes, as in Chromium
REFERENCED = frozenset(("clipPath", "mask", "pattern", "linearGradient", "radialGradient", "filter", "marker", "symbol", "defs", "style"))
DEFAULT_LANGUAGE = "en"
# The lang of the element whose image is being built, None outside one or without a lang
LANGUAGE: ContextVar[str | None] = ContextVar("weasysvg_language", default=None)
_ORIGINAL_HANDLE_ELEMENT = wp_html.handle_element


def local_name(tag: object) -> str | None:
    return tag.split("}", 1)[-1] if isinstance(tag, str) else None


def reader_languages() -> list[str]:
    """The languages of the reader, as the Accept-Language list a browser sends: "de-CH" sends "de-CH,de"."""
    language = (LANGUAGE.get() or DEFAULT_LANGUAGE).strip().lower()
    return list(dict.fromkeys((language, language.split("-", 1)[0])))


def _matches(code: str, languages: list[str]) -> bool:
    """SVG 1.1, as Blink: a reader language equals the code, or the code begins with it and a hyphen."""
    return any(code == language or code.startswith(language + "-") for language in languages)


def passes(element: ET.Element) -> bool:
    """Evaluate the conditional attributes the way Chromium does, in the language of the reader."""
    extensions = element.get("requiredExtensions")
    if extensions is not None:
        parts = extensions.split()
        if not parts or any(part not in SUPPORTED_EXTENSIONS for part in parts):
            return False
    languages = element.get("systemLanguage")
    if languages is not None:
        codes = [code.strip().lower() for code in languages.split(",") if code.strip()]
        reader = reader_languages()
        if not any(_matches(code, reader) for code in codes):
            return False
    # requiredFeatures is gone from SVG 2: browsers treat it as true
    return True


def _choose(switch: ET.Element) -> None:
    """A <switch> keeps its first element that passes and drops the other elements."""
    chosen = None
    for child in list(switch):
        if not isinstance(child.tag, str):
            continue
        if chosen is None and passes(child):
            chosen = child
        else:
            switch.remove(child)


def _hidden(element: ET.Element, root: ET.Element) -> bool:
    """Outside a switch the attributes hide what is rendered."""
    return element is not root and isinstance(element.tag, str) and local_name(element.tag) not in REFERENCED and not passes(element)


def apply_conditionals(root: ET.Element) -> None:
    parents = {child: parent for parent in root.iter() for child in parent}
    for element in list(root.iter()):
        if element is not root and local_name(element.tag) == "switch":
            _choose(element)
    for element in list(root.iter()):
        if _hidden(element, root):
            parent = parents.get(element)
            if parent is not None and element in list(parent):
                parent.remove(element)


def handle_element(element: Any, box: Any, get_image_from_uri: Callable[..., Any], base_url: str | None) -> Any:
    """handle_element of WeasyPrint, the image of the element built in the language of the element.

    The images of a document are cached by URL: an image in another language gets a cache of its own.
    """
    language = box.style["lang"]
    if language and isinstance(get_image_from_uri, functools.partial) and isinstance(get_image_from_uri.keywords.get("cache"), dict):
        cache = get_image_from_uri.keywords["cache"].setdefault(("weasysvg language", language.lower()), {})
        get_image_from_uri = functools.partial(get_image_from_uri, cache=cache)
    token = LANGUAGE.set(language)
    try:
        return _ORIGINAL_HANDLE_ELEMENT(element, box, get_image_from_uri, base_url)
    finally:
        LANGUAGE.reset(token)


def install() -> None:
    _core.add_tree_pass(10, "conditional", apply_conditionals)
    wp_html.handle_element = handle_element


def set_language(language: str) -> None:
    """The language of the reader for a document or image without a lang."""
    global DEFAULT_LANGUAGE  # noqa: PLW0603  one setting for the process, as install() sets it
    DEFAULT_LANGUAGE = language
