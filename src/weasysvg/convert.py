"""A command line converter from SVG to PDF, PNG or a flat SVG, compatible with the options of ``rsvg-convert`` that pandoc uses.

pandoc calls ``rsvg-convert`` by name: ``-f pdf ... -o out.pdf in.svg`` for a PDF through LaTeX, and
``-f png ...`` from stdin to stdout for the PNG fallback of an SVG in DOCX. Installed under that name,
this converter draws the SVG with WeasyPrint and weasysvg instead of librsvg, so ``<foreignObject>``,
filters and masks render. The PDF stays vector. The PNG is the PDF rasterized by PDFium.

``-f svg`` is not an option of rsvg-convert. It flattens the SVG for Word and LibreOffice: see to_svg().

The size follows ``rsvg-convert``: the ``width`` and ``height`` of the root, in pixels at the given
DPI, or the ``viewBox`` when they are missing or relative. A PDF page is that size at 72 points per
DPI pixels, a PNG has that many pixels.
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import math
import os
import pathlib
import re
import signal
import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from typing import IO, cast

import weasyprint
from weasyprint.urls import URLFetcher

import weasysvg
from weasysvg._core import DEFAULT_BAND_PX

DEFAULT_DPI = 96.0
# The CSS units an absolute length of the root can carry, in inches
UNIT_INCHES = {"in": 1.0, "cm": 1 / 2.54, "mm": 1 / 25.4, "pt": 1 / 72, "pc": 1 / 6}
# What rsvg takes for a font-relative length on the root, in pixels at 96 DPI
FONT_PX = {"em": 16.0, "ex": 8.0}
VIEWBOX_PARTS = 4
# The largest PNG drawn from an untrusted SVG: one side, and its pixels. The limits of pandoc-service for Chromium
MAX_PNG_SIDE = 10_000
MAX_PNG_PIXELS = 50_000_000
# The flat SVG is read from a PDF this many times larger, its viewBox as large and its size the SVG's own. cairo
# writes each glyph as its outline at the size it is drawn, hinted: at 24 px a bold label came out wider and
# heavier in every viewer, at 8 times that the hinting is below a pixel of the result.
FLAT_SCALE = 8
# How long pdftocairo may read back one PDF, in seconds
PDFTOCAIRO_TIMEOUT = 60
# The address space pdftocairo may take, in bytes. The flat SVG of the corpus needs under 50 MB, but cairo draws a soft mask
# of a rotated radial shading with gigabytes: out of memory it fails at once, rather than taking the memory of the service.
PDFTOCAIRO_MEMORY = 2 * 1024**3
# The exit code of sh when it finds no command to exec
COMMAND_NOT_FOUND = 127
# The most of the error output of pdftocairo a ConvertError repeats, in characters
MAX_MESSAGE = 200


class ConvertError(Exception):
    """The SVG cannot be converted."""


def root_attributes(svg: bytes) -> dict[str, str]:
    """The attributes of the root element. The whole document is parsed: WeasyPrint draws nothing for a broken one, silently."""
    parser: ET.XMLPullParser[ET.Element] = ET.XMLPullParser(events=("start",))
    try:
        parser.feed(svg)
        parser.close()
    except ET.ParseError as error:
        raise ConvertError(f"not an SVG document: {error}") from error
    # A parsed document has a root, and its "start" event comes first
    _, root = next(cast("Iterator[tuple[str, ET.Element]]", parser.read_events()))
    return dict(root.attrib)


def length_px(value: str | None, dpi: float) -> float | None:
    """A length of the root in pixels at dpi, or None when it is missing, relative or invalid."""
    text = (value or "").strip()
    # The unit is the letters or percent sign at the end; an exponent is followed by a digit
    digits = text.rstrip("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ%")
    unit = text[len(digits) :].lower()
    try:
        number = float(digits.rstrip())
    except ValueError:
        return None
    if unit in ("", "px"):
        return number
    if unit in UNIT_INCHES:
        return number * UNIT_INCHES[unit] * dpi
    if unit in FONT_PX:
        return number * FONT_PX[unit] * dpi / DEFAULT_DPI
    return None


def size_px(svg: bytes, dpi_x: float, dpi_y: float) -> tuple[float, float]:
    """The size of the SVG in pixels, as rsvg-convert computes it."""
    attributes = root_attributes(svg)
    width = length_px(attributes.get("width"), dpi_x)
    height = length_px(attributes.get("height"), dpi_y)
    try:
        box = [float(part) for part in re.split(r"[\s,]+", attributes.get("viewBox", "").strip()) if part]
    except ValueError:
        box = []  # an invalid viewBox is ignored, as in Chromium
    if len(box) == VIEWBOX_PARTS and box[2] > 0 and box[3] > 0:
        if width is None and height is None:
            width, height = box[2], box[3]
        elif width is None:
            width = height * box[2] / box[3]  # type: ignore[operator]
        elif height is None:
            height = width * box[3] / box[2]
    if not width or not height or width <= 0 or height <= 0:
        raise ConvertError("the SVG has no size: no width and height, and no viewBox")
    return width, height


def page_html(svg: bytes, width_pt: float, height_pt: float) -> str:
    """One page of exactly the SVG's size, with the SVG as its only content."""
    data = base64.b64encode(svg).decode("ascii")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
        f"@page{{size:{width_pt}pt {height_pt}pt;margin:0}}"
        "html,body{margin:0;padding:0}"
        f"img{{display:block;width:{width_pt}pt;height:{height_pt}pt}}"
        f'</style></head><body><img src="data:image/svg+xml;base64,{data}"></body></html>'
    )


