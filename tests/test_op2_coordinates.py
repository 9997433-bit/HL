"""Unit tests for OP2 coordinate-system transforms."""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.io.op2_coordinates import (
    RectangularSystem,
    resolve_rectangular_systems,
    transform_point_to_basic,
    transform_vector_to_basic,
)


def test_cord2r_rotates_local_x_into_global_y() -> None:
    raw = {
        1: RectangularSystem(
            cid=1,
            rid=0,
            origin=np.array([0.0, 0.0, 0.0]),
            z_point=np.array([0.0, 0.0, 1.0]),
            xz_point=np.array([0.0, 1.0, 0.0]),
        )
    }
    systems = resolve_rectangular_systems(raw)
    basic = transform_point_to_basic(np.array([1.0, 0.0, 0.0]), systems[1])
    assert basic == pytest.approx([0.0, 1.0, 0.0])
    vector = transform_vector_to_basic(np.array([1.0, 0.0, 0.0]), systems[1])
    assert vector == pytest.approx([0.0, 1.0, 0.0])
