"""ITU-R BS.1770-4 / EBU R 128 loudness measurement.

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

Three measurement windows come out of that machinery, and the standards
disagree about how often each is stepped, so each one is stepped the way the
document that defines it says:

============  ==========  ===============  ================================
Reading       Window      Step             Defined by
============  ==========  ===============  ================================
Momentary     400 ms      100 ms (10 Hz)   BS.1770-4 gating block, EBU 3341
Short-term    3 s         100 ms (10 Hz)   EBU Tech 3341 (meter refresh)
LRA           3 s         1 s              EBU Tech 3342
True peak     --          4x interpolated  BS.1770-4 Annex 2
============  ==========  ===============  ================================

Measuring a file uses :class:`LoudnessMeter`, which is stateless and can be
shared between threads. Metering a live stream uses
:class:`StreamingLoudnessMeter`, which carries the filter state and the
100 ms energy grid across calls and therefore reports the same numbers the
offline meter would give for the concatenated blocks.

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
from typing import Any

import numpy as np
from scipy.signal import sosfilt, sosfilt_zi

from .util import (
    TRUE_PEAK_KERNEL_HALF,
    as_planar,
    linear_to_db,
    true_peak_level,
)

__all__ = [
    "ABSOLUTE_GATE_LUFS",
    "DELIVERY_TARGETS",
    "LRA_STEP_S",
    "MOMENTARY_STEP_S",
    "MOMENTARY_WINDOW_S",
    "RELATIVE_GATE_LU",
    "SHORT_TERM_STEP_S",
    "SHORT_TERM_WINDOW_S",
    "ComplianceResult",
    "DeliveryTarget",
    "LoudnessMeter",
    "LoudnessReport",
    "StreamingLoudnessMeter",
    "channel_weights",
    "delivery_target",
    "format_lufs",
    "integrated_loudness",
    "k_weighting_sos",
    "true_peak_oversample",
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

#: Step between gating blocks: 75% overlap, and the 10 Hz refresh EBU Tech 3341
#: requires of a compliant meter's momentary and short-term displays.
MOMENTARY_STEP_S = 0.100
SHORT_TERM_STEP_S = 0.100

#: EBU Tech 3342 builds the loudness range from short-term readings taken once
#: a second, not from the 10 Hz display trace.
LRA_STEP_S = 1.0

#: Percentiles of the gated short-term distribution that bound the loudness
#: range (EBU Tech 3342).
_LRA_PERCENTILES = (10.0, 95.0)
_LRA_RELATIVE_GATE_LU = -20.0

#: Interpolated rate a true-peak meter has to reach. BS.1770-4 Annex 2 specifies
#: 4x oversampling for 48 kHz material, i.e. 192 kHz; expressing the rule as a
#: rate rather than a factor keeps the same interpolation density at 44.1 kHz
#: (4x -> 176.4 kHz) and stops 96 kHz material from being oversampled twice as
#: far as it needs to be.
TRUE_PEAK_MIN_RATE_HZ = 176_400.0

#: Ceiling on the oversampling factor, so an 8 kHz file does not ask for 32x.
_MAX_TRUE_PEAK_OVERSAMPLE = 8

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


def true_peak_oversample(sample_rate: float) -> int:
    """Oversampling factor a BS.1770-4 Annex 2 true-peak meter needs.

    A power of two, chosen so the interpolated rate reaches
    :data:`TRUE_PEAK_MIN_RATE_HZ`: 4x at 44.1 and 48 kHz, 2x at 88.2 and
    96 kHz, and none at all once the material is already sampled that finely.

    Examples
    --------
    >>> [true_peak_oversample(rate) for rate in (44_100, 48_000, 96_000, 192_000)]
    [4, 4, 2, 1]
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    factor = 1
    while sample_rate * factor < TRUE_PEAK_MIN_RATE_HZ and factor < _MAX_TRUE_PEAK_OVERSAMPLE:
        factor *= 2
    return factor


