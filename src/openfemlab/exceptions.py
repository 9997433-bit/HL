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
    "UpdatingDivergenceError",
    "OptimizationError",
    "MPEError",
    "PretestError",
    "MissingDependencyError",
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
    """A system matrix is not symmetric to the MS-1.1 tolerance.

    MS-1.1 lets the solvers *enforce* symmetry by averaging ``(A + Aᵀ)/2``, but
    only once the input is already symmetric up to round-off. A larger defect
    means the caller assembled or imported something the symmetric
    eigenproblem does not describe, so averaging it would silently solve a
    different problem.

    Attributes
    ----------
    matrix:
        Which matrix failed, ``"K"`` or ``"M"``.
    defect:
        ``‖A - Aᵀ‖_max / ‖A‖_max``, the quantity that was compared.
    tolerance:
        The relative tolerance it had to meet.
    """

    def __init__(
        self,
        message: str,
        *,
        matrix: str = "",
        defect: float = 0.0,
        tolerance: float = 0.0,
    ) -> None:
        super().__init__(message)
        self.matrix = str(matrix)
        self.defect = float(defect)
        self.tolerance = float(tolerance)


class MatrixDefinitenessError(SolverError):
    """A system matrix violates the definiteness MS-1.1 requires.

    Raised for a mass matrix that is not positive (semi-)definite and for a
    stiffness matrix whose spectrum reaches below the rigid-body noise floor —
    an unstable model or wrong material data, which must not be reported as a
    set of modes at an imaginary frequency.

    Attributes
    ----------
    matrix:
        Which matrix failed, ``"K"`` or ``"M"``.
    value:
        The offending quantity (the most negative eigenvalue or generalized
        mass found).
    tolerance:
        The floor it had to stay above.
    """

    def __init__(
        self,
        message: str,
        *,
        matrix: str = "",
        value: float = 0.0,
        tolerance: float = 0.0,
    ) -> None:
        super().__init__(message)
        self.matrix = str(matrix)
        self.value = float(value)
        self.tolerance = float(tolerance)


class MissedModesWarning(UserWarning):
    """A frequency window returned fewer modes than the MS-1.2 count says it holds.

    Not an error: the modes that were extracted are still correct eigenpairs,
    and a caller sweeping a band may well want them. But a window presented as
    complete when it is not is how a missed mode reaches a correlation report,
    so the gap is announced rather than left to be noticed downstream.
    Solving with ``strict=True`` turns it into
    :class:`SolverError` instead.
    """


class UpdatingDivergenceError(OpenFEMLabError):
    """The updating loop increased its objective instead of reducing it.

    MS-3.4 lets a run stop, but not run away: a sequence of accepted steps that
    keeps raising ``J`` means the linearization no longer describes the model,
    and continuing would return parameters that are worse than the ones the
    caller started with. The guard aborts instead, and hands back the cost
    history so the caller can see how far the climb went.

    Attributes
    ----------
    costs:
        Objective after every accepted step up to and including the abort.
    iteration:
        The iteration the guard fired on.
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


class MPEError(OpenFEMLabError):
    """Modal parameter extraction cannot proceed (MS-10.5).

    Reserved by the spec-first M9 module (GAP-06) for the typed failures of
    ``openfemlab.mpe``: an empty estimation band, a model order the frequency
    line cannot support, a non-receptance input the caller declined to
    convert, or a stabilization diagram with no fully stable alignment to
    pick from.
    """


class PretestError(OpenFEMLabError):
    """A sensor-placement request that cannot yield an observable test (MS-11).

    Raised when fewer sensors than target modes are requested, or when the
    candidate mode partition is rank deficient — MS-11.2 refuses to return a
    placement on which the target modes cannot be distinguished, rather than
    handing a silently unobservable channel set to the M2/M4 chain.
    """


class MissingDependencyError(OpenFEMLabError, ImportError):
    """An optional dependency behind an adapter seam is not installed.

    Architecture P7 keeps ``meshio`` and ``rich`` out of the hard dependency
    set, so the seams that use them must fail with an install hint rather than
    a bare ``ModuleNotFoundError``. Inheriting from :class:`ImportError` keeps
    the existing ``except ImportError`` call sites working.
    """
