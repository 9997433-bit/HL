# Superseded Branch Cleanup

Audit date: 2026-08-26  
Integration branch audited: `cursor/femtools-industrial-7aa3` at `7cc1120`

These remote branches no longer carry work that should be merged. Delete them after
review; no GitHub pull request (open or closed) is associated with any of the three.

| Branch | Remote tip | Relationship to trunk | Disposition |
|---|---|---|---|
| `cursor/r1o2-correlation-updating-e393` | `f1452f8` | Not an ancestor by design. A14 reconciled its useful behavior through `cursor/reconcile-r1o2-correlation-updating-64c5`; that reconciliation tip (`5762f2d`) is on trunk. The original branch still has three branch-only commits because trunk retained its stricter null-mode MAC contract and avoided restoring a parallel correlation/updating implementation. | **Close/delete as superseded. Do not merge.** |
| `cursor/merge-quad4-backfill-4595` | `d3498b4` | The remote tip is an ancestor of trunk and has zero branch-only commits. Its QUAD4 backfill and later integration merges are already present. | **Close/delete as fully merged.** |
| `cursor/dynamics-damping-frf-9500` | `f4683d6` | The remote tip is an ancestor of trunk and has zero branch-only commits. The dynamics/FRF implementation entered the integration history through merge `acda625`. | **Close/delete as fully merged.** |

Verification used the fetched remote tips, not potentially stale local branch pointers:

```text
git merge-base --is-ancestor origin/<branch> HEAD
r1o2-correlation-updating: no (expected; reconciled rather than merged)
merge-quad4-backfill:       yes
dynamics-damping-frf:       yes

git rev-list --left-right --count HEAD...origin/<branch>
r1o2-correlation-updating: 200  3
merge-quad4-backfill:        4  0
dynamics-damping-frf:      133  0
```
