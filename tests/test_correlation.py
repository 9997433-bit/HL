"""FE/test correlation: DOF alignment, MAC family, mode pairing, error metrics.

The synthetic fixture ``fixtures/test_modes.yaml`` is the reference case: an
analytical mode set on four DOFs, an "experimental" set that omits ``node_2``
and carries arbitrary per-mode scaling and sign, and the correlation results
they must produce. Any implementation that forgets to align the DOF sets, or
that compares shapes without normalizing them, fails these tests.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from openfemlab.correlation import (
    SCHEMA_VERSION,
    align_by_labels,
    auto_mac,
    automac,
    comac,
    correlate,
    correlate_modal_data,
    correlation_report,
    correlation_summary,
    frequency_difference,
    frequency_error_matrix,
    mac,
    mac_matrix,
    mac_value,
    modal_scale_factor,
    normalized_frequency_residual,
    off_diagonal_mac,
    orthogonality,
    pair_modes,
    relative_frequency_error,
    selection_matrix,
)
from tests.modal_reference import two_dof_chain, uniform_chain

FIXTURES = Path(__file__).parent / "fixtures"
MODE_FIXTURE = FIXTURES / "test_modes.yaml"

MATCHED_MAC_GATE = 0.95  # MS-4.2 validation gate for paired modes


def load_fixture() -> dict:
    return yaml.safe_load(MODE_FIXTURE.read_text(encoding="utf-8"))


def shapes_of(section: dict) -> np.ndarray:
    """Fixture shapes are stored mode-by-DOF; correlation wants DOF-by-mode."""
    return np.asarray(section["mode_shapes"], dtype=float).T


@pytest.fixture(scope="module")
def fixture_data() -> dict:
    return load_fixture()


@pytest.fixture(scope="module")
def aligned(fixture_data: dict):
    analytical = fixture_data["analytical"]
    experimental = fixture_data["experimental"]
    return align_by_labels(
        shapes_of(analytical),
        analytical["dof_labels"],
        shapes_of(experimental),
        experimental["dof_labels"],
    )


# ---------------------------------------------------------------------------
# DOF alignment (MS-2.1)
# ---------------------------------------------------------------------------


def test_alignment_reduces_the_model_onto_the_instrumented_dofs(fixture_data, aligned) -> None:
    expected = fixture_data["expected"]
    analytical_labels = fixture_data["analytical"]["dof_labels"]

    assert aligned.n_dof == len(expected["shared_dof_labels"])
    assert list(aligned.labels) == expected["shared_dof_labels"]
    assert aligned.fe.shape == (3, 3)
    assert aligned.test.shape == (3, 3)
    assert [analytical_labels[i] for i in aligned.unmatched_fe] == expected[
        "analytical_dofs_missing_from_test"
    ]
    assert aligned.unmatched_test.size == 0


def test_alignment_keeps_the_rows_of_both_sets_in_the_same_dof_order(fixture_data) -> None:
    analytical = fixture_data["analytical"]
    experimental = fixture_data["experimental"]
    # Feed the sensors in a scrambled order: alignment must follow the labels,
    # not the row positions.
    order = [2, 0, 1]
    scrambled_labels = [experimental["dof_labels"][i] for i in order]
    scrambled_shapes = shapes_of(experimental)[order, :]

    result = align_by_labels(
        shapes_of(analytical),
        analytical["dof_labels"],
        scrambled_shapes,
        scrambled_labels,
    )

    assert list(result.labels) == scrambled_labels
    for row, label in enumerate(result.labels):
        source = analytical["dof_labels"].index(label)
        np.testing.assert_allclose(result.fe[row], shapes_of(analytical)[source])


def test_alignment_reports_a_sensor_the_model_does_not_have(fixture_data) -> None:
    analytical = fixture_data["analytical"]

    with pytest.raises(KeyError, match="sensor_99:x"):
        align_by_labels(
            shapes_of(analytical),
            analytical["dof_labels"],
            np.ones((2, 3)),
            ["node_1:x", "sensor_99:x"],
        )


def test_alignment_can_drop_unknown_sensors_when_asked(fixture_data) -> None:
    analytical = fixture_data["analytical"]

    result = align_by_labels(
        shapes_of(analytical),
        analytical["dof_labels"],
        np.ones((2, 3)),
        ["node_1:x", "sensor_99:x"],
        strict=False,
    )

    assert list(result.labels) == ["node_1:x"]
    assert result.unmatched_test.tolist() == [1]


def test_alignment_applies_sensor_orientation_signs(fixture_data) -> None:
    analytical = fixture_data["analytical"]
    experimental = fixture_data["experimental"]
    flipped = shapes_of(experimental).copy()
    flipped[1, :] *= -1.0  # one accelerometer mounted the other way round

    result = align_by_labels(
        shapes_of(analytical),
        analytical["dof_labels"],
        flipped,
        experimental["dof_labels"],
        signs=[1.0, -1.0, 1.0],
    )

    np.testing.assert_allclose(result.test, shapes_of(experimental))


def test_selection_operator_matches_index_based_reduction(fixture_data, aligned) -> None:
    shapes = shapes_of(fixture_data["analytical"])

    operator = selection_matrix(shapes.shape[0], aligned.fe_rows)

    assert operator.shape == (3, 4)
    np.testing.assert_allclose(operator @ shapes, aligned.fe)


# ---------------------------------------------------------------------------
# MAC family (MS-2.2, MS-2.5)
# ---------------------------------------------------------------------------


def test_fixture_matched_modes_correlate_above_the_acceptance_gate(aligned, fixture_data) -> None:
    expected = fixture_data["expected"]
    tolerance = fixture_data["tolerances"]["mac_absolute"]

    macs = mac(aligned.test, aligned.fe)
    diagonal = np.diag(macs)

    assert macs.shape == (3, 3)
    np.testing.assert_allclose(diagonal, expected["mac_diagonal"], atol=tolerance)
    assert diagonal.min() > MATCHED_MAC_GATE
    # Unrelated modes must stay far away from the gate, otherwise a high
    # diagonal would prove nothing. Three sensors no longer see the modes as
    # orthogonal, so the off-diagonal terms are small rather than zero.
    off_diagonal = macs[~np.eye(3, dtype=bool)]
    assert off_diagonal.max() < 0.2


def test_mac_ignores_scaling_and_sign_of_either_shape(aligned) -> None:
    reference = mac(aligned.test, aligned.fe)
    scales = np.array([-3.5, 0.02, 7.0])

    scaled = mac(aligned.test * scales[None, :], aligned.fe * -1.25)

    np.testing.assert_allclose(scaled, reference, atol=1.0e-14)


def test_mac_of_a_complex_mode_ignores_its_phase(aligned) -> None:
    complex_test = aligned.test.astype(complex) * np.exp(1j * 0.7)

    assert mac_value(complex_test[:, 0], aligned.fe[:, 0]) == pytest.approx(1.0, abs=1.0e-14)


def test_automac_of_the_analytical_set_is_the_identity(fixture_data) -> None:
    shapes = shapes_of(fixture_data["analytical"])

    np.testing.assert_allclose(automac(shapes), np.eye(3), atol=1.0e-14)


def test_automac_exposes_a_sensor_set_that_cannot_separate_two_modes() -> None:
    # Sensors only on the first two DOFs see modes 2 and 3 as the same shape.
    shapes = np.array([[1.0, 1.0, 1.0], [1.0, -1.0, -1.0], [1.0, 2.0, -2.0]])

    reduced = automac(shapes[:2, :])

    assert reduced[1, 2] == pytest.approx(1.0, abs=1.0e-14)
    assert automac(shapes)[1, 2] < 0.9


def test_mass_weighted_mac_of_mass_normalized_modes_is_the_identity() -> None:
    mass = np.diag([2.0, 1.0, 3.0])
    stiffness = np.array([[2000.0, -800.0, 0.0], [-800.0, 1400.0, -600.0], [0.0, -600.0, 600.0]])
    shapes = _mass_normalized_modes(stiffness, mass)

    np.testing.assert_allclose(mac(shapes, shapes, mass), np.eye(3), atol=1.0e-12)
    np.testing.assert_allclose(orthogonality(shapes, shapes, mass), np.eye(3), atol=1.0e-12)


def test_orthogonality_unlike_mac_also_checks_the_normalization() -> None:
    mass = np.diag([2.0, 1.0, 3.0])
    stiffness = np.array([[2000.0, -800.0, 0.0], [-800.0, 1400.0, -600.0], [0.0, -600.0, 600.0]])
    shapes = _mass_normalized_modes(stiffness, mass)

    rescaled = shapes * np.array([1.0, 4.0, 1.0])

    np.testing.assert_allclose(mac(shapes, rescaled, mass), np.eye(3), atol=1.0e-12)
    assert orthogonality(shapes, rescaled, mass)[1, 1] == pytest.approx(4.0, abs=1.0e-12)


def test_modal_scale_factor_brings_a_measured_shape_onto_the_model_scale(aligned) -> None:
    phi_fe = aligned.fe[:, 1]
    phi_test = aligned.test[:, 1]

    factor = modal_scale_factor(phi_fe, phi_test)

    assert factor == pytest.approx(-0.8, rel=1.0e-12)
    np.testing.assert_allclose(factor * phi_test, phi_fe, atol=1.0e-14)


def test_comac_of_the_fixture_pair_is_one_at_every_shared_dof(aligned) -> None:
    np.testing.assert_allclose(comac(aligned.test, aligned.fe), np.ones(3), atol=1.0e-12)


def test_comac_localizes_a_single_faulty_sensor(aligned) -> None:
    faulty = 1
    measured = aligned.test.copy()
    measured[faulty, :] *= np.array([0.4, -1.8, 0.3])  # inconsistent across modes

    values = comac(measured, aligned.fe)

    assert int(np.argmin(values)) == faulty
    assert values[faulty] < 0.9
    assert np.delete(values, faulty).min() > 0.95


def test_mac_rejects_mismatched_dof_counts_and_null_shapes(aligned) -> None:
    with pytest.raises(ValueError, match="DOF mismatch"):
        mac(aligned.test, np.ones((4, 2)))
    with pytest.raises(ValueError, match="zero-norm"):
        mac(aligned.test, np.zeros((3, 1)))


# ---------------------------------------------------------------------------
# Mode pairing (MS-2.3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["greedy", "optimal"])
def test_pairing_recovers_a_shuffled_mode_order(aligned, fixture_data, method: str) -> None:
    permutation = [2, 0, 1]
    fe_shapes = aligned.fe[:, permutation]
    fe_frequencies = np.asarray(fixture_data["analytical"]["frequencies_hz"])[permutation]

    pairing = pair_modes(
        test_shapes=aligned.test,
        fe_shapes=fe_shapes,
        test_frequencies=fixture_data["experimental"]["frequencies_hz"],
        fe_frequencies=fe_frequencies,
        method=method,
    )

    assert pairing.as_tuples() == [(0, 1), (1, 2), (2, 0)]
    assert pairing.mac_values.min() > MATCHED_MAC_GATE
    assert not pairing.unpaired_test and not pairing.unpaired_fe


def test_pairing_leaves_a_missing_test_mode_unpaired(aligned, fixture_data) -> None:
    # The test campaign missed the second mode; the FE model still predicts it.
    measured = aligned.test[:, [0, 2]]
    measured_frequencies = [10.1, 30.6]

    pairing = pair_modes(
        test_shapes=measured,
        fe_shapes=aligned.fe,
        test_frequencies=measured_frequencies,
        fe_frequencies=fixture_data["analytical"]["frequencies_hz"],
        mac_threshold=0.7,
    )

    assert pairing.as_tuples() == [(0, 0), (1, 2)]
    assert pairing.unpaired_fe == [1]
    assert pairing.unpaired_test == []


def test_pairing_reports_an_uncorrelated_mode_instead_of_forcing_a_pair(aligned) -> None:
    noise = np.array([[1.0], [-1.0], [0.0]])  # unrelated to any analytical mode
    measured = np.hstack([aligned.test[:, :1], noise])

    pairing = pair_modes(test_shapes=measured, fe_shapes=aligned.fe, mac_threshold=0.7)

    assert pairing.as_tuples() == [(0, 0)]
    assert pairing.unpaired_test == [1]
    assert sorted(pairing.unpaired_fe) == [1, 2]


def test_frequency_pairing_works_without_any_mode_shapes(fixture_data) -> None:
    pairing = pair_modes(
        test_frequencies=fixture_data["experimental"]["frequencies_hz"],
        fe_frequencies=fixture_data["analytical"]["frequencies_hz"],
    )

    assert pairing.as_tuples() == [(0, 0), (1, 1), (2, 2)]
    assert pairing.method == "frequency"
    assert np.isnan(pairing.mac_values).all()


def test_frequency_tolerance_rejects_a_distant_candidate(aligned, fixture_data) -> None:
    pairing = pair_modes(
        test_shapes=aligned.test,
        fe_shapes=aligned.fe,
        test_frequencies=fixture_data["experimental"]["frequencies_hz"],
        fe_frequencies=[10.0, 20.0, 45.0],
        frequency_tolerance_pct=5.0,
    )

    assert pairing.as_tuples() == [(0, 0), (1, 1)]
    assert pairing.unpaired_test == [2]
    assert pairing.unpaired_fe == [2]


def test_frequency_penalty_separates_two_equally_shaped_candidates() -> None:
    # Two FE modes with the same shape: only the frequency can decide.
    shape = np.array([[1.0], [0.5], [-0.25]])
    fe_shapes = np.hstack([shape, shape])

    without = pair_modes(
        test_shapes=shape,
        fe_shapes=fe_shapes,
        test_frequencies=[12.0],
        fe_frequencies=[30.0, 12.4],
    )
    with_penalty = pair_modes(
        test_shapes=shape,
        fe_shapes=fe_shapes,
        test_frequencies=[12.0],
        fe_frequencies=[30.0, 12.4],
        freq_penalty=0.1,
    )

    assert without.as_tuples() == [(0, 0)]  # ties broken by column order
    assert with_penalty.as_tuples() == [(0, 1)]


def test_optimal_pairing_maximizes_the_total_correlation() -> None:
    from itertools import permutations

    rng = np.random.default_rng(11)
    test_shapes = rng.standard_normal((8, 4))
    fe_shapes = rng.standard_normal((8, 4))
    macs = mac(test_shapes, fe_shapes)
    best = max(sum(macs[i, order[i]] for i in range(4)) for order in permutations(range(4)))

    optimal = pair_modes(test_shapes=test_shapes, fe_shapes=fe_shapes, method="optimal")
    greedy = pair_modes(test_shapes=test_shapes, fe_shapes=fe_shapes, method="greedy")

    assert optimal.mac_values.sum() == pytest.approx(best)
    assert optimal.mac_values.sum() >= greedy.mac_values.sum()


# ---------------------------------------------------------------------------
# Frequency metrics (MS-2.4)
# ---------------------------------------------------------------------------


def test_fixture_frequency_errors_reproduce_the_expected_table(fixture_data) -> None:
    expected = fixture_data["expected"]["relative_frequency_error_percent"]
    tolerance = fixture_data["tolerances"]["frequency_error_percent_absolute"]
    # The fixture states the measured frequency relative to the analytical one,
    # so here the analytical set takes the reference (denominator) role.
    difference = frequency_difference(
        test_frequencies=fixture_data["analytical"]["frequencies_hz"],
        fe_frequencies=fixture_data["experimental"]["frequencies_hz"],
    )

    np.testing.assert_allclose(difference.percent, expected, atol=tolerance)
    np.testing.assert_allclose(difference.absolute, [0.1, -0.2, 0.6], atol=1.0e-12)
    assert difference.max_abs_percent == pytest.approx(2.0, abs=tolerance)
    assert difference.mean_abs_percent == pytest.approx(4.0 / 3.0, abs=tolerance)


def test_frequency_error_is_positive_when_the_model_is_too_stiff() -> None:
    # AC-CORR-005: the test data is the reference, the FE model is judged.
    errors = relative_frequency_error(test_frequencies=[10.0, 20.0], fe_frequencies=[10.5, 19.0])

    np.testing.assert_allclose(errors, [0.05, -0.05], atol=1.0e-15)


def test_frequency_error_of_a_rigid_body_mode_stays_finite_free() -> None:
    errors = relative_frequency_error([0.0, 0.0, 10.0], [0.0, 1.5, 10.0])

    assert errors[0] == 0.0
    assert np.isposinf(errors[1])
    assert errors[2] == 0.0


def test_frequency_vectors_of_different_length_are_rejected() -> None:
    with pytest.raises(ValueError, match="equal length"):
        relative_frequency_error([1.0, 2.0], [1.0])


# ---------------------------------------------------------------------------
# Summary and report (MS-2.6, MS-4.2)
# ---------------------------------------------------------------------------


def test_summary_of_the_fixture_passes_the_validation_gates(aligned, fixture_data) -> None:
    summary = correlation_summary(
        test_frequencies=fixture_data["experimental"]["frequencies_hz"],
        fe_frequencies=fixture_data["analytical"]["frequencies_hz"],
        test_shapes=aligned.test,
        fe_shapes=aligned.fe,
    )

    assert summary.n_paired == 3
    assert summary.min_mac > MATCHED_MAC_GATE
    assert summary.mean_mac == pytest.approx(1.0, abs=1.0e-12)
    assert summary.max_off_diagonal_mac < 0.2
    assert summary.max_abs_freq_error_pct == pytest.approx(100.0 * 0.6 / 30.6, abs=1.0e-9)
    assert summary.is_correlated(mac_threshold=MATCHED_MAC_GATE, freq_tolerance_pct=2.0)
    assert "mean / min MAC" in summary.report()


def test_summary_fails_the_gate_when_a_mode_is_badly_correlated(aligned, fixture_data) -> None:
    degraded = aligned.fe.copy()
    degraded[:, 2] = [1.0, -1.0, 0.0]

    summary = correlation_summary(
        test_frequencies=fixture_data["experimental"]["frequencies_hz"],
        fe_frequencies=fixture_data["analytical"]["frequencies_hz"],
        test_shapes=aligned.test,
        fe_shapes=degraded,
    )

    assert not summary.is_correlated(mac_threshold=MATCHED_MAC_GATE)


def test_report_serializes_the_whole_correlation_to_json(aligned, fixture_data) -> None:
    import json

    report = correlation_report(
        test_frequencies=fixture_data["experimental"]["frequencies_hz"],
        fe_frequencies=fixture_data["analytical"]["frequencies_hz"],
        aligned=aligned,
    )

    payload = json.loads(report.to_json())

    assert payload["schema_version"] == SCHEMA_VERSION == "1.1"
    assert payload["frf"] is None  # the key exists even without an FRF comparison
    assert payload["dof_labels"] == fixture_data["expected"]["shared_dof_labels"]
    assert [pair["mac"] for pair in payload["pairs"]] == pytest.approx([1.0, 1.0, 1.0])
    assert [[pair["test_index"], pair["fe_index"]] for pair in payload["pairs"]] == fixture_data[
        "expected"
    ]["paired_mode_indices"]
    assert np.allclose(payload["comac"], 1.0)
    assert np.array(payload["mac_matrix"]).shape == (3, 3)
    assert payload["summary"]["n_paired"] == 3


def test_report_names_the_worst_correlation_dof(aligned, fixture_data) -> None:
    measured = aligned.test.copy()
    measured[2, :] *= np.array([0.2, -1.5, 0.9])

    report = correlation_report(
        test_frequencies=fixture_data["experimental"]["frequencies_hz"],
        fe_frequencies=fixture_data["analytical"]["frequencies_hz"],
        test_shapes=measured,
        fe_shapes=aligned.fe,
        dof_labels=aligned.labels,
    )

    index, value = report.worst_comac_dof()
    assert index == 2
    assert value < 0.95
    assert "node_4:x" in report.report()


def test_full_pipeline_from_the_fixture_files(fixture_data) -> None:
    io = pytest.importorskip("openfemlab.io")

    analytical = io.read_modal_result(MODE_FIXTURE)
    measured = io.read_test_data(MODE_FIXTURE)

    report = correlate_modal_data(analytical, measured)

    assert report.meta["n_correlation_dofs"] == 3
    assert report.meta["n_unmatched_fe_dofs"] == 1  # node_2 is not instrumented
    assert report.meta["n_unmatched_test_dofs"] == 0
    assert report.pairing.as_tuples() == [
        tuple(pair) for pair in fixture_data["expected"]["paired_mode_indices"]
    ]
    assert report.min_mac > MATCHED_MAC_GATE
    np.testing.assert_allclose(
        report.summary.mac_values,
        fixture_data["expected"]["mac_diagonal"],
        atol=fixture_data["tolerances"]["mac_absolute"],
    )
    assert report.is_correlated(mac_threshold=MATCHED_MAC_GATE, freq_tolerance_pct=2.0)


def test_noisy_measurements_stay_above_the_acceptance_gate(aligned, fixture_data) -> None:
    rng = np.random.default_rng(20240826)
    noisy = aligned.test * (1.0 + 0.02 * rng.standard_normal(aligned.test.shape))
    noisy_frequencies = np.asarray(fixture_data["experimental"]["frequencies_hz"]) * (
        1.0 + 0.002 * rng.standard_normal(3)
    )

    report = correlation_report(
        test_frequencies=noisy_frequencies,
        fe_frequencies=fixture_data["analytical"]["frequencies_hz"],
        test_shapes=noisy,
        fe_shapes=aligned.fe,
        mac_threshold=0.7,
    )

    assert report.pairing.as_tuples() == [(0, 0), (1, 1), (2, 2)]
    assert report.min_mac > MATCHED_MAC_GATE
    assert report.summary.max_off_diagonal_mac < 0.5


# ---------------------------------------------------------------------------
# Spring-mass chain cases (reconciled from the R1-O2 correlation branch)
#
# The fixture cases above pin the documented reference numbers; these drive the
# same API from the analytic chain in ``tests.modal_reference``, so correlation
# stays covered independently of the fixture files and of the FE core.
# ---------------------------------------------------------------------------


def test_mac_matrix_alias_matches_the_pairwise_mac_value() -> None:
    rng = np.random.default_rng(7)
    a = rng.normal(size=(6, 3))
    b = rng.normal(size=(6, 4))

    matrix = mac_matrix(a, b)

    assert matrix.shape == (3, 4)
    for i in range(3):
        for j in range(4):
            assert matrix[i, j] == pytest.approx(mac_value(a[:, i], b[:, j]))


def test_mac_matrix_alias_rejects_different_dof_counts() -> None:
    with pytest.raises(ValueError, match="DOF mismatch"):
        mac_matrix(np.ones((4, 2)), np.ones((5, 2)))


def test_auto_mac_alias_separates_the_modes_of_a_two_dof_chain() -> None:
    modes = two_dof_chain().modes()

    matrix = auto_mac(modes.mode_shapes)

    assert np.allclose(np.diag(matrix), 1.0)
    # Mass-normalised modes of a non-uniform chain are not Euclidean
    # orthogonal, but they must remain clearly distinguishable.
    assert matrix[0, 1] < 0.2


def test_dof_weights_can_mask_out_a_polluted_sensor() -> None:
    phi_test = np.array([1.0, 0.6, 0.2])
    phi_fe = np.array([1.0, 0.6, -5.0])

    assert mac_value(phi_test, phi_fe) < 0.2
    assert mac_value(phi_test, phi_fe, np.array([1.0, 1.0, 0.0])) == pytest.approx(1.0)


def test_frequency_difference_rejects_unequal_lengths() -> None:
    with pytest.raises(ValueError):
        frequency_difference([1.0, 2.0], [1.0])


def test_frequency_error_matrix_is_relative_to_the_test_frequency() -> None:
    matrix = frequency_error_matrix([10.0, 20.0], [11.0, 22.0])

    assert matrix[0, 0] == pytest.approx(10.0)
    assert matrix[1, 1] == pytest.approx(10.0)
    assert matrix[0, 1] == pytest.approx(120.0)


def test_frequency_only_pairing_picks_the_closest_frequency_not_the_order() -> None:
    pairing = pair_modes(test_frequencies=[10.0, 25.0], fe_frequencies=[24.0, 10.4])

    assert pairing.as_tuples() == [(0, 1), (1, 0)]
    assert pairing.method == "frequency"
    assert np.isnan(pairing.mac_values).all()


def test_frequency_tolerance_can_leave_every_mode_unpaired() -> None:
    modes = uniform_chain(2).modes()

    pairing = pair_modes(
        test_shapes=modes.mode_shapes,
        fe_shapes=modes.mode_shapes,
        test_frequencies=modes.frequencies,
        fe_frequencies=modes.frequencies * 1.5,
        frequency_tolerance_pct=10.0,
    )

    assert len(pairing) == 0
    assert pairing.unpaired_test == [0, 1]
    assert pairing.unpaired_fe == [0, 1]


def test_optimal_and_greedy_pairing_agree_on_a_cleanly_separated_case() -> None:
    modes = uniform_chain(6).modes()
    fe_shapes = modes.mode_shapes[:, [1, 0, 3, 2, 5, 4]]

    greedy = pair_modes(test_shapes=modes.mode_shapes, fe_shapes=fe_shapes, method="greedy")
    optimal = pair_modes(test_shapes=modes.mode_shapes, fe_shapes=fe_shapes, method="optimal")

    assert greedy.as_tuples() == optimal.as_tuples()


def test_unknown_pairing_method_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown pairing method"):
        pair_modes(test_frequencies=[1.0], fe_frequencies=[1.0], method="magic")


def test_pairing_table_lists_every_pair() -> None:
    modes = two_dof_chain().modes()

    table = pair_modes(
        test_shapes=modes.mode_shapes,
        fe_shapes=modes.mode_shapes,
        test_frequencies=modes.frequencies,
        fe_frequencies=modes.frequencies,
    ).table()

    assert table.count("\n") == 3  # header, rule and two pairs
    assert "MAC" in table


def test_correlate_reports_a_perfect_correlation() -> None:
    modes = two_dof_chain().modes()

    summary = correlate(
        modes.frequencies, modes.frequencies, modes.mode_shapes, modes.mode_shapes
    )

    assert summary.n_paired == 2
    assert summary.mean_mac == pytest.approx(1.0)
    assert summary.max_abs_freq_error_pct == pytest.approx(0.0)
    assert summary.is_correlated()


def test_summary_error_statistics_expose_a_stiff_model() -> None:
    chain = two_dof_chain()
    test = chain.modes()
    fe = chain.modes(stiffness_scales=[1.3, 0.8])

    summary = correlation_summary(
        test_frequencies=test.frequencies,
        fe_frequencies=fe.frequencies,
        test_shapes=test.mode_shapes,
        fe_shapes=fe.mode_shapes,
    )

    expected = 100.0 * (fe.frequencies - test.frequencies) / test.frequencies
    assert summary.n_paired == 2
    assert summary.mean_mac < 0.999
    assert not summary.is_correlated(mac_threshold=0.999, freq_tolerance_pct=1.0)
    assert summary.mean_signed_freq_error_pct == pytest.approx(np.mean(expected))
    assert summary.rms_freq_error_pct == pytest.approx(np.sqrt(np.mean(expected**2)))


def test_summary_is_serializable_to_a_flat_dict() -> None:
    modes = two_dof_chain().modes()

    data = correlate(
        modes.frequencies, modes.frequencies, modes.mode_shapes, modes.mode_shapes
    ).as_dict()

    assert data["n_paired"] == 2
    assert set(data) >= {"mean_mac", "max_abs_freq_error_pct", "max_off_diagonal_mac"}


def test_off_diagonal_mac_flags_a_duplicated_fe_mode() -> None:
    modes = uniform_chain(4).modes()
    fe_shapes = modes.mode_shapes.copy()
    fe_shapes[:, 2] = modes.mode_shapes[:, 1]

    pairing = pair_modes(test_shapes=modes.mode_shapes, fe_shapes=fe_shapes)

    assert off_diagonal_mac(pairing.mac_matrix, pairing) > 0.9


def test_normalized_frequency_residual_follows_the_pairing() -> None:
    pairing = pair_modes(test_frequencies=[10.0, 20.0], fe_frequencies=[22.0, 10.5])

    residual = normalized_frequency_residual([10.0, 20.0], [22.0, 10.5], pairing)

    assert residual == pytest.approx([0.05, 0.10])


def test_correlation_from_a_measured_dof_subset() -> None:
    chain = uniform_chain(6)
    measured = [0, 2, 4]
    test = chain.modes(n_modes=3, dofs=measured)
    fe = chain.modes(n_modes=3, stiffness_scales=np.full(6, 1.1), dofs=measured)

    summary = correlate(test.frequencies, fe.frequencies, test.mode_shapes, fe.mode_shapes)

    assert summary.n_paired == 3
    # A uniform stiffness scaling leaves the mode shapes untouched.
    assert summary.min_mac == pytest.approx(1.0)
    assert summary.max_abs_freq_error_pct == pytest.approx(100.0 * (np.sqrt(1.1) - 1.0), rel=1e-6)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _mass_normalized_modes(stiffness: np.ndarray, mass: np.ndarray) -> np.ndarray:
    """Modes of ``K φ = λ M φ`` scaled so that ``Φᵀ M Φ = I``."""
    scale = 1.0 / np.sqrt(np.diag(mass))
    reduced = stiffness * scale[:, None] * scale[None, :]
    _, vectors = np.linalg.eigh(0.5 * (reduced + reduced.T))
    return vectors * scale[:, None]
