"""Matplotlib-backed mode-shape and correlation plots."""

from __future__ import annotations

from collections.abc import Hashable, Sequence
from importlib import import_module
from types import ModuleType
from typing import Any

import numpy as np

from openfemlab.exceptions import MissingDependencyError

__all__ = ["plot_mac_matrix", "plot_mode_shape", "require_matplotlib"]

_MATPLOTLIB_EXTRA = "openfemlab[plot]"


def require_matplotlib() -> ModuleType:
    """Import and return :mod:`matplotlib.pyplot`, or raise a typed install hint."""

    try:
        return import_module("matplotlib.pyplot")
    except ImportError as exc:
        raise MissingDependencyError(
            "matplotlib is required for plotting; install it with "
            f'pip install "{_MATPLOTLIB_EXTRA}"'
        ) from exc


def plot_mac_matrix(
    matrix: Any,
    *,
    ax: Any | None = None,
    row_labels: Sequence[object] | None = None,
    column_labels: Sequence[object] | None = None,
    cmap: str = "viridis",
    annotate: bool = False,
    colorbar: bool = True,
    title: str | None = "Modal Assurance Criterion (MAC)",
) -> Any:
    """Plot a Modal Assurance Criterion matrix as a heatmap.

    Parameters
    ----------
    matrix:
        Two-dimensional MAC values. The color scale is fixed to ``[0, 1]``.
    ax:
        Existing Matplotlib axes. A new figure and axes are made when omitted.
    row_labels, column_labels:
        Optional labels for the two mode sets. One-based mode numbers are used
        by default.
    annotate:
        Write each MAC value into its heatmap cell.
    colorbar:
        Add a colorbar to the axes' figure.

    Returns
    -------
    matplotlib.axes.Axes
        The axes containing the heatmap.
    """

    values = _as_mac_matrix(matrix)
    rows = _labels(row_labels, values.shape[0], "row_labels")
    columns = _labels(column_labels, values.shape[1], "column_labels")

    pyplot = require_matplotlib()
    if ax is None:
        _, ax = pyplot.subplots()

    image = ax.imshow(values, cmap=cmap, vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_xticks(np.arange(values.shape[1]), labels=columns)
    ax.set_yticks(np.arange(values.shape[0]), labels=rows)
    ax.set_xlabel("Mode set B")
    ax.set_ylabel("Mode set A")
    if title is not None:
        ax.set_title(title)

    if annotate:
        for row, column in np.ndindex(values.shape):
            value = values[row, column]
            color = "white" if value < 0.5 else "black"
            ax.text(column, row, f"{value:.2f}", ha="center", va="center", color=color)

    if colorbar:
        ax.figure.colorbar(image, ax=ax, label="MAC")
    return ax


def plot_mode_shape(
    model: Any,
    mode_shape: Any,
    *,
    mode: int = 0,
    scale: float = 1.0,
    ax: Any | None = None,
    show_undeformed: bool = True,
    title: str | None = None,
) -> Any:
    """Plot a model's undeformed geometry and one displaced mode shape.

    ``mode_shape`` may be a single full-model DOF vector, a canonical
    ``(ndof, n_modes)`` shape matrix, or an object exposing ``mode_shapes``
    (for example :class:`~openfemlab.core.results.ModalResult`). Translational
    DOFs displace the nodes; rotational components are intentionally ignored.

    The helper uses a three-dimensional axes by default. A supplied 2-D axes is
    also supported and shows the XY projection.

    Returns
    -------
    matplotlib.axes.Axes
        The axes containing the geometry.
    """

    try:
        factor = float(scale)
    except (TypeError, ValueError) as exc:
        raise ValueError("scale must be a finite number") from exc
    if not np.isfinite(factor):
        raise ValueError("scale must be a finite number")

    coordinates, node_indices = _model_geometry(model)
    vector, selected_mode, frequency = _select_mode_shape(mode_shape, mode)
    if vector.size != model.num_dofs:
        raise ValueError(
            f"mode shape has {vector.size} DOFs but the model has {model.num_dofs}"
        )
    if np.iscomplexobj(vector) and np.any(np.imag(vector) != 0.0):
        raise ValueError("plot_mode_shape requires a real mode shape")
    vector = np.asarray(np.real(vector), dtype=float)
    if not np.all(np.isfinite(vector)):
        raise ValueError("mode shape values must be finite")

    displacements = np.zeros_like(coordinates)
    for position, dof in enumerate(model.dofs):
        if dof.is_translational:
            displacements[:, int(dof)] = vector[position :: model.ndof_per_node]
    deformed = coordinates + factor * displacements

    pyplot = require_matplotlib()
    if ax is None:
        figure = pyplot.figure()
        ax = figure.add_subplot(111, projection="3d")

    is_3d = hasattr(ax, "get_zlim")
    undeformed_label = "Undeformed"
    deformed_label = f"Mode {selected_mode + 1}"
    plotted_undeformed = False
    plotted_deformed = False

    for element in model.elements:
        for start, end in _element_edges(element):
            indices = [node_indices[element.node_ids[start]], node_indices[element.node_ids[end]]]
            if show_undeformed:
                _plot_segment(
                    ax,
                    coordinates[indices],
                    is_3d=is_3d,
                    color="0.65",
                    linestyle="--",
                    linewidth=1.0,
                    label=undeformed_label if not plotted_undeformed else None,
                )
                plotted_undeformed = True
            _plot_segment(
                ax,
                deformed[indices],
                is_3d=is_3d,
                color="C0",
                linestyle="-",
                linewidth=1.8,
                label=deformed_label if not plotted_deformed else None,
            )
            plotted_deformed = True

    _scatter_nodes(
        ax,
        deformed,
        is_3d=is_3d,
        color="C0",
        s=18,
        label=deformed_label if not plotted_deformed else None,
    )
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    if is_3d:
        ax.set_zlabel("Z")
        extents = np.ptp(np.vstack((coordinates, deformed)), axis=0)
        ax.set_box_aspect(np.where(extents > 0.0, extents, 1.0))
    else:
        ax.set_aspect("equal", adjustable="datalim")

    if title is None:
        title = deformed_label
        if frequency is not None:
            title += f" — {frequency:.3g} Hz"
    if title:
        ax.set_title(title)
    ax.legend()
    return ax


def _as_mac_matrix(matrix: Any) -> np.ndarray:
    raw = np.asarray(matrix)
    if not np.issubdtype(raw.dtype, np.number):
        raise ValueError("MAC matrix must be numeric")
    if np.iscomplexobj(raw) and np.any(np.imag(raw) != 0.0):
        raise ValueError("MAC matrix must be real")
    values = np.asarray(np.real(raw), dtype=float)
    if values.ndim != 2 or 0 in values.shape:
        raise ValueError("MAC matrix must be a non-empty 2-D array")
    if not np.all(np.isfinite(values)):
        raise ValueError("MAC matrix values must be finite")
    return values


def _labels(labels: Sequence[object] | None, count: int, name: str) -> list[str]:
    if labels is None:
        return [str(index) for index in range(1, count + 1)]
    resolved = [str(label) for label in labels]
    if len(resolved) != count:
        raise ValueError(f"{name} has {len(resolved)} entries; expected {count}")
    return resolved


def _model_geometry(model: Any) -> tuple[np.ndarray, dict[Hashable, int]]:
    required = ("nodes", "elements", "dofs", "ndof_per_node", "num_dofs")
    if any(not hasattr(model, attribute) for attribute in required):
        raise TypeError("model must be an openfemlab Model")
    nodes = list(model.nodes)
    if not nodes:
        raise ValueError("model must contain at least one node")
    coordinates = np.vstack([np.asarray(node.coords, dtype=float) for node in nodes])
    return coordinates, {node.id: index for index, node in enumerate(nodes)}


def _select_mode_shape(mode_shape: Any, mode: int) -> tuple[np.ndarray, int, float | None]:
    shapes = np.asarray(getattr(mode_shape, "mode_shapes", mode_shape))
    frequency: float | None = None
    selected_mode = int(mode)
    if shapes.ndim == 1:
        if selected_mode not in (0, -1):
            raise IndexError("a single mode-shape vector only has mode 0")
        selected_mode = 0
        vector = shapes
    elif shapes.ndim == 2:
        if not -shapes.shape[1] <= selected_mode < shapes.shape[1]:
            raise IndexError(
                f"mode index {selected_mode} out of range for {shapes.shape[1]} modes"
            )
        selected_mode %= shapes.shape[1]
        vector = shapes[:, selected_mode]
    else:
        raise ValueError("mode_shape must be a 1-D vector or 2-D (ndof, n_modes) array")

    frequencies = getattr(mode_shape, "frequencies", None)
    if frequencies is not None:
        frequency = float(np.asarray(frequencies)[selected_mode])
    return vector, selected_mode, frequency


def _element_edges(element: Any) -> tuple[tuple[int, int], ...]:
    count = len(element.node_ids)
    if count < 2:
        return ()
    if count == 2:
        return ((0, 1),)
    name = type(element).__name__.lower()
    if count == 4 and "tet" in name:
        return ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    if count == 8 and "hex" in name:
        return (
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
        )
    return tuple((index, (index + 1) % count) for index in range(count))


def _plot_segment(ax: Any, points: np.ndarray, *, is_3d: bool, **style: Any) -> None:
    if is_3d:
        ax.plot(points[:, 0], points[:, 1], points[:, 2], **style)
    else:
        ax.plot(points[:, 0], points[:, 1], **style)


def _scatter_nodes(ax: Any, points: np.ndarray, *, is_3d: bool, **style: Any) -> None:
    if is_3d:
        ax.scatter(points[:, 0], points[:, 1], points[:, 2], **style)
    else:
        ax.scatter(points[:, 0], points[:, 1], **style)
