# Changelog

All notable changes are documented here. The project follows Keep a Changelog
structure. Versions 0.2.0 and 0.3.0 were internal development milestones
merged to the release branch without their own tags; they are recorded here so
the v1.0.0-beta diff against v0.1.0-alpha is fully accounted for.

## [1.0.0-beta] - 2026-08-27

The professional-workstation beta. This release closes the "v1.0 SOTA
alignment" round planned at the alpha sign-off: mastering-grade export,
the full repair suite, plugin delay compensation, accessibility, and soak
tooling. It is a professional single-track editor with a multitrack MVP —
not full Adobe Audition parity; the honest gap register lives in
`.agent_workspace/v1.0/FINAL_RELEASE_SUMMARY.md`.

Merged PRs: *v1.0 Round A — PDC, soak, NR, a11y, dither, DeClip* plus this
release-preparation branch.

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
