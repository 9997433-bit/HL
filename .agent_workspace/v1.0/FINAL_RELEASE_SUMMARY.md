# Audio Studio v1.0.0-beta — Final Release Summary

Date: 2026-08-27
Branch: `cursor/v1.0-round-b-b3cf` (release preparation, Round B)
Baseline: alpha mainline at merge `e230762` (v1.0 Round A) plus this branch.
Prepared by: fable (release-preparation slot).

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
  submix buses and a summing mixer — a skeleton, not a production mixing
  console.

What it is not: a multitrack production environment with automation lanes
and a mixer console, a certified low-latency monitoring system, a
broadcast-compliance-certified mastering chain, or a packaged desktop
application. Those are the remaining gaps in §4.

## 2. Delivered since v0.1.0-alpha

Eight PR merges landed between the alpha changelog entry and this branch.
Full detail is in `CHANGELOG.md` (sections 0.2.0, 0.3.0, 1.0.0-beta);
capability summary:

| Wave | Merged PRs | Capabilities |
|---|---|---|
| v0.2 workstation | workstation; dynamics; continuation (v0.2 part); telemetry; multitrack bus | Recording MVP → crash-safe BWF; markers/regions; batch CLI; compressor/limiter/gate/delay/reverb; loudness match; sounddevice backend; triple-buffered telemetry; peak `.pk` cache; feeder-thread preview; fader ramp; interpolated playhead; submix buses |
| v0.3 VST3/repair/scale | continuation (v0.3 part); VST3 panel + GC + RF64; VST3 scanner + streaming edit + WASAPI | VST3 dock, scanner and three-slot rack (GPL-isolated extra); spectral selection attenuate/delete; RF64/W64 streaming with memory budget; sparse streaming edit session; 256-frame block + RT GC discipline; WASAPI exclusive opt-in |
| v1.0 Round A | PDC, soak, NR, a11y, dither, DeClip | Plugin delay compensation + state blobs; spectral noise reduction; DeClip; TPDF dither + SRC quality report; take registry; WCAG 2.2 AA contrast, fractional HiDPI, full shortcut coverage; render-callback allocation cleanup; 30-minute headless soak harness |
| v1.0 Round B (this branch) | release preparation | Version 1.0.0-beta, changelog, this summary, README release notes |

Against the Round 3 acceptance checklist recorded at the alpha
(`.agent_workspace/round3/fable-sota-final-acceptance.md`, P0: 4 pass /
6 partial / 10 fail; P1: 0 pass / 2 partial / 8 fail), the waves above
closed or materially advanced most of the hard failures: the true-peak
limiter (A6), TPDF dither (A7), batch processing (B7), spectral repair
tools (B5), VST3 hosting with PDC (B6), RF64 streaming (B3), a recording
path (C2's functional prerequisite), callback allocation discipline (C3),
keyboard workflow (D3), UI scaling (D5) and HiDPI (part of D1). The
checklist itself has not been re-run and re-graded against this HEAD; that
re-grade is the first post-beta acceptance task, and no "checklist passed"
claim should be derived from this table.

## 3. Verification state

- The alpha carried a green three-platform CI (Linux full suite,
  macOS/Windows smoke, GUI smoke, performance probes) at `c908a7e`, and
  every subsequent wave was merged through the same Audio CI workflow.
- The SOTA acceptance suite still reports `sota_claimed: false` by design.
- Performance evidence remains **headless proxy** evidence: the realtime
  SLO probe, the accelerated 30-minute soak
  (`.agent_workspace/soak/soak-30min-accelerated.json`) and the benchmark
  deltas were produced on cloud vCPUs without a physical audio device.
- This release-preparation branch changed version metadata and
  documentation only; Ruff was run on the edited Python file. The full test
  suite was not re-run on this branch per the release-preparation
  instructions — the beta tag must be cut from a HEAD with a green CI run.

## 4. Remaining P1 gaps

These are the known, accepted gaps shipping inside v1.0.0-beta. Each one is
disclosed in the README limitations; none is silently claimed as done.

1. **Compliance matrix incomplete.** The product meter is certified against
   EBU 3341/3342 cases 1–3 only; cases 4–9 (gating stress, absolute/relative
   gate) and the 3341 true-peak vectors are not synthesized, and there is no
   AES17 THD+N harness (`tools/aes17.py` does not exist). No broadcast
   compliance certification may be claimed.
2. **Mastering SRC not closed.** The measured SciPy resampling path misses
   the offline VHQ gates (mirror suppression / THD+N); the `mastering` extra
   stages soxr but the application does not yet select it. Final masters
   should preserve the source sample rate.
3. **Multitrack is an MVP.** Buses, clip envelopes and mute/solo exist, but
   there are no automation lanes, clip crossfades, comping or mixer console
   view, and no 32-track real-time playback evidence on hardware.
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
10. **No distribution artifacts.** No installer, code signing or
    notarization, and no per-platform SBOM/license bundle; the release is a
    source tag. `THIRD_PARTY_LICENSES.md` defines the obligations an
    installer must satisfy before one is shipped.

## 5. Release verdict

**Go for v1.0.0-beta as a source-tag beta**, with the positioning in §1 and
the gap register in §4 reproduced in the release notes. Preconditions for
cutting the tag:

1. A green Audio CI run on the final HEAD (this branch merged).
2. Release notes link to this document — the beta must not be announced as
   Audition parity or as SOTA-accepted.

Post-beta priorities, in order: re-run and re-grade the 30-item acceptance
checklist against beta HEAD; complete the EBU/AES vector matrix; integrate
the soxr VHQ SRC path; hardware RTT + soak certification on all three
platforms; multitrack automation and mixer console; installer + SBOM.
