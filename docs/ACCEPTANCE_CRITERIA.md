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
  `DYN` (M6), `ELEM` (M7), `IO` (M8), `MPE` (M9), `PRETEST` (M10).
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
frequencies). The M7 gates add the structured element meshes of
`openfemlab.mesh.simple` (`quad_plate_mesh`, `tet_block_mesh`,
`hex_block_mesh`) with deterministically displaced interior nodes. The M8 gates
add files written into `tmp_path` during the run — a native JSON/YAML document
and, for the mesh formats, a meshio file whose contents come from those same
generators — rather than committed binaries, so no gate depends on a fixture
whose provenance cannot be read off the test. All randomized inputs use seeded
`numpy.random.Generator` instances; a criterion is only "verified" if its test
is deterministic.

### 1.5 Status lifecycle

Each registry entry carries a status: `specified` → `implemented`
(test exists and passes locally) → `verified` (test passing in CI on the
default branch). The registry file is the single source of truth for status.

The `implemented` → `verified` promotion is enforced, not asserted by hand.
`tests/acceptance/test_registry_ci.py` re-runs the tagged tests of every
criterion the registry marks `verified` in a clean pytest subprocess — the
selection is derived from the registry, so the two cannot drift — and the
promotion only holds when

1. the gate run exits green with no failure, error, or skip,
2. every promoted criterion contributes at least one passing test, landing in
   the suite its registry row names,
3. a second run under a different interpreter hash seed and single-threaded
   BLAS reproduces the outcome test for test (the determinism rule of
   section 1.4), and
4. the CI `gates` job still runs `import openfemlab`, Ruff, the registry
   consistency tests, this gate, and the acceptance suites on every push.

Any of those failing turns the suite red, so a broken criterion has to be
demoted to `implemented` (or fixed) before the branch can go green again.
The gate selection is available to any run through
`pytest --criterion AC-<MODULE>-NNN [--criterion-report PATH]`
(`tests/conftest.py`).

Performing a promotion is a tool run rather than an edit:

```
python scripts/promote_verified.py --run --apply AC-DYN-001 AC-DYN-002
```

`scripts/promote_verified.py` runs that same gate selection (or reads the
report of a run that already happened, `--report PATH`), and rewrites the
status literal of a row only when the run exited zero and every one of the
criterion's collected tests passed in the suite the registry names. A skip, a
partial result, evidence from another suite, or a row still `specified` blocks
the promotion and leaves the registry untouched; without `--apply` the tool
only prints the plan.

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

## 8. M7 — Element Library (spec MS-8)

Added in Round 2 by R2-T02 (gap GAP-02) once the QUAD4, TET4 and HEX8
formulations were all on the trunk, and widened to `ShellQuad4Element` when the
flat facet followed. The module supplies the `K` and `M` every other module
consumes, so its criteria are the preconditions of the M1 gates:
AC-ELEM-002 is what makes the AC-MODAL-004 rigid-body count meaningful, and
AC-ELEM-003 is the mesh-convergence half of AC-MODAL-001's "mesh-converged
oracle" wording. Each criterion is checked on **every** formulation in MS-8.2,
not on a representative one: `tests/acceptance/test_elements.py` holds one
`ELEMENT_CASES` row per family (QUAD4, TET4, HEX8, SHELL4) and every criterion
is parameterized over it, so a new formulation is covered by adding a row.

| ID | Pri | Criterion (summary) | Quantitative gate | Spec |
|----|-----|--------------------|-------------------|------|
| AC-ELEM-001 | P0 | Patch test exact to machine precision | distorted patch: interior rel. err ≤ 1e-12 (≤ 1e-10 for the shell facet, see below); element stress rel. err ≤ 1e-9 | MS-8.3 |
| AC-ELEM-002 | P0 | Rigid-body invariance and zero-energy mode count | ‖Kd‖ and energy ≤ 1e-10 relative; nullity = 3 (planar) / 6 (spatial) exactly | MS-8.3 |
| AC-ELEM-003 | P1 | Quadratic h-convergence on the continuum oracle | error ratio ≥ 3.6 per halving (observed order ∈ [1.8, 2.2]); finest ≤ 1e-3 (≤ 6e-3 on the plate oracle) | MS-8.4 |

