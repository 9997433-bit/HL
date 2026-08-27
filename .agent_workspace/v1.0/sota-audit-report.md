# SOTA Acceptance Checklist Audit — v1.0 Round B

- **Date:** 2026-08-27
- **Audited tree:** `cursor/audio-studio-v0.1.0-alpha-b3cf` at `e230762` (Merge v1.0 Round A: PDC, soak, NR, a11y, dither, DeClip)
- **Suite:** `tests/acceptance/test_sota_checklist.py` (30 independently reported items + 1 structural count test)

## Result summary

| | Passed | XFailed | XPassed |
|---|---|---|---|
| Before Round B audit | 7 | 23 | 1 (E3) |
| **After Round B audit** | **9** | **22** | **0** |

Checklist items passing: **8 of 30** (before: 6 of 30; the pytest "passed" totals above
include the structural count test).

## Changes made in this round

1. **A1-TP promoted to a hard pass.** `TECH_3341_TRUE_PEAK_VECTORS` landed in
   `tools/ebu_vectors.py` in Round A, but the verifier still used the pre-landing
   hypothetical API (`vector.samples`, single fixed-rate meter). The verifier now
   synthesizes each vector with `synthesize_true_peak` and meters at the vector's own
   sample rate. All 7 vectors measure within the +0.2/-0.4 dB window (worst error
   +0.116 dB on the quarter-rate 45°-phase vectors).
2. **E3 promoted from XPASS to a hard pass.** `THIRD_PARTY_LICENSES.md` exists at the
   repository root and covers PySide6, NumPy, SciPy, and libsndfile; the stale xfail
   marker was removed.
3. **Verifiers realigned with the code that actually landed** (items remain xfail, but
   the passing halves are now asserted against real module paths):
   - B5: DeClick/DeHum are asserted in `audio_studio.dsp.repair` (landed); the item
     stays open on missing spectral selection editing.
   - B8: `MultitrackSession` is asserted in `audio_studio.core.session` (landed, not
     the previously hypothesized `core/multitrack.py`); the item stays open on the
     missing 32-track evidence report.
   - D2: the real workspace names (`"waveform"`/`"multitrack"`) are asserted (landed);
     the item stays open on missing `saveState()`/`restoreState()` dock-layout
     persistence.
4. **Tightened `expected_gap` strings** for A5, A7, B3, B5, B6, B8, C1, D2, and D4 so
   each xfail reason names only what is still missing (see scorecards below).

## P0 scorecard (8 / 20 pass)

| Item | Title | Status | Remaining gap |
|---|---|---|---|
| A1-LUFS | EBU Tech 3341 loudness ±0.1 LU | PASS | — |
| A1-TP | EBU Tech 3341 true peak +0.2/-0.4 dB | **PASS (new)** | — |
| A2 | EBU Tech 3342 LRA ±1 LU | PASS | — |
| A3 | WAV 16/24/32f null round-trip | PASS | — |
| A4 | Parametric EQ response <0.05 dB | PASS | — |
| A5 | VHQ SRC stopband and THD+N | XFAIL | `resample()` has no quality parameter and the SRC report misses the stopband/THD+N mastering thresholds (measured -31.2 dBFS stopband vs -120 required; -88.6 dBFS THD+N vs -130 required) |
| A6 | True-peak limiter ISP ceiling | XFAIL | no true-peak limiter is implemented |
| B1 | M1-M13 demonstrated with evidence | XFAIL | no complete M1-M13 evidence manifest exists |
| B2 | One-hour file performance | XFAIL | only shortened headless performance proxies exist |
| B3 | 4GB RF64 streaming under 1GB RSS | XFAIL | RF64/W64 decode support landed; 4GB streaming under-1GB-RSS evidence is missing |
| B4 | 100-step undo/redo | PASS | — |
| C1 | 48k/256 30-minute playback stability | XFAIL | only an accelerated headless soak exists (`.agent_workspace/soak/soak-30min-accelerated.json`); hardware 30-minute playback evidence is missing |
| C2 | 60-minute recording stability | XFAIL | hardware recording stability evidence is missing |
| C3 | Callback p99 and realtime discipline | XFAIL | zero-alloc callback fixed; formal callback-p99 timing evidence is missing |
| D1 | 60fps, HiDPI, and dark default | XFAIL | UI timer is 30Hz (`UI_REFRESH_MS = 33`) and no frame-time/HiDPI report exists |
| D2 | Dock presets and layout persistence | XFAIL | waveform/multitrack workspaces landed; dock-layout saveState/restoreState persistence is missing |
| D3 | Keyboard-only end-to-end workflow | XFAIL | no keyboard-only workflow evidence exists |
| E1 | Three-platform CI gates | PASS | — |
| E2 | Cross-platform DSP golden consistency | XFAIL | no three-platform golden comparison artifact exists |
| E3 | Third-party license inventory | **PASS (was XPASS)** | — |

