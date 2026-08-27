# Changelog

All notable changes are documented here. The project follows Keep a Changelog
structure while it remains pre-1.0.

## Unreleased

### Added

- `.hlprojz` project archives: the `.hlproj` bundle stored as a single zip
  file, at the same schema version, with atomic packing and unpacking and
  validation of member names from untrusted archives. File ▸ Open Project
  Archive (`Ctrl+Shift+H`) and File ▸ Save Project Archive As (`Ctrl+Alt+H`);
  `audio_studio.project.archive` headlessly.
- Desktop bundle scaffold: `packaging/pyinstaller.spec` and
  `scripts/build-linux.sh`, building a one-directory artifact that keeps the
  LGPL shared libraries replaceable, refuses to bundle GPL components, and
  ships `LGPL-RELINKING.txt` beside the third-party notices.

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
