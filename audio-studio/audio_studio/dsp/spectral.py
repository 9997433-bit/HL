"""Short-time Fourier analysis: spectrograms, real-time bars and waterfalls.

The module is built around three objects:

:class:`SpectralConfig`
    Everything that defines *how* the transform is taken — FFT size, hop,
    window, calibration — plus derived read-outs such as the frequency and
    time resolution actually achieved.
:class:`SpectralAnalyzer`
    The stateless workhorse. Turns audio into complex STFT frames, calibrated
    magnitude/power/PSD spectra, dB spectrograms, and back again via a
    weighted overlap-add inverse.
:class:`RealtimeSpectrum` / :class:`WaterfallBuffer`
    Stateful adapters for live displays: a streaming frame producer with
    ballistics (attack/release smoothing and peak hold) and a ring buffer that
    feeds a scrolling spectrogram.

Calibration follows the convention used by hardware analyzers and by Adobe
Audition's spectral display: a full-scale sine reads 0 dBFS in
:attr:`SpectrumScaling.AMPLITUDE`, independent of window choice, FFT size or
overlap.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum

import numpy as np

from .util import as_planar, next_pow2, restore_layout
from .windows import WindowInfo, WindowType, window_info

try:  # scipy's pocketfft wrapper is multithreaded; numpy's is not.
    from scipy.fft import irfft as _irfft
    from scipy.fft import rfft as _rfft

    _HAVE_SCIPY_FFT = True
except ImportError:  # pragma: no cover - exercised only without scipy
    from numpy.fft import irfft as _irfft
    from numpy.fft import rfft as _rfft

    _HAVE_SCIPY_FFT = False

__all__ = [
    "SpectrumScaling",
    "SpectralConfig",
    "Spectrogram",
    "SpectrumBars",
    "SpectralAnalyzer",
    "RealtimeSpectrum",
    "WaterfallBuffer",
]


class SpectrumScaling(str, Enum):
    """How complex STFT coefficients are turned into a real spectrum.

    ``AMPLITUDE``
        Linear amplitude. A sinusoid of amplitude ``A`` peaks at ``A``, so a
        full-scale sine reads 0 dBFS. Converted to dB with ``20*log10``.
    ``POWER``
        Mean-square power. The same sinusoid reads ``A**2 / 2`` (i.e. 3.01 dB
        below its amplitude reading). Converted with ``10*log10``.
    ``PSD``
        Power spectral density in ``units**2 / Hz``, normalised by the window's
        equivalent noise bandwidth. This is the scaling to use when comparing
        noise floors across different FFT sizes, since it is independent of
        transform length. Converted with ``10*log10``.
    """

    AMPLITUDE = "amplitude"
    POWER = "power"
    PSD = "psd"

    @classmethod
    def coerce(cls, value: SpectrumScaling | str) -> SpectrumScaling:
        if isinstance(value, cls):
            return value
        key = str(value).strip().lower()
        aliases = {"magnitude": cls.AMPLITUDE, "linear": cls.AMPLITUDE, "density": cls.PSD}
        if key in aliases:
            return aliases[key]
        try:
            return cls(key)
        except ValueError as exc:
            raise ValueError(f"unknown spectrum scaling {value!r}") from exc

    @property
    def db_factor(self) -> float:
        """``20`` for amplitude quantities, ``10`` for power quantities."""
        return 20.0 if self is SpectrumScaling.AMPLITUDE else 10.0


@dataclass(frozen=True)
class SpectralConfig:
    """Immutable description of an STFT analysis.

    Parameters
    ----------
    sample_rate:
        Sample rate of the audio to be analysed, in hertz.
    fft_size:
        Transform length. Determines the bin spacing ``sample_rate/fft_size``.
    hop_size:
        Advance between successive frames, in samples. ``None`` selects 25% of
        ``window_size`` (75% overlap), which keeps a Hann-windowed waterfall
        visually smooth and satisfies COLA for resynthesis.
    window_size:
        Length of the analysis window. ``None`` means "same as ``fft_size``".
        A shorter window zero-pads the transform, which interpolates the
        spectrum onto a finer bin grid without improving true resolution.
    window:
        Window function; see :class:`~audio_studio.dsp.windows.WindowType`.
    scaling:
        Calibration applied by :meth:`SpectralAnalyzer.spectrum_from_stft`.
    reference:
        Amplitude that maps to 0 dB. ``1.0`` gives dBFS.
    db_floor:
        Lower clamp applied to every dB conversion, so silence does not become
        ``-inf`` and ruin autoscaling.
    center:
        Pad the signal by half a window on both sides so that frame ``m`` is
        *centred* on sample ``m*hop_size``. This is what makes spectrogram
        columns line up with the waveform underneath them.
    pad_mode:
        ``numpy.pad`` mode used for the centring pad. ``"constant"`` (silence)
        matches how a file boundary actually sounds; ``"reflect"`` avoids the
        edge dip when analysing a excerpt of a longer signal.
    dtype:
        ``numpy.float32`` roughly halves STFT time and memory versus
        ``float64``; the ~7 digit mantissa is far below the dynamic range any
        display or ear resolves.
    fft_workers:
        Threads handed to ``scipy.fft``. ``-1`` uses every core, ``1`` disables
        threading (useful inside an already-parallel pipeline).
    max_frames_per_chunk:
        Upper bound on how many frames are windowed at once, which caps peak
        memory on long files at roughly ``chunk * fft_size * itemsize``.
    """

    sample_rate: float = 48_000.0
    fft_size: int = 2048
    hop_size: int | None = None
    window_size: int | None = None
    window: WindowType = WindowType.HANN
    scaling: SpectrumScaling = SpectrumScaling.AMPLITUDE
    reference: float = 1.0
    db_floor: float = -140.0
    center: bool = True
    pad_mode: str = "constant"
    dtype: np.dtype = field(default_factory=lambda: np.dtype(np.float32))
    fft_workers: int = -1
    max_frames_per_chunk: int = 4096

    def __post_init__(self) -> None:
        object.__setattr__(self, "window", WindowType.coerce(self.window))
        object.__setattr__(self, "scaling", SpectrumScaling.coerce(self.scaling))
        object.__setattr__(self, "dtype", np.dtype(self.dtype))
        object.__setattr__(self, "sample_rate", float(self.sample_rate))
        object.__setattr__(self, "fft_size", int(self.fft_size))

        if self.sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if self.fft_size < 2:
            raise ValueError("fft_size must be at least 2")
        if self.dtype not in (np.dtype(np.float32), np.dtype(np.float64)):
            raise ValueError("dtype must be float32 or float64")

        window_size = int(self.window_size) if self.window_size else self.fft_size
        if not 1 <= window_size <= self.fft_size:
            raise ValueError(
                f"window_size ({window_size}) must be in 1..fft_size ({self.fft_size})"
            )
        object.__setattr__(self, "window_size", window_size)

        hop = int(self.hop_size) if self.hop_size else max(1, window_size // 4)
        if hop < 1:
            raise ValueError("hop_size must be at least 1")
        object.__setattr__(self, "hop_size", hop)

        if self.max_frames_per_chunk < 1:
            raise ValueError("max_frames_per_chunk must be at least 1")

    # -- derived geometry -------------------------------------------------

    @property
    def n_bins(self) -> int:
        """Number of one-sided FFT bins, including DC and Nyquist."""
        return self.fft_size // 2 + 1

    @property
    def bin_spacing_hz(self) -> float:
        """Spacing between adjacent bins. *Not* the same as resolution."""
        return self.sample_rate / self.fft_size

    @property
    def frequency_resolution_hz(self) -> float:
        """Smallest resolvable frequency separation, in hertz.

        This is the window's equivalent noise bandwidth referred to the signal
        length, i.e. ``enbw_bins * sample_rate / window_size``. Zero-padding
        shrinks :attr:`bin_spacing_hz` but leaves this value untouched, which
        is exactly the distinction the number exists to express.
        """
        info = window_info(self.window, self.window_size)
        return info.enbw_bins * self.sample_rate / self.window_size

    @property
    def time_resolution_s(self) -> float:
        """Duration of one analysis window — the temporal smearing of an event."""
        return self.window_size / self.sample_rate

    @property
    def hop_seconds(self) -> float:
        """Time between successive spectrogram columns."""
        return self.hop_size / self.sample_rate

    @property
    def frame_rate(self) -> float:
        """Spectrogram columns produced per second of audio."""
        return self.sample_rate / self.hop_size

    @property
    def overlap_ratio(self) -> float:
        """Fraction of each window shared with its neighbour, in ``[0, 1)``."""
        return max(0.0, 1.0 - self.hop_size / self.window_size)

    @property
    def window_info(self) -> WindowInfo:
        """Cached window samples and calibration sums."""
        return window_info(self.window, self.window_size)

    def frequencies(self) -> np.ndarray:
        """Centre frequency of every one-sided bin, in hertz."""
        return np.fft.rfftfreq(self.fft_size, d=1.0 / self.sample_rate)

    def n_frames(self, n_samples: int) -> int:
        """Number of frames :meth:`SpectralAnalyzer.stft` will produce."""
        if n_samples <= 0:
            return 0
        if self.center:
            return 1 + int(n_samples) // self.hop_size
        if n_samples < self.window_size:
            return 0
        return 1 + (int(n_samples) - self.window_size) // self.hop_size

    def frame_times(self, n_samples: int) -> np.ndarray:
        """Timestamp of each frame's *centre*, in seconds."""
        count = self.n_frames(n_samples)
        offset = 0.0 if self.center else self.window_size / 2.0
        return (np.arange(count, dtype=np.float64) * self.hop_size + offset) / self.sample_rate

    def with_(self, **changes) -> SpectralConfig:
        """Return a copy with ``changes`` applied (``dataclasses.replace``)."""
        return replace(self, **changes)

    # -- resolution-driven construction -----------------------------------

    @classmethod
    def for_frequency_resolution(
        cls,
        sample_rate: float,
        resolution_hz: float,
        *,
        overlap: float = 0.75,
        window: WindowType | str = WindowType.HANN,
        power_of_two: bool = True,
        **kwargs,
    ) -> SpectralConfig:
        """Build a config that resolves tones ``resolution_hz`` apart.

        The window's equivalent noise bandwidth is taken into account, so a
        Blackman window — which smears roughly 1.7x wider than Hann — is given
        a proportionally longer transform rather than silently under-delivering.
        """
        if resolution_hz <= 0:
            raise ValueError("resolution_hz must be positive")
        window = WindowType.coerce(window)
        # One probe at an arbitrary length is enough: enbw_bins is length-invariant.
        enbw = window_info(window, 4096).enbw_bins
        needed = enbw * sample_rate / resolution_hz
        fft_size = next_pow2(math.ceil(needed)) if power_of_two else int(math.ceil(needed))
        fft_size = max(2, fft_size)
        return cls(
            sample_rate=sample_rate,
            fft_size=fft_size,
            hop_size=max(1, int(round(fft_size * (1.0 - overlap)))),
            window=window,
            **kwargs,
        )

    @classmethod
    def for_time_resolution(
        cls,
        sample_rate: float,
        resolution_s: float,
        *,
        overlap: float = 0.75,
        window: WindowType | str = WindowType.HANN,
        power_of_two: bool = True,
        **kwargs,
    ) -> SpectralConfig:
        """Build a config whose window is at most ``resolution_s`` long.

        Time and frequency resolution trade off against each other; this is the
        transient-friendly end of the same dial as
        :meth:`for_frequency_resolution`.
        """
        if resolution_s <= 0:
            raise ValueError("resolution_s must be positive")
        target = sample_rate * resolution_s
        if power_of_two:
            fft_size = next_pow2(int(target))
            if fft_size > target:  # round *down* so the window is never longer
                fft_size //= 2
        else:
            fft_size = int(target)
        fft_size = max(2, fft_size)
        return cls(
            sample_rate=sample_rate,
            fft_size=fft_size,
            hop_size=max(1, int(round(fft_size * (1.0 - overlap)))),
            window=window,
            **kwargs,
        )

    def describe(self) -> str:
        """One-line human-readable summary, handy for logs and UI tooltips."""
        return (
            f"{self.fft_size}-pt {self.window.value} @ {self.sample_rate:g} Hz, "
            f"hop {self.hop_size} ({self.overlap_ratio * 100:.0f}% overlap), "
            f"df={self.frequency_resolution_hz:.2f} Hz, "
            f"dt={self.time_resolution_s * 1e3:.1f} ms, "
            f"{self.frame_rate:.1f} fps, {self.scaling.value}"
        )


