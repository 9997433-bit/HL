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

## 0. Status snapshot — Round 2 sign-off (A126 + A121, 2026-08-26, integration tip `8065205`)

Verified at integration tip `8065205` from a detached private worktree (`PYTHONPATH`
pinned): full suite **1335 passed, 0 failed**, `ruff check .` clean, on Python
3.12.3 / NumPy 2.5.2 / SciPy 1.18.1. Registry: **44 criteria — 44 `verified`,
0 `implemented`, 0 `specified`** (all 34 P0 + 10 P1 rows gated in CI). **A121**
batch-promoted the last 30 `implemented` rows via `promote_verified.py --run
--apply`.

Earlier snapshots on this page read **1133 passed / 0 `verified`** (A93), **1149 /
9 `verified`** (A72), and **1331 / 14 `verified` / 30 `implemented`** (A109 at
`571c864`). Since `571c864`: `quad4_as="shell"` in `neutral_convert` (A129),
the imported-shell modal example (A128), and the A121 closure above.

| Task | Status |
|---|---|
| R2-T01 dynamics/FRF | **COMPLETE** — engine (`acda625`), AC-DYN-001..005 **`verified`**, report `frf` block at schema 1.1 (A41), `openfemlab correlate-frf` CLI (A54). |
| R2-T02 3D elements | **PARTIAL** — all formulations in `core/elements.py`; `neutral_convert` with `quad4_as="shell"` (A129); Nastran BDF reads CQUAD4/CTETRA/CHEXA/CBAR + PSHELL/PSOLID (A119). Open: fold shell into AC-ELEM case table. |
| R2-T03 reduction/expansion | **ACCEPTANCE-COMPLETE** — engine (A36), AC-CORR-006/009 **`verified`**. Open: sparse inputs. |
| R2-T04 Bayesian MAP | **ACCEPTANCE-COMPLETE** — estimator (A49), AC-UPD-006a/b **`verified`**, σ_post in `CorrectionReport` and CLI `update` (A122). |
| R2-T05 meshio & IO | **ACCEPTANCE-COMPLETE for registration** — meshio bridge (A89), `neutral_convert` (A106), UFF read/write (A123), UNV 2411/2412 (A125), AC-IO-001..003 as module M8 (A120). Open: promote the three M8 rows to `verified`. |
| R2-T06 updating depth | P0 slice closed (AC-UPD-007 **`verified`**); P1 depth (MAC-row Jacobian, model-level resolver) open. |
| R2-T07 optimization | **COMPLETE for sizing** — AC-OPT-001..004 **`verified`**. Shape variables still FD. |
| R2-T08 R1-O2 reconciliation | **COMPLETE** |
| R2-T09 exit hardening | **COMPLETE for Round 2 sign-off** — CI gates + `promote_verified.py` (A72, A109, A121); **44/44 `verified`**. |

---

## 1. Starting state — what is already closed or in flight

The plan is *targeted*: it excludes work Round 1 backfills already landed. Delta against
the gap register at audit time:

