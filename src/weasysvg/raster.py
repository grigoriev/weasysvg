"""Raster fallback for filters that PDF cannot express: one element, rendered by resvg, drawn as an image.

Touches: ``svg.SVG.draw``, to record the stream and scale an SVG starts with. filters.py decides what
goes raster; this module builds the standalone SVG, calls resvg and draws the PNG.

The standalone SVG is a copy of the document in the user space of the element, after its own
transform: the ancestors keep their styles but lose transform, opacity, clip, mask, filter and blend,
which WeasyPrint applies itself around the image. Siblings are dropped unless the element references
something inside them. The root viewBox is the filter region, so only that region is rendered.

resvg (the resvg-py binding) is optional. Without it, filters.py keeps the vector approximation.
"""

from __future__ import annotations

import copy
import hashlib
import io
import logging
import math
import re
from collections.abc import Collection
from typing import Any
from xml.etree import ElementTree as ET

from weasyprint import svg as wp_svg
from weasyprint.images import RasterImage

LOGGER = logging.getLogger("weasysvg")
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
FILTER_ID = "__svg_ext_filter"
SETTINGS = {"scale": 2.0, "max_side": 10000, "max_pixels": 50_000_000}
# Chromium-like fonts for resvg; @font-face data: fonts of the SVG are not passed yet
FONTS = {"serif_family": "Liberation Serif", "sans_serif_family": "Liberation Sans", "monospace_family": "DejaVu Sans Mono", "font_family": "Liberation Serif"}
# Never rendered by themselves: kept wherever they are
NON_RENDERING = frozenset(("defs", "linearGradient", "radialGradient", "pattern", "mask", "clipPath", "filter", "marker", "symbol"))
# Applied by WeasyPrint around the image, so the copy must not apply them again
OUTER_EFFECTS = ("transform", "opacity", "filter", "clip-path", "mask", "mix-blend-mode")
VIEWPORT = ("x", "y", "width", "height", "viewBox", "preserveAspectRatio")
INHERITED = (
    "fill",
    "fill-opacity",
    "fill-rule",
    "stroke",
    "stroke-width",
    "stroke-opacity",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-miterlimit",
    "stroke-dasharray",
    "stroke-dashoffset",
    "color",
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "text-anchor",
    "visibility",
    "letter-spacing",
    "word-spacing",
    "dominant-baseline",
)
_REFERENCE = re.compile(r"url\(\s*['\"]?#([^'\")\s]+)")

_RESVG: Any = None  # None: not tried yet, False: missing
_ORIGINAL_SVG_DRAW = wp_svg.SVG.draw


def _resvg() -> Any:
    global _RESVG
    if _RESVG is None:
        try:
            import resvg_py  # noqa: PLC0415

            _RESVG = resvg_py
        except ImportError:
            _RESVG = False
            LOGGER.warning("resvg_py is not installed: blurred and other raster-only SVG filters are approximated in vector")
    return _RESVG


def available() -> bool:
    return bool(_resvg())


# ---------------- scale ----------------


def _svg_draw(self: Any, stream: Any, concrete_width: float, concrete_height: float, base_url: Any, context: Any) -> Any:
    self._svg_ext_base = (stream, math.sqrt(abs(stream.ctm.determinant)) or 1)
    return _ORIGINAL_SVG_DRAW(self, stream, concrete_width, concrete_height, base_url, context)


def _css_px_per_unit(svg: Any) -> float:
    """CSS px of the image per user unit of the current stream."""
    local: float = math.sqrt(abs(svg.stream.ctm.determinant)) or 1
    base_stream, base_scale = getattr(svg, "_svg_ext_base", (None, 1))
    if svg.stream is base_stream:
        return local / float(base_scale)
    # A group stream starts with its own identity matrix: count at least the viewBox scale of the root
    viewbox = svg.tree.get_viewbox()
    root: float = svg.concrete_width / viewbox[2] if viewbox and viewbox[2] else 1
    return local * root


def _pixel_size(svg: Any, width: float, height: float) -> tuple[int, int]:
    scale = SETTINGS["scale"] * _css_px_per_unit(svg)
    pw, ph = width * scale, height * scale
    limit = min(SETTINGS["max_side"] / max(pw, ph, 1), math.sqrt(SETTINGS["max_pixels"] / max(pw * ph, 1)))
    if limit < 1:
        LOGGER.warning("SVG filter raster of %d x %d px exceeds the cap, reduced by %.2f", pw, ph, limit)
        pw, ph = pw * limit, ph * limit
    return max(1, round(pw)), max(1, round(ph))


# ---------------- standalone document ----------------


def _local(tag: object) -> str:
    return tag.split("}", 1)[-1] if isinstance(tag, str) else ""