@dataclass(frozen=True)
class Spectrogram:
    """Result of :meth:`SpectralAnalyzer.spectrogram`.

    ``values`` is ``(n_channels, n_frames, n_bins)`` in the units implied by
    ``config.scaling``. Mono input keeps its channel axis here so that all
    downstream code can be written once; use :meth:`channel` or :meth:`mono` to
    reduce it.
    """

    values: np.ndarray
    frequencies: np.ndarray
    times: np.ndarray
    config: SpectralConfig

    @property
    def n_channels(self) -> int:
        return int(self.values.shape[0])

    @property
    def n_frames(self) -> int:
        return int(self.values.shape[1])

    @property
    def n_bins(self) -> int:
        return int(self.values.shape[2])

    @property
    def shape(self) -> tuple[int, int, int]:
        return tuple(self.values.shape)  # type: ignore[return-value]

    @property
    def duration(self) -> float:
        """Length of the analysed audio in seconds."""
        return float(self.n_frames * self.config.hop_seconds)

    def channel(self, index: int = 0) -> np.ndarray:
        """The ``(n_frames, n_bins)`` matrix for one channel."""
        return self.values[index]

    def mono(self) -> np.ndarray:
        """Channel-averaged ``(n_frames, n_bins)`` matrix.

        Averaging happens in the power domain so that the result reflects total
        energy rather than cancelling correlated channels.
        """
        if self.n_channels == 1:
            return self.values[0]
        if self.config.scaling is SpectrumScaling.AMPLITUDE:
            return np.sqrt(np.mean(np.square(self.values, dtype=np.float64), axis=0))
        return np.mean(self.values, axis=0)

    def to_db(self, floor_db: float | None = None) -> np.ndarray:
        """Full ``(n_channels, n_frames, n_bins)`` matrix in dB."""
        return _to_db(self.values, self.config, floor_db)

    def db(self, channel: int | None = None, floor_db: float | None = None) -> np.ndarray:
        """dB matrix for one channel, or the mono mix when ``channel`` is None."""
        values = self.mono() if channel is None else self.values[channel]
        return _to_db(values, self.config, floor_db)

    def frame_at(self, time_s: float, channel: int = 0) -> np.ndarray:
        """Spectrum of the frame nearest ``time_s``."""
        index = int(np.clip(np.searchsorted(self.times, time_s), 0, self.n_frames - 1))
        return self.values[channel, index]

    def bin_at(self, frequency_hz: float, channel: int = 0) -> np.ndarray:
        """Level of the bin nearest ``frequency_hz`` across all frames."""
        index = int(np.clip(np.searchsorted(self.frequencies, frequency_hz), 0, self.n_bins - 1))
        return self.values[channel, :, index]

    def peak_frequencies(self, channel: int = 0) -> np.ndarray:
        """Dominant frequency of every frame, in hertz.

        The peak bin is refined by fitting a parabola to its two neighbours in
        the log domain, which recovers sub-bin accuracy for stationary tones.
        """
        frame = self.values[channel]
        if frame.size == 0:
            return np.zeros(0, dtype=np.float64)
        peaks = np.argmax(frame, axis=1)
        return _parabolic_peak_hz(frame, peaks, self.frequencies, self.config)

    def band_energy(self, low_hz: float, high_hz: float, channel: int = 0) -> np.ndarray:
        """Total energy per frame inside ``[low_hz, high_hz)``."""
        lo, hi = np.searchsorted(self.frequencies, (low_hz, high_hz))
        block = self.values[channel, :, lo:hi].astype(np.float64, copy=False)
        if self.config.scaling is SpectrumScaling.AMPLITUDE:
            block = np.square(block)
        return np.sum(block, axis=1)