def to_pdf(svg: bytes, dpi_x: float = DEFAULT_DPI, dpi_y: float = DEFAULT_DPI, *, portable: bool = False, scale: float = 1.0, band_px: float = DEFAULT_BAND_PX) -> bytes:
    """The SVG as a one-page vector PDF. Only data: URLs are fetched, as rsvg-convert fetches no remote file.

    portable draws without soft masks and blend modes where weasysvg can, with levels of opacity at least
    band_px wide, see weasysvg.portable(). scale enlarges the page and the drawing on it.
    """
    width, height = size_px(svg, dpi_x, dpi_y)
    html = page_html(svg, width * 72 / dpi_x * scale, height * 72 / dpi_y * scale)
    document = weasyprint.HTML(string=html, url_fetcher=URLFetcher(allowed_protocols={"data"}))
    with weasysvg.portable(band_px=band_px, zoom=scale) if portable else contextlib.nullcontext():
        pdf: bytes = document.write_pdf()
    return pdf


def to_png(svg: bytes, dpi_x: float = DEFAULT_DPI, dpi_y: float = DEFAULT_DPI) -> bytes:
    """The SVG as a PNG of its size in pixels, on a transparent background."""
    import io

    try:
        import pypdfium2 as pdfium
    except ImportError as error:
        raise ConvertError('PNG output needs the convert extra: pip install "weasysvg[convert]"') from error

    width, height = size_px(svg, dpi_x, dpi_y)
    if max(width, height) > MAX_PNG_SIDE or width * height > MAX_PNG_PIXELS:
        raise ConvertError(f"the PNG would be too large: {width:g} x {height:g} pixels")
    document = pdfium.PdfDocument(to_pdf(svg, dpi_x, dpi_y))
    page = document[0]
    bitmap = page.render(scale=dpi_x / 72, fill_color=(255, 255, 255, 0))
    try:
        image = bitmap.to_pil()
    finally:
        # Children first: see tests/helpers.close
        bitmap.close()
        page.close()
        document.close()
    # The page is width x height pixels at dpi_x: only a different dpi_y or the rounding changes it
    target = (max(1, round(width)), max(1, round(height)))
    if image.size != target:
        image = image.resize(target)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def to_svg(svg: bytes, dpi_x: float = DEFAULT_DPI, dpi_y: float = DEFAULT_DPI, *, band_px: float = DEFAULT_BAND_PX) -> bytes:
    """The SVG flattened to paths, clips, gradients and images, which Word draws: the portable PDF read back by pdftocairo of Poppler.

    Word draws no <foreignObject> and no filters, and only some masks. The flat SVG keeps the drawing as
    weasysvg renders it, and its text becomes glyph outlines. It is vector where the portable PDF has no
    soft mask: cairo turns each soft mask into an image.
    """
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = os.path.join(tmp, "in.pdf")
        svg_path = os.path.join(tmp, "out.svg")
        with open(pdf_path, "wb") as handle:
            handle.write(to_pdf(svg, dpi_x, dpi_y, portable=True, scale=FLAT_SCALE, band_px=band_px))
        try:
            result = subprocess.run(pdftocairo_command(pdf_path, svg_path), capture_output=True, check=False, timeout=PDFTOCAIRO_TIMEOUT)  # noqa: S603
        except FileNotFoundError as error:
            raise ConvertError(MISSING_PDFTOCAIRO) from error
        except subprocess.TimeoutExpired as error:
            raise ConvertError(f"pdftocairo took longer than {PDFTOCAIRO_TIMEOUT} s") from error
        # Killed, pdftocairo may leave no file at all
        flat = pathlib.Path(svg_path).read_bytes() if os.path.exists(svg_path) else b""
        check_pdftocairo(result.returncode, result.stderr.decode(errors="replace"), flat)
    width, height = size_px(svg, dpi_x, dpi_y)
    # Rounded first: clip paths that differ in the sixth place are then one
    return sized(shared_clip_paths(fewer_stops(short_path_data(constant_masks_as_opacity(flat)))), width * 72 / dpi_x, height * 72 / dpi_y)


