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
| stationarity | trust-constr `optimality`; for SLSQP, which reports none, a projected KKT residual computed here |

**Stationarity.** SLSQP exposes no optimality measure, and its raw gradient norm
is not one: at a constrained optimum `∇f` is balanced by the active constraint
gradients, not zero. So the backend reconstructs the first-order residual
`∇f + Σ λ_k ∇g_k`, recovering the multipliers of the active set by *non-negative*
least squares (`λ_k ≥ 0` is part of KKT — an unsigned solve could report a
spuriously small residual), and projecting out components held at a bound where a
bound multiplier legitimately absorbs them.

**Hessians (trust-constr only).** trust-constr needs a Lagrangian Hessian and the
package supplies no second derivatives. Constraint curvature is neglected — the
usual SQP approximation, and a necessary one here: scipy's default is a
per-constraint BFGS, which degenerates when the jacobian is constant, and the
canonical sizing constraint (a mass budget) is exactly linear. On the 2-variable
reference problem the default exhausts `maxiter` where a zero constraint Hessian
converges in 17 iterations. Neglecting curvature costs step quality, not
correctness: the gradients that drive the KKT test are exact. The objective's
Hessian is still approximated by quasi-Newton unless the caller passes an exact
one as `options={"hess": …}` — worth doing for a minimum-mass objective, which is
linear.

**Status.** Implemented and gated. Measured on the reference problems of
`tests/acceptance/test_optimization.py` with SLSQP:

| Problem | Optimum | Objective rel. err | Active `|g|` | Eigensolves |
|---------|---------|--------------------|--------------|-------------|
| Sized oscillator, min mass s.t. `f_1 ≥ f_min` | `t* = λ m₀/(k − λμ)` | 3.3e-16 | 4.4e-16 | 8 |
| Payload placement, max `f_1` s.t. `m ≥ m_req` | even split `m_j = m_req/2` | 1.0e-12 | 2.0e-15 | 7 |

trust-constr reaches the same optima within the 1e-4 objective gate, but as an
interior-point method it stops a barrier width short of the boundary, so its
`|g|` settles around 1e-5 at default tolerances rather than at zero. AC-OPT-002
is therefore read from SLSQP, the MS-5.2 default.

## 8. Shared statement with updating

`problem_from_updater(updater)` re-expresses a calibration run as the same vector
problem: the objective is the updater's weighted least-squares cost
`f(x) = ½‖r(x)‖²` with the Gauss-Newton gradient `Jᵀr`, built from the updater's
own residual and jacobian machinery. This is the seam through which Round 2 can
drive updating with a generic bound-constrained backend instead of the built-in
Levenberg-Marquardt loop — and the reason calibration and design optimization do
not need two problem statements.

## 9. Staging

| Round | Scope | State |
|-------|-------|-------|
| 1 | Design space, lowering, both gradient routes, mode tracking, response/result contracts, backend seam | done |
| 2 | `ScipyBackend.solve` (GAP-12) and the AC-OPT-001..004 gates | done |
| 2 | Drive `ModelUpdater` through the shared statement of section 8 | open |
| 3 | Geometric `dK/da` for shape variables; DOE sampling and response-surface surrogates for expensive objectives | open |

Still open in the module, beyond the staging above: no equality constraints
(`Constraint` is `>=`/`<=` only), no multistart despite the `seed` parameter, and
`translational_mass` treats every DOF as translational until
`AssembledSystem.dof_types` is threaded through, so `TotalMass` is exact for
chain and bar models but would count rotational rows on a continuum model.
