# Superseded Branch Cleanup

Audit date: 2026-08-26  
Initial integration snapshot audited and tested: `cursor/femtools-industrial-7aa3` at `8604807`

These remote branches no longer carry work that should be merged. Delete them after
review; no GitHub pull request (open or closed) is associated with any of the eight.
All eight were deleted from `origin` on 2026-08-26.

| Branch | Deleted remote tip | Relationship to trunk | Deletion status |
|---|---|---|---|
| `cursor/r1o2-correlation-updating-e393` | `f1452f8` | Not an ancestor by design. A14 reconciled its useful behavior through `cursor/reconcile-r1o2-correlation-updating-64c5`; that reconciliation tip (`5762f2d`) is on trunk. The original branch still has three branch-only commits because trunk retained its stricter null-mode MAC contract and avoided restoring a parallel correlation/updating implementation. | **Deleted from `origin` as superseded. Do not merge.** |
| `cursor/merge-quad4-backfill-4595` | `d3498b4` | The remote tip is an ancestor of trunk and has zero branch-only commits. Its QUAD4 backfill and later integration merges are already present. | **Deleted from `origin` as fully merged.** |
| `cursor/dynamics-damping-frf-9500` | `f4683d6` | The remote tip is an ancestor of trunk and has zero branch-only commits. The dynamics/FRF implementation entered the integration history through merge `acda625`. | **Deleted from `origin` as fully merged.** |
| `cursor/optimization-scipy-backend-f421` | `069d37a` | The functional tip (`8b46480`) entered trunk through harvest merge `6cf0f49`. The five branch-only commits at deletion are two base merges and three progress-only commits; the active-set KKT and trust-constr Hessian fixes are on trunk and summarized in A40's progress record. | **Deleted from `origin` as superseded.** |
| `cursor/optimization-acceptance-gates-2414` | `00572d8` | The remote tip is an ancestor of trunk and has zero branch-only commits. Its strengthened AC-OPT-002/003 gates and documentation entered trunk through A52's merge. | **Deleted from `origin` as fully merged.** |
| `cursor/ac-corr-009-tam-orthogonality-113b` | `927f164` | The remote tip is an ancestor of integration tip `9052f95` and has zero branch-only commits. Its AC-CORR-009 registration and `SensorMap.signs` wiring are already integrated. | **Deleted from `origin` as fully merged.** |
| `cursor/hex8-brick-ac-elem-d0b7` | `226728b` | The remote tip is an ancestor of integration tip `441f80a` and has zero branch-only commits. Its HEX8 implementation and AC-ELEM-001..003 acceptance slice entered the integration history through merge `8a0f10f`. | **Deleted from `origin` as fully merged.** |
| `cursor/beam3d-cbar-element-c9a7` | `c5433f7` | The remote tip is an ancestor of trunk and has zero branch-only commits. Its `BeamElement3D` formulation, `MeshBuilder.add_beam3d` seam and 42-test suite entered the integration history through merge `75dd070`, verified at that merge as **1089 passed, 0 failed** with `ruff check .` clean. | **Deleted from `origin` as fully merged.** |

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

The A86 follow-up verified the seventh branch before deletion:

```text
git merge-base --is-ancestor 226728b 441f80a
yes

git rev-list --left-right --count 441f80a...226728b
28  0
```

The A93 follow-up merged and then verified the eighth branch before deletion. Unlike
the others it was still *unmerged* when the audit ran, so A93 merged it into the
integration branch first and confirmed the ancestry afterwards:

```text
git merge-base --is-ancestor origin/cursor/beam3d-cbar-element-c9a7 \
                             origin/cursor/femtools-industrial-7aa3
yes

git rev-list --left-right --count 75dd070...c5433f7
2  0
```

> [!WARNING]
> `cursor/hex8-solid-element-d0b7` **MUST NOT be merged**. It is superseded by the
> integrated `cursor/hex8-brick-ac-elem-d0b7` work and is contaminated with
> unrelated AC-MODAL-008 commits. Its remote ref is retained only pending explicit
> team agreement that deletion is safe; retention does not make it merge-eligible.

The full committed trunk suite passed for the initial five-branch snapshot:
**876 passed, 0 failed** in 29.26 seconds.

After deletion, `git ls-remote --heads origin` returned no ref for any branch in
this table.

## A56 registry closure — two more branches to retire

The A56 run produced two remote branches, only one of which should be merged. Both
were audited at trunk `4668ff6`, the merge that closed the acceptance registry at
44/44 (**1168 passed, 0 failed**, `ruff check .` clean, collection confirming the
same 1168).

