# OpenFEMLab — Optimization Hook (M5)

**Spec:** `docs/MODULE_SPEC.md` §5 (MS-5) · **Gates:** `docs/ACCEPTANCE_CRITERIA.md` §6
(AC-OPT-001..004) · **Package:** `openfemlab.optimization`

This document is the design and staging reference for gradient-based structural
sizing optimization. It records how a sizing statement is lowered onto a plain
bound-constrained NLP, which gradient routes exist and when each is taken, and
the exact mapping a backend must implement (§7).

---

## 1. Position in the platform

Optimization is an L3 consumer: it sits on the same layer as updating and
imports from it rather than duplicating it.

```
L2  solver.modal.ModalSolver        eigen solves           (M1)
L3  updating.parameters             design variables       (M3)
    updating.scaling_model          parametric model K(θ), M(θ)
    updating.sensitivity            Fox-Kapoor dλ/dp, MAC mode tracking (M2/M3)
        │
        └── optimization            THIS module            (M5)
```

Three reuse decisions follow from that, and they are the reason the module is
small:

- **Design variables are updating parameters.** A model calibrated with
  `ModelUpdater` is optimized without re-declaring anything: the same
  `UpdatableParameter` objects (bounds, log scaling, FD steps, element targets)
  define the sizing design space.
- **Gradients come from the M3 kernel.** Frequency gradients are the Fox-Kapoor
  eigenvalue sensitivities converted by `∂f_i/∂p = ∂λ_i/∂p / (8π² f_i)`; the mass
  gradient is the translational diagonal of `∂M/∂p`.
- **Mode identity comes from the M2 kernel.** "Mode `i`" is tracked by MAC
  against the previous design point, so a constraint stays attached to a physical
  branch across a crossing (AC-OPT-004).

## 2. Two API levels

The package deliberately has a *structural* layer and a *vector* layer, split so
that no FE concept reaches the optimizer.

| Layer | Speaks in | Types |
|-------|-----------|-------|
| Structural | models, parameters, responses | `DesignSpace`, `ShapeVariable`, `Objective`, `Constraint`, `TotalMass`, `NaturalFrequency`, `minimize_sizing`, `compile_sizing_problem` |
| Vector | arrays and callables | `OptimizationProblem`, `VectorConstraint`, `OptimizationResult`, `OptimizationIterate`, `OptimizerBackend`, `ScipyBackend` |

Everything below the vector layer is swappable, which is the extension point
`docs/ARCHITECTURE.md` §11 reserves for external optimizers.

Module layout:

| File | Owns |
|------|------|
| `variables.py` | `DesignSpace`, `ShapeVariable` (sizing reuses `UpdatableParameter`) |
| `responses.py` | `DesignState`, `Response`, `TotalMass`, `NaturalFrequency`, `Objective`, `Constraint`, `frequency_floor` |
| `gradients.py` | `MatrixDerivativeProvider`, Fox-Kapoor adapter, FD fallback, `check_gradient` |
| `problem.py` | `OptimizationProblem`, `VectorConstraint`, `OptimizationIterate`, `OptimizationResult` |
| `backends.py` | `OptimizerBackend` protocol, `ScipyBackend` (stub), registry |
| `sizing.py` | `ModalDesignEvaluator`, `compile_sizing_problem`, `minimize_sizing`, `problem_from_updater` |

Errors raise `OptimizationError` (`openfemlab.exceptions`); the top level
re-exports `OptimizationProblem`, `OptimizationResult` and `minimize_sizing`.
Contract tests: `tests/test_optimization.py` (16 tests pin the design space,
both gradient routes, mode tracking, the bound contract, the backend registry,
the stub, and the updater interop).

## 3. Problem statement

The vector layer is the standardized bound-constrained NLP of MS-5.1:

```
min_x  f(x)
s.t.   g_k(x) ≤ 0        k = 1..m
       lo ≤ x ≤ hi
```

Constraints are always *standardized* to `g ≤ 0` and, by default, normalized so
they are dimensionless: `f_1 ≥ f_min` becomes `g = 1 − f_1/f_min ≤ 0`. That keeps
constraint scales comparable across physical quantities, which matters because
SLSQP shares one tolerance across the whole constraint vector.

Bounds are a *hard* contract, not a preference: `OptimizationProblem.clip` and
`DesignSpace.clip` project onto the box, and `feasible()` is the predicate
AC-OPT-003 audits over `result.history`.

## 4. Design space

`x = [sizing design values…, shape amplitudes…]`.

The sizing block uses the *design-space* mapping of `ParameterSet`: identity for
linear parameters, `log(value)` for logarithmic ones, so a positive property can
never go negative along a step. `DesignSpace.chain(x)` returns the diagonal
`dp/dx` (`p` for log-scaled variables, 1 otherwise); multiplying a physical-space
gradient row by it gives the design-space gradient. Fixed parameters are excluded
from the vector but still handed to the model at their held values.

