"""Filter chains: vector layers, CSS filter functions, and the resvg raster fallback."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

import pytest
from helpers import content, pixel, render, svg

from weasysvg import filters, raster
from weasysvg.filters import Layer, Unsupported

RED = (255, 0, 0)
WHITE = (255, 255, 255)


def near(actual: tuple[int, int, int], expected: tuple[int, int, int], tolerance: int = 40) -> bool:
    return all(abs(a - e) <= tolerance for a, e in zip(actual, expected, strict=True))


def filtered(primitives: str, attributes: str = "", target: str = '<rect x="20" y="20" width="60" height="40" fill="red" filter="url(#f)"/>') -> str:
    return svg(f'<defs><filter id="f"{attributes}>{primitives}</filter></defs>{target}', height=120)


@pytest.fixture
def no_resvg(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(raster, "_RESVG", False)
    yield


def images(pdf: bytes) -> int:
    """The color images of the PDF, without their alpha soft masks."""
    return len(re.findall(r"<<[^\n]*/Subtype /Image[^\n]*/DeviceRGB", pdf.decode("latin-1")))


# ---------------- helpers ----------------


def test_std_and_num() -> None:
    assert filters._std("2", "0") == (2.0, 2.0)
    assert filters._std("1,3", "0") == (1.0, 3.0)
    assert filters._std(None, "2") == (2.0, 2.0)
    assert filters._std("-1", "0") == (0.0, 0.0)
    assert filters._std("1 2 3", "0") == (0.0, 0.0)
    assert filters._std("", "") == (0.0, 0.0)
    assert filters._num("10%") == 0.0
    assert filters._num(None, 2) == 2
    assert filters._add_blur((3.0, 0.0), (4.0, 0.0)) == (5.0, 0.0)


@pytest.mark.parametrize(
    ("value", "kinds", "blur"),
    [
        ("blur(4px)", ["source"], (4.0, 4.0)),
        ("blur()", ["source"], (0.0, 0.0)),
        ("drop-shadow(2px 3px 4px red)", ["alpha", "source"], (2.0, 2.0)),
        ("drop-shadow(rgba(0, 0, 0, 0.5) 2px 3px)", ["alpha", "source"], (0.0, 0.0)),
    ],
)
def test_function_layers(value: str, kinds: list[str], blur: tuple[float, float]) -> None:
    layers = filters._function_layers(value)
    assert [layer.kind for layer in layers] == kinds
    assert layers[0].blur == blur


@pytest.mark.parametrize("value", ["blur(1px 2px)", "drop-shadow(2px, 3px)", "drop-shadow(red)", "sepia(1)"])
def test_function_layers_reject(value: str) -> None:
    with pytest.raises(Unsupported):
        filters._function_layers(value)


def test_layer_filter_markup() -> None:
    from weasyprint.svg.utils import color

    region = (0.0, 0.0, 10.0, 10.0)
    source = filters._layer_filter(Layer("source", blur=(1, 1), opacity=0.5), region, None)
    assert "feComponentTransfer" in source
    assert "color-interpolation-filters" not in source
    node = {"color-interpolation-filters": "sRGB"}
    lum = filters._layer_filter(Layer("lum", blur=(1, 1)), region, node)
    assert 'type="luminanceToAlpha"' in lum
    assert 'color-interpolation-filters="sRGB"' in lum
    alpha = filters._layer_filter(Layer("alpha", blur=(1, 1), rgba=color("red"), opacity=0.5), region, None)
    assert 'flood-color="rgb(255.00,0.00,0.00)" flood-opacity="0.5"' in alpha


# ---------------- vector chains ----------------


def test_offset_flood_merge_shadow_is_vector(no_resvg: None) -> None:
    pdf = render(
        filtered(
            '<feFlood flood-color="blue" flood-opacity="0.5" result="f"/><feComposite in="f" in2="SourceAlpha" operator="in" result="shadow"/>'
            '<feOffset in="shadow" dx="10" dy="10" result="moved"/><feMerge><feMergeNode in="moved"/><feMergeNode in="SourceGraphic"/><desc/></feMerge>',
        )
    )
    assert images(pdf) == 0
    assert "/SMask" in pdf.decode("latin-1")
    # The shadow shows below and right of the red rectangle
    assert near(pixel(pdf, 60, 45), (128, 128, 255), 60)
    assert near(pixel(pdf, 30, 30), RED)


def test_drop_shadow_primitive_and_blend(no_resvg: None) -> None:
    pdf = render(filtered('<feDropShadow dx="5" dy="5" stdDeviation="0" flood-color="black"/><feBlend in2="SourceGraphic"/>'))
    assert images(pdf) == 0
    assert near(pixel(pdf, 63, 47), (0, 0, 0), 60)


def test_flood_subregion_and_composite_over(no_resvg: None) -> None:
    pdf = render(filtered('<feFlood x="0" y="0" width="10" height="10" flood-color="lime" result="f"/><feComposite in="SourceGraphic" in2="f" operator="over"/>', ' filterUnits="userSpaceOnUse" x="0" y="0" width="200" height="120"'))
    assert near(pixel(pdf, 3, 3), (0, 255, 0))
    assert near(pixel(pdf, 30, 30), RED)


def test_component_transfer_fades(no_resvg: None) -> None:
    pdf = render(filtered('<feComponentTransfer><feFuncA type="linear" slope="0.5" intercept="0"/></feComponentTransfer>'))
    assert "/x" in content(pdf)
    assert near(pixel(pdf, 30, 30), (255, 128, 128), 40)


def test_empty_component_transfer_and_saturate(no_resvg: None) -> None:
    pdf = render(filtered('<feComponentTransfer/><feColorMatrix type="saturate" values="1"/>'))
    assert near(pixel(pdf, 30, 30), RED)


def test_luminance_to_alpha_in_srgb(no_resvg: None) -> None:
    pdf = render(filtered('<feColorMatrix type="luminanceToAlpha"/>', ' color-interpolation-filters="sRGB"'))
    assert "/Luminosity" in pdf.decode("latin-1")


def test_filter_with_opacity_and_mask(no_resvg: None) -> None:
    target = '<defs><mask id="m"><rect width="200" height="120" fill="white"/></mask></defs><rect x="20" y="20" width="60" height="40" fill="red" opacity="0.5" mask="url(#m)" filter="url(#f)"/>'
    pdf = render(filtered('<feOffset dx="0" dy="0"/>', target=target))
    assert near(pixel(pdf, 30, 30), (255, 128, 128), 40)


# ---------------- unsupported without resvg ----------------


@pytest.mark.parametrize(
    "primitives",
    [
        '<feTurbulence baseFrequency="0.05"/>',
        '<feBlend mode="multiply" in2="SourceGraphic"/>',
        '<feComposite operator="xor" in2="SourceGraphic"/>',
        '<feComponentTransfer><feFuncR type="table"/></feComponentTransfer>',
        '<feColorMatrix type="hueRotate" values="90"/>',
        '<feColorMatrix type="luminanceToAlpha"/>',
        '<feOffset in="nowhere"/>',
        '<feGaussianBlur stdDeviation="3"/>',
    ],
)
def test_unsupported_chain_draws_the_element(no_resvg: None, primitives: str) -> None:
    pdf = render(filtered(primitives))
    assert images(pdf) == 0
    assert near(pixel(pdf, 30, 30), RED, 60)


def test_primitive_units_and_bad_references(no_resvg: None) -> None:
    pdf = render(filtered('<feOffset dx="0.1"/>', ' primitiveUnits="objectBoundingBox"'))
    assert near(pixel(pdf, 30, 30), RED)
    pdf = render(svg('<rect x="20" y="20" width="60" height="40" fill="red" filter="url(#missing)"/><g filter="url(#f)"/><defs><filter id="f"/></defs>'))
    assert near(pixel(pdf, 30, 30), RED)


def test_css_functions_without_resvg(no_resvg: None) -> None:
    body = '<rect x="20" y="20" width="60" height="40" fill="red" style="filter:drop-shadow(5px 5px 0 black)"/><rect x="120" y="20" width="40" height="40" fill="red" style="filter:sepia(1)"/>'
    pdf = render(svg(body, height=120))
    assert near(pixel(pdf, 63, 47), (0, 0, 0), 60)
    assert near(pixel(pdf, 100, 30), RED)


def test_filter_on_the_root_without_resvg(no_resvg: None) -> None:
    pdf = render(filtered('<feOffset dx="10"/>', target='<rect x="20" y="20" width="60" height="40" fill="red"/>').replace("<svg ", '<svg filter="url(#f)" ', 1))
    assert near(pixel(pdf, 30, 30), RED)


# ---------------- raster through resvg ----------------


def test_blur_layer_goes_raster() -> None:
    pdf = render(filtered('<feGaussianBlur stdDeviation="4"/>'))
    assert images(pdf) == 1
    assert near(pixel(pdf, 40, 30), RED, 60)


def test_blurred_shadow_keeps_the_source_vector() -> None:
    pdf = render(filtered('<feDropShadow dx="4" dy="4" stdDeviation="3"/>', ' color-interpolation-filters="sRGB"'))
    assert images(pdf) == 1
    assert "0 0 0 rg" not in content(pdf) or "1 0 0 rg" in content(pdf)


def test_css_blur_and_drop_shadow_go_raster() -> None:
    body = '<rect x="20" y="20" width="60" height="40" fill="red" style="filter:blur(2px)"/><rect x="120" y="20" width="40" height="40" fill="red" style="filter:drop-shadow(3px 3px 4px black)"/><g style="filter:blur(2px)"/>'
    pdf = render(svg(body, height=120))
    assert images(pdf) == 2


def test_luminance_blur_goes_raster() -> None:
    pdf = render(filtered('<feColorMatrix type="luminanceToAlpha"/><feGaussianBlur stdDeviation="2"/>', ' color-interpolation-filters="sRGB"'))
    assert images(pdf) == 1


def test_unsupported_chain_goes_raster_as_a_whole() -> None:
    pdf = render(filtered('<feTurbulence baseFrequency="0.05" numOctaves="2"/>'))
    assert images(pdf) == 1


def test_filter_on_the_root_goes_raster() -> None:
    document = filtered('<feGaussianBlur stdDeviation="2"/>', target='<rect x="20" y="20" width="60" height="40" fill="red"/>')
    pdf = render(document.replace("<svg ", '<svg filter="url(#f)" viewBox="0 0 200 120" ', 1))
    assert images(pdf) == 1
    pdf = render(document.replace("<svg ", '<svg style="filter:blur(2px)" ', 1))
    assert images(pdf) == 0


def test_resvg_failure_keeps_the_element(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    class Broken:
        @staticmethod
        def svg_to_bytes(**kwargs: Any) -> bytes:
            raise RuntimeError("panic")

    monkeypatch.setattr(raster, "_RESVG", Broken)
    pdf = render(filtered('<feTurbulence baseFrequency="0.05"/>'))
    assert images(pdf) == 0
    assert near(pixel(pdf, 30, 30), RED)
    assert "resvg failed" in caplog.text
    pdf = render(filtered('<feGaussianBlur stdDeviation="2"/>'))
    assert near(pixel(pdf, 40, 30), RED, 60)


def test_inner_svg_filter_is_left_to_weasyprint() -> None:
    body = '<defs><filter id="f"><feGaussianBlur stdDeviation="2"/></filter></defs><svg x="10" y="10" width="80" height="80" filter="url(#f)"><rect width="40" height="40" fill="red"/></svg>'
    node = type("Node", (), {"get": {"filter": "url(#f)"}.get, "tag": "svg"})()
    fake = type("SVG", (), {"tree": object()})()
    assert filters.plan(fake, node, 16) is None
    render(svg(body))


def test_drop_shadow_of_a_flood(no_resvg: None) -> None:
    pdf = render(
        filtered(
            '<feFlood flood-color="red" x="20" y="20" width="60" height="40" result="f"/><feDropShadow in="f" dx="5" dy="5" stdDeviation="0" flood-color="black"/>',
            ' filterUnits="userSpaceOnUse" x="0" y="0" width="200" height="120"',
        )
    )
    assert near(pixel(pdf, 30, 30), RED)
    assert near(pixel(pdf, 63, 47), (0, 0, 0), 60)


# ---------------- exceptions ----------------


class RecordingStream:
    """A stand-in for the PDF stream: counts state pushes and pops, hands out child streams."""

    def __init__(self) -> None:
        self.depth = 0
        self.id = "x0"

    def push_state(self) -> None:
        self.depth += 1

    def pop_state(self) -> None:
        self.depth -= 1

    def set_alpha_state(self, *_args: Any, **_kwargs: Any) -> RecordingStream:
        return RecordingStream()

    def add_group(self, *_args: Any) -> RecordingStream:
        return RecordingStream()

    def __getattr__(self, _name: str) -> Any:
        # transform, rectangle, clip, end, set_color, fill, set_alpha, draw_x_object
        return lambda *_args, **_kwargs: None


class FakeSvg:
    def __init__(self) -> None:
        self.stream = RecordingStream()
        self.tree = object()


def failing_original(*_args: Any) -> None:
    raise RuntimeError("drawing failed")


@pytest.mark.parametrize("layer", [Layer("alpha", opacity=0.5), Layer("lum"), Layer("source", opacity=0.5)])
@pytest.mark.parametrize("opacity", [1, 0.5])
def test_a_failing_layer_restores_the_stream(no_resvg: None, layer: Layer, opacity: float) -> None:
    fake = FakeSvg()
    stream = fake.stream
    plan = filters.Plan([layer], None)
    with pytest.raises(RuntimeError):
        filters.draw(fake, failing_original, object(), 12, None, plan, opacity)
    # Else the caller pops the state of a mask or group stream, and q and Q of the page drift apart
    assert fake.stream is stream
    assert stream.depth == 0
