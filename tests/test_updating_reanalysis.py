"""Reanalysis acceleration for affine scaling models."""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp

from openfemlab.updating import ScalingModel


def _chain_scaling_model(dof: int = 40) -> ScalingModel:
    off = np.full(dof - 1, -1.0)
    diag = np.full(dof, 2.0)
    diag[-1] = 1.0
    k_part = sp.diags([off, diag, off], offsets=[-1, 0, 1], format="csr")
    m_part = sp.diags(np.full(dof, 1.0), format="csr")
    return ScalingModel(
        {"k1": k_part},
        {"m1": m_part},
        num_modes=4,
        use_solver=True,
    )


def test_scaling_model_reuses_modal_solver_instance():
    model = _chain_scaling_model()
    first = model.modal_data({"k1": 1.0, "m1": 1.0})
    second = model.modal_data({"k1": 0.95, "m1": 1.02})
    assert model._solver is not None
    assert first.frequencies.size == 4
    assert np.all(np.diff(second.frequencies) > 0.0)


def test_affine_fast_assembly_matches_slow_path():
    model = _chain_scaling_model()
    theta = {"k1": 0.88, "m1": 1.05}
    assert model._affine_stiffness is not None and model._affine_mass is not None
    fast_k, fast_m = model.assemble(theta)
    slow = ScalingModel(
        model.stiffness_parts,
        model.mass_parts,
        num_modes=4,
        use_solver=True,
        reanalysis=False,
    )
    slow_k, slow_m = slow.assemble(theta)
    np.testing.assert_allclose(fast_k.toarray(), slow_k.toarray(), rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(fast_m.toarray(), slow_m.toarray(), rtol=0.0, atol=1e-12)


def test_eigen_cache_avoids_repeat_solves():
    model = _chain_scaling_model()
    theta = {"k1": 1.0, "m1": 1.0}
    model.modal_data(theta)
    model.frequency_sensitivity(theta)
    assert model.n_eigen_calls == 2
    assert model.n_solves == 1
