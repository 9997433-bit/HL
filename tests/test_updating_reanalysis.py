"""Reanalysis acceleration of the affine :class:`ScalingModel` updating loop.

An updating run walks the *same* parameterisation over and over, so three kinds
of work are worth doing once instead of once per iteration: folding the affine
sum onto a fixed sparsity pattern, constructing the modal solver, and solving
the eigenproblem at a ``θ`` that has already been solved.

The cases below hold the accelerated model against the same model with
``reanalysis=False``, which assembles and solves from scratch every time.  Two
things have to come out of that comparison: the accelerated path must do
strictly less work (fewer assemblies, fewer solver constructions, fewer
factorizations, fewer eigensolves), and it must return the very same numbers —
bitwise for the assembly, and to the last converged parameter for a whole
updating run.
"""

from __future__ import annotations

import time

import numpy as np
import pytest
import scipy.sparse as sp

from openfemlab.solver import modal
from openfemlab.solver.modal import ModalSolver
from openfemlab.updating import ScalingModel, UpdatableParameter, update_model
from openfemlab.updating.scaling_model import _AffineTerms

N_DOF = 10
N_GROUPS = 4
BASE_STIFFNESS = 1.0e6
BASE_MASS = 2.0

#: Free DOFs above ``ModalSolver.dense_threshold``, so the solver takes the
#: sparse shift-invert path and a factorization exists to be cached at all.
SPARSE_DOF = 600


# --------------------------------------------------------------------- fixtures


def group_masks(n_dof: int, n_groups: int) -> list[np.ndarray]:
    bounds = np.linspace(0, n_dof, n_groups + 1).astype(int)
    return [
        np.isin(np.arange(n_dof), np.arange(lo, hi)).astype(float)
        for lo, hi in zip(bounds[:-1], bounds[1:], strict=False)
    ]


def chain_stiffness(stiffnesses: np.ndarray) -> np.ndarray:
    """Fixed-free chain: spring ``j`` links DOF ``j-1`` (ground for 0) to DOF ``j``."""
    n = stiffnesses.size
    K = np.zeros((n, n))
    for j, k in enumerate(stiffnesses):
        K[j, j] += k
        if j > 0:
            K[j - 1, j - 1] += k
            K[j - 1, j] -= k
            K[j, j - 1] -= k
    return K


def dense_parts(n_dof: int = N_DOF, n_groups: int = N_GROUPS) -> dict:
    """Dense stiffness groups against a dense mass base — the default base is sparse."""
    return {
        "stiffness_parts": {
            f"k{g}": chain_stiffness(BASE_STIFFNESS * mask)
            for g, mask in enumerate(group_masks(n_dof, n_groups))
        },
        "base_mass": np.eye(n_dof) * BASE_MASS,
    }


def sparse_parts(n_dof: int = N_DOF, n_groups: int = N_GROUPS) -> dict:
    """The same chain, every contribution sparse, one factor per substructure.

    Each ``k{g}`` scales its group's stiffness *and* mass, so both matrix groups
    are folded against the same parameter vector.
    """
    parts = dense_parts(n_dof, n_groups)
    return {
        "stiffness_parts": {
            name: sp.csr_matrix(part) for name, part in parts["stiffness_parts"].items()
        },
        "mass_parts": {
            f"k{g}": sp.csr_matrix(np.diag(BASE_MASS * mask))
            for g, mask in enumerate(group_masks(n_dof, n_groups))
        },
        "base_stiffness": sp.csr_matrix((n_dof, n_dof)),
        "base_mass": sp.csr_matrix((n_dof, n_dof)),
    }


def fully_dense_parts(n_dof: int = N_DOF, n_groups: int = N_GROUPS) -> dict:
    parts = dense_parts(n_dof, n_groups)
    return {
        "stiffness_parts": parts["stiffness_parts"],
        "base_stiffness": np.zeros((n_dof, n_dof)),
        "base_mass": parts["base_mass"],
    }


PARAMETERISATIONS = {
    "mixed": dense_parts,
    "sparse": sparse_parts,
    "dense": fully_dense_parts,
}


def model_pair(builder, **kwargs) -> tuple[ScalingModel, ScalingModel]:
    """``(accelerated, from_scratch)`` — the same model with reanalysis on and off."""
    settings = {"num_modes": 6, **kwargs}
    return (
        ScalingModel(**builder(), **settings, reanalysis=True),
        ScalingModel(**builder(), **settings, reanalysis=False),
    )


