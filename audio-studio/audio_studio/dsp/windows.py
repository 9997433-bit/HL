"""Analysis windows and their calibration constants.

A spectrum is only quantitatively meaningful once the window's gain has been
divided back out, so every window is paired here with the two sums that all
amplitude/power calibration derives from:

``S1 = sum(w)``
    Coherent gain. Divide an amplitude spectrum by ``S1`` so that a full-scale
    sinusoid reads its true amplitude regardless of the window.
``S2 = sum(w**2)``
    Incoherent (noise) gain. Divide a power spectrum by ``fs * S2`` to obtain a
    power spectral density in units of V^2/Hz.

Windows are generated in *periodic* (DFT-even) form, which is the correct
choice for spectral analysis and for overlap-add resynthesis; the symmetric
form used for FIR filter design would break the constant-overlap-add property.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

import numpy as np

__all__ = ["WindowType", "WindowInfo", "get_window", "window_info", "available_windows"]


class WindowType(str, Enum):
    """Supported analysis windows.

    The three required by the module spec (Hann, Hamming, Blackman) are joined
    by the rest of the Harris family so that the analyzer can trade main-lobe
    width against sidelobe rejection without extra code.
    """

    RECTANGULAR = "rectangular"
    HANN = "hann"
    HAMMING = "hamming"
    BLACKMAN = "blackman"
    BLACKMAN_HARRIS = "blackman_harris"
    NUTTALL = "nuttall"
    FLATTOP = "flattop"
    BARTLETT = "bartlett"

    @classmethod
    def coerce(cls, value: WindowType | str) -> WindowType:
        """Accept either an enum member or its string name."""
        if isinstance(value, cls):
            return value
        key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "none": cls.RECTANGULAR,
            "boxcar": cls.RECTANGULAR,
            "rect": cls.RECTANGULAR,
            "hanning": cls.HANN,
            "blackmanharris": cls.BLACKMAN_HARRIS,
            "triangular": cls.BARTLETT,
        }
        if key in aliases:
            return aliases[key]
        try:
            return cls(key)
        except ValueError as exc:
            raise ValueError(
                f"unknown window {value!r}; expected one of "
                f"{', '.join(w.value for w in cls)}"
            ) from exc


def _cosine_sum(length: int, coefficients: tuple[float, ...]) -> np.ndarray:
    """Generalised cosine window ``sum_k (-1)^k a_k cos(2*pi*k*n/N)``."""
    n = np.arange(length, dtype=np.float64)
    phase = 2.0 * np.pi * n / length  # periodic: divide by N, not N-1
    window = np.zeros(length, dtype=np.float64)
    for k, a_k in enumerate(coefficients):
        window += ((-1.0) ** k) * a_k * np.cos(k * phase)
    return window


def _bartlett(length: int) -> np.ndarray:
    n = np.arange(length, dtype=np.float64)
    half = length / 2.0
    return 1.0 - np.abs((n - half) / half)


_GENERATORS: dict[WindowType, Callable[[int], np.ndarray]] = {
    WindowType.RECTANGULAR: lambda n: np.ones(n, dtype=np.float64),
    WindowType.HANN: lambda n: _cosine_sum(n, (0.5, 0.5)),
    WindowType.HAMMING: lambda n: _cosine_sum(n, (0.54, 0.46)),
    WindowType.BLACKMAN: lambda n: _cosine_sum(n, (0.42, 0.5, 0.08)),
    WindowType.BLACKMAN_HARRIS: lambda n: _cosine_sum(
        n, (0.35875, 0.48829, 0.14128, 0.01168)
    ),
    WindowType.NUTTALL: lambda n: _cosine_sum(
        n, (0.3635819, 0.4891775, 0.1365995, 0.0106411)
    ),
    WindowType.FLATTOP: lambda n: _cosine_sum(
        n, (0.21557895, 0.41663158, 0.277263158, 0.083578947, 0.006947368)
    ),
    WindowType.BARTLETT: _bartlett,
}


@dataclass(frozen=True)
class WindowInfo:
    """A window together with everything needed to calibrate a spectrum."""

    type: WindowType
    samples: np.ndarray
    #: ``sum(w)`` — coherent gain, used for amplitude calibration.
    s1: float
    #: ``sum(w**2)`` — incoherent gain, used for power/PSD calibration.
    s2: float

    @property
    def length(self) -> int:
        return int(self.samples.size)

    @property
    def coherent_gain(self) -> float:
        """Mean window value; the amplitude attenuation applied to a tone."""
        return self.s1 / self.length

    @property
    def enbw_bins(self) -> float:
        """Equivalent noise bandwidth, in FFT bins.

        Multiply by ``sample_rate / fft_size`` to get the ENBW in hertz — the
        width of the ideal brick-wall filter each bin actually behaves like.
        """
        return self.length * self.s2 / (self.s1**2)

    def enbw_hz(self, sample_rate: float, fft_size: int) -> float:
        """Equivalent noise bandwidth in hertz for a given transform size."""
        return self.enbw_bins * sample_rate / float(fft_size)


_CACHE: dict[tuple[WindowType, int], WindowInfo] = {}


def window_info(window: WindowType | str, length: int) -> WindowInfo:
    """Return a cached :class:`WindowInfo` for ``window`` of ``length`` samples.

    Windows are immutable and shared; call ``.samples.copy()`` before mutating.
    """
    if length <= 0:
        raise ValueError(f"window length must be positive, got {length}")
    window_type = WindowType.coerce(window)
    key = (window_type, int(length))
    cached = _CACHE.get(key)
    if cached is not None:
        return cached

    samples = _GENERATORS[window_type](int(length))
    samples.flags.writeable = False
    info = WindowInfo(
        type=window_type,
        samples=samples,
        s1=float(np.sum(samples)),
        s2=float(np.sum(np.square(samples))),
    )
    _CACHE[key] = info
    return info


def get_window(window: WindowType | str, length: int) -> np.ndarray:
    """Return just the window samples (read-only view)."""
    return window_info(window, length).samples


def available_windows() -> list[str]:
    """Names of every supported window, suitable for a UI dropdown."""
    return [w.value for w in WindowType]
