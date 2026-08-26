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

MS-1.2 also lists ``lobpcg`` as an optional third backend. ``ModalSolver``
exposes the dense and shift-invert Lanczos paths today through its ``sparse``
switch; :data:`BACKENDS` picks up a ``backend`` keyword automatically if one
lands later, so the pairwise comparison extends without editing this suite.
"""

from __future__ import annotations

import inspect
from itertools import combinations
from typing import Any

import numpy as np
import pytest

from openfemlab import ModalSolver
from openfemlab.correlation import mac
from openfemlab.mesh.simple import beam_mesh, spring_mass_chain

from ._support import (
    SQUARE,
    STEEL,
    cantilever_frequencies,
    chain_eigenvalues_fixed_fixed,
    chain_eigenvalues_fixed_free,
    criterion,
    fixture_matrices,
    load_fixture,
    mass_orthonormality_error,
    relative_error,
)

#: Gates of AC-MODAL-001..003.
EIGENVALUE_RTOL = 1e-10
BEAM_TOLERANCE_PERCENT = 0.5
BACKEND_FREQUENCY_RTOL = 1e-8
BACKEND_MAC_TOLERANCE = 1e-10
ORTHONORMALITY_TOLERANCE = 1e-8

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
