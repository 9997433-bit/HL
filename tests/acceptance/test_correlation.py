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
- **AC-CORR-005** (oracle, MS-2.4) — a model stiffened by 1 % against the test
  article reports ``df = +0.4988 %`` on every pair, the closed-form
  ``100 (sqrt(1.01) - 1)``; the MS-2.4 formula ``100 (f_a - f_e) / f_e`` is
  pinned across every function that reports one.
- **AC-CORR-007** (property, MS-2.2) — MAC entries stay in ``[0, 1]`` for random
  real and complex mode sets, and the complex kernel is the Hermitian one:
  ``MAC(phi, psi) = MAC(conj(phi), conj(psi))`` and a global phase rotation
  leaves it unchanged.
- **AC-CORR-006** (twin, MS-2.1) — SEREP expansion of noise-free sensor data
  reproduces the full-space analysis shapes with MAC >= 0.999, and the pairing
  computed on the sensor DOFs equals the pairing computed after expansion.

The first two criteria are checked on a diagonal mass matrix (the chain
fixtures) and on the consistent, fully populated mass matrix of the cantilever
beam, so the weighting path is exercised with a non-diagonal ``W`` as well.

Naming: the criteria document calls the model side "analysis"; the
implementation calls it "fe", so ``ModePairing.unpaired_fe`` is the
``unpaired_analysis`` of AC-CORR-003.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from openfemlab import ModalSolver
from openfemlab.correlation import (
    automac,
    comac,
    correlation_summary,
    expand_shapes,
    frequency_difference,
    frequency_error_matrix,
    guyan_reduction,
    mac,
    mac_value,
    normalized_frequency_residual,
    pair_modes,
    relative_frequency_error,
    tam_mass,
)
from openfemlab.mesh.simple import beam_mesh

