"""External solver drivers."""

from .nastran import NastranRunResult, resolve_nastran_executable, run_nastran

__all__ = [
    "NastranRunResult",
    "resolve_nastran_executable",
    "run_nastran",
]
