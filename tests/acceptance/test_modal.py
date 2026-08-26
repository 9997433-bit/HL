"""M1 modal-analysis acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 2).

Implemented here
----------------
- **AC-MODAL-001** (oracle, MS-1.1) — analytic eigenvalue accuracy: the
  ``two_dof_analytic`` and ``ten_dof_chain`` fixtures to relative error 1e-10,
  the cantilever beam to 0.5 % of Euler-Bernoulli theory.
- **AC-MODAL-002** (property, MS-1.2) — the available eigensolver backends
  return the same k = 10 lowest modes of a 240-DOF chain.
- **AC-MODAL-003** (contract, MS-1.3) — every accepted result is mass
  orthonormal: ``max |Phi^T M Phi - I| <= 1e-8``.
- **AC-MODAL-004** (oracle, MS-1.2) — a structure with no connection to ground
  reports exactly ``nullity(K)`` modes at ``f = 0`` flagged rigid, and its
  elastic spectrum survives both the closed form and a constrained reference
  analysis of the same structure.
- **AC-MODAL-005** (contract, MS-1.3) — repeated runs are bitwise identical and
  the backends agree on the sign of every mode.
- **AC-MODAL-006** (contract, MS-1.2) — every returned eigenpair satisfies the
  MS-1.2 relative residual, and a starved Lanczos run raises
  ``SolverConvergenceError`` with the residuals attached.
- **AC-MODAL-007** (oracle, MS-1.4) — over the complete modal basis the
  effective modal masses sum to the total translational mass in every
  direction, to 1e-8 relative; a truncated basis visibly does not.
- **AC-MODAL-008** (oracle, MS-1.2) — a ``freq_window`` request returns exactly
  the modes the dense reference places in the window, and a window the
  extraction cannot fill raises ``MissedModesWarning`` (a ``SolverError`` under
  ``strict=True``).
- **AC-MODAL-009** (contract, MS-1.1) — asymmetric, indefinite and non-finite
  inputs fail with typed exceptions off the ``OpenFEMLabError`` hierarchy
  instead of returning plausible numbers.

MS-1.2 also lists ``lobpcg`` as an optional third backend. ``ModalSolver``
exposes the dense and shift-invert Lanczos paths today through its ``sparse``
switch; :data:`BACKENDS` picks up a ``backend`` keyword automatically if one
lands later, so the pairwise comparison extends without editing this suite.
"""

from __future__ import annotations

import ast
import inspect
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from scipy.linalg import eigh, null_space

from openfemlab import DOF, ModalSolver, Section
from openfemlab.correlation import mac
from openfemlab.exceptions import (
    MatrixDefinitenessError,
    MatrixSymmetryError,
    MissedModesWarning,
    OpenFEMLabError,
    SolverConvergenceError,
    SolverError,
)
from openfemlab.mesh.simple import beam_mesh, spring_mass_chain, truss_from_arrays
from openfemlab.solver import modal as modal_module
from openfemlab.solver.modal import SYMMETRY_TOL, eigenvalue_count_in_range, residual_floor

from ._support import (
    SQUARE,
    STEEL,
    cantilever_frequencies,
    chain_eigenvalues_fixed_fixed,
    chain_eigenvalues_fixed_free,
    chain_eigenvalues_free_free,
    criterion,
    dense,
    eigenpair_residuals,
    fixture_matrices,
    free_free_chain_matrices,
    load_fixture,
    mass_orthonormality_error,
    nullity,
    relative_error,
)

#: Gates of AC-MODAL-001..006.
EIGENVALUE_RTOL = 1e-10
BEAM_TOLERANCE_PERCENT = 0.5
BACKEND_FREQUENCY_RTOL = 1e-8
BACKEND_MAC_TOLERANCE = 1e-10
ORTHONORMALITY_TOLERANCE = 1e-8
RESIDUAL_TOLERANCE = 1e-8
SIGN_TIE_TOLERANCE = 1e-8

#: Gate of AC-MODAL-007.
EFFECTIVE_MASS_RTOL = 1e-8

#: Solver keywords per MS-1.2 backend name.
BACKENDS: dict[str, dict[str, Any]] = {
    "dense": {"sparse": False},
    "lanczos": {"sparse": True},
}
if "backend" in inspect.signature(ModalSolver.solve).parameters:  # pragma: no cover
    BACKENDS["lobpcg"] = {"backend": "lobpcg"}

#: Chain sized above the MS-1.2 dense/sparse crossover (n >= 200 DOFs).
BACKEND_CHAIN_DOFS = 240
BACKEND_MODES = 10

BEAM_LENGTH = 1.0
BEAM_ELEMENTS = 40


def _fixture_solver(name: str) -> tuple[ModalSolver, int]:
    K, M = fixture_matrices(load_fixture(name))
    return ModalSolver.from_matrices(K, M), K.shape[0]


def _chain_solver() -> tuple[ModalSolver, int]:
    return ModalSolver(spring_mass_chain(BACKEND_CHAIN_DOFS, 1.0, 1.0)), BACKEND_MODES