| Gap | Audit status | Status entering Round 2 |
|---|---|---|
| GAP-01 integration split-brain | P0, suite not collecting | **Largely closed.** `ModalResult` unified (commit `508813e`), `modal/eigen.py` is a thin adapter over `solver/modal.py` (A08), full suite green at **192 passed** (A22). Residual: enforce the "seams land atomically with consumers" rule and keep CI green. |
| GAP-03 industrial IO | P0, absent | **Partial.** Native/meshio/BDF/UNV/UFF interchange is gated by AC-IO-001..003 (A120, module M8). Remaining: OP2, promote M8 criteria. |
| GAP-14 CLI stubs | P2, stubbed | **Closed for R2.** `modal`/`correlate`/`update` landed with model-spec format, gates, JSON/YAML documents on clean stdout (A07/A16/A22). |
| GAP-10 updating depth | P1, absent | **Partial.** Dotted-path parameter targeting in the CLI spec layer (A07), affine `ScalingModel` dK/dθ (A04), vectorized Fox–Kapoor + MAC sensitivities (A04/A10). Remaining: model-level resolver, assembled per-element dK/dp, analytic MAC-row Jacobian wiring → R2-T06. The MS-3.6 collinearity screen is done: `workflow/selection.py` plus the AC-UPD-007 acceptance tests (A44). |
| GAP-09 node mapping | P1, absent | **Partial.** Label-based DOF alignment (`correlation/align.py`, `workflow/sensors.py`). Remaining: geometry-based nearest-node mapping → folded into R2-T05/T06 scope notes. |
| GAP-04/05 dynamics & FRF | P0/P1, absent | **Closed by R2-T01.** `cursor/dynamics-damping-frf-9500` merged at `acda625`; AC-DYN-001..005 registered and `implemented`. GAP-05's FRF *updating residual* stays deferred to Round 3 as planned below. |
| GAP-02 3D elements | P0, absent | **Partial.** QUAD4 plane stress/strain landed with `mesh.simple.quad_plate_mesh` and 61 tests (R2-T02 first slice, merged from `cursor/quad4-plane-stress-element-b99c`); TET4 landed with `mesh.simple.tet_block_mesh` and 66 tests (A46); HEX8 landed with `mesh.simple.hex_block_mesh`, 76 tests and the AC-ELEM-001..003 registration over all three elements (A59); the CBAR-like `BeamElement3D` landed with `MeshBuilder.add_beam3d` and 42 tests (A82); the flat-facet shell landed as `ShellQuad4Element` with `shell_plate_mesh` / `MeshBuilder.add_shell_quad4` and 72 tests (A98); and `io/neutral_convert.py` binds an imported `ROD2`/`BEAM2`/`QUAD4`/`TET4`/`HEX8` block into those formulations (A106). Remaining: the solid/shell BDF cards and a shell branch in the converter → R2-T02 remainder. |
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

### R2-T02 — 3D element library (QUAD4 / TET4 / HEX8 / spatial beam / shell facet)

- **Priority:** 2 (P0) · **Gap:** [GAP-02](../docs/SOTA_GAP_ANALYSIS.md) (§4)
- **Why second:** every `ElementType` beyond 1D is declared but has no formulation, so no
  imported industrial mesh can be *re-analyzed* internally — it can only be correlated.
  This blocks the value of both the BDF reader (A18) and the meshio bridge (R2-T05).
