"""Digital signal processing layer: spectral analysis, effects and metering.

Quick start::

    from audio_studio.dsp import LoudnessMeter, SpectralAnalyzer, ThreeBandEQ

    analyzer = SpectralAnalyzer(sample_rate=48_000, fft_size=2048, window="hann")
    spectrogram = analyzer.spectrogram(audio)      # calibrated, dBFS-referenced
    eq = ThreeBandEQ(low_gain_db=3.0, mid_frequency=2_500.0, mid_gain_db=-4.0)
    processed = eq.process(audio, 48_000)
    LoudnessMeter(48_000).integrated(processed)    # LUFS, ITU-R BS.1770

All buffers are planar ``(n_channels, n_samples)`` float arrays; mono may be
passed as plain 1-D. See :mod:`audio_studio.dsp.util` for the conversion
helpers used at file and device boundaries.
"""

from .effects import (
    Effect,
    EffectChain,
    EQBand,
    FadeEffect,
    FadeShape,
    FilterType,
    GainEffect,
    LevelReport,
    NormalizeEffect,
    NormalizeMode,
    ParametricEQ,
    ThreeBandEQ,
    apply_fade,
    fade_envelope,
    measure_levels,
)
from .loudness import (
    LoudnessMeter,
    LoudnessReport,
    channel_weights,
    format_lufs,
    integrated_loudness,
    k_weighting_sos,
)
from .preview import EffectPreview
from .spectral import (
    RealtimeSpectrum,
    SpectralAnalyzer,
    SpectralConfig,
    Spectrogram,
    SpectrumBars,
    SpectrumScaling,
    WaterfallBuffer,
)
from .util import (
    amplitude_to_db,
    as_interleaved,
    as_planar,
    db_to_linear,
    linear_to_db,
    peak_level,
    power_to_db,
    rms_level,
    true_peak_level,
)
from .windows import WindowInfo, WindowType, available_windows, get_window, window_info

__all__ = [
    # spectral
    "SpectralAnalyzer",
    "SpectralConfig",
    "Spectrogram",
    "SpectrumBars",
    "SpectrumScaling",
    "RealtimeSpectrum",
    "WaterfallBuffer",
    # windows
    "WindowType",
    "WindowInfo",
    "get_window",
    "window_info",
    "available_windows",
    # effects
    "Effect",
    "EffectChain",
    "ThreeBandEQ",
    "ParametricEQ",
    "EQBand",
    "FilterType",
    "GainEffect",
    "NormalizeEffect",
    "NormalizeMode",
    "LevelReport",
    "measure_levels",
    "FadeEffect",
    "FadeShape",
    "fade_envelope",
    "apply_fade",
    # live preview
    "EffectPreview",
    # loudness
    "LoudnessMeter",
    "LoudnessReport",
    "channel_weights",
    "format_lufs",
    "integrated_loudness",
    "k_weighting_sos",
    # utils
    "as_planar",
    "as_interleaved",
    "db_to_linear",
    "linear_to_db",
    "amplitude_to_db",
    "power_to_db",
    "peak_level",
    "rms_level",
    "true_peak_level",
]
