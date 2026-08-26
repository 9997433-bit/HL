# PR Draft — OpenFEMLab Round 2 Sign-Off

Ready to file. Base: `main`. Head: `cursor/femtools-industrial-7aa3`.
Verified at commit pending sign-off push: full suite **1508 passed**,
`ruff check .` clean (Python 3.12 / NumPy 2.5.2 / SciPy 1.18.1).
Registry: **47/47 acceptance criteria `verified`**.
Source references: [README](../README.md), [Chinese user guide](../docs/USER_GUIDE_zh.md),
[Round 2 sign-off](ROUND2_SIGNOFF.md), and [orchestrator report](ORCHESTRATOR_REPORT.md).

## Title

```
OpenFEMLab: industrial CAE platform — modal, correlation, updating, dynamics, 3D elements, IO interchange (1508 tests, 47 verified criteria)
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
  model with SPCs and lumped masses; spring/truss/planar-beam elements, the spatial
  Euler–Bernoulli `BeamElement3D`, plus the QUAD4
  isoparametric plane-stress/plane-strain continuum element (2×2 Gauss stiffness,
  consistent mass, `mesh.simple.quad_plate_mesh` generator) that passes the constant-strain
  patch test exactly and matches an equivalent bar spectrum to 2.4e-13, the TET4
  constant-strain tetrahedron (`mesh.simple.tet_block_mesh` on a Kuhn/Freudenthal split)
  which passes the 3D patch test on distorted geometry to 2.8e-16, and the HEX8 trilinear
  brick (`gauss_legendre_3d` tensor quadrature, `mesh.simple.hex_block_mesh` sharing its
  node numbering with `tet_block_mesh` so the two are element-for-element comparable
  discretizations of the same box), and the flat-facet `ShellQuad4Element` shell
  (six DOFs per node: the plane-stress membrane reused verbatim, a MITC4 Mindlin plate,
  and a drilling penalty, with `mesh.simple.shell_plate_mesh` numbering its nodes like
  `quad_plate_mesh`); one-pass preallocated COO→CSR assembly; one
  `ModalSolver` façade with dense and sparse shift-invert backends, static condensation of
  massless DOFs, mass normalization, participation/effective masses, and a shift-invert LU
  cache. Validated against closed-form spectra to 1e-9 relative (worst continuum case
  0.2 %). R2-T02 is **complete**: no formulation is outstanding, the solid/shell BDF
  cards read (A119), the converter reaches the shell through `quad4_as="shell"` (A129)
  and AC-ELEM-001..003 carry a `SHELL4` row beside QUAD4/TET4/HEX8 (A124). TET4's
  bending lock stays pinned by test rather than fixed, as documented.
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
  reader (GRID/CROD/MAT1 → neutral model); and a meshio bridge behind the optional
  `[io]` extra that reads and writes Gmsh, Abaqus, VTK, and the other formats
  supported by meshio. The public `read_meshio` / `write_meshio` entry points
  convert mesh files to and from `NeutralModel` for `vertex`, `line`, `triangle`,
  `quad`, `tetra`, and `hexahedron` cells. For example, `read_meshio("bracket.msh")`
  imports a model and `write_meshio(model, "bracket.vtu")` exports it. The adapter
  imports meshio lazily so `openfemlab.io` stays importable without the extra and
  records unmapped cell types in `meta["skipped_cell_types"]` instead of failing.
- **CLI** (`cli/`): `openfemlab modal | correlate | correlate-frf | update` over
  JSON/YAML model specs and UFF-58 measured FRFs; machine-readable JSON on stdout,
  diagnostics on stderr, CI acceptance gates via exit codes; covered end to end
  including subprocess runs.
- **QA stack**: 1331 tests including a machine-readable registry of 44 quantified
  acceptance criteria: **44 `verified`**, 0 `implemented`, and 0 `specified`, with
  **34/34 P0** and **10/10 P1** rows covered — plus boundary/probe suites,
  performance-regression gates, and benchmarks; GitHub Actions CI on Python
  3.10–3.13; `ruff check` clean.
- **Docs**: [`README`](README.md) with a reproducible CLI walkthrough,
  [`中文用户指南`](docs/USER_GUIDE_zh.md), `ARCHITECTURE.md`, `MODULE_SPEC.md` (MS-0..8),
  `ACCEPTANCE_CRITERIA.md` (44 criteria), `SOTA_GAP_ANALYSIS.md` (GAP-01..15),
  `OPTIMIZATION.md`, runnable `examples/`, and the
  [orchestrator report](.agent_workspace/ORCHESTRATOR_REPORT.md).

## Verification

- `PYTHONPATH=src python -m pytest` — **1331 passed** at commit `571c864`
  on Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1, from a detached private worktree.
- `ruff check .` — clean.
- The 147 tests added since the 1184-test snapshot at `e111901` are the flat-facet
  shell (72), the `NeutralModel` → `Model` converter (52) and the R2-T09 promotion
  tool (23).
- Per-suite breakdown (sums to 1331): acceptance registry + gates 388, dynamics 82,
  HEX8 76, shell facet 72, TET4 66, QUAD4 61, updating 57, correlation 52,
  neutral-model conversion 52, meshio bridge 44,
  modal solver 44, `BeamElement3D` 42, workflow 41, Bayesian updating 36,
  reduction/expansion 32, optimization 27, FRF correlation 25, promotion tool 23,
  IO (native/UFF/Nastran) 24, CLI 22+16+1 (incl. `correlate-frf`), core 18,
  result contract 17, boundary/performance/e2e/scaffold 13.
- The three continuum elements are held to one shared standard: AC-ELEM-001..003 are
  parametrized over QUAD4, TET4 and HEX8 alike, so the patch test (defects 1.5e-16 /
  2.8e-16 / 2.8e-16), the exact zero-energy mode count, and quadratic h-convergence
  (observed orders 4.005 / 4.095 / 4.005 per halving) describe the element library rather
  than whichever element landed most recently. The shell carries its own 72-test suite
  but is not yet in that parametrization.
- HEX8 is the concrete argument for hexes over tets: against the Euler–Bernoulli
  cantilever it is +8.0 % at 2475 DOF where TET4 on the *same* grid is still +25 %. Its
  shear locking at one element through the thickness (+89 %) is asserted too, so the
  limitation cannot drift into a silent regression.
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
| Solver-independent data model | mature, many interfaces | same idea; UNV 55/58, Nastran-lite, and the meshio bridge | parity (breadth later) |
| Modal analysis | internal + external solvers | SciPy dense + shift-invert Lanczos, sparse throughout, LU cache | parity |
| Element library | full industrial set | QUAD4 / TET4 / HEX8 continuum + spring/truss/planar beam + spatial `BeamElement3D` + the MITC4 flat-facet shell; no formulation outstanding, breadth (TRI3, quadratic elements, composites) still short | gap (narrowing) |
| Dynamic response / FRF | mature | Rayleigh/modal/hysteretic damping, complex modes, receptance/mobility/accelerance synthesis, FRAC/FDAC | parity |
| Correlation (MAC/COMAC/orthogonality) | yes | plus globally optimal Hungarian pairing | **exceed** |
| Sensitivity-based updating | weighted LSQ, manual tuning | LM with adaptive damping, Tikhonov, bounds by construction, analytic MAC sensitivities, Bayesian MAP with a Laplace posterior | **exceed** |
| Validation workflow | GUI-driven | seeded, schema-versioned six-stage pipeline with held-out gates and machine-readable failures | **exceed** |
| Scripting | proprietary BASIC-like | full Python + SciPy ecosystem, CI-native CLI | **exceed** |
| Reproducibility | binary project files | plain-text models, journaled runs in git, headless reruns | **exceed** |
| Cost / auditability | commercial licenses, closed numerics | MIT, every algorithm inspectable | **exceed** |
| Reduction & expansion (TAM) | mature | Guyan/IRS/SEREP bases, TAM mass, SEREP expansion | parity |
| GUI, pretest planning, MPE from FRFs | mature | not in v1 (MPE targeted Round 2+, GAP-06/07) | gap (accepted) |
| Format breadth (Ansys/Abaqus native) | yes | partial — meshio bridge landed behind the `[io]` extra; no native OP2/ODB | gap (narrowing) |

## Notes for reviewers

- **R2-T01 is COMPLETE.** The `correlate-frf` CLI closes its final exit item:
  measured UFF-58 or JSON/YAML FRFs can be correlated against synthesized damped-model
  responses with machine-readable FRAC/FDAC gates.
- **R2-T04 is ACCEPTANCE-COMPLETE.** The 36-test MS-3.5 Bayesian MAP estimator,
  AC-UPD-006a/b `implemented` gates, and Laplace σ_post in the `CorrectionReport`
  are all on the integration branch. CLI `update` document output remains outside
  this acceptance slice.
- `.agent_workspace/` holds orchestration records (progress log, Round 2 plan);
  it is documentation, not runtime code.
- **R2-T02 is complete.** QUAD4, TET4, HEX8, `BeamElement3D` and the flat-facet
  `ShellQuad4Element` are all in; module **M7** (`ELEM`) gates every one of them, since
  AC-ELEM-001..003 are parameterized over a case table that carries a `SHELL4` row
  beside the three continuum ones (A124, 9 shell cases); `io/neutral_convert.to_model`
  binds an imported ROD2/BEAM2/QUAD4/TET4/HEX8 block into those formulations and reaches
  the facet through `quad4_as="shell"` (A129); and the
  `CQUAD4`/`CTETRA`/`CHEXA`/`CBAR`/`PSHELL`/`PSOLID` cards read (A119). An imported
  industrial mesh — solid, frame or shell — can now be re-analyzed internally.
- The acceptance registry is closed at **47/47 `verified`** (all 37 P0 and 10 P1 rows),
  including module **M8 (IO)** AC-IO-001..003 promoted at Round 2 sign-off. MPE from
  measured FRFs and pretest planning remain Round 3 scope — see
  `.agent_workspace/ROUND2_SIGNOFF.md`.
- R2-T09 is **complete**: CI gates plus `promote_verified.py` advanced every row to
  `verified`.
```