BEAM_MODES = 6


def _beam_solver() -> tuple[ModalSolver, int]:
    beam = beam_mesh(BEAM_LENGTH, BEAM_ELEMENTS, STEEL, SQUARE, support="cantilever")
    return ModalSolver(beam), BEAM_MODES


#: Models every accepted result of which must satisfy MS-1.3.
MODEL_CASES = {
    "two_dof_fixture": lambda: _fixture_solver("two_dof_analytic"),
    "ten_dof_fixture": lambda: _fixture_solver("ten_dof_chain"),
    "chain_240": _chain_solver,
    "cantilever_beam": _beam_solver,
}


# --------------------------------------------------------------- AC-MODAL-001


@criterion("AC-MODAL-001")
@pytest.mark.parametrize(
    ("fixture", "closed_form"),
    [
        ("two_dof_analytic", lambda: chain_eigenvalues_fixed_fixed(2)),
        ("ten_dof_chain", lambda: chain_eigenvalues_fixed_free(10)),
    ],
)
def test_ac_modal_001_fixture_eigenvalues_match_the_closed_form(fixture, closed_form):
    """Dense extraction reproduces the analytic spectrum to 1e-10 relative."""
    data = load_fixture(fixture)
    K, M = fixture_matrices(data)
    expected = closed_form()

    result = ModalSolver.from_matrices(K, M).solve(num_modes=K.shape[0], sparse=False)

    assert result.num_modes == K.shape[0]
    assert np.max(relative_error(result.eigenvalues, expected)) <= EIGENVALUE_RTOL
    # The stored fixture spectrum is the same closed form, so it must agree too.
    assert np.max(relative_error(data["expected"]["eigenvalues"], expected)) <= EIGENVALUE_RTOL
    assert np.max(relative_error(result.frequencies, data["expected"]["frequencies_hz"])) <= (
        EIGENVALUE_RTOL
    )


@criterion("AC-MODAL-001")
def test_ac_modal_001_cantilever_frequencies_match_euler_bernoulli_theory():
    """The first five bending frequencies stay within 0.5 % of theory."""
    solver, _ = _beam_solver()
    theory = cantilever_frequencies(BEAM_LENGTH)

    result = solver.solve(num_modes=theory.size, sparse=False)

    error_percent = 100.0 * relative_error(result.frequencies[: theory.size], theory)
    assert np.max(error_percent) <= BEAM_TOLERANCE_PERCENT, (
        f"worst beam frequency error {np.max(error_percent):.4g} % "
        f"at mode {int(np.argmax(error_percent)) + 1}"
    )
    # A converged discretization must not merely pass: it converges from above.
    assert np.all(result.frequencies[: theory.size] >= theory * (1.0 - 1e-9))


# --------------------------------------------------------------- AC-MODAL-002


@criterion("AC-MODAL-002")
@pytest.mark.parametrize(("first", "second"), list(combinations(BACKENDS, 2)))
def test_ac_modal_002_backends_return_the_same_lowest_modes(first, second):
    """Frequencies agree to 1e-8 relative and paired MAC reaches 1 - 1e-10."""
    model = spring_mass_chain(BACKEND_CHAIN_DOFS, 1.0, 1.0)
    reference = ModalSolver(model).solve(num_modes=BACKEND_MODES, **BACKENDS[first])
    other = ModalSolver(model).solve(num_modes=BACKEND_MODES, **BACKENDS[second])

    assert reference.num_modes == other.num_modes == BACKEND_MODES
    assert np.max(relative_error(reference.frequencies, other.frequencies)) <= (
        BACKEND_FREQUENCY_RTOL
    )

    paired = np.diag(mac(reference.mode_shapes, other.mode_shapes))
    assert np.min(paired) >= 1.0 - BACKEND_MAC_TOLERANCE
    # Same ordering, so the pairing is the diagonal and nothing crosses over.
    assert np.array_equal(
        np.argmax(mac(reference.mode_shapes, other.mode_shapes), axis=1),
        np.arange(BACKEND_MODES),
    )


@criterion("AC-MODAL-002")
def test_ac_modal_002_declared_backends_are_available():
    """The comparison covers the MS-1.2 dense and Lanczos paths at least."""
    assert {"dense", "lanczos"} <= set(BACKENDS)


# --------------------------------------------------------------- AC-MODAL-003


@criterion("AC-MODAL-003")
@pytest.mark.parametrize("case", sorted(MODEL_CASES))
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_modal_003_returned_modes_are_mass_orthonormal(case, backend):
    """``max |Phi^T M Phi - I| <= 1e-8`` for every backend and every model."""
    solver, num_modes = MODEL_CASES[case]()

    result = solver.solve(num_modes=num_modes, **BACKENDS[backend])

    assert result.normalization == "mass"
    error = mass_orthonormality_error(result.mode_shapes, result.system.M)
    assert error <= ORTHONORMALITY_TOLERANCE, (
        f"{case}/{backend}: mass-orthonormality defect {error:.3e}"
    )


