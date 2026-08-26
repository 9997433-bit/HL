"""Guyan / IRS / SEREP reduction and SEREP expansion (MS-2.1, R2-T03).

The reference case is the 2-DOF grounded chain of :mod:`tests.modal_reference`
instrumented at a single DOF, which is the smallest model where reduction is a
real approximation and expansion has something to reconstruct: DOF 0 is the
sensor, DOF 1 is condensed away, and every property below has a closed form.

    m0 --k0-- m1 --k1-- ground        masters = [0], slaves = [1]

The Guyan transformation is then ``[1, k0/(k0 + k1)]ᵀ`` and the reduced
stiffness is the series combination ``k0 k1/(k0 + k1)`` — oracles the tests
check against, not regression values.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.correlation import (
    ReductionBasis,
    expand_shapes,
    guyan_reduction,
    irs_reduction,
    mac,
    orthogonality,
    serep_basis,
    tam_mass,
)
from openfemlab.exceptions import SolverError
from tests.modal_reference import (
    solve_generalized_symmetric,
    two_dof_chain,
    uniform_chain,
)

SENSOR = [0]


@pytest.fixture
def toy():
    """``(K, M)`` of the canonical 2-DOF chain: m = [2, 1], k = [1200, 800]."""
    return two_dof_chain().matrices()


def static_transformation(K: np.ndarray) -> np.ndarray:
    """Closed-form Guyan basis of a 2-DOF chain condensed onto DOF 0."""
    return np.array([[1.0], [-K[1, 1] ** -1 * K[1, 0]]])


# ---------------------------------------------------------------------------
# Guyan static condensation
# ---------------------------------------------------------------------------


def test_guyan_transformation_matches_the_closed_form(toy):
    K, _ = toy
    basis = guyan_reduction(K, SENSOR)
    assert basis.kind == "guyan"
    assert basis.n_full == 2
    assert basis.n_master == 1
    np.testing.assert_allclose(basis.transformation, static_transformation(K), rtol=1e-14)


def test_guyan_reduced_stiffness_is_the_springs_in_series(toy):
    K, _ = toy
    k0, k1 = 1200.0, 800.0
    reduced = guyan_reduction(K, SENSOR).reduce_matrix(K)
    np.testing.assert_allclose(reduced, [[k0 * k1 / (k0 + k1)]], rtol=1e-13)


def test_guyan_is_exact_when_the_condensed_dof_is_massless(toy):
    """The eigensolver's own use of this kernel: zero slave inertia, no error.

    Once ``m1 = 0`` the only finite root of ``det(K − λ M)`` is the series
    stiffness over ``m0``, which is what the reduced 1-DOF system must return.
    """
    K, M = toy
    k0, k1, m0 = 1200.0, 800.0, 2.0
    M[1, 1] = 0.0
    basis = guyan_reduction(K, SENSOR)
    reduced_eigenvalue = basis.reduce_matrix(K)[0, 0] / basis.reduce_matrix(M)[0, 0]
    assert float(reduced_eigenvalue) == pytest.approx(k0 * k1 / (k0 + k1) / m0, rel=1e-13)


def test_guyan_overestimates_the_first_frequency(toy):
    """With slave mass present, static condensation is stiff (Rayleigh quotient).

    The reduced eigenvalue is a Rayleigh quotient over a one-dimensional
    subspace, so it is bounded below by the first exact eigenvalue and above by
    the second.
    """
    K, M = toy
    basis = guyan_reduction(K, SENSOR)
    reduced = float(basis.reduce_matrix(K)[0, 0] / basis.reduce_matrix(M)[0, 0])
    exact = solve_generalized_symmetric(K, M)[0]
    assert exact[0] < reduced < exact[1]


def test_guyan_reduction_rejects_a_singular_slave_partition():
    K = np.array([[1.0, 0.0], [0.0, 0.0]])
    with pytest.raises(SolverError, match="singular"):
        guyan_reduction(K, SENSOR)


# ---------------------------------------------------------------------------
# IRS
# ---------------------------------------------------------------------------


def test_irs_beats_guyan_on_the_first_eigenvalue(toy):
    K, M = toy
    exact = float(solve_generalized_symmetric(K, M)[0][0])

    def reduced_eigenvalue(basis: ReductionBasis) -> float:
        return float(basis.reduce_matrix(K)[0, 0] / basis.reduce_matrix(M)[0, 0])

    guyan_error = abs(reduced_eigenvalue(guyan_reduction(K, SENSOR)) - exact)
    irs_error = abs(reduced_eigenvalue(irs_reduction(K, M, SENSOR)) - exact)
    assert irs_error < guyan_error


def test_irs_collapses_to_guyan_without_slave_mass(toy):
    K, M = toy
    M[1, 1] = 0.0
    np.testing.assert_allclose(
        irs_reduction(K, M, SENSOR).transformation,
        guyan_reduction(K, SENSOR).transformation,
        atol=1e-12,
    )


# ---------------------------------------------------------------------------
# SEREP
# ---------------------------------------------------------------------------


def test_serep_reproduces_the_in_band_mode_exactly(toy):
    """One sensor, one mode: the expansion is exact, not an approximation."""
    K, M = toy
    _, shapes = solve_generalized_symmetric(K, M)
    first = shapes[:, :1]
    basis = serep_basis(first, SENSOR)
    np.testing.assert_allclose(basis.expand(basis.reduce_shapes(first)), first, rtol=1e-12)


def test_serep_reduced_matrices_carry_the_exact_eigenvalue(toy):
    K, M = toy
    eigenvalues, shapes = solve_generalized_symmetric(K, M)
    basis = serep_basis(shapes[:, :1], SENSOR)
    reduced = float(basis.reduce_matrix(K)[0, 0] / basis.reduce_matrix(M)[0, 0])
    assert reduced == pytest.approx(float(eigenvalues[0]), rel=1e-12)


def test_serep_with_a_full_sensor_set_is_the_identity(toy):
    K, M = toy
    _, shapes = solve_generalized_symmetric(K, M)
    basis = serep_basis(shapes, [0, 1])
    np.testing.assert_allclose(basis.transformation, np.eye(2), atol=1e-12)


def test_serep_needs_at_least_as_many_sensors_as_modes(toy):
    K, M = toy
    _, shapes = solve_generalized_symmetric(K, M)
    with pytest.raises(SolverError, match="at least as many master DOFs"):
        serep_basis(shapes, SENSOR)


def test_serep_rejects_a_rank_deficient_sensor_partition():
    """Two modes that look identical at the sensors cannot be separated."""
    shapes = np.array([[1.0, 1.0], [1.0, 1.0], [1.0, -1.0]])
    with pytest.raises(SolverError, match="rank"):
        serep_basis(shapes, [0, 1])


def test_serep_rejects_complex_shapes():
    with pytest.raises(ValueError, match="real mode shapes"):
        serep_basis(np.array([[1.0 + 1.0j], [0.5]]), SENSOR)


# ---------------------------------------------------------------------------
# Expansion (AC-CORR-006 precursor)
# ---------------------------------------------------------------------------


def test_expansion_recovers_full_space_shapes_from_sensor_data(toy):
    """Noise-free twin: measured = FE shapes at the sensors, expanded back."""
    K, M = toy
    _, shapes = solve_generalized_symmetric(K, M)
    measured = shapes[SENSOR, :1] * -3.7  # arbitrary test-side scaling
    expanded = expand_shapes(shapes[:, :1], SENSOR, measured)
    assert mac(expanded, shapes[:, :1])[0, 0] == pytest.approx(1.0, abs=1e-12)


def test_expansion_of_an_underinstrumented_chain_keeps_mac_above_the_gate():
    """AC-CORR-006 scale model: 8-DOF chain, 3 modes seen by 4 sensors."""
    chain = uniform_chain(8)
    K, M = chain.matrices()
    _, shapes = solve_generalized_symmetric(K, M)
    sensors = [1, 3, 5, 7]
    band = shapes[:, :3]

    expanded = expand_shapes(band, sensors, band[sensors, :])
    diagonal = np.diag(mac(expanded, band))
    assert np.all(diagonal >= 0.999)


def test_expansion_row_count_and_sensor_rows_are_preserved():
    chain = uniform_chain(6)
    K, M = chain.matrices()
    _, shapes = solve_generalized_symmetric(K, M)
    sensors = [0, 2, 4]
    measured = shapes[sensors, :2]

    expanded = expand_shapes(shapes[:, :2], sensors, measured)
    assert expanded.shape == (6, 2)
    np.testing.assert_allclose(expanded[sensors, :], measured, atol=1e-10)


def test_expansion_rejects_a_measured_set_with_the_wrong_row_count(toy):
    K, M = toy
    _, shapes = solve_generalized_symmetric(K, M)
    with pytest.raises(ValueError, match="master DOFs"):
        expand_shapes(shapes, [0, 1], np.ones((3, 1)))


# ---------------------------------------------------------------------------
# TAM mass / pseudo-orthogonality
# ---------------------------------------------------------------------------


def test_tam_mass_is_symmetric_and_positive(toy):
    K, M = toy
    tam = tam_mass(guyan_reduction(K, SENSOR), M)
    np.testing.assert_allclose(tam, tam.T, atol=1e-14)
    assert np.all(np.linalg.eigvalsh(tam) > 0.0)


def test_serep_tam_gives_unit_pseudo_orthogonality(toy):
    """Mass-normalized modes through their own SEREP TAM: POC diagonal is 1."""
    K, M = toy
    _, shapes = solve_generalized_symmetric(K, M)
    basis = serep_basis(shapes[:, :1], SENSOR)
    poc = orthogonality(basis.reduce_shapes(shapes[:, :1]), basis.reduce_shapes(shapes[:, :1]),
                        tam_mass(basis, M))
    np.testing.assert_allclose(poc, np.eye(1), atol=1e-10)


def test_tam_pseudo_orthogonality_separates_modes_of_a_longer_chain():
    """AC-CORR-009 (proposed) shape: diag >= 0.99, off-diag <= 0.10."""
    chain = uniform_chain(8)
    K, M = chain.matrices()
    _, shapes = solve_generalized_symmetric(K, M)
    sensors = [1, 3, 5, 7]
    band = shapes[:, :4]

    basis = serep_basis(band, sensors)
    poc = orthogonality(basis.reduce_shapes(band), basis.reduce_shapes(band), tam_mass(basis, M))
    assert np.all(np.abs(np.diag(poc)) >= 0.99)
    off_diagonal = poc - np.diag(np.diag(poc))
    assert np.max(np.abs(off_diagonal)) <= 0.10


# ---------------------------------------------------------------------------
# Shared basis contract
# ---------------------------------------------------------------------------


def test_master_rows_of_a_condensation_basis_are_the_identity(toy):
    K, M = toy
    for basis in (guyan_reduction(K, SENSOR), irs_reduction(K, M, SENSOR)):
        np.testing.assert_allclose(basis.transformation[basis.master, :], np.eye(1), atol=1e-14)


def test_reduce_then_expand_is_idempotent_on_the_basis_range(toy):
    K, _ = toy
    basis = guyan_reduction(K, SENSOR)
    reduced = np.array([[2.5]])
    np.testing.assert_allclose(basis.reduce_shapes(basis.expand(reduced)), reduced, rtol=1e-14)


def test_basis_validates_input_dimensions(toy):
    K, _ = toy
    basis = guyan_reduction(K, SENSOR)
    with pytest.raises(ValueError, match="rows"):
        basis.reduce_matrix(np.eye(3))
    with pytest.raises(ValueError, match="rows"):
        basis.reduce_shapes(np.ones((5, 1)))


def test_master_dof_validation(toy):
    K, _ = toy
    with pytest.raises(ValueError, match="unique"):
        guyan_reduction(K, [0, 0])
    with pytest.raises(ValueError, match="at least one master"):
        guyan_reduction(K, [])
    with pytest.raises(IndexError, match="out of range"):
        guyan_reduction(K, [7])


def test_reduction_accepts_sparse_matrices(toy):
    sparse = pytest.importorskip("scipy.sparse")
    K, M = toy
    dense_basis = guyan_reduction(K, SENSOR)
    sparse_basis = guyan_reduction(sparse.csr_matrix(K), SENSOR)
    np.testing.assert_allclose(sparse_basis.transformation, dense_basis.transformation, atol=1e-14)
    np.testing.assert_allclose(
        sparse_basis.reduce_matrix(sparse.csr_matrix(M)),
        dense_basis.reduce_matrix(M),
        atol=1e-14,
    )
