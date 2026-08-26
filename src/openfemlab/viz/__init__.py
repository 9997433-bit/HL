"""Lightweight plotting helpers.

Matplotlib is optional and is imported only when a plotting function is
called. Install the ``[plot]`` extra to use this package.
"""

from .plotting import plot_mac_matrix, plot_mode_shape, require_matplotlib

__all__ = ["plot_mac_matrix", "plot_mode_shape", "require_matplotlib"]