@criterion("AC-MODAL-003")
def test_ac_modal_003_unnormalized_results_are_reported_as_such():
    """The contract holds for mass normalization only, and says which it used."""
    solver, num_modes = _fixture_solver("ten_dof_chain")

    unnormalized = solver.solve(num_modes=num_modes, normalization="max", sparse=False)

    assert unnormalized.normalization == "max"
    assert np.allclose(np.max(np.abs(unnormalized.mode_shapes), axis=0), 1.0)


# --------------------------------------------------------------- AC-MODAL-004

FREE_FREE_CHAIN_MASSES = 8


def _disconnected_chains(first: int, second: int):
    """Block-diagonal ``(K, M)`` of two chains with nothing tying them together."""
    K_a, M_a = free_free_chain_matrices(first)
    K_b, M_b = free_free_chain_matrices(second)
    K = np.zeros((first + second,) * 2)
    K[:first, :first], K[first:, first:] = K_a, K_b
    M = np.zeros_like(K)
    M[:first, :first], M[first:, first:] = M_a, M_b
    return K, M


#: Free-free structures and the nullity of their stiffness matrix. Two
#: unconnected chains have one rigid-body translation each, so the expected
#: count follows nullity(K) rather than the (still one) spatial dimension.
FREE_FREE_CASES = {
    "one_chain": (lambda: free_free_chain_matrices(FREE_FREE_CHAIN_MASSES), 1),
    "two_chains": (lambda: _disconnected_chains(5, 4), 2),
}


def _constrained_reference_eigenvalues(K: np.ndarray, M: np.ndarray, rigid: int) -> np.ndarray:
    """Elastic spectrum of the same structure, constrained against rigid motion.

    Restricting the eigenproblem to the ``M``-orthogonal complement of the null
    space of ``K`` is the classical inertia-relief constraint: it removes the
    rigid-body subspace and leaves every elastic mode untouched, so it is an
    independent reference for the elastic part of a free-free analysis.
    """
    rigid_basis = null_space(K, rcond=1e-10)
    assert rigid_basis.shape[1] == rigid
    complement = null_space((M @ rigid_basis).T)
    values, _ = eigh(complement.T @ K @ complement, complement.T @ M @ complement)
    return np.sort(values)


@criterion("AC-MODAL-004")
@pytest.mark.parametrize("case", sorted(FREE_FREE_CASES))
def test_ac_modal_004_rigid_body_count_equals_the_nullity_of_the_stiffness(case):
    """``sum(is_rigid) == nullity(K)``, and every flagged mode reports ``f = 0``."""
    matrices, expected_rigid = FREE_FREE_CASES[case]
    K, M = matrices()
    assert nullity(K) == expected_rigid

    result = ModalSolver.from_matrices(K, M).solve(num_modes=K.shape[0], sparse=False)

    flagged = result.is_rigid
    assert np.array_equal(flagged, result.rigid_body_modes)
    assert int(np.count_nonzero(flagged)) == expected_rigid, (
        f"{case}: flagged {int(np.count_nonzero(flagged))} rigid modes, "
        f"nullity(K) = {expected_rigid}"
    )
    assert np.all(flagged[:expected_rigid]) and not np.any(flagged[expected_rigid:])
    # Exactly zero, not the round-off frequency the raw eigenvalue would give.
    assert np.all(result.eigenvalues[:expected_rigid] == 0.0)
    assert np.all(result.frequencies[:expected_rigid] == 0.0)
    assert np.all(np.isinf(result.periods[:expected_rigid]))
    assert np.all(result.frequencies[expected_rigid:] > 0.0)


@criterion("AC-MODAL-004")
def test_ac_modal_004_free_free_elastic_spectrum_matches_theory_and_a_constrained_run():
    """The elastic modes are the free-free ones, rigid-body mode notwithstanding."""
    K, M = free_free_chain_matrices(FREE_FREE_CHAIN_MASSES)
    expected = chain_eigenvalues_free_free(FREE_FREE_CHAIN_MASSES)

    result = ModalSolver.from_matrices(K, M).solve(num_modes=K.shape[0], sparse=False)

    elastic = result.eigenvalues[1:]
    assert np.max(relative_error(elastic, expected[1:])) <= EIGENVALUE_RTOL
    constrained = _constrained_reference_eigenvalues(K, M, rigid=1)
    assert np.max(relative_error(elastic, constrained)) <= EIGENVALUE_RTOL