# ---------------------------------------------------------------------------
# Delivery specifications
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeliveryTarget:
    """A published loudness specification, as a thing a report can be checked against.

    Parameters
    ----------
    integrated_lufs:
        Programme loudness the platform asks for.
    tolerance_lu:
        How far either side of it is still accepted. Broadcast specs state one
        (EBU R 128 allows +-0.5 LU); streaming platforms normalise on playback
        instead, so their entry is generous and the true-peak ceiling is the
        part that actually matters.
    max_true_peak_dbtp:
        Ceiling on the inter-sample peak. Lossy encoders overshoot, which is
        why every modern spec leaves at least 1 dB of room below full scale.
    max_lra_lu:
        Optional cap on the loudness range; ``None`` means the spec reports it
        without constraining it.
    """

    name: str
    integrated_lufs: float
    tolerance_lu: float
    max_true_peak_dbtp: float
    max_lra_lu: float | None = None

    def __str__(self) -> str:
        return (
            f"{self.name}: {self.integrated_lufs:+.0f} LUFS "
            f"+-{self.tolerance_lu:.1f} LU, <= {self.max_true_peak_dbtp:.1f} dBTP"
        )


#: The specifications a master is usually checked against. Keys are lowercase
#: and hyphen-insensitive; :func:`delivery_target` does the lookup.
DELIVERY_TARGETS: dict[str, DeliveryTarget] = {
    "ebu_r128": DeliveryTarget("EBU R 128", -23.0, 0.5, -1.0),
    "atsc_a85": DeliveryTarget("ATSC A/85", -24.0, 2.0, -2.0),
    "spotify": DeliveryTarget("Spotify", -14.0, 1.0, -1.0),
    "youtube": DeliveryTarget("YouTube", -14.0, 1.0, -1.0),
    "apple_podcasts": DeliveryTarget("Apple Podcasts", -16.0, 1.0, -1.0),
    "amazon_alexa": DeliveryTarget("Amazon Alexa", -14.0, 2.0, -2.0),
}


def delivery_target(target: DeliveryTarget | str) -> DeliveryTarget:
    """Resolve a :class:`DeliveryTarget`, by object or by name.

    Examples
    --------
    >>> delivery_target("EBU R128").integrated_lufs
    -23.0
    """
    if isinstance(target, DeliveryTarget):
        return target
    key = str(target).strip().lower().replace("-", "_").replace(" ", "_").replace("/", "")
    if key in DELIVERY_TARGETS:
        return DELIVERY_TARGETS[key]
    raise KeyError(f"unknown delivery target {target!r}; known: {sorted(DELIVERY_TARGETS)}")