@dataclass(frozen=True)
class SpectrumBars:
    """Band-aggregated spectrum, ready to drive a bar-graph display."""

    centers: np.ndarray
    edges: np.ndarray
    values_db: np.ndarray
    peaks_db: np.ndarray | None = None

    @property
    def n_bands(self) -> int:
        return int(self.centers.size)


# ---------------------------------------------------------------------------
# internals
# ---------------------------------------------------------------------------


def _to_db(values: np.ndarray, config: SpectralConfig, floor_db: float | None) -> np.ndarray:
    floor = config.db_floor if floor_db is None else floor_db
    factor = config.scaling.db_factor
    ref = config.reference if factor == 20.0 else config.reference**2
    eps = 10.0 ** (floor / factor) * max(ref, 1e-30)
    scaled = np.maximum(np.abs(values.astype(np.float64, copy=False)), eps) / ref
    return factor * np.log10(scaled)


def _parabolic_peak_hz(
    frame: np.ndarray,
    peaks: np.ndarray,
    frequencies: np.ndarray,
    config: SpectralConfig,
) -> np.ndarray:
    """Quadratic interpolation of peak position over the three highest bins."""
    n_bins = frame.shape[1]
    rows = np.arange(frame.shape[0])
    interior = (peaks > 0) & (peaks < n_bins - 1)
    offsets = np.zeros(frame.shape[0], dtype=np.float64)
    if np.any(interior):
        idx = peaks[interior]
        r = rows[interior]
        eps = 1e-30
        left = np.log(np.maximum(frame[r, idx - 1], eps))
        mid = np.log(np.maximum(frame[r, idx], eps))
        right = np.log(np.maximum(frame[r, idx + 1], eps))
        denom = left - 2.0 * mid + right
        safe = np.abs(denom) > 1e-12
        delta = np.zeros_like(denom)
        delta[safe] = 0.5 * (left[safe] - right[safe]) / denom[safe]
        offsets[interior] = np.clip(delta, -0.5, 0.5)
    return frequencies[peaks] + offsets * config.bin_spacing_hz


