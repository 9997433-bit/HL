"""GAP-01 regression: one ``ModalResult`` shared by every producer and consumer.

The solver used to return its own ``ModalResult`` (eigenvalues / mode_shapes /
system) while ``io`` and ``correlation`` spoke a different one (frequencies /
shapes / dof_map). These tests pin the merged contract so the split cannot
reappear: the two vocabularies must name the same arrays, and a result must be
able to travel from the eigensolver to the correlation and io layers without
being rebuilt as a different type.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import openfemlab.core.results as core_results
import openfemlab.solver as solver_package
import openfemlab.solver.modal as solver_modal
from openfemlab.core.dofs import DofMap, DofType
from openfemlab.core.results import ModalResult
from openfemlab.core.results import TestData as ModalTestData
from openfemlab.io import FormatError, read_modal_result, write_modal_result
from openfemlab.mesh.simple import spring_mass_chain
from openfemlab.modal.eigen import solve_modes
from openfemlab.solver.modal import ModalSolver

#: A 4-mass chain is grounded at node 0, so the full DOF space has five rows.
CHAIN_DOF_MAP = DofMap.regular([0, 1, 2, 3, 4], (DofType.UX,))
FREE_DOF_MAP = DofMap.regular([1, 2, 3, 4], (DofType.UX,))


def chain_result(n: int = 4, num_modes: int = 3) -> ModalResult:
    return ModalSolver(spring_mass_chain(n, 1000.0, 1.0)).solve(num_modes=num_modes)


# ------------------------------------------------------------------- identity


def test_every_module_exposes_the_same_modal_result_class():
    assert solver_modal.ModalResult is core_results.ModalResult
    assert solver_package.ModalResult is core_results.ModalResult
    assert ModalResult.__module__ == "openfemlab.core.results"


def test_the_solver_returns_the_core_contract():
    assert isinstance(chain_result(), ModalResult)


# ------------------------------------------------------------ dual vocabulary


def test_both_spellings_name_the_same_arrays():
    result = chain_result()

    assert result.shapes is result.mode_shapes
    assert result.n_modes == result.num_modes == 3
    np.testing.assert_allclose(
        result.frequencies, result.angular_frequencies / (2.0 * np.pi), rtol=0.0
    )


def test_a_spectrum_given_in_hertz_yields_the_matching_eigenvalues():
    frequencies = np.array([2.0, 7.5, 19.0])
    result = ModalResult(frequencies=frequencies, shapes=np.eye(3))

    np.testing.assert_allclose(result.eigenvalues, (2.0 * np.pi * frequencies) ** 2, rtol=1e-15)
    np.testing.assert_allclose(result.frequencies, frequencies, rtol=1e-15)


def test_a_spectrum_given_as_eigenvalues_yields_the_matching_frequencies():
    eigenvalues = np.array([0.0, 4.0e3, 2.5e5])
    result = ModalResult(eigenvalues=eigenvalues, mode_shapes=np.eye(3))

    np.testing.assert_allclose(result.eigenvalues, eigenvalues, rtol=0.0)
    np.testing.assert_allclose(
        result.frequencies, np.sqrt(eigenvalues) / (2.0 * np.pi), rtol=1e-15
    )
    assert result.rigid_body_modes[0]


@pytest.mark.parametrize(
    "spectrum",
    [{}, {"frequencies": [1.0], "eigenvalues": [39.5]}],
    ids=["missing", "ambiguous"],
)
def test_the_spectrum_must_be_given_exactly_once(spectrum):
    with pytest.raises(ValueError, match="'frequencies'.*'eigenvalues'"):
        ModalResult(shapes=[[1.0]], **spectrum)


@pytest.mark.parametrize(
    "shapes",
    [{}, {"shapes": [[1.0]], "mode_shapes": [[1.0]]}],
    ids=["missing", "ambiguous"],
)
def test_the_shapes_must_be_given_exactly_once(shapes):
    with pytest.raises(ValueError, match="'shapes' or 'mode_shapes'"):
        ModalResult(frequencies=[1.0], **shapes)


def test_shapes_must_match_the_dof_map():
    with pytest.raises(ValueError, match="inconsistent"):
        ModalResult(
            frequencies=[1.0, 2.0],
            shapes=np.ones((3, 2)),
            dof_map=DofMap.regular([1, 2], (DofType.UX,)),
        )


# ---------------------------------------------------- solver result stays rich


def test_generalized_quantities_survive_the_merge():
    result = chain_result(n=6, num_modes=6)

    np.testing.assert_allclose(result.modal_masses, np.ones(6), atol=1e-9)
    np.testing.assert_allclose(
        result.modal_stiffnesses, result.eigenvalues * result.modal_masses, rtol=1e-9
    )
    assert result.orthogonality_error() < 1e-9
    assert float(np.sum(result.effective_masses("UX"))) == pytest.approx(6.0, rel=1e-9)
    assert result.num_condensed_dofs == 0
    assert result.normalization == "mass"


def test_a_result_without_a_system_reports_why_it_cannot_be_expanded():
    result = ModalResult(frequencies=[1.0], shapes=[[1.0]])

    assert result.system is None
    with pytest.raises(core_results.SolverError, match="no assembled system"):
        _ = result.modal_masses


# ------------------------------------------------------- travelling downstream


def test_attaching_a_dof_map_keeps_the_solver_provenance():
    result = chain_result()
    labelled = result.with_dof_map(CHAIN_DOF_MAP, meta={"model": "chain"})

    assert isinstance(labelled, ModalResult)
    assert labelled.dof_map is CHAIN_DOF_MAP
    assert labelled.meta == {"model": "chain"}
    np.testing.assert_array_equal(labelled.eigenvalues, result.eigenvalues)
    np.testing.assert_array_equal(labelled.shapes, result.shapes)
    assert labelled.system is result.system
    assert labelled.normalization == result.normalization
    np.testing.assert_allclose(labelled.modal_masses, result.modal_masses, rtol=0.0)


def test_a_solver_result_reaches_io_without_being_rebuilt(tmp_path: Path):
    labelled = chain_result().with_dof_map(CHAIN_DOF_MAP)

    path = tmp_path / "modes.json"
    write_modal_result(labelled, path)
    restored = read_modal_result(path)

    np.testing.assert_allclose(restored.frequencies, labelled.frequencies)
    np.testing.assert_allclose(restored.shapes, labelled.shapes)
    np.testing.assert_allclose(restored.eigenvalues, labelled.eigenvalues, rtol=1e-12)


def test_writing_a_result_without_a_dof_map_says_what_is_missing(tmp_path: Path):
    with pytest.raises(FormatError, match="with_dof_map"):
        write_modal_result(chain_result(), tmp_path / "modes.json")


def test_a_solver_result_correlates_against_test_data():
    from openfemlab.correlation import correlate_modal_data

    labelled = chain_result().with_dof_map(CHAIN_DOF_MAP)
    measured = ModalTestData(
        frequencies=labelled.frequencies * 1.01,
        shapes=labelled.shapes,
        dof_map=CHAIN_DOF_MAP,
    )

    report = correlate_modal_data(labelled, measured)

    assert report.summary.min_mac == pytest.approx(1.0, abs=1e-12)


def test_the_matrix_entry_point_returns_the_same_contract():
    system = ModalSolver(spring_mass_chain(4, 1000.0, 1.0)).system
    K, M = system.reduced()

    result = solve_modes(K, M, FREE_DOF_MAP, n_modes=3)

    assert isinstance(result, ModalResult)
    assert result.dof_map is FREE_DOF_MAP
    np.testing.assert_allclose(
        result.frequencies, chain_result().frequencies, rtol=1e-8
    )
