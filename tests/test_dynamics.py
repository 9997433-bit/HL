"""Verification of the damped-dynamics chain: damping, complex modes, FRFs.

Analytic references used here
-----------------------------
Rayleigh damping ``C = alpha M + beta K``::

    zeta(omega) = alpha / (2 omega) + beta omega / 2
    min zeta    = sqrt(alpha beta)   at   omega = sqrt(alpha / beta)

Damped SDOF oscillator ``m x'' + c x' + k x = f``, ``omega_0 = sqrt(k/m)``,
``zeta = c / (2 m omega_0)``::

    poles      s = -zeta omega_0 +/- i omega_0 sqrt(1 - zeta^2)   (zeta < 1)
    receptance H(omega) = 1 / (k - omega^2 m + i omega c)
    at resonance |H(omega_0)| = 1 / (omega_0 c)

Overdamped SDOF (``zeta > 1``) has two real poles with ``s1 s2 = k/m`` and
``s1 + s2 = -c/m``.

The strongest checks in this file are consistency ones: with every mode
retained, real-mode superposition (proportional damping) and complex-mode
residue superposition (arbitrary damping) must both reproduce the direct
inversion of ``Z(omega) = K - omega^2 M + i omega C`` to machine precision.
"""

from __future__ import annotations

import numpy as np
import pytest
import scipy.sparse as sp

from openfemlab import DOF, Material, ModalSolver, Section, SolverError
from openfemlab.mesh.simple import bar_mesh, beam_mesh, spring_mass_chain
from openfemlab.solver.dynamics import (
    ComplexModalResult,
    FrequencyResponse,
    ModalDamping,
    RayleighDamping,
    StructuralDamping,
    complex_modal_frf,
    complex_modes,
    damped_matrices,
    damping_matrix,
    direct_frf,
    fdac,
    frac,
    harmonic_response,
    is_proportional,
    modal_damping_matrix,
    modal_frf,
    modal_phase_collinearity,
    proportionality_index,
    residual_flexibility,
)

STEEL = Material(E=2.1e11, density=7850.0, nu=0.3, name="steel")
SQUARE = Section(area=1e-4, inertia_z=1e-4**2 / 12.0, name="10x10 mm")


# --------------------------------------------------------------------- helpers


def chain_matrices(num_masses=4, stiffness=1000.0, mass=1.0, damping=None):
    """Free-DOF dense ``(K, M, C)`` of a fixed-free spring/mass chain."""
    model = spring_mass_chain(num_masses, stiffness, mass)
    K, M, C, free = damped_matrices(model, damping=damping)
    grid = np.ix_(free, free)
    K_d = K.toarray()[grid]
    M_d = M.toarray()[grid]
    C_d = None
    if C is not None:
        C_d = (C.toarray() if sp.issparse(C) else np.asarray(C))[grid]
    return K_d, M_d, C_d


def real_modes(K, M, num_modes=None):
    """Mass-normalized real modes of the dense pair, ascending."""
    solver = ModalSolver.from_matrices(sp.csr_matrix(K), sp.csr_matrix(M))
    result = solver.solve(num_modes=num_modes or K.shape[0], sparse=False)
    return result


def mac(a, b):
    """MAC between two (possibly complex) shape vectors."""
    numerator = abs(np.vdot(a, b)) ** 2
    return float(numerator / (np.vdot(a, a).real * np.vdot(b, b).real))


def impedance_inverse(frequency, K, M, C):
    omega = 2.0 * np.pi * frequency
    return np.linalg.inv(K - omega**2 * M + 1j * omega * C)


# ================================================================== Rayleigh


def test_rayleigh_matrix_is_the_linear_combination():
    K, M, _ = chain_matrices()
    model = RayleighDamping(alpha=0.3, beta=1e-4)
    np.testing.assert_allclose(model.matrix(K, M), 0.3 * M + 1e-4 * K)


def test_rayleigh_matrix_preserves_sparsity():
    K, M, _ = chain_matrices()
    result = RayleighDamping(alpha=0.2, beta=2e-4).matrix(sp.csr_matrix(K), sp.csr_matrix(M))
    assert sp.issparse(result)
    np.testing.assert_allclose(result.toarray(), 0.2 * M + 2e-4 * K)


def test_rayleigh_from_frequencies_hits_both_anchors_exactly():
    model = RayleighDamping.from_frequencies(2.0, 20.0, 0.02, 0.05)
    omega = 2.0 * np.pi * np.array([2.0, 20.0])
    np.testing.assert_allclose(model.damping_ratios(omega), [0.02, 0.05], rtol=1e-14)


def test_rayleigh_equal_ratio_anchors_bracket_the_minimum():
    model = RayleighDamping.from_frequencies(1.0, 100.0, 0.03)
    omega = 2.0 * np.pi * np.array([1.0, 100.0])
    np.testing.assert_allclose(model.damping_ratios(omega), [0.03, 0.03], rtol=1e-14)
    assert model.minimum_ratio < 0.03
    assert 2.0 * np.pi < model.critical_angular_frequency < 2.0 * np.pi * 100.0


