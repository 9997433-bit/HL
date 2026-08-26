# Module Specification — FEMtools-like CAE Platform

**Document ID:** MS-R1-F2 · **Round:** 1 · **Author:** R1-F2 (module spec & acceptance criteria)
**Status:** Draft for Round-1 implementation · **Companion doc:** `docs/ACCEPTANCE_CRITERIA.md`

This document specifies the five core modules of the platform. Section anchors
(`MS-<module>.<section>`) are referenced by acceptance criteria IDs
(`AC-<MODULE>-NNN`) in the companion document and by the machine-readable
registry in `tests/acceptance/test_criteria_registry.py`.

Package naming follows the approved R1-F1 architecture document
(`docs/ARCHITECTURE.md`): top-level package `openfemlab`. Module boundaries
and public APIs specified here are binding.

---

## 0. Conventions and Cross-Cutting Requirements (MS-0)

### MS-0.1 Notation

| Symbol | Meaning |
|--------|---------|
| `K` | Stiffness matrix, `n×n`, real symmetric, PSD (SPD after constraints) |
| `M` | Mass matrix, `n×n`, real symmetric, SPD (consistent) or PSD (lumped) |
| `λ_i = ω_i²` | i-th eigenvalue; `ω_i` circular frequency [rad/s]; `f_i = ω_i/(2π)` [Hz] |
| `φ_i` / `Φ` | i-th mode shape / mode matrix (columns = modes) |
| `p ∈ R^m` | Updating/design parameter vector |
| `S` | Sensitivity (Jacobian) matrix `∂z/∂p` of outputs `z` w.r.t. parameters |
| Subscript `a` / `e` | analysis (FE) / experimental (test) quantity |

### MS-0.2 Units and data model

- SI units internally (m, kg, s, Pa, Hz for reported frequencies). Unit
  conversion happens only at I/O boundaries.
- All matrices accepted as dense `numpy.ndarray` or sparse
  `scipy.sparse` (CSR/CSC). Modules must not densify sparse inputs above
  `n = 2000` except where explicitly specified (dense fallback path).
- DOFs are identified by `(node_id, dof_type)` pairs; `dof_type ∈ {UX, UY, UZ,
  RX, RY, RZ}`. A `DofMap` object owns the ordering and is passed alongside
  matrices; mode shape rows are always interpreted through a `DofMap`.
- Every solver-facing function is deterministic given a seed: any randomized
  starting block (LOBPCG, Lanczos starting vector) takes an explicit
  `rng: numpy.random.Generator` or `seed: int` argument.

### MS-0.3 Error handling and diagnostics

- Numerical failures (non-convergence, indefinite matrix where SPD required,
  singular factorization) raise typed exceptions
  (`SolverConvergenceError`, `MatrixDefinitenessError`, ...) carrying
  diagnostics (iteration count, residual history), never bare asserts.
- Every result object carries a `diagnostics` dict: residual norms, iteration
  counts, wall time, backend used, tolerances in effect.

---

## 1. Module M1 — Modal Analysis (`openfemlab.modal`) (MS-1)

### MS-1.1 Problem statement

Solve the symmetric generalized eigenvalue problem

```
K φ_i = λ_i M φ_i ,   λ_i = ω_i² ,   f_i = ω_i / (2π)
```

for the `k` lowest eigenpairs (`k` requested by the caller). Requirements:

- `K` symmetric PSD (semidefinite when rigid-body modes are present),
  `M` symmetric SPD or PSD (lumped mass with massless DOFs allowed only if
  those DOFs are constrained or condensed before the solve).
- Symmetry is validated (`‖A − Aᵀ‖_max ≤ 1e-10 · ‖A‖_max`) and enforced by
  symmetrization `A ← (A + Aᵀ)/2` before factorization.
- Eigenvalues returned sorted ascending; negative eigenvalues above a noise
  floor (`λ < −ε_rigid · λ_max`) raise `MatrixDefinitenessError`.

### MS-1.2 Solver backends

Three backends behind one interface; automatic selection by problem size
unless the caller pins a backend.

