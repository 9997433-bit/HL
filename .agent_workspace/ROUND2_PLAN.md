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

## 0. Status snapshot — mid-round (A83, 2026-08-26, integration tip after the AC-UPD-006 and spatial-beam merges)

Verified at that tip from a private clone (`PYTHONPATH` pinned): full suite
**1089 passed, 0 failed**, `ruff check .` clean, on Python 3.12.3 / NumPy 2.5.2 /
SciPy 1.18.1. Registry: **44 criteria — 41 `implemented`, 3 `specified`, 0 `verified`**
once the A59 element slice's three M7 rows and the AC-UPD-006a/b pair joined the
trunk's AC-CORR-008/009. Every **P0** row is now `implemented`; the three still
`specified` are all P1 (AC-MODAL-008, AC-UPD-008, AC-WORK-003). Nothing can reach
`verified` until R2-T09 stands up the CI job.

| Task | Status |
|---|---|
| R2-T01 dynamics/FRF | **COMPLETE** — engine (`acda625`), AC-DYN-001..005 `implemented`, report `frf` block at schema 1.1 (A41), `openfemlab correlate-frf` CLI (A54). No open work. |
| R2-T02 3D elements | **PARTIAL** — QUAD4 (A37), TET4 (A46) and HEX8 (A59, merged by A79) are all on the integration branch with mesh generators and 203 tests, AC-ELEM-001..003 are registered as module M7 over all three (+24 acceptance cases), and the spatial beam `BeamElement3D` landed with 42 tests (A82). Open: flat-facet shell, `NeutralModel` → `Model` conversion, solid/shell BDF cards (`CBAR` included). |
| R2-T03 reduction/expansion | **ACCEPTANCE-COMPLETE** — engine (A36, `correlation/reduction.py`) with the AC-CORR-006 gate `implemented` (A43), and AC-CORR-009 plus the `SensorMap.signs` wiring landed (A58). Open: sparse inputs, `verified` flip. |
| R2-T04 Bayesian MAP | **ACCEPTANCE-COMPLETE** — estimator (A49, `updating/bayesian.py`, 36 tests) plus the AC-UPD-006a/b tagging, the registry flip and the Laplace σ_post in the `CorrectionReport` (A57, on the trunk since the `ac-upd-006-registration-6615` merge). Open: σ_post in the CLI `update` document, which is outside the acceptance slice. |
| R2-T05 meshio & IO | **NOT STARTED** — the only core track with no commit. |
| R2-T06 updating depth | P0 slice closed (AC-UPD-007, A44); P1 depth (MAC-row Jacobian wiring, model-level resolver, per-element dK/dp) open. |
| R2-T07 optimization | **COMPLETE for sizing** — A27 backend + A40 harvest; AC-OPT-001..004 `implemented`. Shape variables still FD. |
| R2-T08 R1-O2 reconciliation | Pending a close-as-superseded decision (A40/A14); no merge wanted. |
| R2-T09 exit hardening | **NOT STARTED** — no CI job, so nothing can move `implemented → verified`. |

---

## 1. Starting state — what is already closed or in flight

The plan is *targeted*: it excludes work Round 1 backfills already landed. Delta against
the gap register at audit time:

