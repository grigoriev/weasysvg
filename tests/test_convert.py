"""weasysvg-convert: the size rsvg-convert gives an SVG, the PDF, PNG and flat SVG, and the command line."""

from __future__ import annotations

import contextlib
import io
import os
import random
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pypdfium2 as pdfium
import pytest
from helpers import SVG_NS, close, svg
from PIL import Image

from weasysvg import convert
from weasysvg.convert import ConvertError, constant_masks_as_opacity, fewer_stops, length_px, root_attributes, shared_clip_paths, short_path_data, size_px, sized, to_pdf, to_png, to_svg

RED_RECT = svg('<rect width="200" height="100" fill="red"/>')
# A red rect cut by a binary mask: a soft mask by default, a clip in the portable PDF
KNOCKOUT = svg(
    '<defs><mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="200" height="100">'
    '<rect width="200" height="100" fill="white"/><rect x="80" width="40" height="100" fill="black"/></mask></defs>'
    '<rect width="200" height="100" fill="red" mask="url(#m)"/>'
)
LABEL = svg('<foreignObject width="200" height="100"><div xmlns="http://www.w3.org/1999/xhtml">Label</div></foreignObject>')


def page_size(pdf: bytes) -> tuple[float, float]:
    document = pdfium.PdfDocument(pdf)
    page = document[0]
    try:
        width, height = page.get_size()
        return width, height
    finally:
        close(page, document)


# ---------------- size ----------------


@pytest.mark.parametrize(
    ("value", "dpi", "expected"),
    [
        ("200", 96, 200.0),
        (" 1.5e2px ", 96, 150.0),
        ("1in", 96, 96.0),
        ("1in", 72, 72.0),
        ("2.54cm", 96, 96.0),
        ("25.4mm", 96, 96.0),
        ("72pt", 96, 96.0),
        ("6pc", 96, 96.0),
        ("2em", 96, 32.0),
        ("2ex", 192, 32.0),
        ("100%", 96, None),
        ("auto", 96, None),
        ("10vw", 96, None),
        ("", 96, None),
        (None, 96, None),
    ],
)
def test_length_px(value: str | None, dpi: float, expected: float | None) -> None:
    assert length_px(value, dpi) == pytest.approx(expected) if expected is not None else length_px(value, dpi) is None


@pytest.mark.parametrize(
    ("attributes", "expected"),
    [
        ('width="200" height="100"', (200.0, 100.0)),
        ('width="1in" height="2in"', (96.0, 192.0)),
        ('viewBox="0 0 40 30"', (40.0, 30.0)),
        ('viewBox="0,0,40,30" width="80"', (80.0, 60.0)),
        ('viewBox="0 0 40 30" height="60"', (80.0, 60.0)),
        ('viewBox="0 0 40 30" width="100%" height="100%"', (40.0, 30.0)),
        # The viewBox does not change a size the root gives
        ('viewBox="0 0 40 30" width="10" height="10"', (10.0, 10.0)),
        # An invalid viewBox is ignored, as in Chromium
        ('viewBox="0 0 10px 10px" width="10" height="20"', (10.0, 20.0)),
    ],
)
def test_size_px(attributes: str, expected: tuple[float, float]) -> None:
    assert size_px(f'<svg xmlns="{SVG_NS}" {attributes}/>'.encode(), 96, 96) == pytest.approx(expected)


@pytest.mark.parametrize("attributes", ["", 'width="100"', 'viewBox="0 0 none 30"', 'width="100%" height="100%"', 'viewBox="0 0 0 30"', 'viewBox="0 0 40"', 'width="0" height="10"'])
def test_size_px_without_a_size(attributes: str) -> None:
    document = f'<svg xmlns="{SVG_NS}" {attributes}/>'.encode()
    with pytest.raises(ConvertError, match="no size"):
        size_px(document, 96, 96)