@criterion("AC-MODAL-004")
def test_ac_modal_004_rigid_mode_of_an_assembled_chain_is_the_translation():
    """The Model path agrees: one rigid mode, and it is a uniform translation."""
    model = spring_mass_chain(FREE_FREE_CHAIN_MASSES, 1.0, 1.0, fixed_start=False)
    solver = ModalSolver(model)
    K_free, _ = solver.system.reduced()

    result = solver.solve(num_modes=FREE_FREE_CHAIN_MASSES, sparse=False)

    assert int(np.count_nonzero(result.is_rigid)) == nullity(K_free) == 1
    assert result.frequencies[0] == 0.0
    translation = np.ones((result.mode_shapes.shape[0], 1))
    assert mac(result.mode_shapes[:, :1], translation)[0, 0] >= 1.0 - 1e-12
    # Grounding the same chain leaves no rigid mode at all, so the flag tracks
    # the structure and not some fixed property of the solver.
    grounded = ModalSolver(spring_mass_chain(FREE_FREE_CHAIN_MASSES, 1.0, 1.0)).solve(
        num_modes=FREE_FREE_CHAIN_MASSES, sparse=False
    )
    assert not np.any(grounded.is_rigid)


# --------------------------------------------------------------- AC-MODAL-005


@criterion("AC-MODAL-005")
@pytest.mark.parametrize("case", sorted(MODEL_CASES))
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_modal_005_repeated_runs_are_bitwise_identical(case, backend):
    """Same inputs, same numbers — down to the last bit."""
    first_solver, num_modes = MODEL_CASES[case]()
    second_solver, _ = MODEL_CASES[case]()

    first = first_solver.solve(num_modes=num_modes, **BACKENDS[backend])
    second = second_solver.solve(num_modes=num_modes, **BACKENDS[backend])
    # A third run through the solver that now holds cached factorizations:
    # reuse must not perturb the answer either.
    third = first_solver.solve(num_modes=num_modes, **BACKENDS[backend])

    for other, label in ((second, "fresh solver"), (third, "cached solver")):
        assert np.array_equal(first.eigenvalues, other.eigenvalues), label
        assert np.array_equal(first.mode_shapes, other.mode_shapes), label


@criterion("AC-MODAL-005")
@pytest.mark.parametrize("case", sorted(MODEL_CASES))
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_modal_005_largest_component_of_every_mode_is_positive(case, backend):
    """The MS-1.3 sign rule, with ties broken by the lowest DOF index.

    Chain modes routinely peak twice with opposite signs, so "the largest
    component" is only well defined once near-equal peaks count as tied; the
    rule then names the lowest-index peak, which need not be the strict argmax.
    """
    solver, num_modes = MODEL_CASES[case]()

    result = solver.solve(num_modes=num_modes, **BACKENDS[backend])

    shapes = result.mode_shapes
    magnitudes = np.abs(shapes)
    peaks = np.max(magnitudes, axis=0)
    columns = np.arange(shapes.shape[1])
    dominant = np.argmax(magnitudes >= peaks * (1.0 - SIGN_TIE_TOLERANCE), axis=0)

    np.testing.assert_allclose(magnitudes[dominant, columns], peaks, rtol=SIGN_TIE_TOLERANCE)
    assert np.all(shapes[dominant, columns] > 0.0)


@criterion("AC-MODAL-005")
def test_ac_modal_005_backends_agree_on_the_sign_of_every_mode():
    """Two backends, one convention: paired shapes are positively collinear."""
    model = spring_mass_chain(BACKEND_CHAIN_DOFS, 1.0, 1.0)
    reference = ModalSolver(model).solve(num_modes=BACKEND_MODES, **BACKENDS["dense"])
    other = ModalSolver(model).solve(num_modes=BACKEND_MODES, **BACKENDS["lanczos"])

    projection = np.einsum("ij,ij->j", reference.mode_shapes, other.mode_shapes)
    assert np.all(projection > 0.0), f"sign disagreement on modes {np.flatnonzero(projection <= 0)}"
    # The MAC gate of AC-MODAL-002 is blind to sign, so this is a real addition:
    # the shapes themselves, not merely the subspaces, have to coincide.
    assert np.max(np.abs(reference.mode_shapes - other.mode_shapes)) <= 1e-7


@criterion("AC-MODAL-005")
def test_ac_modal_005_sign_of_a_tied_mode_is_still_decided():
    """Every component of a rigid-body translation ties; the rule still decides."""
    K, M = free_free_chain_matrices(FREE_FREE_CHAIN_MASSES)

    result = ModalSolver.from_matrices(K, M).solve(num_modes=2, sparse=False)

    rigid = result.mode_shapes[:, 0]
    assert np.all(rigid > 0.0)
    assert np.max(rigid) - np.min(rigid) <= 1e-14


# --------------------------------------------------------------- AC-MODAL-006

#: The lowest mode of this model cannot reach the fixed MS-1.2 tolerance in
#: double precision; it is held to the solver's arithmetic floor instead.
ROUNDOFF_LIMITED_CASE = "cantilever_beam"


def _free_dof_residuals(result) -> np.ndarray:
    K, M = result.system.reduced()
    return eigenpair_residuals(K, M, result.eigenvalues, result.mode_shapes[result.free_dofs])


def _floor(result) -> np.ndarray:
    """Smallest residual double precision can deliver for this result."""
    K, M = result.system.reduced()
    return residual_floor(
        dense(K), dense(M), result.eigenvalues, result.mode_shapes[result.free_dofs]
    )


