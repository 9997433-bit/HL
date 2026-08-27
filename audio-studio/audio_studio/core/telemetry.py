"""Lock-free engine telemetry shared by the render, feeder and UI threads.

The level meter has one producer and one consumer (the UI timer).
:class:`EngineTelemetry` gives each side a private :class:`LevelSnapshot` and
uses the third slot as the most recently published value.  The producer
therefore never waits for the UI, and neither publishing nor reading creates a
new snapshot.

Measurement itself is split in two so the device callback stays free of NumPy
reductions (which allocate temporaries and intermediate scalars):

* :meth:`EngineTelemetry.capture_block` is the **device-thread** entry point.
  It copies the rendered block into one preallocated capture buffer and bumps a
  sequence counter — a bounded ``memcpy`` and two integer stores, nothing more.
* :meth:`EngineTelemetry.publish_pending` is the **feeder-thread** entry point.
  It notices a fresh capture, runs the peak/RMS reductions in the preallocated
  workspace and publishes the result through the triple buffer.

The capture hand-off is a seqlock: the writer holds an odd sequence while
copying, and the reader re-checks the sequence after its own copy so a torn
block is discarded rather than measured.  Losing a block this way only skips
one meter update; the next capture supersedes it anyway.

Snapshots returned by :meth:`EngineTelemetry.read_levels` are borrowed.  A
snapshot remains protected from the producer until the consumer calls
``read_levels`` again; callers should consume it immediately rather than retain
it across UI ticks.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from .types import SAMPLE_DTYPE

__all__ = ["EngineTelemetry", "LevelSnapshot"]


@dataclass(slots=True)
class LevelSnapshot:
    """One preallocated per-channel peak/RMS meter reading."""

    peak: np.ndarray
    rms: np.ndarray
    valid: bool = False

    @property
    def is_empty(self) -> bool:
        """Whether the engine has published audio into this slot."""
        return not self.valid


class EngineTelemetry:
    """Triple-buffered level telemetry for one render and one UI thread.

    The real-time entry point is ``capture_block``: the device callback copies
    its rendered block into a preallocated capture buffer and returns.  The
    feeder thread later calls ``publish_pending``, which runs the peak/RMS
    reductions in the preallocated workspace and publishes them.
    ``publish_block`` remains for callers that already run off the device
    thread (tests, offline render backends) and want to measure and publish in
    one step.  ``read_levels`` returns a preallocated slot and marks it as
    consumer-owned, leaving the producer the other two slots to alternate
    between.

    Slot exchange relies on the CPython GIL making reference and small-integer
    assignments atomic.  The verification in ``read_levels`` handles a publish
    that lands between selecting and claiming a slot; the sequence re-check in
    ``publish_pending`` handles a capture that lands mid-measurement.
    """

    _SLOT_COUNT = 3

    def __init__(self, channels: int = 0, *, block_size: int = 1024) -> None:
        self._channels = 0
        self._block_size = 0
        self._slots: tuple[LevelSnapshot, LevelSnapshot, LevelSnapshot]
        self._workspace = np.empty((0, 0), dtype=SAMPLE_DTYPE)
        self._capture = np.empty((0, 0), dtype=SAMPLE_DTYPE)
        self._capture_frames = 0
        self._capture_sequence = 0
        self._drained_sequence = 0
        self._published_index = 0
        self._reader_index = 0
        self._writer_index = 1
        self.configure(channels, block_size=block_size)

    @property
    def channels(self) -> int:
        """Number of channels represented by every snapshot."""
        return self._channels

    @property
    def block_size(self) -> int:
        """Maximum frame count covered by the preallocated workspace."""
        return self._block_size

    def configure(self, channels: int, *, block_size: int | None = None) -> None:
        """Allocate slots for a stream before its render callback starts."""
        channels = int(channels)
        frames = self._block_size if block_size is None else int(block_size)
        if channels < 0:
            raise ValueError(f"channels must be non-negative, got {channels}")
        if frames <= 0:
            raise ValueError(f"block_size must be positive, got {frames}")

        if channels == self._channels and frames == self._block_size:
            self.clear()
            return

        self._channels = channels
        self._block_size = frames
        self._slots = tuple(
            LevelSnapshot(
                peak=np.zeros(channels, dtype=np.float64),
                rms=np.zeros(channels, dtype=np.float64),
            )
            for _ in range(self._SLOT_COUNT)
        )  # type: ignore[assignment]
        self._workspace = np.empty((frames, channels), dtype=SAMPLE_DTYPE)
        self._capture = np.empty((frames, channels), dtype=SAMPLE_DTYPE)
        self._capture_frames = 0
        self._capture_sequence = 0
        self._drained_sequence = 0
        self._published_index = 0
        self._reader_index = 0
        self._writer_index = 1

    def clear(self) -> None:
        """Publish an empty reading without replacing any slot or array.

        Also drops any block captured but not yet measured, so a stopped
        transport cannot resurrect a stale meter reading afterwards.
        """
        self._drained_sequence = self._capture_sequence
        slot = self._slots[self._writer_index]
        slot.peak.fill(0.0)
        slot.rms.fill(0.0)
        slot.valid = False
        self._commit_write()

    def capture_block(self, block: np.ndarray) -> None:
        """Stash one rendered ``(frames, channels)`` block for later measuring.

        This is the device-thread half of the meter: a bounded copy into
        preallocated storage plus two integer stores, with no NumPy reductions
        and no allocation.  A block longer than ``block_size`` is clamped to
        its first ``block_size`` frames and a channel-count mismatch is
        silently dropped — a real-time callback must never raise.
        """
        frames = block.shape[0]
        if block.ndim != 2 or block.shape[1] != self._channels or self._channels == 0:
            return
        if frames == 0:
            return
        sequence = self._capture_sequence + 1
        self._capture_sequence = sequence  # odd: a write is in flight
        if frames >= self._block_size:
            np.copyto(self._capture, block[: self._block_size])
            self._capture_frames = self._block_size
        else:
            self._capture[:frames] = block[:frames]
            self._capture_frames = frames
        self._capture_sequence = sequence + 1  # even: stable and ready

    def publish_pending(self) -> bool:
        """Measure and publish the most recent capture; ``False`` when stale.

        This is the feeder-thread half of the meter.  The reductions run in
        the preallocated workspace, so steady-state metering allocates no
        sample arrays on any thread.  A capture that lands mid-copy is
        discarded (the sequence re-check fails) and simply measured on the
        next call.
        """
        sequence = self._capture_sequence
        if sequence == self._drained_sequence or sequence & 1:
            return False
        frames = self._capture_frames
        source = self._capture if frames == self._block_size else self._capture[:frames]
        workspace = self._workspace if frames == self._block_size else self._workspace[:frames]
        np.copyto(workspace, source)
        if self._capture_sequence != sequence:
            return False  # torn by a concurrent capture; a fresher block follows
        self._drained_sequence = sequence
        self._measure_and_publish(workspace, workspace)
        return True

    def publish_block(self, block: np.ndarray) -> None:
        """Measure and publish one ``(frames, channels)`` block in one step.

        Not for the device callback — its reductions are the very work
        :meth:`capture_block` exists to defer.  Offline callers and tests that
        already run off the real-time thread use this to measure and publish
        without the capture hand-off.
        """
        if block.ndim != 2:
            raise ValueError(f"meter block must be 2-D, got {block.ndim}-D")
        frames, channels = block.shape
        if channels != self._channels:
            raise ValueError(
                f"meter block has {channels} channels, telemetry expects {self._channels}"
            )
        if frames > self._block_size:
            raise ValueError(
                f"meter block has {frames} frames, workspace holds {self._block_size}"
            )
        if frames == 0 or channels == 0:
            return

        workspace = self._workspace if frames == self._block_size else self._workspace[:frames]
        self._measure_and_publish(block, workspace)

    def _measure_and_publish(self, block: np.ndarray, workspace: np.ndarray) -> None:
        """Reduce ``block`` through ``workspace`` into the writer slot.

        ``block`` may *be* the workspace: every step either reads before it
        writes or works in place.  The RMS reduction accumulates into the
        slot's float64 output for numerical stability.
        """
        slot = self._slots[self._writer_index]
        np.absolute(block, out=workspace)
        np.max(workspace, axis=0, out=slot.peak)
        np.square(workspace, out=workspace)
        np.mean(workspace, axis=0, dtype=np.float64, out=slot.rms)
        np.sqrt(slot.rms, out=slot.rms)
        slot.valid = True
        self._commit_write()

    def publish(
        self,
        peak: Sequence[float] | np.ndarray,
        rms: Sequence[float] | np.ndarray,
    ) -> None:
        """Publish already-reduced levels into a preallocated slot.

        The engine uses :meth:`publish_block`; this form is useful to another
        render backend that already computed meter reductions.
        """
        if len(peak) != self._channels or len(rms) != self._channels:
            raise ValueError(f"peak and RMS must each contain {self._channels} channels")
        slot = self._slots[self._writer_index]
        np.copyto(slot.peak, peak, casting="unsafe")
        np.copyto(slot.rms, rms, casting="unsafe")
        slot.valid = True
        self._commit_write()

    def read_levels(self) -> LevelSnapshot:
        """Borrow the latest complete snapshot without copying or allocating."""
        while True:
            index = self._published_index
            self._reader_index = index
            if index == self._published_index:
                return self._slots[index]

    def read(self) -> LevelSnapshot:
        """Short alias for :meth:`read_levels`."""
        return self.read_levels()

    def _commit_write(self) -> None:
        """Publish the producer slot and choose the only unowned slot."""
        self._published_index = self._writer_index
        published = self._published_index
        reader = self._reader_index

        # When producer and consumer point at different slots, their indices
        # subtract from 0 + 1 + 2 to identify the sole free slot.  When they
        # point at the same slot, either other slot is safe.
        self._writer_index = (
            (published + 1) % self._SLOT_COUNT
            if published == reader
            else self._SLOT_COUNT - published - reader
        )