def _index(svg: Any) -> tuple[ET.Element, dict[ET.Element, ET.Element], dict[str, ET.Element], list[ET.Element]]:
    root = svg.tree._etree_node
    cached = getattr(svg, "_svg_ext_index", None)
    if cached is None or cached[0] is not root:
        parents = {child: parent for parent in root.iter() for child in parent}
        ids = {element.get("id"): element for element in root.iter() if element.get("id")}
        styles = [element for element in root.iter() if _local(element.tag) == "style"]
        cached = (root, parents, ids, styles)
        svg._svg_ext_index = cached
    return cached


def _references(element: ET.Element) -> set[str]:
    found = set()
    for sub in element.iter():
        for key, value in sub.attrib.items():
            found.update(_REFERENCE.findall(value))
            if key in ("href", XLINK_HREF) and value.startswith("#"):
                found.add(value[1:])
        if _local(sub.tag) == "style" and sub.text:
            found.update(_REFERENCE.findall(sub.text))
    return found


def _referenced(start: set[str], ids: dict[str, ET.Element]) -> list[ET.Element]:
    seen: set[str] = set()
    todo, elements = list(start), []
    while todo:
        name = todo.pop()
        if name in seen or name not in ids:
            continue
        seen.add(name)
        elements.append(ids[name])
        todo.extend(_references(ids[name]))
    return elements


def _strip_style(value: str, names: Collection[str]) -> str:
    kept = [part for part in value.split(";") if part.strip() and part.split(":", 1)[0].strip().lower() not in names]
    return ";".join(kept)


def _shallow(element: ET.Element, drop: Collection[str] = (), extra_style: str = "") -> ET.Element:
    attrib = {key: value for key, value in element.attrib.items() if key not in drop}
    style = _strip_style(attrib.pop("style", ""), drop)
    style = ";".join(filter(None, [style, extra_style]))
    if style:
        attrib["style"] = style
    return ET.Element(element.tag, attrib)


def _target_copy(element: ET.Element, filter_value: str, strip_mask: bool) -> ET.Element:
    drop = {"transform", "opacity", "mix-blend-mode", "filter"} | ({"mask"} if strip_mask else set())
    target = copy.deepcopy(element)
    style = _strip_style(target.attrib.pop("style", ""), drop)
    for key in drop:
        target.attrib.pop(key, None)
    override = f"opacity:1;mix-blend-mode:normal;filter:{filter_value}" + (";mask:none" if strip_mask else "")
    target.set("style", ";".join(filter(None, [style, override])))
    return target


def _ancestors(element: ET.Element, parents: dict[ET.Element, ET.Element]) -> list[ET.Element]:
    """The ancestors of element, the outermost first."""
    chain = []
    ancestor = parents.get(element)
    while ancestor is not None:
        chain.append(ancestor)
        ancestor = parents.get(ancestor)
    chain.reverse()
    return chain


def _needed(referenced: list[ET.Element], parents: dict[ET.Element, ET.Element]) -> set[ET.Element]:
    """The referenced elements and all their ancestors."""
    needed = set()
    item: ET.Element | None
    for item in referenced:
        while item is not None and item not in needed:
            needed.add(item)
            item = parents.get(item)
    return needed


def _skeleton(root: ET.Element, styles: list[ET.Element], region: tuple[float, float, float, float], pixel_size: tuple[int, int], extra_defs: str) -> tuple[ET.Element, ET.Element]:
    """The root of the standalone SVG over region, and its defs with the styles of the document."""
    x, y, width, height = region
    pw, ph = pixel_size
    document = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox": f"{x} {y} {width} {height}",
            "width": str(pw),
            "height": str(ph),
            "preserveAspectRatio": "none",
            "overflow": "visible",
        },
    )
    for key, value in root.attrib.items():
        if key not in VIEWPORT and key not in OUTER_EFFECTS and key not in ("style", "id", "class"):
            document.set(key, value)
    defs = ET.SubElement(document, f"{{{SVG_NS}}}defs")
    for style in styles:
        defs.append(copy.deepcopy(style))
    if extra_defs:
        defs.extend(ET.fromstring(f'<defs xmlns="{SVG_NS}">{extra_defs}</defs>'))
    return document, defs


def _root_group(root: ET.Element) -> ET.Element:
    """The root as a group: it keeps class, id and style for the selectors, without viewport and effects."""
    group = _shallow(root, drop=VIEWPORT + OUTER_EFFECTS, extra_style=_effects_off())
    group.tag = f"{{{SVG_NS}}}g"
    return group


def _append_root(document: ET.Element, root: ET.Element, filter_value: str) -> None:
    """The root as the filtered element: its content moves into a group with the filter."""
    wrapper = _root_group(root)
    group = ET.SubElement(wrapper, f"{{{SVG_NS}}}g", {"style": f"filter:{filter_value}"})
    for child in root:
        if _local(child.tag) != "style":
            group.append(copy.deepcopy(child))
    document.append(wrapper)


def _append_detached(document: ET.Element, defs: ET.Element, node: Any, target: ET.Element, referenced: list[ET.Element]) -> None:
    """Drawn through <use> or from another document: no ancestors, the cascade of WeasyPrint stands in for them."""
    for key in INHERITED:
        if key not in target.attrib and node.get(key) is not None:
            target.set(key, str(node.get(key)))
    for item in referenced:
        defs.append(copy.deepcopy(item))
    document.append(target)


