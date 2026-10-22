"""Each SVG image drawn as one Form XObject, its BBox the viewport.

Touches: a wrapper of ``images.SVGImage.draw``, and ``draw.draw_replacedbox``, which notes an inline
<svg> whose overflow is visible. WeasyPrint draws the operators of an SVG straight into the stream of the
page. A reader of the PDF then cannot tell where a diagram starts or how large it is: PDFBox and PyMuPDF
find a Form XObject, its box and the matrix that places it.

The form is no transparency group, so it composites as the inline drawing did. Its BBox clips, as
Chromium clips an image at its box: an <img>, a background, a list marker. An inline <svg> with
``overflow: visible`` draws past its viewport in Chromium, so its box grows to let the overflow through.
In a tagged PDF the Figure of the image marks the Do: the form marks nothing of its own.

The same image at the same size, painted from the same resources, is one form painted again.
"""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
from typing import Any

from weasyprint import draw as wp_draw

from . import _core

_ORIGINAL_DRAW_REPLACEDBOX = wp_draw.draw_replacedbox
# Whether the image being drawn is an inline <svg> with visible overflow
_UNCLIPPED: ContextVar[bool] = ContextVar("weasysvg_unclipped", default=False)


def draw_replacedbox(stream: Any, box: Any) -> None:
    """draw_replacedbox of WeasyPrint, noting whether the box is an inline <svg> that lets its overflow show."""
    tag = str(getattr(box, "element_tag", "") or "")
    unclipped = tag.rsplit("}", 1)[-1] == "svg" and box.style["overflow"] == "visible"
    token = _UNCLIPPED.set(unclipped)
    try:
        _ORIGINAL_DRAW_REPLACEDBOX(stream, box)
    finally:
        _UNCLIPPED.reset(token)


def _box(width: float, height: float, unclipped: bool) -> tuple[float, float, float, float]:
    """The BBox of the form: the viewport, or around it as far as a group reaches where nothing clips."""
    if not unclipped:
        return 0, 0, width, height
    margin = max(width, height, _core.MIN_GROUP_EXTENT)
    return -margin, -margin, width + 2 * margin, height + 2 * margin


def _scale(stream: Any) -> float:
    """The scale of stream on the page: weasysvg sizes blur steps and noise by it."""
    return round(abs(float(_core.absolute_matrix(stream).determinant)), 9)


def _new_form(stream: Any, box: tuple[float, float, float, float]) -> Any:
    # A group of WeasyPrint is a Form XObject with its own resources; without its group dictionary it
    # paints as if its content stood in the stream
    form = _core._ORIGINAL_ADD_GROUP(stream, *box)
    del form.extra["Group"]
    # The marked content of the image encloses the Do: content marked inside would nest in it, and the
    # tags of the boxes of a foreignObject belong to no box of the page
    form._tags = None
    form.weasysvg_base = _core.absolute_matrix(stream)
    return form


def draw_as_form(image: Any, stream: Any, width: float, height: float, _style: Any, draw: Callable[[Any], None]) -> None:
    """Draw image into a Form XObject the size of its viewport, then paint the form in stream."""
    unclipped = _UNCLIPPED.get()
    # An image drawn inside this one, an <image> or an <img> in a foreignObject, has a box of its own
    token = _UNCLIPPED.set(False)
    try:
        xobjects = stream._resources["XObject"]
        key = (id(xobjects), width, height, unclipped, _scale(stream))
        forms: dict[tuple[Any, ...], Any] = image.__dict__.setdefault("weasysvg_forms", {})
        form = forms.get(key)
        # A key of a resources dictionary gone may come back with another one
        if form is None or xobjects.get(form.id) is not form:
            form = forms[key] = _new_form(stream, _box(width, height, unclipped))
            draw(form)
        stream.draw_x_object(form.id)
    finally:
        _UNCLIPPED.reset(token)


def install() -> None:
    _core.add_draw_wrapper(20, draw_as_form)
    # draw_inline_level and draw_block_level call it by its global name
    wp_draw.draw_replacedbox = draw_replacedbox
