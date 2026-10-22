"""Conditional processing: <switch>, requiredExtensions, systemLanguage.

Touches: a tree pass in ``images.SVGImage.__init__``; a wrapper of ``images.SVGImage.draw``, which draws
in the language the image was built in; ``html.handle_element``, which notes the language of the element
an image belongs to; and ``document.original_get_image_from_uri``, which keys
the cache of images by that language. WeasyPrint draws every child of a <switch> and ignores
the conditional attributes, so draw.io drew both its foreignObject and its fallback text.

systemLanguage reads the language of the document, its ``lang`` where the image sits, as a browser reads
the language of its reader. Without one it reads DEFAULT_LANGUAGE, which ``install(language=...)`` sets.
"""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from typing import Any
from xml.etree import ElementTree as ET

from weasyprint import document as wp_document
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
_ORIGINAL_GET_IMAGE_FROM_URI = wp_document.original_get_image_from_uri


def local_name(tag: object) -> str | None:
    return tag.split("}", 1)[-1] if isinstance(tag, str) else None


def reader_language() -> str:
    return (LANGUAGE.get() or DEFAULT_LANGUAGE).strip().lower()


def reader_languages() -> list[str]:
    """The languages of the reader, as the Accept-Language list a browser sends: "de-CH" sends "de-CH,de"."""
    language = reader_language()
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

    An element without a lang inside a foreignObject keeps the language of the SVG around it.
    """
    token = LANGUAGE.set(box.style["lang"] or LANGUAGE.get())
    try:
        return _ORIGINAL_HANDLE_ELEMENT(element, box, get_image_from_uri, base_url)
    finally:
        LANGUAGE.reset(token)


class _ByLanguage:
    """The cache of images, each key in the language of the reader: an SVG differs from one language to another.

    WeasyPrint reads and writes the cache by key alone, a dict or a DiskCache, which takes string keys.
    """

    def __init__(self, cache: Any, language: str) -> None:
        self._cache, self._suffix = cache, f" weasysvg-language:{language}"

    def __contains__(self, key: str) -> bool:
        return key + self._suffix in self._cache

    def __getitem__(self, key: str) -> Any:
        return self._cache[key + self._suffix]

    def __setitem__(self, key: str, value: Any) -> None:
        self._cache[key + self._suffix] = value


def get_image_from_uri(cache: Any, *args: Any, **kwargs: Any) -> Any:
    """get_image_from_uri of WeasyPrint, its cache kept apart for each language of the reader."""
    return _ORIGINAL_GET_IMAGE_FROM_URI(_ByLanguage(cache, reader_language()), *args, **kwargs)


def _note_language(image: Any) -> None:
    image.weasysvg_language = LANGUAGE.get()


def svgimage_draw(image: Any, stream: Any, _width: float, _height: float, _style: Any, draw: Callable[[Any], None]) -> None:
    """SVGImage.draw of WeasyPrint in the language the image was built in.

    An SVG it draws, an <image> or the content of a foreignObject, is built while it draws.
    """
    token = LANGUAGE.set(getattr(image, "weasysvg_language", None))
    try:
        draw(stream)
    finally:
        LANGUAGE.reset(token)


def install() -> None:
    _core.add_tree_pass(10, "conditional", apply_conditionals)
    _core.add_image_hook(_note_language)
    _core.add_draw_wrapper(10, svgimage_draw)
    wp_html.handle_element = handle_element
    # document.py builds its partial from this name on each rendering
    wp_document.original_get_image_from_uri = get_image_from_uri


def set_language(language: str) -> None:
    """The language of the reader for a document or image without a lang."""
    if not language.strip():
        raise ValueError("language must not be empty: it would match no systemLanguage")
    global DEFAULT_LANGUAGE
    DEFAULT_LANGUAGE = language