def _frame_view(signal: np.ndarray, frame_length: int, hop: int, n_frames: int) -> np.ndarray:
    """Zero-copy ``(n_frames, frame_length)`` strided view of ``signal``."""
    if n_frames <= 0:
        return np.empty((0, frame_length), dtype=signal.dtype)
    itemsize = signal.strides[-1]
    return np.lib.stride_tricks.as_strided(
        signal,
        shape=(n_frames, frame_length),
        strides=(hop * itemsize, itemsize),
        writeable=False,
    )


class SpectralAnalyzer:
    """Computes STFTs, spectrograms and calibrated spectra.

    The analyzer holds no per-signal state, so a single instance can be shared
    across threads and reused for every buffer that matches its
    :class:`SpectralConfig`.

    Examples
    --------
    >>> import numpy as np
    >>> sr, fft_size = 48_000, 4096
    >>> frequency = 85 * sr / fft_size              # exactly on bin 85
    >>> t = np.arange(sr) / sr
    >>> tone = 0.5 * np.sin(2 * np.pi * frequency * t)
    >>> analyzer = SpectralAnalyzer(sample_rate=sr, fft_size=fft_size, center=False)
    >>> spec = analyzer.spectrogram(tone)
    >>> round(float(np.max(spec.db())), 1)          # 0.5 amplitude -> -6 dBFS
    -6.0
    """

    def __init__(self, config: SpectralConfig | None = None, **overrides) -> None:
        if config is None:
            config = SpectralConfig(**overrides)
        elif overrides:
            config = config.with_(**overrides)
        self._config = config
        self._frequencies = config.frequencies()

    # -- configuration ----------------------------------------------------

    @property
    def config(self) -> SpectralConfig:
        return self._config

    @config.setter
    def config(self, config: SpectralConfig) -> None:
        self._config = config
        self._frequencies = config.frequencies()

    def reconfigure(self, **changes) -> SpectralAnalyzer:
        """Apply ``changes`` to the config in place and return ``self``."""
        self.config = self._config.with_(**changes)
        return self

    @property
    def frequencies(self) -> np.ndarray:
        """Bin centre frequencies in hertz, ``(n_bins,)``."""
        return self._frequencies

    @property
    def n_bins(self) -> int:
        return self._config.n_bins

    def frame_times(self, n_samples: int) -> np.ndarray:
        return self._config.frame_times(n_samples)

    # -- forward transform ------------------------------------------------

    def stft(
        self,
        audio: np.ndarray,
        channels_last: bool | None = None,
    ) -> np.ndarray:
        """Complex STFT of ``audio``.

        Returns ``(n_channels, n_frames, n_bins)`` complex coefficients, or
        ``(n_frames, n_bins)`` when ``audio`` is 1-D. No window or length
        normalisation is applied — use :meth:`spectrum_from_stft` for
        calibrated output, or :meth:`istft` to invert.
        """
        cfg = self._config
        planar, was_mono = as_planar(audio, channels_last=channels_last, dtype=cfg.dtype)
        n_samples = planar.shape[1]
        n_frames = cfg.n_frames(n_samples)
        complex_dtype = np.complex64 if cfg.dtype == np.float32 else np.complex128

        out = np.empty((planar.shape[0], n_frames, cfg.n_bins), dtype=complex_dtype)
        if n_frames == 0:
            return out[0] if was_mono else out

        window = cfg.window_info.samples.astype(cfg.dtype, copy=False)
        for channel_index, channel in enumerate(planar):
            self._stft_channel(channel, n_frames, window, out[channel_index])
        return out[0] if was_mono else out

    def _stft_channel(
        self,
        channel: np.ndarray,
        n_frames: int,
        window: np.ndarray,
        out: np.ndarray,
    ) -> None:
        cfg = self._config
        padded = self._pad_signal(channel, n_frames)
        frames = _frame_view(padded, cfg.window_size, cfg.hop_size, n_frames)

        needs_zero_pad = cfg.window_size != cfg.fft_size
        buffer = (
            np.zeros((min(n_frames, cfg.max_frames_per_chunk), cfg.fft_size), dtype=cfg.dtype)
            if needs_zero_pad
            else None
        )

        for start in range(0, n_frames, cfg.max_frames_per_chunk):
            stop = min(start + cfg.max_frames_per_chunk, n_frames)
            chunk = frames[start:stop]
            if buffer is not None:
                block = buffer[: stop - start]
                np.multiply(chunk, window, out=block[:, : cfg.window_size])
            else:
                block = chunk * window
            out[start:stop] = self._rfft(block)

    def _pad_signal(self, channel: np.ndarray, n_frames: int) -> np.ndarray:
        """Pad so that ``n_frames`` full frames can be read without bounds checks."""
        cfg = self._config
        lead = cfg.window_size // 2 if cfg.center else 0
        required = (n_frames - 1) * cfg.hop_size + cfg.window_size
        trail = max(0, required - (channel.shape[0] + lead))
        if lead == 0 and trail == 0:
            return np.ascontiguousarray(channel)
        if cfg.pad_mode == "constant":
            padded = np.zeros(channel.shape[0] + lead + trail, dtype=channel.dtype)
            padded[lead : lead + channel.shape[0]] = channel
            return padded
        # Reflection needs at least one sample to mirror against.
        lead = min(lead, max(0, channel.shape[0] - 1))
        trail_reflect = min(trail, max(0, channel.shape[0] - 1))
        padded = np.pad(channel, (lead, trail_reflect), mode=cfg.pad_mode)
        if trail_reflect < trail:
            padded = np.pad(padded, (0, trail - trail_reflect), mode="constant")
        return padded

    def _rfft(self, block: np.ndarray) -> np.ndarray:
        cfg = self._config
        if _HAVE_SCIPY_FFT:
            return _rfft(block, n=cfg.fft_size, axis=-1, workers=cfg.fft_workers)
        return _rfft(block, n=cfg.fft_size, axis=-1)

    # -- calibration ------------------------------------------------------

    def scaling_factors(self, scaling: SpectrumScaling | None = None) -> tuple[float, float]:
        """``(interior, edge)`` multipliers applied to ``|X|`` or ``|X|**2``.

        One-sided spectra fold negative frequencies onto their positive twins,
        which doubles every bin except DC and Nyquist — hence two factors.
        """
        cfg = self._config
        scaling = cfg.scaling if scaling is None else SpectrumScaling.coerce(scaling)
        info = cfg.window_info
        if scaling is SpectrumScaling.AMPLITUDE:
            edge = 1.0 / info.s1
        elif scaling is SpectrumScaling.POWER:
            edge = 1.0 / (info.s1**2)
        else:  # PSD
            edge = 1.0 / (cfg.sample_rate * info.s2)
        return 2.0 * edge, edge

    def spectrum_from_stft(
        self,
        stft: np.ndarray,
        scaling: SpectrumScaling | None = None,
    ) -> np.ndarray:
        """Convert complex STFT coefficients into a calibrated real spectrum."""
        cfg = self._config
        scaling = cfg.scaling if scaling is None else SpectrumScaling.coerce(scaling)
        interior, edge = self.scaling_factors(scaling)

        magnitude = np.abs(stft)
        values = magnitude if scaling is SpectrumScaling.AMPLITUDE else np.square(magnitude)
        values = values * interior
        values[..., 0] *= edge / interior
        if cfg.fft_size % 2 == 0 and values.shape[-1] > 1:
            values[..., -1] *= edge / interior
        return values

    def to_db(self, values: np.ndarray, floor_db: float | None = None) -> np.ndarray:
        """Convert calibrated spectrum values to dB using the configured floor."""
        return _to_db(values, self._config, floor_db)

    # -- high level -------------------------------------------------------

    def spectrogram(
        self,
        audio: np.ndarray,
        channels_last: bool | None = None,
        scaling: SpectrumScaling | None = None,
    ) -> Spectrogram:
        """Full calibrated spectrogram of ``audio``."""
        cfg = self._config
        planar, _ = as_planar(audio, channels_last=channels_last, dtype=cfg.dtype)
        stft = self.stft(planar, channels_last=False)
        values = self.spectrum_from_stft(stft, scaling=scaling)
        config = cfg if scaling is None else cfg.with_(scaling=SpectrumScaling.coerce(scaling))
        return Spectrogram(
            values=values,
            frequencies=self._frequencies,
            times=cfg.frame_times(planar.shape[1]),
            config=config,
        )

    def spectrum(
        self,
        block: np.ndarray,
        channels_last: bool | None = None,
        as_db: bool = True,
    ) -> np.ndarray:
        """Single-frame spectrum of exactly one block of samples.

        ``block`` shorter than ``window_size`` is zero-padded; longer input is
        truncated. Intended for meters and probes where one number per bin is
        wanted rather than a time axis.
        """
        cfg = self._config
        planar, was_mono = as_planar(block, channels_last=channels_last, dtype=cfg.dtype)
        n = planar.shape[1]
        if n < cfg.window_size:
            padded = np.zeros((planar.shape[0], cfg.window_size), dtype=cfg.dtype)
            padded[:, :n] = planar
            planar = padded
        elif n > cfg.window_size:
            planar = planar[:, : cfg.window_size]

        windowed = planar * cfg.window_info.samples.astype(cfg.dtype, copy=False)
        values = self.spectrum_from_stft(self._rfft(windowed))
        if as_db:
            values = self.to_db(values)
        return restore_layout(values, was_mono)

    # -- inverse ----------------------------------------------------------

    def istft(
        self,
        stft: np.ndarray,
        length: int | None = None,
    ) -> np.ndarray:
        """Weighted overlap-add inverse of :meth:`stft`.

        Uses the analysis window as the synthesis window and divides by the
        summed squared window, so the reconstruction is exact (to floating
        point) wherever the overlap-add denominator is non-zero — no COLA
        restriction on the hop size beyond that.

        ``length`` trims the result, which is needed to undo the centring pad
        and any trailing partial frame.
        """
        cfg = self._config
        spec = np.asarray(stft)
        was_mono = spec.ndim == 2
        if was_mono:
            spec = spec[np.newaxis]
        if spec.ndim != 3:
            raise ValueError(f"expected 2-D or 3-D STFT, got shape {spec.shape}")

        n_channels, n_frames, _ = spec.shape
        window = cfg.window_info.samples.astype(cfg.dtype, copy=False)
        total = (n_frames - 1) * cfg.hop_size + cfg.window_size if n_frames else 0

        out = np.zeros((n_channels, max(total, 0)), dtype=cfg.dtype)
        norm = np.zeros(max(total, 0), dtype=cfg.dtype)
        if n_frames:
            if _HAVE_SCIPY_FFT:
                frames = _irfft(spec, n=cfg.fft_size, axis=-1, workers=cfg.fft_workers)
            else:
                frames = _irfft(spec, n=cfg.fft_size, axis=-1)
            frames = frames[..., : cfg.window_size] * window
            square = np.square(window)
            for index in range(n_frames):
                start = index * cfg.hop_size
                out[:, start : start + cfg.window_size] += frames[:, index]
                norm[start : start + cfg.window_size] += square
            np.divide(out, np.maximum(norm, 1e-12), out=out)

        lead = cfg.window_size // 2 if cfg.center else 0
        out = out[:, lead:]
        if length is not None:
            if out.shape[1] < length:
                out = np.pad(out, ((0, 0), (0, length - out.shape[1])))
            out = out[:, :length]
        return out[0] if was_mono else out

    # -- streaming helpers ------------------------------------------------

    def iter_frames(
        self,
        blocks: Iterable[np.ndarray],
        channels_last: bool | None = None,
    ) -> Iterator[np.ndarray]:
        """Yield one complex STFT frame per hop from a stream of blocks.

        Blocks may be any length; the analyzer buffers the remainder. Yields
        ``(n_channels, n_bins)`` arrays. Note that streaming implies
        ``center=False`` semantics: the first frame covers samples ``0`` to
        ``window_size``.
        """
        cfg = self._config
        pending: np.ndarray | None = None
        window = cfg.window_info.samples.astype(cfg.dtype, copy=False)

        for block in blocks:
            planar, _ = as_planar(block, channels_last=channels_last, dtype=cfg.dtype)
            pending = planar if pending is None else np.concatenate([pending, planar], axis=1)
            while pending.shape[1] >= cfg.window_size:
                frame = pending[:, : cfg.window_size] * window
                yield self._rfft(frame)
                pending = pending[:, cfg.hop_size :]


