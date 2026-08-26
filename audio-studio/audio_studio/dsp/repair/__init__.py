"""Restoration tools: the two faults that dominate real recordings.

`DeClickEffect` removes impulsive damage — vinyl ticks, dropouts, edit clicks —
by predicting what the signal should have been and interpolating across what it
was. `DeHumEffect` removes steady mains interference with a comb of notches on
50 or 60 Hz and its harmonics.

Both are ordinary rack effects, so they combine with the rest of the chain::

    from audio_studio.dsp import EffectChain
    from audio_studio.dsp.repair import DeClickEffect, DeHumEffect

    restoration = EffectChain([DeHumEffect(frequency="auto"), DeClickEffect()])
    cleaned = restoration.process(audio, sample_rate)

The de-hummer streams; the de-clicker needs the samples on both sides of a
click and therefore renders offline, which an :class:`EffectChain` handles by
skipping it during live preview.
"""

from .declick import (
    ClickEvent,
    DeClickEffect,
    DeClickReport,
    detect_clicks,
    repair_clicks,
    threshold_sigma_for,
)
from .dehum import DeHumEffect, HumEstimate, detect_hum

__all__ = [
    "ClickEvent",
    "DeClickEffect",
    "DeClickReport",
    "DeHumEffect",
    "HumEstimate",
    "detect_clicks",
    "detect_hum",
    "repair_clicks",
    "threshold_sigma_for",
]
