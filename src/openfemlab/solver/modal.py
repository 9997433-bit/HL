"""Normal-mode (real, undamped) eigenvalue analysis.

The generalized symmetric eigenproblem solved here is

    K phi = lambda M phi,      lambda = omega^2,      f = omega / (2 pi)

restricted to the free DOFs of the model. Massless free DOFs (rotations of an
Euler-Bernoulli mesh, interior nodes of a massless bar carrying only point
masses, ...) make ``M`` singular and the eigenproblem ill-posed; they are removed
by exact static (Guyan) condensation, which introduces no approximation because
their inertia is exactly zero, and recovered afterwards from

    u_s = -K_ss^-1 K_sm u_m

The result contract itself lives in :mod:`openfemlab.core.results`; this module
re-exports :class:`~openfemlab.core.results.ModalResult` so that the internal
solver and external importers hand consumers the same object.
"""

from __future__ import annotations

import warnings

import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from ..core.assembly import AssembledSystem, assemble_system
from ..core.results import NORMALIZATIONS, RIGID_BODY_TOL, ModalResult
from ..exceptions import (
    MatrixDefinitenessError,
    MatrixSymmetryError,
    MissedModesWarning,
    SolverConvergenceError,
    SolverError,
)

__all__ = [
    "ModalSolver",
    "ModalResult",
    "NORMALIZATIONS",
    "RIGID_BODY_TOL",
    "RESIDUAL_TOL",
    "SYMMETRY_TOL",
    "INERTIA_CHECK_LIMIT",
    "eigenpair_residuals",
    "eigenvalue_count_below",
    "eigenvalue_count_in_range",
    "residual_floor",
    "validate_symmetry",
]

#: Default MS-1.2 relative-residual tolerance every returned eigenpair must meet.
RESIDUAL_TOL = 1e-8

#: MS-1.1 symmetry tolerance ``‖A - A^T‖_max <= SYMMETRY_TOL * ‖A‖_max``.
SYMMETRY_TOL = 1e-10

#: Reduced problem size up to which the MS-1.2 missed-mode inertia check runs
#: automatically. The check factorizes a dense ``K - sigma M`` twice, so it is
#: only worth its O(n^3) below a size where that is cheap next to the solve.
INERTIA_CHECK_LIMIT = 2000

#: Relative slack on the frequency-window bounds, so a mode sitting exactly on
#: ``f_lo`` or ``f_hi`` is inside the window rather than at the mercy of the
#: last bit of the eigenvalue.
WINDOW_RTOL = 1e-12

#: Relative gap below which two mode components count as tied for the MS-1.3
#: sign rule, so a near-symmetric mode gets the same sign from every backend.
SIGN_TIE_TOL = 1e-8

