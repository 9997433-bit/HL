"""Tests for the optional Matplotlib plotting seam."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from openfemlab.core.elements import SpringElement
from openfemlab.core.model import Model
from openfemlab.core.results import ModalResult
from openfemlab.exceptions import MissingDependencyError
from openfemlab.viz import (
    plot_frf_overlay,
    plot_mac_matrix,
    plot_mode_shape,
    plot_stabilization_diagram,
    plotting,
)


@pytest.fixture
def pyplot() -> Any:
    matplotlib = pytest.importorskip(
        "matplotlib", reason="requires the optional [plot] extra"
    )
    matplotlib.use("Agg")
    from matplotlib import pyplot

    yield pyplot
    pyplot.close("all")


def _two_node_model() -> Model:
    model = Model(dofs=("UX", "UY"))
    model.add_node(1, (0.0, 0.0))
    model.add_node(2, (1.0, 0.0))
    model.add_element(SpringElement((1, 2), stiffness=1.0, dof="UX"))
    return model


def test_matplotlib_dependency_is_guarded(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(name: str):
        raise ImportError(name)

    monkeypatch.setattr(plotting, "import_module", unavailable)

    with pytest.raises(MissingDependencyError, match=r'pip install "openfemlab\[plot\]"'):
        plotting.require_matplotlib()


def test_plot_mac_matrix_returns_populated_axes(pyplot: Any) -> None:
    matrix = np.array([[1.0, 0.25], [0.4, 0.9]])

    ax = plot_mac_matrix(matrix, colorbar=False)

    assert ax.images[0].get_clim() == (0.0, 1.0)
    np.testing.assert_array_equal(ax.images[0].get_array(), matrix)
    assert [tick.get_text() for tick in ax.get_xticklabels()] == ["1", "2"]
    assert [tick.get_text() for tick in ax.get_yticklabels()] == ["1", "2"]


def test_plot_mac_matrix_supports_labels_annotations_and_colorbar(pyplot: Any) -> None:
    ax = plot_mac_matrix(
        [[1.0, 0.1]],
        row_labels=["Test 1"],
        column_labels=["FE 1", "FE 2"],
        annotate=True,
    )

    assert [tick.get_text() for tick in ax.get_xticklabels()] == ["FE 1", "FE 2"]
    assert [text.get_text() for text in ax.texts] == ["1.00", "0.10"]
    assert len(ax.figure.axes) == 2


@pytest.mark.parametrize(
    ("matrix", "message"),
    [
        ([1.0, 0.5], "non-empty 2-D"),
        ([[1.0, np.nan]], "finite"),
        ([[1.0 + 1.0j]], "real"),
    ],
)
def test_plot_mac_matrix_rejects_invalid_values(matrix, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        plot_mac_matrix(matrix)


def test_plot_mac_matrix_validates_label_lengths() -> None:
    with pytest.raises(ValueError, match="column_labels has 1 entries; expected 2"):
        plot_mac_matrix([[1.0, 0.5]], column_labels=["only one"])


def test_plot_mode_shape_displaces_translational_dofs(pyplot: Any) -> None:
    model = _two_node_model()
    shape = np.array([0.0, 0.0, 0.25, 0.5])

    ax = plot_mode_shape(model, shape, scale=2.0)

    assert len(ax.lines) == 2
    x, y, z = ax.lines[1].get_data_3d()
    np.testing.assert_allclose(x, [0.0, 1.5])
    np.testing.assert_allclose(y, [0.0, 1.0])
    np.testing.assert_allclose(z, [0.0, 0.0])
    assert ax.get_title() == "Mode 1"


def test_plot_mode_shape_selects_mode_from_modal_result(pyplot: Any) -> None:
    model = _two_node_model()
    result = ModalResult(
        frequencies=[2.0, 4.0],
        shapes=np.array(
            [
                [0.0, 0.0],
                [0.0, 0.0],
                [0.1, 0.2],
                [0.0, 0.3],
            ]
        ),
    )

    ax = plot_mode_shape(model, result, mode=1, show_undeformed=False)

    assert len(ax.lines) == 1
    assert ax.get_title() == "Mode 2 — 4 Hz"


def test_plot_mode_shape_accepts_existing_2d_axes(pyplot: Any) -> None:
    _, ax = pyplot.subplots()

    returned = plot_mode_shape(_two_node_model(), np.zeros(4), ax=ax)

    assert returned is ax
    assert len(ax.lines) == 2


def test_plot_mode_shape_rejects_dof_mismatch() -> None:
    with pytest.raises(ValueError, match="3 DOFs but the model has 4"):
        plot_mode_shape(_two_node_model(), np.zeros(3))


def test_plot_stabilization_diagram_scatters_poles(pyplot: Any) -> None:
    import openfemlab.mpe as mpe
    from openfemlab.solver.dynamics import modal_frf

    line = np.linspace(0.05, 30.0, 200)
    shapes = np.array([[1.0, 1.0], [1.5, -0.8], [0.6, 0.9]])
    frf = modal_frf(
        line,
        (2.0 * np.pi * np.array([3.0, 7.0]), shapes),
        np.array([0.02, 0.015]),
        response_dofs=[0, 1, 2],
        excitation_dofs=[0],
    )
    diagram = mpe.stabilization_diagram(frf, range(4, 9), band=(1.0, 12.0))

    ax = plot_stabilization_diagram(diagram, show_legend=False)

    assert len(ax.collections) > 0
    assert ax.get_xlabel() == "Model order"
    assert ax.get_ylabel() == "Frequency [Hz]"


def test_plot_frf_overlay_plots_two_curves(pyplot: Any) -> None:
    from openfemlab.solver.dynamics import FrequencyResponse, modal_frf

    line = np.linspace(1.0, 20.0, 50)
    shapes = np.array([[1.0], [0.5]])
    measured = modal_frf(
        line,
        (2.0 * np.pi * np.array([5.0]), shapes),
        np.array([0.02]),
        response_dofs=[0, 1],
        excitation_dofs=[0],
    )
    synthesized = FrequencyResponse(
        measured.frequencies,
        measured.data * 1.05,
        measured.response_dofs,
        measured.excitation_dofs,
    )

    ax = plot_frf_overlay(measured, synthesized, yscale="linear")

    assert len(ax.lines) == 2
    assert ax.get_yscale() == "linear"


def test_plot_frf_overlay_accepts_tuple_pair(pyplot: Any) -> None:
    frequencies = np.linspace(1.0, 10.0, 20)
    measured = frequencies, np.exp(1.0j * frequencies)
    synthesized = frequencies, np.exp(1.0j * frequencies) * 0.9

    ax = plot_frf_overlay(measured, synthesized, yscale="linear")

    assert len(ax.lines) == 2


def test_plot_frf_overlay_rejects_mismatched_frequency_lines() -> None:
    with pytest.raises(ValueError, match="same frequency line"):
        plot_frf_overlay((np.linspace(1, 2, 3), np.ones(3)), (np.linspace(1, 3, 4), np.ones(4)))