def _ancestor_copy(ancestor: ET.Element, root: ET.Element) -> ET.Element:
    if ancestor is root:
        return _root_group(root)
    drop = OUTER_EFFECTS + (VIEWPORT if _local(ancestor.tag) == "svg" else ())
    current = _shallow(ancestor, drop=drop, extra_style=_effects_off())
    if _local(ancestor.tag) == "svg":
        current.tag = f"{{{SVG_NS}}}g"
    return current


def _copy_children(ancestor: ET.Element, current: ET.Element, on_path: ET.Element, target: ET.Element, element: ET.Element, needed: set[ET.Element]) -> None:
    """The children of an ancestor the copy keeps: the path to the element, non-rendering ones and what it references."""
    for child in ancestor:
        if child is on_path:
            if child is element:
                current.append(target)
        elif _local(child.tag) == "style":
            continue
        elif _local(child.tag) in NON_RENDERING:
            current.append(copy.deepcopy(child))
        elif child in needed:
            holder = ET.SubElement(current, f"{{{SVG_NS}}}defs")
            holder.append(copy.deepcopy(child))


def _append_chain(document: ET.Element, root: ET.Element, chain: list[ET.Element], element: ET.Element, target: ET.Element, needed: set[ET.Element]) -> None:
    """The ancestors of the element, each with the children it keeps, down to the target."""
    parent_copy = document
    for index, ancestor in enumerate(chain):
        on_path = chain[index + 1] if index + 1 < len(chain) else element
        current = _ancestor_copy(ancestor, root)
        parent_copy.append(current)
        _copy_children(ancestor, current, on_path, target, element, needed)
        parent_copy = current


def build_document(svg: Any, node: Any, region: tuple[float, float, float, float], pixel_size: tuple[int, int], filter_value: str, extra_defs: str = "", strip_mask: bool = False) -> str:
    """The standalone SVG for node, in the user space of node after its own transform."""
    root, parents, ids, styles = _index(svg)
    element = node._etree_node
    chain = _ancestors(element, parents)
    referenced = _referenced(_references(element) | {name for style in styles for name in _REFERENCE.findall(style.text or "")}, ids)
    document, defs = _skeleton(root, styles, region, pixel_size, extra_defs)
    if element is root:
        _append_root(document, root, filter_value)
    elif chain and chain[0] is root:
        _append_chain(document, root, chain, element, _target_copy(element, filter_value, strip_mask), _needed(referenced, parents))
    else:
        _append_detached(document, defs, node, _target_copy(element, filter_value, strip_mask), referenced)
    return ET.tostring(document, encoding="unicode")


def _effects_off() -> str:
    return "opacity:1;filter:none;clip-path:none;mask:none;mix-blend-mode:normal"


# ---------------- render and draw ----------------


def render(svg: Any, node: Any, region: tuple[float, float, float, float], filter_value: str, extra_defs: str = "", strip_mask: bool = False) -> Any:
    """Return a RasterImage of node with the filter, over region in the current user space, or None."""
    resvg = _resvg()
    if not resvg or region[2] <= 0 or region[3] <= 0:
        return None
    pixel_size = _pixel_size(svg, region[2], region[3])
    key = (id(node._etree_node), tuple(round(v, 3) for v in region), pixel_size, filter_value, extra_defs, strip_mask)
    cache = svg.__dict__.setdefault("_svg_ext_raster_cache", {})
    if key in cache:
        return cache[key]
    image = None
    try:
        document = build_document(svg, node, region, pixel_size, filter_value, extra_defs, strip_mask)
        png = resvg.svg_to_bytes(svg_string=document, width=pixel_size[0], height=pixel_size[1], background=None, **FONTS)
        from PIL import Image  # noqa: PLC0415

        digest = hashlib.sha1(bytes(png), usedforsecurity=False).hexdigest()[:20]
        image = RasterImage(Image.open(io.BytesIO(bytes(png))), f"svgext{digest}", bytes(png))
    except BaseException as error:  # noqa: BLE001  resvg panics surface as BaseException
        if isinstance(error, (KeyboardInterrupt, SystemExit, GeneratorExit)):
            raise
        LOGGER.warning("resvg failed on an SVG filter, kept the vector approximation: %s", repr(error)[:200])
    cache[key] = image
    return image


def draw(svg: Any, image: Any, region: tuple[float, float, float, float]) -> None:
    x, y, width, height = region
    stream = svg.stream
    stream.push_state()
    stream.transform(e=x, f=y)
    image.draw(stream, width, height, {"image_rendering": "auto"})
    stream.pop_state()


def install(*, scale: float = 2.0, enabled: bool = True) -> None:
    global _RESVG
    SETTINGS["scale"] = scale
    if not enabled:
        _RESVG = False
    wp_svg.SVG.draw = _svg_draw