@pytest.mark.parametrize("document", [b"", b"not xml", b"<svg><g></svg>", f'<svg xmlns="{SVG_NS}" width="1" height="1"/><extra/>'.encode()])
def test_root_attributes_of_a_broken_document(document: bytes) -> None:
    with pytest.raises(ConvertError, match="not an SVG document"):
        root_attributes(document)


# ---------------- PDF, PNG and flat SVG ----------------


def test_pdf_page_has_the_size_of_the_svg() -> None:
    # 200 x 100 px at 96 dpi: 150 x 75 pt, as rsvg-convert writes it
    assert page_size(to_pdf(RED_RECT.encode())) == pytest.approx((150, 75))
    # At 72 dpi a px is a pt
    assert page_size(to_pdf(RED_RECT.encode(), 72, 72)) == pytest.approx((200, 100))


def inflated(pdf: bytes) -> bytes:
    """The PDF with every compressed stream inflated: WeasyPrint keeps the dictionaries in object streams."""
    parts = [pdf]
    for data in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", pdf, re.S):
        with contextlib.suppress(zlib.error):
            parts.append(zlib.decompress(data))
    return b"\n".join(parts)


def test_pdf_page_at_a_scale() -> None:
    assert page_size(to_pdf(RED_RECT.encode(), scale=8)) == pytest.approx((1200, 600))


def test_flat_svg_is_drawn_large_and_sized_as_the_svg() -> None:
    # The glyphs come from a PDF eight times as large, where their hinting is below a pixel of the result
    flat = to_svg(RED_RECT.encode()).decode()
    assert 'width="150pt" height="75pt"' in flat
    assert 'viewBox="0 0 1200 600"' in flat


def test_portable_pdf_has_no_soft_mask() -> None:
    assert b"/SMask" in inflated(to_pdf(KNOCKOUT.encode()))
    assert b"/SMask" not in inflated(to_pdf(KNOCKOUT.encode(), portable=True))


def test_png_has_the_size_of_the_svg_and_a_transparent_background() -> None:
    document = svg('<rect width="100" height="100" fill="red"/>')
    image = Image.open(io.BytesIO(to_png(document.encode())))
    assert image.size == (200, 100)
    assert image.mode == "RGBA"
    assert image.getpixel((50, 50)) == (255, 0, 0, 255)
    assert image.getchannel("A").getpixel((150, 50)) == 0


def test_png_with_another_vertical_dpi() -> None:
    # A length in inches follows the dpi, a length in px does not
    document = f'<svg xmlns="{SVG_NS}" width="200" height="1in"><rect width="200" height="100" fill="red"/></svg>'
    image = Image.open(io.BytesIO(to_png(document.encode(), 96, 192)))
    assert image.size == (200, 192)


def test_png_draws_foreign_object() -> None:
    image = Image.open(io.BytesIO(to_png(LABEL.encode())))
    # The text of the label paints some pixels
    lowest, highest = cast("tuple[int, int]", image.getchannel("A").getextrema())
    assert lowest == 0
    assert highest > 0


def test_only_data_urls_are_fetched(tmp_path: Path) -> None:
    picture = tmp_path / "red.png"
    Image.new("RGB", (10, 10), "red").save(picture)
    document = svg(f'<image href="{picture.as_uri()}" width="200" height="100"/>')
    image = Image.open(io.BytesIO(to_png(document.encode())))
    assert image.getchannel("A").getextrema() == (0, 0)


@pytest.mark.parametrize(
    "html",
    [
        '<img src="{uri}" style="width:200px;height:100px"/>',
        '<div style="width:200px;height:100px;background:url({uri})"></div>',
    ],
)
def test_only_data_urls_are_fetched_inside_foreign_object(tmp_path: Path, html: str) -> None:
    picture = tmp_path / "red.png"
    Image.new("RGB", (10, 10), "red").save(picture)
    body = html.format(uri=picture.as_uri())
    document = svg(f'<foreignObject width="200" height="100"><div xmlns="http://www.w3.org/1999/xhtml">{body}</div></foreignObject>')
    image = Image.open(io.BytesIO(to_png(document.encode())))
    assert image.getchannel("A").getextrema() == (0, 0)


