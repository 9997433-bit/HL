# Acceptance Criteria — FEMtools-like CAE Platform

**Document ID:** AC-R1-F2 · **Round:** 1 · **Author:** R1-F2 / A01 (module spec & acceptance criteria)
**Status:** Binding for Round-1..3 acceptance · **Companion doc:** `docs/MODULE_SPEC.md`
**Machine-readable registry:** `tests/acceptance/test_criteria_registry.py`

Every criterion below is a measurable, automatable gate bound to a section of
the module specification (`MS-x.y` anchors in `docs/MODULE_SPEC.md`). The
registry test enforces that this document, the module spec, and the registry
stay consistent (unique IDs, no dangling references, no numbering gaps).

---

## 1. Conventions

### 1.1 Criterion ID format

```
AC-<MODULE>-<NNN>[<suffix>]
```

- `<MODULE>` ∈ `MODAL` (M1), `CORR` (M2), `UPD` (M3), `WORK` (M4), `OPT` (M5),
  `DYN` (M6).
- `<NNN>`: three-digit number, dense per module (no gaps).
- `<suffix>`: optional single lowercase letter for closely coupled
  sub-criteria that share a number (e.g. `AC-UPD-006a` / `AC-UPD-006b`).

### 1.2 Priorities and round gates

| Priority | Meaning | Gate |
|----------|---------|------|
| **P0** | Core correctness — must pass for Round-1 module acceptance | blocks Round-1 sign-off |
| **P1** | Extended capability — must pass for Round-2 acceptance | blocks Round-2 sign-off |
| **P2** | Stretch/polish — targeted at Round 3 | tracked, non-blocking before Round 3 |

### 1.3 Verification method categories

| Method | Description |
|--------|-------------|
| `oracle` | Compare against a closed-form/analytic solution |
| `property` | Metamorphic/invariance property (e.g. scaling invariance) |
| `twin` | Twin experiment: synthetic "test" data generated from a known perturbed model; recovery of ground truth is checked |
| `contract` | API/behavioral contract: exceptions, schemas, determinism, serialization round-trips |
| `regression` | Pinned numeric baseline from a validated run |

### 1.4 Fixtures

Canonical fixtures live in `tests/fixtures/` (`two_dof_analytic.yaml`,
`ten_dof_chain.yaml`, `test_modes.yaml`) plus procedurally generated
spring–mass chains and Euler–Bernoulli cantilever beams (closed-form
frequencies). All randomized inputs use seeded `numpy.random.Generator`
instances; a criterion is only "verified" if its test is deterministic.

### 1.5 Status lifecycle

Each registry entry carries a status: `specified` → `implemented`
(test exists and passes locally) → `verified` (test passing in CI on the
default branch). The registry file is the single source of truth for status.

---

## 2. M1 — Modal Analysis (spec MS-1)

| ID | Pri | Criterion (summary) | Quantitative gate | Spec |
|----|-----|--------------------|-------------------|------|
| AC-MODAL-001 | P0 | Analytic eigenvalue accuracy | fixtures: rel. err ≤ 1e-10; beam vs theory ≤ 0.5 % | MS-1.1 |
| AC-MODAL-002 | P0 | Backend consistency (dense/lanczos/lobpcg) | freq rel. diff ≤ 1e-8; paired MAC ≥ 1 − 1e-10 | MS-1.2 |
| AC-MODAL-003 | P0 | Mass-orthonormality of returned modes | ‖ΦᵀMΦ − I‖_max ≤ 1e-8 | MS-1.3 |
| AC-MODAL-004 | P0 | Rigid-body mode detection | count = nullity(K); f = 0, `is_rigid=True` | MS-1.2 |
| AC-MODAL-005 | P0 | Sign convention & determinism | repeat runs bitwise identical; backends sign-agree | MS-1.3 |
| AC-MODAL-006 | P0 | Residual convergence guarantee | all pairs rel. residual ≤ tol (1e-8); else typed error | MS-1.2 |
| AC-MODAL-007 | P0 | Effective modal mass completeness | Σ m_eff = total mass, rel. err ≤ 1e-8 per direction | MS-1.4 |
| AC-MODAL-008 | P1 | Frequency-window extraction + missed-mode guard | window contents match dense reference exactly | MS-1.2 |
| AC-MODAL-009 | P0 | Input validation & typed failures | asymmetric/indefinite inputs raise typed exceptions | MS-1.1 |

