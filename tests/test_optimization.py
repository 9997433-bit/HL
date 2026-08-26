"""Contract tests for the optimization hook (spec MS-5, AC-OPT-001..004).

The Round 1 deliverable is the *design*: the lowering pipeline, the gradient
interface and the mode tracking are real and tested here; the only stub is
``ScipyBackend.solve`` (Round 2, GAP-12), whose stub-ness is itself pinned.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.exceptions import OptimizationError
from openfemlab.optimization import (
    DesignSpace,
    NaturalFrequency,
    Objective,
    OptimizationProblem,
    ShapeVariable,
    TotalMass,
    available_backends,
    check_gradient,
    compile_sizing_problem,
    frequency_floor,
    get_backend,
    minimize_sizing,
    problem_from_updater,
)
from openfemlab.updating import ModelUpdater, ScalingModel, UpdatableParameter

TWO_PI = 2.0 * np.pi


def chain_model(mass_scale: bool = True) -> ScalingModel:
    """Fixed 2-DOF spring chain: K = k1*K1 + k2*K2, M = I (+ pm * diag(1/2))."""
    K1 = np.array([[1.0, 0.0], [0.0, 0.0]])
    K2 = np.array([[1.0, -1.0], [-1.0, 1.0]])
    mass_parts = {"pm": np.diag([0.5, 0.5])} if mass_scale else None
    return ScalingModel(
        stiffness_parts={"k1": K1, "k2": K2},
        mass_parts=mass_parts,
        base_mass=np.eye(2),
    )


def sizing_parameters(include_mass: bool = True) -> list[UpdatableParameter]:
    params = [
        UpdatableParameter("k1", value=1.0, lower=0.2, upper=5.0),
        UpdatableParameter("k2", value=1.0, lower=0.2, upper=5.0),
    ]
    if include_mass:
        params.append(UpdatableParameter("pm", value=1.0, lower=0.1, upper=3.0, kind="mass"))
    return params


# ---------------------------------------------------------------------------
# design space
# ---------------------------------------------------------------------------


class TestDesignSpace:
    def test_vector_layout_bounds_and_clip(self):
        space = DesignSpace(sizing=sizing_parameters())
        assert space.names == ["k1", "k2", "pm"]
        assert np.allclose(space.x0(), [1.0, 1.0, 1.0])
        lo, hi = space.bounds()
        assert np.allclose(lo, [0.2, 0.2, 0.1])
        assert np.allclose(hi, [5.0, 5.0, 3.0])
        assert np.allclose(space.clip([10.0, 0.0, 1.0]), [5.0, 0.2, 1.0])

    def test_physical_mapping_includes_fixed_parameters(self):
        params = sizing_parameters()
        params[1].fixed = True
        space = DesignSpace(sizing=params)
        assert space.names == ["k1", "pm"]
        physical = space.to_physical([2.0, 0.5])
        assert physical == {"k1": 2.0, "k2": 1.0, "pm": 0.5}

    def test_log_scaled_chain_rule(self):
        params = [
            UpdatableParameter("k", value=2.0, lower=0.5, upper=8.0, log_scaled=True)
        ]
        space = DesignSpace(sizing=params)
        x = space.x0()
        assert np.isclose(x[0], np.log(2.0))
        assert np.isclose(space.chain(x)[0], 2.0)  # dp/dx = exp(x) = p

    def test_shape_variables_morph_linearly(self):
        basis = np.zeros((3, 3))
        basis[2, 1] = 1.0  # move node 2 in +y
        space = DesignSpace(
            sizing=sizing_parameters(include_mass=False),
            shape=[ShapeVariable("bulge", basis, lower=-0.5, upper=0.5)],
        )
        assert space.n_variables == 3
        coords = np.zeros((3, 3))
        morphed = space.apply_to_coordinates(coords, [1.0, 1.0, 0.25])
        assert np.isclose(morphed[2, 1], 0.25)
        physical = space.to_physical([1.0, 1.0, 0.25])
        assert np.isclose(physical["bulge"], 0.25)

    def test_rejects_duplicates_and_empty(self):
        with pytest.raises(OptimizationError):
            DesignSpace(
                sizing=[UpdatableParameter("a")],
                shape=[ShapeVariable("a", np.zeros((1, 3)))],
            )
        with pytest.raises(OptimizationError):
            DesignSpace()


# ---------------------------------------------------------------------------
# evaluator: modal integration, caching, analytic gradients
# ---------------------------------------------------------------------------


class TestLoweringAndGradients:
    def test_one_modal_solve_shared_by_objective_and_constraints(self):
        problem, evaluator = compile_sizing_problem(
            chain_model(),
            sizing_parameters(),
            Objective(TotalMass()),
            [frequency_floor(0, f_min=0.05)],
        )
        x0 = problem.x0
        problem.objective(x0)
        for constraint in problem.constraints:
            constraint.fun(x0)
        assert evaluator.n_modal_solves == 1

    def test_analytic_route_detected_for_scaling_model(self):
        _, evaluator = compile_sizing_problem(
            chain_model(), sizing_parameters(), TotalMass()
        )
        assert evaluator.analytic

    def test_total_mass_value_and_exact_gradient(self):
        problem, evaluator = compile_sizing_problem(
            chain_model(), sizing_parameters(), TotalMass()
        )
        x0 = problem.x0
        # M = I + pm * diag(1/2, 1/2): mass = 2 + pm, dm/dpm = 1, dm/dk = 0.
        assert np.isclose(problem.objective(x0), 3.0)
        assert np.allclose(problem.gradient(x0), [0.0, 0.0, 1.0])

    def test_frequency_gradients_pass_ac_opt_001(self):
        """AC-OPT-001: analytic vs central FD, rel. err <= 1e-6, seeded points."""
        problem, _ = compile_sizing_problem(
            chain_model(),
            sizing_parameters(),
            Objective(NaturalFrequency(0)),
            [frequency_floor(1, f_min=0.2)],
        )
        rng = np.random.default_rng(0)
        lo, hi = problem.bounds
        for _ in range(3):
            x = lo + (hi - lo) * rng.uniform(0.2, 0.8, size=lo.size)
            for fun, jac in [
                (problem.objective, problem.gradient),
                (problem.constraints[0].fun, problem.constraints[0].jac),
            ]:
                report = check_gradient(fun, jac, x, tolerance=1.0e-6)
                assert report.passed, str(report)

    def test_fd_fallback_used_for_plain_callables(self):
        def model(values):  # plain callable: no matrix derivatives
            k1, k2 = values["k1"], values["k2"]
            K = np.array([[k1 + k2, -k2], [-k2, k2]])
            lam = np.linalg.eigvalsh(K)
            return np.sqrt(np.clip(lam, 0.0, None)) / TWO_PI

        problem, evaluator = compile_sizing_problem(
            model, sizing_parameters(include_mass=False), NaturalFrequency(0)
        )
        assert not evaluator.analytic
        with pytest.warns(RuntimeWarning, match="finite differences"):
            g = problem.gradient(problem.x0)
        numeric = check_gradient(problem.objective, lambda x: g, problem.x0, tolerance=1e-4)
        assert numeric.passed

    def test_constraint_standardization_matches_spec(self):
        """MS-5.1: f_1 >= f_min lowered to g = 1 - f_1/f_min <= 0."""
        f_min = 0.1
        problem, evaluator = compile_sizing_problem(
            chain_model(),
            sizing_parameters(),
            TotalMass(),
            [frequency_floor(0, f_min=f_min)],
        )
        state = evaluator.state(problem.x0)
        f1 = state.tracked_frequency(0)
        assert np.isclose(problem.constraints[0].fun(problem.x0), 1.0 - f1 / f_min)


# ---------------------------------------------------------------------------
# mode tracking (AC-OPT-004 mechanism)
# ---------------------------------------------------------------------------


class TestModeTracking:
    def test_frequency_response_follows_physical_branch_across_crossing(self):
        # Two uncoupled SDOFs: K = diag(k1, k2), M = I -> shapes e1, e2.
        model = ScalingModel(
            stiffness_parts={
                "k1": np.diag([1.0, 0.0]),
                "k2": np.diag([0.0, 1.0]),
            },
            base_mass=np.eye(2),
        )
        params = [
            UpdatableParameter("k1", value=1.0, lower=0.1, upper=10.0),
            UpdatableParameter("k2", value=4.0, lower=0.1, upper=10.0, fixed=True),
        ]
        _, evaluator = compile_sizing_problem(model, params, NaturalFrequency(0))

        before = evaluator.state([1.0])  # k1 < k2: mode 0 is the k1 oscillator
        assert np.isclose(before.tracked_frequency(0) * TWO_PI, 1.0)

        after = evaluator.state([9.0])  # k1 > k2: eigen order swaps, tracking must not
        assert np.isclose(after.tracked_frequency(0) * TWO_PI, 3.0)
        assert np.isclose(after.tracked_frequency(1) * TWO_PI, 2.0)


# ---------------------------------------------------------------------------
# vector problem and backends
# ---------------------------------------------------------------------------


class TestProblemAndBackends:
    def test_bounds_are_validated_and_enforced(self):
        with pytest.raises(OptimizationError):
            OptimizationProblem(
                objective=lambda x: 0.0,
                x0=np.array([2.0]),
                bounds=(np.array([0.0]), np.array([1.0])),
            )
        problem = OptimizationProblem(
            objective=lambda x: 0.0,
            x0=np.array([0.5]),
            bounds=(np.array([0.0]), np.array([1.0])),
        )
        assert problem.feasible(np.array([1.0]))
        assert not problem.feasible(np.array([1.1]))
        assert np.allclose(problem.clip(np.array([-3.0])), [0.0])

    def test_backend_registry(self):
        assert available_backends() == ["slsqp", "trust-constr"]
        assert get_backend("trust-constr").method == "trust-constr"
        with pytest.raises(OptimizationError):
            get_backend("nelder-mead")

    def test_scipy_backend_is_the_round_2_stub(self):
        with pytest.raises(NotImplementedError, match="GAP-12"):
            minimize_sizing(
                chain_model(),
                sizing_parameters(),
                TotalMass(),
                [frequency_floor(0, f_min=0.05)],
            )


# ---------------------------------------------------------------------------
# updating interop
# ---------------------------------------------------------------------------


class TestUpdatingInterop:
    def test_updater_cost_and_gradient_through_the_vector_interface(self):
        model = chain_model(mass_scale=False)
        params = sizing_parameters(include_mass=False)
        target = model({"k1": 1.5, "k2": 0.8}).frequencies
        updater = ModelUpdater(
            model,
            params,
            target_frequencies=target,
            sensitivity_function=model.sensitivity_function(["k1", "k2"]),
        )
        problem = problem_from_updater(updater)
        assert problem.names == ["k1", "k2"]
        assert np.allclose(problem.x0, [1.0, 1.0])

        # Gauss-Newton gradient J^T r matches central FD of the cost.
        report = check_gradient(
            problem.objective, problem.gradient, problem.x0, tolerance=1.0e-6
        )
        assert report.passed, str(report)

        # Zero residual (and zero gradient) at the true parameters.
        x_true = np.array([1.5, 0.8])
        assert problem.objective(x_true) < 1.0e-16
        assert np.linalg.norm(problem.gradient(x_true)) < 1.0e-8