class RealtimeSpectrum:
    """Streaming spectrum with analyzer ballistics for live displays.

    Feed it arbitrary-sized blocks; it emits one smoothed spectrum per hop and
    maintains falling peak-hold values, the same behaviour as the bar display
    in a hardware RTA or Audition's frequency analysis panel.

    Parameters
    ----------
    attack_ms / release_ms:
        Exponential time constants for rising and falling levels. Fast attack
        with slow release is what makes transients visible without flicker.
    peak_hold_s:
        How long a peak is held before it starts to fall. ``0`` disables hold.
    peak_decay_db_s:
        Fall rate of the peak markers once the hold expires.
    """

    def __init__(
        self,
        analyzer: SpectralAnalyzer | None = None,
        *,
        attack_ms: float = 10.0,
        release_ms: float = 300.0,
        peak_hold_s: float = 1.5,
        peak_decay_db_s: float = 20.0,
        **config_overrides,
    ) -> None:
        self.analyzer = analyzer or SpectralAnalyzer(**config_overrides)
        if config_overrides and analyzer is not None:
            self.analyzer.reconfigure(**config_overrides)

        self.attack_ms = float(attack_ms)
        self.release_ms = float(release_ms)
        self.peak_hold_s = float(peak_hold_s)
        self.peak_decay_db_s = float(peak_decay_db_s)

        self._pending: np.ndarray | None = None
        self._levels_db: np.ndarray | None = None
        self._peaks_db: np.ndarray | None = None
        self._hold_frames: np.ndarray | None = None
        self._band_plan: _BandPlan | None = None
        self._frames_seen = 0

    # -- lifecycle --------------------------------------------------------

    @property
    def config(self) -> SpectralConfig:
        return self.analyzer.config

    @property
    def frequencies(self) -> np.ndarray:
        return self.analyzer.frequencies

    @property
    def frames_processed(self) -> int:
        """Total hops consumed since construction or the last :meth:`reset`."""
        return self._frames_seen

    def reset(self) -> None:
        """Drop buffered audio and all smoothing state."""
        self._pending = None
        self._levels_db = None
        self._peaks_db = None
        self._hold_frames = None
        self._frames_seen = 0

    # -- feeding ----------------------------------------------------------

    def push(self, block: np.ndarray, channels_last: bool | None = None) -> int:
        """Consume a block of audio; return how many frames were produced.

        Channels are summed in the power domain into a single display
        spectrum, matching how a stereo RTA is normally read.
        """
        cfg = self.config
        planar, _ = as_planar(block, channels_last=channels_last, dtype=cfg.dtype)
        self._pending = (
            planar if self._pending is None else np.concatenate([self._pending, planar], axis=1)
        )

        produced = 0
        window = cfg.window_info.samples.astype(cfg.dtype, copy=False)
        while self._pending.shape[1] >= cfg.window_size:
            frame = self._pending[:, : cfg.window_size] * window
            values = self.analyzer.spectrum_from_stft(self.analyzer._rfft(frame))
            if values.shape[0] > 1:
                if cfg.scaling is SpectrumScaling.AMPLITUDE:
                    values = np.sqrt(np.mean(np.square(values, dtype=np.float64), axis=0))
                else:
                    values = np.mean(values, axis=0)
            else:
                values = values[0]
            self._update(self.analyzer.to_db(values))
            self._pending = self._pending[:, cfg.hop_size :]
            produced += 1
        self._frames_seen += produced
        return produced

    def _update(self, frame_db: np.ndarray) -> None:
        hop_s = self.config.hop_seconds
        if self._levels_db is None:
            self._levels_db = frame_db.copy()
            self._peaks_db = frame_db.copy()
            self._hold_frames = np.zeros(frame_db.shape, dtype=np.float64)
        else:
            rising = frame_db > self._levels_db
            alpha = np.where(
                rising,
                _smoothing_alpha(self.attack_ms / 1000.0, hop_s),
                _smoothing_alpha(self.release_ms / 1000.0, hop_s),
            )
            self._levels_db += alpha * (frame_db - self._levels_db)

        assert self._peaks_db is not None and self._hold_frames is not None
        hold_limit = self.peak_hold_s / hop_s if hop_s > 0 else 0.0
        beat = self._levels_db > self._peaks_db
        self._peaks_db = np.where(beat, self._levels_db, self._peaks_db)
        self._hold_frames = np.where(beat, 0.0, self._hold_frames + 1.0)
        decaying = self._hold_frames > hold_limit
        self._peaks_db = np.where(
            decaying,
            np.maximum(self._peaks_db - self.peak_decay_db_s * hop_s, self._levels_db),
            self._peaks_db,
        )

    # -- reading ----------------------------------------------------------

    @property
    def levels_db(self) -> np.ndarray:
        """Smoothed per-bin levels in dB; all-floor before the first frame."""
        if self._levels_db is None:
            return np.full(self.analyzer.n_bins, self.config.db_floor)
        return self._levels_db

    @property
    def peaks_db(self) -> np.ndarray:
        """Peak-hold markers in dB."""
        if self._peaks_db is None:
            return np.full(self.analyzer.n_bins, self.config.db_floor)
        return self._peaks_db

    def bars(
        self,
        n_bands: int = 31,
        f_min: float = 20.0,
        f_max: float | None = None,
        include_peaks: bool = True,
    ) -> SpectrumBars:
        """Aggregate the current spectrum into ``n_bands`` log-spaced bands.

        Bands sum energy rather than averaging dB, so a band that contains two
        equal tones reads 3 dB hotter than one containing a single tone — which
        is the physically correct behaviour for a band-limited meter.
        """
        f_max = f_max if f_max is not None else self.config.sample_rate / 2.0
        plan = self._band_plan
        if plan is None or not plan.matches(n_bands, f_min, f_max, self.frequencies.size):
            plan = _BandPlan(self.frequencies, n_bands, f_min, f_max)
            self._band_plan = plan
        return SpectrumBars(
            centers=plan.centers,
            edges=plan.edges,
            values_db=plan.aggregate_db(self.levels_db),
            peaks_db=plan.aggregate_db(self.peaks_db) if include_peaks else None,
        )