| Backend | Method | When |
|---------|--------|------|
| `dense` | `scipy.linalg.eigh(K, M)` (LAPACK `sygvd`) | `n ≤ 2000` or reference/validation runs |
| `lanczos` | Shift-invert Lanczos, `scipy.sparse.linalg.eigsh(K, k, M, sigma=σ, mode='normal')` with sparse LDLᵀ/LU factorization of `K − σM` | default sparse path, `n > 2000` |
| `lobpcg` | `scipy.sparse.linalg.lobpcg` with preconditioner (Jacobi default; AMG via `pyamg` when available) | very large `n`, matrix-free operators, or when factorization is too expensive |

Backend contract:

- **Shift strategy (`lanczos`).** Default shift `σ = −0.01 · tr(K)/tr(M)`
  (small negative) so that `K − σM` is definite even with rigid-body modes.
  User-supplied `sigma` allowed for interior eigenvalues (frequency window
  requests `f ∈ [f_lo, f_hi]`).
- **Rigid-body modes.** Eigenvalues with `λ_i ≤ ε_rigid · max(λ_k, tr(K)/tr(M)·1e-9)`
  are classified rigid; reported as `f = 0` with `is_rigid=True` flags. The
  count of rigid modes must equal the nullity of `K` on the free structure
  (up to 6 per unconnected component).
- **Convergence.** Each accepted eigenpair must satisfy the relative residual

  ```
  ‖K φ_i − λ_i M φ_i‖₂ / ‖K φ_i‖₂ ≤ tol      (default tol = 1e-8)
  ```

  For rigid modes the denominator is replaced by `λ_ref ‖M φ_i‖₂` with
  `λ_ref = tr(K)/tr(M)`. Non-converged pairs raise `SolverConvergenceError`
  with the residual history attached.
- **Missed-mode guard.** For `lanczos`/`lobpcg`, an optional Sylvester
  inertia check (LDLᵀ of `K − σ̄M` at `σ̄` just above the highest returned
  eigenvalue) verifies the eigenvalue count in `(σ, σ̄)`; discrepancy raises
  `MissedModesWarning` (P1: escalate to error under `strict=True`).

### MS-1.3 Mode normalization and sign convention

- **Primary normalization: mass-normalized** — `Φᵀ M Φ = I`, hence
  `Φᵀ K Φ = diag(λ)`. All downstream modules (correlation weighting,
  sensitivities, updating) assume mass-normalized analysis modes.
- Secondary normalizations available as views (never mutating stored modes):
  `unit-max` (largest |component| = 1) and `unit-length` (‖φ‖₂ = 1).
- **Sign convention:** the component of largest absolute value is made
  positive; ties broken by lowest DOF index. This makes dense/iterative
  backends and repeated runs sign-stable (required by AC-MODAL-005).
