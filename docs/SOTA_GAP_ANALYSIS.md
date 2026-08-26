# OpenFEMLab vs FEMtools — SOTA Gap Analysis (Round 1 Audit)

**Auditor:** A03 (backfill) · **Date:** 2026-08-26 07:08 UTC
**Snapshot:** branch `cursor/femtools-industrial-7aa3`, commit `8625fc2` plus in-flight
uncommitted work from concurrent Round 1 subagents (correlation/updating/cli/optimization
modules were untracked at audit time).
**Companion documents:** `ARCHITECTURE.md` (design), `MODULE_SPEC.md` (MS-x requirements),
`ACCEPTANCE_CRITERIA.md` (AC-x tests). This document measures the *code that exists* against
FEMtools' shipped capability set and the wider 2026 state of the art, and ranks the gaps.

---

## 1. Audit method

1. Read every module under `src/openfemlab/` and every test under `tests/`.
2. Attempted `import openfemlab` and each subpackage; ran the full pytest suite; recorded
   failures (Appendix A).
3. Built a FEMtools capability map from its module structure (Framework, Dynamics,
   Pretest & Correlation, Model Updating, Optimization, MPE, Probabilistic Analysis) and
   extended it with modern open-source SOTA (Bayesian updating, OMA/SSI, AD sensitivities,
   CMS reduction).
4. Classified each capability as **Present**, **Partial**, or **Absent**, then ranked gaps
   by severity × workflow impact.

Severity scale: **P0** = blocks the core FEMtools workflow (model → analyze → correlate →
update); **P1** = core parity feature missing; **P2** = enhancement / scale / polish.

---

## 2. Capability baseline — what OpenFEMLab has today

### L1 Model (`core`, `mesh`)
| Capability | Status | Evidence |
|---|---|---|
| Rich internal `Model` (nodes, DOF signature, SPCs, point masses, node-major numbering) | Present | `core/model.py` |
| `DofMap` with FE/test DOF intersection primitive | Present | `core/dofs.py` |
| `ModalResult` / `TestData` result contracts carrying their own DofMap | Present | `core/results.py` |
| 1D mesh builders (bar/beam/spring-mass chain) | Present | `mesh/simple.py` |
| Neutral interchange model (`ElementType` blocks) unified with solver `Model` | **Partial** — two representations coexist, io targets the neutral one | `core/model.py` vs `io/_native.py` |
| 2D/3D mesh generators, nearest-node spatial queries | Absent | planned in `ARCHITECTURE.md` §3 |

### L2 Analysis (`solver`, `modal`)
| Capability | Status | Evidence |
|---|---|---|
| Elements: grounded/2-node spring, truss/bar (2D/3D), planar Euler-Bernoulli beam, point mass | Present | `core/elements.py` |
| Shells (TRI3/QUAD4), solids (TET4/HEX8), 3D beam, Timoshenko, offsets/orientation | **Absent** | `ElementType` enum declares them; no formulations |
| COO→CSR assembly, symmetrization, free/constrained partition | Present | `core/assembly.py` |
| Dense + sparse shift-invert Lanczos eigensolver, auto backend choice | Present | `solver/modal.py` |
| Massless-DOF static (Guyan) condensation with exact recovery | Present | `solver/modal.py::_MasslessCondensation` |
| Rigid-body mode handling, mass/max normalization, deterministic signs | Present | `solver/modal.py` |
| Participation factors, effective masses, orthogonality check | Present | `solver/modal.py::ModalResult` |
| Second, redundant eigensolver entry point | **Duplicate** | `modal/eigen.py::solve_modes` |
| Damping models (Rayleigh/modal/structural), complex modes | **Absent** | — |
| Harmonic/transient response, FRF synthesis, mode superposition | **Absent** | — |
| Static analysis, stress recovery | Absent | — |