#: Safety margin over the round-off floor of :func:`residual_floor`; the
#: backward-error bound of a dense LAPACK solve carries a problem-size constant,
#: so the floor is only meaningful up to a factor of this order.
RESIDUAL_ROUNDOFF_FACTOR = 64.0


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
        freq_window: tuple[float, float] | None = None,
        condense_massless: bool = True,
        tol: float = 0.0,
        maxiter: int | None = None,
        residual_tol: float | None = RESIDUAL_TOL,
        missed_mode_check: bool | None = None,
        strict: bool = False,
        seed: int | None = 0,
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
        freq_window:
            MS-1.2 frequency-window request ``(f_lo, f_hi)`` in Hz: only modes
            inside the window are returned, ``num_modes`` acting as a cap on
            how many of them. The dense backend evaluates the whole spectrum
            and is therefore exact; the Lanczos backend shifts to the middle of
            the window so an interior window is reachable at all. Either way
            the count is checked against :func:`eigenvalue_count_in_range`, so
            a truncated window is reported rather than passed off as complete.
        condense_massless:
            Statically condense DOFs with zero mass instead of failing on a
            singular mass matrix.
        tol:
            Convergence tolerance handed to the sparse backend (0 = machine
            precision). It bounds the backend's own error estimate, which is
            why the returned pairs are verified against ``residual_tol`` too.
        maxiter:
            Cap on the sparse backend's Arnoldi restarts. ``None`` leaves the
            ARPACK default; a value too low to converge raises
            :class:`~openfemlab.exceptions.SolverConvergenceError`.
        residual_tol:
            Every returned eigenpair must satisfy the MS-1.2 relative residual
            ``‖K phi - lambda M phi‖ / ‖K phi‖ <= residual_tol``, else
            :class:`~openfemlab.exceptions.SolverConvergenceError` is raised
            carrying the residuals. ``None`` skips the check.
        missed_mode_check:
            Run the MS-1.2 Sylvester inertia check behind a ``freq_window``
            request. ``None`` runs it for reduced problems of at most
            :data:`INERTIA_CHECK_LIMIT` equations and records that it was
            skipped in ``ModalResult.meta`` otherwise.
        strict:
            Escalate the MS-1.2 diagnostic warnings — today the
            :class:`~openfemlab.exceptions.MissedModesWarning` of an incomplete
            frequency window — into
            :class:`~openfemlab.exceptions.SolverError`.
        seed:
            Seeds the Lanczos starting vector, which ARPACK would otherwise
            draw at random — making repeated sparse runs differ in the last
            bits (MS-1.3 and AC-MODAL-005 require bitwise reproducibility).
            ``None`` restores ARPACK's random start.
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

        window = None if freq_window is None else _window_eigenvalues(freq_window)

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
                shift=_window_shift(window) if shift is None and window is not None else shift,
                tol=tol,
                maxiter=maxiter,
                seed=seed,
                cache_factorization=cache_factorization,
            )
        else:
            # A window filters the extraction, so the extraction has to reach
            # into it; the dense backend has the whole spectrum in hand anyway.
            values, vectors = self._solve_dense(
                K_r, M_r, size if window is not None else requested
            )

        values, vectors = _sort_and_clip(values, vectors, K_r, M_r)
        if residual_tol is not None:
            _verify_residuals(K_r, M_r, values, vectors, residual_tol)

        meta: dict[str, object] = {}
        if window is not None:
            values, vectors = _apply_window(values, vectors, window, requested)
            meta = self._window_diagnostics(
                K_r, M_r, window, values.size, missed_mode_check, strict
            )

        if max_frequency is not None:
            limit = (2.0 * np.pi * float(max_frequency)) ** 2
            keep = values <= limit * (1.0 + WINDOW_RTOL)
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
            meta=meta or None,
            system=self.system,
            num_condensed_dofs=0 if transform is None else int(transform.num_condensed),
        )

    def _window_diagnostics(
        self,
        K,
        M,
        window: tuple[float, float],
        found: int,
        missed_mode_check: bool | None,
        strict: bool,
    ) -> dict[str, object]:
        """Compare the window contents against the MS-1.2 inertia count."""
        lower, upper = window
        meta: dict[str, object] = {
            "freq_window_hz": (
                float(np.sqrt(max(lower, 0.0)) / (2.0 * np.pi)),
                float(np.sqrt(max(upper, 0.0)) / (2.0 * np.pi)),
            ),
            "modes_in_window": int(found),
        }
        run = K.shape[0] <= INERTIA_CHECK_LIMIT if missed_mode_check is None else missed_mode_check
        if not run:
            meta["expected_in_window"] = None
            return meta

        expected = eigenvalue_count_in_range(K, M, lower, upper)
        meta["expected_in_window"] = expected
        if found < expected:
            message = (
                f"the frequency window holds {expected} modes but only {found} were "
                f"extracted; raise 'num_modes' (or widen 'maxiter') to complete it"
            )
            if strict:
                raise SolverError(message)
            warnings.warn(message, MissedModesWarning, stacklevel=3)
        return meta

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
        for matrix, name in ((K_ff, "K"), (M_ff, "M")):
            _validate_finite(matrix, name)
            validate_symmetry(matrix, name)
        _validate_mass_definiteness(M_ff)
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
        except np.linalg.LinAlgError as exc:
            raise MatrixDefinitenessError(
                "dense eigensolver failed; the mass matrix is not positive definite"
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
        maxiter: int | None,
        seed: int | None,
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
                maxiter=maxiter,
                v0=None if seed is None else _start_vector(K.shape[0], seed),
            )
        except spla.ArpackNoConvergence as exc:
            partial_values = np.atleast_1d(np.asarray(exc.eigenvalues, dtype=float).ravel())
            partial_vectors = np.asarray(exc.eigenvectors, dtype=float)
            if partial_vectors.ndim != 2 or partial_vectors.shape[1] != partial_values.size:
                partial_values = np.empty(0)
            raise SolverConvergenceError(
                f"the Lanczos backend converged {partial_values.size} of {num_modes} modes "
                f"with sigma={sigma:g}; raise 'maxiter', loosen 'tol' or use sparse=False",
                residuals=eigenpair_residuals(K, M, partial_values, partial_vectors),
                tolerance=tol,
            ) from exc
        except (RuntimeError, ValueError) as exc:
            raise SolverError(
                f"sparse eigensolver failed for {num_modes} modes with sigma={sigma:g}; "
                "try a different 'shift' or sparse=False"
            ) from exc
        return values, vectors


