"""Exception hierarchy shared by all OpenFEMLab subpackages."""

from __future__ import annotations

__all__ = [
    "OpenFEMLabError",
    "ModelError",
    "ElementError",
    "SolverError",
    "SolverConvergenceError",
    "MatrixSymmetryError",
    "MatrixDefinitenessError",
    "MissedModesWarning",
    "UpdatingError",
    "UpdatingDivergenceError",
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


class MatrixSymmetryError(SolverError):
    """A system matrix violates the MS-1.1 symmetry tolerance.

    Symmetry is *enforced* by ``A <- (A + A^T)/2`` before factorization, so a
    small asymmetry is harmless; past the tolerance the symmetrization would
    silently solve a different problem than the one handed in, which is what
    this error prevents.

    Attributes
    ----------
    asymmetry:
        ``‖A - A^T‖_max / ‖A‖_max`` actually measured.
    tolerance:
        The relative asymmetry MS-1.1 still accepts.
    """

    def __init__(
        self,
        message: str,
        *,
        asymmetry: float = 0.0,
        tolerance: float = 0.0,
    ) -> None:
        super().__init__(message)
        self.asymmetry = float(asymmetry)
        self.tolerance = float(tolerance)


class MatrixDefinitenessError(SolverError):
    """A system matrix has the wrong inertia for the eigenproblem (MS-1.1).

    Raised for an indefinite mass matrix and for a stiffness matrix whose
    spectrum reaches below the rigid-body noise floor: both make
    ``K phi = lambda M phi`` meaningless rather than merely hard.

    Attributes
    ----------
    eigenvalue:
        The offending eigenvalue, when one was computed.
    floor:
        The noise floor it had to clear.
    """

    def __init__(
        self,
        message: str,
        *,
        eigenvalue: float | None = None,
        floor: float = 0.0,
    ) -> None:
        super().__init__(message)
        self.eigenvalue = None if eigenvalue is None else float(eigenvalue)
        self.floor = float(floor)


class MissedModesWarning(UserWarning):
    """A frequency-window extraction returned fewer modes than the window holds.

    The Sylvester inertia count of MS-1.2 knows how many eigenvalues live in
    ``[f_lo, f_hi]``; when the backend returns fewer, the window is incomplete
    and any completeness argument built on it (effective mass, response
    synthesis) is wrong. A warning rather than an error by default because a
    truncated window is still a usable result, escalated by ``strict=True``.
    """


class UpdatingError(OpenFEMLabError):
    """The model-updating loop cannot proceed."""


class UpdatingDivergenceError(UpdatingError):
    """The updating objective grew over consecutive accepted steps (MS-3.4).

    Attributes
    ----------
    costs:
        The objective values of the accepted steps that triggered the guard,
        oldest first.
    iteration:
        The iteration at which the guard fired.
    """

    def __init__(
        self,
        message: str,
        *,
        costs: object = (),
        iteration: int = 0,
    ) -> None:
        super().__init__(message)
        self.costs: tuple[float, ...] = tuple(float(value) for value in costs)  # type: ignore[union-attr]
        self.iteration = int(iteration)


class OptimizationError(OpenFEMLabError):
    """Ill-posed optimization statement or a failed optimization run."""