### L3 Applications (`correlation`, `updating`, `optimization`)
| Capability | Status | Evidence |
|---|---|---|
| MAC / AutoMAC / weighted MAC / orthogonality / MSF / COMAC | Present | `correlation/mac.py` |
| Greedy + Hungarian (optimal) mode pairing, re-paired per updating iteration | Present | `correlation/pairing.py` |
| Frequency-error metrics with pinned sign convention, correlation summary/report | Present | `correlation/metrics.py` |
| FRF correlation (FRAC/FDAC) | **Absent** | — |
| Geometry alignment / test-sensor ↔ FE-node mapping | **Absent** | correlation assumes a common DOF set already exists |
| Pseudo-orthogonality with TAM mass (Guyan/IRS/SEREP) | **Absent** | — |
| Fox & Kapoor analytic eigenvalue sensitivity (pure-array) | Present | `updating/sensitivity.py` |
| FD sensitivities with MAC-based mode tracking | Present | `updating/sensitivity.py::modal_sensitivity` |
| LM / Gauss-Newton updater, Tikhonov regularization, bounds, audit trail | Present | `updating/updater.py` |
| Analytic dK/dp / dM/dp providers wired to the element library | **Absent** | Fox-Kapoor is fed by hand |
| Parameter target resolver (`material.<id>.<attr>`) | **Absent** | declared "Round 2" in `updating/parameters.py` |
| Bayesian updating / UQ / parameter collinearity diagnostics | **Absent** | promised by AC-UPD-006/007 |
| Optimization backend | **Stub** | `optimization/__init__.py::solve` raises `NotImplementedError` |

### L0/L4 Foundation & interfaces (`io`, `cli`)
| Capability | Status | Evidence |
|---|---|---|
| Native schema-versioned JSON/YAML round-trip (model, modal result, test data) | Present | `io/_native.py`, `io/_common.py` |
| UNV/UFF (55/58/2411/2412), Nastran BDF/OP2, meshio bridge | **Absent** | planned in `ARCHITECTURE.md` L0 |
| CLI: `version`, `info` | Present | `cli/main.py` |
| CLI: `modal`, `correlate`, `update` | **Stub** | exit code 2, "scheduled for Round 2" |
| Visualization (mode shapes, MAC heatmaps) | Absent (deferred by design) | non-goal for v1 |

### Quality infrastructure
Tests (unit, boundary, probes, acceptance-registry), benchmarks (≤1000 DOF), CI workflow,
packaging, and three spec documents exist — a genuinely strong Round 1 scaffold. However,
at audit time the suite did **not** collect cleanly (Appendix A).

---

## 3. Reference SOTA

### 3.1 FEMtools capability map (parity target)
| FEMtools module | Key capabilities | OpenFEMLab status |
|---|---|---|
| Framework | Scripting API, database, solver interfaces (Nastran/Ansys/Abaqus/UFF) | Python API present; **no external solver/format interfaces** |
| Dynamics | FRF synthesis, forced response, structural modification | **Absent** |
| Pretest & Correlation | Sensor/exciter placement (EI), TAM, geometry mapping, MAC/COMAC/orthogonality, FRF correlation | Shape metrics + pairing present; **pretest, TAM, mapping, FRF metrics absent** |
| Model Updating | Sensitivity-based (freq/shape/FRF/mass residuals), local/global parameters, robust estimation | Freq+MAC residual LM updater present; **FRF/mass residuals, parameter resolver, analytic dK/dp absent** |
| Optimization | Sizing/shape optimization on validated models | **Stub** |
| MPE | Modal parameter extraction from measured FRFs, stabilization diagrams | **Absent** |
| Probabilistic Analysis | Monte Carlo, DOE, response surfaces | **Absent** |

### 3.2 Modern SOTA beyond FEMtools (differentiation opportunities)
- **Bayesian/stochastic updating** (TMCMC, hierarchical models) — supersedes deterministic
  LM in research practice; FEMtools has only limited probabilistic tooling.
- **Operational modal analysis** (SSI-cov/SSI-data), automated stabilization-diagram
  clustering — standard in 2026 open tooling (pyOMA-class).
