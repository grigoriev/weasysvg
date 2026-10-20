"""A per-SVG cache in front of the URL fetcher.

Touches: the fetcher that ``images.SVGImage.__init__`` hands to the SVG. A foreignObject is laid
out as a document of its own, which would load the stylesheets and fonts of the SVG again.
"""

from __future__ import annotations

from typing import Any

from weasyprint.urls import URLFetcherResponse

from . import _core


class CachingFetcher:
    """Fetch each URL once per SVG. A failure is kept too: a dead host would time out once per object."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._cache: dict[str, tuple[Any, ...]] = {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    def __call__(self, url: str) -> Any:
        if url not in self._cache:
            try:
                response = self._inner(url)
            except Exception as e:  # noqa: BLE001
                self._cache[url] = (e,)
            else:
                try:
                    self._cache[url] = (response.url, response.read(), response.headers, response.status)
                finally:
                    response.close()
        if len(self._cache[url]) == 1:
            raise self._cache[url][0]
        response_url, body, headers, status = self._cache[url]
        return URLFetcherResponse(response_url, body, headers, status)


def _wrap(fetcher: object) -> object:
    return fetcher if isinstance(fetcher, CachingFetcher) else CachingFetcher(fetcher)


def install() -> None:
    _core.add_fetcher_wrapper(_wrap)