MISSING_PDFTOCAIRO = "SVG output needs pdftocairo of Poppler on the PATH"


def pdftocairo_command(pdf_path: str, svg_path: str, posix: bool = os.name == "posix") -> list[str]:
    """The command that writes the flat SVG of pdf_path to svg_path, at most PDFTOCAIRO_MEMORY of address space on POSIX.

    sh sets the limit and execs pdftocairo, so the exit code and the signal are its own. A preexec_fn would set
    it without sh, but is not safe in a process with threads, as pandoc-service runs the flattening. Where ulimit
    -v is not supported, pdftocairo runs without the limit.
    """
    if not posix:
        return ["pdftocairo", "-svg", pdf_path, svg_path]
    script = 'ulimit -v "$0" 2>/dev/null; exec pdftocairo -svg "$1" "$2"'
    return ["sh", "-c", script, str(PDFTOCAIRO_MEMORY // 1024), pdf_path, svg_path]


def check_pdftocairo(returncode: int, stderr: str, flat: bytes) -> None:
    """Raise ConvertError when pdftocairo did not write the whole flat SVG.

    Out of memory, pdftocairo is killed by the kernel without a word; under the limit, cairo reports it on the
    error output, and pdftocairo exits with 0 and a file cut short or empty. An allocation of Poppler or of C++
    that fails prints "Out of memory" or std::bad_alloc and aborts.
    """
    # Out of memory, pdftocairo repeats its error for every drawing: megabytes of it, of which the message keeps one line
    message = stderr.strip().partition("\n")[0][:MAX_MESSAGE]
    out_of_memory = "out of memory" in stderr.lower() or "bad_alloc" in stderr
    if out_of_memory and returncode in (0, -signal.SIGABRT):
        raise ConvertError(f"pdftocairo ran out of memory, over {PDFTOCAIRO_MEMORY // 1024**2} MB")
    if returncode < 0:
        name = signal.Signals(-returncode).name
        hint = ": out of memory, most likely" if -returncode == signal.SIGKILL else ""
        raise ConvertError(f"pdftocairo was killed by {name}{hint}" + (f": {message}" if message else ""))
    # sh found no pdftocairo; the loader exits with 127 as well, when it cannot load a library
    if returncode == COMMAND_NOT_FOUND and "pdftocairo" in message and "not found" in message:
        raise ConvertError(MISSING_PDFTOCAIRO)
    if returncode != 0:
        raise ConvertError(f"pdftocairo failed: {message}")
    if not flat:
        raise ConvertError(f"pdftocairo wrote nothing: {message}" if message else "pdftocairo wrote nothing")


SVG_NS = "http://www.w3.org/2000/svg"
# What starts each flat SVG a rewrite of the tree returns, as cairo starts it
XML_DECLARATION = b'<?xml version="1.0" encoding="UTF-8"?>\n'
XLINK_NS = "http://www.w3.org/1999/xlink"
# What cairo writes for the alpha of a group: a mask of one rect of black at that opacity, through this filter
_REMOVE_COLOR = "url(#filter-remove-color)"


def constant_masks_as_opacity(flat: bytes) -> bytes:
    """The flat SVG with each mask of one constant opacity over the whole drawing written as an opacity.

    cairo writes the opacity of a group (CSS opacity, a faded filter layer) as a mask: a rect over the
    whole drawing in black at that opacity, through a filter that keeps its alpha. Word draws only some
    masks, and every SVG renderer draws an opacity.
    """
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    root = ET.fromstring(flat)
    box = [float(part) for part in root.get("viewBox", "").split()]
    if len(box) != VIEWBOX_PARTS:
        return flat
    opacities = {}
    for mask in root.iter(f"{{{SVG_NS}}}mask"):
        opacity = _constant_opacity(mask, box)
        if opacity is not None:
            opacities[f"url(#{mask.get('id')})"] = opacity
    if not opacities:
        return flat
    _drop_unused_masks(root, _as_opacity(root, opacities))
    return XML_DECLARATION + ET.tostring(root)


def shared_clip_paths(flat: bytes) -> bytes:
    """The flat SVG with each clip path written once, its copies named by the first.

    cairo writes the clip of a shape anew for every paint inside it. A gradient with a transparent stop is
    painted once per opacity level in the portable PDF, so a long outline came out once per level.
    """
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    root = ET.fromstring(flat)
    first: dict[bytes, str] = {}
    shared: dict[str, str] = {}
    copies: list[ET.Element] = []
    # Document order: cairo defines a clip before the clip that names it
    for clip in root.iter(f"{{{SVG_NS}}}clipPath"):
        _name_shared(clip, shared)
        for child in clip.iter():
            _name_shared(child, shared)
        attributes = sorted((name, value) for name, value in clip.attrib.items() if name != "id")
        key = repr(attributes).encode() + b"".join(ET.tostring(child) for child in clip)
        if key in first:
            shared[f"url(#{clip.get('id')})"] = first[key]
            copies.append(clip)
        else:
            first[key] = f"url(#{clip.get('id')})"
    if not copies:
        return flat
    for element in root.iter():
        _name_shared(element, shared)
    parents = {child: parent for parent in root.iter() for child in parent}
    for clip in copies:
        parents[clip].remove(clip)
    return XML_DECLARATION + ET.tostring(root)


def _name_shared(element: ET.Element, shared: dict[str, str]) -> None:
    reference = element.get("clip-path")
    if reference in shared:
        element.set("clip-path", shared[reference])


def _as_opacity(root: ET.Element, opacities: dict[str, float]) -> set[str]:
    """Write each use of a constant mask as an opacity; return the masks it replaced somewhere.

    A transformed element keeps its mask: the mask then lies in the space of the transform, where it may not
    cover the drawing.
    """
    used: set[str] = set()
    for element in root.iter():
        reference = element.get("mask")
        if reference in opacities and element.get("transform") is None:
            del element.attrib["mask"]
            element.set("opacity", f"{float(element.get('opacity', '1')) * opacities[reference]:g}")
            used.add(reference)
    return used


def _drop_unused_masks(root: ET.Element, replaced: set[str]) -> None:
    """Remove each replaced mask that nothing names any more."""
    named = {element.get("mask") for element in root.iter()}
    unused = [(parent, child) for parent in root.iter() for child in parent if child.tag == f"{{{SVG_NS}}}mask" and f"url(#{child.get('id')})" in replaced - named]
    for parent, child in unused:
        parent.remove(child)


def _constant_opacity(mask: ET.Element, box: list[float]) -> float | None:
    """The opacity of a mask that is one black rect over all of box through the filter that keeps its alpha, else None."""
    children = list(mask)
    if len(children) != 1 or children[0].get("filter") != _REMOVE_COLOR or len(list(children[0])) != 1:
        return None
    rect = children[0][0]
    if rect.tag != f"{{{SVG_NS}}}rect" or rect.get("transform") is not None:
        return None
    try:
        x, y, width, height = (float(rect.get(name, "0")) for name in ("x", "y", "width", "height"))
        opacity = float(rect.get("fill-opacity", "1"))
    except ValueError:
        return None
    left, top, right, bottom = box[0], box[1], box[0] + box[2], box[1] + box[3]
    covers = x <= left and y <= top and x + width >= right and y + height >= bottom
    return opacity if covers and 0 <= opacity <= 1 else None


# How far a stop may lie off the line between the stops kept around it: in percent of a color channel, and in opacity
STOP_COLOR_TOLERANCE = 0.1
STOP_OPACITY_TOLERANCE = 0.001
_STOP_COLOR = re.compile(r"rgb\(\s*([-\d.]+)%,\s*([-\d.]+)%,\s*([-\d.]+)%\s*\)")


def fewer_stops(flat: bytes) -> bytes:
    """The flat SVG with the stops of each gradient that lie on the line between their neighbors left out.

    cairo samples the function of a PDF shading into 257 stops, where WeasyPrint wrote a few linear pieces:
    the blurred glare of Tux came out at 32361 stops, of which 293 change the gradient.
    """
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    root = ET.fromstring(flat)
    dropped = False
    for gradient in root.iter():
        if gradient.tag not in (f"{{{SVG_NS}}}linearGradient", f"{{{SVG_NS}}}radialGradient"):
            continue
        stops = [child for child in gradient if child.tag == f"{{{SVG_NS}}}stop"]
        values = [_stop_values(stop) for stop in stops]
        if len(stops) < 3 or any(value is None for value in values):  # noqa: PLR2004
            continue
        kept = _kept_stops(cast("list[tuple[float, ...]]", values))
        for index, stop in enumerate(stops):
            if index not in kept:
                gradient.remove(stop)
                dropped = True
    if not dropped:
        return flat
    return XML_DECLARATION + ET.tostring(root)


def _stop_values(stop: ET.Element) -> tuple[float, ...] | None:
    """Offset, red, green, blue in percent and opacity of a stop as cairo writes it; None for any other form."""
    color = _STOP_COLOR.fullmatch(stop.get("stop-color", ""))
    try:
        return (float(stop.get("offset", "")), *(float(channel) for channel in color.groups()), float(stop.get("stop-opacity", "1"))) if color else None
    except ValueError:
        return None


def _kept_stops(values: list[tuple[float, ...]]) -> set[int]:
    """The stops that keep the gradient within the tolerances: the ends, and each one the line from the last kept one cannot skip.

    The stops between the last kept one and the next allow, per channel, a range of slopes of that line: each new stop
    narrows it, and the line to a stop is good while its slopes lie in all ranges. One pass, where checking every stop
    between again for each new one took a second for the 32361 stops of Tux.
    """
    tolerances = (STOP_COLOR_TOLERANCE,) * 3 + (STOP_OPACITY_TOLERANCE,)
    kept, anchor = {0, len(values) - 1}, 0
    ranges = _open_ranges()
    for end in range(1, len(values)):
        if end > anchor + 1 and not _within(values[anchor], values[end], ranges):
            anchor = end - 1
            kept.add(anchor)
            ranges = _open_ranges()
        _narrow(ranges, values[anchor], values[end], tolerances)
    return kept


def _open_ranges() -> list[list[float]]:
    return [[-math.inf, math.inf] for _ in range(4)]


def _within(start: tuple[float, ...], end: tuple[float, ...], ranges: list[list[float]]) -> bool:
    """Whether the line from start to end passes every stop that narrowed ranges, within the tolerances."""
    span = end[0] - start[0]
    if span <= 0:
        return False  # a jump at one offset: both stops make it
    return all(low <= (b - a) / span <= high for a, b, (low, high) in zip(start[1:], end[1:], ranges, strict=True))


def _narrow(ranges: list[list[float]], start: tuple[float, ...], middle: tuple[float, ...], tolerances: tuple[float, ...]) -> None:
    """Narrow ranges to the slopes of the lines from start that pass middle within the tolerances."""
    span = middle[0] - start[0]
    for (a, m, tolerance), bounds in zip(zip(start[1:], middle[1:], tolerances, strict=True), ranges, strict=True):
        if span > 0:
            bounds[0], bounds[1] = max(bounds[0], (m - tolerance - a) / span), min(bounds[1], (m + tolerance - a) / span)
        elif abs(m - a) > tolerance:
            # At the offset of start, a line passes middle only when start does already
            bounds[0], bounds[1] = math.inf, -math.inf


# The places a coordinate of a path keeps. The flat SVG is drawn FLAT_SCALE times larger: a hundredth of a unit is a
# few thousandths of a pixel of the result, where cairo writes six places
PATH_PLACES = 2
_PATH = re.compile(rb"<path\b[^>]*>")
_DATA = re.compile(rb'\sd="[^"]*"')
# A number starts after no digit or point, and gives back no digit: a long run of digits without a point is passed
# over once, where a search from each of its digits read the rest of the run again
_DECIMAL = re.compile(rb"(?<![\d.])-?\d++\.\d++")


def short_path_data(flat: bytes) -> bytes:
    """The flat SVG with the coordinates of its paths rounded to PATH_PLACES.

    A path with a transform keeps them: cairo writes a stroke in the units of the SVG and its scale in the transform,
    where a hundredth of a unit of a viewBox one unit wide was a pixel of the result.
    """

    def short(number: re.Match[bytes]) -> bytes:
        text = f"{float(number.group(0)):.{PATH_PLACES}f}".rstrip("0").rstrip(".")
        return b"0" if text == "-0" else text.encode()

    def path(tag: re.Match[bytes]) -> bytes:
        text = tag.group(0)
        return text if b" transform=" in text else _DATA.sub(lambda data: _DECIMAL.sub(short, data.group(0)), text)

    return _PATH.sub(path, flat)


def sized(flat: bytes, width_pt: float, height_pt: float) -> bytes:
    """The flat SVG with the size of its root in points. Poppler 25.03 writes it without a unit, which reads as px."""
    for name, value in ((b"width", width_pt), (b"height", height_pt)):
        attribute = re.compile(rb"(<svg\b[^>]*?\s" + name + rb'=")[^"]*(")')
        flat = attribute.sub(rb"\g<1>" + f"{value:g}pt".encode() + rb"\g<2>", flat, count=1)
    return flat


def positive(text: str) -> float:
    """A DPI: a finite number above 0."""
    try:
        value = float(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"not a number: {text}") from error
    if not 0 < value < math.inf:
        raise argparse.ArgumentTypeError(f"not a positive number: {text}")
    return value


def not_negative(text: str) -> float:
    """A width of a level: a finite number, 0 or more."""
    try:
        value = float(text)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"not a number: {text}") from error
    if not 0 <= value < math.inf:
        raise argparse.ArgumentTypeError(f"not a number of 0 or more: {text}")
    return value


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="weasysvg-convert", description="Convert SVG to PDF, PNG or a flat SVG with WeasyPrint and weasysvg. Accepts the rsvg-convert options pandoc uses.")
    parser.add_argument("-f", "--format", default="png", choices=("png", "pdf", "svg"), help="output format (default: png)")
    parser.add_argument("-o", "--output", help="output file (default: stdout)")
    parser.add_argument("-d", "--dpi-x", type=positive, default=DEFAULT_DPI, help="pixels per inch, horizontal (default: 96)")
    parser.add_argument("-p", "--dpi-y", type=positive, default=DEFAULT_DPI, help="pixels per inch, vertical (default: 96)")
    parser.add_argument(
        "--band-px",
        type=not_negative,
        default=DEFAULT_BAND_PX,
        help=f"flat SVG: the least width of an opacity level of a gradient, in px as shown; 0 for a level per 1/64 (default: {DEFAULT_BAND_PX:g})",
    )
    parser.add_argument("-a", "--keep-aspect-ratio", action="store_true", help="accepted for compatibility: the size is always the SVG's own")
    parser.add_argument("input", nargs="?", default="-", help="input SVG file (default: stdin)")
    return parser.parse_args(argv)


def read_input(name: str, stdin: IO[bytes]) -> bytes:
    if name == "-":
        return stdin.read()
    # A command line tool reads the file its caller names, as rsvg-convert does
    with open(name, "rb") as handle:  # NOSONAR
        return handle.read()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    weasysvg.install()
    try:
        svg = read_input(args.input, sys.stdin.buffer)
        result = to_svg(svg, args.dpi_x, args.dpi_y, band_px=args.band_px) if args.format == "svg" else {"pdf": to_pdf, "png": to_png}[args.format](svg, args.dpi_x, args.dpi_y)
        if args.output:
            # A command line tool writes the file its caller names, as rsvg-convert does
            with open(args.output, "wb") as handle:  # NOSONAR
                handle.write(result)
        else:
            sys.stdout.buffer.write(result)
    except (ConvertError, OSError) as error:
        print(f"weasysvg-convert: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
