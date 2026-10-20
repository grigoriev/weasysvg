"""Probes run against WeasyPrint alone: weasysvg must not be imported in this process."""

from __future__ import annotations

import sys

import pytest


@pytest.fixture(autouse=True)
def _native() -> None:
    assert "weasysvg" not in sys.modules, "run the probes in a process of their own: pytest upstream"