### Details

- **AC-MODAL-001** (`oracle`) — Given the 2-DOF analytic fixture, the 10-DOF
  spring–mass chain (tridiagonal closed form), and a cantilever
  Euler–Bernoulli beam at a mesh-converged discretization; when
  `solve_modes(backend="dense")` is called; then fixture eigenvalues match
  closed form to relative error ≤ 1e-10 and the first 5 beam frequencies are
  within 0.5 % of theory.
- **AC-MODAL-002** (`property`) — On a chain with n ≥ 200 DOFs, `dense` and
  `lanczos` (and `lobpcg` where enabled) return the same k = 10 lowest modes:
  frequency relative differences ≤ 1e-8 and diagonal MAC between mode sets
  ≥ 1 − 1e-10 after pairing.
- **AC-MODAL-003** (`contract`) — For every backend and every accepted
  result, `‖Φᵀ M Φ − I‖_max ≤ 1e-8` (mass-normalized primary storage,
  MS-1.3), re-orthogonalization included.
- **AC-MODAL-004** (`oracle`) — A free-free chain (no ground springs) yields
  exactly `nullity(K)` modes flagged rigid with reported `f = 0`; elastic
  frequencies match the constrained reference analysis of the same structure.
- **AC-MODAL-005** (`contract`) — Two runs with identical inputs and `seed`
  produce bitwise-identical `ModalResult` arrays; across backends, the
  largest-|component|-positive sign rule yields identical signs.
- **AC-MODAL-006** (`contract`) — Every returned eigenpair satisfies the
  MS-1.2 relative residual ≤ `tol` (default 1e-8), asserted independently in
  the test; a deliberately starved iterative solve (max iterations forced
  low) raises `SolverConvergenceError` carrying a residual history.
- **AC-MODAL-007** (`oracle`) — With the complete modal basis (k = n) of a
  constrained structure, the effective modal mass summed over modes equals
  the total mass in each translational direction to relative error ≤ 1e-8.
- **AC-MODAL-008** (`oracle`) — A frequency-window request
  `f ∈ [f_lo, f_hi]` returns exactly the modes the dense reference places in
  that window; a constructed missed-mode scenario triggers
  `MissedModesWarning` (escalating to an error under `strict=True`).
- **AC-MODAL-009** (`contract`) — An asymmetric `K` beyond the MS-1.1
  symmetry tolerance raises a typed exception; an indefinite `M` (or a
  negative eigenvalue beyond the rigid-mode noise floor) raises
  `MatrixDefinitenessError`. No bare `assert`/silent NaN paths.

---

## 3. M2 — Correlation (spec MS-2)

| ID | Pri | Criterion (summary) | Quantitative gate | Spec |
|----|-----|--------------------|-------------------|------|
| AC-CORR-001 | P0 | Weighted MAC self-identity | ‖MAC_M(Φ,Φ) − I‖_max ≤ 1e-8 | MS-2.2 |
| AC-CORR-002 | P0 | MAC scaling/sign invariance | change ≤ 1e-12 under column scaling/flips | MS-2.2 |
| AC-CORR-003 | P0 | Pairing recovers ground truth | exact permutation recovery incl. missing modes | MS-2.3 |
| AC-CORR-004 | P0 | COMAC localizes bad DOF | argmin COMAC = perturbed DOF; others ≥ 0.99 | MS-2.5 |
| AC-CORR-005 | P0 | Frequency-error sign convention | stiffer model ⇒ Δf > 0; formula pinned | MS-2.4 |
| AC-CORR-006 | P1 | Reduction/expansion (SEREP) consistency | reduced vs expanded pairing identical; MAC ≥ 0.999 | MS-2.1 |
| AC-CORR-007 | P0 | MAC range and complex-shape support | values in [0, 1]; Hermitian identity holds | MS-2.2 |
| AC-CORR-008 | P0 | CorrelationReport JSON round-trip | serialize→parse→equal (arrays ≤ 1e-15) | MS-2.6 |
| AC-CORR-009 | P1 | TAM pseudo-orthogonality | \|POC\| diag ≥ 0.99, off-diag ≤ 0.10 | MS-2.1, MS-2.2 |

