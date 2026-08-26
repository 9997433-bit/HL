# Audio Studio

A professional audio editing and analysis workstation, benchmarked against the
baseline capabilities of Adobe Audition. This repository holds the Python MVP:
a fast path to a working, testable product whose architecture is deliberately
portable to a later C++/JUCE host.

```
┌──────────────────────────────────────────────────────────────┐
│ audio_studio.ui      PyQt6 widgets, DAW-style editing surface │
├──────────────────────────────────────────────────────────────┤
│ audio_studio.core    engine · transport · decode · envelopes  │  ← Qt-free
├──────────────────────────────────────────────────────────────┤
│ numpy · scipy · soundfile · PortAudio                         │
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
pip install -e ".[dev]"
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
  the source, so the real-time thread only ever performs a bounded copy.
- Play, pause, resume, stop-with-rewind, sample-accurate seek, looping, and
  selection-restricted playback.
- The reported playhead subtracts what is still queued in the ring buffer, so
  it reflects what is audible rather than how far the feeder has run ahead.
- Per-channel peak/RMS metering published from the render callback.
- Pluggable output: `PyAudioOutput` (PortAudio) or `NullOutput` (simulated
  clock, plus a manually-pumped mode used by the tests).

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

## Tests

```bash
QT_QPA_PLATFORM=offscreen pytest
```

The suite covers value-type invariants, ring-buffer wrap-around and
over/under-run handling, decoding round-trips and resampling, the peak pyramid
against brute-force numpy reductions, the transport state machine, seek
accuracy (including discarding stale buffered audio mid-playback), gain and
metering, and the Qt widgets under the offscreen platform plugin.

## Known limitations

- Single track, single clip. `TrackPanel` is written as a reusable lane, but
  there is no mixer, no multi-clip timeline and no track routing yet.
- No editing operations that mutate audio (cut, paste, trim, fades) and no undo
  history — the MVP is read/transport/analyse only. Export writes the loaded
  buffer or the selected range unchanged.
- Playhead accuracy is bounded by the device block size; it does not consult
  PortAudio's stream time for sub-block precision.
- `RingBuffer` uses a short-held mutex rather than a genuinely lock-free SPSC
  queue. Adequate at these block sizes, but it is the first thing to replace
  for very low-latency work.
- Loop playback restarts from the region start without a crossfade, and the
  reported position is briefly clamped across the wrap.
- The clip is held fully in RAM; there is no streaming-from-disk path, so very
  long files are limited by available memory.