- **Status: PARTIAL** — the three continuum slices, the spatial beam and the shell
  facet are **done**, and the element criteria are registered.
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
  *Spatial beam* (A82, merged onto the integration branch by A93 at `75dd070`, after
  which `cursor/beam3d-cbar-element-c9a7` was deleted from `origin`; suite **1089
  passed** at that merge, Ruff clean):
  `BeamElement3D`, the CBAR-like two-node frame member with six DOFs per node —
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
  *Shell facet* (A98, `cursor/shell-quad4-facet-1c70`; the branch reached the trunk's
  first-parent line at `9ad7a6b`, so its 72 tests are integrated rather than pending —
  reverified by A104 at integration tip `571c864` as **1331 passed, 0 failed** in
  27.06 s with `ruff check .` clean on Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1, and
  the branch is retired in [`BRANCH_CLEANUP.md`](BRANCH_CLEANUP.md)):
  `ShellQuad4Element`, the flat facet with six DOFs per node. Membrane action is the
  existing plane-stress `Quad4Element` evaluated on the projected in-plane
  coordinates — the global membrane sub-block reproduces `Quad4Element` to 2.4e-16 and
  the in-plane spectrum of `shell_plate_mesh` equals `quad_plate_mesh` to 1e-10, so
  there is no second membrane kernel (GAP-01 rule). Bending is a Reissner–Mindlin plate
  whose transverse shear uses the **MITC4** assumed-strain field (Bathe–Dvorkin, tying
  points at the four edge midpoints), which cures shear locking *without* the rank
  deficiency of reduced integration: the facet has exactly six zero-energy modes and
  reproduces a constant-curvature state to machine precision on a distorted
  quadrilateral. The rotation about the normal carries a fictitious diagonal drilling
  stiffness (`drilling_factor`, default 1e-3 of the mean plate rotational diagonal),
  which is what keeps a folded two-facet shell from hinging at the crease; because it
  is decoupled from the membrane, a coplanar assembly never loads it and still shows
  exactly six rigid-body modes. `shell_plate_mesh` / `MeshBuilder.add_shell_quad4` are
  the mesh seams and `tests/test_shell_quad4.py` carries 72 tests — both MacNeal–Harder
  patch tests (membrane exact to 1e-16, bending to 5e-12 with zero recovered shear),
  quadratic convergence to the Navier simply-supported plate spectrum
  (+7.2 %, +1.7 %, +0.42 % on 4/8/12 grids), the Euler–Bernoulli cantilever strip to
  +0.21 % in frequency and 1 % in tip deflection, spectrum invariance under an
  arbitrary 3D rotation to 1e-8, and the folded shell solving with a positive-definite
  stiffness. Documented limitations: the facet is rejected rather than projected when
  warped, the drilling stiffness is a penalty and not an Allman/Hughes–Brezzi rotation
  field, membrane and bending do not couple inside one facet, and the bending rotary
  inertia is off by default (`rotary_inertia=True` restores it, at the cost of a mass
  matrix ill conditioned enough to trip the modal residual guard on a thin plate).
  **The AC-ELEM-* rows are registered** (see the acceptance-links bullet below), so
  what remains open is the solid/shell BDF cards, the shell branch of the neutral-model
  conversion and folding the shell into the AC-ELEM case table; the task does **not**
  close. See the R2-T02, A37, A46, A59, A82 and A98 entries in
  [`PROGRESS.md`](PROGRESS.md).
