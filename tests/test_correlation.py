"""Tests for the FE/test correlation module (MAC, COMAC, pairing, metrics)."""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.correlation import (
    auto_mac,
    comac,
    correlate,
    correlation_summary,
    frequency_difference,
    frequency_error_matrix,
    mac,
    mac_matrix,
    modal_scale_factor,
    normalized_frequency_residual,
    off_diagonal_mac,
    pair_modes,
)
from tests.modal_reference import two_dof_chain, uniform_chain


# --------------------------------------------------------------------- MAC


def test_mac_of_identical_shape_is_one():
    phi = np.array([1.0, -0.5, 0.25])
    assert mac(phi, phi) == pytest.approx(1.0)


def test_mac_is_insensitive_to_scaling_and_sign():
    phi = np.array([1.0, -0.5, 0.25])
    assert mac(phi, -3.7 * phi) == pytest.approx(1.0)


def test_mac_of_orthogonal_shapes_is_zero():
    assert mac([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_mac_of_null_shape_is_zero():
    assert mac([0.0, 0.0], [1.0, 2.0]) == 0.0


def test_mac_handles_complex_modes():
    phi = np.array([1.0 + 1.0j, 0.5 - 0.25j])
    assert mac(phi, phi * (0.3 - 1.2j)) == pytest.approx(1.0)
    assert 0.0 <= mac(phi, np.conj(phi)) <= 1.0


def test_mac_rejects_incompatible_sizes():
    with pytest.raises(ValueError):
        mac([1.0, 2.0], [1.0, 2.0, 3.0])


def test_mac_matrix_matches_pairwise_mac():
    rng = np.random.default_rng(7)
    a = rng.normal(size=(6, 3))
    b = rng.normal(size=(6, 4))
    matrix = mac_matrix(a, b)
    assert matrix.shape == (3, 4)
    for i in range(3):
        for j in range(4):
            assert matrix[i, j] == pytest.approx(mac(a[:, i], b[:, j]))


def test_mac_matrix_rejects_different_dof_counts():
    with pytest.raises(ValueError):
        mac_matrix(np.ones((4, 2)), np.ones((5, 2)))


def test_auto_mac_of_mass_orthogonal_modes_is_the_identity():
    modes = two_dof_chain().modes()
    matrix = auto_mac(modes.mode_shapes)
    assert np.allclose(np.diag(matrix), 1.0)
    # Mass-normalised modes of a non-uniform chain are not Euclidean orthogonal,
    # but they must remain clearly distinguishable.
    assert matrix[0, 1] < 0.2


def test_dof_weights_can_mask_out_a_polluted_sensor():
    phi_test = np.array([1.0, 0.6, 0.2])
    phi_fe = np.array([1.0, 0.6, -5.0])
    weights = np.array([1.0, 1.0, 0.0])
    assert mac(phi_test, phi_fe) < 0.2
    assert mac(phi_test, phi_fe, weights=weights) == pytest.approx(1.0)


def test_modal_scale_factor_rescales_the_fe_shape():
    phi_test = np.array([2.0, -1.0, 0.5])
    phi_fe = -0.25 * phi_test
    msf = modal_scale_factor(phi_test, phi_fe)
    assert msf == pytest.approx(-4.0)
    assert np.allclose(msf * phi_fe, phi_test)


# ------------------------------------------------------------- frequencies


def test_frequency_difference_reports_signed_relative_error():
    difference = frequency_difference([10.0, 20.0], [11.0, 19.0])
    assert difference.absolute == pytest.approx([1.0, -1.0])
    assert difference.percent == pytest.approx([10.0, -5.0])
    assert difference.max_abs_percent == pytest.approx(10.0)
    assert difference.mean_abs_percent == pytest.approx(7.5)
    assert difference.rms_percent == pytest.approx(np.sqrt((100.0 + 25.0) / 2.0))


def test_frequency_difference_rejects_unequal_lengths():
    with pytest.raises(ValueError):
        frequency_difference([1.0, 2.0], [1.0])


def test_frequency_error_matrix_is_relative_to_the_test_frequency():
    matrix = frequency_error_matrix([10.0, 20.0], [11.0, 22.0])
    assert matrix[0, 0] == pytest.approx(10.0)
    assert matrix[1, 1] == pytest.approx(10.0)
    assert matrix[0, 1] == pytest.approx(120.0)


# ----------------------------------------------------------------- pairing


def test_pairing_recovers_a_permuted_mode_order():
    modes = uniform_chain(5).modes()
    permutation = [2, 0, 4, 1, 3]
    fe_shapes = modes.mode_shapes[:, permutation]
    fe_frequencies = modes.frequencies[permutation]

    pairing = pair_modes(
        test_shapes=modes.mode_shapes,
        fe_shapes=fe_shapes,
        test_frequencies=modes.frequencies,
        fe_frequencies=fe_frequencies,
    )

    assert len(pairing) == 5
    assert list(pairing.fe_indices) == [permutation.index(i) for i in range(5)]
    assert np.allclose(pairing.mac_values, 1.0)
    assert np.allclose(pairing.frequency_errors_pct, 0.0)
    assert pairing.unpaired_test == [] and pairing.unpaired_fe == []


def test_pairing_leaves_uncorrelated_modes_unpaired():
    modes = uniform_chain(4).modes()
    fe_shapes = modes.mode_shapes.copy()
    fe_shapes[:, 3] = np.array([1.0, -1.0, 1.0, -1.0]) * 1e-3 + 0.0
    pairing = pair_modes(
        test_shapes=modes.mode_shapes,
        fe_shapes=fe_shapes,
        test_frequencies=modes.frequencies,
        fe_frequencies=modes.frequencies,
        mac_threshold=0.95,
    )
    assert len(pairing) < 4
    assert 3 in pairing.unpaired_test or 3 in pairing.unpaired_fe


def test_frequency_tolerance_blocks_distant_candidates():
    modes = uniform_chain(3).modes()
    shifted = modes.frequencies * 1.5
    pairing = pair_modes(
        test_shapes=modes.mode_shapes,
        fe_shapes=modes.mode_shapes,
        test_frequencies=modes.frequencies,
        fe_frequencies=shifted,
        frequency_tolerance_pct=10.0,
    )
    assert len(pairing) == 0
    assert pairing.unpaired_test == [0, 1, 2]


def test_frequency_only_pairing_uses_closest_frequency():
    pairing = pair_modes(
        test_frequencies=[10.0, 25.0],
        fe_frequencies=[24.0, 10.4],
    )
    assert [(p.test_index, p.fe_index) for p in pairing] == [(0, 1), (1, 0)]
    assert pairing.method == "frequency"
    assert np.isnan(pairing.mac_values).all()


def test_optimal_and_greedy_pairing_agree_on_a_clean_case():
    modes = uniform_chain(6).modes()
    permutation = [1, 0, 3, 2, 5, 4]
    fe_shapes = modes.mode_shapes[:, permutation]
    greedy = pair_modes(test_shapes=modes.mode_shapes, fe_shapes=fe_shapes, method="greedy")
    optimal = pair_modes(test_shapes=modes.mode_shapes, fe_shapes=fe_shapes, method="optimal")
    assert [(p.test_index, p.fe_index) for p in greedy] == [
        (p.test_index, p.fe_index) for p in optimal
    ]


def test_unknown_pairing_method_is_rejected():
    with pytest.raises(ValueError):
        pair_modes(test_frequencies=[1.0], fe_frequencies=[1.0], method="magic")


def test_pairing_table_lists_every_pair():
    modes = two_dof_chain().modes()
    pairing = pair_modes(
        test_shapes=modes.mode_shapes,
        fe_shapes=modes.mode_shapes,
        test_frequencies=modes.frequencies,
        fe_frequencies=modes.frequencies,
    )
    table = pairing.table()
    assert table.count("\n") == 3  # header, rule and two pairs
    assert "MAC" in table


# ----------------------------------------------------------------- metrics


def test_summary_of_a_perfect_correlation():
    modes = two_dof_chain().modes()
    summary = correlate(
        modes.frequencies, modes.frequencies, modes.mode_shapes, modes.mode_shapes
    )
    assert summary.n_paired == 2
    assert summary.mean_mac == pytest.approx(1.0)
    assert summary.min_mac == pytest.approx(1.0)
    assert summary.max_abs_freq_error_pct == pytest.approx(0.0)
    assert summary.is_correlated()
    assert "mean / min MAC" in summary.report()


def test_summary_detects_a_stiff_model():
    chain = two_dof_chain()
    test = chain.modes()
    fe = chain.modes(stiffness_scales=[1.3, 0.8])

    summary = correlation_summary(
        test_frequencies=test.frequencies,
        fe_frequencies=fe.frequencies,
        test_shapes=test.mode_shapes,
        fe_shapes=fe.mode_shapes,
    )
    assert summary.n_paired == 2
    assert summary.mean_mac < 0.999
    assert summary.max_abs_freq_error_pct > 1.0
    assert not summary.is_correlated(mac_threshold=0.999, freq_tolerance_pct=1.0)
    expected = 100.0 * (fe.frequencies - test.frequencies) / test.frequencies
    assert summary.mean_signed_freq_error_pct == pytest.approx(np.mean(expected))
    assert summary.rms_freq_error_pct == pytest.approx(np.sqrt(np.mean(expected**2)))


def test_summary_is_serialisable_to_a_flat_dict():
    modes = two_dof_chain().modes()
    summary = correlate(
        modes.frequencies, modes.frequencies, modes.mode_shapes, modes.mode_shapes
    )
    data = summary.as_dict()
    assert data["n_paired"] == 2
    assert set(data) >= {"mean_mac", "max_abs_freq_error_pct", "max_off_diagonal_mac"}


def test_off_diagonal_mac_flags_a_near_duplicate_mode():
    modes = uniform_chain(4).modes()
    fe_shapes = modes.mode_shapes.copy()
    fe_shapes[:, 2] = modes.mode_shapes[:, 1]  # duplicated mode
    pairing = pair_modes(test_shapes=modes.mode_shapes, fe_shapes=fe_shapes)
    assert off_diagonal_mac(pairing.mac_matrix, pairing) > 0.9


def test_comac_is_one_for_identical_mode_sets():
    modes = uniform_chain(5).modes()
    assert np.allclose(comac(modes.mode_shapes, modes.mode_shapes), 1.0)


def test_comac_localises_a_corrupted_dof():
    modes = uniform_chain(5).modes()
    fe_shapes = modes.mode_shapes.copy()
    fe_shapes[2, :] += 0.7 * np.array([1.0, -1.0, 1.0, -1.0, 1.0]) * np.abs(fe_shapes[2, :]).max()
    values = comac(modes.mode_shapes, fe_shapes)
    assert values[2] == pytest.approx(values.min())
    assert values[2] < 0.99


def test_normalized_frequency_residual_follows_the_pairing():
    pairing = pair_modes(test_frequencies=[10.0, 20.0], fe_frequencies=[22.0, 10.5])
    residual = normalized_frequency_residual([10.0, 20.0], [22.0, 10.5], pairing)
    assert residual == pytest.approx([0.05, 0.10])


def test_correlation_of_measured_dof_subset():
    chain = uniform_chain(6)
    measured = [0, 2, 4]
    test = chain.modes(n_modes=3, dofs=measured)
    fe = chain.modes(n_modes=3, stiffness_scales=np.full(6, 1.1), dofs=measured)

    summary = correlate(test.frequencies, fe.frequencies, test.mode_shapes, fe.mode_shapes)
    assert summary.n_paired == 3
    # A uniform stiffness scaling leaves the mode shapes untouched.
    assert summary.min_mac == pytest.approx(1.0)
    assert summary.max_abs_freq_error_pct == pytest.approx(
        100.0 * (np.sqrt(1.1) - 1.0), rel=1e-6
    )