@criterion("AC-MODAL-006")
@pytest.mark.parametrize("case", sorted(MODEL_CASES))
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_modal_006_every_returned_eigenpair_meets_the_residual_gate(case, backend):
    """``‖K phi - lambda M phi‖ / ‖K phi‖ <= 1e-8`` for every accepted pair.

    Held against ``max(1e-8, floor)``, because the fixed MS-1.2 number is not
    reachable for the lowest mode of every model — see the test below, which
    pins the one case where the floor actually binds so this relaxation cannot
    quietly spread.
    """
    solver, num_modes = MODEL_CASES[case]()

    result = solver.solve(num_modes=num_modes, **BACKENDS[backend])

    residuals = _free_dof_residuals(result)
    limits = np.maximum(RESIDUAL_TOLERANCE, _floor(result))
    assert np.all(residuals <= limits), (
        f"{case}/{backend}: worst relative residual {np.max(residuals):.3e}"
    )


@criterion("AC-MODAL-006")
@pytest.mark.parametrize("case", sorted(MODEL_CASES))
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_modal_006_only_the_dense_cantilever_needs_the_arithmetic_floor(case, backend):
    """Where the plain 1e-8 of MS-1.2 holds, and the one place it cannot.

    LAPACK returns the 40-element cantilever's lowest mode at a relative
    residual of 2.7e-8, a factor two above ``eps ‖K‖ / lambda_1`` — the limit
    of double precision for a spectrum that wide, not a solver defect. The
    shift-invert Lanczos path concentrates its accuracy near the shift and gets
    the same mode to 1.7e-9, so even there the exception is one backend deep.
    """
    solver, num_modes = MODEL_CASES[case]()

    result = solver.solve(num_modes=num_modes, **BACKENDS[backend])

    worst = float(np.max(_free_dof_residuals(result)))
    if case == ROUNDOFF_LIMITED_CASE and backend == "dense":
        assert RESIDUAL_TOLERANCE < worst <= np.max(_floor(result))
    else:
        assert worst <= RESIDUAL_TOLERANCE


@criterion("AC-MODAL-006")
def test_ac_modal_006_a_starved_lanczos_run_raises_with_its_residuals():
    """Capping the Arnoldi restarts must fail loudly, not return junk modes."""
    model = spring_mass_chain(600, 1.0, 1.0)

    with pytest.raises(SolverConvergenceError) as excinfo:
        ModalSolver(model).solve(num_modes=10, sparse=True, maxiter=1)

    error = excinfo.value
    assert "converged" in str(error)
    # ARPACK hands back the subspace it did finish; its residuals travel with
    # the error, so a caller can see how far the run got.
    assert len(error.residuals) < 10


@criterion("AC-MODAL-006")
def test_ac_modal_006_a_loosely_converged_run_is_rejected_by_the_residual_gate():
    """A backend tolerance the eigenpairs cannot honour is caught on the way out."""
    model = spring_mass_chain(600, 1.0, 1.0)

    with pytest.raises(SolverConvergenceError) as excinfo:
        ModalSolver(model).solve(num_modes=10, sparse=True, tol=1e-3)

    error = excinfo.value
    assert len(error.residuals) == 10
    assert max(error.residuals) > RESIDUAL_TOLERANCE

    # Disabling the gate returns those very pairs, which is what makes the gate
    # — and not some other guard — the thing that rejected them.
    loose = ModalSolver(model).solve(num_modes=10, sparse=True, tol=1e-3, residual_tol=None)
    assert np.max(_free_dof_residuals(loose)) > RESIDUAL_TOLERANCE


# --------------------------------------------------------------- AC-MODAL-007

EFFECTIVE_MASS_CHAIN_MASSES = 10
EFFECTIVE_MASS_PER_NODE = 2.0

#: A pyramid on four pinned feet: one free node carrying mass in all three
#: translational directions, so the completeness relation has three
#: independent instances rather than the single one a chain offers.
TRUSS_APEX = (0.5, 0.5, 0.8)
TRUSS_BASE = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0))


def _pyramid_truss():
    coordinates = np.array([*TRUSS_BASE, TRUSS_APEX], dtype=float)
    connectivity = [(index, 4) for index in range(4)]
    model = truss_from_arrays(
        coordinates, connectivity, STEEL, Section(area=1e-4, name="1 cm2 rod")
    )
    for node in range(4):
        model.fix(node)
    return model


def _influence_vector(system, direction: DOF) -> np.ndarray:
    """Rigid-body influence vector ``r`` for one translational direction.

    Spelled out here rather than taken from ``ModalResult`` for the same reason
    as the residual helper: AC-MODAL-007 must not be checked against the
    private vector the quantity under test is built from.
    """
    vector = np.zeros(system.num_dofs, dtype=float)
    vector[np.asarray(system.dof_types) == int(direction)] = 1.0
    vector[system.constrained_dofs] = 0.0
    return vector


