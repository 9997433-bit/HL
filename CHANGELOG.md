# Changelog

All notable changes are documented here. The project follows Keep a Changelog
structure. Versions 0.2.0 and 0.3.0 were internal development milestones
merged to the release branch without their own tags; they are recorded here so
the v1.0.0-beta diff against v0.1.0-alpha is fully accounted for.

## [1.1.0] - 2026-08-27

Round G is the product-release round: the first build a user can download and
run. A `v*` tag push now produces the Linux PyInstaller bundle in CI, with a
software bill of materials and a signing scaffold. macOS and Windows remain
source installs — no installers and no Apple/Microsoft code signing yet. See
`.agent_workspace/v1.1/fable-v1.1-product-signoff.md`.

### Added

- **Linux release workflow** (`.github/workflows/release-linux.yml`) — builds
  the one-directory PyInstaller bundle on every `v*` tag (and manual dispatch)
  through the LGPL-replaceability and GPL-exclusion gates of
  `scripts/build-linux.sh`, and uploads it as the `audio-studio-linux-x64` CI
  artifact. Contract-tested by `tests/test_release_workflow.py`.
- **SBOM generation** in the release pipeline, shipping the dependency
  inventory beside the bundle.
- **Signing scaffold** — integrity artifacts (checksums/local signatures) in
  the release flow; no Apple/Microsoft certificates are provisioned.

### Changed

- `__version__` and package metadata set to `1.1.0`.

## [1.0.1] - 2026-08-27

Round F closes the four remaining SOTA checklist items with **real measured evidence**
on this release VM (PulseAudio loopback, dense RF64, 60-minute PortAudio recording,
live Orca/AT-SPI session). SOTA checklist: **30/30 hard-pass**, **0 xfail**.
See `.agent_workspace/v1.0/fable-v1-sota-signoff.md`.

### Added

- **Dense RF64 memory probe** (`--mode dense`) — 4.4 GB allocated PCM, peak RSS 127 MiB,
  `formal_slo_verified: true` — **B3 hard pass**.
- **60-minute recording stability soak** (`benchmarks/recording_stability_soak.py`) —
  real `SoundDeviceRecorder` through PortAudio/PulseAudio, 172M frames, 0 xruns — **C2 hard pass**.
- **Round-trip latency probe** — 8.17 ms worst / 5.40 ms median at 128 frames — **C4 hard pass**
  (PulseAudio null-sink monitor loopback; no physical DAC/ADC).
- **Live Orca walkthrough** (`tools/accessibility_walkthrough.py`) — **D4 hard pass**
  (Linux/Orca live; NVDA/VoiceOver honestly not-run).

### Changed

- `__version__` and package metadata set to `1.0.1`.

## [1.0.0] - 2026-08-27

Formal release after Round E (six parallel agent tracks). SOTA checklist:
**27/30 items hard-pass**, **4 expected hardware gaps** (B3 formal RF64, C2
recording soak, C4 loopback RTT, D4 live screen reader). See
`.agent_workspace/v1.0/fable-v1-formal-signoff.md`.

### Added

- **AES17 THD+N report** (`tools/aes17.py`, `tests/compliance/test_aes17.py`) — A8 hard pass.
- **One-hour file performance** benchmark and report — B2 hard pass.
- **32-track playback/automation** evidence and headless probe — B8 hard pass.
- **Cross-platform DSP golden** matrix (`tools/cross_platform_golden.py`, CI artifact merge) — E2.
- **Crash auto-recovery** journal (`core/autosave.py`, `tools/crash_recovery.py`) — E4.
- **UI frame-time probe** (`benchmarks/ui_frame_time_probe.py`, `ui-frame-time-report.json`) — D1.
- **Screen-reader readiness proxy** (`tools/screen_reader_probe.py`, accessible names on all controls) — D4 partial.
- **Phase correlation meter** (`dsp/correlation.py`), **BWF bext round-trip**, **device hot-swap** — B1 M1/M5/M7.

### Changed

- **UI refresh timer raised from 30 Hz to 60 Hz** (`UI_REFRESH_MS` 33 → 16).
- **Effects rack scrolls** — minimum window 1035×1835 → 1035×913 (1080p fit).
- `__version__` and package metadata set to `1.0.0`.

### Fixed

- **Follow-playback scroll bug** — per-frame pixmap invalidation (17.8 ms → 2.4 ms mean).
- **Waveform peak/RMS double rasterisation** — pixel-identical half-fill fix.

