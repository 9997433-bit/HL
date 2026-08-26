"""M2 correlation acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 3).

Implemented here
----------------
- **AC-CORR-001** (property, MS-2.2) — weighted MAC self-identity: with mass
  weighting and mass-normalized shapes, ``max |MAC_M(Phi, Phi) - I| <= 1e-8``.
- **AC-CORR-002** (property, MS-2.2) — MAC scaling/sign invariance: scaling any
  column of either mode set by a nonzero real factor (negative included) moves
  no MAC entry by more than 1e-12.
- **AC-CORR-003** (twin, MS-2.3) — pairing recovers a known permutation of a
  test set that was permuted, sign-flipped and thinned on both sides, and never
  pairs a candidate below ``mac_min``.
- **AC-CORR-004** (twin, MS-2.5) — COMAC puts its minimum on the one sensor DOF
  a synthetic fault was injected into.

The first two criteria are checked on a diagonal mass matrix (the chain
fixtures) and on the consistent, fully populated mass matrix of the cantilever
beam, so the weighting path is exercised with a non-diagonal ``W`` as well.

Naming: the criteria document calls the model side "analysis"; the
implementation calls it "fe", so ``ModePairing.unpaired_fe`` is the
``unpaired_analysis`` of AC-CORR-003.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab import ModalSolver
from openfemlab.correlation import automac, comac, mac, pair_modes
from openfemlab.mesh.simple import beam_mesh

from ._support import (
    SQUARE,
    STEEL,
    criterion,
    fixture_matrices,
    load_fixture,
)

#: Gates of AC-CORR-001..004.
SELF_MAC_TOLERANCE = 1e-8
UNIT_DIAGONAL_TOLERANCE = 1e-15
INVARIANCE_TOLERANCE = 1e-12
MAC_MIN = 0.7
COMAC_HEALTHY = 0.99

#: Seeded scaling draws of AC-CORR-002; a criterion only counts if deterministic.
SCALING_SEED = 20260826
SCALING_DRAWS = 8

#: Seed of the twin experiments of AC-CORR-003/004.
TWIN_SEED = 5150


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


# ---------------------------------------------------------------- AC-CORR-003

#: Ground truth of the twin: test mode i is analysis mode ANALYSIS_OF[i],
#: measured with an arbitrary sign and scale. Analysis modes 2 and 7 were never
#: measured, and test mode 4 is a spurious pick-up correlated with nothing.
ANALYSIS_OF = {0: 5, 1: 0, 2: 9, 3: 3, 5: 8, 6: 1, 7: 6}
SPURIOUS_TEST_MODE = 4
UNMEASURED_ANALYSIS_MODES = [2, 4, 7]


def _pairing_twin(noise: float = 0.0):
    """``(analysis, test, frequencies)`` of the AC-CORR-003 twin experiment."""
    analysis, _ = _fixture_modes("ten_dof_chain")
    frequencies = np.sqrt(np.linalg.eigvalsh(fixture_matrices(load_fixture("ten_dof_chain"))[0]))
    frequencies = np.sort(frequencies) / (2.0 * np.pi)

    rng = np.random.default_rng(TWIN_SEED)
    columns = []
    test_frequencies = []
    for index in range(len(ANALYSIS_OF) + 1):
        if index == SPURIOUS_TEST_MODE:
            # A measurement that corresponds to no analysis mode at all: an
            # orthogonal direction, so its MAC against every column is ~0.
            columns.append(rng.standard_normal(analysis.shape[0]))
            test_frequencies.append(float(np.mean(frequencies)))
            continue
        source = ANALYSIS_OF[index]
        scale = rng.uniform(0.2, 5.0) * rng.choice([-1.0, 1.0])
        shape = analysis[:, source] * scale
        if noise:
            shape = shape + noise * np.linalg.norm(shape) * rng.standard_normal(shape.size)
        columns.append(shape)
        test_frequencies.append(float(frequencies[source]))
    return analysis, np.column_stack(columns), frequencies, np.array(test_frequencies)


@criterion("AC-CORR-003")
@pytest.mark.parametrize("method", ["greedy", "optimal"])
@pytest.mark.parametrize("noise", [0.0, 0.02])
def test_ac_corr_003_pairing_recovers_the_ground_truth_permutation(method, noise):
    """The known correspondence comes back exactly, dropped modes included."""
    analysis, test, fe_frequencies, test_frequencies = _pairing_twin(noise)

    pairing = pair_modes(
        test_shapes=test,
        fe_shapes=analysis,
        test_frequencies=test_frequencies,
        fe_frequencies=fe_frequencies,
        method=method,
        mac_threshold=MAC_MIN,
    )

    assert pairing.as_tuples() == sorted(ANALYSIS_OF.items())
    assert pairing.unpaired_test == [SPURIOUS_TEST_MODE]
    assert pairing.unpaired_fe == UNMEASURED_ANALYSIS_MODES
    assert np.min(pairing.mac_values) >= MAC_MIN


@criterion("AC-CORR-003")
def test_ac_corr_003_a_candidate_below_mac_min_is_reported_unpaired():
    """The threshold is the reason the spurious mode stays out of ``pairs``."""
    analysis, test, fe_frequencies, test_frequencies = _pairing_twin()

    unfiltered = pair_modes(
        test_shapes=test, fe_shapes=analysis, method="optimal", mac_threshold=0.0
    )
    filtered = pair_modes(
        test_shapes=test, fe_shapes=analysis, method="optimal", mac_threshold=MAC_MIN
    )

    # Without a threshold the assignment happily marries the spurious mode to
    # whatever is left over -- at a MAC no correlation report should accept.
    forced = {pair.test_index: pair.mac for pair in unfiltered.pairs}
    assert SPURIOUS_TEST_MODE in forced and forced[SPURIOUS_TEST_MODE] < MAC_MIN
    assert SPURIOUS_TEST_MODE not in {pair.test_index for pair in filtered.pairs}
    # Every genuine pair survives the threshold, so it rejects only the bad one.
    assert filtered.as_tuples() == sorted(ANALYSIS_OF.items())


@criterion("AC-CORR-003")
def test_ac_corr_003_pairing_ignores_measurement_sign_and_scale():
    """Rescaling the measured shapes cannot move a single pair."""
    analysis, test, fe_frequencies, test_frequencies = _pairing_twin()
    rng = np.random.default_rng(TWIN_SEED + 1)
    columns = test.shape[1]
    rescaled = test * (rng.uniform(0.1, 10.0, columns) * rng.choice([-1.0, 1.0], columns))

    reference = pair_modes(test_shapes=test, fe_shapes=analysis, mac_threshold=MAC_MIN)
    other = pair_modes(test_shapes=rescaled, fe_shapes=analysis, mac_threshold=MAC_MIN)

    assert other.as_tuples() == reference.as_tuples()


# ---------------------------------------------------------------- AC-CORR-004

#: Sensor the AC-CORR-004 fault is injected into, and the modes it corrupts.
FAULTY_DOF = 6
CORRUPTED_MODES = (0, 2, 4)
MAGNITUDE_ERROR = 1.5


def _sensor_fault(shapes: np.ndarray, factor, modes=CORRUPTED_MODES) -> np.ndarray:
    """Copy of ``shapes`` with one row scaled on a subset of the modes."""
    faulty = shapes.copy()
    faulty[FAULTY_DOF, list(modes)] *= factor
    return faulty


@criterion("AC-CORR-004")
@pytest.mark.parametrize("factor", [MAGNITUDE_ERROR, 1.0 / MAGNITUDE_ERROR])
def test_ac_corr_004_comac_localizes_a_faulty_sensor(factor):
    """A 50 % gain error on one channel is the argmin of COMAC; the rest stay 1."""
    analysis, _ = _fixture_modes("ten_dof_chain")
    analysis = analysis[:, :6]
    test = _sensor_fault(analysis, factor)

    values = comac(test, analysis)

    assert int(np.argmin(values)) == FAULTY_DOF
    healthy = np.delete(values, FAULTY_DOF)
    assert np.min(healthy) >= COMAC_HEALTHY
    assert values[FAULTY_DOF] < COMAC_HEALTHY, f"COMAC at the fault {values[FAULTY_DOF]:.4f}"


@criterion("AC-CORR-004")
def test_ac_corr_004_comac_localizes_a_noisy_channel_through_the_pairing():
    """Same verdict when the modes arrive shuffled and only the pairing links them."""
    analysis, _ = _fixture_modes("ten_dof_chain")
    analysis = analysis[:, :6]
    order = [3, 0, 5, 1, 4, 2]
    rng = np.random.default_rng(TWIN_SEED)
    test = analysis[:, order].copy()
    test[FAULTY_DOF, :] += 0.2 * np.linalg.norm(test[FAULTY_DOF, :]) * rng.standard_normal(6)

    pairing = pair_modes(test_shapes=test, fe_shapes=analysis, mac_threshold=MAC_MIN)
    values = comac(test, analysis, pairing)

    assert pairing.as_tuples() == list(enumerate(order))
    assert int(np.argmin(values)) == FAULTY_DOF
    assert np.min(np.delete(values, FAULTY_DOF)) >= COMAC_HEALTHY


@criterion("AC-CORR-004")
def test_ac_corr_004_a_reversed_polarity_channel_scores_a_perfect_comac():
    """The one fault AC-CORR-004 names that MS-2.5 provably cannot localize.

    MS-2.5 accumulates ``|phi_a(d) phi_e(d)|``, so the sign of a channel drops
    straight out of the numerator and the broken sensor scores exactly 1. What
    the flip does leave behind is a per-mode change in the modal scale factor,
    and COMAC is not invariant to that — it depresses every *other* DOF by
    ~2.7 %. A reversed cable therefore makes the argmin point at a healthy
    sensor, the exact opposite of the diagnosis. Localizing it needs the
    phase-aware eCOMAC that MS-2.5 lists as a P2 extension; the magnitude
    faults above are what the criterion can be met with today.
    """
    analysis, _ = _fixture_modes("ten_dof_chain")
    analysis = analysis[:, :6]

    values = comac(_sensor_fault(analysis, -1.0, range(analysis.shape[1])), analysis)

    assert values[FAULTY_DOF] == pytest.approx(1.0, rel=1e-12)
    assert int(np.argmax(values)) == FAULTY_DOF
    assert np.max(np.delete(values, FAULTY_DOF)) < COMAC_HEALTHY


@criterion("AC-CORR-004")
def test_ac_corr_004_a_polarity_error_on_some_modes_does_not_localize_either():
    """Flipping only a few modes does not rescue it: the fault stays hidden."""
    analysis, _ = _fixture_modes("ten_dof_chain")
    analysis = analysis[:, :6]

    values = comac(_sensor_fault(analysis, -1.0), analysis)

    healthy = np.delete(values, FAULTY_DOF)
    assert int(np.argmin(values)) != FAULTY_DOF
    # Worse than a miss: a healthy sensor scores lower, and the broken one sits
    # 0.06 % above it — inside the scatter the flip induced everywhere else.
    assert values[FAULTY_DOF] - np.min(healthy) < 1e-3