@dataclass(frozen=True)
class ComplianceResult:
    """Verdict of checking a :class:`LoudnessReport` against a spec."""

    target: DeliveryTarget
    integrated_lufs: float
    true_peak_dbtp: float
    loudness_range_lu: float
    failures: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.failures

    @property
    def gain_to_target_db(self) -> float:
        """Gain that would put the programme on target, ignoring the ceiling."""
        if not math.isfinite(self.integrated_lufs):
            return 0.0
        return self.target.integrated_lufs - self.integrated_lufs

    def __bool__(self) -> bool:
        return self.passed

    def __str__(self) -> str:
        if self.passed:
            return f"{self.target.name}: pass ({format_lufs(self.integrated_lufs)})"
        return f"{self.target.name}: FAIL — " + "; ".join(self.failures)


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
    threshold_lufs: float = -math.inf
    true_peak_per_channel_dbtp: tuple[float, ...] = ()
    sample_rate: float = 0.0

    @property
    def n_channels(self) -> int:
        return len(self.true_peak_per_channel_dbtp)

    def target_offset_lu(self, target_lufs: float = -23.0) -> float:
        """How far the programme is from ``target_lufs``; negative means quiet."""
        return self.integrated_lufs - float(target_lufs)

    def normalization_gain_db(
        self,
        target: DeliveryTarget | str | float = -23.0,
        respect_ceiling: bool = True,
    ) -> float:
        """Gain that lands the programme on ``target``.

        With ``respect_ceiling`` the gain is held back so the true peak stays
        under the spec's ceiling, which is the difference between a master that
        meets a delivery spec and one that only meets half of it. A programme
        that cannot reach the loudness target without clipping needs a limiter,
        and the shortfall is visible as the gap that remains.
        """
        if isinstance(target, int | float):
            spec = DeliveryTarget("custom", float(target), 0.5, 0.0)
            respect_ceiling = False
        else:
            spec = delivery_target(target)
        if not math.isfinite(self.integrated_lufs):
            return 0.0
        gain = spec.integrated_lufs - self.integrated_lufs
        if respect_ceiling and math.isfinite(self.true_peak_dbtp):
            gain = min(gain, spec.max_true_peak_dbtp - self.true_peak_dbtp)
        return gain

    def check(self, target: DeliveryTarget | str = "ebu_r128") -> ComplianceResult:
        """Check this measurement against a delivery specification.

        Examples
        --------
        >>> import numpy as np
        >>> sr = 48_000
        >>> tone = 10 ** (-23 / 20) * np.sin(
        ...     2 * np.pi * 1000.0 * np.arange(sr * 4) / sr
        ... )
        >>> result = LoudnessMeter(sr).analyze(np.stack([tone, tone])).check("EBU R128")
        >>> result.passed
        True
        """
        spec = delivery_target(target)
        failures: list[str] = []
        if not math.isfinite(self.integrated_lufs):
            failures.append("no gated audio to measure")
        elif abs(self.integrated_lufs - spec.integrated_lufs) > spec.tolerance_lu:
            failures.append(
                f"integrated {self.integrated_lufs:.1f} LUFS is "
                f"{self.integrated_lufs - spec.integrated_lufs:+.1f} LU off "
                f"{spec.integrated_lufs:.1f}"
            )
        if self.true_peak_dbtp > spec.max_true_peak_dbtp:
            failures.append(
                f"true peak {self.true_peak_dbtp:.2f} dBTP exceeds "
                f"{spec.max_true_peak_dbtp:.1f} dBTP"
            )
        if spec.max_lra_lu is not None and self.loudness_range_lu > spec.max_lra_lu:
            failures.append(
                f"loudness range {self.loudness_range_lu:.1f} LU exceeds "
                f"{spec.max_lra_lu:.1f} LU"
            )
        return ComplianceResult(
            target=spec,
            integrated_lufs=self.integrated_lufs,
            true_peak_dbtp=self.true_peak_dbtp,
            loudness_range_lu=self.loudness_range_lu,
            failures=tuple(failures),
        )

    def as_dict(self) -> dict[str, Any]:
        """Flat, JSON-friendly snapshot for a report file or a session state."""
        return {
            "integrated_lufs": self.integrated_lufs,
            "momentary_max_lufs": self.momentary_max_lufs,
            "short_term_max_lufs": self.short_term_max_lufs,
            "loudness_range_lu": self.loudness_range_lu,
            "true_peak_dbtp": self.true_peak_dbtp,
            "true_peak_per_channel_dbtp": list(self.true_peak_per_channel_dbtp),
            "sample_peak_dbfs": self.sample_peak_dbfs,
            "threshold_lufs": self.threshold_lufs,
            "duration_s": self.duration_s,
            "gated_blocks": self.gated_blocks,
            "sample_rate": self.sample_rate,
        }

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
    nothing extra. The meter holds no per-signal state, so a single instance
    can be shared between threads — :class:`StreamingLoudnessMeter` is the
    stateful one.

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
        step_s: float = MOMENTARY_STEP_S,
        channels_last: bool | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """``(times, lufs)`` for every gating block of ``window_s`` seconds.

        ``times`` are the block *end* times, which is where a live meter would
        display them. Buffers shorter than one window produce empty arrays —
        the standard has nothing to say about a fragment.
        """
        power, times = self._block_power(audio, window_s, step_s, channels_last)
        return times, _power_to_lufs(power)

    def _block_power(
        self,
        audio: np.ndarray,
        window_s: float,
        step_s: float,
        channels_last: bool | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Channel-weighted mean square of each block, plus the block end times."""
        weighted = self.k_weight(audio, channels_last=channels_last)
        n_channels, n_samples = weighted.shape
        window = int(round(window_s * self.sample_rate))
        hop = max(1, int(round(step_s * self.sample_rate)))
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
        """``(times, lufs)`` on the 400 ms window, stepped 100 ms."""
        return self.block_loudness(
            audio, MOMENTARY_WINDOW_S, MOMENTARY_STEP_S, channels_last=channels_last
        )

    def short_term(
        self, audio: np.ndarray, channels_last: bool | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """``(times, lufs)`` on the 3 s window, stepped 100 ms.

        EBU Tech 3341 wants a short-term display refreshed at least ten times a
        second; the once-a-second grid Tech 3342 defines for the loudness range
        is a different measurement and lives in :meth:`loudness_range`.
        """
        return self.block_loudness(
            audio, SHORT_TERM_WINDOW_S, SHORT_TERM_STEP_S, channels_last=channels_last
        )

    def integrated(self, audio: np.ndarray, channels_last: bool | None = None) -> float:
        """Gated integrated loudness in LUFS, or ``-inf`` for silence."""
        power, _ = self._block_power(
            audio, MOMENTARY_WINDOW_S, MOMENTARY_STEP_S, channels_last
        )
        return self._gated_loudness(power)[0]

    def _gated_loudness(self, power: np.ndarray) -> tuple[float, int, float]:
        """Two-stage gate over block powers.

        Returns ``(lufs, blocks_counted, relative_threshold_lufs)``.
        """
        if power.size == 0:
            return (-math.inf, 0, -math.inf)

        absolute = _power_to_lufs(power) > ABSOLUTE_GATE_LUFS
        if not np.any(absolute):
            return (-math.inf, 0, -math.inf)

        # The relative threshold is derived from the mean of the blocks that
        # passed the absolute gate — mean *power*, not mean dB.
        threshold = float(_power_to_lufs(np.mean(power[absolute])) + RELATIVE_GATE_LU)
        keep = absolute & (_power_to_lufs(power) > threshold)
        if not np.any(keep):
            return (-math.inf, 0, threshold)
        return (
            float(_power_to_lufs(np.mean(power[keep]))),
            int(np.count_nonzero(keep)),
            threshold,
        )

    def loudness_range(self, audio: np.ndarray, channels_last: bool | None = None) -> float:
        """EBU Tech 3342 loudness range in LU: how much the level moves about."""
        power, _ = self._block_power(audio, SHORT_TERM_WINDOW_S, LRA_STEP_S, channels_last)
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

    # -- peaks -------------------------------------------------------------

    @property
    def oversample(self) -> int:
        """True-peak interpolation factor for this meter's sample rate."""
        return true_peak_oversample(self.sample_rate)

    def true_peak(self, audio: np.ndarray, channels_last: bool | None = None) -> float:
        """Highest inter-sample peak in dBTP, per BS.1770-4 Annex 2.

        Examples
        --------
        A 12 kHz tone at 48 kHz is sampled four times per cycle; land those
        samples half way between the peaks and every one of them reads 3 dB
        low, while the waveform they describe still reaches -6 dBFS:

        >>> import numpy as np
        >>> sr = 48_000
        >>> tone = 0.5 * np.sin(2 * np.pi * 12_000 * np.arange(sr) / sr + np.pi / 4)
        >>> round(float(20 * np.log10(np.max(np.abs(tone)))), 2)
        -9.03
        >>> round(LoudnessMeter(sr).true_peak(tone), 1)
        -5.9
        """
        planar, _ = as_planar(audio, channels_last=channels_last, dtype=np.float64)
        if planar.size == 0:
            return -math.inf
        return _peak_to_db(true_peak_level(planar, self.oversample))

    def true_peak_per_channel(
        self, audio: np.ndarray, channels_last: bool | None = None
    ) -> tuple[float, ...]:
        """Per-channel true peak in dBTP, in the buffer's channel order."""
        planar, _ = as_planar(audio, channels_last=channels_last, dtype=np.float64)
        oversample = self.oversample
        return tuple(_peak_to_db(true_peak_level(channel, oversample)) for channel in planar)

    # -- the whole report --------------------------------------------------

    def analyze(self, audio: np.ndarray, channels_last: bool | None = None) -> LoudnessReport:
        """Full report: integrated, momentary/short-term maxima, LRA and peaks."""
        planar, _ = as_planar(audio, channels_last=channels_last, dtype=np.float64)
        momentary_power, _ = self._block_power(
            planar, MOMENTARY_WINDOW_S, MOMENTARY_STEP_S, channels_last=False
        )
        short_power, _ = self._block_power(
            planar, SHORT_TERM_WINDOW_S, SHORT_TERM_STEP_S, channels_last=False
        )
        lra_power, _ = self._block_power(
            planar, SHORT_TERM_WINDOW_S, LRA_STEP_S, channels_last=False
        )
        integrated, gated_blocks, threshold = self._gated_loudness(momentary_power)

        sample_peak = float(np.max(np.abs(planar))) if planar.size else 0.0
        per_channel = self.true_peak_per_channel(planar, channels_last=False)
        return LoudnessReport(
            integrated_lufs=integrated,
            momentary_max_lufs=_max_lufs(momentary_power),
            short_term_max_lufs=_max_lufs(short_power),
            loudness_range_lu=self._range_from_power(lra_power),
            true_peak_dbtp=max(per_channel) if per_channel else -math.inf,
            sample_peak_dbfs=_peak_to_db(sample_peak),
            duration_s=planar.shape[1] / self.sample_rate,
            gated_blocks=gated_blocks,
            threshold_lufs=threshold,
            true_peak_per_channel_dbtp=per_channel,
            sample_rate=self.sample_rate,
        )


class StreamingLoudnessMeter:
    """Live BS.1770 metering of a stream arriving in arbitrary-sized blocks.

    The filter memory and the 100 ms energy grid carry across calls, so pushing
    a signal in blocks reports what :class:`LoudnessMeter` reports for the
    whole thing — the numbers on the meter during playback are the numbers the
    file will be delivered with, which is the only reason to have a live meter
    at all.

    Only the energy of each finished 100 ms sub-block is kept, so an hour of
    metering costs 36 000 floats rather than an hour of audio.

    Examples
    --------
    >>> import numpy as np
    >>> sr = 48_000
    >>> tone = 10 ** (-23 / 20) * np.sin(2 * np.pi * 1000 * np.arange(sr * 4) / sr)
    >>> meter = StreamingLoudnessMeter(sr, n_channels=2)
    >>> for start in range(0, tone.size, 1024):          # device-sized blocks
    ...     meter.push(np.stack([tone, tone])[:, start : start + 1024])
    >>> round(meter.integrated_lufs, 1)
    -23.0
    >>> round(meter.momentary_lufs, 1)
    -23.0
    """

    def __init__(
        self,
        sample_rate: float,
        n_channels: int = 2,
        weights: tuple[float, ...] | None = None,
        measure_true_peak: bool = True,
    ) -> None:
        self.meter = LoudnessMeter(sample_rate, weights)
        self.sample_rate = self.meter.sample_rate
        self.n_channels = int(n_channels)
        self.measure_true_peak = bool(measure_true_peak)
        self._step = max(1, int(round(MOMENTARY_STEP_S * self.sample_rate)))
        self._momentary_blocks = int(round(MOMENTARY_WINDOW_S / MOMENTARY_STEP_S))
        self._short_term_blocks = int(round(SHORT_TERM_WINDOW_S / MOMENTARY_STEP_S))
        self.reset()

    # -- state -------------------------------------------------------------

    def reset(self) -> None:
        """Forget everything measured so far, keeping the configuration."""
        sos = self.meter.sos
        # sosfilt_zi gives the steady state for unit input; scaled by zero it is
        # the at-rest state, which is what a meter starting from silence has.
        self._zi = np.repeat(
            (sosfilt_zi(sos) * 0.0)[:, np.newaxis, :], self.n_channels, axis=1
        )
        self._weights = self.meter.weights_for(self.n_channels)
        self._energies: list[float] = []
        self._pending = 0.0
        self._pending_samples = 0
        self._sample_peak = 0.0
        self._true_peak = 0.0
        self._peak_tail = np.zeros((self.n_channels, 0), dtype=np.float64)
        self._tail_start = 0
        self._measured_to = 0
        self._n_samples = 0

    def push(self, block: np.ndarray, channels_last: bool | None = None) -> None:
        """Feed one block of audio. Any length, including zero."""
        planar, _ = as_planar(block, channels_last=channels_last, dtype=np.float64)
        if planar.shape[0] != self.n_channels:
            raise ValueError(
                f"meter was configured for {self.n_channels} channels, got {planar.shape[0]}"
            )
        if planar.shape[1] == 0:
            return

        self._n_samples += planar.shape[1]
        self._update_peaks(planar)

        filtered, self._zi = sosfilt(self.meter.sos, planar, axis=-1, zi=self._zi)
        energy = self._weights @ np.square(filtered)
        self._accumulate(energy)

    def _accumulate(self, energy: np.ndarray) -> None:
        """Split the block's per-sample energy along the 100 ms grid."""
        offset = 0
        if self._pending_samples:
            take = min(self._step - self._pending_samples, energy.size)
            self._pending += float(np.sum(energy[:take]))
            self._pending_samples += take
            offset = take
            if self._pending_samples == self._step:
                self._energies.append(self._pending / self._step)
                self._pending, self._pending_samples = 0.0, 0

        remaining = energy.size - offset
        whole = remaining // self._step
        if whole:
            stop = offset + whole * self._step
            sums = energy[offset:stop].reshape(whole, self._step).sum(axis=1)
            self._energies.extend((sums / self._step).tolist())
            offset = stop

        if offset < energy.size:
            self._pending += float(np.sum(energy[offset:]))
            self._pending_samples += energy.size - offset

    def _update_peaks(self, planar: np.ndarray) -> None:
        self._sample_peak = max(self._sample_peak, float(np.max(np.abs(planar))))
        if not self.measure_true_peak:
            return
        # The interpolation kernel reaches TRUE_PEAK_KERNEL_HALF samples either
        # side. The tail of the previous block is prepended so that the samples
        # at the start of this one have their left context, and the last few
        # samples of this one are left for the next push, because the audio that
        # would give them their right context has not arrived: measuring them
        # now would read a block boundary as the end of the signal and ring.
        context = (
            planar
            if self._peak_tail.shape[1] == 0
            else np.concatenate([self._peak_tail, planar], axis=1)
        )
        base, length = self._tail_start, context.shape[1]
        measurable = max(base, base + length - TRUE_PEAK_KERNEL_HALF)
        if measurable > self._measured_to:
            self._true_peak = max(
                self._true_peak,
                true_peak_level(
                    context,
                    self.meter.oversample,
                    start=self._measured_to - base,
                    stop=measurable - base,
                ),
            )
            self._measured_to = measurable
        keep = min(length, 2 * TRUE_PEAK_KERNEL_HALF)
        self._peak_tail = np.ascontiguousarray(context[:, length - keep :])
        self._tail_start = base + length - keep

    # -- readings ----------------------------------------------------------

    @property
    def duration_s(self) -> float:
        return self._n_samples / self.sample_rate

    def _window_power(self, n_blocks: int) -> float:
        if len(self._energies) < n_blocks:
            return 0.0
        return float(np.mean(self._energies[-n_blocks:]))

    def _gating_powers(self) -> np.ndarray:
        """Mean square of every 400 ms gating block, on the 100 ms grid."""
        energies = np.asarray(self._energies, dtype=np.float64)
        span = self._momentary_blocks
        if energies.size < span:
            return np.zeros(0)
        cumulative = np.concatenate(([0.0], np.cumsum(energies)))
        return (cumulative[span:] - cumulative[:-span]) / span

    @property
    def momentary_lufs(self) -> float:
        """Loudness of the last 400 ms, or ``-inf`` before that much has arrived."""
        return float(_power_to_lufs(self._window_power(self._momentary_blocks)))

    @property
    def short_term_lufs(self) -> float:
        """Loudness of the last 3 s, or ``-inf`` before that much has arrived."""
        return float(_power_to_lufs(self._window_power(self._short_term_blocks)))

    @property
    def integrated_lufs(self) -> float:
        """Gated loudness of everything pushed so far."""
        return self.meter._gated_loudness(self._gating_powers())[0]  # noqa: SLF001

    @property
    def loudness_range_lu(self) -> float:
        """EBU Tech 3342 range of everything pushed so far."""
        energies = np.asarray(self._energies, dtype=np.float64)
        span = self._short_term_blocks
        step = max(1, int(round(LRA_STEP_S / MOMENTARY_STEP_S)))
        if energies.size < span:
            return 0.0
        cumulative = np.concatenate(([0.0], np.cumsum(energies)))
        starts = np.arange(0, energies.size - span + 1, step)
        power = (cumulative[starts + span] - cumulative[starts]) / span
        return self.meter._range_from_power(power)  # noqa: SLF001

    @property
    def true_peak_dbtp(self) -> float:
        """Highest inter-sample peak so far, including the samples still held.

        The last few samples of the stream have no audio after them to give the
        interpolator its right-hand context, so they are measured here — where
        the stream is treated as having ended — rather than in :meth:`push`,
        which cannot know whether more is coming.
        """
        return _peak_to_db(max(self._true_peak, self._pending_peak()))

    def _pending_peak(self) -> float:
        if not self.measure_true_peak or self._peak_tail.shape[1] == 0:
            return 0.0
        return true_peak_level(
            self._peak_tail,
            self.meter.oversample,
            start=self._measured_to - self._tail_start,
        )

    @property
    def sample_peak_dbfs(self) -> float:
        return _peak_to_db(self._sample_peak)

    def report(self) -> LoudnessReport:
        """Snapshot of the stream so far, in the same shape as an offline report."""
        gating = self._gating_powers()
        integrated, gated_blocks, threshold = self.meter._gated_loudness(gating)  # noqa: SLF001
        return LoudnessReport(
            integrated_lufs=integrated,
            momentary_max_lufs=_max_lufs(gating),
            short_term_max_lufs=_max_lufs(self._short_term_powers()),
            loudness_range_lu=self.loudness_range_lu,
            true_peak_dbtp=self.true_peak_dbtp,
            sample_peak_dbfs=self.sample_peak_dbfs,
            duration_s=self.duration_s,
            gated_blocks=gated_blocks,
            threshold_lufs=threshold,
            true_peak_per_channel_dbtp=(),
            sample_rate=self.sample_rate,
        )

    def _short_term_powers(self) -> np.ndarray:
        energies = np.asarray(self._energies, dtype=np.float64)
        span = self._short_term_blocks
        if energies.size < span:
            return np.zeros(0)
        cumulative = np.concatenate(([0.0], np.cumsum(energies)))
        return (cumulative[span:] - cumulative[:-span]) / span


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


def _peak_to_db(peak: float) -> float:
    """Linear peak -> dB, with digital silence reading ``-inf`` rather than -400."""
    return float(linear_to_db(peak)) if peak > 0.0 else -math.inf


def _max_lufs(power: np.ndarray) -> float:
    if power.size == 0:
        return -math.inf
    return float(_power_to_lufs(np.max(power)))