### Details

- **AC-ELEM-001** (`oracle`) — A patch of 9 (planar) or 27 (spatial) cells whose
  interior nodes are pulled 20 % off the regular grid, so no element is a
  parallelogram or parallelepiped, carries the linear field `u = G x` on every
  boundary node. Then: the interior displacements reproduce `G x` to ≤ 1e-12
  relative to the largest prescribed value, and every element reports the
  constant stress `D ε(G)` to ≤ 1e-9 relative at every sampled natural point
  (no component of that stress is allowed to be trivially zero). The
  single-element form — exact strain recovery on distorted geometry and
  self-equilibrated consistent nodal forces — is asserted alongside.
- **AC-ELEM-002** (`property`) — On the same distorted geometry, each of the 3
  planar or 6 spatial rigid-body motions gives `‖K d‖_∞ ≤ 1e-10 · max|K| · ‖d‖_∞`,
  strain energy ≤ 1e-10 relative, and zero recovered strain. The element
  stiffness has exactly that many zero eigenvalues — full integration leaves no
  hourglass mode — and an unsupported assembly returns exactly that many
  zero frequencies with the first elastic mode well separated. The nullity is
  asserted as its two halves — every rigid-body eigenvalue below 1e-10 of the
  largest, and eigenvalue number `nullity` above a formulation-dependent floor
  of it — rather than as a count against one fixed cut, because where that cut
  may sit is itself a property of the formulation (see the shell row below).
- **AC-ELEM-003** (`property`) — With `ν = 0` the lateral directions decouple
  and a strip/block cantilever discretizes the continuum bar whose first axial
  frequency is `c/(4L)`, `c = √(E/ρ)`. Refining 4 → 8 → 16 elements, the
  frequency error is positive (a conforming displacement field with consistent
  mass converges from above), strictly decreasing, at least 3.6× smaller per
  halving with an observed order in [1.8, 2.2], and below 1e-3 at the finest
  mesh. A formulation that carries bending DOFs is refined a second time
  against a plate oracle, because the bar reaches it only through its membrane.

### The shell row

`ShellQuad4Element` is the first formulation whose nodes carry rotations, and
the three criteria say the following about it rather than anything weaker.

- **The prescribed state is two states.** The shell patch carries a constant
  membrane strain *and* a constant curvature at once — a facet that reproduced
  only the first would still be an inadmissible plate — and the recovered
  quantities are the membrane stress, the bending moment, and the transverse
  shear that the exact state leaves at zero.
- **The fixtures are not axis-aligned.** A facet reports its resultants in a
  frame its own geometry fixes, so the patch and the single element are laid on
  a plane sharing no axis with the global frame; every expected resultant is
  rotated into the reporting facet's frame before it is compared. On a global
  plane, every facet rotation would be an identity and none of the machinery
  that makes the element a shell would be gated.
- **The rigid-body set drops the drilling component.** Rotation about the facet
  normal is not part of the shell's kinematics: the director does not turn with
  it, and the drilling stiffness is a penalty on a fictitious DOF (MS-8.2). The
  six motions carry the director rotation with its normal component projected
  out, which is what an unsupported shell assembly moves along — and the
  free-assembly half of AC-ELEM-002 confirms exactly six zero frequencies.
- **Two gate numbers differ, and only for stated reasons.** The patch gate is
  1e-10 rather than 1e-12: the facet couples a membrane going as `t`, a bending
  rigidity going as `t³` and two penalties, which puts `cond(K)` of the patch at
  ~1e7 against the continuum patches' ~1e4, so the measured defect is 2.6e-12
  rather than the ~1e-16 the continuum rows reach — the gate keeps the same two
  decades of headroom over the measurement. And the zero-energy floor is 1e-9 of
  the largest eigenvalue rather than 1e-3: the facet's smallest elastic mode
  *is* the drilling penalty, at 2e-8 of its largest, so a cut chosen for a
  continuum element would swallow the mode that makes the facet non-singular and
  report ten zero-energy modes instead of six.
