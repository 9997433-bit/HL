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

Thread contract
---------------

An effect chain is not real-time safe. It allocates, it can be reconfigured
from the GUI mid-block, and a filter or a lookahead limiter can easily take
longer than a block period on a busy machine. None of that belongs on the
device callback, where overrunning the deadline is an audible dropout.

So the rack runs on the **feeder thread** whenever it can. When the object that
handed :meth:`EffectPreview.open` its render callback exposes
``set_stream_processor`` — which :class:`~audio_studio.core.engine.AudioEngine`
does — the chain is installed there and processes each block on its way *into*
the ring buffer. The device callback then only copies audio that is already
wet, and the whole depth of the ring is available as slack for a chain that
runs long.

Three consequences follow, and they are the reason this is worth spelling out:

* **Effects sit before the master fader**, because the engine applies volume on
  the way out of the ring. That is the conventional order for an insert.
* **A parameter change lands after the ring drains**, roughly the transport's
  buffer depth. Bypass is no longer instant to the sample; it is instant to the
  block that has not been queued yet.
* **The counters below are written by the feeder**, not the device thread.

The device path is kept for anything the preview cannot bind to — a bare
backend opened with a plain callback, as the tests do. Its behaviour is
identical apart from where the work happens, which is why
:meth:`EffectPreview.process_block` is the single implementation both use.

Whichever thread runs it, an effect that raises costs one dry block rather than
the stream, and an offline-only effect (normalise, fades) is skipped rather
than treated as an error.
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
    Processing happens on the feeder thread when the engine offers one, and on
    the device thread otherwise; see the module docstring for the contract.
    Effects that need the whole signal (normalise, fades) are skipped rather
    than raising — see :class:`~audio_studio.dsp.effects.base.EffectChain`'s
    ``skip_offline_in_stream``. Anything that does raise is caught and the dry
    block is passed through: a mistyped parameter must not silence the output
    or take the stream down.
    """

    def __init__(self, output: Any, chain: EffectChain | None = None) -> None:
        self._output = output
        self.chain = chain if chain is not None else EffectChain()
        self._callback: RenderCallback | None = None
        self._host: Any | None = None
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
    def runs_on_feeder(self) -> bool:
        """Whether the chain is currently running ahead of the ring buffer."""
        return self._host is not None

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
        self._bind_feeder(callback)
        kwargs = {} if block_size is None else {"block_size": block_size}
        self._output.open(sample_rate, channels, self.render, **kwargs)

    def close(self) -> None:
        self._release_feeder()
        self._callback = None
        self._output.close()

    def render(self, n_frames: int) -> np.ndarray:
        """Device callback: hand over a block, wet already if the feeder ran.

        With the chain bound to the feeder this is a pull and nothing else —
        the audio in the ring buffer has been processed since before it was
        queued.
        """
        callback = self._callback
        if callback is None:
            return np.zeros(
                (n_frames, max(getattr(self._output, "channels", 1), 1)), dtype=np.float32
            )
        block = callback(n_frames)
        if self._host is not None:
            return block
        return self.process_block(block, self._output.sample_rate)

    def process_block(self, block: np.ndarray, sample_rate: int) -> np.ndarray:
        """Run the rack over one block. Called from the feeder or the device.

        Never raises: a failing effect is counted and its block passed through
        dry, because a wrong parameter must cost a block rather than the
        stream.
        """
        if not self.is_active or block.size == 0:
            return block
        try:
            processed = self.chain.process_block(block, sample_rate, channels_last=True)
        except Exception as exc:  # noqa: BLE001 - neither thread may see this raise
            self._failed_blocks += 1
            self._last_error = exc
            return block
        self._processed_blocks += 1
        return np.asarray(processed, dtype=block.dtype)

    # -- feeder binding ----------------------------------------------------

    def _bind_feeder(self, callback: RenderCallback) -> None:
        """Move the chain off the device thread when the caller allows it.

        The engine reaches us as the ``__self__`` of the bound render callback
        it passed to :meth:`open`, so nothing has to be threaded through the
        backend API to find it. A host that offers no insert point (a bare
        backend driven by a plain function) simply keeps the device path.
        """
        self._release_feeder()
        host = getattr(callback, "__self__", None)
        install = getattr(host, "set_stream_processor", None)
        if callable(install):
            install(self.process_block)
            self._host = host

    def _release_feeder(self) -> None:
        host, self._host = self._host, None
        if host is not None:
            host.set_stream_processor(None)

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
