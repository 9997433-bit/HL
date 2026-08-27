# Audio Studio

A professional audio editing and analysis workstation, benchmarked against the
baseline capabilities of Adobe Audition. This repository holds the Python MVP:
a fast path to a working, testable product whose architecture is deliberately
portable to a later C++/JUCE host.

> **Beta status:** v1.0.0-beta is a professional single-track editor with a
> repair/mastering toolset, a VST3 host MVP and a multitrack MVP — not an
> Adobe Audition replacement. The implemented and missing workflows are
> listed explicitly below.

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
pip install -e ".[mastering]"    # add optional libsoxr bindings
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

On **Windows only**, the sounddevice backend can additionally request WASAPI
*exclusive* mode. Shared mode (the default) routes through the Windows audio
engine's mixer, which adds its own buffering (typically around 10 ms) on top of
the device period; exclusive mode bypasses the mixer and talks to the device
directly, so output latency is bounded mostly by the negotiated block size
(256 frames ≈ 5.3 ms at 48 kHz). The trade-off is that an exclusive stream
takes over the device — other applications go silent — and the device may
refuse to open at all, in which case the backend automatically falls back to a
shared-mode stream. Because of that footgun it is off by default and must be
switched on explicitly:

```bash
set AUDIO_STUDIO_WASAPI_EXCLUSIVE=1        # cmd.exe; ignored on non-Windows hosts
python -m audio_studio
python -m audio_studio --wasapi-exclusive  # equivalent: sets the variable for you
```

The active mode shows up in the status bar and the About box as
`sounddevice (WASAPI exclusive)`.

If the PortAudio library loaded by `sounddevice` already exposes an ASIO host
API, Audio Studio can prefer its first output device:

```bat
set AUDIO_STUDIO_ASIO=1
python -m audio_studio
```

This is Windows-only host selection, not an official ASIO integration. Audio
Studio ships no Steinberg ASIO SDK, does not set `SD_ENABLE_ASIO`, and does not
add an ASIO-enabled PortAudio binary. If the user's `sounddevice`/PortAudio
runtime exposes no ASIO output, or its stream refuses the requested format, the
backend falls back to the ordinary default device. An explicitly configured
`SoundDeviceOutput(device=...)` always wins over the environment preference.
The active backend label is `sounddevice (ASIO)`.

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
| `--wasapi-exclusive` | Request WASAPI exclusive-mode output (Windows only, see above) |
| `--offscreen` | Use Qt's offscreen platform plugin (headless smoke tests) |
| `--exit-after N` | Quit after N seconds, for CI |
| `--scale-factor F` | Scale the whole interface by F (1.0–2.0), see *Accessibility* |

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
audio-studio-batch --input "takes/*.wav" --output edited/ --macro edit.json
```

Each matched file is decoded, run through the requested operations in order —
`--macro` first, `--gain-db`, then `--lufs` loudness normalisation (BS.1770
integrated, with an optional `--true-peak` ceiling), then
`--fade-in`/`--fade-out` (`--fade-shape` picks the curve) — and re-encoded into
`--output`, keeping its name.
`--format` converts the container and `--subtype` overrides the encoding
(e.g. `PCM_16`, `FLOAT`). Progress is printed to stdout one line per file; the
exit code is 0 when every file rendered, 1 when any failed, 2 when the
configuration is invalid or nothing matched. The same pipeline is scriptable from Python via
`audio_studio.batch.BatchJob` and `run_batch`.

An edit macro is the applied command branch of an `EditSession`, in exact frame
coordinates with the source sample rate recorded in schema-v1 JSON:

```python
from audio_studio.batch import save_macro

save_macro(session, "edit.json")
```

Gain, fade, silence, reverse, spectral edit, delete, trim, insert-silence and
cut/paste command sequences round-trip. The batch input sample rate must match
the macro. A paste of copied or external PCM cannot be made portable without
embedding source audio, so serialization rejects it; a paste backed by an
earlier cut in the same macro is supported and uses each batch input's own
samples.

## Mastering exports

Audio Studio processes samples as float32. Exporting to `PCM_16` or `PCM_24`
reduces that working precision, so `save_audio()` applies TPDF dither by
default. Dither is added independently per sample/channel at ±1 target-format
LSB and is not applied to floating-point or compressed subtypes. Leave it on
for the final integer master; use `dither=False` only for a deliberate
bit-exact round trip or when the material was already dithered at its final
depth. Repeatedly dithering intermediate files raises their noise floor.

The reproducible 96 kHz → 44.1 kHz SRC probe can be run from the repository
root:

```bash
python tools/src_report.py
```

It writes `.agent_workspace/round3/src-quality-report.json`, reports passband
sweep deviation, out-of-band sweep mirrors, and 1 kHz THD+N, and exits nonzero
when any offline mastering gate is missed. With the `mastering` extra installed,
Audio Studio automatically uses `soxr` VHQ for offline conversion; otherwise it
falls back to `scipy.signal.resample_poly`. The report records the selected path
and every available path. Selection can be pinned for reproducible comparisons:

```bash
AUDIO_STUDIO_SRC=soxr  python tools/src_report.py  # VHQ when the extra is installed
AUDIO_STUDIO_SRC=scipy python tools/src_report.py  # force the built-in fallback
```

`audio_studio.core.resample.resample_buffer()` exposes `quality="vhq"` by
default (QQ/LQ/MQ/HQ/VHQ are accepted), and `loader.resample()` forwards the
same option. Requesting soxr without the optional extra remains operational by
falling back to SciPy. The SciPy path is suitable for preview and general
editing but only the measured soxr VHQ path is held to the mastering gates.

## Repair and recording takes

`DeClipEffect` reconstructs short, flat-topped peaks offline. It detects
repeated samples on a clipping rail and fits a cubic Hermite spline between
the intact values and slopes on either side; untouched samples remain bit for
bit unchanged. Set `threshold` to the known rail when the source clipped below
digital full scale:

```python
from audio_studio.dsp.repair import DeClipEffect

