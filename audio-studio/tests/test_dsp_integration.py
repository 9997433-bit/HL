"""End-to-end DSP integration: analyse, process, re-analyse, render.

These tests wire the pieces together the way an application does, so they
catch the class of bug that unit tests miss — a calibration convention that
disagrees between two modules, a layout assumption that only holds for mono, a
renderer that silently drops the data it was handed.
"""

from __future__ import annotations

import os
import time

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from signals import SR, bin_centered_frequency, chirp, sine, stereo, white_noise  # noqa: E402

from audio_studio.dsp import (  # noqa: E402
    EffectChain,
    FadeEffect,
    GainEffect,
    NormalizeEffect,
    RealtimeSpectrum,
    SpectralAnalyzer,
    SpectralConfig,
    ThreeBandEQ,
    WaterfallBuffer,
    measure_levels,
)
from audio_studio.dsp.util import linear_to_db, peak_level  # noqa: E402


@pytest.fixture(scope="module")
def qt_app():
    """A QApplication that stays alive for the module.

    Qt aborts the process if a widget is constructed without a live
    application, and the instance must be held in a variable — letting it be
    garbage collected is the same as never creating it.
    """
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def music_like() -> np.ndarray:
    """Stereo material with content spread across the spectrum.

    A bass note, a mid tone, a bright sweep and a noise bed, panned slightly
    differently per channel so a bug that collapses channels is visible.
    """
    duration = 2.0
    left = (
        0.30 * sine(80.0, duration)
        + 0.20 * sine(1000.0, duration)
        + 0.10 * chirp(2000.0, 12_000.0, duration, amplitude=1.0)
        + white_noise(duration, amplitude=0.01, seed=1)
    )
    right = (
        0.25 * sine(80.0, duration, phase=0.3)
        + 0.22 * sine(1500.0, duration)
        + 0.08 * chirp(3000.0, 15_000.0, duration, amplitude=1.0)
        + white_noise(duration, amplitude=0.01, seed=2)
    )
    return stereo(left, right)


def band_level_db(analyzer: SpectralAnalyzer, audio: np.ndarray, low: float, high: float) -> float:
    """Average energy in a band, in dB, over the whole buffer."""
    spectrum = analyzer.spectrogram(audio)
    lo, hi = np.searchsorted(analyzer.frequencies, (low, high))
    power = np.square(spectrum.mono()[:, lo:hi].astype(np.float64))
    return float(10.0 * np.log10(max(np.mean(np.sum(power, axis=1)), 1e-30)))


# ---------------------------------------------------------------------------
# analyse -> process -> re-analyse
# ---------------------------------------------------------------------------


def test_eq_changes_only_the_bands_it_should(music_like: np.ndarray) -> None:
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=4096, dtype=np.float64)
    eq = ThreeBandEQ(
        low_frequency=120.0, low_gain_db=-12.0,
        mid_frequency=1200.0, mid_gain_db=0.0,
        high_frequency=8000.0, high_gain_db=6.0,
    )
    processed = eq.process(music_like, SR)

    low_change = band_level_db(analyzer, processed, 40.0, 100.0) - band_level_db(
        analyzer, music_like, 40.0, 100.0
    )
    high_change = band_level_db(analyzer, processed, 10_000.0, 16_000.0) - band_level_db(
        analyzer, music_like, 10_000.0, 16_000.0
    )
    mid_change = band_level_db(analyzer, processed, 900.0, 1600.0) - band_level_db(
        analyzer, music_like, 900.0, 1600.0
    )

    assert low_change < -8.0
    assert high_change > 4.0
    assert abs(mid_change) < 2.0


