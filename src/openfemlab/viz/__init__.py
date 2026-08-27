"""Lightweight plotting helpers.

Matplotlib is optional and is imported only when a plotting function is
called. Install the ``[plot]`` extra to use this package.
"""

from .plotting import (
    plot_frf_overlay,
    plot_mac_matrix,
    plot_mode_shape,
    plot_stabilization_diagram,
    require_matplotlib,
)

__all__ = [
    "plot_frf_overlay",
    "plot_mac_matrix",
    "plot_mode_shape",
    "plot_stabilization_diagram",
    "require_matplotlib",
]
