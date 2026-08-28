"""Shared contract for external solver displacement results."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

__all__ = ["ExternalResult"]


@dataclass(frozen=True, slots=True)
class ExternalResult:
    """Nodal coordinates and displacements from an external solver."""

    node_ids: npt.NDArray[np.int64]
    coordinates: npt.NDArray[np.float64]
    displacements: npt.NDArray[np.float64]
    format: str
    meta: dict[str, object]

    @property
    def num_nodes(self) -> int:
        return int(self.node_ids.size)

    def to_npz_dict(self) -> dict[str, object]:
        return {
            "format": self.format,
            "node_ids": self.node_ids,
            "coordinates": self.coordinates,
            "displacements": self.displacements,
            "meta": np.array([self.meta], dtype=object),
        }

    @classmethod
    def from_npz(cls, archive: dict[str, object]) -> ExternalResult:
        meta_value = archive.get("meta")
        if isinstance(meta_value, np.ndarray) and meta_value.size:
            meta = dict(meta_value[0]) if isinstance(meta_value[0], dict) else {}
        else:
            meta = dict(meta_value) if isinstance(meta_value, dict) else {}
        return cls(
            node_ids=np.asarray(archive["node_ids"], dtype=np.int64),
            coordinates=np.asarray(archive["coordinates"], dtype=float),
            displacements=np.asarray(archive["displacements"], dtype=float),
            format=str(archive.get("format", "openfemlab-external-v1")),
            meta=meta,
        )
