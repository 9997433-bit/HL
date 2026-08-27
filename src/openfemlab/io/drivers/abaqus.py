"""External Abaqus driver stub (Framework seam, MS-9.7)."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from .._common import FormatError

__all__ = [
    "AbaqusRunResult",
    "resolve_abaqus_executable",
    "run_abaqus",
]


@dataclass(frozen=True)
class AbaqusRunResult:
    """Outcome of an Abaqus batch run."""

    exit_code: int
    input_path: str
    work_dir: str
    stdout: str
    stderr: str


def resolve_abaqus_executable(explicit: str | None = None) -> str | None:
    """Return an Abaqus executable path from args or environment."""
    if explicit:
        return explicit
    for key in ("OPENFEMLAB_ABAQUS_EXE", "ABAQUS_EXE", "ABAQUS"):
        value = os.environ.get(key)
        if value:
            return value
    return shutil.which("abaqus") or shutil.which("abq2024")


def run_abaqus(
    input_path: str | PathLike[str],
    *,
    work_dir: str | PathLike[str] | None = None,
    executable: str | None = None,
    job: str | None = None,
    timeout_s: float | None = None,
) -> AbaqusRunResult:
    """Run Abaqus on an input deck when an executable is available."""
    deck = Path(input_path).resolve()
    if not deck.is_file():
        raise FormatError(f"Abaqus input file not found: {deck}")
    exe = resolve_abaqus_executable(executable)
    if exe is None:
        raise FormatError(
            "no Abaqus executable found; set OPENFEMLAB_ABAQUS_EXE or install "
            "an 'abaqus' binary on PATH"
        )
    directory = Path(work_dir).resolve() if work_dir is not None else deck.parent
    directory.mkdir(parents=True, exist_ok=True)
    job_name = job or deck.stem
    completed = subprocess.run(
        [exe, f"job={job_name}", f"input={deck.name}"],
        cwd=str(directory),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    return AbaqusRunResult(
        exit_code=int(completed.returncode),
        input_path=str(deck),
        work_dir=str(directory),
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