| Gap | Audit status | Status entering Round 2 |
|---|---|---|
| GAP-01 integration split-brain | P0, suite not collecting | **Largely closed.** `ModalResult` unified (commit `508813e`), `modal/eigen.py` is a thin adapter over `solver/modal.py` (A08), full suite green at **192 passed** (A22). Residual: enforce the "seams land atomically with consumers" rule and keep CI green. |
| GAP-03 industrial IO | P0, absent | **Partial.** UFF datasets 55/58 reader (A12), minimal Nastran BDF `GRID`/`CROD`/`MAT1` (A18). Remaining: UNV 2411/2412, broader BDF cards, **meshio bridge (R2-T05)**, UFF writing, OP2. |
| GAP-14 CLI stubs | P2, stubbed | **Closed for R2.** `modal`/`correlate`/`update` landed with model-spec format, gates, JSON/YAML documents on clean stdout (A07/A16/A22). |
| GAP-10 updating depth | P1, absent | **Partial.** Dotted-path parameter targeting in the CLI spec layer (A07), affine `ScalingModel` dK/dθ (A04), vectorized Fox–Kapoor + MAC sensitivities (A04/A10). Remaining: model-level resolver, assembled per-element dK/dp, analytic MAC-row Jacobian wiring → R2-T06. The MS-3.6 collinearity screen is done: `workflow/selection.py` plus the AC-UPD-007 acceptance tests (A44). |
| GAP-09 node mapping | P1, absent | **Partial.** Label-based DOF alignment (`correlation/align.py`, `workflow/sensors.py`). Remaining: geometry-based nearest-node mapping → folded into R2-T05/T06 scope notes. |
| GAP-04/05 dynamics & FRF | P0/P1, absent | **Closed by R2-T01.** `cursor/dynamics-damping-frf-9500` merged at `acda625`; AC-DYN-001..005 registered and `implemented`. GAP-05's FRF *updating residual* stays deferred to Round 3 as planned below. |
| GAP-02 3D elements | P0, absent | **Partial.** QUAD4 plane stress/strain landed with `mesh.simple.quad_plate_mesh` and 61 tests (R2-T02 first slice, merged from `cursor/quad4-plane-stress-element-b99c`); TET4 landed with `mesh.simple.tet_block_mesh` and 66 tests (A46); HEX8 landed with `mesh.simple.hex_block_mesh`, 76 tests and the AC-ELEM-001..003 registration over all three elements (A59); the CBAR-like `BeamElement3D` landed with `MeshBuilder.add_beam3d` and 42 tests (A82). Remaining: the flat-facet shell, the solid/shell BDF cards → R2-T02 remainder. |
| GAP-08 reduction/expansion | P1, absent | **Partial.** `correlation/reduction.py` landed (A36): Guyan/IRS/SEREP bases, `expand_shapes`, `tam_mass`, 25 tests; the AC-CORR-006 gate is `implemented` via the 19-case acceptance batch (A43), and AC-CORR-009 plus the `SensorMap.signs` wiring landed with A58. Remaining: sparse inputs, the `verified` flip → R2-T03 remainder. |
| GAP-11 Bayesian/UQ | P1, absent | **Closed for MAP by R2-T04, acceptance included.** The MS-3.5 estimator landed in `updating/bayesian.py` with Gaussian prior, noise covariance and Laplace posterior σ_post (A49, 36 tests); AC-UPD-006a/b are registered and `implemented` behind an eight-test gate on the ten-DOF twin, and the `CorrectionReport` σ_post column now carries the posterior (A57, merged to the trunk by A83). Remaining: σ_post in the CLI `update` document. Sampling (TMCMC/MC/DOE) stays Round 3 → R2-T04. |
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

- **Status: COMPLETE.** The in-flight branch was merged at `acda625` (no second dynamics
  implementation on the branch) and the spec-first deliverable landed: `MODULE_SPEC.md`
  §7 (module M6, anchors MS-7.1..7.5), `ACCEPTANCE_CRITERIA.md` §7, and registry entries
  AC-DYN-001..005, all `implemented` and tagged in
  `tests/acceptance/test_dynamics.py`. `frac`/`fdac` are re-exported from
  `openfemlab.correlation`. Measured margins are recorded in the R2-T01 entry of
  [`PROGRESS.md`](PROGRESS.md); the proposed criteria below were adopted as written apart
  from AC-DYN-005, whose dataset-58 formatter lives in `tests/_uff58.py` because UFF
  *writing* is R2-T05 scope. The FRF block in the `CorrelationReport` schema is **now
  closed too** (A41): `correlation/frf.py` drives the same `frac`/`fdac` kernels into an
  `FRFCorrelation` block that the report publishes under `frf`, `schema_version` is
  bumped to `1.1`, and `tests/test_frf_correlation.py` (25 tests) gates it. **The last
  exit item, the CLI FRF demo, is closed as well** (A54): `openfemlab correlate-frf`
  (`cli/commands/correlate_frf.py`) reads a measured UFF-58 column or its JSON/YAML
  equivalent, synthesizes the same channels from a damped model spec on the measured
  frequency line, publishes the `frf` block at schema `1.1`, and gates it with
  `--require-frac` / `--require-fdac`; `tests/test_cli_frf.py` (16 tests) covers it, the
  headline demo included. **R2-T01 carries no open work.**
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