def test_rayleigh_ratio_curve_follows_the_closed_form():
    model = RayleighDamping(alpha=0.4, beta=5e-4)
    omega = np.linspace(1.0, 500.0, 25)
    expected = 0.5 * model.alpha / omega + 0.5 * model.beta * omega
    np.testing.assert_allclose(model.damping_ratios(omega), expected, rtol=1e-14)


def test_rayleigh_minimum_is_sqrt_alpha_beta():
    model = RayleighDamping(alpha=0.4, beta=5e-4)
    omega_min = model.critical_angular_frequency
    np.testing.assert_allclose(omega_min, np.sqrt(0.4 / 5e-4))
    np.testing.assert_allclose(model.damping_ratios(omega_min)[0], model.minimum_ratio)
    sampled = model.damping_ratios(np.linspace(1.0, 2000.0, 501))
    assert sampled.min() >= model.minimum_ratio - 1e-12


def test_rayleigh_proportional_constructors():
    mass_only = RayleighDamping.mass_proportional(5.0, 0.04)
    assert mass_only.beta == 0.0
    np.testing.assert_allclose(mass_only.damping_ratios(2.0 * np.pi * 5.0)[0], 0.04)

    stiffness_only = RayleighDamping.stiffness_proportional(5.0, 0.04)
    assert stiffness_only.alpha == 0.0
    np.testing.assert_allclose(stiffness_only.damping_ratios(2.0 * np.pi * 5.0)[0], 0.04)


def test_rayleigh_least_squares_fit_recovers_exact_coefficients():
    truth = RayleighDamping(alpha=0.25, beta=3e-4)
    frequencies = np.array([1.5, 4.0, 9.0, 17.0, 30.0])
    ratios = truth.damping_ratios(2.0 * np.pi * frequencies)
    fitted = RayleighDamping.from_modal_damping(frequencies, ratios)
    np.testing.assert_allclose(fitted.alpha, truth.alpha, rtol=1e-10)
    np.testing.assert_allclose(fitted.beta, truth.beta, rtol=1e-10)


def test_rayleigh_fit_of_noisy_damping_stays_close():
    truth = RayleighDamping(alpha=0.25, beta=3e-4)
    frequencies = np.linspace(2.0, 40.0, 12)
    exact = truth.damping_ratios(2.0 * np.pi * frequencies)
    rng = np.random.default_rng(7)
    noisy = exact * (1.0 + 0.02 * rng.standard_normal(exact.size))
    fitted = RayleighDamping.from_modal_damping(frequencies, noisy)
    residual = fitted.damping_ratios(2.0 * np.pi * frequencies) - exact
    assert np.max(np.abs(residual)) < 0.05 * np.max(exact)


def test_rayleigh_modal_coefficients_stay_finite_at_zero_frequency():
    model = RayleighDamping(alpha=0.5, beta=1e-3)
    omega = np.array([0.0, 10.0])
    np.testing.assert_allclose(model.modal_coefficients(omega), [0.5, 0.5 + 1e-3 * 100.0])
    assert np.isinf(model.damping_ratios(omega)[0])


def test_rayleigh_rejects_degenerate_anchors():
    with pytest.raises(SolverError, match="must differ"):
        RayleighDamping.from_frequencies(3.0, 3.0, 0.01, 0.02)
    with pytest.raises(SolverError, match="positive"):
        RayleighDamping.from_frequencies(0.0, 3.0, 0.01, 0.02)


def test_rayleigh_fit_needs_two_modes():
    with pytest.raises(SolverError, match="at least two modes"):
        RayleighDamping.from_modal_damping([3.0], [0.01])
    with pytest.raises(SolverError, match="damping ratios"):
        RayleighDamping.from_modal_damping([3.0, 4.0], [0.01])


def test_rayleigh_warns_when_the_fit_turns_negative():
    with pytest.warns(RuntimeWarning, match="negative Rayleigh"):
        model = RayleighDamping.from_frequencies(1.0, 10.0, 0.05, 0.001)
    assert model.beta < 0.0


# ==================================================== modal / structural models


def test_modal_damping_broadcasts_a_scalar():
    model = ModalDamping(np.array([0.02]))
    np.testing.assert_allclose(model.damping_ratios([1.0, 2.0, 3.0]), 0.02)


def test_modal_damping_rejects_a_length_mismatch():
    model = ModalDamping(np.array([0.01, 0.02]))
    with pytest.raises(SolverError, match="do not match"):
        model.damping_ratios([1.0, 2.0, 3.0])


def test_modal_damping_has_no_physical_matrix():
    with pytest.raises(SolverError, match="modal_damping_matrix"):
        ModalDamping(np.array([0.02])).matrix(np.eye(2), np.eye(2))


def test_modal_damping_warns_on_negative_ratios():
    with pytest.warns(RuntimeWarning, match="unstable"):
        ModalDamping(np.array([-0.01]))


def test_structural_damping_ratio_is_half_the_loss_factor():
    model = StructuralDamping(loss_factor=0.04)
    np.testing.assert_allclose(model.damping_ratios([1.0, 50.0]), 0.02)


def test_structural_complex_stiffness():
    K, _, _ = chain_matrices()
    model = StructuralDamping(loss_factor=0.05)
    np.testing.assert_allclose(model.complex_stiffness(K), K * (1.0 + 0.05j))


