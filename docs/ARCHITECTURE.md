# OpenFEMLab — System Architecture

**Version:** 0.1 (Round 1 baseline) · **Status:** Approved for implementation
**Scope:** Open-source, solver-independent CAE platform for structural dynamics —
modal analysis, FE–test correlation, sensitivity-based model updating, and
simulation correction — inspired by FEMtools, designed to exceed it in the areas
where a modern, scriptable, open platform has structural advantages.

---

## 1. Vision and Scope

OpenFEMLab is a **Python-native structural dynamics validation platform**. It covers
the classic FEMtools workflow end to end:

1. **Model** a structure (import an FE model or build one with the internal solver).
2. **Analyze** its dynamics (eigenvalues, mode shapes, FRFs).
3. **Correlate** predictions against test data (MAC, COMAC, frequency error, FRF metrics).
4. **Update** the model so it matches reality (sensitivity-based iterative parameter
   estimation with modern regularization).
5. **Exploit** the validated model (structural optimization, what-if studies).

Non-goals for v1: GUI/3D visualization (headless-first; plots via matplotlib later),
nonlinear FE, explicit dynamics, full commercial-format parsers (subset importers only).

## 2. Design Principles

| # | Principle | Consequence |
|---|-----------|-------------|
| P1 | **Solver independence** | A neutral in-memory `Model` + results contracts. The internal FE solver is *one producer* among many; imported Nastran/UNV/meshio data are first-class. This mirrors FEMtools' key architectural idea. |
| P2 | **Arrays first** | All bulk data are NumPy arrays or SciPy sparse matrices with documented shapes/dtypes. No per-node Python objects on hot paths. Mode shapes are `(ndof, nmodes)` arrays, period. |
| P3 | **Pure functional core, thin stateful shell** | Numerics (MAC, sensitivities, eigensolves) are pure functions of arrays → trivially testable, parallelizable, and AD-friendly. Stateful orchestration (sessions, updating loops) lives above them. |
| P4 | **Headless, deterministic, CI-native** | Every workflow runs from script/CLI with seeded determinism. Validation workflows become version-controlled, reviewable artifacts — impossible with a proprietary desktop tool. |
| P5 | **Strict layering** | A module may import only from layers below it (see §3). Enforced by convention now, import-linter later. |
| P6 | **Typed contracts** | Public APIs are fully type-annotated dataclasses/functions; `mypy --strict` on `core` from Round 2. |
| P7 | **Optional dependencies stay optional** | `numpy`+`scipy` are the only hard deps. `meshio`, `rich` are extras behind adapter seams; the numerics never import them. |

## 3. Module Diagram (layered)

```
┌─────────────────────────────────────────────────────────────────────┐
│  L4  INTERFACES                                                     │
│      openfemlab.cli          rich-powered CLI (modal/correlate/     │
│                              update/info subcommands)               │
│      openfemlab (top level)  scripting API = the package itself     │
├─────────────────────────────────────────────────────────────────────┤
│  L3  APPLICATIONS (workflows that combine analyses)                 │
│      openfemlab.updating     parameters, residuals, sensitivities,  │
│                              regularized iterative updater          │
│      openfemlab.optimization objective/constraint abstraction over  │
│                              scipy.optimize; DOE hooks              │
│      openfemlab.correlation  MAC/COMAC/orthogonality, mode pairing, │
│                              geometry alignment, error tables       │
├─────────────────────────────────────────────────────────────────────┤
│  L2  ANALYSIS (produce results from a model)                        │
│      openfemlab.modal        sparse eigensolvers (shift-invert      │
│                              Lanczos/LOBPCG), MPE (Round 2+)        │
│      openfemlab.solver       element library, K/M/C assembly,       │
│                              static & harmonic response             │
├─────────────────────────────────────────────────────────────────────┤
│  L1  MODEL (neutral representation)                                 │
│      openfemlab.core         Model, DofMap, Material/Property,      │
│                              ModalResult, TestData contracts        │
│      openfemlab.mesh         mesh containers, generators,           │
│                              nearest-node queries                   │
├─────────────────────────────────────────────────────────────────────┤
│  L0  FOUNDATION (world ↔ platform)                                  │
│      openfemlab.io           UNV (55/58/2411/2412), Nastran-lite    │
│                              BDF/OP2 subsets, meshio bridge,        │
│                              native .ofl (npz/json) round-trip      │
└─────────────────────────────────────────────────────────────────────┘
Rule: imports point strictly downward. `core` imports nothing but numpy/scipy.
```

