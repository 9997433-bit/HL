"""Restoration tools: the faults that dominate real recordings.

`DeClickEffect` removes impulsive damage — vinyl ticks, dropouts, edit clicks —
by predicting what the signal should have been and interpolating across what it
was. `DeClipEffect` reconstructs flat-topped peaks with a cubic spline.
`DeHumEffect` removes steady mains interference with a comb of notches on 50 or
60 Hz and its harmonics. `NoiseReduceEffect` takes out a stationary noise floor
— hiss, rumble, room tone — by learning its spectrum and applying a Wiener
gain to every bin.

All of them are ordinary rack effects, so they combine with the rest of the
chain in the order a restoration engineer works in::

    from audio_studio.dsp import EffectChain
    from audio_studio.dsp.repair import DeClickEffect, DeHumEffect, NoiseReduceEffect

    restoration = EffectChain(
        [DeHumEffect(frequency="auto"), DeClickEffect(), NoiseReduceEffect()]
    )
    cleaned = restoration.process(audio, sample_rate)

Hum and noise removal stream; the de-clicker needs the samples on both sides of
a click and therefore renders offline, which an :class:`EffectChain` handles by
skipping it during live preview. Noise reduction streams at the cost of one
analysis window of latency, the same bargain the limiter's lookahead makes.
"""

from .declick import (
    ClickEvent,
    DeClickEffect,
    DeClickReport,
    detect_clicks,
    repair_clicks,
    threshold_sigma_for,
)
from .declip import (
    ClipEvent,
    DeClipEffect,
    DeClipReport,
    detect_clipping,
    repair_clipping,
)
from .dehum import DeHumEffect, HumEstimate, detect_hum
from .noise_reduce import (
    NoiseProfile,
    NoiseReduceEffect,
    learn_noise_profile,
    reduce_noise,
)

__all__ = [
    "ClipEvent",
    "ClickEvent",
    "DeClipEffect",
    "DeClipReport",
    "DeClickEffect",
    "DeClickReport",
    "DeHumEffect",
    "HumEstimate",
    "NoiseProfile",
    "NoiseReduceEffect",
    "detect_clipping",
    "detect_clicks",
    "detect_hum",
    "learn_noise_profile",
    "reduce_noise",
    "repair_clipping",
    "repair_clicks",
    "threshold_sigma_for",
]