def _smoothing_alpha(time_constant_s: float, step_s: float) -> float:
    """One-pole coefficient for a given time constant and update period."""
    if time_constant_s <= 0.0 or step_s <= 0.0:
        return 1.0
    return float(1.0 - math.exp(-step_s / time_constant_s))


class _BandPlan:
    """Precomputed mapping from FFT bins to logarithmically spaced bands."""

    def __init__(self, frequencies: np.ndarray, n_bands: int, f_min: float, f_max: float) -> None:
        if n_bands < 1:
            raise ValueError("n_bands must be at least 1")
        self.n_bands = int(n_bands)
        self.n_bins = int(frequencies.size)
        self.requested = (float(f_min), float(f_max))

        nyquist = float(frequencies[-1]) if frequencies.size else float(f_max)
        low = max(float(f_min), float(frequencies[1]) if frequencies.size > 1 else 1e-3)
        high = min(float(f_max), nyquist)
        if high <= low:
            raise ValueError(f"empty band range: f_min={low}, f_max={high}")

        self.edges = np.geomspace(low, high, self.n_bands + 1)
        self.centers = np.sqrt(self.edges[:-1] * self.edges[1:])
        bounds = np.searchsorted(frequencies, self.edges)
        self._starts = bounds[:-1]
        self._stops = np.maximum(bounds[1:], bounds[:-1])
        # Bands narrower than one bin get the nearest bin instead of nothing.
        self._fallback = np.clip(
            np.searchsorted(frequencies, self.centers), 0, max(self.n_bins - 1, 0)
        )
        self._empty = self._stops <= self._starts

    def matches(self, n_bands: int, f_min: float, f_max: float, n_bins: int) -> bool:
        return (
            self.n_bands == n_bands
            and self.n_bins == n_bins
            and self.requested == (float(f_min), float(f_max))
        )

    def aggregate_db(self, levels_db: np.ndarray) -> np.ndarray:
        """Energy-sum ``levels_db`` (already in dB) within each band."""
        power = np.power(10.0, np.asarray(levels_db, dtype=np.float64) / 10.0)
        out = np.empty(self.n_bands, dtype=np.float64)
        for index in range(self.n_bands):
            if self._empty[index]:
                out[index] = power[self._fallback[index]]
            else:
                out[index] = np.sum(power[self._starts[index] : self._stops[index]])
        return 10.0 * np.log10(np.maximum(out, 1e-30))