- Orthogonality guarantee: `‖Φᵀ M Φ − I‖_max ≤ 1e-8` on return
  (re-orthogonalization applied if the backend's raw output violates it).

### MS-1.4 Derived modal quantities

For excitation direction matrix `R` (`n×6` rigid-body influence, built from
geometry):

- Participation factors: `Γ = Φᵀ M R` (rows = modes, columns = directions).
- Effective modal mass: `m_eff,ij = Γ_ij²` (mass-normalized modes); the sum
  over the complete modal basis must equal the total mass/inertia in each
  direction (AC-MODAL-007).
- Modal stiffness `k_i = λ_i`, modal mass `m_i = 1` (mass-normalized).

### MS-1.5 Public API

```python
@dataclass(frozen=True)
class ModalResult:
    frequencies_hz: np.ndarray        # (k,)
    eigenvalues: np.ndarray           # (k,) λ = ω²
    modes: np.ndarray                 # (n, k), mass-normalized, sign-fixed
    dof_map: DofMap
    is_rigid: np.ndarray              # (k,) bool
    participation: np.ndarray | None  # (k, 6)
    effective_mass: np.ndarray | None # (k, 6)
    diagnostics: dict                 # backend, residuals, iterations, time

def solve_modes(K, M, k: int, *, backend: str = "auto",
                sigma: float | None = None,
                freq_window: tuple[float, float] | None = None,
                tol: float = 1e-8, seed: int = 0,
                dof_map: DofMap | None = None) -> ModalResult
```

---

## 2. Module M2 — Correlation (`openfemlab.correlation`) (MS-2)

Quantifies agreement between an analysis mode set `(f_a, Φ_a)` and a test mode
set `(f_e, Φ_e)`, generally observed on a reduced sensor DOF set.

### MS-2.1 DOF mapping (test–analysis model)

- `SensorMap`: ordered mapping from test channels to analysis DOFs
  (node/dof pairs, with per-channel orientation sign). Produces a selection
  operator `T ∈ R^{s×n}` (s = sensor count).
- **Reduction** (default): compare `T Φ_a` against `Φ_e` directly.
- **Expansion** (optional, P1): SEREP expansion of test shapes to full space,
  `Φ_e^full = Φ_a (T Φ_a)⁺ Φ_e`, and Guyan static reduction of `K, M` to
  sensor DOFs for mass-weighted metrics on the reduced space. Consistency
  requirement: for noise-free synthetic "test" data extracted from the model
  itself, reduced-space and full-space pairing must agree (AC-CORR-006).

### MS-2.2 MAC — Modal Assurance Criterion

```
MAC(i, j) = |φ_a,iᴴ φ_e,j|² / ( (φ_a,iᴴ φ_a,i) (φ_e,jᴴ φ_e,j) )
```

- Defined for real or complex shapes (Hermitian transpose); output real in
  `[0, 1]` within floating-point roundoff (clipped to `[0, 1]`).
- **Invariance requirement:** MAC is invariant to any nonzero real scaling
  and sign flip of either shape (AC-CORR-002).
- **Weighted MAC** (mass- or stiffness-weighted, on matched DOF spaces):

  ```
  MAC_W(i, j) = |φ_a,iᵀ W φ_e,j|² / ( (φ_a,iᵀ W φ_a,i) (φ_e,jᵀ W φ_e,j) )
  ```

  with `W = M` (or Guyan-reduced `M_ss` on sensor space). For a
  mass-normalized set correlated with itself, `MAC_M` must be the identity
  matrix to solver precision (AC-CORR-001).
- Related matrices provided by the same kernel: auto-MAC (`Φ_a` vs `Φ_a`,
  spatial-independence check for sensor placement) and pseudo-orthogonality
  `POC = Φ_eᵀ M_ss Φ_a` (P1).

### MS-2.3 Mode pairing

- Cost matrix `C_ij = 1 − MAC(i, j)` optionally augmented with a frequency
  penalty `+ β · |f_a,i − f_e,j| / f_e,j` (default `β = 0.1`).
- **Algorithm:** Hungarian assignment (`scipy.optimize.linear_sum_assignment`)
  on the rectangular cost matrix; greedy fallback available for diagnostics.
- Pairs with `MAC < mac_min` (default **0.7**) are rejected → reported as
  unpaired analysis/test modes. Pairing must recover ground-truth
  permutations exactly and tolerate missing modes on either side
  (AC-CORR-003).
- Output: `ModePairing` with `pairs: list[(i_a, j_e, mac, dfreq_pct)]`,
  `unpaired_analysis`, `unpaired_test`.

### MS-2.4 Frequency error and scalar metrics

- Per-pair relative frequency error (signed, analysis relative to test):

  ```
  Δf_ij [%] = 100 · (f_a,i − f_e,j) / f_e,j
  ```

  Positive means the model is stiffer/lighter than the test article
  (AC-CORR-005 pins this convention).
- Aggregates over paired modes: mean(|Δf|), max(|Δf|), mean MAC, min MAC —
  these are the quantities gated by acceptance criteria and by the
  updating convergence monitor.

### MS-2.5 COMAC — Coordinate MAC

For paired mode sets (after MS-2.3 pairing, shapes scaled by the Modal Scale
Factor so pairs are consistently signed), per DOF `d` over `P` pairs:

```
COMAC(d) = ( Σ_{i=1..P} |φ_a,i(d) · φ_e,i(d)| )²
           / ( Σ_i φ_a,i(d)² · Σ_i φ_e,i(d)² )
```

- Range `[0, 1]`; low values localize DOFs responsible for poor correlation
  (sensor faults or local model errors). Requirement: a synthetic
  perturbation injected at one sensor DOF must produce the minimum COMAC at
  that DOF (AC-CORR-004). Enhanced CoMAC (eCOMAC) is a P2 extension.

### MS-2.6 Public API

```python
def mac(phi_a, phi_e, *, weight=None) -> np.ndarray            # (ka, ke)
def pair_modes(freqs_a, phi_a, freqs_e, phi_e, *,
               weight=None, mac_min=0.7, freq_penalty=0.1) -> ModePairing
def comac(phi_a, phi_e, pairing) -> np.ndarray                 # (s,)
def correlate(modal_a: ModalResult, test: TestModeSet,
              sensor_map: SensorMap, **kw) -> CorrelationReport
def frf_correlation(reference, comparison, *, excitation_dof=None,
                    frequencies=None, channels=None,
                    with_fdac=True) -> FRFCorrelation
```

`CorrelationReport` is a serializable (JSON) artifact containing the MAC
matrix, pairing table, frequency-error table, COMAC vector, the optional FRF
block, and the settings used — it is the exchange currency between M2, M3 and
M4. Its `schema_version` is **1.1**: 1.1 added the `frf` key, which is `null`
whenever no FRF comparison was run, so the key set is independent of the
analyses performed. `is_correlated(..., frac_threshold=...)` adds the MS-7.4
frequency-domain gate to the MS-4.2 modal ones and refuses to run without a
block.

---

## 3. Module M3 — Model Updating (`openfemlab.updating`) (MS-3)

Iterative correction of model parameters `p` so analysis outputs match test
targets.

### MS-3.1 Parameterization

- `Parameter`: name, physical meaning (E, ρ, thickness `t`, section area/I,
  lumped spring stiffness, lumped mass), the element/property set it scales,
  bounds `[p_lo, p_hi]`, prior `(p_0, σ_p)`.
- Internally, updating always works on **relative parameters**
  `θ_j = p_j / p_j,0` (dimensionless, start at 1) so `S` is well scaled.
- The model interface must expose parameter-differentiated system matrices:
  `∂K/∂p_j`, `∂M/∂p_j` — analytic when matrix assembly is affine in `p`
  (the common `K(p) = K_0 + Σ θ_j K_j` substructure form), otherwise
  semi-analytic central finite difference on assembled matrices
  (step `h = 1e-6 · p_j,0`).

### MS-3.2 Residuals (targets)

Stacked weighted residual vector `r(p)`; supported blocks:

1. **Eigenvalue residuals** (default, dimensionless):
   `r_λ,i = (λ_e,i − λ_a,i(p)) / λ_e,i` for each paired mode `i`.
2. **Mode-shape residuals** (optional): either component residuals
   `r_φ = vec(T φ_a,i − φ_e,i)` after MSF scaling, or scalar
   `r_MAC,i = 1 − MAC_ii`.
3. FRF residuals: out of scope Round 1 (interface reserved).

Re-pairing (MS-2.3) is executed every iteration — mode switching during
updating must not corrupt the residual ordering.

### MS-3.3 Sensitivities

- **Eigenvalue sensitivity** (mass-normalized `φ_i`, simple eigenvalues):

  ```
  ∂λ_i/∂p_j = φ_iᵀ ( ∂K/∂p_j − λ_i ∂M/∂p_j ) φ_i
  ```

  Validated against central finite differences to relative error ≤ 1e-6
  (AC-UPD-001).
- **Mode-shape sensitivity** — Fox–Kapoor modal superposition:

  ```
  ∂φ_i/∂p_j = Σ_{r≠i}  [ φ_rᵀ ( ∂K/∂p_j − λ_i ∂M/∂p_j ) φ_i / (λ_i − λ_r) ] φ_r
              − ½ ( φ_iᵀ ∂M/∂p_j φ_i ) φ_i
  ```

  Truncated basis allowed for large models (document truncation error);
  Nelson's method (exact with one factorization per mode) is the P1 upgrade
  path. Validated per AC-UPD-002.
- Degenerate/close eigenvalues (`|λ_i − λ_r| < 1e-6 · λ_i`): shape
  sensitivities for the cluster are flagged unreliable and excluded from `S`
  (eigenvalue sensitivities remain valid for the cluster sum only —
  Round 1 policy: warn and drop the affected shape residuals).

### MS-3.4 Deterministic updating — regularized weighted Gauss–Newton

Minimize `J(p) = r(p)ᵀ W r(p)` with diagonal weighting `W` (default:
`1/σ_i²` from measurement confidence; eigenvalue residuals already relative).
Iteration:

```
Δθ = ( Sᵀ W S + λ_reg Lᵀ L )⁻¹ Sᵀ W r        (Tikhonov, L = I default)
θ ← clip(θ + α Δθ, θ_lo, θ_hi)
```

- `λ_reg`: fixed user value, or Levenberg–Marquardt adaptation (increase ×10
  on rejected step, decrease ÷3 on accepted step). L-curve selection is P2.
- Line search `α ∈ {1, ½, ¼, ⅛}` accepting the first step that decreases `J`;
  a fully rejected step triggers LM damping increase.
- **Convergence:** stop when `‖Δθ‖_∞ < 1e-4` **or** `J` relative decrease
  `< 1e-6` over 2 iterations **or** correlation gates met
  (`max|Δf| ≤ target`, `min MAC ≥ target`). Hard cap `max_iter` (default 20).
  Divergence guard: `J` increasing for 3 consecutive accepted steps aborts
  with `UpdatingDivergenceError`.
- Robustness requirement: with more parameters than residuals or collinear
  parameters, iterates must remain bounded within parameter bounds and `J`
  non-increasing over accepted steps (AC-UPD-005).

### MS-3.5 Bayesian updating (MAP with Gaussian prior)

Objective:

```
J(p) = (z_e − h(p))ᵀ C_ε⁻¹ (z_e − h(p)) + (p − p_0)ᵀ C_p⁻¹ (p − p_0)
```

Iterative MAP step (linearized):

```
Δθ = ( Sᵀ C_ε⁻¹ S + C_p⁻¹ )⁻¹ [ Sᵀ C_ε⁻¹ r − C_p⁻¹ (θ − θ_0) ]
```

- Posterior covariance estimate at convergence:
  `C_post ≈ (Sᵀ C_ε⁻¹ S + C_p⁻¹)⁻¹`, reported per parameter (σ_post).
- Limit consistency: as `C_p⁻¹ → 0` the step must equal the unregularized
  GN step (AC-UPD-006a); a tight prior must contract the posterior
  (`σ_post ≤ σ_prior` componentwise, AC-UPD-006b).
- Sampling-based posterior (MCMC/TMCMC) is out of scope Round 1; the MAP
  API is designed so a sampler can reuse `h(p)`, `C_ε`, `C_p`.

### MS-3.6 Parameter selection

Pre-updating diagnosis on the initial sensitivity matrix `S_0` (columns
scaled by `θ` — relative sensitivities):

- Rank/collinearity: pairwise column cosine `> 0.99` or subset condition
  number `κ(S_sel) > 1e6` flags redundancy; greedy subset selection keeps the
  most observable independent columns (QR with column pivoting).
- Low-sensitivity rejection: `‖S_·j‖ < 1e-3 · max_j ‖S_·j‖` → parameter
  frozen with a report entry (never silently).
- Requirement AC-UPD-007: a deliberately duplicated parameter must be
  detected and one of the pair frozen, with updating still converging.

### MS-3.7 Public API

```python
def update_model(model: ParametricModel, test: TestModeSet,
                 params: list[Parameter], *,
                 method: str = "gauss_newton",     # or "bayesian"
                 residuals=("eigenvalue", "mac"),
                 weights=None, regularization="lm",
                 max_iter: int = 20, seed: int = 0) -> UpdatingResult
```

`UpdatingResult`: parameter history, residual history, per-iteration
`CorrelationReport`s, final `C_post` (Bayesian), convergence flag + reason.

---

## 4. Module M4 — Simulation Correction Workflow (`openfemlab.workflow`) (MS-4)

End-to-end orchestration: **baseline FEA → correlate → update → re-analyze →
validate**. This is the productized loop a user runs; M1–M3 are its engines.

### MS-4.1 Pipeline stages (state machine)

| Stage | Action | Gate to proceed |
|-------|--------|-----------------|
| S1 `BASELINE` | Solve baseline modes (M1) on nominal `p_0` | solve converged; requested modes found |
| S2 `PAIRING` | Sensor mapping + initial pairing (M2) | ≥ `min_pairs` paired modes (default 3) with MAC ≥ 0.5 |
| S3 `DIAGNOSIS` | Correlation report, COMAC, parameter selection (MS-3.6) | ≥ 1 selected parameter |
| S4 `UPDATING` | Run M3 loop (re-solving M1 and re-pairing each iteration) | converged without `UpdatingDivergenceError` |
| S5 `REANALYSIS` | Full modal re-solve on updated `p*`, fresh correlation | — |
| S6 `VALIDATION` | Evaluate acceptance gates incl. held-out targets | gates below |

- Stage transitions, inputs, and outputs are logged; a failed gate stops the
  pipeline with stage + reason (machine-readable), never a partial silent
  result.
- **Held-out validation:** the caller may reserve modes (e.g., highest paired
  mode) or channels that are excluded from S4 residuals; S6 checks the
  updated model against them to detect overfitting (AC-WORK-003).

### MS-4.2 Default validation gates (S6)

- All paired modes: `MAC ≥ 0.95` (weighted MAC where mass is available).
- Frequency: `|Δf| ≤ 1%` per paired mode (configurable; 2% for noisy data).
- Parameters within bounds and `|θ* − 1|` reported against plausibility
  limits (warn > 50% change).
- Held-out targets: MAC ≥ 0.9 and `|Δf|` improved w.r.t. baseline.

### MS-4.3 Artifacts and reproducibility

- Single JSON report (`CorrectionReport`, schema-versioned
  `schema_version: "1.0"`): baseline correlation, iteration history, final
  correlation, parameter table (initial/final/bounds/σ_post), gate results,
  environment (package versions, seed), wall-time per stage.
- Re-running the pipeline with identical inputs and seed must reproduce all
  reported numbers to 1e-12 relative (AC-WORK-002).

### MS-4.4 Public API

```python
def run_correction(model, test, sensor_map, params, *,
                   gates: ValidationGates = ValidationGates(),
                   holdout: HoldoutSpec | None = None,
                   seed: int = 0) -> CorrectionReport
```

---

## 5. Module M5 — Optimization Hook (`openfemlab.optimization`) (MS-5)

Gradient-based **sizing optimization** reusing M1 solves and M3 sensitivities.
Round 1 delivers the hook + one reference problem class; topology/shape
optimization out of scope.

### MS-5.1 Problem class

```
min_p  f(p)          e.g. total mass  m(p)
s.t.   g_k(p) ≤ 0    e.g. f_1(p) ≥ f_min  →  g = 1 − f_1(p)/f_min ≤ 0
       p_lo ≤ p ≤ p_hi
```

- Design variables: same `Parameter` abstraction as M3 (sizing scalars:
  thickness, area, stiffness/mass scalars), relative internally.
- Objective/constraint gradients: mass gradient analytic from `∂M/∂p`
  (`∂m/∂p_j = Σ` of `∂M/∂p_j` translational diagonal, or per-property closed
  form); frequency-constraint gradients from the M3 eigenvalue sensitivity
  kernel via `∂f_i/∂p = ∂λ_i/∂p / (8π²f_i)`. All gradients must pass central
  finite-difference checks at 1e-6 relative tolerance (AC-OPT-001).

### MS-5.2 Optimizer backend

- Default `scipy.optimize.minimize(method="SLSQP")`; `trust-constr`
  selectable. Both consume the analytic gradient callbacks; numerical
  differentiation inside the optimizer is forbidden (each `f`/`g` evaluation
  triggers a modal solve — gradients must come from the sensitivity kernel).
- Mode-tracking during optimization: constraint on "mode `i`" tracks by MAC
  against the previous iterate's shape (reuses MS-2.3 machinery), preventing
  constraint switching when modes cross.
- Termination report: converged flag, KKT/stationarity measure as reported
  by the backend, iteration and modal-solve counts, active constraint set.
- Requirements: iterates never violate box bounds (AC-OPT-003); reference
  problem reaches the known optimum (AC-OPT-002).

### MS-5.3 Public API

```python
def minimize_sizing(model: ParametricModel, params: list[Parameter],
                    objective: Objective, constraints: list[Constraint], *,
                    backend: str = "slsqp", tol: float = 1e-8,
                    max_iter: int = 100, seed: int = 0) -> OptimizationResult
```

---

## 6. Inter-module contracts summary (MS-6)

```
M1 ModalResult ──▶ M2 correlate ──▶ CorrelationReport ─┐
      ▲                                                ▼
      └── re-solve ◀── M3 update_model ◀── residuals/S │
                            │                          │
M4 run_correction orchestrates S1..S6 ◀────────────────┘
M5 minimize_sizing reuses M1 solves + M3 sensitivity kernel + M2 mode tracking
M6 damped dynamics extends M1 modes to FRFs; FRAC/FDAC feed M2 correlation
```

- Mass-normalized, sign-fixed modes (MS-1.3) are the invariant every consumer
  relies on.
- `CorrelationReport` / `CorrectionReport` JSON artifacts are the stable
  external interfaces; schema changes require a `schema_version` bump.
- Acceptance criteria in `docs/ACCEPTANCE_CRITERIA.md` bind each requirement
  above to a measurable test; the ID registry is enforced by
  `tests/acceptance/test_criteria_registry.py`.

---

## 7. Module M6 — Damped Dynamics and Frequency Response (`openfemlab.solver.dynamics`) (MS-7)

Round-2 module (R2-T01) carrying the M1 undamped eigenproblem through to the
quantity a test campaign actually measures: the frequency response function.
Numbering note — MS-6 is the inter-module contracts section above, so the
sixth module takes the anchor prefix `MS-7`.

### MS-7.1 Damping models

Three descriptions, all reducible to the modal coefficient `2ζ_rω_r` the FRF
denominator consumes:

| Model | Physical form | Modal ratio |
|---|---|---|
| Rayleigh (proportional) | `C = αM + βK` | `ζ_r = α/(2ω_r) + βω_r/2` |
| Modal | none in general | `ζ_r` given per mode |
| Structural (hysteretic) | `K(1 + iη)` | `ζ_r = η/2` at every frequency |

- Rayleigh exposes `2ζ_rω_r = α + βω_r²` directly so a rigid-body mode
  (`ω_r = 0`) stays finite where the ratio itself diverges.
- Fits: two-point anchoring (`from_frequencies`), least-squares over measured
  modal damping (`from_modal_damping`), and the mass-/stiffness-only
  degenerate cases.
- `modal_damping_matrix` realizes prescribed modal ratios physically as
  `C = MΦ diag(2ζ_rω_r/m_r) ΦᵀM`; the Caughey–O'Kelly residual
  `‖CM⁻¹K − KM⁻¹C‖` (`proportionality_index`) classifies any `C` as
  classical or not.
- Structural damping has no viscous matrix unless a reference frequency is
  named; requesting one without it raises `SolverError` (MS-0.3).

### MS-7.2 Complex (damped) modes

The quadratic eigenproblem `(s²M + sC + K)φ = 0` is solved through the
symmetric state-space linearization

```
A = [[C, M], [M, 0]],   B = [[K, 0], [0, −M]],   (sA + B)ψ = 0,  ψ = [φ; sφ]
```

- One member of each conjugate pair is retained; overdamped (real) roots have
  no partner and are flagged by `is_oscillatory`.
- Default `"state"` normalization scales each mode to unit modal-A
  `a_r = φ_rᵀCφ_r + 2s_rφ_rᵀMφ_r`, the scaling that makes the residue
  numerator exactly `φ_rφ_rᵀ`.
- Derived spectrum: `ω_r = |s_r|`, `ω_d = |Im s_r|`, `ζ_r = −Re s_r/|s_r|`.
- Modal Phase Collinearity grades how monophase each mode is; proportional
  damping must return MPC = 1 to machine precision (AC-DYN-003).
- Massless retained DOFs make the pencil singular and raise `SolverError`
  rather than returning junk eigenvalues.

### MS-7.3 Harmonic response and FRF synthesis

Receptance is displacement per unit force; mobility is `iωH` and accelerance
`−ω²H`, and the three are interconvertible on a `FrequencyResponse`
(conversion to a lower order at 0 Hz is refused as singular).

- **Real-mode superposition** (`modal_frf`):
  `H_jk(ω) = Σ_r φ_jrφ_kr / (m_r[(ω_r² − ω²) + iω·2ζ_rω_r])`, optionally plus
  a residual-flexibility matrix `R = K⁻¹ − Σ_r φ_rφ_rᵀ/(m_rω_r²)` that
  restores the static contribution of the truncated modes.
- **Complex-mode residues** (`complex_modal_frf`):
  `H(iω) = Σ_r [φ_rφ_rᵀ/(a_r(iω − s_r)) + conj]`, valid for non-proportional
  damping where real-mode superposition is not.
- **Direct inversion** (`direct_frf`, `harmonic_response`): solve
  `Z(ω)x = f` with `Z = (1 + iη)K − ω²M + iωC` per frequency line. This is the
  untruncated reference the two syntheses are gated against (AC-DYN-002), and
  a singular `Z` raises `SolverError` naming the offending frequency.
- With the full basis retained, both syntheses must reproduce direct inversion
  to solver precision; against a closed-form 1-DOF/2-DOF oracle the receptance
  must match to 1e-8 relative off resonance (AC-DYN-001).

### MS-7.4 FRF correlation metrics

- **FRAC** — `|h_aᴴh_b|² / ((h_aᴴh_a)(h_bᴴh_b))` over the frequency axis: the
  FRF analogue of MAC (MS-2.2), 1 for FRFs differing only by a complex scale.
- **FDAC** — the same ratio between the deflection shapes of two FRF sets at
  every pair of frequency lines; a clean diagonal means matched resonances and
  an off-diagonal ridge exposes a frequency shift.
- Both are re-exported through `openfemlab.correlation` so FRF correlation
  reaches consumers through the M2 namespace without a second implementation
  (the GAP-01 rule). Degenerate (zero-norm) inputs return 0 rather than NaN.
- `correlation.frf_correlation` drives the two kernels over a measured/
  synthesized pair — resolving the shared frequency line, the exciter column
  and the channel labels — and returns the `FRFCorrelation` block
  (per-channel FRAC, the FDAC matrix, mean/min scalars) that `CorrelationReport`
  publishes under its `frf` key from schema 1.1 on (MS-2.6). The FDAC matrix is
  `O(n_frequencies²)` and can be suppressed with `with_fdac=False`.
- Self-identity and scale invariance mirror AC-CORR-001/002 and are gated by
  AC-DYN-004.
- Measured FRFs enter through the dataset-58 reader (`io/uff.py`); a
  synthesized `FrequencyResponse` written in that format must survive the
  round trip and correlate at FRAC = 1 with its source (AC-DYN-005).

### MS-7.5 Public API

```python
def complex_modes(K, M, C=None, num_modes=None, *, free_dofs=None,
                  normalization: str = "state") -> ComplexModalResult

def modal_frf(frequencies, modes, damping=0.0, *, modal_masses=None,
              num_modes=None, response_dofs=None, excitation_dofs=None,
              residual=None,
              response_type: str = "receptance") -> FrequencyResponse

def direct_frf(frequencies, K, M, C=None, *, free_dofs=None,
               structural_damping=None, response_dofs=None,
               excitation_dofs=None,
               response_type: str = "receptance") -> FrequencyResponse

def harmonic_response(frequencies, K, M, C=None, *, load, free_dofs=None,
                      structural_damping=None) -> np.ndarray

def frac(reference, comparison, *, axis: int = 0)
def fdac(reference, comparison) -> np.ndarray
```
