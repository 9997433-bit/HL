"""Coordinate-system helpers for OP2 Phase 4 (MS-9.6).

Reads ``CORD1R``/``CORD2R``/``CORD2C`` records from ``GEOM1`` and transforms
``GRID`` locations written in ``CP`` and eigenvectors written in ``CD`` into
the basic frame.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from ._common import FormatError

__all__ = [
    "GEOM1_CORD1R_RECORD",
    "GEOM1_CORD2C_RECORD",
    "GEOM1_CORD2R_RECORD",
    "CORD1R_ENTRY_WORDS",
    "CORD2R_ENTRY_WORDS",
    "Cord1RDefinition",
    "CoordinateSystem",
    "read_cord1r_definitions",
    "read_cord2c_systems",
    "read_cord2r_systems",
    "resolve_coordinate_systems",
    "transform_point_to_basic",
    "transform_vector_to_basic",
    "transform_six_dof_to_basic",
    "require_defined_frames",
]

GEOM1_CORD2R_RECORD = (2101, 21, 8)
GEOM1_CORD2C_RECORD = (2001, 20, 9)
GEOM1_CORD1R_RECORD = (1801, 18, 5)
CORD2R_ENTRY_WORDS = 13
CORD1R_ENTRY_WORDS = 6

PointSystemRecord = tuple[
    int,
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
    npt.NDArray[np.float64],
    str,
]


@dataclass(frozen=True)
class Cord1RDefinition:
    """One ``CORD1R`` card referencing three ``GRID`` ids."""

    cid: int
    g1: int
    g2: int
    g3: int


@dataclass(frozen=True)
class CoordinateSystem:
    """One resolved rectangular or cylindrical coordinate system."""

    cid: int
    rid: int
    kind: str
    origin_basic: npt.NDArray[np.float64]
    basis: npt.NDArray[np.float64]


# Backward-compatible alias used inside op2.py while the reader migrates.
RectangularSystem = CoordinateSystem


def read_cord2r_systems(
    integers: npt.NDArray[np.integer],
    floats: npt.NDArray[np.floating],
    *,
    source_name: str | None,
) -> dict[int, PointSystemRecord]:
    """Parse one ``CORD2R`` record body into cid → (rid, origin, z, xz, kind)."""
    return _read_point_systems(
        integers,
        floats,
        kind="rectangular",
        source_name=source_name,
        card="CORD2R",
    )


def read_cord2c_systems(
    integers: npt.NDArray[np.integer],
    floats: npt.NDArray[np.floating],
    *,
    source_name: str | None,
) -> dict[int, PointSystemRecord]:
    """Parse one ``CORD2C`` record body into cid → (rid, origin, z, xz, kind)."""
    return _read_point_systems(
        integers,
        floats,
        kind="cylindrical",
        source_name=source_name,
        card="CORD2C",
    )


def _read_point_systems(
    integers: npt.NDArray[np.integer],
    floats: npt.NDArray[np.floating],
    *,
    kind: str,
    source_name: str | None,
    card: str,
) -> dict[int, PointSystemRecord]:
    if integers.size != floats.size:
        raise FormatError(f"{card} record integer and float views disagree on length")
    if integers.size % CORD2R_ENTRY_WORDS:
        raise FormatError(
            f"{card} record holds {integers.size} words, which is not a multiple of "
            f"{CORD2R_ENTRY_WORDS}"
        )
    systems: dict[int, PointSystemRecord] = {}
    for start in range(0, integers.size, CORD2R_ENTRY_WORDS):
        cid = int(integers[start])
        rid = int(integers[start + 3])
        origin = np.asarray(floats[start + 4 : start + 7], dtype=float)
        z_point = np.asarray(floats[start + 7 : start + 10], dtype=float)
        xz_point = np.asarray(floats[start + 10 : start + 13], dtype=float)
        if cid in systems:
            where = f"OP2 file {source_name}" if source_name else "OP2 stream"
            raise FormatError(f"{where}: duplicate {card} id {cid}")
        systems[cid] = (rid, origin, z_point, xz_point, kind)
    return systems


def read_cord1r_definitions(
    integers: npt.NDArray[np.integer],
    *,
    source_name: str | None,
) -> dict[int, Cord1RDefinition]:
    """Parse one ``CORD1R`` record body."""
    if integers.size % CORD1R_ENTRY_WORDS:
        raise FormatError(
            f"CORD1R record holds {integers.size} words, which is not a multiple of "
            f"{CORD1R_ENTRY_WORDS}"
        )
    definitions: dict[int, Cord1RDefinition] = {}
    for start in range(0, integers.size, CORD1R_ENTRY_WORDS):
        cid = int(integers[start])
        g1 = int(integers[start + 3])
        g2 = int(integers[start + 4])
        g3 = int(integers[start + 5])
        if cid in definitions:
            where = f"OP2 file {source_name}" if source_name else "OP2 stream"
            raise FormatError(f"{where}: duplicate CORD1R id {cid}")
        definitions[cid] = Cord1RDefinition(cid=cid, g1=g1, g2=g2, g3=g3)
    return definitions


def _rectangular_basis(
    origin: npt.NDArray[np.float64],
    z_point: npt.NDArray[np.float64],
    xz_point: npt.NDArray[np.float64],
) -> npt.NDArray[np.float64]:
    z_axis = z_point - origin
    z_norm = float(np.linalg.norm(z_axis))
    if z_norm <= 0.0:
        raise FormatError("coordinate z-axis point coincides with the origin")
    z_hat = z_axis / z_norm
    x_vec = xz_point - origin
    x_vec = x_vec - np.dot(x_vec, z_hat) * z_hat
    x_norm = float(np.linalg.norm(x_vec))
    if x_norm <= 0.0:
        raise FormatError("coordinate xz-plane point does not define a valid x-axis")
    x_hat = x_vec / x_norm
    y_hat = np.cross(z_hat, x_hat)
    return np.vstack([x_hat, y_hat, z_hat])


def resolve_coordinate_systems(
    point_systems: dict[int, PointSystemRecord],
    cord1r: dict[int, Cord1RDefinition],
    grid_basic: dict[int, tuple[float, float, float]],
) -> dict[int, CoordinateSystem]:
    """Resolve every coordinate system into the basic frame."""
    resolved: dict[int, CoordinateSystem] = {
        0: CoordinateSystem(
            cid=0,
            rid=0,
            kind="rectangular",
            origin_basic=np.zeros(3, dtype=float),
            basis=np.eye(3, dtype=float),
        )
    }

    pending_point = dict(point_systems)
    pending_cord1r = dict(cord1r)

    def resolve(cid: int) -> CoordinateSystem:
        if cid in resolved:
            return resolved[cid]
        if cid in pending_point:
            rid, origin, z_point, xz_point, kind = pending_point.pop(cid)
            parent = resolve(rid)
            origin_basic = transform_point_to_basic(origin, parent, cylindrical=False)
            z_basic = transform_point_to_basic(z_point, parent, cylindrical=False)
            xz_basic = transform_point_to_basic(xz_point, parent, cylindrical=False)
            basis = _rectangular_basis(origin_basic, z_basic, xz_basic)
            frame = CoordinateSystem(
                cid=cid,
                rid=rid,
                kind=kind,
                origin_basic=origin_basic,
                basis=basis,
            )
            resolved[cid] = frame
            return frame
        if cid in pending_cord1r:
            definition = pending_cord1r.pop(cid)
            for grid_id in (definition.g1, definition.g2, definition.g3):
                if grid_id not in grid_basic:
                    raise FormatError(
                        f"CORD1R {cid} references GRID {grid_id}, which is not available "
                        "when the coordinate system is resolved"
                    )
            origin = np.asarray(grid_basic[definition.g1], dtype=float)
            z_point = np.asarray(grid_basic[definition.g2], dtype=float)
            xz_point = np.asarray(grid_basic[definition.g3], dtype=float)
            basis = _rectangular_basis(origin, z_point, xz_point)
            frame = CoordinateSystem(
                cid=cid,
                rid=0,
                kind="rectangular",
                origin_basic=origin,
                basis=basis,
            )
            resolved[cid] = frame
            return frame
        raise FormatError(f"coordinate system {cid} is referenced but not defined")

    while pending_point or pending_cord1r:
        before = len(resolved)
        for cid in list(pending_point) + list(pending_cord1r):
            try:
                resolve(cid)
            except FormatError:
                continue
        if len(resolved) == before:
            missing = sorted(set(pending_point) | set(pending_cord1r))
            raise FormatError(
                f"coordinate systems could not be resolved; remaining ids: {missing[:5]}"
            )
    return resolved


def resolve_rectangular_systems(
    systems: dict[int, object],
) -> dict[int, CoordinateSystem]:
    """Resolve ``CORD2R`` definitions from either tuples or legacy dataclass inputs."""
    point: dict[int, PointSystemRecord] = {}
    for cid, value in systems.items():
        if isinstance(value, CoordinateSystem):
            continue
        if isinstance(value, tuple) and len(value) == 5:
            point[cid] = value
            continue
        origin = np.asarray(value.origin, dtype=float)
        z_point = np.asarray(value.z_point, dtype=float)
        xz_point = np.asarray(value.xz_point, dtype=float)
        point[cid] = (
            int(value.rid),
            origin,
            z_point,
            xz_point,
            "rectangular",
        )
    return resolve_coordinate_systems(point, {}, {})


def transform_point_to_basic(
    point: npt.NDArray[np.floating],
    frame: CoordinateSystem,
    *,
    cylindrical: bool = False,
) -> npt.NDArray[np.float64]:
    """Map a location written in ``frame`` into the basic frame."""
    if frame.origin_basic is None or frame.basis is None:
        raise FormatError(f"coordinate system {frame.cid} is not resolved")
    if frame.cid == 0:
        return np.asarray(point, dtype=float).reshape(3)
    values = np.asarray(point, dtype=float).reshape(3)
    if cylindrical or frame.kind == "cylindrical":
        radius, theta_deg, axial = values
        theta = np.deg2rad(theta_deg)
        values = np.array(
            [radius * np.cos(theta), radius * np.sin(theta), axial],
            dtype=float,
        )
    return values @ frame.basis + frame.origin_basic


def transform_vector_to_basic(
    vector: npt.NDArray[np.floating],
    frame: CoordinateSystem,
) -> npt.NDArray[np.float64]:
    """Map a displacement/rotation vector from ``frame`` into the basic frame."""
    if frame.basis is None:
        raise FormatError(f"coordinate system {frame.cid} is not resolved")
    values = np.asarray(vector, dtype=float).reshape(3)
    if frame.cid == 0:
        return values
    return values @ frame.basis


def transform_six_dof_to_basic(
    components: npt.NDArray[np.floating],
    frame: CoordinateSystem,
    *,
    cylindrical_position: npt.NDArray[np.floating] | None = None,
) -> npt.NDArray[np.float64]:
    """Map six eigenvector components from ``CD`` into the basic frame."""
    values = np.asarray(components, dtype=float).reshape(6)
    if frame.kind == "cylindrical":
        if cylindrical_position is None:
            raise FormatError(
                f"coordinate system {frame.cid} is cylindrical; eigenvector transform "
                "requires the grid location in that frame"
            )
        radius, theta_deg, _axial = np.asarray(cylindrical_position, dtype=float).reshape(3)
        theta = np.deg2rad(theta_deg)
        dr, dtheta_deg, dz = values[:3]
        dtheta = np.deg2rad(dtheta_deg)
        local = np.array(
            [
                dr * np.cos(theta) - radius * np.sin(theta) * dtheta,
                dr * np.sin(theta) + radius * np.cos(theta) * dtheta,
                dz,
            ],
            dtype=float,
        )
        translation = transform_vector_to_basic(local, frame)
        rotation = transform_vector_to_basic(values[3:], frame)
        return np.concatenate([translation, rotation])
    translation = transform_vector_to_basic(values[:3], frame)
    rotation = transform_vector_to_basic(values[3:], frame)
    return np.concatenate([translation, rotation])


def require_defined_frames(
    frames: npt.NDArray[np.integer],
    defined_ids: set[int],
    *,
    source_name: str | None,
) -> None:
    """Raise when a ``GRID`` names a ``CP``/``CD`` that the file never defined."""
    missing = sorted({int(value) for value in frames.reshape(-1) if int(value) != 0})
    undefined = [cid for cid in missing if cid not in defined_ids]
    if not undefined:
        return
    listed = ", ".join(str(cid) for cid in undefined[:5])
    more = ", ..." if len(undefined) > 5 else ""
    where = f"OP2 file {source_name}" if source_name else "OP2 stream"
    raise FormatError(
        f"{where}: GRID {listed}{more} reference coordinate system(s) the file "
        "does not define through CORD1R/CORD2R/CORD2C"
    )
