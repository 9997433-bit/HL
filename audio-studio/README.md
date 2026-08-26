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
pip install -e ".[audio,dev]"    # also add the optional hardware backends
```

The `audio` extra installs two PortAudio bindings: `sounddevice`, which is the
preferred output backend, and `PyAudio`, which still drives recording. The
`sounddevice` wheels carry their own PortAudio build (including WASAPI on
Windows), so nothing else is needed for playback. `PyAudio` compiles against the
system library:

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

`create_output()` tries `sounddevice` first, then `PyAudio`, opening a throwaway
stream on each before it commits. If neither yields a device the engine
transparently falls back to a simulated output clock and synthetic input, so the
application still starts and every control still works — you just will not hear
or capture a real device. `AUDIO_STUDIO_OUTPUT` pins the choice:

```bash
AUDIO_STUDIO_OUTPUT=pyaudio     python -m audio_studio   # force the legacy binding
AUDIO_STUDIO_OUTPUT=sounddevice python -m audio_studio   # never fall back to PyAudio
AUDIO_STUDIO_OUTPUT=null        python -m audio_studio   # skip hardware entirely
```

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

## Batch processing

`audio_studio.batch` processes whole folders offline, no GUI required:

```bash
python -m audio_studio.batch.cli --input "stems/*.wav" --output out/ --lufs -16
audio-studio-batch --input "takes/**/*.flac" --output out/ \
    --lufs -16 --true-peak -1.0 --fade-in 0.05 --fade-out 0.5 --format wav
```

Each matched file is decoded, run through the requested operations in order —
`--gain-db`, then `--lufs` loudness normalisation (BS.1770 integrated, with an
optional `--true-peak` ceiling), then `--fade-in`/`--fade-out` (`--fade-shape`
picks the curve) — and re-encoded into `--output`, keeping its name.
`--format` converts the container and `--subtype` overrides the encoding
(e.g. `PCM_16`, `FLOAT`). Progress is printed to stdout one line per file; the
exit code is 0 when every file rendered, 1 when any failed, 2 when nothing
matched. The same pipeline is scriptable from Python via
`audio_studio.batch.BatchJob` and `run_batch`.

## VST3 plugins (optional `plugins` extra — not enabled by default)

Audio Studio can host VST3 effect plugins through
[pedalboard](https://github.com/spotify/pedalboard). The bridge is **not part
of the default install**: nothing in the application imports pedalboard unless
you opt in explicitly.

```bash
pip install -e ".[plugins]"      # installs pedalboard (GPL-3.0)
```

```python
from audio_studio.plugins import create_plugin_host

