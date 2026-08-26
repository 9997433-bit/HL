"""ITU-R BS.1770 / EBU R 128 loudness measurement.

Loudness is not level. Two masters can share a peak of -1 dBFS and still be
6 LU apart, which is why delivery specs are written in LUFS: -14 for most
streaming platforms, -23 for EBU R 128 broadcast. This module measures that
number the way the standard defines it:

1. **K-weighting** — a +4 dB high shelf above ~1.5 kHz (the head's acoustic
   response) followed by a 38 Hz high-pass (the ear's insensitivity to very low
   frequencies). Both are the second-order sections BS.1770-4 Table 1 and 2
   specify at 48 kHz; at any other rate they are re-derived from the same
   analog prototypes, so the response is right at 44.1 kHz and 96 kHz too.
2. **Mean square over 400 ms blocks**, overlapping by 75%.
3. **Channel weighting** — surrounds count 1.5 dB louder than the front pair,
   LFE not at all.
4. **Two-stage gating** — blocks below -70 LUFS absolute are dropped, then
   blocks more than 10 LU below the ungated mean. Gating is what stops the
   silence between dialogue from dragging a programme's reading down.

Examples
--------
>>> import numpy as np
>>> sr = 48_000
>>> t = np.arange(sr * 2) / sr
>>> tone = 0.5 * np.sin(2 * np.pi * 1000.0 * t)      # -9.03 dBFS RMS
>>> meter = LoudnessMeter(sr)
>>> round(meter.integrated(tone), 1)
-9.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.signal import sosfilt

from .util import as_planar, linear_to_db, true_peak_level

__all__ = [
    "ABSOLUTE_GATE_LUFS",
    "RELATIVE_GATE_LU",
    "LoudnessReport",
    "LoudnessMeter",
    "channel_weights",
    "integrated_loudness",
    "k_weighting_sos",
]

#: BS.1770 calibration offset, chosen so a K-weighted full-scale sine reads
#: 0 LKFS in the front-left channel alone.
_OFFSET_LU = -0.691

#: Blocks quieter than this never count towards the integrated loudness.
ABSOLUTE_GATE_LUFS = -70.0

#: Second gate, relative to the ungated mean of the surviving blocks.
RELATIVE_GATE_LU = -10.0

#: Momentary loudness window, in seconds (BS.1770 "gating block").
MOMENTARY_WINDOW_S = 0.400

#: Short-term loudness window, in seconds (EBU Tech 3341).
SHORT_TERM_WINDOW_S = 3.0

#: Window overlap used for both. 75% is what the standard specifies for the
#: gating block and what every compliant meter uses for the short-term trace.
WINDOW_OVERLAP = 0.75

#: Percentiles of the gated short-term distribution that bound the loudness
#: range (EBU Tech 3342).
_LRA_PERCENTILES = (10.0, 95.0)
_LRA_RELATIVE_GATE_LU = -20.0

# Analog prototypes behind the BS.1770-4 coefficient tables. Re-deriving from
# these is what makes the filter correct at sample rates the tables do not list.
_SHELF_FREQUENCY_HZ = 1681.974450955533
_SHELF_GAIN_DB = 3.999843853973347
_SHELF_Q = 0.7071752369554196
_SHELF_VB_EXPONENT = 0.4996667741545416
_HIGHPASS_FREQUENCY_HZ = 38.13547087602444
_HIGHPASS_Q = 0.5003270373238773


@lru_cache(maxsize=16)
def k_weighting_sos(sample_rate: float) -> np.ndarray:
    """K-weighting filter as a ``(2, 6)`` second-order-section matrix.

    Section 0 is the high shelf, section 1 the high-pass. At 48 kHz the
    coefficients match BS.1770-4 Tables 1 and 2 to 1e-6.
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    shelf_k = math.tan(math.pi * _SHELF_FREQUENCY_HZ / sample_rate)
    vh = 10.0 ** (_SHELF_GAIN_DB / 20.0)
    vb = vh**_SHELF_VB_EXPONENT
    shelf_a0 = 1.0 + shelf_k / _SHELF_Q + shelf_k**2
    shelf = np.array(
        [
            (vh + vb * shelf_k / _SHELF_Q + shelf_k**2) / shelf_a0,
            2.0 * (shelf_k**2 - vh) / shelf_a0,
            (vh - vb * shelf_k / _SHELF_Q + shelf_k**2) / shelf_a0,
            1.0,
            2.0 * (shelf_k**2 - 1.0) / shelf_a0,
            (1.0 - shelf_k / _SHELF_Q + shelf_k**2) / shelf_a0,
        ],
        dtype=np.float64,
    )

    hp_k = math.tan(math.pi * _HIGHPASS_FREQUENCY_HZ / sample_rate)
    hp_a0 = 1.0 + hp_k / _HIGHPASS_Q + hp_k**2
    highpass = np.array(
        [
            1.0,
            -2.0,
            1.0,
            1.0,
            2.0 * (hp_k**2 - 1.0) / hp_a0,
            (1.0 - hp_k / _HIGHPASS_Q + hp_k**2) / hp_a0,
        ],
        dtype=np.float64,
    )
    return np.stack([shelf, highpass])