def test_structural_equivalent_viscous_matrix_needs_a_reference():
    K, M, _ = chain_matrices()
    with pytest.raises(SolverError, match="reference_frequency"):
        StructuralDamping(loss_factor=0.05).matrix(K, M)
    referenced = StructuralDamping(loss_factor=0.05, reference_frequency=4.0)
    np.testing.assert_allclose(referenced.matrix(K, M), K * 0.05 / (2.0 * np.pi * 4.0))


def test_damping_matrix_dispatch():
    K, M, _ = chain_matrices()
    assert damping_matrix(None, K, M) is None
    np.testing.assert_allclose(
        damping_matrix(RayleighDamping(alpha=0.1), K, M), 0.1 * M
    )
    explicit = np.eye(K.shape[0])
    np.testing.assert_allclose(damping_matrix(explicit, K, M), explicit)
    with pytest.raises(SolverError, match="does not match"):
        damping_matrix(np.eye(2), K, M)


# ============================================================= proportionality


def test_rayleigh_damping_is_classical():
    K, M, C = chain_matrices(damping=RayleighDamping(alpha=0.3, beta=2e-4))
    assert proportionality_index(K, M, C) < 1e-12
    assert is_proportional(K, M, C)


def test_a_single_local_dashpot_is_not_classical():
    K, M, _ = chain_matrices()
    C = np.zeros_like(K)
    C[0, 0] = 5.0
    assert not is_proportional(K, M, C)
    assert proportionality_index(K, M, C) > 0.1


def test_modal_damping_matrix_is_classical_and_realizes_the_ratios():
    K, M, _ = chain_matrices(num_masses=4)
    modes = real_modes(K, M)
    ratios = np.array([0.01, 0.02, 0.03, 0.04])
    C = modal_damping_matrix(M, modes.mode_shapes, modes.angular_frequencies, ratios)

    assert is_proportional(K, M, C)
    damped = complex_modes(K, M, C)
    np.testing.assert_allclose(damped.damping_ratios, ratios, rtol=1e-10)
    np.testing.assert_allclose(
        damped.angular_frequencies, modes.angular_frequencies, rtol=1e-10
    )


def test_modal_damping_matrix_validates_its_inputs():
    K, M, _ = chain_matrices(num_masses=4)
    modes = real_modes(K, M)
    with pytest.raises(SolverError, match="do not span"):
        modal_damping_matrix(M, np.ones((2, 4)), modes.angular_frequencies, 0.01)
    with pytest.raises(SolverError, match="angular frequencies"):
        modal_damping_matrix(M, modes.mode_shapes, modes.angular_frequencies[:2], 0.01)


# ============================================================== complex modes


def test_undamped_complex_modes_reproduce_the_real_spectrum():
    K, M, _ = chain_matrices(num_masses=5)
    reference = real_modes(K, M)
    damped = complex_modes(K, M)

    np.testing.assert_allclose(
        damped.angular_frequencies, reference.angular_frequencies, rtol=1e-10
    )
    np.testing.assert_allclose(damped.damping_ratios, 0.0, atol=1e-12)
    np.testing.assert_allclose(np.real(damped.eigenvalues), 0.0, atol=1e-9)
    np.testing.assert_allclose(damped.modal_phase_collinearity, 1.0, rtol=1e-12)
    for index in range(damped.num_modes):
        assert mac(damped.mode_shapes[:, index], reference.mode_shapes[:, index]) > 1 - 1e-12


def test_sdof_poles_match_the_closed_form():
    m, k, zeta = 2.0, 200.0, 0.07
    omega_0 = np.sqrt(k / m)
    C = np.array([[2.0 * zeta * omega_0 * m]])
    result = complex_modes(np.array([[k]]), np.array([[m]]), C)

    assert result.num_modes == 1
    expected = -zeta * omega_0 + 1j * omega_0 * np.sqrt(1.0 - zeta**2)
    np.testing.assert_allclose(result.eigenvalues[0], expected, rtol=1e-12)
    np.testing.assert_allclose(result.angular_frequencies[0], omega_0, rtol=1e-12)
    np.testing.assert_allclose(result.damping_ratios[0], zeta, rtol=1e-12)
    np.testing.assert_allclose(
        result.damped_angular_frequencies[0], omega_0 * np.sqrt(1.0 - zeta**2), rtol=1e-12
    )


def test_overdamped_sdof_gives_two_real_poles():
    m, k, c = 1.0, 100.0, 40.0
    result = complex_modes(np.array([[k]]), np.array([[m]]), np.array([[c]]))

    assert result.num_modes == 2
    poles = np.sort(np.real(result.eigenvalues))
    np.testing.assert_allclose(np.imag(result.eigenvalues), 0.0, atol=1e-12)
    np.testing.assert_allclose(poles.sum(), -c / m, rtol=1e-12)
    np.testing.assert_allclose(poles.prod(), k / m, rtol=1e-12)
    assert not result.is_oscillatory.any()
    np.testing.assert_allclose(result.damping_ratios, 1.0, rtol=1e-12)


