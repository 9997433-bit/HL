"""Rectangular coordinate-system helpers for OP2 Phase 4 (MS-9.6).

Reads ``CORD2R`` records from ``GEOM1`` and transforms ``GRID`` locations
written in ``CP`` and eigenvectors written in ``CD`` into the basic frame.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from ._common import FormatError

__all__ = [
    "GEOM1_CORD2R_RECORD",
    "CORD2R_ENTRY_WORDS",
    "RectangularSystem",
    "read_cord2r_systems",
    "resolve_rectangular_systems",
    "transform_point_to_basic",
    "transform_vector_to_basic",
    "transform_six_dof_to_basic",
    "require_defined_frames",
]

GEOM1_CORD2R_RECORD = (2101, 21, 8)
CORD2R_ENTRY_WORDS = 13


@dataclass(frozen=True)
class RectangularSystem:
    """One ``CORD2R`` definition before and after resolution."""

    cid: int
    rid: int
    origin: npt.NDArray[np.float64]
    z_point: npt.NDArray[np.float64]
    xz_point: npt.NDArray[np.float64]
    origin_basic: npt.NDArray[np.float64] | None = None
    basis: npt.NDArray[np.float64] | None = None

    @property
    def is_resolved(self) -> bool:
        return self.origin_basic is not None and self.basis is not None


def read_cord2r_systems(
    integers: npt.NDArray[np.integer],
    floats: npt.NDArray[np.floating],
    *,
    source_name: str | None,
) -> dict[int, RectangularSystem]:
    """Parse one ``CORD2R`` record body into cid → system."""
    if integers.size != floats.size:
        raise FormatError("CORD2R record integer and float views disagree on length")
    if integers.size % CORD2R_ENTRY_WORDS:
        raise FormatError(
            f"CORD2R record holds {integers.size} words, which is not a multiple of "
            f"{CORD2R_ENTRY_WORDS}"
        )
    systems: dict[int, RectangularSystem] = {}
    for start in range(0, integers.size, CORD2R_ENTRY_WORDS):
        cid = int(integers[start])
        rid = int(integers[start + 3])
        origin = np.asarray(floats[start + 4 : start + 7], dtype=float)
        z_point = np.asarray(floats[start + 7 : start + 10], dtype=float)
        xz_point = np.asarray(floats[start + 10 : start + 13], dtype=float)
        if cid in systems:
            where = f"OP2 file {source_name}" if source_name else "OP2 stream"
            raise FormatError(f"{where}: duplicate CORD2R id {cid}")
        systems[cid] = RectangularSystem(
            cid=cid,
            rid=rid,
            origin=origin,
            z_point=z_point,
            xz_point=xz_point,
        )
    return systems


def _rectangular_basis(
    origin: npt.NDArray[np.float64],
    z_point: npt.NDArray[np.float64],
    xz_point: npt.NDArray[np.float64],
) -> npt.NDArray[np.float64]:
    z_axis = z_point - origin
    z_norm = float(np.linalg.norm(z_axis))
    if z_norm <= 0.0:
        raise FormatError("CORD2R z-axis point coincides with the origin")
    z_hat = z_axis / z_norm
    x_vec = xz_point - origin
    x_vec = x_vec - np.dot(x_vec, z_hat) * z_hat
    x_norm = float(np.linalg.norm(x_vec))
    if x_norm <= 0.0:
        raise FormatError("CORD2R xz-plane point does not define a valid x-axis")
    x_hat = x_vec / x_norm
    y_hat = np.cross(z_hat, x_hat)
    return np.vstack([x_hat, y_hat, z_hat])


def resolve_rectangular_systems(
    systems: dict[int, RectangularSystem],
) -> dict[int, RectangularSystem]:
    """Resolve every ``CORD2R`` into the basic frame."""
    resolved: dict[int, RectangularSystem] = {
        0: RectangularSystem(
            cid=0,
            rid=0,
            origin=np.zeros(3, dtype=float),
            z_point=np.array([0.0, 0.0, 1.0]),
            xz_point=np.array([1.0, 0.0, 0.0]),
            origin_basic=np.zeros(3, dtype=float),
            basis=np.eye(3, dtype=float),
        )
    }

    def resolve(cid: int) -> RectangularSystem:
        if cid in resolved:
            return resolved[cid]
        if cid not in systems:
            raise FormatError(f"coordinate system {cid} is referenced but not defined")
        raw = systems[cid]
        parent = resolve(raw.rid)
        origin_basic = transform_point_to_basic(raw.origin, parent)
        z_basic = transform_point_to_basic(raw.z_point, parent)
        xz_basic = transform_point_to_basic(raw.xz_point, parent)
        basis = _rectangular_basis(origin_basic, z_basic, xz_basic)
        frame = RectangularSystem(
            cid=raw.cid,
            rid=raw.rid,
            origin=raw.origin,
            z_point=raw.z_point,
            xz_point=raw.xz_point,
            origin_basic=origin_basic,
            basis=basis,
        )
        resolved[cid] = frame
        return frame

    for cid in systems:
        resolve(cid)
    return resolved


def transform_point_to_basic(
    point: npt.NDArray[np.floating], frame: RectangularSystem
) -> npt.NDArray[np.float64]:
    """Map a location written in ``frame`` into the basic frame."""
    if frame.origin_basic is None or frame.basis is None:
        raise FormatError(f"coordinate system {frame.cid} is not resolved")
    vector = np.asarray(point, dtype=float).reshape(3)
    if frame.cid == 0:
        return vector
    return vector @ frame.basis + frame.origin_basic


def transform_vector_to_basic(
    vector: npt.NDArray[np.floating], frame: RectangularSystem
) -> npt.NDArray[np.float64]:
    """Map a displacement/rotation vector from ``frame`` into the basic frame."""
    if frame.basis is None:
        raise FormatError(f"coordinate system {frame.cid} is not resolved")
    values = np.asarray(vector, dtype=float).reshape(3)
    if frame.cid == 0:
        return values
    return values @ frame.basis


def transform_six_dof_to_basic(
    components: npt.NDArray[np.floating], frame: RectangularSystem
) -> npt.NDArray[np.float64]:
    """Map six eigenvector components from ``CD`` into the basic frame."""
    values = np.asarray(components, dtype=float).reshape(6)
    translation = transform_vector_to_basic(values[:3], frame)
    rotation = transform_vector_to_basic(values[3:], frame)
    return np.concatenate([translation, rotation])


def require_defined_frames(
    frames: npt.NDArray[np.integer],
    systems: dict[int, RectangularSystem],
    *,
    source_name: str | None,
    grid_ids: npt.NDArray[np.integer] | None = None,
) -> None:
    """Raise when a ``GRID`` names a ``CP``/``CD`` that the file never defined."""
    missing = sorted({int(value) for value in frames.reshape(-1) if int(value) != 0})
    undefined = [cid for cid in missing if cid not in systems]
    if not undefined:
        return
    listed = ", ".join(str(cid) for cid in undefined[:5])
    more = ", ..." if len(undefined) > 5 else ""
    where = f"OP2 file {source_name}" if source_name else "OP2 stream"
    raise FormatError(
        f"{where}: GRID {listed}{more} reference coordinate system(s) the file "
        "does not define through CORD2R; Phase 4 reads CORD2R only"
    )
