"""Rust assembly kernel spike tests."""

from __future__ import annotations

import numpy as np
import pytest


def test_rust_assembly_extension_round_trips_rod_stiffness() -> None:
    pytest.importorskip("openfemlab_asm")
    import openfemlab_asm

    node_coords = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=float)
    connectivity = np.array([[0, 1]], dtype=np.int64)
    axial = np.array([[210e9 * 1e-4]], dtype=float)
    dof_indices = np.array([[0, 1, 2], [3, 4, 5]], dtype=np.int64)
    rows, cols, data = openfemlab_asm.assemble_rod2_stiffness(
        node_coords, connectivity, axial, dof_indices
    )
    assert rows.size > 0
    assert np.max(np.abs(data)) == pytest.approx(axial[0, 0])