- **Bending convergence has its own oracle.** The AC-ELEM-003 bar row reaches
  the facet only through its membrane, so a simply supported square plate is
  refined 4 → 8 → 16 against the Reissner–Mindlin Navier spectrum,
  `ω² = ω_Kirchhoff² / (1 + D k² / (κGt))`. Rotary inertia is absent from that
  closed form and from the element's default mass matrix alike, so the two
  describe the same theory and the whole error is the discretization error —
  which is what lets a rate be measured. Measured: 7.3e-2 → 1.7e-2 → 4.3e-3, an
  observed order of 2.06 and 2.01. The finest-mesh gate is 6e-3 rather than
  1e-3 because the plate oracle's error constant is an order of magnitude above
  the bar's; the rate gates are unchanged.

---

## 9. M8 — Model Interchange (spec MS-9)

Added in Round 2 by R2-T05 (gap GAP-03) once the meshio bridge and the
`NeutralModel` → `Model` conversion were both on the trunk. The module is the
platform's only door: every other module's gates start from matrices, and these
three are what make the claim "an externally meshed structure can be analyzed
here" testable. They are ordered as the path a file travels — the native schema
that all readers write into (AC-IO-001), the foreign-format bridge that fills it
(AC-IO-002), and the conversion that turns it into something the M1 solver can
run (AC-IO-003).

| ID | Pri | Criterion (summary) | Quantitative gate | Spec |
|----|-----|--------------------|-------------------|------|
| AC-IO-001 | P0 | Native document survives the JSON/YAML round trip | arrays bitwise equal; both encodings parse to one document | MS-9.2 |
| AC-IO-002 | P1 | meshio file round trip preserves the neutral model | nodes bitwise; blocks, property ids and labels exact | MS-9.3 |
| AC-IO-003 | P0 | Imported mesh assembles as the hand-built model | `K`, `M`, DOF partition and mass identical; f₁ within 1 % of the bar oracle | MS-9.4 |

### Details

- **AC-IO-001** (`contract`) — A `NeutralModel` carrying two element blocks,
  material and property tables and a `DofMap`, a `ModalResult`, and a
  `TestData` with *complex* shapes, damping and geometry are each written and
  read back in both encodings. Then: every array compares bitwise equal (the
  writer emits full float repr precision, and complex arrays travel as an
  explicit real/imaginary pair), every table and `meta` entry compares equal,
  the JSON and YAML files of one object parse to the *same* mapping, and each
  document carries `format`, `schema_version` and its `object_type`. A
  non-finite float is rejected at write time rather than emitted in a spelling
  the two encodings disagree on.
- **AC-IO-002** (`contract`) — A neutral model with `rod2`, `quad4` and `hex8`
  blocks, non-contiguous node labels and per-element property and element ids
  round trips through `to_meshio` → `from_meshio` in memory and through
  `write_meshio` → `read_meshio` on disk in every format that carries data
  arrays (VTU, VTK, and Gmsh for a single-block model): coordinates bitwise,
  and node ids, per-block connectivity *in those ids*, property ids and element
  ids exactly. A format with no data arrays (Abaqus `.inp`) preserves geometry
  and topology positionally and renumbers the labels from 1, which the gate
  asserts so the degradation stays documented. An `ElementType` outside the
  one-to-one table raises `FormatError` instead of collapsing onto a cell type
  that would read back as a different element, and an unmapped *cell* type is
  skipped with a warning and a `meta["skipped_cell_types"]` record.