### R2-T02 — 3D element library (QUAD4 / TET4 / HEX8 / spatial beam)

- **Priority:** 2 (P0) · **Gap:** [GAP-02](../docs/SOTA_GAP_ANALYSIS.md) (§4)
- **Why second:** every `ElementType` beyond 1D is declared but has no formulation, so no
  imported industrial mesh can be *re-analyzed* internally — it can only be correlated.
  This blocks the value of both the BDF reader (A18) and the meshio bridge (R2-T05).
- **Status: PARTIAL** — the three continuum slices and the spatial beam are **done**,
  and the element criteria are registered.
  *QUAD4* (merged from `cursor/quad4-plane-stress-element-b99c` by A37; suite **559
  passed**, Ruff clean after the merge): bilinear isoparametric, plane stress/strain,
  1–4 point Gauss rule, consistent + row-sum lumped mass, strain/stress recovery in
  `core/elements.py`, with `quad_plate_mesh` / `MeshBuilder.add_quad4` in `mesh/simple.py`
  and 61 tests in `tests/test_quad4.py` — MacNeal-Harder patch exact to machine precision,
  exactly three zero-energy modes under full integration, axial spectrum matching an
  equivalent bar mesh to 2.4e-13, quadratic h-convergence.
  *TET4* (A46, `cursor/tet4-solid-element-08d1`; suite **781 passed** at the merged tip
  `e4bd20c`, Ruff clean):
  `Tet4Element` constant-strain tetrahedron plus `solid_constitutive_matrix`,
  `tet_block_mesh` / `MeshBuilder.add_tet4`, and 66 tests in `tests/test_tet4.py` —
  a 162-element distorted 3D patch exact to 2.8e-16, exactly six zero-energy modes,
  quadratic axial h-convergence from above, and the element's bending locking pinned as
  a known limitation.
  *HEX8* (A59, `cursor/hex8-brick-ac-elem-d0b7`, **merged into the integration branch by
  A79**; suite **1033 passed** at the merged tip, Ruff clean):
  `Hex8Element` trilinear brick plus `gauss_legendre_3d`, `hex_block_mesh` /
  `MeshBuilder.add_hex8` (sharing the structured-grid helper with `tet_block_mesh`, so
  both number their nodes alike), and 76 tests in `tests/test_hex8.py` — a 27-element
  distorted patch exact to 2.8e-16 *at four sample points per element*, six zero-energy
  modes under full integration and eighteen under reduced, volume and mass row sums
  quadrature-exact on a distorted brick, and the bending comparison that motivates the
  element: +8.0 % against Euler–Bernoulli at 2475 DOF where TET4 on the same grid is
  +25 %.
  *Spatial beam* (A82, `cursor/beam3d-cbar-element-c9a7`; suite **1089 passed** at the
  merged tip, Ruff clean): `BeamElement3D`, the CBAR-like two-node frame member with six DOFs per node —
  axial extension, St Venant torsion and uncoupled bending in the two principal planes,
  built from the same Hermitian 4x4 blocks the planar beam uses, so the
  `(u, v, theta_z)` sub-block of both local matrices reproduces `BeamElement2D` to
  1e-14 and there is no second beam kernel (GAP-01 rule). The local frame follows the
  Nastran CBAR orientation-vector convention, with `MeshBuilder.add_beam3d` as the mesh
  seam and 42 tests in `tests/test_beam3d.py` — closed-form cantilever statics exact to
  1e-12 in both bending planes (a cubic element is exact for an end load) plus axial and
  torsional compliance, the cantilever bending spectrum in both planes and the fixed-free
  shaft torsion formula to 5e-3, planar-beam frequencies recovered to 1e-8 by the spatial
  model, rotation invariance of the assembled spectrum, and six free-free rigid-body
  modes. Torsional rotary inertia `rho (Iy + Iz) L` is carried (the twist DOFs would be
  massless otherwise); bending rotary inertia, shear deformation, warping and
  shear-centre offsets are documented limitations.
  **The AC-ELEM-* rows are now registered** (see the acceptance-links bullet below), so
  what remains open is the shell facet, the solid/shell BDF cards and the neutral-model
  conversion; the task does **not** close. See the R2-T02, A37, A46, A59 and A82 entries
  in [`PROGRESS.md`](PROGRESS.md).
