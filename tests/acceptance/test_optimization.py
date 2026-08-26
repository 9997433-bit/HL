"""M5 optimization acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 6).

Implemented here
----------------
- **AC-OPT-001** (oracle, MS-5.1) — the analytic mass and frequency gradients of
  the lowered problem match central finite differences to relative error 1e-6
  at three seeded feasible design points.
- **AC-OPT-002** (oracle, MS-5.2) — the reference sizing problem reaches its
  known optimum: objective within 1e-4 relative and the frequency floor active
  to ``|g| <= 1e-6``.
- **AC-OPT-003** (contract, MS-5.2) — every iterate the backend reports, and
  every point the model is asked to evaluate, satisfies the box bounds to 1e-12.
- **AC-OPT-004** (twin, MS-5.2) — driven along a design path on which two modes
  cross, the tracked frequency stays on its physical branch and consecutive
  tracked shapes keep MAC >= 0.9.

The reference model is a grounded spring-mass chain in which design variable
``t_j`` scales both the stiffness **and** the structural mass of link ``j``,
while each node also carries a fixed non-structural mass ``m_0``. Without
``m_0`` a uniform scaling would leave every frequency unchanged and the problem
would be degenerate; with it, minimizing mass genuinely fights the frequency
floor and the optimum sits on the constraint boundary, which is what
AC-OPT-002 asks for.

That gives the oracle a closed form. Scaling every link by one variable makes
``K(t) = t K_1`` and ``M(t) = (t m_s + m_0) I``, so
``lambda_i(t) = t mu_i / (t m_s + m_0)`` and ``f_1 >= f_min`` binds exactly at

    t* = w^2 m_0 / (mu_1 - w^2 m_s),      w = 2 pi f_min

with ``mu_1`` the smallest eigenvalue of ``K_1``.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.correlation import mac
from openfemlab.optimization import (
    Constraint,
    DesignSpace,
    ModalDesignEvaluator,
    NaturalFrequency,
    Objective,
    TotalMass,
    check_gradient,
    compile_sizing_problem,
    frequency_floor,
    minimize_sizing,
)
from openfemlab.updating import ScalingModel, UpdatableParameter

from ._support import criterion

#: Gates of AC-OPT-001..004.
GRADIENT_RTOL = 1e-6
OPTIMUM_RTOL = 1e-4
ACTIVE_TOLERANCE = 1e-6
BOUND_TOLERANCE = 1e-12
TRACKING_MAC = 0.9

#: Seeded feasible design points of AC-OPT-001; a criterion only counts if
#: it is deterministic.
GRADIENT_SEEDS = (0, 1, 2)

NUM_MASSES = 3
LINK_MASS = 1.0
FIXED_MASS = 0.5
LOWER, UPPER = 0.25, 6.0
F_MIN = 0.065

TWO_PI = 2.0 * np.pi


def _link_stiffness(link: int, num_masses: int = NUM_MASSES) -> np.ndarray:
    """Unit stiffness contribution of link ``link`` (link 0 ties mass 0 to ground)."""
    part = np.zeros((num_masses, num_masses))
    part[link, link] += 1.0
    if link > 0:
        part[link - 1, link - 1] += 1.0
        part[link, link - 1] -= 1.0
        part[link - 1, link] -= 1.0
    return part


def _sizing_chain(*, uniform: bool) -> ScalingModel:
    links = range(NUM_MASSES)
    if uniform:
        stiffness = {"t": sum(_link_stiffness(j) for j in links)}
        mass = {"t": LINK_MASS * np.eye(NUM_MASSES)}
    else:
        stiffness = {f"t{j + 1}": _link_stiffness(j) for j in links}
        mass = {f"t{j + 1}": LINK_MASS * np.diag(np.eye(NUM_MASSES)[j]) for j in links}
    return ScalingModel(
        stiffness, mass, base_mass=FIXED_MASS * np.eye(NUM_MASSES), num_modes=NUM_MASSES
    )


def _sizing_parameters(*, uniform: bool) -> list[UpdatableParameter]:
    names = ["t"] if uniform else [f"t{j + 1}" for j in range(NUM_MASSES)]
    return [UpdatableParameter(n, value=1.0, lower=LOWER, upper=UPPER) for n in names]


def _uniform_optimum(f_min: float = F_MIN) -> float:
    """``t*``: the closed-form design at which the frequency floor binds."""
    K1 = sum(_link_stiffness(j) for j in range(NUM_MASSES))
    mu_1 = float(np.linalg.eigvalsh(K1)[0])
    omega_squared = (TWO_PI * f_min) ** 2
    return omega_squared * FIXED_MASS / (mu_1 - omega_squared * LINK_MASS)


def _reference_problem(*, uniform: bool = False):
    return compile_sizing_problem(
        _sizing_chain(uniform=uniform),
        _sizing_parameters(uniform=uniform),
        TotalMass(),
        [frequency_floor(0, f_min=F_MIN)],
    )


@criterion("AC-OPT-001")
@pytest.mark.parametrize("seed", GRADIENT_SEEDS)
def test_ac_opt_001_gradients_match_central_differences(seed):
    """Analytic ``df/dx`` of objective and constraint within 1e-6 relative of FD."""
    problem, evaluator = _reference_problem()
    assert evaluator.analytic, "the oracle must exercise the Fox-Kapoor route"

    lower, upper = problem.bounds
    rng = np.random.default_rng(seed)
    x = lower + (upper - lower) * rng.uniform(0.15, 0.85, size=lower.size)

    for label, fun, jac in (
        ("objective", problem.objective, problem.gradient),
        ("constraint", problem.constraints[0].fun, problem.constraints[0].jac),
    ):
        report = check_gradient(fun, jac, x, tolerance=GRADIENT_RTOL)
        assert report.passed, f"{label}: {report}"


@criterion("AC-OPT-002")
def test_ac_opt_002_reference_problem_reaches_the_known_optimum():
    """Mass within 1e-4 relative of the closed form, floor active to 1e-6."""
    t_star = _uniform_optimum()
    assert LOWER < t_star < UPPER, "the oracle must lie strictly inside the box"
    expected_mass = NUM_MASSES * (t_star * LINK_MASS + FIXED_MASS)

    result = minimize_sizing(
        _sizing_chain(uniform=True),
        _sizing_parameters(uniform=True),
        TotalMass(),
        [frequency_floor(0, f_min=F_MIN)],
    )

    assert result.converged, result.report()
    assert result.objective == pytest.approx(expected_mass, rel=OPTIMUM_RTOL)
    assert result.variables["t"] == pytest.approx(t_star, rel=OPTIMUM_RTOL)
    assert abs(result.max_violation) <= ACTIVE_TOLERANCE
    assert result.active_set == [f"f1 >= {F_MIN:g}"]


@criterion("AC-OPT-002")
def test_ac_opt_002_no_feasible_sample_beats_the_multi_variable_optimum():
    """With three independent link sizes the optimum still dominates the feasible set."""
    result = minimize_sizing(
        _sizing_chain(uniform=False),
        _sizing_parameters(uniform=False),
        TotalMass(),
        [frequency_floor(0, f_min=F_MIN)],
    )
    assert result.converged, result.report()
    assert abs(result.max_violation) <= ACTIVE_TOLERANCE

    problem, _ = _reference_problem()
    lower, upper = problem.bounds
    rng = np.random.default_rng(20260826)
    feasible = 0
    for _ in range(80):
        x = lower + (upper - lower) * rng.random(problem.n_variables)
        if problem.constraints[0].fun(x) > 0.0:
            continue
        feasible += 1
        assert problem.objective(x) >= result.objective - 1e-8
    assert feasible >= 5, "the probe must actually sample feasible designs"


#: Payload-placement oracle: a coupled two-mass system carrying a required
#: mass, split between its two mounts.  ``dlambda_1/dm_j = -lambda_1 phi_j^2``,
#: so the split is stationary where the mode is equal-amplitude; for this ``K``
#: that mode is ``phi = (1, 1)``, giving ``m_1 = m_2`` and ``lambda_1 = 2/m_req``.
#: The floor binds from the other side than the sizing chain's does — a lighter
#: structure would be stiffer, so the *required* mass is what holds the optimum.
PAYLOAD_K = np.array([[2.0, -1.0], [-1.0, 2.0]])
REQUIRED_MASS = 2.0


def _payload_placement():
    model = ScalingModel(
        mass_parts={"m1": np.diag([1.0, 0.0]), "m2": np.diag([0.0, 1.0])},
        base_stiffness=PAYLOAD_K,
    )
    parameters = [
        UpdatableParameter("m1", value=1.6, lower=0.2, upper=5.0, kind="mass"),
        UpdatableParameter("m2", value=1.4, lower=0.2, upper=5.0, kind="mass"),
    ]
    return model, parameters


@criterion("AC-OPT-002")
@pytest.mark.parametrize("backend", ["slsqp", "trust-constr"])
def test_ac_opt_002_payload_placement_reaches_its_closed_form_optimum(backend):
    """A closed-form oracle for a genuinely multi-variable optimum.

    The sizing-chain oracle above pins one variable; here two interact, and the
    optimum is still known exactly rather than argued from sampling.
    """
    expected_frequency = np.sqrt(2.0 / REQUIRED_MASS) / (2.0 * np.pi)

    model, parameters = _payload_placement()
    result = minimize_sizing(
        model,
        parameters,
        Objective(NaturalFrequency(0), scale=-1.0),
        [Constraint(TotalMass(), bound=REQUIRED_MASS, kind=">=")],
        backend=backend,
        tol=1e-10,
        max_iter=200,
    )

    assert result.converged, result.report()
    frequency = -result.objective
    assert frequency == pytest.approx(expected_frequency, rel=OPTIMUM_RTOL)
    for name in ("m1", "m2"):
        assert result.variables[name] == pytest.approx(REQUIRED_MASS / 2.0, rel=1e-3)
    assert result.max_violation <= ACTIVE_TOLERANCE
    if backend == "slsqp":
        # An interior-point run stops a barrier width inside the boundary, so
        # only the active-set method is held to the activity gate.
        assert abs(result.max_violation) <= ACTIVE_TOLERANCE
        assert result.active_set == [f"total_mass >= {REQUIRED_MASS:g}"]


@criterion("AC-OPT-003")
def test_ac_opt_003_no_iterate_or_evaluation_leaves_the_box():
    """Recorded iterates and requested evaluations both obey the bounds to 1e-12."""
    problem, _ = _reference_problem()
    lower, upper = problem.bounds
    requested: list[np.ndarray] = []

    def spy(function):
        def wrapped(x):
            requested.append(np.asarray(x, dtype=float).ravel().copy())
            return function(x)

        return wrapped

    problem.objective = spy(problem.objective)
    problem.gradient = spy(problem.gradient)
    for constraint in problem.constraints:
        constraint.fun = spy(constraint.fun)
        constraint.jac = spy(constraint.jac)

    result = problem.solve("slsqp")

    assert result.history, "the backend must record its iterates"
    for iterate in result.history:
        assert iterate.in_bounds, iterate
        assert np.all(iterate.x >= lower - BOUND_TOLERANCE)
        assert np.all(iterate.x <= upper + BOUND_TOLERANCE)

    assert requested, "the spy must have seen the model being evaluated"
    for x in requested:
        assert np.all(x >= lower - BOUND_TOLERANCE)
        assert np.all(x <= upper + BOUND_TOLERANCE)
    assert problem.feasible(result.x, tolerance=BOUND_TOLERANCE)


@criterion("AC-OPT-004")
def test_ac_opt_004_tracked_mode_follows_its_branch_across_a_crossing():
    """Two uncoupled oscillators swap eigenvalue order; the tracked mode does not."""
    stiffness, other = 1.0, 1.0
    model = ScalingModel(
        {"a": np.diag([stiffness, 0.0])},
        base_stiffness=np.diag([0.0, other]),
        base_mass=np.eye(2),
        num_modes=2,
    )
    space = DesignSpace(
        sizing=[UpdatableParameter("a", value=0.5, lower=0.4, upper=2.0)]
    )
    evaluator = ModalDesignEvaluator(model, space)

    path = (0.5, 0.7, 0.9, 1.1, 1.3, 1.5)
    assert min(path) < other / stiffness < max(path), "the path must cross the second mode"

    tracked_shapes = []
    for amplitude in path:
        state = evaluator.state([amplitude])
        assert state.tracked_frequency(0) == pytest.approx(
            np.sqrt(amplitude * stiffness) / TWO_PI, rel=1e-9
        )
        assert state.tracked_frequency(1) == pytest.approx(
            np.sqrt(other) / TWO_PI, rel=1e-9
        )
        tracked_shapes.append(state.modal.mode_shapes[:, state.tracking[0]])

    consecutive = np.abs(
        np.diag(mac(np.column_stack(tracked_shapes[:-1]), np.column_stack(tracked_shapes[1:])))
    )
    assert np.all(consecutive >= TRACKING_MAC), consecutive


@criterion("AC-OPT-004")
def test_ac_opt_004_active_set_names_the_tracked_constraint():
    """The termination report identifies the constraint by its tracked mode."""
    result = minimize_sizing(
        _sizing_chain(uniform=True),
        _sizing_parameters(uniform=True),
        TotalMass(),
        [frequency_floor(0, f_min=F_MIN)],
    )
    assert result.active_set == [f"f1 >= {F_MIN:g}"]
    assert set(result.constraint_values) == {f"f1 >= {F_MIN:g}"}
