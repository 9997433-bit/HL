"""Normal-mode (real, undamped) eigenvalue analysis.

The generalized symmetric eigenproblem solved here is

    K phi = lambda M phi,      lambda = omega^2,      f = omega / (2 pi)

restricted to the free DOFs of the model. Massless free DOFs (rotations of an
Euler-Bernoulli mesh, interior nodes of a massless bar carrying only point
masses, ...) make ``M`` singular and the eigenproblem ill-posed; they are removed
by exact static (Guyan) condensation, which introduces no approximation because
their inertia is exactly zero, and recovered afterwards from

    u_s = -K_ss^-1 K_sm u_m
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from ..core.assembly import AssembledSystem, assemble_system
from ..core.model import DOF
from ..exceptions import SolverError

__all__ = ["ModalSolver", "ModalResult", "NORMALIZATIONS"]

NORMALIZATIONS = ("mass", "max", "none")

#: Eigenvalues below ``RIGID_BODY_TOL * max(|lambda|)`` are treated as rigid-body modes.
RIGID_BODY_TOL = 1e-8


@dataclass
class ModalResult:
    """Eigenvalues and mode shapes of a :class:`ModalSolver` run.

    Attributes
    ----------
    eigenvalues:
        ``omega^2`` in ascending order (rigid-body modes clipped to exactly 0).
    mode_shapes:
        ``(num_dofs, num_modes)`` array in *full* model DOF space; constrained
        DOFs hold zeros, condensed massless DOFs are recovered statically.
    normalization:
        Which scaling was applied (``"mass"``, ``"max"`` or ``"none"``).
    """

    eigenvalues: np.ndarray
    mode_shapes: np.ndarray
    free_dofs: np.ndarray
    normalization: str = "mass"
    system: AssembledSystem | None = field(default=None, repr=False)
    num_condensed_dofs: int = 0

    # ------------------------------------------------------------- spectrum

    @property
    def num_modes(self) -> int:
        return int(self.eigenvalues.size)

    @property
    def angular_frequencies(self) -> np.ndarray:
        """Circular natural frequencies ``omega`` [rad/s]."""
        return np.sqrt(np.clip(self.eigenvalues, 0.0, None))

    @property
    def frequencies(self) -> np.ndarray:
        """Natural frequencies ``f = omega / (2 pi)`` [Hz]."""
        return self.angular_frequencies / (2.0 * np.pi)

    @property
    def periods(self) -> np.ndarray:
        """Modal periods [s]; ``inf`` for rigid-body modes."""
        with np.errstate(divide="ignore"):
            return np.where(self.frequencies > 0.0, 1.0 / self.frequencies, np.inf)

    @property
    def rigid_body_modes(self) -> np.ndarray:
        """Boolean mask flagging (numerically) zero-frequency modes."""
        scale = float(np.max(np.abs(self.eigenvalues))) if self.num_modes else 0.0
        return self.eigenvalues <= max(RIGID_BODY_TOL * scale, 0.0)

    def mode(self, index: int) -> np.ndarray:
        """Mode shape ``index`` as a full-length DOF vector."""
        return self.mode_shapes[:, index]

    # ------------------------------------------------- generalized quantities

    def _mass_matrix(self):
        if self.system is None:
            raise SolverError("modal result carries no mass matrix; solve from a Model or system")
        return self.system.M

    @property
    def modal_masses(self) -> np.ndarray:
        """Generalized masses ``diag(phi^T M phi)`` (all ones for mass normalization)."""
        M = self._mass_matrix()
        return np.einsum("ij,ij->j", self.mode_shapes, M @ self.mode_shapes)

    @property
    def modal_stiffnesses(self) -> np.ndarray:
        """Generalized stiffnesses ``diag(phi^T K phi) = lambda * modal mass``."""
        if self.system is None:
            raise SolverError("modal result carries no stiffness matrix")
        K = self.system.K
        return np.einsum("ij,ij->j", self.mode_shapes, K @ self.mode_shapes)

    def orthogonality_error(self) -> float:
        """Max off-diagonal magnitude of ``phi^T M phi`` (a solver quality check)."""
        M = self._mass_matrix()
        gram = self.mode_shapes.T @ (M @ self.mode_shapes)
        off = gram - np.diag(np.diag(gram))
        return float(np.max(np.abs(off))) if off.size else 0.0

    def _influence_vector(self, direction: DOF | str | int) -> np.ndarray:
        if self.system is None or self.system.dof_types is None:
            raise SolverError("participation factors need an assembled system with DOF types")
        target = DOF.parse(direction)
        vector = np.zeros(self.system.num_dofs, dtype=float)
        vector[np.asarray(self.system.dof_types) == int(target)] = 1.0
        vector[self.system.constrained_dofs] = 0.0
        return vector

    def participation_factors(self, direction: DOF | str | int = DOF.UX) -> np.ndarray:
        """Modal participation factors ``L_j = phi_j^T M r / (phi_j^T M phi_j)``."""
        M = self._mass_matrix()
        r = self._influence_vector(direction)
        numerator = self.mode_shapes.T @ (M @ r)
        return numerator / self.modal_masses

    def effective_masses(self, direction: DOF | str | int = DOF.UX) -> np.ndarray:
        """Effective modal masses ``L_j^2 * m_j``; they sum to the total mass."""
        factors = self.participation_factors(direction)
        return factors**2 * self.modal_masses

    # ---------------------------------------------------------------- output

    def summary(self, max_rows: int = 20) -> str:
        lines = [
            f"{'mode':>5} {'f [Hz]':>14} {'omega [rad/s]':>16} {'lambda':>16}",
            "-" * 55,
        ]
        for i in range(min(self.num_modes, max_rows)):
            lines.append(
                f"{i + 1:>5} {self.frequencies[i]:>14.6g} "
                f"{self.angular_frequencies[i]:>16.6g} {self.eigenvalues[i]:>16.6g}"
            )
        if self.num_modes > max_rows:
            lines.append(f"... {self.num_modes - max_rows} more modes")
        return "\n".join(lines)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        freqs = np.array2string(self.frequencies[:5], precision=4)
        return f"<ModalResult {self.num_modes} modes, f[Hz]={freqs}>"


class ModalSolver:
    """Solve ``K phi = omega^2 M phi`` for a model or a pair of matrices.

    Examples
    --------
    >>> result = ModalSolver(model).solve(num_modes=5)          # doctest: +SKIP
    >>> result.frequencies                                       # doctest: +SKIP

    Parameters
    ----------
    model:
        A :class:`~openfemlab.core.model.Model`; it is assembled on construction.
    system:
        Alternatively, a pre-assembled :class:`~openfemlab.core.assembly.AssembledSystem`.
    """

    #: Free-DOF count above which the sparse shift-invert path is preferred.
    dense_threshold = 400

    def __init__(
        self,
        model=None,
        *,
        system: AssembledSystem | None = None,
    ) -> None:
        if (model is None) == (system is None):
            raise SolverError("provide exactly one of 'model' or 'system'")
        self.model = model
        self.system = system if system is not None else assemble_system(model)
        if self.system.num_free_dofs == 0:
            raise SolverError("the model has no free DOF: every equation is constrained")
        self._prepared_problems: dict[bool, tuple[object, object, object | None, object]] = {}
        self._factorizations: dict[tuple[int, int, float], object] = {}

    # ---------------------------------------------------------- construction

    @classmethod
    def from_matrices(cls, K, M, *, free_dofs=None, dof_types=None) -> ModalSolver:
        """Build a solver directly from stiffness/mass matrices (test rigs, ROMs)."""
        K = sp.csr_matrix(K, dtype=float)
        M = sp.csr_matrix(M, dtype=float)
        if K.shape != M.shape or K.shape[0] != K.shape[1]:
            raise SolverError(f"K {K.shape} and M {M.shape} must be square and of equal size")
        ndof = K.shape[0]
        if free_dofs is None:
            free = np.arange(ndof, dtype=int)
        else:
            free = np.unique(np.asarray(free_dofs, dtype=int))
        constrained = np.setdiff1d(np.arange(ndof, dtype=int), free)
        system = AssembledSystem(
            K=K,
            M=M,
            free_dofs=free,
            constrained_dofs=constrained,
            dof_labels=[f"dof{i}" for i in range(ndof)],
            dof_types=None if dof_types is None else np.asarray(dof_types, dtype=int),
        )
        return cls(system=system)

    # ----------------------------------------------------------------- solve

    def solve(
        self,
        num_modes: int = 6,
        *,
        normalization: str = "mass",
        sparse: bool | None = None,
        shift: float | None = None,
        max_frequency: float | None = None,
        condense_massless: bool = True,
        tol: float = 0.0,
        cache_factorization: bool = True,
    ) -> ModalResult:
        """Extract the ``num_modes`` lowest normal modes.

        Parameters
        ----------
        num_modes:
            Number of modes requested; silently capped at the number of
            available (post-condensation) equations.
        normalization:
            ``"mass"`` gives ``phi^T M phi = I``, ``"max"`` scales the largest
            absolute component to 1, ``"none"`` leaves the solver output as is.
        sparse:
            Force the sparse Lanczos (``scipy.sparse.linalg.eigsh``) path or the
            dense one (``scipy.linalg.eigh``). ``None`` picks automatically.
        shift:
            Shift ``sigma`` for the shift-invert spectral transform, in units of
            ``omega^2``. Defaults to a small negative value so that structures
            with rigid-body modes still factorize.
        max_frequency:
            Discard modes above this frequency [Hz].
        condense_massless:
            Statically condense DOFs with zero mass instead of failing on a
            singular mass matrix.
        cache_factorization:
            Reuse the sparse ``K - shift M`` LU factorization on subsequent
            solves by this solver. Disable when benchmarking cold solves. Call
            :meth:`clear_cache` after mutating matrices in-place.
        """
        if normalization not in NORMALIZATIONS:
            raise SolverError(
                f"unknown normalization {normalization!r}; expected one of {NORMALIZATIONS}"
            )
        if num_modes < 1:
            raise SolverError(f"num_modes must be >= 1, got {num_modes}")

        K_r, M_r, transform, M_ff = self._prepare_problem(condense_massless)

        size = K_r.shape[0]
        if size == 0:
            raise SolverError("no DOF carries mass: the eigenproblem is empty")
        requested = min(num_modes, size)

        use_sparse = self._choose_sparse(size, requested) if sparse is None else bool(sparse)
        if use_sparse and requested >= size - 1:
            use_sparse = False  # ARPACK requires k < n - 1 to be reliable

        if use_sparse:
            values, vectors = self._solve_sparse(
                K_r,
                M_r,
                requested,
                shift=shift,
                tol=tol,
                cache_factorization=cache_factorization,
            )
        else:
            values, vectors = self._solve_dense(K_r, M_r, requested)

        values, vectors = _sort_and_clip(values, vectors)

        if max_frequency is not None:
            limit = (2.0 * np.pi * float(max_frequency)) ** 2
            keep = values <= limit * (1.0 + 1e-12)
            values, vectors = values[keep], vectors[:, keep]

        if transform is not None:
            vectors = transform.recover(vectors)
        vectors = _mass_normalize(vectors, M_ff, normalization)
        vectors = _fix_signs(vectors)

        return ModalResult(
            eigenvalues=values,
            mode_shapes=self.system.expand(vectors),
            free_dofs=self.system.free_dofs,
            normalization=normalization,
            system=self.system,
            num_condensed_dofs=0 if transform is None else int(transform.num_condensed),
        )

    def clear_cache(self) -> None:
        """Discard reduced matrices and sparse factorizations cached by this solver."""
        self._prepared_problems.clear()
        self._factorizations.clear()

    @property
    def factorization_cache_size(self) -> int:
        """Number of reusable sparse shift-invert factorizations currently held."""
        return len(self._factorizations)

    def _prepare_problem(self, condense_massless: bool):
        cached = self._prepared_problems.get(condense_massless)
        if cached is not None:
            return cached

        K_ff, M_ff = self.system.reduced()
        K_ff = _symmetrize(K_ff)
        M_ff = _symmetrize(M_ff)
        _, transform = _condense_massless(K_ff, M_ff, enabled=condense_massless)
        if transform is None:
            K_r, M_r = K_ff, M_ff
        else:
            K_r, M_r = transform.reduced_matrices()
        prepared = (K_r, M_r, transform, M_ff)
        self._prepared_problems[condense_massless] = prepared
        return prepared

    # -------------------------------------------------------------- backends

    def _choose_sparse(self, size: int, num_modes: int) -> bool:
        return size > self.dense_threshold and num_modes < size // 4

    @staticmethod
    def _solve_dense(K, M, num_modes: int):
        K_d = K.toarray() if sp.issparse(K) else np.asarray(K, dtype=float)
        M_d = M.toarray() if sp.issparse(M) else np.asarray(M, dtype=float)
        try:
            values, vectors = sla.eigh(K_d, M_d)
        except np.linalg.LinAlgError as exc:  # pragma: no cover - LAPACK dependent
            raise SolverError(
                "dense eigensolver failed; the mass matrix is probably not positive definite"
            ) from exc
        return values[:num_modes], vectors[:, :num_modes]

    def _solve_sparse(
        self,
        K,
        M,
        num_modes: int,
        *,
        shift: float | None,
        tol: float,
        cache_factorization: bool,
    ):
        sigma = _default_shift(K, M) if shift is None else float(shift)
        cache_key = (id(K), id(M), sigma)
        try:
            factorization = self._factorizations.get(cache_key) if cache_factorization else None
            if factorization is None:
                shifted = sp.csc_matrix(K - sigma * M)
                factorization = spla.splu(shifted)
                if cache_factorization:
                    self._factorizations[cache_key] = factorization
            inverse = spla.LinearOperator(
                K.shape,
                matvec=factorization.solve,
                matmat=factorization.solve,
                dtype=float,
            )
            values, vectors = spla.eigsh(
                sp.csc_matrix(K),
                k=num_modes,
                M=sp.csc_matrix(M),
                sigma=sigma,
                which="LM",
                OPinv=inverse,
                tol=tol,
            )
        except (spla.ArpackNoConvergence, RuntimeError, ValueError) as exc:
            raise SolverError(
                f"sparse eigensolver failed for {num_modes} modes with sigma={sigma:g}; "
                "try a different 'shift' or sparse=False"
            ) from exc
        return values, vectors


# --------------------------------------------------------------------- helpers


def _symmetrize(matrix):
    if sp.issparse(matrix):
        return ((matrix + matrix.T) * 0.5).tocsr()
    matrix = np.asarray(matrix, dtype=float)
    return 0.5 * (matrix + matrix.T)


def _default_shift(K, M) -> float:
    """A small negative shift keeps ``K - sigma M`` positive definite for PSD ``K``."""
    k_scale = float(np.max(np.abs(K.diagonal()))) if K.shape[0] else 1.0
    m_scale = float(np.max(np.abs(M.diagonal()))) if M.shape[0] else 1.0
    if m_scale <= 0.0:
        return 0.0
    return -1e-6 * (k_scale / m_scale)


class _MasslessCondensation:
    """Exact static condensation of the zero-mass DOFs of a free-DOF system."""

    def __init__(self, K, M, massful: np.ndarray, massless: np.ndarray) -> None:
        self.K = K
        self.M = M
        self.massful = massful
        self.massless = massless
        self.size = K.shape[0]
        K_ss = K[massless, :][:, massless]
        K_sm = K[massless, :][:, massful]
        dense = self.size <= 800
        K_ss_d = K_ss.toarray() if sp.issparse(K_ss) else np.asarray(K_ss)
        K_sm_d = K_sm.toarray() if sp.issparse(K_sm) else np.asarray(K_sm)
        try:
            if dense:
                self._coupling = -sla.solve(K_ss_d, K_sm_d, assume_a="sym")
            else:
                lu = spla.splu(sp.csc_matrix(K_ss))
                self._coupling = -lu.solve(K_sm_d)
        except (np.linalg.LinAlgError, RuntimeError) as exc:
            raise SolverError(
                "cannot condense the massless DOFs: their stiffness sub-matrix is singular "
                "(the model contains a massless mechanism)"
            ) from exc

    @property
    def num_condensed(self) -> int:
        return int(self.massless.size)

    def reduced_matrices(self):
        K_mm = self.K[self.massful, :][:, self.massful]
        K_ms = self.K[self.massful, :][:, self.massless]
        K_ms_d = K_ms.toarray() if sp.issparse(K_ms) else np.asarray(K_ms)
        K_mm_d = K_mm.toarray() if sp.issparse(K_mm) else np.asarray(K_mm)
        K_red = _symmetrize(K_mm_d + K_ms_d @ self._coupling)
        M_red = self.M[self.massful, :][:, self.massful]
        M_red = M_red.toarray() if sp.issparse(M_red) else np.asarray(M_red)
        return K_red, _symmetrize(M_red)

    def recover(self, vectors: np.ndarray) -> np.ndarray:
        """Expand reduced mode shapes back to the full free-DOF space."""
        full = np.zeros((self.size, vectors.shape[1]), dtype=float)
        full[self.massful, :] = vectors
        full[self.massless, :] = self._coupling @ vectors
        return full


def _condense_massless(K, M, *, enabled: bool):
    row_sums = np.asarray(np.abs(M).sum(axis=1)).reshape(-1)
    massful = np.flatnonzero(row_sums > 0.0)
    massless = np.flatnonzero(row_sums <= 0.0)
    if massless.size == 0:
        return massful, None
    if not enabled:
        raise SolverError(
            f"{massless.size} free DOFs have zero mass, so M is singular; "
            "pass condense_massless=True or add mass to those DOFs"
        )
    if massful.size == 0:
        raise SolverError("no DOF carries mass: the eigenproblem is empty")
    return massful, _MasslessCondensation(K, M, massful, massless)


def _sort_and_clip(values: np.ndarray, vectors: np.ndarray):
    values = np.asarray(values, dtype=float)
    order = np.argsort(values)
    values = values[order]
    vectors = np.asarray(vectors, dtype=float)[:, order]
    if values.size:
        scale = float(np.max(np.abs(values)))
        threshold = -1e-6 * max(scale, 1.0)
        if np.any(values < threshold):
            warnings.warn(
                "negative eigenvalues encountered: the stiffness matrix is not positive "
                "semi-definite (unstable model or wrong material data)",
                RuntimeWarning,
                stacklevel=3,
            )
        values = np.where(values < 0.0, 0.0, values)
    return values, vectors


def _mass_normalize(vectors: np.ndarray, M, normalization: str) -> np.ndarray:
    if vectors.size == 0 or normalization == "none":
        return vectors
    if normalization == "max":
        peaks = np.max(np.abs(vectors), axis=0)
        peaks[peaks == 0.0] = 1.0
        return vectors / peaks
    generalized = np.einsum("ij,ij->j", vectors, M @ vectors)
    if np.any(generalized <= 0.0):
        raise SolverError("non-positive generalized mass; the mass matrix is not positive definite")
    return vectors / np.sqrt(generalized)


def _fix_signs(vectors: np.ndarray) -> np.ndarray:
    """Deterministic sign convention: the largest-magnitude component is positive."""
    if vectors.size == 0:
        return vectors
    dominant = np.argmax(np.abs(vectors), axis=0)
    signs = np.sign(vectors[dominant, np.arange(vectors.shape[1])])
    signs[signs == 0.0] = 1.0
    return vectors * signs
