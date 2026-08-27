"""Quality and backend-selection gates for offline sample-rate conversion."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
AUDIO_STUDIO_ROOT = REPOSITORY_ROOT / "audio-studio"
if str(AUDIO_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(AUDIO_STUDIO_ROOT))

from audio_studio.core.resample import (
    resample_backend,
    resample_buffer,
    soxr_available,
)

SOURCE_RATE = 96_000
TARGET_RATE = 44_100


def _db(value: float) -> float:
    return 20.0 * math.log10(max(value, np.finfo(np.float64).tiny))


def _log_sweep(sample_rate: int, duration: float) -> np.ndarray:
    start_hz = 20.0
    end_hz = 18_000.0
    time = np.arange(round(sample_rate * duration), dtype=np.float64) / sample_rate
    log_ratio = math.log(end_hz / start_hz)
    phase = (
        2.0
        * np.pi
        * start_hz
        * duration
        / log_ratio
        * (np.exp(time * log_ratio / duration) - 1.0)
    )
    return 0.5 * np.sin(phase)


def _sweep_snr_db() -> float:
    duration = 1.5
    converted = resample_buffer(
        _log_sweep(SOURCE_RATE, duration),
        SOURCE_RATE,
        TARGET_RATE,
    ).astype(np.float64)
    reference = _log_sweep(TARGET_RATE, duration)
    usable = min(converted.size, reference.size)
    trim = round(0.1 * TARGET_RATE)
    converted = converted[trim : usable - trim]
    reference = reference[trim : usable - trim]
    error_rms = math.sqrt(float(np.mean(np.square(converted - reference))))
    reference_rms = math.sqrt(float(np.mean(np.square(reference))))
    return _db(reference_rms / error_rms)


def _tone_thd_plus_n_dbfs() -> float:
    duration = 1.0
    source_time = np.arange(round(SOURCE_RATE * duration), dtype=np.float64) / SOURCE_RATE
    source = 0.9 * np.sin(2.0 * np.pi * 1_000.0 * source_time)
    converted = resample_buffer(source, SOURCE_RATE, TARGET_RATE).astype(np.float64)
    trim = round(0.1 * TARGET_RATE)
    converted = converted[trim:-trim]

    time = np.arange(converted.size, dtype=np.float64) / TARGET_RATE
    basis = np.column_stack(
        (
            np.sin(2.0 * np.pi * 1_000.0 * time),
            np.cos(2.0 * np.pi * 1_000.0 * time),
            np.ones(converted.size, dtype=np.float64),
        )
    )
    coefficients, *_ = np.linalg.lstsq(basis, converted, rcond=None)
    residual = converted - basis @ coefficients
    return _db(math.sqrt(float(np.mean(np.square(residual)))))


def test_scipy_fallback_meets_relaxed_sweep_and_distortion_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIO_STUDIO_SRC", "scipy")

    assert resample_backend() == "scipy"
    assert _sweep_snr_db() > 45.0
    assert _tone_thd_plus_n_dbfs() < -75.0


@pytest.mark.skipif(not soxr_available(), reason="requires the optional mastering extra")
def test_soxr_vhq_meets_mastering_sweep_and_distortion_gates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIO_STUDIO_SRC", "soxr")

    assert resample_backend() == "soxr"
    assert _sweep_snr_db() > 100.0
    assert _tone_thd_plus_n_dbfs() < -130.0


def test_resample_buffer_preserves_channel_layout_and_float32(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUDIO_STUDIO_SRC", "scipy")
    source = np.column_stack((np.linspace(-0.5, 0.5, 960), np.zeros(960)))

    converted = resample_buffer(source, 48_000, 44_100)

    assert converted.shape == (882, 2)
    assert converted.dtype == np.float32
    assert converted.flags.c_contiguous


def test_invalid_src_override_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDIO_STUDIO_SRC", "unknown")

    with pytest.raises(ValueError, match="AUDIO_STUDIO_SRC"):
        resample_buffer(np.zeros(32), 48_000, 44_100)
