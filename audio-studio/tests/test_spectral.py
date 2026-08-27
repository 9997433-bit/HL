"""SpectralAnalyzer: calibration, geometry, inversion and streaming."""

from __future__ import annotations

import numpy as np
import pytest
from signals import SR, bin_centered_frequency, chirp, sine, stereo, white_noise

from audio_studio.dsp import (
    RealtimeSpectrum,
    SpectralAnalyzer,
    SpectralConfig,
    SpectrumScaling,
    WaterfallBuffer,
    WindowType,
)


@pytest.fixture
def stereo_tone() -> np.ndarray:
    """1 kHz at -6 dBFS on the left, 3 kHz at -12 dBFS on the right."""
    return stereo(sine(1000.0, amplitude=0.5), sine(3000.0, amplitude=0.25))


# ---------------------------------------------------------------------------
# configuration and geometry
# ---------------------------------------------------------------------------


def test_default_hop_is_75_percent_overlap() -> None:
    config = SpectralConfig(fft_size=2048)
    assert config.hop_size == 512
    assert config.overlap_ratio == pytest.approx(0.75)


def test_bin_spacing_and_resolution_are_different_numbers() -> None:
    """Zero-padding refines the bin grid but not the true resolution."""
    plain = SpectralConfig(sample_rate=SR, fft_size=2048)
    padded = SpectralConfig(sample_rate=SR, fft_size=8192, window_size=2048)

    assert padded.bin_spacing_hz == pytest.approx(plain.bin_spacing_hz / 4)
    assert padded.frequency_resolution_hz == pytest.approx(plain.frequency_resolution_hz)


def test_time_resolution_follows_window_length() -> None:
    config = SpectralConfig(sample_rate=SR, fft_size=4800)
    assert config.time_resolution_s == pytest.approx(0.1)


def test_for_frequency_resolution_delivers_what_it_promises() -> None:
    config = SpectralConfig.for_frequency_resolution(SR, 10.0, window=WindowType.HANN)
    assert config.frequency_resolution_hz <= 10.0
    assert config.fft_size & (config.fft_size - 1) == 0  # power of two


def test_for_frequency_resolution_accounts_for_window_width() -> None:
    """A wider window needs a longer transform to hit the same resolution."""
    hann = SpectralConfig.for_frequency_resolution(SR, 20.0, window="hann")
    blackman = SpectralConfig.for_frequency_resolution(SR, 20.0, window="blackman")
    assert blackman.fft_size >= hann.fft_size
    assert blackman.frequency_resolution_hz <= 20.0


def test_for_time_resolution_never_exceeds_the_budget() -> None:
    config = SpectralConfig.for_time_resolution(SR, 0.02)
    assert config.time_resolution_s <= 0.02


@pytest.mark.parametrize("center", [True, False])
def test_frame_count_matches_produced_frames(center: bool) -> None:
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=1024, hop_size=256, center=center)
    audio = sine(440.0, duration_s=0.5)
    assert analyzer.stft(audio).shape[0] == analyzer.config.n_frames(audio.size)


def test_frame_times_are_hop_spaced() -> None:
    config = SpectralConfig(sample_rate=SR, fft_size=1024, hop_size=256)
    times = config.frame_times(SR)
    assert np.allclose(np.diff(times), 256 / SR)


def test_invalid_configs_are_rejected() -> None:
    with pytest.raises(ValueError):
        SpectralConfig(fft_size=1)
    with pytest.raises(ValueError):
        SpectralConfig(fft_size=1024, window_size=2048)
    with pytest.raises(ValueError):
        SpectralConfig(sample_rate=0)


# ---------------------------------------------------------------------------
# amplitude calibration
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("window", ["rectangular", "hann", "hamming", "blackman", "flattop"])
def test_full_scale_sine_reads_zero_dbfs(window: str) -> None:
    """The headline guarantee: calibration is window-independent."""
    fft_size = 4096
    frequency = bin_centered_frequency(1000.0, fft_size)
    analyzer = SpectralAnalyzer(
        sample_rate=SR, fft_size=fft_size, window=window,
        dtype=np.float64, center=False,
    )
    spectrum = analyzer.spectrogram(sine(frequency, amplitude=1.0))
    assert float(np.max(spectrum.db())) == pytest.approx(0.0, abs=0.01)