# --------------------------------------------------------------------- helpers


def _start_vector(size: int, seed: int) -> np.ndarray:
    """Reproducible Lanczos start vector; ARPACK draws a random one otherwise."""
    return np.random.default_rng(seed).standard_normal(size)


def _symmetrize(matrix):
    if sp.issparse(matrix):
        return ((matrix + matrix.T) * 0.5).tocsr()
    matrix = np.asarray(matrix, dtype=float)
    return 0.5 * (matrix + matrix.T)


def _to_dense(matrix) -> np.ndarray:
    return matrix.toarray() if sp.issparse(matrix) else np.asarray(matrix, dtype=float)


def validate_symmetry(matrix, name: str, tolerance: float = SYMMETRY_TOL) -> float:
    """Check the MS-1.1 symmetry tolerance and return the relative asymmetry.

    Symmetrization is applied unconditionally afterwards, so this exists to
    stop a matrix that is *not* nearly symmetric from being quietly replaced by
    ``(A + A^T)/2`` — a different problem with a plausible-looking answer.
    """
    difference = matrix - matrix.T
    peak = float(abs(matrix).max()) if matrix.shape[0] else 0.0
    worst = float(abs(difference).max()) if matrix.shape[0] else 0.0
    if peak <= 0.0:
        return 0.0
    asymmetry = worst / peak
    if asymmetry > tolerance:
        raise MatrixSymmetryError(
            f"{name} is not symmetric: ‖{name} - {name}^T‖_max / ‖{name}‖_max = "
            f"{asymmetry:.3e} exceeds {tolerance:.1e}",
            asymmetry=asymmetry,
            tolerance=tolerance,
        )
    return asymmetry


def _validate_finite(matrix, name: str) -> None:
    data = matrix.data if sp.issparse(matrix) else np.asarray(matrix)
    if not np.all(np.isfinite(data)):
        raise SolverError(f"{name} contains NaN or infinite entries")


def _validate_mass_definiteness(M) -> None:
    """Reject the obviously indefinite mass matrices before factorization.

    A negative diagonal entry is enough on its own: ``e_i^T M e_i < 0`` means
    ``M`` is indefinite, whatever the rest of it looks like. The remaining
    cases surface as a failed factorization inside the backend and are mapped
    onto the same error there.
    """
    diagonal = np.asarray(M.diagonal(), dtype=float)
    negative = np.flatnonzero(diagonal < 0.0)
    if negative.size:
        worst = int(negative[np.argmin(diagonal[negative])])
        raise MatrixDefinitenessError(
            f"the mass matrix is indefinite: DOF {worst} has mass "
            f"{diagonal[worst]:.6g} < 0",
            eigenvalue=float(diagonal[worst]),
        )


def _negative_inertia(blocks: np.ndarray, scale: float) -> int:
    """Negative eigenvalues of the block-diagonal factor ``D`` of an LDL^T."""
    zero = 1e-12 * max(scale, 1.0)
    size = blocks.shape[0]
    negatives = 0
    index = 0
    while index < size:
        coupled = index + 1 < size and abs(blocks[index + 1, index]) > zero
        if coupled:
            a, b = blocks[index, index], blocks[index + 1, index + 1]
            off = blocks[index, index + 1]
            determinant = a * b - off * off
            if determinant < -zero * zero:
                negatives += 1  # a saddle: one eigenvalue of each sign
            elif determinant > zero * zero and a + b < 0.0:
                negatives += 2
            index += 2
        else:
            if blocks[index, index] < -zero:
                negatives += 1
            index += 1
    return negatives


def eigenvalue_count_below(K, M, sigma: float) -> int:
    """Number of eigenvalues of ``K phi = lambda M phi`` strictly below ``sigma``.

    Sylvester's law of inertia: with ``M`` positive definite, the count equals
    the number of negative eigenvalues of ``K - sigma M``, which an LDL^T
    factorization reports directly. That is the MS-1.2 missed-mode check —
    it answers "how many modes are down there" without extracting any of them.
    """
    shifted = _to_dense(K) - float(sigma) * _to_dense(M)
    shifted = 0.5 * (shifted + shifted.T)
    scale = float(np.max(np.abs(shifted))) if shifted.size else 0.0
    _, blocks, _ = sla.ldl(shifted)
    return _negative_inertia(blocks, scale)