- **Scope:**
  - ~~QUAD4 (plane stress/strain first; shell via flat facet + drilling treatment
    documented as a limitation)~~ **landed**; the flat-facet shell with drilling DOFs is
    *not* covered and stays open. ~~TET4~~ **landed** as the constant-strain tetrahedron
    with consistent + row-sum lumped mass. ~~HEX8 (with standard hourglass/locking
    notes)~~ **landed** as the trilinear brick, hourglass count and shear locking both
    pinned by tests. ~~a 3D two-node beam (extends the planar Euler–Bernoulli one) to
    make frame models importable~~ **landed** as `BeamElement3D`. No formulation is
    outstanding in `core/elements.py` except the flat-facet shell.
  - `mesh/simple.py` generators for structured quad/hex blocks (needed for convergence
    fixtures) and neutral-model → assembly wiring for the new blocks — the structured
    **quad**, **tet** (Kuhn-subdivided box) and **hex** generators are all landed; what
    remains is the `NeutralModel` → `Model` conversion that turns an imported block into
    bound elements.
  - Nastran card coverage follows the element set: `CQUAD4`/`CTETRA`/`CHEXA`/`CBAR`,
    `PSHELL`/`PSOLID` in `io/nastran.py` (remaining GAP-03 scope, coordinated with
    R2-T05).
- **Acceptance links:** existing modal gates apply unchanged —
  [AC-MODAL-001](../docs/ACCEPTANCE_CRITERIA.md) (analytic accuracy; extend the fixture
  set with a mesh-converged plate/solid oracle at ≤ 0.5 % like the beam gate),
  AC-MODAL-003 (mass-orthonormality), AC-MODAL-004 (rigid-body count = 6 for free-free
  3D bodies), AC-MODAL-007 (effective-mass completeness per direction).
  **The three proposed element criteria are now registered and `implemented`** (A59),
  as module **M7** / family `ELEM` with spec anchors MS-8.3 and MS-8.4: AC-ELEM-001
  patch test exact to machine precision (P0, `oracle`); AC-ELEM-002 rigid-body-motion
  invariance plus the exact zero-energy mode count (P0, `property`); AC-ELEM-003
  quadratic h-convergence against the continuum bar oracle (P1, `property`). They
  landed atomically with `ACCEPTANCE_CRITERIA.md` §8 (enforcement renumbered to §9),
  `MODULE_SPEC.md` §8 and the registry, which is what the spec-first rule requires, and
  the pinned inventory moved **40 → 43**. `tests/acceptance/test_elements.py` gates every
  criterion on **all three** formulations through one parametrized case table, so the
  QUAD4 and TET4 evidence is claimed by the registry rather than left implicit in the
  developer suites. The spatial beam is **not** in that case table: AC-ELEM-001's
  constant-strain patch test has no beam analogue and AC-ELEM-003's continuum bar oracle
  is not the right convergence target for a cubic element, so only AC-ELEM-002
  (rigid-body invariance, which `tests/test_beam3d.py` checks in global axes) is a
  candidate — folding it in is a follow-up that needs no new criterion ID.
