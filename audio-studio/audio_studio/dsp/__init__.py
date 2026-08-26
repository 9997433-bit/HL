"""Digital signal processing layer: spectral analysis, effects and metering.

Quick start::

    from audio_studio.dsp import LoudnessMeter, SpectralAnalyzer, ThreeBandEQ

    analyzer = SpectralAnalyzer(sample_rate=48_000, fft_size=2048, window="hann")
    spectrogram = analyzer.spectrogram(audio)      # calibrated, dBFS-referenced
    eq = ThreeBandEQ(low_gain_db=3.0, mid_frequency=2_500.0, mid_gain_db=-4.0)
    processed = eq.process(audio, 48_000)
    LoudnessMeter(48_000).analyze(processed).check("EBU R128")   # ITU-R BS.1770-4

Restoration lives in :mod:`audio_studio.dsp.repair`: ``DeClickEffect`` for
impulsive damage, ``DeHumEffect`` for mains interference. Both are ordinary
rack effects.

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
    DELIVERY_TARGETS,
    ComplianceResult,
    DeliveryTarget,
    LoudnessMeter,
    LoudnessReport,
    StreamingLoudnessMeter,
    channel_weights,
    delivery_target,
    format_lufs,
    integrated_loudness,
    k_weighting_sos,
    true_peak_oversample,
)
from .preview import EffectPreview
from .repair import (
    ClickEvent,
    DeClickEffect,
    DeClickReport,
    DeHumEffect,
    HumEstimate,
    detect_clicks,
    detect_hum,
    repair_clicks,
)
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
    true_peak_candidate_db,
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
    # restoration
    "DeClickEffect",
    "DeClickReport",
    "ClickEvent",
    "detect_clicks",
    "repair_clicks",
    "DeHumEffect",
    "HumEstimate",
    "detect_hum",
    # live preview
    "EffectPreview",
    # loudness
    "LoudnessMeter",
    "StreamingLoudnessMeter",
    "LoudnessReport",
    "ComplianceResult",
    "DeliveryTarget",
    "DELIVERY_TARGETS",
    "delivery_target",
    "channel_weights",
    "format_lufs",
    "integrated_loudness",
    "k_weighting_sos",
    "true_peak_oversample",
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
    "true_peak_candidate_db",
]
