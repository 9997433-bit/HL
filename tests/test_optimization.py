"""Contract tests for the optimization hook (spec MS-5, AC-OPT-001..004).

Covers the whole path: the design space, the lowering pipeline, both gradient
routes, mode tracking, the scipy backends, and the seam that re-expresses a
model-updating run as the same vector problem.  The quantified acceptance
gates themselves live in ``tests/acceptance/test_optimization.py``; what is
pinned here is the behaviour those gates rest on.

The reference sizing problem is a chain whose links carry both stiffness and
structural mass on top of a fixed non-structural mass, so minimizing mass
genuinely fights a frequency floor and the optimum sits on the constraint
boundary.
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
    ScipyBackend,
    ShapeVariable,
    TotalMass,
    available_backends,
    check_gradient,
    compile_sizing_problem,
    frequency_floor,
    get_backend,
    kkt_residual,
    minimize_sizing,
    problem_from_updater,
)
from openfemlab.updating import ModelUpdater, ScalingModel, UpdatableParameter

TWO_PI = 2.0 * np.pi

#: Structural and non-structural mass per link of the sizing reference chain.
LINK_MASS = 1.0
FIXED_MASS = 0.5


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


def link_stiffness(num_masses: int, link: int) -> np.ndarray:
    """Unit stiffness contribution of link ``link`` of a grounded chain."""
    part = np.zeros((num_masses, num_masses))
    part[link, link] += 1.0
    if link > 0:
        part[link - 1, link - 1] += 1.0
        part[link, link - 1] -= 1.0
        part[link - 1, link] -= 1.0
    return part


def sizing_chain(num_masses: int = 3, *, uniform: bool = False) -> ScalingModel:
    """Chain whose links carry stiffness *and* structural mass (see the module docstring)."""
    if uniform:
        stiffness = {"t": sum(link_stiffness(num_masses, j) for j in range(num_masses))}
        mass = {"t": LINK_MASS * np.eye(num_masses)}
    else:
        stiffness = {f"t{j + 1}": link_stiffness(num_masses, j) for j in range(num_masses)}
        mass = {
            f"t{j + 1}": LINK_MASS * np.diag(np.eye(num_masses)[j]) for j in range(num_masses)
        }
    return ScalingModel(
        stiffness, mass, base_mass=FIXED_MASS * np.eye(num_masses), num_modes=num_masses
    )


def sizing_chain_parameters(num_masses: int = 3, *, uniform: bool = False):
    names = ["t"] if uniform else [f"t{j + 1}" for j in range(num_masses)]
    return [UpdatableParameter(name, value=1.0, lower=0.25, upper=6.0) for name in names]


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

    def test_backend_settings_are_validated(self):
        with pytest.raises(OptimizationError, match="unknown scipy method"):
            ScipyBackend(method="powell")
        with pytest.raises(OptimizationError, match="tolerance must be positive"):
            ScipyBackend(tol=0.0)
        with pytest.raises(OptimizationError, match="max_iter"):
            ScipyBackend(max_iter=0)

    def test_backend_refuses_to_differentiate_internally(self):
        """MS-5.2: a hidden 2-point jacobian would cost one modal solve per column."""
        problem = OptimizationProblem(
            objective=lambda x: float(x @ x),
            x0=np.array([0.5]),
            bounds=(np.zeros(1), np.ones(1)),
        )
        with pytest.raises(OptimizationError, match="no gradient callback"):
            problem.solve("slsqp")

    def test_unconstrained_problem_reaches_the_interior_minimum(self):
        problem = OptimizationProblem(
            objective=lambda x: float((x[0] - 0.25) ** 2),
            x0=np.array([0.9]),
            bounds=(np.zeros(1), np.ones(1)),
            gradient=lambda x: np.array([2.0 * (x[0] - 0.25)]),
        )
        result = problem.solve("slsqp")
        assert result.converged, result.report()
        assert np.isclose(result.x[0], 0.25, atol=1e-6)
        assert result.stationarity == pytest.approx(0.0, abs=1e-6)
        assert result.active_set == []
        assert result.n_evaluations > 0

    def test_kkt_residual_reads_the_active_set(self):
        bounds = (np.zeros(1), np.ones(1))
        interior = np.array([0.5])
        assert kkt_residual(np.array([0.0]), {}, interior, bounds) == pytest.approx(0.0)
        assert kkt_residual(np.array([2.0]), {}, interior, bounds) == pytest.approx(1.0)
        # Pressed against the lower bound, a downhill gradient is still stationary.
        assert kkt_residual(np.array([2.0]), {}, np.zeros(1), bounds) == pytest.approx(
            0.0, abs=1e-12
        )

    def test_unreachable_constraint_reports_failure_inside_the_box(self):
        """A floor the box cannot reach fails loudly rather than escaping the bounds."""
        result = minimize_sizing(
            sizing_chain(2),
            sizing_chain_parameters(2),
            TotalMass(),
            [frequency_floor(0, f_min=10.0)],
        )
        assert not result.converged
        assert result.max_violation > 0.0
        assert np.all(result.x >= 0.25 - 1e-12) and np.all(result.x <= 6.0 + 1e-12)


class TestSizingRuns:
    """End-to-end runs of the reference sizing problem through both backends."""

    @staticmethod
    def uniform_optimum(num_masses: int, f_min: float) -> float:
        """Closed-form ``t*`` where the floor binds: see the module docstring."""
        K1 = sum(link_stiffness(num_masses, j) for j in range(num_masses))
        mu_1 = float(np.linalg.eigvalsh(K1)[0])
        omega_squared = (TWO_PI * f_min) ** 2
        return omega_squared * FIXED_MASS / (mu_1 - omega_squared * LINK_MASS)

    def test_uniform_chain_lands_on_the_closed_form_optimum(self):
        num_masses, f_min = 3, 0.065
        t_star = self.uniform_optimum(num_masses, f_min)
        assert 0.25 < t_star < 6.0

        result = minimize_sizing(
            sizing_chain(num_masses, uniform=True),
            sizing_chain_parameters(num_masses, uniform=True),
            TotalMass(),
            [frequency_floor(0, f_min=f_min)],
        )

        assert result.converged, result.report()
        assert result.variables["t"] == pytest.approx(t_star, rel=1e-4)
        assert abs(result.max_violation) <= 1e-6
        assert result.active_set == [f"f1 >= {f_min:g}"]
        assert result.n_modal_solves > 0
        assert "design variables" in result.report()

    @pytest.mark.filterwarnings("ignore:delta_grad == 0.0")  # a linear mass objective
    def test_trust_constr_agrees_with_slsqp(self):
        num_masses, f_min = 3, 0.065
        arguments = (
            sizing_chain(num_masses, uniform=True),
            sizing_chain_parameters(num_masses, uniform=True),
            TotalMass(),
            [frequency_floor(0, f_min=f_min)],
        )
        slsqp = minimize_sizing(*arguments, backend="slsqp")
        trust = minimize_sizing(*arguments, backend="trust-constr", tol=1e-10)
        assert trust.converged, trust.report()
        assert trust.objective == pytest.approx(slsqp.objective, rel=1e-4)

    def test_multi_variable_optimum_beats_every_feasible_sample(self):
        num_masses, f_min = 3, 0.066
        model, parameters = sizing_chain(num_masses), sizing_chain_parameters(num_masses)
        result = minimize_sizing(
            model, parameters, TotalMass(), [frequency_floor(0, f_min)]
        )
        assert result.converged, result.report()
        assert result.stationarity < 1e-4

        problem, _ = compile_sizing_problem(
            model,
            sizing_chain_parameters(num_masses),
            TotalMass(),
            [frequency_floor(0, f_min)],
        )
        lo, hi = problem.bounds
        rng = np.random.default_rng(7)
        feasible = 0
        for _ in range(80):
            x = lo + (hi - lo) * rng.random(problem.n_variables)
            if problem.constraints[0].fun(x) > 0.0:
                continue
            feasible += 1
            assert problem.objective(x) >= result.objective - 1e-8
        assert feasible >= 5, "the random probe must actually hit feasible designs"


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
