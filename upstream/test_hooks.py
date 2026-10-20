"""The WeasyPrint internals weasysvg hooks have not changed since upstream/hooks.json was written."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

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