def to_array(matrix) -> np.ndarray:
    return matrix.toarray() if sp.issparse(matrix) else np.asarray(matrix)


def big_sparse_chain(n_dof: int = SPARSE_DOF, n_groups: int = N_GROUPS) -> dict:
    """A chain large enough that the solver picks the sparse backend."""
    band = sp.diags(
        [-np.ones(n_dof - 1), 2.0 * np.ones(n_dof), -np.ones(n_dof - 1)],
        offsets=[-1, 0, 1],
        format="csr",
    )
    parts = {}
    for g, mask in enumerate(group_masks(n_dof, n_groups)):
        rows = band.multiply(mask[:, None])
        columns = band.multiply(mask[None, :])
        parts[f"k{g}"] = sp.csr_matrix(rows + columns) * BASE_STIFFNESS
    return {
        "stiffness_parts": parts,
        "base_stiffness": sp.csr_matrix((n_dof, n_dof)),
        "base_mass": sp.diags(np.full(n_dof, BASE_MASS), format="csr"),
    }


# ------------------------------------------------------- fixed-pattern assembly


@pytest.mark.parametrize("kind", sorted(PARAMETERISATIONS))
def test_fixed_pattern_assembly_reproduces_the_naive_affine_sum(kind: str) -> None:
    """The fast path is bitwise equal to ``K_0 + Σ θ_j K_j``, not merely close.

    Anything less would make ``reanalysis`` a numerical setting: two runs of the
    same updating problem could then stop on different iterations.
    """
    fast, from_scratch = model_pair(PARAMETERISATIONS[kind], use_solver=False)
    theta = np.array([1.07, 0.88, 1.19, 0.94])[: len(fast.parameter_names)]

    K_fast, M_fast = fast.assemble(theta)
    K_slow, M_slow = from_scratch.assemble(theta)

    assert np.array_equal(to_array(K_fast), to_array(K_slow))
    assert np.array_equal(to_array(M_fast), to_array(M_slow))


def test_the_sparsity_pattern_is_folded_once_and_then_shared() -> None:
    """Only the CSR ``data`` array is rebuilt; the index arrays are the fold's."""
    model = ScalingModel(**sparse_parts(), num_modes=6, use_solver=False)
    union = sum(
        sp.csr_matrix((np.ones(part.nnz), part.indices, part.indptr), shape=part.shape)
        for part in model.stiffness_parts.values()
    )

    first, _ = model.assemble(np.full(N_GROUPS, 1.0))
    second, _ = model.assemble(np.full(N_GROUPS, 0.5))

    assert sp.issparse(first) and sp.issparse(second)
    np.testing.assert_array_equal(first.indptr, second.indptr)
    np.testing.assert_array_equal(first.indices, second.indices)
    np.testing.assert_array_equal(first.indptr, union.indptr)
    np.testing.assert_array_equal(first.indices, union.indices)
    # The pattern is the union, so it holds through a θ that cancels an entry.
    assert second.nnz == first.nnz


def test_a_repeated_theta_is_not_reassembled() -> None:
    model = ScalingModel(**sparse_parts(), num_modes=6, use_solver=False)
    theta = np.array([1.1, 0.9, 1.0, 1.2])

    model.assemble(theta)
    model.assemble(theta)
    model.assemble(theta)
    assert model.n_assemblies == 1

    model.assemble(theta * 1.01)
    assert model.n_assemblies == 2


def test_a_mixed_group_too_large_to_densify_keeps_the_generic_sum(monkeypatch) -> None:
    """The fold declines rather than materialising an ``n²`` buffer it cannot afford."""
    monkeypatch.setattr(_AffineTerms, "dense_fold_limit", 4)
    populated = sp.csr_matrix(np.diag(np.arange(1.0, N_DOF + 1)))

    folded = _AffineTerms.build(populated, [chain_stiffness(np.ones(N_DOF))], N_DOF)
    assert folded is None

    model = ScalingModel(
        **dense_parts(), base_stiffness=populated, num_modes=6, use_solver=False
    )
    reference = ScalingModel(
        **dense_parts(),
        base_stiffness=populated,
        num_modes=6,
        use_solver=False,
        reanalysis=False,
    )
    theta = np.array([1.03, 0.97, 1.11, 0.92])
    np.testing.assert_array_equal(
        to_array(model.assemble(theta)[0]), to_array(reference.assemble(theta)[0])
    )


