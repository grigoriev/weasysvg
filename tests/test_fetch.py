"""The per-SVG cache in front of the URL fetcher."""

from __future__ import annotations

from typing import Any

import pytest
from weasyprint.urls import URLFetcherResponse

from weasysvg.fetch import CachingFetcher, _wrap


class Inner:
    timeout = 7

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, url: str) -> Any:
        self.calls.append(url)
        if "dead" in url:
            raise OSError("unreachable")
        return URLFetcherResponse(url, b"body:" + url.encode(), {"Content-Type": "text/css"}, 200)


def test_fetches_each_url_once() -> None:
    inner = Inner()
    fetcher = CachingFetcher(inner)
    first = fetcher("https://example.com/a.css")
    second = fetcher("https://example.com/a.css")
    assert inner.calls == ["https://example.com/a.css"]
    assert first.read() == second.read() == b"body:https://example.com/a.css"
    assert second.url == "https://example.com/a.css"
    assert second.status == 200


def test_keeps_a_failure() -> None:
    inner = Inner()
    fetcher = CachingFetcher(inner)
    for _ in range(3):
        with pytest.raises(OSError, match="unreachable"):
            fetcher("https://dead.example.com/font.woff")
    assert len(inner.calls) == 1


def test_delegates_attributes() -> None:
    assert CachingFetcher(Inner()).timeout == 7


def test_wraps_once() -> None:
    inner = Inner()
    wrapped = _wrap(inner)
    assert isinstance(wrapped, CachingFetcher)
    assert _wrap(wrapped) is wrapped