| Branch | Remote tip | Relationship to trunk | Recommendation |
|---|---|---|---|
| `cursor/ac-backfill-a56-r2-02bf` | `89c93a5` | Ancestor of trunk with zero branch-only commits. Its MS-1.2 frequency-window feature, the AC-MODAL-008/UPD-008/WORK-003 suites and the non-finite JSON fix entered the integration history through merge `8bc2ec4`. | **Deleted from `origin` as fully merged.** |
| `cursor/ac-backfill-a56-02bf` | `03757fe` | Not an ancestor; four branch-only commits. This is the same run's first attempt, based on `7faaf23` and finished against a trunk 60 commits further on. Its `modal.py`, `test_modal.py` and `test_workflow.py` are byte-identical to trunk; its M3 gates are covered by the reviewed trunk suites, and its independent AC-CORR-008 implementation is superseded by `1e99970` plus the fix now on trunk. | **Deleted from `origin` as superseded. Do not merge.** |

```text
git merge-base --is-ancestor origin/cursor/ac-backfill-a56-r2-02bf \
                             origin/cursor/femtools-industrial-7aa3
yes
git rev-list --left-right --count origin/cursor/femtools-industrial-7aa3...origin/cursor/ac-backfill-a56-r2-02bf
42  0

git merge-base --is-ancestor origin/cursor/ac-backfill-a56-02bf \
                             origin/cursor/femtools-industrial-7aa3
no
git rev-list --left-right --count origin/cursor/femtools-industrial-7aa3...origin/cursor/ac-backfill-a56-02bf
146  4
```

The fully merged R2 branch was deleted from `origin` on 2026-08-26 after its
`89c93a5` tip was reverified against trunk. The first-attempt tip `03757fe` was
reverified against integration tip `0449651`: one branch-only commit is
patch-identical to integrated commit `6475d6e`; its modal and workflow artifacts
match byte-for-byte, while its M3 and correlation alternatives are superseded by
the reviewed implementations on trunk. It was deleted from `origin` on 2026-08-26,
and `git ls-remote --heads origin` confirmed that the remote ref is absent.

> [!NOTE]
> The warning above about `cursor/hex8-solid-element-d0b7` being "contaminated with
> unrelated AC-MODAL-008 commits" no longer describes work at risk of being lost.
> AC-MODAL-008 was rebuilt against the reviewed trunk and landed in `8bc2ec4`, so
> that branch holds nothing unique and the warning stands unchanged: do not merge it.

## A116 backfill — R2-T09 verified promotion retired

The R2-T09 promotion branch was verified against integration tip `a3e6375` before
deletion. Its tip `b7b526b` is an ancestor with zero branch-only commits:

```text
git merge-base --is-ancestor origin/cursor/r2-t09-verified-promotion-c554 a3e6375
yes

git rev-list --left-right --count a3e6375...origin/cursor/r2-t09-verified-promotion-c554
3  0
```

`cursor/r2-t09-verified-promotion-c554` was deleted locally and from `origin` on
2026-08-26. A subsequent `git ls-remote --heads origin` confirmed that the remote
ref is absent.

## A104 backfill — the shell facet branch retired

The R2-T02 shell slice needed no merge of its own: A98 merged the integration tip into
`cursor/shell-quad4-facet-1c70` and pushed the result, so the branch tip `9ad7a6b` sits
on the trunk's **first-parent** line rather than arriving through a side merge. Verified
against integration tip `571c864`:

```text
git merge-base --is-ancestor origin/cursor/shell-quad4-facet-1c70 571c864
yes

git rev-list --left-right --count 571c864...origin/cursor/shell-quad4-facet-1c70
3  0
```

The full suite at `571c864` was **1331 passed, 0 failed, 0 skipped** in 27.06 s with
`ruff check .` clean (Python 3.12.3 / NumPy 2.5.2 / SciPy 1.18.1); the shell module
itself contributes 72 of those. `cursor/shell-quad4-facet-1c70` was deleted locally and
from `origin` on 2026-08-26, and `git ls-remote --heads origin` confirmed the remote ref
is absent.

| Branch | Deleted remote tip | Relationship to trunk | Deletion status |
|---|---|---|---|
| `cursor/shell-quad4-facet-1c70` | `9ad7a6b` | First-parent ancestor of trunk with zero branch-only commits. `ShellQuad4Element`, the `shell_plate_mesh` / `MeshBuilder.add_shell_quad4` seams and the 72-case `tests/test_shell_quad4.py` are all integrated. | **Deleted from `origin` as fully merged.** |

> [!NOTE]
> `cursor/merge-shell-quad4-facet-6224` was opened in parallel to land the same shell
> code while A98's branch was still in flight. A114 landed its branch-only documentation
> (`3accf8b`, `319c50e`) onto the integration branch, after which the branch tip matched
> trunk with zero unique commits. It was deleted from `origin` on 2026-08-26.

## A109 backfill — R2-T09 promotion tool retired

The promotion branch tip is an ancestor of integration tip `319c50e` with zero
branch-only commits; its `scripts/promote_verified.py` tool and five-criterion promotion
landed through merges at `571c864`. `cursor/r2-t09-promote-verified-bb5f` was deleted
from `origin` on 2026-08-26 after reverification.