- **Scope:**
  - ~~QUAD4 (plane stress/strain first; shell via flat facet + drilling treatment
    documented as a limitation)~~ **landed**, the flat facet included. ~~TET4~~
    **landed** as the constant-strain tetrahedron with consistent + row-sum lumped mass.
    ~~HEX8 (with standard hourglass/locking notes)~~ **landed** as the trilinear brick,
    hourglass count and shear locking both pinned by tests. ~~a 3D two-node beam
    (extends the planar Euler–Bernoulli one) to make frame models importable~~
    **landed** as `BeamElement3D`. No formulation is outstanding in `core/elements.py`.
  - `mesh/simple.py` generators for structured quad/hex blocks (needed for convergence
    fixtures) and neutral-model → assembly wiring for the new blocks — the structured
    **quad**, **shell**, **tet** (Kuhn-subdivided box) and **hex** generators are all
    landed, and `io/neutral_convert.py`'s `neutral_to_model` turns an imported
    `ROD2`/`BEAM2`/`QUAD4`/`TET4`/`HEX8` block into bound elements (A106); what remains
    is a shell branch in that converter, which today lands `ElementType.QUAD4` on the
    two-DOF membrane element.
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
  candidate — folding it in is a follow-up that needs no new criterion ID. The **shell
  facet is a stronger candidate**: `tests/test_shell_quad4.py` already carries all three
  criteria in developer form (a MacNeal–Harder patch exact to 1e-16 in membrane and
  5e-12 in bending, six zero-energy modes plus rigid-body invariance, quadratic
  convergence to the Navier plate oracle rather than the bar one), so adding it to the
  parametrized case table needs a per-case oracle switch but no new criterion ID.
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
  where each half stops holding under noise. AC-CORR-006 is now **`verified`**:
  A72's R2-T09 gate re-runs its 19 tagged tests green and reproducibly on every
  push. **Remaining to close the task:** stop densifying sparse inputs —
  AC-CORR-009's registration and the `SensorMap.signs` folding both landed
  with A58 (see the table in §0).
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
- **Status: PARTIAL — the bridge is on the trunk (A89).**
  `src/openfemlab/io/meshio_bridge.py` carries `from_meshio` / `to_meshio` over the
  one-to-one `CELL_TYPE_TO_ELEMENT` table
  (`vertex`/`line`/`triangle`/`quad`/`tetra`/`hexahedron` ↔
  `MASS1`/`ROD2`/`TRI3`/`QUAD4`/`TET4`/`HEX8`), the `read_meshio` / `write_meshio` file
  entry points, and the P7 seam: `meshio` is imported lazily by `require_meshio`, which
  raises the new `MissingDependencyError` (an `OpenFEMLabError` that is *also* an
  `ImportError`, so the old `except ImportError` call sites still work) with an install
  hint. `from_meshio` itself is duck-typed on `points`/`cells`, so a caller that already
  holds a mesh converts it without the extra installed. Node labels ride in `node_ids`
  point data and element labels in `element_ids` cell data, so `to_meshio` → `from_meshio`
  is label-preserving; `gmsh:physical` / `medit:ref` / `property_ids` cell data become
  `element_property_ids`; unmapped cell types are skipped with a `UserWarning` and
  recorded in `meta["skipped_cell_types"]`. `BEAM2` / `SPRING2` are deliberately absent
  from the export table because meshio's `line` cell cannot distinguish them from `ROD2`,
  and exporting one raises `FormatError` rather than silently changing the element type.
  `tests/test_meshio_bridge.py` (44 tests) skips as a module when meshio is missing; the
  `[dev]` extra now installs it so the bridge is exercised by default.
  The re-analysis half landed with A106: `io/neutral_convert.py` converts a
  `NeutralModel` into the internal `Model`, inferring the DOF signature from the blocks
  present, resolving each element's material and section through the neutral property
  tables, and taking caller-supplied `material=` / `section=` / `thickness=` fallbacks
  for the geometry-only files meshio returns. `read_meshio` → `neutral_to_model` →
  `ModalSolver` is therefore a working path for rod, beam, quad, tet and hex blocks.
  UFF writing landed with A123: `write_uff`/`format_uff` emit datasets 55 and 58 in the
  records `read_uff` accepts, with 20 round-trip tests. UNV 2411/2412 reading landed
  with A125 (`read_unv`, 50 tests). The acceptance rows landed with A120 as module **M8**
  (`MS-9`), which moves the pinned inventory to 47. **Remaining to close the task:**
  promoting the three M8 rows once a gate run with the `[io]` extra is green.