cleaned = DeClipEffect(threshold=0.8).process(clipped, 48_000)
```

The effect is deliberately skipped by live preview because it needs future
samples. `last_report` lists every detected range and whether it was repaired;
edge plateaus and runs longer than `max_clip_ms` are reported but left alone.

Every completed transport recording is assigned `Take 001`, `Take 002`, and so
on. **File ▸ Takes** lists the current session's recordings and reopens one in
the waveform editor. A saved project keeps `takes.json` and copied take audio
inside its `.hlproj` directory. An unsaved or file-based session uses an atomic
`*.takes.json` sidecar instead. The Qt-free API is
`audio_studio.core.recorder.TakeRegistry`.

## VST3 plugins (optional `plugins` extra — not enabled by default)

Audio Studio can host VST3 effect plugins through
[pedalboard](https://github.com/spotify/pedalboard). The bridge is **not part
of the default install**: nothing in the application imports pedalboard unless
you opt in explicitly.

```bash
pip install -e ".[plugins]"      # installs pedalboard (GPL-3.0)
```

### In the application

**View ▸ VST3 Plugins** opens the plugin dock, tabbed behind the effects rack on
the right-hand side because both drive the same preview chain.

1. **Scan…** picks a folder and lists the `.vst3` bundles under it in the combo
   beside it, then **Load** puts the selected one into the first free slot.
   Scanning reads each bundle's own `moduleinfo.json` — the metadata file the
   VST3 SDK ships so hosts can enumerate plugins — so it never runs plugin code
   and works without the `plugins` extra installed.
2. **Load VST3…** in a slot opens a file dialog filtered to `*.vst3`, for a
   plugin that lives somewhere a scan did not reach. On macOS and Linux a plugin
   is a directory bundle, so pick the `.vst3` folder itself; the "All files"
   filter is there for platforms that hide the extension.
3. The plugin's name appears in its slot, and the **Parameters** box below shows
   the *selected* slot's controls — click a slot to select it. One slider is
   generated per parameter the plugin reports on the normalised 0–1 host scale,
   and moving a slider writes straight through to the running plugin. Parameters
   reported as display values (`4800.0`, `"bell"`) are shown read-only rather
   than guessed at — edit those in the plugin's own editor.
4. **Bypass** takes one plugin out of the playback path; **Remove** unloads it
   and empties its slot; **▲**/**▼** swap it with the neighbouring slot.

There are **three** slots. They process in slot order — slot 1 first — and the
whole group is inserted into the preview chain ahead of the true-peak limiter,
so the rack's safety net still catches them, and they show up in the `FX:` field
of the status bar like any built-in effect. Like the rest of the rack they are
*monitoring inserts*: they change what is heard and never rewrite the audio in
memory until you render.

Plugin latency is **compensated** on the preview path (PDC). The readout under
the slots shows the constant the playback path is padded to — the sum of what
every loaded plugin reports, bypassed slots included, because the preview
inserts a matching delay wherever a latent plugin is bypassed
(`audio_studio.dsp.preview.LatencyCompensator`, applied on the engine's feeder
thread with the rest of the insert). That is what makes bypass a real A/B: the
stream does not move in time when a lookahead limiter or linear-phase EQ is
toggled, so a null test against the dry signal still aligns. The **PDC** button
beside the readout turns the padding off; the readout then reports the
uncompensated delay of the plugins actually running, which are heard late.
Compensation covers the preview chain only (MVP): it does not shift the
playhead readout, changing the padding mid-stream (a bypass toggle) re-primes
the delay line with silence rather than resampling across the join, and a
plugin that reports `0` — which includes pedalboard backends that compensate
internally — needs and gets no padding.

Saving a project records which bundle sits in which slot, the bypass flag, and
— when the host can produce one — an opaque per-slot **state blob**,
base64-encoded in the bundle's `plugins` array. The blob is pedalboard's native
state chunk when the installed build exposes one and a parameter-dict JSON
fallback otherwise; reopening the project loads each bundle and applies its
blob back, best-effort, so a plugin whose newer version rejects the old state
simply keeps its defaults rather than failing the slot. A plugin the project
names but this machine does not have leaves its slot empty and says so in the
panel rather than failing the open. Without the extra installed, the panel says
so in place, with the install command, instead of failing at the file dialog.

### From Python

```python
from audio_studio.plugins import create_plugin_host, create_plugin_effect

