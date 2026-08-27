"""M9 modal-parameter-extraction acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 10).

Implemented here
----------------
- **AC-MPE-001** (oracle, MS-10.2) — the LSCF / poly-reference fit recovers the
  frequencies and damping ratios of a synthesized three-mode receptance, and the
  physicality filter leaves nothing else inside the band.
- **AC-MPE-002** (twin, MS-10.4) — with those poles frozen, LSFD recovers the
  source mode shapes, resynthesizes the input, and reproduces the source residues
  in unity-modal-A scaling; without a driving point the degradation is flagged.
- **AC-MPE-003** (property, MS-10.3) — over a range of model orders the physical
  poles form fully stable alignments, computational poles do not, the automatic
  pick returns the ground-truth mode count, and tightening a tolerance never
  promotes a pole to a more stable label.
- **AC-MPE-004** (contract, MS-10.5) — a synthesized FRF set written as dataset-58
  records is read back, fitted, bridged through ``to_test_data`` and correlated
  against the source model; the typed failures of MS-10.5 are raised.
- **AC-MPE-005** (property, MS-10.2/MS-10.3) — under seeded 1 % multiplicative
  noise the estimates degrade gracefully, and two runs on the same seeded input
  are bitwise identical.

The oracle throughout is the ``ten_dof_chain`` fixture: proportional (Rayleigh)
damping makes the ground-truth ``f_r``/``zeta_r`` closed-form, and ``modal_frf``
(MS-7.3) synthesizes the receptance the estimator must invert. Retaining only the
first three modes gives an FRF whose exact modal content is known; the full
ten-mode synthesis adds the out-of-band content the stabilization diagram and the
residual terms have to cope with.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pytest

from openfemlab import ModalSolver
from openfemlab.core.dofs import DofMap, DofType
from openfemlab.correlation import correlate, mac
from openfemlab.exceptions import MPEError
from openfemlab.io import format_uff
from openfemlab.io.uff import UFFFunction, read_uff_functions
from openfemlab.mpe import extract_modes, extract_shapes, fit_lscf, stabilization_diagram
from openfemlab.mpe.lscf import MAX_DAMPING_RATIO
from openfemlab.mpe.types import POLE_LABELS
from openfemlab.solver.dynamics import (
    FrequencyResponse,
    RayleighDamping,
    complex_modes,
    modal_frf,
)

from ._support import criterion, fixture_matrices, load_fixture

#: Gates of AC-MPE-001 (noise-free pole recovery).
FREQUENCY_TOLERANCE = 1e-6
DAMPING_TOLERANCE = 1e-4

#: Gates of AC-MPE-002 (shape recovery and resynthesis quality).
SHAPE_MAC_GATE = 0.999
FRAC_GATE = 0.999

#: Gate of AC-MPE-004 (the measurement path pairs against the source model).
PIPELINE_MAC_GATE = 0.99

#: Gates of AC-MPE-005 (seeded 1 % noise).
NOISE_LEVEL = 0.01
NOISE_FREQUENCY_GATE = 0.001
NOISE_DAMPING_GATE = 0.20
NOISE_MAC_GATE = 0.98

#: Seeded draws; a criterion only counts if its test is deterministic.
SEED = 20260826

#: Modes retained in the "exact" synthesis, i.e. the ground-truth count.
NUM_MODES = 3

#: Response channels and references of the simulated campaign. DOF 0 is both,
#: so the channel set contains a driving point (MS-10.4 scaling).
SENSORS = (0, 2, 4, 6, 8)
REFERENCES = (0, 6)

#: Sensors that observe no reference, used for the no-driving-point case.
OFF_DRIVE_SENSORS = (1, 3, 5, 7)

#: Damping ratios the Rayleigh model is anchored on at the band edges.
LOW_RATIO, HIGH_RATIO = 0.012, 0.008

#: Model orders the stabilization diagram spans (the true count is 3).
ORDERS = tuple(range(2, 17))


@lru_cache(maxsize=1)
def _model():
    """``(modes, damping)`` of the damped ten-DOF chain oracle."""
    K, M = fixture_matrices(load_fixture("ten_dof_chain"))
    modes = ModalSolver.from_matrices(K, M).solve(num_modes=K.shape[0], sparse=False)
    damping = RayleighDamping.from_frequencies(
        modes.frequencies[0], modes.frequencies[NUM_MODES - 1], LOW_RATIO, HIGH_RATIO
    )
    return K, M, modes, damping


def _truth() -> tuple[np.ndarray, np.ndarray]:
    """Closed-form ``(f_r, zeta_r)`` of the retained modes."""
    _, _, modes, damping = _model()
    return (
        modes.frequencies[:NUM_MODES],
        damping.damping_ratios(modes.angular_frequencies[:NUM_MODES]),
    )


def _band() -> tuple[float, float]:
    """Estimation band, generous around the three retained modes."""
    frequencies, _ = _truth()
    return float(0.5 * frequencies[0]), float(1.25 * frequencies[-1])


def _line() -> np.ndarray:
    """Measured frequency line: the band plus the tail that anchors ``dt``."""
    frequencies, _ = _truth()
    return np.linspace(0.002, 5.0 * frequencies[-1], 320)


def _synthesized(
    *,
    sensors: tuple[int, ...] = SENSORS,
    references: tuple[int, ...] = REFERENCES,
    truncated: bool = True,
) -> FrequencyResponse:
    """Receptance of the oracle over :func:`_line`.

    ``truncated`` keeps only the three modes the gates know the answer for;
    the full synthesis adds the out-of-band content of the other seven.
    """
    _, _, modes, damping = _model()
    return modal_frf(
        _line(),
        modes,
        damping,
        num_modes=NUM_MODES if truncated else None,
        response_dofs=list(sensors),
        excitation_dofs=list(references),
    )


def _source_shapes(sensors: tuple[int, ...] = SENSORS) -> np.ndarray:
    """Source mode shapes restricted to the response channels."""
    _, _, modes, _ = _model()
    return modes.mode_shapes[np.ix_(list(sensors), range(NUM_MODES))]


def _sorted_estimates(poles) -> tuple[np.ndarray, np.ndarray]:
    """``(frequencies, damping ratios)`` of a pole tuple, ascending."""
    frequencies = np.array([pole.frequency_hz for pole in poles], dtype=float)
    ratios = np.array([pole.damping_ratio for pole in poles], dtype=float)
    order = np.argsort(frequencies)
    return frequencies[order], ratios[order]


def _relative(actual: np.ndarray, expected: np.ndarray) -> float:
    """Worst per-entry relative error — the form the per-mode gates are written in."""
    return float(np.max(np.abs(actual - expected) / np.abs(expected)))


def _block_error(actual: np.ndarray, expected: np.ndarray) -> float:
    """``max |actual - expected| / max |expected|`` over a matrix with node lines."""
    return float(np.max(np.abs(actual - expected)) / np.max(np.abs(expected)))


# --------------------------------------------------------------- AC-MPE-001


@criterion("AC-MPE-001")
def test_lscf_recovers_the_poles_of_a_synthesized_receptance() -> None:
    """Noise-free oracle: the fit reproduces the closed-form ``f_r`` and ``zeta_r``."""
    response = _synthesized()
    frequencies, ratios = _truth()

    poles = fit_lscf(response, 6, band=_band())
    assert len(poles) == NUM_MODES, [pole.frequency_hz for pole in poles]

    found_f, found_zeta = _sorted_estimates(poles)
    assert _relative(found_f, frequencies) <= FREQUENCY_TOLERANCE
    assert _relative(found_zeta, ratios) <= DAMPING_TOLERANCE

    # The poly-reference denominator carries one participation column per
    # reference, and the poles are the continuous-time roots MS-10.2 defines.
    for pole in poles:
        assert pole.participation.shape == (len(REFERENCES),)
        expected = -pole.damping_ratio * abs(pole.pole)
        assert pole.pole.real == pytest.approx(expected, rel=1e-12)


@criterion("AC-MPE-001")
def test_the_physicality_filter_leaves_no_spurious_in_band_pole() -> None:
    """Over-ordered fits gain accuracy, not extra in-band poles."""
    response = _synthesized()
    frequencies, ratios = _truth()
    low, high = _band()

    for order in (4, 8, 12):
        poles = fit_lscf(response, order, band=(low, high))
        assert len(poles) == NUM_MODES, (order, [p.frequency_hz for p in poles])
        found_f, found_zeta = _sorted_estimates(poles)
        assert _relative(found_f, frequencies) <= FREQUENCY_TOLERANCE
        assert _relative(found_zeta, ratios) <= DAMPING_TOLERANCE
        for pole in poles:
            assert low <= pole.frequency_hz <= high
            assert 0.0 < pole.damping_ratio <= MAX_DAMPING_RATIO
            assert pole.pole.real < 0.0 < pole.pole.imag


@criterion("AC-MPE-001")
def test_the_single_reference_path_is_the_same_kernel() -> None:
    """One reference degenerates the matrix denominator to a scalar one (GAP-01)."""
    response = _synthesized(references=(0,))
    frequencies, ratios = _truth()

    poles = fit_lscf(response, 10, band=_band())
    assert len(poles) == NUM_MODES
    found_f, found_zeta = _sorted_estimates(poles)
    assert _relative(found_f, frequencies) <= FREQUENCY_TOLERANCE
    assert _relative(found_zeta, ratios) <= DAMPING_TOLERANCE
    assert all(pole.participation.shape == (1,) for pole in poles)


# --------------------------------------------------------------- AC-MPE-002


@criterion("AC-MPE-002")
def test_lsfd_recovers_the_source_shapes_and_resynthesizes_the_input() -> None:
    """Shape MAC and per-channel resynthesis FRAC against the synthesized FRF."""
    response = _synthesized()
    result = extract_shapes(response, fit_lscf(response, 6, band=_band()), band=_band())

    assert result.shapes.shape == (len(SENSORS), NUM_MODES)
    assert result.participation.shape == (len(REFERENCES), NUM_MODES)
    assert np.min(np.diag(mac(result.shapes, _source_shapes()))) >= SHAPE_MAC_GATE
    assert result.frac.shape == (len(SENSORS),)
    assert np.min(result.frac) >= FRAC_GATE


@criterion("AC-MPE-002")
def test_unity_modal_a_scaling_reproduces_the_source_residues() -> None:
    """With a driving point the residue numerator comes back as ``psi psi^T``.

    The oracle is the MS-7.2 residue convention itself: ``complex_modes`` with
    unit modal-A normalization makes the source residue of mode ``r`` exactly
    ``phi_r phi_r^T``, so the extracted shapes must square to the same matrix.
    """
    K, M, _, damping = _model()
    response = _synthesized()
    result = extract_shapes(response, fit_lscf(response, 8, band=_band()), band=_band())
    assert result.diagnostics["scaling"] == "unity-modal-A"
    assert result.diagnostics["drive_point"] == SENSORS[0]

    source = complex_modes(
        K, M, damping.matrix(K, M), num_modes=NUM_MODES, normalization="state"
    ).mode_shapes[list(SENSORS), :]
    for index in range(NUM_MODES):
        extracted = np.outer(result.shapes[:, index], result.shapes[:, index])
        expected = np.outer(source[:, index], source[:, index])
        assert _block_error(extracted, expected) <= 1e-4


@criterion("AC-MPE-002")
def test_without_a_driving_point_the_scaling_is_flagged_as_arbitrary() -> None:
    """A degradation the result declares, rather than a silently wrong scale."""
    response = _synthesized(sensors=OFF_DRIVE_SENSORS)
    result = extract_shapes(response, fit_lscf(response, 6, band=_band()), band=_band())

    assert result.diagnostics["scaling"] == "arbitrary"
    assert result.diagnostics["drive_point"] is None
    assert np.max(np.abs(result.shapes)) == pytest.approx(1.0, abs=1e-12)
    assert np.min(result.frac) >= FRAC_GATE
    assert (
        np.min(np.diag(mac(result.shapes, _source_shapes(OFF_DRIVE_SENSORS))))
        >= SHAPE_MAC_GATE
    )

    dof_map = DofMap(list(OFF_DRIVE_SENSORS), [int(DofType.UX)] * len(OFF_DRIVE_SENSORS))
    assert result.to_test_data(dof_map).meta["scaling"] == "arbitrary"


# --------------------------------------------------------------- AC-MPE-003


def _diagram(**tolerances):
    """Stabilization diagram of the full (untruncated) synthesis."""
    return stabilization_diagram(
        _synthesized(truncated=False), ORDERS, band=_band(), **tolerances
    )


def _is_physical(frequency: float, truth: np.ndarray) -> bool:
    return bool(np.min(np.abs(truth - frequency) / truth) <= 1e-3)


@criterion("AC-MPE-003")
def test_physical_poles_align_where_computational_poles_do_not() -> None:
    """Only the physical alignments survive the MS-10.3 classification."""
    truth, _ = _truth()
    diagram = _diagram()
    assert diagram.orders == ORDERS
    assert len(diagram.poles) == len(ORDERS)

    runs = np.zeros(NUM_MODES, dtype=int)
    longest = np.zeros(NUM_MODES, dtype=int)
    for level in diagram.poles:
        seen = np.zeros(NUM_MODES, dtype=bool)
        for pole in level:
            if not _is_physical(pole.frequency_hz, truth):
                assert pole.label != "stable", (pole.order, pole.frequency_hz)
                continue
            index = int(np.argmin(np.abs(truth - pole.frequency_hz)))
            seen[index] = pole.label == "stable"
        runs = np.where(seen, runs + 1, 0)
        longest = np.maximum(longest, runs)
    assert np.all(longest >= 3), longest


@criterion("AC-MPE-003")
def test_the_automatic_pick_returns_the_ground_truth_mode_count() -> None:
    """``select`` resolves the diagram to exactly the modes that are there."""
    truth, _ = _truth()
    picked = _diagram().select(min_count=3)

    assert len(picked) == NUM_MODES
    assert all(pole.label == "stable" for pole in picked)
    found, _ = _sorted_estimates(picked)
    assert _relative(found, truth) <= 1e-3

    # A count no alignment can reach is a typed failure, not an empty answer.
    with pytest.raises(MPEError, match="fully stable"):
        _diagram().select(min_count=len(ORDERS) + 1)


@criterion("AC-MPE-003")
def test_tightening_a_tolerance_never_promotes_a_pole() -> None:
    """Monotonicity of the classification in each of its three tolerances."""
    baseline = _diagram()
    rank = {label: index for index, label in enumerate(POLE_LABELS)}

    for tighter in ({"freq_tol": 1e-4}, {"damp_tol": 1e-3}, {"mac_tol": 0.999999}):
        strict = _diagram(**tighter)
        for loose_level, strict_level in zip(baseline.poles, strict.poles, strict=True):
            assert len(loose_level) == len(strict_level)
            for loose, tight in zip(loose_level, strict_level, strict=True):
                assert loose.frequency_hz == tight.frequency_hz
                assert rank[tight.label] <= rank[loose.label], (tighter, tight.order)


# --------------------------------------------------------------- AC-MPE-004


#: Free-text header of the records this criterion writes.
_ID_LINES = ("simulated campaign", "AC-MPE-004", "26-AUG-26", "OpenFEMLab", "receptance")


def _write_campaign(response: FrequencyResponse, path) -> None:
    """One dataset-58 record per (response, reference) pair of ``response``."""
    records = [
        UFFFunction(
            frequencies_hz=response.frequencies,
            values=response.data[:, j, k],
            response_node=int(response.response_dofs[j]) + 1,
            response_direction=int(DofType.UX),
            reference_node=int(response.excitation_dofs[k]) + 1,
            reference_direction=int(DofType.UX),
            ordinate_label="Receptance",
            ordinate_units="m/N",
            id_lines=_ID_LINES,
        )
        for j in range(response.num_response_dofs)
        for k in range(response.num_excitation_dofs)
    ]
    path.write_text(format_uff(records), encoding="utf-8")


def _read_campaign(path) -> FrequencyResponse:
    """Reassemble the FRF matrix from the dataset-58 records at ``path``."""
    functions = read_uff_functions(path)
    assert functions, "the campaign file carries no dataset-58 record"
    response_nodes = sorted({function.response_node for function in functions})
    reference_nodes = sorted({function.reference_node for function in functions})
    line = functions[0].frequencies_hz
    data = np.zeros((line.size, len(response_nodes), len(reference_nodes)), dtype=complex)
    for function in functions:
        assert function.function_type == 4
        row = response_nodes.index(function.response_node)
        column = reference_nodes.index(function.reference_node)
        data[:, row, column] = function.values
    return FrequencyResponse(
        line,
        data,
        np.array(response_nodes) - 1,
        np.array(reference_nodes) - 1,
    )


@criterion("AC-MPE-004")
def test_the_measurement_path_reaches_a_correlated_test_data(tmp_path) -> None:
    """UFF-58 -> MPE -> ``TestData`` -> ``correlate``, with provenance intact."""
    truth, ratios = _truth()
    path = tmp_path / "campaign.unv"
    _write_campaign(_synthesized(truncated=False), path)

    measured = _read_campaign(path)
    assert measured.data.shape == (_line().size, len(SENSORS), len(REFERENCES))

    result = extract_modes(measured, ORDERS, band=_band(), min_count=3)
    dof_map = DofMap(list(SENSORS), [int(DofType.UX)] * len(SENSORS))
    test_data = result.to_test_data(dof_map)

    assert test_data.n_modes == NUM_MODES
    assert test_data.damping == pytest.approx(ratios, rel=0.05)
    for key in ("method", "orders", "band_hz", "tolerances", "scaling"):
        assert key in test_data.meta, key
    assert test_data.meta["method"] == "pLSCF/LSFD"
    assert test_data.meta["orders"] == ORDERS

    summary = correlate(
        test_data.frequencies, truth, test_data.shapes, _source_shapes()
    )
    assert summary.n_paired == NUM_MODES
    assert summary.min_mac >= PIPELINE_MAC_GATE
    assert summary.max_abs_freq_error_pct <= 0.1


@criterion("AC-MPE-004")
def test_the_measurement_path_fails_with_typed_errors() -> None:
    """MS-10.5 names four refusals; each one is an ``MPEError``, not a wrong answer."""
    response = _synthesized()
    low, high = _band()

    with pytest.raises(MPEError, match="none of the"):
        fit_lscf(response, 6, band=(10.0 * high, 20.0 * high))
    with pytest.raises(MPEError, match="real unknowns"):
        fit_lscf(response, 500, band=(low, high))
    with pytest.raises(MPEError, match="receptance"):
        fit_lscf(response.converted("accelerance"), 6, band=(low, high))
    with pytest.raises(MPEError, match="fully stable"):
        extract_modes(response, (2, 3), band=(low, high), min_count=3)

    dof_map = DofMap([0], [int(DofType.UX)])
    result = extract_shapes(response, fit_lscf(response, 6, band=(low, high)), band=(low, high))
    with pytest.raises(MPEError, match="DofMap"):
        result.to_test_data(dof_map)


# --------------------------------------------------------------- AC-MPE-005


def _noisy(seed: int, level: float = NOISE_LEVEL) -> FrequencyResponse:
    """The synthesized FRF with seeded multiplicative noise of ``level`` RMS."""
    response = _synthesized()
    generator = np.random.default_rng(seed)
    scale = level / np.sqrt(2.0)
    perturbation = 1.0 + scale * (
        generator.standard_normal(response.data.shape)
        + 1j * generator.standard_normal(response.data.shape)
    )
    return FrequencyResponse(
        response.frequencies,
        response.data * perturbation,
        response.response_dofs,
        response.excitation_dofs,
        response.response_type,
    )


@criterion("AC-MPE-005")
def test_seeded_one_percent_noise_degrades_the_estimates_gracefully() -> None:
    """The gates loosen by orders of magnitude; the estimator must not."""
    truth, ratios = _truth()
    for seed in (SEED, SEED + 1, SEED + 2):
        result = extract_modes(_noisy(seed), ORDERS, band=_band(), min_count=3)
        assert result.num_modes == NUM_MODES, seed

        order = np.argsort(result.frequencies_hz)
        assert _relative(result.frequencies_hz[order], truth) <= NOISE_FREQUENCY_GATE
        assert _relative(result.damping_ratios[order], ratios) <= NOISE_DAMPING_GATE
        assert (
            np.min(np.diag(mac(result.shapes[:, order], _source_shapes())))
            >= NOISE_MAC_GATE
        )


@criterion("AC-MPE-005")
def test_the_estimator_is_bitwise_deterministic_on_a_seeded_input() -> None:
    """The noise carries the seed; the estimator has none (MS-10.1)."""
    first = _noisy(SEED)
    second = _noisy(SEED)
    assert np.array_equal(first.data, second.data), "the noise draw itself must be seeded"

    left = extract_modes(first, ORDERS, band=_band(), min_count=3)
    right = extract_modes(second, ORDERS, band=_band(), min_count=3)
    for name in ("frequencies_hz", "damping_ratios", "poles", "shapes", "participation", "frac"):
        assert np.array_equal(getattr(left, name), getattr(right, name)), name


@criterion("AC-MPE-006")
def test_ac_mpe_006_ssi_cov_recovers_operational_modes() -> None:
    """SSI-COV identifies both modes of a synthesized ambient record."""
    from openfemlab.mpe.ssi import simulate_operational_response, ssi_cov

    record = simulate_operational_response(
        (4.0, 9.5),
        (0.015, 0.02),
        np.array([[1.0, 0.8], [1.2, -0.6], [0.7, 1.1]]),
        sampling_rate_hz=200.0,
        samples=8192,
        seed=17,
    )
    result = ssi_cov(
        record,
        200.0,
        range(6, 20, 2),
        block_rows=30,
        min_count=2,
        freq_tol=0.05,
        damp_tol=0.15,
        mac_tol=0.85,
    )
    frequencies = list(result.frequencies_hz)
    assert any(abs(value - 4.0) < 0.6 for value in frequencies)
    assert any(abs(value - 9.5) < 0.6 for value in frequencies)


# --------------------------------------------------------------- AC-MPE-007

SSI_FREQUENCIES = (4.0, 9.5)
SSI_DAMPINGS = (0.015, 0.02)
SSI_SHAPES = np.array([[1.0, 0.8], [1.2, -0.6], [0.7, 1.1]])
SSI_FS = 200.0
SSI_SAMPLES = 8192
SSI_ORDERS = tuple(range(6, 24, 2))
SSI_NUM_MODES = len(SSI_FREQUENCIES)


def _ssi_record() -> np.ndarray:
    from openfemlab.mpe.ssi import simulate_operational_response

    return simulate_operational_response(
        SSI_FREQUENCIES,
        SSI_DAMPINGS,
        SSI_SHAPES,
        sampling_rate_hz=SSI_FS,
        samples=SSI_SAMPLES,
        seed=17,
    )


def _ssi_diagram(**tolerances):
    from openfemlab.mpe import ssi_cov_diagram

    return ssi_cov_diagram(
        _ssi_record(),
        SSI_FS,
        SSI_ORDERS,
        block_rows=25,
        **tolerances,
    )


def _ssi_is_physical(frequency: float) -> bool:
    truth = np.asarray(SSI_FREQUENCIES, dtype=float)
    return bool(np.min(np.abs(truth - frequency) / truth) <= 1e-2)


@criterion("AC-MPE-007")
def test_ac_mpe_007_ssi_physical_poles_stabilize() -> None:
    diagram = _ssi_diagram()
    runs = np.zeros(SSI_NUM_MODES, dtype=int)
    longest = np.zeros(SSI_NUM_MODES, dtype=int)
    for level in diagram.poles:
        seen = np.zeros(SSI_NUM_MODES, dtype=bool)
        for pole in level:
            if not _ssi_is_physical(pole.frequency_hz):
                assert pole.label != "stable"
                continue
            index = int(
                np.argmin([abs(pole.frequency_hz - truth) for truth in SSI_FREQUENCIES])
            )
            seen[index] = pole.label == "stable"
        runs = np.where(seen, runs + 1, 0)
        longest = np.maximum(longest, runs)
    assert np.all(longest >= 3)


@criterion("AC-MPE-007")
def test_ac_mpe_007_ssi_select_returns_the_oracle_mode_count() -> None:
    picked = _ssi_diagram().select(min_count=3)
    assert len(picked) == SSI_NUM_MODES
    assert all(pole.label == "stable" for pole in picked)


@criterion("AC-MPE-008")
def test_ac_mpe_008_rbpe_recovers_total_mass_and_center_of_gravity() -> None:
    from openfemlab.mpe.rbpe import from_lumped_masses

    nodes = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [1.0, 1.0, 0.0]])
    masses = np.array([1.0, 3.0, 2.0])
    props = from_lumped_masses(nodes, masses)
    assert props.total_mass == 6.0
    assert props.center_of_gravity == pytest.approx([1.3333333333, 0.3333333333, 0.0])
    assert props.inertia_tensor is not None
    assert np.all(np.diag(props.inertia_tensor) > 0.0)


@criterion("AC-MPE-007")
def test_ac_mpe_007_ssi_tightening_tolerances_never_promotes_a_pole() -> None:
    baseline = _ssi_diagram()
    rank = {label: index for index, label in enumerate(POLE_LABELS)}
    for tighter in ({"freq_tol": 1e-4}, {"damp_tol": 1e-3}, {"mac_tol": 0.999999}):
        strict = _ssi_diagram(**tighter)
        for loose_level, strict_level in zip(baseline.poles, strict.poles, strict=True):
            for loose, tight in zip(loose_level, strict_level, strict=True):
                assert rank[tight.label] <= rank[loose.label]
