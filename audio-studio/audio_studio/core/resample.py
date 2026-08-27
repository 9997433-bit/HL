"""Offline sample-rate conversion with an optional libsoxr VHQ path."""

from __future__ import annotations

import os
from math import gcd
from typing import Literal

import numpy as np

from .types import SAMPLE_DTYPE

try:
    import soxr as _soxr
except ImportError:  # pragma: no cover - availability depends on the mastering extra
    _soxr = None

_SOXR_QUALITIES = frozenset({"qq", "lq", "mq", "hq", "vhq"})
_SRC_ENVIRONMENT_VARIABLE = "AUDIO_STUDIO_SRC"


def soxr_available() -> bool:
    """Return whether the optional Python libsoxr bindings can be used."""
    return _soxr is not None


def resample_backend() -> Literal["soxr", "scipy"]:
    """Return the backend selected by availability and ``AUDIO_STUDIO_SRC``.

    With no override, libsoxr is preferred and SciPy is the dependency-free
    fallback. Setting ``AUDIO_STUDIO_SRC=scipy`` forces the fallback for
    reproducibility. A requested but unavailable soxr backend also falls back
    to SciPy so opening an audio file never depends on an optional extra.
    """
    requested = os.environ.get(_SRC_ENVIRONMENT_VARIABLE, "").strip().lower()
    if requested not in {"", "soxr", "scipy"}:
        raise ValueError(
            f"{_SRC_ENVIRONMENT_VARIABLE} must be 'soxr' or 'scipy', got {requested!r}"
        )
    if requested == "scipy":
        return "scipy"
    return "soxr" if soxr_available() else "scipy"


def resample_buffer(
    data: np.ndarray,
    src_rate: int,
    dst_rate: int,
    *,
    quality: str = "vhq",
) -> np.ndarray:
    """Convert mono or interleaved-by-column PCM to ``dst_rate``.

    The return value is contiguous ``float32`` and keeps the input's one- or
    two-dimensional channel layout. ``quality`` uses libsoxr's QQ/LQ/MQ/HQ/VHQ
    names; SciPy's polyphase fallback accepts the same API but has one fixed
    Kaiser-window quality.
    """
    if src_rate <= 0:
        raise ValueError(f"src_rate must be positive, got {src_rate}")
    if dst_rate <= 0:
        raise ValueError(f"dst_rate must be positive, got {dst_rate}")

    normalized_quality = str(quality).strip().lower()
    if normalized_quality not in _SOXR_QUALITIES:
        choices = ", ".join(sorted(_SOXR_QUALITIES))
        raise ValueError(f"quality must be one of {choices}, got {quality!r}")

    samples = np.asarray(data)
    if samples.ndim not in (1, 2):
        raise ValueError(
            f"resample_buffer expects a 1-D or 2-D array, got {samples.ndim}-D"
        )
    samples = np.ascontiguousarray(samples, dtype=SAMPLE_DTYPE)
    if src_rate == dst_rate or samples.shape[0] == 0:
        return samples

    if resample_backend() == "soxr":
        assert _soxr is not None  # narrowed by resample_backend()
        converted = _soxr.resample(
            samples,
            float(src_rate),
            float(dst_rate),
            quality=normalized_quality.upper(),
        )
    else:
        from scipy.signal import resample_poly

        divisor = gcd(int(src_rate), int(dst_rate))
        converted = resample_poly(
            samples,
            dst_rate // divisor,
            src_rate // divisor,
            axis=0,
        )

    return np.ascontiguousarray(converted, dtype=SAMPLE_DTYPE)
