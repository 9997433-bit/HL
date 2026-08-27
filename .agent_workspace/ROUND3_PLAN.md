# Round 3 Plan — Parity Completion and Differentiation (OpenFEMLab)

**Author:** A130 · **Date:** 2026-08-26
**Branch:** `cursor/femtools-industrial-7aa3` (Round 2 signed off at `104e9e1`;
plan drafted against `a662cc3`, rebased onto `413310a` after the A135/A137/A138
merges landed mid-draft)
**Inputs:** [`docs/SOTA_GAP_ANALYSIS.md`](../docs/SOTA_GAP_ANALYSIS.md) (gap
register §4, sequencing §6), [`ROUND2_SIGNOFF.md`](ROUND2_SIGNOFF.md) (deferred
list), [`ROUND2_PLAN.md`](ROUND2_PLAN.md) (task history and format),
[`docs/ACCEPTANCE_CRITERIA.md`](../docs/ACCEPTANCE_CRITERIA.md) (conventions §1,
enforcement §10), [`docs/MODULE_SPEC.md`](../docs/MODULE_SPEC.md) (MS anchors),
[`PROGRESS.md`](PROGRESS.md) (Round 3 kickoff table, A130–A139).

This plan turns `SOTA_GAP_ANALYSIS.md` §6 ("Round 3: parity completion +
differentiation") and the `ROUND2_SIGNOFF.md` deferred list into a prioritized,
dependency-ordered backlog. Round 3's theme: **close the measurement loop**
(raw FRFs → extracted modes → correlation), **plan the test** (sensor
placement), **scale to industrial size** (50k DOF, sparse end to end), and
**finish the updating depth** Round 2 left at P1.

---

## 0. Entry state

Round 2 exit bar met on the integration branch (see
[`ROUND2_SIGNOFF.md`](ROUND2_SIGNOFF.md)): full suite **1508 passed, 0
failed**, `ruff check .` clean, registry **47/47 `verified`** (37 P0 + 10 P1),
CI `gates` job re-running every promoted criterion. Modules M1–M8 all carry
verified rows. Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1, `PYTHONPATH=src`.

Deferred into this round (signoff §"Deferred to Round 3" + gap register §4):

| Item | Source | Round 3 task |
|---|---|---|
| GAP-06 — modal parameter estimation from measured FRFs | §6, signoff | R3-T01 |
| GAP-07 — pretest planning / effective independence | §6, signoff | R3-T02 |
| GAP-13 — 50k-DOF sparse scale; R2-T03 densification residue | §6, signoff, STATUS §4.2 | R3-T03 |
| R2-T06 remainder — QR screen, MAC-row Jacobian, model-level resolver | signoff, STATUS §4.1 | R3-T04 |
| FRF updating residual (GAP-05 residue) | §6, signoff | R3-T05 |
| GAP-03 extension — OP2 / native industrial readers | signoff, STATUS §4.3 | R3-T06 |
| GAP-15 — plotting / visualization | §6, signoff | R3-T07 |
| GAP-11 residue (sampling/DOE), GAP-12 residue (shape dK/da) | §4 | stretch (§3) |

Per [AC §1.2](../docs/ACCEPTANCE_CRITERIA.md), **P2 criteria are targeted at
Round 3**: new Round 3 rows register at P2, and the P2 tier becomes the
sign-off gate for this round the way P1 gated Round 2.

---

## 1. Core backlog (dependency-ordered)

The spec-first rule carries over unchanged from Round 2: any task introducing
new AC IDs lands `ACCEPTANCE_CRITERIA.md` + `MODULE_SPEC.md` +
`tests/acceptance/test_criteria_registry.py` **in the same change**
([AC §10](../docs/ACCEPTANCE_CRITERIA.md)), and IDs are dense per module
([AC §1.1](../docs/ACCEPTANCE_CRITERIA.md)). Because module numbering and the
pinned registry inventory are global, **registry-editing changes must merge
serially** (see §2). Proposed module slots below follow the current tail
(M8/MS-9): the first registration to land takes the next slot and later ones
rebase — the IDs here are proposals, not reservations.

### R3-T01 — Modal parameter estimation (MPE) from measured FRFs

- **Priority:** 1 · **Gap:** [GAP-06](../docs/SOTA_GAP_ANALYSIS.md) (§5.4) ·
  **Dispatched:** A133 (spec + acceptance scaffold, spec-first)
- **Why first:** the `TestData` contract exists but nothing produces it from
  measurements — this is the largest remaining FEMtools parity hole and, with
  the UFF-58 reader already landed (A12), it closes the loop from raw
  measurement to correlation input. Everything Round 2 built consumes
  pre-extracted mode tables; MPE makes them producible in-platform.
- **Scope:**
  - `mpe/` package: one FRF-domain poly-reference curve fitter (LSCF /
    PolyMAX-class) over a measured FRF matrix; pole extraction with frequency
    and damping ratio per model order.
  - Stabilization diagram: pole classification (stable in frequency / damping
    / vector across orders, tolerance-based, deterministic) with a plain data
    result the CLI and R3-T07 plotting can both consume.
  - `TestData` population: extracted poles + mode shape columns → the existing
    `TestData` contract, feeding `correlate_modal_data` unchanged (no second
    correlation entry point — GAP-01 rule).
  - SSI-based OMA is **out of scope** for the round (differentiation follow-up;
    record as stretch if the LSCF core lands early).
- **Acceptance links (proposed, module M9 / family `MPE` / spec anchor MS-10):**
  AC-MPE-001 (P2, `twin`) — FRFs synthesized from a known damped model (M6
  machinery, AC-DYN-001 fixtures) → LSCF recovers natural frequencies to
  ≤ 0.1 % and damping ratios to ≤ 5 %; AC-MPE-002 (P2, `property`) —
  stabilization: physical poles classify stable across model orders, spurious
  poles do not persist, classification deterministic under the AC §1.4 seeding
  rule; AC-MPE-003 (P2, `contract`) — UFF-58 file → MPE → `TestData` →
  `correlate_modal_data` end to end, self-correlation MAC = 1 on the twin.
- **Dependencies:** none on other R3 tasks. Consumes M6 FRF synthesis (done)
  for fixtures and `io/uff.py` (done) for ingest. Feeds the R3-T07
  stabilization plot and headline demo 1 (§4).

### R3-T02 — Pretest planning: effective independence sensor placement

- **Priority:** 2 · **Gap:** [GAP-07](../docs/SOTA_GAP_ANALYSIS.md) (§5.5) ·
  **Dispatched:** A134 (spec + stub API, spec-first)
- **Why second:** the other half of the test–analysis bridge. Round 2 landed
  reduction/expansion and TAM pseudo-orthogonality (R2-T03, AC-CORR-006/009
  `verified`); pretest placement is their natural consumer and needs no new
  numerics beyond a ranking loop.
- **Scope:**
  - `pretest/` package: Effective Independence (EI) — iterative removal of the
    lowest-contribution DOF from the Fisher information of the target mode
    partition — plus modal kinetic energy ranking as the cheap alternative.
  - Candidate-set and constraint handling through the existing
    `workflow/sensors.py::SensorMap` seam (no parallel sensor abstraction).
  - Placement quality report: EI values, condition of `Φ_sensor`, and TAM
    pseudo-orthogonality of the selected set via `correlation/reduction.py`
    (`tam_mass`) — reusing the AC-CORR-009 machinery, not duplicating it.
- **Acceptance links (proposed, module M10 / family `PRE` / spec anchor MS-11):**
  AC-PRE-001 (P2, `property`) — EI invariants: contributions sum to the mode
  count, are shape-scaling invariant, and iterative removal never deletes a
  DOF whose removal makes `Φ_sensor` rank-deficient; AC-PRE-002 (P2, `twin`) —
  on the 36-DOF cantilever twin, the EI-selected set passes the AC-CORR-009
  thresholds (diag ≥ 0.99, off-diag ≤ 0.10) through the TAM where a
  worst-case set of equal size does not.
- **Dependencies:** R2-T03 machinery (done). Independent of R3-T01. Feeds
  headline demo 2 (§4).

### R3-T03 — Industrial scale: sparse end to end, 50k-DOF budget

- **Priority:** 3 · **Gap:** [GAP-13](../docs/SOTA_GAP_ANALYSIS.md) (§4);
  R2-T03 residue (STATUS §4.2) · **Dispatched:** A131 (sparse-aware reduction
  slice)
- **Why third:** the dense threshold sits at 400 DOF, benchmarks stop at
  1k DOF, and `correlation/reduction.py` densifies sparse inputs — 3D meshes
  (R2-T02) and imported models (R2-T05) are exactly what push past that.
  The gap register cites an **AC-PERF-001 50k budget that was never
  registered**; this task owes the registration.
- **Scope, in slices:**
  1. *Sparse-aware reduction* (A131): stop densifying in
     `correlation/reduction.py` — Guyan/IRS/SEREP bases and `tam_mass` operate
     on `scipy.sparse` inputs with sparse factorizations, dense only on the
     reduced (sensor-sized) side. No API change; the dense path stays for
     dense inputs.
  2. *Iterative eigensolver path*: LOBPCG and/or shift-invert Lanczos behind
     the existing `ModalSolver` facade (no second solver entry point — GAP-01
     rule), selected by size/sparsity heuristic with an explicit override.
  3. *Benchmark + budget*: a procedurally generated ≥ 50k-DOF sparse model
     (hex block from `mesh.simple` scales there) solving k modes without any
     densification of the operator, wall-clock enveloped generously enough to
     be CI-stable.
- **Acceptance links (proposed, family `PERF`, cross-cutting module slot after
  M9/M10 land):** AC-PERF-001 (P2, `contract`/`regression`) — 50k-DOF sparse
  modal solve completes with a no-densification tripwire (no `toarray` on the
  full-order operator) and a pinned, loose runtime envelope; AC-PERF-002 (P2,
  `property`) — iterative path agrees with the dense reference on a mid-size
  model to rel. err ≤ 1e-8 in frequencies and MAC ≥ 0.999 in shapes.
  Prefer structural assertions (sparsity preserved, scaling slope) over tight
  wall-clock limits — CI time budgets flake.
- **Dependencies:** slice 1 is independent (A131 already dispatched); slice 2
  independent; slice 3 needs both. Reanalysis acceleration inside updating
  loops is **stretch** (§3), not a gate.

### R3-T04 — Updating depth completion (R2-T06 remainder)

- **Priority:** 4 · **Gap:** [GAP-10](../docs/SOTA_GAP_ANALYSIS.md) residue ·
  **Dispatched:** A132 (QR screen), A136 (MAC-row Jacobian)
- **Why fourth:** carried P1 depth from Round 2 (STATUS §4.1) — three known,
  well-scoped items on existing seams, two already dispatched.
- **Scope, in slices:**
  1. *QR-with-pivoting collinearity screen* (A132): refine the MS-3.6 screen
     in `workflow/selection.py` from the pairwise-cosine heuristic to
     QR-with-pivoting subset selection. **No new AC ID** — strengthen the
     existing [AC-UPD-007](../docs/ACCEPTANCE_CRITERIA.md) gate in place (it
     is `verified`; the promotion machinery re-runs it, so the strengthened
     test must stay green or the row demotes).
  2. *Analytic MAC-row Jacobian* (A136): wire the A04/A10 analytic MAC
     sensitivities into the updater's shape-residual path so the FD fallback
     stops being the default whenever shapes are present.
  3. *Model-level parameter resolver*: `material.<id>.<attr>` /
     `section.<id>.<attr>` targets resolved against the assembled `Model`
     with per-element dK/dp (and dM/dp) providers, replacing the
     `ScalingModel`-only design space for model-spec workflows.
- **Acceptance links:** AC-UPD-007 strengthened in place (slice 1); proposed
  AC-UPD-009 (P2, `property`) — analytic MAC-row Jacobian matches central FD
  to rel. err ≤ 1e-6 on the 10-DOF chain and is the active path when shapes
  are present; proposed AC-UPD-010 (P2, `twin`) — resolver + assembled dK/dp
  recover the AC-UPD-003 stiffness twin end to end from a model-spec target
  string. Spec anchors MS-3.1/3.3/3.6.
- **Dependencies:** slices 1–2 independent of everything (dispatched). Slice 3
  unlocks R3-T05's sensitivities and pairs with the CLI `update` spec schema.

### R3-T05 — FRF updating residual (GAP-05 close-out)

- **Priority:** 5 · **Gap:** [GAP-05](../docs/SOTA_GAP_ANALYSIS.md) residue
  (signoff "FRF updating residual") · **Dispatched:** not yet — first
  undispatched track
- **Why fifth:** the last piece of the FRF chain. Synthesis (R2-T01),
  correlation (FRAC/FDAC), and ingest (UFF-58) all exist; updating still
  minimizes only modal residuals. Industrially this is the FEMtools "FRF
  updating" workflow.
- **Scope:**
  - FRF residual `r(ω_l) = H_synth(ω_l; θ) − H_meas(ω_l)` (real/imag or
    log-magnitude stacking, documented choice) on a frequency-line subset,
    as a residual *provider* in the existing GN/LM loop — the estimator,
    re-pairing, bounds and σ_post plumbing stay shared (GAP-01 rule).
  - Analytic FRF sensitivity `∂H/∂θ = −H (∂K/∂θ + iω ∂C/∂θ − ω² ∂M/∂θ) H`
    through the dK/dp providers (R3-T04 slice 3 for model-level targets;
    `ScalingModel` suffices for the gate fixture).
  - Frequency-line selection guard (off-resonance weighting or damping floor)
    documented as a limitation if deferred.
- **Acceptance links (proposed):** AC-UPD-011 (P2, `twin`) — a perturbed
  10-DOF damped chain recovers stiffness (and one damping) parameter from
  noisy synthesized FRFs; post-update FRAC ≥ 0.99 on held-out lines.
  Spec anchor MS-3.2 extension + MS-7.3.
- **Dependencies:** M6 (done); soft on R3-T04 slice 3 (hard only for
  model-level targets). Should start after A136's Jacobian wiring merges to
  avoid a three-way conflict in `updating/updater.py`.

### R3-T06 — OP2 and native industrial readers (GAP-03 extension)

- **Priority:** 6 · **Gap:** [GAP-03](../docs/SOTA_GAP_ANALYSIS.md) extension
  (signoff, STATUS §4.3) · **Dispatched:** A139 (research spike + `io/op2`
  stub)
- **Scope:**
  - A139's spike decides the read strategy: a `pyNastran`-backed reader behind
    the P7 optional-dependency seam (like meshio — `MissingDependencyError`,
    `[io]` extra grows the dep) vs a native minimal OP2 table parser. The
    plan's default recommendation is **pyNastran behind the seam** — OP2 is a
    versioned binary format and a native parser is not a one-round item.
  - Target tables: geometry (GEOM1/GEOM2 → `NeutralModel` blocks, reusing
    `neutral_to_model`) and real eigenvector output (OUG) → `ModalResult` /
    `TestData`, so an OP2 can serve as either the FE side or the reference
    side of a correlation.
  - Fixture policy per AC §1.4: no committed binaries — write the fixture in
    the test via pyNastran itself or a minimal table formatter in
    `tests/_op2.py` (precedent: `tests/_uff58.py` from R2-T01).
- **Acceptance links (proposed, module M8 extension):** AC-IO-004 (P2,
  `contract`) — OP2 → `NeutralModel` → `neutral_to_model` → `assemble_system`
  matches the hand-built model on a generated fixture; AC-IO-005 (P2,
  `contract`) — OP2 modal output → `correlate_modal_data` against the same
  model's solved modes, MAC diag = 1. Dense-numbering: next free IO IDs.
- **Dependencies:** none. Merges are `io/`-local plus the registry edit.

### R3-T07 — Plotting / visualization helpers (GAP-15)

- **Priority:** 7 · **Gap:** [GAP-15](../docs/SOTA_GAP_ANALYSIS.md) (§4,
  "deferred by design for v1") · **Dispatched:** A135 — **MVP merged**
  (`a6e607b`, 1519 tests): `viz/plotting.py` carries `plot_mac_matrix` and
  `plot_mode_shape` behind `require_matplotlib` and the `[plot]` extra, with
  `tests/test_viz.py` skip-scoped when matplotlib is absent.
- **Remaining scope:**
  - FRF overlay (measured vs synthesized) and — once R3-T01 lands — the
    stabilization diagram over MPE's pole-classification data, both in the
    same `viz/plotting.py` (no second plotting seam).
  - Helpers return the `Figure` and take an `ax=` injection point; CLI wiring
    (`--plot` flags) is stretch, not a gate.
- **Acceptance links (proposed):** AC-VIZ-001 (P2, `contract`) — each helper
  renders to a file under the Agg backend in `tmp_path`, is deterministic in
  structure (axes count, artist count), and the missing-dependency path raises
  per P7. One row suffices; per-plot rows would be inventory noise. The MVP
  merged without a registry row, so this registration is still owed.
- **Dependencies:** none hard; the stabilization plot consumes R3-T01's data
  contract, so that helper lands after A133's spec merges (plot against the
  spec's result shape, not a private one).

### R3-T08 — Round 3 exit hardening and sign-off

- **Priority:** 9 (last) · mirrors R2-T09.
- **Scope:** promote every green Round 3 row via
  `scripts/promote_verified.py --run --apply`; registry consistency and the CI
  `gates` job stay the enforcement mechanism (AC §1.5, §10); reconcile
  `STATUS.md` / `PROGRESS.md` / `PR_DRAFT.md`; branch cleanup per
  `BRANCH_CLEANUP.md` conventions; write `ROUND3_SIGNOFF.md`.
- **Dependencies:** everything above.

---

## 2. Dependency order, parallelization, and merge order

Same ground rule as Round 2 (`SOTA_GAP_ANALYSIS.md` Appendix A): **seam
changes land atomically with their consumers**, and one new constraint that
Round 2's dense-numbering near-miss exposed: **registry-editing merges are
serialized** — module numbers, MS anchors, and the pinned inventory count are
global, so two spec-first scaffolds cannot land in parallel without one
rebasing.

- **Wave 0 — docs (merge first, trivial):** this plan (A130, docs-only).
  A138's PR-readiness checklist, A137's quickstart, and A135's plotting MVP
  **already merged** (`5fe7192`, `44e931c`, `a6e607b`) while this plan was in
  draft.
- **Wave 0.5 — registry serialization queue (one at a time):**
  A133 (M9/MPE spec scaffold) → A134 (M10/PRE spec scaffold) → any `PERF`
  registration from the R3-T03 track → later `AC-UPD-009/010/011`,
  `AC-IO-004/005`, `AC-VIZ-001` registrations as their tracks mature. Each
  entry rebases its module slot and inventory count over the previous one.
- **Wave 1 — parallel code tracks (disjoint files):**
  A131 (`correlation/reduction.py` sparse), A132 (`workflow/selection.py` QR
  screen), A136 (`updating/updater.py` MAC-row Jacobian), A139 (`io/op2.py`
  spike). A132 and A136 are adjacent in the updating stack — textual overlap
  is low but their acceptance edits can collide; merge A132 before A136 (A132
  strengthens an existing gate and is the smaller diff).
- **Wave 2 — consumers:** MPE implementation (after A133's spec), pretest EI
  implementation (after A134's spec), LOBPCG + 50k benchmark (after A131),
  model-level resolver (R3-T04 slice 3, after A132/A136), stabilization plot
  (after MPE's data contract).
- **Wave 3 — close-out:** R3-T05 FRF residual (after the updater seams
  settle), then R3-T08 promotion and sign-off.

Recommended merge order for the still-open dispatched pool, conflict-risk
ranked: **A130 → A133 → A134 → A131 → A132 → A136 → A139** (A135, A137, A138
already landed), with Wave-1 members reorderable freely among themselves
*except* the A132-before-A136 pairing and the rule that whoever registers AC
rows next queues behind A134.

---

## 3. Stretch backlog (tracked, non-gating)

| Item | Gap | Note |
|---|---|---|
| SSI-based OMA | GAP-06 | after LSCF core; differentiation, not parity |
| Sampling UQ (TMCMC/MC), DOE, response surfaces | GAP-11 | MAP landed R2-T04; sampling reuses its residual/prior plumbing |
| Geometric dK/da for shape variables; topology | GAP-12 | optimization backend done for sizing (R2-T07) |
| Reanalysis acceleration in updating loops | GAP-13 | after AC-PERF rows land |
| Craig–Bampton CMS | GAP-08 | deferred from R2-T03 by design |
| Geometry-based nearest-node mapping | GAP-09 | label-based alignment landed R2; geometric mapping still open |
| CLI surfaces: `mpe`, `pretest`, `--plot` flags | GAP-14 | after the library halves gate |

---

## 4. Round 3 exit bar (sketch)

Round 3 is done when, on the integration branch in CI:

1. Every Round 3-registered criterion (the `MPE`, `PRE`, `PERF`, `VIZ`
   families and the new `UPD`/`IO` rows above) is **`verified`** through
   `scripts/promote_verified.py` and the `gates` job — the same enforced
   lifecycle as Round 2 (AC §1.5); any row consciously dropped is *removed or
   re-prioritized in the registry*, not left `specified` (dense-numbering
   rule).
2. AC-UPD-007 remains `verified` after the QR-screen strengthening (a demotion
   is a red flag, not an acceptable outcome).
3. **Headline demos** run end to end:
   - *Measurement loop:* a UFF-58 FRF set → LSCF + stabilization → `TestData`
     → `correlate_modal_data` against the FE model — raw measurement to MAC
     table with no hand-built mode table (closes GAP-06 + GAP-03's test-data
     half).
   - *Pretest:* EI placement on a 3D mesh (R2-T02 elements) whose selected
     sensor set passes TAM pseudo-orthogonality (closes GAP-07 against
     R2-T03's machinery).
   - *Scale:* a ≥ 50k-DOF sparse model solves k modes within the AC-PERF
     envelope with the no-densification tripwire green (closes GAP-13's
     budget claim).
   - *FRF updating:* a damped twin recovers its perturbation from FRF
     residuals with post-update FRAC ≥ 0.99 (closes GAP-05).
4. Full suite + Ruff + registry consistency green; **no duplicate numeric
   kernels** — MPE, pretest, and viz consume `correlation/`, `solver/`, and
   `workflow/sensors.py` seams rather than reimplementing them (GAP-01 stays
   closed).
5. `STATUS.md`, `PROGRESS.md`, `PR_DRAFT.md` reconciled and `ROUND3_SIGNOFF.md`
   written with the measured numbers.