### Details

- **AC-CORR-001** (`property`) — For a mass-normalized mode set correlated
  with itself using mass weighting, the MAC matrix is the identity within
  1e-8 max-norm; unweighted `MAC(φ_i, φ_i) = 1` exactly (post-clipping).
- **AC-CORR-002** (`property`) — Multiplying any column of either mode set by
  a random nonzero real scalar (including negative) changes no MAC entry by
  more than 1e-12 absolute.
- **AC-CORR-003** (`twin`) — Given analysis modes and a synthetic test set
  built by permuting, sign-flipping, and dropping modes on both sides, the
  Hungarian pairing recovers the ground-truth correspondence exactly;
  candidate pairs with MAC < `mac_min` (0.7) appear in
  `unpaired_analysis`/`unpaired_test`, never in `pairs`.
- **AC-CORR-004** (`twin`) — Perturbing a single sensor DOF of the test
  shapes (sign flip or 50 % magnitude error) makes that DOF the argmin of
  COMAC while all unperturbed DOFs retain COMAC ≥ 0.99.
- **AC-CORR-005** (`oracle`) — Scaling the model stiffness by 1.01 relative
  to the "test" model yields Δf ≈ +0.5 % per mode (sign positive), computed
  as `100·(f_a − f_e)/f_e` (MS-2.4 convention pinned by test).
- **AC-CORR-006** (`twin`) — For noise-free synthetic test data extracted
  from the model at sensor DOFs, SEREP expansion reproduces the full-space
  analysis shapes with MAC ≥ 0.999, and pairing computed in reduced space
  equals pairing computed in expanded space.
- **AC-CORR-007** (`property`) — For random real and complex mode sets, all
  MAC entries lie in [0, 1] after clipping; for complex shapes,
  `MAC(φ, ψ) = MAC(conj(φ), conj(ψ))` (Hermitian transpose handling).
- **AC-CORR-008** (`contract`) — A `CorrelationReport` written to JSON and
  parsed back compares equal: settings and pairing table exactly, float
  arrays to ≤ 1e-15; the artifact carries `schema_version` (currently `"1.1"`,
  bumped when the `frf` block was added) and emits every schema key, `frf`
  included, whether or not the corresponding analysis ran.
- **AC-CORR-009** (`twin`) — Noise-free synthetic test modes read at the
  sensor DOFs and normalized through the TAM mass `M_TAM = Tᵀ M T` (MS-2.1)
  satisfy the MS-2.2 pseudo-orthogonality gate against the analysis modes on
  the same DOF set: `|POC| = |Φ_eᵀ M_TAM Φ_a|` has every paired diagonal entry
  ≥ 0.99 and every off-diagonal entry ≤ 0.10. The SEREP TAM meets it exactly
  (off-diagonal 0 to solver precision, because `T Φ_sensor = Φ`); a Guyan TAM
  on the *same* sensor set is the discriminating case and fails it, so the
  criterion gates test-analysis-model and instrumentation adequacy rather than
  restating the normalization.

---

## 4. M3 — Model Updating (spec MS-3)

| ID | Pri | Criterion (summary) | Quantitative gate | Spec |
|----|-----|--------------------|-------------------|------|
| AC-UPD-001 | P0 | Eigenvalue sensitivity vs central FD | rel. err ≤ 1e-6 | MS-3.3 |
| AC-UPD-002 | P0 | Fox–Kapoor shape sensitivity vs central FD | rel. err ≤ 1e-5 (full basis) | MS-3.3 |
| AC-UPD-003 | P0 | Twin-experiment parameter recovery | ‖θ* − θ_true‖_∞ ≤ 1e-3 in ≤ 10 iterations | MS-3.4 |
| AC-UPD-004 | P0 | Convergence monitoring & divergence guard | J non-increasing; typed stop reason; divergence raises | MS-3.4 |
| AC-UPD-005 | P0 | Ill-posed robustness (over-parameterized) | iterates bounded & in bounds; J non-increasing | MS-3.4 |
| AC-UPD-006a | P1 | Bayesian step → GN limit (weak prior) | step diff ≤ 1e-8 rel. as C_p⁻¹ → 0 | MS-3.5 |
| AC-UPD-006b | P1 | Posterior contraction (tight prior) | σ_post ≤ σ_prior componentwise | MS-3.5 |
| AC-UPD-007 | P0 | Collinear parameter detection & freeze | duplicate flagged (cos > 0.99), one frozen, still converges | MS-3.6 |
| AC-UPD-008 | P1 | Mode switching handled by re-pairing | residual ordering correct through a mode crossing | MS-3.2 |

