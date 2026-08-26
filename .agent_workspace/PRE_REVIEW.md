# Pre-Review Checklist — PR #5 (OpenFEMLab)

**Author:** A100 (backfill for completed A83) · **Date:** 2026-08-26
**Branch:** `cursor/femtools-industrial-7aa3` ·
**Pull request:** [PR #5](https://github.com/9997433-bit/HL/pull/5) (open against `main`)

Final consolidation before human review: what is verified, what the reviewer
should know, and which items are deliberately still open. A100 synchronized the
current-tip figures below to the detached-worktree verification at `c92729a`
with `PYTHONPATH=src` on Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1.

---

## 1. Test suite

- [x] **The 876-test trunk snapshot is independently confirmed.** At `d696bcb`
  (the snapshot STATUS.md and the recent verification entries describe):
  **876 passed, 0 failed.** This is the fourth independent confirmation of that
  figure — A62 measured it at `8604807`, A67 at `e1a4cc8`, A55 at `0928f95`,
  and this run at `d696bcb`.
- [x] **The current PR head is green too.** The branch on GitHub moved past the
  876 snapshot while this checklist was being prepared; re-verified twice as
  it moved: **921 passed** at `9052f95` (the AC-UPD-004/005 batch (A50),
  AC-CORR-009 with the `SensorMap.signs` reduction wiring (A58), and the
  MS-3.4 divergence guard with typed stop reasons), then **1033 passed,
  0 failed** at the `5641d75` HEX8 merge tip — the trilinear brick landed
  with `tests/test_hex8.py` (76 tests) and the AC-ELEM-001..003 acceptance
  slice while this file was first being pushed.
- [x] **The reconciled trunk is green.** The local trunk carried a parallel
  line (A57: AC-UPD-006a/b registration, Laplace σ_post in the
  `CorrectionReport`) that this run merged with the HEX8 line; on the merged
  tree: **1045 passed, 0 failed** in 56.37 s.
- [x] **Latest check at the pushed tip** (`c92729a`, including the 42-test
  `BeamElement3D`, 44-test meshio bridge, and final 35 registry-closure tests):
  **1168 passed, 0 failed** in 58.50 s.
- [x] No skips, xfails-as-passes, or flaky reruns observed in any run.

## 2. Lint

- [x] `ruff check .` — **clean at every verification point** (`d696bcb`,
  `9052f95`, the `5641d75` HEX8 merge tip, the reconciled merge, and `c92729a`).
- [x] CI (`ci.yml`, Python 3.10–3.13 matrix) runs both pytest and Ruff.

## 3. PR #5 state

- [x] Open against `main`, head `cursor/femtools-industrial-7aa3`,
  227+ commits; the verified 876 snapshot is an ancestor of the PR head, so
  nothing verified here is off-branch.
- [ ] **Title is stale** — it still says "430 tests". Refresh title and body
  from [`PR_DRAFT.md`](PR_DRAFT.md) before review; the draft is now pinned at
  the latest 1168-test tip.
- [x] Reviewer-facing docs are in place: `PR_DRAFT.md` (body + FEMtools
  comparison table), [`STATUS.md`](STATUS.md) (module table, registry census),
  [`BRANCH_CLEANUP.md`](BRANCH_CLEANUP.md) (side-branch audit; superseded
  branches deleted from origin, R2-T08 closed).

## 4. Round 1 — COMPLETE

- [x] Concluded at `bae4b77` (192 tests; Round Conclusions section of
  [`PROGRESS.md`](PROGRESS.md)).
- [x] Both carry-over packages (`workflow/`, `optimization/`) landed; the
  dynamics/optimization integration merged at `acda625`, closing the round at
  430 tests. The suite has since grown to 1168 with no Round 1 regressions.
- [x] No open Round 1 items remain.

## 5. Round 2 — IN PROGRESS

Live state per task (backlog in [`ROUND2_PLAN.md`](ROUND2_PLAN.md), updated for
the A50/A58 landings):

| Task | Status | Open items handed to review context |
|---|---|---|
| R2-T01 dynamics/FRF | **Done** | — (engine, AC-DYN-001..005, schema-1.1 FRF report block, `correlate-frf` CLI all landed) |
| R2-T02 3D elements | **Partial** | QUAD4, TET4, HEX8, and the 42-test `BeamElement3D` batch have landed with AC-ELEM-001..003 implemented; remaining: shell facet and solid/shell BDF cards |
| R2-T03 reduction/TAM | **Done at gate level** | AC-CORR-006 and AC-CORR-009 registered and implemented; `SensorMap.signs` folded into the bases (A58). Residual: reduction densifies sparse inputs (a GAP-13-scale concern, not a correctness one) |
| R2-T04 Bayesian MAP | **Acceptance-complete** | Estimator + posterior landed (36 tests); AC-UPD-006a/b are registered and `implemented`, with Laplace σ_post in the `CorrectionReport` (A57, merged by A83). The remaining CLI `update` document work is outside the acceptance slice. |
| R2-T05 meshio/IO | **Partial** | The meshio bridge landed with 44 tests; UNV 2411/2412, UFF writing, and AC-IO-001..003 registration remain. |
| R2-T06 updating depth | **Partial** | MS-3.4 divergence guard landed this window; remaining: QR-pivot refinement of the collinearity screen, analytic MAC-row Jacobian in the shape-residual path, model-level parameter resolver |
| R2-T07 optimization | **Done** | Shape variables still fall back to finite differences (documented) |
| R2-T08 branch reconciliation | **Done** | — (audited and cleaned, see `BRANCH_CLEANUP.md`) |
| R2-T09 CI hardening | **Partial** | Pytest and Ruff run in CI; no `implemented → verified` promotion mechanism has been applied |

## 6. Acceptance-criteria registry (measured at the PR head)

- [x] **44 criteria: 44 `implemented`, 0 `specified`, 0 `verified`**
  (re-measured at `c92729a`): all **34/34 P0** and **10/10 P1** rows are
  `implemented`.
- [ ] The Round-2 exit bar requires every P0+P1 criterion `verified`; the
  promotion step (a CI run at a pinned tip) is R2-T09 scope and has not been
  defined yet. Reviewers should read `implemented` as "tagged acceptance test
  passing locally and in CI", not as sign-off.

## 7. Reviewer notes

- [x] `.agent_workspace/` is orchestration documentation (progress log, plans,
  this checklist) — not runtime code, not packaged.
- [x] Known limitations are pinned by tests rather than hidden: TET4's bending
  lock (+207 % at 108 DOF, asserted), QUAD4's missing drilling-DOF shell
  facet, the optimization backend's FD fallback for shape variables.
- [x] Verification hygiene: the shared `/workspace` checkout is mutated by
  concurrent agents (nine+ recorded incidents, including mid-command ref moves
  observed by this run). Reproduce any number in this file from a **private
  clone with `PYTHONPATH` pinned** — A67 hit cross-worktree import
  contamination when unpinned.

## Bottom line

Suite green at the current `c92729a` tip (**1168 passed**) with all P0 and P1
criteria implemented; the registry stands at **44 total: 44 implemented,
0 specified, 0 verified**. Round 1 is closed; the T02/T05 remainders and
registry promotion are known, tracked, and disclosed. The only pre-review
action left is refreshing the PR #5 title/body from `PR_DRAFT.md`.