- **AC-IO-003** (`contract`) — For each formulation the converter binds
  (`ROD2`, `QUAD4`, `TET4`, `HEX8`), a mesh written by meshio itself — no
  OpenFEMLab data arrays, so the labels and property ids are the reader's own —
  is read with `read_meshio`, converted with `neutral_to_model`, constrained and
  assembled. Then `K`, `M`, the free/constrained DOF partition and
  `total_mass` are **identical** to the assembly of the model
  `openfemlab.mesh.simple` builds from the same nodes and elements, and the
  modal frequencies agree to 1e-12 relative. The imported bar, restrained to
  its axial direction, reaches the continuum first frequency `c/(4L)`,
  `c = √(E/ρ)`, within 1 %, so the path produces a physically right model and
  not merely a self-consistent one.

---

## 10. M9 — Modal Parameter Extraction (spec MS-10)

Specified in Round 3 (A133, gap GAP-06) ahead of its implementation, which
landed in the same round: `openfemlab.mpe` implements the MS-10.6 surface and
every row below is gated by `tests/acceptance/test_mpe.py`. M9 leaves the
registry's `MODULES_AWAITING_PROMOTION` list — the rule-8 exemption for a
module with no promoted row — at its first promotion.

The fixtures are the modules already on the trunk: FRFs synthesized by the M6
chain (`modal_frf`, MS-7.3) from models with known modal parameters are the
ground truth the estimators must recover, and the M8 dataset-58 reader is the
door measured data enters through — so every gate below is a twin or oracle
experiment against a modal model the test itself constructed.

| ID | Pri | Criterion (summary) | Quantitative gate | Spec |
|----|-----|--------------------|-------------------|------|
| AC-MPE-001 | P0 | LSCF pole recovery on synthesized FRFs | noise-free: f rel. err ≤ 1e-6, ζ rel. err ≤ 1e-4; no spurious in-band pole survives the filter | MS-10.2 |
| AC-MPE-002 | P0 | Shape/residue recovery (LSFD) | recovered shapes MAC ≥ 0.999 vs source modes; resynthesis FRAC ≥ 0.999 per channel | MS-10.4 |
| AC-MPE-003 | P0 | Stabilization diagram separates physical from computational poles | physical alignments fully stable over ≥ 3 consecutive orders; no computational alignment fully stable; auto-pick count = ground truth | MS-10.3 |
| AC-MPE-004 | P1 | Measurement path: UFF-58 → MPE → TestData → correlate | pipeline yields a `TestData` that pairs every mode at MAC ≥ 0.99 against the source model; `meta` carries provenance | MS-10.5 |
| AC-MPE-005 | P1 | Noise robustness of the estimator | seeded 1 % noise: f within 0.1 %, ζ within 20 % rel., MAC ≥ 0.98; bitwise deterministic per seed | MS-10.2, MS-10.3 |

### Details

- **AC-MPE-001** (`oracle`) — FRFs are synthesized over a band containing
  `n` well-separated modes of a known damped model (MS-7.3, proportional
  damping so the ground-truth `f_r`, `ζ_r` are closed-form). Fitting at a
  model order ≥ `n`, the physical poles recover every ground-truth frequency
  to relative error ≤ 1e-6 and every damping ratio to relative error ≤ 1e-4,
  and the MS-10.2 physicality filter leaves no spurious pole inside the band.
- **AC-MPE-002** (`twin`) — With the AC-MPE-001 poles frozen, the LSFD step
  recovers mode shapes whose MAC against the source model's channel-space
  shapes is ≥ 0.999 per mode, and the FRF resynthesized from the extracted
  model correlates with the input at FRAC ≥ 0.999 on every channel. With a
  driving point present the unity-modal-A scaling reproduces the source
  residues; without one the result is flagged `meta["scaling"] = "arbitrary"`.
- **AC-MPE-003** (`property`) — Over orders `n_min..n_max` spanning the true
  count, every physical pole forms an alignment classified fully `stable`
  (frequency 1 %, damping 5 %, vector MAC 0.95) over at least 3 consecutive
  orders, while no computational pole does; the automatic pick returns
  exactly the ground-truth number of modes, and tightening any tolerance
  never converts a `new` pole into a `stable` one (monotonicity of the
  classification).
