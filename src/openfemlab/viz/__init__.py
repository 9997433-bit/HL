"""Lightweight plotting helpers.

Matplotlib is optional and is imported only when a plotting function is
called. Install the ``[plot]`` extra to use this package.

:func:`~openfemlab.viz.plotting.element_edges` carries no such dependency: it
is the wireframe topology the plots and the browser viewer share.
"""

from .plotting import (
    element_edges,
    plot_frf_overlay,
    plot_mac_matrix,
    plot_mode_shape,
    plot_modes_side_by_side,
    plot_stabilization_diagram,
    require_matplotlib,
)

__all__ = [
    "element_edges",
    "plot_frf_overlay",
    "plot_mac_matrix",
    "plot_mode_shape",
    "plot_modes_side_by_side",
    "plot_stabilization_diagram",
    "require_matplotlib",
]
