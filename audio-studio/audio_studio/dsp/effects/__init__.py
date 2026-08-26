"""Audio effects: EQ, dynamics, spatial processing, level control and fades.

Every processor subclasses :class:`~audio_studio.dsp.effects.base.Effect` and
can be combined with :class:`~audio_studio.dsp.effects.base.EffectChain`::

    chain = EffectChain([
        ThreeBandEQ(low_gain_db=3.0, high_gain_db=-2.0),
        NormalizeEffect(target_db=-1.0, mode="true_peak"),
        FadeEffect(fade_in_s=0.01, fade_out_s=0.05),
    ])
    processed = chain.process(audio, sample_rate)
"""

from .base import Effect, EffectChain
from .dynamics import CompressorEffect, LimiterEffect
from .eq import EQBand, FilterType, ParametricEQ, ThreeBandEQ
from .fade import FadeEffect, FadeShape, apply_fade, fade_envelope
from .gain import (
    GainEffect,
    LevelReport,
    NormalizeEffect,
    NormalizeMode,
    measure_levels,
)
from .loudness_effect import (
    LOUDNESS_PRESETS,
    LoudnessNormalizeEffect,
    LoudnessPreset,
    loudness_preset,
)
from .spatial import DelayEffect, FDNReverbEffect, NoiseGateEffect

__all__ = [
    "Effect",
    "EffectChain",
    "CompressorEffect",
    "LimiterEffect",
    "EQBand",
    "FilterType",
    "ParametricEQ",
    "ThreeBandEQ",
    "FadeEffect",
    "FadeShape",
    "apply_fade",
    "fade_envelope",
    "GainEffect",
    "LevelReport",
    "NormalizeEffect",
    "NormalizeMode",
    "measure_levels",
    "LOUDNESS_PRESETS",
    "LoudnessNormalizeEffect",
    "LoudnessPreset",
    "loudness_preset",
    "NoiseGateEffect",
    "DelayEffect",
    "FDNReverbEffect",
]