@criterion("AC-MODAL-007")
def test_ac_modal_007_chain_effective_masses_sum_to_the_physical_total():
    """The simplest oracle: lumped masses, so the total is known by counting."""
    solver = ModalSolver(
        spring_mass_chain(EFFECTIVE_MASS_CHAIN_MASSES, 1.0, EFFECTIVE_MASS_PER_NODE)
    )

    result = solver.solve(num_modes=EFFECTIVE_MASS_CHAIN_MASSES, sparse=False)

    total = EFFECTIVE_MASS_CHAIN_MASSES * EFFECTIVE_MASS_PER_NODE
    recovered = float(np.sum(result.effective_masses(DOF.UX)))
    assert abs(recovered / total - 1.0) <= EFFECTIVE_MASS_RTOL
    # Mass normalization is what makes ``m_eff = L^2`` in MS-1.4; assert it
    # rather than assume it, since the completeness relation depends on it.
    np.testing.assert_allclose(result.modal_masses, 1.0, rtol=EFFECTIVE_MASS_RTOL)


@criterion("AC-MODAL-007")
@pytest.mark.parametrize("direction", [DOF.UX, DOF.UY, DOF.UZ])
def test_ac_modal_007_completeness_holds_in_every_translational_direction(direction):
    """``sum_j m_eff,j = r^T M r`` per direction over the complete basis."""
    solver = ModalSolver(_pyramid_truss())
    system = solver.system

    result = solver.solve(num_modes=system.num_free_dofs, sparse=False)

    influence = _influence_vector(system, direction)
    total = float(influence @ (system.M @ influence))
    assert total > 0.0
    recovered = float(np.sum(result.effective_masses(direction)))
    assert abs(recovered / total - 1.0) <= EFFECTIVE_MASS_RTOL, (
        f"{direction.name}: {recovered:.12g} vs {total:.12g}"
    )


@criterion("AC-MODAL-007")
def test_ac_modal_007_a_truncated_basis_does_not_close_the_sum():
    """"Complete basis" is load-bearing: the gate fails for any smaller one."""
    solver = ModalSolver(
        spring_mass_chain(EFFECTIVE_MASS_CHAIN_MASSES, 1.0, EFFECTIVE_MASS_PER_NODE)
    )
    total = EFFECTIVE_MASS_CHAIN_MASSES * EFFECTIVE_MASS_PER_NODE

    partial = [
        float(np.sum(solver.solve(num_modes=k, sparse=False).effective_masses(DOF.UX)))
        for k in range(1, EFFECTIVE_MASS_CHAIN_MASSES + 1)
    ]

    assert partial == sorted(partial), "adding a mode can only add effective mass"
    assert partial[-1] == pytest.approx(total, rel=EFFECTIVE_MASS_RTOL)
    assert partial[-2] < total * (1.0 - EFFECTIVE_MASS_RTOL)


# --------------------------------------------------------------- AC-MODAL-008

WINDOW_CHAIN_MASSES = 12
#: Windows over the fixed-free chain spectrum, all with bounds strictly between
#: two eigenvalues so the contents do not depend on how a bound is rounded. The
#: expected contents come from the dense reference, never hard-coded. The
#: closed-interval behaviour on a bound is pinned separately below.
WINDOW_CASES = ("low", "interior", "empty", "everything")


def _window_reference() -> np.ndarray:
    """Every frequency of the window chain, from a full dense extraction."""
    solver = ModalSolver(spring_mass_chain(WINDOW_CHAIN_MASSES, 1.0, 1.0))
    return solver.solve(num_modes=WINDOW_CHAIN_MASSES, sparse=False).frequencies


def _window_bounds(case: str, reference: np.ndarray) -> tuple[float, float]:
    if case == "low":
        return 0.0, float(0.5 * (reference[2] + reference[3]))
    if case == "interior":
        return (
            float(0.5 * (reference[3] + reference[4])),
            float(0.5 * (reference[7] + reference[8])),
        )
    if case == "empty":
        gap = float(reference[1] - reference[0])
        return float(reference[0] + 0.3 * gap), float(reference[0] + 0.7 * gap)
    return 0.0, float(2.0 * reference[-1])


@criterion("AC-MODAL-008")
@pytest.mark.parametrize("case", WINDOW_CASES)
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_modal_008_a_window_returns_exactly_the_dense_reference_contents(case, backend):
    """``f in [f_lo, f_hi]`` selects the reference modes and nothing else."""
    reference = _window_reference()
    low, high = _window_bounds(case, reference)
    expected = reference[(reference >= low) & (reference <= high)]
    solver = ModalSolver(spring_mass_chain(WINDOW_CHAIN_MASSES, 1.0, 1.0))

    # Headroom over the window contents, so nothing is truncated, but still
    # under the ARPACK ``k < n - 1`` limit wherever the window is narrow enough
    # for the Lanczos path to be the one actually taken.
    result = solver.solve(
        num_modes=min(WINDOW_CHAIN_MASSES, expected.size + 2),
        freq_window=(low, high),
        **BACKENDS[backend],
    )

    assert result.num_modes == expected.size, (
        f"{case}/{backend}: {result.frequencies} vs {expected}"
    )
    if expected.size:
        assert np.max(relative_error(result.frequencies, expected)) <= BACKEND_FREQUENCY_RTOL
    assert result.meta["modes_in_window"] == expected.size
    assert result.meta["expected_in_window"] == expected.size


