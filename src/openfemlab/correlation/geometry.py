"""Rigid geometry alignment between FE nodes and test sensor coordinates (MS-2.1).

Maps accelerometer positions onto model nodes through a rigid transform
(translation + rotation) and a nearest-node query with a distance gate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from openfemlab.mesh import nearest_nodes

__all__ = [
    "GeometryAlignment",
    "apply_rigid_transform",
    "estimate_rigid_transform",
    "map_sensors_to_nodes",
    "rotation_matrix_to_euler_xyz_deg",
]


@dataclass(frozen=True)
class GeometryAlignment:
    """Outcome of mapping test sensor coordinates onto FE node indices."""

    node_indices: npt.NDArray[np.intp]
    distances: npt.NDArray[np.float64]
    rotation: npt.NDArray[np.float64]
    translation: npt.NDArray[np.float64]
    euler_xyz_deg: npt.NDArray[np.float64]
    matched_mask: npt.NDArray[np.bool_]

    def as_meta(self) -> dict[str, object]:
        """JSON-ready rigid-transform metadata for ``TestData.meta``."""
        return {
            "rotation_matrix": self.rotation.tolist(),
            "translation": self.translation.tolist(),
            "rotation_euler_xyz_deg": self.euler_xyz_deg.tolist(),
        }


def estimate_rigid_transform(
    source: npt.ArrayLike,
    target: npt.ArrayLike,
) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Estimate rotation ``R`` and translation ``t`` with ``target ≈ R source + t``."""
    src = np.asarray(source, dtype=np.float64)
    tgt = np.asarray(target, dtype=np.float64)
    if src.shape != tgt.shape or src.ndim != 2 or src.shape[1] != 3:
        raise ValueError("source and target must both be (n, 3) coordinate arrays")
    if src.shape[0] < 3:
        raise ValueError("at least three points are required to estimate a rigid transform")
    centroid_src = src.mean(axis=0)
    centroid_tgt = tgt.mean(axis=0)
    centered_src = src - centroid_src
    centered_tgt = tgt - centroid_tgt
    covariance = centered_src.T @ centered_tgt
    left, _, right_transpose = np.linalg.svd(covariance)
    rotation = right_transpose.T @ left.T
    if np.linalg.det(rotation) < 0.0:
        right_transpose[-1, :] *= -1.0
        rotation = right_transpose.T @ left.T
    translation = centroid_tgt - rotation @ centroid_src
    return rotation.astype(np.float64), translation.astype(np.float64)


def apply_rigid_transform(
    points: npt.ArrayLike,
    rotation: npt.ArrayLike,
    translation: npt.ArrayLike,
) -> npt.NDArray[np.float64]:
    """Apply ``R p + t`` to every row of ``points``."""
    coords = np.asarray(points, dtype=np.float64)
    matrix = np.asarray(rotation, dtype=np.float64)
    shift = np.asarray(translation, dtype=np.float64).ravel()
    if coords.ndim != 2 or coords.shape[1] != 3:
        raise ValueError("points must have shape (n, 3)")
    if matrix.shape != (3, 3):
        raise ValueError("rotation must be 3x3")
    if shift.shape != (3,):
        raise ValueError("translation must have length 3")
    return (matrix @ coords.T).T + shift


def rotation_matrix_to_euler_xyz_deg(rotation: npt.ArrayLike) -> npt.NDArray[np.float64]:
    """Intrinsic XYZ (roll-pitch-yaw) Euler angles in degrees from ``R``."""
    matrix = np.asarray(rotation, dtype=np.float64)
    if matrix.shape != (3, 3):
        raise ValueError("rotation must be 3x3")
    sy = float(np.sqrt(matrix[0, 0] ** 2 + matrix[1, 0] ** 2))
    singular = sy < 1e-8
    if not singular:
        roll = np.arctan2(matrix[2, 1], matrix[2, 2])
        pitch = np.arctan2(-matrix[2, 0], sy)
        yaw = np.arctan2(matrix[1, 0], matrix[0, 0])
    else:
        roll = np.arctan2(-matrix[1, 2], matrix[1, 1])
        pitch = np.arctan2(-matrix[2, 0], sy)
        yaw = 0.0
    return np.degrees(np.array([roll, pitch, yaw], dtype=np.float64))


def map_sensors_to_nodes(
    model_coords: npt.ArrayLike,
    sensor_coords: npt.ArrayLike,
    *,
    max_distance: float,
    reference_sensor_coords: npt.ArrayLike | None = None,
    reference_model_coords: npt.ArrayLike | None = None,
) -> GeometryAlignment:
    """Map each sensor position to the nearest FE node after optional rigid fit.

    When ``reference_sensor_coords`` and ``reference_model_coords`` are both
    provided (same length, at least three pairs), a rigid transform is estimated
    from those correspondences and applied to every sensor before nearest-node
    lookup.  Sensors farther than ``max_distance`` from their nearest node are
    marked unmatched in ``matched_mask``.
    """
    model = np.asarray(model_coords, dtype=np.float64)
    sensors = np.asarray(sensor_coords, dtype=np.float64)
    if model.ndim != 2 or model.shape[1] != 3:
        raise ValueError("model_coords must have shape (n_nodes, 3)")
    if sensors.ndim != 2 or sensors.shape[1] != 3:
        raise ValueError("sensor_coords must have shape (n_sensors, 3)")
    if max_distance < 0.0:
        raise ValueError("max_distance must be non-negative")

    if reference_sensor_coords is not None and reference_model_coords is not None:
        rotation, translation = estimate_rigid_transform(
            reference_sensor_coords,
            reference_model_coords,
        )
        transformed = apply_rigid_transform(sensors, rotation, translation)
    else:
        rotation = np.eye(3, dtype=np.float64)
        translation = np.zeros(3, dtype=np.float64)
        transformed = sensors

    indices, distances = nearest_nodes(model, transformed)
    matched = distances <= float(max_distance)
    euler = rotation_matrix_to_euler_xyz_deg(rotation)
    return GeometryAlignment(
        node_indices=indices,
        distances=distances.astype(np.float64, copy=False),
        rotation=rotation,
        translation=translation,
        euler_xyz_deg=euler,
        matched_mask=matched,
    )
