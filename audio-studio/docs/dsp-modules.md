# DSP Modules

Reference for `audio_studio.dsp` (spectral analysis, effects) and the Qt
spectrogram view in `audio_studio.ui`. Adobe Audition is the behavioural
reference: a full-scale sine reads 0 dBFS, the spectral display defaults to a
logarithmic frequency axis, and fades offer the same curve family.

---

## Contents

- [Buffer conventions](#buffer-conventions)
- [Windows](#windows)
- [SpectralAnalyzer](#spectralanalyzer)
  - [Configuration](#configuration)
  - [Resolution](#resolution)
  - [Calibration and scaling](#calibration-and-scaling)
  - [Spectrogram](#spectrogram)
  - [Inverse transform](#inverse-transform)
- [Real-time analysis](#real-time-analysis)
  - [RealtimeSpectrum](#realtimespectrum)
  - [WaterfallBuffer](#waterfallbuffer)
- [Effects](#effects)
  - [The Effect contract](#the-effect-contract)
  - [ThreeBandEQ / ParametricEQ](#threebandeq--parametriceq)
  - [GainEffect](#gaineffect)
  - [NormalizeEffect](#normalizeeffect)
  - [FadeEffect](#fadeeffect)
  - [EffectChain](#effectchain)
- [SpectrogramWidget](#spectrogramwidget)
- [Performance](#performance)
- [Testing](#testing)

---

## Buffer conventions

Every public entry point speaks **planar** audio: a `(n_channels, n_samples)`
float array. Mono may be passed as a plain 1-D `(n_samples,)` array, and the
same shape comes back out.

File and device libraries hand back **interleaved** `(n_samples, n_channels)`
frames, so convert at the boundary:

```python
from audio_studio.dsp import as_planar, as_interleaved

planar, was_mono = as_planar(frames_from_soundfile)   # auto-detects layout
frames = as_interleaved(planar)                        # back for playback
```

Passing `channels_last=True` skips the heuristic when the layout is known.
Integer input is promoted to `float32`; `float32` and `float64` are both carried
through end to end.

---

## Windows

`audio_studio.dsp.windows` generates windows in **periodic (DFT-even)** form,
which is the correct choice for spectral analysis and for overlap-add
resynthesis. Verified sample-for-sample against
`scipy.signal.get_window(..., fftbins=True)`.

| `WindowType` | ENBW (bins) | Sidelobes | Use for |
|---|---|---|---|
| `RECTANGULAR` | 1.00 | -13 dB | Transient onsets, exact-periodic signals |
| `BARTLETT` | 1.33 | -27 dB | Cheap general purpose |
| `HAMMING` | 1.36 | -43 dB | Closely spaced tones of similar level |
| `HANN` | 1.50 | -32 dB | Default; good all-round compromise |
| `BLACKMAN` | 1.73 | -58 dB | Weak tone next to a strong one |
| `NUTTALL` | 1.98 | -93 dB | Very high dynamic range |
| `BLACKMAN_HARRIS` | 2.00 | -92 dB | Very high dynamic range |
| `FLATTOP` | 3.77 | -69 dB | Amplitude measurement (< 0.02 dB error off-bin) |

Each window carries the two sums all calibration derives from — `S1 = sum(w)`
(coherent gain) and `S2 = sum(w**2)` (noise gain):

```python
from audio_studio.dsp import window_info

info = window_info("blackman", 2048)
info.enbw_bins            # 1.727
info.enbw_hz(48_000, 2048)  # 40.5 Hz
```

Names are coerced leniently, so `"hanning"`, `"Hann"`, `"blackman-harris"` and
`"boxcar"` all resolve.

---

## SpectralAnalyzer

```python
from audio_studio.dsp import SpectralAnalyzer

analyzer = SpectralAnalyzer(sample_rate=48_000, fft_size=2048, window="hann")
spectrogram = analyzer.spectrogram(audio)
print(analyzer.config.describe())
# 2048-pt hann @ 48000 Hz, hop 512 (75% overlap), df=35.16 Hz, dt=42.7 ms, 93.8 fps, amplitude
```

The analyzer holds no per-signal state, so one instance can be shared across
threads and reused for every buffer matching its config.

### Configuration

`SpectralConfig` is a frozen dataclass; `config.with_(fft_size=4096)` returns a
modified copy and `analyzer.reconfigure(fft_size=4096)` applies changes in place.

| Field | Default | Meaning |
|---|---|---|
| `sample_rate` | `48000.0` | Hz |
| `fft_size` | `2048` | Transform length; sets bin spacing |
| `hop_size` | `None` | Frame advance; `None` = 25% of window (75% overlap) |
| `window_size` | `None` | Window length; `None` = `fft_size`. Shorter zero-pads |
| `window` | `HANN` | See [Windows](#windows) |
| `scaling` | `AMPLITUDE` | See [Calibration](#calibration-and-scaling) |
| `reference` | `1.0` | Amplitude mapping to 0 dB (`1.0` gives dBFS) |
| `db_floor` | `-140.0` | Lower clamp on every dB conversion |
| `center` | `True` | Pad by half a window so frame *m* is centred on sample `m*hop` |
| `pad_mode` | `"constant"` | `numpy.pad` mode for the centring pad |
| `dtype` | `float32` | `float32` is ~2.4x faster than `float64` |
| `fft_workers` | `-1` | `scipy.fft` threads; `-1` = all cores |
| `max_frames_per_chunk` | `4096` | Caps peak memory on long files |

`center=True` is what makes spectrogram columns line up with the waveform
underneath them, and is the default for that reason.

### Resolution

Bin spacing and resolution are different numbers, and the config exposes both:

```python
config.bin_spacing_hz            # sample_rate / fft_size — the grid
config.frequency_resolution_hz   # ENBW-based — what can actually be told apart
config.time_resolution_s         # window duration — temporal smearing
config.hop_seconds               # spacing between columns
config.frame_rate                # columns per second
config.overlap_ratio             # 0.0 .. 1.0
```

Zero-padding (`window_size < fft_size`) shrinks `bin_spacing_hz` without
touching `frequency_resolution_hz` — it interpolates the spectrum onto a finer
grid, which sharpens peak-position estimates but resolves nothing new.

Construct from the requirement rather than from the FFT size:

```python
# "I need to tell apart tones 10 Hz apart"
config = SpectralConfig.for_frequency_resolution(48_000, 10.0, window="hann")
config.fft_size                     # 8192
config.frequency_resolution_hz      # 8.79 Hz

# "I need 20 ms of temporal precision"
config = SpectralConfig.for_time_resolution(48_000, 0.02)
config.fft_size                     # 512
```

`for_frequency_resolution` accounts for the window's ENBW, so asking for 20 Hz
with a Blackman window yields a longer transform than with Hann rather than
silently under-delivering.

### Calibration and scaling

| `SpectrumScaling` | Sinusoid of amplitude A reads | dB conversion |
|---|---|---|
| `AMPLITUDE` (default) | `A` | `20*log10` |
| `POWER` | `A**2 / 2` | `10*log10` |
| `PSD` | `V**2 / Hz` | `10*log10` |

The guarantee: **a full-scale sine reads 0 dBFS regardless of window, FFT size
or overlap.** One-sided folding doubles every bin except DC and Nyquist, and
window gain is divided back out via `S1` (amplitude) or `S2` (PSD).

Use `PSD` to compare noise floors across different FFT sizes; unlike the other
two it is independent of transform length.

An off-bin tone still loses *scalloping* — up to 1.42 dB for Hann, 0.02 dB for
flat-top. That is the window's shape, not a calibration error, and is the
reason `FLATTOP` exists.

### Spectrogram

```python
spec = analyzer.spectrogram(audio)     # (n_channels, n_frames, n_bins)

spec.db()                # mono mix in dB, (n_frames, n_bins)
spec.db(channel=0)       # one channel
spec.to_db()             # all channels, (n_channels, n_frames, n_bins)
spec.mono()              # power-averaged linear values
spec.frequencies         # (n_bins,) Hz
spec.times               # (n_frames,) s, frame centres
spec.duration

spec.frame_at(1.5)                  # spectrum nearest t=1.5 s
spec.bin_at(1000.0)                 # level of the 1 kHz bin over time
spec.peak_frequencies()             # dominant frequency per frame, sub-bin
spec.band_energy(200.0, 2000.0)     # energy per frame in a band
```

`peak_frequencies()` fits a parabola across the three highest bins, which
recovers roughly 10x better than the raw bin spacing for stationary tones — a
1 kHz tone analysed with 11.7 Hz bins locates to within 1 Hz.

Channel averaging in `mono()` happens in the power domain, so correlated
channels do not cancel.

### Inverse transform

`istft` performs weighted overlap-add using the analysis window as the
synthesis window and dividing by the summed squared window:

```python
stft = analyzer.stft(audio)
restored = analyzer.istft(stft, length=audio.shape[-1])
```

Reconstruction is exact to floating point (`< 1e-9`) wherever the overlap-add
denominator is non-zero, which means **there is no COLA restriction on the hop
size** — a hop of 333 samples round-trips as cleanly as 512. With
`center=False` the final `< hop` samples fall outside every frame and cannot be
reconstructed; `center=True` covers the whole signal.

---

## Real-time analysis

### RealtimeSpectrum

Feed it arbitrary-sized blocks; it emits one smoothed spectrum per hop and
maintains falling peak-hold markers, the behaviour of a hardware RTA.

```python
from audio_studio.dsp import RealtimeSpectrum

meter = RealtimeSpectrum(
    sample_rate=48_000, fft_size=2048, hop_size=512,
    attack_ms=10.0,        # fast rise, so transients register
    release_ms=300.0,      # slow fall, so the display does not flicker
    peak_hold_s=1.5,
    peak_decay_db_s=20.0,
)

for block in audio_callback_blocks:      # any length
    if meter.push(block):                # returns frames produced
        levels = meter.levels_db         # per-bin, smoothed
        peaks = meter.peaks_db           # peak-hold markers
        bars = meter.bars(n_bands=31)    # log-spaced band aggregation
```

`bars()` returns `SpectrumBars` with `centers`, `edges`, `values_db` and
`peaks_db`. Bands **sum energy** rather than averaging dB, so a band containing
two equal tones reads 3 dB hotter than one containing a single tone. That is
physically correct for a band-limited meter, but it also means white noise
slopes upward across log-spaced bands by design; compare against a reference
rather than reading the raw shape as flatness.

Bands narrower than one bin fall back to the nearest bin rather than reading
`-inf`, so `n_bands=200` on a 256-point FFT still produces finite values.

Stereo input is collapsed into a single display spectrum in the power domain.

### WaterfallBuffer

Fixed-capacity ring buffer of dB frames. Pushing is `O(n_bins)` and reading
returns a contiguous, oldest-first view, so a repaint never shifts the history.

```python
from audio_studio.dsp import WaterfallBuffer

history = WaterfallBuffer(n_bins=analyzer.n_bins, capacity=512, fill_db=-140.0)
history.push(meter.levels_db.astype("float32"))
image = history.image()                  # (512, n_bins), oldest first
recent = history.image(rows=128, newest_first=True)
```

Unwritten slots hold `fill_db`, so the array is always exactly `rows` tall and
safe to hand straight to a renderer.

---

## Effects

### The Effect contract

Two processing modes, required to agree:

```python
out = effect.process(audio, sample_rate)              # offline, whole buffer
out = effect.process_block(block, sample_rate)        # streaming, keeps state
```

**Concatenating the streaming output of a signal split into blocks equals the
offline result for that signal.** Every effect is tested for this, because a
mismatch is exactly the class of bug that only shows up as clicks at buffer
boundaries during playback.

Effects needing the whole signal (`NormalizeEffect` must see the global peak,
`FadeEffect` must know the total length) set `is_offline_only = True` and raise
from `process_block`.

Other shared members: `enabled`, `prepare(sample_rate, n_channels)`, `reset()`,
`parameters()` (a serialisable dict for presets and undo). `process()` never
modifies its input.

### ThreeBandEQ / ParametricEQ

Cascaded RBJ Audio EQ Cookbook biquads run through `scipy.signal.sosfilt` in
second-order-section form, which stays numerically well-behaved at low corner
frequencies. State is per-channel and zero-initialised, so the impulse response
is the filter's actual impulse response.

```python
from audio_studio.dsp import ThreeBandEQ

eq = ThreeBandEQ(
    low_frequency=100.0,  low_gain_db=3.0,  low_q=0.707,    # low shelf
    mid_frequency=1000.0, mid_gain_db=-4.0, mid_q=1.0,      # peaking bell
    high_frequency=8000.0, high_gain_db=2.0, high_q=0.707,  # high shelf
    output_gain_db=0.0,
)
processed = eq.process(audio, 48_000)

eq.set_mid(frequency=2500.0, gain_db=-6.0, q=2.0)
eq.low.enabled = False
```

Draw the curve a UI shows with the same coefficients the audio gets:

```python
frequencies, magnitude_db = eq.response_curve(48_000, n_points=512)
eq.magnitude_response_db(np.array([1000.0]), 48_000)
eq.frequency_response(frequencies, 48_000)   # complex, for a phase trace
```

The predicted curve is tested against gain measured from real audio at 0.2 dB.

`ParametricEQ` takes any number of `EQBand`s, each with an independent
`FilterType`:

| `FilterType` | Uses `gain_db` | Notes |
|---|---|---|
| `PEAKING` | yes | Bell. `gain_db` at the centre frequency |
| `LOW_SHELF` / `HIGH_SHELF` | yes | `gain_db/2` at the corner, full gain in the band |
| `LOW_PASS` / `HIGH_PASS` | no | 12 dB/octave per band |
| `BAND_PASS` | no | Constant 0 dB peak gain |
| `NOTCH` | no | Deep null at the centre |
| `ALL_PASS` | no | Flat magnitude, phase rotation only |

`EQBand.bandwidth_octaves()` and `set_bandwidth_octaves()` convert to and from
Q for UIs that expose bandwidth instead. Coefficients are cached and rebuilt
only when a parameter changes.

### GainEffect

```python
from audio_studio.dsp import GainEffect

GainEffect(gain_db=-6.0).process(audio, 48_000)
GainEffect(gain_db=0.0, invert_polarity=True)     # phase flip
```

Changing `gain_db` mid-stream glides over `ramp_ms` (default 5 ms) at the start
of the next block instead of stepping, which removes the click without the
caller scheduling anything. Offline `process()` resets state first and applies
a single constant gain.

### NormalizeEffect

```python
from audio_studio.dsp import NormalizeEffect, measure_levels

NormalizeEffect(target_db=-1.0, mode="peak")
NormalizeEffect(target_db=-1.0, mode="true_peak")            # ITU-R BS.1770
NormalizeEffect(target_db=-20.0, mode="rms", ceiling_db=-1.0)
NormalizeEffect(target_db=-1.0, per_channel=True)            # multi-mono stems
```

| Mode | Drives to target | When |
|---|---|---|
| `PEAK` | Sample peak | Fast; what "Normalize to 0 dB" means in most editors |
| `TRUE_PEAK` | 4x oversampled peak | Before delivery — sample-peak 0 dBFS routinely clips a DAC or lossy encoder on inter-sample overshoot |
| `RMS` | Root-mean-square | Rough loudness match; pair with `ceiling_db` |

`per_channel=False` (default) applies one gain to every channel and preserves
the stereo image. `max_gain_db` (default 60) bounds how far digital silence
adjacent to a very quiet signal can be boosted; exact silence is left alone.
`applied_gain_db` reports what the last call chose.

`measure_levels(audio)` returns peak, true peak, RMS, crest factor and
per-channel peaks, all in dBFS.

### FadeEffect

```python
from audio_studio.dsp import FadeEffect, fade_envelope, apply_fade

FadeEffect(fade_in_s=0.5, fade_out_s=1.0, shape="cosine", curve=0.0)
apply_fade(audio, 48_000, fade_in_s=0.01)            # one-shot helper
fade_envelope(4096, "equal_power", fade_in=True)     # the raw gain ramp
```

| `FadeShape` | Curve | Use for |
|---|---|---|
| `LINEAR` | Straight amplitude ramp | Short de-click fades |
| `LOGARITHMIC` | Straight line in dB from `floor_db` | Long fades; sounds most even |
| `EXPONENTIAL` | Squared ramp | Stays quiet longer, rushes at the end |
| `COSINE` | Raised-cosine S-curve | Joins surrounding audio with no slope break |
| `EQUAL_POWER` | Square-root ramp | Crossfades — two of these hold constant power |

`curve` in `[-1, 1]` skews any shape without moving its endpoints, matching the
draggable curve handle in a DAW. A fade-out is the exact mirror of a fade-in of
the same length, so the two sum to a click-free crossfade. Overlapping fades
(in + out longer than the signal) are shrunk proportionally rather than
double-attenuating the middle.

`effect.envelope(n_samples, sample_rate)` exposes the full gain curve so a
waveform view can draw the fade handles.

### EffectChain

```python
from audio_studio.dsp import EffectChain

chain = EffectChain([
    ThreeBandEQ(low_gain_db=3.0, high_gain_db=-2.0),
    NormalizeEffect(target_db=-1.0, mode="true_peak"),
    FadeEffect(fade_in_s=0.01, fade_out_s=0.05),
])
processed = chain.process(audio, 48_000)
```

Chains are themselves `Effect`s, so they nest. A chain reports
`is_offline_only` as soon as any enabled member does, which keeps the streaming
contract honest rather than failing halfway through a block. Disabled members
are skipped.

---

## SpectrogramWidget

`audio_studio.ui.spectrogram_widget` renders a dB matrix as a colour-mapped
heat map with calibrated axes and a hover read-out.

```python
from audio_studio.ui import SpectrogramWidget, FrequencyScale

widget = SpectrogramWidget()
widget.set_spectrogram(analyzer.spectrogram(audio))
widget.set_colormap("audition")
widget.set_frequency_scale(FrequencyScale.LOG)
widget.set_frequency_range(20.0, 20_000.0)
widget.auto_scale(percentile=99.9, floor_range_db=90.0)

widget.cursorMoved.connect(lambda t, f, db: status.showMessage(f"{t:.3f}s {f:.0f}Hz {db:.1f}dB"))
widget.positionClicked.connect(seek_to)
```

Waterfall mode scrolls live frames instead:

```python
widget.start_waterfall(analyzer.frequencies, history=512,
                       frame_interval_s=analyzer.config.hop_seconds)
widget.push_frame(meter.levels_db.astype("float32"))
```

**Colormaps** (`audio_studio.ui.colormaps`) are stored as a handful of RGB
control points and expanded on demand into 256-entry `uint8` LUTs:
`audition` (default, black -> blue -> magenta -> orange -> white),
`viridis`, `magma`, `inferno`, `grayscale`, `ice`, and `jet`. All but `jet` are
monotonic in luminance, so level maps to brightness without reversal; `jet`
stays on the menu because it is still the fastest way to spot a narrow line.
`colorize(values, v_min, v_max, name)` applies a LUT to any array and needs no
Qt.

**Downsampling is max-pooled, not sub-sampled.** The dB matrix is reduced onto
the widget's pixel grid with `numpy.maximum.reduceat` before colourisation, so
a 10-minute file paints as fast as a 1-second one *and* a single hot bin
survives being zoomed out instead of aliasing away. Where the view is zoomed in
past one sample per pixel the same call degenerates to nearest-neighbour, which
is the wanted behaviour there.

`render_image(width, height)` is separate from `paintEvent`, so the renderer
can be exercised headlessly and reused for thumbnails and export.

---

## Performance

Measured on 4 vCPU x86-64, Python 3.12.3, NumPy 2.4.4, SciPy 1.18.1. Reproduce
with `python benchmarks/bench_stft.py [--duration N] [--json out.json]`.

### Headline: 60 s of 48 kHz stereo, FFT 2048, hop 512, Hann, float32

| | |
|---|---|
| Median | **37.7 ms** |
| Best | 34.7 ms |
| Realtime factor | **1593x** |
| CPU per second of audio | 0.63 ms |
| Output | 5626 frames x 1025 bins x 2 channels |

### STFT across transform sizes (60 s stereo, 75% overlap)

| FFT | Frames | Median | x realtime | Resolution |
|---|---|---|---|---|
| 512 | 22501 | 31.4 ms | 1914x | 140.6 Hz |
| 1024 | 11251 | 34.2 ms | 1753x | 70.3 Hz |
| 2048 | 5626 | 37.7 ms | 1593x | 35.2 Hz |
| 4096 | 2813 | 31.1 ms | 1932x | 17.6 Hz |
| 8192 | 1407 | 31.9 ms | 1882x | 8.8 Hz |
| 16384 | 704 | 31.8 ms | 1888x | 4.4 Hz |

Cost is nearly flat in FFT size because total sample throughput is fixed by the
overlap, not by the transform length.

### What actually costs time

| Lever | Effect |
|---|---|
| Overlap 0% -> 87.5% | 10.7 ms -> 71.7 ms (frame count is the dominant term) |
| `float32` -> `float64` | 33.9 ms -> 80.0 ms (2.4x) |
| 1 -> 4 FFT workers | 55.8 ms -> 32.8 ms (1.7x; saturates at 4 on this box) |

### Pipeline stages (60 s stereo, FFT 2048)

| Stage | Median | x realtime |
|---|---|---|
| `stft` | 34.8 ms | 1726x |
| `spectrogram` (calibrated) | 45.8 ms | 1310x |
| `spectrogram` -> dB | 94.1 ms | 638x |
| `istft` | 43.7 ms | 1374x |

### Effects (60 s stereo, offline)

| Effect | Median | x realtime |
|---|---|---|
| 3-band EQ | 34.9 ms | 1717x |
| Normalize (peak) | 3.4 ms | 17448x |
| Normalize (true peak) | 356.3 ms | 168x |
| Fade in/out | 3.8 ms | 15666x |
| Full chain | 402.9 ms | 149x |

True-peak normalisation dominates a chain: it polyphase-upsamples the entire
buffer 4x just to find a maximum.

### Real-time and rendering

| Case | Median | Note |
|---|---|---|
| Meter, 128-sample blocks | 58.9 ms / 10 s audio | 170x realtime, 2.7 ms callbacks |
| Meter, 1024-sample blocks | 47.7 ms / 10 s audio | 209x realtime |
| Render 640x360 | 25.6 ms | 39 fps |
| Render 1280x720 | 44.4 ms | 23 fps |
| Render 1920x1080 | 70.7 ms | 14 fps |

---

## Testing

```bash
cd audio-studio
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_windows.py \
    tests/test_spectral.py tests/test_effects.py \
    tests/test_spectrogram_widget.py tests/test_dsp_integration.py

# every example in this document's API sections is also a runnable doctest
python -m pytest --doctest-modules audio_studio/dsp
```

284 tests plus 5 doctests. Signal generators live in `tests/signals.py`. The
suite is written
to check behaviour against analytic expectations rather than against the
implementation:

- Windows are compared sample-for-sample with `scipy.signal.get_window`.
- Calibration is asserted against known sine amplitudes (`0.5` -> `-6.02 dBFS`),
  Parseval's theorem, and the analytic PSD of white noise.
- EQ response is measured from **processed audio** and from the **impulse
  response**, then compared to the curve the UI would draw — three independent
  paths that have to agree.
- Streaming output is asserted equal to offline output for every streamable
  effect.
- The widget is rendered offscreen and the resulting pixels are checked: a
  boosted band must be brighter, a 2 kHz tone must land at the right height on
  a log axis, a one-bin line must survive being zoomed out.

Edge cases with dedicated coverage: empty buffers, input shorter than one
window, DC and Nyquist (the two bins one-sided folding must not double), exact
digital silence, 1/2/6 channels, six sample rates from 8 kHz to 192 kHz, and
extreme EQ settings that must not produce NaN.