### Details

- **AC-UPD-001** (`oracle`) — On the 10-DOF chain with stiffness and mass
  parameters, the analytic eigenvalue sensitivity
  `∂λ_i/∂p_j = φ_iᵀ(∂K/∂p_j − λ_i ∂M/∂p_j)φ_i` matches central finite
  differences (h = 1e-6·p_j,0) to relative error ≤ 1e-6 for all (i, j).
- **AC-UPD-002** (`oracle`) — Fox–Kapoor mode-shape sensitivities with the
  complete modal basis match central finite differences to relative error
  ≤ 1e-5 (componentwise, after MSF alignment); documented truncation error
  decreases monotonically as basis size grows.
- **AC-UPD-003** (`twin`) — Detuning 2–3 parameters of a known model by
  ±20 % and generating noise-free "test" modes, regularized Gauss–Newton
  recovers `θ_true` with `‖θ* − θ_true‖_∞ ≤ 1e-3` within 10 iterations, and
  the post-update correlation satisfies max|Δf| ≤ 0.1 % and min MAC ≥ 0.999.
- **AC-UPD-004** (`contract`) — Over all accepted steps, the objective `J` is
  non-increasing; `UpdatingResult` reports a stop reason from
  {`step_tol`, `cost_tol`, `gates_met`, `max_iter`}; a constructed diverging
  problem (wrong-sign residual injection) raises `UpdatingDivergenceError`
  after 3 consecutive accepted-step increases.
- **AC-UPD-005** (`property`) — With more parameters than residuals and two
  exactly collinear parameters, the LM-regularized iteration completes
  without exception, all iterates satisfy the parameter bounds, and `J` is
  non-increasing over accepted steps.
- **AC-UPD-006a** (`property`) — With `C_p⁻¹` scaled toward 0, the Bayesian
  MAP step converges to the unregularized Gauss–Newton step (relative
  difference ≤ 1e-8 at scale 1e-12).
- **AC-UPD-006b** (`property`) — At convergence, the reported posterior
  standard deviations satisfy `σ_post ≤ σ_prior` componentwise; with a very
  tight prior, `θ*` stays within 3σ_prior of `θ_0`.
- **AC-UPD-007** (`twin`) — A deliberately duplicated parameter (identical
  element set) is detected by the MS-3.6 collinearity screen
  (pairwise cosine > 0.99), one of the pair is frozen with a report entry,
  and updating still meets the AC-UPD-003 recovery gates on the survivor.
- **AC-UPD-008** (`twin`) — A parameter trajectory that makes two modes cross
  during updating is handled by per-iteration re-pairing: residuals stay
  attached to the physically correct modes (verified by ground-truth MAC
  tracking) and the run converges.

---

## 5. M4 — Simulation Correction Workflow (spec MS-4)

| ID | Pri | Criterion (summary) | Quantitative gate | Spec |
|----|-----|--------------------|-------------------|------|
| AC-WORK-001 | P0 | End-to-end correction passes gates | MAC ≥ 0.95 all pairs; |Δf| ≤ 1 % all pairs | MS-4.1, MS-4.2 |
| AC-WORK-002 | P0 | Deterministic reproducibility | all reported numbers within 1e-12 rel. across reruns | MS-4.3 |
| AC-WORK-003 | P1 | Held-out validation detects overfitting | reserved targets evaluated at S6; overfit run fails gate | MS-4.1 |
| AC-WORK-004 | P0 | Failed gate halts with typed reason | stage + machine-readable reason; no silent partial PASS | MS-4.1 |
| AC-WORK-005 | P0 | CorrectionReport schema & versioning | schema_version "1.0"; required keys; JSON-serializable | MS-4.3 |

