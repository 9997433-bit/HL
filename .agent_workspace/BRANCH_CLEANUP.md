# Superseded Branch Cleanup

Audit date: 2026-08-26  
Initial integration snapshot audited and tested: `cursor/femtools-industrial-7aa3` at `8604807`

These remote branches no longer carry work that should be merged. Delete them after
review; no GitHub pull request (open or closed) is associated with any of the six.
All six were deleted from `origin` on 2026-08-26.

| Branch | Deleted remote tip | Relationship to trunk | Deletion status |
|---|---|---|---|
| `cursor/r1o2-correlation-updating-e393` | `f1452f8` | Not an ancestor by design. A14 reconciled its useful behavior through `cursor/reconcile-r1o2-correlation-updating-64c5`; that reconciliation tip (`5762f2d`) is on trunk. The original branch still has three branch-only commits because trunk retained its stricter null-mode MAC contract and avoided restoring a parallel correlation/updating implementation. | **Deleted from `origin` as superseded. Do not merge.** |
| `cursor/merge-quad4-backfill-4595` | `d3498b4` | The remote tip is an ancestor of trunk and has zero branch-only commits. Its QUAD4 backfill and later integration merges are already present. | **Deleted from `origin` as fully merged.** |
| `cursor/dynamics-damping-frf-9500` | `f4683d6` | The remote tip is an ancestor of trunk and has zero branch-only commits. The dynamics/FRF implementation entered the integration history through merge `acda625`. | **Deleted from `origin` as fully merged.** |
| `cursor/optimization-scipy-backend-f421` | `069d37a` | The functional tip (`8b46480`) entered trunk through harvest merge `6cf0f49`. The five branch-only commits at deletion are two base merges and three progress-only commits; the active-set KKT and trust-constr Hessian fixes are on trunk and summarized in A40's progress record. | **Deleted from `origin` as superseded.** |
| `cursor/optimization-acceptance-gates-2414` | `00572d8` | The remote tip is an ancestor of trunk and has zero branch-only commits. Its strengthened AC-OPT-002/003 gates and documentation entered trunk through A52's merge. | **Deleted from `origin` as fully merged.** |
| `cursor/ac-corr-009-tam-orthogonality-113b` | `927f164` | The remote tip is an ancestor of integration tip `9052f95` and has zero branch-only commits. Its AC-CORR-009 registration and `SensorMap.signs` wiring are already integrated. | **Deleted from `origin` as fully merged.** |

Verification for the original five used the fetched remote tips, not potentially stale
local branch pointers:

```text
git merge-base --is-ancestor origin/<branch> 8604807
r1o2-correlation-updating: no (expected; reconciled rather than merged)
merge-quad4-backfill:       yes
dynamics-damping-frf:       yes
optimization-scipy-backend: no (expected; functional tip was harvested)
optimization-acceptance:    yes

git rev-list --left-right --count 8604807...origin/<branch>
r1o2-correlation-updating: 203  3
merge-quad4-backfill:        7  0
dynamics-damping-frf:      136  0
optimization-scipy-backend: 89  5
optimization-acceptance:    81  0
```

The A81 follow-up verified the sixth branch before deletion:

```text
git merge-base --is-ancestor origin/cursor/ac-corr-009-tam-orthogonality-113b 9052f95
yes

git rev-list --left-right --count 9052f95...origin/cursor/ac-corr-009-tam-orthogonality-113b
12  0
```

The full committed trunk suite passed for the initial five-branch snapshot:
**876 passed, 0 failed** in 29.26 seconds.

After deletion, `git ls-remote --heads origin` returned no ref for any branch in
this table.
