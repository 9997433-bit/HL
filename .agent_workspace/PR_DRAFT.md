# PR Draft — OpenFEMLab Round 1

Ready to file. Base: `main`. Head: `cursor/femtools-industrial-7aa3`.
Verified at `8d6ef7c`: full suite **797 passed**, `ruff check .` clean
(Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1).

## Title

```
OpenFEMLab: solver-independent CAE platform — modal analysis, correlation, model updating, damped dynamics (797 tests)
```

## Body

```markdown
## Summary

First integrated release of **OpenFEMLab**, an open-source, solver-independent CAE
platform inspired by FEMtools: modal analysis, FE–test correlation, sensitivity-based
model updating, a productized simulation-correction workflow, damped dynamics with FRF
synthesis, and optimization hooks — all behind one CLI and a schema-versioned IO layer.

## What's included

- **Core FEM & modal solver** (`core/`, `solver/modal.py`, `mesh/`): node-major DOF
  model with SPCs and lumped masses; spring/truss/planar-beam elements plus the QUAD4
  isoparametric plane-stress/plane-strain continuum element (2×2 Gauss stiffness,
  consistent mass, `mesh.simple.quad_plate_mesh` generator) that passes the constant-strain
  patch test exactly and matches an equivalent bar spectrum to 2.4e-13, and the TET4
  constant-strain tetrahedron (`mesh.simple.tet_block_mesh` on a Kuhn/Freudenthal split)
  which passes the 3D patch test on distorted geometry to 2.8e-16; one-pass
  preallocated COO→CSR assembly; one `ModalSolver` façade with dense and sparse
  shift-invert backends, static condensation of massless DOFs, mass normalization,
  participation/effective masses, and a shift-invert LU cache. Validated against
  closed-form spectra to 1e-9 relative (worst continuum case 0.2 %). R2-T02 remains
  **partial**: HEX8, the 3D beam, shell facets, and the corresponding solid/shell
  BDF cards are still open, and TET4's bending lock is pinned by test rather than fixed.
- **Damped dynamics** (`solver/dynamics.py`): Rayleigh, modal, and structural damping
  models; complex modes with modal phase collinearity; modal, complex-modal, and direct
  FRF synthesis; harmonic response; residual flexibility; FRAC/FDAC FRF correlation
  metrics. 82 tests.
- **Correlation** (`correlation/`): MAC / autoMAC / mass-weighted MAC, MSF,
  pseudo-orthogonality, COMAC; sensor/DOF alignment with orientation signs; Hungarian
  or greedy mode pairing with MAC threshold, frequency window, and frequency penalty;
  Guyan / IRS / SEREP reduction bases with the TAM mass and SEREP mode-shape expansion
  back into full FE space; FRAC/FDAC FRF correlation carried as a serializable
  schema-1.1 `frf` block—with per-channel FRAC summaries and an optional FDAC
  matrix—in the JSON `CorrelationReport`.
- **Model updating** (`updating/`): analytic Fox–Kapoor eigenvalue, eigenvector, and
  MAC sensitivities (vectorized, sparse-aware, FD-verified to ≤ 1e-6); affine
  `ScalingModel` (one eigensolve per iteration); Levenberg–Marquardt / Gauss–Newton
  updater with Tikhonov regularization, bounds, and per-iteration MAC re-pairing;
  an MS-3.5 Bayesian MAP path (`GaussianPrior`, `BayesianUpdater`) that reuses the same
  loop through overridable normal-equation and penalty hooks and reports a Laplace
  posterior with σ_post and credible intervals. Twin experiments recover grouped
  stiffness/mass factors to machine precision.
- **Correction workflow** (`workflow/`): the six-stage S1 BASELINE → S6 VALIDATION
  state machine with machine-readable gate failures, MS-3.6 collinearity screening,
  held-out validation targets that catch overfitting, σ_post parameter uncertainty,
  and a reproducible schema-versioned `CorrectionReport` (rerun-identical to 1e-12).
- **Optimization** (`optimization/`): design variables, modal/mass/frequency response
  functions, analytic gradients with MAC mode tracking, `OptimizationProblem`, sizing
  compilation reusing the updater's model contract, and an implemented SciPy backend for
  SLSQP/trust-constr with hard bounds, analytic Jacobians, standardized inequalities,
  iteration audits, and method-independent KKT residuals fitted over the active
  constraints *and* the active bound directions together. GAP-12 is closed for sizing.
- **IO** (`io/`): schema-versioned native YAML/JSON round trip for models, modal
  results, and test data; ASCII UFF/UNV dataset 55/58 reader; minimal Nastran BDF
  reader (GRID/CROD/MAT1 → neutral model).
- **CLI** (`cli/`): `openfemlab modal | correlate | update` over JSON/YAML model
  specs; machine-readable JSON on stdout, diagnostics on stderr, CI acceptance gates
  via exit codes; covered end to end including subprocess runs.
- **QA stack**: 797 tests including a machine-readable registry of 40 quantified
  acceptance criteria wired to tagged acceptance tests, boundary/probe suites,
  performance-regression gates, and benchmarks; GitHub Actions CI on Python
  3.10–3.13; `ruff check` clean.
- **Docs**: `ARCHITECTURE.md`, `MODULE_SPEC.md` (MS-0..7), `ACCEPTANCE_CRITERIA.md`
  (40 criteria), `SOTA_GAP_ANALYSIS.md` (GAP-01..15), `OPTIMIZATION.md`, README with
  reproducible CLI walkthrough, runnable `examples/`.

## Verification

- `python -m pytest` — **797 passed** at `8d6ef7c` in 88.29 s on Python 3.12.3 /
  NumPy 2.5.2 / SciPy 1.18.1.
- `ruff check .` — clean.
- Per-suite breakdown (sums to 797): acceptance registry + gates 174, dynamics 82, TET4 66,
  QUAD4 61, updating 57, correlation 52, modal solver 44, workflow 38, Bayesian updating 35,
  optimization 27, FRF correlation 25, reduction/expansion 25, IO (native/UFF/Nastran) 24,
  CLI 22+1+16 (incl. `correlate-frf`), core 18, result contract 17,
  boundary/performance/e2e/scaffold 13.
- Sizing optimization is gated on a closed-form optimum that *distributes* material, not
  just a scalar scaling: the two-link chain's asymmetric `(6, 4)` optimum is recovered
  from a symmetric start to 1.1e-16 relative, and a companion bound-active run pins the
  active-set/barrier split between SLSQP and trust-constr.
- End-to-end: model → modal → correlate → update → re-solve converges 22.86 % → 0 %
  frequency error at MAC 1.0; the README CLI session reproduces exit codes 0/3/0/0.
- Performance (single BLAS thread, medians): 100-DOF five-iteration updating loop
  35.3 → 7.9 ms (4.47x); 240-DOF eigenvalue sensitivity 1.83 → 0.68 ms (2.70x);
  2,000-DOF sparse assembly 26.3 → 19.3 ms (1.36x), gated by regression probes.

## FEMtools comparison

Per `docs/ARCHITECTURE.md` §7 — concede GUI and format breadth, win on algorithms,
openness, and automation:

| Capability | FEMtools | OpenFEMLab (this PR) | Verdict |
|---|---|---|---|
| Solver-independent data model | mature, many interfaces | same idea; UNV 55/58 + Nastran-lite now, meshio planned | parity (breadth later) |
| Modal analysis | internal + external solvers | SciPy dense + shift-invert Lanczos, sparse throughout, LU cache | parity |
| Dynamic response / FRF | mature | Rayleigh/modal/hysteretic damping, complex modes, receptance/mobility/accelerance synthesis, FRAC/FDAC | parity |
| Correlation (MAC/COMAC/orthogonality) | yes | plus globally optimal Hungarian pairing | **exceed** |
| Sensitivity-based updating | weighted LSQ, manual tuning | LM with adaptive damping, Tikhonov, bounds by construction, analytic MAC sensitivities, Bayesian MAP with a Laplace posterior | **exceed** |
| Validation workflow | GUI-driven | seeded, schema-versioned six-stage pipeline with held-out gates and machine-readable failures | **exceed** |
| Scripting | proprietary BASIC-like | full Python + SciPy ecosystem, CI-native CLI | **exceed** |
| Reproducibility | binary project files | plain-text models, journaled runs in git, headless reruns | **exceed** |
| Cost / auditability | commercial licenses, closed numerics | MIT, every algorithm inspectable | **exceed** |
| Reduction & expansion (TAM) | mature | Guyan/IRS/SEREP bases, TAM mass, SEREP expansion | parity |
| GUI, pretest planning, MPE from FRFs | mature | not in v1 (MPE targeted Round 2+, GAP-06/07) | gap (accepted) |
| Format breadth (Ansys/Abaqus native) | yes | partial (planned via meshio) | gap (accepted) |

## Notes for reviewers

- `.agent_workspace/` holds orchestration records (progress log, Round 2 plan);
  it is documentation, not runtime code.
- Known scope limits are registered, not hidden: QUAD4 and TET4 are the first two
  continuum slices, with HEX8 and the 3D beam still open; the Bayesian MAP estimator is
  implemented but its AC-UPD-006a/b rows are not yet tagged; MPE from measured FRFs and
  pretest planning remain pending — all tracked in `docs/SOTA_GAP_ANALYSIS.md`
  and `.agent_workspace/ROUND2_PLAN.md`.
```
