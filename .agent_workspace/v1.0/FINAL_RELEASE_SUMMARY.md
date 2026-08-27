# Audio Studio v1.1.0 — Product Release Summary

Date: 2026-08-27
Branch: `cursor/v1.0-round-g-b3cf` merged to alpha
Tag: `v1.1.0`

## 1. Positioning

**v1.1.0 is the first product release with a distributable build.** A `v*` tag
now produces a downloadable Linux bundle straight from CI — the PyInstaller
one-directory bundle built by `scripts/build-linux.sh`, uploaded as the
`audio-studio-linux-x64` artifact with a software bill of materials, on top of
the 30/30 SOTA checklist closed at v1.0.1. Full signoff:
`.agent_workspace/v1.1/fable-v1.1-product-signoff.md`.

## 2. Round G deliverables

- **Linux release workflow** (`.github/workflows/release-linux.yml`): builds
  the bundle on every `v*` tag push (and manual dispatch), runs the LGPL
  replaceability and GPL-exclusion gates from `scripts/build-linux.sh`, and
  uploads the `audio-studio-linux-x64` CI artifact. Contract-tested by
  `tests/test_release_workflow.py`.
- **AppImage and deb built for real** (`scripts/package-appimage.sh`,
  `scripts/package-deb.sh`): `audio-studio-1.1.0-x86_64.AppImage` smoke-run,
  `audio-studio_1.1.0-1_amd64.deb` installed/run/purged on Ubuntu 24.04 —
  hashes and transcripts in `../v1.1/linux-packaging-evidence.md`.
- **SBOM** (`tools/generate_sbom.py`, `packaging/DISTRIBUTION.md`): CycloneDX
  1.5 bundle SBOM (151 components), SPDX-shaped build-environment SBOM and a
  pass-status build report, policy-checked by `tests/test_sbom.py`.
- **Signing scaffold** (`scripts/sign-linux-artifact.sh`): `SHA256SUMS` plus
  optional GPG detached signatures; today's artifacts are recorded
  `signed: false` — checksums, no production key.

## 3. Honest gaps

- **No macOS or Windows installers.** Both platforms remain source installs
  (`pip install`) verified by CI smoke lanes only.
- **No Apple or Microsoft code signing.** No Developer ID signing or
  notarization on macOS, no Authenticode on Windows; no certificates are
  provisioned. The signing scaffold covers integrity, not platform trust —
  Gatekeeper and SmartScreen will warn.
- The Linux artifacts are x86_64 only and unsigned; the AppImage/deb were
  built locally (CI publishes the raw bundle), nothing is attached to a
  GitHub Release, and there is no reproducible-build attestation.

---

_Previous v1.0.1 summary below._

# Audio Studio v1.0.1 — SOTA Complete Release Summary (archived header)

Date: 2026-08-27
Branch: `cursor/v1.0-round-f-b3cf` merged to alpha
Tag: `v1.0.1-sota`

## 1. Positioning

**v1.0.1 closes the SOTA acceptance checklist: 30/30 items pass**, 0 expected gaps.
This is **not** Adobe Audition feature parity — see `fable-v1-sota-signoff.md`.

## 2. Test evidence (Round F)

| Suite | Result |
|---|---|
| Application | **1721 passed**, 12 skipped |
| SOTA acceptance | **31 passed**, 0 xfailed |

## 3. Round F highlights

Dense RF64 formal probe, 60-minute PortAudio recording, PulseAudio loopback
latency (8.17 ms worst), live Orca/AT-SPI walkthrough.

---

_Previous v1.0.0 summary below._

# Audio Studio v1.0.0 — Final Release Summary (archived header)

Date: 2026-08-27
Branch: `cursor/v1.0-round-e-b3cf` merged to alpha
Tag: `v1.0.0`

## 1. Positioning

**v1.0.0 is the formal professional audio workstation release**, not Adobe
Audition parity. SOTA checklist: **27/30 items pass**, **4 expected hardware
gaps** (formal RF64, recording soak, loopback RTT, live screen reader).