def channel_weights(n_channels: int) -> tuple[float, ...]:
    """BS.1770 weights ``G_i`` for a channel count, in ITU channel order.

    Surround channels are weighted ``1.41`` (+1.5 dB) because sound arriving
    from behind is judged louder than the same level from the front; the LFE of
    a 5.1 layout is excluded entirely.
    """
    surround = 1.41
    layouts: dict[int, tuple[float, ...]] = {
        1: (1.0,),
        2: (1.0, 1.0),
        3: (1.0, 1.0, 1.0),
        4: (1.0, 1.0, surround, surround),
        5: (1.0, 1.0, 1.0, surround, surround),
        6: (1.0, 1.0, 1.0, 0.0, surround, surround),  # L R C LFE Ls Rs
    }
    if n_channels < 1:
        raise ValueError("n_channels must be at least 1")
    return layouts.get(n_channels, (1.0,) * n_channels)


@dataclass(frozen=True)
class LoudnessReport:
    """Everything an R 128 compliance check asks for, measured in one pass."""

    integrated_lufs: float
    momentary_max_lufs: float
    short_term_max_lufs: float
    loudness_range_lu: float
    true_peak_dbtp: float
    sample_peak_dbfs: float
    duration_s: float
    gated_blocks: int

    def target_offset_lu(self, target_lufs: float = -23.0) -> float:
        """How far the programme is from ``target_lufs``; negative means quiet."""
        return self.integrated_lufs - float(target_lufs)

    def __str__(self) -> str:
        return (
            f"{format_lufs(self.integrated_lufs)} integrated, "
            f"{format_lufs(self.short_term_max_lufs)} short-term max, "
            f"LRA {self.loudness_range_lu:.1f} LU, "
            f"{self.true_peak_dbtp:.2f} dBTP"
        )


def format_lufs(value: float, unit: str = "LUFS") -> str:
    """Render a loudness reading, with a proper -inf for digital silence."""
    if not math.isfinite(value):
        return f"-\u221e {unit}"
    return f"{value:.1f} {unit}"