def test_flat_svg_keeps_the_drawing_vector() -> None:
    flat = to_svg(KNOCKOUT.encode()).decode()
    assert 'width="150pt" height="75pt"' in flat
    assert "<image" not in flat
    assert "<mask" not in flat
    assert "<clipPath" in flat


def test_flat_svg_has_no_foreign_object() -> None:
    flat = to_svg(LABEL.encode()).decode()
    assert "foreignObject" not in flat
    # The text is glyph outlines
    assert "<path" in flat


@pytest.mark.parametrize("root", [b'<svg xmlns="x" width="150" height="75" viewBox="0 0 150 75">', b'<svg height="75pt" width="150pt">'])
def test_flat_svg_size_is_in_points(root: bytes) -> None:
    # Poppler 25.03 writes the size without a unit, newer versions in pt
    flat = sized(b'<?xml version="1.0"?>\n' + root + b'<rect width="1" height="1"/></svg>', 150, 75)
    assert b'width="150pt"' in flat
    assert b'height="75pt"' in flat
    assert b'<rect width="1" height="1"/>' in flat


def test_flat_svg_reports_a_failing_pdftocairo(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(returncode=1, stderr=b"Syntax Error\n")

    monkeypatch.setattr(subprocess, "run", failing)
    document = RED_RECT.encode()
    with pytest.raises(ConvertError, match="pdftocairo failed: Syntax Error"):
        to_svg(document)


# A soft mask of a rotated radial shading, the lens of the OpenStreetMap logo, which cairo draws with gigabytes. weasysvg
# draws the stop opacity as levels, so only WeasyPrint alone makes this PDF: tests/helpers.py installs weasysvg in this process
GREEDY_PDF = """
import sys
from weasysvg import convert
stops = ('<stop stop-color="#d0e9f2" stop-opacity="0" offset="0"/><stop stop-color="#d0e9f2" stop-opacity="0" offset=".839"/>'
         '<stop stop-color="#d0e9f2" stop-opacity=".282" offset=".943"/><stop stop-color="#d0e9f2" offset="1"/>')
lens = ('M127.03 132.72c26.1 26.09 68.4 26.09 94.49 0 26.1-26.1 26.1-68.4 0-94.493-26.09-26.093-68.39-26.093-94.49 0'
        '-26.09 26.093-26.09 68.393 0 94.493z')
svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><defs><radialGradient id="g" gradientUnits="userSpaceOnUse"'
       ' cx="128" cy="86" r="47" gradientTransform="rotate(-45 -51.091 19.464)">' + stops + '</radialGradient></defs>'
       '<path d="' + lens + '" fill="url(#g)"/></svg>')
sys.stdout.buffer.write(convert.to_pdf(svg.encode()))
"""


def fake_pdftocairo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, script: str) -> None:
    """Put a pdftocairo that runs script, with the PDF and the SVG as $2 and $3, first on the PATH."""
    folder = tmp_path / "bin"
    folder.mkdir()
    fake = folder / "pdftocairo"
    fake.write_text(f"#!/bin/sh\n{script}\n")
    fake.chmod(0o755)
    monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ['PATH']}")


