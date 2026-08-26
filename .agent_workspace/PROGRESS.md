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
| R2-T02 | claude-opus-5-thinking-high-fast | GAP-02 QUAD4 plane-stress/plane-strain element, patch test & modal suite (backfill for A19) | partial — QUAD4 slice landed; TET4/HEX8/3D beam open |
| A37 | claude-opus-5-thinking-high-fast | Merge the QUAD4 branch onto the trunk and re-verify the suite (backfill for R2-T02) | complete |

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
**Status:** IN PROGRESS — backlog planned in `.agent_workspace/ROUND2_PLAN.md` (A24); the
MS-4 workflow carried over from Round 1 is landed and verified at `5bc6a6d` (A26), the
damped-dynamics and optimization tracks are merged in at `acda625` (A19 implementation,
A28 integration), **R2-T01 is DONE** — AC-DYN-001..005 registered and implemented — and
**R2-T02 is PARTIAL**, its QUAD4 slice merged onto the trunk by A37

Core backlog (prioritized, from `docs/SOTA_GAP_ANALYSIS.md` §4/§6 + Round 1 conclusion):
1. ~~**R2-T01 Dynamics/FRF chain** (GAP-04/05, P0) — damping models, harmonic response,
   FRF synthesis, FRAC/FDAC.~~ **DONE.** The engine landed with the `acda625` merge of
   `cursor/dynamics-damping-frf-9500`, and AC-DYN-001..005 are now registered spec-first
   against that API and `implemented` (see the R2-T01 entry below). GAP-04 is closed;
   GAP-05 is closed apart from the FRF updating residual the plan defers to Round 3.
   Handed on to the exit-bar work: the measured-vs-synthesized FRF demo through the CLI,
   and an FRF block in the `CorrelationReport` schema.
2. **R2-T02 3D continuum elements** (GAP-02, P0) — QUAD4/TET4/HEX8 + 3D beam with patch
   /convergence gates (AC-MODAL-001/003/004/007 extended, new AC-ELEM-*). **PARTIAL:
   QUAD4 is landed on the trunk**, merged from `cursor/quad4-plane-stress-element-b99c`
   by A37 (see the R2-T02 and A37 entries below); TET4, HEX8, the 3D beam, the
   `CQUAD4`/`CTETRA`/`CHEXA`/`PSHELL`/`PSOLID` BDF cards and the AC-ELEM-* registry rows
   are the remaining slice.
3. **R2-T03 SEREP/TAM reduction & expansion** (GAP-08) — Guyan/IRS/SEREP, TAM
   pseudo-orthogonality, shape expansion; closes Round-2 gate AC-CORR-006. *Engine
   landed by A36 (`correlation/reduction.py`, 25 tests); the AC-CORR-006 acceptance test
   and the AC-CORR-009 registration are what remain — see the A36 entry below.*
4. **R2-T04 Bayesian MAP updating** (GAP-11 slice, MS-3.5) — Gaussian-prior MAP step +
   posterior covariance; closes Round-2 gates AC-UPD-006a/b.
5. **R2-T05 meshio bridge & IO completion** (GAP-03 remainder) — optional-dependency
   meshio ↔ NeutralModel bridge, UNV 2411/2412.

Supporting: R2-T06 updating depth (incl. the still-unimplemented **P0** AC-UPD-007
collinearity screen), R2-T07 scipy optimization backend (GAP-12 — the surrounding M5
package landed at `acda625` and `ScipyBackend.solve` is now wired too, so this is
**done**, A27), R2-T08 R1-O2 branch reconciliation, R2-T09 CI exit hardening.
Exit bar: all P0+P1 criteria `verified`,
new dynamics/element/IO criteria at least `implemented`, GAP-01 stays closed.

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
  `CorrelationReport` schema is deliberately untouched: an FRF block there is a
  `schema_version` bump that belongs with the CLI demo in the exit-bar work.
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
  1. The AC-CORR-006 gate itself. The physics is covered by
     `test_expansion_of_an_underinstrumented_chain_keeps_mac_above_the_gate`, but the
     criterion also demands *pairing computed in reduced space equals pairing computed in
     expanded space*, and it must live in `tests/acceptance/test_correlation.py` tagged
     `@criterion("AC-CORR-006")` before the registry may leave `specified`. Until that
     lands the criterion still reads `specified` and P1 sign-off is still blocked.
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
and AC-WORK-001/002/004/005 are still `specified` (20 of 41 criteria `implemented`
after the A27/AC-DYN batches, none `verified`), even though `tests/test_workflow.py`
demonstrates the AC-WORK gates numerically — tagging them is already scheduled with
R2-T06 and the next acceptance batches. The first PR body draft (`17d03ba`) was folded
into the closure lineage and superseded by the A30/A32 polish now in
`.agent_workspace/PR_DRAFT.md`; both record the same platform state.
