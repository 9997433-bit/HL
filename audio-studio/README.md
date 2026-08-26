# Audio Studio

A professional audio editing and analysis workstation, benchmarked against the
baseline capabilities of Adobe Audition. This repository holds the Python MVP:
a fast path to a working, testable product whose architecture is deliberately
portable to a later C++/JUCE host.

> **Alpha status:** the current release is a strong single-track analysis and
> editing foundation, not an Adobe Audition replacement. The implemented and
> missing workflows are listed explicitly below.

```
┌──────────────────────────────────────────────────────────────┐
│ audio_studio.ui    PySide6 widgets, DAW-style editing surface │
├──────────────────────────────────────────────────────────────┤
│ audio_studio.core  engine · streaming · edits · SPSC transport│  ← Qt-free
├──────────────────────────────────────────────────────────────┤
│ audio_studio.dsp   effects · spectrum · BS.1770 loudness      │
├──────────────────────────────────────────────────────────────┤
│ NumPy · SciPy · SoundFile/libsndfile · optional PortAudio     │
└──────────────────────────────────────────────────────────────┘
```

The `core` package imports no Qt symbol anywhere. That boundary is what makes
the engine unit-testable head-lessly, keeps the audio threads away from the
widget hierarchy, and leaves the door open for a native re-implementation
behind the same interfaces.

## Install

```bash
cd audio-studio
python -m venv .venv && source .venv/bin/activate
pip install -e .                 # application + null-audio backend
pip install -e ".[dev]"          # add tests, lint, and type checking
pip install -e ".[audio,dev]"    # also add optional PyAudio hardware output
```

PortAudio needs its system library before `PyAudio` will build:

```bash
sudo apt-get install -y portaudio19-dev python3-dev   # Debian/Ubuntu
brew install portaudio                                # macOS
```

Qt additionally needs the usual X/EGL runtime on a bare Linux container:

```bash
sudo apt-get install -y libegl1 libgl1 libxkbcommon-x11-0 libdbus-1-3 \
    libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 \
    libxcb-randr0 libxcb-render-util0 libxcb-xinerama0 libasound2t64
```

If PortAudio is unavailable the engine transparently falls back to a simulated
output clock, so the application still starts and every control still works —
you just will not hear anything.

## Run

```bash
python -m audio_studio                    # empty editor
python -m audio_studio path/to/track.flac # open a file on start-up
audio-studio path/to/track.flac           # installed console script
```

Useful flags:

| Flag | Purpose |
|---|---|
| `--null-audio` | Force the simulated backend instead of a hardware device |
| `--offscreen` | Use Qt's offscreen platform plugin (headless smoke tests) |
| `--exit-after N` | Quit after N seconds, for CI |

Headless smoke test:

```bash
xvfb-run -a python -m audio_studio --null-audio --exit-after 5 track.wav
```

## What the MVP does

**Audio engine** (`audio_studio.core.engine.AudioEngine`)

- Decodes WAV, FLAC, MP3, Ogg/Vorbis, Opus, AIFF, W64, CAF and AU through
  libsndfile, with an `ffmpeg` fallback for codecs the local libsndfile lacks.
- Everything is normalised to `float32` in `[-1, 1]`, shaped `(frames, channels)`.
- Plays from a `SampleSource` — either an in-memory clip or a file streamed
  from disk a block at a time — so long programmes no longer have to fit in
  RAM to be played.
- Ring-buffered playback: a feeder thread decouples the device callback from
  the source through a lock-free SPSC ring (monotonic counters, zero-allocation
  `read_into`), so the real-time thread only ever performs a bounded copy.
- Play, pause, resume, stop-with-rewind, sample-accurate seek, looping, and
  selection-restricted playback.
- The reported playhead subtracts what is still queued in the ring buffer, so
  it reflects what is audible rather than how far the feeder has run ahead.
- Per-channel peak/RMS metering published from the render callback.
- Pluggable output: `PyAudioOutput` (PortAudio) or `NullOutput` (simulated
  clock, plus a manually-pumped mode used by the tests).

