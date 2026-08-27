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

Plugin delay compensation (PDC)
-------------------------------

An external plugin that reports latency hands back audio that is late by that
many samples. On its own that is only a constant offset — but the offset
*changes* when the plugin is bypassed, because a bypassed member is skipped
entirely: toggling bypass moves the stream in time, and an A/B against the dry
signal no longer nulls.

The preview therefore pads the path to a constant. Every block, the deficit
between what the chain *would* delay with the bypassed plugins running too
(:meth:`EffectChain.latency_samples` with ``include_bypassed=True``, which
counts bypassed members only when they opt in via
``Effect.compensate_when_bypassed`` — the plugin adapters do) and what it
delays right now is made up by a :class:`LatencyCompensator` — a plain FIFO
delay appended after the chain. Bypassing a latent plugin swaps its delay for
an equal compensation delay, so the null test still aligns; the plugins that
*are* running are heard exactly as before, and a *native* latent processor
that is switched off keeps costing nothing.

This is the MVP shape of PDC: it compensates the preview insert as a whole and
runs wherever :meth:`EffectPreview.process_block` runs (the engine's feeder
thread when the preview is bound to one). It does not shift the transport's
playhead reporting, and changing the deficit mid-stream (a bypass toggle)
re-primes the delay with silence rather than resampling across the join —
audible as a one-off tick, never as drift. ``pdc_enabled = False`` restores
the uncompensated behaviour.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np

from .effects.base import EffectChain

__all__ = ["EffectPreview", "LatencyCompensator"]

RenderCallback = Callable[[int], np.ndarray]


class LatencyCompensator:
    """A FIFO delay that pads a streamed path to a target latency.

    The delay length is set in whole samples with :meth:`set_delay` and applied
    along axis 0 (time, for the ``(frames, channels)`` blocks the preview
    streams; a 1-D mono block works the same). Changing the length re-primes
    the line with silence — the stream stays sample-continuous *after* the
    change, but the join itself is a hard edit, which is the honest MVP
    behaviour for a toggle that by definition moves the signal in time.

    Examples
    --------
    >>> import numpy as np
    >>> pdc = LatencyCompensator()
    >>> pdc.set_delay(2)
    >>> pdc.process(np.array([1.0, 2.0, 3.0], dtype=np.float32)).tolist()
    [0.0, 0.0, 1.0]
    >>> pdc.process(np.array([4.0, 5.0], dtype=np.float32)).tolist()
    [2.0, 3.0]
    """

    def __init__(self, delay_samples: int = 0) -> None:
        self._delay = max(int(delay_samples), 0)
        self._tail: np.ndarray | None = None

    @property
    def delay_samples(self) -> int:
        """Current delay length, in samples."""
        return self._delay

    def set_delay(self, samples: int) -> None:
        """Resize the delay; a change drops the buffered tail and re-primes."""
        samples = max(int(samples), 0)
        if samples != self._delay:
            self._delay = samples
            self._tail = None

    def reset(self) -> None:
        """Forget buffered audio; the next block is delayed by fresh silence."""
        self._tail = None

    def process(self, block: np.ndarray) -> np.ndarray:
        """Return ``block`` delayed by :attr:`delay_samples` along axis 0."""
        if self._delay <= 0 or block.shape[0] == 0:
            return block
        tail_shape = (self._delay, *block.shape[1:])
        if (
            self._tail is None
            or self._tail.shape != tail_shape
            or self._tail.dtype != block.dtype
        ):
            # First block after a resize/format change: prime with silence.
            self._tail = np.zeros(tail_shape, dtype=block.dtype)
        joined = np.concatenate([self._tail, block], axis=0)
        self._tail = joined[block.shape[0] :]
        return joined[: block.shape[0]]


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
    pdc_enabled:
        Whether plugin delay compensation pads the path to a constant latency
        (see the module docstring). On by default; turning it off restores the
        uncompensated behaviour where a bypass toggle moves the stream in time.

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

    def __init__(
        self,
        output: Any,
        chain: EffectChain | None = None,
        *,
        pdc_enabled: bool = True,
    ) -> None:
        self._output = output
        self.chain = chain if chain is not None else EffectChain()
        self._callback: RenderCallback | None = None
        self._host: Any | None = None
        self._processed_blocks = 0
        self._failed_blocks = 0
        self._last_error: Exception | None = None
        self._pdc = LatencyCompensator()
        self._pdc_enabled = bool(pdc_enabled)

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

    # -- plugin delay compensation ------------------------------------------

    @property
    def pdc_enabled(self) -> bool:
        """Whether the path is padded to a constant latency."""
        return self._pdc_enabled

    @pdc_enabled.setter
    def pdc_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._pdc_enabled:
            return
        self._pdc_enabled = enabled
        # Turning compensation off drops the buffered tail (the stream jumps
        # forward by the padding); turning it on re-primes with silence on the
        # next block. Both are inherent to moving the signal in time.
        self._pdc.set_delay(0)

    def pdc_padding_samples(self) -> int:
        """Silence currently inserted to hold the path's latency constant.

        The deficit between the chain's compensated reference latency
        (running members plus bypassed members that opt in — the plugin
        adapters) and what the members actually running report. Zero when
        compensation is off, when nothing reports latency, or when every
        latent member is active.
        """
        if not self._pdc_enabled:
            return 0
        reference = self.chain.latency_samples(include_bypassed=True)
        active = self.chain.latency_samples() if self.is_active else 0
        return max(reference - active, 0)

    def latency_samples(self) -> int:
        """Total delay the insert imposes on the stream right now, in samples.

        With compensation on this is constant across bypass toggles — the
        chain's full reported latency; with it off it is whatever the members
        currently running report.
        """
        active = self.chain.latency_samples() if self.is_active else 0
        return active + self.pdc_padding_samples()

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
        self._pdc.reset()
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
        stream. Delay compensation applies to every path out of here — wet,
        bypassed and failed alike — because its whole point is that the
        stream's timing does not depend on which of those happened.
        """
        if block.size == 0:
            return block
        out = block
        if self.is_active:
            try:
                out = np.asarray(
                    self.chain.process_block(block, sample_rate, channels_last=True),
                    dtype=block.dtype,
                )
                self._processed_blocks += 1
            except Exception as exc:  # noqa: BLE001 - neither thread may see this raise
                self._failed_blocks += 1
                self._last_error = exc
                out = block
        if not self._pdc_enabled:
            return out
        self._pdc.set_delay(self.pdc_padding_samples())
        return self._pdc.process(out)

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