host = create_plugin_host("/path/to/Plugin.vst3")
host.prepare(sample_rate=48_000, n_channels=2)
out = host.process_block(block, 48_000)   # planar (n_channels, n_samples)
host.parameters()                          # {name: normalised value}
host.set_parameter("Drive", 0.75)          # same scale parameters() reports
host.latency_samples()                     # reported plugin delay, in samples
blob = host.state_blob()                   # opaque settings snapshot (or None)
host.restore_state(blob)                   # best-effort; False when refused

# The same plugin as an ordinary Effect, for an EffectChain:
chain.add(create_plugin_effect("/path/to/Plugin.vst3"))
chain.latency_samples()                        # summed delay of what runs now
chain.latency_samples(include_bypassed=True)   # the constant PDC pads to
```

`PluginEffectAdapter` is the bridge between the two: it wraps a `PluginHost` as
an `Effect`, adding the rack's `bypass`/`mix` controls and forwarding
`prepare`/`reset`/`process_block` so the plugin's streaming state is its own.
It also forwards `latency_samples`/`state_blob`/`restore_state`, and marks
itself `compensate_when_bypassed` so the delay-compensated preview keeps
padding for it while it is bypassed.

### Finding plugins

`audio_studio.plugins.scanner` is the discovery half, and it is deliberately
pedalboard-free: it reads the bundle layout and `Contents/moduleinfo.json`
rather than loading binaries, so a scan cannot be crashed by a bad plugin.

```python
from audio_studio.plugins.scanner import ScanCache, discover_plugins

cache = ScanCache.load("~/.cache/audio-studio/plugins.json")
for plugin in discover_plugins(cache=cache):   # platform plugin folders
    print(plugin.id, plugin.name, plugin.vendor, plugin.path)
