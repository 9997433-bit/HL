"""M2 correlation acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 3).

Implemented here
----------------
- **AC-CORR-001** (property, MS-2.2) — weighted MAC self-identity: with mass
  weighting and mass-normalized shapes, ``max |MAC_M(Phi, Phi) - I| <= 1e-8``.
- **AC-CORR-002** (property, MS-2.2) — MAC scaling/sign invariance: scaling any
  column of either mode set by a nonzero real factor (negative included) moves
  no MAC entry by more than 1e-12.

Both criteria are checked on a diagonal mass matrix (the chain fixtures) and on
the consistent, fully populated mass matrix of the cantilever beam, so the
weighting path is exercised with a non-diagonal ``W`` as well.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab import ModalSolver
from openfemlab.correlation import automac, mac
from openfemlab.mesh.simple import beam_mesh

from ._support import (
    SQUARE,
    STEEL,
    criterion,
    fixture_matrices,
    load_fixture,
)

#: Gates of AC-CORR-001..002.
SELF_MAC_TOLERANCE = 1e-8
UNIT_DIAGONAL_TOLERANCE = 1e-15
INVARIANCE_TOLERANCE = 1e-12

#: Seeded scaling draws of AC-CORR-002; a criterion only counts if deterministic.
SCALING_SEED = 20260826
SCALING_DRAWS = 8


def _fixture_modes(name: str):
    """``(Phi, M)`` — every mass-normalized mode of a matrix fixture."""
    K, M = fixture_matrices(load_fixture(name))
    result = ModalSolver.from_matrices(K, M).solve(num_modes=K.shape[0], sparse=False)
    return result.mode_shapes, M


def _beam_modes(num_modes: int = 6):
    """``(Phi, M)`` of the cantilever beam: a non-diagonal consistent mass matrix."""
    beam = beam_mesh(1.0, 12, STEEL, SQUARE, support="cantilever")
    result = ModalSolver(beam).solve(num_modes=num_modes, sparse=False)
    return result.mode_shapes, result.system.M


MODE_SETS = {
    "two_dof_fixture": lambda: _fixture_modes("two_dof_analytic"),
    "ten_dof_fixture": lambda: _fixture_modes("ten_dof_chain"),
    "cantilever_beam": _beam_modes,
}


def _detuned_modes(scale: float = 1.35, num_modes: int = 6):
    """Modes of a locally stiffened chain: a non-trivial MAC against the fixture."""
    K, M = fixture_matrices(load_fixture("ten_dof_chain"))
    detuned = K.copy()
    detuned[:4, :4] *= scale
    result = ModalSolver.from_matrices(detuned, M).solve(num_modes=num_modes, sparse=False)
    return result.mode_shapes


# ---------------------------------------------------------------- AC-CORR-001


@criterion("AC-CORR-001")
@pytest.mark.parametrize("case", sorted(MODE_SETS))
def test_ac_corr_001_mass_weighted_self_mac_is_the_identity(case):
    """``MAC_M(Phi, Phi) = I`` for mass-normalized shapes (MS-2.2)."""
    shapes, mass = MODE_SETS[case]()

    weighted = automac(shapes, weights=mass)

    defect = np.max(np.abs(weighted - np.eye(shapes.shape[1])))
    assert defect <= SELF_MAC_TOLERANCE, f"{case}: weighted self-MAC defect {defect:.3e}"


@criterion("AC-CORR-001")
@pytest.mark.parametrize("case", sorted(MODE_SETS))
def test_ac_corr_001_unweighted_self_mac_has_a_unit_diagonal(case):
    """Unweighted ``MAC(phi_i, phi_i) = 1``, clipped so it can never exceed 1."""
    shapes, _ = MODE_SETS[case]()

    unweighted = automac(shapes)

    assert np.all(unweighted <= 1.0)
    assert np.all(unweighted >= 0.0)
    assert np.max(np.abs(np.diag(unweighted) - 1.0)) <= UNIT_DIAGONAL_TOLERANCE
    assert np.allclose(unweighted, unweighted.T, atol=UNIT_DIAGONAL_TOLERANCE)


@criterion("AC-CORR-001")
def test_ac_corr_001_mass_weighting_separates_modes_the_shapes_alone_do_not():
    """The weighted identity is a real gate: unweighted off-diagonals are not zero."""
    shapes, mass = _beam_modes()

    weighted = automac(shapes, weights=mass)
    unweighted = automac(shapes)

    off_diagonal = ~np.eye(shapes.shape[1], dtype=bool)
    assert np.max(np.abs(weighted[off_diagonal])) <= SELF_MAC_TOLERANCE
    assert np.max(unweighted[off_diagonal]) > 1e-3


# ---------------------------------------------------------------- AC-CORR-002


def _random_scalings(rng: np.random.Generator, count: int) -> np.ndarray:
    """Nonzero real factors spanning six decades, roughly half of them negative."""
    magnitudes = 10.0 ** rng.uniform(-3.0, 3.0, size=count)
    signs = rng.choice(np.array([-1.0, 1.0]), size=count)
    return magnitudes * signs


@criterion("AC-CORR-002")
@pytest.mark.parametrize("draw", range(SCALING_DRAWS))
def test_ac_corr_002_mac_is_invariant_to_column_scaling(draw):
    """Rescaling either mode set moves no MAC entry by more than 1e-12."""
    analysis, mass = _fixture_modes("ten_dof_chain")
    test = _detuned_modes()
    reference = mac(analysis, test)
    assert 0.0 < np.min(reference) and np.max(reference) < 1.0, "expected a non-trivial MAC"

    rng = np.random.default_rng(SCALING_SEED + draw)
    scaled_analysis = analysis * _random_scalings(rng, analysis.shape[1])
    scaled_test = test * _random_scalings(rng, test.shape[1])

    for label, pair in {
        "analysis": (scaled_analysis, test),
        "test": (analysis, scaled_test),
        "both": (scaled_analysis, scaled_test),
    }.items():
        deviation = np.max(np.abs(mac(*pair) - reference))
        assert deviation <= INVARIANCE_TOLERANCE, f"{label} scaling moved MAC by {deviation:.3e}"

    weighted_reference = mac(analysis, test, weights=mass)
    weighted_deviation = np.max(
        np.abs(mac(scaled_analysis, scaled_test, weights=mass) - weighted_reference)
    )
    assert weighted_deviation <= INVARIANCE_TOLERANCE


@criterion("AC-CORR-002")
def test_ac_corr_002_sign_flips_leave_the_mac_bitwise_unchanged():
    """Sign is not information: flipping columns is exact in floating point."""
    analysis, _ = _fixture_modes("ten_dof_chain")
    test = _detuned_modes()
    reference = mac(analysis, test)

    rng = np.random.default_rng(SCALING_SEED)
    flips_a = rng.choice(np.array([-1.0, 1.0]), size=analysis.shape[1])
    flips_b = rng.choice(np.array([-1.0, 1.0]), size=test.shape[1])

    assert np.array_equal(mac(analysis * flips_a, test * flips_b), reference)