## P1 scorecard (0 / 10 pass)

| Item | Title | Status | Remaining gap |
|---|---|---|---|
| A7 | TPDF dither spectrum | XFAIL | `quantize_with_tpdf` landed; the TPDF spectrum evidence report is missing |
| A8 | AES17 THD+N report | XFAIL | AES17 measurement tool and report are missing |
| B5 | Spectral edit, DeClick, and DeHum | XFAIL | DeClick/DeHum landed in `dsp.repair`; spectral selection editing is missing |
| B6 | VST3/AU host, state, and PDC | XFAIL | plugin host package landed (`plugins/host.py`, `scanner.py`, `adapter.py`, `pedalboard_bridge.py`); VST3 compatibility/state/PDC evidence is missing |
| B7 | 10-file -16 LUFS FLAC batch | XFAIL | batch loudness workflow is missing |
| B8 | 32-track playback and automation | XFAIL | `MultitrackSession` landed; 32-track playback/automation evidence is missing |
| C4 | Hardware round-trip latency under 15 ms | XFAIL | hardware loopback evidence is missing |
| D4 | WCAG AA, color-safe map, screen reader | XFAIL | palette and colormap checks pass (a headless a11y suite also landed in `audio-studio/tests/test_accessibility.py`); screen-reader evidence is missing |
| D5 | UI scaling from 100% to 200% | XFAIL | multi-scale UI evidence is missing |
| E4 | Crash auto-recovery | XFAIL | crash recovery implementation/evidence is missing |

## Partial-progress notes

Implementation halves that landed in Round A but whose items stay open pending evidence
or a remaining feature half:

- **A5:** `.agent_workspace/round3/src-quality-report.json` now exists but reports
  `status: fail` against the mastering thresholds; the SciPy `resample_poly` backend
  needs the optional soxr/VHQ path plus a `quality` parameter on `loader.resample`.
- **A7:** `loader.quantize_with_tpdf` is implemented and unit-tested
  (`tests/test_dither.py`); only `.agent_workspace/round3/tpdf-spectrum-report.json`
  is missing.
- **B3:** the loader decodes RF64/W64 containers; the 4GB / <1GB-RSS streaming report
  is missing.
- **C1:** an accelerated soak artifact exists; the formal
  `playback-stability-report.json` is missing.
- **C3:** the audio callback is allocation-free (meter reductions moved to the feeder
  thread; enforced by `audio-studio/tests/test_render_discipline.py`); only the formal
  callback-p99 hardware timing report is missing.

## Evidence reports still missing under `.agent_workspace/round3/`

`tpdf-spectrum-report.json`, `aes17-report.json` (+ `tools/aes17.py`),
`must-have-evidence.json`, `file-performance-report.json`,
`rf64-streaming-report.json`, `plugin-host-report.json`,
`batch-loudness-report.json` (+ `core/batch.py`), `multitrack-report.json`,
`playback-stability-report.json`, `recording-stability-report.json`,
`callback-timing-report.json`, `roundtrip-latency-report.json`,
`ui-frame-time-report.json`, `keyboard-workflow-report.json`,
`accessibility-report.json`, `ui-scaling-report.json`,
`cross-platform-golden.json`, `crash-recovery-report.json`.