cache.save()
```

`discover_plugins(paths)` walks each root to `max_depth` levels (4 by default),
never descends into a `.vst3`, and returns one `PluginDescriptor(id, name, path,
vendor)` per bundle, sorted by name. A bundle that predates the `moduleinfo`
convention reports its file name and an empty vendor rather than a guess.

The `ScanCache` keys each description on the bundle's size and modification
time, so rescanning a system plugin folder costs a `stat` per bundle; changed
bundles are re-read, uninstalled ones are pruned, and `force=True` re-probes
everything. `discover_plugins(..., isolate=True)` runs each probe in a
subprocess with a timeout — the same list, at the cost of an interpreter
start-up per bundle, for a probe that must not be trusted with the editor's
process. The scanner is also a command line:

```bash
python -m audio_studio.plugins.scanner                     # platform defaults
python -m audio_studio.plugins.scanner ~/.vst3 --isolate
```

`audio_studio.plugins` always imports cleanly — pedalboard is loaded lazily,
inside the single bridge module `audio_studio/plugins/pedalboard_bridge.py`,
the first time a plugin is opened. Discovery never reaches it at all. The UI
panel keeps that boundary too: it probes for the extra with
`importlib.util.find_spec`, which locates the package without executing it.
Without the extra installed, loading a plugin raises `PluginLoadError` with
installation instructions. Projects remember plugin paths, bypass flags and a
best-effort per-slot state blob, and the preview path is plugin-delay
compensated (both described under "In the application" above).

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
  is what the UI draws so a 60 Hz repaint glides instead of stepping.
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
- Crash-safe PCM-24 BWF recording from mono or stereo `PyAudio` input, with
  marker cues, numbered session takes, and a deterministic silence/tone
  `NullRecorder` for headless systems and tests.

**Editing core** (`audio_studio.core.edit_session.EditSession`)

- Copy-on-write document: an immutable list of segment views onto immutable
  chunks, so cutting ten seconds out of an hour rewrites a handful of records
  and copies nothing.
- Ten undoable commands — cut, copy, paste, delete, trim, silence, insert
  silence, gain, fade, reverse and spectral band edits — on an undo stack whose
  revisions share almost all of their storage.
- The session itself satisfies `SampleSource`, so the transport plays an
  edited document straight off the undo stack without flattening it first;
  revision publication is atomic, so a reader sees either the old or the new
  complete document, never half an edit.
- Over-budget RF64/W64 files use a streaming edit session: unchanged timeline
  segments remain references to the file, while gain/fade/silence and other
  sample-changing operations materialise only the selected ranges as sparse
  overlay chunks. Cut and paste splice those references without decoding the
  base, and undo swaps immutable sparse revisions.
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

**Spectral selection editing** (`audio_studio.dsp.spectral_edit`)

- Drag a rectangle across the spectral display to select a time span crossed
  with a frequency band; the panel reports it as a frame range plus an interval
  in hertz, with the offset of the analysed excerpt added back.
- *Attenuate Selection* (`Ctrl+Alt+A`) ducks the band by 12 dB and *Delete
  Selection* (`Ctrl+Alt+D`) removes it: an STFT is taken over the selected
  range, the bins inside the band are scaled, and the result is resynthesised
  through the same weighted overlap-add inverse the analyser uses.
- The mask is feathered across a couple of bins *outside* the band, so the
  interval the user drew is attenuated in full while the brick-wall ringing a
  hard gate produces is kept down.
- Both land on the undo stack as ordinary in-place commands, so undo restores
  the original samples bit for bit rather than resynthesising them back.

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
- Offline cubic reconstruction for hard-clipped peaks, alongside predictive
  de-clicking and mains-hum detection/removal.
- Repair suite (`audio_studio.dsp.repair`): de-hum, de-click, de-clip and
  spectral noise reduction, all as ordinary rack effects. The noise reducer
  learns a per-bin profile of the noise floor — from a dragged selection, or
  from the head of the clip — and applies a decision-directed Wiener gain
  floored at the requested reduction, so hiss drops by 24 dB by default while
  the programme comes through at its own level. It streams, at one analysis
  window of latency; `reduce_noise()` shifts that delay back out so a rendered
  buffer lines up with the original sample for sample.
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

### Large files (RF64 / W64)

Plain RIFF/WAV stores chunk sizes in 32 bits, so a recording cannot cross 4 GB
without switching container. Audio Studio reads and writes the two containers
that lift the limit — **RF64** (EBU Tech 3306; `BW64` broadcast headers are
recognised too) and **Sony Wave64** (`.w64`) — through libsndfile, and treats
their size as a first-class concern rather than an accident:

- **Detection is explicit.** `core.large_file.is_large_container()` sniffs the
  header magic (`RF64`/`BW64`/the Wave64 GUID) without touching a decoder, and
  `probe()` pins the container name from the same bytes when a libsndfile
  build labels a 64-bit WAV variant generically.
- **Frame counts are 64-bit safe.** An RF64 capture can exceed 2³¹ frames.
  `probe_frames()` and `StreamingSampleSource.n_frames` report plain Python
  `int`s (arbitrary precision), so no offset computation downstream can wrap.
- **A memory budget guards full decodes.** Decoding a file into the editor
  costs `frames × channels × 4` bytes of float32 before undo history is even
  counted. `core.large_file.check_memory_budget()` estimates that from the
  header alone and refuses files past the budget (500 MB by default,
  ~48 minutes of stereo 48 kHz) with an error that points at streaming
  playback instead of an opaque `MemoryError` minutes later.
- **The editor streams what it cannot slurp.** *File ▸ Open* on an over-budget
  file opens a `StreamingEditSession`: transport and unchanged edit ranges pull
  blocks from `StreamingSampleSource`, while cut, paste, gain and the other
  selection edits use sparse in-memory overlays. Undo never writes the base
  file. Whole-file analysis (loudness, full-clip spectrogram) is skipped under
  the same budget; selection-sized analysis still works. A current `.pk`
  sidecar supplies the full overview, and sample-level zoom reads only a
  bounded detail window around the playhead.
- **Export round-trips.** `save_audio("bounce.rf64", …)` writes RF64 (and
  `.w64` writes Wave64) whenever the local libsndfile supports it, so a
  long-form bounce is not silently truncated at 4 GB.

## Accessibility

The editor targets **WCAG 2.2 level AA** for everything it draws itself, and
the three claims below are enforced by `tests/test_accessibility.py` rather
than asserted in prose: contrast is recomputed from the live palette, the
shortcut audit walks the real menu bar, and the scale factor is checked
end to end in a fresh interpreter.

### Display scaling and HiDPI

Qt 6 picks up the desktop's own scaling, but rounds the device pixel ratio to
a whole number by default, which throws away a 125% or 150% setting. Audio
Studio switches the rounding policy to `PassThrough` before the
`QApplication` exists, so fractional display scales arrive intact, and adds an
explicit override for the cases where the desktop reports the wrong thing —
a 4K laptop panel driving an unscaled X session, or simply wanting bigger
type:

```bash
python -m audio_studio --scale-factor 1.5   # 1.0–2.0, refused outside that
QT_SCALE_FACTOR=1.25 python -m audio_studio # the same knob, from the session
```

The flag writes `QT_SCALE_FACTOR`, which Qt reads once while the application
object is constructed; passing it explicitly overrides an inherited value,
and omitting it leaves whatever the desktop session set alone. Everything in
the interface is laid out in logical pixels — no pixel geometry is hard-coded
against a physical display — so the waveform, the meters and the spectral
display scale with the chrome.

### Colour and contrast

`audio_studio.ui.theme` documents a measured contrast ratio for every colour
pair the interface actually puts on screen, and `theme.failing_pairs()` audits
a palette against the WCAG floors:

- **4.5:1** for normal-size text (SC 1.4.3). The tightest pair shipped is body
  text on a pressed or checked button at 4.99:1; the rest run from 5.16:1 to
  13.38:1.
- **3:1** for graphics and control boundaries (SC 1.4.11): waveform ink,
  meter segments, markers, playhead, and the outline that identifies a
  control. Interactive controls are outlined in a dedicated `control_border`
  grey held above 3:1 against every fill it is drawn over, rather than in the
  quieter `border` hairline used to separate chrome panels.
- Keyboard focus is a 2 px accent ring instead of Qt's default dotted
  outline, which is nearly invisible on a dark fill (SC 2.4.11 / 2.4.13).

Two colours were changed to meet that budget: `text_dim` was lightened so
secondary labels clear 4.5:1 on every surface they appear on, and the
selection fill was split in two — a selected menu row is now full-strength
accent with an inverted near-black label (6.77:1), while the darker
`accent_dim` fills pressed and checked buttons *under* unchanged body text
(4.99:1). Colour is never the only channel for state (SC 1.4.1): the meter's
clip strip paints the word `CLIP` when it lights up and says so in its
accessible description, recording carries a `●` glyph and an elapsed-time
readout, and a bypassed rack reads `FX bypassed` in the status bar.

Known deviation: the chrome fills themselves (window → panel → control)
differ by roughly 1.2:1. Depth is carried by luminance ordering, which is why
controls get an explicit outline and a focus ring rather than being
identified by their fill.

### Keyboard

Every command in the menu bar has a shortcut and no sequence is bound twice —
a test walks the menus and fails on either. **Help ▸ Keyboard Shortcuts**
(`F1`) opens the full table, generated from the live actions so it cannot
document a binding the build does not have.

| Shortcut | Action |
|---|---|
| `Ctrl+O` / `Ctrl+W` | Open / close file |
| `Ctrl+S` / `Ctrl+Alt+S` | Save project / save project as… |
| `Ctrl+Shift+O` | Open project |
| `Ctrl+Shift+H` / `Ctrl+Alt+H` | Open project archive / save project archive as… |
| `Ctrl+Shift+S` | Export as… |
| `Ctrl+Q` | Exit |
| `Ctrl+Z` / `Ctrl+Y` | Undo / redo (the platform's own Redo binding) |
| `Ctrl+X` / `Ctrl+C` / `Ctrl+V` / `Del` | Cut / copy / paste / delete |
| `Ctrl+Shift+M` / `Ctrl+T` | Silence / trim to selection |
| `Ctrl+G` / `Ctrl+R` | Apply gain… / reverse |
| `Ctrl+Shift+I` / `Ctrl+Shift+U` | Fade in / fade out |
| `Ctrl+Shift+N` | Insert silence… |
| `Ctrl+A` / `Ctrl+Shift+A` | Select all / deselect |
| `Ctrl+Alt+A` / `Ctrl+Alt+D` | Attenuate / delete the spectral selection |
| `M` / `Shift+M` | Add a marker at the playhead / a region from the selection |
| `Ctrl+Left` / `Ctrl+Right` | Go to the previous / next marker |
| `F2` / `Ctrl+Shift+Del` | Rename / remove the selected marker |
| `Ctrl+Alt+M` | Clear all markers and regions |
| `Ctrl+=` / `Ctrl+-` / `Ctrl+0` | Zoom in / out / fit |
| `Ctrl+Shift+0` | Zoom to selection |
| `Ctrl+Up` / `Ctrl+Down` | Amplitude zoom |
| `Alt+1` / `Alt+2` / `Alt+3` | Waveform / spectral / split layout |
| `Alt+4` / `Ctrl+Shift+T` | Multitrack mode / add the clip as a track |
| `Alt+=` / `Alt+-` | Multitrack zoom in / out |
| `Ctrl+Alt+1`…`Ctrl+Alt+4` | Toggle the spectral, effects, plugin and marker docks |
| `F5` | Re-run the spectral analysis |
| `Space` / `Esc` | Play-pause / stop |
| `Home` / `End` | Go to start / end of the playback region |
| `L` / `Shift+L` | Toggle loop / play selection only |
| `F1` / `Shift+F1` | Keyboard shortcuts / about |

Menu bar titles carry Alt mnemonics (`Alt+F` for File, and so on), and every
dialog is reachable and dismissable from the keyboard.

### Not covered yet

Screen-reader support is only what Qt provides by default: the shortcut sheet
sets an accessible name and description, but the custom-painted widgets — the
waveform, the spectrogram and the level meter — expose no accessible value or
text alternative, so their content is unreadable to a screen reader. There is
no high-contrast or light theme, no reduced-motion setting for the 60 Hz
playhead, and no user-configurable font size beyond `--scale-factor`.

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

## Delivery

### Project files: `.hlproj` folders and `.hlprojz` archives

A project saves as a `.hlproj` **directory**: `project.json`, a `media/` copy
of every clip the session refers to, the take registry, and cached waveform
overviews. That shape suits the application — media can be added without
rewriting a container, and a save replaces one small JSON file — and it suits
nothing else. Mailing a session, attaching it to a ticket or dropping it on a
share all want one file.

**File ▸ Save Project Archive As** (`Ctrl+Alt+H`) writes exactly that bundle
as a zipped `.hlprojz`, and **File ▸ Open Project Archive** (`Ctrl+Shift+H`)
opens one. The two representations carry the same `project.json` at the same
schema version, so a session can move between them as often as you like and
an older build still reads what comes out.

- While an archive is open, its expanded bundle lives in a scratch directory —
  that is where the media the engine plays actually sits. A plain **Save**
  (`Ctrl+S`) rewrites that bundle and repacks the archive in place; **Save
  Project As** to a folder converts the session back into a directory project;
  opening a plain audio file releases the scratch copy.
- Packing and unpacking both rename a finished temporary into place, so a
  crash or a full disk mid-save cannot cost you the archive you already had,
  and a reader never sees a half-extracted bundle at the real path.
- `backups/` — the store's timestamped copies of `project.json`, local undo of
  last resort — stays out of the archive. Pass `include_backups=True` to
  `pack_project` if you want them.
- Archives from elsewhere are treated as untrusted input: a member name that
  is absolute, that traverses out of the bundle with `..`, or that is a
  symlink fails the whole open rather than being quietly skipped.

The same operations are available headlessly:

```python
from pathlib import Path

