"""Degree-of-freedom bookkeeping.

A :class:`DofMap` gives every ``(node_id, DofType)`` pair a stable global row
index. Mode shapes, load vectors, and system matrices are meaningless arrays
without one; correlation between FE and test data is expressed as operations
on two DofMaps (intersection, reduction, expansion).
"""

from __future__ import annotations

from enum import IntEnum

import numpy as np
import numpy.typing as npt


class DofType(IntEnum):
    """Nodal degree-of-freedom kinds (translations then rotations)."""

    UX = 0
    UY = 1
    UZ = 2
    RX = 3
    RY = 4
    RZ = 5


class DofMap:
    """Bidirectional map ``(node_id, DofType) <-> global index``.

    Rows are ordered exactly as given at construction; global matrices and
    result vectors follow this ordering. Instances are immutable.

    Parameters
    ----------
    node_ids:
        External node label per DOF row, shape ``(ndof,)``.
    dof_types:
        :class:`DofType` value per DOF row, shape ``(ndof,)``.
    """

    __slots__ = ("_node_ids", "_dof_types", "_index")

    def __init__(
        self,
        node_ids: npt.ArrayLike,
        dof_types: npt.ArrayLike,
    ) -> None:
        self._node_ids = np.asarray(node_ids, dtype=np.int64)
        self._dof_types = np.asarray(dof_types, dtype=np.int64)
        if self._node_ids.shape != self._dof_types.shape or self._node_ids.ndim != 1:
            raise ValueError("node_ids and dof_types must be 1-D and equal length")
        self._index: dict[tuple[int, int], int] = {
            (int(n), int(d)): i
            for i, (n, d) in enumerate(zip(self._node_ids, self._dof_types, strict=False))
        }
        if len(self._index) != self._node_ids.size:
            raise ValueError("duplicate (node_id, dof_type) pair in DofMap")

    @classmethod
    def regular(cls, node_ids: npt.ArrayLike, dofs_per_node: tuple[DofType, ...]) -> DofMap:
        """Build a map with the same DOF set at every node (node-major order)."""
        nodes = np.asarray(node_ids, dtype=np.int64)
        nids = np.repeat(nodes, len(dofs_per_node))
        dtypes = np.tile(np.array(dofs_per_node, dtype=np.int64), nodes.size)
        return cls(nids, dtypes)

    @property
    def ndof(self) -> int:
        return self._node_ids.size

    @property
    def node_ids(self) -> npt.NDArray[np.int64]:
        return self._node_ids.copy()

    @property
    def dof_types(self) -> npt.NDArray[np.int64]:
        return self._dof_types.copy()

    def index_of(self, node_id: int, dof: DofType) -> int:
        """Global row index of one DOF. Raises ``KeyError`` if absent."""
        return self._index[(int(node_id), int(dof))]

    def intersection_indices(self, other: DofMap) -> tuple[
        npt.NDArray[np.intp], npt.NDArray[np.intp]
    ]:
        """Row indices ``(rows_self, rows_other)`` of the common DOFs.

        The common DOFs are returned in ``self``'s ordering. This is the
        primitive behind FE/test DOF matching in ``correlation``.
        """
        rows_self: list[int] = []
        rows_other: list[int] = []
        for key, i in self._index.items():
            j = other._index.get(key)
            if j is not None:
                rows_self.append(i)
                rows_other.append(j)
        order = np.argsort(rows_self, kind="stable")
        return (
            np.asarray(rows_self, dtype=np.intp)[order],
            np.asarray(rows_other, dtype=np.intp)[order],
        )

    def __len__(self) -> int:
        return self.ndof

    def __repr__(self) -> str:
        return f"DofMap(ndof={self.ndof}, nodes={np.unique(self._node_ids).size})"
