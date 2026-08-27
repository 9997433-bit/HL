"""Mains hum removal: a comb of notches on 50 or 60 Hz and its harmonics.

Hum is not one tone. A ground loop or an unshielded cable picks up the mains
fundamental *and* a stack of harmonics — often with the odd ones dominant,
because the magnetic pickup is a differentiated square-ish wave rather than a
sine. Notching only 50 Hz leaves 100, 150 and 250 Hz buzzing away, which is why
this is a comb rather than a filter.

Each tooth is a second-order RBJ notch, so the filter is cheap and — because it
is built out of the same :class:`~audio_studio.dsp.effects.eq.EQBand` machinery
as the equaliser — it streams with the rest of the rack and can draw its own
response curve. Notches are minimum-phase: the magnitude a few Hz from a tooth
is untouched, but the phase rotates through it, so a de-hummed signal will not
null against the original even where its spectrum is identical.

Two knobs matter:

``q``
    How narrow each tooth is. A hum tone is a pure sinusoid, so the notch can
    be very narrow: the default Q of 30 is about 1.7 Hz wide at 50 Hz, narrow
    enough that a bass note a semitone away survives.
``depth_db``
    ``None`` for an infinitely deep null, or a finite cut when the music has
    content sitting on the hum frequency and a full null would be more audible
    than the hum.

:func:`detect_hum` picks between 50 and 60 Hz by measuring the material rather
than by asking which country it came from.

Examples
--------
>>> import numpy as np
>>> sr = 48_000
>>> t = np.arange(sr) / sr
>>> music = 0.3 * np.sin(2 * np.pi * 440.0 * t)
>>> hum = 0.05 * np.sin(2 * np.pi * 50.0 * t) + 0.02 * np.sin(2 * np.pi * 150.0 * t)
>>> cleaned = DeHumEffect(frequency=50.0).process(music + hum, sr)
>>> def level(signal, frequency):           # amplitude of one tone, by projection
...     phasor = np.exp(-2j * np.pi * frequency * np.arange(signal.size) / sr)
...     return float(2 * abs(np.vdot(phasor, signal)) / signal.size)
>>> settled = cleaned[sr // 2 :]            # past the notches' ring-down
>>> round(level(settled, 50.0), 3), round(level(settled, 440.0), 3)
(0.001, 0.294)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ..effects.eq import EQBand, FilterType, ParametricEQ
from ..util import as_planar

__all__ = ["DeHumEffect", "HumEstimate", "detect_hum"]

#: Mains frequencies worth testing for. Everywhere on earth is one or the other.
MAINS_FREQUENCIES = (50.0, 60.0)

#: Harmonics notched by default. Above the tenth the hum is normally buried.
DEFAULT_HARMONICS = 8

#: Default notch Q: ~1.7 Hz wide at 50 Hz.
DEFAULT_Q = 30.0

#: Highest fraction of Nyquist a tooth may sit at. A notch designed on top of
#: Nyquist is not a notch.
_MAX_FREQUENCY_RATIO = 0.95


@dataclass(frozen=True)
class HumEstimate:
    """Result of looking for mains hum in a buffer."""

    frequency: float
    strength_db: float
    harmonics_found: int

    @property
    def present(self) -> bool:
        """Whether the hum stands far enough above the surrounding spectrum.

        The threshold is 6 dB over the local noise floor, which is roughly
        where a steady tone stops being maskable by the programme around it.
        """
        return self.strength_db >= 6.0

    def __str__(self) -> str:
        if not self.present:
            return "no mains hum detected"
        return (
            f"{self.frequency:.0f} Hz hum, {self.strength_db:.1f} dB above the floor "
            f"across {self.harmonics_found} harmonics"
        )


def detect_hum(
    audio: np.ndarray,
    sample_rate: float,
    candidates: tuple[float, ...] = MAINS_FREQUENCIES,
    harmonics: int = 5,
    channels_last: bool | None = None,
) -> HumEstimate:
    """Decide whether a buffer hums, and at which mains frequency.

    Each candidate's harmonic stack is compared against the median level of the
    spectrum around it, so the answer does not depend on how loud the programme
    is — only on how far the hum stands out of it.

    Examples
    --------
    >>> import numpy as np
    >>> sr = 48_000
    >>> t = np.arange(4 * sr) / sr
    >>> noisy = 0.2 * np.sin(2 * np.pi * 440 * t) + 0.02 * np.sin(2 * np.pi * 60 * t)
    >>> detect_hum(noisy, sr).frequency
    60.0
    """
    planar, _ = as_planar(audio, channels_last=channels_last, dtype=np.float64)
    if planar.shape[1] < 4:
        return HumEstimate(candidates[0], -np.inf, 0)

    mono = planar.mean(axis=0)
    # A four-second window resolves 0.25 Hz, which separates 50 from 60 Hz and
    # their harmonics without needing the whole file.
    length = min(mono.size, int(round(4.0 * sample_rate)))
    segment = mono[:length] * np.hanning(length)
    spectrum = np.abs(np.fft.rfft(segment))
    frequencies = np.fft.rfftfreq(length, 1.0 / sample_rate)
    resolution = sample_rate / length

    best = HumEstimate(candidates[0], -np.inf, 0)
    for candidate in candidates:
        levels: list[float] = []
        for harmonic in range(1, harmonics + 1):
            target = candidate * harmonic
            if target >= sample_rate / 2.0 * _MAX_FREQUENCY_RATIO:
                break
            level = _peak_over_floor_db(spectrum, frequencies, target, resolution)
            if level is not None:
                levels.append(level)
        if not levels:
            continue
        strength = float(np.mean(levels))
        if strength > best.strength_db:
            best = HumEstimate(
                float(candidate),
                strength,
                int(np.count_nonzero(np.asarray(levels) >= 6.0)),
            )
    return best


def _peak_over_floor_db(
    spectrum: np.ndarray,
    frequencies: np.ndarray,
    target: float,
    resolution: float,
) -> float | None:
    """How far the bins at ``target`` stand above the local median level."""
    tone = (frequencies > target - 2.0 * resolution) & (frequencies < target + 2.0 * resolution)
    around = (frequencies > target - 10.0) & (frequencies < target + 10.0) & ~tone
    if not np.any(tone) or np.count_nonzero(around) < 4:
        return None
    floor = float(np.median(spectrum[around]))
    peak = float(np.max(spectrum[tone]))
    if peak <= 0.0:
        return None
    return 20.0 * np.log10(peak / max(floor, 1e-20))


class DeHumEffect(ParametricEQ):
    """Comb notch filter on a mains fundamental and its harmonics.

    Parameters
    ----------
    frequency:
        Mains frequency, or ``"auto"`` to pick between 50 and 60 Hz from the
        first buffer the effect sees.
    harmonics:
        How many teeth, counting the fundamental. Teeth above Nyquist are
        dropped rather than folded back.
    q:
        Tooth width. ``frequency / q`` is roughly the -3 dB bandwidth.
    depth_db:
        ``None`` for a true null; a positive number for a finite cut of that
        many dB, which is gentler on music that lives at the hum frequency.

    Examples
    --------
    >>> dehum = DeHumEffect(frequency=50.0, harmonics=3)
    >>> [round(band.frequency) for band in dehum.teeth(48_000)]
    [50, 100, 150]
    >>> round(float(dehum.magnitude_response_db([100.0], 48_000)[0]), 1) < -20.0
    True
    >>> round(float(dehum.magnitude_response_db([1000.0], 48_000)[0]), 2)
    -0.0
    """

    name = "De-Hum"

    def __init__(
        self,
        frequency: float | str = 50.0,
        harmonics: int = DEFAULT_HARMONICS,
        q: float = DEFAULT_Q,
        depth_db: float | None = None,
        enabled: bool = True,
    ) -> None:
        super().__init__(bands=[], enabled=enabled)
        self.auto = isinstance(frequency, str)
        if self.auto and str(frequency).strip().lower() != "auto":
            raise ValueError("frequency must be a number or 'auto'")
        self._frequency = MAINS_FREQUENCIES[0] if self.auto else float(frequency)
        self.harmonics = int(harmonics)
        self.q = float(q)
        self.depth_db = None if depth_db is None else float(depth_db)
        self._detected: HumEstimate | None = None

    # -- parameters --------------------------------------------------------

    @property
    def frequency(self) -> float:
        """Mains frequency in use; the detected one when ``auto``."""
        return self._frequency

    @frequency.setter
    def frequency(self, value: float | str) -> None:
        if isinstance(value, str):
            if value.strip().lower() != "auto":
                raise ValueError("frequency must be a number or 'auto'")
            self.auto = True
            return
        self.auto = False
        self._frequency = float(value)

    @property
    def detected(self) -> HumEstimate | None:
        """What ``auto`` mode measured, or ``None`` if it has not run."""
        return self._detected

    def teeth(self, sample_rate: float) -> list[EQBand]:
        """The bands this comb applies at ``sample_rate``."""
        limit = sample_rate / 2.0 * _MAX_FREQUENCY_RATIO
        shape = FilterType.NOTCH if self.depth_db is None else FilterType.PEAKING
        gain = 0.0 if self.depth_db is None else -abs(self.depth_db)
        bands = []
        for harmonic in range(1, max(1, self.harmonics) + 1):
            centre = self._frequency * harmonic
            if centre >= limit:
                break
            bands.append(
                EQBand(centre, gain, self.q, shape, label=f"{centre:.0f} Hz")
            )
        return bands

    def parameters(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "mix": self.mix,
            "frequency": "auto" if self.auto else self._frequency,
            "harmonics": self.harmonics,
            "q": self.q,
            "depth_db": self.depth_db,
        }

    # -- ParametricEQ ------------------------------------------------------

    def sos(self, sample_rate: float) -> np.ndarray:
        self.bands = self.teeth(sample_rate)
        return super().sos(sample_rate)

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        if self.auto and self._detected is None:
            self._detected = detect_hum(audio, sample_rate, channels_last=False)
            self._frequency = self._detected.frequency
        return super()._process_planar(audio, sample_rate)

    def reset(self) -> None:
        super().reset()
        if self.auto:
            self._detected = None