**Editing core** (`audio_studio.core.edit_session.EditSession`)

- Copy-on-write document: an immutable list of segment views onto immutable
  chunks, so cutting ten seconds out of an hour rewrites a handful of records
  and copies nothing.
- Nine undoable commands — cut, copy, paste, delete, trim, silence, insert
  silence, gain, fade and reverse — on an undo stack whose revisions share
  almost all of their storage.
- The session itself satisfies `SampleSource`, so the transport plays an
  edited document straight off the undo stack without flattening it first;
  revision publication is atomic, so a reader sees either the old or the new
  complete document, never half an edit.
- The source file is never modified in place; export writes a new file.

**Waveform display** (`audio_studio.ui.waveform_view.WaveformView`)

- Multi-resolution min/max/RMS pyramid, so a repaint costs O(widget width)
  rather than O(clip length).
- Below ~4 px per sample the view switches to a sample-accurate polyline with
  individual sample dots.
- Zoom (`Ctrl`+wheel, anchored under the pointer), horizontal scroll (wheel),
  vertical amplitude zoom (`Alt`+wheel), middle-drag panning.
- Click-drag range selection, shift-click to extend, double-click to select
  all; playhead, edit cursor, clipping markers and a time grid.
- The static waveform is cached to a pixmap, so playhead motion does not
  re-reduce the envelope.

**Application shell** (`audio_studio.ui.main_window.MainWindow`)

- Track lane with header (name, format summary, mute), a timeline ruler and a
  synchronised scrollbar.
- Transport strip: skip-to-start, play/pause, stop, skip-to-end, loop, a large
  timecode readout, selection length and an output gain slider.
- Output level meter with peak hold, RMS shading and a latching clip indicator.
- Menus and shortcuts, drag-and-drop file opening, a recent-files list, export
  of the whole clip or just the selection, and a status bar carrying format,
  duration, selection and active output backend.
- Dockable spectrum and effects-rack panels, live wet/dry/bypass preview, and
  asynchronous integrated loudness/LRA analysis.

**DSP and analysis** (`audio_studio.dsp`)

- Calibrated STFT/iSTFT, eight window functions, linear/log frequency display,
  waterfall data and color-blind-safe maps.
- Gain, peak/RMS/true-peak normalization, multiple fade curves, and
  RBJ parametric EQ with stateful block processing.
- ITU-R BS.1770 K-weighted integrated loudness and EBU-style loudness range.
- Cached spectrogram reduction/colorization and candidate-window true-peak
  evaluation keep common redraw and normalization paths bounded.

### Keyboard

| Shortcut | Action |
|---|---|
| `Ctrl+O` / `Ctrl+W` | Open / close file |
| `Space` | Play / pause |
| `Esc` | Stop |
| `Home` / `End` | Go to start / end of the playback region |
| `L` | Toggle loop |
| `Ctrl+A` / `Ctrl+Shift+A` | Select all / deselect |
| `Ctrl+=` / `Ctrl+-` / `Ctrl+0` | Zoom in / out / fit |
| `Ctrl+Shift+0` | Zoom to selection |
| `Ctrl+Up` / `Ctrl+Down` | Amplitude zoom |
| `Ctrl+Shift+S` | Export as… |

## Licensing and optional components

The application is declared MIT. Its default dependency profile uses
PySide6/Qt and libsndfile dynamically under their LGPL terms. PyAudio is an
optional hardware-output extra; the null backend remains available without it.
FFmpeg is discovered as a separate executable and is never linked into the
application.

pedalboard is GPL-3.0 and is intentionally absent from the default dependency
tree and current package manifests. A future pedalboard plugin bridge must be
an explicit, lazy-loaded optional extra; any installer that bundles it must
distribute the combined work under GPL-3.0. The ASIO SDK is not included, and
Audio Studio does not enable `SD_ENABLE_ASIO`.

See [`THIRD_PARTY_LICENSES.md`](../THIRD_PARTY_LICENSES.md) for versions,
upstream license pointers, LGPL source/relinking obligations, FFmpeg build
restrictions and the release checklist.

