# FEMtools-like Industrial CAE Platform — Agent Progress

## Goal
Build an open-source, solver-independent CAE platform inspired by FEMtools, with improvements:
- Modal analysis (eigenvalue extraction, mode shapes)
- FE-Test correlation (MAC, frequency/error metrics)
- Sensitivity-based model updating (iterative parameter correction)
- Simulation correction / model validation workflow
- Optimization hooks and scripting API

## Branch
`cursor/femtools-industrial-7aa3`

## Pull Request
[PR #5](https://github.com/9997433-bit/HL/pull/5) is open against `main`.

## 永久编排规则（不可遗忘）
- **始终保持 10 个子代理并发满负荷运行**
- 任一子代理完成/失败 → 主调度器**立即**派发新 Task 补齐至 10
- 此规则优先级最高，无论上下文是否已满
- 活跃池目标：10（3×fable + 4×opus-fast + 3×gpt-sol 推荐配比）

## Active Pool

| Agent | Model | Focus | Status |
|-------|-------|-------|--------|
| A01 | claude-fable-5-thinking-xhigh | Module spec & acceptance criteria (docs + registry) | complete |
| A03 | claude-fable-5-thinking-xhigh | SOTA gap audit & Round 1 conclusion (backfill) | complete |
| A04 | claude-opus-5-thinking-high-fast | Updating sensitivity kernel, updater wiring & test suite | complete |
| A17 | claude-fable-5-thinking-xhigh | Round 1 conclusion brief & full-suite verification (backfill) | complete |
| A07 | claude-opus-5-thinking-high-fast | Rich CLI (modal/correlate/update), model spec format & workflow example | complete |
| A24 | claude-fable-5-thinking-xhigh | Round 2 plan: prioritized backlog with AC links (backfill for A22) | complete |
| A25 | gpt-5.6-sol-xhigh-fast | CLI subprocess coverage over example 02 fixtures | complete |
| A19 | claude-opus-5-thinking-high-fast | GAP-04/05 damped dynamics: damping, complex modes, FRF synthesis (backfill for A11) | complete |
| A29 | gpt-5.6-sol-xhigh-fast | Rebase A13 workflow into dynamics/optimization integration branch | complete |
| A15 | claude-opus-5-thinking-high-fast | GAP-01 `ModalResult` contract unification (backfill for R1-F1) | complete |
| A13 | claude-opus-5-thinking-high-fast | M4 correction workflow state machine & `CorrectionReport` (backfill for A01) | complete |
| A14 | claude-opus-5-thinking-high-fast | R1-O2 correlation/updating branch reconciliation (backfill) | complete |
| A26 | claude-opus-5-thinking-high-fast | MS-4 workflow landing verification & Round 2 kickoff (backfill for A17) | complete |
| A02 | claude-fable-5-thinking-xhigh | M5 optimization design & stubs: size/shape hooks, gradient interface, `docs/OPTIMIZATION.md` (backfill for A05) | complete |
| A28 | claude-opus-5-thinking-high-fast | Dynamics/optimization branch integration onto the trunk (backfill for A15) | complete |
| A32 | claude-fable-5-thinking-xhigh | Round 1 closure: 430-test/Ruff verification, PR draft, progress reconciliation (backfill for A29) | complete |
| A30 | claude-fable-5-thinking-xhigh | Round 1 close-out: independent full-suite verification & PR-draft completion (backfill for A14) | complete |
| A27 | claude-opus-5-thinking-high-fast | R2-T07 scipy optimization backend & AC-OPT gates (backfill for A25) | complete |
| A39 | gpt-5.6-sol-xhigh-fast | R2-T07 post-integration verification & PR-draft refresh (backfill for A27) | complete |
| A36 | claude-opus-5-thinking-high-fast | R2-T03 start: `correlation/reduction.py` (Guyan/IRS/SEREP, TAM mass, expansion) + 2-DOF suite (backfill for A32) | complete |
| A23 | claude-fable-5-thinking-xhigh | Round 1 sign-off audit: independent multi-tip verification & first PR body draft (backfill for A20) | complete |
| A42 | gpt-5.6-sol-xhigh-fast | 498-test baseline timestamp & current-tip CI verification (backfill for A39) | complete |
| R2-T02 | claude-opus-5-thinking-high-fast | GAP-02 QUAD4 plane-stress/plane-strain element, patch test & modal suite (backfill for A19) | partial — QUAD4, TET4 and HEX8 landed with AC-ELEM-001..003 registered; 3D beam, shell facet and the solid/shell BDF cards open |
| A37 | claude-opus-5-thinking-high-fast | Merge the QUAD4 branch onto the trunk and re-verify the suite (backfill for R2-T02) | complete |
| A35 | claude-fable-5-thinking-xhigh | AC-DYN registration (backfill for A28): found R2-T01 had landed it mid-run; dropped the duplicate, verified the head | complete |
| A45 | gpt-5.6-sol-xhigh-fast | Current-tip 595-test/Ruff verification and PR-draft refresh (backfill for A37) | complete |
| A47 | gpt-5.6-sol-xhigh-fast | Reconcile A23's 41-vs-40 criteria audit count and pin the registry inventory (backfill for A35) | complete |
| A41 | claude-opus-5-thinking-high-fast | FRF block in the `CorrelationReport` schema, `schema_version` 1.1 (backfill for R2-T01) | complete |
| A40 | claude-opus-5-thinking-high-fast | Side-branch merge sweep (scipy backend harvest; QUAD4 raced with A37), full-suite verification & PR-draft refresh (backfill for A38) | complete |
| A44 | claude-opus-5-thinking-high-fast | Tag AC-WORK-001/002/004/005 and AC-UPD-007; new `tests/acceptance/test_workflow.py` (backfill for A23) | complete |
| A43 | claude-opus-5-thinking-high-fast | R2-T03: AC-CORR-006 acceptance gate (reduced- vs expanded-space pairing) and its registration (backfill for A36) | complete |
| A46 | claude-opus-5-thinking-high-fast | R2-T02 continued: TET4 constant-strain tetrahedron, Kuhn tet-block mesh, 3D patch suite (backfill for A42) | complete |
| A59 | claude-opus-5-thinking-high-fast | R2-T02 continued: HEX8 trilinear brick, hex-block mesh, and the AC-ELEM-001..003 registration over QUAD4/TET4/HEX8 (backfill for A46) | complete |
| A64 | claude-fable-5-thinking-xhigh | Chinese quickstart user guide `docs/USER_GUIDE_zh.md`: install, CLI, workflow, FEMtools mapping (backfill for A52) | complete |
| A54 | claude-opus-5-thinking-high-fast | `openfemlab correlate-frf`: the CLI surface over `correlation/frf.py`, closing the last R2-T01 exit item (backfill for A41) | complete |
| A62 | gpt-5.6-sol-xhigh-fast | Superseded-branch closure record and current-trunk verification (backfill for A40) | complete |
| A55 | claude-fable-5-thinking-xhigh | Status snapshot: `.agent_workspace/STATUS.md` — 876-test verification, Round 1/2 state, module table, open gaps (backfill for A51) | complete |
| A61 | claude-fable-5-thinking-xhigh | Round 2 mid-point brief, plan status snapshot & 876-test tip verification (backfill for A53) | complete |
| A50 | claude-opus-5-thinking-high-fast | Remaining P0 acceptance batch: AC-MODAL-007/009, AC-CORR-005/007, AC-UPD-004/005, AC-WORK-001/002/004/005 + MS-1.1 solver validation and MS-3.4 stop reasons/divergence guard (backfill for A31) | complete |
| A58 | claude-opus-5-thinking-high-fast | R2-T03: register AC-CORR-009 (TAM pseudo-orthogonality) and wire `SensorMap.signs` through the reduction bases (backfill for A43) | complete |
| A76 | gpt-5.6-sol-xhigh-fast | Current-tip pytest verification (backfill for completed A75) | complete — A75 done; 921 passed |
| A80 | gpt-5.6-sol-xhigh-fast | Authoritative current-tip pytest count (backfill for completed A76) | complete — 1033 passed at `ff484e4`; collection confirmed 1033 |
| A57 | claude-opus-5-thinking-high-fast | R2-T04 acceptance gate: register AC-UPD-006a/b, penalize the starting cost, and carry the Laplace σ_post into the `CorrectionReport` (backfill for A49) | complete |
| A83 | claude-opus-5-thinking-high-fast | Land the AC-UPD-006 registration branch on the trunk, verify the tip and mark R2-T04 acceptance-complete (backfill for completed A57) | complete — 1089 passed at `7368c92`, Ruff clean, side branch deleted |
| A84 | claude-fable-5-thinking-xhigh | P0 32/32→34/34 milestone chronology pinned; AC-UPD-006 registry-count divergence with A57's branch reconciled (backfill for completed A69) | complete — 1033 passed at `c5afc35`; post-merge union 41/3 confirmed at the tip |
| A99 | gpt-5.6-sol-xhigh-fast | Current-tip pytest verification (backfill for completed A97) | complete — A97 done; 1133 passed |

## Reference: FEMtools Core Capabilities
| Module | Description |
|--------|-------------|
| Framework | Scripting + desktop environment for CAE automation |
| Dynamics | Dynamic response simulation, structural modifications |
| Pretest & Correlation | Modal pretest, FE-test correlation (MAC, COMAC) |
| Model Updating | Sensitivity-based iterative updating (freq, mode shapes, FRF) |
| Optimization | Structural design optimization |
| MPE | Modal parameter extraction from FRFs |

## Round Status

### Round 1 — Initial Build & Baseline Exploration
**Status:** COMPLETE — concluded at `bae4b77` (192 tests, see Round Conclusions below);
both carry-over packages have since landed and the dynamics/optimization work is merged
(`acda625`), bringing the suite to **430 passed** with `ruff check` clean (final
addendum below).  
**Dispatched:** 6 subagents (2×fable, 2×opus-fast, 2×gpt-sol), plus backfill agents A01–A20

| Agent | Model | Focus | Status |
|-------|-------|-------|--------|
| R1-F1 | claude-fable-5-thinking-xhigh | Global architecture & SOTA audit | done |
| R1-F2 | claude-fable-5-thinking-xhigh | Module spec & acceptance criteria | complete |
| R1-O1 | claude-opus-5-thinking-high-fast | Core FEM + modal solver | complete |
| R1-O2 | claude-opus-5-thinking-high-fast | Model updating & correlation | complete (branch `cursor/r1o2-correlation-updating-e393`, reconciled into the integration branch by A14) |
| R1-G1 | gpt-5.6-sol-xhigh-fast | Project scaffold & benchmarks | complete |
| R1-G2 | gpt-5.6-sol-xhigh-fast | Boundary tests & mock probes | complete |

#### R1-F1 — Global Architecture & SOTA Audit
- Added `docs/ARCHITECTURE.md`: layered module diagram (io -> core/mesh -> solver/modal
  -> correlation/updating/optimization -> cli), data-flow diagrams for the modal,
  correlation, and updating pipelines, core data contracts, tech-stack policy, and a
  FEMtools SOTA gap table (we concede GUI/format breadth; exceed on Hungarian mode
  pairing, auto-regularized updating, Bayesian hooks, Python scripting, reproducibility).
- Contributed the shared L1 contracts now committed in core: `DofMap`/`DofType`
  (`core/dofs.py`), `ModalResult`/`TestData` (`core/results.py`), and the neutral
  interchange model relocated by R1-O1 to `core/neutral.py`.
- Added `modal/eigen.py` (neutral eigsh shift-invert kernel for imported K/M),
  `optimization/` problem stub, and the `openfemlab` CLI (`cli/main.py`, argparse+rich
  with plain fallback; wired to `[project.scripts]`).
- Reconciled `pyproject.toml` (setuptools src-layout, numpy/scipy/pyyaml hard deps,
  `io`/`cli`/`dev` extras, console script) and restored the R1-O1 status cell lost in a
  concurrent PROGRESS edit.
- Flagged for Round 2 (see ARCHITECTURE.md §11): consolidate the two eigen entry points
  (`solver.modal.ModalSolver` vs `modal.eigen.solve_modes`) and merge the duplicate
  `ModalResult` classes into the neutral contract; UNV 55/58/2411/2412 io is the top
  io priority.

#### R1-G1 — Project Scaffold & Benchmarks
- Added Python packaging metadata, runtime/dev dependencies, Make targets, and push CI.
- Added sparse modal benchmarks for 10/100/1000-DOF spring chains.
- Added a five-iteration sensitivity-based model-updating benchmark.
- Added a cantilever modal-analysis example and scaffold smoke tests.
- Verified on Python 3.12: 8 tests passed; R1-G1 files pass Ruff.
- Modal median baselines: 10 DOF 0.669 ms; 100 DOF 1.180 ms; 1000 DOF 1.815 ms.
- Updating baseline: 35.640 ms median for five iterations at 100 DOF (RMS 5.848e-3 to 1.583e-5).

#### R1-O1 — Core FEM & Modal Solver
- Added `core/model.py`: node-major DOF numbering over a configurable DOF signature
  (`UX..RZ`), single-point constraints, concentrated masses and rotary inertias,
  validated `Material`/`Section` value objects.
- Added `core/elements.py`: scalar spring (grounded or 2-node), 2-node truss/bar with
  consistent or lumped mass valid in 1D/2D/3D, planar Euler-Bernoulli beam (UX, UY, RZ).
- Added `core/assembly.py`: COO-triplet assembly of symmetric CSR `K`/`M`, free/constrained
  partitioning, free-to-full shape expansion, total-mass check.
- Added `solver/modal.py`: `ModalSolver` for `K phi = omega^2 M phi` with automatic dense
  (`scipy.linalg.eigh`) / sparse shift-invert (`scipy.sparse.linalg.eigsh`) selection, exact
  static condensation of massless DOFs, mass/max normalization, deterministic mode signs,
  and `ModalResult` (frequencies, modal masses, participation factors, effective masses).
- Added `mesh/simple.py`: `MeshBuilder` plus spring-mass chain, axial bar, planar beam and
  array-driven truss generators.
- Verified against closed-form solutions: 2-DOF and 10-DOF chains (fixed-free `omega_i =
  2 sqrt(k/m) sin((2i-1)pi/(2(2N+1)))`, fixed-fixed `omega_i = 2 sqrt(k/m) sin(i pi/(2(N+1)))`)
  to 1e-9 relative, continuum bar `f_i = (2i-1)c/(4L)`, cantilever beam `beta_i^2/(2 pi)
  sqrt(EI/(rho A L^4))` to 0.2%, plus quadratic mesh convergence, rigid-body and rotation
  invariance checks.
- Verified on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1: 33 tests in
  `tests/test_modal_solver.py` and 18 in `tests/test_core.py` pass (0.9 s).
- Note for the orchestrator: `openfemlab/modal/eigen.py` (A09/neutral-model stack) duplicates
  the eigen extraction now provided by `solver/modal.py`; `io/_native.py` still imports the
  neutral names from `core.model`, which moved to `core.neutral`.

#### R1-G2 — Boundary Tests & Mock Probes
- Added analytic 2-DOF and 10-DOF chain fixtures plus synthetic FE/test modal data.
- Added environment/BLAS, repeated-eigensolve, and finite-difference sensitivity probes.
- Added zero-mass, rigid-mode, repeated-root, and missing-DOF boundary coverage.
- Verified NumPy 2.5.2, SciPy 1.18.1, and OpenBLAS 0.3.34; all environment checks passed.
- Repeated 50 eigen solves with zero eigenpair drift (normalized residual 6.58e-17).
- Sensitivity finite differences matched analytic derivatives within 1.69e-9 relative error.
- Verified on Python 3.12: 5 boundary tests passed; aggregate install validation passed.

#### A09 — Native Model and Modal IO
- Added schema-versioned YAML/JSON readers and writers for neutral models,
  analytical modal results, and experimental test data.
- Preserved complex mode shapes, DOF maps, element/property/material tables,
  metadata, damping, and test geometry across text round trips.
- Added safe generic fixture loading and adapters for repository
  `tests/fixtures/*.yaml`, including `modes_by_dof` layout conversion.
- Added IO round-trip, fixture compatibility, format-error, and validation tests.

#### A03 — SOTA Gap Audit (backfill)
- Audited every module in `src/openfemlab/` and the full test suite against FEMtools'
  capability map (Framework, Dynamics, Pretest & Correlation, Updating, Optimization,
  MPE, Probabilistic) plus modern open-source SOTA (Bayesian updating, OMA/SSI, AD, CMS).
- Published `docs/SOTA_GAP_ANALYSIS.md`: capability baseline, 15-entry gap register
  (GAP-01..GAP-15 with P0/P1/P2 severity), top-5 detail, and Round 2/3 sequencing.
- Top 5 gaps: (1) GAP-01 split-brain integration debt — two parallel core architectures,
  renamed seam symbols, duplicate `ModalResult`/eigensolver, suite not collecting cleanly
  at audit time; (2) GAP-03 no industrial model/test-data exchange (UFF/UNV, Nastran BDF,
  meshio); (3) GAP-04/05 no damping, forced response, FRF synthesis or FRF correlation;
  (4) GAP-06 no modal parameter extraction from measured FRFs; (5) GAP-07/08 no pretest
  planning, TAM reduction (Guyan/IRS/SEREP) or mode-shape expansion.
- Recorded timestamped import/test evidence (three distinct broken states observed while
  concurrent agents integrated) as justification for a Round 2 "seams land atomically
  with consumers" rule.

#### A01 — Module Spec & Acceptance Criteria
- Finalized `docs/MODULE_SPEC.md` (MS-0..MS-6): modal analysis, correlation,
  sensitivity-based updating, simulation-correction workflow, optimization hooks;
  package naming aligned to the approved `openfemlab` architecture.
- Added `docs/ACCEPTANCE_CRITERIA.md`: 35 quantified criteria
  (MODAL 9, CORR 8, UPD 9, WORK 5, OPT 4) with P0/P1 round gates, tolerances,
  and verification methods (oracle/property/twin/contract/regression).
- Added `tests/acceptance/test_criteria_registry.py`: machine-readable registry
  of all 35 criteria with consistency tests (ID format/uniqueness, dense
  numbering, cross-references against both docs, vocabularies, P0 coverage);
  final registry body merged with the parallel R1-F2 rewrite (10 tests).
- Verified on Python 3.12: 10/10 registry tests pass on the committed state;
  new files pass Ruff.

#### R1-F2 — Module Spec & Acceptance Criteria
- Added `docs/MODULE_SPEC.md`: binding specs for M1 modal analysis
  (K·φ = λ·M·φ, dense/shift-invert-Lanczos/LOBPCG backends, rigid-body and
  missed-mode handling, mass-normalization + sign convention), M2 correlation
  (MAC/weighted MAC, Hungarian mode pairing, frequency error, COMAC,
  test–analysis DOF mapping), M3 updating (Fox–Kapoor and eigenvalue
  sensitivities, LM-regularized weighted Gauss–Newton, Bayesian MAP with
  posterior covariance, collinearity-based parameter selection), M4 correction
  workflow (S1–S6 state machine with validation gates and held-out targets),
  M5 gradient-based sizing optimization hook. Aligned to `openfemlab` layering
  from `docs/ARCHITECTURE.md`.
- Added `docs/ACCEPTANCE_CRITERIA.md`: 35 measurable criteria
  (AC-MODAL-001..009, AC-CORR-001..008, AC-UPD-001..008 incl. 006a/b,
  AC-WORK-001..005, AC-OPT-001..004) with quantitative gates (e.g. analytic
  eigenvalues ≤ 1e-10 rel. err; sensitivities vs FD ≤ 1e-6; post-update
  MAC ≥ 0.95 and |Δf| ≤ 1%), verification-method taxonomy, and P0/P1/P2
  round gates.
- Added `tests/acceptance/test_criteria_registry.py`: machine-readable
  registry of all 35 criteria + 10 consistency tests (ID format/uniqueness,
  dense numbering, doc/spec/registry sync, P0 coverage). All 10 pass.

#### A05 — Modal Module Completion & Fixture Benchmarks
- Resolved the `core/model.py` name collision behind GAP-01: the solver-side model
  (`DOF`, `Node`, `Material`, `Section`, `Model`) stays in `core.model`, while the flat
  importer-facing contract moved to the new `core/neutral.py` as `NeutralModel`,
  `NeutralMaterial`, `NeutralProperty`, `ElementType`. Before this, `core.elements`,
  `core.assembly`, `mesh/simple.py` and `solver/modal.py` could not be imported together.
- Repointed `io/_native.py`, `tests/test_io.py` and `solver/__init__.py` at
  `core.neutral`, clearing the collection errors in the committed IO suite — the open
  item R1-O1 flagged for the orchestrator.
- Committed `core/results.py`, without which the already-committed `openfemlab.io`
  could not be imported from a clean checkout.
- Added 11 fixture-driven cases to `tests/test_modal_solver.py`:
  `tests/fixtures/two_dof_analytic.yaml` and `tests/fixtures/ten_dof_chain.yaml` now
  supply the reference spectra, mass-normalized shapes and tolerances, rather than
  numbers hard-coded in the test body.
- Fixture coverage: eigenvalues/omega/f to the fixture tolerances (1e-12 and 1e-11
  relative), `phi^T M phi = I` and `phi^T K phi = diag(lambda)` to 1e-12, relative
  eigenpair residual `||K phi - lambda M phi|| / ||K phi|| < 1e-12`, the 2-DOF shapes to
  1e-10 absolute after sign alignment, the fixed-free sine law for the 10-DOF shapes,
  and agreement of the sparse shift-invert backend with the reference.
- Integration is pinned in both directions: `spring_mass_chain(2, 1, 1, fixed_end=True)`
  and `spring_mass_chain(10, 1, 1)` must assemble exactly the fixture `K`/`M`, and the
  full Model -> assembly -> eigensolve path must reproduce the fixture spectrum.
- Verified on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1:
  `pytest tests/test_modal_solver.py -v` gives 44 passed (0.4 s); `tests/test_io.py`
  13 passed. Touched files pass Ruff.
- Open for the orchestrator: `ruff check .` still fails on files owned by other agents
  (`openfemlab/__init__.py` TYPE_CHECKING re-export block, `core/dofs.py` B905,
  `core/elements.py` E741, `core/model.py` UP037/E501), and `openfemlab/modal/eigen.py`
  still duplicates the eigen extraction in `solver/modal.py`.

#### A08 — Concurrent Integration Reconciliation
- Made native IO use the explicit `NeutralModel`, `NeutralMaterial`, and
  `NeutralProperty` contracts from `core.neutral`; it no longer aliases or imports the
  internal solver model types from `core.model`.
- Replaced the duplicate eigensolver in `modal/eigen.py` with a compatibility adapter over
  `solver/modal.py::ModalSolver`, retaining the portable `DofMap`/`core.results.ModalResult`
  API while keeping one numerical eigen-extraction implementation.
- Completed the correlation package seam required by updating and retained compatibility
  aliases (`auto_mac`, `mac_matrix`); numerically orthogonal modes are no longer paired as
  valid zero-threshold candidates.
- Added `tests/test_e2e_workflow.py`: Model → modal solve → correlation → LM update →
  explicit re-solve → validation. The stiffness scale converged from 0.72 to 1.21 in five
  iterations; maximum frequency error fell from 22.861078% to 0%, with minimum MAC 1.0
  (acceptance gates: frequency error <1%, MAC >0.95).
- Verified the portable modal adapter directly, and `pytest --collect-only -q` collected
  all 156 current tests without errors. The focused E2E + IO + modal regression run passed
  all 58 tests.

#### R1-O2 — FE-Test Correlation & Sensitivity-Based Updating
**Delivered on branch `cursor/r1o2-correlation-updating-e393`, not on the integration branch.**
While R1-O2 was implementing, A08 and others landed their own `correlation/` and `updating/`
packages at the same paths on `cursor/femtools-industrial-7aa3` (R1-O2's `correlation/mac.py`
was overwritten in the shared working tree mid-run). Rather than start an overwrite war,
R1-O2 finished in an isolated worktree and pushed a self-contained branch for the
orchestrator to diff against the landed implementation in Round 2.

- `correlation/mac.py`: MAC / cross-MAC / auto-MAC over real or complex shapes with optional
  per-DOF weighting (pretest sensor weighting, mass weighting), modal scale factor, signed
  frequency-error metrics (`FrequencyDifference`, `frequency_error_matrix`), and automatic
  mode pairing — greedy or Hungarian (`scipy.optimize.linear_sum_assignment`, greedy
  fallback) — with MAC-threshold and frequency-window acceptance so uncorrelated modes are
  reported unpaired instead of forced into a pair.
- `correlation/metrics.py`: `CorrelationSummary` (mean/min/max MAC, mean/max/rms frequency
  error, worst off-diagonal MAC as a mode-swap indicator, `is_correlated` acceptance gate,
  printable pair table), COMAC, and the normalised frequency residual.
- `updating/parameters.py`: bounded `UpdatableParameter` scaling factors (stiffness, mass,
  damping, generic) carrying element/group targets, FD step, fixed flag and an optional
  logarithmic design-space transform that guarantees positive properties; `ParameterSet`
  handles ordering, free/fixed splitting, bound projection and design-space mapping.
- `updating/sensitivity.py`: analytical Fox–Kapoor eigenvalue sensitivity
  `dλ_i/dp = φ_i^T (dK/dp − λ_i dM/dp) φ_i / (φ_i^T M φ_i)`, eigenvalue→frequency conversion,
  a generic finite-difference Jacobian, and a solver-independent modal sensitivity that
  re-pairs perturbed modes to the baseline by MAC so mode switching cannot corrupt the matrix.
  `as_modal_data` adapts tuples, mappings, arrays and any solver result object exposing
  frequencies/mode shapes, so the updater drives `solver.modal.ModalSolver` unmodified.
- `updating/updater.py`: iterative updater minimising `r = [w_f (f_fe − f_test)/f_test,
  w_s (1 − sqrt(MAC))]` (or per-DOF MSF-scaled shape differences) through damped normal
  equations `(J^T J + λ diag(J^T J) + β I) Δx = −(J^T r + β (x − x0))`, Levenberg–Marquardt
  with adaptive damping or Gauss–Newton, Tikhonov regularisation towards the starting model,
  bound projection, per-iteration MAC re-pairing, convergence history and correlation
  summaries before/after.
- Tests (`tests/test_correlation.py` 29, `tests/test_updating.py` 33, plus the standalone
  `tests/modal_reference.py` spring-mass chain): **61 passed, 1 skipped in 0.42 s** on
  Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1; the skip is the core-solver integration test,
  which was verified separately against `solver.modal.ModalSolver` (recovers a 1.44 stiffness
  factor to 1e-4). Key results: analytical vs finite-difference sensitivities agree to 1e-6
  relative; a 2-DOF model recovers stiffness factors 1.25 / 0.80 to 1e-4; a 6-DOF model with
  two stiffness groups and a tip mass goes from mean MAC < 0.99 and 5%+ frequency error to
  min MAC > 0.999 and < 0.01% error; an 8-DOF model with only 4 measured DOFs, 3 measured
  modes and noisy targets (0.2% frequency, 1% shape) recovers all three group factors within
  5% and removes > 90% of the cost. All new files pass the project Ruff configuration.

#### A14 — R1-O2 Branch Reconciliation (backfill)
**Closes the open R1-O2 item above: `cursor/r1o2-correlation-updating-e393` is now folded
into the integration branch, so nothing is left stranded on a side branch.**

- Diffed the R1-O2 branch against the landed `correlation/` and `updating/` packages
  file by file, then ran R1-O2's own 62 tests against the landed implementation as the
  acid test. 60 passed unchanged, which confirmed the algorithms R1-O2 delivered had
  already been absorbed: the Levenberg–Marquardt updater, the Fox–Kapoor eigenvalue
  sensitivities, and the Hungarian mode pairing (A06 also split them into
  `pairing.py`/`summary.py` and extended pairing with `freq_penalty`/`max_pairs`, and
  A04 extended sensitivity with `mode_shape_sensitivity`/`mac_sensitivity`). Two
  failures remained, and both were real findings rather than merge noise.
- **Regression fixed.** `ModelUpdater.__init__` lost R1-O2's `ParameterSet.copy()` when
  the code landed, so a run wrote its solution back into the caller's
  `UpdatableParameter` objects. A second run over the same parameters then started from
  the first run's answer, which silently made Tikhonov regularisation a no-op: `x0` was
  the already-converged point, so the regularised and unregularised runs returned
  identical parameters (1.40/0.70 on the 2-DOF twin experiment). Restored the copy.
- **Behaviour deliberately kept from the integration branch.** The other failure was
  `mac([0, 0], [1, 2])`: R1-O2 returned 0.0, the integration branch raises on a
  zero-norm mode (commit "reject undefined MAC for null modes"). Raising is the better
  contract — an undefined MAC should not silently look like a perfectly uncorrelated
  pair — so R1-O2's contradicting test was dropped rather than the behaviour.
- **Strictness restored.** The repository-wide Ruff pass (A11) resolved B905 by writing
  `strict=False` everywhere, which turned R1-O2's length-checked `zip`s into silently
  truncating ones. Put `strict=True` back in `updating/parameters.py` (3),
  `updating/sensitivity.py` (3), `updating/updater.py` (2), `correlation/pairing.py` (1)
  and `tests/modal_reference.py` (1) — every one of those is either guarded by an
  explicit size check or pairs equal-length outputs, so a mismatch is a bug worth raising.
- **Hungarian pairing wired into the updater.** `correlation.pairing` implemented the
  globally optimal assignment but `ModelUpdater` only ever asked for `"greedy"`.
  `UpdatingOptions.mode_pairing` now also accepts `"optimal"`, threaded through both the
  per-iteration re-pairing and the correlation summaries.
- **Test suites merged**, not replaced: the two branches covered different things (R1-O2
  drives a callable model over the analytic spring-mass chain, the integration branch
  drives the affine `ScalingModel`), so R1-O2's distinct cases were added alongside.
  New on the correlation side: the `mac_matrix`/`auto_mac` compatibility aliases, per-DOF
  sensor weighting that masks a polluted channel, `frequency_error_matrix`, frequency-only
  pairing, an all-modes-unpaired frequency window, the pairing table, greedy-vs-optimal
  agreement, `off_diagonal_mac`, `normalized_frequency_residual`, and the flat summary
  dict. New on the updating side: the whole parameter/design-space layer (bounds,
  log-scaling round trip, `ParameterSet` bookkeeping), `as_modal_data` over the common
  solver return types, `ModalData` validation, forward/central FD agreement, and the
  callable-model runs — shape-difference residual, frequency-only updating, noisy targets
  on a measured DOF subset, bounds, history monotonicity, evaluation counting for the
  analytical path, and an updating run driven through `solver.modal.ModalSolver`.
- Added guards for both reconciled behaviours: the updater must leave the caller's
  parameter objects at their initial values, and `mode_pairing="optimal"` must reach the
  greedy pass's solution.
- **Follow-on in the M4 workflow.** A13's S1–S6 correction pipeline landed mid-run and
  read the correction back by aliasing the `ParameterSet` it handed to `ModelUpdater`,
  so restoring the copy left all 12 of its end-to-end cases failing at S5/S6. Fixed at
  the consumer: `_stage_updating` now adopts `UpdatingResult.parameter_set`, which
  carries the same bounds, initial values and fixed flags the gates report on. This is
  the seam rule Round 1 already learned the hard way — the alias was load-bearing but
  undeclared, and only a full-suite run after rebasing surfaced it.
- Verified on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1, rebased onto the integration tip:
  `tests/test_correlation.py` 52 passed (was 35) and `tests/test_updating.py` 57 (was 28),
  so 109 correlation + updating tests all green, and **+46 on the whole suite**
  (332 passed against a 286-test tip at the time of the final rebase; the branch was
  moving, so read the delta rather than the absolute). `tests/test_workflow.py` 38/38
  and `tests/test_cli.py` still pass on the reconciled updater.
  `ruff check src tests` passes.
- Method note for the orchestrator: this run worked in a detached `git worktree` because
  `/workspace` had concurrent uncommitted edits, and the base branch advanced four times
  during the run. Tests there need `PYTHONPATH` pointed at the worktree's `src`, since
  the venv's editable install resolves `openfemlab` to `/workspace/src` — measuring a
  worktree without it silently tests the shared tree instead.

#### A11 — Repository-wide Ruff Cleanup
- Cleared all reported Ruff failures across `openfemlab` and its tests: modernized
  imports and annotations, wrapped overlong lines, removed an unused test import, renamed
  an ambiguous inertia variable, and made every `zip` policy explicit.
- Used `strict=False` for existing `zip` calls so unequal inputs retain their prior
  truncation behavior. (A14 later put `strict=True` back on the ten correlation/updating
  call sites that were written strict before this pass; see the A14 entry above.)

#### A06 — Correlation Package Completion & Fixture Test Suite
- Completed `src/openfemlab/correlation/` against MS-2 and landed it on the integration
  branch (the R1-O2 branch work above stayed isolated): `mac.py`, `align.py`, `metrics.py`,
  `pairing.py`, `summary.py`, `report.py`, with the package `__init__` exporting the whole
  public API so consumers no longer import private submodules.
- `mac.py`: MAC / autoMAC over real or complex shapes, now with optional DOF weighting —
  a per-DOF vector or a full (also sparse) matrix such as a Guyan-reduced mass — giving the
  mass-weighted MAC of MS-2.2; added scalar `mac_value`, `modal_scale_factor`, the
  pseudo-orthogonality check `Φ_aᴴ M Φ_b`, and a COMAC that MSF-scales each pair and can
  accumulate over a `ModePairing` instead of assuming column order.
- `align.py` (new, the missing MS-2.1 piece): reduction of FE shapes onto the instrumented
  DOFs, by `DofMap` intersection or by string labels, with sensor orientation signs, the
  explicit selection operator `T`, strict-by-default reporting of sensors the model does not
  have, and the list of model DOFs left uninstrumented.
- `metrics.py`: frequency errors with the test set pinned as the reference
  (`Δf% = 100 (f_fe − f_test) / f_test`, AC-CORR-005), rigid-body safe (no divide-by-zero
  warnings, `±inf` reported instead).
- `pairing.py`: added the MS-2.3 frequency penalty `β·|Δf|/f_test` on the MAC score, and made
  the MAC threshold and frequency window act on the raw MAC so the penalty can only rank
  candidates, never reject them.
- `report.py` (new): schema-versioned `CorrelationReport` (v1.0) carrying the summary, pair
  table, MAC matrix, COMAC and settings, serializable with `to_json()` for CLI/CI artifacts,
  plus `correlate_modal_data(fe_result, test_data)` — the ARCHITECTURE §5.2 pipeline
  (align → MAC → pair → report) over any objects exposing `frequencies`/`shapes`/`dof_map`.
- Added `tests/test_correlation.py` (35 tests) driven by `tests/fixtures/test_modes.yaml`:
  alignment (scrambled sensor order, unknown channel, orientation signs, selection operator),
  MAC invariance to scaling/sign/complex phase, autoMAC exposing a sensor set that cannot
  separate two modes, mass-weighted MAC and orthogonality on a non-unit mass matrix, COMAC
  fault localization, pairing (shuffled order, missing test mode, uncorrelated mode left
  unpaired, frequency-only pairing, tolerance window, frequency penalty, Hungarian optimality
  against brute force), frequency-error conventions, gates, JSON round trip, the full fixture
  pipeline through `openfemlab.io`, and a noisy-measurement case.
- **Correlation metrics achieved on the fixture** (4-DOF model vs 3-channel test, `node_2`
  uninstrumented): all three modes paired 0↔0, 1↔1, 2↔2 with **MAC = 1.000000000000000
  (min = mean = max, gate 0.95)**; max off-diagonal MAC 0.1111 (three sensors no longer see
  the modes as orthogonal); COMAC = [1, 1, 1]; frequency errors −0.990 / +1.010 / −1.961 %,
  max |Δf| 1.961 %, rms 1.396 %, mean 1.320 % — passes the MS-4.2 gate (MAC ≥ 0.95,
  |Δf| ≤ 2 %). Same numbers through the `DofMap` pipeline (min MAC 0.999999999999999,
  3 correlation DOFs, 1 unmatched FE DOF). With 2 % shape noise and 0.2 % frequency noise the
  pairing is unchanged and min MAC stays above 0.95.
- Verified on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1: `tests/test_correlation.py` 35 passed,
  full suite 157 passed. `ruff check src/openfemlab/correlation tests/test_correlation.py`
  clean.
- Resolved by A16: `cli/analysis.py` contains only solver/result adapters, while the
  `correlate` command delegates DOF alignment, MAC, mode pairing, COMAC, summaries, and
  serialization to the public `openfemlab.correlation` report pipeline.

#### A04 — Sensitivity Kernel, Updater Wiring & Updating Test Suite
- Completed `updating/sensitivity.py` against MS-3.3. On top of the Fox–Kapoor eigenvalue
  sensitivity it now carries `mode_shape_sensitivity` (modal-superposition eigenvector
  derivatives, with the degenerate-cluster contributions dropped and warned about, since
  only a cluster's subspace is differentiable), the induced `mac_sensitivity`
  `dMAC_ii/dp`, and `frequency_sensitivity` folding in the λ → Hz conversion. This makes
  the MAC residual block differentiable analytically, not just by finite differences.
- Added `updating/scaling_model.py`: `ScalingModel`, the parametric model for the
  substructuring form `K(θ) = K_0 + Σ θ_j K_j`, `M(θ) = M_0 + Σ θ_j M_j`. Because the
  assembly is affine, `∂K/∂θ_j` *is* the contribution matrix, so the whole sensitivity
  matrix costs one eigensolve per iteration instead of one per parameter. It is callable
  (so it drops straight into `ModelUpdater`), restricts reported shapes to the sensor DOFs,
  solves through `solver.modal.ModalSolver` when the core stack is importable and through a
  dense `scipy.linalg.eigh` otherwise, and exposes `sensitivity_function(names)` matching
  the updater's analytical-Jacobian signature.
- Repointed `updating/updater.py` at the correlation layer as A06 restructured it
  (`mac.mac_value`, `pairing.pair_modes`, `summary.correlation_summary`).
- **Collision recovery.** The updating stack was unimportable when A04 started: the
  correlation rewrite had removed the pairing and summary API that `metrics.py` and the
  updater build on, `updating/parameters.py` had been replaced by a declaration-only
  `Parameter`, and the root `__init__` eagerly imported a `core.model` that no longer
  exported `DOF`. Rather than restore the old files, A04 moved the layer to where the
  rewrite was heading: added `correlation/pairing.py` (the module the new `mac.py` already
  type-references) and `correlation/summary.py`, merged the declarative `Parameter`
  alongside the mutable `UpdatableParameter`/`ParameterSet` the optimiser iterates on, and
  made top-level names resolve lazily (PEP 562) so a leaf subpackage imports without
  dragging in the whole core stack. A06 then built `report.py` on top of `summary.py`.
- Added `tests/test_updating.py` (28 tests) as twin experiments on a grouped fixed-free
  spring/mass chain: measurements are generated from a detuned truth model, the updater
  starts from the nominal one, so recovery is checked against the truth and not only
  against a shrinking residual.
- **Results.** 10-DOF chain, 4 stiffness groups, truth `θ = (0.80, 1.25, 0.95, 1.10)`,
  6 modes: max |Δf| **3.561 % → 2.1e-12 %**, min MAC **0.857 → 1.000**, cost
  1.27e-3 → 2.3e-28 in 5 iterations, every factor recovered to machine precision.
  With only 5 of 10 DOFs instrumented and the MAC residual active: max |Δf|
  **1.968 % → 4.2e-13 %**, min MAC **0.936 → 1.000** in 7 iterations. With 0.5 % frequency
  noise and no shapes: 94.2 % cost reduction, all four factors within 0.045 of the truth
  (no overfitting). Analytical sensitivities match central differences to **< 1e-6
  relative** (AC-UPD-001) for eigenvalues and to 1e-6 absolute for eigenvectors and
  `dMAC/dp` (AC-UPD-002). Underdetermined (6 parameters, 2 modes): iterates stay inside
  the bounds and the cost is monotone over accepted steps (AC-UPD-005).
- **Two identifiability facts the suite now records rather than papers over.** Eigenvalues
  only see `K/M`, so leaving every stiffness *and* every mass group free admits a
  one-parameter family of exact fits — the updater reaches cost 4.3e-26 and lands on the
  truth scaled by a single common factor (0.9738 across all five parameters). Fixing one
  mass anchors the scale and the truth is recovered exactly. Likewise two collinear
  parameters are redundant, not fatal: LM damping alone converges to machine precision and
  only their sum is observable (2.400 ± 1e-3 recovered from 1.20 + 1.20).
- Verified on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1: `tests/test_updating.py` **28
  passed** (0.31 s), full suite **157 passed** (0.80 s) — including the
  `test_truncated_mode_shape_sensitivity` case A06 saw failing in flight, now restated as
  the exact property (a truncated derivative is the mass-orthogonal projection of the exact
  one onto the retained subspace) and passing to 1e-12. `ruff check` clean on
  `src/openfemlab/updating`, `src/openfemlab/correlation`, `tests/test_updating.py` and
  `src/openfemlab/__init__.py`.
- Open for the orchestrator: the updater's analytical-Jacobian path is used only when the
  residual has no shape block (it falls back to finite differences otherwise), even though
  `mac_sensitivity` now makes the MAC rows analytic — wiring the two together is a cheap
  Round 2 win. MS-3.5 Bayesian MAP and MS-3.6 automatic parameter selection
  (QR-pivoting collinearity screening) are still unimplemented.

#### A12 — GAP-03 UFF 55/58 Reader
- Added `io/uff.py`, a dependency-free ASCII UFF/UNV reader for dataset 55 normal-mode
  shapes and dataset 58 functions at nodal DOFs. Dataset 55 supports real and complex
  nodal values with arbitrary values-per-node; dataset 58 supports real/complex ordinates
  and even/uneven frequency abscissae.
- Exposed `read_uff`, `read_uff_modes`, and `read_uff_functions` plus typed `UFFMode` and
  `UFFFunction` records through `openfemlab.io`. Mixed UFF files skip unrelated datasets;
  malformed supported records and unsupported binary dataset 58b raise `FormatError`.
- Added five synthetic tests covering fixed-width dataset headers, normal-mode metadata and
  shapes, complex FRFs, uneven real abscissae, mixed datasets, incomplete records, and the
  58b boundary. Focused IO tests: **18 passed**; full suite: **166 passed**. Touched files
  pass Ruff.
- Remaining GAP-03 scope: datasets 2411/2412, Nastran BDF/OP2, meshio conversion, UFF
  writing, and binary 58b.

#### A18 — GAP-03 Minimal Nastran BDF Reader
- Added `io/nastran.py`, a dependency-free ASCII BDF reader for free-field and small
  fixed-field `GRID`, `CROD`, and `MAT1` cards, exposed as `read_bdf` and
  `read_nastran`. Unsupported cards are skipped and standard Nastran implicit exponents
  are accepted.
- Converted directly to `NeutralModel`: `GRID` labels and coordinates become the node
  arrays, `CROD` connectivity becomes a `ROD2` block, property ids remain aligned with
  that block, `MAT1` records populate neutral materials, and source format plus external
  element ids are retained as metadata. `MAT1` derives a missing elastic constant from
  the other two.
- Added six tests for path and stream input, free and fixed fields, comments and bulk-data
  boundaries, implicit exponents, unsupported cards, unknown nodes, unresolved coordinate
  systems, and malformed-card diagnostics. Focused reader tests: **6 passed**; combined
  native/UFF/Nastran IO tests: **24 passed**; touched files pass Ruff. The concurrent full
  suite run reached **191 passed, 1 failed** in an unrelated uncommitted CLI regression
  (`test_update_recovers_the_identifiable_parameter_ratio` emitted a progress line before
  JSON).
- Remaining GAP-03 scope: UFF 2411/2412, broader BDF cards and coordinate systems, OP2,
  meshio conversion, UFF writing, binary 58b, and Nastran large-field/continuation cards.

#### A22 — CLI JSON Output Regression Backfill
- Confirmed the A18 failure is fixed by routing CLI notes and warnings to stderr whenever a
  command emits JSON or YAML, leaving stdout as one parseable document.
- The end-to-end CLI regression suite covers modal, correlate, and update document output,
  including the previously failing identifiable-parameter update case.
- Verified the complete suite on the integrated working tree: **192 passed**.

#### A25 — CLI Subprocess Coverage Backfill
- Extended `tests/test_cli.py` across the actual process boundary with
  `python -m openfemlab.cli` runs for `modal`, `correlate`, and `update`.
- The process tests generate their model, measured-data, and updating-configuration fixtures
  through `examples/02_model_updating_workflow.py`, parse each command's stdout as JSON, and
  assert successful exit statuses plus correlation's intentional acceptance-gate exit 3.
- Child processes explicitly import the current checkout, preventing an editable installation
  from a sibling worktree from silently testing stale code.
- Verified on Python 3.12: `tests/test_cli.py` **22 passed**; complete suite **195 passed**.

#### A16 — CLI Correlation Kernel Reconciliation
- Confirmed the pulled integration branch no longer contains duplicate `mac_matrix`,
  `pair_modes`, or `common_rows` implementations in `cli/analysis.py`; correlation
  numerics have one owner in `openfemlab.correlation`.
- Added a CLI seam regression that replaces the public correlation entry point and verifies
  the `correlate` command forwards all alignment and pairing settings to that kernel.
- Verified the regression in isolation and the complete suite: **167 passed**. The touched
  CLI module and regression test pass Ruff.

#### A20 — Project README
- Replaced the placeholder README with an OpenFEMLab overview and an alpha-status notice.
- Documented modal analysis, FE/test correlation, sensitivity-based updating, the six-stage
  correction workflow, and native/UFF/Nastran IO, including the supported format subsets.
- Added installation and Python quickstart instructions, reproducible CLI examples for
  modal/correlate/update, contributor test and lint commands, and single-threaded modal and
  updating benchmark commands.

#### A10 — Sparse Assembly, Factorization Cache & Vectorized Sensitivity
- Reworked `core/assembly.py` around preallocated COO buffers and a single shared topology
  traversal for `K` and `M`; coordinates, global DOF maps, rows, and columns are no longer
  rebuilt in two separate element passes. All-zero element matrices skip COO conversion.
- Added per-`ModalSolver` reduced-problem and shift-invert LU caches. Repeated sparse solves
  reuse `K - sigma M`; `cache_factorization=False` supports cold-run comparisons and
  `clear_cache()` explicitly invalidates caches after an in-place matrix change.
- Vectorized Fox–Kapoor eigenvalue/eigenvector and MAC sensitivities over all requested
  modes, preserving complex arithmetic and adding native sparse `dK/dp`, `dM/dp`, and mass
  matrix support.
- Updated the modal and updating benchmarks to report before/after medians. With one BLAS
  thread and seven repetitions: repeated spring-chain solves improved at 10/100/1000 DOF
  by **1.17x / 1.11x / 1.14x**, and the 100-DOF five-iteration updating loop improved
  **35.301 ms -> 7.904 ms (4.47x)** using exact vectorized sensitivities.
- Added `tests/probes/probe_performance_regression.py` with numerical-equivalence and minimum
  speed gates. Measured medians: 2,000-DOF sparse assembly **26.302 -> 19.331 ms (1.36x)**;
  repeated 1,600-DOF sparse solve **12.270 -> 9.449 ms (1.30x)**; 240-DOF, 24-mode,
  12-parameter eigenvalue sensitivity **1.829 -> 0.678 ms (2.70x)**. All probe gates pass.
- Added focused guards for one-pass assembly, LU reuse/bypass/invalidation, sparse derivative
  matrices, and complex vectorized MAC derivatives. Focused core/modal/updating/performance
  suite: **94 passed**; touched files pass Ruff.

#### A07 — Rich CLI: `modal`, `correlate`, `update`
- Built out `src/openfemlab/cli/` behind the `openfemlab` console script already declared in
  `[project.scripts]`: `main.py` (registry + global `--quiet`/`--no-color`/`--traceback`),
  `console.py`, `spec.py`, `analysis.py` and a `commands/` package with one module per
  command. Added `cli/__main__.py` so `python -m openfemlab.cli` works where the script is
  not on PATH.
- `spec.py` defines the CLI's project file, the piece the platform was missing: the neutral
  interchange model cannot carry supports or concentrated masses, so a modal run cannot be
  reproduced from a `NeutralModel` alone. A spec is a JSON/YAML mapping with a `mesh` block
  (`bar`, `beam`, `chain`, `truss` over `mesh.simple`, or `custom` for explicit
  nodes/elements), named `materials`/`sections` tables, plus `supports`, `point_masses` and
  `rotary_inertias`. `lookup`/`scaled` address individual numbers by dotted path
  (`materials.steel.E`, `mesh.elements.2.stiffness`), which is what lets updating parameters
  point at a document rather than at Python objects.
- `console.py` renders rich tables when the `[cli]` extra is installed and aligned plain text
  otherwise. Notes and warnings go to stderr whenever a command emits JSON or YAML, so
  `--format json` output stays pipeable — this fixes the interleaving A18 observed.
- `commands/modal.py`: frequencies, angular frequencies, periods, modal masses, participation
  factors, effective and cumulative mass fractions, rigid-body flags, condensation and
  orthogonality diagnostics. The participation direction defaults to the most excited
  translational axis (defaulting to the first DOF reports a ~1e-31 effective mass for a
  bending model). `-o` writes the full native `ModalResult` including shapes and DOF map.
- `commands/correlate.py`: the FE side accepts either a stored modal result or a model spec,
  which is then solved on the fly. All numerics delegate to
  `correlation.correlate_modal_data` — no MAC, pairing or COMAC code lives in the CLI.
  Exposes `--pairing greedy|optimal|frequency`, `--mac-threshold`, `--frequency-tolerance`,
  `--freq-penalty`, `--partial-dofs`, `--matrix`, and the CI gates `--require-mac` /
  `--require-frequency` (exit 3).
- `commands/update.py`: a config naming a model spec, dotted-path parameters with bounds and
  kind, a measured target (`target.file` or inline frequencies) and any `UpdatingOptions`
  field. Each evaluation rescales the spec from its nominal values and re-solves, so the run
  is idempotent; the updated spec is written back in the same format and feeds straight into
  `openfemlab modal`. Shape residuals align FE and test DOFs through
  `correlation.align_dof_maps`. `--strict` exits 4 when the loop does not converge.
- Added `examples/02_model_updating_workflow.py`: writes the model spec, synthesises a modal
  test (5 UY accelerometers on a 21-node cantilever, truth `E×0.88`, `A×1.05`), correlates,
  updates, correlates again, and emits the equivalent shell session plus a ready-to-run
  `updating.yaml`.
- **Results on that workflow.** As designed: `f₁ = 8.35517 Hz` against the analytic
  8.3552 Hz; all 4 modes paired with min MAC 1.000000 and a uniform **+9.233 %** frequency
  bias. After updating: cost **1.705e-2 → 2.573e-20** (100 %) in **4 iterations / 21 model
  evaluations**, max |Δf| **9.233 % → 1.33e-8 %**. Bending frequencies only constrain `E/A`,
  and the recovered ratio 0.9122/1.0884 = **0.8381** matches the truth 0.88/1.05 = 0.8381 to
  4 decimals — the suite records that identifiability limit instead of asserting the
  individual factors.
- Added `tests/test_cli.py` (19 tests): spec building and error paths, dotted-path scaling
  leaving the source document untouched, the analytic cantilever frequency through the
  command, JSON reports, the written modal result reloading through `openfemlab.io`, the
  default participation direction, correlation against a spec and against a stored result,
  both acceptance-gate exit codes, the full update-then-recorrelate loop, and unknown
  option/target diagnostics.
- **Import-conflict status.** At start `openfemlab.io` could not import (`_native.py` still
  wanted `ElementType`/`Property` from `core.model` after the `core.neutral` rename) and
  `correlation`/`updating` were mid-rewrite. A05/A08/A06/A04 landed those fixes while this
  agent was writing; verified afterwards that `core`, `mesh`, `solver`, `modal`,
  `correlation`, `updating`, `io`, `optimization` and `cli` all import cleanly, and adopted
  the landed `correlate_modal_data`/`align_dof_maps` instead of keeping the CLI-local pairing
  written against the earlier API.
- Verified on Python 3.12: full suite **192 passed**; the README CLI session
  (modal → correlate → update → recorrelate) reproduces exit codes 0 / 3 / 0 / 0. `ruff check`
  clean on `src/openfemlab/cli`, `examples/02_model_updating_workflow.py` and
  `tests/test_cli.py`.

#### A15 — GAP-01 `ModalResult` Contract Unification (backfill for R1-F1)
- **Closed the last half of the GAP-01 split-brain.** `solver/modal.py` still defined its own
  `ModalResult` (`eigenvalues` / `mode_shapes` / `free_dofs` / `system` /
  `num_condensed_dofs`, plus the generalized quantities) while `core/results.py` defined an
  incompatible one (`frequencies` / `shapes` / `dof_map` / `meta`). Nothing typed as one
  worked with the other, so every producer→consumer hop went through a hand-written adapter
  (`cli/analysis.as_modal_result`, `modal/eigen.solve_modes`), and a solver result silently
  lost its eigenvalues, normalization and assembled system on the way to `io`.
- `core.results.ModalResult` is now the single contract, and it is a superset rather than a
  compromise. It takes the spectrum as **either** `frequencies` [Hz] **or** `eigenvalues`
  [ω²] and the shapes under **either** `shapes` or `mode_shapes` — exactly one of each pair,
  the other derived — and carries the optional solver provenance (`free_dofs`,
  `normalization`, `system`, `num_condensed_dofs`) that backs `modal_masses`,
  `modal_stiffnesses`, `orthogonality_error()`, `participation_factors()`,
  `effective_masses()`, `rigid_body_modes`, `periods` and `summary()`. Storing the
  eigenvalues as given keeps the fixture spectra bit-comparable (the previous
  λ → f → λ round trip would have introduced ~1e-16 relative drift into assertions held at
  1e-12).
- `dof_map` became optional, because modes of bare `(K, M)` matrices genuinely have no nodal
  interpretation — `ModalSolver.from_matrices` labels DOFs `dof0..dofN`, which no `DofMap`
  can parse. `ModalResult.with_dof_map(dof_map, meta=...)` attaches one later without
  recomputing or dropping anything, so a solver result reaches `io` and `correlation` as
  itself. `io.write_modal_result` now raises `FormatError` naming `with_dof_map()` instead of
  failing with `AttributeError: 'NoneType'`.
- `solver/modal.py` re-exports `ModalResult`, `NORMALIZATIONS` and `RIGID_BODY_TOL` (137
  lines of duplicate class deleted); both adapters collapsed into single `with_dof_map()`
  calls; `cli/analysis.py` no longer needs its `SolverModalResult` alias.
- Added `tests/test_result_contract.py` (17 tests) as the regression that pins the merge:
  `core.results`, `solver.modal` and `openfemlab.solver` must expose the *same class object*;
  `result.shapes is result.mode_shapes` and `n_modes == num_modes`; the frequency↔eigenvalue
  pair round-trips in both directions to 1e-15; an ambiguous or missing spectrum/shape
  argument is rejected; the generalized quantities still hold (unit modal masses, φᵀKφ =
  λ·mⱼ, orthogonality error < 1e-9, effective masses summing to the model mass); a
  system-less result explains why it cannot expand; and a solver result travels through
  `with_dof_map()` into `write_modal_result`/`read_modal_result` and into
  `correlate_modal_data` (min MAC 1.0) without being rebuilt.
- Updated `docs/ARCHITECTURE.md` §11.3 and the `docs/SOTA_GAP_ANALYSIS.md` GAP-01 entry,
  which both still listed the duplication as an open Round 2 item; the capability table row
  for participation factors now points at `core/results.py`.
- Verified on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1: full suite **212 passed** (5.4 s), up
  from the 166 collected when this agent started and the 192 of the A17 conclusion; both
  `examples/` scripts and the CLI session still run. `ruff check` clean on every touched
  file.
- **Working-tree hazard, again.** Mid-run a concurrent agent switched the shared `/workspace`
  checkout onto `cursor/dynamics-damping-frf-9500`, so the unification commit landed there
  and was then committed on top of; it was recovered by cherry-picking through a detached
  worktree at `/tmp/gap01`, which is also where the rest of this task ran. Agents editing the
  shared tree should hold a private worktree, as A14/R1-O2 already do.

#### A13 — M4 Simulation-Correction Workflow (backfill for A01)
- Added `src/openfemlab/workflow/`, the MS-4 state machine that turns the M1/M2/M3 engines
  into the productized loop: `S1 BASELINE → S2 PAIRING → S3 DIAGNOSIS → S4 UPDATING →
  S5 REANALYSIS → S6 VALIDATION`, driven by `run_correction(model, test, sensor_map,
  params, *, gates, holdout, seed)` / `CorrectionWorkflow`.
- Every stage carries its gate and every gate failure is machine-readable: the pipeline
  stops with a `StageGateError`-shaped `{stage, reason, message, details}` block
  (`baseline_solve_failed`, `insufficient_modes`, `insufficient_pairs`,
  `no_identifiable_parameters`, `no_fitted_targets`, `updating_diverged`, `gate_failed`),
  the stages behind it are recorded `SKIPPED`, and the report is marked `FAIL` — a partial
  run can never read as a pass (AC-WORK-004). `strict=True` raises instead of returning.
- `workflow/selection.py` implements the MS-3.6 pre-updating diagnosis on the initial
  relative sensitivity matrix: columns are ranked by norm, then frozen for zero
  observability (`‖S_j‖ < 1e-3·max‖S‖`), for collinearity (column cosine > 0.99) or for
  pushing the retained subset past `κ = 1e6`. Nothing is ever frozen silently — each
  parameter carries its reason, partner and cosine into the report.
- `workflow/gates.py` holds the MS-4.2 limits (MAC ≥ 0.95, |Δf| ≤ 1 %, ≥ 3 pairs, bounds,
  and a *warning*-severity plausibility check at ±50 %) plus `HoldoutSpec`: reserved modes
  (explicit, or the N highest-frequency paired ones) are dropped from the S4 residuals and
  reserved channels are zero-weighted in the MAC, then both are evaluated at S6 against
  MAC ≥ 0.9 and "no worse than baseline".
- `workflow/report.py` is the schema-versioned (`1.0`) `CorrectionReport`: stage log,
  baseline/final `CorrelationReport`s, held-out block, iteration history, parameter table
  (initial/final/bounds/change/selected/freeze reason/σ_post), gate results, settings,
  environment (package versions + seed) and per-stage wall time — `to_dict()`, `to_json()`,
  `save()` and a printable `report()`. Wall times sit behind `include_timing`, so
  `to_dict(include_timing=False)` is exactly the content two runs must reproduce.
- σ_post comes from the linearized least-squares covariance `C ≈ σ²(JᵀJ)⁻¹` of the final
  Gauss-Newton Jacobian, so a deterministic run still reports parameter uncertainty
  without the Bayesian path.
- Added `tests/test_workflow.py` (38 tests) over a grouped 8-DOF spring/mass chain twin.
  Key results: a model detuned to θ = (1.30, 0.80, 1.10) is recovered to 1e-4 relative with
  min MAC 1.0 and max |Δf| 0 % from a 4.13 % / 0.89-MAC baseline (AC-WORK-001); two runs
  with the same seed agree on every reported number to 1e-12 (AC-WORK-002); a duplicated
  parameter is detected at cosine 1.0000 and frozen with the run still converging
  (MS-3.6/AC-UPD-007); and an overfitting run — eight parameters fitted to four targets
  carrying 3 % frequency noise — passes *every* in-sample gate (min MAC 0.9985, max |Δf|
  0.75 %) while the reserved mode degrades from 0.0096 % to 0.7522 %, so only the held-out
  gate catches it (AC-WORK-003).
- Verified on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1: full suite **250 passed** (10 s);
  `ruff check` clean on every new file.
- Hit the same working-tree hazard A15 reports: a concurrent agent switched `/workspace`
  onto `cursor/dynamics-damping-frf-9500` and reset over the package commit mid-run, so
  both commits were recovered by cherry-picking into a detached worktree at `/tmp/a13wt`.
  `workflow/sensors.py` had already been swept into another agent's `e031b5a` before that.

#### A24 — Round 2 Plan (backfill for A22)
- Wrote `.agent_workspace/ROUND2_PLAN.md`: prioritized Round 2 backlog derived from
  `docs/SOTA_GAP_ANALYSIS.md` (gap register §4, sequencing §6) and the Round 1
  conclusion, with every task linked to its binding gates in
  `docs/ACCEPTANCE_CRITERIA.md` / `docs/MODULE_SPEC.md` anchors.
- Reconciled the plan against work landed since the audit so tasks are targeted, not
  duplicative: GAP-01 largely closed (unified `ModalResult`, 192-test green suite),
  GAP-03 partially closed (UFF 55/58, minimal BDF), GAP-14 closed (CLI), GAP-10/09
  partial; flagged the in-flight `cursor/dynamics-damping-frf-9500` branch so R2-T01
  integrates it instead of forking a second dynamics implementation.
- Core backlog: T01 dynamics/FRF, T02 3D elements, T03 SEREP/TAM, T04 Bayesian MAP,
  T05 meshio; supporting T06–T09 (updating depth incl. P0 AC-UPD-007, optimization
  backend, R1-O2 reconciliation, CI exit hardening). Three parallel waves with a
  spec-first rule: new AC IDs (AC-DYN/ELEM/IO-*) land in the criteria doc, module spec,
  and registry in the same commit, enforced by the registry consistency tests.
- Defined the Round 2 exit bar: all P0+P1 registry criteria `verified` (P1 blocks
  Round-2 sign-off per AC §1.2), new-track criteria at least `implemented`, and two
  headline demos — measured UFF-58 FRF vs synthesized FRF via FRAC/FDAC through the
  CLI, and an imported 3D mesh re-analyzed internally.

#### A21 — First P0 Acceptance Batch (backfill for A10)
- Turned the first six P0 criteria of `docs/ACCEPTANCE_CRITERIA.md` from registry rows
  into executable gates under `tests/acceptance/`: `test_modal.py` (AC-MODAL-001..003),
  `test_correlation.py` (AC-CORR-001..002) and `test_updating.py` (AC-UPD-001), on the
  suite paths the registry already declared. 34 acceptance tests, selectable with
  `pytest -m acceptance`.
- Added `tests/acceptance/_support.py`: the `@criterion("AC-…")` tag (rejects IDs the
  registry does not define, at collection time), the fixture loaders, the closed-form
  spectra (fixed-free / fixed-fixed chains, Euler–Bernoulli cantilever) and the affine
  spring-chain group contributions used as exact `∂K/∂θ`, `∂M/∂θ`.
- **Wired status to evidence.** The six criteria are now `implemented`, and two new
  registry tests make that claim falsifiable in both directions: a criterion may only
  leave `specified` when the suite it names carries a test tagged with its ID, and every
  tag must resolve to a criterion that names that suite. Recorded as enforcement item 6
  in the criteria document; `pyproject.toml` registers the `acceptance`/`criterion` marks.
- **AC-MODAL-001** (gate: fixtures ≤ 1e-10 rel., beam ≤ 0.5 %): 2-DOF **2.2e-16**, 10-DOF
  chain **2.8e-15** against the closed forms (the stored fixture spectra are checked
  against the same closed form, so the data cannot drift either). Cantilever, 40 elements:
  per-mode error **5.5e-8 / 1.3e-5 / 1.0e-4 / 3.9e-4 / 1.1e-3 %** — 460x inside the gate,
  and the discretization is verified to converge from above.
- **AC-MODAL-002** (gate: 1e-8 rel. freq., paired MAC ≥ 1 − 1e-10): 240-DOF chain, 10
  modes, dense vs shift-invert Lanczos — frequency difference **6.2e-12**, worst paired
  MAC **1 − 1.6e-15**, and the pairing is verified to be the diagonal (no crossings).
  MS-1.2's optional `lobpcg` backend is not exposed by `ModalSolver`; the backend table
  picks up a `backend=` keyword automatically if one lands, so the pairwise comparison
  extends without touching the suite.
- **AC-MODAL-003** (gate: 1e-8): `‖ΦᵀMΦ − I‖_max` over four models × both backends, worst
  **1.3e-15** (chain-240 dense); includes the cantilever, whose massless rotations are
  condensed and recovered, and the consistent (non-diagonal) beam mass matrix.
- **AC-CORR-001** (gate: 1e-8): mass-weighted self-MAC defect **2.2e-16** on the fixtures
  and on the beam. The beam makes the gate real — its *unweighted* off-diagonal MAC
  reaches **0.327**, so only the mass weighting recovers the identity. The unweighted
  diagonal is 1 to **2.2e-16**, not bitwise (clipping bounds MAC ≤ 1 from above but the
  ratio of two differently accumulated dot products can land one ulp below); the suite
  asserts 1e-15, one place where the prose "exactly" in the criteria detail is stricter
  than float arithmetic allows.
- **AC-CORR-002** (gate: 1e-12): 8 seeded draws scaling every column of either mode set by
  factors spanning ±10⁻³..±10³ against a non-trivial reference MAC (2.3e-6 .. 0.970);
  worst deviation **6.7e-16**. Pure sign flips are asserted **bitwise identical**.
- **AC-UPD-001** (gate: 1e-6 rel.): 10-DOF chain, 3 stiffness + 2 mass groups, 6 modes,
  central FD with `h = 1e-6·p_j,0` — max relative error **1.4e-7** at θ = 1 and **5.2e-8**
  at a detuned point. The parameterization is pinned to the fixture (contributions sum
  back to its exact `K`/`M`) and the FD comparison is guarded against a vanishing
  denominator, so the relative gate cannot pass by accident.
- Verified on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1: `tests/acceptance` **46 passed**
  (34 acceptance + 12 registry), full suite **286 passed** (4.4 s) on `b5a0099`; Ruff clean.
- Same working-tree hazard A13/A15 report: a concurrent agent switched `/workspace` onto
  `cursor/dynamics-damping-frf-9500` mid-run and the tracked-file edits were lost, so the
  batch was finished and pushed from a detached worktree at `/tmp/a21`.
- Open for the orchestrator: 29 criteria remain `specified`. The next batches are
  AC-MODAL-004..007/009 and AC-CORR-003..005/007..008 (engines exist, tests are the only
  gap), then AC-UPD-002..005/007 and the M4/M5 suites — `tests/test_workflow.py` already
  demonstrates AC-WORK-001..004 numerically but is not tagged, so those criteria stay
  `specified` until an `tests/acceptance/test_workflow.py` claims them.

#### A29 — A13/Dynamics Integration Backfill
- Reconciled the feature branch with the completed A13 workflow and later A14/A21 updates,
  preserving both A13's workflow record and A24's Round 2 plan during the progress-file
  conflict, and pushed the resulting feature tip.
- Rebased `cursor/dynamics-damping-frf-9500` onto that feature history. Git skipped the
  already-landed workflow-test patch, so `tests/test_workflow.py` remains paired with the
  complete `openfemlab.workflow` package instead of leaving tests without their consumer.
- Preserved the workflow, damped-dynamics, and optimization package-root exports together.
  The final branch includes the M4 workflow, reconciled updating stack, P0 acceptance batch,
  structural sizing contracts, and GAP-04/05 damped dynamics/FRF implementation.
- Verified the final integrated committed tree with full `pytest`: **430 passed, 0 failed**
  (12.35 s, Python 3.12).

#### A19 — GAP-04/05 Damped Dynamics: Damping, Complex Modes, FRF Synthesis
Delivered on branch `cursor/dynamics-damping-frf-9500` — the branch R2-T01 is told to
integrate rather than fork.

- Added `solver/dynamics.py`, the chain from undamped normal modes to a measurable FRF —
  the P0 gap A03 recorded as "everything downstream of undamped real modes is missing".
- **Damping models.** `RayleighDamping` (`C = αM + βK`) with the exact two-anchor fit
  (`from_frequencies`), a least-squares fit over any number of measured modes
  (`from_modal_damping`), mass-/stiffness-only constructors, and the minimum of the ratio
  curve (`√(αβ)` at `ω = √(α/β)`). `ModalDamping` carries explicit per-mode ratios;
  `modal_damping_matrix` realizes them physically as `C = MΦ diag(2ζω/m) ΦᵀM`.
  `StructuralDamping` gives the hysteretic `K(1+iη)` plus an equivalent viscous matrix once
  a reference frequency is named. `proportionality_index`/`is_proportional` are the
  Caughey-O'Kelly classical-damping test.
- The models expose `modal_coefficients(ω) = 2ζω` alongside `damping_ratios(ω)`; for
  Rayleigh that is `α + βω²`, so the FRF denominator stays finite at a rigid-body mode
  where `ζ → ∞`.
- **Complex modes.** `complex_modes` solves `(s²M + sC + K)φ = 0` through the *symmetric*
  state-space linearization `A = [[C, M], [M, 0]]`, `B = [[K, 0], [0, −M]]`, keeping one
  member of each conjugate pair and both members of an overdamped real pair.
  `ComplexModalResult` reports undamped/damped frequencies, damping ratios, the quadratic
  residual per mode, the modal phase collinearity (MPC), a best real approximation, and the
  state-space constant `a_r = φᵀCφ + 2sφᵀMφ`, so residues stay correct under any
  normalization (`"state"` → unit modal-A, `"max"`, `"none"`).
- **FRF synthesis.** `modal_frf` (real-mode superposition, accepting a `ModalResult`, an
  `(ω, Φ)` pair, or a `ComplexModalResult`), `complex_modal_frf` (residue superposition),
  `direct_frf` (per-line inversion of `Z = (1+iη)K − ω²M + iωC`, dense or sparse LU above
  400 DOFs), `harmonic_response` for constant or frequency-dependent loads, and
  `residual_flexibility` for mode-truncation correction. `FrequencyResponse` carries the
  `(nf, n_out, n_in)` matrix with receptance/mobility/accelerance conversion and
  drive-point/row/column accessors.
- **GAP-05 opener.** `frac` (Frequency Response Assurance Criterion) and `fdac` (Frequency
  Domain Assurance Criterion matrix) are the platform's first FRF-domain correlation metrics.
- **Results.** With every mode retained, real-mode superposition reproduces the direct
  inversion to **2.1e-14** relative on a 6-DOF Rayleigh-damped chain, and complex-mode
  residue superposition to **2.4e-12** on the *non-proportionally* damped version of the
  same model (proportionality index 0.66, MPC 0.963–1.000, max quadratic residual 3.7e-13).
  Under proportional damping the complex modes stay monophase (MPC = 1.000) and reproduce
  the undamped spectrum to **8.0e-14** relative, with damping ratios matching the Rayleigh
  curve to **7.2e-15** absolute. Truncating to 2 of 6 modes and adding the residual
  flexibility restores the static response to **4.3e-16** relative and cuts the in-band
  error **19.2×**. Closed-form checks pass exactly: SDOF poles `s = −ζω₀ ± iω₀√(1−ζ²)`,
  receptance `1/(k − ω²m + iωc)`, resonant amplitude `1/(ω₀c)`, and the overdamped `ζ = 2`
  case (two real poles with `s₁s₂ = k/m`, `s₁+s₂ = −c/m`) whose residue synthesis also
  matches the direct solve to 1e-10.
- Added `tests/test_dynamics.py` (**82 tests**, 0.3 s): damping fits and their failure
  modes, classical/non-classical discrimination, complex modes against closed forms and
  against the undamped solver, MPC properties, the three FRF paths against each other and
  against analytic references, reciprocity, response-type algebra, truncation residuals,
  harmonic response, the `FrequencyResponse` container, FRAC/FDAC, and a full
  model → assembly → modes → damping → FRF integration case.
- Verified on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1: `tests/test_dynamics.py` 82 passed;
  full repository suite on the integrated branch **430 passed**. `ruff check` clean on
  `src/openfemlab/solver`, `src/openfemlab/__init__.py` and `tests/test_dynamics.py`.
- **Known limitation, deliberately surfaced.** The state-space pencil is singular when a
  retained DOF is massless, and unlike the undamped case there is no exact condensation once
  `C` is present, so `complex_modes` raises with that instruction instead of returning
  garbage (covered by a lumped-mass beam test). The undamped `ModalSolver` still condenses
  automatically.
- Hit the shared-working-tree hazard A13/A15 also report: concurrent checkouts reverted the
  `__init__.py` export wiring and these progress notes twice mid-run, so the last steps were
  finished in a detached worktree at `/tmp/a19wt`. All A19 commits are on the remote branch.
- Open for the orchestrator: FRAC/FDAC currently live in `solver/dynamics.py` beside the FRF
  types; if `correlation/` grows an FRF section they should be re-exported from there rather
  than reimplemented. Remaining GAP-05 scope is an FRF residual inside `updating/updater.py`;
  GAP-04 still lacks transient (time-domain) response.

#### A02 — M5 Optimization Design & Stubs (backfill for A05)
- Designed and landed `src/openfemlab/optimization/` (spec MS-5, GAP-12): a two-level
  architecture where a structural layer (models, parameters, responses) lowers into a
  plain bound-constrained vector NLP (`OptimizationProblem`) that swappable backends
  consume — no FE concept leaks below the lowering line. Full design rationale, reuse
  map, gradient-route table and AC-OPT mapping in the new `docs/OPTIMIZATION.md`.
- **Size hooks / updating integration:** sizing variables *are* the updating
  parameters — `DesignSpace` wraps `updating.parameters.ParameterSet` (bounds, log
  design-space mapping, FD steps) and appends `ShapeVariable` amplitudes, so a model
  calibrated by `ModelUpdater` is optimized without re-declaring anything. Deeper:
  `problem_from_updater(updater)` lowers an updating run itself into the same vector
  problem (`f = 1/2‖r‖²`, gradient `Jᵀr` from the updater's own jacobian machinery),
  the seam for driving updating with a generic backend in Round 2.
- **Shape hooks:** basis-field mesh morphing `X(a) = X0 + Σ aⱼVⱼ` with the exact
  linear morph and geometry gradient `dX/da = V` implemented
  (`DesignSpace.morph_displacement` / `apply_to_coordinates`); FE regeneration and
  geometric `dK/da` deferred to Round 3, shape gradients route through tracked FD.
- **Gradient interface (modal integration):** `ModalDesignEvaluator` produces one
  cached `DesignState` per design point (objective + all constraints share a single
  eigensolve) and auto-detects the `MatrixDerivativeProvider` shape (`assemble` /
  `derivatives` / `eigen` — `ScalingModel` satisfies it unmodified) to fill an
  analytic bundle from the shared M3 Fox–Kapoor kernel: `df/dp` re-ordered to
  MAC-tracked reference mode labels, exact `dm/dp = mass(Mⱼ)`. Fallback: central FD
  over the design vector with a one-time warning; `check_gradient` is the AC-OPT-001
  verification gate. MAC tracking (via `updating.sensitivity.track_modes` against the
  previous iterate's tracked view) keeps `NaturalFrequency(i)` responses and gradient
  rows attached to physical branches across crossings (AC-OPT-004 mechanism).
- Constraints standardize to `g ≤ 0` with dimensionless normalization
  (`frequency_floor` gives MS-5.1's `g = 1 − f/f_min`); `minimize_sizing` exposes the
  exact MS-5.3 signature. Backend contract (bounds hard per AC-OPT-003, no internal
  differentiation per MS-5.2, `g ≤ 0 → g ≥ 0` sign mapping for SLSQP) is documented in
  `ScipyBackend`; its `solve` is the **single** `NotImplementedError` stub, Round 2
  gated by AC-OPT-002/003. Added `OptimizationError` to `openfemlab.exceptions` and
  top-level lazy exports (`OptimizationProblem`/`OptimizationResult`/`minimize_sizing`).
- `tests/test_optimization.py`: 16 contract tests — design-space layout/bounds/clip,
  log chain rule, shape morphing, single-solve sharing, analytic-route detection,
  exact mass gradient, AC-OPT-001 frequency-gradient checks at 3 seeded points
  (objective and constraint callbacks), MS-5.1 standardization, FD-fallback warning,
  mode tracking across an eigen-order crossing, vector-problem bound validation,
  backend registry, stub pinning, and updater-interop gradient consistency (`Jᵀr` vs
  FD ≤ 1e-6; zero residual/gradient at the true parameters). All 16 pass at the
  current tip; new files Ruff-clean.
- Same shared working-tree hazard A13/A15/A21 reported, worse this round: sibling
  agents repeatedly reverted `exceptions.py` and both `__init__.py` files mid-edit,
  `/workspace` was switched onto `cursor/dynamics-damping-frf-9500` mid-run (taking
  the in-flight files with it, committed there as `9d77b80` by the concurrent flow and
  merged back via `acda625`), so verification and the docs/PROGRESS commits were
  finished from a detached worktree at `/tmp/a02-opt`.
- Open for the orchestrator: R2-T07 (optimization backend) should wire
  `ScipyBackend.solve` + the AC-OPT-002 reference problem against the already-compiled
  lowering; element-level assembled `dK/dp` for the native `Model` stack is the other
  half of GAP-12 (today only affine `ScalingModel`-style models get analytic
  gradients).

### Round 2 — Targeted Refactor & Deep Optimization
**Status:** IN PROGRESS, past the mid-point — backlog planned in
`.agent_workspace/ROUND2_PLAN.md` (A24; §0 status snapshot refreshed by A83).
**R2-T01 is COMPLETE** (engine `acda625`, AC-DYN-001..005, report `frf` block A41,
`correlate-frf` CLI A54 — no open work); **R2-T02 is PARTIAL while R2-T03 and R2-T04
are ACCEPTANCE-COMPLETE** — QUAD4/TET4/HEX8 and the spatial beam landed
(A37/A46/A59/A82) with the shell facet and the solid/shell BDF cards open, the
reduction/expansion engine and both its gates landed (A36/A43/A58 — AC-CORR-006 and
AC-CORR-009 are `implemented` and the `SensorMap.signs` wiring is done), and the
Bayesian MAP estimator landed (A49) with the AC-UPD-006a/b tagging and the report
σ_post closed (A57). Both tracks now wait only on the R2-T09 CI job that can move a
criterion to `verified`. See the mid-point brief below.

Core backlog (prioritized, from `docs/SOTA_GAP_ANALYSIS.md` §4/§6 + Round 1 conclusion):
1. ~~**R2-T01 Dynamics/FRF chain** (GAP-04/05, P0) — damping models, harmonic response,
   FRF synthesis, FRAC/FDAC.~~ **DONE.** The engine landed with the `acda625` merge of
   `cursor/dynamics-damping-frf-9500`, and AC-DYN-001..005 are now registered spec-first
   against that API and `implemented` (see the R2-T01 entry below). GAP-04 is closed;
   GAP-05 is closed apart from the FRF updating residual the plan defers to Round 3.
   The last exit item of the task — an FRF block in the `CorrelationReport` schema — is
   closed too (A41, `schema_version` 1.1), and so is the measured-vs-synthesized FRF
   demo through the CLI (A54, `openfemlab correlate-frf`). **R2-T01 has no open work.**
2. **R2-T02 3D continuum elements** (GAP-02, P0) — QUAD4/TET4/HEX8 + 3D beam with patch
   /convergence gates (AC-MODAL-001/003/004/007 extended, new AC-ELEM-*). **PARTIAL:
   QUAD4 and TET4 are landed on the trunk**, QUAD4 merged from
   `cursor/quad4-plane-stress-element-b99c` by A37 and TET4 from
   `cursor/tet4-solid-element-08d1` by A46 (see the R2-T02, A37 and A46 entries below);
   HEX8, the 3D beam, the `CQUAD4`/`CTETRA`/`CHEXA`/`PSHELL`/`PSOLID` BDF cards and the
   AC-ELEM-* registry rows are the remaining slice.
3. **R2-T03 SEREP/TAM reduction & expansion** (GAP-08) — Guyan/IRS/SEREP, TAM
   pseudo-orthogonality, shape expansion; closes Round-2 gates AC-CORR-006 and
   AC-CORR-009. *Engine landed by A36 (`correlation/reduction.py`) and **both criteria
   are now `implemented`** — A43 added the 19-case AC-CORR-006 gate, A58 registered
   AC-CORR-009 with 14 cases and wired `SensorMap.signs` through all three bases.
   **The only remaining item is the `implemented` → `verified` flip, which needs a CI
   run rather than more code**, i.e. R2-T09. See the A36, A43 and A58 entries below.*
4. **R2-T04 Bayesian MAP updating** (GAP-11 slice, MS-3.5) — Gaussian-prior MAP step +
   posterior covariance; closes Round-2 gates AC-UPD-006a/b. *The estimator landed by
   A49 (`updating/bayesian.py`, 35 tests), driving the shared LM loop through the new
   `normal_equations`/`penalty` hooks, and **both criteria are now `implemented`** —
   A57 added the eight-test acceptance gate on the ten-DOF twin, flipped the registry
   in the same commit and wired the Laplace σ_post into the `CorrectionReport` column
   AC-WORK-005 reserves. Remaining: σ_post in the CLI `update` document, and moving
   both rows from `implemented` to `verified` once CI has run them. See the A49 and A57
   entries below.*
5. **R2-T05 meshio bridge & IO completion** (GAP-03 remainder) — optional-dependency
   meshio ↔ NeutralModel bridge, UNV 2411/2412. **NOT STARTED.**

Supporting: R2-T06 updating depth (the P0 AC-UPD-007 collinearity-screen slice closed
with A44's tagging; P1 depth work remains), R2-T07 scipy optimization backend (GAP-12 —
the surrounding M5 package landed at `acda625` and `ScipyBackend.solve` is now wired
too, so this is **done**, A27), R2-T08 R1-O2 branch reconciliation, R2-T09 CI exit
hardening. Exit bar: all P0+P1 criteria `verified`,
new dynamics/element/IO criteria at least `implemented`, GAP-01 stays closed.

#### Round 2 — mid-point brief (A61, backfill for A53)

Written at code baseline `7cc1120` and verified there from a private clone
(`/tmp/a61`, `PYTHONPATH` pinned): full suite **876 passed, 0 failed**,
`ruff check .` clean, Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1. For scale: Round 2
opened at 430 tests, so the round has roughly doubled the suite while keeping it
green throughout.

- **Scoreboard.** Of the five core tracks, one is closed and three are half-way:
  **R2-T01 COMPLETE** (dynamics engine, AC-DYN-001..005, `frf` report block at schema
  1.1, `correlate-frf` CLI — the round's first headline demo is deliverable today);
  **R2-T02 PARTIAL** (QUAD4 + TET4 landed with generators and 127 tests; HEX8, the 3D
  beam, the `NeutralModel` → `Model` conversion, solid/shell BDF cards and AC-ELEM-*
  registration open); **R2-T03 PARTIAL** (reduction/expansion engine plus the
  AC-CORR-006 gate `implemented`; AC-CORR-009 and `SensorMap.signs` closed by A58
  after this brief was written, leaving only the `verified` flip); **R2-T04 PARTIAL** (MAP estimator with posterior covariance landed on the
  shared LM loop; acceptance tagging and σ_post surfacing open — both closed by A57
  after this brief was written, so the track is now acceptance-complete and only the
  CLI σ_post surface is left); **R2-T05 NOT
  STARTED** — the only core track with no commit. Supporting: R2-T06's P0 slice and
  R2-T07 are done, R2-T08 needs only a close-as-superseded decision, R2-T09 has not
  begun.
- **Registry.** 40 criteria: **32 `implemented`, 8 `specified`, 0 `verified`.** Still
  `specified`: AC-CORR-008, AC-UPD-004, AC-UPD-005 (P0) and AC-MODAL-008,
  AC-UPD-006a/b, AC-UPD-008, AC-WORK-003 (P1) — every one an engine-exists /
  acceptance-tags-missing case, which is the cheap kind of open work. The structural
  risk is the third number: the exit bar demands every P0+P1 criterion `verified`, and
  nothing can reach `verified` until R2-T09 stands up CI. That task is the round's
  critical path even though it is ranked last.
- **Headline demos.** The FRF demo (exit-bar item 4, first half) works end to end:
  `openfemlab correlate-frf measured.unv model.yaml --require-frac 0.9`. The second
  half — a meshio- or BDF-imported 3D mesh re-analyzed internally — is blocked on the
  R2-T02 remainder (conversion + BDF cards) and R2-T05, which should be dispatched
  together per the plan's Wave-2 sequencing.
- **Recommended second-half order.** (1) R2-T04's acceptance slice — the cheapest
  gate-blocker close, since `tests/test_bayesian_updating.py` already proves both
  MS-3.5 limits; (2) the R2-T02 remainder, which unblocks the second demo and carries
  the AC-ELEM-* registration (a spec-first, three-file change that moves the pinned
  40-criterion inventory); (3) R2-T05 meshio/UNV; (4) R2-T09 CI so the
  `implemented → verified` flips can start; alongside, the small closes: AC-CORR-009,
  the seven remaining tag-only criteria above, and `SensorMap.signs`.
- **Process.** The shared-`/workspace` hazard has hit essentially every task since
  A28 — twelve-plus recorded occurrences, including destroyed *committed* work (A52)
  and a moved branch ref (A43). The private-clone rule is now the working standard and
  was followed here; the tip moved once during this brief's preparation
  (`d3498b4 → 7cc1120`), confirming it is still necessary. GAP-01 discipline has held:
  no duplicate kernels were introduced this round, and the two near-misses (A35's
  AC-DYN registration, A34's backend) were both caught and dropped before landing.

#### R2-T01 — Dynamics & FRF chain closed out (GAP-04/05, P0)
- **Integration first, and only one implementation.** The plan's binding constraint was
  to harvest `cursor/dynamics-damping-frf-9500` rather than fork a rival dynamics kernel
  (the GAP-01 lesson). Confirmed done: A28's merge `acda625` carries `solver/dynamics.py`
  (1,288 lines — damping models, complex modes, FRF synthesis, FRAC/FDAC),
  `tests/test_dynamics.py` (**82 passed**) and the `optimization/` sizing contracts, and
  `frac`/`fdac` are defined in exactly one place on the branch. This entry adds the
  spec-first half of R2-T01 that the merge did not cover.
- **Criteria registered spec-first.** `MODULE_SPEC.md` §7 defines module **M6** with
  anchors **MS-7.1..7.5** (damping models, complex modes, harmonic response and FRF
  synthesis, FRF correlation, public API). MS-6 was already the inter-module contracts
  section, so the sixth module takes the `MS-7` prefix rather than renumbering live
  anchors. `ACCEPTANCE_CRITERIA.md` §7 defines AC-DYN-001..005; the registry gained the
  `DYN` family (→ M6) and all five entries at `implemented`, which the enforcement tests
  accept only because `tests/acceptance/test_dynamics.py` carries a `@criterion` tag for
  each ID.
- **AC-DYN-001** (`oracle`, gate 1e-8) — 1-DOF damped receptance against
  `1/(k − mω² + iωc)`: direct inversion **exact (0)**, real-mode superposition
  **1.9e-16**. 2-DOF fixture against the hand-inverted 2×2 dynamic stiffness on 31
  off-resonance lines: **1.1e-15** direct, **1.2e-15** modal. Mobility and accelerance
  are checked against `iωH` and `−ω²H`, so the MS-7.3 conventions are pinned rather than
  assumed.
- **AC-DYN-002** (`property`, gate 1e-8) — with the full basis retained on the 10-DOF
  chain, real-mode superposition matches `Z(ω)⁻¹` to **8.0e-15**; for a deliberately
  non-classical `C` (single grounded dashpot, Caughey–O'Kelly residual **0.632**) the
  complex-mode residue expansion matches to **8.4e-15** — the case where real-mode
  superposition is not valid at all. Truncating to 3 of 10 modes costs **4.6 %** at 0 Hz
  and `residual_flexibility` brings it back to **9.8e-16**; the test asserts the
  truncation error is real before crediting the correction.
- **AC-DYN-003** (`property`) — for `C = αM + βK` (α=0.02, β=0.004, ζ spanning
  **0.90 %..6.72 %** across the chain spectrum) the complex modes are monophase to
  **1 − 2.2e-16** MPC, the extracted ratios match `α/(2ω_r) + βω_r/2` to **1.2e-15**, and
  `ω_d = ω_r√(1 − ζ²)` holds. The negative control is what makes the gate meaningful: the
  grounded dashpot drops the worst MPC to **0.7516** and `is_proportional` rejects it.
- **AC-DYN-004** (`property`, gate 1e-12) — the frequency-domain mirror of
  AC-CORR-001/002. Self-FRAC deviates by **4.4e-16**; 8 seeded complex scale factors move
  FRAC by at most **1.2e-15** against a non-trivial reference (cross-DOF FRAC spans
  **0.0014..0.5353**, so invariance is measured against real signal, not against 1); the
  FDAC diagonal is unit to **8.9e-16** with **exact** symmetry; zero-norm inputs return 0,
  not NaN.
- **AC-DYN-005** (`contract`, gate 1e-9) — a synthesized drive-point receptance written
  as an ASCII dataset-58 record (ordinate type 6, even spacing) and read back through
  `io/uff.py` recovers the abscissa **exactly** and the complex ordinates to **1.2e-13**,
  correlating with its source at FRAC **1 − 0**. The formatter lives in the test, not the
  library: the criterion gates the reader contract, and UFF *writing* stays R2-T05 scope.
- **FRAC/FDAC reachable from the correlation namespace.** `openfemlab.correlation` and
  the package root now re-export `frac`/`fdac` from `solver.dynamics` — a re-export, not
  a copy, and the import points downward (correlation is L3, solver L2). The
  `CorrelationReport` schema was deliberately left untouched here, since an FRF block
  there is a `schema_version` bump; **A41 has since closed that item** (schema 1.1),
  leaving only the CLI demo in the exit-bar work.
- Verified on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1: `tests/test_dynamics.py`
  **82 passed**, `tests/acceptance` **59 passed** (13 new AC-DYN tests + 46 existing),
  full suite **443 passed** (430 before this change), Ruff clean.
- **Working-tree hazard, fourth occurrence** — and this time it destroyed work rather
  than just risking it. The R2-T02 element agent was editing `/workspace` concurrently;
  midway through, a reset there wiped four of this task's edited files
  (`MODULE_SPEC.md`, `ACCEPTANCE_CRITERIA.md`, the registry, `correlation/__init__.py`)
  out of the tree, and the editable install briefly resolved `openfemlab` to
  `/tmp/a28/src`. The work was redone in a private detached worktree at `/tmp/r2t01` and
  pushed from there. A13, A15, A21 and A26 all report the same failure mode; the
  private-worktree rule should be mandatory, not advisory.

#### A41 — FRF block in the `CorrelationReport` schema (closes the last R2-T01 exit item)
- **The gap this closes.** R2-T01 shipped `frac`/`fdac` and re-exported them from
  `openfemlab.correlation`, but left the report artifact modal-only, so an FRF comparison
  had no way to be published: the exit item it handed on. `correlation/frf.py` now drives
  those same kernels — imported from `solver.dynamics`, not reimplemented — over a
  reference/comparison pair and returns the `FRFCorrelation` block the report carries.
- **What the builder resolves, so callers do not.** `frf_correlation` accepts either
  `FrequencyResponse` objects or plain `(n_frequencies, n_channels)` arrays and settles
  the three things that silently corrupt an FRF comparison: the shared frequency line
  (two sets on different lines are rejected, not interpolated), the exciter column (a
  multi-exciter response demands an explicit `excitation_dof` rather than guessing), and
  the response type (receptance against accelerance is refused, naming
  `FrequencyResponse.converted`). Channel labels default to the response DOFs.
- **Schema 1.1.** `CorrelationReport` gained an optional `frf` field, serialized under
  the `frf` key and rendered by `report()`; `SCHEMA_VERSION` moved `1.0 → 1.1` as MS-6
  requires for any change to the external interface. The key is emitted as `null` when no
  FRF comparison ran, so the artifact's key set does not depend on which analyses were
  performed — a consumer can read `payload["frf"]` unconditionally.
  `is_correlated(frac_threshold=...)` extends the MS-4.2 modal gates with the MS-7.4
  frequency-domain one and *raises* when the report has no block, rather than reporting a
  gate it could not evaluate as a failure. `docs/MODULE_SPEC.md` (MS-2.6, MS-7.4),
  `docs/ACCEPTANCE_CRITERIA.md` (AC-CORR-008) and `docs/ARCHITECTURE.md` record the bump.
- **`tests/test_frf_correlation.py`, 25 tests** on a damped fixed-free spring/mass chain
  whose FRFs come from the untruncated `direct_frf`, so every number is physics rather
  than a recorded run. Self-correlation: FRAC deviates by **4.4e-16** and the FDAC
  diagonal by **8.9e-16**; a complex scale factor `2.5 − 1.3j` moves FRAC by **4.4e-16**.
  The negative control is what makes those meaningful — a chain stiffened 15 % gives
  per-channel FRAC **0.072..0.315** (mean **0.174**), drops the worst FDAC diagonal to
  **0.500**, and pushes the FDAC peak above the diagonal on **88.3 %** of lines, which is
  the frequency shift showing up exactly where the metric is supposed to expose it.
- Verified from a private worktree at `/tmp/a41` with `PYTHONPATH` pinned to its `src`,
  on Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1: full suite **636 passed** (611 before
  this change), `ruff check src tests` and `ruff format --check` clean.
- **Working-tree hazard, again.** The first pass was written directly in `/workspace`,
  verified green there, and then destroyed mid-run when a concurrent agent reset the
  shared checkout onto `cursor/tag-work-upd-acceptance-0809`; the whole change had to be
  rewritten in the private worktree. A13, A15, A19, A21, A26 and A36 all report this. The
  private-worktree rule should be the default first step of every task, not a recovery
  procedure.
- Open for the orchestrator: the CLI FRF demo is the only R2-T01 exit item left
  (`ROUND2_PLAN.md` §5 item 4) — a command surface over `frf_correlation`, with the
  metric and the artifact already in place. *Closed by A54 below.* Registering an AC ID
  for the block (the natural home is an AC-CORR-* contract row alongside AC-CORR-008)
  needs the spec-first three-file commit and was deliberately not half-done here.

#### A54 — `openfemlab correlate-frf`: the CLI FRF demo (closes R2-T01 outright)
- **The last R2-T01 exit item** (`ROUND2_PLAN.md` §5 item 4): a measured UFF-58 FRF
  compared against one synthesized from a damped model, through the CLI. A41 had already
  landed the metric and the artifact, so this is a command surface — no new kernel, and
  `frac`/`fdac` still exist exactly once (GAP-01 holds).
- **`cli/commands/correlate_frf.py`.** `openfemlab correlate-frf MEASURED COMPARISON`
  resolves both sides to one *FRF column* — the response channels driven by a single
  exciter — and hands the pair to `correlation.frf_correlation`. The measured side reads
  a UFF/UNV dataset-58 file (one record per channel, response and reference DOFs taken
  from the identification record) or a JSON/YAML FRF document with the same content. The
  comparison side is either a second measurement or a model specification, which is then
  solved and synthesized *on the measured frequency line, at the measured channels*:
  every `(node, DOF)` channel is resolved to a model equation through
  `Model.dof_index`, so a channel the model does not carry is named rather than silently
  dropped, and a second measurement is reordered onto the reference channel order.
- **Damping is part of the command, because a synthesized FRF is meaningless without
  it.** `--damping ZETA` (uniform modal ratio) and `--rayleigh ALPHA BETA` override an
  optional `damping:` block in the spec (`ratio`, per-mode `ratios`, or `alpha`/`beta`),
  which in turn overrides the 2 % default; the report records which of the three the
  numbers came from. The spec block is read in the CLI layer, not in `cli/spec.py`,
  because `Model` carries no damping — `solver.dynamics` takes it as a separate argument.
- **The artifact is the schema-1.1 one.** The report publishes `FRFCorrelation.as_dict()`
  under `frf` next to `schema_version` `1.1`, so a consumer reads the same block whether
  it came from the library or the CLI. `--require-frac` / `--require-fdac` gate it and
  reuse `correlate.CORRELATION_FAILED` (exit 3) rather than defining a second code;
  `--no-fdac` suppresses the matrix that is quadratic in the frequency count, and asking
  for the FDAC gate anyway is reported instead of silently passing.
- **`tests/test_cli_frf.py`, 16 tests.** The headline demo is the exit-bar one: modes of
  a fixed-fixed chain → Rayleigh-damped synthesis → dataset-58 file → the CLI → FRAC and
  the FDAC diagonal back at 1 within **8.9e-16** and **4.4e-16**, carried through the
  12-digit UFF interchange. The negative control keeps that honest: the same measurement
  against a 40 %-softened chain gives per-channel FRAC **0.134 / 0.054 / 0.075** (mean
  **0.087**) and a worst FDAC diagonal of **0.183**, and trips `--require-frac 0.99` with
  exit 3. The rest pin the input resolution (UFF vs document, spec vs second
  measurement), channel reordering, the named failures (missing channel, channel outside
  the model, mismatched frequency lines, unnamed exciter), the three damping sources, and
  the table/JSON/file outputs.
- `tests/_uff58.py` now holds the ASCII dataset-58 formatter that AC-DYN-005 had inlined,
  parameterized by response/reference node and direction. The suite writes UFF in one
  place; the library still writes none (that is R2-T05).
- Verified from a private clone at `/tmp/a54` (`PYTHONPATH` pinned to its `src`), Python
  3.12.3: full suite **695 passed** (679 before this change) on the clone's base, and
  **797 passed** after rebasing onto the branch tip the sibling agents had advanced
  meanwhile; `ruff check .` clean at both points.
- **Working-tree hazard, a seventh time.** The first pass was written in `/workspace` and
  wiped mid-run by a concurrent agent's `git reset --hard`; only the untracked new files
  survived. Same lesson as A13/A15/A19/A21/A26/A36/A41 — start in a private clone.
- Open for the orchestrator: the command has no AC ID. The natural row is an AC-CORR-*
  `contract` criterion next to AC-CORR-008 covering the CLI artifact, and it needs the
  spec-first three-file commit (`ACCEPTANCE_CRITERIA.md`, `MODULE_SPEC.md`, registry), so
  it was deliberately not half-done here.

#### A35 — AC-DYN registration backfill: duplicate dropped, head verified (backfill for A28)
- Dispatched to register AC-DYN-* criteria (FRF match, damping ratios, FRAC) and wire the
  first three to `tests/test_dynamics.py` — the item A28 left open ("no AC-DYN-* criteria
  exist yet"). Built the full registration in a private worktree (`/tmp/a35`, base
  `b9d26f0`): `DYN` family → M6 with spec anchors MS-7.1..7.4, criteria doc §7, and
  `@criterion` tags on six existing `tests/test_dynamics.py` cases; 430 passed, Ruff
  clean at that base.
- The pre-push fetch showed R2-T01's `a5766f5` had landed the same registration four
  minutes into this run — same five IDs, different definitions and numbering, bound to a
  new dedicated suite `tests/acceptance/test_dynamics.py` (13 tests, oracle gates the
  unit suite doesn't state). Rebasing would have re-registered rival definitions of
  already-landed IDs, so the duplicate commit (`b51546a`) was **dropped unpushed** and
  the landed set adopted — the GAP-01 "one implementation" rule applied to criteria.
- Deliberately did **not** add the tasked `@criterion` tags to `tests/test_dynamics.py`:
  the registry binds AC-DYN-001..005 to the acceptance suite, and a tag in a suite the
  registry does not name is exactly the drift the section-8 enforcement rules exist to
  reject. The unit suite stays the engine's regression net; the acceptance suite carries
  the criteria.
- Independent verification at head `3fcc6a6` (Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1,
  `PYTHONPATH` pinned to the private worktree): full suite **534 passed** (67 s),
  `pytest -m acceptance` **106 passed**, `ruff check .` clean. Registry now holds
  **40 criteria, 20 implemented / 20 specified**, with all five AC-DYN `implemented`
  (A23's 41 was an arithmetic slip; A47 reconciled it to 40 and pinned the
  9+8+9+5+4+5 module inventory in the criteria document and registry tests).
- Working-tree hazard, still live: `/workspace` was mid-rebase on
  `cursor/optimization-sizing-hook-254c` with unresolved conflicts when this run
  started, and the branch tip advanced five times during the run (three of them while
  this entry was being verified). Concurs with R2-T01: private worktree + fetch-before-
  push should be mandatory.

#### A26 — Round 1 carry-over cleared: MS-4 workflow landed (backfill for A17)
- Round 1 closed with the MS-4 `workflow/` package listed as its single largest piece of
  uncommitted debt ("Remaining defects / open items", and Round 2 priority 1). That debt is
  now retired on this branch: A13's `2f21993` (package) and `36befc3` (tests) carry the
  six-stage state machine, with `26aa64a` the follow-on that reads the corrected parameters
  back out of `UpdatingResult.parameter_set`. This agent recovered and re-derived the
  package independently and confirmed the trees are identical — the recovered commit
  rebased onto the branch as "patch contents already upstream", so there is exactly one
  MS-4 implementation on this branch, not two competing ones.
- Verified at `5bc6a6d` on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1: `tests/test_workflow.py`
  **38 passed**, full suite **332 passed** (7 s), `ruff check src tests` clean. Re-verified
  after `acda625` merged the dynamics and optimization branches in: workflow still **38
  passed**, full suite **430 passed**, Ruff still clean — the S1-S6 pipeline is unaffected
  by the merged tracks.
- Coverage confirmed against the spec section by section: MS-4.1 stage order and the
  machine-readable `(stage, reason)` halt with `SKIPPED` successors; MS-4.2 gates
  (MAC ≥ 0.95, |Δf| ≤ 1 %, ≥ 3 pairs, bounds, warning-severity plausibility, held-out
  MAC ≥ 0.9 and no-worse-than-baseline); MS-4.3 `schema_version = "1.0"` and rerun
  reproducibility to 1e-12 via `to_dict(include_timing=False)`; MS-4.4 `run_correction`
  signature; and the MS-3.6 selection diagnosis behind S3.
- **Backlog correction for R2-T06.** The A24 plan above lists AC-UPD-007 (MS-3.6 collinear
  parameter detection and freeze) as the last unimplemented **P0** criterion. It is no
  longer unimplemented: `workflow/selection.py` is the collinearity screen, and
  `test_workflow.py::test_duplicated_parameter_is_frozen_and_updating_still_converges`
  exercises exactly the criterion's twin scenario — `k0_copy` is frozen with
  `freeze_reason == "collinear"`, the other three parameters stay selected, and the run
  recovers `k0 = 1.3` to 1e-4 with `status == "PASS"`. What R2-T06 still owes is the
  registry tagging (so the criterion reads `verified` rather than `unimplemented`) and the
  QR-with-column-pivoting refinement; the greedy norm-ordered screen already in place is
  the MS-3.6 behaviour, not a placeholder.
- **Working-tree hazard, third occurrence.** The `workflow/*.py` sources were deleted from
  the shared `/workspace` checkout mid-run by a concurrent agent while
  `tests/test_workflow.py` stayed committed — an import-broken state. They were recovered
  from the dangling commit `021163e` (`git fsck --lost-found`) into a private worktree at
  `/tmp/a26`. Three rounds of this failure mode now argue for making the private-worktree
  rule mandatory rather than advisory, since `git clean`/branch-switch collateral is not
  something the offending agent can see.

#### R2-T02 — QUAD4 plane-stress/plane-strain element (first slice of GAP-02; PARTIAL)
- **The first continuum element on the branch.** `ElementType.QUAD4` has been declared in
  `core/neutral.py` since Round 1 with no formulation behind it, so an imported shell mesh
  could be correlated but never re-analyzed. `core/elements.py` now carries
  `Quad4Element`: a four-node isoparametric bilinear quadrilateral in the XY plane
  (`UX`, `UY`), with `K = t ∫ BᵀDB dA` and `M = ρt ∫ NᵀN dA` on a tensor-product
  Gauss-Legendre rule (`gauss_legendre_2d`, 1–4 points per direction, 2×2 by default,
  which integrates both exactly for any non-degenerate quadrilateral). Plane stress and
  plane strain share one `plane_constitutive_matrix` helper; mass is consistent by
  default, or row-sum lumped, which preserves the total mass for any element shape.
  `strain()`/`stress()` recover the element state at any natural point.
- **Validation is refused rather than tolerated.** A non-positive Jacobian at any Gauss
  point — degenerate, inverted, or clockwise connectivity — raises `ElementError` naming
  the point, and nodes spanning Z beyond 1e-9 of the in-plane scale are rejected instead
  of being silently projected. A constant Z offset is accepted, so a plate at `z = 3.5`
  gives bit-identical matrices to the same plate at `z = 0`.
- `mesh/simple.py` gained `quad_plate_mesh(length, height, num_x, num_y, material, …)` —
  a row-major structured grid with counter-clockwise connectivity and
  `cantilever`/`free`/`simply-supported` supports — plus `MeshBuilder.add_quad4`, so the
  convergence and modal fixtures are generated rather than hand-written.
- **Patch test, exactly.** The MacNeal-Harder five-element distorted patch (0.24 × 0.12
  rectangle, four interior nodes, boundary field `u = 1e-3(x + y/2)`,
  `v = 1e-3(y + x/2)`) recovers the interior displacements to **2.7e-20 absolute against
  a 2e-4 field** — machine precision — and every element reports the exact constant stress
  **σₓ = σᵧ = 1333.333, τₓᵧ = 400.0** at every sample point, for integration orders 2 and 3
  alike. At element level an arbitrary constant strain state is reproduced to 1e-12
  relative on a distorted quad, and its consistent nodal forces are self-equilibrated.
- **Zero-energy modes are counted, not assumed.** With full 2×2 integration a distorted
  element has exactly **three** zero eigenvalues (the planar rigid-body motions) and no
  hourglass modes; the suite also pins the counterpart, that one-point reduced integration
  is rank deficient with **five**. Rigid translation produces no nodal force and rigid
  rotation produces neither strain nor strain energy, both to 1e-12 of the matrix scale.
- **Modal results.** With `ν = 0` the column-constant axial subspace of a rectangular
  QUAD4 strip is both K- and M-invariant and coincides with a linear bar discretization,
  so the strip's axial spectrum must equal `bar_mesh`'s exactly — measured agreement is
  **2.4e-13 relative** over three modes, which is a far sharper oracle than a continuum
  comparison. Against the continuum bar the first axial frequency converges
  quadratically, error **4.1e-3 → 1.0e-3 → 2.6e-4** for 5/10/20 elements. Bending is the
  honest weak spot and is recorded as such: bilinear elements carry bending through shear,
  so a cantilever strip locks *from above* at **+18.7 % → +4.9 % → +1.2 %** for
  20×2 / 40×4 / 80×8, a clean 4× error reduction per refinement. A free plate returns
  exactly three rigid-body modes with the first elastic mode at 6.9 kHz, cantilever modes
  are mass-orthonormal to < 1e-9, plane strain is stiffer than plane stress, and lumped
  mass is never stiffer than consistent mass.
- Added `tests/test_quad4.py` — **61 tests** covering shape-function and quadrature
  identities, the two constitutive closed forms, geometry validation and every error path,
  stiffness invariances (including in-plane rotation and linear scaling in `t` and `E`),
  the patch tests above, mass bookkeeping (total mass in each direction, lumped = row sum,
  massless material), the mesh generator and assembly, and the modal checks.
- Verified on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1: full suite **491 passed**
  (430 + 61) at `174a0fc`, `ruff check src tests` clean.
- **Working-tree hazard, fifth occurrence.** Two variants hit this run. The venv's
  editable install had been repointed at a sibling agent's `/tmp/a28/src`, so an unguarded
  `pytest` in `/workspace` tested that tree and could not even import `Quad4Element`;
  every run here pinned `PYTHONPATH`. Then a concurrent agent ran
  `git reset --hard origin/…` plus a branch checkout on the shared clone mid-commit, which
  deleted `tests/test_quad4.py` from disk and left the branch pointer on a foreign tree.
  The work was recovered from the reflog commit `6e6d126` and finished in a private
  worktree at `/tmp/quad4wt`. The same `git add -A src` also swept a concurrent agent's
  uncommitted `correlation/__init__.py` FRAC/FDAC edit into the first commit; it was
  dropped from the recovered one, so this branch touches only element, mesh and export
  files.
- Open for the orchestrator: the AC-ELEM-001/002/003 registry rows the A24 plan proposes
  are **not** registered — this branch adds no criteria IDs, so the spec-first rule is not
  violated, but the numbers above are exactly the evidence those rows want (AC-ELEM-001
  patch test at machine precision, AC-ELEM-002 rigid-body invariance, AC-ELEM-003
  quadratic h-convergence). Registering them should land with the TET4/HEX8 slice, in the
  same change as the `ACCEPTANCE_CRITERIA.md` / `MODULE_SPEC.md` edits.

**Round 2 entry state.** Both packages Round 1 left uncommitted are now in and green:
`workflow/` via A13/A26, and the `optimization/` build-out (`variables`, `responses`,
`gradients`, `problem`, `sizing`, `backends`) via the A28 merge below. No Round-1
carry-over remains, and R2-T07's remaining debt — `ScipyBackend.solve` — was cleared by
A27. The A24 backlog above is otherwise the live plan.

#### A37 — QUAD4 branch merged onto the trunk (backfill for R2-T02)
- Merged `cursor/quad4-plane-stress-element-b99c` into the integration branch. The branch
  had been cut from `b9d26f0` and the trunk had moved on by the R2-T01 dynamics close-out,
  the AC-DYN/AC-MODAL/AC-OPT acceptance batches and the A27 optimization backend, so the
  merge was replayed against the current trunk rather than fast-forwarded.
- **Conflicts and how they were resolved.** Both were documentation-only:
  - `PROGRESS.md` Active Pool — the two sides appended different rows to the same table
    line. Both kept; the R2-T02 row is recorded as **partial** rather than complete, since
    the branch delivers only the QUAD4 slice of GAP-02.
  - `ROUND2_PLAN.md` §1 gap table — the trunk had rewritten the GAP-04/05 row to
    "Closed by R2-T01" while the branch rewrote the adjacent GAP-02 row to "Partial".
    Both rewrites kept.
  - `src/openfemlab/__init__.py` auto-merged: the trunk's `SolverConvergenceError` export
    and the branch's `Quad4Element` / `plane_constitutive_matrix` / `fdac` / `frac`
    exports land side by side. Verified by resolving all 54 names in `__all__` through
    the lazy `__getattr__`, so the PEP 562 table and the `TYPE_CHECKING` aliases agree.
- No source conflicts: the branch only adds to `core/elements.py`, `core/__init__.py` and
  `mesh/simple.py`, none of which the trunk touched in the interval.
- **Verification after the merge** (Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1, `PYTHONPATH`
  pinned at the worktree `src` so the venv's editable install cannot shadow it): full
  suite **559 passed**, `ruff check .` clean. That is the trunk's 498 plus the branch's
  61 QUAD4 tests, comfortably past the 491 the R2-T02 record measured in isolation.
  The trunk moved again while this was being verified (A39's PR-draft refresh and A36's
  R2-T03 reduction/expansion start), so it was merged back in and re-run: **595 passed**,
  Ruff still clean. Only the Active Pool table conflicted the second time.
- **Working-tree hazard, sixth occurrence.** A concurrent agent ran
  `git reset --hard origin/cursor/femtools-industrial-7aa3` on the shared `/workspace`
  clone twice during this run, discarding a completed and verified merge commit both
  times. The merge was redone in a private worktree at `/tmp/a37wt`, which git protects
  because a branch checked out in one worktree cannot be checked out in another. The
  private-worktree rule R2-T02 asked to make mandatory should be treated as such.

#### A28 — Dynamics & Optimization Branch Integration (backfill for A15)
- Merged `cursor/dynamics-damping-frf-9500` into the integration branch at `acda625`,
  landing the two tracks Round 1 and A24 had both flagged as in-flight: A19's GAP-04/05
  damped-dynamics chain (`solver/dynamics.py`, `tests/test_dynamics.py`, 82 tests) and
  A02's MS-5 optimization build-out
  (`optimization/{variables,responses,gradients,problem,sizing,backends}.py`,
  `tests/test_optimization.py`, 16 tests), which had been swept into A19's commits from
  the shared tree. The A02, A19 and A29 entries describe the delivered engines; this
  entry records the integration.
- **No conflicts to resolve.** A19 had rebased onto `0409b3e` before pushing, so the merge
  base was current and git took every hunk cleanly, including the `openfemlab/__init__.py`
  export table and the PROGRESS line both sides touched. Verified afterwards that the
  merge is content-complete rather than merely conflict-free: `openfemlab.solver` exports
  the dynamics API, and `OptimizationProblem`, `OptimizationResult`, `minimize_sizing` and
  `OptimizationError` all resolve from the package root.
- **A second merge** (`57ba8c2`) brought the A29 and A19 progress records themselves onto
  the trunk. Both were written after the rebase and lived only on the side branch, which
  is exactly the "nothing stranded on a side branch" rule A29 states.
- **The failure mode this backfill actually guarded against.** In the shared `/workspace`
  clone the branch pointer `cursor/dynamics-damping-frf-9500` had been reset onto the
  trunk after A19 pushed, so merging that local ref reported "Already up to date" and
  would have silently landed nothing. The five commits were located through the branch
  reflog (`490970a` and its parents), then confirmed still present on
  `origin/cursor/dynamics-damping-frf-9500` — the ref that was actually merged. This is
  the fourth occurrence of the shared-tree hazard A13/A15/A21/A26 report and the worst
  variant so far: a lost *ref* rather than a lost working tree, because it fails silently
  instead of breaking an import. All of this agent's work was done in a private worktree
  at `/tmp/a28` with `PYTHONPATH` pinned to it, since the venv's editable install points
  at `/workspace/src` and would otherwise test a sibling agent's tree.
- Verified at `acda625` on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1: full suite
  **332 → 430 passed** (5 s), `ruff check .` clean. Every pre-existing suite is unchanged;
  the 98 new tests are the two merged files.
- **Independent integration checks** — not a re-run of A19's suite, but the merged packages
  driven through the trunk's own `ModalSolver`, `mesh.simple.spring_mass_chain` and
  `updating.ScalingModel`, which is the part a merge can break. Damped SDOF poles match
  `s = −ζω₀ ± iω₀√(1−ζ²)` to **7.4e-16** relative and ζ to **6.1e-16**. A 10-DOF chain
  under Rayleigh damping reports proportionality index **exactly 0.0**. Over 400 frequency
  lines from 1–120 Hz, real-mode superposition and complex-mode residue superposition
  reproduce the direct inversion of `Z(ω) = K − ω²M + iωC` to **2.1e-13** and **1.3e-10**
  relative, with drive-point **FRAC = 1.000000000000000** on both routes. On the 2-DOF
  sizing reference the analytic Fox-Kapoor route matches central differences to
  **1.4e-10** (mass objective) and **2.1e-10** (normalized frequency constraint) against
  the 1e-6 AC-OPT-001 gate, at **7** eigensolves for both checks together — the
  evaluator's one-solve-per-design-point cache behaving as specified.
- Opened `docs/OPTIMIZATION.md` (`9c674d5`). `optimization/__init__.py`, `backends.py`
  and the `ScipyBackend.solve` `NotImplementedError` message all cite it by name — the
  last of those is user-facing — but the merge landed code referencing a file that
  existed on no branch and in no reachable commit, so the two API levels, the design
  space and lowering pipeline, both gradient routes and the "section 7" scipy mapping the
  stub message promises were written up from the shipped code. A02 then extended it
  (`ea65d7b`) with the module layout, the public API block and the AC-OPT mapping.
- Open for the orchestrator, in priority order:
  1. `ScipyBackend.solve` is the one remaining stub, so `minimize_sizing` raises
     `NotImplementedError` and AC-OPT-002/003 cannot be claimed. This is R2-T07/GAP-12,
     now unblocked: the lowering, both gradient routes, mode tracking and the result
     contract are all in and tested.
  2. No `AC-DYN-*` criteria exist yet, so 82 passing dynamics tests move nothing in the
     registry. R2-T01's spec-first rule (criteria doc + module spec + registry in one
     commit) should now be applied to the landed API rather than to a planned one.
  3. `frac`/`fdac` are reachable only as `openfemlab.solver.dynamics.frac`: the curated
     `openfemlab.solver.__all__` and the package root export the synthesis API but not the
     FRF correlation metrics. A19 flags the same seam from the other side (they belong in
     `correlation/` if it grows an FRF section); worth settling before the R2-T01 CLI demo
     depends on it.

#### A27 — R2-T07 scipy optimization backend & the AC-OPT gates (backfill for A25)
- **Cleared the one stub A28 left open.** `9d77b80`/`db36a32` landed the optimization
  package with a deliberate hole: `ScipyBackend.solve` raised `NotImplementedError`, so
  `minimize_sizing` could lower a problem but never solve one and all four AC-OPT criteria
  were unmet. The backend is now wired exactly as `docs/OPTIMIZATION.md` §7 specified it —
  `Bounds(keep_feasible=True)`, negated inequalities for SLSQP against
  `NonlinearConstraint(g, -inf, 0)` for trust-constr, `jac` always supplied — and GAP-12 is
  closed for sizing.
- **`jac` is not an optimization, it is the contract.** Letting scipy fall back to 2-point
  differencing would spend one hidden eigensolve per variable per iteration on top of the
  analytic Fox-Kapoor gradients the package already computes for free, so a problem with no
  gradient callback now raises `OptimizationError` rather than silently costing 4x.
- **Bounds audit made non-tautological.** Points are projected onto the box before they
  reach the model, but `OptimizationIterate.x` stores the *raw* point the backend reported,
  so `in_bounds` audits AC-OPT-003 instead of restating the projection. The acceptance test
  additionally spies on the compiled callbacks and asserts that no point the model is asked
  to evaluate leaves the box.
- **One stationarity measure for both methods.** SLSQP reports a final gradient norm and
  trust-constr an `optimality`; neither is comparable to the other. `kkt_residual` instead
  solves the NNLS fit of the multipliers of the active inequalities and active bounds and
  reports `‖df/dx + Σ λ_k dg_k/dx + μ_bounds‖` relative to the gradient scale, so a run's
  first-order optimality reads the same whichever backend produced it.
- **Reference problem with a closed-form oracle.** A grounded spring-mass chain where
  `t_j` scales the stiffness *and* the structural mass of link `j` over a fixed
  non-structural mass `m_0`. Without `m_0` a uniform scaling leaves every frequency
  unchanged and mass minimization stops fighting the frequency floor; with it the optimum
  is on the constraint boundary. Scaling every link together gives
  `λ_i(t) = t μ_i/(t m_s + m_0)`, so `f_1 ≥ f_min` binds at
  `t* = ω² m_0/(μ_1 − ω² m_s)` — an oracle, not a previous run of the code.
- **Results.** 3-mass chain, `f_min = 0.065 Hz`, `t*` = 2.667380 (mass 9.502139).
  SLSQP converges in **7 iterations / 8 eigensolves** to `t` = 2.667380
  (**9.2e-11** relative), `|g| = 0` and stationarity **0.000e+00**; trust-constr agrees to
  4.9e-6 relative in 16 iterations / 11 eigensolves. Sizing the three links independently
  reaches mass **3.977** against the uniform design's 9.502 at the same floor, with the
  constraint active and stationarity 6.9e-06, and no feasible sample out of 80 random
  draws beats it. AC-OPT-001: analytic vs central FD worst relative error **1.03e-09**
  (mass objective) and **2.42e-10** (normalized frequency constraint) over three seeded
  feasible points — three orders inside the 1e-6 gate.
- Added `tests/acceptance/test_optimization.py`, the suite the registry has named since the
  criteria were written, and flipped AC-OPT-001..004 from `specified` to `implemented`;
  the registry's own status-honesty test enforces the tagging. Extended
  `tests/test_optimization.py` over the wired backend, replacing the test that pinned the
  stub's stub-ness.
- Verified on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1: full suite **485 passed** (13 s)
  after the final rebase onto `2f9d6e6`, `ruff check src tests` clean.
- Open for the orchestrator: shape variables still route through finite differences (no
  geometric `dK/da`), `problem_from_updater` is wired and gradient-checked but nothing
  drives `ModelUpdater` through it yet, and DOE/surrogates remain Round 3. Ran in a private
  worktree at `/tmp/a27` — the shared `/workspace` checkout was on another agent's branch
  with uncommitted optimization drafts when this task started, and A28's ref-level variant
  of the same hazard is recorded above.

#### A39 — R2-T07 post-integration verification (backfill for A27)
- Reset the feature branch to remote tip `f0c65c2` and independently ran the complete suite
  from a private worktree with `PYTHONPATH` pinned to that checkout: **498 passed, 0 failed**
  in 29.42 s on Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1. The increase from A27's 485 is
  the 13-test AC-DYN acceptance batch subsequently landed by R2-T01.
- Refreshed `.agent_workspace/PR_DRAFT.md` from the stale 430-test baseline to 498,
  including the exact per-suite total, and replaced the obsolete backend-stub wording:
  `ScipyBackend` now implements SLSQP and trust-constr with analytic Jacobians, hard bounds,
  iteration/KKT audit fields, and standardized constraint mapping. **GAP-12 is closed for
  sizing optimization.**

#### A36 — R2-T03 started: reduction / expansion module (backfill for A32)
- Opened `src/openfemlab/correlation/reduction.py`, the GAP-08 / MS-2.1 bridge the plan
  ranks as the top Round-2 sign-off blocker. One `ReductionBasis` dataclass carries the
  transformation `u_full = T u_master` plus the master rows it was built for, and knows
  three operations every consumer needs: `reduce_matrix` (`TᵀAT`, symmetrized),
  `reduce_shapes` (pick the sensor rows), and `expand` (`T Φ_master`). Three constructors
  fill it: `guyan_reduction` (static condensation, `T_s = [I; −K_ss⁻¹K_sm]`),
  `irs_reduction` (`T_s + S M T_s M_r⁻¹K_r`), and `serep_basis`
  (`T = Φ_full (Φ_sensor)⁺`). `expand_shapes` is the MS-2.1 one-liner
  `Φ_test^full = Φ_fe (T Φ_fe)⁺ Φ_test`; `tam_mass` returns `TᵀMT`, which feeds the
  existing `correlation.mac.orthogonality` / weighted-MAC machinery unchanged — no second
  metric kernel was written (GAP-01 rule).
- **No new numeric kernel forked from the solver either.** `solver/modal.py::_MasslessCondensation`
  stays the eigensolver's private path; the new module is the general-master-set version
  of the same algebra and is verified against the property that motivated the private one
  (a massless slave DOF condenses exactly). Merging the two is a follow-up, not a
  duplicate: the solver's variant partitions by zero mass and is wired into the
  eigenproblem's recovery step, while this one takes an arbitrary sensor set.
- `tests/test_reduction.py`, **25 tests**, built on the 2-DOF chain of
  `tests/modal_reference.py` with DOF 0 as the only sensor — the smallest model where
  reduction is a genuine approximation. Every numeric assertion is a closed form, not a
  recorded value: the Guyan basis `[1, k0/(k0+k1)]ᵀ`, the reduced stiffness as the
  series spring `k0k1/(k0+k1)`, exactness at `m1 = 0`, and the Rayleigh bracket
  `λ_1 < λ_guyan < λ_2` when the slave carries mass (λ_guyan = 400 against λ_1 = 325.5,
  λ_2 = 1474.5 — a 23 % error on one sensor, which is the honest size of the effect the
  gate exists to catch). IRS cuts that error and collapses back onto Guyan without slave
  inertia. Two longer-chain cases carry the shape of the pending gates: 3 modes of an
  8-DOF chain seen by 4 sensors expand back with **MAC ≥ 0.999** (AC-CORR-006), and the
  SEREP TAM gives pseudo-orthogonality with diag ≥ 0.99 / off-diag ≤ 0.10 (the proposed
  AC-CORR-009).
- Verified from a private worktree at `/tmp/a36` with `PYTHONPATH` pinned to it, on
  Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1: full suite **523 passed** (66 s; 498 before
  this change), `ruff check src tests` clean. Landed as `7d4bd7b` (module) and `1bbc4d3`
  (tests) after rebasing twice onto a moving remote tip.
- **What R2-T03 still owes**, in the order the plan wants it:
  1. ~~The AC-CORR-006 gate itself. The physics is covered by
     `test_expansion_of_an_underinstrumented_chain_keeps_mac_above_the_gate`, but the
     criterion also demands *pairing computed in reduced space equals pairing computed in
     expanded space*, and it must live in `tests/acceptance/test_correlation.py` tagged
     `@criterion("AC-CORR-006")` before the registry may leave `specified`.~~ **DONE** —
     delivered by A43 below; the criterion now reads `implemented`.
  2. AC-CORR-009 (TAM pseudo-orthogonality) is *not* registered. Registering it means
     editing `docs/ACCEPTANCE_CRITERIA.md`, `docs/MODULE_SPEC.md` and the registry in one
     commit — the spec-first rule — which is why this change deliberately touched no
     document: a half-registered ID fails `test_registry_matches_acceptance_criteria_doc`.
  3. `SensorMap` wiring. The module takes master rows as plain indices, which is exactly
     `SensorMap.rows`, but it ignores `SensorMap.signs`; a caller with flipped
     accelerometers must apply `SensorMap.reduce` first. A `from_sensor_map` constructor
     that folds the signs into `T` is the clean fix.
  4. Sparse inputs are accepted but densified (`_dense`), fine at Round-2 fixture scale
     and wrong at GAP-13 scale. Craig-Bampton CMS and geometry-based sensor mapping stay
     out of scope per the plan.

#### A42 — 498-test baseline timestamp and current-tip verification (backfill for A39)
- Verification recorded **2026-08-26 07:53:53 UTC**. A39's **498 passed, 0 failed**
  result remains the post-R2-T07 baseline at `f0c65c2`. After resetting to the current
  remote tip `8f65f64`, A42 independently ran the CI command with imports pinned to the
  isolated checkout: **595 passed, 0 failed** in 38.19 s on Python 3.12.3 / NumPy 2.5.2 /
  SciPy 1.18.1. Repository-wide `python -m ruff check .` also passed with no findings.

#### A45 — current-tip verification and PR-draft refresh (backfill for A37)
- Verification recorded **2026-08-26 07:57:23 UTC** after fetching and resetting to
  remote tip `2bbd695`. From a clean isolated worktree with `PYTHONPATH` pinned to its
  `src`, full `python -m pytest` completed with **595 passed, 0 failed** in 64.15 s on
  Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1; repository-wide
  `python -m ruff check .` passed with no findings.
- The isolated rerun was necessary because concurrent uncommitted acceptance-test edits
  appeared in the shared `/workspace` checkout during its first run. Those edits are not
  part of `2bbd695` and were excluded from the recorded result.
- Refreshed `PR_DRAFT.md` to the 595-test current tip and made the R2-T02 status explicit:
  **QUAD4 plane stress/strain is landed, but the task remains partial** while TET4, HEX8,
  the 3D beam, shell facets, and corresponding solid/shell BDF cards remain open.

#### A40 — side-branch merge sweep & verification (backfill for A38)
- **Swept every side branch for work not yet on the integration branch** and merged the
  two that still carried unique commits. `cursor/optimization-sizing-hook-254c` needed
  nothing — it is an ancestor of the trunk (zero unique commits), so the sizing hook was
  already landed. Same for `cursor/dynamics-damping-frf-9500` and
  `cursor/dynamics-optimization-integration-75b6`.
- **QUAD4 (R2-T02) — merged here as `b34f072`, but A37 landed the same merge on the trunk
  concurrently**, so the trunk merge in this task's history is a no-op re-merge of an
  identical tree rather than the delivery. Recorded because the conflict resolution was
  independent and agreed: the branch was cut before R2-T01 landed and still described
  dynamics as in flight, so its `ROUND2_PLAN.md` GAP-04/05 row had to lose to the trunk's
  newer status while its GAP-02 row was kept. Two agents merging one side branch is the
  dispatch-level twin of the working-tree hazard below.
- **`cursor/optimization-scipy-backend-f421` harvested** as `6cf0f49` — the one branch in
  the sweep nobody else had taken, and *not* redundant with A27's backend: it had been
  rebased onto trunk tip `b1b0ab8` and carries two real fixes on top of it.
  `kkt_residual` now receives only the constraints active at `x` — a multiplier on a strictly satisfied constraint violates complementary slackness
  and can certify a non-stationary point as converged — and `trust-constr` gets an
  explicit zero constraint Hessian, because scipy's per-constraint BFGS default
  degenerates on the linear mass-budget constraint that dominates sizing work (the
  2-variable payload problem exhausted `maxiter` before, converges in under 30 iterations
  now). Merged additively: +6 tests, no conflicts.
  `cursor/optimization-acceptance-gates-2414` is subsumed (its unique content is the same
  `932fccd` plus a merge commit).
- **Still unmerged, deliberately:** `cursor/r1o2-correlation-updating-e393` and
  `cursor/reconcile-r1o2-correlation-updating-64c5` — both branch from pre-Round-1-close
  ancestors and A14 already reconciled their content; merging them now would resurrect a
  parallel correlation/updating implementation. Left for the orchestrator to close as
  superseded rather than merged.
- **Verified** from a private worktree at `/tmp/a40` with `PYTHONPATH` pinned to it,
  Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1: **595 passed** at the QUAD4 merge, **601**
  with the harvest at `6cf0f49`, **617** after merging the trunk tip back in (A31's P0
  acceptance batch), **642** once A41's FRF correlation block landed, and finally
  **841 passed, 0 failed** (26 s) at `936edc5`, the last commit this sweep pushed to the
  trunk. `ruff check .` clean at every step. `PR_DRAFT.md` refreshed off the stale 498
  baseline — count, title, per-suite breakdown (sums to 841), the QUAD4,
  reduction/expansion and FRF-block capabilities, 40 registered criteria, and the scope
  note that used to claim no continuum elements exist. The trunk moved under this task
  eight times; the count holds only for as long as that does, and the per-suite
  breakdown is the part worth re-deriving rather than trusting.
- **Working-tree hazard, sixth occurrence.** `/workspace` was on another agent's branch
  with an uncommitted FRF-correlation draft (`correlation/frf.py`, untracked) and gained
  three commits *during* this task's first merge attempt, which is how that merge ended up
  parented on A36's reduction work by accident. Redone from the private worktree and
  `/workspace` was handed back on the branch and tree state it was found in. The editable
  install still points at `/workspace/src`, so any private worktree needs
  `PYTHONPATH=<worktree>/src` or it silently tests the shared checkout — which is exactly
  how the first QUAD4 run failed to import `Quad4Element`.

#### A34 — AC-OPT-002/003 strengthened; three parallel backends reconciled (backfill for A02)
- **Task as issued, and why it changed.** A34 was dispatched to wire `ScipyBackend.solve`
  and land the AC-OPT-002/003 cases. By the time it read the tree, that work existed
  **three times**: A27's, already merged and closing GAP-12 on the trunk; A33's, pushed on
  `cursor/optimization-scipy-backend-f421` and still being extended; and this branch's
  merge of A33. Writing a fourth was the GAP-01 failure mode, so the branch adopted the
  trunk's module wholesale — `src/openfemlab/optimization`, `docs/OPTIMIZATION.md`,
  `tests/test_optimization.py` and both acceptance files — and kept only what the trunk
  did not already have. The abandoned intermediate states are in this branch's history,
  not in its diff against the trunk.
- **Independent corroboration of the KKT design.** Working from A33's implementation, A34
  found a verified optimum reported at stationarity **2.6e-2**: the multipliers were fitted
  over the active constraints alone and bound-blocked components projected out afterwards,
  which leaves the residue in the *free* components. Putting the active bound directions
  (`∓e_i`) into the same non-negative fit dropped it to **2.8e-17**. A27's `kkt_residual`
  on the trunk was already built that way, so the fix was discarded on merge — two
  independent derivations of the same requirement, which is the useful part of the finding.
- **What this branch adds: an optimum that distributes material.** The trunk's AC-OPT-002
  oracle is the *uniform* chain (one variable scaling every link), and the multi-variable
  case is gated by sampling — 80 random feasible designs must not beat the answer. Neither
  exercises the thing sizing optimization is for: a solver that never broke the symmetry of
  its start would pass both. The two-link chain does. Each link carries mass with its
  stiffness, so `M = (1 + ε S) I` with `S = k1 + k2` and minimizing mass is minimizing `S`;
  at fixed `S` the fundamental is largest for the split `(3S/5, 2S/5)` (the characteristic
  polynomial becomes `μ² − 1.4 S μ + 0.24 S²`, roots `S/5` and `6S/5`), so the floor is
  first met at `S* = λ*/(1/5 − ε λ*)` **and only at that split**. With `ε = 1/10`, `λ* = 1`
  the optimum is exactly `(6, 4)` at mass 4.
- **Results.** From the symmetric start `(8, 8)`, SLSQP recovers `k* = (6, 4)` to
  **1.1e-16** relative on the objective with `|g| = 2.2e-16` in **10 iterations /
  11 eigensolves**; trust-constr agrees to 2.6e-9 in 123 iterations. A companion test
  guards the oracle itself — over 72 neighbours at radii 1e-3..1e-1, none is both feasible
  and lighter — so a mis-derived "optimum" fails before the solver is blamed.
- **AC-OPT-003 with the optimum *on* a bound.** Raising the `k2` lower bound above its free
  optimum (4) puts the solution on the bound instead of leaving it approached from inside.
  The oracle is a `brentq` root of `λ_1(·, 5) = λ*`. The gate pins the *direction* of the
  error rather than its size, because the methods differ in kind: SLSQP is active-set and
  lands on the bound (`k2 = 5` to 1e-9, stationarity 0), trust-constr is a barrier method
  and stops **1.8e-4** inside it — so its solution is not a KKT point of the bound-active
  problem and its residual legitimately does not vanish. Neither crosses the bound, and no
  point below it is ever handed to an eigensolve.
- **Where the KKT measure earns its keep.** At that solution `df/dx = (0.2, 0.2)` is not in
  the cone of the only constraint gradient, `(−3.8e-2, −6.2e-3)`; a constraint-only fit
  reports **0.166** where the bound-aware fit reports 0. The test asserts the bound-aware
  number, so a regression to the projection form fails here.
- **Also recorded in the docs.** `docs/OPTIMIZATION.md` §8 gains the two-link oracle and the
  bound-active behaviour of each method; §7 gains the measured evidence for why bound
  multipliers belong in the same fit.
- Verified on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1: **600 passed, 0 failed**,
  `ruff check src tests` clean. The five added tests cost 1.2 s.
- **Hazard for the orchestrator, repeated because it recurred.** Three agents implemented
  GAP-12 concurrently, and A34 additionally found the shared `/workspace` checkout on
  another agent's branch with uncommitted work, which it restored before moving to a private
  worktree at `/tmp/a34` (the same hazard A27 and A28 recorded). Dispatching a backfill for
  a task already closed on the trunk is what produced the duplication; a check of the trunk's
  gap table before dispatch would have caught it.

#### A52 — `cursor/optimization-acceptance-gates-2414` merged onto the trunk (backfill for A34)
- **A40's "subsumed" verdict was true when written and is no longer.** The sweep above
  closed `cursor/optimization-acceptance-gates-2414` as carrying nothing but `932fccd`
  plus a merge commit. A34 then pushed four more commits onto it — the two-link AC-OPT-002
  oracle, the bound-active AC-OPT-003 case, the §7/§8 `OPTIMIZATION.md` notes, and its own
  progress record — so the branch had unique content after all and was still unmerged at
  `ec0e927`. Merged here.
- **What the merge actually takes.** Only `tests/acceptance/test_optimization.py`,
  `docs/OPTIMIZATION.md` and the A34 progress entry. Git reported conflicts across
  `optimization/backends.py`, `optimization/problem.py` and `tests/test_optimization.py`
  as well, but those are an artifact of a criss-cross history — the two branches have
  **two** merge bases (`1db2f03` and `7f1a094`), so the ort strategy diffs against a
  synthesized base. Against the real tip base the gates branch changes none of those three
  files: A34 had already adopted the trunk's module wholesale, and the trunk has since
  advanced past it via A40's harvest of `f421`. All three were resolved to the trunk side,
  which is the no-op resolution, not a judgement call.
- The one substantive resolution was an import block: the gates branch's copy of the
  acceptance file predates the trunk's `NaturalFrequency`/`Objective` imports, so the
  union was kept. `PROGRESS.md` took both new sections.
- **Verified** from a private clone at `/tmp/a52` with `PYTHONPATH=/tmp/a52/src`, Python
  3.12.3 / NumPy 2.5.2 / SciPy 1.18.1: **676 passed, 0 failed** at the gate merge itself,
  and finally **876 passed, 0 failed** at `0928f95`, the pushed tip, after the integration
  branch moved six times underneath this task — A44's AC-WORK/AC-UPD-007 tagging, then
  A46's TET4 slice and A49's Bayesian MAP estimator, then A43's dataset-58 sharing and the
  `correlate-frf` CLI command, then the MS-1.1 modal input validation with AC-MODAL-007/009,
  then a further AC-CORR batch. `ruff check .` clean at every step; the 15 AC-OPT gates pass
  on the merged tree. The count is a moving target on a trunk this active: treat it as
  correct for the named commit, not as a standing figure.
- `PR_DRAFT.md` was re-pinned at 876 with the per-suite breakdown re-derived from
  `--collect-only` rather than adjusted arithmetically, and three claims it had outgrown
  were corrected rather than left standing behind a fresh count: TET4 is landed (so
  R2-T02's open list is HEX8, the 3D beam and shell facets, with TET4's bending lock
  pinned by test rather than fixed), the Bayesian MAP path is implemented with its
  AC-UPD-006a/b rows still untagged, and the CLI has a fourth command.
- **Working-tree hazard, seventh occurrence — and this time it ate a commit.** The first
  merge was made in `/workspace` and verified green at 665, and was then destroyed by
  another agent's `git reset --hard` before it could be pushed; the reflog shows the
  branch reset out from under this task three times inside a few minutes. Redone in a
  private clone. The lesson is not new but the failure mode is sharper than the earlier
  reports: `/workspace` loses *committed, unpushed* work, so committing is not a
  safeguard there — only a private checkout is.

#### A43 — R2-T03: the AC-CORR-006 gate lands and the criterion is registered (backfill for A36)
- **AC-CORR-006 is `implemented`.** `tests/acceptance/test_correlation.py` gained the
  nine tests (**19 parametrized cases**) A36's hand-off asked for, and the registry row
  moved from `specified` in the *same* commit (`4310a66`) — the spec-first rule, which the
  registry enforces from both directions: `test_covered_criteria_have_a_tagged_test`
  rejects a status flip without a tagged test, `test_tagged_tests_match_the_registry`
  rejects a tagged test without the status. `docs/ACCEPTANCE_CRITERIA.md` and
  `docs/MODULE_SPEC.md` already carried the ID, its gate and the MS-2.1 consistency
  requirement, so no document needed editing and none was touched.
- **What the criterion actually demands, and how it is met.** The gate has two halves.
  *Reconstruction*: SEREP expansion of noise-free sensor data reproduces the full-space
  analysis shapes at MAC ≥ 0.999. *Consistency*: pairing computed in reduced space equals
  pairing computed in expanded space. Both are checked on two twins — the 10-DOF chain
  fixture read at 5 of its 10 DOFs, and a 12-element cantilever whose accelerometers see
  transverse translation only, so every rotational and axial DOF is unmeasured. The beam
  is the honest test-analysis case: 5 channels observing a 36-DOF free partition, with a
  consistent (non-diagonal) mass matrix.
- **The reconstruction half is exact, not marginal.** `T = Φ(Φ_s)⁺` is a left inverse of
  the sensor partition whenever that partition has full column rank, so in-band noise-free
  data comes back at MAC = 1 to 1e-12 and the instrumented rows return their own values to
  1e-10. Recorded as its own test rather than hidden behind the 0.999 gate, because the
  difference between "passes the gate" and "is algebraically exact" is the difference
  between a threshold that happens to hold and one with no margin question at all.
- **The consistency half is a result, not a tautology** — worth stating because it would
  be easy to assume the two pairings are the same arithmetic. They are not: `T` is not
  orthogonal, so the MAC of expanded shapes is a genuinely different matrix from the MAC
  of the sensor rows. The two differ by **0.13** (chain) and **0.16** (beam) somewhere,
  and the sensor-space matrix carries off-diagonals up to **0.31** on the beam, i.e. real
  ambiguity for the assignment to get wrong. It does not: both `greedy` and `optimal`
  recover the same ground-truth permutation in both spaces, and they agree on
  `unpaired_fe` too when a mode is left unmeasured. The Guyan-TAM mass-weighted route
  MS-2.1 also names (`tam_mass(guyan_reduction(K, sensors), M)` as the MAC weighting)
  reaches the same pairing.
- **Where the gate stops being true, stated in the suite.** A noise sweep pins what the
  0.999 threshold does and does not measure. At 0.2 % per-channel noise both pairings hold
  and the gate passes. At 5 % the gate *fails* — SEREP projects noise onto the retained
  band rather than rejecting it, dropping the worst reconstruction MAC to 0.990 (chain) /
  0.833 (beam) — while both pairings still recover the ground truth exactly. So the
  reconstruction gate is the strictly harder of the two halves, and reading a passing
  AC-CORR-006 as "the pairing is safe under measurement noise" overstates it by more than
  an order of magnitude in noise level. The suite asserts that failure, so the limitation
  cannot silently drift.
- **And where consistency itself breaks, which the criterion's "noise-free" wording
  quietly reserves.** At 8 % noise on the beam the two pairings genuinely disagree. Not by
  crossing wires: every pair they both make is identical, but the expanded pairing drops
  its worst mode below `mac_min` where the reduced one still accepts it, because expansion
  spreads one corrupted channel across all 36 DOFs while the sensor-space MAC only ever
  sees the 5 measured rows. The conservative side is the expanded one — useful to know for
  anyone tempted to treat expansion as cosmetic. Also pinned by a test, so the equality the
  criterion asserts is never read as unconditional.
- **Verified 2026-08-26 08:19 UTC** at the pushed tip `9f8a1b6`, from a private worktree
  with both `PYTHONPATH` entries pinned to it (`<worktree>:<worktree>/src`) — necessary
  because the venv's editable install resolves `openfemlab` to the shared `/workspace/src`.
  Full suite **680 passed, 0 failed** in 104.9 s on Python 3.12.3 / NumPy 2.5.2 /
  SciPy 1.18.1; the same tip with `-k "not ac_corr_006"` gives **661 passed, 19
  deselected**, so this change is exactly +19 and touches nothing else. Repository-wide
  `python -m ruff check .` clean. Rebased five times onto a tip that moved under the work
  each time; the absolute count is only meaningful next to the delta.
- **Working-tree hazard, seventh and eighth occurrence — and the first one that cost a
  branch ref.** `/workspace` was reset out from under the first attempt exactly as A40
  describes, so the work moved to a private worktree at `/tmp/a43`. That path was then
  *also* reset by another agent, and because the branch was checked out there, the reset
  moved the **branch ref**, not just a detached HEAD: two commits were left unreferenced
  and recoverable only from the worktree reflog. Two lessons for anyone following: a
  private worktree needs a path no other agent will guess (`/tmp/a<id>` is exactly the
  pattern everyone uses), and checking a branch out into it converts someone else's
  `reset --hard` from a nuisance into lost work — a detached worktree plus
  `git push origin HEAD:<branch>` would have been safe.
- **Still open on R2-T03**, unchanged by this commit: AC-CORR-009 (TAM
  pseudo-orthogonality) is still unregistered although both the engine and
  `test_tam_pseudo_orthogonality_separates_modes_of_a_longer_chain` exist — registering it
  needs `docs/ACCEPTANCE_CRITERIA.md`, `docs/MODULE_SPEC.md`, the registry row and the
  `EXPECTED_CRITERIA_PER_FAMILY` inventory count in one commit; the `SensorMap.signs`
  wiring (`from_sensor_map`); and the densification of sparse inputs. AC-CORR-006 itself
  needs one more step to reach `verified`: a CI run, not another test.

#### A58 — R2-T03: AC-CORR-009 registered and `SensorMap.signs` wired (backfill for A43)
- **AC-CORR-009 is `implemented`, registered atomically.** `docs/ACCEPTANCE_CRITERIA.md`
  (M2 table row, details entry, inventory **40 → 41** with M2 = 9),
  `docs/MODULE_SPEC.md` (a TAM-mass bullet under MS-2.1 and the gate on MS-2.2's `POC`
  formula), the registry row and the 14 tagged cases in
  `tests/acceptance/test_correlation.py` all land in one commit, which is the only way
  the registry lets a criterion leave `specified` — `test_covered_criteria_have_a_tagged_test`
  rejects a flip without a tag and `test_tagged_tests_match_the_registry` rejects a tag
  without the flip. Registered as **P1, `twin`, spec anchors MS-2.1 + MS-2.2**: P1
  because TAM pseudo-orthogonality is mandated R2-T03 scope, so it belongs on the
  Round-2 exit bar next to AC-CORR-006.
- **The gate, stated precisely.** `|POC| = |Φ_eᵀ M_TAM Φ_a|` with *both* mode sets
  normalized through the TAM mass, paired diagonal ≥ 0.99 and every off-diagonal ≤ 0.10,
  on the same two twins AC-CORR-006 uses (10-DOF chain read at 5 of 10 DOFs; 12-element
  cantilever with 5 transverse channels over a 36-DOF free partition). The plan proposed
  the thresholds; the normalization and the cross form come from MS-2.2, which defines
  `POC = Φ_eᵀ M_ss Φ_a` rather than a self-orthogonality.
- **Half the gate is uninformative on a noise-free twin, and the suite says so.** Exact
  test modes *are* the analysis modes at the sensors up to sign and gain, so after TAM
  normalization the paired diagonal is 1 for **any** symmetric weighting — the 0.99 half
  is arithmetic, not a measurement, on this data. The off-diagonal is the half that
  discriminates, and it separates the three bases cleanly on both twins: SEREP 0.000,
  IRS 0.187 (chain) / 0.018 (beam), Guyan 0.336 (chain) / 0.110 (beam). So a Guyan TAM
  at this instrumentation **fails** the criterion it is registered under, which is the
  point: AC-CORR-009 grades the test-analysis model, not the normalization.
- **On the SEREP TAM it is exact, not marginal.** `T Φ_sensor = Φ` whenever the sensor
  partition has full column rank, so `Tᵀ M T` carries the full-space mass orthogonality
  onto the sensor set and the POC of in-band data is the pairing permutation to 1e-10.
  Pinned as its own test, separately from the 0.99/0.10 assertion, for the same reason
  A43 separated the AC-CORR-006 exactness case: "clears the gate" and "is the identity"
  are different claims.
- **Where the numbers make it a real gate.** Two tests bracket its sensitivity.
  *Sensor placement*: five channels on the chain at (0, 2, 5, 7, 9) leave the Guyan TAM
  at 0.336 and five at (1, 3, 5, 7, 9) bring it to 0.054 — same count, same modes,
  opposite verdict, so on an approximate TAM this is the GAP-07 pretest question in
  disguise. *Model error and noise*: reading the test modes off a 35 %-stiffened chain
  through the nominal TAM drops the diagonal to 0.975 and lifts the off-diagonal to
  0.177 (both halves fail) while a 10 % error still passes at 0.997 / 0.069; and at the
  8 % channel noise that already breaks AC-CORR-006's pairing agreement, AC-CORR-009
  fails too at 0.986 / 0.126, while 5 % passes at 0.994 / 0.077. The diagonal therefore
  only becomes a measurement once the article differs from the model — which is exactly
  when it is wanted.
- **`SensorMap.signs` wiring, done without a new import edge.** `guyan_reduction`,
  `irs_reduction` and `serep_basis` now accept a sensor map wherever they accepted
  master rows, resolved structurally (`rows`/`signs` attributes) rather than by
  importing `openfemlab.workflow.sensors` into `openfemlab.correlation` — the workflow
  layer already imports the correlation layer, and reversing that would close a cycle.
  The transformation is post-scaled by `diag(1/s)`, so reduced coordinates are measured
  channels: `reduce_shapes` reproduces `SensorMap.reduce` exactly, `expand` undoes the
  orientations, and `tam_mass` returns the unoriented TAM conjugated by the sign matrix.
  That last identity is why a reversed cable cannot move the AC-CORR-009 verdict, which
  is asserted entry by entry rather than only at the gate. A43's hand-off named this
  `from_sensor_map`; widening the existing `master` parameter is the smaller API.
- **Not done, and deliberately.** A43 also listed "densification of sparse inputs" —
  `_dense` already densifies sparse `K`/`M` in every constructor and
  `test_reduction_accepts_sparse_matrices` covers it, so there was nothing to do beyond
  confirming it. The `ReductionBasis` is still dense throughout; a sparse-native TAM is
  a GAP-13 scale question, not an R2-T03 one.
- **Verified 2026-08-26** at the pushed tip on
  `cursor/ac-corr-009-tam-orthogonality-113b`, rebased onto trunk `6cc6f53`. Full suite
  **897 passed, 0 failed** in 15.3 s on Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1; the
  merge base `e1a4cc8` gives **876 passed** in the same clone, so this change is exactly
  **+21** (14 acceptance cases + 7 reduction unit tests) and moves nothing else.
  Repository-wide `python -m ruff check .` clean.
- **Working-tree hazard, ninth occurrence — and a new failure mode: `git stash` is
  shared.** A private detached worktree under `/workspace/.git` was not enough this
  time. `refs/stash` is a single ref for the whole repository, worktrees included, so a
  `git stash` taken to measure a baseline was overwritten by a concurrent agent's stash
  between the push and the pop; the pop then restored *their* changes into this
  worktree, with conflicts, and this task's edits were gone — the stash commit was never
  reachable afterwards. The worktree's `HEAD` had also been moved by something outside
  this task. The work was redone in a **fully independent clone** (`git clone <origin>`,
  no `--shared`, its own object store and refs), which is the only arrangement in this
  environment that another agent cannot reach. Two rules for anyone following:
  **never run `git stash` in the shared repository or any worktree of it**, and commit
  and push after every self-contained edit rather than at the end.
- **Still open on R2-T03:** nothing but the `implemented` → `verified` flip for
  AC-CORR-006 and AC-CORR-009, which needs the R2-T09 CI job, not more code.

#### A55 — status snapshot recorded (backfill for A51)
- Wrote [`.agent_workspace/STATUS.md`](STATUS.md): the current verification
  snapshot, Round 1/2/3 status, the R2-T01..T09 task table, a module completion
  table (M1–M6 plus core/elements, IO, CLI, QA), the registry census, the
  prioritized open-gap list, and the [PR #5](https://github.com/9997433-bit/HL/pull/5)
  link.
- **Verified three times, because the tip moved under the task twice.** First
  pass at `0bed333`: 671 passed in 92.04 s. Before the first push the tip was
  at `be38d2c` — the TET4 slice (A46, 66 tests), the Bayesian MAP estimator
  (A49, 35 tests), the AC-WORK/AC-UPD-007 tagging (A44), the strengthened
  AC-OPT gates (A34), the AC-CORR-006 gate (A43) and the `correlate-frf` CLI
  (A54) had landed — re-verified there: 797 passed in 56.94 s. Before the
  second push the tip was at `0928f95` (AC-MODAL-007/009 with typed solver
  input validation, AC-CORR-005/007) — re-verified again: full suite
  **876 passed, 0 failed** in 8.26 s (Python 3.12.3 / NumPy 2.5.2 /
  SciPy 1.18.1, private detached worktree at `/tmp/a55`, `PYTHONPATH` pinned),
  `ruff check .` clean, per-suite counts sum to 876. The snapshot numbers in
  STATUS.md are the `0928f95` ones, not carried over from earlier passes.
- Registry census at `0928f95`: **40 criteria — 32 `implemented`,
  8 `specified`, 0 `verified`** (P0: 29/3, P1: 3/5). The 8 still-`specified`
  IDs are enumerated in STATUS.md §4 — the remaining P0s are AC-CORR-008 and
  AC-UPD-004/005. STATUS.md also flags that `PR_DRAFT.md` is pinned at 841
  (`2774fa1`) and needs one more refresh.
- **Working-tree hazard, live again.** The shared `/workspace` checkout was
  mid-merge with conflicts (`UU` on this file) and carried a concurrent agent's
  staged TET4 slice when this task started; HEAD moved between two consecutive
  commands. All work was done in the detached private worktree and nothing in
  `/workspace` was touched after the fact was noticed.

### Round 3 — SOTA Polish & Final Acceptance
**Status:** PENDING

## Round Conclusions

### Round 1 — Conclusion (FINAL, recorded by A17)

**Recorded** 2026-08-26 at commit `bae4b77` on `cursor/femtools-industrial-7aa3`.
Full `pytest`: **192 passed, 0 failed** (1.38 s, Python 3.12 / NumPy 2.5.2 /
SciPy 1.18.1). During conclusion the tree was still live: an earlier run caught the
in-flight CLI test emitting a progress line before its JSON (191 passed / 1 failed);
`bae4b77` fixed it by routing diagnostics to stderr, restoring green.

**Implemented features.**
- Core FEM: node-major DOF model with SPCs and lumped masses; spring / truss /
  planar-beam elements; one-pass preallocated COO→CSR assembly with free/constrained
  partitioning (R1-O1, A10).
- Modal solver: one `ModalSolver` façade with dense and sparse shift-invert backends,
  static condensation of massless DOFs, mass normalization, deterministic signs,
  participation/effective masses, and a shift-invert LU cache; the former duplicate
  `modal/eigen.py` is now a thin adapter over it (R1-O1, A08, A10).
- Correlation: MAC / autoMAC / mass-weighted MAC, MSF, pseudo-orthogonality, COMAC,
  sensor/DOF alignment with orientation signs, Hungarian pairing with MAC threshold and
  frequency window/penalty, frequency-error metrics, schema-versioned JSON
  `CorrelationReport` (A06, A08; R1-O2 variant preserved on
  `cursor/r1o2-correlation-updating-e393`).
- Updating: Fox–Kapoor eigenvalue, modal-superposition eigenvector, and MAC
  sensitivities — vectorized and sparse-aware; affine `ScalingModel` (one eigensolve per
  iteration); LM / Gauss–Newton updater with Tikhonov regularization, bounds, and
  per-iteration MAC re-pairing (A04, R1-O2, A10).
- IO: schema-versioned native YAML/JSON round trip for models, modal results, and test
  data (A09); ASCII UFF/UNV dataset 55/58 reader (A12); minimal Nastran BDF reader
  (GRID/CROD/MAT1 → `NeutralModel`, A18).
- CLI: `modal` / `correlate` / `update` over the single correlation kernel,
  machine-readable JSON on stdout with diagnostics on stderr, covered end to end
  (R1-F1, A16, `bae4b77`).
- Spec & QA stack: architecture doc, module spec MS-0..6, 35 quantified acceptance
  criteria with a machine-readable registry, SOTA gap register GAP-01..15, boundary and
  probe suites, benchmarks, packaging + push CI, README (R1-F1/F2, A01, A03, R1-G1/G2,
  A11, A20).
- Verification highlights: closed-form modal validation to 1e-9 (worst continuum case
  0.2%); E2E model→modal→correlate→update→re-solve converges 22.86% → 0% frequency
  error at MAC 1.0; 10-DOF/4-group twin recovery to machine precision; analytic vs FD
  sensitivities agree to ≤ 1e-6; 50 repeated eigensolves with zero drift.

**Remaining defects / open items.**
- Uncommitted in-flight work at conclusion time: the MS-4 correction workflow package
  (`workflow/` stages, gates, selection, correction, report) and the optimization
  build-out (`optimization/` variables, responses, gradients, problem) exist only in the
  shared working tree. Round 2 must land them atomically with tests and consumers.
- The updater takes the analytic-Jacobian path only for frequency-only residuals; the
  shape/MAC residual block still falls back to finite differences even though
  `mac_sensitivity` is analytic — a cheap wiring win.
- MS-3.5 Bayesian MAP updating and MS-3.6 automatic parameter selection (collinearity
  screening) are unimplemented; optimization remains a stub pending the in-flight work
  (GAP-12).
- Industrial IO residue (GAP-03): no UNV 2411/2412 geometry, no UFF writing or binary
  58b, BDF limited to GRID/CROD/MAT1 (no coordinate systems, large-field or continuation
  cards), no OP2, no meshio bridge.
- No damping models, FRF synthesis, harmonic response, or FRF correlation (GAP-04/05);
  no modal parameter extraction from measured FRFs (GAP-06); no pretest planning, TAM
  reduction (Guyan/IRS/SEREP), or mode-shape expansion (GAP-07/08).
- Element library has no continuum elements (QUAD4/TET4/HEX8) and no 3-D beam.
- GAP-01 (split-brain core) is resolved — one eigensolver, one neutral contract, one
  correlation kernel — but the concurrency hazard that caused it persists: three broken
  import states and one transient CLI regression were observed during Round 1 while
  agents edited the shared tree. The "seams land atomically with consumers" rule stays
  in force for Round 2.

**Performance baselines** (single BLAS thread, medians; reproduce via `benchmarks/` and
`tests/probes/probe_performance_regression.py`, which gates on them).
- Modal solve, spring chains: 10/100/1000 DOF at 0.669 / 1.180 / 1.815 ms cold (R1-G1);
  repeated solves 1.17x / 1.11x / 1.14x faster with the factorization cache (A10).
- Sparse assembly at 2,000 DOF: 26.302 → 19.331 ms (1.36x); repeated 1,600-DOF sparse
  solve: 12.270 → 9.449 ms (1.30x).
- Eigenvalue sensitivity, 240 DOF / 24 modes / 12 parameters: 1.829 → 0.678 ms (2.70x).
- Five-iteration 100-DOF updating loop: 35.301 → 7.904 ms (4.47x) with exact vectorized
  sensitivities.

**Round 2 priorities.**
1. Land the in-flight MS-4 workflow and optimization packages atomically with their
   tests and consumers; wire the analytic MAC Jacobian into the updater's shape-residual
   path.
2. Industrial IO depth: UNV 2411/2412 geometry, UFF writing, broader BDF cards and
   coordinate systems, meshio bridge (OP2 and binary 58b as stretch).
3. Dynamics chain: damping models, FRF synthesis, harmonic response, FRF correlation,
   then MPE from measured FRFs (GAP-04/05/06).
4. Updating depth: Bayesian MAP (MS-3.5), automatic parameter selection (MS-3.6),
   parameter target resolver and assembled dK/dp providers over real element groups.
5. Element growth (QUAD4/TET4/HEX8 continuum set) and pretest/TAM/expansion
   (GAP-07/08).

**Round 1 exit bar: MET.** Module content, spec coverage, and integration health are all
green — `import openfemlab` is clean, the full committed suite collects and passes end
to end (**192 passed**), and repo-wide Ruff is clean on committed files.

#### Addendum — Round 1 nearing completion (A15, commit `490dc4c`)

The conclusion above credited GAP-01 as resolved while `solver/modal.py` still carried a
second `ModalResult`; that duplicate is now deleted and `core.results.ModalResult` is the
only result contract, pinned by `tests/test_result_contract.py`. Full suite at this commit:
**212 passed** (Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1).

What is left before Round 1 can be declared closed is unchanged in kind and small in number:
the MS-4 `workflow/` correction package and the `optimization/` build-out are still landing
from the shared working tree and are the only pieces of declared Round 1 scope not yet
committed with tests. Everything else in the "Remaining defects / open items" list above is
Round 2/3 scope by design, not Round 1 debt. Once those two packages land green, the round
closes on content as well as on the exit bar.

#### Addendum — Round 1 COMPLETE (A32, backfill for A29)

The two packages the A15 addendum listed as the last uncommitted Round 1 scope are both
landed and green on this branch. A13's MS-4 `workflow/` package was verified in by A26 at
`5bc6a6d`; the `optimization/` build-out (`variables`, `responses`, `gradients`,
`problem`, `sizing`, scipy `backends`, 16 tests) arrived together with the damped-dynamics
track when `acda625` merged `cursor/dynamics-damping-frf-9500` —
`solver/dynamics.py` now carries Rayleigh/modal/structural damping, complex modes with
modal phase collinearity, modal/complex-modal/direct FRF synthesis, harmonic response,
residual flexibility, and FRAC/FDAC (82 tests, the largest suite in the repository).
`docs/OPTIMIZATION.md` (`9c674d5`) is the design reference the package points at.

Verified at `9c674d5` on Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1, from a private
detached worktree (`/tmp/a32`, `PYTHONPATH` pinned to its `src` per the A14 method note —
the shared `/workspace` checkout had been switched onto `cursor/quad4-plane-stress-element-b99c`
by a concurrent agent mid-run, the fifth occurrence of the working-tree hazard counting
the lost-ref variant A28 reports): full
suite **430 passed** (4.9 s), `ruff check .` clean. **Round 1 is closed on content as
well as on the exit bar.** The ready-to-file PR for `main` (title + body) is in
`.agent_workspace/PR_DRAFT.md`.

#### Addendum — independent close-out verification (A30, backfill for A14)

A30 ran the same close-out independently and the two agents' numbers agree, so the
Round 1 declaration rests on two separate measurements rather than one: full suite
**332 passed** at `5bc6a6d` (9.98 s) before the dynamics/optimization merge, and
**430 passed** (4.6 s) with `ruff check .` clean (ruff 0.16.4) on the merged tip
`9c674d5`, both on Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1 from the `/tmp/a23`
worktree with `PYTHONPATH` pinned per the A14 method note. Per-file collection sums
to exactly 430 (dynamics 82, updating 57, correlation 52, modal 44, workflow 38,
acceptance 46, CLI 22+1, core 18, result contract 17, optimization 16, IO 24,
boundary/perf/e2e/scaffold 13).

A30 completed the A32 PR draft rather than replacing it: added the per-suite test
breakdown and the `docs/ARCHITECTURE.md` §7 FEMtools comparison table to the PR body,
and corrected one overstated claim — `ScipyBackend.solve` is a pinned Round 2 stub
(its own test asserts `NotImplementedError` naming GAP-12), so the optimization bullet
now says the backend seam and KKT result fields exist while the `minimize` wiring is
Round 2 scope. Two docs-only close-out commits raced this one onto the branch tip
(`516184b`, `b9d26f0`); this record was rebuilt on top of them instead of fighting the
rebase, so nothing from the concurrent closure was overwritten.

#### Addendum — Independent sign-off audit (A23, backfill for A20)

Ran in parallel with the A30/A32 closure, from a private worktree with `PYTHONPATH`
pinned to its own `src` (the shared environment pointed at a sibling worktree's sources).
Independently re-verified the full suite green at five successive branch tips while the
closure landed — `2bfad98` **195**, `36befc3` **250**, `5bc6a6d` **332**, the merged tip
`3f4cad6` **430**, and, after the A27 optimization backend landed, **498 passed,
0 failed** — with repo-wide `ruff check .` clean at every checkpoint (Python 3.12 /
NumPy 2.5.2 / SciPy 1.18.1). Concurs with the closure: the exit bar is met and both A15
carry-over packages are landed and green, so COMPLETE stands.

One bookkeeping caveat carried to Round 2: per AC §1.2 the P0 registry rows AC-UPD-007
and AC-WORK-001/002/004/005 are still `specified` (20 of 40 criteria `implemented`
after the A27/AC-DYN batches, none `verified`), even though `tests/test_workflow.py`
demonstrates the AC-WORK gates numerically — tagging them is already scheduled with
R2-T06 and the next acceptance batches. The first PR body draft (`17d03ba`) was folded
into the closure lineage and superseded by the A30/A32 polish now in
`.agent_workspace/PR_DRAFT.md`; both record the same platform state.

#### Round 2 — P0 acceptance batch 2 (A31, backfill for A21)

Seven P0 criteria moved from `specified` to `implemented`, taking the registry to
**22 of 40** covered (20 P0, 2 P1; none `verified` yet). Landed as four commits on
`cursor/femtools-industrial-7aa3`, tip `33473fe`.

**AC-MODAL-004..006** (`3570fd2` solver, `3f4cad6` reproducibility, `69ae903` tests).
The acceptance tests exposed three real gaps in `solver/modal.py` rather than merely
recording existing behaviour:

- *Rigid bodies.* Free-free chains now report exactly `f = 0` (and infinite period) for
  as many modes as the nullity of `K`, with the clip driven by a rigid-body threshold
  instead of leaking a tiny positive eigenvalue. Verified against the closed-form
  free-free spectrum and, independently, against an inertia-relief constrained run.
- *Determinism.* ARPACK seeds its Lanczos start vector randomly, so repeated sparse
  solves were not bitwise identical. `ModalSolver.solve` grew a `seed` argument
  (default 0) that builds the start vector deterministically. Separately, the MS-1.3
  sign convention broke on near-degenerate peaks: strict `argmax` let the dense and
  Lanczos backends pick different "largest" components on symmetric modes. Both
  `solver/modal.py` and the `updating/scaling_model.py` fallback now treat components
  within `1e-8` of the peak as tied and break the tie on the lowest DOF index, which is
  what the spec text already said.
- *Residuals.* Every returned eigenpair is gated on
  `‖K phi - lambda M phi‖ / ‖K phi‖`, and a breach raises the new
  `SolverConvergenceError` carrying the offending residuals and the tolerance. A flat
  `1e-8` is not reachable for the cantilever beam — its spectrum is wide enough that
  round-off dominates — so the gate is `max(tolerance, floor)` with an arithmetic floor
  derived from the matrix norms. One test asserts the general gate; a second pins the
  cantilever as the *only* case where the floor binds, so the escape hatch cannot widen
  unnoticed.

**AC-CORR-003..004** (`b1b0ab8`). A pairing twin permutes, sign-flips, drops and pollutes
a known mode set and requires both the greedy and the Hungarian method to recover the
ground-truth permutation, with sub-threshold candidates reported unpaired. For COMAC the
tests confirm localisation of a gain-error sensor (directly and through the pairing) and
then document a blind spot worth knowing: a reversed-polarity channel scores a *perfect*
COMAC at the faulty DOF, so `argmin` points at a healthy sensor instead, and a polarity
error on a subset of modes does not localise either. COMAC diagnoses magnitude faults,
not sign faults.

**AC-UPD-002..003** (`33473fe`). Fox-Kapoor eigenvector derivatives match central
differences to ~1e-8 over the complete basis at two operating points, well inside the
1e-5 gate, and their truncation error is a strictly decreasing sequence that reaches zero
at full rank. Getting there needed one correction to the obvious method: when aligning the
perturbed shapes, only the *sign* of the modal scale factor may be transferred, because
rescaling by the full MSF divides out the `-1/2 phi^T dM/dp phi` normalisation term and
breaks every mass-parameter derivative (stiffness ones survive, since their self term is
zero). A test pins that asymmetry so the shortcut is not reintroduced. The twin
experiments detune two or three factors by ±20 % — stiffness only, mixed stiffness/mass,
and a two-factor case — check the starting model genuinely fails both MS-4.2 gates, and
require recovery to 1e-3 in the infinity norm within ten iterations with a non-increasing
objective; a fourth case repeats it through the finite-difference/MAC-residual path so the
result does not rest on the analytical Jacobian.

Verified at `33473fe` on Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1: full suite
**550 passed**, `ruff check .` clean (ruff 0.16.4). Re-verified after the concurrent
criterion-inventory commit `c8e3ce2` landed underneath this record: **611 passed**, ruff
clean. Run from a private clone (`/tmp/a31c`) rather than a worktree — the first attempt
used a worktree under `/tmp` and lost committed test edits to a concurrent reset, the
working-tree hazard A28/A32 already report.

Remaining P0 rows still `specified`: AC-MODAL-007/009, AC-CORR-005/007/008,
AC-UPD-004/005/007, AC-WORK-001/002/004/005.

#### A47 — reconcile A23's criteria count (backfill for A35)

- Audited the criteria document against the machine registry: both define the same
  **40 distinct IDs**, split M1..M6 as **9 + 8 + 9 + 5 + 4 + 5**. The two suffixed M3
  rows (`AC-UPD-006a` and `AC-UPD-006b`) are separate criteria under one dense base
  number. No criterion is missing from either source; A23's **41** was arithmetic, not
  a lost registry row.
- Commit `c8e3ce2` records that inventory in `docs/ACCEPTANCE_CRITERIA.md` and pins the
  per-family counts in `test_criteria_registry.py`. It also fixes real documentation
  drift left by the M6 insertion: the enforcement contract moved from section 7 to
  section 8, and the blocking-criterion check now correctly describes M1..M6.
- Full committed suite verified in the clean `/tmp/a47` worktree at `c8e3ce2`, with
  `PYTHONPATH=/tmp/a47/src`: **611 passed** in 122.32 s. The shared checkout contained
  an unrelated untracked `tests/acceptance/test_workflow.py`; it was preserved and
  excluded by verifying the exact committed tree rather than deleting concurrent work.

#### A46 — R2-T02 continued: TET4 constant-strain tetrahedron (backfill for A42)

`Tet4Element` in `core/elements.py` is the second element slice of GAP-02: the 4-node
linear tetrahedron with `UX`/`UY`/`UZ` at each node, `K = V Bᵀ D B` from a constant `B`,
consistent mass `ρV/20 (1 + I) ⊗ I₃`, row-sum lumping to `ρV/4` per node, and constant
strain/stress recovery. The 3D elasticity matrix moved out into a reusable
`solid_constitutive_matrix(material)` alongside the existing planar one, so HEX8 and the
solid BDF cards can share it.

**Meshing.** `mesh/simple.py` gained `tet_block_mesh` (plus `MeshBuilder.add_tet4`), a
structured box whose cells are split by the **Kuhn/Freudenthal** triangulation into six
tetrahedra. Kuhn was chosen over the 5-tet split because it is translation-invariant:
every cell puts the same diagonal on a shared face, so the mesh is conforming without a
checkerboard orientation rule. The six connectivity tuples are stored pre-oriented for
positive volume (odd permutations have their last two nodes swapped), and a test walks
every triangular face of a 2×2×3 block to confirm each interior face is shared by exactly
two tets and the boundary count is `4(n_x n_y + n_y n_z + n_z n_x)`.

**Verification** — `tests/test_tet4.py`, **66 tests**, layered like `test_quad4.py`:

- *Patch.* A 3×3×3 Kuhn box (64 nodes, 162 elements) with its eight interior nodes pulled
  20 % off the grid by a deterministic trig offset, driven by a prescribed linear field on
  every boundary node. The interior displacements come back at **2.8e-16 relative** and
  every element reports the same constant stress to 1e-9 relative — the element passes the
  patch test on genuinely distorted geometry, not just on the reference tetrahedron.
- *Oracle.* A roller-supported block under uniaxial extension recovers `σxx = E ε` with
  all five other components at zero, and the far corner contracts by exactly `−ν ε w`
  and `−ν ε h`; strain energy of a linear field matches `½ V εᵀ D ε` to 1e-12.
- *Kinematics.* Exactly six zero-energy modes (no hourglassing to guard against — one
  point is full integration for a constant-strain element), zero nodal force under all
  three rigid translations, zero strain energy and zero strain under all three rigid
  rotations, invariance of `K` under a Rodrigues rotation about `(1,1,1)`.
- *Modal.* Six rigid-body modes on a free block; with lateral motion suppressed and
  `ν = 0`, the axial spectrum converges to `c/4L` **from above** at rates 4.09/4.04, hitting
  3.7e-4 at 16 elements; mass-orthonormality below 1e-9; lumped mass never above
  consistent.
- *Limitation, pinned.* Bending locks hard. Against the Euler–Bernoulli cantilever the
  first frequency is **+207 %** at 108 DOF and still **+25 %** at 2475 DOF, where QUAD4 is
  inside 2 % with a fraction of the equations. The test asserts the monotone-from-above
  decay *and* that the finest mesh is still 10–30 % stiff, so nobody mistakes TET4 for a
  bending element.

**Scope deliberately left alone.** No AC-ELEM-* rows were registered. `test_quad4.py` and
`test_tet4.py` both produce the evidence for the three proposed criteria, but registering
them means moving the 40-criterion inventory A47 has just pinned in
`test_criteria_registry.py` and `ACCEPTANCE_CRITERIA.md` §1.4 — a spec-first change that
belongs with the HEX8 slice that completes the element family, not squeezed in beside it.

Verified in a private clone at `/tmp/a46` with `PYTHONPATH=/tmp/a46/src`, on Python
3.12.3 / NumPy 2.5.2 / SciPy 1.18.1: **702 tests collected, 702 passed**, `ruff check .`
clean. That is the trunk's 636 at `1db2f03` plus the 66 new ones. The trunk moved to
`0bed333` (A40's merge sweep and A41's FRF report block) while this was being verified, so
the slice was merged onto that tip and re-run: **737 passed**, Ruff still clean. It moved
three more times during the push — A44's AC-WORK/AC-UPD-007 tagging, A43's AC-CORR-006
gate and the R2-T04 Bayesian MAP landing — so the branch was synced after each and re-run
at 740, 746 and finally **781 passed** at the pushed tip `e4bd20c`, Ruff clean throughout.
Every conflict was the Active Pool table or the appended entries at the end of this file,
where each side had added its own rows; all were kept.

**Working-tree hazard, again.** A concurrent agent ran `git reset --hard` on `/workspace`
mid-edit and discarded the first pass of this element wholesale. The work was redone in a
private clone at `/tmp/a46`. Every entry since A28 has now hit this; the shared checkout
should be treated as read-only scratch and nothing but a fetch target.

#### A44 — AC-WORK and AC-UPD-007 tagging (backfill for A23)

Closes the bookkeeping caveat A23 carried into Round 2: five **P0** criteria that the
engine had satisfied numerically since A13 were still `specified` because no tagged
acceptance test claimed them.

- Added `tests/acceptance/test_workflow.py`, the M4 suite the registry has always named
  and never had (11 tests). It builds its own twin from the shared `ten_dof_chain`
  parameterization rather than reusing `tests/test_workflow.py`, so the criterion is
  checked independently of the developer suite that motivated it.
  **AC-WORK-001** wraps the AC-UPD-003 detuning in S1–S6 and asserts every paired mode
  clears MAC 0.95 and |Δf| 1 % from a baseline at min MAC 0.913 / 4.53 %, with the
  recovered factors within 1e-3 of `(1.20, 0.80, 1.15)`; **AC-WORK-002** compares two
  seeded runs field by field to 1e-12 and byte-compares the JSON with wall times
  dropped; **AC-WORK-004** drives both the S2 pairing gate and the S6 validation gate
  and checks the typed `{stage, reason}` halt leaves S3–S6 `SKIPPED` and nothing marked
  PASS; **AC-WORK-005** walks the report schema (`schema_version "1.0"`, both
  correlation blocks, iteration history, parameter table with σ_post, gates,
  environment, per-stage wall time) and its JSON round trip through memory and disk.
- Extended `tests/acceptance/test_updating.py` with **AC-UPD-007** (3 tests) over
  `workflow/selection.py`: the screen alone on a rank-deficient matrix, then the twin
  where `k1_twin` scales exactly the `k1` spring group. S3 detects the pair at cosine
  1.0000, freezes `k1_twin` with `reason="collinear"` and `collinear_with="k1"`, and the
  run still lands the survivors within 1e-14 of the truth at min MAC 1.0 and max |Δf|
  1.9e-13 % — the AC-UPD-003 gates, whose constants the new tests reuse rather than
  restate.
- Registry: the five criteria move `specified → implemented`. The inventory is now
  **28 implemented / 12 specified of 40**; the remaining P0 rows are AC-MODAL-007/009,
  AC-CORR-005/007/008 and AC-UPD-004/005, all engines-exist/tests-missing cases.
- Atomic doc update in the same landing: `docs/SOTA_GAP_ANALYSIS.md` no longer lists the
  MS-3.6 subset selection as absent under GAP-10 or the session report schema as absent
  under GAP-14, and `ROUND2_PLAN.md` stops calling AC-UPD-007 the last unimplemented P0
  (R2-T06's remainder is P1 depth work).
- Verified on Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1 from the private `/tmp/a44merge`
  worktree with `PYTHONPATH` pinned to its own `src`: **674 passed** in 50 s,
  `ruff check .` clean, after merging the A40 sweep that landed underneath this record.
- Third report of the shared-checkout hazard, and the sharpest one yet. A concurrent
  agent reset `/workspace` onto `cursor/femtools-industrial-7aa3` mid-run and the
  tracked-file edits were lost, so the work was redone from private worktrees. The
  integration tip then moved four times during the landing: the AC-UPD-002/003 batch that
  arrived in parallel was merged into the M3 suite by hand rather than overwritten, and
  the A40 sweep picked up the still-untracked `tests/acceptance/test_workflow.py` from the
  shared checkout and committed it verbatim at `529739e`. The AC-WORK half of this task
  therefore reached the branch under A40's commit; the file merged without conflict
  because it is the same bytes. Nothing was duplicated or reverted, but the shared
  checkout is now demonstrably a place where one agent's uncommitted work becomes
  another's commit — private worktrees are not optional.

#### A49 — R2-T04 starts: the MS-3.5 Bayesian MAP estimator lands (backfill for A47)

First slice of the second Round-2 gate-blocker. The MAP estimator exists and is tested;
the AC-UPD-006a/b registry rows stay `specified` because their tags belong in
`tests/acceptance/test_updating.py`, which is the follow-on slice.

- `src/openfemlab/updating/bayesian.py` (new): `GaussianPrior` over the free design
  variables — scalar, per-parameter or full `C_p`, plus `from_std`, `uninformative` and
  an optional prior mean; `covariance_matrix` / `precision_matrix` validate and expand a
  covariance spec (symmetry and positive-definiteness included). `map_step` and
  `posterior_covariance` are the bare kernels;
  `PosteriorEstimate` reports the mean, the covariance, per-parameter σ_post against
  σ_prior, a correlation matrix, credible intervals and a table;
  `BayesianUpdater` / `update_model_bayesian` / `BayesianUpdatingResult` are the
  run-level API, re-exported from `openfemlab.updating` and the lazy top-level map.
- **No second updating loop.** `ModelUpdater` grew two overridable hooks —
  `normal_equations` and `penalty` — extracted from `run()` with behaviour unchanged, and
  `BayesianUpdater` substitutes
  `(Jᵀ C_ε⁻¹ J + C_p⁻¹) Δθ = −[Jᵀ C_ε⁻¹ r + C_p⁻¹ (θ − θ₀)]` plus the matching
  noise-weighted cost. Mode re-pairing, bounds projection, LM damping and the
  Fox–Kapoor/FD sensitivity stack are shared, per the GAP-01 rule. The posterior is a
  Laplace estimate from a Jacobian re-evaluated *at* the converged point rather than the
  last iterate's, and falls back to a pseudo-inverse on a rank-deficient information
  matrix so an unidentifiable direction reports zero variance instead of raising.
- The prior lives in the updater's **design space**, so a `log_scaled` parameter gets a
  lognormal prior on its scaling factor. Documented in the module and pinned by a test;
  a physical-space spelling is left as an open question for the AC slice.
- `tests/test_bayesian_updating.py` (new, 35 tests) on the canonical 2-DOF grounded chain
  (`two_dof_chain` as an affine `ScalingModel`, two stiffness factors against two measured
  frequencies, truth `(1.15, 0.88)`). Both MS-3.5 limits are pinned twice, at the algebra
  level and end to end: the MAP step's relative distance to the Gauss–Newton step falls
  monotonically over prior precisions 1e-2 → 1e-6 → 1e-12 and lands at ≤ 1e-8 even with a
  deliberately off-centre prior mean (AC-UPD-006a), and a σ = 1e6 run reproduces
  `update_model`'s parameters to 1e-8; σ_post ≤ σ_prior componentwise, tighter priors
  shrink the posterior monotonically over σ ∈ {1, 0.1, 0.01}, and at σ = 0.01 the solution
  stays inside 3σ_prior of θ₀ while provably *not* recovering the truth (AC-UPD-006b).
  Also covered: covariance validation rejects negative, mis-sized, asymmetric, indefinite
  and rank-3 specs; the step is invariant to a uniform `C_ε` rescale but follows a
  non-uniform one on an over-determined fit; a 100× noise covariance widens σ_post exactly
  10×; the weak-prior twin recovers `(1.15, 0.88)` to ≤ 1e-3.
- Verified at the rebased tip on Python 3.12.3 / NumPy 2.4.4 / SciPy 1.18.1 from the
  private clone `/tmp/a49`: **709 passed** in 103 s, `ruff check .` clean. Baseline before
  the change on the same clone was 671.
- Remaining for R2-T04: tag AC-UPD-006a/b in the M3 acceptance suite and flip both rows
  to `implemented`; surface σ_post through the CLI `update` document and the
  `CorrectionReport` parameter table (AC-WORK-005 already reserves the column).
- Fourth run to take the private-clone route rather than the shared `/workspace`
  checkout, and it was again the right call: the integration tip moved twice during this
  landing (a 34-commit A40/A52 merge sweep, then the A43 AC-CORR-006 batch) and both were
  absorbed by rebase with no conflicts and no lost work.

#### A62 — superseded-branch closure record and trunk verification (backfill for A40)

- Added `.agent_workspace/BRANCH_CLEANUP.md` with explicit closure dispositions for
  `cursor/r1o2-correlation-updating-e393`, `cursor/merge-quad4-backfill-4595`, and
  `cursor/dynamics-damping-frf-9500`.
- Verified against fetched remote tips that the QUAD4 backfill (`d3498b4`) and
  dynamics/FRF (`f4683d6`) branches are ancestors of trunk with zero branch-only commits.
  R1-O2 (`f1452f8`) remains intentionally non-ancestral: A14's reconciliation tip
  (`5762f2d`) is on trunk, while merging the three obsolete branch-only commits would
  restore a parallel implementation and weaken the trunk's null-mode MAC contract.
- Confirmed that none of the three branches has an associated open or closed GitHub pull
  request. All three remote branches can be deleted; R1-O2 must be closed as superseded,
  not merged.
- Verified the exact committed trunk snapshot `8604807` from the isolated
  `/tmp/a62-cleanup` clone with `PYTHONPATH` pinned to its own `src`: **876 passed,
  0 failed** in 29.26 seconds.

#### A67 — trunk verification (backfill for completed A65)

- Verified the integration tip `e1a4cc8` from the isolated `/tmp/a38` worktree with
  `PYTHONPATH` pinned to its own `src`: **876 passed, 0 failed** with `pytest -q`;
  `ruff check .` also passed cleanly.
- The unpinned pytest invocation inherited `/workspace/src` and failed collection
  against that unrelated checkout. Pinning the branch-local source removed the
  cross-worktree import contamination; no product-code fix was required.

#### A57 — R2-T04 closes its acceptance gate: AC-UPD-006a/b registered (backfill for A49)

The second slice of the second Round-2 gate-blocker. A49 landed the MS-3.5 estimator
and left the two registry rows at `specified` because their tags belong in the M3
acceptance suite; this run writes them, flips both rows in the same commit, and
finishes the σ_post surface A49 listed as outstanding.

- `tests/acceptance/test_updating.py` gains eight tagged tests on the suite's *own*
  rig — the `ten_dof_chain` split into three stiffness and two mass groups, run as the
  AC-UPD-003 `stiffness` twin, so the deterministic answer the weak-prior limit has to
  reproduce is already pinned a few tests above. Deliberately not a copy of A49's 2-DOF
  unit suite: different model, different residual dimension (6 modes / 3 free factors,
  over-determined rather than square), and the linearization the step tests compare on
  is assembled in the suite from the model's analytic frequency sensitivity rather than
  read back from either estimator.
- **AC-UPD-006a** three ways. A zero prior precision is an *identity*, not a limit, so
  the MAP step matches Gauss–Newton to 1e-12 even with an off-centre prior mean. Over
  precisions 1e-2 → 1e-6 → 1e-12 the relative gap falls monotonically 2.2e-1 → 3.8e-5 →
  3.8e-11, inside the documented 1e-8; the sweep asserts the strongest prior bends the
  step by > 10 % so the gate cannot pass vacuously. End to end a σ = 1e6 prior
  reproduces the deterministic run's factors to 1e-8 and still clears the MS-4.2 gates.
- **AC-UPD-006b** likewise. σ_post ≤ σ_prior componentwise over σ ∈ {1, 0.1, 0.01} and
  below the width the same run reports with no prior at all; every narrowing of the
  prior strictly narrows every posterior marginal; and at σ = 0.01 the solution stays
  inside 3σ_prior of θ₀ (7.9e-6, against a 3e-2 limit) while provably *not* recovering
  the truth — which is what makes the three-sigma statement a gate rather than an
  accident of a prior that happens to agree with the data.
- **A real bug fell out of the σ_post work.** `ModelUpdater.run()` recorded the bare
  data misfit as the starting cost but compared every trial against `cost + penalty`,
  so the first acceptance test weighed two different objectives. Both penalties in the
  tree are zero at the starting point — `regularization` is anchored at θ₀, and so is a
  Gaussian prior that takes its default mean — which is why nothing caught it. Give the
  prior an explicit mean and it bites: with `from_std(0.01, mean=[0.90, 1.10])` on the
  2-DOF chain the initial cost read 2.85e-3 against a first trial of 8.5e-3, no step
  was ever accepted, and the run returned θ₀ with the prior mean silently ignored.
  Penalizing the starting cost fixes it (initial 4.50, step accepted, run lands on the
  prior mean). `GaussianPrior.mean` was effectively dead at run level until now; the
  existing test only exercised the linearized step.
- **σ_post reaches the `CorrectionReport`.** AC-WORK-005 has reserved the column since
  the schema landed, but S4 could only fill it with the least-squares stand-in
  `C_post ≈ σ² (JᵀJ)⁻¹`, σ² read off the final residual — on the noise-free twins the
  workflow tests use that collapses to ~1e-12, a statement about how well the fit
  closed rather than about what the measurement was worth. `CorrectionWorkflow` now
  takes `prior` and `noise_covariance`; either switches S4 from `ModelUpdater` to
  `BayesianUpdater` and the column carries the Laplace posterior the run already
  evaluated at its solution. With neither, nothing changes to the last digit, so
  AC-WORK-002 reproducibility and every existing report stay put.
- Verified from the isolated clone with `PYTHONPATH` pinned to its own `src`:
  **888 passed** (884 at the merged trunk tip + 1 updating + 3 workflow, on top of the
  8 acceptance tests already counted), `ruff check .` clean.
- **Left open for R2-T04:** σ_post in the CLI `update` document — that needs a
  prior/noise block in the update spec schema, a column in the rendered table and the
  JSON payload, and CLI doc updates, which is a slice of its own rather than a
  footnote. Also still open from A49: whether the prior should be expressible in
  *physical* space rather than only the updater's design space.
- **Process note, the hard way.** The private-clone rule A48/A49 established is not
  enough on its own if the clone has a *guessable* name. A concurrent agent ran
  `git checkout && git fetch && git reset --hard` inside `/tmp/a57` — the obvious path
  for subagent A57 — and destroyed this run's uncommitted working tree; only the
  already-pushed acceptance commit survived. Redone in a timestamped, PID-suffixed
  directory. Two rules, not one: work in a private clone, and give it a name no other
  agent would pick.

#### A64 — Chinese quickstart user guide `docs/USER_GUIDE_zh.md` (backfill for A52)

Documentation-only landing: the first end-user document in a language other than
English, aimed at the FEMtools-adjacent audience the platform targets.

- `docs/USER_GUIDE_zh.md` (new): a Simplified-Chinese quickstart covering the whole
  README surface plus the file formats the README only points at. Sections: project
  positioning with a FEMtools-module-to-OpenFEMLab-module mapping table (Framework →
  API/CLI, Dynamics → `solver`, Pretest & Correlation → `correlation`, Model Updating →
  `updating`, Optimization → `optimization`, MPE → not provided but UFF 55/58 readable);
  installation (Python ≥ 3.10, `pip install -e .` and the `dev,cli` / `io` extras);
  the five-minute Python cantilever quickstart; a CLI overview with the global flags
  and the CI exit-code contract (0 / 1 / 3 `CORRELATION_FAILED` / 4 `NOT_CONVERGED`);
  the model-spec document (all five `mesh.type` builders, named material/section
  tables, supports/point masses/rotary inertias, the optional `damping` block, and the
  dotted-path addressing `update` relies on); one section per analysis command with an
  option table each; and the four-step end-to-end workflow over the
  `examples/02_model_updating_workflow.py` fixtures, mirroring the README shell session.
- Every documented default, choice list and format was pinned against the source rather
  than the README: `modal` defaults (`-n 6`, `mass|max|none` normalization, direction
  auto-pick), `correlate` pairing methods and `--require-*` gates, the `update`
  configuration schema from `commands/update.py` (`parameters[].target` dotted paths,
  bounds defaults 0.5/2.0, `kind` ∈ stiffness/mass/damping/generic per `ParameterType`),
  and `correlate-frf` damping resolution order (CLI flag → spec block → 0.02 default)
  with the JSON/YAML FRF document shape from `commands/correlate_frf.py`. The
  `test_data` sample matches `io/_native.py`'s writer (`dofs_by_mode` layout,
  `dof_map.node_ids`/`dof_types` by name).
- No code changes, so the suite is untouched; the tree at the base tip `e47426e` was
  already verified at **876 passed** by A62/A63's records.
- Followed the shared-checkout rule: worked from the private detached worktree
  `/tmp/a64`, and the base tip indeed moved twice (`8604807` → `e47426e` → the A67
  record) between the first fetch and the landing — re-synced by rebase both times,
  nothing lost.

#### A50 — the remaining P0 acceptance batch (backfill for A31)

Eleven P0 criteria closed across four modules, plus the two pieces of product code
they turned out to require. AC-CORR-008 is now the only P0 row left `specified`;
the registry stands at **39 implemented of 40**.

**M1 modal — AC-MODAL-007, AC-MODAL-009.** AC-MODAL-007 checks that a complete
basis accounts for all participating mass: the effective modal masses of the full
spectrum sum back to the rigid-body mass in each direction, and a basis truncated
at half its modes provably falls short of it, so the test cannot pass by summing
nothing. AC-MODAL-009 needed the solver to *have* typed failures first —
`ModalSolver.solve` previously trusted its inputs, so an asymmetric or indefinite
matrix produced modes at an imaginary frequency instead of an error. It now
screens non-finite entries, relative symmetry defect above 1e-10, and mass
definiteness before factorising, raising the new `MatrixSymmetryError` /
`MatrixDefinitenessError` with the offending matrix, the measured defect and the
tolerance attached. The acceptance test also AST-scans the whole `solver` package
for bare `assert` statements, which are stripped under `python -O` and would make
the guarantee conditional on the interpreter flags.

Opening the definiteness gate (`definiteness_tol=None`) is not by itself enough to
inspect an unstable spectrum: clipping a negative eigenvalue to zero leaves an
eigenpair that fails the residual check, so `residual_tol=None` has to come with
it. The test records that pairing rather than papering over it.

**M2 correlation — AC-CORR-005, AC-CORR-007.** AC-CORR-005 pins the frequency-error
sign convention `100 (f_fe − f_test) / f_test` as an oracle: a stiffer or lighter
model reports a positive error, a softer or heavier one negative, and the three
reporting paths that surface the number (`relative_frequency_error`,
`ModePair.frequency_error_pct`, and the `CorrelationSummary`) are checked to agree
to the last bit rather than merely to a tolerance. AC-CORR-007 is the property
half: over randomised draws every MAC entry lies in [0, 1] for real *and* complex
shapes, the complex kernel is Hermitian, and a zero-norm shape is rejected instead
of silently clipped to a MAC of 0 or 1.

**M3 updating — AC-UPD-004, AC-UPD-005.** These two needed the loop to report more
than a boolean. `UpdatingResult` now carries `stop_reason` from the closed
`STOP_REASONS` vocabulary (`step_tol`, `cost_tol`, `gates_met`, `gradient_tol`,
`max_iter`, `no_step`) with `converged` derived from it, `UpdatingOptions` grows
the optional MS-3.4 correlation gates that end a run as soon as the paired modes
satisfy them, and the divergence guard aborts with `UpdatingDivergenceError` once
the objective has risen on `divergence_patience` consecutive accepted steps.
`UpdatingDivergenceError` moved from `workflow.stages` to the shared `exceptions`
module — `updating` cannot import from `workflow`, which sits above it — and now
carries the cost history and the iteration it fired on; `workflow.stages`
re-exports it, so its public name is unchanged.

AC-UPD-004 then pins all of that: non-increasing objective over the accepted steps
on every AC-UPD-003 twin, and every token in the vocabulary reachable by some run
of that same twin. The twin is exactly solvable, so its gradient collapses to
round-off before either tolerance can fire — the step and cost cases have to
switch the gradient test off to reach the criterion they are about, which is
recorded in the parameter table rather than hidden. The divergence half uses the
wrong-signed Jacobian MS-3.4 asks for: with the line search off, three accepted
uphill steps abort; with it on, the identical Jacobian cannot take a single step
and the run stops at `no_step` with the initial model untouched. That contrast is
what makes the abort a property of the run rather than of the model.

AC-UPD-005 runs four parameters against two frequencies with an exactly collinear
pair, deliberately bypassing the AC-UPD-007 screen — the point is what the bare
loop does when nobody removed the degeneracy. Under both LM and Gauss-Newton it
completes, keeps every *recorded* iterate inside the bounds (not just the last
one), and never raises the objective. Two residuals cannot pin four parameters, so
the test claims no parameter recovery at all — not even of the sum the duplicate
collapses to, since three effective factors still outnumber the two frequencies —
and pins the thing that is actually guaranteed instead: the null-space direction,
the difference between the collinear pair, stays at zero from the first step to
the last while the fit is reached.

**M4 workflow — AC-WORK-001/002/004/005.** `tests/acceptance/test_workflow.py`
covers the S1–S6 correction pipeline end to end: the detuned twin passes both MS-4.2
gates (AC-WORK-001), a rerun reproduces every reported number bit for bit
(AC-WORK-002), too few mode pairs halts at S2 with a typed `(stage, reason)` rather
than a traceback (AC-WORK-004), and the report carries its versioned schema with
every required block present (AC-WORK-005).

**Verification.** `900 passed, 0 failed` and `ruff check src tests` clean, from an
isolated clone with `PYTHONPATH` pinned to its own `src`.

**One process note worth recording.** Mid-run another agent ran `git reset --hard`
inside `/tmp/a50`, the private clone this work was staged in, and destroyed the
uncommitted AC-UPD-004/005 tree — the shared-checkout hazard the earlier entries
describe for `/workspace`, but one directory further out. The work was rebuilt in a
uniquely named directory and pushed immediately after each commit. Private
worktrees are only private if their names are unlikely to collide.

#### A59 — R2-T02 continued: HEX8 brick and the AC-ELEM-001..003 registration (backfill for A46)

The third element slice closes the *continuum* half of GAP-02 and, with it, the
spec-first debt A46 deliberately left standing: the element family now has acceptance
criteria, and they are gated on all three formulations rather than on the new one.

**`Hex8Element` (`core/elements.py`).** The 8-node trilinear brick in the CHEXA/VTK
corner order (`-ζ` face counter-clockwise, then `+ζ`), `K = ∫BᵀDB dV` and
`M = ρ∫NᵀN dV` on a `gauss_legendre_3d` tensor rule (2×2×2 default), row-sum lumping,
and strain/stress recovery at any natural point. It reuses `solid_constitutive_matrix`
rather than re-deriving `D` — the seam A46 extracted for exactly this. Three quadrature
facts decide what the element is *exact* at, so all three are pinned by tests rather
than assumed: `det J` of a trilinear map is degree ≤ 2 per direction, so the **volume**
and the **mass row sums** (hence the total mass and the whole lumped matrix) are
integrated exactly by the default rule on *any* hexahedron, while the off-diagonal
consistent-mass terms are only quadrature-approximated on a distorted brick (0.09 %
against `integration_order=3`, and exact on any parallelepiped).

**Meshing.** `hex_block_mesh` plus `MeshBuilder.add_hex8`. Its node numbering is
identical to `tet_block_mesh`'s — the structured grid both need is now one `_box_grid`
helper — so the two generators are interchangeable discretizations of the same box and
can be compared element for element, which the bending test below does.

**`tests/test_hex8.py`, 76 tests.** The 3D MacNeal–Harder patch (27 elements, interior
nodes pulled 20 % off the grid) recovers the interior displacements to **2.8e-16** and
the constant stress to 2.5e-15 — and, unlike TET4, the stress is sampled at four natural
points per element rather than one, because a trilinear element could pass at the
centroid and fail elsewhere. Exactly six zero-energy modes under full integration and
exactly eighteen (6 rigid + 12 hourglass) under `integration_order=1`; axial modes
converge from above at ratios 4.005/4.001; a roller-supported block returns `σxx = Eε`
with `−νε` contractions to 1e-10.

**The headline comparison.** Against the Euler–Bernoulli cantilever the brick is
**+89 %** at one element through the thickness (shear locking, pinned so it is not
mistaken for a bending element) but **+8.0 %** at 2475 DOF, where TET4 on the *same*
grid is still **+25 %** — a 3× accuracy gap at equal DOF count, which is the concrete
reason a mesher should prefer hexes. Both numbers are asserted, so neither can drift.

**AC-ELEM-001..003 registered, atomically and with QUAD4/TET4 evidence.** Module **M7**
(`ELEM` family) is new: `MODULE_SPEC.md` §8 (MS-8.1 contract, MS-8.2 formulations,
MS-8.3 completeness/stability, MS-8.4 mass and convergence, MS-8.5 API — the seventh
module takes `MS-8` because MS-6 is the contracts section), `ACCEPTANCE_CRITERIA.md` §8
with the enforcement contract renumbered to §9, the registry rows, and
`tests/acceptance/test_elements.py` all in one commit, as the spec-first rule and the
registry's two-way status check require. The pinned inventory moves **40 → 43**
(M7 = 3, so 35 `implemented` / 8 `specified`) and
`VALID_MODULES`/`FAMILY_TO_MODULE`/`ID_REGEX` grow the family.

- **AC-ELEM-001** (P0, `oracle`, MS-8.3) — patch test exact to machine precision.
- **AC-ELEM-002** (P0, `property`, MS-8.3) — rigid-body invariance plus the exact
  zero-energy mode count, at element and at assembly level. This is the precondition
  AC-MODAL-004 leans on.
- **AC-ELEM-003** (P1, `property`, MS-8.4) — quadratic h-convergence against the
  continuum bar `c/(4L)`; the gate is the *observed order* in [1.8, 2.2], not just a
  ratio, so a lucky pair of meshes cannot pass it.

Each is parametrized over an `ELEMENT_CASES` table covering **QUAD4, TET4 and HEX8**
(24 cases), so the criteria describe the library rather than the newest element, and a
future formulation is covered by adding a row. Measured: patch defects 1.5e-16 /
2.8e-16 / 2.8e-16 and convergence ratios 4.005 / 4.095 / 4.005. QUAD4 and HEX8 return
*identical* axial numbers, which is the expected result rather than a coincidence — with
`ν = 0` and lateral motion suppressed both reduce to the same 1D axial discretization.

Verified from a private clone with `PYTHONPATH` pinned to it, Python 3.12.3 /
NumPy 2.5.2 / SciPy 1.18.1, at the rebuilt tip on the current trunk: full suite
**976 passed, 0 failed** (158 s), `ruff check .` clean. That is the trunk's **876**
plus exactly the **100** this slice adds (76 in `tests/test_hex8.py`, 24 in
`tests/acceptance/test_elements.py`).

**Working-tree hazard, and two new variants of it.** Two agents were writing
`/workspace` at once. This slice's `git add -A` swept a concurrent agent's in-flight
`solver/modal.py`/`exceptions.py` edits into its first commit, and minutes later that
agent's commit swept *this* slice's uncommitted AC-ELEM registration (both documents,
the registry rows and `tests/acceptance/test_elements.py`) into theirs — on this
branch. Then the fallback failed too: the private clone this run made at `/tmp/.a59-*`
was itself checked out and `reset --hard` by another agent within minutes, so a private
clone is only safe under a path nobody will guess, and the only durable store is the
remote. Resolution: the entangled branch `cursor/hex8-solid-element-d0b7` is
**superseded and must not be merged** — the other agent's AC-MODAL work reached the
trunk independently (AC-MODAL-007/009 are `implemented` there from their own landing),
so merging that branch would fork a second copy of it. This slice was rebuilt clean on
the current trunk as `cursor/hex8-brick-ac-elem-d0b7`, carrying only the five element
files plus the three registration edits. Two rules follow: in a shared checkout never
stage with `git add -A` — stage explicit paths — and push as soon as a slice is
coherent.

**Remaining on R2-T02**, unchanged: the 3D two-node beam, the flat-facet shell with
drilling DOFs, the `CQUAD4`/`CTETRA`/`CHEXA`/`CBAR`/`PSHELL`/`PSOLID` cards in
`io/nastran.py`, and the `NeutralModel → Model` conversion that turns an imported block
into bound elements. AC-ELEM-001..003 need a CI run, not another test, to reach
`verified`.

#### A82 — R2-T02 continued: the spatial beam (CBAR-like) (backfill for completed A81)

The frame slice of GAP-02. With `BeamElement3D` on the trunk every element type an
imported model is likely to carry — bar, planar beam, shell quad, tet, hex and now the
spatial frame member — has a formulation, so a frame model can be re-analyzed rather
than only correlated.

**`BeamElement3D` (`core/elements.py`).** Two nodes, six DOFs each: axial extension,
St Venant torsion (`G J / L`) and uncoupled bending in the two principal planes,
`inertia_z` governing the local x-y plane and `inertia_y` the x-z plane. The two
bending planes are the *same* Hermitian 4x4 blocks, extracted as
`_bending_stiffness_block` / `_bending_mass_block` and conjugated by
`diag(1, -1, 1, -1)` for the x-z plane because `dw/dx = -theta_y` there. That reuse is
the point: the `(u, v, theta_z)` sub-block of both local matrices reproduces
`BeamElement2D` to 1e-14, which a test asserts, so there is no second beam kernel to
drift (GAP-01 rule).

**Orientation.** The local frame follows the Nastran CBAR convention — local `x` from
the first to the second node, the orientation vector `v` placing local `y` in the
`x`-`v` plane. `orientation=None` picks whichever of global `Y` and `Z` is *least*
aligned with the member, chosen so a member along global `X` reproduces the planar
element's frame exactly (local `y` = global `Y`); a `v` parallel to the member is
rejected rather than silently substituted, since silently substituting rolls the
section and changes which inertia resists a load.

**Mass.** The consistent matrix carries torsional rotary inertia `rho (Iy + Iz) L` —
without it the twist DOFs are massless and there is no torsional mode at all — and
neglects bending rotary inertia, matching the Euler-Bernoulli assumption and the planar
element. `lumped_mass` row-lumps translation and twist and leaves the bending rotations
massless, exactly as `BeamElement2D` does. Shear deformation, warping, shear-centre
offsets and rigid end offsets are *not* modelled and are documented on the class: the
element matches CBAR only where the shear centre coincides with the centroid.

**`tests/test_beam3d.py`, 42 tests**, plus `MeshBuilder.add_beam3d` as the mesh seam.
The closed-form checks are exact rather than approximate wherever the formulation
allows it, because a cubic element is exact for an end load: tip deflection
`P L^3 / (3 E I)` and tip rotation `P L^2 / (2 E I)` to **1e-12** in *both* bending
planes (the x-z case pinning the rotation sign convention), axial `P L / (E A)` and
torsional `T L / (G J)` to 1e-12, all on a single element. At model level a 12-element
cantilever matches the Euler-Bernoulli spectrum in both planes to 5e-3 (16.71 / 25.07 /
104.7 / 157.1 Hz), the fixed-free shaft mode matches `c / (4 L)` = 314.5 Hz to 4e-4 with
the tip twist dominant, the second-mode error falls by more than 10x from 2 to 8
elements, a free-free member has exactly six rigid-body modes, and every frequency of
the planar `beam_mesh` cantilever reappears in the spatial model to 1e-8 — the planes
decouple along global `X`, so that is an identity, not a tolerance. Rigid-body
translations and rotations store no energy in global axes, and the assembled spectrum is
invariant under a rigid rotation of the whole model.

Verified in a private worktree with `PYTHONPATH` pinned, Python 3.12.3 / NumPy 2.5.2 /
SciPy 1.18.1, at the branch tip on trunk `c5afc35`: full suite **1075 passed, 0 failed**
(74 s), `ruff check .` clean. That is the trunk's 1033 plus exactly the 42 this slice
adds. Re-verified after merging the trunk tip `e809290` (which moved under the task):
**1089 passed, 0 failed** (85 s), Ruff clean — again the trunk's 1047 plus the same 42. No acceptance criterion was touched: AC-ELEM-001's constant-strain patch test has
no beam analogue and AC-ELEM-003's continuum bar oracle is the wrong convergence target
for a cubic element, so the pinned 43-criterion inventory does not move. AC-ELEM-002
(rigid-body invariance) is the one row the beam could join in
`tests/acceptance/test_elements.py`'s case table, which needs no new ID and is left as a
follow-up.

**Working-tree hazard, tenth occurrence — A66's `git stash` warning, reproduced.** A
concurrent agent ran `reset --hard` in `/workspace` while this task's edits were
uncommitted, moving this task's branch to their commit, and a `git stash` taken moments
later was entangled with their in-flight correlation changes: the pop restored *theirs*
with conflicts and this task's source edits were gone. That is precisely the failure
A66 recorded and warned against. The disturbed state was preserved as a named stash
(`A82 backup of worktree state disturbed by a concurrent reset`), `/workspace` was left
detached at the origin tip it had been reset to, and the work was redone in a private
worktree at `/tmp/a82`. The rules stand and are worth repeating: **never `git stash` in
the shared checkout or any worktree of it**, stage explicit paths, and push as soon as a
slice is coherent.

**Remaining on R2-T02:** the flat-facet shell with drilling DOFs, the
`CQUAD4`/`CTETRA`/`CHEXA`/`CBAR`/`PSHELL`/`PSOLID` cards in `io/nastran.py`, and the
`NeutralModel → Model` conversion. No element formulation is outstanding except the
shell.

#### A79 — merging the HEX8 brick slice into the integration branch (backfill for A59)

A59 left two branches with the same `d0b7` suffix and only one of them mergeable. This
entry records which, why, and what the counters became.

**Which branch, and why not the other.** `cursor/hex8-solid-element-d0b7` is the branch
A59's own entry marks **superseded**: it was built in the shared `/workspace` checkout and
its `git add -A` swept a concurrent agent's in-flight `solver/modal.py` and
`exceptions.py` into it. That agent's AC-MODAL-007/009 work reached the trunk on its own
afterwards, so merging the entangled branch would fork a second copy of it — its diff
against the rebuilt branch is 17 files and ~2500 lines of exactly that duplication.
`cursor/hex8-brick-ac-elem-d0b7` is the clean rebuild: five element files plus the three
registration edits, nothing else. That is the one merged here; the superseded branch stays
unmerged and should be deleted rather than revisited.

**The three conflicts were all the same conflict.** Every one was an inventory counter
that the trunk and the branch each moved for a different reason — the trunk had added
AC-CORR-009 (M2: 8 → 9) while the branch added the M7 `ELEM` family. The registry rows
themselves auto-merged cleanly, since the two sides touched disjoint entries; only the
hand-maintained totals that shadow them collided:

- `tests/acceptance/test_criteria_registry.py` — `EXPECTED_CRITERIA_PER_FAMILY` (take
  `CORR: 9` from the trunk *and* `ELEM: 3` from the branch) and `len(REGISTRY) == 44`
  (41 + 3), not either side's 41 or 43.
- `docs/ACCEPTANCE_CRITERIA.md` §9 — the same numbers in prose.
- `.agent_workspace/PROGRESS.md` — not a counter but a two-sided append (A50 on the trunk,
  A59 on the branch); both entries kept, in agent order.

Resolving by taking either side wholesale would have passed `git merge` and then failed
`test_registry_inventory_matches_documented_scope`, which is the point of pinning the
totals twice. Each resolved file was staged by explicit path — `git add <file>`, never
`git add -A` — which is the rule A59's incident produced.

**Verification at the merged tip:** full suite **1033 passed, 0 failed**, `ruff check .`
clean, Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1, from a private clone with `PYTHONPATH`
pinned to its own `src`. The HEX8 merge alone took the trunk's 921 to **1021** — exactly
the 100 tests A59 measured (76 in `tests/test_hex8.py`, 24 parametrized cases in
`tests/acceptance/test_elements.py`) — and the AC-CORR-008 work that landed upstream
mid-merge added the remaining 12. Registry: **44 criteria, 39 `implemented`, 5
`specified`**, and with AC-CORR-008 and AC-ELEM-001..003 both in, **every P0 row is now
`implemented`**; the five outstanding are all P1 (AC-MODAL-008, AC-UPD-006a/b,
AC-UPD-008, AC-WORK-003).

**The shared checkout is still moving.** `/workspace` advanced under this run before the
merge even started, and the integration branch's remote tip moved three more times during
it (`a975087` → `b56593c` → `ca5abae` → the AC-CORR-008 landing). The merge was therefore
staged in a private clone under a name no other agent would pick, committed as soon as it
was coherent, and pushed through a fetch-merge-push retry loop rather than a single push.
Two of those three upstream moves touched files this merge also touched and still merged
cleanly; the loop is cheap insurance, not ceremony.

#### A78 — milestone: every P0 acceptance criterion is `implemented` (backfill for A50)

**The milestone.** With AC-CORR-008 closed, the registry at tip `c5afc35` reads
**44 criteria: 39 `implemented`, 5 `specified`, 0 `verified`** — and by priority
**P0 34 implemented / 0 specified**, P1 4 / 5. Every blocking criterion in
`docs/ACCEPTANCE_CRITERIA.md` now has an executable, tagged test behind it. The five
rows still `specified` are all P1 and all of the same cheap kind (the engine exists
and is unit-tested; the acceptance tagging is not written): AC-MODAL-008,
AC-UPD-006a/006b, AC-UPD-008, AC-WORK-003. This supersedes the A50 entry above, which
recorded AC-CORR-008 as the last P0 row outstanding, and the P0 count in A61's
mid-point brief; A79 reports the same census from the merge side.

**AC-CORR-008 itself was closed by `1e99970`, not by this task.** That commit gave the
artifact a parse side — `from_dict`/`from_json` across `ModePair`, `ModePairing`,
`CorrelationSummary`, `FRFCorrelation` and `CorrelationReport`, plus `SCHEMA_KEYS`, the
pinned key set `to_dict` emits — and registered the criterion with eleven tagged cases.
That is the right shape for the criterion: MS-2.6 calls the report the exchange
currency between M2, M3 and M4, and until then it could only be written. The parser is
the strict inverse of the serializer: a payload missing a schema key, or carrying a
`schema_version` this build does not know, is refused as corrupt rather than turned
into a report with a silently empty block.

**What this task added (`515aa2e`), two cases.** The batch exercises the parser only on
reports built from mode shapes. A report paired on frequencies alone is the emptiest
payload the schema can emit — `mac_matrix`, `comac` and `dof_labels` all `null` — and
the only one that can contain a NaN, since `ModePair.mac` is unknown without shapes.
The first case pins that the parse rebuilds the absent blocks as absent and keeps the
NaN a NaN, rather than reading either as a zero, which would report a correlation of
nothing with nothing; the restored summary, pairing and `report()` text are identical.
The second records the cost: `json` writes that NaN as a bare token, so the file is
**not RFC 8259** and a conforming reader (`JSON.parse`, `serde_json`) rejects it, as
does `json` itself under `allow_nan=False`. Shape-based reports — what
`openfemlab correlate` and `correlate-frf` publish — are conforming, so the exposure is
bounded to the shape-free case rather than excused. Whether to spell an unknown MAC as
`null` instead is a schema change (1.1 → 1.2 under the MS-6 rule) and was deliberately
not started here.

**Verification.** From a private detached worktree at `/tmp/a78` with `PYTHONPATH`
pinned to its `src`, Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1: full suite
**1035 passed, 0 failed** (86 s) at `c5afc35` plus these two cases, `ruff check .`
clean. STATUS.md was already refreshed for the milestone by A69 (at `1e99970`,
933 tests, before the HEX8 merge); its test count and criteria total now trail this
tip and need one more pass.

**Dispatch note, a new hazard alongside the shared-checkout one.** This task was
dispatched to implement AC-CORR-008 and was three minutes behind a sibling agent that
had already landed it — a complete duplicate suite was written, verified green and
committed in a private worktree before the rebase onto the trunk surfaced the
collision, and was then dropped in favour of the version already on the branch. The
shared-checkout rule (work in a private worktree) is what made the collision
recoverable, but it does not prevent it: `git fetch` and a look at the registry status
of the target criterion belong at the *start* of a backfill task, not at its first
push.

**Open for the orchestrator.** The exit bar wants every P0+P1 criterion `verified`, and
nothing can leave `implemented` until R2-T09 defines and runs the promotion (a CI run
at a pinned tip). That is now the only structural blocker on the P0 set; the five P1
tagging tasks are independent of it and can go in parallel.
A90 backfill verification: **1089 passed, 0 failed**; `ruff check .` clean.

#### A89 — R2-T05 opens: the meshio bridge (backfill for completed A85)

R2-T05 was the last core track with no commit. This slice lands its first half — the
optional-dependency seam and the mesh conversion — and leaves the acceptance
registration and the UNV/UFF work for the rest of the track.

**`io/meshio_bridge.py`.** `from_meshio` turns a `meshio.Mesh` into a `NeutralModel`
and `to_meshio` goes back, through one explicit table,
`CELL_TYPE_TO_ELEMENT`: `vertex`/`line`/`triangle`/`quad`/`tetra`/`hexahedron` ↔
`MASS1`/`ROD2`/`TRI3`/`QUAD4`/`TET4`/`HEX8`. `read_meshio` and `write_meshio` wrap
meshio's file entry points and re-raise its errors as `FormatError`, the same error
type the BDF and UFF readers use. Four conversion decisions are worth recording:

- **The table is one-to-one, and `BEAM2`/`SPRING2` are deliberately outside it.**
  meshio's `line` cell carries no attribute distinguishing a rod from a beam or a
  bushing, so exporting one would come back as a `ROD2` — a silently different model.
  `to_meshio` raises `FormatError` instead, and a test pins that the two stay unmapped.
- **Connectivity stores node *ids*, not point indices**, per the `NeutralModel`
  contract; meshio's zero-based indices are translated on the way in and back out.
  Labels survive a round trip because `to_meshio` writes them as the `node_ids` point
  data and `element_ids` cell data that `from_meshio` reads back — which is exactly the
  shape the proposed AC-IO-001 asks for.
- **Property ids come from whatever the file has**: `property_ids`, else
  `gmsh:physical`, else `medit:ref`, else a configurable default. A mesher tag is the
  closest thing most formats have to a property assignment, and no format carries
  material data at all, so `materials`/`properties` come back empty by construction
  rather than by omission.
- **Unmapped cell types are skipped, not fatal** — a `UserWarning` plus a per-type count
  in `meta["skipped_cell_types"]`, mirroring the BDF reader's "import the supported
  subset" policy. A second-order mesh therefore imports its corner cells instead of
  refusing to open.

**The P7 seam.** `meshio` is imported lazily inside `require_meshio()`, never at module
import time, so `import openfemlab.io` still works with only numpy/scipy/pyyaml — a test
asserts it. A missing package raises the new `MissingDependencyError`, which subclasses
**both** `OpenFEMLabError` and `ImportError`: the typed hierarchy gets the error, and the
`except ImportError` call sites that predate it keep working. `from_meshio` goes one step
further and needs nothing but NumPy — it is duck-typed on `points`/`cells`, so a caller
holding a mesh converts it in an installation without the extra. This replaces the
`NotImplementedError` stub that had been sitting in `io/__init__.py`.

**`tests/test_meshio_bridge.py`, 44 tests**, skipped as a module via
`pytest.importorskip` when meshio is absent. Coverage runs from the simple cases (a
two-quad mesh, a unit cube, 2-D points padded to three columns, mixed and repeated cell
blocks) through the id plumbing, the malformed-input rejections, the export round trip,
a real file round trip through `.vtu`, and the seam itself — the missing-dependency path
is exercised by monkeypatching the guarded `import_module`, so it is tested even in an
environment that *has* meshio. Two findings shaped the tests: `meshio.Mesh` validates
cell-data lengths itself, so the bridge's own check needs a duck-typed mesh to reach,
and meshio raises `ReadError` (not `WriteError`) when a writer cannot deduce the format
from the path, so both are caught.

`pyproject.toml`'s `[dev]` extra grew `meshio` — the `[io]` extra already had it — so
`make install` exercises the bridge instead of skipping it; without the extra the module
skips cleanly, which was verified by blocking the import.

**Verification** from a private clone with `PYTHONPATH` pinned, Python 3.12.3: full
suite **1133 passed, 0 failed** at the merged tip (the trunk's 1089 from A90 plus
exactly these 44), `ruff check .` clean. With meshio unavailable: **1089 passed,
1 skipped**.

**Remaining on R2-T05**: AC-IO-001..003 registration (AC-IO-001's engine and test now
exist, so it needs the three-file spec-first commit and moves the pinned 44-criterion
inventory), UNV 2411/2412 in `io/uff.py`, UFF writing, and — shared with R2-T02 — the
`NeutralModel` → `Model` conversion, which is the one thing standing between
`read_meshio` and the round's imported-3D-mesh demo.

#### A83 — R2-T04 is acceptance-complete; the AC-UPD-006 branch is closed out (backfill for completed A57)

A57's work — the AC-UPD-006a/b acceptance gate, the starting-cost penalty fix and the
Laplace σ_post in the `CorrectionReport` — was finished on
`cursor/ac-upd-006-registration-6615`, but the branch was still open and the task
boards still called R2-T04 partial. This run lands the merge, verifies the tip and
closes the bookkeeping.

- **The merge was made twice and neither copy is the one on the trunk.** The first was
  made in the shared `/workspace` checkout; by the next command another agent had moved
  HEAD to `cursor/beam3d-cbar-element-c9a7` in a conflicted state and the commit was
  orphaned — though it was later picked up and pushed by someone else as `3e2df81`, and
  a concurrent run reconciled it against the HEX8 trunk in `ad035d7`. The second was
  built in a private clone and re-resolved against a trunk that had advanced seven more
  commits; by the time it was verified, `git merge-base --is-ancestor` showed the branch
  content was already an ancestor of `origin`, so this run reset to the trunk rather
  than pushing a duplicate merge of the same tree. All three routes reached the same
  product code: the `src/` and `tests/` diffs are identical.
- **Verification.** At `e809290`, the first trunk commit carrying both AC-UPD-006 and
  the AC-CORR-008 shape-free round-trip flavor: **1047 passed, 0 failed** in 97.7 s
  with a collection-only pass confirming the same 1047, `ruff check .` clean. That is
  A79's 1033 plus the twelve tests AC-UPD-006 carries — eight acceptance cases, three
  workflow σ_post cases and one Bayesian unit case — and the two AC-CORR-008 cases
  alongside. Re-verified at `7368c92` after the spatial beam landed: **1089 passed**,
  Ruff clean. Both runs from a private clone with `PYTHONPATH` pinned to its own `src`.
- **Registry: 44 criteria, 41 `implemented`, 3 `specified`, 0 `verified`** — by priority
  P0 34/0 and P1 7/3, leaving AC-MODAL-008, AC-UPD-008 and AC-WORK-003 as the only rows
  still unwritten.
- **R2-T04 is marked acceptance-complete** in `STATUS.md`, in `ROUND2_PLAN.md` (the §0
  board, the GAP-11 register row and the task section) and in the Round-2 header here.
  What remains on the task is σ_post in the CLI `update` document — a prior/noise block
  in the update spec schema plus a column in the rendered table and the JSON payload —
  which is a slice of its own and does not hold the acceptance gate. R2-T03 has been in
  the same position since A58 and is marked the same way. Neither can reach `verified`
  until R2-T09 stands up the CI promotion, which is now the sole blocker on both.
- `cursor/ac-upd-006-registration-6615` deleted from `origin`; its content is an
  ancestor of the integration branch.
- **Process.** Two agents merged the same side branch within minutes because neither
  could see the other's in-flight work. `git merge-base --is-ancestor <branch> <trunk>`
  is the cheap check that catches this, and it belongs *before* committing a merge, not
  just before pushing one — re-run after every fetch, since on this branch the trunk
  moved four times during a single run. The shared `/workspace` checkout was
  unusable throughout: HEAD was moved out from under this run twice, once mid-merge.

#### A72 — R2-T09 starts: gate-backed `verified` promotion (backfill for completed A61)

The registry documented a three-step lifecycle but only ever used two of them: nothing
re-ran a criterion as a gate, so `verified` was a status a human could type. R2-T09's
first slice makes it an enforced claim and promotes the first batch of criteria.

- **`tests/conftest.py` (new)** — marker *arguments* cannot be selected with `-m`, so
  the gate needs its own selection: `--criterion AC-<MODULE>-NNN` (repeatable) keeps
  only the tests tagged with those registry IDs and deselects the rest, and
  `--criterion-report PATH` writes a JSON summary per criterion (tests / passed /
  failed / skipped / errors and the node IDs that produced them). The reporter plugin
  is registered only when the option is given, so ordinary runs carry no bookkeeping.
- **`tests/acceptance/test_registry_ci.py` (new, 13 tests)** — the simulated CI run.
  It derives its selection from `verified_ids()`, so the gate and the registry cannot
  drift, and launches two pytest subprocesses concurrently, under different
  `PYTHONHASHSEED` values and single-threaded BLAS. The promotion holds only when the
  run is green with no failure, error *or* skip; when every promoted criterion
  contributes at least one passing test whose node IDs land in the suite its registry
  row names; when both seeds reproduce the outcome test for test (the §1.4 determinism
  rule); and when the CI `gates` job still runs the import check, Ruff, registry
  consistency, this gate and `-m acceptance`.
- **Promotions (9, all P0/P1, 69 tagged tests)** — one gate per module so the slice
  exercises the whole platform: AC-MODAL-003 (mass-orthonormality), AC-CORR-001 /
  AC-CORR-002 (weighted MAC identity, scale invariance), AC-UPD-001 (eigenvalue
  sensitivity vs central FD), AC-WORK-002 (deterministic reproducibility), AC-OPT-003
  (box bounds), AC-DYN-004 (FRAC/FDAC identity), AC-ELEM-001 (patch test) — plus
  **AC-CORR-006**, the P1 Round-2 sign-off blocker A43 left at `implemented`, which
  closes that R2-T03 exit item. AC-ELEM-001 answers A59's note that AC-ELEM-001..003
  "need a CI run, not another test": the run now exists, and the other two follow the
  same way once someone flips them. Registry split is now **9 `verified` /
  32 `implemented` / 3 `specified`** of 44.
- **Registry and docs** — `test_criteria_registry.py` gained `verified_ids()`, the
  `CI_WORKFLOW` / `CI_GATE_JOB` anchors and three consistency tests (no P2 promotion,
  every module carries a verified criterion, the gate job exists);
  `ACCEPTANCE_CRITERIA.md` §1.5 spells the promotion rule out and §9 adds it as
  enforcement rule 7. `.github/workflows/ci.yml` gained the `gates` job.
- **Negative checks** (both reverted afterwards): injecting one failing assertion into
  an AC-CORR-001 test turned three gate tests red, and deleting the Ruff step from the
  workflow failed the corresponding parametrization — the gate is load-bearing, not
  decorative.
- **Measured** — full suite **1149 passed** (the trunk's 1133 at `06e85ba` plus the 16
  this slice adds), `ruff check .` clean, on Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1
  from the private worktree `/tmp/a72` with `PYTHONPATH` pinned to its own `src`.
  Pinning BLAS to one thread inside the gate cut the two concurrent runs from 17.4 s to
  under 5 s (oversubscription, not test cost) and removes thread-count-dependent
  reduction order as a source of nondeterminism.
- **The shared-checkout hazard bit again, in its subtlest form.** An unpinned
  `python -m pytest` in the private worktree still imported `openfemlab` from
  `/workspace/src` — the editable install's `.pth` puts it on `sys.path` — so one
  otherwise-green run reported four failures in `tests/test_workflow.py` that came from
  another agent's mid-edit `/workspace`. Three consecutive pinned runs are clean. The
  gate subprocess was never exposed to this: it pins `PYTHONPATH` to the repo root it
  computes from its own file.
- **Open for R2-T09** — the remaining 32 `implemented` rows still have to be promoted
  as their tracks close, and the 3 `specified` ones need tests first; the gate itself
  scales to them by construction (flip the status, the gate picks it up).

#### A84 — the P0 milestone chronology pinned and the AC-UPD-006 count divergence reconciled (backfill for A69)

This task was dispatched to record the P0 milestone and reconcile the registry
counts with A57's AC-UPD-006 work; sibling agents were recording and merging
both while it ran (A78's entry above, the `3e2df81` merge), so this entry pins
the arithmetic and the chronology rather than re-announcing either.

**The milestone, dated.** Every P0 criterion has been `implemented` since
`1e99970`, where the AC-CORR-008 flip closed the last open P0 row — **32 of
32** on the then-41-row registry. Twenty-six seconds after the milestone was
recorded in STATUS.md (`ca5abae`), the HEX8 merge (`8a0f10f`) grew the P0 set
itself: AC-ELEM-001/002 arrived already `implemented`, so the bar has read
**34 of 34** ever since. Nothing has reached `verified`; that promotion is
R2-T09's, defined but never applied.

**The count corrections.** Re-counted by executing the registry source rather
than reading its prose: at `c5afc35` the split was P0 34/0 and **P1 5/5** —
39 implemented of 44. A80's STATUS snapshot recorded P0 35 / P1 4, and A78's
entry above P0 34 / P1 4 (internally inconsistent with the 39 total it also
quotes); both P1 figures drop AC-ELEM-003, and A80's P0 gains it. Per family
the P0 set is 8 MODAL + 7 CORR + 6 UPD + 4 WORK + 3 OPT + 4 DYN + 2 ELEM = 34.

**The AC-UPD-006 divergence, now closed.** Between `c479ee4` (A57 flips
AC-UPD-006a/b to `implemented` on `cursor/ac-upd-006-registration-6615`) and
`3e2df81` (that branch merges onto the trunk), the two histories legitimately
disagreed about the same two rows: A57's "34 implemented / 6 specified
(P1 5/3)" was exact for its then-40-row tree, and the trunk's 39/5 was exact
for its 44-row tree — the branch carried the UPD-006a/b flips but predated the
trunk's AC-CORR-008 flip and the ELEM family. The merge produced the union
this task was dispatched to predict: **44 rows, 41 `implemented` /
3 `specified` (P0 34/34, P1 7/3)**, re-counted from the registry source at the
current tip, leaving AC-MODAL-008, AC-UPD-008 and AC-WORK-003. The rule this
window demonstrates: a registry count is only meaningful together with the
commit it was counted at, so status claims in these documents should always
carry one.

**Verification (independent, this run).** Private clone, `PYTHONPATH` pinned
to its `src`, Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1, at `c5afc35`:
**1033 passed, 0 failed**; `ruff check .` clean; the per-suite collection
summed to the same 1033 (706 unit + 327 acceptance). The tip moved four more
times during the run (the spatial-beam slice, the AC-UPD-006 merge, the meshio
bridge, the shape-free AC-CORR-008 cases), so A95's 1,089-test STATUS snapshot
supersedes these suite numbers; the milestone chronology and the registry
arithmetic above are commit-pinned and unaffected.

**Hazards, again, twice.** The shared `/workspace` checkout was switched to
another agent's branch between two consecutive commands of this run, and the
run's own private clone at `/tmp/a84` was fetch-and-`reset --hard` by a
concurrent agent mid-edit — the guessable-name variant A50 and A57 recorded.
The in-flight edits survived the interleaving and reached the remote through a
fetch-merge-push loop, but only because they had not yet been staged when the
reset hit; the durable store is the remote, nothing else.