@pytest.mark.parametrize(
    ("script", "message"),
    [
        # Killed by the kernel, without a word and without a file
        ("kill -KILL $$", "killed by SIGKILL: out of memory, most likely$"),
        ('echo "Terminated by the service" >&2; kill -TERM $$', "killed by SIGTERM: Terminated by the service$"),
        # Under a memory limit cairo reports it and pdftocairo exits with 0, its file empty or cut short
        ('echo "Internal Error: cairo context error: out of memory" >&2; : > "$3"', "ran out of memory, over 2048 MB"),
        ('echo "Syntax Warning: odd" >&2; echo "cairo error: out of memory" >&2; echo "<svg" > "$3"', "ran out of memory"),
        # A failing allocation of Poppler or of C++ aborts
        ('echo "Out of memory" >&2; kill -ABRT $$', "ran out of memory"),
        ("echo \"terminate called after throwing an instance of 'std::bad_alloc'\" >&2; kill -ABRT $$", "ran out of memory"),
        ('echo "double free" >&2; kill -ABRT $$', "killed by SIGABRT: double free$"),
        # The loader exits with 127 too, when it cannot load a library
        ('echo "pdftocairo: error while loading shared libraries: libnss3.so" >&2; exit 127', "failed: pdftocairo: error while loading"),
        (': > "$3"', "wrote nothing$"),
        ('echo "Syntax Warning: odd" >&2; : > "$3"', "wrote nothing: Syntax Warning: odd$"),
        # Only the first line, and not all of it: out of memory, pdftocairo writes megabytes of errors
        ('printf "%0300d\\nsecond\\n" 0 >&2; exit 1', "failed: 0{200}$"),
    ],
)
def test_flat_svg_reports_why_pdftocairo_wrote_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, script: str, message: str) -> None:
    fake_pdftocairo(tmp_path, monkeypatch, script)
    document = RED_RECT.encode()
    with pytest.raises(ConvertError, match=message):
        to_svg(document)


@pytest.mark.skipif(os.name != "posix", reason="ulimit of sh")
def test_flat_svg_limits_the_memory_of_pdftocairo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_pdftocairo(tmp_path, monkeypatch, 'echo "limit $(ulimit -v)" >&2; exit 1')
    document = RED_RECT.encode()
    with pytest.raises(ConvertError, match=f"limit {convert.PDFTOCAIRO_MEMORY // 1024}$"):
        to_svg(document)


@pytest.mark.skipif(os.name != "posix", reason="sh")
def test_flat_svg_reports_a_missing_pdftocairo_behind_sh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # sh is there, pdftocairo is not: sh exits with 127
    folder = tmp_path / "bin"
    folder.mkdir()
    (folder / "sh").symlink_to(cast(str, shutil.which("sh")))
    monkeypatch.setenv("PATH", str(folder))
    document = RED_RECT.encode()
    with pytest.raises(ConvertError, match="needs pdftocairo of Poppler"):
        to_svg(document)


def test_pdftocairo_runs_alone_outside_posix() -> None:
    assert convert.pdftocairo_command("in.pdf", "out.svg", posix=False) == ["pdftocairo", "-svg", "in.pdf", "out.svg"]


@pytest.mark.skipif(shutil.which("pdftocairo") is None or os.name != "posix", reason="needs pdftocairo of Poppler and ulimit of sh")
def test_pdftocairo_out_of_memory_fails_in_seconds(tmp_path: Path) -> None:
    # Without the limit this PDF takes 8.3 GB and 39 s; with it, pdftocairo gives up in a few seconds
    pdf = tmp_path / "in.pdf"
    pdf.write_bytes(subprocess.run([sys.executable, "-c", GREEDY_PDF], capture_output=True, check=True).stdout)
    svg_path = tmp_path / "out.svg"
    result = subprocess.run(convert.pdftocairo_command(str(pdf), str(svg_path)), capture_output=True, check=False, timeout=60)  # noqa: S603
    stderr, flat = result.stderr.decode(errors="replace"), svg_path.read_bytes()
    with pytest.raises(ConvertError, match="ran out of memory"):
        convert.check_pdftocairo(result.returncode, stderr, flat)


# ---------------- command line ----------------


@pytest.mark.parametrize(("output_format", "magic"), [("pdf", b"%PDF"), ("png", b"\x89PNG"), ("svg", b"<?xml")])
def test_main_writes_the_output_file(tmp_path: Path, output_format: str, magic: bytes) -> None:
    source = tmp_path / "in.svg"
    source.write_text(RED_RECT)
    target = tmp_path / f"out.{output_format}"
    # The options pandoc passes
    assert convert.main(["-f", output_format, "-a", "--dpi-x", "96", "--dpi-y", "96", "-o", str(target), str(source)]) == 0
    assert target.read_bytes().startswith(magic)


