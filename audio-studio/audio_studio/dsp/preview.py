"""Live effect preview: run an :class:`EffectChain` on the device render path.

The engine hands its render callback to whatever
:class:`~audio_studio.core.output.AudioOutput` it was built with, so an effect
rack can be inserted by wrapping that backend rather than by reaching into the
transport::

    preview = EffectPreview(engine.output, chain)
    engine = AudioEngine(preview)

Every block the device pulls goes through the chain on its way out. Nothing
about the clip in memory changes — bypassing the rack instantly returns the
original audio, which is the difference between auditioning a setting and
committing to it.

The wrapper delegates every other attribute to the backend it wraps, so a
device-specific API (``NullOutput.pump``, ``PyAudioOutput.latency``) keeps
working through it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from .effects.base import EffectChain

__all__ = ["EffectPreview"]

RenderCallback = Callable[[int], np.ndarray]


class EffectPreview:
    """An :class:`~audio_studio.core.output.AudioOutput` with an insert.

    Parameters
    ----------
    output:
        The backend to wrap. Its ``open``/``start``/``stop``/``close`` surface
        is used as-is.
    chain:
        Rack to run. Defaults to an empty chain, which is a pass-through until
        something is added to it.

    Notes
    -----
    Processing happens on the device thread. Effects that need the whole signal
    (normalise, fades) are skipped rather than raising — see
    :class:`~audio_studio.dsp.effects.base.EffectChain`'s
    ``skip_offline_in_stream``. Anything that does raise is caught and the dry
    block is passed through: a mistyped parameter must not silence the output
    or take the stream down.
    """

    def __init__(self, output: Any, chain: EffectChain | None = None) -> None:
        self._output = output
        self.chain = chain if chain is not None else EffectChain()
        self._callback: RenderCallback | None = None
        self._processed_blocks = 0
        self._failed_blocks = 0
        self._last_error: Exception | None = None

    # -- introspection -----------------------------------------------------

    @property
    def output(self) -> Any:
        """The wrapped backend."""
        return self._output

    @property
    def name(self) -> str:
        return f"{getattr(self._output, 'name', 'unknown')}+fx"

    @property
    def is_active(self) -> bool:
        """Whether the rack will change anything on the next block."""
        return bool(self.chain.enabled and self.chain.active and self.chain.mix > 0.0)

    @property
    def processed_blocks(self) -> int:
        return self._processed_blocks

    @property
    def failed_blocks(self) -> int:
        """Blocks that fell back to dry audio because the chain raised."""
        return self._failed_blocks

    @property
    def last_error(self) -> Exception | None:
        return self._last_error

    # -- AudioOutput surface ----------------------------------------------

    def open(
        self,
        sample_rate: int,
        channels: int,
        callback: RenderCallback,
        *,
        block_size: int | None = None,
    ) -> None:
        """Open the backend with the chain spliced into ``callback``."""
        self._callback = callback
        self.chain.reset()
        self.chain.prepare(float(sample_rate), int(channels))
        kwargs = {} if block_size is None else {"block_size": block_size}
        self._output.open(sample_rate, channels, self.render, **kwargs)

    def close(self) -> None:
        self._callback = None
        self._output.close()

    def render(self, n_frames: int) -> np.ndarray:
        """Pull a block from the engine and run it through the rack."""
        callback = self._callback
        block = (
            np.zeros((n_frames, max(getattr(self._output, "channels", 1), 1)), dtype=np.float32)
            if callback is None
            else callback(n_frames)
        )
        if not self.is_active or block.size == 0:
            return block

        try:
            processed = self.chain.process_block(
                block, self._output.sample_rate, channels_last=True
            )
        except Exception as exc:  # noqa: BLE001 - the device thread must survive anything
            self._failed_blocks += 1
            self._last_error = exc
            return block
        self._processed_blocks += 1
        return np.asarray(processed, dtype=block.dtype)

    def __getattr__(self, name: str) -> Any:
        # Only reached for attributes this class does not define, so the
        # backend's own API (pump, device_index, is_open, ...) stays reachable.
        # Private names are refused so that a half-initialised instance raises
        # AttributeError instead of recursing through a missing ``_output``.
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._output, name)

    def __repr__(self) -> str:
        return f"EffectPreview({self._output!r}, {len(self.chain)} effects)"
