"""Industrial sparse-scale acceptance gates (MS-1.6, GAP-13).

The 50k case is procedural so the gate stores O(n) data while exercising the
same :class:`openfemlab.ModalSolver` facade as a meshed/imported model.  A
class-level CSR/CSC tripwire follows ``tests.test_reduction.guarded_csr`` but
also catches format conversions made inside the solver.
"""

from __future__ import annotations

import time

import numpy as np
import pytest
import scipy.sparse as sp

from openfemlab import ModalSolver
from openfemlab.correlation import mac

from ._support import criterion, relative_error

INDUSTRIAL_DOFS = 50_000
INDUSTRIAL_MODES = 6
INDUSTRIAL_TIME_LIMIT_SECONDS = 120.0
REFERENCE_DOFS = 600
REFERENCE_MODES = 8
FREQUENCY_RTOL = 1e-8
MAC_MINIMUM = 0.999


def sparse_chain(
    n_dof: int,
    *,
    mass: float = 1.5,
    stiffness: float = 2500.0,
) -> tuple[sp.csr_matrix, sp.csr_matrix]:
    """Fixed-fixed uniform chain assembled directly into O(n) CSR storage."""
    off_diagonal = np.full(n_dof - 1, -stiffness)
    diagonal = np.full(n_dof, 2.0 * stiffness)
    stiffness_matrix = sp.diags(
        [off_diagonal, diagonal, off_diagonal],
        offsets=[-1, 0, 1],
        format="csr",
    )
    mass_matrix = sp.diags([np.full(n_dof, mass)], offsets=[0], format="csr")
    return stiffness_matrix, mass_matrix


def guarded_csr(matrix: sp.spmatrix, monkeypatch: pytest.MonkeyPatch) -> sp.csr_matrix:
    """Return CSR and reject dense materialization of any full-shape CSR/CSC.

    ``ModalSolver`` legitimately converts CSR to CSC for sparse LU, so guarding
    the two concrete classes catches the original operators and full-order
    derived matrices after that conversion.
    """
    guarded_shape = matrix.shape
    for matrix_type in (sp.csr_matrix, sp.csc_matrix):
        original = matrix_type.toarray

        def refuse_full_toarray(self, *args, _original=original, **kwargs):
            if self.shape == guarded_shape:
                raise AssertionError(f"a {self.shape} full-order operator was densified")
            return _original(self, *args, **kwargs)

        monkeypatch.setattr(matrix_type, "toarray", refuse_full_toarray)
    return sp.csr_matrix(matrix)


@criterion("AC-PERF-001")
def test_ac_perf_001_50k_sparse_modal_solve_never_densifies(monkeypatch):
    """Six modes of a 50k-DOF chain stay sparse and finish inside 120 seconds."""
    stiffness, mass = sparse_chain(INDUSTRIAL_DOFS)
    stiffness = guarded_csr(stiffness, monkeypatch)

    started = time.perf_counter()
    result = ModalSolver.from_matrices(stiffness, mass).solve(
        num_modes=INDUSTRIAL_MODES,
        sparse=True,
        cache_factorization=False,
    )
    elapsed = time.perf_counter() - started

    assert stiffness.nnz == 3 * INDUSTRIAL_DOFS - 2
    assert mass.nnz == INDUSTRIAL_DOFS
    assert result.mode_shapes.shape == (INDUSTRIAL_DOFS, INDUSTRIAL_MODES)
    assert np.all(np.isfinite(result.frequencies))
    assert np.all(np.diff(result.frequencies) > 0.0)
    assert elapsed <= INDUSTRIAL_TIME_LIMIT_SECONDS

    # Prove the tripwire was active during the solve, rather than merely
    # relying on successful completion of a problem whose dense copy is 20 GB.
    with pytest.raises(AssertionError, match="full-order operator was densified"):
        stiffness.toarray()