def test_full_chain_produces_a_correctly_levelled_result(music_like: np.ndarray) -> None:
    """EQ, then normalise, then fade — the order a mastering pass would use."""
    chain = EffectChain([
        ThreeBandEQ(low_gain_db=3.0, high_gain_db=2.0),
        NormalizeEffect(target_db=-1.0, mode="true_peak"),
        FadeEffect(fade_in_s=0.05, fade_out_s=0.1, shape="cosine"),
    ])
    processed = chain.process(music_like, SR)

    assert processed.shape == music_like.shape
    assert np.all(np.isfinite(processed))
    # The fade is applied after normalisation, so the peak sits at or below it.
    assert measure_levels(processed).true_peak_db <= -1.0 + 1e-6
    assert abs(float(processed[0, 0])) < 1e-9
    assert abs(float(processed[0, -1])) < 1e-9


def test_normalising_a_quiet_file_lifts_the_whole_spectrum_uniformly() -> None:
    """Gain is frequency-flat: every bin must move by the same amount."""
    audio = 0.01 * (sine(200.0, 1.0) + 0.5 * sine(3000.0, 1.0))
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=4096, dtype=np.float64, center=False)

    before = analyzer.spectrogram(audio).mono()[5]
    normalizer = NormalizeEffect(target_db=-3.0)
    after = analyzer.spectrogram(normalizer.process(audio, SR)).mono()[5]

    expected_db = normalizer.applied_gain_db[0]
    loud = before > 10 ** (-60 / 20)
    shift = 20 * np.log10(after[loud] / before[loud])
    assert np.allclose(shift, expected_db, atol=0.01)


def test_fade_shows_up_as_a_ramp_in_the_spectrogram() -> None:
    """Time-domain envelope and spectrogram time axis must agree."""
    audio = sine(1000.0, duration_s=1.0, amplitude=0.8)
    faded = FadeEffect(fade_in_s=0.5, shape="linear").process(audio, SR)

    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=2048, hop_size=512, dtype=np.float64)
    spectrum = analyzer.spectrogram(faded)
    level = spectrum.db()[:, int(np.argmin(np.abs(analyzer.frequencies - 1000.0)))]

    quarter = int(np.searchsorted(spectrum.times, 0.25))
    half = int(np.searchsorted(spectrum.times, 0.5))
    three_quarters = int(np.searchsorted(spectrum.times, 0.75))

    # At the halfway point of a linear fade the level is 6 dB down.
    assert level[quarter] - level[half] == pytest.approx(-6.02, abs=0.5)
    assert level[three_quarters] == pytest.approx(level[half], abs=0.2)


def test_effects_survive_a_spectral_round_trip(music_like: np.ndarray) -> None:
    """STFT -> ISTFT is transparent enough to sit inside a processing chain."""
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=2048, hop_size=512, dtype=np.float64)
    eq = ThreeBandEQ(mid_frequency=1000.0, mid_gain_db=6.0)

    direct = eq.process(music_like, SR)
    through_stft = analyzer.istft(analyzer.stft(direct), length=direct.shape[1])
    assert np.max(np.abs(through_stft - direct)) < 1e-9


def test_clipping_is_visible_as_harmonic_distortion() -> None:
    """A negative check: the analyzer resolves what a level mistake sounds like."""
    fundamental = bin_centered_frequency(1000.0, 8192)
    clean = sine(fundamental, duration_s=1.0, amplitude=0.5)
    clipped = np.clip(GainEffect(gain_db=12.0).process(clean, SR), -1.0, 1.0)

    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=8192, dtype=np.float64, center=False)
    third = int(np.argmin(np.abs(analyzer.frequencies - 3 * fundamental)))

    clean_db = float(analyzer.spectrogram(clean).db()[3, third])
    clipped_db = float(analyzer.spectrogram(clipped).db()[3, third])
    assert clipped_db > clean_db + 40.0


# ---------------------------------------------------------------------------
# realtime path
# ---------------------------------------------------------------------------