### Details

- **AC-WORK-001** (`twin`) — Running `run_correction` on a synthetic detuned
  model (the AC-UPD-003 scenario wrapped in the S1–S6 pipeline) ends in
  S6 = PASS with every paired mode at MAC ≥ 0.95 and |Δf| ≤ 1 %.
- **AC-WORK-002** (`contract`) — Two invocations with identical inputs and
  `seed` produce `CorrectionReport`s whose every numeric field agrees to
  relative error ≤ 1e-12 (byte-identical JSON modulo wall-time fields).
- **AC-WORK-003** (`twin`) — With the highest paired mode reserved via
  `HoldoutSpec`, S4 residuals exclude it and S6 evaluates it (MAC ≥ 0.9 and
  |Δf| improved vs baseline); a constructed overfitting run (fitting noisy
  targets with excess parameters) fails the held-out gate and the report
  says so.
- **AC-WORK-004** (`contract`) — Feeding test data that pairs fewer than
  `min_pairs` modes stops the pipeline at S2 with a machine-readable
  `{stage: "PAIRING", reason: ...}` failure; no partial report is marked
  PASS and downstream stages do not run.
- **AC-WORK-005** (`contract`) — The report contains `schema_version: "1.0"`,
  baseline and final correlation blocks, iteration history, the parameter
  table (initial/final/bounds/σ_post where applicable), gate results,
  environment (package versions, seed), and per-stage wall time; it
  serializes to valid JSON.

---

## 6. M5 — Optimization Hook (spec MS-5)

| ID | Pri | Criterion (summary) | Quantitative gate | Spec |
|----|-----|--------------------|-------------------|------|
| AC-OPT-001 | P0 | Analytic gradients vs central FD | rel. err ≤ 1e-6 at 3 seeded feasible points | MS-5.1 |
| AC-OPT-002 | P0 | Reference problem reaches known optimum | objective within 1e-4 rel.; constraint active |g| ≤ 1e-6 | MS-5.2 |
| AC-OPT-003 | P0 | Box bounds never violated | every iterate satisfies bounds (tol 1e-12) | MS-5.2 |
| AC-OPT-004 | P1 | Mode tracking across crossings | tracked constraint follows physical mode (MAC ≥ 0.9) | MS-5.2 |

### Details

- **AC-OPT-001** (`oracle`) — Mass-objective and frequency-constraint
  gradients from the sensitivity kernel match central finite differences to
  relative error ≤ 1e-6 at three seeded feasible design points.
- **AC-OPT-002** (`oracle`) — The reference sizing problem (minimize total
  mass of a spring–mass chain subject to `f_1 ≥ f_min`, whose optimum is
  known to lie on the constraint boundary) converges to the known optimum:
  objective within 1e-4 relative, `|g_1| ≤ 1e-6` at the solution.
- **AC-OPT-003** (`contract`) — All design iterates recorded via the
  optimizer callback satisfy `p_lo ≤ p ≤ p_hi` within 1e-12; no objective or
  constraint evaluation is requested outside the box.
