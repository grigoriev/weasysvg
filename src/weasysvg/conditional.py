"""Conditional processing: <switch>, requiredExtensions, systemLanguage.

Touches: a tree pass in ``images.SVGImage.__init__``. WeasyPrint draws every child of a <switch>
and ignores the conditional attributes, so draw.io drew both its foreignObject and its fallback text.
"""

from __future__ import annotations

from xml.etree import ElementTree as ET

from . import _core

XHTML_NS = "http://www.w3.org/1999/xhtml"
# Filled by foreign_object.install(). Without it nothing draws a foreignObject, and a <switch> must keep its fallback
SUPPORTED_EXTENSIONS: set[str] = set()
# A referenced element ignores the attributes, as in Chromium
REFERENCED = frozenset(("clipPath", "mask", "pattern", "linearGradient", "radialGradient", "filter", "marker", "symbol", "defs", "style"))


def local_name(tag: object) -> str | None:
    return tag.split("}", 1)[-1] if isinstance(tag, str) else None


def passes(element: ET.Element) -> bool:
    """Evaluate the conditional attributes the way Chromium does (language en-US)."""
    extensions = element.get("requiredExtensions")
    if extensions is not None:
        parts = extensions.split()
        if not parts or any(part not in SUPPORTED_EXTENSIONS for part in parts):
            return False
    languages = element.get("systemLanguage")
    if languages is not None:
        codes = [code.strip().lower() for code in languages.split(",") if code.strip()]
        if not any(code == "en" or code.startswith("en-") for code in codes):
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


def install() -> None:
    _core.add_tree_pass(10, "conditional", apply_conditionals)
