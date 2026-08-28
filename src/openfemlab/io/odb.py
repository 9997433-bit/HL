"""Abaqus ``.odb`` reader: native sidecar NPZ + licence-local extraction."""

from __future__ import annotations

import subprocess
import textwrap
from os import PathLike
from pathlib import Path

import numpy as np

from ._common import FormatError
from .drivers.abaqus import resolve_abaqus_executable
from .external_result import ExternalResult

__all__ = [
    "ODBResult",
    "extract_odb_npz",
    "read_odb",
    "read_odb_npz",
    "sidecar_npz_path",
]

ODBResult = ExternalResult

_SIDEcar_SUFFIX = ".openfemlab.npz"
_FORMAT = "abaqus-odb"


def sidecar_npz_path(source: str | PathLike[str]) -> Path:
    """Return the canonical NPZ cache path for an ODB file."""
    path = Path(source).resolve()
    return path.with_suffix(path.suffix + ".openfemlab.npz")


def read_odb(
    source: str | PathLike[str],
    *,
    step: int = -1,
    frame: int = -1,
    force_extract: bool = False,
) -> ExternalResult:
    """Read nodal ``U`` from an Abaqus ``.odb`` file.

    Resolution order:

    1. Fresh sidecar ``*.odb.openfemlab.npz`` when present and up to date.
    2. Licence-local extraction through ``abaqus python`` when an executable
       is available (writes/refreshes the sidecar).
    3. A path ending in ``.npz`` is treated as a previously extracted archive.
    """
    path = Path(source).resolve()
    if path.suffix.lower() == ".npz":
        return read_odb_npz(path, step=step, frame=frame)
    if not path.is_file():
        raise FormatError(f"ODB file not found: {path}")
    cache = sidecar_npz_path(path)
    if not force_extract and cache.is_file() and cache.stat().st_mtime >= path.stat().st_mtime:
        return read_odb_npz(cache, step=step, frame=frame)
    extract_odb_npz(path, destination=cache, step=step, frame=frame)
    return read_odb_npz(cache, step=step, frame=frame)


def read_odb_npz(
    source: str | PathLike[str],
    *,
    step: int = -1,
    frame: int = -1,
) -> ExternalResult:
    """Read a previously extracted Abaqus ODB archive."""
    path = Path(source).resolve()
    if not path.is_file():
        raise FormatError(f"ODB archive not found: {path}")
    with np.load(path, allow_pickle=True) as archive:
        payload = {key: archive[key] for key in archive.files}
    result = ExternalResult.from_npz(payload)
    selected_step = int(payload.get("step", step))
    selected_frame = int(payload.get("frame", frame))
    if step >= 0 or frame >= 0:
        meta = dict(result.meta)
        meta["requested_step"] = step
        meta["requested_frame"] = frame
        result = ExternalResult(
            node_ids=result.node_ids,
            coordinates=result.coordinates,
            displacements=result.displacements,
            format=result.format,
            meta=meta,
        )
    else:
        meta = dict(result.meta)
        meta.setdefault("step", selected_step)
        meta.setdefault("frame", selected_frame)
        result = ExternalResult(
            node_ids=result.node_ids,
            coordinates=result.coordinates,
            displacements=result.displacements,
            format=result.format,
            meta=meta,
        )
    return result


def extract_odb_npz(
    source: str | PathLike[str],
    *,
    destination: str | PathLike[str] | None = None,
    step: int = -1,
    frame: int = -1,
    executable: str | None = None,
    timeout_s: float | None = None,
) -> Path:
    """Extract ``U`` from ``source`` into an NPZ archive using Abaqus Python."""
    odb_path = Path(source).resolve()
    if not odb_path.is_file():
        raise FormatError(f"ODB file not found: {odb_path}")
    if destination is not None:
        out_path = Path(destination).resolve()
    else:
        out_path = sidecar_npz_path(odb_path)
    exe = resolve_abaqus_executable(executable)
    if exe is None:
        raise FormatError(
            "no Abaqus executable found for ODB extraction; set OPENFEMLAB_ABAQUS_EXE "
            f"or provide a sidecar archive at {out_path}"
        )
    script = _extract_script(
        odb_path=str(odb_path),
        npz_path=str(out_path),
        step=step,
        frame=frame,
    )
    completed = subprocess.run(
        [exe, "python", "-c", script],
        cwd=str(odb_path.parent),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    if completed.returncode != 0:
        raise FormatError(
            "Abaqus ODB extraction failed "
            f"(exit {completed.returncode}): {completed.stderr.strip() or completed.stdout.strip()}"
        )
    if not out_path.is_file():
        raise FormatError(f"Abaqus ODB extraction did not produce {out_path}")
    return out_path


def _extract_script(*, odb_path: str, npz_path: str, step: int, frame: int) -> str:
    return textwrap.dedent(
        f"""
        import numpy as np
        from odbAccess import openOdb

        odb = openOdb(path={odb_path!r})
        steps = list(odb.steps.values())
        step_index = {step} if {step} >= 0 else len(steps) - 1
        step_obj = steps[step_index]
        frames = step_obj.frames
        frame_index = {frame} if {frame} >= 0 else len(frames) - 1
        frame_obj = frames[frame_index]
        u_field = frame_obj.fieldOutputs['U']
        node_ids = []
        coords = []
        values = []
        for value in u_field.values:
            node_ids.append(int(value.nodeLabel))
            coords.append(list(value.instance.nodes[value.nodeLabel].coordinates))
            data = value.data
            if len(data) == 2:
                data = (float(data[0]), float(data[1]), 0.0)
            values.append(list(data))
        odb.close()
        np.savez(
            {npz_path!r},
            format='{_FORMAT}',
            node_ids=np.asarray(node_ids, dtype=np.int64),
            coordinates=np.asarray(coords, dtype=float),
            displacements=np.asarray(values, dtype=float),
            step=np.asarray(step_index, dtype=np.int64),
            frame=np.asarray(frame_index, dtype=np.int64),
            meta=np.asarray([{{'source': {odb_path!r}}}], dtype=object),
        )
        """
    ).strip()