def test_realtime_display_tracks_a_processed_stream() -> None:
    """Feed EQ'd audio block by block and watch the bars respond.

    Bars sum energy per band, and a log band an octave higher holds twice as
    many bins, so white noise slopes upward by design. The EQ move is therefore
    checked as a *difference* against the same noise pushed unprocessed.
    """
    audio = white_noise(duration_s=1.0, amplitude=0.1)
    eq = ThreeBandEQ(mid_frequency=1000.0, mid_gain_db=12.0, mid_q=3.0)
    eq.prepare(SR, 1)

    def stream(process: bool) -> tuple[RealtimeSpectrum, WaterfallBuffer]:
        realtime = RealtimeSpectrum(
            sample_rate=SR, fft_size=4096, hop_size=1024,
            attack_ms=5.0, release_ms=50.0, dtype=np.float64,
        )
        waterfall = WaterfallBuffer(n_bins=realtime.analyzer.n_bins, capacity=64)
        for start in range(0, audio.size, 512):
            block = audio[start : start + 512]
            if process:
                block = eq.process_block(block, SR)
            if realtime.push(block):
                waterfall.push(realtime.levels_db.astype(np.float32))
        return realtime, waterfall

    flat, _ = stream(process=False)
    boosted, waterfall = stream(process=True)

    assert boosted.frames_processed > 0
    assert len(waterfall) > 0

    difference = boosted.bars(n_bands=31).values_db - flat.bars(n_bands=31).values_db
    peak_band = flat.bars(n_bands=31).centers[int(np.argmax(difference))]
    assert 700.0 < peak_band < 1400.0
    assert np.max(difference) > 6.0


def test_streaming_and_offline_spectra_converge() -> None:
    """The live meter and the offline spectrogram must report the same level."""
    fft_size = 4096
    frequency = bin_centered_frequency(1000.0, fft_size)
    audio = sine(frequency, duration_s=2.0, amplitude=0.5)

    offline = SpectralAnalyzer(
        sample_rate=SR, fft_size=fft_size, dtype=np.float64, center=False
    ).spectrogram(audio)
    realtime = RealtimeSpectrum(
        sample_rate=SR, fft_size=fft_size, hop_size=1024,
        attack_ms=1.0, release_ms=1.0, dtype=np.float64,
    )
    for start in range(0, audio.size, 1000):
        realtime.push(audio[start : start + 1000])

    assert float(np.max(realtime.levels_db)) == pytest.approx(
        float(np.max(offline.db())), abs=0.1
    )


def test_realtime_keeps_up_with_realtime() -> None:
    """A live meter that cannot outrun the audio clock is useless."""
    realtime = RealtimeSpectrum(sample_rate=SR, fft_size=2048, hop_size=512)
    audio = white_noise(duration_s=5.0, amplitude=0.2).astype(np.float32)
    blocks = [audio[i : i + 512] for i in range(0, audio.size, 512)]

    start = time.perf_counter()
    for block in blocks:
        realtime.push(block)
    elapsed = time.perf_counter() - start

    assert elapsed < 5.0 * 0.25  # at least 4x realtime with plenty of margin


# ---------------------------------------------------------------------------
# analysis -> display
# ---------------------------------------------------------------------------


def test_spectrogram_reaches_the_widget_intact(qt_app, music_like: np.ndarray) -> None:
    from audio_studio.ui.spectrogram_widget import SpectrogramWidget

    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=2048, hop_size=512)
    spectrum = analyzer.spectrogram(music_like)

    widget = SpectrogramWidget()
    widget.resize(800, 400)
    widget.set_spectrogram(spectrum)
    widget.auto_scale()

    image = widget.render_image(400, 200)
    assert image is not None and (image.width(), image.height()) == (400, 200)

    # The 80 Hz fundamental should read back through the cursor API.
    _, frequency, level_db = widget.value_at(widget._plot_rect().center())
    assert np.isfinite(level_db)
    assert widget.frequency_range[1] <= SR / 2 + 1e-6