- **Dependencies:** none. Unblocks R2-T05's re-analysis path and future GAP-13 scale
  work (real 3D meshes are what push past 1k DOF).

### R2-T03 — SEREP / Guyan reduction, TAM pseudo-orthogonality, mode-shape expansion

- **Status: PARTIAL — engine and gate are on the trunk.**
  *Engine* (A36): `correlation/reduction.py` carries `ReductionBasis` with
  `reduce_matrix` / `reduce_shapes` / `expand`, built by `guyan_reduction`,
  `irs_reduction` and `serep_basis`, plus `expand_shapes` (the MS-2.1
  back-projection) and `tam_mass` feeding the existing weighted-MAC machinery —
  no second metric kernel (GAP-01 rule). 25 closed-form tests in
  `tests/test_reduction.py`. *Gate* (A43): **AC-CORR-006 is `implemented`** — the
  19-case acceptance batch in `tests/acceptance/test_correlation.py` checks both
  halves (SEREP reconstruction MAC ≥ 0.999, reduced-space pairing = expanded-space
  pairing) on the 10-DOF chain and a 36-DOF cantilever twin, and additionally pins
  where each half stops holding under noise. **Remaining to close the task:**
  register AC-CORR-009 (engine and test exist; needs the spec-first three-file
  commit and moves the pinned 40-criterion inventory), fold `SensorMap.signs`
  into the basis (`from_sensor_map`), stop densifying sparse inputs, and move
  AC-CORR-006 `implemented → verified` once CI runs it (R2-T09).
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

- **Status: acceptance-complete — AC-UPD-006a/b are `implemented` (A57).**
  `tests/acceptance/test_updating.py` carries eight tagged tests on the M3 suite's own
  ten-DOF chain, run as the AC-UPD-003 `stiffness` twin, and both registry rows left
  `specified` in the same change. `CorrectionWorkflow` now accepts `prior` /
  `noise_covariance`; either switches S4 to `BayesianUpdater` and fills the report's
  reserved σ_post column with the Laplace posterior instead of the least-squares
  stand-in. Suite **888 passed** on A57's own tree, and **1089 passed** with
  `ruff check .` clean at the trunk tip once the branch landed (A83). Both criteria
  still need a CI
  run to reach `verified`, which is the R2 sign-off condition. **Left open:** σ_post in
  the CLI `update` document (needs a prior/noise block in the update spec schema), and
  whether the prior should also be expressible in *physical* rather than design space.
- **Estimator history (A49).**
  `src/openfemlab/updating/bayesian.py` carries `GaussianPrior` (scalar /
  per-parameter / full `C_p`, `from_std`, `uninformative`, optional prior mean),
  `map_step`, `posterior_covariance`, a `PosteriorEstimate` reporting per-parameter
  σ_post, and `BayesianUpdater` / `update_model_bayesian`. The estimator drives the
  *existing* LM loop rather than forking it: `ModelUpdater` grew two overridable hooks
  (`normal_equations`, `penalty`) and `BayesianUpdater` swaps in
  `(Jᵀ C_ε⁻¹ J + C_p⁻¹) Δθ = −[Jᵀ C_ε⁻¹ r + C_p⁻¹ (θ − θ₀)]`, so mode re-pairing, bounds
  projection and the sensitivity stack stay shared (GAP-01 rule). `tests/test_bayesian_
  updating.py` pins both MS-3.5 limits on the 2-DOF grounded chain in 35 tests — the GN
  limit as `C_p⁻¹ → 0` (rel. diff ≤ 1e-8 at scale 1e-12, and end to end against
  `update_model`) and posterior contraction with a tight prior holding θ* inside
  3σ_prior of θ₀. Suite **709 passed**, `ruff check .` clean.
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
| R2-T06 | 6 | Updating depth completion: the MS-3.6 collinearity screen with norm-ranked subset selection is **done** ([AC-UPD-007](../docs/ACCEPTANCE_CRITERIA.md), P0, `twin`: duplicated parameter detected at cosine > 0.99, one frozen, recovery gates still met — `workflow/selection.py`, tagged by A44); wire the analytic MAC-row Jacobian into the updater's shape-residual path (A04 flagged this as a cheap win — FD fallback currently used whenever shapes are present); model-level parameter target resolver (`material.<id>.<attr>`) with assembled per-element dK/dp providers | [GAP-10](../docs/SOTA_GAP_ANALYSIS.md), AC-UPD-007, MS-3.1/3.3/3.6 | What is left is P1 depth work; the P0 slice closed with the AC-UPD-007 tagging. |
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

