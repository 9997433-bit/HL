"""Common contract shared by every processor in :mod:`audio_studio.dsp.effects`.

Two processing modes are supported and are required to agree:

*Offline* — :meth:`Effect.process` takes a whole buffer and returns a new one.
*Streaming* — :meth:`Effect.process_block` is called repeatedly with
consecutive blocks and carries state across calls.

Concatenating the streaming output of a signal split into blocks must equal the
offline result for the same signal. :class:`~audio_studio.dsp.effects` tests
assert this for every effect, because a mismatch is exactly the class of bug
that only shows up as clicks at buffer boundaries during playback.

Effects that depend on the whole signal (normalisation needs the global peak,
fades need the total length) are marked :attr:`Effect.is_offline_only` and
raise from :meth:`process_block`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import numpy as np

from ..util import as_planar, restore_layout

__all__ = ["Effect", "EffectChain"]


class Effect(ABC):
    """Base class for audio processors.

    Subclasses implement :meth:`_process_planar`, which always receives a
    ``(n_channels, n_samples)`` float array and returns one of the same shape.
    Layout conversion, dtype promotion and mono flattening are handled here.
    """

    #: Display name shown in a UI.
    name: str = "Effect"

    #: ``True`` when the effect needs the entire signal and cannot stream.
    is_offline_only: bool = False

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = bool(enabled)
        self._prepared_sample_rate: Optional[float] = None
        self._prepared_channels: Optional[int] = None

    # -- subclass hooks ---------------------------------------------------

    @abstractmethod
    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        """Process planar audio. Must not modify ``audio`` in place."""

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        """Allocate/rebuild state for a given stream format.

        Called automatically whenever the format changes. Subclasses that hold
        filter memory should override and call ``super().prepare(...)``.
        """
        self._prepared_sample_rate = float(sample_rate)
        self._prepared_channels = int(n_channels)

    def reset(self) -> None:
        """Clear streaming state without changing parameters."""

    def parameters(self) -> Dict[str, Any]:
        """Serialisable parameter snapshot, for presets and undo history."""
        return {"enabled": self.enabled}

    # -- public API -------------------------------------------------------

    def process(
        self,
        audio: np.ndarray,
        sample_rate: float,
        channels_last: Optional[bool] = None,
    ) -> np.ndarray:
        """Process a complete buffer and return a new one.

        The input is never modified. The returned array keeps the caller's
        layout: 1-D in, 1-D out; interleaved in, interleaved out.
        """
        planar, was_mono = as_planar(audio, channels_last=channels_last)
        if not self.enabled or planar.shape[1] == 0:
            return restore_layout(planar.copy(), was_mono)

        self._ensure_prepared(sample_rate, planar.shape[0])
        self.reset()
        out = self._process_planar(planar, float(sample_rate))
        result = restore_layout(out, was_mono)
        if channels_last and not was_mono:
            result = np.ascontiguousarray(result.T)
        return result

    def process_block(
        self,
        block: np.ndarray,
        sample_rate: float,
        channels_last: Optional[bool] = None,
    ) -> np.ndarray:
        """Process one block of a stream, carrying state across calls."""
        if self.is_offline_only:
            raise NotImplementedError(
                f"{type(self).__name__} needs the whole signal; use process() instead"
            )
        planar, was_mono = as_planar(block, channels_last=channels_last)
        if not self.enabled or planar.shape[1] == 0:
            return restore_layout(planar.copy(), was_mono)

        self._ensure_prepared(sample_rate, planar.shape[0])
        out = self._process_planar(planar, float(sample_rate))
        result = restore_layout(out, was_mono)
        if channels_last and not was_mono:
            result = np.ascontiguousarray(result.T)
        return result

    def _ensure_prepared(self, sample_rate: float, n_channels: int) -> None:
        if (
            self._prepared_sample_rate != float(sample_rate)
            or self._prepared_channels != int(n_channels)
        ):
            self.prepare(sample_rate, n_channels)

    def __repr__(self) -> str:
        params = ", ".join(f"{k}={v!r}" for k, v in self.parameters().items())
        return f"{type(self).__name__}({params})"


class EffectChain(Effect):
    """Serial chain of effects processed in list order.

    The chain is itself an :class:`Effect`, so chains nest. It reports as
    offline-only as soon as any member is, which keeps the streaming contract
    honest rather than failing halfway through a block.
    """

    name = "Effect Chain"

    def __init__(self, effects: Optional[list[Effect]] = None, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)
        self.effects: list[Effect] = list(effects or [])

    @property
    def is_offline_only(self) -> bool:  # type: ignore[override]
        return any(effect.is_offline_only for effect in self.effects if effect.enabled)

    def add(self, effect: Effect) -> "EffectChain":
        self.effects.append(effect)
        if self._prepared_sample_rate is not None and self._prepared_channels is not None:
            effect.prepare(self._prepared_sample_rate, self._prepared_channels)
        return self

    def remove(self, effect: Effect) -> "EffectChain":
        self.effects.remove(effect)
        return self

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        super().prepare(sample_rate, n_channels)
        for effect in self.effects:
            effect.prepare(sample_rate, n_channels)

    def reset(self) -> None:
        for effect in self.effects:
            effect.reset()

    def parameters(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "effects": [
                {"type": type(e).__name__, **e.parameters()} for e in self.effects
            ],
        }

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        out = audio
        for effect in self.effects:
            if not effect.enabled:
                continue
            out = effect._process_planar(out, sample_rate)
        return out

    def __len__(self) -> int:
        return len(self.effects)

    def __iter__(self):
        return iter(self.effects)

    def __getitem__(self, index: int) -> Effect:
        return self.effects[index]