def test_main_reads_stdin_and_writes_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = io.BytesIO()
    monkeypatch.setattr("sys.stdin", SimpleNamespace(buffer=io.BytesIO(RED_RECT.encode())))
    monkeypatch.setattr("sys.stdout", SimpleNamespace(buffer=stdout))
    assert convert.main(["-f", "png", "-a", "--dpi-x", "96", "--dpi-y", "96"]) == 0
    assert stdout.getvalue().startswith(b"\x89PNG")


@pytest.mark.parametrize("content", [None, "not an svg"])
def test_main_fails_with_a_message(tmp_path: Path, capsys: pytest.CaptureFixture[str], content: str | None) -> None:
    source = tmp_path / "in.svg"
    if content is not None:
        source.write_text(content)
    assert convert.main(["-f", "pdf", "-o", str(tmp_path / "out.pdf"), str(source)]) == 1
    assert capsys.readouterr().err.startswith("weasysvg-convert: ")
    assert not (tmp_path / "out.pdf").exists()


def test_png_too_large_is_refused() -> None:
    document = f'<svg xmlns="{SVG_NS}" width="100000" height="100000"/>'.encode()
    with pytest.raises(ConvertError, match="too large"):
        to_png(document)


def test_png_without_the_convert_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    # A None entry in sys.modules makes the import fail
    monkeypatch.setitem(sys.modules, "pypdfium2", None)
    document = RED_RECT.encode()
    with pytest.raises(ConvertError, match=r"weasysvg\[convert\]"):
        to_png(document)