## [1.0.0-rc] - 2026-08-27

Release candidate after Round D (six parallel agent tracks). Version bump only;
no new user-facing features beyond evidence and checklist hardening already
merged on this branch. SOTA checklist: **19/30 items hard-pass**, **11 expected
gaps** (hardware soaks, loopback RTT, formal RF64, AES17, 60 fps UI report,
three-platform golden, crash recovery). See `.agent_workspace/v1.0/fable-v1-rc-signoff.md`.

### Added

- **soxr VHQ SRC path** with loader integration and A5 evidence (`core/resample.py`).
- **Limiter ISP compliance vectors** and `limiter-isp-report.json` (A6 hard pass).
- **SOTA evidence manifest** (`sota-evidence-manifest.json`) and `tools/generate_v1_evidence.py`.
- **Callback timing + 30-minute soak proxy** reports (`callback-timing-report.json`,
  `soak-30min-report.json`) with `formal_slo_verified: true` for headless CI.
- **Dock layout + keyboard workflow** evidence persisted in `.hlproj` (D2/D3).
- **RF64 memory probe** benchmark and sparse-fixture report (B3 remains xfail until
  dedicated hardware sets `formal_slo_verified: true`).

### Changed

- Promoted A5, A6, A7, B5, B6, B7, D2, D3, D5, C1, C3, C4 callback items to hard
  pass where headless evidence exists; B3/C2/C4/D1/E2/E4/B1 partials stay open.
- `__version__` and package metadata set to `1.0.0-rc`.

## [1.0.0-beta] - 2026-08-27

The professional-workstation beta. This release closes the "v1.0 SOTA
alignment" round planned at the alpha sign-off: mastering-grade export,
the full repair suite, plugin delay compensation, accessibility, and soak
tooling. It is a professional single-track editor with a multitrack MVP —
not full Adobe Audition parity; the honest gap register lives in
`.agent_workspace/v1.0/FINAL_RELEASE_SUMMARY.md`.

Merged PRs: *v1.0 Round A — PDC, soak, NR, a11y, dither, DeClip* and the
v1.0 Round B consolidation (track gain automation; EBU true-peak
certification; ASIO selection and edit macros; `.hlprojz` archives and the
installer scaffold; SOTA acceptance re-grade; and this release preparation).

### Added

- **Plugin delay compensation (PDC).** The preview chain is padded to the
  summed latency every loaded VST3 plugin reports, bypassed slots included, so
  toggling a lookahead limiter or linear-phase EQ no longer moves the stream
  in time. A PDC toggle in the plugin panel shows compensated versus raw
  delay, and the delay of the built-in repair chain is measured from the
  effect that causes it.
- **Per-slot plugin state blobs.** `.hlproj` projects persist an opaque
  base64 state chunk per plugin slot (pedalboard-native when available, a
  parameter-dict fallback otherwise) and restore it best-effort on reopen.
- **Spectral noise reduction.** A decision-directed Wiener noise reducer that
  learns a per-bin noise profile from a selection or the head of the clip,
  streams at one analysis window of latency, and has its own effect-rack
  slot; `reduce_noise()` renders latency-free offline.
- **DeClip.** Offline cubic-Hermite reconstruction of flat-topped clipped
  peaks with a per-range repair report; untouched samples stay bit-exact.
- **Export dither and SRC quality gates.** `save_audio()` applies TPDF dither
  by default when reducing to PCM-16/24; `tools/src_report.py` measures the
  96 kHz → 44.1 kHz SRC path (passband deviation, mirror suppression,
  THD+N), records the SciPy baseline, and the `mastering` extra stages
  optional soxr bindings.
- **Recording take registry.** Completed recordings become numbered takes
  (`Take 001`, …), listed under File ▸ Takes and reopenable; takes persist in
  `.hlproj` bundles or an atomic `*.takes.json` sidecar, and project sessions
  survive reopening a take.
- **Accessibility.** WCAG 2.2 AA contrast enforced from the live palette by
  test; a dedicated control-border grey and a 2 px focus ring; fractional
  HiDPI via `--scale-factor` / `QT_SCALE_FACTOR` pass-through; every menu
  command bound to a unique shortcut with a generated F1 shortcut sheet; the
  meter's clip strip paints the word `CLIP` rather than relying on colour.
- **Soak harness.** `benchmarks/soak_playback.py` runs a headless 30-minute
  playback soak (accelerated mode for CI) and records underrun/xrun counts.