1. Every **P0** criterion in the registry is `verified`, including
   [AC-UPD-007](../docs/ACCEPTANCE_CRITERIA.md) and AC-WORK-001/002/004/005, which
   reached `implemented` once the acceptance suites claimed them (A44).
2. Every **P1** criterion is `verified` (AC §1.2: P1 blocks Round-2 sign-off) — in
   particular AC-CORR-006 (SEREP), AC-UPD-006a/b (Bayesian), AC-MODAL-008,
   AC-WORK-003, AC-UPD-008, AC-OPT-004.
3. The newly registered dynamics / element / IO criteria (T01/T02/T05 proposals above)
   are at least `implemented` — done on the integration branch for AC-DYN-001..005 (T01)
   and, since the A79 merge, AC-ELEM-001..003 (T02); the AC-IO-* rows of T05 are still
   unregistered.
4. A measured FRF (UFF-58) can be compared against a synthesized FRF from a damped model
   via FRAC/FDAC through the CLI, and a meshio- or BDF-imported 3D mesh can be
   re-analyzed internally — the two headline workflow demos for the round. **The FRF
   demo is done** (A41 library half, A54 CLI half): `openfemlab correlate-frf
   measured.unv chain.yaml --require-frac 0.9` reads the dataset-58 column, synthesizes
   the same channels from the spec's damping, and publishes the `FRFCorrelation` block
   through `schema_version` `1.1`, with FRAC = 1 against its own model in
   `tests/test_cli_frf.py`. The imported-3D-mesh demo still waits on R2-T02/T05.
5. Full suite + Ruff + registry consistency green; no duplicate implementations of any
   numeric kernel (GAP-01 stays closed).

## 6. Top 3 priorities (summary)

1. ~~**R2-T01 — Dynamics/FRF chain** (GAP-04/05, P0)~~ — **COMPLETE**: merged at
   `acda625`, AC-DYN-001..005 registered and `implemented`, report `frf` block (A41)
   and `correlate-frf` CLI (A54) landed. The live top three are now T02, T03 and
   T04.
2. **R2-T02 — 3D elements** (GAP-02, P0): QUAD4/TET4/HEX8 plus the spatial beam so
   imported industrial meshes can be re-analyzed, unblocking the meshio bridge
   (R2-T05). All three continuum elements are landed, AC-ELEM-001..003 are registered,
   and the CBAR-like `BeamElement3D` closed the frame slice (A82); the shell facet and
   the solid/shell BDF cards remain, and R2-T05 is now unblocked for solid *and* frame
   meshes.
3. **R2-T03 — SEREP/TAM reduction & expansion** (GAP-08) and **R2-T04 Bayesian MAP**
   were the tied Round-2 sign-off blockers, via AC-CORR-006 and AC-UPD-006a/b. Both
   engines are on the trunk (`correlation/reduction.py` A36, `updating/bayesian.py`
   A49); AC-CORR-006 (A43), AC-CORR-009 (A58) and AC-UPD-006a/b (A57) are all
   registered and `implemented`, so what stands between them and the gate is a CI
   run that moves them to `verified`. R2-T04 still owes σ_post in the CLI `update`
   document.
