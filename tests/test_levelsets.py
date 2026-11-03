"""Level sets of a sampled field: the opacities that stack into its profile, the contours, their simplification."""

from __future__ import annotations

import math

import pytest
from PIL import Image, ImageDraw, ImageFilter

from weasysvg.levelsets import OPACITY_STEPS, _off_line, contours, simplified, thresholds


def stacked(opacities: list[float]) -> float:
    """The opacity of the levels painted one over the other."""
    total = 0.0
    for opacity in opacities:
        total += opacity * (1 - total)
    return total


@pytest.mark.parametrize("opacity", [1.0, 0.4, 0.05, 1e-6])
def test_thresholds_stack_to_the_opacity(opacity: float) -> None:
    steps = thresholds(opacity)
    assert len(steps) == max(1, math.ceil(OPACITY_STEPS * opacity))
    # The levels are the midpoints between the steps, rising
    assert [threshold for threshold, _ in steps] == pytest.approx([(k - 0.5) / len(steps) for k in range(1, len(steps) + 1)])
    # Painted over all the levels below, level k brings the field to opacity * k / n
    for k in range(1, len(steps) + 1):
        assert stacked([alpha for _, alpha in steps[:k]]) == pytest.approx(opacity * k / len(steps))


def blurred_disc() -> Image.Image:
    field = Image.new("L", (200, 200))
    ImageDraw.Draw(field).ellipse((50, 50, 150, 150), fill=255)
    return field.filter(ImageFilter.GaussianBlur(6))


@pytest.mark.parametrize(("level", "radius"), [(0.5, 50), (0.05, 60), (0.95, 40)])
def test_contour_of_a_blurred_disc(level: float, radius: float) -> None:
    rings = contours(blurred_disc(), [level])[level]
    assert len(rings) == 1
    distances = [math.dist(point, (100, 100)) for point in rings[0]]
    # Half a sample on either side, and the edge pixels Pillow draws for the disc
    assert min(distances) == pytest.approx(radius, abs=0.6)
    assert max(distances) == pytest.approx(radius, abs=0.6)


def test_a_ring_has_a_hole() -> None:
    field = Image.new("L", (100, 100))
    draw = ImageDraw.Draw(field)
    draw.ellipse((10, 10, 90, 90), fill=255)
    draw.ellipse((35, 35, 65, 65), fill=0)
    assert len(contours(field, [0.5])[0.5]) == 2


def test_a_flat_field_has_contours_at_its_border_only() -> None:
    assert contours(Image.new("L", (20, 20), 0), [0.5]) == {0.5: []}
    # 128 reaches 0.25 everywhere: one contour around the field; it never reaches 0.75
    traced = contours(Image.new("L", (20, 20), 128), [0.25, 0.75])
    assert len(traced[0.25]) == 1
    assert traced[0.75] == []


def test_a_field_up_to_its_border_closes() -> None:
    # Past the field it is 0: a field full to its edge closes around it, half a sample outside
    rings = contours(Image.new("L", (10, 6), 255), [0.5])[0.5]
    assert len(rings) == 1
    xs, ys = [x for x, _ in rings[0]], [y for _, y in rings[0]]
    assert (min(xs), max(xs), min(ys), max(ys)) == pytest.approx((-0.5, 9.5, -0.5, 5.5))


@pytest.mark.parametrize(("level", "count"), [(0.4, 1), (0.6, 2)])
def test_a_saddle_joins_its_corners_by_their_mean(level: float, count: int) -> None:
    # Two corners at 255 across from each other, two at 0: the mean 127.5 joins them below it, parts them above
    field = Image.new("L", (2, 2))
    field.putpixel((0, 0), 255)
    field.putpixel((1, 1), 255)
    assert len(contours(field, [level])[level]) == count


@pytest.mark.parametrize(("level", "count"), [(0.4, 1), (0.6, 2)])
def test_a_saddle_the_other_way(level: float, count: int) -> None:
    field = Image.new("L", (2, 2))
    field.putpixel((1, 0), 255)
    field.putpixel((0, 1), 255)
    assert len(contours(field, [level])[level]) == count


def test_simplified_keeps_the_corners_of_a_square() -> None:
    side = [(float(x), 0.0) for x in range(10)] + [(10.0, float(y)) for y in range(10)] + [(float(x), 10.0) for x in range(10, 0, -1)] + [(0.0, float(y)) for y in range(10, 0, -1)]
    assert sorted(simplified(side, 0.1)) == [(0.0, 0.0), (0.0, 10.0), (10.0, 0.0), (10.0, 10.0)]


def test_simplified_keeps_a_curve_within_tolerance() -> None:
    ring = [(50 * math.cos(2 * math.pi * k / 400), 50 * math.sin(2 * math.pi * k / 400)) for k in range(400)]
    kept = simplified(ring, 0.05)
    assert 20 < len(kept) < 400
    # Every point of the ring lies within tolerance of the polygon of the kept ones
    edges = list(zip(kept, kept[1:] + kept[:1], strict=True))
    assert max(min(_off_line(point, start, end) for start, end in edges) for point in ring) <= 0.05 + 1e-9


def test_simplified_leaves_a_triangle() -> None:
    triangle = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    assert simplified(triangle, 1.0) == triangle


def test_simplified_with_repeated_points() -> None:
    # A segment of length 0 between kept points
    ring = [(0.0, 0.0), (0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0), (0.0, 0.0)]
    assert len(simplified(ring, 0.1)) >= 4


def test_distance_from_a_segment_of_length_zero() -> None:
    assert _off_line((3.0, 4.0), (0.0, 0.0), (0.0, 0.0)) == 5.0