Shape variables are amplitudes of node-coordinate perturbation fields:

```
X(a) = X_0 + Σ_j a_j V_j          V_j : (n_nodes, 3) design velocity field
```

The linear morph and its geometry gradient `dX/da_j = V_j` are exact and
implemented. Regenerating element matrices from morphed coordinates — and with
them the geometric `dK/da` chain — is a Round 3 item, so shape variables
currently route their response gradients through finite differences.

## 5. Lowering pipeline

```
ParametricModel + Parameters
    │  ModalDesignEvaluator      one modal solve per design point,
    │                            MAC mode tracking, analytic df/dp
    ▼                            when matrix derivatives exist
Objective / Constraints          physical-space values and gradients
    │  compile_sizing_problem    chain rule to design space,
    ▼                            tracked-FD fallback otherwise
OptimizationProblem              plain bound-constrained NLP
    │  problem.solve(backend)
    ▼
OptimizationResult
```

`ModalDesignEvaluator` is where the cost is controlled. It caches one
`DesignState` per design point, so the objective and every constraint at the same
`x` share a single eigensolve, and it counts real eigensolves in
`n_modal_solves` — the number that belongs in the termination report, since it is
the dominant expense.

The model contract is the one `ModelUpdater` already uses: a callable mapping
`{parameter name: value}` to anything `as_modal_data` understands. A model that
*additionally* exposes `eigen` / `assemble` / `derivatives` / `parameter_names`
(the `MatrixDerivativeProvider` shape, which `ScalingModel` satisfies) unlocks the
analytic route and the total-mass objective.

## 6. Gradient routes

| Route | Condition | Cost per gradient |
|-------|-----------|-------------------|
| Analytic Fox-Kapoor | model is a `MatrixDerivativeProvider` **and** every design variable is one of its parameters | 0 extra eigensolves |
| Tracked central FD | otherwise | `2n` eigensolves, mode-tracked per point |

The finite-difference fallback is tracked, not naive: every perturbed point goes
through the same MAC re-labeling as the base point, so a mode crossing inside the
FD stencil cannot silently corrupt a row of the jacobian.

`check_gradient(fun, jac, x)` is the AC-OPT-001 harness. It compares against
central differences and reports `max_relative_error` scaled by the gradient
magnitude, so zero components are compared absolutely rather than dividing by
zero.

Measured on the 2-DOF reference chain (two stiffness groups, one mass group), the
analytic route agrees with central differences to **1.4e-10** for the mass
objective and **2.1e-10** for the normalized frequency constraint — four orders
inside the 1e-6 gate — at **7** eigensolves for both checks together.

## 7. Backend mapping (`ScipyBackend`)

A backend consumes a fully lowered `OptimizationProblem` and returns an
`OptimizationResult`. Three rules bind every implementation:

1. **Bounds are hard** (AC-OPT-003). Never evaluate outside the box; record every
   accepted iterate in `result.history` so the audit is checkable after the fact.
2. **No internal differentiation** (MS-5.2). The problem carries gradient
   callbacks; a backend must pass them through and must not request its own
   numerical jacobians, because each hidden evaluation is a full modal solve.
3. **Standardized constraints.** The problem states `g(x) ≤ 0`; SLSQP's
   convention is `g(x) ≥ 0`, so the adapter negates both the function and its
   jacobian.

The `scipy.optimize.minimize` lowering:

| Problem member | scipy |
|----------------|-------|
| `bounds` | `Bounds(lo, hi)`, plus a clip in the objective wrapper so round-off cannot escape the box (tolerance 1e-12) |
| `VectorConstraint` | `{"type": "ineq", "fun": -g, "jac": -dg}` (SLSQP) or `NonlinearConstraint(g, -inf, 0)` (trust-constr) |
| `gradient` | `jac=`, always set — scipy's 2-point fallback is explicitly disabled |
| iterate callback | one `OptimizationIterate` row plus the evaluator's modal-solve counter |
| `result.success` / `message` | `OptimizationResult.converged` / `message` |
| stationarity | `kkt_residual` (see below), the same measure for both methods |

`OptimizationResult.converged` additionally requires the solution to be
feasible, so a run that terminates "successfully" against an unreachable
constraint is reported as a failure rather than as an optimum.

**Stationarity.** SLSQP and trust-constr report incomparable diagnostics
(a final gradient norm versus `optimality`), so the termination report uses one
method-independent measure. `kkt_residual` solves the non-negative
least-squares problem for the multipliers of the active inequalities and active
bounds,

