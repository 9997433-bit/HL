"""Gradient interface: analytic Fox-Kapoor route, FD fallback, verification.

Three gradient routes, in order of preference:

1. **Analytic** — when the parametric model exposes assembled matrix
   derivatives (:class:`MatrixDerivativeProvider`, satisfied structurally by
   :class:`~openfemlab.updating.scaling_model.ScalingModel`), frequency
   gradients come from the Fox-Kapoor eigenvalue sensitivity kernel in
   :mod:`openfemlab.updating.sensitivity` — one eigensolve per design point
   instead of one per parameter, and exact for affine ``K(p)``/``M(p)``.
2. **Finite differences** — tracked central differences over the design
   vector via :func:`finite_difference_gradient`; MAC tracking inside
   :func:`~openfemlab.updating.sensitivity.modal_sensitivity` keeps the
   columns meaningful across mode reordering.
3. **Verification** — :func:`check_gradient` compares any analytic gradient
   against central differences and reports the worst relative error; this is
   the AC-OPT-001 gate (relative error <= 1e-6 at seeded feasible points).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import numpy as np

from ..exceptions import OptimizationError
from ..updating.sensitivity import (
    finite_difference_jacobian,
    frequency_sensitivity,
)

__all__ = [
    "MatrixDerivativeProvider",
    "modal_frequency_gradients",
    "translational_mass",
    "mass_gradients",
    "finite_difference_gradient",
    "GradientCheck",
    "check_gradient",
]


@runtime_checkable
class MatrixDerivativeProvider(Protocol):
    """A parametric model that knows its assembled matrix derivatives.

    ``derivatives(names)`` returns one ``dK/dp`` and one ``dM/dp`` matrix per
    requested parameter (``None`` where the parameter does not touch that
    matrix); ``assemble(values)`` returns the system matrices at a parameter
    point.  :class:`~openfemlab.updating.scaling_model.ScalingModel` satisfies
    this protocol; an element-level ``dK/dp`` assembler will provide it for the
    native :class:`~openfemlab.core.model.Model` stack.
    """

    def assemble(
        self, values: Mapping[str, float] | Sequence[float] | np.ndarray
    ) -> tuple[Any, Any]: ...

    def derivatives(
        self, names: Sequence[str] | None = None
    ) -> tuple[list[Any], list[Any]]: ...


def modal_frequency_gradients(
    mode_shapes: np.ndarray,
    eigenvalues: np.ndarray,
    provider: MatrixDerivativeProvider,
    names: Sequence[str],
) -> np.ndarray:
    """Analytic ``df/dp`` [Hz] via Fox-Kapoor, shape ``(n_modes, len(names))``.

    ``mode_shapes`` must be the mass-normalised eigenvectors of the *full*
    model (the spaces of ``phi`` and ``dK/dp`` must match).  Delegates to the
    shared kernel in :mod:`openfemlab.updating.sensitivity`, keeping updating
    and optimization on one implementation (spec MS-6).
    """
    dK, dM = provider.derivatives(names)
    return frequency_sensitivity(mode_shapes, eigenvalues, dK, dM)


def translational_mass(mass_matrix: Any, dof_types: np.ndarray | None = None) -> float:
    """Rigid-translation mass ``e^T M e`` averaged over translational directions.

    Without DOF-type information every DOF is treated as translational along a
    single direction (exact for chain/bar models, the Round 1 reference class);
    Round 2 threads :attr:`~openfemlab.core.assembly.AssembledSystem.dof_types`
    through so continuum models mask rotational rows.
    """
    dense_sum = float(np.asarray(mass_matrix.sum()).ravel()[0])
    if dof_types is None:
        return dense_sum
    mask = np.asarray(dof_types) < 3  # UX, UY, UZ per core.model.DOF ordering
    n_directions = max(len(np.unique(np.asarray(dof_types)[mask])), 1)
    M = mass_matrix.tocsr() if hasattr(mass_matrix, "tocsr") else np.asarray(mass_matrix)
    reduced = M[mask][:, mask]
    return float(np.asarray(reduced.sum()).ravel()[0]) / n_directions


def mass_gradients(
    provider: MatrixDerivativeProvider,
    names: Sequence[str],
    dof_types: np.ndarray | None = None,
) -> np.ndarray:
    """Analytic ``dm/dp`` per parameter: total mass of each ``dM/dp`` block.

    Exact for affine mass parameterisations (``dm/dp_j = mass(M_j)``); zero
    for stiffness-only parameters.
    """
    _, dM = provider.derivatives(names)
    out = np.zeros(len(dM))
    for j, dm in enumerate(dM):
        if dm is not None:
            out[j] = translational_mass(dm, dof_types)
    return out


def finite_difference_gradient(
    function: Callable[[np.ndarray], float],
    x: Sequence[float] | np.ndarray,
    steps: Sequence[float] | np.ndarray | float = 1.0e-6,
    scheme: str = "central",
) -> np.ndarray:
    """Finite-difference gradient of a scalar function of the design vector.

    Thin wrapper over the shared
    :func:`~openfemlab.updating.sensitivity.finite_difference_jacobian` for the
    single-response case; the fallback route of the problem compiler.
    """
    jacobian = finite_difference_jacobian(
        lambda p: np.atleast_1d(float(function(p))), x, steps=steps, scheme=scheme
    )
    return jacobian.ravel()


@dataclass
class GradientCheck:
    """Outcome of an analytic-vs-finite-difference gradient comparison."""

    analytic: np.ndarray
    numeric: np.ndarray
    max_relative_error: float
    tolerance: float

    @property
    def passed(self) -> bool:
        return bool(self.max_relative_error <= self.tolerance)

    def __str__(self) -> str:  # pragma: no cover - convenience only
        verdict = "PASS" if self.passed else "FAIL"
        return (
            f"gradient check {verdict}: max relative error "
            f"{self.max_relative_error:.3e} (tolerance {self.tolerance:.1e})"
        )


def check_gradient(
    function: Callable[[np.ndarray], float],
    gradient: Callable[[np.ndarray], np.ndarray],
    x: Sequence[float] | np.ndarray,
    *,
    steps: Sequence[float] | np.ndarray | float = 1.0e-6,
    tolerance: float = 1.0e-6,
) -> GradientCheck:
    """Verify an analytic gradient against central finite differences.

    The AC-OPT-001 acceptance gate: the returned
    :attr:`GradientCheck.max_relative_error` must not exceed ``tolerance``
    (relative to the gradient scale, so zero components are compared
    absolutely against ``tolerance * max(|g|, 1)``).
    """
    x = np.asarray(x, dtype=float).ravel()
    analytic = np.asarray(gradient(x), dtype=float).ravel()
    if analytic.size != x.size:
        raise OptimizationError(
            f"analytic gradient has {analytic.size} entries for {x.size} variables"
        )
    numeric = finite_difference_gradient(function, x, steps=steps, scheme="central")
    scale = max(float(np.max(np.abs(numeric))), float(np.max(np.abs(analytic))), 1.0)
    max_relative_error = float(np.max(np.abs(analytic - numeric))) / scale
    return GradientCheck(
        analytic=analytic,
        numeric=numeric,
        max_relative_error=max_relative_error,
        tolerance=float(tolerance),
    )
