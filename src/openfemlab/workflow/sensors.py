"""Test-channel to analysis-DOF mapping (MS-2.1) as the workflow consumes it.

A :class:`SensorMap` is the ordered list of analysis rows the instrumentation
observes, with a per-channel orientation sign for accelerometers mounted
against the model axis.  Reducing an FE mode shape through it yields a matrix
whose rows line up with the measured channels, which is the precondition for
every correlation metric downstream.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt

from ..correlation.align import selection_matrix

__all__ = ["SensorMap"]


@dataclass(frozen=True)
class SensorMap:
    """Ordered mapping from test channels to analysis DOF rows.

    Parameters
    ----------
    rows:
        Analysis row index observed by each test channel, in channel order.
    signs:
        Orientation sign per channel (``+1`` / ``-1``); defaults to all ``+1``.
    labels:
        Optional channel labels used in reports and COMAC tables.
    """

    rows: tuple[int, ...]
    signs: tuple[float, ...] = ()
    labels: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        rows = tuple(int(row) for row in self.rows)
        if not rows:
            raise ValueError("a sensor map needs at least one channel")
        if len(set(rows)) != len(rows):
            raise ValueError("a sensor map must not observe the same analysis row twice")
        if any(row < 0 for row in rows):
            raise ValueError("sensor rows must be non-negative")
        signs = tuple(float(s) for s in self.signs) if self.signs else (1.0,) * len(rows)
        if len(signs) != len(rows):
            raise ValueError("signs must have one entry per channel")
        if any(s == 0.0 for s in signs):
            raise ValueError("sensor signs must be nonzero")
        labels = None if self.labels is None else tuple(str(label) for label in self.labels)
        if labels is not None and len(labels) != len(rows):
            raise ValueError("labels must have one entry per channel")
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "signs", signs)
        object.__setattr__(self, "labels", labels)

    def __len__(self) -> int:
        return len(self.rows)

    @property
    def n_channels(self) -> int:
        return len(self.rows)

    @classmethod
    def identity(cls, n_channels: int, labels: Sequence[str] | None = None) -> SensorMap:
        """Map channel ``i`` onto analysis row ``i`` — a fully instrumented model."""
        return cls(
            rows=tuple(range(int(n_channels))),
            labels=None if labels is None else tuple(labels),
        )

    def channel_labels(self) -> tuple[str, ...]:
        """Labels if given, else ``"dof<row>"`` placeholders."""
        return self.labels or tuple(f"dof{row}" for row in self.rows)

    def operator(self, ndof: int) -> npt.NDArray[np.float64]:
        """The dense selection operator ``T`` (``n_channels × ndof``)."""
        return selection_matrix(ndof, self.rows, self.signs)

    def reduce(self, shapes: Any) -> npt.NDArray[Any]:
        """Reduce ``(ndof, n_modes)`` analysis shapes onto the sensor channels."""
        matrix = np.asarray(shapes)
        if matrix.ndim == 1:
            matrix = matrix.reshape(-1, 1)
        highest = max(self.rows)
        if matrix.shape[0] <= highest:
            raise ValueError(
                f"sensor map observes analysis row {highest} but the shapes have "
                f"{matrix.shape[0]} rows"
            )
        return matrix[list(self.rows), :] * np.asarray(self.signs)[:, None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": list(self.rows),
            "signs": list(self.signs),
            "labels": None if self.labels is None else list(self.labels),
        }