```
min_{λ, μ ≥ 0}  ‖ df/dx + Σ_k λ_k dg_k/dx + μ_bounds ‖
```

and returns the residual relative to the gradient scale. Zero means the
first-order KKT conditions hold at the solution.

**Status.** Wired and gated. AC-OPT-002 is verified against the closed-form
optimum of §8 (objective within 1e-4 relative, active `|g| ≤ 1e-6`), AC-OPT-003
over both the recorded iterates and the points the model is actually asked to
evaluate. The remaining stub-free gap in the package is the geometric `dK/da`
for shape variables (§4).

## 8. Reference problem and its oracle

The reference class is a grounded spring-mass chain of `n` masses in which
design variable `t_j` scales both the stiffness **and** the structural mass of
link `j`, while every node also carries a fixed non-structural mass `m_0`. The
`m_0` matters: without it a uniform scaling of `K` and `M` leaves every
frequency unchanged, mass minimization and the frequency floor stop fighting,
and the problem is degenerate. With it the optimum sits on the constraint
boundary, which is what AC-OPT-002 wants to see.

The uniform variant — one variable scaling every link — has a closed-form
optimum. With `K(t) = t K_1` and `M(t) = (t m_s + m_0) I` the eigenvalues are
`λ_i(t) = t μ_i / (t m_s + m_0)`, so `f_1 ≥ f_min` binds exactly at

```
t* = ω² m_0 / (μ_1 − ω² m_s),        ω = 2π f_min
```

where `μ_1` is the smallest eigenvalue of `K_1`.

| Criterion | Verified by |
|---|---|
| AC-OPT-001 | `check_gradient` on the compiled objective and constraint at three seeded feasible points |
| AC-OPT-002 | the uniform chain solved to `t*` within 1e-4 relative with `\|g\| ≤ 1e-6`, plus a random-probe check that no feasible sample beats the three-variable optimum |
| AC-OPT-003 | every recorded iterate *and* every point the model is asked to evaluate inside the box to 1e-12 |
| AC-OPT-004 | two uncoupled oscillators driven through a crossing: the tracked frequency follows its branch and consecutive tracked shapes keep MAC ≥ 0.9 |

`tests/acceptance/test_optimization.py` holds the gates;
`tests/test_optimization.py` holds the behaviour they rest on.

## 9. Shared statement with updating

`problem_from_updater(updater)` re-expresses a calibration run as the same vector
problem: the objective is the updater's weighted least-squares cost
`f(x) = ½‖r(x)‖²` with the Gauss-Newton gradient `Jᵀr`, built from the updater's
own residual and jacobian machinery. This is the seam through which a generic
bound-constrained backend can drive updating instead of the built-in
Levenberg-Marquardt loop — and the reason calibration and design optimization do
not need two problem statements.

## 10. Public API

```python
# spec MS-5.3 hook
minimize_sizing(model, params, objective, constraints=(), *,
                backend="slsqp", tol=1e-8, max_iter=100, seed=0)
    -> OptimizationResult

# lowering, exposed for tests and Round 2
compile_sizing_problem(model, params, objective, constraints=(), **options)
    -> (OptimizationProblem, ModalDesignEvaluator)

# updating interop
problem_from_updater(updater: ModelUpdater) -> OptimizationProblem

# verification (AC-OPT-001)
check_gradient(fun, jac, x, *, steps=1e-6, tolerance=1e-6) -> GradientCheck
```

## 11. Staging

| Round | Scope |
|-------|-------|
| 1 | Design space, lowering, both gradient routes, mode tracking, response/result contracts, backend seam |
| 2 | `ScipyBackend.solve` and the KKT termination report (GAP-12); AC-OPT-001..004 gates — **done** |
| 3 | Element-level assembled `∂K/∂p`/`∂M/∂p` for the native `Model` stack (today only affine `ScalingModel`-style models take the analytic route); `dof_types`-aware translational mass for continuum models; geometric `dK/da` for shape variables (FE regeneration from morphed coordinates); driving `ModelUpdater` through the shared statement; DOE sampling and response-surface surrogates; multistart driver over `seed` |

## 12. Acceptance criteria mapping

| Criterion | Mechanism | Status |
|-----------|-----------|--------|
| AC-OPT-001 (gradients vs FD, 1e-6) | `check_gradient` + analytic routes | verified at 3 seeded points; worst 1.03e-09 |
| AC-OPT-002 (reference optimum) | `ScipyBackend.solve` against the §8 oracle | verified; `t*` recovered to 9.2e-11 relative |
| AC-OPT-003 (bounds never violated) | iterate history plus a spy on the compiled callbacks | verified over iterates *and* evaluations |
| AC-OPT-004 (mode tracking) | evaluator reference tracking via `track_modes` | verified across a crossing at MAC ≥ 0.9 |