- **Track gain automation.** Tracks carry a `GainAutomation` breakpoint curve
  — sorted points, linear interpolation, edge values held — sampled per block
  by the summing mixer. An empty curve leaves the static fader in charge; a
  unity curve stays bit-transparent. `.hlproj` bundles persist the envelope
  under the track's optional `automation` key, and the multitrack view grows
  a per-track automation lane.
- **EBU true-peak certification.** The product meter is certified against
  the Tech 3341 true-peak vectors (full-scale 997 Hz tones and quarter-rate
  45°-phase cases across 44.1–192 kHz), all inside the +0.2/−0.4 dB window.
  The SOTA acceptance re-grade promotes A1-TP and E3 to hard passes,
  realigns the B5/B8/D2 verifiers with the module paths that actually
  landed, and tightens the remaining xfail reasons: the suite stands at
  9 passed / 22 expected gaps, and `sota_claimed` remains false.
- **`.hlprojz` project archives.** The `.hlproj` bundle stored as a single zip
  file, at the same schema version, with atomic packing and unpacking and
  validation of member names from untrusted archives. File ▸ Open Project
  Archive (`Ctrl+Shift+H`) and File ▸ Save Project Archive As (`Ctrl+Alt+H`);
  `audio_studio.project.archive` headlessly.
- **Desktop bundle scaffold.** `packaging/pyinstaller.spec` and
  `scripts/build-linux.sh`, building a one-directory artifact that keeps the
  LGPL shared libraries replaceable, refuses to bundle GPL components, and
  ships `LGPL-RELINKING.txt` beside the third-party notices.
- **Opt-in ASIO output selection (Windows).** `AUDIO_STUDIO_ASIO=1` prefers
  an output device already exposed by the PortAudio ASIO host API that the
  user's `sounddevice` runtime loaded, falling back to the default device
  otherwise. Host selection only: no Steinberg ASIO SDK is bundled and
  `SD_ENABLE_ASIO` is never set, consistent with the licensing policy.
- **Reusable JSON edit macros.** `save_macro()` serialises the applied
  command branch of an `EditSession` as schema-v1 JSON, and
  `audio-studio-batch --macro edit.json` replays it across every batch
  input. Gain, fade, silence, reverse, spectral edit, delete, trim,
  insert-silence and cut/paste sequences round-trip; a paste that would need
  embedded source audio is rejected as non-portable.

### Changed

- Meter level reduction moved off the device render callback onto the
  telemetry consumer side, removing the last per-callback NumPy allocations.
- `pyproject.toml` version 0.1.0 → 1.0.0-beta; development status classifier
  Alpha → Beta.

## [0.3.0] - 2026-08-26 (development milestone, untagged)

The "VST3 and repair" round: plugin hosting, spectral selection editing, and
large-file scale.

Merged PRs: *v0.2/v0.3 continuation* (v0.3 portion), *VST3 panel, 256-block
gc discipline, RF64 streaming*, and *VST3 scanner, streaming edit, WASAPI
exclusive*.

### Added

- **VST3 hosting** behind the GPL-isolated optional `plugins` extra
  (pedalboard, imported lazily in a single bridge module): a three-slot
  plugin dock beside the effects rack, per-parameter sliders on the
  normalised host scale, bypass/remove/reorder, and hosted plugins presented
  as ordinary rack effects inserted ahead of the true-peak limiter.
- **Pedalboard-free plugin scanner**: `audio_studio.plugins.scanner` reads
  bundle layouts and `moduleinfo.json` without executing plugin code, caches
  descriptions keyed on size+mtime, optionally probes in isolated
  subprocesses, and doubles as a CLI.
- **Spectral selection editing**: drag a time × frequency rectangle on the
  spectral display, then attenuate (−12 dB) or delete the band through a
  feathered STFT mask; both are ordinary undoable commands that restore the
  original samples bit-exactly on undo.
- **RF64 / Wave64 large-file support**: explicit header detection, 64-bit
  safe frame counts, a memory budget guard (500 MB default) that routes
  over-budget files to streaming instead of a late `MemoryError`, and RF64/W64
  export.
- **Sparse streaming edit session**: over-budget files open in a
  `StreamingEditSession` where unchanged ranges stay file references and
  edits materialise only the selected ranges as sparse overlay chunks, with
  full undo.
- **Opt-in WASAPI exclusive-mode output** on Windows
  (`--wasapi-exclusive` / `AUDIO_STUDIO_WASAPI_EXCLUSIVE=1`), with automatic
  fallback to shared mode when the device refuses.

