"""Font family resolution as Chromium on Linux does it. The test image has DejaVu, Liberation and Noto Color Emoji."""

from __future__ import annotations

import pytest
from helpers import XHTML_NS, render, svg, text_of
from weasyprint.text.ffi import ffi, fontconfig
from weasyprint.text.fonts import FontConfiguration

from weasysvg import fonts
from weasysvg.fonts import resolve_families


@pytest.mark.parametrize(
    ("families", "expected"),
    [
        ("Arial", "Liberation Sans"),
        ("sans-serif", "Liberation Sans"),
        ("serif", "Liberation Serif"),
        ("'Times New Roman', serif", "Liberation Serif"),
        ('"Courier New"', "Liberation Mono"),
        ("Courier", "Liberation Mono"),
        ("Times", "Liberation Serif"),
        ("Helvetica", "Liberation Sans"),
        ("NoSuchFont, Arial", "Liberation Sans"),
        ("NoSuchFont", "Liberation Serif"),
        ("", "Liberation Serif"),
        ("DejaVu Sans Mono", "DejaVu Sans Mono"),
        ("monospace", "DejaVu Sans Mono"),
        ("system-ui", "DejaVu Sans"),
    ],
)
def test_resolve_families(families: str, expected: str) -> None:
    assert resolve_families(families) == expected


def test_resolve_a_list_with_a_document_configuration() -> None:
    config = FontConfiguration()
    assert resolve_families(["NoSuchFont", "Arial"], config) == "Liberation Sans"
    # The answers are cached per configuration
    assert config._svg_ext_family_cache["arial"] == "Liberation Sans"
    assert resolve_families(["Arial"], config) == "Liberation Sans"


def test_nothing_found_falls_back_to_serif(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fonts, "_match", lambda family, config: None)
    assert resolve_families("Arial", FontConfiguration()) == "serif"


def test_equivalents() -> None:
    assert fonts._acceptable("Arial", "Liberation Sans")
    assert fonts._acceptable("Calibri", "Carlito")
    assert not fonts._acceptable("Arial", "DejaVu Sans")


def test_computed_families_outside_a_foreign_object() -> None:
    assert fonts._computed_families(type("Style", (), {"font_config": None})(), "font_family", ("Arial",)) == ("Arial",)


def test_foreign_object_text_uses_the_resolved_family() -> None:
    body = f'<foreignObject width="200" height="60"><div xmlns="{XHTML_NS}" style="font-family:NoSuchFont, Arial">Sans</div></foreignObject>'
    pdf = render(svg(body))
    assert "Sans" in text_of(pdf)
    assert b"+Liberation-Sans" in pdf


def test_svg_text_uses_the_resolved_family() -> None:
    pdf = render(svg('<text x="10" y="50" font-family="Helvetica">Sans</text><text x="10" y="80">Serif</text>'))
    assert b"+Liberation-Sans" in pdf
    assert b"+Liberation-Serif" in pdf


def test_no_fontconfig_match(monkeypatch: pytest.MonkeyPatch) -> None:
    class NoMatch:
        def __getattr__(self, name: str) -> object:
            return getattr(real, name)

        @staticmethod
        def FcFontMatch(*args: object) -> object:  # noqa: N802  fontconfig's name
            return ffi.NULL

    real = fontconfig
    monkeypatch.setattr(fonts, "fontconfig", NoMatch())
    assert fonts._match("Arial", ffi.NULL) is None
