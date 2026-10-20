"""feTurbulence: Perlin noise, as the reference code of the SVG filter specification computes it.

Noise is raster by nature: filters.py draws it as an image over the primitive subregion. The image is
computed here in pure Python and encoded by Pillow, which WeasyPrint already needs; no vector content is
rasterized. Values come out in the space of color-interpolation-filters, linearRGB by default, and are
turned into sRGB for the image, as Chromium does.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from PIL import Image

B_SIZE = 0x100
BM = 0xFF
PERLIN_N = 0x1000
RAND_M = 2147483647
RAND_A = 16807
RAND_Q = 127773  # RAND_M / RAND_A
RAND_R = 2836  # RAND_M % RAND_A
# The most pixels one image may hold: pure Python computes each one
MAX_PIXELS = 65_536
# Octaves past this add less than one 8-bit step
MAX_OCTAVES = 10


def _setup_seed(seed: int) -> int:
    if seed <= 0:
        # The remainder of C truncates toward zero: for a negative seed it is -(|seed| % m)
        seed = (-seed) % (RAND_M - 1) + 1
    return min(seed, RAND_M - 1)


def _random(seed: int) -> int:
    result = RAND_A * (seed % RAND_Q) - RAND_R * (seed // RAND_Q)
    return result + RAND_M if result <= 0 else result


@lru_cache(maxsize=16)
def lattice(seed: int) -> tuple[tuple[int, ...], tuple[tuple[tuple[float, float], ...], ...]]:
    """The lattice selector and the gradients of the four channels, for a seed."""
    seed = _setup_seed(seed)
    selector = list(range(B_SIZE))
    gradients: list[list[tuple[float, float]]] = []
    for _ in range(4):
        channel = []
        for _ in range(B_SIZE):
            vector = []
            for _ in range(2):
                seed = _random(seed)
                vector.append(((seed % (B_SIZE + B_SIZE)) - B_SIZE) / B_SIZE)
            length = math.hypot(*vector) or 1.0
            channel.append((vector[0] / length, vector[1] / length))
        gradients.append(channel)
    for i in range(B_SIZE - 1, 0, -1):
        seed = _random(seed)
        j = seed % B_SIZE
        selector[i], selector[j] = selector[j], selector[i]
    selector += selector[: B_SIZE + 2]
    full = tuple(tuple(channel + channel[: B_SIZE + 2]) for channel in gradients)
    return tuple(selector), full


@dataclass
class _Stitch:
    width: int
    height: int
    wrap_x: int
    wrap_y: int


@dataclass(frozen=True)
class Turbulence:
    """The attributes of one feTurbulence, in user units."""

    base_x: float
    base_y: float
    octaves: int
    seed: int
    fractal: bool
    stitch: bool


def _stitched_frequency(frequency: float, size: float) -> float:
    if not frequency or not size:
        return frequency
    low, high = math.floor(size * frequency) / size, math.ceil(size * frequency) / size
    if not low:
        return high
    return low if frequency / low < high / frequency else high


def _noise(point: tuple[float, float], selector: tuple[int, ...], gradients: tuple[tuple[tuple[float, float], ...], ...], stitch: _Stitch | None) -> tuple[float, float, float, float]:
    """noise2 of the specification, for the four channels at once: they share the lattice."""
    t = point[0] + PERLIN_N
    bx0 = int(t)
    rx0 = t - bx0
    t = point[1] + PERLIN_N
    by0 = int(t)
    ry0 = t - by0
    bx1, by1 = bx0 + 1, by0 + 1
    rx1, ry1 = rx0 - 1.0, ry0 - 1.0
    if stitch is not None:
        # Wrap before the mask, as Chromium and Firefox do: the reference code masks first, so its
        # comparison with the wrap point never holds
        bx0, bx1 = (value - stitch.width if value >= stitch.wrap_x else value for value in (bx0, bx1))
        by0, by1 = (value - stitch.height if value >= stitch.wrap_y else value for value in (by0, by1))
    bx0, bx1, by0, by1 = bx0 & BM, bx1 & BM, by0 & BM, by1 & BM
    i, j = selector[bx0], selector[bx1]
    b00, b10, b01, b11 = selector[i + by0], selector[j + by0], selector[i + by1], selector[j + by1]
    sx, sy = rx0 * rx0 * (3.0 - 2.0 * rx0), ry0 * ry0 * (3.0 - 2.0 * ry0)
    out = []
    for channel in gradients:
        q = channel[b00]
        u = rx0 * q[0] + ry0 * q[1]
        q = channel[b10]
        v = rx1 * q[0] + ry0 * q[1]
        a = u + sx * (v - u)
        q = channel[b01]
        u = rx0 * q[0] + ry1 * q[1]
        q = channel[b11]
        v = rx1 * q[0] + ry1 * q[1]
        b = u + sx * (v - u)
        out.append(a + sy * (b - a))
    return out[0], out[1], out[2], out[3]


def value(spec: Turbulence, point: tuple[float, float], tile: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """The four channels at a point, 0 to 1, in the space of color-interpolation-filters."""
    selector, gradients = lattice(spec.seed)
    base_x, base_y = spec.base_x, spec.base_y
    stitch = None
    if spec.stitch:
        tile_x, tile_y, tile_width, tile_height = tile
        base_x, base_y = _stitched_frequency(base_x, tile_width), _stitched_frequency(base_y, tile_height)
        width, height = int(tile_width * base_x + 0.5), int(tile_height * base_y + 0.5)
        stitch = _Stitch(width, height, int(tile_x * base_x + PERLIN_N + width), int(tile_y * base_y + PERLIN_N + height))
    sums = [0.0, 0.0, 0.0, 0.0]
    vector = (point[0] * base_x, point[1] * base_y)
    ratio = 1.0
    for _ in range(spec.octaves):
        noise = _noise(vector, selector, gradients, stitch)
        for k in range(4):
            sums[k] += (noise[k] if spec.fractal else abs(noise[k])) / ratio
        vector, ratio = (vector[0] * 2, vector[1] * 2), ratio * 2
        if stitch is not None:
            stitch = _Stitch(stitch.width * 2, stitch.height * 2, 2 * stitch.wrap_x - PERLIN_N, 2 * stitch.wrap_y - PERLIN_N)
    if spec.fractal:
        sums = [(total + 1) / 2 for total in sums]
    r, g, b, a = (min(max(total, 0.0), 1.0) for total in sums)
    return r, g, b, a


def _to_srgb(component: float) -> float:
    return component * 12.92 if component <= 0.0031308 else 1.055 * component ** (1 / 2.4) - 0.055


@lru_cache(maxsize=8)
def image(spec: Turbulence, region: tuple[float, float, float, float], scale: float, linear: bool) -> Image.Image:
    """The noise over region, at scale pixels per user unit, sampled at pixel centers, as straight RGBA."""
    x, y, width, height = region
    scale = min(scale, math.sqrt(MAX_PIXELS / max(width * height, 1e-9)))
    # A thin region gets one pixel across: the cap must hold for the other side alone
    columns = max(1, min(round(width * scale), MAX_PIXELS))
    rows = max(1, min(round(height * scale), MAX_PIXELS // columns))
    step_x, step_y = width / columns, height / rows
    pixels = []
    for row in range(rows):
        py = y + (row + 0.5) * step_y
        for column in range(columns):
            r, g, b, a = value(spec, (x + (column + 0.5) * step_x, py), region)
            if linear:
                r, g, b = _to_srgb(r), _to_srgb(g), _to_srgb(b)
            pixels.append((round(r * 255), round(g * 255), round(b * 255), round(a * 255)))
    out = Image.new("RGBA", (columns, rows))
    out.putdata(pixels)
    return out