## Tests

```bash
QT_QPA_PLATFORM=offscreen pytest
```

The suite covers value-type invariants, ring-buffer wrap-around and
over/under-run handling, decoding round-trips and resampling, the peak pyramid
against brute-force numpy reductions, the transport state machine, seek
accuracy (including discarding stale buffered audio mid-playback), gain and
metering, copy-on-write edits and deep undo/redo, disk-streaming sources, DSP
streaming equivalence, loudness/spectrum behavior, and Qt widgets under the
offscreen platform plugin. Repository-level compliance, null-roundtrip and SLO
tests live one directory above this package.

## Known limitations

- Single visible track/clip. `TrackPanel` is reusable, but there is no finished
  multitrack mixer, clip timeline, bus/send routing or automation workflow.
- Waveform editing is wired through `EditSession`: cut, copy, paste, delete,
  silence, trim and unlimited undo/redo from the Edit menu and toolbar. Project
  save and recovery are not implemented yet — export the edited clip to disk.
- No recording path, no repair suite (de-click, de-hum, noise reduction), no
  spectral selection editing, no production VST3/AU host or plugin delay
  compensation, no batch processing, and no project files or markers yet — see
  the roadmap in the release sign-off.
- Not a low-latency monitor: the default device block is 1024 frames
  (~21 ms at 48 kHz) and there is no exclusive-mode backend handling; playhead
  accuracy is bounded by the block size.
- The effect-rack preview chain runs on the device render path. Light chains
  are fine in practice; a heavy chain can starve the callback. Committed
  (offline) effects are unaffected.
- The SPSC ring is lock-free at the Python level but still executes under
  CPython/GIL scheduling; physical-device p99 timing and a long soak are not
  certified by headless tests.
- Sample-rate conversion quality is unrated against the acceptance targets and
  bit-depth reduction applies no TPDF dither yet — for mastering-grade exports
  keep the source rate and float depth. Do not claim certified broadcast
  compliance from the current alpha.
- Loop playback restarts from the region start without a crossfade, and the
  reported position is briefly clamped across the wrap.
- Long files stream from disk for playback, but the edit history and peak
  pyramid are held in memory; RF64/>4 GB out-of-core workflows are not yet
  complete end to end.

## Release notes — v0.1.0-alpha

The first tagged preview: a **single-track waveform editor and analyzer**, not
yet a multitrack DAW.

- **Highlights:** streaming or in-memory playback over a lock-free SPSC ring;
  nine undoable copy-on-write edit commands with storage-sharing undo;
  parametric EQ / gain / normalize / fade with a live preview rack;
  calibrated spectral display; BS.1770-4 loudness and 4x true-peak metering;
  bit-exact WAV null-test, EBU 3341/3342 compliance vectors and an SLO suite
  shipped in-repo.
- **Known limitations:** the section above is the authoritative list; loudness
  compliance certification of the product meter against the full EBU vector
  set is still in progress (an independent oracle, `tools/ebu_r128.py`, ships
  alongside), and published performance numbers are headless proxies rather
  than audio-device certification.
- **System requirements:** Python ≥ 3.10 (3.12 is the verified baseline);
  `numpy`, `scipy`, `soundfile`, `PySide6-Essentials`; optional `PyAudio`
  (hardware output; falls back to a simulated clock without it) and `ffmpeg`
  (extended decode). On headless Linux install the Qt runtime libraries listed
  under *Install*.
- **Release gates:** three-platform CI (with the GUI smoke job) is green and
  `THIRD_PARTY_LICENSES.md` is in place; the orchestrator cuts the tag once
  the remaining Round 3 merges (multitrack session MVP, BS.1770 product
  compliance) are either verified in or explicitly deferred. Full scope, the
  deviations register and the v0.2 → v1.0 roadmap:
  [`.agent_workspace/round3/fable-release-signoff.md`](../.agent_workspace/round3/fable-release-signoff.md).