@pytest.mark.parametrize("amplitude,expected_db", [(1.0, 0.0), (0.5, -6.02), (0.1, -20.0)])
def test_amplitude_maps_to_expected_dbfs(amplitude: float, expected_db: float) -> None:
    fft_size = 4096
    frequency = bin_centered_frequency(1000.0, fft_size)
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=fft_size, dtype=np.float64, center=False)
    spectrum = analyzer.spectrogram(sine(frequency, amplitude=amplitude))
    assert float(np.max(spectrum.db())) == pytest.approx(expected_db, abs=0.02)


@pytest.mark.parametrize("fft_size", [512, 2048, 8192])
def test_calibration_is_independent_of_fft_size(fft_size: int) -> None:
    frequency = bin_centered_frequency(1000.0, fft_size)
    analyzer = SpectralAnalyzer(
        sample_rate=SR, fft_size=fft_size, dtype=np.float64, center=False
    )
    spectrum = analyzer.spectrogram(sine(frequency, amplitude=0.5))
    assert float(np.max(spectrum.db())) == pytest.approx(-6.02, abs=0.02)


def test_power_scaling_is_3db_below_amplitude() -> None:
    """A sinusoid of amplitude A has mean-square power A^2/2."""
    fft_size = 4096
    frequency = bin_centered_frequency(1000.0, fft_size)
    audio = sine(frequency, amplitude=1.0)
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=fft_size, dtype=np.float64, center=False)

    amplitude_db = float(np.max(analyzer.spectrogram(audio, scaling="amplitude").db()))
    power_db = float(np.max(analyzer.spectrogram(audio, scaling="power").db()))
    assert amplitude_db - power_db == pytest.approx(10 * np.log10(2), abs=0.02)


def test_psd_of_white_noise_is_flat_and_fft_size_independent() -> None:
    """PSD is the scaling that lets two different FFT sizes be compared."""
    noise = white_noise(duration_s=4.0, amplitude=0.1)
    levels = []
    for fft_size in (1024, 4096):
        analyzer = SpectralAnalyzer(
            sample_rate=SR, fft_size=fft_size, scaling=SpectrumScaling.PSD,
            dtype=np.float64, center=False,
        )
        values = analyzer.spectrogram(noise).mono()
        # Ignore DC and Nyquist, which are single-sided special cases.
        levels.append(float(np.mean(values[:, 10:-10])))

    expected = 0.1**2 / (SR / 2)  # variance spread over the one-sided bandwidth
    for level in levels:
        assert level == pytest.approx(expected, rel=0.1)
    assert levels[0] == pytest.approx(levels[1], rel=0.05)


def test_parseval_energy_is_conserved() -> None:
    """Summed power spectrum equals time-domain mean square."""
    noise = white_noise(duration_s=2.0, amplitude=0.3)
    analyzer = SpectralAnalyzer(
        sample_rate=SR, fft_size=2048, window="rectangular", hop_size=2048,
        scaling=SpectrumScaling.POWER, dtype=np.float64, center=False,
    )
    values = analyzer.spectrogram(noise).mono()
    spectral_mean_square = float(np.mean(np.sum(values, axis=1)))
    time_mean_square = float(np.mean(np.square(noise)))
    assert spectral_mean_square == pytest.approx(time_mean_square, rel=0.02)


def test_peak_frequency_is_accurate_to_a_fraction_of_a_bin() -> None:
    """Parabolic interpolation should beat the raw bin spacing by ~10x."""
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=4096, dtype=np.float64)
    spectrum = analyzer.spectrogram(sine(1000.0, amplitude=0.8))
    interior = spectrum.peak_frequencies()[5:-5]
    assert np.allclose(interior, 1000.0, atol=1.0)
    assert analyzer.config.bin_spacing_hz > 10.0  # so 1 Hz really is sub-bin