- **Scope:**
  - ~~`io/meshio_bridge.py`: bidirectional `meshio.Mesh` ↔ `NeutralModel` conversion
    (points → node arrays, cell blocks → `ElementType` blocks with an explicit,
    documented mapping table; unmapped cell types skipped with a diagnostic, mirroring
    the BDF reader's policy).~~ **landed** (A89).
  - ~~Optional-dependency seam per the ARCHITECTURE P7 policy (import guarded, clear
    `MissingDependencyError`, `[io]` extra grows `meshio`), matching how the `[cli]`
    extra degrades.~~ **landed** (A89); the `[io]` extra already carried `meshio`, and
    `[dev]` grew it so the tests do not silently skip in CI.
  - UNV 2411/2412 (nodes/elements) in `io/uff.py` so a *complete* UFF test model —
    geometry + modes (55) + FRFs (58) — round-trips; this also gives correlation a real
    test-geometry source for the GAP-09 nearest-node mapping.
- **Acceptance links:** registered by A120 as module **M8** over
  `tests/acceptance/test_io.py` (30 cases), ordered as the path a file travels rather
  than as the three proposals below: **AC-IO-001** (P0, `contract`, MS-9.2) the native
  JSON/YAML round trip, bitwise and with the two encodings proven to be one document;
  **AC-IO-002** (P1, `contract`, MS-9.3) the meshio round trip, in memory and on disk in
  every format that carries data arrays, plus the two edges of the skip/raise policy;
  **AC-IO-003** (P0, `contract`, MS-9.4) `read_meshio` → `neutral_to_model` →
  `assemble_system` over rod/quad/tet/hex, gated against the hand-built model bit for bit
  and against the continuum bar oracle. The originally proposed wording — a meshio
  round trip, a Gmsh/Abaqus fixture solving through the modal pipeline, and a UNV
  2411/2412 + 55 fixture feeding `correlate_modal_data` — was superseded: the first two
  fold into AC-IO-002/003, and the third had to wait for a reader that does not exist
  yet, which would have left a `specified` row blocking the dense-numbering rule.
- **Dependencies:** all cleared. R2-T02 supplied the solid/shell formulations and A106
  the `NeutralModel` → `Model` conversion AC-IO-003 needed; no committed binary fixture
  was required in the end, because the suite writes its meshes with meshio into
  `tmp_path` from the `mesh.simple` generators.

---

## 3. Supporting backlog (remaining Round 2 items)

| ID | Pri | Task | Gaps / gates | Notes |
|---|---|---|---|---|
| R2-T06 | 6 | Updating depth completion: the MS-3.6 collinearity screen with norm-ranked subset selection is **done** ([AC-UPD-007](../docs/ACCEPTANCE_CRITERIA.md), P0, `twin`: duplicated parameter detected at cosine > 0.99, one frozen, recovery gates still met — `workflow/selection.py`, tagged by A44); wire the analytic MAC-row Jacobian into the updater's shape-residual path (A04 flagged this as a cheap win — FD fallback currently used whenever shapes are present); model-level parameter target resolver (`material.<id>.<attr>`) with assembled per-element dK/dp providers | [GAP-10](../docs/SOTA_GAP_ANALYSIS.md), AC-UPD-007, MS-3.1/3.3/3.6 | What is left is P1 depth work; the P0 slice closed with the AC-UPD-007 tagging. |
| R2-T07 | 7 | Optimization backend: replace `optimization.solve` `NotImplementedError` with a scipy SLSQP/trust-constr backend using the sensitivity kernel for gradients and MAC-based mode tracking | [GAP-12](../docs/SOTA_GAP_ANALYSIS.md), [AC-OPT-001..003](../docs/ACCEPTANCE_CRITERIA.md) (P0), AC-OPT-004 (P1), MS-5 | Coordinate with the in-flight `optimization/{backends,gradients,problem,responses,variables}.py` on `cursor/dynamics-damping-frf-9500` — land that branch, don't fork. |
| R2-T08 | 8 | R1-O2 reconciliation: diff `cursor/r1o2-correlation-updating-e393` against the landed correlation/updating packages; harvest superior pieces (per-DOF MSF-scaled shape residuals, log-space parameter transform, frequency-window pairing acceptance) and delete the rest | GAP-01 hygiene | Already in progress on `cursor/reconcile-r1o2-correlation-updating-64c5`; merge through the integration branch, not around it. |
| R2-T09 | 9 | Round 2 exit hardening: CI job runs `import openfemlab` + full suite + Ruff + registry consistency on every push; registry statuses advanced `specified → implemented → verified` for every criterion a Round 2 task closes | Round 1 exit-bar carryover, AC §1.5 | **COMPLETE (A72, A109, A121).** Gates job + `promote_verified.py`; **44/44 `verified`**. |

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

0. *(machinery, A72 — done)* `verified` is a gated status, not a hand-written one:
   the CI `gates` job and `tests/acceptance/test_registry_ci.py` re-run every
   promoted criterion and revert-or-fail on a red, non-deterministic or
   unevidenced claim (AC §1.5, enforcement rule 7). The nine-criterion first
   slice — one per module plus AC-CORR-006 — is through it, and
   `scripts/promote_verified.py` (A109) has since made the flip a tool run,
   taking the count to **14 `verified`**; items 1–2 below are now a matter of
   promoting each of the 30 remaining rows as its track closes.
1. Every **P0** criterion in the registry is `verified`, including
   [AC-UPD-007](../docs/ACCEPTANCE_CRITERIA.md) and AC-WORK-001/002/004/005, which
   reached `implemented` once the acceptance suites claimed them (A44).
2. Every **P1** criterion is `verified` (AC §1.2: P1 blocks Round-2 sign-off) —
   AC-CORR-006 (SEREP) is through as of A72; the other nine P1 rows —
   AC-UPD-006a/b (Bayesian), AC-CORR-009, AC-MODAL-008, AC-WORK-003,
   AC-UPD-008, AC-OPT-004, AC-DYN-005 and AC-ELEM-003 — remain `implemented`.
3. The newly registered dynamics / element / IO criteria (T01/T02/T05 proposals above)
   are at least `implemented` — **met**: AC-DYN-001..005 (T01) and AC-ELEM-001..003
   (T02) are `verified`, and AC-IO-001..003 (T05) landed `implemented` with A120.
4. A measured FRF (UFF-58) can be compared against a synthesized FRF from a damped model
   via FRAC/FDAC through the CLI, and a meshio- or BDF-imported 3D mesh can be
   re-analyzed internally — the two headline workflow demos for the round. **The FRF
   demo is done** (A41 library half, A54 CLI half): `openfemlab correlate-frf
   measured.unv chain.yaml --require-frac 0.9` reads the dataset-58 column, synthesizes
   the same channels from the spec's damping, and publishes the `FRFCorrelation` block
   through `schema_version` `1.1`, with FRAC = 1 against its own model in
   `tests/test_cli_frf.py`. **The imported-3D-mesh demo now runs end to end in the
   library**: `read_meshio` turns any meshio-supported file into a `NeutralModel` (A89)
   and `neutral_to_model` binds its blocks into a solvable `Model` (A106), which
   `tests/test_neutral_convert.py` exercises on an imported hexahedron. What is left is
   a committed industrial fixture and a CLI surface over the pair.
5. Full suite + Ruff + registry consistency green; no duplicate implementations of any
   numeric kernel (GAP-01 stays closed).

## 6. Top 3 priorities (summary)

1. ~~**R2-T01 — Dynamics/FRF chain** (GAP-04/05, P0)~~ — **COMPLETE**: merged at
   `acda625`, AC-DYN-001..005 registered (001..004 since `verified` through the
   R2-T09 gate), report `frf` block (A41)
   and `correlate-frf` CLI (A54) landed. The live top three are now T02, T03 and
   T04.
2. **R2-T02 — 3D elements** (GAP-02, P0): QUAD4/TET4/HEX8 plus the spatial beam and the
   shell facet so imported industrial meshes can be re-analyzed, unblocking the meshio
   bridge (R2-T05). All three continuum elements are landed, AC-ELEM-001..003 are
   registered, the CBAR-like `BeamElement3D` closed the frame slice (A82, merged at
   `75dd070` by A93) and `ShellQuad4Element` closed the shell slice (A98); **no element
   formulation is outstanding in `core/elements.py`**. What remains is plumbing — a
   shell branch in `io/neutral_convert.py`, the solid/shell BDF cards, and folding the
   shell into the AC-ELEM case table. R2-T05 is unblocked for solid, frame *and* shell
   meshes, and A106's `neutral_to_model` connected the two tracks: an imported block now
   reaches the assembler.
3. **R2-T03 — SEREP/TAM reduction & expansion** (GAP-08) and **R2-T04 Bayesian MAP**
   were the tied Round-2 sign-off blockers, via AC-CORR-006 and AC-UPD-006a/b. Both
   engines are on the trunk (`correlation/reduction.py` A36, `updating/bayesian.py`
   A49); AC-CORR-006 (A43), AC-CORR-009 (A58) and AC-UPD-006a/b (A57) are all
   registered and `implemented`, and AC-CORR-006 is **`verified`** through the
   R2-T09 gate (A72) — the same gate the other three flip through once someone
   promotes them. R2-T04 still owes σ_post in the CLI `update` document.
