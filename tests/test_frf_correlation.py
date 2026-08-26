"""FRF correlation: the FRAC/FDAC block carried by ``CorrelationReport``.

The reference model is a damped fixed-free spring/mass chain whose FRFs come
from ``direct_frf`` (untruncated inversion of ``Z(omega)``), so every
expectation here follows from the physics of the comparison rather than from a
recorded run:

* a set correlated against itself must give FRAC = 1 on every channel and a
  unit FDAC diagonal (MS-7.4, mirroring the AC-DYN-004 gate);
* FRAC is invariant under a complex scale factor, because a shared exciter
  calibration error must not read as a model error;
* stiffening the chain shifts its resonances, which has to drop FRAC and push
  the FDAC peak off the diagonal.

The schema half of the file pins the 1.1 contract: the ``frf`` key exists on
every report, is ``null`` when no FRF comparison was run, and survives a JSON
round trip when one was.
"""

from __future__ import annotations

import json

import numpy as np
import pytest
import scipy.sparse as sp

from openfemlab.correlation import (
    SCHEMA_VERSION,
    FRFCorrelation,
    correlation_report,
    frf_correlation,
)
from openfemlab.mesh.simple import spring_mass_chain
from openfemlab.solver.dynamics import RayleighDamping, damped_matrices, direct_frf

#: ~1 % damping over the band the chain resonates in.
DAMPING = RayleighDamping(alpha=0.3, beta=2.0e-4)

#: Self-correlation is exact up to the FRAC kernel's own round-off.
IDENTITY_TOLERANCE = 1.0e-12

NUM_MASSES = 4
LINE = np.linspace(0.5, 15.0, 60)


def chain_matrices(stiffness: float = 1000.0, mass: float = 1.0):
    """Free-DOF dense ``(K, M, C)`` of the damped fixed-free chain."""
    model = spring_mass_chain(NUM_MASSES, stiffness, mass)
    K, M, C, free = damped_matrices(model, damping=DAMPING)
    grid = np.ix_(free, free)
    dense = (C.toarray() if sp.issparse(C) else np.asarray(C))[grid]
    return K.toarray()[grid], M.toarray()[grid], dense


def response(stiffness: float = 1000.0, mass: float = 1.0, line=LINE):
    """FRF of the chain, every DOF measured and every DOF excited."""
    return direct_frf(line, *chain_matrices(stiffness, mass))


@pytest.fixture(scope="module")
def reference():
    return response()


@pytest.fixture(scope="module")
def detuned():
    """The same chain 15 % stiffer: identical DOFs, shifted resonances."""
    return response(stiffness=1150.0)


@pytest.fixture(scope="module")
def block(reference):
    """A single-exciter ``(n_frequencies, n_channels)`` slice."""
    return reference.column(0)


# ================================================================== the metrics


def test_self_correlation_is_perfect_on_every_channel(reference) -> None:
    result = frf_correlation(reference, reference, excitation_dof=0)

    assert result.n_channels == NUM_MASSES
    assert result.n_frequencies == LINE.size
    np.testing.assert_allclose(result.frac, 1.0, atol=IDENTITY_TOLERANCE)
    assert result.mean_frac == pytest.approx(1.0, abs=IDENTITY_TOLERANCE)
    assert result.min_frac == pytest.approx(1.0, abs=IDENTITY_TOLERANCE)
    assert result.max_frac == pytest.approx(1.0, abs=IDENTITY_TOLERANCE)
    np.testing.assert_allclose(result.fdac_diagonal, 1.0, atol=IDENTITY_TOLERANCE)
    assert result.min_fdac_diagonal == pytest.approx(1.0, abs=IDENTITY_TOLERANCE)
    assert result.is_correlated(frac_threshold=0.99)


def test_frac_ignores_a_complex_scale_factor(block) -> None:
    """A shared exciter calibration error must not read as a model error."""
    baseline = frf_correlation(block, block, frequencies=LINE, with_fdac=False)
    scaled = frf_correlation(block, block * (2.5 - 1.3j), frequencies=LINE, with_fdac=False)

    np.testing.assert_allclose(scaled.frac, baseline.frac, atol=IDENTITY_TOLERANCE)