@criterion("AC-MODAL-008")
def test_ac_modal_008_a_mode_exactly_on_a_bound_is_inside_the_window():
    """The window is closed, so its bounds cannot drop a mode to round-off."""
    reference = _window_reference()
    low, high = float(reference[2]), float(reference[6])
    solver = ModalSolver(spring_mass_chain(WINDOW_CHAIN_MASSES, 1.0, 1.0))

    result = solver.solve(num_modes=WINDOW_CHAIN_MASSES, freq_window=(low, high), sparse=False)

    assert result.num_modes == 5
    assert result.frequencies[0] == pytest.approx(low, rel=BACKEND_FREQUENCY_RTOL)
    assert result.frequencies[-1] == pytest.approx(high, rel=BACKEND_FREQUENCY_RTOL)


@criterion("AC-MODAL-008")
def test_ac_modal_008_the_inertia_count_agrees_with_the_dense_reference():
    """The guard's Sylvester count is the number the dense spectrum shows.

    Counted without extracting a single mode, which is what makes the guard
    independent of the extraction it is checking.
    """
    solver = ModalSolver(spring_mass_chain(WINDOW_CHAIN_MASSES, 1.0, 1.0))
    K, M = solver.system.reduced()
    reference = _window_reference()

    for case in WINDOW_CASES:
        low, high = _window_bounds(case, reference)
        inside = int(np.count_nonzero((reference >= low) & (reference < high)))
        counted = eigenvalue_count_in_range(
            dense(K), dense(M), (2.0 * np.pi * low) ** 2, (2.0 * np.pi * high) ** 2
        )
        assert counted == inside, f"{case}: inertia count {counted}, reference {inside}"


@criterion("AC-MODAL-008")
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_modal_008_an_unfillable_window_warns_about_the_missed_modes(backend):
    """Capping ``num_modes`` below the window contents must not look complete."""
    reference = _window_reference()
    low, high = _window_bounds("everything", reference)
    solver = ModalSolver(spring_mass_chain(WINDOW_CHAIN_MASSES, 1.0, 1.0))

    with pytest.warns(MissedModesWarning, match="holds 12 modes but only 3"):
        result = solver.solve(
            num_modes=3, freq_window=(low, high), **BACKENDS[backend]
        )

    assert result.num_modes == 3
    assert result.meta["expected_in_window"] == WINDOW_CHAIN_MASSES


@criterion("AC-MODAL-008")
def test_ac_modal_008_strict_turns_the_missed_modes_into_an_error():
    """P1 escalation: the same run under ``strict=True`` refuses to return."""
    reference = _window_reference()
    low, high = _window_bounds("everything", reference)
    solver = ModalSolver(spring_mass_chain(WINDOW_CHAIN_MASSES, 1.0, 1.0))

    with pytest.raises(SolverError, match="holds 12 modes but only 3"):
        solver.solve(num_modes=3, freq_window=(low, high), sparse=False, strict=True)

    # The same request without the cap is complete, so it is the truncation and
    # not the window itself that the guard objects to.
    complete = solver.solve(
        num_modes=WINDOW_CHAIN_MASSES, freq_window=(low, high), sparse=False, strict=True
    )
    assert complete.num_modes == WINDOW_CHAIN_MASSES


@criterion("AC-MODAL-008")
def test_ac_modal_008_skipping_the_inertia_check_is_recorded_not_assumed():
    """A skipped guard reports ``None``, never a count it did not compute."""
    reference = _window_reference()
    low, high = _window_bounds("everything", reference)
    solver = ModalSolver(spring_mass_chain(WINDOW_CHAIN_MASSES, 1.0, 1.0))

    result = solver.solve(
        num_modes=3, freq_window=(low, high), sparse=False, missed_mode_check=False
    )

    assert result.num_modes == 3
    assert result.meta["expected_in_window"] is None


@criterion("AC-MODAL-008")
@pytest.mark.parametrize("window", [(-1.0, 1.0), (2.0, 1.0)])
def test_ac_modal_008_an_impossible_window_is_rejected(window):
    """``0 <= f_lo <= f_hi`` is a precondition, not a thing to interpret."""
    solver = ModalSolver(spring_mass_chain(4, 1.0, 1.0))

    with pytest.raises(SolverError, match="freq_window"):
        solver.solve(num_modes=2, freq_window=window)


# --------------------------------------------------------------- AC-MODAL-009

#: A 2-DOF chain, the smallest well-posed problem to corrupt one input of.
VALID_K = np.array([[2.0, -1.0], [-1.0, 1.0]])
VALID_M = np.eye(2)


