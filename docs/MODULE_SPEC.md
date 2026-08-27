# Module Specification — FEMtools-like CAE Platform

**Document ID:** MS-R1-F2 · **Round:** 1 · **Author:** R1-F2 (module spec & acceptance criteria)
**Status:** Draft for Round-1 implementation · **Companion doc:** `docs/ACCEPTANCE_CRITERIA.md`

This document specifies the core modules of the platform. Section anchors
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
| `lobpcg` | `scipy.sparse.linalg.lobpcg` on the shifted pencil `(K − σM, M)`, preconditioned by the factorization of `K − σM` | lowest modes when the factorization is too expensive to apply once per iteration |

`ModalSolver.solve` selects between them with `sparse` (dense or sparse path)
and `sparse_method` (`"arpack"`, the default, or `"lobpcg"`).

Backend contract:

- **Shift strategy (`lanczos`).** Default shift `σ = −0.01 · tr(K)/tr(M)`
  (small negative) so that `K − σM` is definite even with rigid-body modes.
  User-supplied `sigma` allowed for interior eigenvalues (frequency window
  requests `f ∈ [f_lo, f_hi]`).
- **Shift strategy (`lobpcg`).** The same small negative `σ`, but it is a
  *definiteness* shift rather than a target: the iteration runs on `K − σM`,
  whose spectrum is that of `K` offset by `σ` and which stays positive definite
  on a free-free structure where the zero eigenvalue of `K` would otherwise
  make the Rayleigh-Ritz projection ill-conditioned. Rayleigh-quotient descent
  reaches only the lowest modes, so a positive shift or a `freq_window` raises
  `SolverError` naming `arpack` instead of converging somewhere else.
- **Tolerance (`lobpcg`).** SciPy stops on the absolute residual
  `‖K φ − λ M φ‖`, which the convergence contract below bounds only relative to
  `‖K φ‖`. The backend therefore runs a first pass to estimate the
  denominators, derives the absolute bound that matches the relative contract
  (never below the round-off floor it could not beat anyway), and converges a
  second pass, warm-started from the first, against it. An explicit `tol` is
  passed straight through as the absolute bound instead.
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
  with the residual history attached — including from `lobpcg`, which SciPy
  reports by warning and returning the block it had rather than by raising.
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

### MS-1.6 Industrial sparse-scale contract

The M1 interface is also the platform's industrial-scale seam: callers do not
switch to a benchmark-only solver when a model grows beyond workstation-dense
size. For a sparse pair `(K, M)` with at least **50,000 free DOFs** and
`k << n`, the explicitly selected iterative path shall preserve sparse storage
through validation, symmetrization, shift construction, factorization and
eigenvalue extraction. A dense `(n, n)` materialization (`toarray`, `todense`,
or an implicit array conversion) of either full-order operator is forbidden;
only the returned `(n, k)` mode block and genuinely reduced blocks may be
dense.

The reference acceptance problem is a deterministic tridiagonal spring-mass
chain with `n = 50,000` and `k = 6`. A cold solve on the supported CI runner
must complete within a deliberately loose **120 s** envelope. The envelope is
a hang/regression tripwire, not a portable speed claim; the primary invariant
is sparse end-to-end storage (AC-PERF-001).

The sparse path remains numerically interchangeable with the dense reference:
on a mid-size problem for which both paths are practical, corresponding
frequencies agree to relative error `1e-8` and diagonal mode-shape MAC is at
least `0.999` (AC-PERF-002). Both checks use the same `ModalSolver` facade and
an explicit `sparse=True`/`False` override.

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
- **TAM mass**: any of those bases gives the test-analysis-model mass
  `M_TAM = Tᵀ M T` on the sensor DOFs, which is the weighting the MS-2.2
  pseudo-orthogonality check runs on. A basis built from a `SensorMap` is
  expressed in *channel* coordinates, so the per-channel orientation signs are
  carried by the reduction rather than applied by every consumer. Adequacy
  requirement: an acceptable TAM keeps exact test modes pseudo-orthogonal
  (AC-CORR-009).

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
  `POC = Φ_eᵀ M_ss Φ_a` (P1), with `M_ss` the MS-2.1 TAM mass and both mode
  sets normalized through it. Unlike the MAC the POC is not scale invariant —
  that is the point, it checks the normalization too. Gate: paired diagonal
  ≥ 0.99, off-diagonal ≤ 0.10 (AC-CORR-009).

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
3. **FRF residuals** (Round 3): on a chosen subset of frequency lines `ω_l`
   and the measured response/excitation channels,

   ```
   r(ω_l) = W_l [ H(ω_l; θ) − H_meas(ω_l) ]      stacked as [Re r, Im r]
   ```

   with `H` synthesized by MS-7.3 from the same parameterized `K(θ)`, `M(θ)`
   and `C(θ)`. Real/imaginary stacking rather than log-magnitude: it keeps the
   residual analytic in `θ` (so the sensitivity below is exact) and retains the
   phase that separates a stiffness error from a damping error, where a
   log-magnitude residual is non-differentiable at the antiresonances.
   `W_l` defaults to `1/|H_meas|` (floored relative to the largest measured
   magnitude), which turns the block into a relative error so no resonance
   peak dominates the fit; the unweighted complex difference is the
   alternative. Choosing *which* lines to fit is the caller's — the residual
   provider takes the subset and the weighting, it does not select them.

Re-pairing (MS-2.3) is executed every iteration — mode switching during
updating must not corrupt the residual ordering. The FRF block needs no
pairing: measured and synthesized lines are matched by frequency.

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
- **FRF sensitivity** — differentiating `H = Z⁻¹` with
  `Z(ω; θ) = K(θ) − ω² M(θ) + iω C(θ)`:

  ```
  ∂H/∂p_j = − H ( ∂K/∂p_j − ω² ∂M/∂p_j + iω ∂C/∂p_j ) H
  ```

  Exact wherever the `∂K/∂p`, `∂M/∂p`, `∂C/∂p` matrices of MS-3.1 are, and it
  costs one factorization of `Z(ω)` per line for *all* parameters rather than
  one per parameter. Validated against central finite differences of the
  assembled residual per AC-UPD-009; the finite-difference route stays
  available for models with no derivative matrices.

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
- Surfaces: `BayesianUpdater` / `update_model_bayesian` in Python, the
  `prior` / `noise_covariance` arguments of the MS-4 workflow, and the
  `prior:` / `noise:` sections of an `openfemlab update` configuration.
  All three report σ_post per parameter — `ParameterEntry.sigma_post` in a
  `CorrectionReport`, the `bayesian` block of the CLI document — through the
  one extractor `updating.bayesian.posterior_sigma`, which falls back to the
  least-squares `σ²(SᵀS)⁻¹` when the run was deterministic.