def test_a_detuned_model_loses_frac_and_shifts_the_fdac_ridge(reference, detuned) -> None:
    result = frf_correlation(reference, detuned, excitation_dof=0)

    assert result.min_frac < 0.9
    assert not result.is_correlated(frac_threshold=0.9)
    assert result.min_fdac_diagonal < 0.9

    # The stiffer chain resonates higher, so the shape a reference line matches
    # best sits at a higher comparison line: the FDAC peak leaves the diagonal.
    peaks = np.argmax(result.fdac, axis=1)
    assert np.mean(peaks > np.arange(result.n_frequencies)) > 0.5


def test_worst_channel_names_the_least_correlated_response(reference) -> None:
    corrupted = reference.column(0).copy()
    corrupted[:, 2] = np.conj(corrupted[:, 2]) * np.linspace(1.0, 40.0, LINE.size)

    result = frf_correlation(
        reference.column(0),
        corrupted,
        frequencies=LINE,
        channels=[f"mass_{index}" for index in range(NUM_MASSES)],
    )

    index, value = result.worst_channel()
    assert index == 2
    assert value == pytest.approx(result.min_frac)
    assert result.channel_label(2) == "mass_2"
    assert "mass_2" in result.report()


def test_channels_default_to_the_response_dofs(reference) -> None:
    result = frf_correlation(reference, reference, excitation_dof=0, with_fdac=False)

    assert result.channels == tuple(f"dof {dof}" for dof in reference.response_dofs)
    assert result.excitation == "dof 0"
    assert result.response_type == "receptance"


def test_fdac_can_be_switched_off_for_long_frequency_lines(reference) -> None:
    result = frf_correlation(reference, reference, excitation_dof=0, with_fdac=False)

    assert result.fdac is None
    assert result.fdac_diagonal.size == 0
    assert result.min_fdac_diagonal is None
    assert result.as_dict()["fdac"] is None


def test_a_plain_array_pair_correlates_with_an_explicit_frequency_line(block) -> None:
    result = frf_correlation(np.asarray(block), np.asarray(block), frequencies=LINE)

    np.testing.assert_allclose(result.frequencies, LINE)
    np.testing.assert_allclose(result.frac, 1.0, atol=IDENTITY_TOLERANCE)


def test_a_single_channel_line_is_accepted_as_a_1d_array(block) -> None:
    line = block[:, 0]
    result = frf_correlation(line, line, frequencies=LINE, with_fdac=False)

    assert result.n_channels == 1
    assert result.frac.shape == (1,)
    assert result.channel_label(0) == "channel 0"


# =================================================================== validation


def test_a_multi_exciter_response_demands_an_excitation_dof(reference) -> None:
    with pytest.raises(ValueError, match="excitation_dof"):
        frf_correlation(reference, reference)


def test_an_unmeasured_exciter_is_rejected(reference) -> None:
    with pytest.raises(ValueError, match="not excited at DOF 9"):
        frf_correlation(reference, reference, excitation_dof=9)


def test_mismatched_shapes_are_rejected(block) -> None:
    with pytest.raises(ValueError, match="same shape"):
        frf_correlation(block, block[:, :2], frequencies=LINE)


def test_a_plain_array_pair_without_a_frequency_line_is_rejected(block) -> None:
    with pytest.raises(ValueError, match="frequency line is unknown"):
        frf_correlation(block, block)


def test_two_different_frequency_lines_are_rejected(reference) -> None:
    shifted = response(line=LINE + 0.25)
    with pytest.raises(ValueError, match="different frequency lines"):
        frf_correlation(reference, shifted, excitation_dof=0)


def test_mixing_receptance_with_accelerance_is_rejected(reference) -> None:
    with pytest.raises(ValueError, match="converted"):
        frf_correlation(reference, reference.converted("accelerance"), excitation_dof=0)


def test_converted_views_correlate_once_both_sides_agree(reference) -> None:
    accelerance = reference.converted("accelerance")
    result = frf_correlation(accelerance, accelerance, excitation_dof=0, with_fdac=False)

    assert result.response_type == "accelerance"
    np.testing.assert_allclose(result.frac, 1.0, atol=IDENTITY_TOLERANCE)


def test_channel_labels_must_cover_every_channel(block) -> None:
    with pytest.raises(ValueError, match="channel labels"):
        frf_correlation(block, block, frequencies=LINE, channels=["a", "b"])