- **AC-MPE-004** (`contract`) — A synthesized FRF set written as dataset-58
  records (the AC-DYN-005 round trip) is read back with
  `openfemlab.io.uff.read_uff_functions`, fitted, and bridged through
  `MPEResult.to_test_data`; the resulting `TestData` feeds
  `correlation.correlate` unchanged and pairs every mode against the source
  model at MAC ≥ 0.99, with `damping` populated and `meta` naming method,
  order, band and tolerances. An empty band or an order the line count
  cannot support raises `MPEError`.
- **AC-MPE-005** (`property`) — With seeded multiplicative noise (1 % RMS,
  `numpy.random.Generator`) added to the synthesized FRFs, the estimator
  stays within 0.1 % on frequencies and 20 % relative on damping ratios with
  shape MAC ≥ 0.98, and two runs on the same seeded input are
  bitwise-identical (the MS-10.1 determinism contract — the noise carries
  the seed, the estimator has none).

---

## 11. M10 — Pretest Planning and Sensor Placement (spec MS-11)

Added in Round 3 by A134 (gap GAP-07), **spec-first**: the `openfemlab.pretest`
API is stubbed against MS-11.5 and every row below is `specified` — no
implementation and no tagged tests exist yet, which section 12 rule 6 enforces
rather than trusts. The quantitative gates were measured on the pinned
fixtures before being written down (backward-elimination EI against exhaustive
subset search on the ten-DOF chain; the two five-channel layouts the
AC-CORR-009 suite already pins), so promotion requires an implementation, not
a renegotiation of the numbers. Until its first promotion, M10 sits in the
registry's `MODULES_AWAITING_PROMOTION`, the rule-8 exemption for a module
with no promoted row.

| ID | Pri | Criterion (summary) | Quantitative gate | Spec |
|----|-----|--------------------|-------------------|------|
| AC-PRETEST-001 | P0 | EI leverage identities and det-FIM downdate | at every step: `E_d ∈ [0, 1]`, `Σ E_d = m` (1e-10); det after removing `d` = `(1 − E_d)·det` to 1e-12 rel.; full orthonormal basis ⇒ every `E_d = 1 ± 1e-12` | MS-11.2 |
| AC-PRETEST-002 | P0 | EI attains the exhaustive det-FIM optimum on the chain fixtures | selected set equals the argmax over all C(10, s) subsets; det ratio = 1 on every pinned (m, s) case | MS-11.2 |
| AC-PRETEST-003 | P1 | Quality metrics separate layouts consistently with AC-CORR-009 | `(1,3,5,7,9)` beats `(0,2,5,7,9)` on all four metrics; EI det ≥ both; contiguous `(0..4)` auto-MAC ≥ 0.9 while EI ≤ 0.10 | MS-11.4 |
| AC-PRETEST-004 | P0 | Determinism, constraints, and typed failures | `s < m` / rank-deficient candidates raise `PretestError`; `keep` rows never eliminated; reruns bitwise identical | MS-11.2, MS-11.5 |
| AC-PRETEST-005 | P2 | MKE ranking matches the closed-form chain | mode-1 MKE strictly increasing toward the free end, argmax = tip; `mass = c·I` changes no EI selection | MS-11.3 |

### Details

- **AC-PRETEST-001** (`property`) — Running EI backward elimination on the
  ten-DOF chain's target modes, at every elimination step the retained
  leverages lie in `[0, 1]` and sum to the target-mode count `m` within 1e-10
  (trace of an orthogonal projector), and the FIM determinant after removing
  DOF `d` equals `(1 − E_d)` times the determinant before it to 1e-12 relative
  (matrix determinant lemma) — asserted against determinants computed
  independently of the selection code. For the full orthonormal basis
  (`k = n`, identity mass) every leverage equals 1 within 1e-12.