## 2. Test evidence (Round E)

| Suite | Result |
|---|---|
| Application | **1713 passed**, 13 skipped |
| SOTA acceptance | **27 passed**, 4 xfailed |
| Full tree | ~1850 passed |

## 3. Round E highlights

AES17 report, one-hour file perf, 32-track evidence, cross-platform golden,
crash auto-recovery, 60 fps UI probe + scroll fixes, accessible-name proxy.

## 4. Remaining for Audition-class

B3, C2, C4, D4 — see `fable-v1-formal-signoff.md`.

---

_Previous RC summary below remains valid for historical context._

# Audio Studio v1.0.0-rc — Final Release Summary (archived header)

# Audio Studio v1.0.0-beta — Final Release Summary (archived header)
Branch: `cursor/v1.0-final-tag-b3cf` (Round C release signoff; final counts
added to the Round B draft prepared on `cursor/v1.0-round-b-b3cf`)
Baseline: consolidated v1.0.0-beta mainline at merge `478014f` (v1.0
Round A + Round B, PR #17) plus the Round C conflict-marker repair in
`tests/acceptance/test_sota_checklist.py`.
Prepared by: fable (release-preparation slot; Round C final signoff in
`fable-v1-beta-signoff.md` beside this file).

## 1. Positioning — read this first

**v1.0.0-beta is a professional audio workstation beta, not Adobe Audition
parity.** The version number marks the completion of the three post-alpha
delivery waves the alpha sign-off planned (v0.2 workstation → v0.3
VST3/repair → v1.0 SOTA alignment), all merged and documented. It does not
mark passage of the Round 1 SOTA acceptance rule (all P0 pass + at most two
P1 degradations); that claim has never been made by any acceptance report in
this repository and is not made now.

What the beta honestly is:

- A **professional single-track waveform editor and analyzer**: streaming or
  in-memory playback over a lock-free SPSC ring at a 256-frame default
  block, copy-on-write editing with unlimited undo, spectral selection
  editing, `.hlproj` project bundles, markers/regions, recording takes, and
  batch processing.
- A **repair and mastering toolset**: De-Hum, De-Click, De-Clip, spectral
  noise reduction, compressor, true-peak limiter, gate, delay, FDN reverb,
  parametric EQ, LUFS loudness match, TPDF export dither, and a BS.1770-4
  meter certified against EBU 3341/3342 cases 1–3.
- A **plugin host MVP**: three VST3 slots behind the GPL-isolated optional
  `plugins` extra, with a crash-safe scanner, per-slot state persistence and
  preview-path plugin delay compensation.
- A **multitrack MVP**: track lanes, clips with envelopes, mute/solo,
  submix buses, per-track gain-automation lanes and a summing mixer — a
  skeleton, not a production mixing console.

What it is not: a multitrack production environment with automation lanes
and a mixer console, a certified low-latency monitoring system, a
broadcast-compliance-certified mastering chain, or a packaged desktop
application. Those are the remaining gaps in §4.

## 2. Delivered since v0.1.0-alpha

Eleven PR merges landed between the alpha changelog entry and the
consolidated v1.0.0-beta mainline. Full detail is in `CHANGELOG.md`
(sections 0.2.0, 0.3.0, 1.0.0-beta); capability summary:

| Wave | Merged PRs | Capabilities |
|---|---|---|
| v0.2 workstation | workstation; dynamics; continuation (v0.2 part); telemetry; multitrack bus | Recording MVP → crash-safe BWF; markers/regions; batch CLI; compressor/limiter/gate/delay/reverb; loudness match; sounddevice backend; triple-buffered telemetry; peak `.pk` cache; feeder-thread preview; fader ramp; interpolated playhead; submix buses |
| v0.3 VST3/repair/scale | continuation (v0.3 part); VST3 panel + GC + RF64; VST3 scanner + streaming edit + WASAPI | VST3 dock, scanner and three-slot rack (GPL-isolated extra); spectral selection attenuate/delete; RF64/W64 streaming with memory budget; sparse streaming edit session; 256-frame block + RT GC discipline; WASAPI exclusive opt-in |
| v1.0 Round A | PDC, soak, NR, a11y, dither, DeClip | Plugin delay compensation + state blobs; spectral noise reduction; DeClip; TPDF dither + SRC quality report; take registry; WCAG 2.2 AA contrast, fractional HiDPI, full shortcut coverage; render-callback allocation cleanup; 30-minute headless soak harness; Tech 3341 true-peak vectors |
| v1.0 Round B | automation; TP certification; SOTA audit + ASIO + macros; hlprojz archive + installer; consolidation | Per-track gain-automation lanes persisted in `.hlproj`; product true-peak certification against the Tech 3341 vectors; acceptance-suite re-grade (A1-TP and E3 promoted to hard passes); opt-in ASIO host selection (no SDK bundled); reusable JSON edit macros in the batch CLI; single-file `.hlprojz` project archives; PyInstaller desktop-bundle scaffold with the LGPL relinking notices wired into the build; version 1.0.0-beta, changelog, this summary, README release notes |

Against the Round 3 acceptance checklist recorded at the alpha
(`.agent_workspace/round3/fable-sota-final-acceptance.md`, P0: 4 pass /
6 partial / 10 fail; P1: 0 pass / 2 partial / 8 fail), the waves above
closed or materially advanced most of the hard failures: the true-peak
limiter (A6), TPDF dither (A7), batch processing (B7), spectral repair
tools (B5), VST3 hosting with PDC (B6), RF64 streaming (B3), a recording
path (C2's functional prerequisite), callback allocation discipline (C3),
keyboard workflow (D3), UI scaling (D5) and HiDPI (part of D1).

The Round B audit re-ran and re-graded the acceptance suite against the
Round A merge (`.agent_workspace/v1.0/sota-audit-report.md`, merged from
the Round B audit branch): 9 passed / 22 expected gaps / 0 XPASS, meaning
**8 of 30 checklist items hard-pass (P0 8/20, P1 0/10)**, with A1-TP and
E3 newly promoted. Several verifiers still under-credit landed features
because they probe evidence artifacts or module paths that do not exist —
the true-peak limiter, the batch loudness CLI and spectral selection
editing are all shipped, but their items stay open pending evidence
reports. Even granting those halves, the Round 1 acceptance rule (all P0
pass + at most two P1 degradations) is far from met, which is exactly why
this release is a beta and not a SOTA claim.

## 3. Verification state

- The alpha carried a green three-platform CI (Linux full suite,
  macOS/Windows smoke, GUI smoke, performance probes) at `c908a7e`, and
  every subsequent wave was merged through the same Audio CI workflow.
- The SOTA acceptance suite still reports `sota_claimed: false` by design;
  the Round B re-grade stands at 9 passed / 22 expected gaps (8 of 30 items
  hard-pass).
- Performance evidence remains **headless proxy** evidence: the realtime
  SLO probe, the accelerated 30-minute soak
  (`.agent_workspace/soak/soak-30min-accelerated.json`) and the benchmark
  deltas were produced on cloud vCPUs without a physical audio device.
- **Final counts (Round C, on the consolidated HEAD plus the
  conflict-marker repair):** the application suite passes **1624 tests**
  (13 skipped: Windows-only WASAPI-exclusive paths and optional-dependency
  cases); the full tree — application, repository compliance/acceptance and
  benchmark gates together — stands at **1723 passed / 13 skipped /
  22 xfailed**; the SOTA acceptance suite reports **9 passed / 22 expected
  gaps / 0 XPASS** (8 of 30 checklist items hard-pass; the ninth pytest pass
  is the structural count test).
- The consolidation merge itself (`478014f`) briefly broke CI: unresolved
  merge-conflict markers in `tests/acceptance/test_sota_checklist.py`
  failed test collection on every platform. Round C removed them (a
  12-line deletion keeping the mainline verifier) on
  `cursor/v1.0-final-tag-b3cf`, where Audio CI is green. The v1.0.0-beta
  tag must be cut from a HEAD that includes this repair.

## 4. Remaining P1 gaps

These are the known, accepted gaps shipping inside v1.0.0-beta. Each one is
disclosed in the README limitations; none is silently claimed as done.

1. **Compliance evidence incomplete.** The synthetic EBU matrix now passes
   in CI — Tech 3341 cases 1–7 plus channel-weighting vectors and all seven
   true-peak vectors, Tech 3342 cases 1–3 — but there is no AES17 THD+N
   harness (`tools/aes17.py` does not exist), no real-material EBU vectors,
   and most formal evidence artifacts the acceptance suite expects (TPDF
   spectrum, callback timing, 4 GB RF64 RSS, and the rest of the audit's
   missing-reports list) have not been generated. No broadcast compliance
   certification may be claimed.
2. **Mastering SRC not closed.** The measured SciPy resampling path misses
   the offline VHQ gates (mirror suppression / THD+N); the `mastering` extra
   stages soxr but the application does not yet select it. Final masters
   should preserve the source sample rate.
3. **Multitrack is an MVP.** Buses, clip envelopes, mute/solo and per-track
   gain-automation lanes exist, but automation covers track gain only — no
   multi-parameter automation, clip crossfades or comping — there is no
   mixer console view, and no 32-track real-time playback evidence on
   hardware.
4. **Recording is an MVP.** No input-device selection or level control, no
   live monitoring, no punch or loop recording; input always runs on PyAudio
   regardless of the selected output backend.
5. **Screen readers cannot read the custom widgets.** The waveform,
   spectrogram and level meter expose no accessible value or text
   alternative; there is no high-contrast/light theme and no reduced-motion
   setting. (Contrast, keyboard reach and scaling *are* enforced by test.)
6. **Spectral editing is rectangular.** No lasso, brush or healing tool and
   no spectral copy/paste; the mask is a feathered rectangle in time ×
   frequency.
7. **Plugin hosting boundaries.** VST3 only, through the GPL-3.0 pedalboard
   opt-in extra — no AU, no plugin editor windows, and no MIT-licensed
   direct VST3 SDK host. PDC covers the preview chain only: the playhead
   readout is not shifted and mid-stream padding changes re-prime with
   silence.
8. **No hardware certification.** No physical-device round-trip latency
   measurement, no real-device 30/60-minute playback/recording soak (the
   headless harness is a proxy), and xrun counts are not surfaced in the UI.
9. **Project persistence limits.** Undo history is not saved in `.hlproj`
   (the saved document is flattened), there is no crash auto-recovery for
   edit sessions (recording is crash-safe; projects are not), and dock
   layout / workspace presets are not persisted across restarts.
10. **No published distribution artifacts.** A PyInstaller one-directory
    bundle scaffold landed (`packaging/pyinstaller.spec`,
    `scripts/build-linux.sh`, LGPL relinking notices, GPL exclusion), but no
    built, signed or notarized installer is published and there is no
    per-platform SBOM; the release is a source tag. `THIRD_PARTY_LICENSES.md`
    defines the obligations an installer must satisfy before one is shipped.

## 5. Release verdict

**Go for v1.0.0-beta as a source-tag beta**, with the positioning in §1 and
the gap register in §4 reproduced in the release notes. Preconditions for
cutting the tag:

1. A green Audio CI run on the final HEAD (this branch merged).
2. Release notes link to this document — the beta must not be announced as
   Audition parity or as SOTA-accepted.

Post-beta priorities, in order: generate the missing acceptance evidence
reports (the audit's "Evidence reports still missing" list) and realign the
remaining under-crediting verifiers; complete the AES17 and real-material
EBU matrix; integrate the soxr VHQ SRC path; hardware RTT + soak
certification on all three platforms; multi-parameter automation and a
mixer console; installer + SBOM.