def _solve(K, M, **kwargs):
    return ModalSolver.from_matrices(K, M).solve(num_modes=2, sparse=False, **kwargs)


@criterion("AC-MODAL-009")
@pytest.mark.parametrize("corrupted", ["K", "M"])
def test_ac_modal_009_an_asymmetric_matrix_raises_before_it_is_symmetrized(corrupted):
    """MS-1.1 symmetrizes silently, so it has to refuse what it cannot repair."""
    K, M = VALID_K.copy(), VALID_M.copy()
    matrix = K if corrupted == "K" else M
    matrix[0, 1] += 0.25

    with pytest.raises(MatrixSymmetryError) as excinfo:
        _solve(K, M)

    error = excinfo.value
    assert corrupted in str(error)
    assert error.tolerance == SYMMETRY_TOL
    assert error.asymmetry > SYMMETRY_TOL
    # The symmetrized problem would have solved happily, which is exactly the
    # plausible wrong answer the guard exists to prevent.
    symmetric = 0.5 * (matrix + matrix.T)
    if corrupted == "K":
        assert _solve(symmetric, M).num_modes == 2
    else:
        assert _solve(K, symmetric).num_modes == 2


@criterion("AC-MODAL-009")
def test_ac_modal_009_asymmetry_inside_the_tolerance_is_repaired_not_rejected():
    """The gate is a tolerance: assembly round-off must still go through."""
    K = VALID_K.copy()
    K[0, 1] += 0.1 * SYMMETRY_TOL * float(np.max(np.abs(K)))

    result = _solve(K, VALID_M)

    exact = _solve(VALID_K, VALID_M)
    assert np.max(relative_error(result.eigenvalues, exact.eigenvalues)) <= 1e-9


@criterion("AC-MODAL-009")
@pytest.mark.parametrize(
    ("case", "mass"),
    [
        ("negative_mass_dof", np.diag([1.0, -1.0])),
        ("indefinite_coupling", np.array([[1.0, 2.0], [2.0, 1.0]])),
    ],
)
def test_ac_modal_009_an_indefinite_mass_matrix_raises_the_definiteness_error(case, mass):
    """Both flavours of indefinite ``M`` land on the same typed failure."""
    with pytest.raises(MatrixDefinitenessError):
        _solve(VALID_K, mass)


@criterion("AC-MODAL-009")
def test_ac_modal_009_a_negative_eigenvalue_beyond_the_noise_floor_raises():
    """An unstable model is reported, not clipped to a 0 Hz rigid-body mode."""
    K = np.diag([1.0, -1.0])

    with pytest.raises(MatrixDefinitenessError) as excinfo:
        _solve(K, VALID_M)

    error = excinfo.value
    assert error.eigenvalue == pytest.approx(-1.0)
    assert error.floor < 0.0
    # A free-free structure has eigenvalues at the floor rather than past it,
    # so the guard separates round-off around zero from genuine instability.
    free_free = ModalSolver.from_matrices(*free_free_chain_matrices(4)).solve(
        num_modes=4, sparse=False
    )
    assert free_free.eigenvalues[0] == 0.0


@criterion("AC-MODAL-009")
@pytest.mark.parametrize("value", [np.nan, np.inf])
def test_ac_modal_009_non_finite_entries_do_not_propagate_into_the_result(value):
    """A NaN in the input must stop the solve, not come back as a NaN frequency."""
    K = VALID_K.copy()
    K[1, 1] = value

    with pytest.raises(SolverError, match="NaN or infinite"):
        _solve(K, VALID_M)


@criterion("AC-MODAL-009")
@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"num_modes": 0}, "num_modes"),
        ({"num_modes": 2, "normalization": "unit-torque"}, "normalization"),
    ],
)
def test_ac_modal_009_invalid_requests_are_typed_failures_too(kwargs, match):
    """The same contract covers the request, not only the matrices."""
    solver = ModalSolver.from_matrices(VALID_K, VALID_M)

    with pytest.raises(SolverError, match=match):
        solver.solve(**kwargs)


@criterion("AC-MODAL-009")
def test_ac_modal_009_every_declared_failure_is_an_openfemlab_error():
    """One hierarchy, so a caller can catch the whole solver in one clause."""
    for failure in (
        MatrixSymmetryError,
        MatrixDefinitenessError,
        SolverConvergenceError,
        SolverError,
    ):
        assert issubclass(failure, OpenFEMLabError)
    assert issubclass(MatrixSymmetryError, SolverError)
    assert issubclass(MatrixDefinitenessError, SolverError)


@criterion("AC-MODAL-009")
def test_ac_modal_009_the_solver_carries_no_bare_assertions():
    """``assert`` vanishes under ``python -O``; a validation gate may not."""
    source = Path(modal_module.__file__).read_text(encoding="utf-8")
    asserts = [
        node.lineno
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Assert)
    ]
    assert not asserts, f"bare assert statements at lines {asserts} of solver/modal.py"
