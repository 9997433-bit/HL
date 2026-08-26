# Round 2 Plan — Targeted Build-Out (OpenFEMLab)

**Author:** A24 (backfill for completed A22) · **Date:** 2026-08-26
**Branch:** `cursor/femtools-industrial-7aa3`
**Inputs:** [`docs/SOTA_GAP_ANALYSIS.md`](../docs/SOTA_GAP_ANALYSIS.md) (gap register §4,
sequencing §6), Round 1 conclusion in [`PROGRESS.md`](PROGRESS.md) (§Round Conclusions),
[`docs/ACCEPTANCE_CRITERIA.md`](../docs/ACCEPTANCE_CRITERIA.md) (binding AC-x gates),
[`docs/MODULE_SPEC.md`](../docs/MODULE_SPEC.md) (MS-x anchors),
[`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) (§11 Round 2 flags).

This plan turns the Round 1 conclusion and the SOTA gap register into a prioritized,
dependency-ordered Round 2 backlog. Five tracks are mandated as the Round 2 core:
**dynamics/FRF, SEREP reduction/expansion, Bayesian updating, 3D elements, meshio.**
A supporting backlog covers the remaining Round 2 items from
`SOTA_GAP_ANALYSIS.md` §6 that are not yet closed.

---

## 1. Starting state — what is already closed or in flight

The plan is *targeted*: it excludes work Round 1 backfills already landed. Delta against
the gap register at audit time:

| Gap | Audit status | Status entering Round 2 |
|---|---|---|
| GAP-01 integration split-brain | P0, suite not collecting | **Largely closed.** `ModalResult` unified (commit `508813e`), `modal/eigen.py` is a thin adapter over `solver/modal.py` (A08), full suite green at **192 passed** (A22). Residual: enforce the "seams land atomically with consumers" rule and keep CI green. |
| GAP-03 industrial IO | P0, absent | **Partial.** UFF datasets 55/58 reader (A12), minimal Nastran BDF `GRID`/`CROD`/`MAT1` (A18). Remaining: UNV 2411/2412, broader BDF cards, **meshio bridge (R2-T05)**, UFF writing, OP2. |
| GAP-14 CLI stubs | P2, stubbed | **Closed for R2.** `modal`/`correlate`/`update` landed with model-spec format, gates, JSON/YAML documents on clean stdout (A07/A16/A22). |
| GAP-10 updating depth | P1, absent | **Partial.** Dotted-path parameter targeting in the CLI spec layer (A07), affine `ScalingModel` dK/dθ (A04), vectorized Fox–Kapoor + MAC sensitivities (A04/A10). Remaining: model-level resolver, assembled per-element dK/dp, analytic MAC-row Jacobian wiring, MS-3.6 collinearity screen (**AC-UPD-007 is P0 and unimplemented**) → R2-T06. |
| GAP-09 node mapping | P1, absent | **Partial.** Label-based DOF alignment (`correlation/align.py`, `workflow/sensors.py`). Remaining: geometry-based nearest-node mapping → folded into R2-T05/T06 scope notes. |
| GAP-04/05 dynamics & FRF | P0/P1, absent | **Closed by R2-T01.** `cursor/dynamics-damping-frf-9500` merged at `acda625`; AC-DYN-001..005 registered and `implemented`. GAP-05's FRF *updating residual* stays deferred to Round 3 as planned below. |
| GAP-02 3D elements | P0, absent | **Partial.** QUAD4 plane stress/strain landed with `mesh.simple.quad_plate_mesh` and 61 tests (R2-T02 first slice, merged from `cursor/quad4-plane-stress-element-b99c`). Remaining: TET4, HEX8, 3D beam, the solid/shell BDF cards → R2-T02 remainder. |
| GAP-08 reduction/expansion | P1, absent | Open (R2 slice: Guyan/SEREP/TAM + expansion) → R2-T03. |
| GAP-11 Bayesian/UQ | P1, absent | Open (R2 slice: MS-3.5 MAP + posterior covariance) → R2-T04. |
| GAP-12 optimization backend | P2, stub | **Closed for sizing by R2-T07.** `ScipyBackend.solve` runs SLSQP/trust-constr with analytic Jacobians, hard bounds and active-set KKT residuals; AC-OPT-001..004 are implemented. `cursor/optimization-scipy-backend-f421` was harvested by A40 (active-set multipliers, zero trust-constr constraint Hessian). Shape variables still fall back to finite differences. |
| R1-O2 parallel implementation | — | Reconciliation of `cursor/r1o2-correlation-updating-e393` in progress on `cursor/reconcile-r1o2-correlation-updating-64c5` → R2-T08 harvests the diff. |

GAP-06 (MPE), GAP-07 (pretest EI), GAP-13 (50k-DOF scale), GAP-15 (plotting) stay in
Round 3 per `SOTA_GAP_ANALYSIS.md` §6.

---

## 2. Prioritized core backlog

Priorities follow the AC gate semantics
([`ACCEPTANCE_CRITERIA.md`](../docs/ACCEPTANCE_CRITERIA.md) §1.2): **P1 criteria block
Round-2 sign-off**, so gate-blocking tasks rank directly behind the two P0 capability
holes. Where a track has no existing AC coverage (dynamics, elements, meshio), the task's
first deliverable is a spec + criteria extension — per §7 of the AC document, new criteria
must land in `ACCEPTANCE_CRITERIA.md`, `MODULE_SPEC.md`, and
`tests/acceptance/test_criteria_registry.py` **in the same change** or the registry
consistency tests fail.

### R2-T01 — Dynamics & FRF chain (damping, forced response, FRF synthesis, FRF correlation)

- **Status: DONE.** The in-flight branch was merged at `acda625` (no second dynamics
  implementation on the branch) and the spec-first deliverable landed: `MODULE_SPEC.md`
  §7 (module M6, anchors MS-7.1..7.5), `ACCEPTANCE_CRITERIA.md` §7, and registry entries
  AC-DYN-001..005, all `implemented` and tagged in
  `tests/acceptance/test_dynamics.py`. `frac`/`fdac` are re-exported from
  `openfemlab.correlation`. Measured margins are recorded in the R2-T01 entry of
  [`PROGRESS.md`](PROGRESS.md); the proposed criteria below were adopted as written apart
  from AC-DYN-005, whose dataset-58 formatter lives in the test because UFF *writing* is
  R2-T05 scope. The FRF block in the `CorrelationReport` schema is **now closed too**
  (A41): `correlation/frf.py` drives the same `frac`/`fdac` kernels into an
  `FRFCorrelation` block that the report publishes under `frf`, `schema_version` is
  bumped to `1.1`, and `tests/test_frf_correlation.py` (25 tests) gates it. Still open
  and handed on to the exit-bar work of §5: only the CLI FRF demo.
- **Priority:** 1 (P0) · **Gaps:** [GAP-04, GAP-05](../docs/SOTA_GAP_ANALYSIS.md) (§5.3)
- **Why first:** the largest missing FEMtools pillar. Test campaigns deliver FRFs; today
  only pre-extracted mode tables can be correlated. UFF-58 FRF *import* already exists
  (A12), so measured FRFs can enter the platform but nothing can be synthesized against
  them.
- **Scope:**
  - Damping models on `Model`/spec: Rayleigh (`αM + βK`), modal damping ratios,
    structural (hysteretic) damping; proportional-damping fast path and complex-mode
    path for the general case.
  - Forced harmonic response and FRF synthesis: modal superposition
    `H_jk(ω) = Σ_i φ_ji φ_ki / (ω_i² − ω² + 2iζ_i ω_i ω)` with residual/static
    correction terms, plus a direct-inversion reference
    `H(ω) = (K + iωC − ω²M)⁻¹` for verification.
  - FRF correlation metrics: FRAC and FDAC over synthesized-vs-measured FRF sets,
    reported through the existing `CorrelationReport` pipeline.
  - Defer the FRF **updating residual** to Round 3 (GAP-05 is marked R2/R3; the residual
    needs FRF sensitivities and is not a Round 2 gate).
- **Integration constraint:** harvest and land the in-flight
  `cursor/dynamics-damping-frf-9500` work first; new code on the integration branch must
  not fork a second dynamics implementation (GAP-01 lesson).
- **Acceptance links:** no AC-DYN-* exist yet — add a Dynamics module section to
  `MODULE_SPEC.md` and register new criteria (proposed): AC-DYN-001 1-DOF/2-DOF damped
  FRF vs closed form (`oracle`, rel. err ≤ 1e-8 off resonance); AC-DYN-002 modal
  superposition with full basis matches direct inversion (`property`, rel. err ≤ 1e-8);
  AC-DYN-003 proportional-damping complex modes collapse to real modes (`property`);
  AC-DYN-004 FRAC/FDAC self-identity = 1 and scaling invariance (`property`, mirrors
  [AC-CORR-001/002](../docs/ACCEPTANCE_CRITERIA.md)); AC-DYN-005 synthesized FRF
  round-trips through the UFF-58 reader (`contract`, ties to `io/uff.py`).
- **Dependencies:** none on other R2 tasks (existing 1D elements suffice for the fixture
  set). FRAC/FDAC builds on `correlation/report.py`.

### R2-T02 — 3D continuum element library (QUAD4 / TET4 / HEX8)

- **Priority:** 2 (P0) · **Gap:** [GAP-02](../docs/SOTA_GAP_ANALYSIS.md) (§4)
- **Why second:** every `ElementType` beyond 1D is declared but has no formulation, so no
  imported industrial mesh can be *re-analyzed* internally — it can only be correlated.
  This blocks the value of both the BDF reader (A18) and the meshio bridge (R2-T05).
- **Status: PARTIAL** — the first slice is **done and on the trunk** (merged from
  `cursor/quad4-plane-stress-element-b99c` by A37; suite **559 passed**, Ruff clean after
  the merge). `Quad4Element` (bilinear isoparametric, plane stress/strain, 1–4 point Gauss
  rule, consistent + row-sum lumped mass, strain/stress recovery) is in
  `core/elements.py`, `quad_plate_mesh` / `MeshBuilder.add_quad4` are in `mesh/simple.py`,
  and `tests/test_quad4.py` carries 61 tests — MacNeal-Harder patch exact to machine
  precision, exactly three zero-energy modes under full integration, axial spectrum
  matching an equivalent bar mesh to 2.4e-13, quadratic h-convergence. TET4, HEX8, the 3D
  beam, the shell facet, the solid/shell BDF cards and the AC-ELEM-* rows remain open, so
  the task does **not** close. See the R2-T02 and A37 entries in
  [`PROGRESS.md`](PROGRESS.md).
- **Scope:**
  - ~~QUAD4 (plane stress/strain first; shell via flat facet + drilling treatment
    documented as a limitation)~~ **landed**; the flat-facet shell with drilling DOFs is
    *not* covered and stays open. Remaining isoparametric formulations with consistent +
    lumped mass in `core/elements.py`: TET4, HEX8 (with standard hourglass/locking
    notes), plus a 3D two-node beam (extends the planar Euler–Bernoulli one) to make
    frame models importable.
  - `mesh/simple.py` generators for structured quad/hex blocks (needed for convergence
    fixtures) and neutral-model → assembly wiring for the new blocks — the structured
    **quad** generator is landed; hex remains, as does the `NeutralModel` → `Model`
    conversion that turns an imported block into bound elements.
  - Nastran card coverage follows the element set: `CQUAD4`/`CTETRA`/`CHEXA`/`CBAR`,
    `PSHELL`/`PSOLID` in `io/nastran.py` (remaining GAP-03 scope, coordinated with
    R2-T05).
- **Acceptance links:** existing modal gates apply unchanged —
  [AC-MODAL-001](../docs/ACCEPTANCE_CRITERIA.md) (analytic accuracy; extend the fixture
  set with a mesh-converged plate/solid oracle at ≤ 0.5 % like the beam gate),
  AC-MODAL-003 (mass-orthonormality), AC-MODAL-004 (rigid-body count = 6 for free-free
  3D bodies), AC-MODAL-007 (effective-mass completeness per direction). Register new
  element criteria (proposed): AC-ELEM-001 patch test exact to machine precision
  (`oracle`); AC-ELEM-002 rigid-body-motion invariance / zero strain energy
  (`property`); AC-ELEM-003 quadratic h-convergence on the plate/solid oracle
  (`property`, mirrors the existing beam convergence check). **None of the three is
  registered yet.** `tests/test_quad4.py` already produces the evidence for all three on
  QUAD4 but carries no `@criterion` tags, so the registry stays consistent; the rows and
  the tags should land together with the TET4/HEX8 slice, in the same change as the
  `ACCEPTANCE_CRITERIA.md` and `MODULE_SPEC.md` edits the spec-first rule requires.
- **Dependencies:** none. Unblocks R2-T05's re-analysis path and future GAP-13 scale
  work (real 3D meshes are what push past 1k DOF).

### R2-T03 — SEREP / Guyan reduction, TAM pseudo-orthogonality, mode-shape expansion

- **Priority:** 3 (P1 — **blocks Round-2 sign-off** via AC-CORR-006) ·
  **Gap:** [GAP-08](../docs/SOTA_GAP_ANALYSIS.md) (§5.5, R2 slice)
- **Why third:** the highest-ranked *gate-blocking* criterion. Correlation currently
  assumes the test DOF set is a labeled subset of FE DOFs; reduction/expansion is the
  bridge that makes correlation and updating honest on real sensor sets, and it is a
  prerequisite for Round 3 pretest (GAP-07) and TAM work.
- **Scope:**
  - `reduction/` (or `correlation/reduction.py`): Guyan (static) reduction — the solver
    already has the kernel in `_MasslessCondensation` — IRS as an incremental
    improvement, and SEREP (`T = Φ_full (Φ_sensor)⁺`) with explicit master-DOF /
    sensor-set selection reusing `workflow/sensors.py::SensorMap`.
  - Mode-shape **expansion** from sensor DOFs to full FE DOFs (SEREP back-projection),
    feeding correlation and the updating shape residual.
  - TAM pseudo-orthogonality: `Φ_testᵀ M_TAM Φ_test` through the existing weighted-MAC /
    orthogonality machinery in `correlation/mac.py` (which already accepts a reduced
    mass matrix).
  - Craig–Bampton CMS stays in Round 3 (differentiation item, not a Round 2 gate).
- **Acceptance links:** [AC-CORR-006](../docs/ACCEPTANCE_CRITERIA.md) (`twin`, P1):
  noise-free synthetic test data at sensor DOFs → SEREP expansion reproduces full-space
  shapes with **MAC ≥ 0.999** and reduced-space pairing equals expanded-space pairing.
  Spec anchor [MS-2.1](../docs/MODULE_SPEC.md). Register a TAM addition (proposed):
  AC-CORR-009 pseudo-orthogonality of exact test modes through the TAM mass —
  diag ≥ 0.99, off-diag ≤ 0.10 (`twin`).
- **Dependencies:** none hard; benefits from R2-T02 (a 3D fixture makes the
  reduced-vs-expanded twin test representative, but the 10-DOF chain suffices for the
  gate).

### R2-T04 — Bayesian MAP updating with posterior covariance

- **Priority:** 4 (P1 — **blocks Round-2 sign-off** via AC-UPD-006a/b) ·
  **Gaps:** [GAP-11](../docs/SOTA_GAP_ANALYSIS.md) (R2 slice), MS-3.5
- **Why fourth:** the second gate-blocker, and the main opportunity to *exceed* FEMtools
  rather than chase it (SOTA §3.2). Deliberately scoped to the deterministic MAP
  formulation of [MS-3.5](../docs/MODULE_SPEC.md); sampling (TMCMC), Monte Carlo, and
  DOE remain Round 3 (GAP-11 proper).
- **Scope:**
  - Extend `updating/updater.py` (or a sibling `updating/bayesian.py` sharing the LM
    machinery) with the Gaussian-prior MAP step
    `(Jᵀ C_e⁻¹ J + C_p⁻¹) Δθ = Jᵀ C_e⁻¹ r + C_p⁻¹ (θ_0 − θ)`, measurement-noise and
    prior covariance inputs on `UpdatingOptions`, and the Laplace posterior covariance
    `C_post = (Jᵀ C_e⁻¹ J + C_p⁻¹)⁻¹` with per-parameter σ_post in `UpdatingResult`
    and the CLI/report output (the AC-WORK-005 report schema already reserves a
    σ_post column).
  - Reuses the analytic sensitivity stack (Fox–Kapoor + MAC rows from A04/A10)
    unchanged — this task is estimator plumbing, not new numerics.
- **Acceptance links:** [AC-UPD-006a](../docs/ACCEPTANCE_CRITERIA.md) (`property`, P1):
  as `C_p⁻¹ → 0` the MAP step matches unregularized Gauss–Newton to rel. diff ≤ 1e-8;
  [AC-UPD-006b](../docs/ACCEPTANCE_CRITERIA.md) (`property`, P1): σ_post ≤ σ_prior
  componentwise, tight prior keeps θ* within 3σ_prior of θ_0. Spec anchor
  [MS-3.5](../docs/MODULE_SPEC.md).
- **Dependencies:** none. Pairs naturally with R2-T06's collinearity screen (a singular
  Jᵀ J the MAP prior regularizes is exactly what MS-3.6 should flag).

### R2-T05 — meshio bridge and IO completion

- **Priority:** 5 (P0 gap area; remaining slice) ·
  **Gap:** [GAP-03](../docs/SOTA_GAP_ANALYSIS.md) (§5.2, remainder after A12/A18)
- **Why fifth:** highest leverage-per-effort in IO — one optional dependency imports
  dozens of mesh formats (Abaqus, Gmsh, VTK, Exodus, …) — but its re-analysis value
  multiplies only once R2-T02 elements exist, so it trails the element task.
- **Scope:**
  - `io/meshio_bridge.py`: bidirectional `meshio.Mesh` ↔ `NeutralModel` conversion
    (points → node arrays, cell blocks → `ElementType` blocks with an explicit,
    documented mapping table; unmapped cell types skipped with a diagnostic, mirroring
    the BDF reader's policy).
  - Optional-dependency seam per the ARCHITECTURE P7 policy (import guarded, clear
    `MissingDependencyError`, `[io]` extra grows `meshio`), matching how the `[cli]`
    extra degrades.
  - UNV 2411/2412 (nodes/elements) in `io/uff.py` so a *complete* UFF test model —
    geometry + modes (55) + FRFs (58) — round-trips; this also gives correlation a real
    test-geometry source for the GAP-09 nearest-node mapping.
- **Acceptance links:** no AC rows exist for IO — register (proposed): AC-IO-001
  meshio round-trip `NeutralModel → meshio → NeutralModel` preserves nodes, blocks,
  ids (`contract`, exact); AC-IO-002 imported Gmsh/Abaqus fixture assembles and solves
  through the modal pipeline with AC-MODAL-003/006 holding (`contract`, needs R2-T02
  for 3D cells); AC-IO-003 UNV 2411/2412 + 55 fixture feeds
  `correlate_modal_data` end to end (`contract`).
- **Dependencies:** R2-T02 for solid/shell re-analysis (bridge itself can land first,
  restricted to already-supported element types).

---

## 3. Supporting backlog (remaining Round 2 items)

| ID | Pri | Task | Gaps / gates | Notes |
|---|---|---|---|---|
| R2-T06 | 6 (contains a **P0** criterion) | Updating depth completion: MS-3.6 collinearity screen with QR-pivoting subset selection ([AC-UPD-007](../docs/ACCEPTANCE_CRITERIA.md), P0, `twin`: duplicated parameter detected at cosine > 0.99, one frozen, recovery gates still met); wire the analytic MAC-row Jacobian into the updater's shape-residual path (A04 flagged this as a cheap win — FD fallback currently used whenever shapes are present); model-level parameter target resolver (`material.<id>.<attr>`) with assembled per-element dK/dp providers | [GAP-10](../docs/SOTA_GAP_ANALYSIS.md), AC-UPD-007, MS-3.1/3.3/3.6 | AC-UPD-007 is the only *P0* criterion still unimplemented — schedule it no later than R2-T03/T04. |
| R2-T07 | 7 | Optimization backend: replace `optimization.solve` `NotImplementedError` with a scipy SLSQP/trust-constr backend using the sensitivity kernel for gradients and MAC-based mode tracking | [GAP-12](../docs/SOTA_GAP_ANALYSIS.md), [AC-OPT-001..003](../docs/ACCEPTANCE_CRITERIA.md) (P0), AC-OPT-004 (P1), MS-5 | Coordinate with the in-flight `optimization/{backends,gradients,problem,responses,variables}.py` on `cursor/dynamics-damping-frf-9500` — land that branch, don't fork. |
| R2-T08 | 8 | R1-O2 reconciliation: diff `cursor/r1o2-correlation-updating-e393` against the landed correlation/updating packages; harvest superior pieces (per-DOF MSF-scaled shape residuals, log-space parameter transform, frequency-window pairing acceptance) and delete the rest | GAP-01 hygiene | Already in progress on `cursor/reconcile-r1o2-correlation-updating-64c5`; merge through the integration branch, not around it. |
| R2-T09 | 9 | Round 2 exit hardening: CI job runs `import openfemlab` + full suite + Ruff + registry consistency on every push; registry statuses advanced `specified → implemented → verified` for every criterion a Round 2 task closes | Round 1 exit-bar carryover, AC §1.5 | The Round 1 bar ("suite must collect and pass before Round 2 refactors begin") is now met — 192 passed — and must not regress. |

---

## 4. Sequencing and parallelization

Respecting the Round 2 rule from the audit (**seam changes land atomically with their
consumers** — `SOTA_GAP_ANALYSIS.md` Appendix A):

- **Wave 1 (parallel, disjoint files):** R2-T01 (dynamics — after landing the in-flight
  branch; **done**), R2-T02 (elements), R2-T04 (Bayesian). These touch `dynamics/`-new,
  `core/elements.py`, `updating/` respectively, with no shared seams.
- **Wave 2:** R2-T03 (SEREP — consumes `SensorMap`, `correlation/mac.py` weighting),
  R2-T05 (meshio + UNV 2411/2412 — consumes R2-T02 element types), R2-T06 (updating
  depth — consumes R2-T02's assembled dK/dp), R2-T07 (optimization).
- **Wave 3:** R2-T08 (reconciliation) and R2-T09 (exit hardening) close the round.
- **Spec-first rule:** any task introducing new AC IDs (T01, T02, T05, T03's AC-CORR-009)
  edits `ACCEPTANCE_CRITERIA.md` + `MODULE_SPEC.md` + the registry in its first commit
  so the registry tests pin the target before implementation starts.

## 5. Round 2 exit bar

Round 2 is done when, on the integration branch in CI:

1. Every **P0** criterion in the registry is `verified`, including the currently
   unimplemented [AC-UPD-007](../docs/ACCEPTANCE_CRITERIA.md).
2. Every **P1** criterion is `verified` (AC §1.2: P1 blocks Round-2 sign-off) — in
   particular AC-CORR-006 (SEREP), AC-UPD-006a/b (Bayesian), AC-MODAL-008,
   AC-WORK-003, AC-UPD-008, AC-OPT-004.
3. The newly registered dynamics / element / IO criteria (T01/T02/T05 proposals above)
   are at least `implemented`.
4. A measured FRF (UFF-58) can be compared against a synthesized FRF from a damped model
   via FRAC/FDAC through the CLI, and a meshio- or BDF-imported 3D mesh can be
   re-analyzed internally — the two headline workflow demos for the round. The library
   half of the FRF demo is done (A41): `frf_correlation` publishes an `FRFCorrelation`
   block through `CorrelationReport` at `schema_version` `1.1`, so what the CLI still
   needs is a command surface over it, not a metric.
5. Full suite + Ruff + registry consistency green; no duplicate implementations of any
   numeric kernel (GAP-01 stays closed).

## 6. Top 3 priorities (summary)

1. ~~**R2-T01 — Dynamics/FRF chain** (GAP-04/05, P0)~~ — **done**: merged at `acda625`,
   AC-DYN-001..005 registered and `implemented`. The live top three are now T02, T03 and
   T04.
2. **R2-T02 — 3D continuum elements** (GAP-02, P0): QUAD4/TET4/HEX8 (+ 3D beam) so
   imported industrial meshes can be re-analyzed, unblocking the meshio bridge
   (R2-T05). QUAD4 is landed; TET4, HEX8 and the 3D beam remain.
3. **R2-T03 — SEREP/TAM reduction & expansion** (GAP-08): the top Round-2 sign-off
   blocker via AC-CORR-006, with R2-T04 Bayesian MAP (AC-UPD-006a/b) as the tied
   gate-blocker immediately behind it.