def test_fixed_pattern_reassembly_is_faster_than_rebuilding_from_scratch() -> None:
    """The point of the fold: a 2000-DOF chain reassembles several times faster."""
    parameterisation = big_sparse_chain(n_dof=2000, n_groups=8)
    fast = ScalingModel(**parameterisation, num_modes=4, use_solver=False)
    from_scratch = ScalingModel(
        **parameterisation, num_modes=4, use_solver=False, reanalysis=False
    )
    thetas = [
        np.random.default_rng(seed).uniform(0.8, 1.2, len(fast.parameter_names))
        for seed in range(20)
    ]

    def best_of_three(model: ScalingModel) -> float:
        timings = []
        for _ in range(3):
            start = time.perf_counter()
            for theta in thetas:
                model.assemble(theta)
            timings.append(time.perf_counter() - start)
        return min(timings)

    # Warm both paths so neither pays a first-call import or allocation.
    best_of_three(fast), best_of_three(from_scratch)
    assert best_of_three(fast) < best_of_three(from_scratch)


# --------------------------------------------------------------- solver reuse


def test_one_modal_solver_instance_serves_every_theta(monkeypatch) -> None:
    """``from_matrices`` rebuilds the DOF partition and labels; do it once."""
    constructions = 0
    original = ModalSolver.from_matrices.__func__

    def counted(cls, K, M, **kwargs):
        nonlocal constructions
        constructions += 1
        return original(cls, K, M, **kwargs)

    monkeypatch.setattr(ModalSolver, "from_matrices", classmethod(counted))

    model = ScalingModel(**sparse_parts(), num_modes=4, use_solver=True)
    for step in range(5):
        model.eigen(np.full(N_GROUPS, 1.0 + 0.01 * step))

    assert constructions == 1
    assert model.modal_solver is not None

    constructions = 0
    from_scratch = ScalingModel(
        **sparse_parts(), num_modes=4, use_solver=True, reanalysis=False
    )
    for step in range(5):
        from_scratch.eigen(np.full(N_GROUPS, 1.0 + 0.01 * step))

    assert constructions == 5
    assert from_scratch.modal_solver is None


def test_the_reused_solver_is_rebound_to_the_new_matrices() -> None:
    """Same instance, refreshed matrices — a stale cache would freeze the modes."""
    model = ScalingModel(**sparse_parts(), num_modes=4, use_solver=True)
    reference = ScalingModel(
        **sparse_parts(), num_modes=4, use_solver=True, reanalysis=False
    )

    softened = np.array([0.6, 1.0, 1.0, 1.0])
    first = model.modal_data(np.ones(N_GROUPS)).frequencies
    solver = model.modal_solver
    second = model.modal_data(softened).frequencies

    assert model.modal_solver is solver
    assert second[0] < first[0]
    np.testing.assert_allclose(
        second, reference.modal_data(softened).frequencies, rtol=1e-12
    )


def test_the_reused_solver_keeps_its_factorization(monkeypatch) -> None:
    """``cache_factorization`` is on, so the shift-invert LU outlives the solve."""
    factorizations = 0
    original = modal.spla.splu

    def counted_splu(*args, **kwargs):
        nonlocal factorizations
        factorizations += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(modal.spla, "splu", counted_splu)

    parameterisation = big_sparse_chain()
    cached = ScalingModel(**parameterisation, num_modes=5, use_solver=True)
    cached.eigen(np.ones(N_GROUPS))

    assert factorizations == 1
    assert cached.modal_solver.factorization_cache_size == 1

    uncached = ScalingModel(
        **big_sparse_chain(), num_modes=5, use_solver=True, cache_factorization=False
    )
    uncached.eigen(np.ones(N_GROUPS))
    assert uncached.modal_solver.factorization_cache_size == 0


def test_a_theta_change_discards_the_stale_factorization() -> None:
    """The LU describes ``K(θ) - σ M(θ)``; keeping it across θ would be wrong."""
    model = ScalingModel(**big_sparse_chain(), num_modes=5, use_solver=True)
    reference = ScalingModel(
        **big_sparse_chain(), num_modes=5, use_solver=True, reanalysis=False
    )
    softened = np.array([0.5, 1.0, 1.0, 1.0])

    model.eigen(np.ones(N_GROUPS))
    values, _ = model.eigen(softened)
    expected, _ = reference.eigen(softened)

    assert model.modal_solver.factorization_cache_size == 1
    np.testing.assert_allclose(values, expected, rtol=1e-9)


# ------------------------------------------------------- eigensolution reuse