def eigenvalue_count_in_range(K, M, lower: float, upper: float) -> int:
    """Number of eigenvalues in the half-open ``[lower, upper)``, by two counts.

    A frequency window is closed on both sides, which the solver gets by
    widening the bounds by :data:`WINDOW_RTOL` before calling this — the same
    padding :func:`_apply_window` filters on, so the count and the filter agree
    on a mode sitting exactly on a bound.
    """
    return eigenvalue_count_below(K, M, upper) - eigenvalue_count_below(K, M, lower)


def _window_eigenvalues(freq_window) -> tuple[float, float]:
    """``(lambda_lo, lambda_hi)`` of a ``(f_lo, f_hi)`` request, bounds padded."""
    try:
        low, high = (float(value) for value in freq_window)
    except (TypeError, ValueError) as exc:
        raise SolverError("freq_window must be a (f_lo, f_hi) pair in Hz") from exc
    if low < 0.0 or high < low:
        raise SolverError(f"freq_window must satisfy 0 <= f_lo <= f_hi, got ({low}, {high})")
    lower = (2.0 * np.pi * low) ** 2
    upper = (2.0 * np.pi * high) ** 2
    return lower * (1.0 - WINDOW_RTOL), upper * (1.0 + WINDOW_RTOL)


def _window_shift(window: tuple[float, float]) -> float:
    """Shift-invert target for an interior window: its centre."""
    lower, upper = window
    return 0.5 * (lower + upper)


def _apply_window(values: np.ndarray, vectors: np.ndarray, window, cap: int):
    lower, upper = window
    keep = np.flatnonzero((values >= lower) & (values <= upper))[:cap]
    return values[keep], vectors[:, keep]


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


def _stiffness_to_inertia_scale(K, M) -> float:
    """``tr(K)/tr(M)`` — the eigenvalue scale of the model (MS-1.2)."""
    inertia = float(np.sum(M.diagonal()))
    return float(np.sum(K.diagonal())) / max(inertia, np.finfo(float).tiny)


def _rigid_body_threshold(values: np.ndarray, K, M) -> float:
    """MS-1.2 rigid-body cut ``eps_rigid * max(lambda_max, 1e-9 tr(K)/tr(M))``."""
    scale = float(np.max(np.abs(values))) if values.size else 0.0
    return RIGID_BODY_TOL * max(scale, 1e-9 * abs(_stiffness_to_inertia_scale(K, M)))


def _sort_and_clip(values: np.ndarray, vectors: np.ndarray, K, M):
    """Ascending eigenpairs with the rigid-body eigenvalues set to exactly zero.

    An eigenvalue that is numerically zero comes out of LAPACK/ARPACK as a
    fraction of the round-off floor and with an arbitrary sign, so leaving it
    alone would report a rigid-body mode at some meaningless ``1e-9 Hz``.
    MS-1.2 asks for ``f = 0`` on those modes, which is also what makes the
    reported spectrum agree with ``ModalResult.is_rigid``.

    Below the same floor on the *negative* side the eigenvalue is no longer
    round-off around zero but a genuinely unstable model, and MS-1.1 wants that
    reported as :class:`~openfemlab.exceptions.MatrixDefinitenessError` rather
    than as an imaginary frequency clipped to 0 Hz.
    """
    values = np.asarray(values, dtype=float)
    order = np.argsort(values)
    values = values[order]
    vectors = np.asarray(vectors, dtype=float)[:, order]
    if values.size:
        floor = _rigid_body_threshold(values, K, M)
        if values[0] < -floor:
            raise MatrixDefinitenessError(
                f"eigenvalue {values[0]:.6g} lies below the rigid-body noise floor "
                f"{-floor:.6g}: the stiffness matrix is not positive semi-definite "
                "(unstable model or wrong material data)",
                eigenvalue=float(values[0]),
                floor=float(-floor),
            )
        values = np.where(values <= floor, 0.0, values)
    return values, vectors


def _row_norm(matrix) -> float:
    """``‖A‖_inf`` (largest absolute row sum), dense or sparse."""
    return float(np.asarray(abs(matrix).sum(axis=1)).max())


def _residual_denominators(K, M, values: np.ndarray, vectors: np.ndarray) -> np.ndarray:
    """``‖K phi‖``, except ``lambda_ref ‖M phi‖`` for rigid-body modes (MS-1.2)."""
    rigid = values <= _rigid_body_threshold(values, K, M)
    elastic = np.linalg.norm(K @ vectors, axis=0)
    reference = abs(_stiffness_to_inertia_scale(K, M)) * np.linalg.norm(M @ vectors, axis=0)
    return np.where(rigid, reference, elastic)


