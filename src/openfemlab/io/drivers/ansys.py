"""External Ansys MAPDL driver (Framework seam, MS-9.7)."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from os import PathLike
from pathlib import Path

from .._common import FormatError

__all__ = [
    "AnsysRunResult",
    "ansys_command",
    "resolve_ansys_executable",
    "run_ansys",
]


@dataclass(frozen=True)
class AnsysRunResult:
    """Outcome of an Ansys batch run."""

    exit_code: int
    input_path: str
    work_dir: str
    stdout: str
    stderr: str
    command: tuple[str, ...] = ()


def resolve_ansys_executable(explicit: str | None = None) -> str | None:
    """Return an Ansys executable path from args or environment."""
    if explicit:
        return explicit
    for key in ("OPENFEMLAB_ANSYS_EXE", "ANSYS_EXE", "ANSYS242", "ANSYS"):
        value = os.environ.get(key)
        if value:
            return value
    return shutil.which("ansys") or shutil.which("mapdl")


def ansys_command(
    input_path: str | PathLike[str],
    *,
    executable: str,
) -> tuple[str, ...]:
    """Argv used for a batch Ansys run (deck basename relative to ``cwd``)."""
    deck = Path(input_path)
    return (executable, "-b", "-i", deck.name)


def run_ansys(
    input_path: str | PathLike[str],
    *,
    work_dir: str | PathLike[str] | None = None,
    executable: str | None = None,
    timeout_s: float | None = None,
    dry_run: bool = False,
) -> AnsysRunResult:
    """Run Ansys on an input deck when an executable is available.

    Pass ``dry_run=True`` to validate paths and return the planned command
    without invoking the solver (licence-free CI path).
    """
    deck = Path(input_path).resolve()
    if not deck.is_file():
        raise FormatError(f"Ansys input file not found: {deck}")
    exe = resolve_ansys_executable(executable)
    if exe is None:
        raise FormatError(
            "no Ansys executable found; set OPENFEMLAB_ANSYS_EXE or install "
            "an 'ansys' binary on PATH"
        )
    directory = Path(work_dir).resolve() if work_dir is not None else deck.parent
    directory.mkdir(parents=True, exist_ok=True)
    command = ansys_command(deck, executable=exe)
    if dry_run:
        return AnsysRunResult(
            exit_code=0,
            input_path=str(deck),
            work_dir=str(directory),
            stdout="",
            stderr="",
            command=command,
        )
    completed = subprocess.run(
        list(command),
        cwd=str(directory),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    return AnsysRunResult(
        exit_code=int(completed.returncode),
        input_path=str(deck),
        work_dir=str(directory),
        stdout=completed.stdout,
        stderr=completed.stderr,
        command=command,
    )