def test_a_repeated_theta_costs_no_eigensolve() -> None:
    model = ScalingModel(**dense_parts(), num_modes=6, use_solver=False)
    theta = np.array([1.05, 0.95, 1.10, 0.90])

    first_values, first_shapes = model.eigen(theta)
    values, shapes = model.eigen(theta)

    assert (model.n_eigen_calls, model.n_solves) == (2, 1)
    np.testing.assert_array_equal(values, first_values)
    np.testing.assert_array_equal(shapes, first_shapes)

    model.eigen(theta * 1.01)
    assert (model.n_eigen_calls, model.n_solves) == (3, 2)


def test_an_iteration_of_modal_data_and_sensitivities_is_one_eigensolve() -> None:
    """What the updater asks for at a point: modes, ``df/dθ``, ``dΦ/dθ``."""
    model = ScalingModel(**dense_parts(), num_modes=6, use_solver=False)
    from_scratch = ScalingModel(
        **dense_parts(), num_modes=6, use_solver=False, reanalysis=False
    )
    theta = np.array([1.02, 0.94, 1.08, 0.99])

    for candidate in (model, from_scratch):
        candidate.modal_data(theta)
        candidate.frequency_sensitivity(theta)
        candidate.mode_shape_sensitivity(theta)

    assert model.n_solves == 1
    assert from_scratch.n_solves == 3
    np.testing.assert_allclose(
        model.frequency_sensitivity(theta),
        from_scratch.frequency_sensitivity(theta),
        rtol=1e-12,
    )


def test_the_cache_hands_out_arrays_the_caller_may_scribble_on() -> None:
    model = ScalingModel(**dense_parts(), num_modes=6, use_solver=False)
    theta = np.ones(N_GROUPS)

    values, shapes = model.eigen(theta)
    values[0] = -1.0
    shapes[0, 0] = 1.0e9

    again, shapes_again = model.eigen(theta)
    assert again[0] != -1.0
    assert shapes_again[0, 0] != 1.0e9


def test_clear_cache_forces_a_fresh_solve() -> None:
    model = ScalingModel(**sparse_parts(), num_modes=4, use_solver=True)
    theta = np.ones(N_GROUPS)

    model.eigen(theta)
    solver = model.modal_solver
    model.clear_cache()
    model.eigen(theta)

    assert model.n_solves == 2
    assert model.n_assemblies == 2
    assert model.modal_solver is not solver


# --------------------------------------------------------------- updating loop


def test_an_updating_run_needs_fewer_eigensolves_with_reanalysis() -> None:
    """The whole point: the same twin experiment, converged on less work.

    Both runs use the analytical Fox & Kapoor sensitivities, so an iteration is
    a modal evaluation plus a frequency and a mode-shape sensitivity at the same
    ``θ`` — three requests the reanalysis cache serves with one eigensolve.
    """
    truth = {"k0": 0.82, "k1": 1.22, "k2": 0.94, "k3": 1.08}
    results = {}
    for reanalysis in (True, False):
        model = ScalingModel(
            **dense_parts(), num_modes=6, use_solver=False, reanalysis=reanalysis
        )
        target = model(truth)
        model.n_solves = model.n_eigen_calls = model.n_assemblies = 0
        parameters = [
            UpdatableParameter(name, 1.0, 0.5, 2.0) for name in model.parameter_names
        ]
        free = [parameter.name for parameter in parameters]
        results[reanalysis] = (
            model,
            update_model(
                model,
                parameters,
                target.frequencies,
                target.mode_shapes,
                sensitivity_function=model.sensitivity_function(free),
                shape_sensitivity_function=model.shape_sensitivity_function(free),
            ),
        )

    accelerated, accelerated_result = results[True]
    baseline, baseline_result = results[False]

    assert accelerated_result.converged and baseline_result.converged
    assert accelerated_result.iterations == baseline_result.iterations
    for name, value in truth.items():
        assert accelerated_result.parameters[name] == pytest.approx(value, abs=1.0e-4)
        assert accelerated_result.parameters[name] == pytest.approx(
            baseline_result.parameters[name], rel=1.0e-12
        )

    # Every iteration evaluates the model three times at one θ, so the cache
    # removes about two thirds of the eigensolves and all of the reassembly.
    assert accelerated.n_eigen_calls == baseline.n_eigen_calls
    assert accelerated.n_solves < baseline.n_solves
    assert accelerated.n_solves <= baseline.n_solves / 2
    assert accelerated.n_assemblies == accelerated.n_solves