- **Exact sensitivities via automatic differentiation** (JAX-style) instead of FD.
- **Component mode synthesis** (Craig-Bampton) and ROM-accelerated updating loops.
- **CI-native, headless, versioned validation workflows** — OpenFEMLab's structural
  advantage (`ARCHITECTURE.md` P4); no commercial equivalent.

---

## 4. Gap register

| ID | Sev | Area | Gap | Target round |
|---|---|---|---|---|
| GAP-01 | P0 | Integration | Split-brain Round 1 architectures; seam symbols renamed mid-flight; duplicate `ModalResult`/eigensolver; io targets a model the solver doesn't use; suite doesn't collect | R2 (first task) |
| GAP-02 | P0 | Elements | 1D-only element library; no shells/solids/3D beam despite declared `ElementType`s | R2 |
| GAP-03 | P0 | IO | No UNV/UFF, Nastran BDF/OP2, or meshio import/export — cannot touch an industrial model or real test data | R2 |
| GAP-04 | P0 | Dynamics | No damping, complex modes, harmonic/transient response, or FRF synthesis | R2 |
| GAP-05 | P1 | Correlation | No FRF correlation metrics (FRAC/FDAC) and no FRF residual in updating | R2/R3 |
| GAP-06 | P1 | MPE | No modal parameter extraction (LSCE/LSCF/PolyMAX-class, stabilization diagram, SSI/OMA); `TestData` never populated from measurements | R3 |
| GAP-07 | P1 | Pretest | No sensor/exciter placement (Effective Independence, kinetic energy), no test planning | R3 |
| GAP-08 | P1 | Reduction/expansion | No Guyan/IRS/SEREP/Craig-Bampton, no TAM pseudo-orthogonality, no shape expansion to full FE DOFs | R2/R3 |
| GAP-09 | P1 | Correlation | No geometry alignment / automated test-sensor ↔ FE-node mapping | R2 |
| GAP-10 | P1 | Updating | No parameter target resolver, no assembled dK/dp providers, no mass/shape-difference residuals, no robust estimation, no subset selection/collinearity diagnostics (AC-UPD-007) | R2 |
| GAP-11 | P1 | UQ | No Bayesian updating (AC-UPD-006), Monte Carlo, DOE, or response surfaces | R3 |
| GAP-12 | P2 | Optimization | `OptimizationProblem.solve` is `NotImplementedError`; AC-OPT-* unmet | R2/R3 |
| GAP-13 | P2 | Scale | Dense threshold 400 DOF; benchmarks stop at 1k DOF vs AC-PERF-001's 50k budget; no LOBPCG/AMG path; no reanalysis acceleration in updating loops | R3 |
| GAP-14 | P2 | Workflow | CLI `modal`/`correlate`/`update` stubbed; no session report schema (AC-WORK-002) | R2/R3 |
| GAP-15 | P2 | Visualization | No mode-shape/MAC plotting helpers (deferred by design for v1) | R3+ |

---

## 5. Top 5 gaps (detailed)

### 1. GAP-01 — Round 1 integration split-brain (P0, blocks everything)
Two subagents produced two incompatible architectures in parallel: a **rich `Model`**
(`core/model.py` + `core/elements.py` + `solver/modal.py`) and a **neutral array container**
(`core/dofs.py` + `core/results.py` + `modal/eigen.py` + `io/_native.py`). During the audit
the tree was observed in three different states within minutes; at each snapshot at least
one import or test-collection failure existed (`ParameterSet`/`FrequencyDifference`/
`auto_mac` renames, `ElementType` removal). There are two `ModalResult` types and two
eigensolver entry points with different APIs and normalization semantics. **Consequence:**
every downstream module builds on a moving foundation; correlation and updating cannot be
trusted end-to-end until one canonical model/result contract is enforced and the duplicate
solver path is deleted or made a thin wrapper. This must be the first Round 2 task, gated
by a green `import openfemlab` + full-suite CI check.

