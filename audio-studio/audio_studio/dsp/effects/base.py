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

Every effect also carries the two controls a mixer strip expects:
:attr:`Effect.bypass` takes it out of the signal path entirely, and
:attr:`Effect.mix` crossfades its output against the untouched input.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

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

    def __init__(self, enabled: bool = True, mix: float = 1.0) -> None:
        self.enabled = bool(enabled)
        self.mix = mix
        self._prepared_sample_rate: float | None = None
        self._prepared_channels: int | None = None

    # -- mixer controls ---------------------------------------------------

    @property
    def mix(self) -> float:
        """Wet/dry balance in ``[0, 1]``: ``1.0`` is fully processed audio.

        The dry signal is the effect's *input*, so a chain member set to
        ``0.5`` blends against whatever the members before it produced rather
        than against the original file.
        """
        return self._mix

    @mix.setter
    def mix(self, value: float) -> None:
        self._mix = float(min(max(float(value), 0.0), 1.0))

    @property
    def bypass(self) -> bool:
        """Inverse of :attr:`enabled`, named the way a mixer strip names it."""
        return not self.enabled

    @bypass.setter
    def bypass(self, value: bool) -> None:
        self.enabled = not bool(value)

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

    def reset(self) -> None:  # noqa: B027 - stateless effects legitimately do nothing
        """Clear streaming state without changing parameters."""

    def parameters(self) -> dict[str, Any]:
        """Serialisable parameter snapshot, for presets and undo history."""
        return {"enabled": self.enabled, "mix": self.mix}

    # -- public API -------------------------------------------------------

    def process(
        self,
        audio: np.ndarray,
        sample_rate: float,
        channels_last: bool | None = None,
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
        out = self._apply_planar(planar, float(sample_rate))
        return self._finish(planar.copy() if out is planar else out, was_mono, channels_last)

    def process_block(
        self,
        block: np.ndarray,
        sample_rate: float,
        channels_last: bool | None = None,
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
        out = self._apply_planar(planar, float(sample_rate))
        return self._finish(planar.copy() if out is planar else out, was_mono, channels_last)

    # -- internals --------------------------------------------------------

    def _apply_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        """:meth:`_process_planar` with :attr:`enabled` and :attr:`mix` honoured.

        This is the entry point a host (or an enclosing :class:`EffectChain`)
        should call: going straight to ``_process_planar`` would silently skip
        both controls.
        """
        if not self.enabled:
            return audio
        wet = self._process_planar(audio, sample_rate)
        if self._mix >= 1.0:
            return wet
        if self._mix <= 0.0:
            return audio
        return audio * (1.0 - self._mix) + wet * self._mix

    @staticmethod
    def _finish(
        planar: np.ndarray, was_mono: bool, channels_last: bool | None
    ) -> np.ndarray:
        result = restore_layout(planar, was_mono)
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

    The chain is itself an :class:`Effect`, so chains nest, and it has the same
    :attr:`~Effect.bypass` and :attr:`~Effect.mix` controls as its members —
    the chain's mix crossfades the whole rack against the audio that went into
    it, which is the "amount" control on a mastering insert.

    Parameters
    ----------
    skip_offline_in_stream:
        What :meth:`process_block` does with a member that needs the whole
        signal. ``True`` (the default) skips it, which is what a live preview
        wants: an EQ can be auditioned while a normaliser waits for render.
        ``False`` restores the strict contract and raises instead.

    Examples
    --------
    >>> import numpy as np
    >>> class Halve(Effect):
    ...     def _process_planar(self, audio, sample_rate):
    ...         return audio * 0.5
    >>> chain = EffectChain([Halve()])
    >>> chain.mix = 0.5                       # half wet, half dry
    >>> float(chain.process(np.ones(4), 48_000)[0])
    0.75
    >>> chain.bypass = True
    >>> float(chain.process(np.ones(4), 48_000)[0])
    1.0
    """

    name = "Effect Chain"

    def __init__(
        self,
        effects: list[Effect] | None = None,
        enabled: bool = True,
        mix: float = 1.0,
        skip_offline_in_stream: bool = True,
    ) -> None:
        super().__init__(enabled=enabled, mix=mix)
        self.effects: list[Effect] = list(effects or [])
        self.skip_offline_in_stream = bool(skip_offline_in_stream)

    @property
    def is_offline_only(self) -> bool:  # type: ignore[override]
        if self.skip_offline_in_stream:
            return False
        return any(effect.is_offline_only for effect in self.effects if effect.enabled)

    @property
    def active(self) -> list[Effect]:
        """Members that will actually process audio right now."""
        return [effect for effect in self.effects if effect.enabled]

    # -- rack editing -----------------------------------------------------

    def add(self, effect: Effect) -> EffectChain:
        self.effects.append(effect)
        self._prepare_member(effect)
        return self

    def insert(self, index: int, effect: Effect) -> EffectChain:
        self.effects.insert(index, effect)
        self._prepare_member(effect)
        return self

    def remove(self, effect: Effect) -> EffectChain:
        self.effects.remove(effect)
        return self

    def move(self, index: int, new_index: int) -> EffectChain:
        """Reorder one slot. Order matters: EQ before a limiter is not the same."""
        effect = self.effects.pop(index)
        self.effects.insert(max(0, min(new_index, len(self.effects))), effect)
        return self

    def clear(self) -> EffectChain:
        self.effects.clear()
        return self

    def _prepare_member(self, effect: Effect) -> None:
        if self._prepared_sample_rate is not None and self._prepared_channels is not None:
            effect.prepare(self._prepared_sample_rate, self._prepared_channels)

    # -- Effect -----------------------------------------------------------

    def prepare(self, sample_rate: float, n_channels: int) -> None:
        super().prepare(sample_rate, n_channels)
        for effect in self.effects:
            effect.prepare(sample_rate, n_channels)

    def reset(self) -> None:
        for effect in self.effects:
            effect.reset()

    def parameters(self) -> dict[str, Any]:
        return {
            **super().parameters(),
            "effects": [
                {"type": type(e).__name__, **e.parameters()} for e in self.effects
            ],
        }

    def _process_planar(self, audio: np.ndarray, sample_rate: float) -> np.ndarray:
        out = audio
        for effect in self.effects:
            out = effect._apply_planar(out, sample_rate)
        return out

    def process_block(
        self,
        block: np.ndarray,
        sample_rate: float,
        channels_last: bool | None = None,
    ) -> np.ndarray:
        """Stream one block through the members that can stream.

        Offline-only members are skipped (or raise, see
        ``skip_offline_in_stream``); everything else keeps its filter state
        across calls exactly as it does on its own.
        """
        planar, was_mono = as_planar(block, channels_last=channels_last)
        if not self.enabled or planar.shape[1] == 0:
            return restore_layout(planar.copy(), was_mono)

        self._ensure_prepared(sample_rate, planar.shape[0])
        rate = float(sample_rate)
        out = planar
        for effect in self.effects:
            if not effect.enabled:
                continue
            if effect.is_offline_only:
                if self.skip_offline_in_stream:
                    continue
                raise NotImplementedError(
                    f"{type(effect).__name__} needs the whole signal; use process() instead"
                )
            out = effect._apply_planar(out, rate)

        if out is not planar and self._mix < 1.0:
            out = planar * (1.0 - self._mix) + out * self._mix
        return self._finish(planar.copy() if out is planar else out, was_mono, channels_last)

    def __len__(self) -> int:
        return len(self.effects)

    def __iter__(self):
        return iter(self.effects)

    def __getitem__(self, index: int) -> Effect:
        return self.effects[index]
