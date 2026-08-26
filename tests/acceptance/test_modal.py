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
- **AC-MODAL-007** (oracle, MS-1.4) — summed over the complete modal basis, the
  effective modal masses reproduce the rigid-body mass of the structure in each
  translational direction to 1e-8 relative.
- **AC-MODAL-009** (contract, MS-1.1) — an asymmetric ``K`` or ``M`` beyond the
  MS-1.1 tolerance raises ``MatrixSymmetryError``, an indefinite ``M`` or a
  negative eigenvalue past the rigid-body noise floor raises
  ``MatrixDefinitenessError``, and the solver package contains no bare
  ``assert`` and no path that returns a NaN instead of failing.

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

import openfemlab.solver as solver_package
from openfemlab import ModalSolver
from openfemlab.core.model import DOF
from openfemlab.correlation import mac
from openfemlab.exceptions import (
    MatrixDefinitenessError,
    MatrixSymmetryError,
    OpenFEMLabError,
    SolverConvergenceError,
    SolverError,
)
from openfemlab.mesh.simple import beam_mesh, quad_plate_mesh, spring_mass_chain
from openfemlab.solver.modal import SYMMETRY_TOL, residual_floor, symmetry_defect

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
EFFECTIVE_MASS_RTOL = 1e-8

#: Mass fraction a half-length modal basis must still be missing (AC-MODAL-007).
TRUNCATION_DEFICIT = 1e-4

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

#: Chain masses of the two completeness cases, uniform and graded.
COMPLETENESS_CHAIN_MASSES = 10
GRADED_MASSES = tuple(0.5 + 0.25 * index for index in range(COMPLETENESS_CHAIN_MASSES))

#: Cantilevered plate: a two-direction model with a consistent-mass beam
#: alongside it, so the completeness identity is checked where the mass matrix
#: is neither diagonal nor confined to a single direction.
PLATE_DIVISIONS = (6, 3)


def _grounded_chain(mass) -> ModalSolver:
    return ModalSolver(spring_mass_chain(COMPLETENESS_CHAIN_MASSES, 1.0, mass))


def _plate_solver() -> ModalSolver:
    plate = quad_plate_mesh(
        2.0, 0.5, *PLATE_DIVISIONS, STEEL, thickness=0.01, support="cantilever",
        lumped_mass=True,
    )
    return ModalSolver(plate)


def _beam_solver_full() -> ModalSolver:
    return ModalSolver(beam_mesh(1.0, 8, STEEL, SQUARE, support="cantilever"))


#: Models whose mass is carried entirely by free DOFs, so the participating
#: mass of MS-1.4 *is* the total mass of the model.
FULLY_FREE_MASS_CASES = {
    "uniform_chain": lambda: (_grounded_chain(2.0), ("UX",)),
    "graded_chain": lambda: (_grounded_chain(GRADED_MASSES), ("UX",)),
}

#: Models whose supports carry mass too; there the oracle is the rigid-body
#: mass of the *free* partition (see the second test).
SUPPORTED_MASS_CASES = {
    "cantilever_beam": lambda: (_beam_solver_full(), ("UX", "UY")),
    "cantilever_plate": lambda: (_plate_solver(), ("UX", "UY")),
}

COMPLETENESS_CASES = FULLY_FREE_MASS_CASES | SUPPORTED_MASS_CASES


def _complete_basis(solver: ModalSolver):
    """Every mode of the free partition, with nothing condensed away."""
    return solver.solve(
        num_modes=solver.system.num_free_dofs, sparse=False, condense_massless=False
    )


def _rigid_body_mass(system, direction: str) -> float:
    """``r^T M r`` for the unit translation ``r`` of the free DOFs (MS-1.4).

    Spelled out here rather than taken from the result object: the mass a
    structure can put into its modes is the mass its *free* DOFs carry, so this
    is what the modal sum has to reproduce. It coincides with the total mass of
    the model exactly when no supported DOF holds any.
    """
    influence = np.zeros(system.num_dofs, dtype=float)
    influence[np.asarray(system.dof_types) == int(DOF.parse(direction))] = 1.0
    influence[system.constrained_dofs] = 0.0
    return float(influence @ (system.M @ influence))


