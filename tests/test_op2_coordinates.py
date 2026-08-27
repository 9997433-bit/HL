"""Unit tests for OP2 coordinate-system transforms."""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.io.op2_coordinates import (
    resolve_coordinate_systems,
    transform_point_to_basic,
    transform_vector_to_basic,
)


def test_cord2r_rotates_local_x_into_global_y() -> None:
    systems = resolve_coordinate_systems(
        {
            1: (
                0,
                np.array([0.0, 0.0, 0.0]),
                np.array([0.0, 0.0, 1.0]),
                np.array([0.0, 1.0, 0.0]),
                "rectangular",
            )
        },
        {},
        {},
    )
    basic = transform_point_to_basic(np.array([1.0, 0.0, 0.0]), systems[1])
    assert basic == pytest.approx([0.0, 1.0, 0.0])
    vector = transform_vector_to_basic(np.array([1.0, 0.0, 0.0]), systems[1])
    assert vector == pytest.approx([0.0, 1.0, 0.0])


def test_cord2c_maps_radius_and_angle() -> None:
    systems = resolve_coordinate_systems(
        {
            1: (
                0,
                np.array([0.0, 0.0, 0.0]),
                np.array([0.0, 0.0, 1.0]),
                np.array([0.0, 1.0, 0.0]),
                "cylindrical",
            )
        },
        {},
        {},
    )
    basic = transform_point_to_basic(np.array([1.0, 0.0, 0.0]), systems[1], cylindrical=True)
    assert basic == pytest.approx([0.0, 1.0, 0.0], rel=1e-6, abs=1e-6)
