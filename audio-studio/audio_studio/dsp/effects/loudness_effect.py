"""Loudness normalisation as an effect: drive integrated LUFS onto a target.

:class:`~audio_studio.dsp.effects.gain.NormalizeEffect` matches *levels* —
peak, true peak or RMS. Delivery specs are written in none of those: they ask
for a BS.1770 integrated loudness, which weights the spectrum the way the ear
does and gates out the silences. :class:`LoudnessNormalizeEffect` is the rack
version of that workflow: measure the whole clip with
:class:`~audio_studio.dsp.loudness.LoudnessMeter`, apply the single global
gain that lands it on the target, and optionally hold that gain back so the
reconstructed (4x oversampled) peak stays under a true-peak ceiling — the
same arithmetic the batch pipeline's ``NormalizeLoudness`` operation uses, so
a clip rendered in the editor measures the same as one rendered by the CLI.

Two published targets cover almost every hand-off and are provided as named
presets:

============  ===========  =========  =================================
Preset        Integrated   True peak  Where it comes from
============  ===========  =========  =================================
`broadcast`   -23 LUFS     -1 dBTP    EBU R 128 programme loudness
`streaming`   -16 LUFS     -1 dBTP    Podcast/streaming distribution
============  ===========  =========  =================================

Like every whole-signal effect, this one is offline only: the gain cannot be
known until the last gating block has been measured, so it applies on render
and is skipped during live preview.

Examples
--------
>>> import numpy as np
>>> sr = 48_000
>>> tone = 0.5 * np.sin(2 * np.pi * 1000.0 * np.arange(sr * 2) / sr)
>>> effect = LoudnessNormalizeEffect.from_preset("broadcast")
>>> out = effect.process(np.stack([tone, tone]), sr)
>>> from audio_studio.dsp.loudness import LoudnessMeter
>>> round(LoudnessMeter(sr).integrated(out), 1)
-23.0
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..loudness import LoudnessMeter
from ..util import db_to_linear
from .base import Effect

__all__ = [
    "LOUDNESS_PRESETS",
    "LoudnessNormalizeEffect",
    "LoudnessPreset",
    "loudness_preset",
]


@dataclass(frozen=True)
class LoudnessPreset:
    """A named loudness-normalisation target: integrated LUFS plus a ceiling."""

    name: str
    target_lufs: float
    max_true_peak_dbtp: float | None = None

    def __str__(self) -> str:
        text = f"{self.name}: {self.target_lufs:+.0f} LUFS"
        if self.max_true_peak_dbtp is not None:
            text += f", <= {self.max_true_peak_dbtp:.1f} dBTP"
        return text


#: The two hand-offs the Loudness Match rack slot offers. Keys are lowercase;
#: :func:`loudness_preset` does the lookup.
LOUDNESS_PRESETS: dict[str, LoudnessPreset] = {
    "broadcast": LoudnessPreset("Broadcast (EBU R 128)", -23.0, -1.0),
    "streaming": LoudnessPreset("Streaming", -16.0, -1.0),
}


def loudness_preset(preset: LoudnessPreset | str) -> LoudnessPreset:
    """Resolve a :class:`LoudnessPreset`, by object or by name.

    Examples
    --------
    >>> loudness_preset("Broadcast").target_lufs
    -23.0
    """
    if isinstance(preset, LoudnessPreset):
        return preset
    key = str(preset).strip().lower().replace("-", "_").replace(" ", "_")
    if key in LOUDNESS_PRESETS:
        return LOUDNESS_PRESETS[key]
    raise KeyError(f"unknown loudness preset {preset!r}; known: {sorted(LOUDNESS_PRESETS)}")


class LoudnessNormalizeEffect(Effect):
    """Scale a buffer so its BS.1770 integrated loudness lands on ``target_lufs``.

    Parameters
    ----------
    target_lufs:
        Integrated loudness the clip should measure after processing.
    max_true_peak_dbtp:
        Optional ceiling on the reconstructed peak. When reaching the loudness
        target would push the true peak over this, the gain is capped instead:
        the clip comes out quieter than asked rather than clipped, exactly as
        the batch pipeline behaves. ``None`` applies the loudness gain
        unconditionally.
    max_gain_db:
        Safety limit on the boost. Near-silent material can be tens of LU
        under any target; amplifying it that far mostly amplifies the noise
        floor, so the gain is clamped here first.

    Material the standard cannot gate — digital silence, or clips shorter
    than one 400 ms gating block — is passed through untouched.

    Examples
    --------
    >>> import numpy as np
    >>> sr = 48_000
    >>> quiet = 0.05 * np.sin(2 * np.pi * 1000.0 * np.arange(sr * 2) / sr)
    >>> effect = LoudnessNormalizeEffect(target_lufs=-16.0)
    >>> _ = effect.process(np.stack([quiet, quiet]), sr)
    >>> round(effect.applied_gain_db)      # -26 LUFS tone, 10 dB up to -16
    10
    """

    name = "Loudness Match"
    is_offline_only = True

    def __init__(
        self,
        target_lufs: float = -23.0,
        max_true_peak_dbtp: float | None = -1.0,
        max_gain_db: float = 60.0,
        enabled: bool = True,
    ) -> None:
        super().__init__(enabled=enabled)
        self.target_lufs = float(target_lufs)
        self.max_true_peak_dbtp = (
            None if max_true_peak_dbtp is None else float(max_true_peak_dbtp)
        )
        self.max_gain_db = float(max_gain_db)
        self._last_gain_db = 0.0
        self._last_measured_lufs = -math.inf

    @classmethod
    def from_preset(
        cls, preset: LoudnessPreset | str, enabled: bool = True
    ) -> LoudnessNormalizeEffect:
        """Build the effect from a named delivery preset.

        Examples
        --------
        >>> LoudnessNormalizeEffect.from_preset("streaming").target_lufs
        -16.0
        """
        spec = loudness_preset(preset)
        return cls(
            target_lufs=spec.target_lufs,
            max_true_peak_dbtp=spec.max_true_peak_dbtp,
            enabled=enabled,
        )

    def apply_preset(self, preset: LoudnessPreset | str) -> None:
        """Point an existing effect at a named preset without replacing it."""
        spec = loudness_preset(preset)
        self.target_lufs = spec.target_lufs
        self.max_true_peak_dbtp = spec.max_true_peak_dbtp

    @property
    def applied_gain_db(self) -> float:
        """Gain chosen by the most recent :meth:`process` call."""
        return self._last_gain_db

    @property
    def measured_lufs(self) -> float:
        """Integrated loudness of the most recently processed input."""
        return self._last_measured_lufs

    def parameters(self) -> dict[str, Any]:
        return {
            **super().parameters(),
            "target_lufs": self.target_lufs,
            "max_true_peak_dbtp": self.max_true_peak_dbtp,
            "max_gain_db": self.max_gain_db,
        }

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        meter = LoudnessMeter(sample_rate)
        measured = meter.integrated(audio, channels_last=False)
        self._last_measured_lufs = measured
        if not math.isfinite(measured):
            self._last_gain_db = 0.0
            return audio

        gain_db = min(self.target_lufs - measured, self.max_gain_db)
        if self.max_true_peak_dbtp is not None:
            true_peak = meter.true_peak(audio, channels_last=False)
            if math.isfinite(true_peak):
                gain_db = min(gain_db, self.max_true_peak_dbtp - true_peak)

        self._last_gain_db = gain_db
        return audio * np.asarray(db_to_linear(gain_db), dtype=audio.dtype)