host = create_plugin_host("/path/to/Plugin.vst3")
host.prepare(sample_rate=48_000, n_channels=2)
out = host.process_block(block, 48_000)   # planar (n_channels, n_samples)
host.parameters()                          # {name: normalised value}
host.latency_samples()                     # reported plugin delay, in samples
```

`audio_studio.plugins` always imports cleanly — pedalboard is loaded lazily,
inside the single bridge module `audio_studio/plugins/pedalboard_bridge.py`,
the first time a plugin is opened. Without the extra installed, loading a
plugin raises `PluginLoadError` with installation instructions. The current
scaffold is API-only: plugins are not yet wired into the effect rack or the
UI, and plugin state is not yet persisted into projects.

**License notice.** pedalboard is GPL-3.0 (incorporating JUCE, Rubber Band
and FFTW). Installing the `plugins` extra for private use does not change the
MIT license of Audio Studio's source, but *distributing* Audio Studio together
with pedalboard — in a wheel, installer or application bundle — creates a
combined work that must be distributed under GPL-3.0 as a whole. Official MIT
binary artifacts must not include it. See
[`THIRD_PARTY_LICENSES.md`](../THIRD_PARTY_LICENSES.md).

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
  `position` moves once per device block; `position_interpolated` walks the
  last block off against the wall clock and returns a fractional frame, which
  is what the UI draws so a 30 Hz repaint glides instead of stepping.
- Master volume and mute are ramped over 10 ms rather than applied as a step,
  so moving the fader during playback cannot click.
- An optional per-block insert (`set_stream_processor`) runs on the feeder
  thread, ahead of the ring buffer. The live effect rack uses it, so a chain
  that overruns a block period costs latency the ring absorbs rather than a
  dropout.
- Per-channel peak/RMS metering published from the render callback.
- Pluggable output: `SoundDeviceOutput` (PortAudio via `sounddevice`, reporting
  device under/overruns through `xruns`), `PyAudioOutput` (PortAudio via
  `PyAudio`) or `NullOutput` (simulated clock, plus a manually-pumped mode used
  by the tests).
- Recording to WAV from mono or stereo `PyAudio` input, with a deterministic
  silence/tone `NullRecorder` for headless systems and tests.

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
- The pyramid is cached to a `.pk` sidecar (see *Peak cache* below), so
  reopening a file restores the overview instead of reducing every sample
  again.
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
- Transport strip: record, skip-to-start, play/pause, stop, skip-to-end, loop,
  a large timecode readout, selection length and an output gain slider.
- Output level meter with peak hold, RMS shading and a latching clip indicator.
- Menus and shortcuts, drag-and-drop file opening, a recent-files list, export
  of the whole clip or just the selection, and a status bar carrying format,
  duration, selection and active output backend.
- Dockable spectrum and effects-rack panels, live wet/dry/bypass preview, and
  asynchronous integrated loudness/LRA analysis. The rack is processed on the
  feeder thread, before the master fader, so a rack change reaches the speakers
  once the already-queued blocks have drained rather than instantly.

**Markers and regions** (`audio_studio.core.markers.MarkerList`)

- Drop a marker at the playhead or name the current selection as a region, then
  walk the timeline marker to marker from the keyboard.
- Both kinds are drawn as coloured flags over the waveform and listed in a
  dockable panel where they can be renamed, removed or double-clicked to seek
  (a region also restores its span as the selection).
- Saved into the `.hlproj` bundle as an optional `markers` array, so a project
  written with markers still opens in a build that predates them.

**DSP and analysis** (`audio_studio.dsp`)

- Calibrated STFT/iSTFT, eight window functions, linear/log frequency display,
  waterfall data and color-blind-safe maps.
- Gain, noise gating, soft-knee lookahead compression, dBTP brickwall limiting,
  feedback delay, FDN reverb, peak/RMS/true-peak normalization, multiple fade
  curves, and RBJ parametric EQ with stateful block processing. Core dynamics
  and time/space effects have basic controls in the live rack.
- ITU-R BS.1770 K-weighted integrated loudness and EBU-style loudness range.
- Cached spectrogram reduction/colorization and candidate-window true-peak
  evaluation keep common redraw and normalization paths bounded.

### Peak cache

Reducing a clip into the waveform pyramid costs one pass over every sample,
which is the part of opening a long file that is actually slow. `AudioEngine`
therefore persists the finished pyramid next to the audio as a `.pk` sidecar —
`track.flac` gets `track.flac.pk`, roughly 0.4% of the audio's size — and reads
it back on the next open, both for decoded (`load`) and streamed
(`open_stream(build_pyramid=True)`) clips.

The sidecar header stores the source's size and modification time, so editing
or replacing the file misses instead of drawing a stale waveform, and the write
goes through a temporary file plus a rename, so a reader never sees a partial
pyramid. Every failure — unreadable sidecar, corrupt payload, read-only folder
— falls back to building the pyramid in memory.

```bash
AUDIO_STUDIO_PEAK_CACHE=0                     python -m audio_studio  # never read or write .pk
AUDIO_STUDIO_PEAK_CACHE_DIR=~/.cache/hl-peaks python -m audio_studio  # keep sidecars out of the audio folders
AUDIO_STUDIO_PEAK_CACHE_KEY=content           python -m audio_studio  # fingerprint by SHA-256 instead of mtime+size
```

`.hlproj` bundles carry the same file for each media copy and point at it from
an optional `peaks` key in the media entry; a bundle written without one (or by
an older build) simply rebuilds the overview on load.

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
| `M` / `Shift+M` | Add a marker at the playhead / a region from the selection |
| `Ctrl+Left` / `Ctrl+Right` | Go to the previous / next marker |
| `F2` | Rename the marker selected in the Markers panel |
| `Ctrl+Shift+S` | Export as… |

## Licensing and optional components

The application is declared MIT. Its default dependency profile uses
PySide6/Qt and libsndfile dynamically under their LGPL terms. `sounddevice`
(MIT, bundling PortAudio under its MIT-style license) and PyAudio are optional
hardware-input/output extras; null backends remain available without either.
FFmpeg is discovered as a separate executable and is never linked into the
application.

pedalboard is GPL-3.0 and is intentionally absent from the default dependency
tree. It is reachable only through the explicit `plugins` optional extra and
is imported lazily inside the isolated bridge module
`audio_studio/plugins/pedalboard_bridge.py`; any installer that bundles it
must distribute the combined work under GPL-3.0. The ASIO SDK is not included,
and Audio Studio does not enable `SD_ENABLE_ASIO`.

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
metering, the real-time discipline rules (volume ramping, playhead
interpolation and which thread the effect rack runs on), copy-on-write edits
and deep undo/redo, disk-streaming sources, DSP streaming equivalence
(including compressor/true-peak limiter dynamics), loudness/spectrum behavior,
and Qt widgets under the offscreen platform plugin.
Repository-level compliance, null-roundtrip and SLO tests live one directory
above this package.

## Known limitations

- Single visible track/clip. `TrackPanel` is reusable, but there is no finished
  multitrack mixer, clip timeline, bus/send routing or automation workflow.
- Waveform editing is wired through `EditSession`: cut, copy, paste, delete,
  silence, trim, gain, fade in/out, reverse, insert silence and unlimited
  undo/redo from the Edit menu. Save and reopen sessions as `.hlproj` directory
  bundles (File ▸ Save/Open Project); undo history is not persisted — the saved
  document is the flattened edit result. Export remains available for one-off
  audio files.
- Recording is an MVP path: PyAudio input supports mono/stereo capture to WAV,
  but there is no input-device/level control, live monitoring, punch recording,
  or Broadcast Wave Format (BWF) metadata yet.
- No complete repair suite (noise reduction remains), spectral selection
  editing, production VST3/AU host or plugin delay compensation, or timeline
  markers yet — see the roadmap in the release sign-off. Batch processing is
  covered by the `audio_studio.batch` CLI above.
- Not a low-latency monitor: the default device block is 1024 frames
  (~21 ms at 48 kHz), and while the drawn playhead is interpolated between
  callbacks, the audio it tracks is still quantised to that block.
  `SoundDeviceOutput` is the step towards fixing this, but it currently opens
  the host API's shared mode only — WASAPI exclusive mode, ASIO and per-host
  latency hints are not wired up, and the ASIO SDK is not shipped.
- Under/overruns are counted per stream (`SoundDeviceOutput.xruns`,
  `.underflows`, `.overflows`) but nothing surfaces them in the UI yet, and
  `PyAudioOutput` cannot report them at all. Recording still runs on PyAudio
  input regardless of which output backend is selected.
- The effect-rack preview chain runs on the feeder thread, so a heavy chain no
  longer starves the device callback — but it is processed a ring buffer ahead
  of what you hear, so a parameter or bypass change lands after the queued
  blocks drain (~340 ms at the default block and ring depth). A backend opened
  outside the transport still processes in the render callback.
- The SPSC ring is lock-free at the Python level but still executes under
  CPython/GIL scheduling; physical-device p99 timing and a long soak are not
  certified by headless tests.
- Sample-rate conversion quality is unrated against the acceptance targets and
  bit-depth reduction applies no TPDF dither yet — for mastering-grade exports
  keep the source rate and float depth. Do not claim certified broadcast
  compliance from the current alpha.
- Loop playback restarts from the region start without a crossfade, and the
  reported position is briefly clamped across the wrap.
- Long files stream from disk for playback and their peak pyramid survives in a
  `.pk` sidecar between sessions, but the edit history and the pyramid itself
  are held in memory while a clip is open, and a pyramid restored for a streamed
  file only resolves down to its finest cached level (256 frames per bin) until
  the samples are read. RF64/>4 GB out-of-core workflows are not yet complete
  end to end.

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
  (hardware input/output; falls back to simulated devices without it) and `ffmpeg`
  (extended decode). On headless Linux install the Qt runtime libraries listed
  under *Install*.
- **Release gates:** three-platform CI (with the GUI smoke job) is green and
  `THIRD_PARTY_LICENSES.md` is in place; the orchestrator cuts the tag once
  the remaining Round 3 merges (multitrack session MVP, BS.1770 product
  compliance) are either verified in or explicitly deferred. Full scope, the
  deviations register and the v0.2 → v1.0 roadmap:
  [`.agent_workspace/round3/fable-release-signoff.md`](../.agent_workspace/round3/fable-release-signoff.md).
