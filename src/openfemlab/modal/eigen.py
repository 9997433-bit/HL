"""Solver-independent matrix entry point for modal analysis.

The numerical implementation lives in :mod:`openfemlab.solver.modal`.  This
module only adapts its internal result to the portable
:class:`openfemlab.core.results.ModalResult` contract.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt
from scipy import sparse

from openfemlab.core.dofs import DofMap
from openfemlab.core.results import ModalResult as PortableModalResult
from openfemlab.solver.modal import ModalSolver

__all__ = ["solve_modes"]


def solve_modes(
    k: sparse.spmatrix | npt.NDArray[np.float64],
    m: sparse.spmatrix | npt.NDArray[np.float64],
    dof_map: DofMap,
    n_modes: int = 10,
    sigma: float = 0.0,
    mass_normalize: bool = True,
) -> PortableModalResult:
    """Extract the ``n_modes`` lowest elastic modes of ``(K, M)``.

    Parameters
    ----------
    k, m:
        Symmetric global stiffness and mass matrices, ordered by ``dof_map``.
    dof_map:
        DOF ordering of the matrix rows; attached to the result.
    n_modes:
        Number of modes requested (must be < ndof).
    sigma:
        Shift for shift-invert mode. ``0.0`` targets the lowest modes; for
        free-free structures pass a small negative shift (e.g. ``-1.0``) so
        the factorization of ``K - sigma*M`` stays nonsingular.
    mass_normalize:
        If True, scale each shape to unit modal mass (``φᵀ M φ = 1``);
        eigsh already returns M-orthonormal vectors, this enforces it exactly.

    Returns
    -------
    :class:`~openfemlab.core.results.ModalResult` with frequencies in Hz,
    ascending.
    """
    k = sparse.csr_array(k, dtype=float)
    m = sparse.csr_array(m, dtype=float)
    if k.shape != m.shape or k.shape[0] != k.shape[1]:
        raise ValueError("K and M must be square and of equal shape")
    if k.shape[0] != dof_map.ndof:
        raise ValueError(f"matrix size {k.shape[0]} != dof_map.ndof {dof_map.ndof}")
    if not 0 < n_modes < dof_map.ndof:
        raise ValueError("need 0 < n_modes < ndof")

    result = ModalSolver.from_matrices(k, m).solve(
        num_modes=n_modes,
        normalization="mass" if mass_normalize else "none",
        sparse=True,
        shift=sigma,
    )
    return PortableModalResult(
        frequencies=result.frequencies,
        shapes=result.mode_shapes,
        dof_map=dof_map,
        meta={
            "solver": "openfemlab.ModalSolver",
            "normalization": "mass" if mass_normalize else "none",
            "sigma": sigma,
        },
    )