class LoudnessMeter:
    """Measures BS.1770 loudness of complete buffers.

    One instance is tied to a sample rate and channel layout; the filter
    coefficients are cached, so measuring many clips at the same rate costs
    nothing extra.

    Examples
    --------
    >>> import numpy as np
    >>> sr = 48_000
    >>> noise = np.random.default_rng(0).normal(0.0, 0.1, (2, sr * 4))
    >>> report = LoudnessMeter(sr).analyze(noise)
    >>> round(report.integrated_lufs, 1)
    -13.8
    >>> round(report.target_offset_lu(-14.0), 1)   # 0.2 LU over a streaming target
    0.2
    """

    def __init__(
        self,
        sample_rate: float,
        weights: tuple[float, ...] | None = None,
    ) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        self.sample_rate = float(sample_rate)
        self._weights = tuple(float(w) for w in weights) if weights is not None else None

    # -- filtering ---------------------------------------------------------

    @property
    def sos(self) -> np.ndarray:
        """K-weighting sections for this meter's sample rate."""
        return k_weighting_sos(self.sample_rate)

    def k_weight(self, audio: np.ndarray, channels_last: bool | None = None) -> np.ndarray:
        """Apply the K-weighting filter, returning planar float64 audio."""
        planar, _ = as_planar(audio, channels_last=channels_last, dtype=np.float64)
        if planar.shape[1] == 0:
            return planar
        return sosfilt(self.sos, planar, axis=-1)

    def weights_for(self, n_channels: int) -> np.ndarray:
        weights = self._weights if self._weights is not None else channel_weights(n_channels)
        if len(weights) < n_channels:
            weights = tuple(weights) + (1.0,) * (n_channels - len(weights))
        return np.asarray(weights[:n_channels], dtype=np.float64)

    # -- block loudness ----------------------------------------------------

    def block_loudness(
        self,
        audio: np.ndarray,
        window_s: float = MOMENTARY_WINDOW_S,
        overlap: float = WINDOW_OVERLAP,
        channels_last: bool | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """``(times, lufs)`` for every gating block of ``window_s`` seconds.

        ``times`` are the block *end* times, which is where a live meter would
        display them. Buffers shorter than one window produce empty arrays —
        the standard has nothing to say about a fragment.
        """
        power, times = self._block_power(audio, window_s, overlap, channels_last)
        return times, _power_to_lufs(power)

    def _block_power(
        self,
        audio: np.ndarray,
        window_s: float,
        overlap: float,
        channels_last: bool | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Channel-weighted mean square of each block, plus the block end times."""
        weighted = self.k_weight(audio, channels_last=channels_last)
        n_channels, n_samples = weighted.shape
        window = int(round(window_s * self.sample_rate))
        hop = max(1, int(round(window * (1.0 - overlap))))
        if window < 1 or n_samples < window:
            return np.zeros(0), np.zeros(0)

        starts = np.arange(0, n_samples - window + 1, hop)
        # One cumulative sum per channel turns every block's mean square into
        # two lookups, so a 60-minute file costs the same per block as a short
        # one instead of re-summing 400 ms of samples four times over.
        cumulative = np.zeros((n_channels, n_samples + 1), dtype=np.float64)
        np.cumsum(np.square(weighted), axis=-1, out=cumulative[:, 1:])
        mean_square = (cumulative[:, starts + window] - cumulative[:, starts]) / window

        weights = self.weights_for(n_channels)[:, np.newaxis]
        power = np.sum(mean_square * weights, axis=0)
        times = (starts + window) / self.sample_rate
        return power, times

    # -- headline numbers --------------------------------------------------

    def momentary(
        self, audio: np.ndarray, channels_last: bool | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """``(times, lufs)`` on the 400 ms window."""
        return self.block_loudness(
            audio, MOMENTARY_WINDOW_S, WINDOW_OVERLAP, channels_last=channels_last
        )

    def short_term(
        self, audio: np.ndarray, channels_last: bool | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """``(times, lufs)`` on the 3 s window."""
        return self.block_loudness(
            audio, SHORT_TERM_WINDOW_S, WINDOW_OVERLAP, channels_last=channels_last
        )

    def integrated(self, audio: np.ndarray, channels_last: bool | None = None) -> float:
        """Gated integrated loudness in LUFS, or ``-inf`` for silence."""
        power, _ = self._block_power(
            audio, MOMENTARY_WINDOW_S, WINDOW_OVERLAP, channels_last
        )
        return self._gated_loudness(power)[0]

    def _gated_loudness(self, power: np.ndarray) -> tuple[float, int]:
        """Two-stage gate over block powers; returns ``(lufs, blocks_counted)``."""
        if power.size == 0:
            return (-math.inf, 0)

        absolute = _power_to_lufs(power) > ABSOLUTE_GATE_LUFS
        if not np.any(absolute):
            return (-math.inf, 0)

        # The relative threshold is derived from the mean of the blocks that
        # passed the absolute gate — mean *power*, not mean dB.
        threshold = _power_to_lufs(np.mean(power[absolute])) + RELATIVE_GATE_LU
        keep = absolute & (_power_to_lufs(power) > threshold)
        if not np.any(keep):
            return (-math.inf, 0)
        return (float(_power_to_lufs(np.mean(power[keep]))), int(np.count_nonzero(keep)))

    def loudness_range(self, audio: np.ndarray, channels_last: bool | None = None) -> float:
        """EBU Tech 3342 loudness range in LU: how much the level moves about."""
        power, _ = self._block_power(
            audio, SHORT_TERM_WINDOW_S, WINDOW_OVERLAP, channels_last
        )
        return self._range_from_power(power)

    def _range_from_power(self, power: np.ndarray) -> float:
        if power.size == 0:
            return 0.0
        lufs = _power_to_lufs(power)
        absolute = lufs > ABSOLUTE_GATE_LUFS
        if not np.any(absolute):
            return 0.0
        threshold = _power_to_lufs(np.mean(power[absolute])) + _LRA_RELATIVE_GATE_LU
        kept = lufs[absolute & (lufs > threshold)]
        if kept.size == 0:
            return 0.0
        low, high = np.percentile(kept, _LRA_PERCENTILES)
        return float(high - low)

    def analyze(self, audio: np.ndarray, channels_last: bool | None = None) -> LoudnessReport:
        """Full report: integrated, momentary/short-term maxima, LRA and peaks."""
        planar, _ = as_planar(audio, channels_last=channels_last, dtype=np.float64)
        momentary_power, _ = self._block_power(
            planar, MOMENTARY_WINDOW_S, WINDOW_OVERLAP, channels_last=False
        )
        short_power, _ = self._block_power(
            planar, SHORT_TERM_WINDOW_S, WINDOW_OVERLAP, channels_last=False
        )
        integrated, gated_blocks = self._gated_loudness(momentary_power)

        sample_peak = float(np.max(np.abs(planar))) if planar.size else 0.0
        return LoudnessReport(
            integrated_lufs=integrated,
            momentary_max_lufs=_max_lufs(momentary_power),
            short_term_max_lufs=_max_lufs(short_power),
            loudness_range_lu=self._range_from_power(short_power),
            true_peak_dbtp=float(linear_to_db(true_peak_level(planar))),
            sample_peak_dbfs=float(linear_to_db(sample_peak)),
            duration_s=planar.shape[1] / self.sample_rate,
            gated_blocks=gated_blocks,
        )


def integrated_loudness(
    audio: np.ndarray, sample_rate: float, channels_last: bool | None = None
) -> float:
    """One-shot :meth:`LoudnessMeter.integrated` for callers without a meter."""
    return LoudnessMeter(sample_rate).integrated(audio, channels_last=channels_last)


def _power_to_lufs(power: np.ndarray | float) -> np.ndarray | float:
    """Channel-summed mean square -> LUFS, with silence mapping to ``-inf``."""
    values = np.asarray(power, dtype=np.float64)
    with np.errstate(divide="ignore"):
        return _OFFSET_LU + 10.0 * np.log10(values)


def _max_lufs(power: np.ndarray) -> float:
    if power.size == 0:
        return -math.inf
    return float(_power_to_lufs(np.max(power)))