from ._support import (
    SQUARE,
    STEEL,
    criterion,
    dense,
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

#: AC-CORR-005: the stiffness factor between model and test article, and the
#: frequency error it must produce. ``omega ~ sqrt(k)``, so 1 % of stiffness is
#: 0.4988 % of frequency, not 1 % and not 0.5 %.
STIFFNESS_FACTOR = 1.01
FREQUENCY_ERROR_PCT = 100.0 * (math.sqrt(STIFFNESS_FACTOR) - 1.0)
FREQUENCY_ERROR_RTOL = 1e-10

#: AC-CORR-007 draws.
RANGE_SEED = 771
RANGE_DRAWS = 6
COMPLEX_TOLERANCE = 1e-12


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


# ---------------------------------------------------------------- AC-CORR-006

#: Modes the SEREP basis spans, and the sensor sets that must observe them.
SEREP_BAND = 4
CHAIN_SENSORS = (0, 2, 5, 7, 9)
BEAM_SENSOR_NODES = (2, 5, 8, 10, 12)

#: Ground truth of the reduction/expansion twin: test mode ``i`` is analysis
#: mode ``MEASURED_ORDER[i]``, recorded with an arbitrary sign and gain.
MEASURED_ORDER = (2, 0, 3, 1)

#: Reconstruction gate of AC-CORR-006 and the seed of its measurement draws.
EXPANSION_MAC_MIN = 0.999
EXPANSION_SEED = 96031

#: Noise floors of the robustness cases, as a fraction of each column's norm.
LIGHT_NOISE = 0.002
HEAVY_NOISE = 0.05
BREAKDOWN_NOISE = 0.08


def _chain_twin():
    """``(Phi, K, M, sensors)`` of the 10-DOF chain read by 5 of its 10 DOFs."""
    K, M = fixture_matrices(load_fixture("ten_dof_chain"))
    result = ModalSolver.from_matrices(K, M).solve(num_modes=K.shape[0], sparse=False)
    return result.mode_shapes[:, :SEREP_BAND], dense(K), dense(M), list(CHAIN_SENSORS)


def _beam_twin():
    """The same, for the cantilever, instrumented the way a rig actually is.

    Accelerometers see transverse translation only, so the rotational DOFs of
    every node and the axial DOFs are unmeasured — the under-instrumentation
    SEREP expansion exists for. Everything is expressed on the free partition
    so the clamped rows, which are identically zero and would make the Guyan
    slave block singular, stay out of the condensation.
    """
    beam = beam_mesh(1.0, 12, STEEL, SQUARE, support="cantilever")
    result = ModalSolver(beam).solve(num_modes=SEREP_BAND, sparse=False)
    system = result.system
    free = np.asarray(system.free_dofs)
    labels = list(system.dof_labels)
    sensors = [
        int(np.flatnonzero(free == labels.index(f"{node}:UY"))[0])
        for node in BEAM_SENSOR_NODES
    ]
    partition = np.ix_(free, free)
    return (
        result.mode_shapes[free, :SEREP_BAND],
        dense(system.K)[partition],
        dense(system.M)[partition],
        sensors,
    )


TWIN_MODELS = {"cantilever_beam": _beam_twin, "ten_dof_chain": _chain_twin}


def _measured(sensor_shapes: np.ndarray, num_modes: int = SEREP_BAND, noise: float = 0.0):
    """``(Phi_test, truth)`` — sensor-space test data extracted from the model.

    The columns are reordered by ``MEASURED_ORDER`` and given an arbitrary sign
    and gain, because a measurement carries neither the FE mode order nor the
    FE scaling. ``truth`` is the ``(test, analysis)`` correspondence both
    pairings have to recover.
    """
    rng = np.random.default_rng(EXPANSION_SEED)
    order = list(MEASURED_ORDER[:num_modes])
    scales = rng.uniform(0.2, 5.0, len(order)) * rng.choice([-1.0, 1.0], len(order))
    measured = sensor_shapes[:, order] * scales
    if noise:
        measured = measured + noise * np.linalg.norm(measured, axis=0) * rng.standard_normal(
            measured.shape
        )
    return measured, list(enumerate(order))


def _paired_mac(shapes: np.ndarray, analysis: np.ndarray, truth) -> np.ndarray:
    """MAC of each test shape against the analysis mode it is known to be."""
    values = mac(shapes, analysis)
    return np.array([values[test, fe] for test, fe in truth])


def _both_pairings(analysis, sensors, measured, method="optimal"):
    """The two pairings AC-CORR-006 requires to agree: reduced and expanded."""
    sensor_analysis = analysis[sensors, :]
    reduced = pair_modes(
        test_shapes=measured,
        fe_shapes=sensor_analysis,
        method=method,
        mac_threshold=MAC_MIN,
    )
    expanded = pair_modes(
        test_shapes=expand_shapes(analysis, sensors, measured),
        fe_shapes=analysis,
        method=method,
        mac_threshold=MAC_MIN,
    )
    return reduced, expanded


@criterion("AC-CORR-006")
@pytest.mark.parametrize("case", sorted(TWIN_MODELS))
def test_ac_corr_006_serep_expansion_reproduces_the_analysis_shapes(case):
    """Expanded test shapes correlate with their analysis modes at MAC >= 0.999."""
    analysis, _, _, sensors = TWIN_MODELS[case]()
    measured, truth = _measured(analysis[sensors, :])

    expanded = expand_shapes(analysis, sensors, measured)

    assert expanded.shape == analysis.shape
    worst = float(np.min(_paired_mac(expanded, analysis, truth)))
    assert worst >= EXPANSION_MAC_MIN, f"{case}: worst reconstruction MAC {worst:.6f}"


@criterion("AC-CORR-006")
@pytest.mark.parametrize("case", sorted(TWIN_MODELS))
def test_ac_corr_006_noise_free_in_band_data_is_reconstructed_exactly(case):
    """The gate has room to spare here: in-band data comes back to solver precision.

    ``T = Phi (Phi_s)^+`` is a left inverse of the sensor partition as long as
    that partition has full column rank, so the twin is not merely above the
    0.999 gate — it is exact, and the instrumented rows return their own values.
    """
    analysis, _, _, sensors = TWIN_MODELS[case]()
    measured, truth = _measured(analysis[sensors, :])

    expanded = expand_shapes(analysis, sensors, measured)

    np.testing.assert_allclose(expanded[sensors, :], measured, atol=1e-10)
    np.testing.assert_allclose(_paired_mac(expanded, analysis, truth), 1.0, atol=1e-12)


@criterion("AC-CORR-006")
@pytest.mark.parametrize("case", sorted(TWIN_MODELS))
@pytest.mark.parametrize("method", ["greedy", "optimal"])
def test_ac_corr_006_reduced_and_expanded_pairing_agree(case, method):
    """The MS-2.1 consistency requirement, stated for both assignment methods."""
    analysis, _, _, sensors = TWIN_MODELS[case]()
    measured, truth = _measured(analysis[sensors, :])

    reduced, expanded = _both_pairings(analysis, sensors, measured, method)

    assert reduced.as_tuples() == truth
    assert expanded.as_tuples() == reduced.as_tuples()
    assert reduced.unpaired_test == expanded.unpaired_test == []
    assert reduced.unpaired_fe == expanded.unpaired_fe == []


@criterion("AC-CORR-006")
@pytest.mark.parametrize("case", sorted(TWIN_MODELS))
def test_ac_corr_006_the_pairings_agree_about_an_unmeasured_mode(case):
    """Agreement covers what was *not* paired, not only the pairs themselves."""
    analysis, _, _, sensors = TWIN_MODELS[case]()
    measured, truth = _measured(analysis[sensors, :], num_modes=SEREP_BAND - 1)
    unmeasured = sorted(set(range(SEREP_BAND)) - {fe for _, fe in truth})

    reduced, expanded = _both_pairings(analysis, sensors, measured)

    assert reduced.as_tuples() == expanded.as_tuples() == truth
    assert reduced.unpaired_fe == expanded.unpaired_fe == unmeasured
    assert reduced.unpaired_test == expanded.unpaired_test == []


@criterion("AC-CORR-006")
@pytest.mark.parametrize("case", sorted(TWIN_MODELS))
def test_ac_corr_006_the_two_pairings_are_not_the_same_arithmetic(case):
    """The agreement above is a result, not an identity of the two computations.

    ``T`` is not orthogonal, so the MAC of the expanded shapes is genuinely a
    different matrix from the MAC of the sensor rows: the two differ by more
    than 0.1 somewhere, and the sensor-space matrix carries off-diagonals large
    enough that the assignment has something to get wrong. What the criterion
    asserts is that the assignment survives that difference.
    """
    analysis, _, _, sensors = TWIN_MODELS[case]()
    measured, truth = _measured(analysis[sensors, :])

    reduced_mac = mac(measured, analysis[sensors, :])
    expanded_mac = mac(expand_shapes(analysis, sensors, measured), analysis)

    assert np.max(np.abs(reduced_mac - expanded_mac)) > 0.1
    off_diagonal = reduced_mac.copy()
    for test_index, fe_index in truth:
        off_diagonal[test_index, fe_index] = 0.0
    assert np.max(off_diagonal) > 0.1, "the reduced-space MAC must be ambiguous enough to matter"


@criterion("AC-CORR-006")
@pytest.mark.parametrize("case", sorted(TWIN_MODELS))
def test_ac_corr_006_the_guyan_tam_weighted_pairing_agrees_as_well(case):
    """MS-2.1's other reduced-space route: mass-weighted MAC on the Guyan TAM."""
    analysis, K, M, sensors = TWIN_MODELS[case]()
    measured, truth = _measured(analysis[sensors, :])

    tam = tam_mass(guyan_reduction(K, sensors), M)
    weighted = pair_modes(
        test_shapes=measured,
        fe_shapes=analysis[sensors, :],
        weights=tam,
        method="optimal",
        mac_threshold=MAC_MIN,
    )

    assert np.all(np.linalg.eigvalsh(tam) > 0.0), "the TAM mass must stay positive definite"
    assert weighted.as_tuples() == truth


@criterion("AC-CORR-006")
@pytest.mark.parametrize("case", sorted(TWIN_MODELS))
def test_ac_corr_006_agreement_survives_a_light_measurement_noise_floor(case):
    """0.2 % noise per channel: both pairings hold and the gate still passes."""
    analysis, _, _, sensors = TWIN_MODELS[case]()
    measured, truth = _measured(analysis[sensors, :], noise=LIGHT_NOISE)

    reduced, expanded = _both_pairings(analysis, sensors, measured)
    worst = float(np.min(_paired_mac(expand_shapes(analysis, sensors, measured), analysis, truth)))

    assert reduced.as_tuples() == expanded.as_tuples() == truth
    assert worst >= EXPANSION_MAC_MIN, f"{case}: worst reconstruction MAC {worst:.6f}"


@criterion("AC-CORR-006")
@pytest.mark.parametrize("case", sorted(TWIN_MODELS))
def test_ac_corr_006_noise_breaks_the_reconstruction_gate_before_the_pairing(case):
    """What the 0.999 gate measures, and what it does not.

    At 5 % noise the expansion no longer reconstructs the analysis shapes to
    0.999 — SEREP projects the noise onto the retained band rather than
    rejecting it — yet the assignment is nowhere near ambiguous and the two
    pairings still agree. The gate is a reconstruction-fidelity requirement;
    pairing consistency is the separate, more robust half of AC-CORR-006, and
    reading a passing gate as "the pairing is safe" would overstate it.
    """
    analysis, _, _, sensors = TWIN_MODELS[case]()
    measured, truth = _measured(analysis[sensors, :], noise=HEAVY_NOISE)

    reduced, expanded = _both_pairings(analysis, sensors, measured)
    worst = float(np.min(_paired_mac(expand_shapes(analysis, sensors, measured), analysis, truth)))

    assert reduced.as_tuples() == expanded.as_tuples() == truth
    assert worst < EXPANSION_MAC_MIN, f"{case}: noise left the gate intact at {worst:.6f}"
    assert worst > 0.8, f"{case}: the modes stopped being recognizable at {worst:.6f}"


@criterion("AC-CORR-006")
def test_ac_corr_006_far_past_the_gate_the_expanded_pairing_is_the_stricter_one():
    """The "noise-free" in the criterion's wording is a real qualifier.

    At 8 % channel noise on the beam the two pairings stop agreeing — not by
    crossing wires, but because expansion spreads one corrupted channel over
    all 36 DOFs while the sensor-space MAC only ever sees the 5 that were
    measured. The expanded pairing therefore drops its worst mode below
    ``mac_min`` where the reduced one still accepts it, and every pair the two
    do make is still the same. The disagreement is about acceptance, not about
    correspondence, and the conservative side is the expanded one; it is
    recorded here so the equality asserted above is not read as unconditional.
    """
    analysis, _, _, sensors = TWIN_MODELS["cantilever_beam"]()
    measured, truth = _measured(analysis[sensors, :], noise=BREAKDOWN_NOISE)

    reduced, expanded = _both_pairings(analysis, sensors, measured)

    assert reduced.as_tuples() == truth
    assert set(expanded.as_tuples()) < set(reduced.as_tuples())
    assert expanded.unpaired_fe and not reduced.unpaired_fe


# ---------------------------------------------------------------- AC-CORR-005

#: Modes compared in the frequency-error twin.
FREQUENCY_MODES = 6


def _scaled_chain(stiffness_factor: float = 1.0, mass_factor: float = 1.0):
    """``(frequencies, shapes)`` of the fixture chain with scaled ``K``/``M``.

    Scaling either matrix globally leaves every mode shape untouched and moves
    the whole spectrum by a known factor, so the pairing is unambiguous and the
    frequency error is a closed form rather than a fitted number.
    """
    K, M = fixture_matrices(load_fixture("ten_dof_chain"))
    result = ModalSolver.from_matrices(stiffness_factor * K, mass_factor * M).solve(
        num_modes=FREQUENCY_MODES, sparse=False
    )
    return result.frequencies, result.mode_shapes


def _ms_2_4_formula(analysis, test) -> np.ndarray:
    """``100 (f_a - f_e) / f_e`` written out, so the convention is in the test."""
    return 100.0 * (np.asarray(analysis) - np.asarray(test)) / np.asarray(test)


def _stiffened_pairing():
    """The AC-CORR-005 twin: identical shapes, spectra a stiffness factor apart."""
    test_frequencies, shapes = _scaled_chain()
    analysis_frequencies, _ = _scaled_chain(stiffness_factor=STIFFNESS_FACTOR)
    pairing = pair_modes(
        test_shapes=shapes,
        fe_shapes=shapes,
        test_frequencies=test_frequencies,
        fe_frequencies=analysis_frequencies,
        mac_threshold=MAC_MIN,
    )
    return test_frequencies, analysis_frequencies, pairing


@criterion("AC-CORR-005")
def test_ac_corr_005_a_stiffer_model_reports_a_positive_frequency_error():
    """A model 1 % stiffer than the test article is +0.4988 % on every pair."""
    _, _, pairing = _stiffened_pairing()

    assert pairing.as_tuples() == [(index, index) for index in range(FREQUENCY_MODES)]
    errors = pairing.frequency_errors_pct
    assert np.all(errors > 0.0), "a stiffer model must report a positive error"
    np.testing.assert_allclose(errors, FREQUENCY_ERROR_PCT, rtol=FREQUENCY_ERROR_RTOL)


@criterion("AC-CORR-005")
@pytest.mark.parametrize(
    ("label", "kwargs", "sign"),
    [
        ("stiffer", {"stiffness_factor": STIFFNESS_FACTOR}, +1.0),
        ("softer", {"stiffness_factor": 1.0 / STIFFNESS_FACTOR}, -1.0),
        ("lighter", {"mass_factor": 1.0 / STIFFNESS_FACTOR}, +1.0),
        ("heavier", {"mass_factor": STIFFNESS_FACTOR}, -1.0),
    ],
)
def test_ac_corr_005_the_sign_says_stiffer_or_lighter(label, kwargs, sign):
    """MS-2.4's reading of the sign, on all four ways to move the spectrum.

    "Positive means the model is stiffer *or lighter* than the test article", so
    a 1 % mass reduction has to read exactly like a 1 % stiffness increase —
    which is also why a frequency error on its own can never say which of the
    two a model got wrong.
    """
    test_frequencies, _ = _scaled_chain()
    analysis_frequencies, _ = _scaled_chain(**kwargs)

    errors = _ms_2_4_formula(analysis_frequencies, test_frequencies)

    assert np.all(np.sign(errors) == sign), f"{label}: {errors}"
    np.testing.assert_allclose(np.abs(errors), abs(FREQUENCY_ERROR_PCT), rtol=1e-2)


@criterion("AC-CORR-005")
def test_ac_corr_005_every_reporting_path_uses_the_same_formula():
    """One convention, six entry points: pair, metrics, matrix, residual, summary."""
    test_frequencies, analysis_frequencies, pairing = _stiffened_pairing()
    expected = _ms_2_4_formula(analysis_frequencies, test_frequencies)
    summary = correlation_summary(pairing=pairing)

    np.testing.assert_allclose(pairing.frequency_errors_pct, expected, rtol=1e-12)
    np.testing.assert_allclose(
        100.0 * relative_frequency_error(test_frequencies, analysis_frequencies),
        expected,
        rtol=1e-12,
    )
    np.testing.assert_allclose(
        frequency_difference(test_frequencies, analysis_frequencies).percent,
        expected,
        rtol=1e-12,
    )
    np.testing.assert_allclose(
        np.diag(frequency_error_matrix(test_frequencies, analysis_frequencies)),
        expected,
        rtol=1e-12,
    )
    np.testing.assert_allclose(
        100.0 * normalized_frequency_residual(test_frequencies, analysis_frequencies, pairing),
        expected,
        rtol=1e-12,
    )
    assert summary.mean_signed_freq_error_pct == pytest.approx(
        float(np.mean(expected)), rel=1e-12
    )
    assert summary.max_abs_freq_error_pct == pytest.approx(
        float(np.max(np.abs(expected))), rel=1e-12
    )


@criterion("AC-CORR-005")
def test_ac_corr_005_the_test_frequency_is_the_denominator():
    """Swapping the roles is a different number, so the convention is load bearing.

    ``100 (f_a - f_e) / f_e`` and ``100 (f_e - f_a) / f_a`` differ by more than
    a sign: at this 0.5 % level the magnitudes are 0.0025 percentage points
    apart, small enough to go unnoticed and large enough to matter against the
    0.1 % gate the updating criteria use.
    """
    test_frequencies, analysis_frequencies, _ = _stiffened_pairing()

    forward = _ms_2_4_formula(analysis_frequencies, test_frequencies)
    reversed_roles = _ms_2_4_formula(test_frequencies, analysis_frequencies)

    np.testing.assert_allclose(
        forward,
        100.0 * relative_frequency_error(test_frequencies, analysis_frequencies),
        rtol=1e-12,
    )
    assert np.all(np.abs(forward) > np.abs(reversed_roles))
    assert np.all(np.abs(forward + reversed_roles) > 1e-6)


@criterion("AC-CORR-005")
def test_ac_corr_005_a_rigid_body_reference_reports_infinity_not_a_nan():
    """``f_e = 0`` has no relative error, and the formula has to say so out loud."""
    errors = relative_frequency_error([0.0, 2.0], [1.0, 2.02])

    assert errors[0] == np.inf
    assert errors[1] == pytest.approx(0.01, rel=1e-12)
    assert not np.any(np.isnan(errors))
    assert relative_frequency_error([0.0], [0.0])[0] == 0.0


# ---------------------------------------------------------------- AC-CORR-007


def _random_shapes(rng: np.random.Generator, ndof: int, modes: int, complex_valued: bool):
    shapes = rng.standard_normal((ndof, modes))
    if complex_valued:
        shapes = shapes + 1j * rng.standard_normal((ndof, modes))
    return shapes


@criterion("AC-CORR-007")
@pytest.mark.parametrize("complex_valued", [False, True])
@pytest.mark.parametrize("draw", range(RANGE_DRAWS))
def test_ac_corr_007_every_mac_entry_lies_in_the_unit_interval(complex_valued, draw):
    """Real or complex, weighted or not, the output is a real score in [0, 1]."""
    rng = np.random.default_rng(RANGE_SEED + draw)
    a = _random_shapes(rng, 12, 5, complex_valued)
    b = _random_shapes(rng, 12, 7, complex_valued)
    weights = rng.uniform(0.1, 10.0, 12)

    for label, values in {
        "unweighted": mac(a, b),
        "weighted": mac(a, b, weights=weights),
        "self": mac(a, a),
    }.items():
        assert np.isrealobj(values) and values.dtype == np.float64, label
        assert np.all(values >= 0.0) and np.all(values <= 1.0), label
        assert not np.any(np.isnan(values)), label

    np.testing.assert_allclose(np.diag(mac(a, a)), 1.0, atol=UNIT_DIAGONAL_TOLERANCE)


@criterion("AC-CORR-007")
@pytest.mark.parametrize("draw", range(RANGE_DRAWS))
def test_ac_corr_007_the_complex_kernel_is_hermitian(draw):
    """``MAC(phi, psi) = MAC(conj(phi), conj(psi))`` — the MS-2.2 identity."""
    rng = np.random.default_rng(RANGE_SEED + 100 + draw)
    a = _random_shapes(rng, 10, 4, complex_valued=True)
    b = _random_shapes(rng, 10, 4, complex_valued=True)

    reference = mac(a, b)

    np.testing.assert_allclose(mac(a.conj(), b.conj()), reference, atol=COMPLEX_TOLERANCE)
    # Conjugating one side only is a different operation, so the identity above
    # is a statement about the Hermitian transpose and not a tautology.
    assert np.max(np.abs(mac(a.conj(), b) - reference)) > COMPLEX_TOLERANCE


@criterion("AC-CORR-007")
@pytest.mark.parametrize("draw", range(RANGE_DRAWS))
def test_ac_corr_007_a_complex_shape_carries_no_usable_phase(draw):
    """Multiplying either set by ``exp(i theta)`` leaves every entry put.

    The complex counterpart of the real scaling invariance of AC-CORR-002: an
    experimental shape arrives with an arbitrary global phase, so a metric that
    moved with it could not compare two measurements of the same mode.
    """
    rng = np.random.default_rng(RANGE_SEED + 200 + draw)
    a = _random_shapes(rng, 10, 4, complex_valued=True)
    b = _random_shapes(rng, 10, 4, complex_valued=True)
    reference = mac(a, b)

    factors = rng.uniform(0.1, 10.0, 4) * np.exp(1j * rng.uniform(0.0, 2.0 * np.pi, 4))

    np.testing.assert_allclose(mac(a * factors, b), reference, atol=COMPLEX_TOLERANCE)
    np.testing.assert_allclose(mac(a, b * factors), reference, atol=COMPLEX_TOLERANCE)


@criterion("AC-CORR-007")
def test_ac_corr_007_a_real_shape_read_as_complex_gives_the_same_mac():
    """The complex path is a generalization, not a second implementation."""
    analysis, _ = _fixture_modes("ten_dof_chain")
    test = _detuned_modes()

    real = mac(analysis, test)
    promoted = mac(analysis.astype(complex), test.astype(complex))

    np.testing.assert_allclose(promoted, real, atol=COMPLEX_TOLERANCE)
    assert np.isrealobj(promoted)


@criterion("AC-CORR-007")
def test_ac_corr_007_a_quadrature_component_lands_strictly_inside_the_range():
    """A worked complex case, so the range gate is not met by trivial inputs.

    Adding an out-of-phase component orthogonal to the reference costs exactly
    the fraction of the energy that component carries, which puts the value in
    the open interval rather than at either end.
    """
    analysis, _ = _fixture_modes("ten_dof_chain")
    real_mode = analysis[:, 0]
    quadrature = analysis[:, 3]
    assert abs(float(real_mode @ quadrature)) < 1e-12, "the two modes must be orthogonal"

    value = mac_value(real_mode, real_mode + 0.5j * quadrature)

    energy = 1.0 / (1.0 + 0.25 * float(quadrature @ quadrature) / float(real_mode @ real_mode))
    assert 0.0 < value < 1.0
    assert value == pytest.approx(energy, rel=1e-12)


@criterion("AC-CORR-007")
def test_ac_corr_007_a_zero_norm_shape_is_rejected_rather_than_clipped():
    """Clipping into [0, 1] must not turn a 0/0 into a plausible-looking score."""
    analysis, _ = _fixture_modes("ten_dof_chain")
    degenerate = analysis.copy()
    degenerate[:, 0] = 0.0

    with pytest.raises(ValueError, match="zero-norm"):
        mac(degenerate, analysis)
