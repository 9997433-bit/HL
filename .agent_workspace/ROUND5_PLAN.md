# Round 5 — SOTA parity

**Branch:** `cursor/round5-sota-parity-7aa3`  
**Goal:** expose the SSI-COV integration seam and add a bounded modal benchmark
to the CI acceptance gates.

| Task | Status | Notes |
|---|---|---|
| SSI-COV API | done | `openfemlab.mpe.ssi_cov` documents the output-only time-history contract and fails explicitly until a numerical backend lands. |
| MPE registration | done | Exported from `openfemlab.mpe`. |
| CI benchmark gate | done | `scripts/bench_ci_gate.py` runs sizes 100 and 500 once, with a 20 s budget and 30 s hard timeout; the `gates` job invokes it. |
| AC-PERF-004 / AC-IO-004 registry review | not applicable | No tests tagged with either ID exist in this branch or the linked agent worktrees, so the requested registration condition was not met. |
| Verification | done | Ruff passed; the benchmark gate finished in 0.92 s; full pytest: 1708 passed, 3 skipped. |
