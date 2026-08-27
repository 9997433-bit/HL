"""Correctness guards for performance-sensitive numerical paths."""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from openfemlab.core.assembly import assemble_system
from openfemlab.mesh.simple import spring_mass_chain
from openfemlab.solver import modal
from openfemlab.solver.modal import ModalSolver
from openfemlab.updating.sensitivity import eigenvalue_sensitivity, mac_sensitivity


def test_system_assembly_traverses_element_topology_once(monkeypatch) -> None:
    model = spring_mass_chain(20, 1.0e6, 2.0)
    original = model.node_coords
    calls = 0

    def counted_node_coords(node_ids):
        nonlocal calls
        calls += 1
        return original(node_ids)

    monkeypatch.setattr(model, "node_coords", counted_node_coords)
    system = assemble_system(model)

    assert calls == model.num_elements
    np.testing.assert_allclose(system.K.toarray(), assemble_system(model).K.toarray())
    np.testing.assert_allclose(system.M.diagonal()[1:], 2.0)


def test_sparse_factorization_is_reused_and_can_be_bypassed(monkeypatch) -> None:
    solver = ModalSolver(spring_mass_chain(600, 2.0e3, 1.5))
    original = modal.spla.splu
    calls = 0

    def counted_splu(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(modal.spla, "splu", counted_splu)
    first = solver.solve(num_modes=6, sparse=True)
    second = solver.solve(num_modes=6, sparse=True)

    assert calls == 1
    assert solver.factorization_cache_size == 1
    np.testing.assert_allclose(second.eigenvalues, first.eigenvalues, rtol=1.0e-10)

    solver.solve(num_modes=6, sparse=True, cache_factorization=False)
    assert calls == 2
    solver.clear_cache()
    assert solver.factorization_cache_size == 0


def test_vectorized_eigenvalue_sensitivity_accepts_sparse_derivatives() -> None:
    rng = np.random.default_rng(7)
    mode_shapes, _ = np.linalg.qr(rng.normal(size=(40, 8)))
    eigenvalues = np.linspace(2.0, 20.0, mode_shapes.shape[1])
    stiffness_derivatives = []
    mass_derivatives = []
    for _ in range(5):
        factor = rng.normal(size=(40, 4))
        stiffness_derivatives.append(sp.csr_matrix(factor @ factor.T))
        mass_derivatives.append(sp.diags(rng.uniform(0.0, 0.1, size=40), format="csr"))

    actual = eigenvalue_sensitivity(
        mode_shapes,
        eigenvalues,
        stiffness_derivatives,
        mass_derivatives,
    )
    expected = np.empty_like(actual)
    for parameter, (dk, dm) in enumerate(
        zip(stiffness_derivatives, mass_derivatives, strict=True)
    ):
        for mode in range(mode_shapes.shape[1]):
            vector = mode_shapes[:, mode]
            expected[mode, parameter] = (
                vector @ (dk @ vector) - eigenvalues[mode] * vector @ (dm @ vector)
            )

    np.testing.assert_allclose(actual, expected, rtol=1.0e-13, atol=1.0e-13)


def test_vectorized_mac_sensitivity_matches_scalar_formula() -> None:
    rng = np.random.default_rng(11)
    reference = rng.normal(size=(30, 6)) + 1j * rng.normal(size=(30, 6))
    shapes = rng.normal(size=(30, 6)) + 1j * rng.normal(size=(30, 6))
    derivatives = rng.normal(size=(4, 30, 6)) + 1j * rng.normal(size=(4, 30, 6))
    weights = rng.uniform(0.2, 2.0, size=30)

    actual = mac_sensitivity(reference, shapes, derivatives, weights)
    expected = np.zeros_like(actual)
    for mode in range(shapes.shape[1]):
        a = reference[:, mode]
        b = shapes[:, mode]
        cross = np.vdot(a, weights * b)
        norm_a = float(np.real(np.vdot(a, weights * a)))
        norm_b = float(np.real(np.vdot(b, weights * b)))
        for parameter in range(derivatives.shape[0]):
            derivative = derivatives[parameter, :, mode]
            d_cross = np.real(np.conj(cross) * np.vdot(a, weights * derivative))
            d_norm_b = float(np.real(np.vdot(b, weights * derivative)))
            expected[mode, parameter] = (
                2.0
                / (norm_a * norm_b)
                * (d_cross - abs(cross) ** 2 / norm_b * d_norm_b)
            )

    np.testing.assert_allclose(actual, expected, rtol=1.0e-13, atol=1.0e-13)
