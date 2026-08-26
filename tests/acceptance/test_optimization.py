"""M5 optimization acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 6).

Implemented here
----------------
- **AC-OPT-001** (oracle, MS-5.1) — the analytic mass and frequency gradients of
  the lowered problem match central finite differences to relative error 1e-6
  at three seeded feasible design points.
- **AC-OPT-002** (oracle, MS-5.2) — the reference sizing problem reaches its
  known optimum: objective within 1e-4 relative and the frequency floor active
  to ``|g| <= 1e-6``.  A two-link variant adds the part a one-variable oracle
  cannot gate: an optimum that *distributes* material unevenly between the
  variables, also known in closed form.
- **AC-OPT-003** (contract, MS-5.2) — every iterate the backend reports, and
  every point the model is asked to evaluate, satisfies the box bounds to 1e-12,
  including a run whose optimum sits on a bound.
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
from scipy.optimize import brentq

from openfemlab.correlation import mac
from openfemlab.optimization import (
    DesignSpace,
    ModalDesignEvaluator,
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


# ---------------------------------------------------------------------------
# Two-link chain: an optimum that is asymmetric, and one that sits on a bound
# ---------------------------------------------------------------------------
#
# The uniform oracle above is one-dimensional, and the multi-variable case is
# checked by sampling rather than against a closed form -- so nothing yet gates
# the solver on *distributing* material between variables, which is what sizing
# optimization is for.  Two links admit a closed form that does.
#
# With both links sized independently and each carrying ``CARRIED`` of mass per
# unit of stiffness on top of a unit non-structural mass per node,
#
#     K(k) = [[k1 + k2, -k2], [-k2, k2]]      M(k) = (1 + CARRIED S) I
#
# with ``S = k1 + k2``.  ``M`` is a multiple of the identity, so
# ``lambda = mu / (1 + CARRIED S)`` for the eigenvalues ``mu`` of ``K``, and
# ``det(K - mu I) = mu^2 - (k1 + 2 k2) mu + k1 k2``.  Total mass
# ``2 (1 + CARRIED S)`` is increasing in ``S``, so the objective *is* ``S``; at
# fixed ``S`` the fundamental is largest for the split ``(3S/5, 2S/5)``, where
# the polynomial becomes ``mu^2 - 1.4 S mu + 0.24 S^2`` with roots ``S/5`` and
# ``6S/5``.  The floor is therefore first met at
# ``S* = lambda*/(1/5 - CARRIED lambda*)`` and only at that split, so the
# optimum is the single asymmetric point ``(3 S*/5, 2 S*/5)``.
#
# With ``CARRIED = 1/10`` and ``lambda* = 1`` it is exactly ``(6, 4)`` at mass 4.

CARRIED = 0.1
TARGET_LAMBDA = 1.0
TARGET_F_MIN = np.sqrt(TARGET_LAMBDA) / TWO_PI

TWO_LINK_S = TARGET_LAMBDA / (0.2 - CARRIED * TARGET_LAMBDA)
TWO_LINK_OPTIMUM = np.array([0.6 * TWO_LINK_S, 0.4 * TWO_LINK_S])

#: trust-constr drives a KKT tolerance rather than SLSQP's ftol and needs an
#: order of magnitude more steps on the same problem.
TWO_LINK_BUDGET = {"slsqp": 100, "trust-constr": 300}


#: A minimum-mass objective is exactly linear, so trust-constr's quasi-Newton
#: Hessian has nothing to learn and scipy says so on every step.  The warning
#: is about the problem, not the run.
LINEAR_OBJECTIVE_WARNING = "ignore:delta_grad == 0.0:UserWarning"


def _two_link_mass(k1: float, k2: float) -> float:
    return 2.0 * (1.0 + CARRIED * (k1 + k2))


def _two_link_lambda(k1: float, k2: float) -> float:
    """``lambda_1`` of the two-link chain, computed without the code under test."""
    stiffness = np.array([[k1 + k2, -k2], [-k2, k2]])
    return float(np.linalg.eigvalsh(stiffness)[0]) / (1.0 + CARRIED * (k1 + k2))


def _two_link_chain() -> ScalingModel:
    carried = CARRIED * np.eye(2)
    return ScalingModel(
        {"k1": _link_stiffness(0, 2), "k2": _link_stiffness(1, 2)},
        {"k1": carried, "k2": carried},
        base_mass=np.eye(2),
        num_modes=2,
    )


def _two_link_parameters(start=(8.0, 8.0), lower=(0.5, 0.5)):
    return [
        UpdatableParameter(name, value=value, lower=lo, upper=20.0)
        for name, value, lo in zip(("k1", "k2"), start, lower, strict=True)
    ]


@criterion("AC-OPT-002")
def test_ac_opt_002_the_two_link_oracle_is_the_constrained_minimum():
    """Guard the oracle before gating against it.

    The closed form counts as an oracle only if it is the constrained minimum:
    it must sit on the frequency floor, with no neighbour both feasible and
    lighter.
    """
    assert np.allclose(TWO_LINK_OPTIMUM, [6.0, 4.0])
    assert _two_link_lambda(*TWO_LINK_OPTIMUM) == pytest.approx(TARGET_LAMBDA, abs=1e-14)
    assert _two_link_mass(*TWO_LINK_OPTIMUM) == pytest.approx(4.0, abs=1e-14)

    optimum = _two_link_mass(*TWO_LINK_OPTIMUM)
    for radius in (1e-3, 1e-2, 1e-1):
        for angle in np.linspace(0.0, 2.0 * np.pi, 24, endpoint=False):
            k = TWO_LINK_OPTIMUM + radius * np.array([np.cos(angle), np.sin(angle)])
            lighter = _two_link_mass(*k) < optimum - 1e-15
            assert not (lighter and _two_link_lambda(*k) >= TARGET_LAMBDA), (
                f"{k} is feasible and lighter than the claimed optimum"
            )


@criterion("AC-OPT-002")
@pytest.mark.filterwarnings(LINEAR_OBJECTIVE_WARNING)
@pytest.mark.parametrize("backend", sorted(TWO_LINK_BUDGET))
def test_ac_opt_002_two_link_optimum_splits_the_material_unevenly(backend):
    """The 3:2 split is recovered from a symmetric start: k* = (6, 4), mass 4."""
    result = minimize_sizing(
        _two_link_chain(),
        _two_link_parameters(),
        TotalMass(),
        [frequency_floor(0, f_min=TARGET_F_MIN)],
        backend=backend,
        max_iter=TWO_LINK_BUDGET[backend],
    )

    assert result.converged, result.report()
    expected = _two_link_mass(*TWO_LINK_OPTIMUM)
    assert result.objective == pytest.approx(expected, rel=OPTIMUM_RTOL)
    # The design, not only its objective: any point on the same mass contour
    # would pass the objective gate, and the start is symmetric, so the split
    # is the solver's work.
    assert result.x == pytest.approx(TWO_LINK_OPTIMUM, abs=1e-4)
    assert abs(result.max_violation) <= ACTIVE_TOLERANCE


@criterion("AC-OPT-003")
@pytest.mark.filterwarnings(LINEAR_OBJECTIVE_WARNING)
@pytest.mark.parametrize("backend", sorted(TWO_LINK_BUDGET))
def test_ac_opt_003_a_bound_tighter_than_the_optimum_is_never_crossed(backend):
    """With the optimum on a bound, the run has to work along the boundary.

    Raising the ``k2`` lower bound above its free optimum (4) moves the solution
    onto that bound rather than leaving it approached from well inside, which is
    where round-off in the bound handling would show.  The oracle is the
    smallest ``k1`` that still meets the floor at ``k2 = 5``, bracketed below the
    interior maximum of ``lambda_1(., 5)``.

    The two methods arrive differently, so the objective gate is the criterion's
    1e-4 rather than machine precision: SLSQP is an active-set method and lands
    on the bound exactly, trust-constr is a barrier method and stops a barrier
    width inside it.  What both must satisfy exactly is the *direction* of the
    error — neither may end up, or evaluate, below the bound.
    """
    floor = 5.0
    expected_k1 = brentq(
        lambda k1: _two_link_lambda(k1, floor) - TARGET_LAMBDA,
        0.5,
        1.5 * floor,
        xtol=1e-15,
        rtol=8.9e-16,
    )
    problem, _ = compile_sizing_problem(
        _two_link_chain(),
        _two_link_parameters(start=(9.0, 9.0), lower=(0.5, floor)),
        TotalMass(),
        [frequency_floor(0, f_min=TARGET_F_MIN)],
    )
    requested: list[np.ndarray] = []
    inner = problem.objective
    problem.objective = lambda x: (requested.append(np.asarray(x, float).ravel()), inner(x))[1]

    result = problem.solve(backend, max_iter=TWO_LINK_BUDGET[backend])

    assert result.converged, result.report()
    assert result.objective == pytest.approx(
        _two_link_mass(expected_k1, floor), rel=OPTIMUM_RTOL
    )
    assert result.x == pytest.approx([expected_k1, floor], abs=1e-3)

    assert result.x[1] >= floor - BOUND_TOLERANCE
    assert requested, "the spy must have seen the objective being evaluated"
    assert min(x[1] for x in requested) >= floor - BOUND_TOLERANCE
    assert all(iterate.in_bounds for iterate in result.history)

    if backend == "slsqp":
        # The KKT residual only vanishes here because the active bound carries
        # a multiplier of its own in ``kkt_residual``: df/dx = (0.2, 0.2) is not
        # in the cone of the constraint gradient (-3.8e-2, -6.2e-3) alone, which
        # a constraint-only fit reports as 0.166.
        assert result.x[1] == pytest.approx(floor, abs=1e-9)
        assert result.stationarity <= ACTIVE_TOLERANCE
    else:
        # The barrier keeps trust-constr strictly inside, so the bound is not
        # active at its solution and the residual legitimately does not vanish.
        assert 0.0 < result.x[1] - floor < 1e-3


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
