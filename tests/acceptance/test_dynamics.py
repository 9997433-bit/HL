"""M6 damped-dynamics acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 7).

Implemented here
----------------
- **AC-DYN-001** (oracle, MS-7.3) — synthesized receptance against the closed-form
  1-DOF oscillator and the closed-form inverse of the 2-DOF dynamic stiffness,
  plus the ``iw H`` / ``-w^2 H`` mobility and accelerance identities.
- **AC-DYN-002** (property, MS-7.3) — with the full modal basis retained, real-mode
  and complex-mode superposition both reproduce the direct inversion of
  ``Z(w)``; a truncated synthesis plus residual flexibility recovers the exact
  static receptance.
- **AC-DYN-003** (property, MS-7.2) — Rayleigh damping produces monophase complex
  modes whose ratios follow ``alpha/(2 w_r) + beta w_r/2``, while a single
  grounded dashpot is detected as non-proportional.
- **AC-DYN-004** (property, MS-7.4) — FRAC self-identity and invariance under a
  complex scale factor; FDAC unit diagonal and symmetry; degenerate inputs
  return 0 rather than NaN.
- **AC-DYN-005** (contract, MS-7.4) — a synthesized receptance line written as an
  ASCII dataset-58 record is recovered by ``io/uff.py`` and correlates with its
  source at FRAC = 1.

The oracles are the fixed-fixed spring-mass chain (``ten_dof_chain``) and the
2-DOF analytic fixture, so every gate compares against theory or against the
untruncated ``Z(w)^-1`` reference rather than against a previous run.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab import ModalSolver
from openfemlab.io.uff import read_uff_functions
from openfemlab.solver.dynamics import (
    RayleighDamping,
    complex_modal_frf,
    complex_modes,
    direct_frf,
    fdac,
    frac,
    is_proportional,
    modal_frf,
    residual_flexibility,
)

from ._support import criterion, fixture_matrices, load_fixture

#: Gates of AC-DYN-001/002 (relative error against a closed form or Z(w)^-1).
ORACLE_TOLERANCE = 1e-8

#: Gates of AC-DYN-003.
MPC_TOLERANCE = 1e-8
RATIO_TOLERANCE = 1e-10

#: Gates of AC-DYN-004 (mirrors the AC-CORR-002 invariance budget).
INVARIANCE_TOLERANCE = 1e-12

#: Gate of AC-DYN-005: 12 significant digits are written, so 1e-9 is generous.
ROUND_TRIP_TOLERANCE = 1e-9

#: Seeded draws; a criterion only counts if its test is deterministic.
SEED = 20260826

#: Rayleigh coefficients used throughout: ~1 % damping over the chain spectrum.
ALPHA, BETA = 0.02, 0.004


def _chain() -> tuple[np.ndarray, np.ndarray]:
    """``(K, M)`` of the 10-DOF fixed-fixed chain fixture."""
    return fixture_matrices(load_fixture("ten_dof_chain"))


def _full_basis(K: np.ndarray, M: np.ndarray):
    """Every mass-normalized mode of ``(K, M)``."""
    return ModalSolver.from_matrices(K, M).solve(num_modes=K.shape[0], sparse=False)


def _off_resonance_line(K: np.ndarray, M: np.ndarray, count: int = 40) -> np.ndarray:
    """A frequency line [Hz] spanning the spectrum but avoiding every resonance.

    The lines sit at the midpoints between consecutive natural frequencies (plus
    one below the first and one above the last), so no denominator of the modal
    synthesis comes near zero and the comparison measures truncation, not the
    conditioning of a resonant peak.
    """
    natural = _full_basis(K, M).frequencies
    edges = np.concatenate(([0.5 * natural[0]], natural, [1.5 * natural[-1]]))
    line = np.linspace(edges[0], edges[-1], count)
    for f in natural:
        line = line[np.abs(line - f) > 0.02 * f]
    return line


def _relative_error(actual: np.ndarray, expected: np.ndarray) -> float:
    """``max |actual - expected| / max |expected|`` over a complex FRF block."""
    scale = float(np.max(np.abs(expected)))
    return float(np.max(np.abs(actual - expected)) / scale)


# --------------------------------------------------------------- AC-DYN-001


@criterion("AC-DYN-001")
def test_single_dof_receptance_matches_the_closed_form() -> None:
    """``H(w) = 1 / (k - m w^2 + i w c)`` for the damped 1-DOF oscillator."""
    mass, stiffness, dashpot = 2.0, 800.0, 3.0
    K = np.array([[stiffness]])
    M = np.array([[mass]])
    C = np.array([[dashpot]])

    frequencies = np.linspace(0.0, 20.0, 61)
    omega = 2.0 * np.pi * frequencies
    expected = 1.0 / (stiffness - mass * omega**2 + 1j * omega * dashpot)

    direct = direct_frf(frequencies, K, M, C).data[:, 0, 0]
    assert _relative_error(direct, expected) <= ORACLE_TOLERANCE

    # The same oracle through real-mode superposition: one mass-normalized mode
    # phi = 1/sqrt(m) at w_r = sqrt(k/m), damped at zeta = c / (2 sqrt(k m)).
    natural = np.sqrt(stiffness / mass)
    ratio = dashpot / (2.0 * np.sqrt(stiffness * mass))
    modal = modal_frf(
        frequencies,
        (np.array([natural]), np.array([[1.0 / np.sqrt(mass)]])),
        ratio,
    ).data[:, 0, 0]
    assert _relative_error(modal, expected) <= ORACLE_TOLERANCE


@criterion("AC-DYN-001")
def test_two_dof_receptance_matches_the_analytic_inverse() -> None:
    """The 2x2 dynamic stiffness inverted in closed form, off resonance."""
    K, M = fixture_matrices(load_fixture("two_dof_analytic"))
    damping = RayleighDamping(alpha=ALPHA, beta=BETA)
    C = damping.matrix(K, M)

    frequencies = _off_resonance_line(K, M)
    omega = 2.0 * np.pi * frequencies
    Z = (
        K[None, :, :]
        - omega[:, None, None] ** 2 * M[None, :, :]
        + 1j * omega[:, None, None] * C[None, :, :]
    )
    determinant = Z[:, 0, 0] * Z[:, 1, 1] - Z[:, 0, 1] * Z[:, 1, 0]
    expected = np.empty_like(Z)
    expected[:, 0, 0] = Z[:, 1, 1]
    expected[:, 1, 1] = Z[:, 0, 0]
    expected[:, 0, 1] = -Z[:, 0, 1]
    expected[:, 1, 0] = -Z[:, 1, 0]
    expected /= determinant[:, None, None]

    response = direct_frf(frequencies, K, M, C)
    assert _relative_error(response.data, expected) <= ORACLE_TOLERANCE

    modes = _full_basis(K, M)
    synthesized = modal_frf(frequencies, modes, damping)
    assert _relative_error(synthesized.data, expected) <= ORACLE_TOLERANCE


@criterion("AC-DYN-001")
def test_mobility_and_accelerance_follow_the_differentiation_identities() -> None:
    """``mobility = i w H`` and ``accelerance = -w^2 H`` (MS-7.3 conventions)."""
    K, M = fixture_matrices(load_fixture("two_dof_analytic"))
    C = RayleighDamping(alpha=ALPHA, beta=BETA).matrix(K, M)
    frequencies = _off_resonance_line(K, M)
    omega = (2.0 * np.pi * frequencies)[:, None, None]

    receptance = direct_frf(frequencies, K, M, C)
    assert _relative_error(
        receptance.converted("mobility").data, 1j * omega * receptance.data
    ) <= ORACLE_TOLERANCE
    assert _relative_error(
        receptance.converted("accelerance").data, -(omega**2) * receptance.data
    ) <= ORACLE_TOLERANCE


# --------------------------------------------------------------- AC-DYN-002


@criterion("AC-DYN-002")
def test_real_mode_superposition_reproduces_the_direct_inversion() -> None:
    """Full basis + proportional damping: modal synthesis == ``Z(w)^-1``."""
    K, M = _chain()
    damping = RayleighDamping(alpha=ALPHA, beta=BETA)
    C = damping.matrix(K, M)
    frequencies = _off_resonance_line(K, M)

    reference = direct_frf(frequencies, K, M, C).data
    synthesized = modal_frf(frequencies, _full_basis(K, M), damping).data
    assert _relative_error(synthesized, reference) <= ORACLE_TOLERANCE


@criterion("AC-DYN-002")
def test_complex_mode_superposition_handles_non_proportional_damping() -> None:
    """Residue expansion == ``Z(w)^-1`` where the real-mode form does not apply."""
    K, M = _chain()
    C = np.zeros_like(K)
    C[0, 0] = 0.35  # a single grounded dashpot: deliberately non-classical
    assert not is_proportional(K, M, C)

    frequencies = _off_resonance_line(K, M)
    reference = direct_frf(frequencies, K, M, C).data
    synthesized = complex_modal_frf(frequencies, complex_modes(K, M, C)).data
    assert _relative_error(synthesized, reference) <= ORACLE_TOLERANCE


@criterion("AC-DYN-002")
def test_residual_flexibility_restores_the_static_receptance() -> None:
    """A truncated synthesis plus ``R`` recovers ``K^-1`` at 0 Hz."""
    K, M = _chain()
    modes = _full_basis(K, M)
    kept = 3
    static = np.linalg.inv(K)

    truncated = modal_frf([0.0], modes, 0.0, num_modes=kept).data[0]
    assert _relative_error(truncated, static) > 1e-3, "truncation must actually bite"

    residual = residual_flexibility(K, modes, num_modes=kept)
    corrected = modal_frf([0.0], modes, 0.0, num_modes=kept, residual=residual).data[0]
    assert _relative_error(corrected, static) <= ORACLE_TOLERANCE


# --------------------------------------------------------------- AC-DYN-003


@criterion("AC-DYN-003")
def test_proportional_damping_gives_monophase_modes_and_rayleigh_ratios() -> None:
    """``C = alpha M + beta K``: MPC = 1 and ``zeta_r = alpha/(2 w_r) + beta w_r/2``."""
    K, M = _chain()
    damping = RayleighDamping(alpha=ALPHA, beta=BETA)
    C = damping.matrix(K, M)
    assert is_proportional(K, M, C)

    result = complex_modes(K, M, C)
    undamped = _full_basis(K, M).angular_frequencies
    assert result.num_modes == undamped.size

    expected_ratios = damping.damping_ratios(undamped)
    assert result.damping_ratios == pytest.approx(expected_ratios, abs=RATIO_TOLERANCE)
    assert result.angular_frequencies == pytest.approx(undamped, rel=RATIO_TOLERANCE)
    assert result.damped_angular_frequencies == pytest.approx(
        undamped * np.sqrt(1.0 - expected_ratios**2), rel=RATIO_TOLERANCE
    )
    assert np.all(result.is_oscillatory)
    assert np.min(result.modal_phase_collinearity) >= 1.0 - MPC_TOLERANCE


@criterion("AC-DYN-003")
def test_a_single_grounded_dashpot_is_detected_as_non_proportional() -> None:
    """Non-classical damping spreads the modal phases, so MPC drops below 1."""
    K, M = _chain()
    C = np.zeros_like(K)
    C[0, 0] = 0.35

    assert not is_proportional(K, M, C)
    result = complex_modes(K, M, C)
    assert np.min(result.modal_phase_collinearity) < 1.0 - 1e-3


# --------------------------------------------------------------- AC-DYN-004


def _chain_response():
    """A damped receptance block of the chain, used by the FRAC/FDAC gates."""
    K, M = _chain()
    damping = RayleighDamping(alpha=ALPHA, beta=BETA)
    frequencies = np.linspace(0.01, 1.2 * _full_basis(K, M).frequencies[-1], 96)
    return modal_frf(frequencies, _full_basis(K, M), damping)


@criterion("AC-DYN-004")
def test_frac_is_one_for_a_response_against_itself() -> None:
    """Self-identity, mirroring AC-CORR-001 in the frequency domain."""
    response = _chain_response()
    for excitation in (0, 4):
        block = response.column(excitation)
        assert frac(block, block) == pytest.approx(1.0, abs=INVARIANCE_TOLERANCE)


@criterion("AC-DYN-004")
def test_frac_is_invariant_under_a_complex_scale_factor() -> None:
    """Scaling either FRF by a nonzero complex constant leaves FRAC unchanged."""
    response = _chain_response()
    reference = response.column(0)
    comparison = response.column(4)
    baseline = frac(reference, comparison)

    rng = np.random.default_rng(SEED)
    for _ in range(8):
        factor = complex(*rng.normal(size=2))
        assert frac(factor * reference, comparison) == pytest.approx(
            baseline, abs=INVARIANCE_TOLERANCE
        )
        assert frac(reference, factor * comparison) == pytest.approx(
            baseline, abs=INVARIANCE_TOLERANCE
        )


@criterion("AC-DYN-004")
def test_fdac_has_a_unit_diagonal_and_is_symmetric() -> None:
    """A response set correlated with itself resonates on the FDAC diagonal."""
    block = _chain_response().column(0)
    matrix = fdac(block, block)

    assert matrix.shape == (block.shape[0], block.shape[0])
    assert np.diag(matrix) == pytest.approx(1.0, abs=INVARIANCE_TOLERANCE)
    assert matrix == pytest.approx(matrix.T, abs=INVARIANCE_TOLERANCE)
    assert np.all(matrix >= -INVARIANCE_TOLERANCE)
    assert np.all(matrix <= 1.0 + INVARIANCE_TOLERANCE)


@criterion("AC-DYN-004")
def test_degenerate_inputs_return_zero_rather_than_nan() -> None:
    """A zero-norm FRF has no shape to correlate; the metrics must not emit NaN."""
    block = _chain_response().column(0)
    zeros = np.zeros_like(block)

    assert np.all(frac(zeros, block) == 0.0)
    assert np.all(fdac(zeros, block) == 0.0)


# --------------------------------------------------------------- AC-DYN-005


def _dataset_58(frequencies: np.ndarray, values: np.ndarray) -> str:
    """Format one complex, evenly spaced dataset-58 record (11 records + data).

    Written here rather than in the library because the criterion gates the
    *reader* contract: the library owns no UFF writer yet (that is R2-T05).
    """
    increment = float(frequencies[1] - frequencies[0])
    identification = (
        f"{4:5d}{1:10d}{0:5d}{0:10d} "
        f"{'NONE':>10}{1:10d}{1:4d} "
        f"{'NONE':>10}{1:10d}{1:4d}"
    )
    data_form = (
        f"{6:10d}{frequencies.size:10d}{1:10d}"
        f"{float(frequencies[0]):13.5E}{increment:13.5E}{0.0:13.5E}"
    )
    abscissa = f"{18:10d}{0:5d}{0:5d}{0:5d} {'Frequency':<20} {'Hz':<20}"
    ordinate = f"{8:10d}{0:5d}{0:5d}{0:5d} {'Receptance':<20} {'m/N':<20}"
    unused = f"{0:10d}{0:5d}{0:5d}{0:5d} {'NONE':<20} {'NONE':<20}"

    interleaved = np.empty(2 * values.size)
    interleaved[0::2] = values.real
    interleaved[1::2] = values.imag
    data = [
        " ".join(f"{value:.12E}" for value in interleaved[start : start + 4])
        for start in range(0, interleaved.size, 4)
    ]
    records = [
        "synthesized FRF",
        "AC-DYN-005",
        "26-AUG-26",
        "OpenFEMLab",
        "receptance",
        identification,
        data_form,
        abscissa,
        ordinate,
        unused,
        unused,
        *data,
    ]
    return "\n".join(["    -1", f"{58:6d}", *records, "    -1", ""])


@criterion("AC-DYN-005")
def test_synthesized_frf_round_trips_through_the_uff_58_reader(tmp_path) -> None:
    """A synthesized drive-point receptance survives the dataset-58 interchange."""
    K, M = _chain()
    frequencies = 0.02 + np.arange(64) * 0.005
    line = modal_frf(
        frequencies,
        _full_basis(K, M),
        RayleighDamping(alpha=ALPHA, beta=BETA),
        response_dofs=[0],
        excitation_dofs=[0],
    ).drive_point(0)

    path = tmp_path / "synthesized.unv"
    path.write_text(_dataset_58(frequencies, line), encoding="utf-8")

    functions = read_uff_functions(path)
    assert len(functions) == 1
    recovered = functions[0]
    assert recovered.function_type == 4
    assert recovered.abscissa_label == "Frequency"
    assert recovered.abscissa_units == "Hz"
    assert recovered.frequencies_hz == pytest.approx(
        frequencies, rel=ROUND_TRIP_TOLERANCE
    )
    assert _relative_error(recovered.values, line) <= ROUND_TRIP_TOLERANCE
    assert frac(line, recovered.values) == pytest.approx(1.0, abs=1e-12)
