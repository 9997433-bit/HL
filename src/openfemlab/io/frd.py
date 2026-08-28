"""CalculiX FRD result reader (displacements and mesh coordinates)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from os import PathLike
from pathlib import Path
from typing import TextIO

import numpy as np
import numpy.typing as npt

from ._common import FormatError

__all__ = ["FRDResult", "read_frd"]

_NUMBER = re.compile(
    r"[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[EeDd][+-]?\d+)?"
)


@dataclass(frozen=True, slots=True)
class FRDResult:
    """Static or modal displacements recovered from a CalculiX ``.frd`` file."""

    node_ids: npt.NDArray[np.int64]
    coordinates: npt.NDArray[np.float64]
    displacements: npt.NDArray[np.float64]
    increment: int
    time: float
    meta: dict[str, object]

    @property
    def num_nodes(self) -> int:
        return int(self.node_ids.size)


def read_frd(source: str | PathLike[str] | TextIO) -> FRDResult:
    """Read node coordinates and the last displacement block from a FRD file."""
    text, source_name = _read_text(source)
    node_ids: list[int] = []
    coordinates: list[list[float]] = []
    disp_ids: list[int] = []
    displacements: list[list[float]] = []
    increment = 1
    time = 0.0
    mode = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("2C"):
            parts = line.split()
            if len(parts) >= 3:
                try:
                    increment = int(parts[1])
                    time = float(parts[2])
                except ValueError:
                    pass
            mode = None
            continue
        if line.startswith("-1"):
            tokens = _NUMBER.findall(line[2:])
            if len(tokens) < 4:
                continue
            node_id = int(float(tokens[0]))
            if mode == "disp":
                if len(tokens) >= 7:
                    values = [float(tokens[4]), float(tokens[5]), float(tokens[6])]
                else:
                    values = [float(tokens[1]), float(tokens[2]), float(tokens[3])]
                disp_ids.append(node_id)
                displacements.append(values)
            elif mode == "coord":
                coords = [float(tokens[1]), float(tokens[2]), float(tokens[3])]
                node_ids.append(node_id)
                coordinates.append(coords)
            continue
        if line.startswith("-2"):
            label = line[2:].strip().upper()
            if "DISP" in label:
                mode = "disp"
                disp_ids = []
                displacements = []
            elif "COORD" in label or "NODES" in label:
                mode = "coord"
                node_ids = []
                coordinates = []
            else:
                mode = None
    if not node_ids:
        raise FormatError("FRD file contains no node coordinates")
    if not displacements:
        raise FormatError("FRD file contains no displacement records")
    ids = np.asarray(node_ids, dtype=np.int64)
    coords = np.asarray(coordinates, dtype=float)
    disp_node_ids = np.asarray(disp_ids, dtype=np.int64)
    disp = np.asarray(displacements, dtype=float)
    if disp_node_ids.size != disp.shape[0]:
        raise FormatError("FRD displacement block is incomplete")
    ordered = np.zeros_like(disp)
    index = {node_id: row for row, node_id in enumerate(disp_node_ids)}
    for row, node_id in enumerate(ids):
        if node_id not in index:
            raise FormatError(f"FRD displacement missing node {node_id}")
        ordered[row] = disp[index[node_id]]
    meta: dict[str, object] = {"format": "calculix-frd"}
    if source_name is not None:
        meta["source"] = source_name
    return FRDResult(
        node_ids=ids,
        coordinates=coords,
        displacements=ordered,
        increment=increment,
        time=time,
        meta=meta,
    )


def _read_text(source: str | PathLike[str] | TextIO) -> tuple[str, str | None]:
    if isinstance(source, (str, PathLike)):
        path = Path(source)
        return path.read_text(encoding="utf-8", errors="replace"), str(path)
    value = source.read()
    if not isinstance(value, str):
        raise FormatError("FRD reader requires a text stream")
    name = getattr(source, "name", None)
    return value, str(name) if name is not None else None