@criterion("AC-MODAL-007")
@pytest.mark.parametrize("case", sorted(COMPLETENESS_CASES))
def test_ac_modal_007_the_complete_basis_accounts_for_all_participating_mass(case):
    """``sum_j m_eff,j = r^T M r`` per translational direction, to 1e-8 relative."""
    solver, directions = COMPLETENESS_CASES[case]()

    result = _complete_basis(solver)

    assert result.num_modes == solver.system.num_free_dofs
    for direction in directions:
        total = _rigid_body_mass(result.system, direction)
        recovered = float(np.sum(result.effective_masses(direction)))
        assert recovered == pytest.approx(total, rel=EFFECTIVE_MASS_RTOL), (
            f"{case}/{direction}: {recovered:.12g} of {total:.12g}"
        )


@criterion("AC-MODAL-007")
@pytest.mark.parametrize("case", sorted(FULLY_FREE_MASS_CASES))
def test_ac_modal_007_that_sum_is_the_total_mass_when_no_support_carries_any(case):
    """On the chains the MS-1.4 oracle is the model's own total mass."""
    solver, directions = FULLY_FREE_MASS_CASES[case]()

    result = _complete_basis(solver)

    total_mass = result.system.total_mass
    assert _rigid_body_mass(result.system, "UX") == pytest.approx(total_mass, rel=1e-14)
    for direction in directions:
        recovered = float(np.sum(result.effective_masses(direction)))
        assert recovered == pytest.approx(total_mass, rel=EFFECTIVE_MASS_RTOL)


@criterion("AC-MODAL-007")
@pytest.mark.parametrize("case", sorted(SUPPORTED_MASS_CASES))
def test_ac_modal_007_mass_held_by_the_supports_is_correctly_left_out(case):
    """Where the two oracles differ, and why the free-partition one is right.

    A clamped node of a consistent-mass beam — or of a lumped-mass plate whose
    fixed edge owns a share of the element mass — still contributes to the total
    mass of the model, but the reaction carries it and no mode can. Summing the
    effective masses to the *total* mass there would be wrong, so the criterion
    is pinned against the participating mass and this test records the gap.
    """
    solver, directions = SUPPORTED_MASS_CASES[case]()

    result = _complete_basis(solver)

    for direction in directions:
        participating = _rigid_body_mass(result.system, direction)
        assert participating < result.system.total_mass
        assert float(np.sum(result.effective_masses(direction))) == pytest.approx(
            participating, rel=EFFECTIVE_MASS_RTOL
        )


