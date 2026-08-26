"""M5 optimization acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 6).

Implemented here
----------------
- **AC-OPT-002** (oracle, MS-5.2) — the reference sizing problem converges to
  its closed-form optimum: objective within 1e-4 relative, active constraint
  ``|g| <= 1e-6``.
- **AC-OPT-003** (contract, MS-5.2) — no design point outside the box ever
  reaches the model, and every recorded iterate satisfies the bounds to 1e-12,
  including a run whose optimum sits *on* a bound.

The reference problem
---------------------
A fixed-free two-mass chain whose two spring groups are the design variables,
sized against a frequency floor.  Each group carries mass as well as stiffness
(``eps`` per unit of ``k``), which is what makes the statement a sizing problem
rather than a free lunch: without the coupling, "minimize mass subject to
``f_1 >= f_min``" would be solved by shrinking every variable to its lower
bound::

    K(k) = [[k1 + k2, -k2], [-k2, k2]]      M(k) = (1 + eps S) I,  S = k1 + k2

Its optimum is known in closed form, which is what makes this an *oracle*
rather than a regression test:

1. ``det(K - mu I) = mu^2 - (k1 + 2 k2) mu + k1 k2``, and because ``M`` is a
   multiple of the identity the generalized eigenvalues are ``lambda =
   mu / (1 + eps S)``.
2. Total mass ``e^T M e = 2 (1 + eps S)`` is increasing in ``S``, so minimizing
   mass is minimizing ``S``.
3. At fixed ``S`` the fundamental ``mu_1`` is largest for the split
   ``(k1, k2) = (3S/5, 2S/5)``: substituting gives ``mu^2 - 1.4 S mu + 0.24
   S^2 = 0``, whose roots are ``S/5`` and ``6S/5``, so ``mu_1 = S/5``.
4. The frequency floor therefore first becomes reachable at
   ``S* = lambda* / (1/5 - eps lambda*)``, and only at the maximizing split —
   so the optimum is the single point ``k* = (3 S*/5, 2 S*/5)`` with mass
   ``2 (1 + eps S*)``, sitting exactly on the constraint boundary.

With ``eps = 1/10`` and ``lambda* = 1`` the numbers are exact:
``S* = 10``, ``k* = (6, 4)``, ``mass* = 4``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
from scipy.optimize import brentq

from openfemlab.optimization import (
    Objective,
    OptimizationResult,
    TotalMass,
    frequency_floor,
    minimize_sizing,
)
from openfemlab.updating import ScalingModel, UpdatableParameter

from ._support import criterion, spring_chain_parts

TWO_PI = 2.0 * np.pi

#: Gates of AC-OPT-002 and AC-OPT-003.
OBJECTIVE_RTOL = 1.0e-4
ACTIVE_TOL = 1.0e-6
BOUND_TOL = 1.0e-12

#: Mass carried per unit of stiffness — the sizing coupling.
MASS_COUPLING = 0.1

#: Frequency floor, as the eigenvalue ``lambda* = (2 pi f_min)^2``.
LAMBDA_TARGET = 1.0
F_MIN = np.sqrt(LAMBDA_TARGET) / TWO_PI

#: Closed-form optimum (see the module docstring).
S_STAR = LAMBDA_TARGET / (0.2 - MASS_COUPLING * LAMBDA_TARGET)
K_STAR = np.array([0.6 * S_STAR, 0.4 * S_STAR])
MASS_STAR = 2.0 * (1.0 + MASS_COUPLING * S_STAR)

#: The methods of ``ScipyBackend`` with the iteration budget each needs here.
#: trust-constr spends an order of magnitude more steps than SLSQP on the same
#: problem: it drives ``gtol`` (a KKT measure) rather than SLSQP's ``ftol``.
BACKENDS = {"slsqp": 100, "trust-constr": 200}


def reference_model() -> ScalingModel:
    """The sizing model of the module docstring."""
    stiffness_parts, _ = spring_chain_parts(2, ((1,), (2,)), ())
    coupled_mass = MASS_COUPLING * np.eye(2)
    return ScalingModel(
        stiffness_parts=stiffness_parts,
        mass_parts={name: coupled_mass for name in stiffness_parts},
        base_mass=np.eye(2),
    )


def reference_parameters(
    start: tuple[float, float] = (8.0, 8.0),
    lower: tuple[float, float] = (0.5, 0.5),
    upper: tuple[float, float] = (20.0, 20.0),
) -> list[UpdatableParameter]:
    return [
        UpdatableParameter(name, value=value, lower=lo, upper=hi)
        for name, value, lo, hi in zip(
            ("k1", "k2"), start, lower, upper, strict=True
        )
    ]


def fundamental_eigenvalue(k1: float, k2: float) -> float:
    """``lambda_1`` of the reference chain, independent of the code under test."""
    stiffness = np.array([[k1 + k2, -k2], [-k2, k2]])
    mass = 1.0 + MASS_COUPLING * (k1 + k2)
    return float(np.linalg.eigvalsh(stiffness / mass)[0])


def total_mass(k1: float, k2: float) -> float:
    return 2.0 * (1.0 + MASS_COUPLING * (k1 + k2))


class RecordingModel:
    """Reference model that logs every design point it is asked to evaluate.

    Forwards the whole :class:`~openfemlab.optimization.gradients.
    MatrixDerivativeProvider` surface, so wrapping does not push the evaluator
    off its analytic gradient route.
    """

    def __init__(self) -> None:
        self.inner = reference_model()
        self.parameter_names = self.inner.parameter_names
        self.points: list[dict[str, float]] = []

    def eigen(self, values: Any) -> Any:
        self.points.append(dict(values))
        return self.inner.eigen(values)

    def assemble(self, values: Any) -> Any:
        self.points.append(dict(values))
        return self.inner.assemble(values)

    def derivatives(self, names: Any = None) -> Any:
        return self.inner.derivatives(names)

    def __call__(self, values: Any) -> Any:
        self.points.append(dict(values))
        return self.inner(values)


def solve_reference(
    backend: str,
    model: Any = None,
    params: list[UpdatableParameter] | None = None,
) -> OptimizationResult:
    """Minimize total mass subject to the frequency floor."""
    return minimize_sizing(
        reference_model() if model is None else model,
        reference_parameters() if params is None else params,
        Objective(TotalMass()),
        [frequency_floor(0, f_min=F_MIN)],
        backend=backend,
        max_iter=BACKENDS[backend],
    )


# ---------------------------------------------------------------------------
# AC-OPT-002 — reference problem reaches the known optimum
# ---------------------------------------------------------------------------


@criterion("AC-OPT-002")
def test_ac_opt_002_closed_form_optimum_is_the_constrained_minimum():
    """Guard the oracle before gating against it.

    The closed form is only an oracle if it really is the constrained minimum:
    it must sit exactly on the frequency floor, and every neighbouring design
    must be either heavier or infeasible.
    """
    assert np.allclose(K_STAR, [6.0, 4.0])
    assert fundamental_eigenvalue(*K_STAR) == pytest.approx(LAMBDA_TARGET, abs=1e-14)
    assert total_mass(*K_STAR) == pytest.approx(MASS_STAR, abs=1e-14)

    angles = np.linspace(0.0, 2.0 * np.pi, 24, endpoint=False)
    for radius in (1e-3, 1e-2, 1e-1):
        for angle in angles:
            k = K_STAR + radius * np.array([np.cos(angle), np.sin(angle)])
            cheaper = total_mass(*k) < MASS_STAR - 1e-15
            feasible = fundamental_eigenvalue(*k) >= LAMBDA_TARGET
            assert not (cheaper and feasible), (
                f"design {k} is both feasible and lighter than the claimed optimum"
            )


@criterion("AC-OPT-002")
@pytest.mark.filterwarnings("ignore:delta_grad == 0.0:UserWarning")
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_opt_002_reference_problem_reaches_the_known_optimum(backend):
    """Objective within 1e-4 relative of the closed form, constraint active."""
    result = solve_reference(backend)

    assert result.converged, result.message
    relative_error = abs(result.objective - MASS_STAR) / MASS_STAR
    assert relative_error <= OBJECTIVE_RTOL, (
        f"{backend}: objective {result.objective:.9f} vs {MASS_STAR:.9f} "
        f"({relative_error:.2e} relative)"
    )

    (name,) = result.constraint_values
    assert abs(result.constraint_values[name]) <= ACTIVE_TOL
    assert result.active_set == [name]
    # The design itself, not only the objective: a wrong point on the same mass
    # contour would pass the objective gate.
    assert result.x == pytest.approx(K_STAR, abs=1e-4)


@criterion("AC-OPT-002")
@pytest.mark.filterwarnings("ignore:delta_grad == 0.0:UserWarning")
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_opt_002_termination_report_is_consistent(backend):
    """The report describes the point it returned: KKT, mass, cost counters."""
    result = solve_reference(backend)

    assert result.objective == pytest.approx(total_mass(*result.x), rel=1e-12)
    assert result.variables == pytest.approx(dict(zip(["k1", "k2"], result.x)))
    # First-order optimality of the returned point, on the same scale as the
    # objective gradient (0.2 per variable here).
    assert result.stationarity <= 1e-6
    # One eigensolve per design point, counted where the evaluator can see it.
    assert 0 < result.n_modal_solves <= result.n_evaluations + len(result.history)


# ---------------------------------------------------------------------------
# AC-OPT-003 — box bounds never violated
# ---------------------------------------------------------------------------


@criterion("AC-OPT-003")
@pytest.mark.filterwarnings("ignore:delta_grad == 0.0:UserWarning")
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_opt_003_no_design_point_outside_the_box_reaches_the_model(backend):
    """Every point the model is asked about lies in the box within 1e-12."""
    model = RecordingModel()
    params = reference_parameters()
    bounds = {p.name: (p.lower, p.upper) for p in params}

    result = solve_reference(backend, model=model, params=params)

    assert model.points, "the run evaluated nothing"
    outside = [
        point
        for point in model.points
        for name, value in point.items()
        if not bounds[name][0] - BOUND_TOL <= value <= bounds[name][1] + BOUND_TOL
    ]
    assert not outside, f"{backend}: {len(outside)} evaluations outside the box"
    assert result.converged, result.message


@criterion("AC-OPT-003")
@pytest.mark.filterwarnings("ignore:delta_grad == 0.0:UserWarning")
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_opt_003_every_recorded_iterate_satisfies_the_bounds(backend):
    """The iterate history is the auditable record the criterion asks for."""
    result = solve_reference(backend)
    lower, upper = np.array([0.5, 0.5]), np.array([20.0, 20.0])

    assert len(result.history) >= 2, "history must cover the path, not the answer"
    assert [row.iteration for row in result.history] == list(range(len(result.history)))
    for row in result.history:
        assert row.in_bounds, f"iterate {row.iteration} left the box: {row.x}"
        assert np.all(row.x >= lower - BOUND_TOL)
        assert np.all(row.x <= upper + BOUND_TOL)
    assert result.history[0].x == pytest.approx([8.0, 8.0])
    assert result.history[-1].objective < result.history[0].objective


@criterion("AC-OPT-003")
@pytest.mark.filterwarnings("ignore:delta_grad == 0.0:UserWarning")
@pytest.mark.parametrize("backend", sorted(BACKENDS))
def test_ac_opt_003_bound_active_optimum_stops_on_the_bound(backend):
    """A bound tighter than the free optimum is respected, not overshot.

    Raising the lower bound of ``k2`` above its free optimum (4) moves the
    solution onto that bound, so the run has to work along the boundary rather
    than approach it from well inside — the case where off-by-round-off bound
    handling shows up.  The oracle is the smallest ``k1`` that still meets the
    floor at ``k2 = 5``, bracketed below the interior maximum of
    ``lambda_1(., 5)``.

    The two methods reach it differently, so the gate is the criterion's 1e-4
    on the objective rather than machine precision: SLSQP is an active-set
    method and lands on the bound exactly, while trust-constr is a barrier
    method and stops a barrier parameter inside it (about 2e-4 here).  What
    both must satisfy exactly is the direction of the error — neither may end
    up, or evaluate, below the bound.
    """
    floor = 5.0
    k1_star = brentq(
        lambda k1: fundamental_eigenvalue(k1, floor) - LAMBDA_TARGET,
        0.5,
        1.5 * floor,
        xtol=1e-15,
        rtol=8.9e-16,
    )
    model = RecordingModel()
    params = reference_parameters(start=(9.0, 9.0), lower=(0.5, floor))

    result = solve_reference(backend, model=model, params=params)

    assert result.converged, result.message
    assert result.objective == pytest.approx(
        total_mass(k1_star, floor), rel=OBJECTIVE_RTOL
    )
    assert result.x == pytest.approx([k1_star, floor], abs=1e-3)
    assert result.x[1] >= floor - BOUND_TOL
    assert min(point["k2"] for point in model.points) >= floor - BOUND_TOL
    assert all(row.in_bounds for row in result.history)
    # Optimality with a bound multiplier in play, not only with the constraint.
    assert result.stationarity <= 1e-6