@criterion("AC-PERF-002")
def test_ac_perf_002_sparse_iterative_modes_match_dense_reference():
    """Sparse frequencies agree to 1e-8 relative and paired MAC is at least 0.999."""
    stiffness, mass = sparse_chain(REFERENCE_DOFS)
    dense = ModalSolver.from_matrices(stiffness, mass).solve(
        num_modes=REFERENCE_MODES,
        sparse=False,
    )
    iterative = ModalSolver.from_matrices(stiffness, mass).solve(
        num_modes=REFERENCE_MODES,
        sparse=True,
        cache_factorization=False,
    )

    assert np.max(relative_error(iterative.frequencies, dense.frequencies)) <= FREQUENCY_RTOL
    agreement = mac(iterative.mode_shapes, dense.mode_shapes)
    assert np.min(np.diag(agreement)) >= MAC_MINIMUM
    assert np.array_equal(np.argmax(agreement, axis=1), np.arange(REFERENCE_MODES))


MAC_LARGE_DOFS = 5_000
MAC_LARGE_MODES = 20
MAC_LARGE_TIME_LIMIT_SECONDS = 2.0
MAC_LARGE_SLOWDOWN_LIMIT = 5.0
MAC_TIMING_REPEATS = 5


def textbook_mac(shapes_a: np.ndarray, shapes_b: np.ndarray) -> np.ndarray:
    """``|Φ_aᵀ Φ_b|² / (‖φ_a‖² ‖φ_b‖²)`` written out, as the gate's oracle.

    Deliberately a second implementation rather than a call into the package:
    AC-PERF-003 asks whether the shipped dispatch still computes the MAC, so it
    must not be checked against the code whose dispatch is under test.
    """
    cross = shapes_a.T @ shapes_b
    norm_a = np.sum(shapes_a * shapes_a, axis=0)
    norm_b = np.sum(shapes_b * shapes_b, axis=0)
    return np.clip((cross * cross) / np.outer(norm_a, norm_b), 0.0, 1.0)


def fastest_seconds(call, repeats: int = MAC_TIMING_REPEATS) -> float:
    """Shortest of ``repeats`` timed runs, after one untimed warm-up.

    The warm-up keeps one-off costs — a Numba compilation, a first-touch page
    fault — out of a measurement that is about steady-state throughput, and
    taking the minimum rejects the upward noise of a shared CI runner.
    """
    call()
    return min(_timed(call) for _ in range(repeats))


def _timed(call) -> float:
    started = time.perf_counter()
    call()
    return time.perf_counter() - started


@criterion("AC-PERF-003")
def test_ac_perf_003_large_mac_stays_fast_and_matches_the_reference():
    """A 5000×20 MAC matches the oracle, fits in 2 s, and beats no-dispatch.

    The slowdown bound is the part with teeth. The wall-clock envelope only
    catches a hang: this correlation is milliseconds of arithmetic, so a
    kernel a hundred times slower than plain NumPy still lands inside 2 s. A
    ratio against the oracle is what actually holds the accelerated route to
    being an acceleration.
    """
    rng = np.random.default_rng(42)
    shapes_a = rng.standard_normal((MAC_LARGE_DOFS, MAC_LARGE_MODES))
    shapes_b = rng.standard_normal((MAC_LARGE_DOFS, MAC_LARGE_MODES))
    reference = textbook_mac(shapes_a, shapes_b)

    started = time.perf_counter()
    correlation = mac(shapes_a, shapes_b)
    cold_elapsed = time.perf_counter() - started

    assert cold_elapsed <= MAC_LARGE_TIME_LIMIT_SECONDS
    np.testing.assert_allclose(correlation, reference, rtol=0.0, atol=1e-10)

    shipped = fastest_seconds(lambda: mac(shapes_a, shapes_b))
    oracle = fastest_seconds(lambda: textbook_mac(shapes_a, shapes_b))
    assert shipped <= MAC_LARGE_SLOWDOWN_LIMIT * oracle, (
        f"mac() took {shipped * 1e3:.3f} ms against {oracle * 1e3:.3f} ms for the "
        f"same correlation written out — the dispatch is a pessimization"
    )
