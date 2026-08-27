# v1.0.0-beta Release Signoff — Final Round C (fable)

- **Date:** 2026-08-27
- **Signed off by:** fable (claude-fable-5), Final Round C release-signoff slot
- **Tree under signoff:** consolidated v1.0.0-beta mainline
  `cursor/audio-studio-v0.1.0-alpha-b3cf` at merge `478014f`
  (PR #17, "v1.0.0-beta: Round A+B consolidation") **plus** the Round C
  conflict-marker repair carried on `cursor/v1.0-final-tag-b3cf`
- **Version metadata:** `pyproject.toml` and `audio_studio.__version__` both
  read `1.0.0-beta`; development-status classifier is Beta
- **Companion documents:** `FINAL_RELEASE_SUMMARY.md` (positioning and gap
  register) and `sota-audit-report.md` (Round B P0/P1 scorecard), both beside
  this file

## Verdicts

| Claim | Verdict |
|---|---|
| v1.0.0-beta as a **professional workstation beta** (source tag) | **Conditional Go** |
| v1.0.0-beta as an **Audition-class ("SOTA") release** | **No-Go** |

### Conditional Go — v1.0.0-beta professional workstation

The beta is what its documents say it is: a professional single-track
waveform editor and analyzer with a repair/mastering toolset, a VST3 host
MVP and a multitrack MVP, verified by 1624 green application tests and a
certified BS.1770-4 metering chain. The Go is conditional on:

1. **Tag from a repaired HEAD.** The consolidation merge `478014f` is
   **red in CI**: PR #17 shipped unresolved merge-conflict markers in
   `tests/acceptance/test_sota_checklist.py`, which fail test collection
   (IndentationError) on all three platforms. `cursor/v1.0-final-tag-b3cf`
   removes them (a 12-line deletion keeping the mainline verifier) and Audio
   CI is **green** on that branch. The v1.0.0-beta tag must point at a
   commit that includes this repair — tagging `478014f` itself would tag a
   HEAD that cannot even collect its acceptance suite.
2. **Honest positioning in the release notes.** The tag must be announced as
   a professional workstation beta linking
   `.agent_workspace/v1.0/FINAL_RELEASE_SUMMARY.md`, not as Adobe Audition
   parity and not as SOTA-accepted. The acceptance suite still reports
   `sota_claimed: false` by design.
3. **Source tag only.** The PyInstaller bundle scaffold exists but no built,
   signed or notarized artifact may be published with this tag; any future
   installer must first satisfy the `THIRD_PARTY_LICENSES.md` release
   checklist (LGPL relinking, GPL exclusion, notices in the bundle).

### No-Go — Audition-class claim

The Round 1 audit (`.agent_workspace/round1/fable-sota-audit.md` §7) set the
acceptance rule: **all P0 items pass, at most two P1 degradations**. The
final state is P0 **8/20**, P1 **0/10** — 8 of 30 checklist items hard-pass.
Twelve P0 items remain open, most blocked on hardware or formal evidence
artifacts (callback-p99 timing, 30/60-minute device soaks, 4 GB RF64 RSS,
60 fps frame-time report) and two on real feature gaps (VHQ SRC, true-peak
limiter ISP evidence). The rule is far from met; no Audition-class or SOTA
claim may accompany the tag.

## Final test evidence (Round C, measured on this tree)

| Suite | Result |
|---|---|
| Application suite (`audio-studio/tests`) | **1624 passed**, 13 skipped (Windows-only WASAPI-exclusive paths, optional-dependency cases) |
| Full tree (application + repo compliance/acceptance + benchmark gates) | **1723 passed**, 13 skipped, 22 xfailed |
| SOTA acceptance checklist (`tests/acceptance/test_sota_checklist.py`) | **9 passed / 22 expected gaps / 0 XPASS** — 8 of 30 items hard-pass (the ninth pytest pass is the structural count test) |
| Audio CI | red on mainline `478014f` (conflict markers); **green on `cursor/v1.0-final-tag-b3cf`** with the repair |

The task brief's shorthand "1624+ app, 9/30 SOTA passes" corresponds to the
first and third rows: 1624 application tests, and 9 pytest passes over the
30-item checklist (which score as 8 of 30 items because one pass is the
structural count test; per item-level scoring the split is P0 8/20, P1 0/10).

## Gaps closed against the Round 1 audit

The Round 1 audit graded the tree **100% greenfield** (a README and a
progress file; zero implementation code) and named ten SOTA gaps G1–G10.
Trajectory of the 30-item checklist since: alpha Round 3 — 7 items
evidenced / 23 expected gaps; Round B re-grade — 8 of 30 items, with A1-TP
and E3 newly promoted to hard passes.

| Round 1 gap | Status at v1.0.0-beta |
|---|---|
| G1 — realtime engine (lock-free callback, async streaming) | **Closed at MVP level.** Lock-free SPSC ring with zero-allocation `read_into`, feeder-thread effect rack, 256-frame default block, first-playback GC freeze; the allocation-free render callback is enforced by test. Hardware p99/soak evidence still missing (C1–C3 open). |
| G2 — non-destructive editing core | **Closed.** Copy-on-write `EditSession` with unlimited undo (B4 passes at 100 steps), sparse `StreamingEditSession` for over-budget RF64/W64 files; the source file is never rewritten in place. |
| G3 — BS.1770/R128 metering chain | **Closed.** The product meter passes EBU Tech 3341 loudness ±0.1 LU, all seven Tech 3341 true-peak vectors within +0.2/−0.4 dB, and Tech 3342 LRA ±1 LU, in CI (A1-LUFS, A1-TP, A2 pass). |
| G4 — spectral view and STFT editing | **Substantially closed.** Calibrated STFT spectrogram plus rectangular spectral selection attenuate/delete with bit-exact undo; no lasso/brush/heal, so B5 stays half-open. |
| G5 — high-quality SRC and dither | **Half closed.** TPDF dither ships by default on PCM-16/24 export (A7 open only on the spectrum evidence report); the SciPy SRC path misses the VHQ mastering gates and the staged soxr path is not yet selected (A5 open). |
| G6 — professional effects with precision verification | **Substantially closed.** Parametric EQ deviates <0.05 dB from the analytic response (A4 passes); compressor, true-peak limiter, gate, delay and FDN reverb landed with streaming/offline equivalence tests; the limiter's formal ISP-vector evidence is missing (A6 open). |
| G7 — VST3/AU plugin host | **Half closed.** Three-slot VST3 host behind the GPL-isolated `plugins` extra, crash-safe pedalboard-free scanner, per-slot state blobs, preview-path PDC; no AU, no plugin editor windows, no validator evidence (B6 open). |
| G8 — cross-platform audio backend abstraction | **Substantially closed.** sounddevice/PortAudio preferred backend with WASAPI shared + opt-in exclusive, opt-in ASIO host selection (no SDK bundled), PyAudio and null fallbacks; recording input remains PyAudio-only. |
| G9 — professional UI (dock/HiDPI/60fps/a11y) | **Half closed.** Dockable panels, dark theme default, fractional HiDPI pass-through, full shortcut coverage with a generated F1 sheet, WCAG 2.2 AA contrast enforced from the live palette by test. Still 30 Hz (not 60 fps), no dock-layout persistence, custom widgets not screen-reader readable (D1–D4 open). |
| G10 — verification infrastructure | **Closed** (the audit's own first priority). EBU 3341/3342 vector synthesis in CI, bit-exact null tests, golden files, the three-platform Audio CI (E1 passes), and the 30-item executable checklist with machine-readable reporting. The AES17 harness is the one missing measurement tool (A8 open). |

Of the Round 1 risk register, R2 (licensing) is closed —
`THIRD_PARTY_LICENSES.md` passes E3, pedalboard is GPL-isolated behind an
extra, the ASIO SDK is not shipped, and the bundle scaffold refuses GPL
components; R3 (realtime not retrofittable) and R4 ("demo-grade DSP") were
addressed by building the callback discipline and measurement gates early.
R5's prediction held: spectral editing stayed within its minimal scope.

## Remaining gaps

The authoritative register is `FINAL_RELEASE_SUMMARY.md` §4 (ten accepted
P1-class gaps, all disclosed in the README limitations). Headlines:
incomplete compliance evidence (no AES17, most formal evidence artifacts
ungenerated), VHQ SRC not integrated, multitrack and recording are MVPs,
custom widgets are screen-reader-opaque, no hardware certification, and no
published installer.

## Doc-drift fixes made in this round

Business logic was not touched. This round changed:

1. `tests/acceptance/test_sota_checklist.py` — removed the unresolved merge
   conflict markers PR #17 shipped (kept the mainline verifier; this is the
   repair CI validates as green on this branch).
2. `CHANGELOG.md` — folded the misplaced "Unreleased" section (`.hlprojz`
   archives, desktop bundle scaffold) into the 1.0.0-beta entry where those
   merges actually landed, and added the ASIO host selection and JSON edit
   macros the entry omitted.
3. `.agent_workspace/v1.0/FINAL_RELEASE_SUMMARY.md` — final Round C test
   counts, corrected merge count (eleven PR merges since the alpha), the
   full Round B wave contents, the CI red/green state, and the
   distribution-gap wording (scaffold landed, nothing published).
4. `audio-studio/README.md` — release-notes highlights now mention the
   `.hlprojz` archives, bundle scaffold, ASIO selection and edit macros the
   body already documents.

## Handoff to the orchestrator

Merge `cursor/v1.0-final-tag-b3cf` into
`cursor/audio-studio-v0.1.0-alpha-b3cf`, confirm Audio CI is green on the
merge commit, and tag that commit `v1.0.0-beta`. The tag annotation should
link `FINAL_RELEASE_SUMMARY.md` and use the §1 positioning language.