def test_two_tones_are_resolved_at_the_advertised_resolution() -> None:
    config = SpectralConfig.for_frequency_resolution(SR, 25.0, window="hann")
    analyzer = SpectralAnalyzer(config.with_(dtype=np.float64, center=False))
    audio = sine(1000.0, duration_s=2.0, amplitude=0.5) + sine(
        1060.0, duration_s=2.0, amplitude=0.5
    )

    frame = analyzer.spectrogram(audio).mono()[5]
    lo, hi = np.searchsorted(analyzer.frequencies, (950.0, 1120.0))
    window = frame[lo:hi]
    # Two separated peaks means the trough between them is clearly lower.
    peaks = np.sort(np.argsort(window)[-2:])
    trough = float(np.min(window[peaks[0] : peaks[1] + 1]))
    assert 20 * np.log10(float(window[peaks[0]]) / trough) > 6.0
    assert 20 * np.log10(float(window[peaks[1]]) / trough) > 6.0


# ---------------------------------------------------------------------------
# shapes, channels and layout
# ---------------------------------------------------------------------------


def test_mono_input_keeps_two_dimensional_stft() -> None:
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=1024)
    assert analyzer.stft(sine(440.0, 0.2)).ndim == 2


def test_stereo_channels_are_analysed_independently(stereo_tone: np.ndarray) -> None:
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=4096, dtype=np.float64)
    spectrum = analyzer.spectrogram(stereo_tone)

    assert spectrum.n_channels == 2
    assert float(np.max(spectrum.db(0))) == pytest.approx(-6.0, abs=0.7)
    assert float(np.max(spectrum.db(1))) == pytest.approx(-12.0, abs=0.7)
    assert spectrum.peak_frequencies(0)[10] == pytest.approx(1000.0, abs=2.0)
    assert spectrum.peak_frequencies(1)[10] == pytest.approx(3000.0, abs=2.0)


def test_interleaved_input_is_detected() -> None:
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=1024)
    planar = stereo(sine(1000.0, 0.2), sine(3000.0, 0.2))
    from_planar = analyzer.spectrogram(planar).values
    from_interleaved = analyzer.spectrogram(np.ascontiguousarray(planar.T)).values
    assert np.allclose(from_planar, from_interleaved)


def test_empty_input_produces_zero_frames() -> None:
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=1024)
    spectrum = analyzer.spectrogram(np.zeros(0))
    assert spectrum.n_frames == 0
    assert spectrum.db().size == 0


def test_input_shorter_than_one_window_still_works_when_centered() -> None:
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=4096, center=True)
    assert analyzer.spectrogram(sine(1000.0, duration_s=0.01)).n_frames >= 1


def test_float32_and_float64_agree_above_the_noise_floor() -> None:
    """float32 costs precision only far below anything audible or displayable."""
    audio = sine(1000.0, amplitude=0.5)
    single = SpectralAnalyzer(sample_rate=SR, fft_size=2048, dtype=np.float32).spectrogram(audio)
    double = SpectralAnalyzer(sample_rate=SR, fft_size=2048, dtype=np.float64).spectrogram(audio)

    assert single.values.dtype == np.float32
    single_db, double_db = single.db(), double.db()
    audible = double_db > -100.0
    assert np.max(np.abs(single_db[audible] - double_db[audible])) < 0.05
    # Even at the very bottom the two stay within a fraction of a dB.
    assert np.max(np.abs(single_db - double_db)) < 1.0


def test_centered_frames_align_with_the_signal() -> None:
    """A tone burst should light up the frames covering it, not the ones before."""
    audio = np.zeros(SR)
    audio[SR // 2 : SR // 2 + 4800] = sine(2000.0, duration_s=0.1, amplitude=0.8)
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=1024, hop_size=256, dtype=np.float64)
    spectrum = analyzer.spectrogram(audio)

    energy = spectrum.band_energy(1900.0, 2100.0)
    loudest_time = float(spectrum.times[int(np.argmax(energy))])
    assert 0.5 <= loudest_time <= 0.6


