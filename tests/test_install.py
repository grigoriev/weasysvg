"""install(): idempotent, additive, and the version check."""

from __future__ import annotations

import warnings
from types import SimpleNamespace

import pytest
import weasyprint
from weasyprint import images as wp_images
from weasyprint import svg as wp_svg
from weasyprint.matrix import Matrix

import weasysvg
from weasysvg import _core, conditional, paint_order, xobject

ALL = {"conditional", "paint", "blend", "text", "fonts", "fetch", "filters", "foreign_object", "markers", "paint_order", "form_xobject"}


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
    assert [name for _, name, _ in _core._TREE_PASSES] == ["conditional", "nested_text", "invalid_rotate", "nested_tails", "trailing_space", "empty_presentation", "arcs", "paint_order", "foreign_object"]
    assert wp_svg.SVG.fill_stroke is paint_order.fill_stroke
    assert wp_images.SVGImage.draw is _core._svgimage_draw
    assert [function for _, function in _core._DRAW_WRAPPERS] == [conditional.svgimage_draw, xobject.draw_as_form]


def test_tree_pass_and_wrapper_are_added_once() -> None:
    passes = list(_core._TREE_PASSES)
    _core.add_tree_pass(99, "conditional", lambda root: None)
    assert passes == _core._TREE_PASSES
    wrappers = list(_core._FETCHER_WRAPPERS)
    _core.add_fetcher_wrapper(wrappers[0])
    assert wrappers == _core._FETCHER_WRAPPERS
    draw_wrappers = list(_core._DRAW_WRAPPERS)
    _core.add_draw_wrapper(99, draw_wrappers[0][1])
    assert draw_wrappers == _core._DRAW_WRAPPERS


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


def test_px_per_unit_without_a_stream_is_one() -> None:
    assert _core.px_per_unit(SimpleNamespace()) == 1.0


def test_px_per_unit_follows_the_groups() -> None:
    page = SimpleNamespace(ctm=Matrix(7.5, 0, 0, 7.5))
    group = SimpleNamespace(ctm=Matrix(2, 0, 0, 2), weasysvg_base=_core.absolute_matrix(page))
    assert _core.px_per_unit(SimpleNamespace(stream=group)) == pytest.approx(20.0)
