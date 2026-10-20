"""The WeasyPrint internals weasysvg hooks have not changed since upstream/hooks.json was written."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("hooks", ROOT / "tools" / "upstream" / "hooks.py")
assert _spec is not None
assert _spec.loader is not None
hooks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hooks)


def test_every_hook_is_found() -> None:
    assert [target for target in hooks.HOOKS if hooks.fingerprint(target) == "missing"] == []


def test_hooks_match_the_snapshot() -> None:
    found = hooks.changes(json.loads(hooks.SNAPSHOT.read_text()))
    assert found == [], "WeasyPrint changed code weasysvg hooks:\n" + "\n".join(found)


def test_font_family_has_no_computer() -> None:
    # fonts.py registers one; a computer of WeasyPrint itself would run first, through _ORIGINAL_FAMILY_COMPUTER
    from weasyprint.css.computed_values import COMPUTER_FUNCTIONS

    assert "font_family" not in COMPUTER_FUNCTIONS, "WeasyPrint computes font_family now: review fonts._computed_families"


def _fingerprint_of(tmp_path: Path, monkeypatch: Any, code: str) -> str:
    package = tmp_path / f"probe_{abs(hash(code))}"
    package.mkdir()
    (package / "__init__.py").write_text(code)
    monkeypatch.syspath_prepend(str(tmp_path))
    return str(hooks.fingerprint(f"{package.name}:Node.tag"))


def test_a_changed_decorator_changes_the_fingerprint(tmp_path: Path, monkeypatch: Any) -> None:
    # @property read again on each access; @cached_property keeps the first tag, and the retagging breaks
    body = "class Node:\n    @{}\n    def tag(self):\n        return self._tag\n"
    assert _fingerprint_of(tmp_path, monkeypatch, body.format("property")) != _fingerprint_of(tmp_path, monkeypatch, "import functools\n" + body.format("functools.cached_property"))


def test_a_setter_counts_in_the_fingerprint(tmp_path: Path, monkeypatch: Any) -> None:
    getter = "class Node:\n    @property\n    def tag(self):\n        return self._tag\n"
    setter = getter + "    @tag.setter\n    def tag(self, value):\n        self._tag = value\n"
    assert _fingerprint_of(tmp_path, monkeypatch, getter) != _fingerprint_of(tmp_path, monkeypatch, setter)
