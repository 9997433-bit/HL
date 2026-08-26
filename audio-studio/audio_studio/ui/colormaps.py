"""Colour lookup tables for spectral displays.

Each map is stored as a handful of RGB control points and expanded on demand
into a 256-entry ``uint8`` LUT, so adding a palette costs a line rather than a
kilobyte and the renderer only ever does a single fancy-index to colourise a
whole frame.

The perceptual maps (``viridis``, ``magma``, ``inferno``) are control-point
approximations of the matplotlib originals — close enough to keep the
monotonic-lightness property that makes level differences readable, without
taking a matplotlib dependency into the GUI.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

import numpy as np

__all__ = ["COLORMAP_NAMES", "DEFAULT_COLORMAP", "get_colormap", "colorize", "make_gradient"]

ControlPoints = Sequence[Tuple[float, Tuple[int, int, int]]]

_CONTROL_POINTS: Dict[str, ControlPoints] = {
    # Audition's spectral display: black through blue and magenta into a hot
    # orange/white top end. The default because it is what users comparing
    # against Audition expect to see.
    "audition": (
        (0.00, (0, 0, 0)),
        (0.15, (20, 12, 72)),
        (0.30, (70, 12, 122)),
        (0.45, (140, 22, 112)),
        (0.60, (200, 52, 62)),
        (0.75, (240, 122, 20)),
        (0.90, (250, 212, 62)),
        (1.00, (255, 255, 255)),
    ),
    "viridis": (
        (0.000, (68, 1, 84)),
        (0.125, (72, 40, 120)),
        (0.250, (62, 74, 137)),
        (0.375, (49, 104, 142)),
        (0.500, (38, 130, 142)),
        (0.625, (31, 158, 137)),
        (0.750, (53, 183, 121)),
        (0.875, (109, 205, 89)),
        (1.000, (253, 231, 37)),
    ),
    "magma": (
        (0.000, (0, 0, 4)),
        (0.125, (28, 16, 68)),
        (0.250, (79, 18, 123)),
        (0.375, (129, 37, 129)),
        (0.500, (181, 54, 122)),
        (0.625, (229, 80, 100)),
        (0.750, (251, 135, 97)),
        (0.875, (254, 194, 135)),
        (1.000, (252, 253, 191)),
    ),
    "inferno": (
        (0.000, (0, 0, 4)),
        (0.125, (31, 12, 72)),
        (0.250, (85, 15, 109)),
        (0.375, (136, 34, 106)),
        (0.500, (186, 54, 85)),
        (0.625, (227, 89, 51)),
        (0.750, (249, 142, 9)),
        (0.875, (249, 201, 50)),
        (1.000, (252, 255, 164)),
    ),
    "grayscale": (
        (0.0, (0, 0, 0)),
        (1.0, (255, 255, 255)),
    ),
    # Classic rainbow. Poor perceptual uniformity, but still the fastest way to
    # spot a narrow spectral line, so it stays on the menu.
    "jet": (
        (0.000, (0, 0, 131)),
        (0.125, (0, 60, 170)),
        (0.375, (5, 255, 255)),
        (0.625, (255, 255, 0)),
        (0.875, (250, 0, 0)),
        (1.000, (128, 0, 0)),
    ),
    # High-contrast on white, for print and light-theme UIs.
    "ice": (
        (0.0, (255, 255, 255)),
        (0.4, (120, 190, 235)),
        (0.7, (30, 80, 180)),
        (1.0, (10, 10, 60)),
    ),
}

#: Palette used when none is specified.
DEFAULT_COLORMAP = "audition"

#: Every available palette name, in menu order.
COLORMAP_NAMES: List[str] = list(_CONTROL_POINTS)

_LUT_CACHE: Dict[Tuple[str, int], np.ndarray] = {}


def make_gradient(control_points: ControlPoints, size: int = 256) -> np.ndarray:
    """Expand ``control_points`` into an ``(size, 3)`` ``uint8`` LUT."""
    positions = np.array([p for p, _ in control_points], dtype=np.float64)
    colors = np.array([c for _, c in control_points], dtype=np.float64)
    x = np.linspace(0.0, 1.0, int(size))
    channels = [np.interp(x, positions, colors[:, i]) for i in range(3)]
    return np.clip(np.stack(channels, axis=1), 0, 255).astype(np.uint8)


def get_colormap(name: str = DEFAULT_COLORMAP, size: int = 256) -> np.ndarray:
    """Return a cached ``(size, 3)`` ``uint8`` LUT for ``name``.

    Raises
    ------
    KeyError
        If ``name`` is not a known palette. The message lists the valid names,
        because this is usually reached from a config file typo.
    """
    key = str(name).strip().lower()
    if key not in _CONTROL_POINTS:
        raise KeyError(f"unknown colormap {name!r}; available: {', '.join(COLORMAP_NAMES)}")
    cache_key = (key, int(size))
    lut = _LUT_CACHE.get(cache_key)
    if lut is None:
        lut = make_gradient(_CONTROL_POINTS[key], size)
        lut.flags.writeable = False
        _LUT_CACHE[cache_key] = lut
    return lut


def colorize(
    values: np.ndarray,
    v_min: float,
    v_max: float,
    colormap: str = DEFAULT_COLORMAP,
) -> np.ndarray:
    """Map ``values`` onto RGB via ``colormap``.

    Values are clipped to ``[v_min, v_max]`` and quantised to the LUT size, so
    the cost is one comparison and one gather per pixel regardless of how many
    colours the palette defines.

    Returns
    -------
    numpy.ndarray
        ``values.shape + (3,)`` of ``uint8``, C-contiguous and therefore safe
        to wrap in a ``QImage`` without a copy.
    """
    lut = get_colormap(colormap)
    span = float(v_max) - float(v_min)
    if span <= 0.0:
        span = 1.0
    normalized = (np.asarray(values, dtype=np.float32) - float(v_min)) / span
    indices = np.clip(normalized * (lut.shape[0] - 1), 0, lut.shape[0] - 1).astype(np.int32)
    return np.ascontiguousarray(lut[indices])