# ---------------------------------------------------------------------------
# inverse transform
# ---------------------------------------------------------------------------


def _covered_samples(analyzer: SpectralAnalyzer, n_samples: int) -> int:
    """Samples that at least one analysis window reaches.

    With ``center=False`` the frame grid stops at the last window that fits, so
    the final ``< hop`` samples are outside every frame and cannot be
    reconstructed. Centred analysis pads and therefore covers everything.
    """
    config = analyzer.config
    if config.center:
        return n_samples
    frames = config.n_frames(n_samples)
    return min(n_samples, (frames - 1) * config.hop_size + config.window_size)


@pytest.mark.parametrize("window", ["hann", "hamming", "blackman"])
@pytest.mark.parametrize("center", [True, False])
def test_istft_round_trip_is_sample_exact(window: str, center: bool) -> None:
    audio = chirp(100.0, 8000.0, duration_s=0.5)
    analyzer = SpectralAnalyzer(
        sample_rate=SR, fft_size=1024, hop_size=256, window=window,
        dtype=np.float64, center=center,
    )
    restored = analyzer.istft(analyzer.stft(audio), length=audio.size)
    assert restored.shape == audio.shape

    covered = _covered_samples(analyzer, audio.size)
    assert np.max(np.abs(restored[:covered] - audio[:covered])) < 1e-9


def test_istft_round_trip_survives_a_hop_that_breaks_cola() -> None:
    """Weighted overlap-add does not require an exact COLA hop."""
    audio = chirp(200.0, 6000.0, duration_s=0.3)
    analyzer = SpectralAnalyzer(
        sample_rate=SR, fft_size=1024, hop_size=333, dtype=np.float64, center=False
    )
    restored = analyzer.istft(analyzer.stft(audio), length=audio.size)
    # The tail beyond the last complete frame is not covered by any window.
    covered = (analyzer.config.n_frames(audio.size) - 1) * 333 + 1024
    assert np.max(np.abs(restored[:covered] - audio[:covered])) < 1e-9


def test_istft_round_trip_for_stereo(stereo_tone: np.ndarray) -> None:
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=2048, dtype=np.float64)
    restored = analyzer.istft(analyzer.stft(stereo_tone), length=stereo_tone.shape[1])
    assert restored.shape == stereo_tone.shape
    assert np.max(np.abs(restored - stereo_tone)) < 1e-9


def test_istft_of_a_zero_padded_analysis_round_trips() -> None:
    audio = chirp(200.0, 5000.0, duration_s=0.2)
    analyzer = SpectralAnalyzer(
        sample_rate=SR, fft_size=2048, window_size=1024, hop_size=256,
        dtype=np.float64, center=False,
    )
    restored = analyzer.istft(analyzer.stft(audio), length=audio.size)
    covered = (analyzer.config.n_frames(audio.size) - 1) * 256 + 1024
    assert np.max(np.abs(restored[:covered] - audio[:covered])) < 1e-9


# ---------------------------------------------------------------------------
# single-frame and streaming interfaces
# ---------------------------------------------------------------------------


def test_single_block_spectrum_matches_the_spectrogram() -> None:
    fft_size = 2048
    frequency = bin_centered_frequency(1000.0, fft_size)
    block = sine(frequency, duration_s=fft_size / SR, amplitude=0.5)
    analyzer = SpectralAnalyzer(
        sample_rate=SR, fft_size=fft_size, dtype=np.float64, center=False
    )
    assert float(np.max(analyzer.spectrum(block))) == pytest.approx(-6.02, abs=0.02)


def test_short_block_is_zero_padded_not_rejected() -> None:
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=2048)
    assert analyzer.spectrum(sine(1000.0, duration_s=0.005)).shape == (analyzer.n_bins,)