def test_eq_change_is_visible_in_the_rendered_image(qt_app) -> None:
    """The whole pipeline in one assertion: filter, analyse, colourise."""
    from audio_studio.ui.spectrogram_widget import FrequencyScale, SpectrogramWidget

    audio = white_noise(duration_s=1.0, amplitude=0.2)
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=2048, hop_size=512)
    eq = ThreeBandEQ(low_frequency=300.0, low_gain_db=-24.0)

    widget = SpectrogramWidget()
    widget.resize(400, 300)
    widget.set_db_range(-100.0, -20.0)
    widget.set_frequency_scale(FrequencyScale.LOG)
    widget.set_frequency_range(20.0, 20_000.0)

    brightness = []
    for buffer in (audio, eq.process(audio, SR)):
        widget.set_spectrogram(analyzer.spectrogram(buffer))
        image = widget.render_image(200, 200)
        pixels = _image_to_array(image) @ np.array([0.2126, 0.7152, 0.0722])
        # Bottom quarter of a 20 Hz - 20 kHz log axis is below ~200 Hz.
        brightness.append(float(pixels[150:, :].mean()))

    assert brightness[1] < brightness[0] - 20.0


def test_waterfall_display_scrolls_with_live_frames(qt_app) -> None:
    from audio_studio.ui.spectrogram_widget import DisplayMode, SpectrogramWidget

    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=1024, hop_size=256)
    realtime = RealtimeSpectrum(analyzer, attack_ms=1.0, release_ms=1.0)

    widget = SpectrogramWidget()
    widget.resize(400, 300)
    widget.start_waterfall(
        analyzer.frequencies, history=128, frame_interval_s=analyzer.config.hop_seconds
    )

    sweep = chirp(200.0, 10_000.0, duration_s=1.0, amplitude=0.5)
    for start in range(0, sweep.size, 256):
        if realtime.push(sweep[start : start + 256]):
            widget.push_frame(realtime.levels_db.astype(np.float32), repaint=False)

    assert widget._mode is DisplayMode.WATERFALL
    assert widget.render_image(200, 150) is not None


# ---------------------------------------------------------------------------
# robustness
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("channels", [1, 2, 6])
def test_pipeline_handles_any_channel_count(channels: int) -> None:
    audio = np.stack([sine(500.0 * (i + 1), 0.3, 0.2) for i in range(channels)])
    if channels == 1:
        audio = audio[0]

    chain = EffectChain([ThreeBandEQ(mid_gain_db=3.0), NormalizeEffect(target_db=-3.0)])
    processed = chain.process(audio, SR)
    spectrum = SpectralAnalyzer(sample_rate=SR, fft_size=1024).spectrogram(processed)

    assert processed.shape == audio.shape
    assert spectrum.n_channels == channels
    assert float(linear_to_db(peak_level(processed))) == pytest.approx(-3.0, abs=0.01)


@pytest.mark.parametrize("sample_rate", [8_000, 22_050, 44_100, 48_000, 96_000, 192_000])
def test_pipeline_handles_any_sample_rate(sample_rate: int) -> None:
    frequency = min(1000.0, sample_rate / 8)
    audio = sine(frequency, duration_s=0.25, amplitude=0.5, sample_rate=sample_rate)

    eq = ThreeBandEQ(mid_frequency=frequency, mid_gain_db=6.0, mid_q=1.0)
    analyzer = SpectralAnalyzer(sample_rate=sample_rate, fft_size=2048, dtype=np.float64)
    spectrum = analyzer.spectrogram(eq.process(audio, sample_rate))

    assert spectrum.peak_frequencies()[3] == pytest.approx(frequency, rel=0.02)
    assert analyzer.frequencies[-1] == pytest.approx(sample_rate / 2)


