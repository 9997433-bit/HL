"""M5 optimization acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 6).

Implemented here
----------------
- **AC-OPT-001** (oracle, MS-5.1) — mass-objective and frequency-constraint
  gradients from the sensitivity kernel match central differences to relative
  error 1e-6 at three seeded feasible design points.
- **AC-OPT-002** (oracle, MS-5.2) — two sizing problems whose optima are known
  in closed form are recovered: objective within 1e-4 relative, active
  ``|g| <= 1e-6``.
- **AC-OPT-003** (contract, MS-5.2) — every recorded iterate satisfies the box
  to 1e-12, *and* no objective or constraint evaluation is requested outside
  it: the reference model records every parameter point it is asked for.  A
  third case puts the optimum itself on a bound, where the contract is hardest
  to keep and the reported KKT measure needs a bound multiplier to be right.
- **AC-OPT-004** (twin, MS-5.2) — across a mode crossing the constraint stays
  attached to the physical branch (MAC >= 0.9 against the previous iterate)
  and the active-constraint report names it consistently.

Reference problems
------------------
The AC-OPT-002 problems are solved analytically rather than against a stored
run, and each is the smallest system that makes its constraint bind.

*Sized oscillator* — the scenario the criteria document describes (minimize
total mass subject to ``f_1 >= f_min``, optimum on the constraint boundary).
The size variable ``t`` scales the spring **and** the structural mass it
carries, which is what makes the floor bind: with a mass-only
parameterization, mass appears solely in the denominator of ``lambda = k/m``,
so shedding mass would raise ``f_1`` for free and the floor could never be
active.  With ``K = t k`` and ``M = m_0 + t mu``,

    lambda(t) = t k / (m_0 + t mu)   =>   t* = lambda_min m_0 / (k - lambda_min mu)

and the optimal mass is ``m_0 k / (k - lambda_min mu)``.

*Payload placement* — a coupled two-mass system carrying a required payload,
split between the two mounting points to maximize the fundamental frequency.
For ``K = [[2, -1], [-1, 2]]`` the mode ``phi = (1, 1)`` equalizes
``dlambda_1/dm_j = -lambda_1 phi_j^2``, so the stationary split is the even
one: ``m_1 = m_2 = m_req / 2`` with ``lambda_1 = 2 / m_req``.  The mass floor
is active because a lighter structure would be stiffer still.

*Sized chain* — a two-group version of the sized oscillator, added because the
optimum of the other two is recoverable by a method that never has to choose
between the variables: the oscillator has one, and the payload optimum is the
symmetric point.  Here the two spring groups of a fixed-free two-mass chain are
sized independently, each carrying ``eps`` of mass per unit of stiffness::

    K(k) = [[k1 + k2, -k2], [-k2, k2]]      M(k) = (1 + eps S) I,  S = k1 + k2

``det(K - mu I) = mu^2 - (k1 + 2 k2) mu + k1 k2``, and since ``M`` is a multiple
of the identity, ``lambda = mu / (1 + eps S)``.  Total mass ``2 (1 + eps S)`` is
increasing in ``S``, so the objective is ``S``; at fixed ``S`` the fundamental
is largest for the split ``(3S/5, 2S/5)``, where the characteristic polynomial
becomes ``mu^2 - 1.4 S mu + 0.24 S^2`` with roots ``S/5`` and ``6S/5``.  The
floor therefore first becomes reachable at ``S* = lambda*/(1/5 - eps lambda*)``
and only at that split, so the optimum is the single asymmetric point
``k* = (3 S*/5, 2 S*/5)`` with mass ``2 (1 + eps S*)``.  With ``eps = 1/10`` and
``lambda* = 1``: ``k* = (6, 4)`` at mass 4, exactly.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.optimize import brentq

from openfemlab.correlation import mac_value
from openfemlab.optimization import (
    Constraint,
    NaturalFrequency,
    Objective,
    TotalMass,
    check_gradient,
    compile_sizing_problem,
    frequency_floor,
    minimize_sizing,
)
from openfemlab.updating import ScalingModel, UpdatableParameter

from ._support import criterion, spring_chain_parts

TWO_PI = 2.0 * np.pi

#: Gates of section 6.
GRADIENT_RTOL = 1e-6
OBJECTIVE_RTOL = 1e-4
ACTIVE_TOL = 1e-6
BOUND_TOL = 1e-12
TRACKING_MAC = 0.9

#: Backends required to agree on the reference optima.  SLSQP is the MS-5.2
#: default and the one the quantitative gates are read from; trust-constr is
#: an interior-point method, so it approaches an active constraint from inside
#: and settles a barrier width short of |g| = 0.
BACKENDS = ("slsqp", "trust-constr")


def _zero_hessian(n: int):
    """Exact objective Hessian of a linear (minimum-mass) objective."""
    return lambda x: np.zeros((n, n))


def _recording(model: ScalingModel) -> ScalingModel:
    """Wrap a model so every parameter point it is asked to solve is recorded."""
    model.requested = []  # type: ignore[attr-defined]
    inner_eigen, inner_assemble = model.eigen, model.assemble

    def eigen(values):
        model.requested.append(dict(values))  # type: ignore[attr-defined]
        return inner_eigen(values)

    def assemble(values):
        model.requested.append(dict(values))  # type: ignore[attr-defined]
        return inner_assemble(values)

    model.eigen = eigen  # type: ignore[method-assign]
    model.assemble = assemble  # type: ignore[method-assign]
    return model


# ---------------------------------------------------------------------------
# AC-OPT-001 — analytic gradients vs central finite differences
# ---------------------------------------------------------------------------


def _grouped_chain() -> tuple[ScalingModel, list[UpdatableParameter]]:
    """Fixed-free 4-mass chain, two stiffness groups and two mass groups."""
    stiffness_parts, mass_parts = spring_chain_parts(
        4, stiffness_groups=((1, 2), (3, 4)), mass_groups=((1, 2), (3, 4))
    )
    model = ScalingModel(stiffness_parts, mass_parts)
    params = [
        UpdatableParameter(name, value=1.0, lower=0.4, upper=2.5)
        for name in ("k1", "k2")
    ] + [
        UpdatableParameter(name, value=1.0, lower=0.4, upper=2.5, kind="mass")
        for name in ("m1", "m2")
    ]
    return model, params


@criterion("AC-OPT-001")
def test_analytic_gradients_match_central_differences():
    """Mass and frequency gradients agree with central FD at seeded points."""
    model, params = _grouped_chain()
    problem, evaluator = compile_sizing_problem(
        model,
        params,
        Objective(TotalMass()),
        [frequency_floor(0, f_min=0.05), Constraint(NaturalFrequency(1), 0.30, "<=")],
    )
    assert evaluator.analytic, "the analytic Fox-Kapoor route must be taken here"

    rng = np.random.default_rng(5)
    lower, upper = problem.bounds
    callbacks = [(problem.objective, problem.gradient, "objective")] + [
        (c.fun, c.jac, c.name) for c in problem.constraints
    ]
    worst = 0.0
    for _ in range(3):
        x = lower + (upper - lower) * rng.uniform(0.15, 0.85, size=lower.size)
        for fun, jac, label in callbacks:
            report = check_gradient(fun, jac, x, tolerance=GRADIENT_RTOL)
            assert report.passed, f"{label}: {report}"
            worst = max(worst, report.max_relative_error)
    assert worst <= GRADIENT_RTOL


# ---------------------------------------------------------------------------
# AC-OPT-002 — reference problems reach their known optima
# ---------------------------------------------------------------------------

#: Sized oscillator: K = t*STIFFNESS, M = BASE_MASS + t*SIZED_MASS.
STIFFNESS = 1.0
BASE_MASS = 1.0
SIZED_MASS = 0.5
LAMBDA_MIN = 0.5

#: Payload placement: required total mass on the coupled two-mass system.
COUPLED_K = np.array([[2.0, -1.0], [-1.0, 2.0]])
REQUIRED_MASS = 2.0


def _sized_oscillator() -> tuple[ScalingModel, list[UpdatableParameter]]:
    model = ScalingModel(
        stiffness_parts={"t": np.array([[STIFFNESS]])},
        mass_parts={"t": np.array([[SIZED_MASS]])},
        base_mass=np.array([[BASE_MASS]]),
    )
    return model, [UpdatableParameter("t", value=2.0, lower=0.1, upper=5.0)]


def _payload_placement() -> tuple[ScalingModel, list[UpdatableParameter]]:
    model = ScalingModel(
        mass_parts={"m1": np.diag([1.0, 0.0]), "m2": np.diag([0.0, 1.0])},
        base_stiffness=COUPLED_K,
    )
    params = [
        UpdatableParameter("m1", value=1.6, lower=0.2, upper=5.0, kind="mass"),
        UpdatableParameter("m2", value=1.4, lower=0.2, upper=5.0, kind="mass"),
    ]
    return model, params


@criterion("AC-OPT-002")
@pytest.mark.parametrize("backend", BACKENDS)
def test_sized_oscillator_reaches_the_closed_form_optimum(backend):
    """Minimum mass under a frequency floor: t* = lam m0 / (k - lam mu)."""
    expected_t = LAMBDA_MIN * BASE_MASS / (STIFFNESS - LAMBDA_MIN * SIZED_MASS)
    expected_mass = BASE_MASS * STIFFNESS / (STIFFNESS - LAMBDA_MIN * SIZED_MASS)

    model, params = _sized_oscillator()
    problem, _ = compile_sizing_problem(
        model,
        params,
        Objective(TotalMass()),
        [frequency_floor(0, f_min=np.sqrt(LAMBDA_MIN) / TWO_PI)],
        # Total mass is exactly linear in the size variable, so its Hessian is
        # exactly zero; telling trust-constr that beats approximating it.
        options={"hess": _zero_hessian(1)},
    )
    result = problem.solve(backend, tol=1e-12, max_iter=300)
    assert result.converged, result.message
    assert abs(result.objective - expected_mass) / expected_mass <= OBJECTIVE_RTOL
    assert result.variables["t"] == pytest.approx(expected_t, rel=OBJECTIVE_RTOL)
    # The floor binds: a lighter design would be too soft.
    assert result.max_violation <= ACTIVE_TOL
    if backend == "slsqp":
        assert abs(result.max_violation) <= ACTIVE_TOL
        assert result.active_set == ["f1 >= 0.11254"]


@criterion("AC-OPT-002")
@pytest.mark.parametrize("backend", BACKENDS)
def test_payload_placement_reaches_the_closed_form_optimum(backend):
    """Maximum f_1 under a required payload: the even split m_j = m_req / 2."""
    expected_split = REQUIRED_MASS / 2.0
    expected_frequency = np.sqrt(2.0 / REQUIRED_MASS) / TWO_PI

    model, params = _payload_placement()
    result = minimize_sizing(
        model,
        params,
        Objective(NaturalFrequency(0), scale=-1.0),
        [Constraint(TotalMass(), bound=REQUIRED_MASS, kind=">=")],
        backend=backend,
        tol=1e-12,
        max_iter=400,
    )
    assert result.converged, result.message
    frequency = -result.objective
    assert abs(frequency - expected_frequency) / expected_frequency <= OBJECTIVE_RTOL
    for name in ("m1", "m2"):
        assert result.variables[name] == pytest.approx(expected_split, rel=1e-3)
    assert result.max_violation <= ACTIVE_TOL
    if backend == "slsqp":
        assert abs(result.max_violation) <= ACTIVE_TOL
        assert result.active_set == ["total_mass >= 2"]


@criterion("AC-OPT-002")
def test_the_optimum_is_reached_without_one_modal_solve_per_gradient():
    """The analytic route is what makes the reference runs cheap (MS-5.2)."""
    model, params = _sized_oscillator()
    result = minimize_sizing(
        model,
        params,
        Objective(TotalMass()),
        [frequency_floor(0, f_min=np.sqrt(LAMBDA_MIN) / TWO_PI)],
        tol=1e-12,
    )
    # One solve per design point, not one per variable and side.
    assert result.n_modal_solves <= len(result.history) + 2


# ---------------------------------------------------------------------------
# AC-OPT-003 — box bounds are never violated
# ---------------------------------------------------------------------------


@criterion("AC-OPT-003")
@pytest.mark.parametrize("backend", BACKENDS)
def test_every_iterate_and_every_evaluation_stays_inside_the_box(backend):
    """No iterate and no *evaluation* leaves the box, including at a bound.

    The floor is set beyond what the upper bound can deliver, so the run is
    driven hard against the box and terminates infeasible — the case where a
    backend is most likely to overshoot.
    """
    model, params = _sized_oscillator()
    # t* = 2/3 is interior; narrow the box and push the floor past what it allows.
    params[0].upper = 1.0
    params[0].value = 0.5
    problem, evaluator = compile_sizing_problem(
        _recording(model),
        params,
        Objective(TotalMass()),
        # lambda = t k / (m0 + t mu) at t = 1 is 1/1.5 = 0.667 < 1.5
        [frequency_floor(0, f_min=np.sqrt(1.5) / TWO_PI)],
        options={"hess": _zero_hessian(1)},
    )
    result = problem.solve(backend, tol=1e-10, max_iter=200)

    lower, upper = problem.bounds
    assert result.history, "the backend must record its iterates"
    for iterate in result.history:
        assert np.all(iterate.x >= lower - BOUND_TOL)
        assert np.all(iterate.x <= upper + BOUND_TOL)
        assert iterate.in_bounds, f"iterate {iterate.iteration} was proposed outside the box"

    # Nothing was *solved* outside the box either.
    assert model.requested, "the recording wrapper saw no evaluation"
    for values in model.requested:
        assert 0.1 - BOUND_TOL <= values["t"] <= 1.0 + BOUND_TOL
    assert np.all(result.x >= lower - BOUND_TOL) and np.all(result.x <= upper + BOUND_TOL)
    assert evaluator.n_modal_solves == len({v["t"] for v in model.requested})


@criterion("AC-OPT-003")
def test_a_run_started_on_a_bound_stays_on_the_feasible_side():
    model, params = _payload_placement()
    params[0].value = params[0].lower  # start pinned to the lower bound
    problem, _ = compile_sizing_problem(
        model,
        params,
        Objective(NaturalFrequency(0), scale=-1.0),
        [Constraint(TotalMass(), bound=REQUIRED_MASS, kind=">=")],
    )
    result = problem.solve("slsqp", tol=1e-12, max_iter=200)
    lower, upper = problem.bounds
    assert all(iterate.in_bounds for iterate in result.history)
    assert np.all(result.x >= lower - BOUND_TOL) and np.all(result.x <= upper + BOUND_TOL)


# ---------------------------------------------------------------------------
# Sized chain — an optimum that is neither one-dimensional nor symmetric
# ---------------------------------------------------------------------------

#: Mass carried per unit of stiffness, and the frequency floor as an eigenvalue.
CHAIN_COUPLING = 0.1
CHAIN_LAMBDA = 1.0

#: Closed-form optimum of the sized chain (see the module docstring).
CHAIN_S_STAR = CHAIN_LAMBDA / (0.2 - CHAIN_COUPLING * CHAIN_LAMBDA)
CHAIN_K_STAR = np.array([0.6 * CHAIN_S_STAR, 0.4 * CHAIN_S_STAR])


def _chain_eigenvalue(k1: float, k2: float) -> float:
    """``lambda_1`` of the sized chain, computed without the code under test."""
    stiffness = np.array([[k1 + k2, -k2], [-k2, k2]])
    return float(np.linalg.eigvalsh(stiffness)[0]) / (
        1.0 + CHAIN_COUPLING * (k1 + k2)
    )


def _chain_mass(k1: float, k2: float) -> float:
    return 2.0 * (1.0 + CHAIN_COUPLING * (k1 + k2))


def _sized_chain(lower=(0.5, 0.5), start=(8.0, 8.0)):
    stiffness_parts, _ = spring_chain_parts(2, ((1,), (2,)), ())
    carried = CHAIN_COUPLING * np.eye(2)
    model = ScalingModel(
        stiffness_parts=stiffness_parts,
        mass_parts={name: carried for name in stiffness_parts},
        base_mass=np.eye(2),
    )
    params = [
        UpdatableParameter(name, value=value, lower=lo, upper=20.0)
        for name, value, lo in zip(("k1", "k2"), start, lower, strict=True)
    ]
    return model, params


#: The chain deliberately does *not* pass the exact zero objective Hessian the
#: sized oscillator uses.  Here the curvature lives entirely in the frequency
#: constraint, whose Hessian the backend neglects; declaring the objective's
#: exact zero as well leaves the trust-region subproblem with no curvature at
#: all, and the run stalls at 2e-3 relative instead of converging.  Keeping the
#: quasi-Newton objective Hessian costs scipy's "delta_grad == 0.0" warning on
#: every step -- the exact linearity it is complaining about is the reason.
CHAIN_LINEAR_OBJECTIVE_WARNING = "ignore:delta_grad == 0.0:UserWarning"


def _solve_sized_chain(backend: str, model, params, **kwargs):
    problem, _ = compile_sizing_problem(
        model,
        params,
        Objective(TotalMass()),
        [frequency_floor(0, f_min=np.sqrt(CHAIN_LAMBDA) / TWO_PI)],
    )
    return problem, problem.solve(backend, **kwargs)


@criterion("AC-OPT-002")
def test_the_sized_chain_optimum_is_the_constrained_minimum():
    """Guard the oracle before gating against it.

    The closed form is only an oracle if it is the constrained minimum: it has
    to sit exactly on the frequency floor, with no neighbouring design both
    feasible and lighter.
    """
    assert np.allclose(CHAIN_K_STAR, [6.0, 4.0])
    assert _chain_eigenvalue(*CHAIN_K_STAR) == pytest.approx(CHAIN_LAMBDA, abs=1e-14)
    assert _chain_mass(*CHAIN_K_STAR) == pytest.approx(4.0, abs=1e-14)

    optimal_mass = _chain_mass(*CHAIN_K_STAR)
    angles = np.linspace(0.0, 2.0 * np.pi, 24, endpoint=False)
    for radius in (1e-3, 1e-2, 1e-1):
        for angle in angles:
            k = CHAIN_K_STAR + radius * np.array([np.cos(angle), np.sin(angle)])
            lighter = _chain_mass(*k) < optimal_mass - 1e-15
            feasible = _chain_eigenvalue(*k) >= CHAIN_LAMBDA
            assert not (lighter and feasible), f"{k} beats the claimed optimum"


@criterion("AC-OPT-002")
@pytest.mark.filterwarnings(CHAIN_LINEAR_OBJECTIVE_WARNING)
@pytest.mark.parametrize("backend", BACKENDS)
def test_sized_chain_reaches_its_asymmetric_optimum(backend):
    """Both variables must be sized *differently*: k* = (6, 4), mass 4."""
    model, params = _sized_chain()
    problem, result = _solve_sized_chain(
        backend, model, params, tol=1e-10, max_iter=300
    )

    assert result.converged, result.message
    expected = _chain_mass(*CHAIN_K_STAR)
    assert abs(result.objective - expected) / expected <= OBJECTIVE_RTOL
    assert result.x == pytest.approx(CHAIN_K_STAR, abs=1e-4)
    assert result.max_violation <= ACTIVE_TOL
    # The starting point is symmetric, so the split is the solver's doing.
    assert problem.x0[0] == problem.x0[1]
    if backend == "slsqp":
        assert abs(result.max_violation) <= ACTIVE_TOL
        assert result.active_set == [problem.constraints[0].name]


@criterion("AC-OPT-003")
@pytest.mark.filterwarnings(CHAIN_LINEAR_OBJECTIVE_WARNING)
@pytest.mark.parametrize("backend", BACKENDS)
def test_a_bound_tighter_than_the_free_optimum_is_never_crossed(backend):
    """With the optimum *on* a bound, the run works along the boundary.

    Raising the lower bound of ``k2`` above its free optimum (4) moves the
    solution onto that bound, instead of approaching it from well inside.  The
    oracle is the smallest ``k1`` still meeting the floor at ``k2 = 5``,
    bracketed below the interior maximum of ``lambda_1(., 5)``.

    The two methods arrive differently, so the objective gate is the
    criterion's 1e-4 rather than machine precision: SLSQP is an active-set
    method and lands on the bound exactly, trust-constr is a barrier method and
    stops a barrier width inside it.  What both must satisfy exactly is the
    *direction* of the error — neither may end up, or evaluate, below the bound.
    """
    floor = 5.0
    expected_k1 = brentq(
        lambda k1: _chain_eigenvalue(k1, floor) - CHAIN_LAMBDA,
        0.5,
        1.5 * floor,
        xtol=1e-15,
        rtol=8.9e-16,
    )
    model, params = _sized_chain(lower=(0.5, floor), start=(9.0, 9.0))
    _, result = _solve_sized_chain(
        backend, _recording(model), params, tol=1e-10, max_iter=300
    )

    assert result.converged, result.message
    expected_mass = _chain_mass(expected_k1, floor)
    assert result.objective == pytest.approx(expected_mass, rel=OBJECTIVE_RTOL)
    assert result.x == pytest.approx([expected_k1, floor], abs=1e-3)

    assert result.x[1] >= floor - BOUND_TOL
    assert min(values["k2"] for values in model.requested) >= floor - BOUND_TOL
    assert all(iterate.in_bounds for iterate in result.history)
    # The KKT residual only vanishes here if the bound carries a multiplier of
    # its own; fitting the constraint multiplier first and projecting the bound
    # out afterwards leaves ~2.6e-2 behind in the free component.
    assert result.stationarity <= 1e-6


# ---------------------------------------------------------------------------
# AC-OPT-004 — mode tracking across a crossing
# ---------------------------------------------------------------------------

#: Two uncoupled oscillators; only the first is sized, so the branches cross
#: as its stiffness grows past the fixed one.
CROSSING_SIZED_MASS = 0.05
CROSSING_BASE_MASS = 1.0
CROSSING_FIXED_K = 4.0
CROSSING_TARGET_LAMBDA = 5.0


def _crossing_problem():
    model = ScalingModel(
        stiffness_parts={"k1": np.diag([1.0, 0.0]), "k2": np.diag([0.0, 1.0])},
        mass_parts={"k1": np.diag([CROSSING_SIZED_MASS, 0.0])},
        base_mass=CROSSING_BASE_MASS * np.eye(2),
    )
    params = [
        UpdatableParameter("k1", value=1.0, lower=0.5, upper=20.0),
        UpdatableParameter("k2", value=CROSSING_FIXED_K, lower=0.5, upper=20.0, fixed=True),
    ]
    return compile_sizing_problem(
        model,
        params,
        Objective(TotalMass()),
        [frequency_floor(0, f_min=np.sqrt(CROSSING_TARGET_LAMBDA) / TWO_PI)],
    )


@criterion("AC-OPT-004")
def test_the_constraint_follows_the_physical_branch_across_a_crossing():
    """The sized branch starts below the fixed one and ends above it.

    Without tracking the constraint would slide onto the fixed oscillator at
    the crossing, which cannot move, and the run would stop early at the wrong
    design.  The closed form of the tracked problem is
    ``k1* = lambda m0 / (1 - lambda mu)``.
    """
    expected_k1 = (
        CROSSING_TARGET_LAMBDA
        * CROSSING_BASE_MASS
        / (1.0 - CROSSING_TARGET_LAMBDA * CROSSING_SIZED_MASS)
    )
    expected_mass = 2.0 * CROSSING_BASE_MASS + CROSSING_SIZED_MASS * expected_k1
    crossing_k1 = CROSSING_FIXED_K / (1.0 - CROSSING_FIXED_K * CROSSING_SIZED_MASS)

    problem, evaluator = _crossing_problem()
    result = problem.solve("slsqp", tol=1e-12, max_iter=200)

    assert result.converged, result.message
    assert result.x[0] == pytest.approx(expected_k1, rel=OBJECTIVE_RTOL)
    assert result.objective == pytest.approx(expected_mass, rel=OBJECTIVE_RTOL)
    # The path really did cross: it starts below and ends above the crossing.
    assert problem.x0[0] < crossing_k1 < result.x[0]

    # The constraint is active on the tracked branch...
    assert result.active_set == [problem.constraints[0].name]
    assert abs(result.max_violation) <= ACTIVE_TOL
    solution = evaluator.state(result.x)
    assert solution.tracked_frequency(0) == pytest.approx(
        np.sqrt(CROSSING_TARGET_LAMBDA) / TWO_PI, rel=OBJECTIVE_RTOL
    )
    # ...and tracking is load-bearing: by raw eigen order, mode 0 at the
    # solution is the *fixed* oscillator, a different frequency entirely.
    assert solution.tracking[0] == 1
    assert solution.modal.frequencies[0] == pytest.approx(
        np.sqrt(CROSSING_FIXED_K) / TWO_PI, rel=1e-9
    )


@criterion("AC-OPT-004")
def test_tracked_shape_keeps_mac_above_the_gate_between_iterates():
    """MAC >= 0.9 against the previous iterate, all along the design path."""
    problem, evaluator = _crossing_problem()
    result = problem.solve("slsqp", tol=1e-12, max_iter=200)

    def tracked_shape(x):
        state = evaluator.state(x)
        return np.asarray(state.modal.mode_shapes)[:, int(state.tracking[0])]

    designs = [iterate.x for iterate in result.history]
    assert len(designs) >= 2
    worst = min(
        mac_value(tracked_shape(previous), tracked_shape(current))
        for previous, current in zip(designs[:-1], designs[1:], strict=True)
    )
    assert worst >= TRACKING_MAC, f"tracked mode drifted: worst MAC {worst:.4f}"
