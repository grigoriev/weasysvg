"""install(): idempotent, additive, and the version check."""

from __future__ import annotations

import warnings

import pytest
import weasyprint
from weasyprint import images as wp_images
from weasyprint import svg as wp_svg

import weasysvg
from weasysvg import _core

ALL = {"conditional", "paint", "blend", "text", "fonts", "fetch", "filters", "foreign_object"}


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
    assert [name for _, name, _ in _core._TREE_PASSES] == ["conditional", "nested_text", "empty_presentation", "foreign_object"]


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
    _core._svgimage_init(object(), object(), None, None, None)
    assert seen == [None]


def test_a_later_install_turns_on_fonts_for_svg_text(monkeypatch: pytest.MonkeyPatch) -> None:
    # A fresh process: text installed without fonts first, fonts asked for later
    monkeypatch.setattr(weasysvg, "_INSTALLED", set(ALL - {"text", "fonts"}))
    monkeypatch.setitem(weasysvg.text.FEATURES, "fonts", True)
    weasysvg.install(fonts=False)
    assert weasysvg.text.FEATURES["fonts"] is False
    assert "fonts" in weasysvg.install(fonts=True)
    assert weasysvg.text.FEATURES["fonts"] is True