### Module responsibilities

| Module | Owns | Key public objects (Round 1 contracts) |
|--------|------|----------------------------------------|
| `core` | Neutral model & result datatypes, DOF bookkeeping | `Model`, `DofMap`, `DofType`, `Material`, `ModalResult`, `TestData` |
| `mesh` | Geometry containers, simple generators, spatial queries | `make_line_mesh`, `make_grid_mesh`, `nearest_nodes` |
| `solver` | Element formulations, sparse assembly, BCs, linear solves | `ElementFormulation` (ABC), `assemble_kм`, `apply_bcs` |
| `modal` | Eigen-extraction, mode normalization, effective mass | `solve_modes`, `normalize_modes` |
| `correlation` | FE↔test comparison metrics & pairing | `mac`, `automac`, `comac`, `pair_modes`, `CorrelationReport` |
| `updating` | Parameter estimation loop | `Parameter`, `Residual` (ABC), `SensitivityEngine`, `ModelUpdater` |
| `optimization` | Design optimization on validated models | `OptimizationProblem`, `minimize` adapter |
| `io` | All file formats, external-solver adapters | `read_unv`, `write_unv`, `from_meshio`, `read_model`, `write_model` |
| `cli` | User-facing command line | `openfemlab` entry point (`main`) |

## 4. Core Data Contracts

The whole platform hinges on four datatypes defined in `core` (all frozen or
append-only dataclasses over arrays):

```python
Model                      # neutral FE model
├── nodes:      (N, 3) float64        node coordinates
├── node_ids:   (N,)  int64           external labels (stable across io)
├── elements:   dict[ElementType, (E, k) int64]   connectivity blocks
├── materials / properties: id → dataclass tables
└── dof_map:    DofMap                 (node_id, DofType) ↔ global index

ModalResult                # produced by modal OR imported from external solver
├── frequencies: (m,) float64   [Hz]
├── shapes:      (ndof, m) float64|complex128
├── dof_map:     DofMap          which rows mean what  ← the correlation key
└── meta:        provenance (solver, units, timestamp)

TestData                   # measured modal model (subset of DOFs)
├── frequencies, shapes, damping
├── dof_map:     DofMap on the *test* geometry
└── geometry:    (n_meas, 3) sensor coordinates

SensitivityMatrix          # ∂(residuals)/∂(parameters), dense (nr, np)
```

`DofMap` is the load-bearing abstraction: correlation between an FE model with
10⁶ DOFs and a test with 40 accelerometers is expressed as **two DofMaps plus a
pairing**, which drives reduction (Guyan/SEREP) or expansion transparently.

## 5. Data Flow

### 5.1 Modal analysis pipeline

```
 io.read_* ──► core.Model ──► solver.assemble (K, M sparse CSR)
                                   │
                                   ▼
                    modal.solve_modes  (scipy.sparse.linalg.eigsh,
                                        shift-invert σ=0, k modes)
                                   │
                                   ▼
                            core.ModalResult ──► io.write_* / cli report
```

### 5.2 Correlation pipeline

```
 core.ModalResult (FE)          core.TestData (io.read_unv 55/58)
        │                              │
        └──► correlation.align ◄───────┘      geometric node pairing +
                    │                         DOF intersection (via DofMaps)
                    ▼
        correlation.mac / comac / orthogonality
                    │
                    ▼
        correlation.pair_modes  (Hungarian assignment on MAC + Δf penalty)
                    │
                    ▼
        CorrelationReport  (paired table: f_FE, f_test, Δf%, MAC) ──► cli/JSON
```

### 5.3 Model updating loop (the heart of the platform)

