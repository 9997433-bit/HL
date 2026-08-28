"""Linear static analysis: solve ``K u = f`` on the free DOFs of a model."""

from __future__ import annotations

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from ..core.assembly import assemble_system
from ..core.results import StaticResult
from ..exceptions import MatrixDefinitenessError, MatrixSymmetryError, SolverError

__all__ = ["StaticSolver", "StaticResult", "SYMMETRY_TOL"]

#: Same symmetry tolerance contract as :mod:`openfemlab.solver.modal`.
SYMMETRY_TOL = 1e-10


class StaticSolver:
    """Assemble ``K``, apply nodal loads and recover the displacement field."""

    def __init__(self, model) -> None:
        self.model = model

    def solve(self) -> StaticResult:
        """Return the static displacement solution of ``self.model``."""
        system = assemble_system(self.model)
        load = self.model.load_vector()
        if system.mpc is not None:
            load = np.asarray(system.mpc.T @ load, dtype=float)
        free = system.free_dofs
        if free.size == 0:
            raise SolverError("model has no free DOFs for a static solve")
        k_ff = system.K[free, :][:, free].tocsr()
        f_f = load[free]
        _check_symmetry(k_ff)
        try:
            u_f = spla.spsolve(k_ff, f_f)
        except Exception as exc:
            raise MatrixDefinitenessError(
                "static solve failed; the stiffness matrix may be singular "
                "(check supports and mechanism modes)"
            ) from exc
        u_f = np.asarray(u_f, dtype=float).reshape(-1)
        displacements = system.expand(u_f)
        return StaticResult(
            displacements,
            load_vector=load,
            free_dofs=free,
            system=system,
            meta={"solver": "openfemlab.solver.static.StaticSolver"},
        )


def _check_symmetry(matrix: sp.csr_matrix) -> None:
    if matrix.shape[0] <= 1:
        return
    defect = float(np.max(np.abs((matrix - matrix.T).toarray())))
    scale = float(np.max(np.abs(matrix.toarray()))) or 1.0
    if defect > SYMMETRY_TOL * scale:
        raise MatrixSymmetryError(
            f"assembled stiffness symmetry defect {defect:.3e} exceeds "
            f"{SYMMETRY_TOL:.1e} * ||K||"
        )