def test_proportional_damping_matches_the_rayleigh_curve():
    rayleigh = RayleighDamping(alpha=0.35, beta=4e-4)
    K, M, C = chain_matrices(num_masses=5, damping=rayleigh)
    undamped = real_modes(K, M)
    damped = complex_modes(K, M, C)

    np.testing.assert_allclose(
        damped.angular_frequencies, undamped.angular_frequencies, rtol=1e-10
    )
    np.testing.assert_allclose(
        damped.damping_ratios,
        rayleigh.damping_ratios(undamped.angular_frequencies),
        rtol=1e-10,
    )


def test_proportional_damping_leaves_the_modes_monophase():
    K, M, C = chain_matrices(num_masses=5, damping=RayleighDamping(alpha=0.35, beta=4e-4))
    damped = complex_modes(K, M, C)
    np.testing.assert_allclose(damped.modal_phase_collinearity, 1.0, rtol=1e-10)


def test_non_proportional_damping_produces_genuinely_complex_modes():
    K, M, _ = chain_matrices(num_masses=5)
    C = np.zeros_like(K)
    C[0, 0] = 8.0
    damped = complex_modes(K, M, C)

    assert not is_proportional(K, M, C)
    assert damped.modal_phase_collinearity.min() < 0.99
    assert np.all(damped.damping_ratios > 0.0)
    assert np.all(np.real(damped.eigenvalues) < 0.0)


def test_complex_mode_residuals_are_negligible():
    K, M, _ = chain_matrices(num_masses=6)
    C = np.zeros_like(K)
    C[0, 0] = 4.0
    C[3, 3] = 1.5
    damped = complex_modes(K, M, C)
    assert np.max(damped.residuals()) < 1e-10


def test_state_normalization_gives_a_unit_modal_constant():
    K, M, C = chain_matrices(num_masses=4, damping=RayleighDamping(alpha=0.2, beta=1e-4))
    damped = complex_modes(K, M, C, normalization="state")
    np.testing.assert_allclose(damped.scaling, 1.0 + 0.0j, rtol=1e-10, atol=1e-12)


def test_max_normalization_puts_the_dominant_component_at_one():
    K, M, C = chain_matrices(num_masses=4, damping=RayleighDamping(alpha=0.2, beta=1e-4))
    damped = complex_modes(K, M, C, normalization="max")
    peaks = np.max(np.abs(damped.mode_shapes), axis=0)
    np.testing.assert_allclose(peaks, 1.0, rtol=1e-12)


def test_normalization_does_not_change_the_synthesized_frf():
    K, M, C = chain_matrices(num_masses=4, damping=RayleighDamping(alpha=0.2, beta=1e-4))
    line = np.linspace(0.5, 12.0, 40)
    reference = complex_modal_frf(line, complex_modes(K, M, C, normalization="state"))
    for style in ("max", "none"):
        other = complex_modal_frf(line, complex_modes(K, M, C, normalization=style))
        np.testing.assert_allclose(other.data, reference.data, rtol=1e-9, atol=1e-14)


def test_complex_modes_truncate_to_the_lowest_poles():
    K, M, C = chain_matrices(num_masses=6, damping=RayleighDamping(alpha=0.2, beta=1e-4))
    everything = complex_modes(K, M, C)
    truncated = complex_modes(K, M, C, num_modes=3)
    assert truncated.num_modes == 3
    np.testing.assert_allclose(truncated.eigenvalues, everything.eigenvalues[:3], rtol=1e-12)


def test_complex_modes_expand_onto_the_full_dof_space():
    model = spring_mass_chain(4, 1000.0, 1.0)
    K, M, C, free = damped_matrices(model, damping=RayleighDamping(alpha=0.2, beta=1e-4))
    damped = complex_modes(K, M, C, free_dofs=free)

    assert damped.num_dofs == K.shape[0]
    constrained = np.setdiff1d(np.arange(K.shape[0]), free)
    np.testing.assert_allclose(damped.mode_shapes[constrained, :], 0.0)
    assert damped.reduced_shapes().shape == (free.size, damped.num_modes)


def test_complex_modes_reject_massless_dofs():
    beam = beam_mesh(1.0, 4, STEEL, SQUARE, lumped_mass=True)
    K, M, C, free = damped_matrices(beam, damping=RayleighDamping(alpha=0.1, beta=1e-5))
    with pytest.raises(SolverError, match="condense the massless DOFs"):
        complex_modes(K, M, C, free_dofs=free)


def test_complex_modes_validate_their_arguments():
    K, M, _ = chain_matrices(num_masses=3)
    with pytest.raises(SolverError, match="unknown normalization"):
        complex_modes(K, M, normalization="banana")
    with pytest.raises(SolverError, match="num_modes must be"):
        complex_modes(K, M, num_modes=0)
    with pytest.raises(SolverError, match="same shape"):
        complex_modes(K, M, np.eye(2))
    with pytest.raises(SolverError, match="every equation is constrained"):
        complex_modes(K, M, free_dofs=[])


def test_real_modes_recover_the_undamped_shapes():
    K, M, C = chain_matrices(num_masses=5, damping=RayleighDamping(alpha=0.3, beta=3e-4))
    reference = real_modes(K, M)
    approximation = complex_modes(K, M, C).real_modes()
    for index in range(reference.num_modes):
        assert mac(approximation[:, index], reference.mode_shapes[:, index]) > 1 - 1e-10