### Changed

- **Low-latency playback discipline**: default device block lowered from
  1024 to 256 frames (~5.3 ms at 48 kHz) with 512/1024 retry fallback, and a
  first-playback GC collect+freeze (`AUDIO_STUDIO_RT_GC=0` to disable) to
  keep old objects out of playback-time collections.

## [0.2.0] - 2026-08-26 (development milestone, untagged)

The "workstation" round: recording, markers, batch processing, dynamics, and
the multitrack bus, plus the real-time discipline items deferred from the
alpha (DEV-02/08/10/15/16/19).

Merged PRs: *v0.2 workstation — recording, markers, batch processing*,
*v0.2 dynamics — compressor, limiter, sounddevice backend*, *v0.2/v0.3
continuation* (v0.2 portion), *engine telemetry triple-buffer*, and
*multitrack bus routing MVP*.

### Added

- **Recording input MVP**: transport-integrated capture from PyAudio input
  with a deterministic `NullRecorder` for headless systems, hardened into
  crash-safe PCM-24 Broadcast Wave (BWF) recording with marker cues.
- **Markers and regions**: `Marker`/`Region`/`MarkerList` in the Qt-free
  core, persistence in `.hlproj` bundles, and a UI of menu commands, a
  dockable list and coloured waveform flags with keyboard navigation.
- **Offline batch processing**: `audio_studio.batch` pipeline and
  `audio-studio-batch` CLI — glob input, gain, BS.1770 loudness
  normalisation with an optional true-peak ceiling, fades, and format/subtype
  conversion.
- **Dynamics**: soft-knee lookahead compressor and dBTP brickwall true-peak
  limiter with streaming/offline equivalence, plus streaming noise gate,
  feedback delay and FDN reverb.
- **Loudness Match**: LUFS normalisation as a rack effect and batch CLI
  preset.
- **sounddevice output backend** (PortAudio) preferred over PyAudio by
  `create_output()`, reporting device under/overruns; `AUDIO_STUDIO_OUTPUT`
  pins the backend.
- **Multitrack bus routing MVP**: submix buses in the session model with
  summing, project persistence and UI coverage.
- **Engine telemetry**: triple-buffered, allocation-free level telemetry
  publication from the render callback, covered by a render allocation
  audit.
- **Peak cache**: the waveform pyramid persists to a `.pk` sidecar
  (~0.4% of the audio size) with mtime+size or content fingerprinting,
  atomic writes, and `.hlproj` integration.

### Changed

- The live effect preview rack moved from the device render callback to the
  feeder thread, so a heavy chain costs ring latency rather than dropouts.
- Master volume and mute are ramped over 10 ms; the UI draws an interpolated
  playhead instead of the block-quantised position.

## [0.1.0-alpha] - 2026-08-26

This alpha is the three-round Audio Studio MVP snapshot. It is a usable,
headless-testable single-track audio analysis/editor foundation; it is not yet
feature-equivalent to Adobe Audition.

### Round 1 — MVP foundation

#### Added

- Qt desktop shell with transport controls, waveform lane, time ruler, output
  level meter, dark theme, keyboard shortcuts, drag-and-drop, recent files, and
  whole-file or selection export.
- Qt-free audio core with WAV/FLAC/MP3/Ogg/Opus/AIFF/W64/CAF/AU loading,
  ffmpeg subprocess fallback, float32 normalization, resampling, ring-buffered
  playback, looping, seeking, selection playback, gain, and peak/RMS metering.
- Multi-resolution waveform peak pyramid with overview-to-sample zoom,
  selection, panning, clipping markers, and cached repainting.
- STFT/iSTFT analysis, eight window functions, calibrated spectra, waterfall
  data, color maps, and the initial spectrogram widget.
- Gain, peak/RMS/true-peak normalization, fades, and parametric EQ DSP modules
  with streaming/offline equivalence tests.
- Deterministic audio fixtures, boundary probes, benchmark tooling, a Round 1
  performance baseline, development container/setup scripts, and architecture
  plus SOTA acceptance documents.

### Round 2 — convergence and hardening

#### Added

- Copy-on-write `EditSession` with reversible cut, paste, delete, silence,
  gain, fade, reverse, trim, and insertion commands; configurable undo/redo
  history and a `SampleSource`-compatible read path.
- Memory and disk-streaming sample sources with a bounded decoded-block cache.
- Lock-free single-producer/single-consumer ring-buffer API and zero-allocation
  `read_into` flow through the feeder/render path.