def test_the_block_validates_its_own_fdac_shape() -> None:
    with pytest.raises(ValueError, match="does not match"):
        FRFCorrelation(frequencies=[1.0, 2.0], frac=[1.0], fdac=np.ones((3, 3)))


def test_the_block_rejects_an_empty_channel_set() -> None:
    with pytest.raises(ValueError, match="at least one channel"):
        FRFCorrelation(frequencies=[1.0], frac=[])


# ======================================================= the schema-1.1 contract


def test_the_report_carries_the_frf_block(reference, detuned) -> None:
    frf = frf_correlation(reference, detuned, excitation_dof=0)
    report = correlation_report(
        test_frequencies=[10.0, 20.0, 30.0],
        fe_frequencies=[10.1, 20.1, 30.2],
        frf=frf,
    )

    assert report.frf is frf
    assert report.mean_frac == pytest.approx(frf.mean_frac)
    assert report.min_frac == pytest.approx(frf.min_frac)
    assert "FRF correlation" in report.report()


def test_a_report_without_an_frf_comparison_reports_none() -> None:
    report = correlation_report(
        test_frequencies=[10.0, 20.0],
        fe_frequencies=[10.1, 20.1],
    )

    assert report.frf is None
    assert report.mean_frac is None
    assert report.min_frac is None
    assert report.to_dict()["frf"] is None
    assert "FRF correlation" not in report.report()


def test_the_schema_version_is_bumped_for_the_frf_block() -> None:
    report = correlation_report(test_frequencies=[10.0], fe_frequencies=[10.1])

    assert SCHEMA_VERSION == "1.1"
    assert report.to_dict()["schema_version"] == SCHEMA_VERSION


def test_the_frf_block_survives_a_json_round_trip(reference, detuned) -> None:
    frf = frf_correlation(reference, detuned, excitation_dof=0)
    report = correlation_report(
        test_frequencies=[10.0, 20.0, 30.0],
        fe_frequencies=[10.1, 20.1, 30.2],
        frf=frf,
    )

    payload = json.loads(report.to_json())["frf"]

    assert set(payload) == {
        "response_type",
        "excitation",
        "n_frequencies",
        "n_channels",
        "mean_frac",
        "min_frac",
        "max_frac",
        "min_fdac_diagonal",
        "frequencies",
        "frac",
        "channels",
        "fdac",
        "meta",
    }
    assert payload["response_type"] == "receptance"
    assert payload["excitation"] == "dof 0"
    assert payload["n_channels"] == NUM_MASSES
    np.testing.assert_allclose(payload["frequencies"], LINE, rtol=1e-15)
    np.testing.assert_allclose(payload["frac"], frf.frac, rtol=1e-15)
    np.testing.assert_allclose(payload["fdac"], frf.fdac, rtol=1e-15)
    assert payload["mean_frac"] == pytest.approx(frf.mean_frac)
    assert payload["min_fdac_diagonal"] == pytest.approx(frf.min_fdac_diagonal)


def test_metadata_rides_along_in_the_artifact(reference) -> None:
    frf = frf_correlation(
        reference,
        reference,
        excitation_dof=0,
        with_fdac=False,
        meta={"source": "uff58", "hammer": "roving"},
    )

    assert json.loads(json.dumps(frf.as_dict()))["meta"] == {
        "source": "uff58",
        "hammer": "roving",
    }


def test_the_frac_gate_extends_the_modal_gates(reference, detuned) -> None:
    good = frf_correlation(reference, reference, excitation_dof=0, with_fdac=False)
    bad = frf_correlation(reference, detuned, excitation_dof=0, with_fdac=False)
    shapes = np.eye(3)

    def report_with(frf):
        return correlation_report(
            test_frequencies=[10.0, 20.0, 30.0],
            fe_frequencies=[10.0, 20.0, 30.0],
            test_shapes=shapes,
            fe_shapes=shapes,
            frf=frf,
        )

    assert report_with(good).is_correlated(frac_threshold=0.99)
    assert report_with(bad).is_correlated()  # the modal gates still pass on their own
    assert not report_with(bad).is_correlated(frac_threshold=0.99)


def test_gating_frac_without_an_frf_block_is_a_caller_error() -> None:
    report = correlation_report(test_frequencies=[10.0], fe_frequencies=[10.0])

    with pytest.raises(ValueError, match="no FRF block"):
        report.is_correlated(frac_threshold=0.9)
