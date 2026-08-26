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
- Ring-buffered playback: a feeder thread decouples the device callback from
  the source through a lock-free SPSC queue, so the real-time thread only ever
  performs a bounded copy into a caller-owned block.
- Short clips use an in-memory source; long supported files can use a bounded
  decoded-block cache and stream from disk.
- Play, pause, resume, stop-with-rewind, sample-accurate seek, looping, and
  selection-restricted playback.
- The reported playhead subtracts what is still queued in the ring buffer, so
  it reflects what is audible rather than how far the feeder has run ahead.
- Per-channel peak/RMS metering published from the render callback.
- Pluggable output: `PyAudioOutput` (PortAudio) or `NullOutput` (simulated
  clock, plus a manually-pumped mode used by the tests).

**Editing core** (`audio_studio.core.edit_session.EditSession`)

- Copy-on-write chunk table with immutable revisions and a configurable
  undo/redo history.
- Reversible cut, paste, delete, silence, gain, fade, reverse, trim and insert
  operations; copy does not modify the source revision.
- Implements the sample-source protocol, so playback can read an edited
  revision without flattening it into one large array.
- Thread-safe revision publication: a reader sees either the old complete
  document or the new complete document.

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
- The `EditSession` command/undo core is implemented, but the main window does
  not yet expose the complete destructive editing workflow or project save and
  recovery.
- No recording/input path, batch processor, production VST3/AU host, plugin
  delay compensation, or installer-supported ASIO path.
- Playhead accuracy is bounded by the device block size; it does not consult
  PortAudio's stream time for sub-block precision.
- The SPSC ring is lock-free at the Python level but still executes under
  CPython/GIL scheduling; physical-device p99 timing and a long soak are not
  certified by headless tests.
- Loop playback restarts from the region start without a crossfade, and the
  reported position is briefly clamped across the wrap.
- Streaming playback exists, but waveform/analysis/export paths are not yet a
  complete RF64/>4 GB out-of-core workflow.
- EBU/AES/SRC acceptance coverage is partial. Do not claim certified broadcast
  compliance from the current alpha.