### MS-3.6 Parameter selection

Pre-updating diagnosis on the initial sensitivity matrix `S_0` (columns
scaled by `θ` — relative sensitivities):

- Rank/collinearity: greedy QR with column pivoting keeps the most observable
  independent columns. The pivot is the column with the largest component
  orthogonal to the span already retained, and a column is frozen when that
  component leaves it at cosine `> 0.99` to that span, or when admitting it
  would take the subset past `κ(S_sel) > 1e6`. Screening against the span
  subsumes the pairwise duplicate of AC-UPD-007 and additionally catches
  redundancy that exists only in combination (`S_c = S_a + S_b`, no pair
  near-parallel) and the wide-matrix case where parameters outnumber targets,
  neither of which a pairwise cosine or `κ(S_sel)` reveals.
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

The FRF block of MS-3.2 enters through a residual *provider* rather than a
second loop: `updating.frf.FRFResidual(model, measured, damping=...)` assembles
`r` and `∂r/∂θ`, and `FRFUpdater` / `update_model_frf` drive it with the
MS-3.4 estimator, line search, bound projection, divergence guard and σ_post
plumbing unchanged. An FRF run has no measured mode table, so its
`CorrelationSummary` is empty and the correlation it does report is the MS-7.4
FRAC/FDAC block (`FRFUpdatingResult.initial_frf_correlation` /
`final_frf_correlation`).

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
M7 elements assemble the K, M every module above consumes
M8 io reads a file into a NeutralModel and converts it into the M7 elements
M9 mpe fits measured FRFs (M8's dataset 58) into the TestData M2 consumes
M10 pretest selects sensor DOFs from M1 modes before M2/M4 mount the campaign
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

---

## 8. Module M7 — Element Library (`openfemlab.core.elements`) (MS-8)

Round-2 module (R2-T02) supplying the `K` and `M` every module above consumes.
Numbering note — the sixth module took `MS-7` because `MS-6` is the
inter-module contracts section, so the seventh takes `MS-8`.

### MS-8.1 Element contract

Every element is an `Element` subclass and exposes the same four things to
`core.assembly`:

- `node_ids` — connectivity in local node order;
- `bind(available)` — freezes the per-node DOF signature against the model's
  active DOFs, raising `ElementError` when a required DOF is inactive
  (MS-0.3: typed failure, never a silent drop);
- `stiffness_matrix(coords)` / `mass_matrix(coords)` — dense local matrices in
  **global** axes, ordered node-major with that DOF signature;
- `total_mass(coords)` — the structural mass the element contributes, which is
  what `AssembledSystem.total_mass` and the AC-MODAL-007 effective-mass balance
  are checked against.

Geometry enters only through `coords`; an element holds no copy of it, so a
model may be re-analyzed at moved nodes without rebuilding its elements.

### MS-8.2 Formulations

| Element | Nodes / DOFs | Formulation | Quadrature |
|---|---|---|---|
| `SpringElement` | 1–2 / one DOF | scalar spring, optionally grounded | — |
| `TrussElement` (`BarElement`) | 2 / translations | axial `EA/L` in direction cosines | closed form |
| `BeamElement2D` | 2 / `UX,UY,RZ` | planar Euler–Bernoulli | closed form |
| `Quad4Element` | 4 / `UX,UY` | bilinear isoparametric, plane stress/strain | `gauss_legendre_2d`, 2×2 default |
| `ShellQuad4Element` | 4 / all six | flat facet: plane-stress membrane + MITC4 Mindlin plate + drilling penalty | `gauss_legendre_2d`, 2×2 default |
| `Tet4Element` | 4 / translations | constant-strain tetrahedron | one point (exact) |
| `Hex8Element` | 8 / translations | trilinear isoparametric brick | `gauss_legendre_3d`, 2×2×2 default |

- Constitutive matrices are shared, not re-derived per element:
  `plane_constitutive_matrix(material, plane)` for the 2D states and
  `solid_constitutive_matrix(material)` for the 3D one (GAP-01 rule).
- Node ordering is counter-clockwise (QUAD4), first three counter-clockwise
  seen from the fourth (TET4), and face-by-face counter-clockwise (HEX8). A
  non-positive Jacobian is rejected with `ElementError` naming the offending
  natural point rather than silently sign-flipped.
- Structured generators in `mesh.simple` build the verification meshes:
  `quad_plate_mesh`, `shell_plate_mesh` (same row-major node numbering as
  `quad_plate_mesh`, so the membrane-only and shell discretizations of one
  rectangle share a node set), `tet_block_mesh` (Kuhn-subdivided cells,
  conforming) and `hex_block_mesh`, which numbers its nodes identically to
  `tet_block_mesh`.
- Known limitations, documented rather than hidden: QUAD4 and HEX8 carry
  bending through parasitic shear and lock on coarse high-aspect-ratio meshes;
  TET4 is constant-strain and locks far harder; all three stiffen as `nu → 0.5`.
  Reduced integration is selectable (`integration_order=1`) but rank deficient
  — 2 hourglass modes on QUAD4, 12 on HEX8 — and is provided for comparison
  studies only, with no hourglass stabilization.

`ShellQuad4Element` is the flat-facet shell that makes an imported shell mesh
analysable, so it carries the extra contract the continuum elements do not:

- **Facet frame.** `e_z` is the normal of the two diagonals, `e_x` the averaged
  `xi` direction projected into the plane, `e_y = e_z × e_x`. The local 24×24
  matrix is rotated into global axes node-block by node-block, exactly as
  `BeamElement3D` rotates its 12×12 blocks, so the element may sit at any
  orientation in space.
- **Three uncoupled parts** in that frame: the plane-stress `Quad4Element`
  membrane evaluated on the projected in-plane coordinates (one bilinear
  membrane kernel in the library, not two); a Reissner–Mindlin plate
  `K = ∫ B_kᵀ D_b B_k dA + κ G t ∫ B_sᵀ B_s dA` with `D_b = t³/12 · D` and
  `κ = 5/6`, whose transverse shear uses the **MITC4** assumed-strain field of
  Bathe and Dvorkin — covariant shears sampled at the four edge midpoints and
  interpolated linearly, curing shear locking without the rank deficiency
  reduced integration leaves behind; and a fictitious `drilling_factor`
  diagonal stiffness on the normal rotation, which keeps the local matrix
  non-singular.
- **Flatness is enforced, not assumed.** Nodes out of plane by more than
  `flatness_tolerance` times the element size raise `ElementError` naming the
  warp rather than being silently projected, so a warped quadrilateral must be
  refined.
- **What the penalty costs.** The drilling stiffness is decoupled from the
  membrane (no Allman or Hughes–Brezzi rotation field), so a coplanar assembly
  never loads it and keeps exactly six rigid-body modes as AC-ELEM-002 requires,
  while a folded assembly picks up a small mesh-dependent artificial stiffness
  at the fold. Drilling DOFs are always massless and the bending rotations are
  massless unless `rotary_inertia` is set — the modal solver condenses such DOFs
  exactly, but a damped or direct solve must constrain them. Membrane and
  bending do not couple within one facet, so curvature is represented only by
  the faceting of the mesh.

### MS-8.3 Completeness and stability

The two requirements that make an element admissible, both gated:

- **Patch test / constant-strain completeness.** On a patch of distorted
  elements whose boundary carries a linear displacement field `u = G x`, the
  interior displacements must reproduce that field and every element must
  report the constant stress `D ε(G)` — to machine precision, not to a
  tolerance (AC-ELEM-001). The quadrature rule must therefore integrate
  `det J` exactly, which the default rules do for any non-degenerate element.
- **Rigid-body invariance and rank.** Every rigid-body motion produces zero
  nodal force, zero strain and zero strain energy, and the element stiffness
  has exactly the rigid-body nullity — 3 planar, 6 spatial — so no hourglass
  mode survives full integration, and an unsupported assembly shows exactly
  that many zero frequencies (AC-ELEM-002). This is the element-level
  precondition for the AC-MODAL-004 rigid-body count.

Both are gated on **every** formulation of MS-8.2 through the one case table in
`tests/acceptance/test_elements.py`. Two things a rotational element states
differently, and both are the shell facet's: its patch prescribes a constant
membrane strain and a constant curvature at once, because a facet that
reproduced only the first would still be an inadmissible plate; and its six
rigid-body motions carry the director rotation with the component about the
facet normal projected out, since the director does not turn about itself and
the drilling stiffness is a penalty on a fictitious DOF, not a rotation field.

### MS-8.4 Mass matrices and convergence

- **Consistent mass** `M = ∫ ρ NᵀN dV` is the default; **lumped mass** is its
  row sum (`np.diag(M.sum(axis=1))`), which is unconditionally positive for
  these shape functions and preserves the total translational mass on any
  element shape. The lumped spectrum must not exceed the consistent one.
- Total mass and the lumped diagonal are integrated exactly by the default
  rules on any element geometry; the off-diagonal consistent terms of a
  distorted HEX8 are quadrature-approximated and converge with
  `integration_order=3`.
- **Convergence.** A conforming displacement element with consistent mass
  bounds eigenvalues from above and converges quadratically in `h`: halving
  the element size must quarter the frequency error against a continuum
  oracle (AC-ELEM-003). The oracle used is the axial spectrum of a bar,
  `f_1 = c/(4L)` with `c = √(E/ρ)`, which a 2D or 3D mesh reproduces exactly
  in the limit once `ν = 0` decouples the lateral directions.
- **Bending convergence** needs a second oracle, because the bar reaches a
  shell only through its membrane. `ShellQuad4Element` is refined against the
  Reissner–Mindlin Navier spectrum of a hard simply supported plate,
  `ω² = ω_Kirchhoff² / (1 + D k² / (κGt))` with `k² = π²(m² + n²)/a²`. Rotary
  inertia is absent from that closed form and from the element's default mass
  matrix alike, so the two describe the same theory and the observed error is
  the discretization error alone; against the Kirchhoff form it would instead
  stall at the plate's own shear correction.

### MS-8.5 Public API

```python
class Element(ABC):
    node_ids: tuple[Hashable, ...]
    def bind(self, available: tuple[DOF, ...]) -> tuple[DOF, ...]
    def stiffness_matrix(self, coords: np.ndarray) -> np.ndarray
    def mass_matrix(self, coords: np.ndarray) -> np.ndarray
    def total_mass(self, coords: np.ndarray) -> float

class Quad4Element(Element):   # thickness, plane, lumped_mass, integration_order
class Tet4Element(Element):    # lumped_mass
class Hex8Element(Element):    # lumped_mass, integration_order

class ShellQuad4Element(Element):
    # thickness, lumped_mass, rotary_inertia, integration_order, drilling_factor
    flatness_tolerance: float   # relative out-of-plane spread still called flat
    shear_correction: float     # 5/6
    def local_frame(self, coords) -> tuple[np.ndarray, np.ndarray]   # origin, [e_x, e_y, e_z]
    def local_coords(self, coords) -> np.ndarray                     # (4, 2) in-plane
    def transformation_matrix(self, coords) -> np.ndarray            # 24 x 24

def plane_constitutive_matrix(material, plane: str = "stress") -> np.ndarray
def solid_constitutive_matrix(material) -> np.ndarray
def gauss_legendre_2d(order: int = 2) -> tuple[np.ndarray, np.ndarray]
def gauss_legendre_3d(order: int = 2) -> tuple[np.ndarray, np.ndarray]
```

---

## 9. Module M8 — Model Interchange (`openfemlab.io`) (MS-9)

Round-2 module (R2-T05) owning every boundary between a file on disk and the
objects the modules above consume. Numbering note — the seventh module took
`MS-8` because `MS-6` is the inter-module contracts section, so the eighth
takes `MS-9`.

### MS-9.1 The two model representations

`docs/ARCHITECTURE.md` §L1 splits the flat interchange description of a
structure from the internal solver model, and this module owns the boundary
between them:

| Representation | Type | Carries |
|---|---|---|
| interchange | `core.neutral.NeutralModel` | node ids and coordinates, connectivity blocks keyed by `ElementType`, per-element property ids, material/property tables, optional `DofMap`, `meta` |
| internal | `core.model.Model` | active DOF signature, nodes, bound `Element` instances (MS-8.1), constraints |

- Every reader returns a `NeutralModel`, never a `Model`. A reader reports what
  the file says; choosing a formulation for a connectivity block is a separate
  decision, taken in MS-9.4.
- Connectivity is stored as **node ids**, not row indices, so the labels a
  format uses survive the trip and DOFs can be addressed by them afterwards.
- Unit conversion (MS-0.2) happens here and nowhere else.

### MS-9.2 Native schema (JSON and YAML)

The native format is one versioned document schema emitted in either encoding;
`format`/`schema_version`/`object_type` head every document, and
`schema_version` is bumped whenever the payload keys change.

| `object_type` | Object | Payload |
|---|---|---|
| `model` | `NeutralModel` | `node_ids`, `nodes`, `elements`, `element_property_ids`, `materials`, `properties`, optional `dof_map`, `meta` |
| `modal_result` | `ModalResult` | `frequencies_hz`, `mode_shapes`, `mode_shape_layout`, `dof_map`, `meta` |
| `test_data` | `TestData` | the above plus optional `damping` and `geometry` |

- **Round-trip exactness.** Writing an object and reading it back returns an
  equal object, arrays included: floats are emitted at full repr precision and
  complex arrays as an explicit `{"real": ..., "imag": ...}` pair, so a complex
  mode shape survives a format that has no complex type (AC-IO-001).
- **JSON and YAML are the same document**, not two schemas: the two encodings
  of one object parse to the same mapping, and either extension may be read.
  Non-finite floats are rejected rather than written, because their JSON and
  YAML spellings differ.
- Reading uses non-object-constructing loaders (`yaml.safe_load`), so an
  untrusted document cannot instantiate arbitrary Python.
- `mode_shape_layout` names the storage order explicitly (`dofs_by_mode` is the
  MS-1.3 contract) so a transposed fixture is converted rather than guessed at.
- Malformed input raises `FormatError` naming the offending field (MS-0.3);
  no reader falls back to a silent default.

### MS-9.3 Foreign formats and the optional-dependency seam

| Reader | Format | Notes |
|---|---|---|
| `read_uff` / `read_uff_modes` / `read_uff_functions` | UFF/UNV datasets 55, 58 | test modes and FRFs |
| `read_bdf` (`read_nastran`) | Nastran bulk data subset | `GRID`, `CROD`, `MAT1`, ... |
| `read_meshio` / `write_meshio` | everything `meshio` opens | optional `[io]` extra |

- **The bridge is a table, not a heuristic.** `CELL_TYPE_TO_ELEMENT` maps
  meshio cell types onto `ElementType` one-to-one, so a model exported with
  `to_meshio` reads back as the same blocks (AC-IO-002). `beam2` and `spring2`
  have no entry by construction: meshio's `line` cell carries nothing that
  would distinguish them from `rod2`, and `to_meshio` raises `FormatError`
  rather than collapsing them onto a cell type that would read back wrong.
- **Unknown cell types are skipped, not fatal**, with a warning and a
  `meta["skipped_cell_types"]` record — the same partial-import policy the
  Nastran reader applies to unknown cards.
- **Labels travel in data arrays.** `to_meshio` writes node ids as
  `point_data["node_ids"]`, element ids as `cell_data["element_ids"]` and
  property ids as `cell_data["property_ids"]`, which is what makes the round
  trip label-exact in a format that carries data arrays (VTU, VTK, Gmsh). A
  format that carries none of them (Abaqus `.inp`) still preserves geometry and
  topology, and the labels are renumbered from 1 — a documented degradation,
  not a silent one.
- **`meshio` is never imported at module import time** (ARCHITECTURE P7): only
  `read_meshio`, `write_meshio` and `to_meshio` need it, and each raises
  `MissingDependencyError` with an install hint when it is absent.
  `from_meshio` needs nothing beyond NumPy and accepts any object exposing
  meshio's `points`/`cells` attributes.
- A mesh file has geometry but no material data, so `materials` and
  `properties` come back empty and only the property *ids* survive, from cell
  data when the file has it.
- Every reader in this table is text. The one binary format worth adding,
  Nastran OP2, reads its framing and its normal modes in MS-9.6 but is
  deliberately absent from the package namespace until it has been held
  against real solver output.

### MS-9.4 Neutral → internal conversion

`neutral_to_model` is what makes an imported mesh *re-analyzable* rather than
only correlatable: it binds each connectivity block to the MS-8.2 formulation
of that element type and returns a `Model` the M1 solver accepts.

| Block | Element | Nodal DOFs |
|---|---|---|
| `ROD2` | `TrussElement` | `UX, UY, UZ` |
| `BEAM2` | `BeamElement3D`, or `BeamElement2D` in a planar model | `UX..RZ` |
| `QUAD4` | `Quad4Element` | `UX, UY` |
| `TET4` | `Tet4Element` | `UX, UY, UZ` |
| `HEX8` | `Hex8Element` | `UX, UY, UZ` |

- **The DOF signature is inferred** as the union of the blocks present, so a
  quad-only mesh comes back planar and anything containing a `BEAM2` gets all
  six DOFs; `dofs=` overrides it.
- **Material and section resolve through the neutral tables** by property id;
  the `material=` / `section=` / `thickness=` arguments are the fallback for
  the geometry-only case a mesh file produces, and a property that *is* defined
  wins over them field by field.
- **Equivalence.** The converted model assembles the same `K`, `M`, DOF
  partition and total mass as the model a user would have built by hand from
  the same nodes and elements — the conversion adds no interpretation
  (AC-IO-003). Node ids survive, so DOFs stay addressable by the file's labels.
- Blocks with no formulation (`TRI3`, `MASS1`, `SPRING2`) are rejected with a
  `FormatError` naming the block unless `skip_unsupported=True` drops them with
  a warning.
- Boundary conditions and point masses are not part of the interchange
  contract, so the returned model is **unconstrained**: apply `Model.fix`
  before a modal solve.

### MS-9.5 Public API

```python
SCHEMA_VERSION: str
SUPPORTED_FORMATS = ("json", "yaml")

def read(source, *, format=None) -> NeutralModel | ModalResult | TestData | Any
def write(value, destination, *, format=None) -> None
def read_model(source, *, format=None) -> NeutralModel
def write_model(model, destination, *, format=None) -> None
def read_modal_result(source, *, format=None, section=None) -> ModalResult
def read_test_data(source, *, format=None, section=None) -> TestData

def read_meshio(source, *, file_format=None, default_property_id=1) -> NeutralModel
def write_meshio(model, destination, *, file_format=None) -> None
def from_meshio(mesh, *, node_ids=None, default_property_id=1, source=None) -> NeutralModel
def to_meshio(model: NeutralModel) -> "meshio.Mesh"

def read_bdf(source) -> NeutralModel
def read_uff(source) -> UFFDataset

def neutral_to_model(neutral, *, dofs=None, name=None, material=None, section=None,
                     thickness=None, plane="stress", lumped_mass=False,
                     beam_orientation=None, integration_order=2,
                     skip_unsupported=False) -> Model
def infer_dofs(model: NeutralModel) -> tuple[DOF, ...]
```

### MS-9.6 Nastran OP2 — extension, Phases 1-3 implemented

Round-3 extension of GAP-03, scoped by the A139 spike. OP2 is the binary
companion of the bulk data MS-9.3 already reads, and the only industrial format
that carries the analysed model *and* its normal-mode solution in one file —
the pair M3 correlation and M4 updating want from an external solver. The
reader lives in `openfemlab.io.op2` over the record layer
`openfemlab.io.op2_framing`.

| Entry point | Phase | Status | Returns |
|---|---|---|---|
| `list_op2_tables(source)` | 1 | implemented | the file's data blocks, in file order |
| `read_op2_modes(source)` | 2 | implemented | `ModalResult` from `LAMA` + `BOUGV1`/`OUGV1`/`OUG1` |
| `read_op2(source)` | 3 | implemented for `GRID`, `CROD`, `MAT1`, `PROD` | `NeutralModel` from `GEOM1`/`GEOM2`/`EPT`/`MPT` |

- **Nothing is re-exported from `openfemlab.io`.** A name in that namespace
  advertises a *supported* reader; these stay reachable only as
  `openfemlab.io.op2.read_op2_modes`. This is the one place MS-9.5's "every
  reader is a package-level name" rule is deliberately broken, and the break
  ends not when the code works but when the corpus test below has run over
  real solver output — until then the implemented phases are validated against
  this repository's own reading of the format and nothing else.
- **`read_op2_modes` returns real normal modes in SORT1 or nothing.** It pairs
  the `LAMA` eigenvalue table with the first eigenvector table the file carries
  (`BOUGV1` first, since it is already in the basic frame), orders the modes by
  the `IDENT` mode number, builds the `DofMap` from the file's grid labels, and
  records the generalized masses and the tables it saw in `meta`. Complex
  eigenvectors (analysis code 9), SORT2, a non-eigenvector table code, a
  format code that is not real, a `num_wide` that is not the 8 words of a real
  grid entry, scalar and extra points, several modal subcases in one file, and
  a mode without a `LAMA` row all raise `FormatError` naming what was found.
- **The subset is the same one every other reader targets**: geometry into a
  `NeutralModel` and modes into a `ModalResult`, with the file's grid labels
  surviving into the `DofMap` (MS-9.1). Element stresses and forces
  (`OES`/`OEF`), loads and constraints (`GEOM3`/`GEOM4`) and the matrix blocks
  are outside it — no module consumes them, and MS-9.4 already excludes
  boundary conditions from the interchange contract.
- **Phasing is by risk, not by table.** Phase 1 is the Fortran record framing
  alone (word size and byte order from the opening byte count, the key
  continuation walk, block names and trailers), which reads no engineering data
  and is therefore the only layer that can be tested exhaustively offline —
  `op2_framing.py` is that layer and nothing else. Phases 2 and 3 build on it;
  Phase 4 adds the `CORD` coordinate-system cards that Phases 2 and 3 must
  **raise** on, since `GRID` carries `CP`/`CD` frames and OP2 eigenvectors are
  written in `CD` — the line `read_bdf` already draws for `GRID` and `read_unv`
  draws for dataset 2420. Phase 2 draws it by reading the `GRID` records of
  `GEOM1` for their frames alone and refusing a file where any is non-zero.
- **`read_op2` imports the geometry it can unpack and refuses the rest.** It
  reads `GRID` from `GEOM1`, the connectivity records listed in
  `GEOM2_ELEMENT_LAYOUTS` from `GEOM2`, the material records of
  `MPT_MATERIAL_RECORDS` from `MPT`, and the `PROD` records of
  `EPT_PROPERTY_RECORDS` from `EPT`, and a rod model imports to the same
  `NeutralModel` `read_bdf` builds from the bulk data of the same run. Records
  outside the subset are stepped over and counted per block in
  `meta["skipped_records"]` (MS-9.3), with one exception: a `GEOM2` record
  whose card is in `GEOM2_ELEMENT_RECORDS` but whose word layout is not in
  `GEOM2_ELEMENT_LAYOUTS` raises, since dropping it would return a model that
  looks complete and has lost an element block. Extending the subset is one
  table entry per card plus the tests that pin its layout; `PSHELL` and
  `PSOLID` are the remaining property increments.
- **Record keys are stable, record contents are not.** `GEOM2` records are
  addressed by a three-integer key (`CQUAD4` is `(2958, 51, 177)`), but MSC
  writes 15 words per `CQUAD4` entry where NX writes 14. Every unpack must
  check the record length against the entry size it assumes and name the block
  and key when it does not divide, rather than reading past an entry. The same
  applies to `GRID`, whose 11-word dialect writes the location in double
  precision: Phase 3 names and refuses it rather than read half a coordinate.
- **The blocker is fixtures, not parsing.** An OP2 cannot be produced without a
  Nastran licence, so CI cannot generate one the way it generates UFF and BDF
  text. The way out is `tests/_op2.py`, a test-only writer that emits the
  documented framing from a known model in both word sizes, both byte orders
  and both `PARAM,POST` forms — which validates the layouts against *our
  reading of the spec* — paired with an opt-in corpus test over real MSC and NX
  output, skipped when the corpus path is unset. That second half is the one
  still missing, and it is what keeps the reader experimental and unexported.
- **`pyNastran` (BSD-3) belongs on the dev side, not behind the MS-9.3 optional
  seam.** It would cover all of this today, but OP2 is the format an
  FE-correlation platform is judged on, and the Phase 1-2 subset is small over
  a stable framing. Its place is as the oracle that says whether our reading of
  a real file matches a mature one.

---

## 10. Module M9 — Experimental Modal Parameter Extraction (`openfemlab.mpe`) (MS-10)

Round-3 module (gap GAP-06). Numbering note — the eighth module took `MS-9`
because `MS-6` is the inter-module contracts section, so the ninth takes
`MS-10`.

**Status: implemented.** `openfemlab.mpe` implements the MS-10.6 surface, and
the `AC-MPE-001..005` rows of `docs/ACCEPTANCE_CRITERIA.md` are gated by
`tests/acceptance/test_mpe.py`. The section below is the binding
specification, not a plan.

### MS-10.1 Problem statement

Every module above ends at a synthesized FRF; MPE runs the arrow the other
way. Given a measured FRF matrix over a frequency line — the MS-7.3
`FrequencyResponse` contract, `data[f, j, k]` with `s` response channels and
`e` references, typically read from a UFF dataset-58 file through MS-9.3 —
estimate the experimental modal model

```
H_jk(iω) ≈ Σ_{r=1..n} [ ψ_jr L_kr / (iω − s_r)  +  ψ̄_jr L̄_kr / (iω − s̄_r) ]
           + UR_jk − LR_jk / ω²
```

with poles `s_r = −ζ_r ω_r + i ω_r √(1 − ζ_r²)`, channel-space mode shapes
`ψ_r`, reference participation factors `L_r`, and upper/lower residual terms
`UR`/`LR` absorbing the static contribution of out-of-band modes.

- Input is **receptance**; mobility/accelerance are converted through the
  MS-7.3 views first (the conversion refuses 0 Hz, so those inputs require an
  estimation band excluding DC).
- Estimation is restricted to a caller-selected band `f ∈ [f_lo, f_hi]`;
  poles are only reported inside it.
- Deterministic (MS-0.2): the estimators are linear algebra over the measured
  lines — no randomized starting values, so no seed argument is needed and
  identical inputs must produce bitwise-identical results.
- The output populates `TestData` — the M2 correlation input that GAP-06
  notes nothing produces from measurements. Combined with the GAP-03 UFF-58
  reader this closes the raw-measurement → correlation loop.

### MS-10.2 LSCF / poly-reference curve fitter

Right matrix-fraction description with a common denominator:

```
H(Ω_f) ≈ B(Ω_f) A(Ω_f)⁻¹ ,   B(Ω) = Σ_{k=0..n} β_k Ω^k ,   A(Ω) = Σ_{k=0..n} α_k Ω^k
```

- **Basis** `Ω_f = exp(iω_f Δt)` with `Δt = 1/(2 f_max)`, `f_max` the top line
  of the *measured* frequency axis rather than of the estimation band — the
  discrete-time (z-domain) basis of the LSCF family, chosen because a
  continuous-time power basis is numerically unusable beyond low model orders.
- **Poly-reference** (pLSCF, PolyMAX-class): `α_k ∈ R^{e×e}` so the
  denominator carries the participation directions; the scalar-`α_k`
  common-denominator LSCF is the single-reference degenerate case of the same
  kernel, not a second implementation (GAP-01 rule).
- **Estimator**: weighted linear least squares over the frequency lines;
  the per-channel numerator coefficients are eliminated through the reduced
  normal equations so only the denominator block is solved globally; the
  constraint `α_n = I` removes the parameterization ambiguity.
- **Poles**: eigenvalues of the block companion matrix of `A(Ω)`, mapped back
  by `s_r = ln(z_r)/Δt`. The participation factor `L_r` is the *left* null
  vector of `A(z_r)`: with `adj(A) = v uᵀ` the right matrix fraction
  `H = B A⁻¹` factors its residue as `(B v) uᵀ`, so `u` is the reference
  direction and `e = 1` degenerates it to a scalar.
- **Physicality filter** applied before anything is reported: discard poles
  with negative damping (the stable/unstable mirror pairs the LS produces by
  construction), poles outside the band, and poles with `ζ_r > ζ_max`
  (default 0.2).
- Requirements: on noise-free FRFs synthesized from a known modal model
  (MS-7.3), recovered frequencies and damping ratios must match ground truth
  (AC-MPE-001); under seeded measurement noise the estimates must degrade
  gracefully, not catastrophically (AC-MPE-005).

### MS-10.3 Stabilization diagram

- The MS-10.2 fit is repeated over model orders `n ∈ {n_min, ..., n_max}`;
  every pole at order `n` is compared against the nearest pole at `n − 1`.
- **Classification** (tolerances configurable, defaults pinned here):
  `new` → frequency-stable (`|Δf|/f ≤ 1 %`) → damping-stable additionally
  (`|Δζ|/ζ ≤ 5 %`) → fully `stable` additionally (participation-vector MAC
  ≥ 0.95, the MS-2.2 kernel on participation columns).
- `StabilizationDiagram` is a serializable (JSON, schema-versioned) artifact
  carrying the per-order pole lists with labels and the settings used, so a
  notebook or GUI renders it without refitting.
- **Pole selection**: explicit picks `(order, pole index)`, or automatic —
  the lowest-order fully stable member of every alignment that stays fully
  stable over ≥ `min_count` consecutive orders (default 3). Automated
  clustering of alignments is a P2 extension.
- Requirement: physical poles of a synthesized FRF form fully stable
  alignments while computational (noise) poles must not, and the automatic
  pick recovers exactly the ground-truth mode count (AC-MPE-003).

### MS-10.4 Residues, shapes and resynthesis (LSFD)

- With poles and participation frozen, the residues are a second **linear**
  least-squares problem (LSFD): solve for `A_r`, `UR`, `LR` per response
  channel over the band.
- Rank-1 decomposition `A_r = ψ_r L_rᵀ`: with `L_r` known from the
  poly-reference denominator, `ψ_r` follows directly per channel; the
  single-reference path takes the dominant left singular vector.
- **Scaling**: when the channel set contains a driving point, shapes are
  reported in unity-modal-A scaling — consistent with the MS-7.2 residue
  convention, which makes the resynthesized residue numerator exactly
  `ψ_r ψ_rᵀ`. Without one, shapes are unit-max and the result carries
  `meta["scaling"] = "arbitrary"` — a documented degradation, never a silent
  one.
- **Resynthesis quality** is the fit diagnostic every result carries: the
  per-channel FRAC (MS-7.4) between the measured FRF and the FRF
  resynthesized from the extracted model. Shape recovery is gated by
  AC-MPE-002; the end-to-end measurement path by AC-MPE-004.

### MS-10.5 Result contract

- `MPEResult` (frozen dataclass): `frequencies_hz`, `damping_ratios`,
  `poles`, `shapes` (`s×n` complex, channel space), `participation`
  (`e×n` complex), per-channel `frac`, and a `diagnostics` dict per MS-0.3 —
  orders fitted, band, tolerances, weighting, the scaling that was achieved,
  and the `UR`/`LR` residual blocks.
- `to_test_data(dof_map)` returns a `TestData` with `damping` populated,
  shapes on the sensor channels the `DofMap` names, and `meta` provenance
  (method, model order, band, tolerances) — the bridge that lets M2/M3/M4
  consume a measurement exactly as they consume a pre-extracted mode table.
- Typed failures (MS-0.3): `MPEError` for an empty estimation band, a model
  order the frequency line cannot support (fewer lines than unknowns), a
  non-receptance input the caller declined to convert, or a stabilization
  diagram with no fully stable alignment to pick from.
- Determinism: identical FRF, band, orders and tolerances produce
  bitwise-identical results (no seed — the estimators are direct solves).

### MS-10.6 Public API

```python
@dataclass(frozen=True)
class PoleEstimate:
    frequency_hz: float
    damping_ratio: float
    pole: complex                       # s_r, continuous-time
    order: int
    participation: np.ndarray | None    # (e,) complex
    label: str                          # "new" | "freq" | "damp" | "stable"

@dataclass(frozen=True)
class StabilizationDiagram:
    orders: tuple[int, ...]
    poles: tuple[tuple[PoleEstimate, ...], ...]   # one tuple per order
    settings: dict
    def select(self, *, min_count: int = 3) -> tuple[PoleEstimate, ...]

@dataclass(frozen=True)
class MPEResult:
    frequencies_hz: np.ndarray
    damping_ratios: np.ndarray
    poles: np.ndarray                   # (n,) complex
    shapes: np.ndarray                  # (s, n) complex, channel space
    participation: np.ndarray           # (e, n) complex
    frac: np.ndarray                    # (s,) resynthesis quality
    diagnostics: dict
    def to_test_data(self, dof_map: DofMap) -> TestData

def fit_lscf(frf: FrequencyResponse, order: int, *,
             band: tuple[float, float] | None = None,
             weighting: str = "unity") -> tuple[PoleEstimate, ...]

def stabilization_diagram(frf: FrequencyResponse, orders: Sequence[int], *,
                          band: tuple[float, float] | None = None,
                          freq_tol: float = 0.01, damp_tol: float = 0.05,
                          mac_tol: float = 0.95) -> StabilizationDiagram

def extract_shapes(frf: FrequencyResponse, poles: Sequence[PoleEstimate], *,
                   band: tuple[float, float] | None = None,
                   residuals: str = "both") -> MPEResult

def extract_modes(frf: FrequencyResponse, orders: Sequence[int], *,
                  band: tuple[float, float] | None = None,
                  min_count: int = 3, **tolerances) -> MPEResult   # one-call driver
```

---

## 11. Module M10 — Pretest Planning and Sensor Placement (`openfemlab.pretest`) (MS-11)

Round-3 module (GAP-07), **specified ahead of its implementation**: the MS-11.5
API is stubbed in `openfemlab.pretest` (every function raises
`NotImplementedError` naming this section) and the AC-PRETEST rows enter the
registry at `specified`. Numbering note — the eighth module took `MS-9`
because `MS-6` is the inter-module contracts section, the ninth took `MS-10`
(M9 MPE), so the tenth takes `MS-11`.

### MS-11.1 Problem statement and scope

Given the target mode set `Φ ∈ R^{n×m}` of an M1 solve (mass-normalized,
MS-1.3) and a candidate DOF set (default: every row of `Φ`; in practice the
translational free DOFs an accelerometer can observe), choose `s ≥ m` sensor
DOFs that keep the target modes observable and mutually distinguishable once
the campaign is reduced to those channels (MS-2.1). The output feeds a
`SensorMap`, so this module is where the sensor set of the whole M2/M4 chain
is decided *before* any hardware is mounted — the question the AC-CORR-009
sensor-placement case asks after the fact.

- **Figure of merit:** the Fisher information matrix of the sensor partition,
  `Q_S = Φ_Sᵀ Φ_S`. Under i.i.d. unit-variance channel noise, the least-squares
  estimate of the modal coordinates from the sensor readings has covariance
  `Q_S⁻¹`, so maximizing `det Q_S` minimizes the confidence volume of the
  identified modal coordinates.
- **Scope.** Round-3 scope is sensor placement (EI) plus the MKE ranking and
  the quality report; exciter (driving-point) placement shares the module and
  the result contract but is a P2 outline (MS-11.3).
- **What EI does *not* claim.** `det Q_S` grades target-mode observability,
  not test-analysis-model orthogonality: on the ten-DOF chain fixture the EI
  optimum for `m = 4, s = 5` is `(1, 3, 4, 6, 9)`, whose **Guyan** TAM fails
  the AC-CORR-009 0.10 off-diagonal gate at 0.19 (a SEREP TAM at the same
  placement is exact as always). TAM adequacy at a chosen placement therefore
  stays a separate check; MS-11.4 reports the observability metrics and leaves
  the TAM verdict to MS-2.1/AC-CORR-009 rather than folding the two together.

### MS-11.2 Effective Independence (EI)

Kammer's backward elimination on the candidate rows `C`:

```
E_d = [Φ_C (Φ_Cᵀ Φ_C)⁻¹ Φ_Cᵀ]_dd          (leverage of candidate DOF d)
```

- The `E_d` are the diagonal of the orthogonal projector onto the column space
  of `Φ_C`, hence `E_d ∈ [0, 1]` and `Σ_d E_d = m` exactly, at every
  elimination step — the conservation law AC-PRETEST-001 pins.
- **Iteration.** Remove the candidate with the smallest `E_d`, recompute the
  leverages, repeat until `s` rows remain. Each removal multiplies the FIM
  determinant by exactly `1 − E_d` (matrix determinant lemma), which is at
  once the justification of the greedy rule — remove the DOF whose loss costs
  the least determinant — and a per-step invariant a test can assert without
  trusting the implementation.
- **The iteration cannot destroy the rank it is protecting.** With
  `|C| > m` candidates the smallest leverage satisfies `E_min ≤ m/|C| < 1`,
  so the post-removal determinant `(1 − E_min) det Q` stays positive; rank
  collapse can only be *requested* (`s < m`, or a candidate set that is rank
  deficient to begin with), and such a request raises `PretestError`
  (typed failure, MS-0.3) instead of returning an unobservable placement.
- **Determinism and tie-breaking.** Among minimizers within `1e-12` of each
  other, the highest row index is removed (low-numbered DOFs are kept), so
  repeated runs are bitwise identical — the MS-0.2/AC-MODAL-005 discipline.
  A full orthonormal basis (`k = n`, mass-normalized modes of an identity
  mass) is the canonical all-tie case: every leverage is exactly 1.
- **Constraints.** `candidates=` restricts the pool (e.g. translations only);
  `keep=` marks rows that are never eliminated (already-mounted channels);
  both are honored row-for-row (AC-PRETEST-004).
- **Mass weighting.** Optional `mass=` reweights the shapes to `M^(1/2) Φ`
  (diagonal mass exactly, consistent mass via Cholesky), turning the FIM into
  a kinetic-energy-weighted information matrix. For `M = c·I` the weighting
  changes no selection.
- The reference implementation recomputes the projector each step; the
  rank-one leverage downdate is an optimization, not part of the contract.

### MS-11.3 Energy rankings (MKE; exciter outline)

- **Modal kinetic energy** `MKE_di = M_dd Φ_di²` (diagonal/lumped mass) ranks
  DOFs by the kinetic energy mode `i` carries there — the classical cross-check
  that an EI selection has not landed on low-signal DOFs. Exposed per mode and
  summed over the target set. On the uniform fixed-free chain the mode-1
  ranking is closed-form: `|φ_1|` increases monotonically toward the free end,
  so the tip is the argmax (AC-PRETEST-005).
- **Exciter placement** (P2 outline, API reserved): rank driving points by the
  average driving-point residue `ADPR_d = Σ_i Φ_di² / ω_i`, which favors DOFs
  that receive all target modes and penalizes node lines. Not part of the
  Round-3 gate set.

### MS-11.4 Placement quality assessment

`placement_quality` grades any placement — EI-selected or externally given —
so competing layouts are compared on numbers rather than adjectives:

| Metric | Definition | Reading |
|---|---|---|
| `det_fim` | `det(Φ_Sᵀ Φ_S)` | volume of the information ellipsoid |
| `condition` | `σ_max/σ_min` of `Φ_S` | worst-direction observability loss |
| `min_singular_value` | `σ_min(Φ_S)` | margin to an unobservable mode |
| `automac_off_diagonal` | max off-diagonal of `automac(Φ_S)` | spatial aliasing between target modes |

- The auto-MAC column is computed by `correlation.automac` (MS-2.2), not by a
  second kernel (the GAP-01 rule).
- On the AC-CORR-009 chain twin (four target modes, five channels) the four
  metrics rank the spread layout `(1, 3, 5, 7, 9)` above `(0, 2, 5, 7, 9)` on
  every axis — det 0.091 vs 0.045, condition 1.20 vs 1.70, `σ_min` 0.71 vs
  0.50, auto-MAC 0.012 vs 0.13 — the same verdict the Guyan-TAM gate reaches
  on that pair, while a contiguous five-channel layout `(0..4)` aliases the
  target modes at auto-MAC 0.91. Pinned by AC-PRETEST-003.

### MS-11.5 Public API

```python
@dataclass(frozen=True)
class PlacementQuality:
    det_fim: float
    condition: float
    min_singular_value: float
    automac_off_diagonal: float

@dataclass(frozen=True)
class PlacementResult:
    selected: tuple[int, ...]      # retained rows, ascending
    eliminated: tuple[int, ...]    # removal order, first removed first
    leverage: np.ndarray           # (s,) EI leverage of the retained rows
    det_fim: float                 # det(Q_S) of the selection
    det_history: np.ndarray        # det(FIM) after each elimination
    quality: PlacementQuality
    diagnostics: dict              # method, weighting, candidate/keep sets

def ei_leverage(shapes, *, mass=None) -> np.ndarray             # (n,)
def select_sensors(shapes, num_sensors, *, mass=None,
                   candidates=None, keep=(),
                   method: str = "ei") -> PlacementResult
def modal_kinetic_energy(shapes, mass) -> np.ndarray            # (n, m)
def placement_quality(shapes, selected) -> PlacementQuality
def to_sensor_map(placement, *, labels=None) -> SensorMap       # MS-2.1 bridge
```
