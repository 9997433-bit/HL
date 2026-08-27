"""External Nastran solver driver (Framework seam, MS-9.7)."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from .._common import FormatError

__all__ = [
    "NastranRunResult",
    "resolve_nastran_executable",
    "run_nastran",
]


@dataclass(frozen=True)
class NastranRunResult:
    """Outcome of a Nastran batch run."""

    exit_code: int
    bdf_path: str
    work_dir: str
    stdout: str
    stderr: str


def resolve_nastran_executable(explicit: str | None = None) -> str | None:
    """Return a Nastran executable path from args or environment."""
    if explicit:
        return explicit
    for key in ("OPENFEMLAB_NASTRAN_EXE", "NASTRAN_EXE", "NASTRAN"):
        value = os.environ.get(key)
        if value:
            return value
    return shutil.which("nastran") or shutil.which("nast")


def run_nastran(
    bdf_path: str | PathLike[str],
    *,
    work_dir: str | PathLike[str] | None = None,
    executable: str | None = None,
    timeout_s: float | None = None,
) -> NastranRunResult:
    """Run Nastran on a BDF file when an executable is available.

    Raises :class:`~openfemlab.io.FormatError` when no solver binary is found.
    The caller is responsible for licence and batch configuration of the
    external solver.
    """
    bdf = Path(bdf_path).resolve()
    if not bdf.is_file():
        raise FormatError(f"BDF file not found: {bdf}")
    exe = resolve_nastran_executable(executable)
    if exe is None:
        raise FormatError(
            "no Nastran executable found; set OPENFEMLAB_NASTRAN_EXE or install "
            "a 'nastran' binary on PATH"
        )
    directory = Path(work_dir).resolve() if work_dir is not None else bdf.parent
    directory.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [exe, str(bdf.name)],
        cwd=str(directory),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    return NastranRunResult(
        exit_code=int(completed.returncode),
        bdf_path=str(bdf),
        work_dir=str(directory),
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
