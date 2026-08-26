"""Window generation and calibration constants."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.signal import get_window as scipy_get_window

from audio_studio.dsp.windows import WindowType, available_windows, get_window, window_info

_SCIPY_NAMES = {
    WindowType.RECTANGULAR: "boxcar",
    WindowType.HANN: "hann",
    WindowType.HAMMING: "hamming",
    WindowType.BLACKMAN: "blackman",
    WindowType.BLACKMAN_HARRIS: "blackmanharris",
    WindowType.NUTTALL: "nuttall",
    WindowType.FLATTOP: "flattop",
    WindowType.BARTLETT: "bartlett",
}


@pytest.mark.parametrize("window_type", list(WindowType))
def test_matches_scipy_periodic_form(window_type: WindowType) -> None:
    ours = get_window(window_type, 512)
    theirs = scipy_get_window(_SCIPY_NAMES[window_type], 512, fftbins=True)
    assert np.allclose(ours, theirs, atol=1e-12)


@pytest.mark.parametrize("name", available_windows())
def test_calibration_sums(name: str) -> None:
    info = window_info(name, 1024)
    assert info.s1 == pytest.approx(float(np.sum(info.samples)))
    assert info.s2 == pytest.approx(float(np.sum(np.square(info.samples))))
    assert info.enbw_bins >= 1.0  # no window can beat a rectangular one


def test_rectangular_enbw_is_exactly_one_bin() -> None:
    assert window_info(WindowType.RECTANGULAR, 256).enbw_bins == pytest.approx(1.0)


def test_hann_enbw_is_1_5_bins() -> None:
    # The textbook value; a good canary for an off-by-one in the periodic form.
    assert window_info(WindowType.HANN, 4096).enbw_bins == pytest.approx(1.5, abs=1e-3)


def test_enbw_is_independent_of_length() -> None:
    short = window_info(WindowType.BLACKMAN, 256).enbw_bins
    long = window_info(WindowType.BLACKMAN, 8192).enbw_bins
    assert short == pytest.approx(long, rel=1e-2)


def test_enbw_hz_scales_with_sample_rate() -> None:
    info = window_info(WindowType.HANN, 2048)
    assert info.enbw_hz(48_000, 2048) == pytest.approx(1.5 * 48_000 / 2048, rel=1e-3)


def test_windows_are_cached_and_read_only() -> None:
    first = get_window("hann", 128)
    assert get_window(WindowType.HANN, 128) is first
    with pytest.raises(ValueError):
        first[0] = 1.0


@pytest.mark.parametrize(
    "alias,expected",
    [
        ("hanning", WindowType.HANN),
        ("Hann", WindowType.HANN),
        ("blackman-harris", WindowType.BLACKMAN_HARRIS),
        ("boxcar", WindowType.RECTANGULAR),
        ("triangular", WindowType.BARTLETT),
    ],
)
def test_name_coercion(alias: str, expected: WindowType) -> None:
    assert WindowType.coerce(alias) is expected


def test_unknown_window_lists_the_valid_ones() -> None:
    with pytest.raises(ValueError, match="hann"):
        WindowType.coerce("gaussian")


def test_zero_length_rejected() -> None:
    with pytest.raises(ValueError):
        window_info(WindowType.HANN, 0)