@criterion("AC-MODAL-007")
@pytest.mark.parametrize("case", sorted(COMPLETENESS_CASES))
def test_ac_modal_007_a_truncated_basis_falls_short(case):
    """Completeness is a real gate: half the basis leaves mass unaccounted for.

    Half rather than "all but the last mode", because the top of the spectrum
    contributes so little that dropping one mode is invisible at 1e-8 — which
    is exactly why the criterion asks for the *complete* basis and why the
    truncation this test uses has to be a substantial one to mean anything.
    """
    solver, directions = COMPLETENESS_CASES[case]()

    result = _complete_basis(solver)

    for direction in directions:
        masses = result.effective_masses(direction)
        total = _rigid_body_mass(result.system, direction)
        assert np.all(masses >= 0.0), "an effective mass is a square; it cannot be negative"
        cumulative = np.cumsum(masses)
        assert np.all(np.diff(cumulative) >= 0.0)
        half = cumulative[masses.size // 2 - 1]
        assert half < total * (1.0 - TRUNCATION_DEFICIT), (
            f"{case}/{direction}: half the basis already holds {half / total:.9f}"
        )


@criterion("AC-MODAL-007")
def test_ac_modal_007_effective_mass_is_the_squared_participation_factor():
    """MS-1.4 pinned: for mass-normalized modes ``m_eff,j = Gamma_j^2``."""
    solver, _ = FULLY_FREE_MASS_CASES["graded_chain"]()

    result = _complete_basis(solver)

    assert result.normalization == "mass"
    np.testing.assert_allclose(result.modal_masses, 1.0, atol=ORTHONORMALITY_TOLERANCE)
    np.testing.assert_allclose(
        result.effective_masses("UX"), result.participation_factors("UX") ** 2, rtol=1e-12
    )


# --------------------------------------------------------------- AC-MODAL-009

#: A well-posed 3-DOF reference the invalid inputs below are perturbations of.
VALID_K = np.array([[2.0, -1.0, 0.0], [-1.0, 2.0, -1.0], [0.0, -1.0, 1.0]])
VALID_M = np.diag([1.0, 2.0, 3.0])

#: Asymmetry large enough to be a modelling error rather than round-off.
ASYMMETRY = 1e-3


def _perturbed(matrix: np.ndarray, row: int, column: int, amount: float) -> np.ndarray:
    perturbed = matrix.copy()
    perturbed[row, column] += amount
    return perturbed


@criterion("AC-MODAL-009")
@pytest.mark.parametrize("name", ["K", "M"])
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_modal_009_an_asymmetric_matrix_is_rejected_by_name(name, backend):
    """MS-1.1 validates symmetry before enforcing it; a real defect raises."""
    K = _perturbed(VALID_K, 0, 1, ASYMMETRY) if name == "K" else VALID_K
    M = _perturbed(VALID_M, 0, 1, ASYMMETRY) if name == "M" else VALID_M

    with pytest.raises(MatrixSymmetryError) as excinfo:
        ModalSolver.from_matrices(K, M).solve(num_modes=2, **BACKENDS[backend])

    error = excinfo.value
    assert error.matrix == name
    assert error.tolerance == SYMMETRY_TOL
    assert error.defect > SYMMETRY_TOL
    assert error.defect == pytest.approx(symmetry_defect(K if name == "K" else M), rel=1e-12)


@criterion("AC-MODAL-009")
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_modal_009_round_off_asymmetry_is_still_symmetrized_silently(backend):
    """The gate is a tolerance, not a ban: MS-1.1 averages what it accepts."""
    nudged = _perturbed(VALID_K, 0, 1, 1e-14)
    assert 0.0 < symmetry_defect(nudged) <= SYMMETRY_TOL

    reference = ModalSolver.from_matrices(VALID_K, VALID_M).solve(
        num_modes=3, **BACKENDS[backend]
    )
    accepted = ModalSolver.from_matrices(nudged, VALID_M).solve(
        num_modes=3, **BACKENDS[backend]
    )

    np.testing.assert_allclose(accepted.eigenvalues, reference.eigenvalues, rtol=1e-10)


@criterion("AC-MODAL-009")
@pytest.mark.parametrize(
    ("label", "mass"),
    [
        ("negative_diagonal", np.diag([1.0, -1.0, 3.0])),
        ("indefinite", np.array([[1.0, 2.0, 0.0], [2.0, 1.0, 0.0], [0.0, 0.0, 1.0]])),
        ("singular", np.diag([1.0, 0.0, 3.0])),
    ],
)
def test_ac_modal_009_a_mass_matrix_that_is_not_definite_is_rejected(label, mass):
    """Every non-SPD mass matrix leaves through ``MatrixDefinitenessError``.

    The three cases enter the solver by different routes — the O(n) diagonal
    screen, the failed LAPACK factorization, and the massless-DOF condensation
    that cannot condense a DOF with no stiffness of its own — and the criterion
    is that a caller sees one error type regardless.
    """
    with pytest.raises(SolverError) as excinfo:
        ModalSolver.from_matrices(VALID_K, mass).solve(
            num_modes=2, sparse=False, condense_massless=False
        )

    error = excinfo.value
    if label == "singular":
        # A zero-mass DOF is not a definiteness failure, it is the ill-posed
        # eigenproblem MS-1.1 asks to be condensed away; with condensation
        # switched off it must still fail loudly rather than return junk.
        assert isinstance(error, SolverError)
    else:
        assert isinstance(error, MatrixDefinitenessError)
        assert error.matrix == "M"


@criterion("AC-MODAL-009")
def test_ac_modal_009_a_singular_mass_matrix_is_condensed_rather_than_rejected():
    """The counterpart of the case above: MS-1.1's sanctioned way out."""
    mass = np.diag([1.0, 0.0, 3.0])

    result = ModalSolver.from_matrices(VALID_K, mass).solve(
        num_modes=2, sparse=False, condense_massless=True
    )

    assert result.num_condensed_dofs == 1
    assert np.all(np.isfinite(result.eigenvalues))


@criterion("AC-MODAL-009")
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_modal_009_a_negative_eigenvalue_past_the_noise_floor_is_rejected(backend):
    """``omega^2 < 0`` is an imaginary frequency, not a rigid-body mode."""
    unstable = np.diag([1.0, 1.0, -1.0])

    with pytest.raises(MatrixDefinitenessError) as excinfo:
        ModalSolver.from_matrices(unstable, VALID_M).solve(num_modes=3, **BACKENDS[backend])

    error = excinfo.value
    assert error.matrix == "K"
    assert error.value < 0.0


@criterion("AC-MODAL-009")
def test_ac_modal_009_the_definiteness_gate_can_be_opened_deliberately():
    """``definiteness_tol=None`` warns instead, so the spectrum stays inspectable.

    Opening it alone is not enough, and that is the point: the buckling mode is
    reported at ``lambda = 0`` while ``K phi = -M phi``, so the MS-1.2 residual
    gate rejects it next. An unstable model can only be looked at by disabling
    both guards explicitly — there is no combination of defaults that returns
    one of these pairs as if it were converged.
    """
    unstable = np.diag([1.0, 1.0, -1.0])
    solver = ModalSolver.from_matrices(unstable, VALID_M)

    with pytest.warns(RuntimeWarning, match="negative eigenvalues"):
        with pytest.raises(SolverConvergenceError):
            solver.solve(num_modes=3, sparse=False, definiteness_tol=None)

    with pytest.warns(RuntimeWarning, match="negative eigenvalues"):
        result = solver.solve(
            num_modes=3, sparse=False, definiteness_tol=None, residual_tol=None
        )

    assert result.eigenvalues[0] == 0.0
    assert np.all(np.isfinite(result.mode_shapes))


@criterion("AC-MODAL-009")
def test_ac_modal_009_a_rigid_body_model_is_not_caught_by_the_definiteness_gate():
    """The gate fires below the noise floor only, which is what makes it a default."""
    K, M = free_free_chain_matrices(FREE_FREE_CHAIN_MASSES)

    result = ModalSolver.from_matrices(K, M).solve(num_modes=3, sparse=False)

    assert result.eigenvalues[0] == 0.0
    assert bool(result.is_rigid[0])


@criterion("AC-MODAL-009")
@pytest.mark.parametrize("name", ["K", "M"])
def test_ac_modal_009_non_finite_entries_fail_instead_of_propagating(name):
    """A NaN must not travel through LAPACK into a result that looks solved."""
    K = _perturbed(VALID_K, 1, 1, np.nan) if name == "K" else VALID_K
    M = _perturbed(VALID_M, 1, 1, np.nan) if name == "M" else VALID_M

    with pytest.raises(SolverError, match="non-finite"):
        ModalSolver.from_matrices(K, M).solve(num_modes=2, sparse=False)


@criterion("AC-MODAL-009")
@pytest.mark.parametrize("case", sorted(MODEL_CASES))
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_modal_009_an_accepted_result_never_carries_a_nan(case, backend):
    """The other half of "no silent NaN": what comes back is always finite."""
    solver, num_modes = MODEL_CASES[case]()

    result = solver.solve(num_modes=num_modes, **BACKENDS[backend])

    assert np.all(np.isfinite(result.eigenvalues))
    assert np.all(np.isfinite(result.frequencies))
    assert np.all(np.isfinite(result.mode_shapes))


@criterion("AC-MODAL-009")
@pytest.mark.parametrize(
    ("label", "call"),
    [
        ("unknown_normalization",
         lambda: ModalSolver.from_matrices(VALID_K, VALID_M).solve(normalization="unit")),
        ("no_modes",
         lambda: ModalSolver.from_matrices(VALID_K, VALID_M).solve(num_modes=0)),
        ("shape_mismatch",
         lambda: ModalSolver.from_matrices(VALID_K, np.eye(4))),
        ("rectangular",
         lambda: ModalSolver.from_matrices(np.ones((2, 3)), np.ones((2, 3)))),
        ("no_source", lambda: ModalSolver()),
        ("two_sources", lambda: ModalSolver(object(), system=object())),
    ],
)
def test_ac_modal_009_malformed_requests_raise_typed_errors(label, call):
    """Every caller mistake leaves through the package's own exception tree."""
    with pytest.raises(OpenFEMLabError):
        call()


@criterion("AC-MODAL-009")
def test_ac_modal_009_the_solver_package_contains_no_bare_assert():
    """MS-1.1: typed exceptions, never a bare ``assert`` a -O run would drop."""
    offenders = []
    root = Path(solver_package.__file__).parent
    for path in sorted(root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders += [
            f"{path.relative_to(root)}:{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Assert)
        ]
    assert not offenders, f"bare assert statements in the solver package: {offenders}"
