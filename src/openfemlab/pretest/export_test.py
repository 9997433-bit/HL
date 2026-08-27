"""Export reduced test models to UFF with rigid-transform metadata (MS-11.8)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from openfemlab.io.uff import UFFMode, write_uff

if TYPE_CHECKING:
    from openfemlab.core.results import TestData

__all__ = [
    "export_test_model",
    "test_data_to_uff_modes",
    "write_transform_meta",
]


def test_data_to_uff_modes(test_data: TestData) -> list[UFFMode]:
    """Convert a :class:`~openfemlab.core.results.TestData` object to UFF-55 modes."""
    node_ids = np.asarray(test_data.dof_map.node_ids, dtype=np.int64)
    modes: list[UFFMode] = []
    meta_prefix = _meta_id_lines(test_data.meta.get("rigid_transform"))
    for index, frequency in enumerate(test_data.frequencies):
        column = np.asarray(test_data.shapes[:, index])
        if np.iscomplexobj(column):
            values = column.reshape(-1, 1)
        else:
            values = np.real(column).reshape(-1, 1)
        modes.append(
            UFFMode(
                frequency_hz=float(frequency),
                mode_number=index + 1,
                node_ids=node_ids,
                values=values,
                id_lines=meta_prefix,
            )
        )
    return modes


def write_transform_meta(meta: dict[str, object], destination: Path) -> None:
    """Write rigid-transform metadata as JSON alongside a UFF export."""
    path = destination.with_suffix(destination.suffix + ".meta.json")
    path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def export_test_model(
    test_data: TestData,
    destination: str | Path,
    *,
    write_meta: bool = True,
) -> None:
    """Write dataset-55 UFF modes and optional Euler-angle metadata (AC-IO-009)."""
    path = Path(destination)
    modes = test_data_to_uff_modes(test_data)
    write_uff(modes, path)
    transform = test_data.meta.get("rigid_transform")
    if write_meta and isinstance(transform, dict):
        write_transform_meta({"rigid_transform": transform}, path)


def _meta_id_lines(transform: object) -> tuple[str, ...]:
    if not isinstance(transform, dict):
        return ()
    euler = transform.get("rotation_euler_xyz_deg")
    translation = transform.get("translation")
    if euler is None or translation is None:
        return ("OpenFEMLab test export",)
    euler_values = np.asarray(euler, dtype=float).ravel()
    translation_values = np.asarray(translation, dtype=float).ravel()
    if euler_values.size != 3 or translation_values.size != 3:
        return ("OpenFEMLab test export",)
    return (
        "OpenFEMLab test export",
        (
            "EulerXYZdeg="
            f"{euler_values[0]:.6f},{euler_values[1]:.6f},{euler_values[2]:.6f}"
        ),
        (
            "Translation="
            f"{translation_values[0]:.6f},{translation_values[1]:.6f},{translation_values[2]:.6f}"
        ),
    )