```
        ┌───────────────────────────────────────────────────────────┐
        │  ModelUpdater.iterate()                                   │
        │                                                           │
        │  θᵢ ──► core.Model(θᵢ) ──► modal.solve ──► correlation    │
        │   ▲                                            │          │
        │   │                                   residuals r(θᵢ)     │
        │   │                                            │          │
        │   │      SensitivityEngine: S = ∂r/∂θ          ▼          │
        │   │      (Fox–Kapoor semi-analytic λ′/φ′,   converged? ──►│──► updated Model
        │   │       Nelson's method, FD fallback)       no          │    + audit trail
        │   │                                            │          │
        │   └── Δθ = argmin ‖W½(SΔθ + r)‖² + α‖LΔθ‖² ◄───┘          │
        │        (Tikhonov / L-curve α; trust region; bounds)       │
        └───────────────────────────────────────────────────────────┘
```

Every iteration is journaled (parameters, residuals, condition numbers) to a
machine-readable audit trail — updating runs become reproducible artifacts.

## 6. Technology Stack

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Language | Python ≥ 3.10 | typing features (`|` unions, `ParamSpec`), dataclass slots |
| Numerics | **NumPy** (hard dep) | array contracts everywhere |
| Sparse & solvers | **SciPy** (hard dep) | `sparse.csr_array`, `eigsh` shift-invert, `lobpcg`, `optimize`, Hungarian (`linear_sum_assignment`) |
| Mesh interchange | **meshio** (extra: `[io]`) | 40+ formats for free; wrapped behind `io.meshio_bridge` so it never leaks into core |
| CLI/UX | **rich** (extra: `[cli]`) + stdlib `argparse` | beautiful tables/progress in terminals & CI logs, zero framework lock-in |
| Native persistence | `.npz` + JSON sidecar | zero-dep, fast, diff-able metadata |
| QA | pytest, ruff, mypy (extra: `[dev]`) | Round 2 gates: coverage on numerics ≥ 90 % |
| Packaging | `pyproject.toml`, setuptools, src-layout | modern standard, no import-shadowing accidents |

Deliberately **not** used in v1: pandas (tables are small; dict-of-arrays suffice),
numba/Cython (assembly via vectorized scatter-add is fast enough at target scale;
revisit with benchmarks), any GUI toolkit.

## 7. FEMtools Comparison — SOTA Gaps We Will Exceed

| Capability | FEMtools (SOTA commercial) | OpenFEMLab plan | Verdict |
|------------|----------------------------|-----------------|---------|
| Solver-independent data model | ✔ mature, many interfaces | ✔ same idea; fewer formats at first (UNV, Nastran-lite, meshio) | parity (breadth later) |
| Modal analysis | ✔ internal + external solvers | ✔ SciPy shift-invert Lanczos/LOBPCG, sparse throughout | parity |
| Correlation (MAC/COMAC/orthogonality) | ✔ | ✔ + **optimal mode pairing via Hungarian assignment** instead of greedy max-MAC | **exceed** |
| Sensitivity-based updating | ✔ classic weighted least squares, manual tuning | ✔ + **modern regularization**: Tikhonov with automatic L-curve/GCV α-selection, trust-region steps, parameter bounds by construction | **exceed** |
| Uncertainty quantification | limited (deterministic updating) | **Bayesian/stochastic updating hooks** (posterior sampling over θ) designed into `updating` from day one | **exceed** |
| Scripting | proprietary BASIC-like language | **full Python** — entire SciPy ecosystem, notebooks, CI pipelines | **exceed** |
| Reproducibility / versioning | binary project files, GUI-driven | **plain-text models & journaled updating runs in git; headless CI reruns** | **exceed** |
| Extensibility | closed, vendor plugin API | open ABCs (`ElementFormulation`, `Residual`) + entry-point plugin discovery | **exceed** |
| Cost / auditability | expensive licenses, closed numerics | free, every algorithm inspectable & citable | **exceed** |
| GUI, pretest planning, MPE from FRFs | ✔ mature | ✘ v1 (MPE targeted Round 2+, sensor placement via effective-independence as stretch goal) | gap (accepted) |
| Format breadth (Ansys/Abaqus native) | ✔ | partial via meshio | gap (accepted) |

