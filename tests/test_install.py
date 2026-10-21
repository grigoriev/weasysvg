"""install(): idempotent, additive, and the version check."""

from __future__ import annotations

import math
import warnings
from types import SimpleNamespace
from typing import Any

import pytest
import weasyprint
from helpers import render, svg
from weasyprint import images as wp_images
from weasyprint import svg as wp_svg
from weasyprint.matrix import Matrix

import weasysvg
from weasysvg import _core

ALL = {"conditional", "paint", "blend", "text", "fonts", "fetch", "filters", "foreign_object", "markers"}


def test_install_returns_every_feature() -> None:
    assert weasysvg.install() == frozenset(ALL)
    assert weasysvg.installed() == frozenset(ALL)


def test_second_install_changes_nothing() -> None:
    draw_node, init = wp_svg.SVG.draw_node, wp_images.SVGImage.__init__
    passes = list(_core._TREE_PASSES)
    assert weasysvg.install(filters=False, text=False) == frozenset(ALL)
    assert wp_svg.SVG.draw_node is draw_node
    assert wp_images.SVGImage.__init__ is init
    assert passes == _core._TREE_PASSES


def test_hooks_are_in_place() -> None:
    assert wp_svg.SVG.draw_node is _core._draw_node
    assert wp_images.SVGImage.__init__ is _core._svgimage_init
    assert _core.original_draw_node() is _core._ORIGINAL_DRAW_NODE
    assert [name for _, name, _ in _core._TREE_PASSES] == ["conditional", "nested_text", "invalid_rotate", "empty_presentation", "foreign_object"]


def test_tree_pass_and_wrapper_are_added_once() -> None:
    passes = list(_core._TREE_PASSES)
    _core.add_tree_pass(99, "conditional", lambda root: None)
    assert passes == _core._TREE_PASSES
    wrappers = list(_core._FETCHER_WRAPPERS)
    _core.add_fetcher_wrapper(wrappers[0])
    assert wrappers == _core._FETCHER_WRAPPERS


def test_version_check_warns_on_other_major(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(weasyprint, "__version__", "71.0")
    with pytest.warns(RuntimeWarning, match="targets WeasyPrint 70.x, found 71.0"):
        weasysvg.install()
    monkeypatch.delattr(weasyprint, "__version__")
    with pytest.warns(RuntimeWarning, match="found unknown"):
        weasysvg.install()


def test_version_check_is_quiet_on_70() -> None:
    assert weasyprint.__version__.startswith("70.")
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        weasysvg.install()


def test_resolve_families_is_exported() -> None:
    assert weasysvg.resolve_families is weasysvg.fonts.resolve_families
    assert weasysvg.SUPPORTED_MAJOR == 70


def test_svgimage_hook_without_fetcher(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[object] = []
    monkeypatch.setattr(_core, "_ORIGINAL_SVGIMAGE_INIT", lambda self, tree, base_url, url_fetcher, context: seen.append(url_fetcher))
    monkeypatch.setattr(_core, "_TREE_PASSES", [])
    monkeypatch.setattr(_core, "_IMAGE_HOOKS", [])
    _core._svgimage_init(object(), object(), None, None, None)
    assert seen == [None]


def test_an_image_hook_is_added_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_core, "_IMAGE_HOOKS", [])

    def hook(_image: object) -> None:
        pass

    _core.add_image_hook(hook)
    _core.add_image_hook(hook)
    hooks = _core._IMAGE_HOOKS
    assert hooks == [hook]


def test_a_later_install_turns_on_fonts_for_svg_text(monkeypatch: pytest.MonkeyPatch) -> None:
    # A fresh process: text installed without fonts first, fonts asked for later
    monkeypatch.setattr(weasysvg, "_INSTALLED", set(ALL - {"text", "fonts"}))
    monkeypatch.setitem(weasysvg.text.FEATURES, "fonts", True)
    weasysvg.install(fonts=False)
    assert weasysvg.text.FEATURES["fonts"] is False
    assert "fonts" in weasysvg.install(fonts=True)
    assert weasysvg.text.FEATURES["fonts"] is True


def test_a_later_install_never_turns_fonts_off(monkeypatch: pytest.MonkeyPatch) -> None:
    # fonts installed first, text later with fonts=False: the installed fonts feature stays on
    monkeypatch.setattr(weasysvg, "_INSTALLED", set(ALL - {"text"}))
    monkeypatch.setitem(weasysvg.text.FEATURES, "fonts", True)
    assert "fonts" in weasysvg.install(fonts=False)
    assert weasysvg.text.FEATURES["fonts"] is True


@pytest.mark.parametrize(
    ("body", "extra", "expected"),
    [
        ('<text x="10" y="50" text-decoration="underline">A</text>', "", 1.0),
        ('<text x="1" y="5" font-size="3" text-decoration="underline">A</text>', ' viewBox="0 0 20 10"', 10.0),
        # An opacity group starts with an identity matrix: the scale outside it still counts
        ('<g opacity="0.5" transform="scale(2)"><text x="1" y="2" font-size="1" text-decoration="underline">A</text></g>', ' viewBox="0 0 20 10"', 20.0),
        # A pattern tile starts with an identity matrix too: its Matrix and the scale outside count
        (
            '<defs><pattern id="p" width="10" height="5" patternUnits="userSpaceOnUse"><text x="1" y="3" font-size="3" text-decoration="underline">A</text></pattern></defs><rect width="10" height="5" fill="url(#p)"/>',
            ' viewBox="0 0 20 10"',
            10.0,
        ),
    ],
)
def test_text_scale_counts_every_transform(monkeypatch: pytest.MonkeyPatch, body: str, extra: str, expected: float) -> None:
    seen: list[float] = []
    original = _core.text_scale

    def recording(image: Any) -> float:
        seen.append(original(image))
        return seen[-1]

    monkeypatch.setattr(_core, "text_scale", recording)
    render(svg(body, extra=extra))
    assert seen
    assert all(value == pytest.approx(expected) for value in seen)


def test_px_per_unit_without_a_stream_is_one() -> None:
    assert _core.px_per_unit(SimpleNamespace()) == 1.0


def test_text_scale_is_the_mean_square_of_the_axes() -> None:
    # scale(1, 0.25) on a page in pt: sqrt((1 + 0.0625) / 2) CSS px per unit
    stream = SimpleNamespace(ctm=Matrix(0.75, 0, 0, 0.1875))
    assert _core.text_scale(SimpleNamespace(stream=stream)) == pytest.approx(math.sqrt((1 + 0.0625) / 2))
    assert _core.text_scale(SimpleNamespace()) == 1.0


def test_px_per_unit_follows_the_groups() -> None:
    page = SimpleNamespace(ctm=Matrix(7.5, 0, 0, 7.5))
    group = SimpleNamespace(ctm=Matrix(2, 0, 0, 2), weasysvg_base=_core.absolute_matrix(page))
    assert _core.px_per_unit(SimpleNamespace(stream=group)) == pytest.approx(20.0)