from audio_studio.project import load_project_archive, pack_project, unpack_project

pack_project(Path("session.hlproj"), Path("session.hlprojz"))
root = unpack_project(Path("session.hlprojz"), Path("/tmp/work"))
snapshot = load_project_archive(Path("session.hlprojz"), Path("/tmp/work2"))
```

`save_project_archive()` writes a session straight to an archive without
leaving a directory behind. Round-trip coverage, atomicity under a failing
write and the hostile-archive cases live in
[`tests/test_hlprojz.py`](tests/test_hlprojz.py).

### Desktop bundle

```bash
scripts/build-linux.sh --install-deps      # first run; installs PyInstaller
scripts/build-linux.sh --clean             # afterwards
```

The result is `dist/audio-studio/`, a launcher plus its interpreter, Qt and the
numerical stack (around 280 MB unpacked). The recipe is
[`packaging/pyinstaller.spec`](../packaging/pyinstaller.spec); the script sets
the paths it expects, then checks what came out.

Those checks are the point of the script. A bundle is a distribution, and a
distribution is where the license terms of everything inside it come due:

- **One directory, never `--onefile`, and no UPX.** Qt, PySide6, Shiboken6 and
  libsndfile reach the application under the LGPL, which is satisfied only
  while a recipient can replace those libraries with their own compatible
  build. `COLLECT` leaves every shared object beside the launcher where it can
  be swapped; a one-file build would unpack to a throwaway directory on each
  launch, and UPX rewrites a shared object so it is no longer a drop-in
  target. The build fails if no Qt shared objects end up in the output.
- **No pedalboard.** It is GPL-3.0, and bundling it relicenses the entire
  artifact. The spec excludes it and the script refuses to build at all from
  an environment where it is importable, unless `ALLOW_GPL=1` says a GPL
  distribution is what you meant.
- **The notices ship inside the bundle.** `licenses/THIRD_PARTY_LICENSES.md`
  and `licenses/LGPL-RELINKING.txt` — the latter naming each LGPL component,
  where its source is, how to replace it in this bundle, and the written
  source offer — must travel with any binary that leaves the building. The
  script will not finish without them.

The bundle is host-specific: build on the oldest Linux you intend to support,
and build the macOS and Windows artifacts on their own machines. PyInstaller
itself is GPL-2.0-or-later with a bootloader exception that covers shipping
the bootloader inside this MIT application; it is a build tool, declared as
the `installer` extra, and is not a runtime dependency of what it produces.
Before publishing anything, walk the release checklist at the end of
[`THIRD_PARTY_LICENSES.md`](../THIRD_PARTY_LICENSES.md).

### Distributable packages

Three wrappers turn that bundle into something you can hand over, and each one
re-runs the bundle's license gate on its own output — the notices, the
separate LGPL shared objects, no pedalboard — because a packaging step is
another chance to lose them:

```bash
scripts/package-appimage.sh --fetch-appimagetool   # dist/*.AppImage
scripts/package-deb.sh                             # dist/*.deb
scripts/sign-linux-artifact.sh dist/*.AppImage dist/*.deb
```

- **AppImage.** The AppDir at `dist/AudioStudio.AppDir` — `AppRun`, desktop
  entry, icon, notices under `usr/share/doc` — is what the script guarantees;
  turning it into a single file needs `appimagetool`, which it will use from
  `PATH`, download with `--fetch-appimagetool`, or print the command for.
  `--appdir-only` stops at the directory, `--require-appimage` refuses to.
- **Debian package.** A skeleton, not a distribution-quality package: the
  bundle installs under `/usr/lib/audio-studio` with a wrapper in `/usr/bin`,
  a desktop entry, and `/usr/share/doc/audio-studio/copyright` alongside the
  two notice files. It depends only on the X and GL libraries Qt needs from
  the host. `--tree-only` stages without `dpkg-deb`.
- **Signing.** Linux GPG only. The script always writes a `SHA256SUMS`
  manifest and, when `SIGNING_KEY` names a key, an armoured detached
  signature per artifact which it then verifies. Without a key it still
  succeeds and records `signed: false` with the reason in
  `.agent_workspace/v1.1/linux-signing-report.json`; pass
  `--require-signature` where an unsigned release is not acceptable.

### Signing the other platforms

Each platform is signed by its own tool on its own machine, and each writes the
same shaped report so one document can describe a whole release:

```bash
scripts/sign-macos-artifact.sh --notarize dist/AudioStudio-1.1.0.dmg   # on a Mac
pwsh -File scripts/sign-windows-artifact.ps1 dist\audio-studio.exe     # on Windows
scripts/release-signing-manifest.sh                                    # anywhere
```

- **macOS.** With `MACOS_SIGNING_IDENTITY` (or `CODESIGN_IDENTITY`, which
  `scripts/build-macos.sh` also reads) the script codesigns with the hardened
  runtime and a secure timestamp and then verifies with
  `codesign --verify --strict`; `--notarize` submits through `notarytool` with
  a stored `--keychain-profile` and staples the ticket. A `.app` directory is
  described by a digest over its file tree, since a directory has no content
  hash of its own. Report:
  `.agent_workspace/v1.2/macos-signing-report.json`.
- **Windows.** With `WINDOWS_SIGNING_CERT` — a `.pfx` path or a certificate
  thumbprint in the store — the script runs `signtool` with SHA-256 and an
  RFC 3161 countersignature, then `signtool verify /pa`. Report:
  `.agent_workspace/v1.2/windows-signing-report.json`.
- **The release manifest.** `scripts/release-signing-manifest.sh` merges the
  three reports into `.agent_workspace/v1.2/release-signing-manifest.json`,
  listing `signed_platforms`, `unsigned_platforms` and `missing_reports`, and
  `--require-all-signed` fails a release that is not signed everywhere. It
  refuses a report filed under the wrong platform, and a report that claims a
  signature while none of its artifacts was verified.

None of this signs anything here. This project holds no GPG release key, no
Apple Developer ID and no Authenticode certificate, so every script takes its
unsigned path: it checksums the artifacts, records `signed: false` with the
reason, and exits 0. A credential set on a host that cannot use it — a
Developer ID off macOS, a certificate off Windows — is an error rather than a
quietly unsigned build. See
`.agent_workspace/v1.2/release-signing-evidence.md`.

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

- Single visible track/clip in the waveform workspace. `TrackPanel` is reusable,
  but the multitrack side is an MVP: lanes, clips, faders, pans, mutes/solos and
  submix buses work, and automation covers track volume only — breakpoints
  joined by straight lines, drawn in the lane the `A` button opens under a
  track's clips. There are no pan, send, clip-gain or plugin-parameter
  envelopes, no touch/latch/write modes, and no recording of fader moves.
- Waveform editing is wired through `EditSession`: cut, copy, paste, delete,
  silence, trim, gain, fade in/out, reverse, insert silence and unlimited
  undo/redo from the Edit menu. Save and reopen sessions as `.hlproj` directory
  bundles or single-file `.hlprojz` archives (File ▸ Save/Open Project, or the
  Archive commands beside them); undo history is not persisted — the saved
  document is the flattened edit result. Export remains available for one-off
  audio files.
- Recording is an MVP path: PyAudio input supports mono/stereo crash-safe BWF
  capture, cues, and numbered takes, but there is no input-device/level control,
  live monitoring, comping, or punch recording.
- Spectral selection editing covers attenuating and deleting a dragged
  rectangle. There is no healing brush, lasso or paintbrush selection, no
  spectral copy/paste, and the mask is rectangular in time as well as in
  frequency.
- Repair covers hum, clicks, clipping and stationary broadband noise. Noise
  reduction assumes the noise floor does not move: it will not follow a
  fan that changes speed, and there is no capture-noise-print command in the
  menus yet — the rack learns from the head of the clip, and a selection has
  to be handed to `NoiseReduceEffect.learn_from()` from Python. VST3 hosting is a
  three-slot rack behind the optional `plugins` extra (View ▸ VST3 Plugins),
  with a filesystem-only bundle scanner: no AU format and no plugin editor
  windows. Plugin delay compensation covers the preview chain only (bypass
  toggles stay time-aligned; the playhead readout is not shifted), and projects
  remember plugin paths, bypass flags and a best-effort per-slot state blob —
  see the roadmap in the release sign-off. Batch processing is covered by the
  `audio_studio.batch` CLI above.
- The default device block is now 256 frames (~5.3 ms at 48 kHz);
  `SoundDeviceOutput` and `PyAudioOutput` retry with 512 and then 1024 frames
  when the device rejects it. On Windows, opt-in WASAPI exclusive mode
  (`--wasapi-exclusive` or `AUDIO_STUDIO_WASAPI_EXCLUSIVE=1`) additionally
  bypasses the shared-mode mixer; `AUDIO_STUDIO_ASIO=1` prefers an ASIO device
  already exposed by the user's PortAudio runtime. These lower-latency host
  choices are not certified low-latency monitoring: the ASIO SDK and an
  ASIO-enabled PortAudio build are not shipped, per-host latency hints are not
  wired up, and no hardware round-trip measurements back the numbers.
- On the first playback, the engine collects cyclic garbage and freezes the
  existing GC-tracked object graph until shutdown to keep old objects out of
  playback-time collections. Set `AUDIO_STUDIO_RT_GC=0` to disable this
  discipline; it reduces one source of jitter but does not make CPython a
  hard-real-time runtime.
- Under/overruns are counted per stream (`SoundDeviceOutput.xruns`,
  `.underflows`, `.overflows`) but nothing surfaces them in the UI yet, and
  `PyAudioOutput` cannot report them at all. Recording still runs on PyAudio
  input regardless of which output backend is selected.
- The effect-rack preview chain runs on the feeder thread, so a heavy chain no
  longer starves the device callback — but it is processed a ring buffer ahead
  of what you hear, so a parameter or bypass change lands after the queued
  blocks drain (~85 ms at the default block and ring depth, or longer after
  device fallback). A backend opened outside the transport still processes in
  the render callback.
- The SPSC ring is lock-free at the Python level but still executes under
  CPython/GIL scheduling; physical-device p99 timing and a long soak are not
  certified by headless tests.
- The optional `mastering` extra selects soxr VHQ for offline SRC and meets the
  measured mastering gates. Without it Audio Studio stays operational through
  the lower-quality SciPy fallback; `AUDIO_STUDIO_SRC` can pin either path.
  PCM-16/24 export applies TPDF dither by default. These synthetic gates do not
  by themselves certify broadcast compliance.
- Loop playback restarts from the region start without a crossfade, and the
  reported position is briefly clamped across the wrap.
- Long files stream from disk and use sparse in-memory edit overlays. Their peak
  pyramid survives in a `.pk` sidecar between sessions; without a current
  sidecar only the bounded detail window is available. A restored overview
  resolves down to its finest cached level (256 frames per bin), then
  sample-level zoom reads the edited source around the playhead. Streaming
  edits can still consume substantial memory when the selected region itself
  is large, and saving an edit project flattens its audio.

## Release notes — v1.0.0-beta

The professional-workstation beta. Everything the alpha sign-off planned for
the v0.2 (workstation), v0.3 (VST3/repair/scale) and v1.0 (SOTA alignment)
waves has been merged; this is a **professional single-track editor with a
multitrack MVP**, positioned honestly rather than as Adobe Audition parity.

- **Highlights since v0.1.0-alpha:** crash-safe BWF recording with numbered
  takes; markers and regions; an offline batch CLI; compressor, true-peak
  limiter, gate, delay and FDN reverb; LUFS loudness match; a sounddevice
  backend and opt-in WASAPI exclusive mode; submix bus routing and per-track
  gain-automation lanes in the multitrack session; a `.pk` peak cache;
  true-peak metering certified against the EBU Tech 3341 vectors;
  a three-slot VST3 host behind the
  GPL-isolated `plugins` extra with a crash-safe scanner, per-slot state
  persistence and preview-path plugin delay compensation; spectral selection
  attenuate/delete; RF64/W64 streaming with a memory budget and sparse
  streaming edits; De-Clip and spectral noise reduction completing the repair
  suite; TPDF export dither and an SRC quality report; WCAG 2.2 AA contrast,
  fractional HiDPI scaling and full keyboard coverage with an F1 shortcut
  sheet; a 256-frame default block with real-time GC discipline and a
  headless 30-minute soak harness; single-file `.hlprojz` project archives
  and a desktop-bundle scaffold with the LGPL obligations wired into the
  build; opt-in ASIO host selection (no SDK bundled); reusable JSON edit
  macros in the batch CLI.
- **Known limitations:** the *Known limitations* section above is the
  authoritative list. Headline gaps: the synthetic EBU 3341/3342 vectors
  pass but there is no AES17 harness or real-material compliance evidence;
  the optional soxr VHQ SRC path is synthetic-test qualified but not a
  broadcast certification; multitrack automation covers track gain only and
  there is no mixer console; recording has no device/level control
  or monitoring; custom-painted widgets are not screen-reader readable; and
  all performance/soak numbers are headless proxies — no physical-device
  round-trip or soak certification.
- **System requirements:** Python ≥ 3.10 (3.12 is the verified baseline);
  `numpy`, `scipy`, `soundfile`, `PySide6-Essentials`; optional
  `sounddevice`/`PyAudio` (hardware output/input; falls back to simulated
  devices without them), `ffmpeg` (extended decode), `soxr` (`mastering`
  extra) and `pedalboard` (`plugins` extra, GPL-3.0 — see the license
  notice). On headless Linux install the Qt runtime libraries listed under
  *Install*.
- **Release gates:** the beta ships as a source tag once Audio CI is green on
  the release HEAD; there is no installer, signing or SBOM yet. Honest
  positioning, the full gap register and post-beta priorities:
  [`.agent_workspace/v1.0/FINAL_RELEASE_SUMMARY.md`](../.agent_workspace/v1.0/FINAL_RELEASE_SUMMARY.md).
  History for every wave, including the untagged 0.2.0/0.3.0 milestones:
  [`CHANGELOG.md`](../CHANGELOG.md).