### 2. GAP-03 — No industrial model & test-data exchange (P0)
FEMtools' defining trait is solver independence *in practice*: it reads Nastran, Ansys,
Abaqus models and universal-file test data. OpenFEMLab currently reads only its own
JSON/YAML schema, so no real structure, mesh, or measured mode set can enter the platform.
Minimum viable parity: UFF/UNV datasets 55 (modes), 58 (FRFs), 2411/2412 (nodes/elements),
a Nastran BDF subset (GRID/CBAR/CQUAD4/CTETRA/PSHELL/PSOLID/MAT1/EIGRL), and a `meshio`
bridge behind an optional-dependency seam (per P7).

### 3. GAP-04 + GAP-05 — No damping, forced response, or FRF chain (P0/P1)
Everything downstream of undamped real modes is missing: damping models, complex modes,
harmonic response, FRF synthesis, FRF correlation (FRAC/FDAC), and FRF-based updating
residuals. Test campaigns deliver FRFs, and FEMtools Dynamics + FRF updating is a core
industrial workflow; without this chain OpenFEMLab can only correlate pre-extracted mode
tables.

### 4. GAP-06 — No experimental modal analysis (MPE) (P1)
The `TestData` contract exists but nothing produces it from measurements. Parity needs at
least one FRF-domain curve fitter (LSCF/poly-reference, i.e. PolyMAX-class) with a
stabilization diagram; modern SOTA adds SSI-based OMA. Combined with UFF-58 import
(GAP-03), this closes the loop from raw measurement to correlation input.

### 5. GAP-07 + GAP-08 — No pretest planning or reduction/expansion bridge (P1)
There is no sensor/exciter placement (Effective Independence, modal kinetic energy), no
test-analysis model (Guyan/IRS/SEREP) for pseudo-orthogonality with the reduced mass
matrix, and no mode-shape expansion from sensor DOFs to full FE DOFs. Today correlation
silently assumes the test DOF set is a subset of FE DOFs with identical labels — the
hard 90% of real FE-test correlation (geometry alignment, mapping, reduction) is absent.

**Runners-up:** GAP-02 (shells/solids — required before any imported industrial mesh can be
*re-analyzed* internally rather than merely correlated) and GAP-11 (Bayesian UQ — the main
opportunity to *exceed* FEMtools rather than chase it).

---

## 6. Recommended sequencing

- **Round 2 (make the core workflow real):** GAP-01 unification first (single Model/Result
  contract, one eigensolver façade, green CI); then GAP-03 (UFF + BDF subset), GAP-04
  (damping + FRF synthesis), GAP-10 (parameter resolver + assembled dK/dp), GAP-09
  (node mapping), GAP-02 (QUAD4/TET4/HEX8 minimum set), GAP-12 (scipy backend), GAP-14
  (CLI wiring).
- **Round 3 (parity completion + differentiation):** GAP-06 (LSCF + stabilization), GAP-07
  (EI pretest), GAP-08 (SEREP/TAM + expansion), GAP-05 (FRAC/FRF updating), GAP-11
  (Bayesian layer), GAP-13 (50k-DOF budget, LOBPCG), GAP-15 (plot helpers).

---

## Appendix A — Evidence snapshot (2026-08-26 ~07:05–07:08 UTC)

Observed sequentially while concurrent Round 1 agents were writing:

1. `import openfemlab` → `ImportError: cannot import name 'DOF' from 'openfemlab.core.model'`
   (neutral-container `model.py` on disk, rich-Model consumers).
2. Minutes later: `NameError: name 'IntEnum' is not defined` (file mid-rewrite), 4 test
   collection errors.
3. Final snapshot (commit `8625fc2` + untracked files):
   `import openfemlab.updating.updater` → `ImportError: cannot import name
   'FrequencyDifference' from 'openfemlab.correlation.mac'` (symbol moved to
   `correlation.metrics`); pytest: 1 collection error (`tests/test_correlation.py` imports
   `auto_mac`, API now `automac`); `tests/acceptance/test_criteria_registry.py` failing
   (registry out of sync with `ACCEPTANCE_CRITERIA.md`).

These are transient integration states, not permanent defects — recorded here as evidence
for GAP-01's severity and for the Round 2 rule that seam changes must land atomically with
their consumers.
