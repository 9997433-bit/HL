"""Matplotlib-backed mode-shape and correlation plots."""

from __future__ import annotations

from collections.abc import Hashable, Sequence
from importlib import import_module
from types import ModuleType
from typing import Any

import numpy as np

from openfemlab.exceptions import MissingDependencyError

__all__ = [
    "element_edges",
    "plot_frf_overlay",
    "plot_mac_matrix",
    "plot_mode_shape",
    "plot_stabilization_diagram",
    "require_matplotlib",
]

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
        for start, end in element_edges(element):
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


_LABEL_COLORS = {
    "new": "0.55",
    "freq": "#e6a700",
    "damp": "#cf222e",
    "stable": "#1a7f37",
}


def plot_stabilization_diagram(
    diagram: Any,
    *,
    ax: Any | None = None,
    title: str | None = "Stabilization diagram",
    show_legend: bool = True,
) -> Any:
    """Plot pole frequency vs model order (standard MPE stabilization chart).

    Parameters
    ----------
    diagram:
        A :class:`~openfemlab.mpe.StabilizationDiagram` or compatible object
        exposing ``orders`` and ``poles`` (per-order pole tuples with
        ``frequency_hz`` and ``label``).
    """
    orders = tuple(getattr(diagram, "orders", ()))
    pole_levels = tuple(getattr(diagram, "poles", ()))
    if not orders or not pole_levels:
        raise ValueError("stabilization diagram must contain at least one model order")

    pyplot = require_matplotlib()
    if ax is None:
        _, ax = pyplot.subplots()

    plotted_labels: set[str] = set()
    for level, order in enumerate(orders):
        for pole in pole_levels[level]:
            label = str(getattr(pole, "label", "new"))
            color = _LABEL_COLORS.get(label, "C0")
            marker = "o" if label == "stable" else "."
            size = 36 if label == "stable" else 18
            legend_label = label if label not in plotted_labels and show_legend else None
            ax.scatter(
                order,
                float(pole.frequency_hz),
                c=color,
                marker=marker,
                s=size,
                label=legend_label,
                alpha=0.85,
            )
            if legend_label is not None:
                plotted_labels.add(label)

    ax.set_xlabel("Model order")
    ax.set_ylabel("Frequency [Hz]")
    if title:
        ax.set_title(title)
    if show_legend and plotted_labels:
        ax.legend(title="Pole label", loc="best")
    return ax


def plot_frf_overlay(
    measured: Any,
    synthesized: Any,
    *,
    response_index: int = 0,
    excitation_index: int = 0,
    ax: Any | None = None,
    yscale: str = "log",
    title: str | None = "FRF overlay",
    measured_label: str = "Measured",
    synthesized_label: str = "Synthesized",
) -> Any:
    """Overlay measured and synthesized FRF magnitude on one frequency axis.

    Each operand may be a :class:`~openfemlab.solver.dynamics.FrequencyResponse`
    or a ``(frequencies, complex_values)`` pair for one channel.
    """
    freq_m, values_m = _frf_channel(measured, response_index, excitation_index, "measured")
    freq_s, values_s = _frf_channel(synthesized, response_index, excitation_index, "synthesized")
    if freq_m.shape != freq_s.shape or not np.allclose(freq_m, freq_s):
        raise ValueError("measured and synthesized FRFs must share the same frequency line")

    magnitude_m = np.abs(values_m)
    magnitude_s = np.abs(values_s)
    if not np.all(np.isfinite(magnitude_m)) or not np.all(np.isfinite(magnitude_s)):
        raise ValueError("FRF magnitudes must be finite")

    pyplot = require_matplotlib()
    if ax is None:
        _, ax = pyplot.subplots()

    ax.plot(freq_m, magnitude_m, label=measured_label, color="C0", linewidth=1.6)
    ax.plot(freq_s, magnitude_s, label=synthesized_label, color="C1", linewidth=1.2, linestyle="--")
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("|FRF|")
    ax.set_yscale(yscale)
    if title:
        ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)
    return ax


def _frf_channel(
    operand: Any,
    response_index: int,
    excitation_index: int,
    name: str,
) -> tuple[np.ndarray, np.ndarray]:
    if hasattr(operand, "frequencies") and hasattr(operand, "data"):
        frequencies = np.asarray(operand.frequencies, dtype=float).ravel()
        data = np.asarray(operand.data)
        if data.ndim != 3:
            raise ValueError(f"{name} FRF data must be (frequencies, responses, excitations)")
        values = data[:, response_index, excitation_index]
        return frequencies, np.asarray(values, dtype=complex).ravel()

    if isinstance(operand, tuple) and len(operand) == 2:
        frequencies = np.asarray(operand[0], dtype=float).ravel()
        values = np.asarray(operand[1])
        if values.ndim != 1:
            raise ValueError(f"{name} channel values must be one-dimensional")
        if frequencies.size != values.size:
            raise ValueError(f"{name} frequencies and values length mismatch")
        return frequencies, np.asarray(values, dtype=complex).ravel()

    raise TypeError(
        f"{name} operand must be a FrequencyResponse or (frequencies, complex_values) pair"
    )


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


def element_edges(element: Any) -> tuple[tuple[int, int], ...]:
    """Local node index pairs drawing an element's wireframe.

    Solids get their real edge list, a shell or membrane its boundary loop, a
    two-node member its single segment, and a grounded spring nothing at all.
    """
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