def test_complex_result_summary_lists_every_mode():
    K, M, C = chain_matrices(num_masses=4, damping=RayleighDamping(alpha=0.2, beta=1e-4))
    text = complex_modes(K, M, C).summary()
    assert "MPC" in text
    assert len(text.splitlines()) == 6


def test_residuals_need_the_system_matrices():
    detached = ComplexModalResult(
        eigenvalues=np.array([1j]),
        mode_shapes=np.ones((1, 1), dtype=complex),
        scaling=np.ones(1, dtype=complex),
    )
    with pytest.raises(SolverError, match="no matrices"):
        detached.residuals()


# ======================================================================== MPC


def test_mpc_of_a_real_mode_is_one_under_any_global_phase():
    shape = np.array([1.0, -0.4, 0.7, 0.2])
    for angle in (0.0, 0.3, 1.1, np.pi / 2):
        rotated = shape * np.exp(1j * angle)
        np.testing.assert_allclose(modal_phase_collinearity(rotated), 1.0, rtol=1e-12)


def test_mpc_of_a_quadrature_mode_is_zero():
    np.testing.assert_allclose(modal_phase_collinearity(np.array([1.0, 1.0j])), 0.0, atol=1e-12)


def test_mpc_maps_over_columns():
    shapes = np.column_stack([np.array([1.0, 2.0]) + 0j, np.array([1.0, 1.0j])])
    np.testing.assert_allclose(modal_phase_collinearity(shapes), [1.0, 0.0], atol=1e-12)


def test_mpc_rejects_a_3d_array():
    with pytest.raises(SolverError, match="vector or a"):
        modal_phase_collinearity(np.zeros((2, 2, 2)))


# =============================================================== FRF synthesis


def test_sdof_receptance_matches_the_closed_form():
    m, k, c = 1.5, 600.0, 3.0
    line = np.linspace(0.5, 8.0, 50)
    response = direct_frf(line, np.array([[k]]), np.array([[m]]), np.array([[c]]))
    omega = 2.0 * np.pi * line
    expected = 1.0 / (k - omega**2 * m + 1j * omega * c)
    np.testing.assert_allclose(response.data[:, 0, 0], expected, rtol=1e-12)


def test_sdof_resonant_amplitude_is_one_over_omega_c():
    m, k, c = 1.0, 400.0, 2.0
    omega_0 = np.sqrt(k / m)
    line = np.array([omega_0 / (2.0 * np.pi)])
    response = direct_frf(line, np.array([[k]]), np.array([[m]]), np.array([[c]]))
    np.testing.assert_allclose(abs(response.data[0, 0, 0]), 1.0 / (omega_0 * c), rtol=1e-10)


def test_real_mode_superposition_matches_the_direct_inversion():
    rayleigh = RayleighDamping(alpha=0.4, beta=3e-4)
    K, M, C = chain_matrices(num_masses=6, damping=rayleigh)
    modes = real_modes(K, M)
    line = np.linspace(0.4, 25.0, 80)

    synthesized = modal_frf(line, modes, rayleigh)
    reference = direct_frf(line, K, M, C)
    scale = np.max(np.abs(reference.data))
    assert np.max(np.abs(synthesized.data - reference.data)) < 1e-10 * scale


def test_complex_mode_superposition_matches_the_direct_inversion():
    K, M, _ = chain_matrices(num_masses=6)
    C = np.zeros_like(K)
    C[0, 0] = 6.0
    C[2, 4] = C[4, 2] = -1.0
    C[4, 4] = 3.0
    assert not is_proportional(K, M, C)

    line = np.linspace(0.4, 25.0, 80)
    synthesized = complex_modal_frf(line, complex_modes(K, M, C))
    reference = direct_frf(line, K, M, C)
    scale = np.max(np.abs(reference.data))
    assert np.max(np.abs(synthesized.data - reference.data)) < 1e-9 * scale


def test_complex_superposition_covers_overdamped_roots():
    m, k, c = 1.0, 100.0, 40.0
    K, M, C = np.array([[k]]), np.array([[m]]), np.array([[c]])
    line = np.linspace(0.1, 5.0, 30)
    synthesized = complex_modal_frf(line, complex_modes(K, M, C))
    reference = direct_frf(line, K, M, C)
    np.testing.assert_allclose(synthesized.data, reference.data, rtol=1e-10)


def test_modal_frf_dispatches_complex_results():
    K, M, C = chain_matrices(num_masses=4, damping=RayleighDamping(alpha=0.2, beta=1e-4))
    line = np.linspace(0.5, 12.0, 30)
    damped = complex_modes(K, M, C)
    np.testing.assert_allclose(
        modal_frf(line, damped).data, complex_modal_frf(line, damped).data
    )


def test_synthesized_frf_is_reciprocal():
    K, M, C = chain_matrices(num_masses=5, damping=RayleighDamping(alpha=0.3, beta=2e-4))
    line = np.linspace(0.5, 20.0, 40)
    data = direct_frf(line, K, M, C).data
    np.testing.assert_allclose(data, np.transpose(data, (0, 2, 1)), rtol=1e-10)