def test_iter_frames_matches_uncentered_stft() -> None:
    audio = white_noise(duration_s=0.4, amplitude=0.2)
    analyzer = SpectralAnalyzer(
        sample_rate=SR, fft_size=1024, hop_size=256, dtype=np.float64, center=False
    )
    reference = analyzer.stft(audio)
    blocks = [audio[i : i + 700] for i in range(0, audio.size, 700)]
    streamed = np.stack([frame[0] for frame in analyzer.iter_frames(blocks)])
    assert np.allclose(streamed[: reference.shape[0]], reference, atol=1e-9)


class TestRealtimeSpectrum:
    def test_produces_one_frame_per_hop(self) -> None:
        realtime = RealtimeSpectrum(sample_rate=SR, fft_size=1024, hop_size=256)
        assert realtime.push(sine(1000.0, duration_s=1024 / SR)) == 1
        assert realtime.push(sine(1000.0, duration_s=1024 / SR)) == 4

    def test_converges_on_the_true_level(self) -> None:
        fft_size = 2048
        frequency = bin_centered_frequency(1000.0, fft_size)
        realtime = RealtimeSpectrum(
            sample_rate=SR, fft_size=fft_size, hop_size=512,
            attack_ms=1.0, release_ms=1.0, dtype=np.float64,
        )
        realtime.push(sine(frequency, duration_s=1.0, amplitude=0.5))
        assert float(np.max(realtime.levels_db)) == pytest.approx(-6.02, abs=0.3)

    def test_smoothing_is_slower_than_the_raw_signal(self) -> None:
        """A long release must hold level after the input stops."""
        realtime = RealtimeSpectrum(
            sample_rate=SR, fft_size=1024, hop_size=256,
            attack_ms=1.0, release_ms=2000.0, peak_hold_s=10.0,
        )
        realtime.push(sine(1000.0, duration_s=0.5, amplitude=0.8))
        loud = float(np.max(realtime.levels_db))
        realtime.push(np.zeros(2048))
        assert float(np.max(realtime.levels_db)) > loud - 6.0

    def test_peaks_never_fall_below_levels(self) -> None:
        realtime = RealtimeSpectrum(sample_rate=SR, fft_size=1024, hop_size=256)
        realtime.push(white_noise(duration_s=0.5, amplitude=0.3))
        assert np.all(realtime.peaks_db >= realtime.levels_db - 1e-6)

    def test_peak_hold_decays_after_the_hold_time(self) -> None:
        realtime = RealtimeSpectrum(
            sample_rate=SR, fft_size=1024, hop_size=256,
            attack_ms=0.1, release_ms=0.1, peak_hold_s=0.01, peak_decay_db_s=200.0,
        )
        realtime.push(sine(1000.0, duration_s=0.2, amplitude=0.9))
        held = float(np.max(realtime.peaks_db))
        realtime.push(np.zeros(SR // 2))
        assert float(np.max(realtime.peaks_db)) < held - 20.0

    def test_reset_clears_state(self) -> None:
        realtime = RealtimeSpectrum(sample_rate=SR, fft_size=1024)
        realtime.push(sine(1000.0, duration_s=0.2))
        realtime.reset()
        assert realtime.frames_processed == 0
        assert np.all(realtime.levels_db == realtime.config.db_floor)

    def test_bars_locate_the_tone_in_the_right_band(self) -> None:
        realtime = RealtimeSpectrum(
            sample_rate=SR, fft_size=4096, hop_size=1024, attack_ms=1.0, release_ms=1.0
        )
        realtime.push(sine(1000.0, duration_s=1.0, amplitude=0.5))
        bars = realtime.bars(n_bands=31, f_min=20.0, f_max=20_000.0)

        assert bars.n_bands == 31
        assert bars.centers.size == 31 and bars.edges.size == 32
        loudest = bars.centers[int(np.argmax(bars.values_db))]
        assert 800.0 < loudest < 1250.0  # within a third-octave of 1 kHz

    def test_bars_are_cached_between_identical_calls(self) -> None:
        realtime = RealtimeSpectrum(sample_rate=SR, fft_size=2048)
        realtime.push(white_noise(duration_s=0.2))
        first = realtime.bars(n_bands=24)
        second = realtime.bars(n_bands=24)
        assert first.centers is second.centers

    def test_bars_handle_more_bands_than_bins(self) -> None:
        """Narrow bands must fall back to the nearest bin, not produce NaN."""
        realtime = RealtimeSpectrum(sample_rate=SR, fft_size=256)
        realtime.push(white_noise(duration_s=0.2))
        bars = realtime.bars(n_bands=200, f_min=20.0, f_max=20_000.0)
        assert np.all(np.isfinite(bars.values_db))

    def test_stereo_input_collapses_to_one_display_spectrum(self, stereo_tone: np.ndarray) -> None:
        realtime = RealtimeSpectrum(sample_rate=SR, fft_size=2048)
        realtime.push(stereo_tone)
        assert realtime.levels_db.shape == (realtime.analyzer.n_bins,)


class TestWaterfallBuffer:
    def test_reports_length_until_full(self) -> None:
        buffer = WaterfallBuffer(n_bins=8, capacity=4)
        assert len(buffer) == 0 and not buffer.is_full
        buffer.extend([np.full(8, float(i)) for i in range(3)])
        assert len(buffer) == 3 and not buffer.is_full

    def test_orders_oldest_first(self) -> None:
        buffer = WaterfallBuffer(n_bins=2, capacity=4)
        buffer.extend([np.full(2, float(i)) for i in range(4)])
        assert np.allclose(buffer.image()[:, 0], [0, 1, 2, 3])

    def test_evicts_oldest_when_full(self) -> None:
        buffer = WaterfallBuffer(n_bins=2, capacity=3)
        buffer.extend([np.full(2, float(i)) for i in range(5)])
        assert np.allclose(buffer.image()[:, 0], [2, 3, 4])

    def test_unwritten_rows_hold_the_fill_value(self) -> None:
        buffer = WaterfallBuffer(n_bins=2, capacity=4, fill_db=-120.0)
        buffer.push(np.full(2, 0.0))
        image = buffer.image()
        assert np.allclose(image[:3], -120.0)
        assert np.allclose(image[3], 0.0)

    def test_newest_first_reverses_the_order(self) -> None:
        buffer = WaterfallBuffer(n_bins=1, capacity=3)
        buffer.extend([np.full(1, float(i)) for i in range(3)])
        assert np.allclose(buffer.image(newest_first=True)[:, 0], [2, 1, 0])

    def test_partial_read_returns_the_newest_rows(self) -> None:
        buffer = WaterfallBuffer(n_bins=1, capacity=8)
        buffer.extend([np.full(1, float(i)) for i in range(8)])
        assert np.allclose(buffer.image(rows=3)[:, 0], [5, 6, 7])

    def test_clear_resets_to_fill(self) -> None:
        buffer = WaterfallBuffer(n_bins=2, capacity=3, fill_db=-90.0)
        buffer.extend([np.zeros(2)] * 3)
        buffer.clear()
        assert len(buffer) == 0
        assert np.allclose(buffer.image(), -90.0)

    def test_wrong_shape_is_rejected(self) -> None:
        buffer = WaterfallBuffer(n_bins=4, capacity=2)
        with pytest.raises(ValueError):
            buffer.push(np.zeros(5))


def test_analyzer_can_be_reconfigured_in_place() -> None:
    analyzer = SpectralAnalyzer(sample_rate=SR, fft_size=1024)
    assert analyzer.n_bins == 513
    analyzer.reconfigure(fft_size=2048)
    assert analyzer.n_bins == 1025
    assert analyzer.frequencies.size == 1025


def test_describe_is_informative() -> None:
    text = SpectralConfig(sample_rate=SR, fft_size=2048).describe()
    assert "2048-pt hann" in text and "75% overlap" in text
