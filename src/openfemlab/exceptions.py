"""Exception hierarchy shared by all OpenFEMLab subpackages."""

from __future__ import annotations

__all__ = [
    "OpenFEMLabError",
    "ModelError",
    "ElementError",
    "SolverError",
    "SolverConvergenceError",
    "OptimizationError",
]


class OpenFEMLabError(Exception):
    """Base class for every error raised by OpenFEMLab."""


class ModelError(OpenFEMLabError):
    """Invalid model definition (unknown nodes, DOFs, duplicate ids, ...)."""


class ElementError(OpenFEMLabError):
    """Invalid element definition or degenerate element geometry."""


class SolverError(OpenFEMLabError):
    """The requested analysis cannot be carried out."""


class SolverConvergenceError(SolverError):
    """An iterative solve did not reach the requested residual tolerance.

    Carries the residuals of the eigenpairs the backend did return, so a caller
    can tell "one stubborn mode" from "the whole subspace is garbage" and pick a
    remedy (tighter ``tol``, more iterations, a different shift, or the dense
    backend) instead of guessing.

    Attributes
    ----------
    residuals:
        Relative residual of every returned eigenpair, in the order they were
        returned (MS-1.2).
    tolerance:
        The tolerance they were required to meet.
    """

    def __init__(
        self,
        message: str,
        *,
        residuals: object = (),
        tolerance: float = 0.0,
    ) -> None:
        super().__init__(message)
        self.residuals: tuple[float, ...] = tuple(float(value) for value in residuals)  # type: ignore[union-attr]
        self.tolerance = float(tolerance)


class OptimizationError(OpenFEMLabError):
    """Ill-posed optimization statement or a failed optimization run."""
