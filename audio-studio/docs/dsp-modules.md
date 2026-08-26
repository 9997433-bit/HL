# DSP Modules

Reference for `audio_studio.dsp` (spectral analysis, effects, loudness) and the
Qt spectral view in `audio_studio.ui`. Adobe Audition is the behavioural
reference: a full-scale sine reads 0 dBFS, the spectral display defaults to a
logarithmic frequency axis, and fades offer the same curve family. Loudness and
true peak follow ITU-R BS.1770-4 and EBU R 128 instead, because those are
written down.

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
  - [Bypass and wet/dry](#bypass-and-wetdry)
  - [ThreeBandEQ / ParametricEQ](#threebandeq--parametriceq)
  - [GainEffect](#gaineffect)
  - [NormalizeEffect](#normalizeeffect)
  - [FadeEffect](#fadeeffect)
  - [EffectChain](#effectchain)
  - [Live preview](#live-preview)
- [Loudness](#loudness)
- [SpectrogramWidget](#spectrogramwidget)
- [Application integration](#application-integration)
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
modifies its input, and neither does a pass-through: an effect that is bypassed
or fully dry still returns a fresh array rather than the caller's buffer.

### Bypass and wet/dry

Every effect carries the two controls a mixer insert has:

```python
effect.bypass = True     # out of the path; the inverse of effect.enabled
effect.mix = 0.35        # 0.0 dry .. 1.0 wet, clamped
```

`mix` crossfades the effect's **output against its own input**, so a member
halfway down a chain blends against what reached it rather than against the
original file. Both controls appear in `parameters()`, so a preset round-trips
them, and both work identically offline and streaming.

The two are not interchangeable. `bypass` skips the processing entirely, which
is what an A/B comparison wants; `mix = 0.0` still runs the effect (keeping its
filter state warm) and throws the result away, which is what a parallel-blend
control wants.

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

#### True peak by candidate window

Oversampling a whole file 4x to find one maximum is the wrong shape of work,
and it made `TRUE_PEAK` the slowest thing in the library at 356 ms per minute
of stereo. `true_peak_level` instead interpolates only where the peak can be.

An interpolated sample is a weighted sum of the 13 input samples around it, so
its magnitude is bounded by the kernel's L1 norm times the largest of them.
That norm is a property of the filter, not a guess:

```python
from audio_studio.dsp import true_peak_candidate_db

true_peak_candidate_db(4)    # -5.64 dB
```

Audio whose local maximum sits below `sample_peak - 5.64 dB` therefore *cannot*
host the true peak, and is skipped. The scan runs on 512-sample blocks (one
strided reduction, ~1 ms per channel-minute), surviving blocks are merged into
windows padded by 64 samples, and each window reads its filter context straight
out of the source array — so a window edge is not a signal edge and the answer
is identical to interpolating everything. `true_peak_level(audio, exact=True)`
does interpolate everything, and the tests assert the two agree on tones,
noise, clicks, fades, DC and stereo material.

When the surviving windows would cost more than one contiguous pass (dense,
loud programme material, where nothing can be skipped) the whole channel is
interpolated instead, so the shortcut never loses to the thing it replaced:

| Material | Before | Now |
|---|---|---|
| Dense mix, 60 s stereo | 356 ms | 45 ms |
| Steady loud tone (worst case) | 356 ms | 47 ms |
| Fade-in | 356 ms | 23 ms |
| Quiet passages, occasional transients | 356 ms | 5 ms |

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

Chains are themselves `Effect`s, so they nest, and they have the same `bypass`
and `mix` controls as their members — the chain's `mix` is the "amount" knob on
a mastering insert, crossfading the whole rack against the audio that went into
it. Disabled members are skipped; `chain.active` lists the ones that are not.

The rack can be edited while it is running:

```python
chain.add(GainEffect(gain_db=-3.0))     # prepared for the live format on the way in
chain.insert(0, ThreeBandEQ())
chain.move(0, 2)                        # order matters: EQ before a limiter is not the same
chain.remove(effect)
chain.clear()
```

**Streaming a rack that contains an offline-only member.** By default the chain
skips it — an EQ can be auditioned while a normaliser waits for render, which
is what a live preview needs. Pass `skip_offline_in_stream=False` for the
strict contract, where the chain reports `is_offline_only` as soon as any
enabled member does and `process_block` raises instead:

```python
EffectChain([eq, NormalizeEffect()]).process_block(block, 48_000)          # EQ only
EffectChain([eq, NormalizeEffect()], skip_offline_in_stream=False)         # raises
```

### Live preview

`EffectPreview` runs a chain on the device render path, so a rack can be
auditioned against playback without touching the clip in memory. It wraps an
`AudioOutput` rather than reaching into the transport, which means no engine
code knows it is there and every backend works the same way:

```python
from audio_studio.dsp import EffectPreview

preview = EffectPreview(engine.output, chain)
engine = AudioEngine(preview)          # or ui.attach_preview(engine, chain)
```

Every block the device pulls goes through the chain on its way out. Bypassing
returns the original audio on the next block, which is the difference between
auditioning a setting and committing to it. Processing happens on the device
thread, so two things are deliberately non-fatal there:

- an effect that raises costs **one dry block**, not the stream —
  `failed_blocks` and `last_error` record it for the UI to report;
- offline-only members are skipped rather than raising, per the chain rule
  above.

`is_active` says whether the rack will change anything on the next block
(enabled, non-empty, `mix > 0`), and every other attribute is proxied to the
wrapped backend so `NullOutput.pump` or a device's `latency` keep working.

---

## Loudness

`audio_studio.dsp.loudness` implements ITU-R BS.1770-4 / EBU R 128. Loudness is
not level: two masters can share a peak of -1 dBFS and sit 6 LU apart, which is
why delivery specs are written in LUFS (-14 for most streaming platforms, -23
for broadcast).

```python
from audio_studio.dsp import LoudnessMeter, format_lufs

meter = LoudnessMeter(48_000)
report = meter.integrated(audio)          # just the headline number, in LUFS
report = meter.analyze(audio)             # everything, in one pass

report.integrated_lufs                    # gated programme loudness
report.short_term_max_lufs                # 3 s window
report.momentary_max_lufs                 # 400 ms window
report.loudness_range_lu                  # EBU Tech 3342 LRA
report.true_peak_dbtp, report.sample_peak_dbfs
report.target_offset_lu(-14.0)            # how far from a delivery target
format_lufs(report.integrated_lufs)       # "-23.0 LUFS", or "-∞ LUFS" for silence
```

The four stages, and what each is for:

| Stage | Detail |
|---|---|
| K-weighting | +4 dB high shelf at 1682 Hz (head response) into a 38 Hz high-pass (ear insensitivity). At 48 kHz the coefficients match BS.1770-4 Tables 1 and 2 to 1e-6 |
| 400 ms blocks, 75% overlap | Mean square per block, computed from one cumulative sum per channel so a 60-minute file costs the same per block as a short one |
| Channel weighting | Surrounds count 1.41x (+1.5 dB); the LFE of a 5.1 layout is excluded entirely. `channel_weights(n)` for 1-6 channels, or pass your own to the meter |
| Two-stage gating | Blocks below -70 LUFS absolute are dropped, then blocks more than 10 LU below the ungated mean. Gating is what stops the silence between dialogue dragging a programme's reading down |

The filter is **re-derived from the analog prototypes** at whatever sample rate
it is asked for rather than resampling the published table, so 44.1 kHz and
96 kHz are as correct as 48 kHz. Coefficients are cached per rate.

Time series are available for a meter display, as `(times, lufs)` with times at
the block *end*:

```python
times, lufs = meter.momentary(audio)
times, lufs = meter.short_term(audio)
```

Digital silence reads `-inf` rather than a large negative number, because the
distinction matters to a compliance check.

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
the widget's pixel grid before colourisation, so a 10-minute file paints as
fast as a 1-second one *and* a single hot bin survives being zoomed out instead
of aliasing away. Where the view is zoomed in past one sample per pixel the
reduction degenerates to nearest-neighbour, which is the wanted behaviour
there. The result is `numpy.maximum.reduceat` semantics element for element,
but computed as one gather per offset-within-a-segment: segments here are a few
rows each and there are thousands of them, which is the case `reduceat` handles
worst, and the difference is 33 ms against 6 ms for a minute of audio at
1920 px.

**Two render caches, because the axes go stale for different reasons.**

| Cache | Keyed on | Survives |
|---|---|---|
| Column-reduced `(width, n_bins)` | data version, pixel width | palette, dB range, height, frequency zoom, scale |
| Row-reduced `(height, width)` | the above plus height, scale, frequency range | palette, dB range |

So changing the colormap or dragging the dynamic range re-runs only the
colourisation, and a frequency zoom or a vertical resize re-pools rows over the
already-reduced columns instead of touching the STFT. On a 1080p view of a
one-minute file that is 34 ms for the first paint and 18 ms for a palette
change, against 64 ms for everything before the caches existed.

`reduced_matrix(width, height)` exposes the pooled grid, and
`render_image(width, height)` is separate from `paintEvent`, so the renderer
can be exercised headlessly and reused for thumbnails and export.

---

## Application integration

`audio_studio.ui.main_window` wires the pieces above into the editor.

**Spectral view.** `SpectrumPanel` (a `SpectrogramWidget` plus its controls)
lives in a `QDockWidget` along the bottom. It owns its analysis: the FFT size
is a control, and the hop widens with the length of the audio so that a
ten-minute file produces about as many columns as a ten-second one — past
`MAX_ANALYSIS_FRAMES` (4096) the extra columns cannot reach the screen anyway.

```python
from audio_studio.ui import SpectrumPanel

panel.analyze(audio, sample_rate, offset_s=selection_start_s)
panel.seekRequested    # click position, in clip time — the offset is added back
panel.readoutChanged   # hover read-out for the status bar
panel.fftSizeChanged   # the owner re-runs the analysis
```

The window analyses the **selection** when there is one and the whole clip
otherwise, debounced by 150 ms so that a drag emitting a selection per mouse
move does not start a transform per event.

**View modes** are exclusive, on `Alt+1` / `Alt+2` / `Alt+3`:

| Mode | Waveform editor | Spectral dock |
|---|---|---|
| `waveform` | shown | hidden |
| `spectrum` | hidden | shown |
| `split` (default) | shown | shown |

**Effect rack.** `EffectRackPanel` docks to the right and drives the live
`EffectChain` through `EffectPreview`. Every control writes straight into the
effect objects the device thread is already reading, so a move is audible on
the next block: there is no apply step, and nothing is written back to the clip
until the user renders. The rack a session starts with is
`default_preview_chain()` — a flat 3-band EQ into a trim, both of which stream.

**Status bar.** Integrated loudness and true peak of the loaded clip, plus a
one-line summary of the rack (`FX: 3-Band EQ → Gain @ 50% wet`, or
`FX bypassed`). The measurement runs on a worker thread and is collected by the
UI tick, because K-weighting and gating a ten-minute file takes over a second
and a slot is the wrong place to spend it.

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

| Effect | Median | x realtime | Was |
|---|---|---|---|
| 3-band EQ | 36.1 ms | 1663x | 34.9 ms |
| Normalize (peak) | 3.4 ms | 17770x | 3.4 ms |
| Normalize (true peak) | **46.9 ms** | 1280x | 356.3 ms |
| Fade in/out | 4.0 ms | 15021x | 3.8 ms |
| Full chain | **89.7 ms** | 669x | 402.9 ms |

True-peak normalisation used to dominate a chain by upsampling the entire
buffer 4x to find a maximum; it now interpolates only the windows that can hold
the peak (see [NormalizeEffect](#true-peak-by-candidate-window)). That is a 7.6x
speed-up on this signal and 4.5x on the chain as a whole, with a bit-identical
result.

### Loudness (60 s stereo)

| Call | Median | x realtime |
|---|---|---|
| `integrated` | 52.3 ms | 1148x |
| `analyze` (integrated + momentary + short-term + LRA + true peak) | 158.5 ms | 378x |

Fast enough for a file, not for a slot: the window measures on a worker thread.

### Real-time and rendering

| Case | Median | Note |
|---|---|---|
| Meter, 128-sample blocks | 58.9 ms / 10 s audio | 170x realtime, 2.7 ms callbacks |
| Meter, 1024-sample blocks | 47.7 ms / 10 s audio | 209x realtime |
| Render 640x360, first paint | 11.0 ms | 91 fps (was 25.6 ms) |
| Render 640x360, palette change | 1.9 ms | 516 fps |
| Render 1280x720, first paint | 18.9 ms | 53 fps (was 44.4 ms) |
| Render 1280x720, palette change | 7.9 ms | 127 fps |
| Render 1920x1080, first paint | 33.9 ms | 30 fps (was 70.7 ms) |
| Render 1920x1080, palette change | 17.6 ms | 57 fps |

Two figures per size because two very different costs share one entry point.
A *first paint* pools the STFT onto the pixel grid; a *palette change* reuses
the cached grid and only re-colourises, which is what the colormap, dynamic
range and auto-scale controls do. The old single figure was measuring the
pooling every time, since there was no cache to hit.

---

## Testing

```bash
cd audio-studio
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_windows.py \
    tests/test_spectral.py tests/test_effects.py tests/test_loudness.py \
    tests/test_preview.py tests/test_spectrogram_widget.py \
    tests/test_ui.py tests/test_dsp_integration.py

# every example in this document's API sections is also a runnable doctest
python -m pytest --doctest-modules audio_studio/dsp
```

501 tests plus 9 doctests. Signal generators live in `tests/signals.py`. The
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
- Loudness is checked against the **EBU Tech 3341 test signals** and the
  published BS.1770-4 coefficient tables, not against this implementation's own
  output: a -23 dBFS 1 kHz stereo tone must read -23.0 LUFS, the surround
  weighting must be +1.5 dB, and the gate must actually discard what it exists
  to discard.
- The true-peak shortcut is asserted equal to full 4x oversampling on tones,
  noise, clicks, fades, DC, one-sample transients and stereo material, plus a
  timing guard on the 60 s stereo case. A shortcut that is merely usually right
  would be worse than no shortcut.
- The render caches are verified by counting calls to the pooling primitive: a
  palette or range change must reach it zero times, a frequency zoom exactly
  once, and a width change twice. The pooled result is compared with
  `numpy.maximum.reduceat` element for element across shapes and both axes.
- The widget is rendered offscreen and the resulting pixels are checked: a
  boosted band must be brighter, a 2 kHz tone must land at the right height on
  a log axis, a one-bin line must survive being zoomed out.
- The preview insert is driven through a real engine on a hand-pumped device:
  the rack must be audible in what the device pulls, bypass must return the
  original samples, a raising effect must cost one dry block rather than the
  stream, and the clip in memory must come out unchanged.

Edge cases with dedicated coverage: empty buffers, input shorter than one
window, DC and Nyquist (the two bins one-sided folding must not double), exact
digital silence, 1/2/6 channels, six sample rates from 8 kHz to 192 kHz, and
extreme EQ settings that must not produce NaN.