class WaterfallBuffer:
    """Fixed-capacity ring buffer of dB frames for a scrolling spectrogram.

    Pushing is O(n_bins) and reading returns a contiguous, oldest-first view,
    so a repaint never has to shift the whole history.
    """

    def __init__(self, n_bins: int, capacity: int = 512, fill_db: float = -140.0) -> None:
        if n_bins < 1 or capacity < 1:
            raise ValueError("n_bins and capacity must both be positive")
        self.n_bins = int(n_bins)
        self.capacity = int(capacity)
        self.fill_db = float(fill_db)
        self._data = np.full((self.capacity, self.n_bins), self.fill_db, dtype=np.float32)
        self._write = 0
        self._count = 0

    def __len__(self) -> int:
        return self._count

    @property
    def is_full(self) -> bool:
        return self._count >= self.capacity

    def clear(self) -> None:
        self._data.fill(self.fill_db)
        self._write = 0
        self._count = 0

    def push(self, frame_db: np.ndarray) -> None:
        """Append one spectrum, evicting the oldest when full."""
        frame = np.asarray(frame_db, dtype=np.float32)
        if frame.shape != (self.n_bins,):
            raise ValueError(f"expected frame of shape ({self.n_bins},), got {frame.shape}")
        self._data[self._write] = frame
        self._write = (self._write + 1) % self.capacity
        self._count = min(self._count + 1, self.capacity)

    def extend(self, frames_db: Sequence[np.ndarray] | np.ndarray) -> None:
        """Append several spectra in order."""
        for frame in frames_db:
            self.push(frame)

    def image(self, rows: int | None = None, newest_first: bool = False) -> np.ndarray:
        """Return ``(rows, n_bins)`` of history, oldest first by default.

        Slots never written are filled with ``fill_db`` so the array is always
        exactly ``rows`` tall and safe to hand straight to a renderer.
        """
        rows = self.capacity if rows is None else min(int(rows), self.capacity)
        # Rolling by -_write puts the oldest slot first; unwritten slots still
        # hold fill_db and naturally land at the front.
        ordered = np.roll(self._data, -self._write, axis=0) if self._write else self._data
        out = ordered[-rows:]
        return out[::-1] if newest_first else out