def test_main_reports_an_output_it_cannot_write(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = tmp_path / "in.svg"
    source.write_text(RED_RECT)
    assert convert.main(["-f", "pdf", "-o", str(tmp_path / "missing" / "out.pdf"), str(source)]) == 1
    assert capsys.readouterr().err.startswith("weasysvg-convert: ")


@pytest.mark.parametrize("dpi", ["0", "-96", "nan", "inf", "x"])
def test_main_refuses_a_dpi_that_is_not_positive(dpi: str, tmp_path: Path) -> None:
    source = tmp_path / "in.svg"
    source.write_text(RED_RECT)
    with pytest.raises(SystemExit) as raised:
        convert.main(["-f", "pdf", "--dpi-x", dpi, "-o", str(tmp_path / "out.pdf"), str(source)])
    assert raised.value.code == 2


@pytest.mark.parametrize(
    ("failure", "message"),
    [(FileNotFoundError(2, "No such file or directory"), "needs pdftocairo of Poppler"), (subprocess.TimeoutExpired("pdftocairo", 60), "pdftocairo took longer than")],
)
def test_flat_svg_reports_pdftocairo_it_cannot_run(monkeypatch: pytest.MonkeyPatch, failure: Exception, message: str) -> None:
    def failing(*_args: object, **_kwargs: object) -> None:
        raise failure

    monkeypatch.setattr(subprocess, "run", failing)
    document = RED_RECT.encode()
    with pytest.raises(ConvertError, match=message):
        to_svg(document)


def cairo_svg(mask: str, use: str, view_box: str = ' viewBox="0 0 100 50"') -> bytes:
    """A flat SVG as cairo writes a group with an opacity."""
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="{SVG_NS}" xmlns:xlink="http://www.w3.org/1999/xlink" width="100pt" height="50pt"{view_box}><defs><filter id="filter-remove-color"/>{mask}</defs>{use}</svg>').encode()


CONSTANT = '<mask id="mask-0"><g filter="url(#filter-remove-color)"><rect x="-10" y="-5" width="120" height="60" fill="rgb(0%, 0%, 0%)" fill-opacity="0.5"/></g></mask>'


def test_a_constant_mask_becomes_an_opacity() -> None:
    flat = constant_masks_as_opacity(cairo_svg(CONSTANT, '<g mask="url(#mask-0)" opacity="0.8"><rect width="10" height="10"/></g>')).decode()
    assert "<mask" not in flat
    assert 'opacity="0.4"' in flat
    assert flat.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg"')


@pytest.mark.parametrize(
    "mask",
    [
        # Not over all of the drawing
        CONSTANT.replace('width="120"', 'width="20"'),
        # Not through the filter that keeps the alpha
        CONSTANT.replace("url(#filter-remove-color)", "url(#other)"),
        # More than one rect, or another shape
        CONSTANT.replace("</g></mask>", '<rect width="1" height="1"/></g></mask>'),
        CONSTANT.replace("<rect ", '<circle r="1" ').replace("/></g>", "/></g>"),
        CONSTANT.replace("<rect ", '<rect transform="scale(2)" '),
        CONSTANT.replace('fill-opacity="0.5"', 'fill-opacity="half"'),
        CONSTANT.replace('fill-opacity="0.5"', 'fill-opacity="2"'),
    ],
)
def test_other_masks_stay(mask: str) -> None:
    document = cairo_svg(mask, '<g mask="url(#mask-0)"><rect width="10" height="10"/></g>')
    assert constant_masks_as_opacity(document) == document


def test_a_mask_on_a_transformed_element_stays() -> None:
    # The mask then lies in the space of the transform, where it may not cover the drawing
    document = cairo_svg(CONSTANT, '<g mask="url(#mask-0)" transform="scale(3)"><rect width="10" height="10"/></g><g mask="url(#mask-0)"><rect width="5" height="5"/></g>')
    flat = constant_masks_as_opacity(document).decode()
    assert flat.count('mask="url(#mask-0)"') == 1
    assert '<mask id="mask-0">' in flat
    assert 'opacity="0.5"' in flat


def test_an_svg_without_a_view_box_stays() -> None:
    document = cairo_svg(CONSTANT, '<g mask="url(#mask-0)"/>', view_box="")
    assert constant_masks_as_opacity(document) == document


SHAPE = '<path d="M 0 0 L 10 0 L 5 8 Z"/>'
BAND = '<path d="M 0 0 L 10 0 L 10 2 L 0 2 Z"/>'


def test_identical_clip_paths_are_shared() -> None:
    # cairo writes the clip of a shape again for every paint inside it: each opacity level of a gradient
    clips = f'<clipPath id="clip-0">{SHAPE}</clipPath><clipPath id="clip-1">{BAND}</clipPath><clipPath id="clip-2">{SHAPE}</clipPath><clipPath id="clip-3" clip-path="url(#clip-2)">{BAND}</clipPath>'
    drawing = '<g clip-path="url(#clip-0)"><g clip-path="url(#clip-1)"><rect width="1" height="1"/></g></g><g clip-path="url(#clip-2)"><g clip-path="url(#clip-3)"><rect width="1" height="1"/></g></g>'
    flat = shared_clip_paths(cairo_svg(clips, drawing)).decode()
    assert flat.count("<clipPath") == 3
    assert 'id="clip-2"' not in flat
    assert 'clip-path="url(#clip-2)"' not in flat
    assert flat.count('clip-path="url(#clip-0)"') == 3
    # A clip of its own makes another clip, even with the same path
    assert '<clipPath id="clip-3" clip-path="url(#clip-0)">' in flat
    assert flat.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg"')


def test_a_flat_svg_without_shared_clip_paths_stays() -> None:
    document = cairo_svg(f'<clipPath id="clip-0">{SHAPE}</clipPath><clipPath id="clip-1">{BAND}</clipPath>', '<g clip-path="url(#clip-0)"/><g clip-path="url(#clip-1)"/>')
    assert shared_clip_paths(document) == document


def stops(*values: tuple[float, float, float]) -> str:
    """Stops as cairo writes them: offset, red in percent, opacity."""
    return "".join(f'<stop offset="{offset}" stop-color="rgb({red}%, 0%, 0%)" stop-opacity="{opacity}" />' for offset, red, opacity in values)


def gradient(body: str) -> bytes:
    return cairo_svg(f'<linearGradient id="linear-pattern-0">{body}</linearGradient>', '<rect width="1" height="1" fill="url(#linear-pattern-0)"/>')


def test_stops_on_a_line_are_left_out() -> None:
    # cairo samples a linear piece into 257 stops: the two ends make the same gradient
    line = [(k / 256, 100 * k / 256, 1 - k / 256) for k in range(257)]
    flat = fewer_stops(gradient(stops(*line))).decode()
    assert flat.count("<stop") == 2
    assert 'offset="0.0"' in flat
    assert 'offset="1.0"' in flat


def test_stops_keep_each_bend() -> None:
    # Two linear pieces: the stop where they meet stays, and so does each one a straight line from the last kept one misses
    bend = [(k / 8, 100 * min(k, 4) / 4, 1.0) for k in range(9)]
    assert fewer_stops(gradient(stops(*bend))).decode().count("<stop") == 3
    # A curve sampled as cairo samples it: a stop stays where the chord would miss the curve by more than the tolerance
    curve = [(k / 256, 100 * (k / 256) ** 2, 1.0) for k in range(257)]
    kept = fewer_stops(gradient(stops(*curve))).decode().count("<stop")
    assert 3 < kept < 257


def test_stops_of_a_jump_stay() -> None:
    # Stops at one offset are a step: none lies on a line, also the middle one of three
    jump = [(0, 0, 1.0), (0.5, 0, 1.0), (0.5, 100, 1.0), (1, 100, 1.0)]
    assert fewer_stops(gradient(stops(*jump))).decode().count("<stop") == 4
    steps = [(0, 0, 1.0), (0.5, 0, 1.0), (0.5, 50, 1.0), (0.5, 100, 1.0), (1, 100, 1.0)]
    assert fewer_stops(gradient(stops(*steps))).decode().count("<stop") == 5


@pytest.mark.parametrize(
    "body",
    [
        # Two stops, a color cairo does not write, a value that is no number
        stops((0, 0, 1.0), (1, 100, 1.0)),
        '<stop offset="0" stop-color="red"/><stop offset="0.5" stop-color="red"/><stop offset="1" stop-color="red"/>',
        stops((0, 0, 1.0), (0.5, 50, 1.0)) + '<stop offset="x" stop-color="rgb(100%, 0%, 0%)" stop-opacity="1" />',
    ],
)
def test_stops_of_another_form_stay(body: str) -> None:
    document = gradient(body)
    assert fewer_stops(document) == document


def kept_by_checking_each(values: list[tuple[float, ...]]) -> set[int]:
    """The stops to keep, found the slow way: every stop between the last kept one and the next checked again."""
    tolerances = (convert.STOP_COLOR_TOLERANCE,) * 3 + (convert.STOP_OPACITY_TOLERANCE,)

    def on_line(start: tuple[float, ...], middle: tuple[float, ...], end: tuple[float, ...]) -> bool:
        if end[0] <= start[0]:
            return False
        share = (middle[0] - start[0]) / (end[0] - start[0])
        return all(abs(a + (b - a) * share - m) <= tolerance for a, m, b, tolerance in zip(start[1:], middle[1:], end[1:], tolerances, strict=True))

    kept, anchor = {0, len(values) - 1}, 0
    for end in range(2, len(values)):
        if not all(on_line(values[anchor], values[middle], values[end]) for middle in range(anchor + 1, end)):
            anchor = end - 1
            kept.add(anchor)
    return kept


@pytest.mark.parametrize("seed", range(20))
def test_stops_kept_in_one_pass_are_the_ones_checking_each_finds(seed: int) -> None:
    # Runs of lines, curves, jumps and repeated offsets, as cairo samples a shading of several pieces
    chance = random.Random(seed)
    values, offset, color = [], 0.0, [chance.uniform(0, 100) for _ in range(3)] + [chance.random()]
    slope = [chance.uniform(-200, 200) for _ in range(3)] + [chance.uniform(-2, 2)]
    for _ in range(200):
        step = 0.0 if chance.random() < 0.05 else 1 / 256
        offset += step
        if chance.random() < 0.1:
            slope = [chance.uniform(-200, 200) for _ in range(3)] + [chance.uniform(-2, 2)]
        noise = 0.0 if chance.random() < 0.7 else chance.uniform(-0.15, 0.15)
        color = [channel + rate * step + noise for channel, rate in zip(color, slope, strict=True)]
        values.append((offset, *color))
    assert convert._kept_stops(values) == kept_by_checking_each(values)


def test_path_data_of_a_transformed_path_stays() -> None:
    # cairo writes a stroke in the units of the SVG, its scale in the transform: a hundredth there may be a pixel
    stroke = b'<path fill="none" stroke="navy" d="M 0.123456 0.2 L 0.876543 0.8 " transform="matrix(3000, 0, 0, 3000, 0, 0)"/>'
    assert short_path_data(b"<svg>" + stroke + b"</svg>") == b"<svg>" + stroke + b"</svg>"


def test_path_data_keeps_two_places() -> None:
    flat = short_path_data(b'<svg><path fill="red" d="M 1.123456 -0.004 L 10.5 2.0 Z M 1.123456 -0.004 " /><rect x="1.123456"/></svg>')
    assert flat == b'<svg><path fill="red" d="M 1.12 0 L 10.5 2 Z M 1.12 0 " /><rect x="1.123456"/></svg>'


def test_flat_svg_writes_the_clip_of_a_faded_shape_once() -> None:
    # A gradient with a transparent stop is painted once per opacity level, each inside the clip of the shape
    document = (
        f'<svg xmlns="{SVG_NS}" width="100" height="100"><defs><linearGradient id="g"><stop stop-color="navy"/><stop offset="1" stop-color="navy" stop-opacity="0"/></linearGradient></defs>'
        '<path d="M10 10 C40 0 60 30 90 10 L80 90 C50 70 30 100 10 90 Z" fill="url(#g)"/></svg>'
    ).encode()
    clips = re.findall(r"<clipPath id=\"[^\"]+\"(.*?)</clipPath>", to_svg(document).decode(), re.DOTALL)
    assert len(clips) > 1
    assert len(clips) == len(set(clips))


@pytest.mark.parametrize("band", ["-1", "inf", "wide"])
def test_main_refuses_a_band_px_below_0(band: str, tmp_path: Path) -> None:
    source = tmp_path / "in.svg"
    source.write_text(RED_RECT)
    with pytest.raises(SystemExit) as raised:
        convert.main(["-f", "svg", "--band-px", band, "-o", str(tmp_path / "out.svg"), str(source)])
    assert raised.value.code == 2


FADED = svg('<defs><linearGradient id="g"><stop stop-color="navy"/><stop offset="1" stop-color="navy" stop-opacity="0"/></linearGradient></defs><rect width="200" height="100" fill="url(#g)"/>')


def test_main_passes_band_px_to_the_flat_svg(tmp_path: Path) -> None:
    # 200 px of fading: a level per pixel at 1 px, per 64th at 0, 50 levels 4 px wide
    source = tmp_path / "in.svg"
    source.write_text(FADED)
    counts = {}
    for band in ("0", "4"):
        out = tmp_path / f"out-{band}.svg"
        assert convert.main(["-f", "svg", "--band-px", band, "-o", str(out), str(source)]) == 0
        counts[band] = out.read_text().count("<clipPath")
    assert counts["4"] < counts["0"]
