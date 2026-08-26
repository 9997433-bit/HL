"""Lock-free engine telemetry shared by the render and UI threads.

The level meter has one producer (the device callback) and one consumer (the
UI timer).  :class:`EngineTelemetry` gives each side a private
:class:`LevelSnapshot` and uses the third slot as the most recently published
value.  The producer therefore never waits for the UI, and neither publishing
nor reading creates a new snapshot.

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

    ``publish_block`` is the real-time entry point.  Its normal path (a device
    block matching ``block_size``) writes into preallocated arrays and only
    changes integer slot indices when publishing.  ``read_levels`` returns a
    preallocated slot and marks it as consumer-owned, leaving the producer the
    other two slots to alternate between.

    Slot exchange relies on the CPython GIL making reference and small-integer
    assignments atomic.  The verification in ``read_levels`` handles a publish
    that lands between selecting and claiming a slot.
    """

    _SLOT_COUNT = 3

    def __init__(self, channels: int = 0, *, block_size: int = 1024) -> None:
        self._channels = 0
        self._block_size = 0
        self._slots: tuple[LevelSnapshot, LevelSnapshot, LevelSnapshot]
        self._workspace = np.empty((0, 0), dtype=SAMPLE_DTYPE)
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
        self._published_index = 0
        self._reader_index = 0
        self._writer_index = 1

    def clear(self) -> None:
        """Publish an empty reading without replacing any slot or array."""
        slot = self._slots[self._writer_index]
        slot.peak.fill(0.0)
        slot.rms.fill(0.0)
        slot.valid = False
        self._commit_write()

    def publish_block(self, block: np.ndarray) -> None:
        """Measure and publish one ``(frames, channels)`` render block.

        Device callbacks normally contain exactly ``block_size`` frames, which
        uses the workspace itself.  Short final/test blocks use a view into the
        same storage and still allocate no sample array.
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

        slot = self._slots[self._writer_index]
        workspace = self._workspace if frames == self._block_size else self._workspace[:frames]

        # Reuse one float32 work array for both reductions.  The RMS reduction
        # accumulates into the slot's float64 output for numerical stability.
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