Strategy: **concede GUI and format breadth; win on algorithms, openness, and
automation** — the dimensions that matter for modern CAE toolchains embedded in
CI/CD and digital-twin pipelines.

## 8. Extension Points

- `solver.ElementFormulation` ABC — add element types without touching assembly.
- `updating.Residual` ABC — new residual kinds (FRF amplitude, antiresonances,
  static flexibility) plug into the same updater.
- `io` registry — `read_model("x.unv")` dispatches on extension; third-party
  packages can register readers via the `openfemlab.io` entry-point group.
- `optimization.OptimizationProblem` — swap scipy backends or external optimizers.

## 9. Testing & Quality Strategy

1. **Analytical oracles**: cantilever Euler–Bernoulli beam and simply-supported
   plate frequencies vs closed-form solutions (target < 0.5 % for converged mesh).
2. **Property tests**: MAC(φ, φ) = I; MAC invariant to scaling/sign; K, M symmetry
   and positive-(semi)definiteness after BCs.
3. **Round-trip tests**: Model → UNV → Model equality; ModalResult npz round-trip.
4. **Regression on updating**: perturbed-parameter twin experiments — start from a
   detuned model, verify the updater recovers known true parameters.
5. CI: ruff + mypy + pytest on 3.10/3.11/3.12.

## 10. Roadmap

| Round | Deliverables |
|-------|--------------|
| **R1 (this)** | Architecture, contracts, package skeleton, working MAC + eigsh wrapper, CLI shell |
| **R2** | Internal solver (rod/beam/tri-shell/quad-shell), UNV io, full correlation report, sensitivity engine (FD + Fox–Kapoor), Tikhonov updater, beam/plate benchmark suite |
| **R3** | FRF residuals, SEREP expansion, Bayesian updating hooks, MPE (poly-reference LSCF candidate), optimization workflows, docs & examples polish, performance benchmarks |

## 11. Round 1 As-Built Notes

Round 1 was built by parallel agents; the merged tree deviates from the plan
above in ways that are deliberate or scheduled for consolidation:

1. **Neutral vs internal model split.** The L1 "neutral model" now lives in
   `core.neutral` (`NeutralModel`, `NeutralMaterial`, `NeutralProperty`,
   `ElementType`), while `core.model.Model` is the *internal solver's* working
   model (nodes, bound elements, SPCs, point masses, DOF signature). This is a
   sharper version of P1 than §4 sketched: the interchange contract and the
   computation model evolve independently, with io converters bridging them.
   `DofMap` (`core.dofs`) and the result contracts (`core.results`) are shared
   by both stacks.
2. **The internal solver landed early.** `core.elements` (spring, truss/bar,
   planar Euler–Bernoulli beam), `core.assembly` (COO-triplet CSR assembly,
   free/constrained partitioning), and `solver.modal.ModalSolver` (dense/
   shift-invert auto-selection, static condensation, participation factors)
   arrived in Round 1 with analytic validation, ahead of the §10 schedule.
3. **Two eigen entry points exist** — `solver.modal.ModalSolver` (internal
   model in) and `modal.eigen.solve_modes` (raw `K, M, DofMap` in, for
   imported matrices) — but they now share one kernel and one result type:
   `solve_modes` is a thin wrapper over `ModalSolver`, and the duplicate
   `ModalResult` in `solver.modal` is gone, so `core.results.ModalResult` is
   the single contract every producer returns. It takes the spectrum as
   frequencies [Hz] or eigenvalues [ω²] and carries the optional solver
   provenance (assembled system, normalization, condensed DOF count) that
   backs modal masses and participation factors. `with_dof_map()` labels a
   solver result for `io`/`correlation` without rebuilding it.
4. **Element placement.** Element formulations currently live in
   `core.elements` (bound to the internal model) rather than `solver` as §3
   drew. Acceptable for Round 1; revisit only if a second matrix producer
   appears.
5. **Native io first.** Schema-versioned YAML/JSON round-trip io for neutral
   models and modal/test data (`io._native`) landed before UNV; UNV datasets
   55/58/2411/2412 remain the top io priority for Round 2 (test-data
   ingestion).