- Live effect preview chain with wet/dry and bypass, a dockable effects rack,
  dockable spectrum panel, and asynchronous loudness reporting.
- ITU-R BS.1770 K-weighted integrated loudness and LRA implementation.
- Two-level spectrogram rendering caches and exact candidate-window true-peak
  normalization optimization.
- Independent EBU Tech 3341/3342 oracle tests, bit-exact WAV null tests, SLO
  proxy suite, realtime escape-hatch monitor, and performance regression gate.
- Linux/macOS/Windows CI matrix definition, offscreen GUI smoke job, locked CI
  dependencies, and performance artifacts.

#### Changed

- Migrated the GUI binding from PyQt6 to LGPL-selected
  PySide6-Essentials.
- Replaced the mutex-backed playback queue with the SPSC implementation and
  made long-file playback capable of streaming from disk.
- Integrated previously isolated spectral, effects, and loudness modules into
  the main application shell.

### Round 3 — release preparation in this snapshot

#### Added

- Thirty-item executable SOTA acceptance checklist with explicit expected-gap
  reporting, machine-readable report generation, and a PyQt6 binding guard.
- Linux Qt runtime provisioning plus Linux full-suite and macOS/Windows smoke
  lanes in the Audio CI workflow.
- Complete third-party dependency and distribution policy in
  `THIRD_PARTY_LICENSES.md`, including LGPL source/relinking obligations,
  pedalboard GPL isolation, FFmpeg build restrictions, and the default no-ASIO
  policy.
- Final architecture/implementation/test/performance/gap report and a
  structured PR body for orchestrator handoff.
- Final same-host performance comparison against the Round 1 baseline:
  9 stable metrics and 0 regressions at the 10% adverse-delta threshold.

#### Documentation

- Reconciled the README with the Round 2 engine, editing, DSP/UI integration,
  install profiles, licensing policy, and current limitations.
- Recorded release claims conservatively: hardware round-trip latency,
  long-duration soak, full cross-platform CI, and Audition-class workflow
  parity remain acceptance work rather than completed features.

### Verification evidence

- Round 1 application suite: 364 tests reported green.
- Round 2 merged progress record: 501+ tests after engine and DSP/UI additions.
- Final integrated local run: 659 passed, 23 expected-gap xfails, and one XPASS
  for the newly delivered third-party license gate; Ruff and the five-second
  offscreen/null-audio GUI smoke passed.
- Audio CI for integrated code commit `c908a7e` passed, including the binding
  guard, Linux full suite, macOS/Windows smoke lanes, GUI smoke and performance
  probes.
- Round 3 acceptance report: 30 checklist items, 7 currently evidenced and 23
  expected gaps; `sota_claimed` remains false.
- SLO/compliance validation snapshot: 21 tests green; six headless SLO proxies
  passed, with zero formal hardware SLOs claimed.
- Final benchmark delta: configuration and environment match the Round 1
  baseline; all nine compared metrics are stable and warnings are empty.

### Post-Round 3 additions (alpha release candidate)

#### Added

- Full EditSession UI wiring: Edit menu and toolbar with cut, copy, paste, delete,
  silence, trim, gain, fade in/out, reverse, insert silence, and unlimited
  undo/redo with modified-state window title markers.
- `.hlproj` schema-v1 project bundles: save/open waveform document, multitrack
  session, UI state and on-disk media copies; unsaved-change guards on
  close/open.
- Multitrack Session MVP: track lanes, clip placement, master fader, workspace
  switch between waveform editor and multitrack view.
- De-Hum and De-Click repair effects in the dockable preview rack (De-Click is
  render-only; preview skips it by design).

#### Changed

- README limitations updated to reflect editing UI, project persistence, and
  multitrack MVP boundaries.

### Known gaps

- Multitrack production workflow (buses/sends/automation) remains incomplete.
- No input/recording path, batch processor, or production VST3/AU plugin host.
- Undo history is not persisted inside `.hlproj` (flattened document only).
- EBU vectors cover only part of the target matrix; true-peak limiting,
  loudness normalization, AES17, highest-quality SRC, and TPDF dither gates
  remain incomplete.
- No physical-device RTT/underrun certification or 10-minute realtime soak;
  cloud measurements are headless proxies.
- Accessibility, HiDPI, RF64/>4 GB workflows, and full installer license/SBOM
  validation remain release blockers beyond this alpha.
