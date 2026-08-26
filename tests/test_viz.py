"""Tests for the optional Matplotlib plotting seam."""

from __future__ import annotations

import numpy as np
import pytest

matplotlib = pytest.importorskip("matplotlib", reason="requires the optional [plot] extra")
matplotlib.use("Agg")

from matplotlib import pyplot as plt  # noqa: E402

from openfemlab.core.elements import SpringElement  # noqa: E402
from openfemlab.core.model import Model  # noqa: E402
from openfemlab.core.results import ModalResult  # noqa: E402
from openfemlab.exceptions import MissingDependencyError  # noqa: E402
from openfemlab.viz import plot_mac_matrix, plot_mode_shape  # noqa: E402
from openfemlab.viz import plotting  # noqa: E402


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


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


def test_plot_mac_matrix_returns_populated_axes() -> None:
    matrix = np.array([[1.0, 0.25], [0.4, 0.9]])

    ax = plot_mac_matrix(matrix, colorbar=False)

    assert ax.images[0].get_clim() == (0.0, 1.0)
    np.testing.assert_array_equal(ax.images[0].get_array(), matrix)
    assert [tick.get_text() for tick in ax.get_xticklabels()] == ["1", "2"]
    assert [tick.get_text() for tick in ax.get_yticklabels()] == ["1", "2"]


def test_plot_mac_matrix_supports_labels_annotations_and_colorbar() -> None:
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


def test_plot_mode_shape_displaces_translational_dofs() -> None:
    model = _two_node_model()
    shape = np.array([0.0, 0.0, 0.25, 0.5])

    ax = plot_mode_shape(model, shape, scale=2.0)

    assert len(ax.lines) == 2
    x, y, z = ax.lines[1].get_data_3d()
    np.testing.assert_allclose(x, [0.0, 1.5])
    np.testing.assert_allclose(y, [0.0, 1.0])
    np.testing.assert_allclose(z, [0.0, 0.0])
    assert ax.get_title() == "Mode 1"


def test_plot_mode_shape_selects_mode_from_modal_result() -> None:
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


def test_plot_mode_shape_accepts_existing_2d_axes() -> None:
    _, ax = plt.subplots()

    returned = plot_mode_shape(_two_node_model(), np.zeros(4), ax=ax)

    assert returned is ax
    assert len(ax.lines) == 2


def test_plot_mode_shape_rejects_dof_mismatch() -> None:
    with pytest.raises(ValueError, match="3 DOFs but the model has 4"):
        plot_mode_shape(_two_node_model(), np.zeros(3))