- **AC-OPT-004** (`twin`) — On a design path where two modes cross, the
  MAC-based mode tracker keeps the frequency constraint attached to the
  physically tracked mode (MAC ≥ 0.9 vs previous iterate's shape), and the
  active-constraint report identifies it consistently.

---

## 7. M6 — Damped Dynamics and FRF (spec MS-7)

Added in Round 2 by R2-T01 (gaps GAP-04/05). The module extends the M1
eigenproblem to damped response; its correlation metrics (FRAC/FDAC) are the
frequency-domain counterparts of the M2 gates AC-CORR-001/002.

| ID | Pri | Criterion (summary) | Quantitative gate | Spec |
|----|-----|--------------------|-------------------|------|
| AC-DYN-001 | P0 | Damped FRF vs closed form | 1-DOF/2-DOF receptance rel. err ≤ 1e-8 off resonance | MS-7.3 |
| AC-DYN-002 | P0 | Modal superposition = direct inversion | full basis: rel. err ≤ 1e-8 vs `Z(ω)⁻¹` | MS-7.3 |
| AC-DYN-003 | P0 | Proportional damping ⇒ real modes | MPC ≥ 1 − 1e-8; ζ_r matches `α/(2ω_r) + βω_r/2` to 1e-10 | MS-7.2 |
| AC-DYN-004 | P0 | FRAC/FDAC self-identity and invariance | self-FRAC = 1 ± 1e-12; scale change ≤ 1e-12; FDAC diagonal = 1 | MS-7.4 |
| AC-DYN-005 | P1 | Synthesized FRF survives UFF-58 round trip | abscissa and ordinate recovered to ≤ 1e-9 rel.; FRAC = 1 | MS-7.4 |

### Details

- **AC-DYN-001** (`oracle`) — For the viscously damped 1-DOF oscillator the
  synthesized receptance equals `1/(k − mω² + iωc)` and for the 2-DOF analytic
  fixture it equals the closed-form inverse of the 2×2 dynamic stiffness, both
  to relative error ≤ 1e-8 on a frequency line that avoids the resonances.
  Mobility and accelerance views satisfy `iωH` and `−ω²H` exactly.
- **AC-DYN-002** (`property`) — With the complete modal basis retained,
  `modal_frf` (real modes, proportional damping) and `complex_modal_frf`
  (complex modes, non-proportional damping) both reproduce `direct_frf` to
  relative error ≤ 1e-8 at every frequency line and every FRF entry. A
  truncated real-mode synthesis plus `residual_flexibility` reproduces the
  exact static (0 Hz) receptance.
- **AC-DYN-003** (`property`) — For `C = αM + βK`, the complex modes are
  monophase: MPC ≥ 1 − 1e-8 per mode, the extracted damping ratios match
  `ζ_r = α/(2ω_r) + βω_r/2` to 1e-10, the damped frequencies match
  `ω_r√(1 − ζ_r²)`, and `is_proportional(K, M, C)` is true while a
  deliberately non-proportional `C` (single grounded dashpot) is rejected.
- **AC-DYN-004** (`property`) — `frac(h, h) = 1` within 1e-12; scaling either
  FRF by a nonzero complex constant leaves FRAC unchanged within 1e-12; the
  FDAC matrix of a response set against itself has a unit diagonal and is
  symmetric; a zero-norm input yields 0 rather than NaN. This mirrors
  AC-CORR-001/002 in the frequency domain.
- **AC-DYN-005** (`contract`) — A synthesized receptance line written as an
  ASCII dataset-58 record (complex, even abscissa spacing) and read back with
  `openfemlab.io.uff.read_uff_functions` recovers the frequency abscissa and
  the complex ordinates to ≤ 1e-9 relative, and correlates with the source at
  FRAC = 1, so measured and synthesized FRFs are interchangeable in the
  correlation pipeline.

---

## 8. Registry and enforcement

`tests/acceptance/test_criteria_registry.py` holds the machine-readable
registry (one entry per criterion: ID, title, module, spec anchor, priority,
verification method, planned test reference, status).

The current inventory is **41 criteria**: M1 = 9, M2 = 9, M3 = 9,
M4 = 5, M5 = 4, and M6 = 5. The two suffixed M3 rows
(`AC-UPD-006a` / `AC-UPD-006b`) are distinct criteria under one dense base
number.

The registry tests enforce:

1. ID uniqueness and format (`AC-<MODULE>-NNN[a-z]?`).
2. Dense numbering per module (no gaps).
3. Every registry ID appears in this document, and every `AC-*` ID mentioned
   in this document or in `docs/MODULE_SPEC.md` exists in the registry.
4. Valid priority/status/method vocabularies and spec-anchor format.
5. Minimum coverage: every module has at least one P0 criterion.
6. Status honesty: a criterion may only carry `implemented`/`verified` when the
   suite named by its `test_file` contains a test tagged
   `@criterion("<ID>")`, and every tag in a suite resolves to a criterion that
   names that suite.

Adding, renaming, or retiring a criterion is done by editing the registry and
this document in the same change; the registry test fails otherwise.

Implementation suites tag their tests through
`tests/acceptance/_support.py::criterion`, which also rejects unknown IDs at
collection time, and are marked `acceptance` so a run can select them with
`pytest -m acceptance`.