def test_silence_stays_silent_and_finite() -> None:
    silence = np.zeros((2, SR // 2))
    chain = EffectChain([
        ThreeBandEQ(low_gain_db=6.0),
        NormalizeEffect(target_db=-1.0),
        FadeEffect(fade_in_s=0.01, fade_out_s=0.01),
    ])
    processed = chain.process(silence, SR)
    assert np.all(processed == 0.0)

    db = SpectralAnalyzer(sample_rate=SR, fft_size=1024).spectrogram(processed).db()
    assert np.all(np.isfinite(db))
    assert np.all(db <= -140.0 + 1e-6)


def test_dc_offset_lands_in_the_dc_bin() -> None:
    """DC and Nyquist are the two bins one-sided folding must *not* double.

    Measured with a rectangular window so the reading is the calibration and
    not the window's main lobe spilling into the neighbouring bins.
    """
    audio = np.full(SR // 2, 0.5)
    analyzer = SpectralAnalyzer(
        sample_rate=SR, fft_size=2048, window="rectangular", dtype=np.float64, center=False
    )
    frame = analyzer.spectrogram(audio).mono()[3]

    assert float(frame[0]) == pytest.approx(0.5, rel=1e-9)
    assert float(np.max(frame[1:])) < 1e-9


def test_nyquist_tone_is_measured_correctly() -> None:
    n = 4096
    audio = 0.5 * np.cos(np.pi * np.arange(n * 2))  # alternating +/-0.5 at fs/2
    analyzer = SpectralAnalyzer(
        sample_rate=SR, fft_size=n, window="rectangular", dtype=np.float64, center=False
    )
    frame = analyzer.spectrogram(audio).mono()[1]

    assert float(frame[-1]) == pytest.approx(0.5, rel=1e-9)
    assert float(np.max(frame[:-1])) < 1e-9


def test_a_windowed_dc_offset_leaks_only_into_the_main_lobe() -> None:
    """The same signal through Hann: energy stays inside a few bins."""
    audio = np.full(SR // 2, 0.5)
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=2048, dtype=np.float64, center=False)
    frame = analyzer.spectrogram(audio).mono()[3]

    assert float(frame[0]) == pytest.approx(0.5, rel=1e-9)
    assert float(np.max(frame[3:])) < 1e-9  # Hann's main lobe is 3 bins wide


def test_extreme_settings_do_not_produce_nan() -> None:
    audio = white_noise(duration_s=0.2, amplitude=0.5)
    chain = EffectChain([
        ThreeBandEQ(
            low_frequency=10.0, low_gain_db=24.0,
            mid_frequency=20.0, mid_gain_db=-24.0, mid_q=10.0,
            high_frequency=23_000.0, high_gain_db=24.0,
        ),
        GainEffect(gain_db=40.0),
        NormalizeEffect(target_db=-0.1, mode="true_peak"),
    ])
    processed = chain.process(audio, SR)
    assert np.all(np.isfinite(processed))
    assert np.all(np.isfinite(SpectralAnalyzer(sample_rate=SR).spectrogram(processed).db()))


def test_a_long_file_analyses_in_bounded_memory() -> None:
    """Chunked framing means memory tracks the chunk size, not the file length."""
    config = SpectralConfig(
        sample_rate=SR, fft_size=4096, hop_size=1024, max_frames_per_chunk=64
    )
    analyzer = SpectralAnalyzer(config)
    audio = white_noise(duration_s=10.0, amplitude=0.2).astype(np.float32)

    chunked = analyzer.spectrogram(audio).values
    analyzer.reconfigure(max_frames_per_chunk=100_000)
    whole = analyzer.spectrogram(audio).values
    assert np.allclose(chunked, whole)


def _image_to_array(image) -> np.ndarray:
    """Copy a Format_RGB888 QImage into an ``(h, w, 3)`` uint8 array."""
    width, height = image.width(), image.height()
    pointer = image.constBits()
    pointer.setsize(image.sizeInBytes())
    stride = image.bytesPerLine()
    raw = np.frombuffer(bytes(pointer), dtype=np.uint8).reshape(height, stride)
    return raw[:, : width * 3].reshape(height, width, 3)