def test_response_types_are_consistent():
    K, M, C = chain_matrices(num_masses=4, damping=RayleighDamping(alpha=0.3, beta=2e-4))
    line = np.linspace(0.5, 12.0, 25)
    receptance = direct_frf(line, K, M, C)
    omega = 2.0 * np.pi * line

    mobility = direct_frf(line, K, M, C, response_type="mobility")
    accelerance = direct_frf(line, K, M, C, response_type="accelerance")
    np.testing.assert_allclose(
        mobility.data, receptance.data * (1j * omega)[:, None, None], rtol=1e-12
    )
    np.testing.assert_allclose(
        accelerance.data, -receptance.data * (omega**2)[:, None, None], rtol=1e-12
    )
    np.testing.assert_allclose(
        receptance.converted("accelerance").data, accelerance.data, rtol=1e-12
    )
    np.testing.assert_allclose(
        accelerance.converted("receptance").data, receptance.data, rtol=1e-12
    )


def test_modal_frf_honours_the_response_type():
    rayleigh = RayleighDamping(alpha=0.3, beta=2e-4)
    K, M, C = chain_matrices(num_masses=4, damping=rayleigh)
    line = np.linspace(0.5, 12.0, 25)
    modes = real_modes(K, M)
    synthesized = modal_frf(line, modes, rayleigh, response_type="accelerance")
    reference = direct_frf(line, K, M, C, response_type="accelerance")
    scale = np.max(np.abs(reference.data))
    assert np.max(np.abs(synthesized.data - reference.data)) < 1e-10 * scale


def test_conversion_below_receptance_at_zero_hertz_is_refused():
    K, M, C = chain_matrices(num_masses=3, damping=RayleighDamping(alpha=0.3, beta=2e-4))
    line = np.array([0.0, 1.0, 2.0])
    accelerance = direct_frf(line, K, M, C, response_type="accelerance")
    with pytest.raises(SolverError, match="singular there"):
        accelerance.converted("receptance")


def test_selected_response_and_excitation_dofs():
    K, M, C = chain_matrices(num_masses=5, damping=RayleighDamping(alpha=0.3, beta=2e-4))
    line = np.linspace(0.5, 12.0, 20)
    full = direct_frf(line, K, M, C)
    partial = direct_frf(line, K, M, C, response_dofs=[1, 4], excitation_dofs=[0])
    assert partial.data.shape == (line.size, 2, 1)
    np.testing.assert_allclose(partial.data[:, :, 0], full.data[:, [1, 4], 0], rtol=1e-12)


def test_frf_dof_selection_is_range_checked():
    K, M, C = chain_matrices(num_masses=3, damping=RayleighDamping(alpha=0.3, beta=2e-4))
    with pytest.raises(SolverError, match="outside the 3-DOF model"):
        direct_frf([1.0], K, M, C, response_dofs=[9])


# ======================================================== truncation residuals


def test_residual_flexibility_restores_the_static_response():
    K, M, _ = chain_matrices(num_masses=6)
    modes = real_modes(K, M)
    residual = residual_flexibility(K, modes, num_modes=2)

    truncated = modal_frf([0.0], modes, 0.02, num_modes=2, residual=residual)
    np.testing.assert_allclose(truncated.data[0].real, np.linalg.inv(K), rtol=1e-10)
    np.testing.assert_allclose(truncated.data[0].imag, 0.0, atol=1e-14)


def test_residual_flexibility_improves_a_truncated_synthesis():
    """Below the first discarded resonance the truncation error is nearly static,
    which is exactly what the residual flexibility term removes."""
    rayleigh = RayleighDamping(alpha=0.4, beta=3e-4)
    K, M, C = chain_matrices(num_masses=6, damping=rayleigh)
    modes = real_modes(K, M)
    assert modes.frequencies[2] > 5.0  # the lowest discarded mode is out of band
    line = np.linspace(0.1, 1.5, 40)
    reference = direct_frf(line, K, M, C)

    plain = modal_frf(line, modes, rayleigh, num_modes=2)
    corrected = modal_frf(
        line, modes, rayleigh, num_modes=2, residual=residual_flexibility(K, modes, num_modes=2)
    )
    plain_error = np.max(np.abs(plain.data - reference.data))
    corrected_error = np.max(np.abs(corrected.data - reference.data))
    assert corrected_error < 0.1 * plain_error


def test_residual_flexibility_is_undefined_for_free_free_models():
    K, M, _ = chain_matrices(num_masses=3)
    free_free = K - np.diag(K.sum(axis=1))
    modes = real_modes(K, M)
    with pytest.raises(SolverError, match="span"):
        residual_flexibility(np.eye(2), modes)
    with pytest.raises(SolverError):
        residual_flexibility(free_free, modes)


def test_residual_flexibility_rejects_rigid_body_modes():
    K, M, _ = chain_matrices(num_masses=3)
    modes = real_modes(K, M)
    zeroed = (np.array([0.0, *modes.angular_frequencies[1:]]), modes.mode_shapes)
    with pytest.raises(SolverError, match="rigid-body"):
        residual_flexibility(K, zeroed)


# ========================================================== harmonic response


