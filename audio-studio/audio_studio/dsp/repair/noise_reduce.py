"""Broadband noise reduction: spectral subtraction sharpened into a Wiener filter.

Tape hiss, preamp noise and air conditioning are *stationary*: their spectrum
during the second before the take is the same spectrum that sits underneath it.
That is the only thing a denoiser has to work with, and it is why everything
here hangs off a **noise profile** — a per-bin power spectrum measured over
material the user declares to be noise alone, either a selection
(:func:`learn_noise_profile`) or the first few hundred milliseconds of the
recording, which :class:`NoiseReduceEffect` learns for itself.

With a profile in hand the audio is taken apart with an STFT and each bin is
scaled by a gain that depends on how far it stands above the noise:

1. **Subtract.** The posterior SNR ``|Y|^2 / lambda`` says how much louder the
   bin is than the profile says the noise should be. Subtracting one gives the
   classical spectral-subtraction estimate of the signal that must be in there.
2. **Decide.** Used directly, that estimate produces *musical noise*: bins
   whose residual randomly clears the threshold in one frame and not the next,
   which the ear hears as a shower of little tones — far more objectionable
   than the hiss it replaced. So the subtraction is treated as the
   *instantaneous* reading of a quantity that is actually slow-moving, and is
   averaged against what the previous frame concluded. That is the
   decision-directed a-priori SNR estimator of Ephraim and Malah, and the
   smoothing is what keeps the residual sounding like noise rather than like
   an algorithm.
3. **Attenuate.** The Wiener gain ``xi / (1 + xi)`` is the scaling that
   minimises the mean-square error given that SNR, and it is floored at
   :attr:`NoiseReduceEffect.reduction_db` rather than allowed to reach zero.
   Removing a noise floor completely is the other way to make a recording
   sound processed: what is left between the words has to be quiet noise, not
   digital silence.

``over_subtraction`` scales the profile before any of that happens. A profile
is a *mean*, so half the noise frames are louder than it; over-subtracting by
a couple of dB trades a little dulling for a residual that does not flutter.

Latency
-------
Analysis needs a whole window before it can emit anything, so the effect
delays the signal by :meth:`NoiseReduceEffect.latency_samples` — exactly the
way :class:`~audio_studio.dsp.effects.dynamics.LimiterEffect` delays it by its
lookahead. Offline and streaming therefore run the *same* code: rendering a
buffer resets the state and submits one large block, and its output is the
concatenation of any block-by-block run of the same audio.
:func:`reduce_noise` is the offline convenience that flushes the tail and
shifts the delay back out, so a rendered file lines up with the original
sample for sample.

Examples
--------
>>> import numpy as np
>>> sr = 48_000
>>> rng = np.random.default_rng(3)
>>> hiss = 0.02 * rng.standard_normal(2 * sr)
>>> tone = 0.2 * np.sin(2 * np.pi * 700.0 * np.arange(2 * sr) / sr)
>>> tone[: sr // 2] = 0.0                      # half a second of noise to learn from
>>> cleaned, profile = reduce_noise(hiss + tone, sr, noise_ms=400.0)
>>> round(profile.level_db, 0)                 # -34 dBFS of hiss, as generated
-34.0
>>> def rms(x):
...     return float(np.sqrt(np.mean(np.square(x))))
>>> pause = slice(sr // 8, sr // 4)            # well inside the noise-only lead-in
>>> rms(cleaned[pause]) < rms((hiss + tone)[pause]) / 10.0    # hiss gone
True
>>> round(rms(cleaned[sr:]) / rms(tone[sr:]), 2)              # tone kept
1.0
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np
from scipy.fft import irfft, rfft
from scipy.ndimage import uniform_filter1d

from ..effects.base import Effect
from ..util import as_planar, restore_layout
from ..windows import WindowType, window_info

__all__ = [
    "DEFAULT_FFT_SIZE",
    "DEFAULT_NOISE_MS",
    "DEFAULT_OVER_SUBTRACTION",
    "DEFAULT_REDUCTION_DB",
    "NoiseProfile",
    "NoiseReduceEffect",
    "learn_noise_profile",
    "reduce_noise",
]

#: Analysis length. At 48 kHz that is 23 ms and 23 Hz per bin — long enough to
#: separate a voice's harmonics from the hiss between them, short enough that a
#: consonant is not smeared across the whole window.
DEFAULT_FFT_SIZE = 2048

#: Frames per window. Hann at 75% overlap sums to a constant, so the
#: overlap-add resynthesis is exact wherever the gains are.
DEFAULT_OVERLAP = 4

#: How far a noise-only bin is pushed down, in dB. Two thirds of the way to
#: inaudible is the setting that still sounds like a recording; the rest of the
#: range exists for material where the noise is the only thing that matters.
DEFAULT_REDUCTION_DB = 24.0

#: Multiplier applied to the profile before subtraction; see the module notes.
DEFAULT_OVER_SUBTRACTION = 1.5

#: Head of the recording learned from when no profile is supplied.
DEFAULT_NOISE_MS = 300.0

#: Decision-directed smoothing. 0.98 is Ephraim and Malah's own figure and is
#: what separates this from plain spectral subtraction.
DEFAULT_SMOOTHING = 0.98

#: Width, in bins, of the box filter applied to a noise estimate. Each bin of
#: an averaged periodogram still scatters several dB about the truth, and a
#: noise floor is smooth, so neighbours are better evidence than none.
_PROFILE_SMOOTHING_BINS = 3

#: Power below which a bin is treated as silence rather than divided by.
_POWER_FLOOR = 1e-24


def _smooth_across_bins(power: np.ndarray) -> np.ndarray:
    """Box-filter a spectrum along its bin axis, holding the edges."""
    if _PROFILE_SMOOTHING_BINS <= 1 or power.shape[-1] < _PROFILE_SMOOTHING_BINS:
        return power
    return uniform_filter1d(power, _PROFILE_SMOOTHING_BINS, axis=-1, mode="nearest")


@dataclass(frozen=True)
class NoiseProfile:
    """Per-bin noise power measured over material believed to be noise alone.

    ``power`` is ``(n_channels, n_bins)`` and is normalised by the window's
    energy, so a bin reads the *variance* the noise contributes there: white
    noise of RMS ``sigma`` gives ``sigma**2`` in every bin, whatever transform
    length measured it. That is what makes a profile portable between analyses
    — and what lets :meth:`level_db` state a plain dBFS noise floor.

    Examples
    --------
    >>> import numpy as np
    >>> sr = 48_000
    >>> hiss = 0.01 * np.random.default_rng(0).standard_normal(sr)
    >>> profile = learn_noise_profile(hiss, sr)
    >>> profile.frames > 40 and profile.n_channels == 1
    True
    >>> round(profile.level_db)                     # 0.01 RMS is -40 dBFS
    -40
    """

    power: np.ndarray
    sample_rate: float
    fft_size: int
    hop_size: int
    frames: int

    @property
    def n_channels(self) -> int:
        return int(self.power.shape[0])

    @property
    def n_bins(self) -> int:
        return int(self.power.shape[1])

    @property
    def duration_s(self) -> float:
        """Length of the material the profile was measured over, in seconds."""
        if self.frames <= 0:
            return 0.0
        return ((self.frames - 1) * self.hop_size + self.fft_size) / self.sample_rate

    def frequencies(self) -> np.ndarray:
        """Centre frequency of every bin, in hertz."""
        return np.fft.rfftfreq(self.fft_size, 1.0 / self.sample_rate)

    def total_power(self) -> np.ndarray:
        """Broadband noise power of each channel, as a plain time-domain variance.

        One-sided bins fold the negative frequencies onto their positive twins,
        so every bin but DC and Nyquist counts twice.
        """
        weights = np.full(self.n_bins, 2.0)
        weights[0] = 1.0
        if self.fft_size % 2 == 0:
            weights[-1] = 1.0
        return self.power @ weights / float(self.fft_size)

    @property
    def level_db(self) -> float:
        """Broadband noise floor in dBFS, averaged across channels."""
        total = float(np.mean(self.total_power()))
        return float(10.0 * np.log10(max(total, _POWER_FLOOR)))

    def to_db(self, channel: int | None = None) -> np.ndarray:
        """Per-bin noise level in dB, for drawing the profile over a spectrum."""
        power = np.mean(self.power, axis=0) if channel is None else self.power[channel]
        return 10.0 * np.log10(np.maximum(power, _POWER_FLOOR))

    def power_for(self, n_channels: int, n_bins: int, sample_rate: float) -> np.ndarray:
        """The profile as an ``(n_channels, n_bins)`` array for another analysis.

        A profile learned at one transform length or sample rate is still a
        measurement of the same noise, so it is interpolated onto the requested
        bin grid rather than refused. Channel counts that do not match collapse
        to the mean: one channel's hiss is a far better estimate of another's
        than no estimate at all.
        """
        power = self.power
        if n_bins != self.n_bins or abs(sample_rate - self.sample_rate) > 1e-6:
            target = np.fft.rfftfreq(2 * (n_bins - 1), 1.0 / sample_rate)
            source = self.frequencies()
            power = np.stack([np.interp(target, source, row) for row in power])
        if power.shape[0] != n_channels:
            power = np.repeat(np.mean(power, axis=0, keepdims=True), n_channels, axis=0)
        return power

    def __str__(self) -> str:
        return (
            f"{self.level_db:.1f} dBFS noise floor, learned from "
            f"{self.duration_s * 1000.0:.0f} ms ({self.frames} frames)"
        )


def learn_noise_profile(
    audio: np.ndarray,
    sample_rate: float,
    start_s: float = 0.0,
    duration_s: float | None = None,
    fft_size: int = DEFAULT_FFT_SIZE,
    hop_size: int | None = None,
    channels_last: bool | None = None,
) -> NoiseProfile:
    """Measure the noise spectrum of one span of a recording.

    ``start_s`` and ``duration_s`` are the selection an operator drags across a
    pause; the default is the whole buffer, which is what a dedicated noise
    file wants. The span must hold at least one full analysis window, since a
    spectrum shorter than its own transform is not a measurement of anything.

    Examples
    --------
    >>> import numpy as np
    >>> sr = 48_000
    >>> rng = np.random.default_rng(1)
    >>> take = np.concatenate([0.01 * rng.standard_normal(sr), 0.5 * np.ones(sr)])
    >>> profile = learn_noise_profile(take, sr, duration_s=0.9)
    >>> round(profile.level_db)
    -40
    """
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    planar, _ = as_planar(audio, channels_last=channels_last, dtype=np.float64)
    fft_size = int(fft_size)
    hop = _hop_for(fft_size, hop_size)

    start = max(0, int(round(start_s * sample_rate)))
    stop = planar.shape[1] if duration_s is None else start + int(round(duration_s * sample_rate))
    segment = planar[:, start : min(stop, planar.shape[1])]
    if segment.shape[1] < fft_size:
        raise ValueError(
            f"a noise profile needs at least {fft_size} samples "
            f"({fft_size / sample_rate * 1000.0:.0f} ms), got {segment.shape[1]}"
        )

    info = window_info(WindowType.HANN, fft_size)
    frames = np.lib.stride_tricks.sliding_window_view(segment, fft_size, axis=-1)[:, ::hop, :]
    spectra = rfft(frames * info.samples, axis=-1)
    power = np.mean(np.square(np.abs(spectra)), axis=1) / info.s2
    return NoiseProfile(
        power=_smooth_across_bins(power),
        sample_rate=float(sample_rate),
        fft_size=fft_size,
        hop_size=hop,
        frames=int(frames.shape[1]),
    )


def _hop_for(fft_size: int, hop_size: int | None) -> int:
    """Validate the transform geometry and return the hop to use.

    The hop has to divide the window: the overlap-add denominator is then the
    same for every frame, which is what lets a streaming resynthesis normalise
    without accumulating a running sum it would have to wait to complete.
    """
    if fft_size < 4:
        raise ValueError("fft_size must be at least 4")
    hop = int(hop_size) if hop_size else max(1, fft_size // DEFAULT_OVERLAP)
    if hop < 1 or fft_size % hop != 0:
        raise ValueError(f"hop_size ({hop}) must be a positive divisor of fft_size ({fft_size})")
    return hop


class NoiseReduceEffect(Effect):
    """Spectral noise reduction as a rack effect.

    Parameters
    ----------
    reduction_db:
        How far a bin holding nothing but noise is attenuated. ``0`` is a
        bypass; the default of 24 dB removes the hiss while leaving a floor
        under it.
    over_subtraction:
        Multiplier applied to the learned profile before it is subtracted.
        Above ``1`` the residual is steadier and the signal a little duller.
    profile:
        A profile measured elsewhere — from a selection, or from a separate
        recording of the room. ``None`` learns from the head of the material.
    noise_ms:
        How much of the head to learn from when no ``profile`` is given. The
        estimate is refined frame by frame across that span rather than waited
        for, so the effect starts reducing immediately and streams.
    fft_size / hop_size:
        Analysis geometry. ``hop_size`` must divide ``fft_size``.
    smoothing:
        Decision-directed weight given to the previous frame's conclusion.

    Examples
    --------
    >>> import numpy as np
    >>> sr = 48_000
    >>> hiss = 0.02 * np.random.default_rng(5).standard_normal(sr)
    >>> effect = NoiseReduceEffect(noise_ms=200.0)
    >>> quieter = effect.process(hiss, sr)
    >>> float(np.sqrt(np.mean(quieter[sr // 2 :] ** 2))) < 0.002
    True
    >>> effect.latency_samples()
    2048
    >>> print(effect.profile)
    -33.9 dBFS noise floor, learned from 224 ms (18 frames)
    """

    name = "Noise Reduction"

    def __init__(
        self,
        reduction_db: float = DEFAULT_REDUCTION_DB,
        over_subtraction: float = DEFAULT_OVER_SUBTRACTION,
        profile: NoiseProfile | None = None,
        noise_ms: float = DEFAULT_NOISE_MS,
        fft_size: int = DEFAULT_FFT_SIZE,
        hop_size: int | None = None,
        smoothing: float = DEFAULT_SMOOTHING,
        enabled: bool = True,
        mix: float = 1.0,
    ) -> None:
        super().__init__(enabled=enabled, mix=mix)
        self.reduction_db = float(reduction_db)
        self.over_subtraction = float(over_subtraction)
        self.noise_ms = float(noise_ms)
        self.smoothing = float(smoothing)
        self._fft_size = int(fft_size)
        self._hop_size = _hop_for(self._fft_size, hop_size)
        self._given_profile = profile

        self._channels = 0
        self._pending = np.zeros((0, 0))
        self._overlap = np.zeros((0, 0))
        self._output = np.zeros((0, 0))
        self._discard = 0
        self._frame_index = 0
        self._noise_sum: np.ndarray | None = None
        self._noise_frames = 0
        self._noise_estimate: np.ndarray | None = None
        self._previous_clean: np.ndarray | None = None
        self._validate()

    # -- geometry ----------------------------------------------------------

    @property
    def fft_size(self) -> int:
        """Analysis window length in samples; also the effect's latency."""
        return self._fft_size

    @fft_size.setter
    def fft_size(self, value: int) -> None:
        self._hop_size = _hop_for(int(value), None)
        self._fft_size = int(value)
        self._channels = 0  # force a rebuild on the next block

    @property
    def hop_size(self) -> int:
        return self._hop_size

    @hop_size.setter
    def hop_size(self, value: int) -> None:
        self._hop_size = _hop_for(self._fft_size, int(value))
        self._channels = 0

    def latency_samples(self) -> int:
        """Delay, in samples, between a sample going in and coming back out.

        One analysis window. A frame cannot be resynthesised before it has been
        filled, and a block boundary may fall anywhere inside a hop, so the
        window is both the requirement and the bound.
        """
        return self._fft_size

    # -- noise profile -----------------------------------------------------

    @property
    def profile(self) -> NoiseProfile | None:
        """The profile in force: the one supplied, or the one learned so far."""
        if self._given_profile is not None:
            return self._given_profile
        if self._noise_sum is None or self._noise_frames == 0:
            return None
        return NoiseProfile(
            power=_smooth_across_bins(self._noise_sum / self._noise_frames),
            sample_rate=float(self._prepared_sample_rate or 0.0),
            fft_size=self._fft_size,
            hop_size=self._hop_size,
            frames=self._noise_frames,
        )

    @profile.setter
    def profile(self, value: NoiseProfile | None) -> None:
        self._given_profile = value
        self._noise_sum = None
        self._noise_frames = 0
        self._noise_estimate = None

    def learn_from(
        self,
        audio: np.ndarray,
        sample_rate: float,
        start_s: float = 0.0,
        duration_s: float | None = None,
        channels_last: bool | None = None,
    ) -> NoiseProfile:
        """Measure a profile from a selection and adopt it.

        This is what a *Capture Noise Print* command calls: the operator drags
        a range over a pause, and everything afterwards is reduced against it
        rather than against the head of the file.
        """
        profile = learn_noise_profile(
            audio,
            sample_rate,
            start_s=start_s,
            duration_s=duration_s,
            fft_size=self._fft_size,
            hop_size=self._hop_size,
            channels_last=channels_last,
        )
        self.profile = profile
        return profile

    # -- Effect ------------------------------------------------------------

    def _validate(self) -> None:
        if not np.isfinite([self.reduction_db, self.over_subtraction, self.smoothing]).all():
            raise ValueError("noise reduction parameters must be finite")
        if self.reduction_db < 0.0:
            raise ValueError("reduction_db must not be negative")
        if self.over_subtraction <= 0.0:
            raise ValueError("over_subtraction must be positive")
        if not 0.0 <= self.smoothing < 1.0:
            raise ValueError("smoothing must be in [0, 1)")
        if self.noise_ms < 0.0:
            raise ValueError("noise_ms must not be negative")

    def parameters(self) -> dict[str, Any]:
        return {
            **super().parameters(),
            "reduction_db": self.reduction_db,
            "over_subtraction": self.over_subtraction,
            "noise_ms": self.noise_ms,
            "fft_size": self._fft_size,
            "hop_size": self._hop_size,
            "smoothing": self.smoothing,
        }

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        self._validate()
        super().prepare(sample_rate, n_channels)
        self._allocate(n_channels)

    def reset(self) -> None:
        """Drop the stream state, and any profile the effect learned itself.

        A profile learned from the head of one buffer says nothing about the
        next one, so it goes the same way as the overlap-add tail. One passed
        in from a selection is a parameter and stays.
        """
        self._allocate(self._channels)

    def _allocate(self, n_channels: int) -> None:
        channels = max(0, int(n_channels))
        window = self._fft_size
        self._channels = channels
        # The pre-roll pads the stream so that the first *real* sample is
        # covered by a full set of overlapping frames and needs no special
        # normalisation; the discard throws the padding's own output away.
        self._discard = window - self._hop_size
        self._pending = np.zeros((channels, self._discard))
        self._overlap = np.zeros((channels, window))
        self._output = np.zeros((channels, window))
        self._frame_index = 0
        self._noise_sum = None
        self._noise_frames = 0
        self._noise_estimate = None
        self._previous_clean = None

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        self._validate()
        n_channels, n_samples = audio.shape
        if n_channels != self._channels:
            self._allocate(n_channels)
        if n_samples == 0:
            return audio

        self._pending = np.concatenate(
            [self._pending, audio.astype(np.float64, copy=False)], axis=1
        )
        # Frames are collected and joined once: appending each hop to the
        # output as it appears would copy the whole buffer per frame, which
        # turns rendering a long file into quadratic work.
        emitted = [self._output]
        while self._pending.shape[1] >= self._fft_size:
            emitted.append(self._advance(sample_rate))
        ready = np.concatenate(emitted, axis=1) if len(emitted) > 1 else self._output

        self._output = ready[:, n_samples:]
        return ready[:, :n_samples].astype(audio.dtype, copy=False)

    # -- internals ---------------------------------------------------------

    def _advance(self, sample_rate: float) -> np.ndarray:
        """Analyse one frame, attenuate it, overlap-add it and emit one hop."""
        window = self._fft_size
        hop = self._hop_size
        info = window_info(WindowType.HANN, window)

        spectrum = rfft(self._pending[:, :window] * info.samples, axis=-1)
        power = np.square(np.abs(spectrum)) / info.s2
        self._observe_noise(power, sample_rate)

        noise = self._noise_power(power.shape, sample_rate)
        if noise is not None:
            spectrum = spectrum * self._gain(power, noise)
        frame = irfft(spectrum, n=window, axis=-1) * info.samples

        self._overlap += frame
        emitted = self._overlap[:, :hop] / _overlap_denominator(window, hop)
        self._overlap[:, : window - hop] = self._overlap[:, hop:]
        self._overlap[:, window - hop :] = 0.0
        self._pending = self._pending[:, hop:]
        self._frame_index += 1

        if self._discard > 0:
            taken = min(self._discard, emitted.shape[1])
            self._discard -= taken
            emitted = emitted[:, taken:]
        return emitted

    def _observe_noise(self, power: np.ndarray, sample_rate: float) -> None:
        """Fold one frame into the learned profile, if it is still learning."""
        if self._given_profile is not None or self.noise_ms <= 0.0:
            return
        # Frames that straddle the pre-roll are part silence and would drag the
        # estimate down, so learning starts at the first fully populated one.
        warmup = (self._fft_size - self._hop_size) // self._hop_size
        if self._frame_index < warmup:
            return
        wanted = max(1, int(self.noise_ms * sample_rate / 1000.0) // self._hop_size)
        if self._noise_frames >= wanted:
            return
        if self._noise_sum is None:
            self._noise_sum = np.zeros_like(power)
        self._noise_sum += power
        self._noise_frames += 1
        self._noise_estimate = _smooth_across_bins(self._noise_sum / self._noise_frames)

    def _noise_power(self, shape: tuple[int, ...], sample_rate: float) -> np.ndarray | None:
        """Per-bin noise power to subtract, or ``None`` while nothing is known."""
        if self._given_profile is None:
            return self._noise_estimate
        if self._noise_estimate is None or self._noise_estimate.shape != shape:
            self._noise_estimate = self._given_profile.power_for(shape[0], shape[1], sample_rate)
        return self._noise_estimate

    def _gain(self, power: np.ndarray, noise: np.ndarray) -> np.ndarray:
        """Decision-directed Wiener gain for one frame."""
        noise = np.maximum(noise * self.over_subtraction, _POWER_FLOOR)
        instant = np.maximum(power / noise - 1.0, 0.0)
        if self._previous_clean is None or self._previous_clean.shape != power.shape:
            snr = instant
        else:
            snr = self.smoothing * (self._previous_clean / noise)
            snr += (1.0 - self.smoothing) * instant
        gain = snr / (1.0 + snr)
        np.maximum(gain, 10.0 ** (-self.reduction_db / 20.0), out=gain)
        self._previous_clean = power * np.square(gain)
        return gain


@lru_cache(maxsize=8)
def _overlap_denominator(window: int, hop: int) -> np.ndarray:
    """Steady-state sum of the squared window across the frames covering a hop.

    Analysis and synthesis both apply the window, so a resynthesised sample is
    the sum of ``window / hop`` shifted copies of ``w**2`` times the signal.
    Because the hop divides the window that sum repeats every hop, which is why
    it can be computed once here instead of accumulated per frame — and why a
    streaming resynthesis can normalise a sample the moment its last frame
    lands rather than waiting to see whether more are coming.
    """
    squared = np.square(window_info(WindowType.HANN, window).samples)
    return np.maximum(squared.reshape(-1, hop).sum(axis=0), 1e-12)


def reduce_noise(
    audio: np.ndarray,
    sample_rate: float,
    profile: NoiseProfile | None = None,
    reduction_db: float = DEFAULT_REDUCTION_DB,
    over_subtraction: float = DEFAULT_OVER_SUBTRACTION,
    noise_ms: float = DEFAULT_NOISE_MS,
    fft_size: int = DEFAULT_FFT_SIZE,
    hop_size: int | None = None,
    smoothing: float = DEFAULT_SMOOTHING,
    channels_last: bool | None = None,
) -> tuple[np.ndarray, NoiseProfile | None]:
    """Denoise a whole buffer, returning ``(audio, profile)``.

    The stream is flushed with a window of silence and the effect's latency is
    shifted back out, so the result is the same length as the input and lines
    up with it sample for sample — which the effect on its own cannot do,
    because in a live rack those samples have not been played yet.

    The input is never modified and the result keeps the caller's layout.
    """
    effect = NoiseReduceEffect(
        reduction_db=reduction_db,
        over_subtraction=over_subtraction,
        profile=profile,
        noise_ms=noise_ms,
        fft_size=fft_size,
        hop_size=hop_size,
        smoothing=smoothing,
    )
    arr = np.asarray(audio)
    planar, was_mono = as_planar(arr, channels_last=channels_last, dtype=np.float64)
    latency = effect.latency_samples()
    flushed = np.concatenate([planar, np.zeros((planar.shape[0], latency))], axis=1)

    processed = effect.process(flushed, sample_rate, channels_last=False)
    dtype = arr.dtype if arr.dtype in (np.float32, np.float64) else np.float32
    result = restore_layout(processed[:, latency:].astype(dtype, copy=False), was_mono)
    if channels_last and not was_mono:
        result = np.ascontiguousarray(result.T)
    return result, effect.profile