def eigenpair_residuals(K, M, eigenvalues, mode_shapes) -> np.ndarray:
    """MS-1.2 relative residual ``‖K phi - lambda M phi‖ / ‖K phi‖`` per eigenpair.

    A rigid-body mode has ``K phi = 0``, so MS-1.2 replaces the denominator
    with ``lambda_ref ‖M phi‖``, ``lambda_ref = tr(K)/tr(M)`` being the
    stiffness-to-inertia scale of the model.
    """
    values = np.asarray(eigenvalues, dtype=float).ravel()
    vectors = np.asarray(mode_shapes, dtype=float)
    if values.size == 0:
        return np.empty(0)
    numerator = np.linalg.norm(K @ vectors - (M @ vectors) * values[None, :], axis=0)
    denominator = _residual_denominators(K, M, values, vectors)
    usable = denominator > 0.0
    return np.where(usable, numerator / np.where(usable, denominator, 1.0), 0.0)


def residual_floor(K, M, eigenvalues, mode_shapes) -> np.ndarray:
    """Smallest :func:`eigenpair_residuals` double precision can deliver.

    A backward-stable eigensolver returns pairs whose *absolute* residual is of
    order ``eps (‖K‖ + lambda ‖M‖) ‖phi‖``. Dividing by the MS-1.2 denominator
    turns that into a relative floor which grows with the spread of the
    spectrum: the lowest mode of a stiff structure simply cannot reach the
    fixed 1e-8 of MS-1.2, so the convergence check is asserted against
    ``max(tol, floor)`` rather than against ``tol`` alone.
    """
    values = np.asarray(eigenvalues, dtype=float).ravel()
    vectors = np.asarray(mode_shapes, dtype=float)
    if values.size == 0:
        return np.empty(0)
    absolute = (
        RESIDUAL_ROUNDOFF_FACTOR
        * np.finfo(float).eps
        * (_row_norm(K) + values * _row_norm(M))
        * np.linalg.norm(vectors, axis=0)
    )
    denominator = _residual_denominators(K, M, values, vectors)
    usable = denominator > 0.0
    return np.where(usable, absolute / np.where(usable, denominator, 1.0), 0.0)


def _verify_residuals(K, M, values: np.ndarray, vectors: np.ndarray, tolerance: float) -> None:
    residuals = eigenpair_residuals(K, M, values, vectors)
    if residuals.size == 0:
        return
    limits = np.maximum(tolerance, residual_floor(K, M, values, vectors))
    exceeded = residuals > limits
    if np.any(exceeded):
        worst = int(np.argmax(residuals / limits))
        raise SolverConvergenceError(
            f"eigenpair {worst + 1} of {residuals.size} has relative residual "
            f"{residuals[worst]:.3e} > {limits[worst]:.3e}; tighten 'tol', raise 'maxiter' "
            "or use sparse=False",
            residuals=residuals,
            tolerance=tolerance,
        )


def _mass_normalize(vectors: np.ndarray, M, normalization: str) -> np.ndarray:
    if vectors.size == 0 or normalization == "none":
        return vectors
    if normalization == "max":
        peaks = np.max(np.abs(vectors), axis=0)
        peaks[peaks == 0.0] = 1.0
        return vectors / peaks
    generalized = np.einsum("ij,ij->j", vectors, M @ vectors)
    if np.any(generalized <= 0.0):
        raise MatrixDefinitenessError(
            "non-positive generalized mass; the mass matrix is not positive definite"
        )
    return vectors / np.sqrt(generalized)


def _fix_signs(vectors: np.ndarray) -> np.ndarray:
    """MS-1.3 sign convention: largest-magnitude component positive.

    Ties go to the lowest DOF index, and "tied" has to mean *nearly* tied: a
    mode with two peaks of equal magnitude and opposite sign (any antisymmetric
    mode of a symmetric structure) never has them bitwise equal, so picking the
    strict argmax lets two backends disagree on the sign of the whole mode over
    a difference in the last few bits.
    """
    if vectors.size == 0:
        return vectors
    magnitudes = np.abs(vectors)
    peaks = np.max(magnitudes, axis=0)
    tied = magnitudes >= peaks * (1.0 - SIGN_TIE_TOL)
    dominant = np.argmax(tied, axis=0)  # first True, i.e. the lowest DOF index
    signs = np.sign(vectors[dominant, np.arange(vectors.shape[1])])
    signs[signs == 0.0] = 1.0
    return vectors * signs