def test_harmonic_response_matches_the_frf_times_the_load():
    K, M, C = chain_matrices(num_masses=5, damping=RayleighDamping(alpha=0.3, beta=2e-4))
    line = np.linspace(0.5, 20.0, 30)
    load = np.array([0.0, 2.0, 0.0, -1.0, 0.5])

    response = harmonic_response(line, K, M, C, load=load)
    expected = direct_frf(line, K, M, C).data @ load
    np.testing.assert_allclose(response, expected, rtol=1e-10)


def test_harmonic_response_accepts_a_frequency_dependent_load():
    K, M, C = chain_matrices(num_masses=3, damping=RayleighDamping(alpha=0.3, beta=2e-4))
    line = np.array([1.0, 2.0, 3.0])
    loads = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    response = harmonic_response(line, K, M, C, load=loads)
    columns = direct_frf(line, K, M, C).data
    for index in range(line.size):
        np.testing.assert_allclose(response[index], columns[index] @ loads[index], rtol=1e-10)


def test_harmonic_response_rejects_a_mis_sized_load():
    K, M, C = chain_matrices(num_masses=3, damping=RayleighDamping(alpha=0.3, beta=2e-4))
    with pytest.raises(SolverError, match="must be"):
        harmonic_response([1.0, 2.0], K, M, C, load=np.ones(7))


def test_structural_damping_in_the_direct_solution():
    K, M, _ = chain_matrices(num_masses=4)
    line = np.linspace(0.5, 12.0, 25)
    eta = 0.04
    response = direct_frf(line, K, M, structural_damping=eta)
    omega = 2.0 * np.pi * line
    for index, w in enumerate(omega):
        expected = np.linalg.inv(K * (1.0 + 1j * eta) - w**2 * M)
        np.testing.assert_allclose(response.data[index], expected, rtol=1e-10)


def test_undamped_resonance_on_the_frequency_line_is_reported():
    K, M, _ = chain_matrices(num_masses=3)
    modes = real_modes(K, M)
    resonance = float(modes.frequencies[0])
    line = np.array([resonance])
    pair = (2.0 * np.pi * np.array([resonance]), modes.mode_shapes[:, :1])
    with pytest.raises(SolverError, match="undamped mode"):
        modal_frf(line, pair, 0.0)


# ================================================== FrequencyResponse container


def test_frequency_response_accessors():
    K, M, C = chain_matrices(num_masses=4, damping=RayleighDamping(alpha=0.3, beta=2e-4))
    line = np.linspace(0.5, 12.0, 20)
    response = direct_frf(line, K, M, C)

    assert response.num_frequencies == 20
    assert response.num_response_dofs == 4
    assert response.num_excitation_dofs == 4
    np.testing.assert_allclose(response.angular_frequencies, 2.0 * np.pi * line)
    np.testing.assert_allclose(response.magnitude, np.abs(response.data))
    np.testing.assert_allclose(response.phase, np.degrees(np.angle(response.data)))
    np.testing.assert_allclose(response.matrix_at(3), response.data[3])
    np.testing.assert_allclose(response.column(2), response.data[:, :, 2])
    np.testing.assert_allclose(response.row(1), response.data[:, 1, :])
    np.testing.assert_allclose(response.drive_point(1), response.data[:, 1, 1])
    assert response.nearest(float(line[7])) == 7


def test_frequency_response_reports_unknown_dofs():
    K, M, C = chain_matrices(num_masses=3, damping=RayleighDamping(alpha=0.3, beta=2e-4))
    response = direct_frf([1.0], K, M, C, response_dofs=[0], excitation_dofs=[0])
    with pytest.raises(SolverError, match="not among the response DOFs"):
        response.row(2)
    with pytest.raises(SolverError, match="not among the excitation DOFs"):
        response.column(2)


def test_frequency_response_validates_its_shape():
    with pytest.raises(SolverError, match="does not match"):
        FrequencyResponse(
            frequencies=np.array([1.0, 2.0]),
            data=np.zeros((3, 1, 1), dtype=complex),
            response_dofs=np.array([0]),
            excitation_dofs=np.array([0]),
        )
    with pytest.raises(SolverError, match="unknown response type"):
        FrequencyResponse(
            frequencies=np.array([1.0]),
            data=np.zeros((1, 1, 1), dtype=complex),
            response_dofs=np.array([0]),
            excitation_dofs=np.array([0]),
            response_type="velocity",
        )


def test_modal_frf_accepts_unnormalized_modes_with_modal_masses():
    rayleigh = RayleighDamping(alpha=0.4, beta=3e-4)
    K, M, C = chain_matrices(num_masses=4, damping=rayleigh)
    modes = real_modes(K, M)
    line = np.linspace(0.5, 15.0, 30)

    reference = modal_frf(line, modes, rayleigh)
    scaled = (modes.angular_frequencies, modes.mode_shapes * 3.0)
    rescaled = modal_frf(line, scaled, rayleigh, modal_masses=np.full(modes.num_modes, 9.0))
    np.testing.assert_allclose(rescaled.data, reference.data, rtol=1e-10)


def test_modal_frf_validates_modes_and_damping():
    K, M, _ = chain_matrices(num_masses=4)
    modes = real_modes(K, M)
    with pytest.raises(SolverError, match="damping ratios"):
        modal_frf([1.0], modes, [0.01, 0.02])
    with pytest.raises(SolverError, match="mode_shapes"):
        modal_frf([1.0], object())
    with pytest.raises(SolverError, match="modal masses"):
        modal_frf([1.0], modes, 0.01, modal_masses=[1.0, 1.0])


