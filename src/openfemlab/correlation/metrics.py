"""Frequency-error metrics for FE/test correlation.

Pure array functions on frequency vectors, kept free of any pairing or shape
machinery so both :mod:`openfemlab.correlation.pairing` and the report layer
can build on them.

Sign convention (MS-2.4, pinned): the *test* data is the reference and the FE
model is judged against it, so a relative error is

``Δf [%] = 100 · (f_fe − f_test) / f_test``

and a positive value means the FE model is too stiff (or too light).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

__all__ = [
    "FrequencyDifference",
    "frequency_difference",
    "frequency_error_matrix",
    "relative_frequency_error",
]

FloatArray = npt.NDArray[np.float64]


def _as_frequencies(values: Any, name: str) -> FloatArray:
    freq = np.asarray(values, dtype=np.float64).ravel()
    if freq.size == 0:
        raise ValueError(f"{name} must contain at least one frequency")
    if np.any(freq < 0.0):
        raise ValueError(f"{name} must be non-negative")
    return freq


def relative_frequency_error(
    test_frequencies: Any,
    fe_frequencies: Any,
) -> FloatArray:
    """Signed relative error ``(f_fe − f_test) / f_test`` of paired frequencies.

    Rigid-body modes (``f_test == 0``) yield ``±inf`` rather than a division
    warning; callers filter on ``np.isfinite``.
    """
    test = _as_frequencies(test_frequencies, "test_frequencies")
    fe = _as_frequencies(fe_frequencies, "fe_frequencies")
    if test.shape != fe.shape:
        raise ValueError(f"frequency vectors must have equal length, got {test.size} and {fe.size}")
    out = np.empty_like(test)
    nonzero = test > 0.0
    out[nonzero] = (fe[nonzero] - test[nonzero]) / test[nonzero]
    residual = fe[~nonzero] - test[~nonzero]
    out[~nonzero] = np.where(residual == 0.0, 0.0, np.copysign(np.inf, residual))
    return out


@dataclass(frozen=True)
class FrequencyDifference:
    """Element-wise frequency comparison of an FE set against a test set."""

    test: FloatArray
    fe: FloatArray
    absolute: FloatArray
    percent: FloatArray

    @property
    def max_abs_percent(self) -> float:
        finite = self.percent[np.isfinite(self.percent)]
        return float(np.max(np.abs(finite))) if finite.size else 0.0

    @property
    def mean_abs_percent(self) -> float:
        finite = self.percent[np.isfinite(self.percent)]
        return float(np.mean(np.abs(finite))) if finite.size else 0.0

    @property
    def rms_percent(self) -> float:
        finite = self.percent[np.isfinite(self.percent)]
        return float(np.sqrt(np.mean(finite**2))) if finite.size else 0.0

    def table(self) -> str:
        """Human-readable per-mode frequency comparison."""
        header = f"{'mode':>5} {'f_test [Hz]':>12} {'f_fe [Hz]':>12} {'Δf [Hz]':>10} {'Δf [%]':>9}"
        lines = [header, "-" * len(header)]
        for i, (ft, ffe, da, dp) in enumerate(
            zip(self.test, self.fe, self.absolute, self.percent, strict=False)
        ):
            lines.append(f"{i:>5} {ft:12.4f} {ffe:12.4f} {da:10.4f} {dp:9.3f}")
        return "\n".join(lines)


def frequency_difference(test_frequencies: Any, fe_frequencies: Any) -> FrequencyDifference:
    """Absolute and relative frequency differences between paired mode sets."""
    test = _as_frequencies(test_frequencies, "test_frequencies")
    fe = _as_frequencies(fe_frequencies, "fe_frequencies")
    if test.shape != fe.shape:
        raise ValueError(f"frequency vectors must have equal length, got {test.size} and {fe.size}")
    return FrequencyDifference(
        test=test,
        fe=fe,
        absolute=fe - test,
        percent=100.0 * relative_frequency_error(test, fe),
    )


def frequency_error_matrix(test_frequencies: Any, fe_frequencies: Any) -> FloatArray:
    """``(n_test, n_fe)`` matrix of relative frequency errors in percent.

    This is the frequency-proximity candidate table used by mode pairing.
    """
    test = _as_frequencies(test_frequencies, "test_frequencies")
    fe = _as_frequencies(fe_frequencies, "fe_frequencies")
    with np.errstate(divide="ignore", invalid="ignore"):
        errors = 100.0 * (fe[None, :] - test[:, None]) / test[:, None]
    return np.where(np.isfinite(errors), errors, np.inf)