- **AC-PRETEST-002** (`oracle`) — On the 10-DOF fixed-free chain, for
  `(m = 3, s ∈ {3, 4, 5})` and `(m = 5, s ∈ {5, 6, 7})`, and on the
  `ten_dof_chain` fixture for `(m = 4, s = 5)`, the EI-selected sensor set
  equals the exhaustive-search argmax of `det(Φ_Sᵀ Φ_S)` over all `C(10, s)`
  subsets, computed by brute force inside the test. (Greedy backward
  elimination carries no general optimality guarantee; on these pinned
  fixtures the agreement is exact and was verified numerically before this row
  was written.)
- **AC-PRETEST-003** (`twin`) — On the AC-CORR-009 chain twin (four target
  modes, five channels), `placement_quality` ranks the spread layout
  `(1, 3, 5, 7, 9)` above the adversarial `(0, 2, 5, 7, 9)` on **all four**
  metrics (det_fim 0.091 vs 0.045, condition 1.20 vs 1.70, `σ_min` 0.71 vs
  0.50, auto-MAC off-diagonal 0.012 vs 0.13) — the same verdict the Guyan-TAM
  gate reaches on that pair; the EI selection's `det_fim` is ≥ both; and the
  contiguous layout `(0, 1, 2, 3, 4)` shows auto-MAC off-diagonal ≥ 0.9
  (spatial aliasing) where the EI selection stays ≤ 0.10. The criterion pins
  the *ranking*, not a TAM verdict: MS-11.1 records that the EI optimum's
  Guyan TAM can still fail AC-CORR-009, and the two checks stay separate.
- **AC-PRETEST-004** (`contract`) — Requesting `s < m` sensors, or a candidate
  set whose mode partition is rank deficient, raises `PretestError` (never a
  silent low-rank placement); rows named in `keep=` appear in every selection
  and never in the elimination order; rows outside `candidates=` are never
  selected; two runs with identical inputs return bitwise-identical
  `PlacementResult` arrays, the ties of the all-tie orthonormal case broken by
  the pinned highest-index-removed rule.
- **AC-PRETEST-005** (`oracle`) — On the uniform fixed-free chain the mode-1
  modal kinetic energy is strictly increasing toward the free end and its
  argmax is the tip DOF (closed-form mode shape `φ_j ∝ sin` of an increasing
  argument below `π/2`); scaling a uniform mass matrix by any positive
  constant changes no EI selection (weighting invariance of MS-11.2).

---

## 12. Registry and enforcement

`tests/acceptance/test_criteria_registry.py` holds the machine-readable
registry (one entry per criterion: ID, title, module, spec anchor, priority,
verification method, planned test reference, status).

The current inventory is **57 criteria**: M1 = 9, M2 = 9, M3 = 9,
M4 = 5, M5 = 4, M6 = 5, M7 = 3, M8 = 3, M9 = 5, and M10 = 5. The two suffixed M3 rows
(`AC-UPD-006a` / `AC-UPD-006b`) are distinct criteria under one dense base
number.

Fourteen of them were `verified` after the first two promotion waves (A109,
A121). The third wave — promoted at Round 2 sign-off — closed module **M8**
(AC-IO-001..003), putting every Round-1/2 row on the CI gate. Round 3 opened
modules **M9** (section 10) and **M10** (section 11) spec-first and then
implemented M9, so the inventory reads **47 `verified`, 5 `implemented`,
5 `specified`**; M9 and M10 are carried in `MODULES_AWAITING_PROMOTION` until
their first promotion.

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
7. Promotion honesty: `verified` is reserved for blocking (P0/P1) criteria,
   requires the green, reproducible gate run of section 1.5, and requires the
   CI `gates` job that runs it to exist.
8. Promotion span: every module in `VALID_MODULES` carries at least one
   `verified` criterion. The registry may name modules in
   `MODULES_AWAITING_PROMOTION` only while they have no promoted row; the same
   test fails if a module on that list already has one.

Adding, renaming, or retiring a criterion is done by editing the registry and
this document in the same change; the registry test fails otherwise.

Implementation suites tag their tests through
`tests/acceptance/_support.py::criterion`, which also rejects unknown IDs at
collection time, and are marked `acceptance` so a run can select them with
`pytest -m acceptance`.