# ============================================================ FRF correlation


def test_frac_is_one_for_a_scaled_copy():
    K, M, C = chain_matrices(num_masses=4, damping=RayleighDamping(alpha=0.3, beta=2e-4))
    line = np.linspace(0.5, 15.0, 60)
    reference = direct_frf(line, K, M, C).drive_point(0)
    np.testing.assert_allclose(frac(reference, reference * (2.5 - 1.3j)), 1.0, rtol=1e-12)


def test_frac_drops_when_the_model_is_detuned():
    rayleigh = RayleighDamping(alpha=0.3, beta=2e-4)
    K, M, C = chain_matrices(num_masses=4, damping=rayleigh)
    line = np.linspace(0.5, 15.0, 120)
    reference = direct_frf(line, K, M, C).drive_point(0)

    detuned_K, detuned_M, detuned_C = chain_matrices(
        num_masses=4, stiffness=1150.0, damping=rayleigh
    )
    detuned = direct_frf(line, detuned_K, detuned_M, detuned_C).drive_point(0)
    assert frac(reference, detuned) < 0.9


def test_frac_maps_over_a_matrix_of_lines():
    K, M, C = chain_matrices(num_masses=4, damping=RayleighDamping(alpha=0.3, beta=2e-4))
    line = np.linspace(0.5, 15.0, 40)
    block = direct_frf(line, K, M, C).column(0)
    values = frac(block, block)
    assert values.shape == (4,)
    np.testing.assert_allclose(values, 1.0, rtol=1e-12)


def test_frac_rejects_mismatched_shapes():
    with pytest.raises(SolverError, match="matching shapes"):
        frac(np.ones(4), np.ones(5))


def test_fdac_diagonal_is_unity_for_identical_data():
    K, M, C = chain_matrices(num_masses=4, damping=RayleighDamping(alpha=0.3, beta=2e-4))
    line = np.linspace(0.5, 15.0, 30)
    block = direct_frf(line, K, M, C).column(0)
    matrix = fdac(block, block)
    assert matrix.shape == (30, 30)
    np.testing.assert_allclose(np.diag(matrix), 1.0, rtol=1e-12)
    assert matrix.max() <= 1.0 + 1e-12


def test_fdac_rejects_a_dof_mismatch():
    with pytest.raises(SolverError, match="same DOF count"):
        fdac(np.ones((3, 4)), np.ones((3, 5)))


# =========================================================== model integration


def test_damped_matrices_from_a_model():
    model = spring_mass_chain(4, 1000.0, 1.0)
    K, M, C, free = damped_matrices(model, damping=RayleighDamping(alpha=0.2, beta=1e-4))
    assert K.shape == M.shape == C.shape
    assert free.size == 4
    np.testing.assert_allclose(C.toarray(), 0.2 * M.toarray() + 1e-4 * K.toarray())


def test_damped_matrices_needs_exactly_one_source():
    with pytest.raises(SolverError, match="exactly one"):
        damped_matrices()


def test_axial_bar_damped_spectrum_matches_the_undamped_solver():
    bar = bar_mesh(1.0, 12, STEEL, SQUARE, dofs=(DOF.UX,))
    rayleigh = RayleighDamping.from_frequencies(1000.0, 8000.0, 0.01, 0.02)
    K, M, C, free = damped_matrices(bar, damping=rayleigh)
    undamped = ModalSolver(bar).solve(num_modes=4, sparse=False)
    damped = complex_modes(K, M, C, num_modes=4, free_dofs=free)

    # The state-space QZ solve is a few digits less accurate than the symmetric
    # eigensolver it is compared against, hence 1e-7 rather than 1e-12.
    np.testing.assert_allclose(damped.frequencies, undamped.frequencies, rtol=1e-7)
    np.testing.assert_allclose(
        damped.damping_ratios,
        rayleigh.damping_ratios(undamped.angular_frequencies),
        rtol=1e-7,
    )
    assert np.all(damped.modal_phase_collinearity > 1 - 1e-7)


def test_full_chain_from_model_to_frf():
    """Model -> assembly -> modes -> damping -> FRF, checked against the direct solve."""
    model = spring_mass_chain(5, 2500.0, 1.5)
    rayleigh = RayleighDamping.from_frequencies(1.0, 12.0, 0.015, 0.025)
    K, M, C, free = damped_matrices(model, damping=rayleigh)
    modes = ModalSolver(model).solve(num_modes=5, sparse=False)

    line = np.linspace(0.5, 15.0, 60)
    synthesized = modal_frf(line, modes, rayleigh, response_dofs=free, excitation_dofs=free)
    reference = direct_frf(
        line, K, M, C, free_dofs=free, response_dofs=free, excitation_dofs=free
    )
    scale = np.max(np.abs(reference.data))
    assert np.max(np.abs(synthesized.data - reference.data)) < 1e-9 * scale

    peak = line[np.argmax(np.abs(synthesized.drive_point(free[-1])))]
    assert abs(peak - modes.frequencies[0]) < 0.5
