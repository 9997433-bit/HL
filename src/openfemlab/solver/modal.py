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
    "SPARSE_METHODS",
    "SYMMETRY_TOL",
    "INERTIA_CHECK_LIMIT",
    "LOBPCG_BLOCK_PADDING",
    "LOBPCG_MAXITER",
    "WINDOW_RTOL",
    "eigenpair_residuals",
    "eigenvalue_count_below",
    "eigenvalue_count_in_range",
    "residual_floor",
    "symmetry_defect",
]

#: Default MS-1.2 relative-residual tolerance every returned eigenpair must meet.
RESIDUAL_TOL = 1e-8

#: MS-1.1 symmetry tolerance: ``‖A - Aᵀ‖_max <= SYMMETRY_TOL * ‖A‖_max``.
SYMMETRY_TOL = 1e-10

#: Reduced problem size up to which the MS-1.2 missed-mode inertia count runs
#: by default. It factorizes ``K - sigma M`` twice, so it is only worth its
#: O(n^3) while that stays cheap next to the extraction it is checking.
INERTIA_CHECK_LIMIT = 2000

#: Relative slack on the frequency-window bounds, so a mode sitting exactly on
#: ``f_lo`` or ``f_hi`` lands inside the window instead of being decided by the
#: last bit of its eigenvalue.
WINDOW_RTOL = 1e-12

#: Relative gap below which two mode components count as tied for the MS-1.3
#: sign rule, so a near-symmetric mode gets the same sign from every backend.
SIGN_TIE_TOL = 1e-8

#: Safety margin over the round-off floor of :func:`residual_floor`; the
#: backward-error bound of a dense LAPACK solve carries a problem-size constant,
#: so the floor is only meaningful up to a factor of this order.
RESIDUAL_ROUNDOFF_FACTOR = 64.0

#: The sparse backends :meth:`ModalSolver.solve` accepts as ``sparse_method``
#: (MS-1.2). ``"arpack"`` is shift-invert Lanczos and reaches an interior part
#: of the spectrum; ``"lobpcg"`` minimizes the Rayleigh quotient and only ever
#: converges to the lowest modes, but it needs the factorization of
#: ``K - sigma M`` as a preconditioner rather than as a solve per iteration.
SPARSE_METHODS = ("arpack", "lobpcg")

#: Search directions LOBPCG carries beyond the requested modes. A block wider
#: than the wanted subspace is what keeps the iteration from stalling on a
#: cluster of close eigenvalues, at the cost of one more solve per iteration.
LOBPCG_BLOCK_PADDING = 3

#: Iteration cap of one LOBPCG pass when the caller names no ``maxiter``.
#: SciPy's own default of 20 is well below what an unpreconditioned pass needs,
#: and a preconditioned one converges long before this.
LOBPCG_MAXITER = 200

#: The part of SciPy's LOBPCG warning that means "stopped short of the
#: tolerance"; it warns instead of raising, so this is how the pass reports it.
_LOBPCG_NOT_CONVERGED = "not reaching the requested tolerance"


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
        sparse_method: str = "arpack",
        shift: float | None = None,
        max_frequency: float | None = None,
        freq_window: tuple[float, float] | None = None,
        condense_massless: bool = True,
        tol: float = 0.0,
        maxiter: int | None = None,
        residual_tol: float | None = RESIDUAL_TOL,
        definiteness_tol: float | None = RIGID_BODY_TOL,
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
            Force the sparse path or the dense one (``scipy.linalg.eigh``).
            ``None`` picks automatically.
        sparse_method:
            Which sparse backend the sparse path uses, one of
            :data:`SPARSE_METHODS`. ``"arpack"`` is shift-invert Lanczos
            (``scipy.sparse.linalg.eigsh``) and is the only one that can target
            an interior part of the spectrum. ``"lobpcg"``
            (``scipy.sparse.linalg.lobpcg``) minimizes the Rayleigh quotient
            over a block, using the factorization of ``K - sigma M`` as a
            preconditioner instead of solving with it every iteration, so it
            reaches the lowest modes of a problem whose factorization is too
            expensive to apply repeatedly — and only the lowest ones, which is
            why it refuses a ``freq_window`` or a positive ``shift``. Ignored
            on the dense path.
        shift:
            Shift ``sigma`` for the shift-invert spectral transform, in units of
            ``omega^2``. Defaults to a small negative value so that structures
            with rigid-body modes still factorize. LOBPCG uses it only to make
            ``K - sigma M`` definite, so it must not be positive there.
        max_frequency:
            Discard modes above this frequency [Hz].
        freq_window:
            MS-1.2 frequency-window request ``(f_lo, f_hi)`` in Hz. Only modes
            inside the closed window are returned, with ``num_modes`` acting as
            a cap on how many of them. The dense backend evaluates the whole
            spectrum and is therefore exact; the sparse backend shifts to the
            centre of the window so that an interior window is reachable at
            all. Either way the number found is compared against
            :func:`eigenvalue_count_in_range`, so a window the extraction could
            not fill is reported instead of being passed off as complete.
        condense_massless:
            Statically condense DOFs with zero mass instead of failing on a
            singular mass matrix.
        tol:
            Convergence tolerance handed to the sparse backend (0 = let the
            backend decide). It bounds the backend's own error estimate, which
            is why the returned pairs are verified against ``residual_tol``
            too. ARPACK reads it as a relative tolerance on its Ritz
            estimates and 0 as machine precision; LOBPCG stops on the absolute
            residual ``‖K phi - lambda M phi‖`` of mass-normalized modes, and 0
            makes this module derive the absolute bound that matches the
            relative MS-1.2 contract (see :func:`residual_floor`).
        maxiter:
            Cap on the sparse backend's iterations — ARPACK's Arnoldi restarts
            or LOBPCG's iterations per pass. ``None`` leaves the ARPACK default
            and uses :data:`LOBPCG_MAXITER`; a value too low to converge raises
            :class:`~openfemlab.exceptions.SolverConvergenceError`.
        residual_tol:
            Every returned eigenpair must satisfy the MS-1.2 relative residual
            ``‖K phi - lambda M phi‖ / ‖K phi‖ <= residual_tol``, else
            :class:`~openfemlab.exceptions.SolverConvergenceError` is raised
            carrying the residuals. ``None`` skips the check.
        definiteness_tol:
            MS-1.1 noise floor below which a negative eigenvalue is reported as
            :class:`~openfemlab.exceptions.MatrixDefinitenessError` instead of
            being clipped to a rigid-body mode. ``None`` downgrades it to a
            ``RuntimeWarning`` so an unstable spectrum can be inspected.
        missed_mode_check:
            Run the MS-1.2 Sylvester inertia count behind a ``freq_window``
            request. ``None`` runs it for reduced problems of at most
            :data:`INERTIA_CHECK_LIMIT` equations and records
            ``expected_in_window = None`` in ``ModalResult.meta`` otherwise, so
            "not checked" never reads as "checked and complete".
        strict:
            Escalate the MS-1.2 window diagnostics — today the
            :class:`~openfemlab.exceptions.MissedModesWarning` of an incomplete
            frequency window — into
            :class:`~openfemlab.exceptions.SolverError`.
        seed:
            Seeds the Lanczos starting vector, or the LOBPCG starting block,
            which the backends would otherwise draw at random — making repeated
            sparse runs differ in the last bits (MS-1.3 and AC-MODAL-005
            require bitwise reproducibility). ``None`` restores the random
            start.
        cache_factorization:
            Reuse the sparse ``K - shift M`` LU factorization on subsequent
            solves by this solver. Disable when benchmarking cold solves. Call
            :meth:`clear_cache` after mutating matrices in-place.
        """
        if normalization not in NORMALIZATIONS:
            raise SolverError(
                f"unknown normalization {normalization!r}; expected one of {NORMALIZATIONS}"
            )
        if sparse_method not in SPARSE_METHODS:
            raise SolverError(
                f"unknown sparse_method {sparse_method!r}; expected one of {SPARSE_METHODS}"
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
            if sparse_method == "lobpcg" and window is not None:
                raise SolverError(
                    "the LOBPCG backend converges to the lowest modes and cannot target "
                    "the interior of the spectrum a 'freq_window' asks for; use "
                    "sparse_method='arpack' or sparse=False"
                )
            backend = (
                self._solve_sparse_lobpcg
                if sparse_method == "lobpcg"
                else self._solve_sparse_arpack
            )
            values, vectors = backend(
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
            # The window filters the extraction, so the extraction has to reach
            # into it; the dense backend has the whole spectrum in hand anyway.
            values, vectors = self._solve_dense(
                K_r, M_r, size if window is not None else requested
            )

        values, vectors = _sort_and_clip(values, vectors, K_r, M_r, definiteness_tol)
        if residual_tol is not None:
            _verify_residuals(K_r, M_r, values, vectors, residual_tol)

        meta: dict[str, object] = {}
        if window is not None:
            values, vectors = _apply_window(values, vectors, window, requested)
            meta = _window_diagnostics(
                K_r, M_r, window, int(values.size), missed_mode_check, strict
            )

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
            meta=meta or None,
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
        _check_finite(K_ff, "K")
        _check_finite(M_ff, "M")
        _check_symmetry(K_ff, "K")
        _check_symmetry(M_ff, "M")
        _check_mass_definiteness(M_ff)
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
                "the dense eigensolver could not factorize the mass matrix; it is not "
                "positive definite",
                matrix="M",
            ) from exc
        return values[:num_modes], vectors[:, :num_modes]

    def _shifted_inverse(self, K, M, sigma: float, cache_factorization: bool):
        """``(K - sigma M)^-1`` as an operator, from a factorization kept per shift.

        Both sparse backends need it: ARPACK applies it once per Lanczos step
        of the spectral transform, LOBPCG applies it as the preconditioner of
        the shifted pencil. They therefore share one cache entry.
        """

        cache_key = (id(K), id(M), sigma)
        factorization = self._factorizations.get(cache_key) if cache_factorization else None
        if factorization is None:
            factorization = spla.splu(sp.csc_matrix(K - sigma * M))
            if cache_factorization:
                self._factorizations[cache_key] = factorization
        return spla.LinearOperator(
            K.shape,
            matvec=factorization.solve,
            matmat=factorization.solve,
            dtype=float,
        )

    def _solve_sparse_arpack(
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
        try:
            inverse = self._shifted_inverse(K, M, sigma, cache_factorization)
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

    def _solve_sparse_lobpcg(
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
        """MS-1.2 LOBPCG backend: the lowest modes by Rayleigh-quotient descent.

        The iteration runs on the *shifted* pencil ``(K - sigma M, M)`` rather
        than on ``(K, M)``. Both have the same eigenvectors and eigenvalues
        offset by ``sigma``, but with the small negative shift of
        :func:`_default_shift` the shifted stiffness is positive definite even
        for a free-free structure, where the zero eigenvalue of ``K`` otherwise
        makes the Rayleigh-Ritz projection ill-conditioned and LOBPCG either
        stalls or fails outright. The preconditioner is the factorization of
        that same matrix, which is why the shift has to be one ``K - sigma M``
        is definite at.
        """

        sigma = _default_shift(K, M) if shift is None else float(shift)
        if sigma > 0.0:
            raise SolverError(
                f"the LOBPCG backend converges to the lowest modes, so its shift only "
                f"makes K - sigma M definite and must not be positive, got {sigma:g}; "
                "targeting an interior eigenvalue needs sparse_method='arpack'"
            )
        size = K.shape[0]
        iterations = LOBPCG_MAXITER if maxiter is None else int(maxiter)
        try:
            preconditioner = self._shifted_inverse(K, M, sigma, cache_factorization)
        except (RuntimeError, ValueError) as exc:
            raise SolverError(
                f"the LOBPCG preconditioner could not factorize K - sigma M with "
                f"sigma={sigma:g}; try a different 'shift' or sparse=False"
            ) from exc
        shifted = sp.csc_matrix(K - sigma * M)
        mass = sp.csc_matrix(M)
        block = min(size, num_modes + LOBPCG_BLOCK_PADDING)

        values, vectors, converged = _run_lobpcg(
            shifted,
            mass,
            preconditioner,
            _start_block(size, block, seed),
            tol=tol if tol > 0.0 else None,
            maxiter=iterations,
        )
        if tol <= 0.0:
            # SciPy's own default is an absolute bound that scales with the
            # problem size alone, so it meets the relative MS-1.2 contract only
            # by accident. A second pass, warm-started from the first and
            # aimed at the bound the first pass makes computable, does.
            target = _lobpcg_tolerance(
                K, M, values[:num_modes] + sigma, vectors[:, :num_modes]
            )
            values, vectors, converged = _run_lobpcg(
                shifted, mass, preconditioner, vectors, tol=target, maxiter=iterations
            )

        values, vectors = values[:num_modes] + sigma, vectors[:, :num_modes]
        if not converged:
            _reject_unconverged_lobpcg(K, M, values, vectors, iterations, tol)
        return values, vectors


# --------------------------------------------------------------------- helpers


def _start_block(size: int, columns: int, seed: int | None) -> np.ndarray:
    """Reproducible LOBPCG starting block; ``seed=None`` draws a random one."""
    return np.random.default_rng(seed).standard_normal((size, columns))


def _run_lobpcg(A, M, preconditioner, start, *, tol, maxiter):
    """One LOBPCG pass, ascending, plus whether it reached ``tol``.

    SciPy reports a pass that ran out of iterations by warning rather than by
    raising, and warns about the conditioning of its Gram matrices along the
    way. Both are internals of a pass whose tolerance this module derives
    itself, so they are collected here and answered as one flag instead of
    reaching a caller who cannot act on them.
    """

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            values, vectors = spla.lobpcg(
                A, start, B=M, M=preconditioner, largest=False, tol=tol, maxiter=maxiter
            )
        except (np.linalg.LinAlgError, ValueError) as exc:
            raise SolverError(
                f"the LOBPCG backend failed on a block of {start.shape[1]} vectors: "
                f"{exc}; use sparse_method='arpack' or sparse=False"
            ) from exc
    converged = not any(_LOBPCG_NOT_CONVERGED in str(entry.message) for entry in caught)
    values = np.atleast_1d(np.asarray(values, dtype=float).ravel())
    vectors = np.asarray(vectors, dtype=float).reshape(A.shape[0], values.size)
    order = np.argsort(values)
    return values[order], vectors[:, order], converged


def _lobpcg_tolerance(K, M, values: np.ndarray, vectors: np.ndarray) -> float:
    """The absolute LOBPCG bound that delivers the relative MS-1.2 residual.

    LOBPCG stops on ``‖K phi - lambda M phi‖`` itself while MS-1.2 bounds that
    norm *relative* to ``‖K phi‖``, so any fixed absolute tolerance is either
    unreachable or vacuous depending on how stiff the model is. Converting one
    into the other needs the denominators, which is what the first pass is for.
    The bound never goes below the round-off floor of :func:`residual_floor`,
    which no amount of iterating gets under.
    """

    denominators = _residual_denominators(K, M, values, vectors)
    usable = denominators[denominators > 0.0]
    if usable.size == 0:
        return 0.0
    floor = residual_floor(K, M, values, vectors) * denominators
    return float(max(RESIDUAL_TOL * np.min(usable), np.min(floor)))


def _reject_unconverged_lobpcg(K, M, values, vectors, iterations: int, tol: float) -> None:
    """Raise when a LOBPCG pass stopped short *and* the pairs are not usable.

    The tolerance a pass was asked for is this module's own translation of the
    MS-1.2 contract, so falling short of it is only a failure once the pairs
    themselves miss the contract — the same ``max(tol, floor)`` comparison
    :func:`_verify_residuals` makes, run here so that the caller hears about a
    stalled iteration even with ``residual_tol=None``.
    """

    residuals = eigenpair_residuals(K, M, values, vectors)
    if residuals.size == 0:
        return
    limits = np.maximum(RESIDUAL_TOL, residual_floor(K, M, values, vectors))
    if not np.any(residuals > limits):
        return
    raise SolverConvergenceError(
        f"the LOBPCG backend stopped after {iterations} iterations with a largest "
        f"relative residual of {float(np.max(residuals)):.3e}; raise 'maxiter', loosen "
        "'tol' or use sparse_method='arpack'",
        residuals=residuals,
        tolerance=tol,
    )


def _start_vector(size: int, seed: int) -> np.ndarray:
    """Reproducible Lanczos start vector; ARPACK draws a random one otherwise."""
    return np.random.default_rng(seed).standard_normal(size)


def _symmetrize(matrix):
    if sp.issparse(matrix):
        return ((matrix + matrix.T) * 0.5).tocsr()
    matrix = np.asarray(matrix, dtype=float)
    return 0.5 * (matrix + matrix.T)


def _max_abs(matrix) -> float:
    if sp.issparse(matrix):
        return float(abs(matrix).max()) if matrix.nnz else 0.0
    array = np.asarray(matrix, dtype=float)
    return float(np.max(np.abs(array))) if array.size else 0.0


def _check_finite(matrix, name: str) -> None:
    """Reject NaN/inf before LAPACK turns them into a plausible-looking result."""
    data = matrix.data if sp.issparse(matrix) else np.asarray(matrix, dtype=float)
    if not np.all(np.isfinite(data)):
        raise SolverError(
            f"{name} contains non-finite entries (NaN or inf); the eigenproblem is undefined"
        )


def symmetry_defect(matrix) -> float:
    """``‖A - Aᵀ‖_max / ‖A‖_max`` — the MS-1.1 asymmetry measure.

    Zero for an empty or all-zero matrix, so a fully constrained partition does
    not trip the validation on a division by zero.
    """
    scale = _max_abs(matrix)
    if scale == 0.0:
        return 0.0
    return _max_abs(matrix - matrix.T) / scale


def _check_symmetry(matrix, name: str, tolerance: float = SYMMETRY_TOL) -> None:
    """MS-1.1: symmetry is validated before it is enforced by averaging."""
    defect = symmetry_defect(matrix)
    if defect > tolerance:
        raise MatrixSymmetryError(
            f"{name} is not symmetric: ‖{name} - {name}ᵀ‖_max is {defect:.3e} of "
            f"‖{name}‖_max, above the {tolerance:.0e} tolerance of MS-1.1; the "
            "symmetric eigenproblem does not describe this matrix",
            matrix=name,
            defect=defect,
            tolerance=tolerance,
        )


def _check_mass_definiteness(M) -> None:
    """Reject a mass matrix that cannot be positive semi-definite.

    A negative diagonal entry rules out PSD outright and costs O(n) to find, so
    it is caught here with a message that names the DOF. The remaining
    indefinite cases surface as a failed factorization or a non-positive
    generalized mass further down, both of which raise the same error type.
    """
    diagonal = np.asarray(M.diagonal(), dtype=float)
    if diagonal.size == 0:
        return
    worst = int(np.argmin(diagonal))
    if diagonal[worst] < 0.0:
        raise MatrixDefinitenessError(
            f"the mass matrix is not positive semi-definite: free DOF {worst} has "
            f"mass {diagonal[worst]:.6g}",
            matrix="M",
            value=float(diagonal[worst]),
        )


def _to_dense(matrix) -> np.ndarray:
    return matrix.toarray() if sp.issparse(matrix) else np.asarray(matrix, dtype=float)


def _negative_inertia(blocks: np.ndarray, scale: float) -> int:
    """Count the negative eigenvalues of the block-diagonal ``D`` of an LDL^T."""
    zero = 1e-12 * max(scale, 1.0)
    size = blocks.shape[0]
    negatives = 0
    index = 0
    while index < size:
        coupled = index + 1 < size and abs(blocks[index + 1, index]) > zero
        if not coupled:
            if blocks[index, index] < -zero:
                negatives += 1
            index += 1
            continue
        a, b = blocks[index, index], blocks[index + 1, index + 1]
        off = blocks[index, index + 1]
        determinant = a * b - off * off
        if determinant < -zero * zero:
            negatives += 1  # a saddle: one eigenvalue of each sign
        elif determinant > zero * zero and a + b < 0.0:
            negatives += 2
        index += 2
    return negatives


def eigenvalue_count_below(K, M, sigma: float) -> int:
    """Eigenvalues of ``K phi = lambda M phi`` strictly below ``sigma``.

    Sylvester's law of inertia: with ``M`` positive definite the count equals
    the number of negative eigenvalues of ``K - sigma M``, which the block
    diagonal of an LDL^T factorization reports directly. That is what makes the
    MS-1.2 missed-mode guard cheap — it answers "how many modes are down there"
    without extracting any of them.
    """
    shifted = _symmetrize(_to_dense(K) - float(sigma) * _to_dense(M))
    scale = float(np.max(np.abs(shifted))) if shifted.size else 0.0
    _, blocks, _ = sla.ldl(shifted)
    return _negative_inertia(blocks, scale)


def eigenvalue_count_in_range(K, M, lower: float, upper: float) -> int:
    """Eigenvalues in ``[lower, upper)``, as the difference of two inertia counts.

    A frequency window is closed on both sides, which the solver gets by
    widening the bounds by :data:`WINDOW_RTOL` before calling this — the same
    padding :func:`_apply_window` filters on, so the count and the filter agree
    about a mode sitting exactly on a bound.
    """
    return eigenvalue_count_below(K, M, upper) - eigenvalue_count_below(K, M, lower)


def _window_eigenvalues(freq_window) -> tuple[float, float]:
    """``(lambda_lo, lambda_hi)`` of a ``(f_lo, f_hi)`` request, bounds padded."""
    try:
        low, high = (float(value) for value in freq_window)
    except (TypeError, ValueError) as exc:
        raise SolverError("freq_window must be an (f_lo, f_hi) pair in Hz") from exc
    if not (np.isfinite(low) and np.isfinite(high)):
        raise SolverError(f"freq_window bounds must be finite, got ({low}, {high})")
    if low < 0.0 or high < low:
        raise SolverError(f"freq_window must satisfy 0 <= f_lo <= f_hi, got ({low}, {high})")
    lower = (2.0 * np.pi * low) ** 2
    upper = (2.0 * np.pi * high) ** 2
    return lower * (1.0 - WINDOW_RTOL), upper * (1.0 + WINDOW_RTOL)


def _window_shift(window: tuple[float, float]) -> float:
    """Shift-invert target for a window request: its centre."""
    lower, upper = window
    return 0.5 * (lower + upper)


def _apply_window(values: np.ndarray, vectors: np.ndarray, window, cap: int):
    lower, upper = window
    keep = np.flatnonzero((values >= lower) & (values <= upper))[:cap]
    return values[keep], vectors[:, keep]


def _window_diagnostics(
    K,
    M,
    window: tuple[float, float],
    found: int,
    missed_mode_check: bool | None,
    strict: bool,
) -> dict[str, object]:
    """Compare what the window returned against the MS-1.2 inertia count."""
    lower, upper = window
    meta: dict[str, object] = {
        "freq_window_hz": (
            float(np.sqrt(max(lower, 0.0)) / (2.0 * np.pi)),
            float(np.sqrt(max(upper, 0.0)) / (2.0 * np.pi)),
        ),
        "modes_in_window": found,
    }
    if missed_mode_check is None:
        run = K.shape[0] <= INERTIA_CHECK_LIMIT
    else:
        run = bool(missed_mode_check)
    if not run:
        meta["expected_in_window"] = None
        return meta

    expected = eigenvalue_count_in_range(K, M, lower, upper)
    meta["expected_in_window"] = expected
    if found < expected:
        message = (
            f"the frequency window holds {expected} modes but only {found} were "
            f"extracted; raise 'num_modes' (or 'maxiter') to fill it"
        )
        if strict:
            raise SolverError(message)
        warnings.warn(message, MissedModesWarning, stacklevel=4)
    return meta


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


def _sort_and_clip(values: np.ndarray, vectors: np.ndarray, K, M, definiteness_tol):
    """Ascending eigenpairs with the rigid-body eigenvalues set to exactly zero.

    An eigenvalue that is numerically zero comes out of LAPACK/ARPACK as a
    fraction of the round-off floor and with an arbitrary sign, so leaving it
    alone would report a rigid-body mode at some meaningless ``1e-9 Hz``.
    MS-1.2 asks for ``f = 0`` on those modes, which is also what makes the
    reported spectrum agree with ``ModalResult.is_rigid``.

    An eigenvalue *below* that floor is a different matter: ``omega^2 < 0`` is
    an imaginary frequency, so MS-1.1 has it raise
    :class:`~openfemlab.exceptions.MatrixDefinitenessError` rather than be
    clipped away. ``definiteness_tol=None`` downgrades that to a warning for
    callers who want to inspect the unstable spectrum itself.
    """
    values = np.asarray(values, dtype=float)
    order = np.argsort(values)
    values = values[order]
    vectors = np.asarray(vectors, dtype=float)[:, order]
    if values.size:
        floor = _rigid_body_threshold(values, K, M)
        if definiteness_tol is None:
            if values[0] < -1e-6 * max(float(np.max(np.abs(values))), 1.0):
                warnings.warn(
                    "negative eigenvalues encountered: the stiffness matrix is not positive "
                    "semi-definite (unstable model or wrong material data)",
                    RuntimeWarning,
                    stacklevel=3,
                )
        elif values[0] < -abs(definiteness_tol) * max(
            float(np.max(np.abs(values))), abs(_stiffness_to_inertia_scale(K, M)) * 1e-9
        ):
            raise MatrixDefinitenessError(
                f"eigenvalue {values[0]:.6g} is negative beyond the rigid-body noise "
                "floor: the stiffness matrix is not positive semi-definite (unstable "
                "model or wrong material data); pass definiteness_tol=None to inspect "
                "the spectrum anyway",
                matrix="K",
                value=float(values[0]),
                tolerance=float(definiteness_tol),
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
    worst = float(np.min(generalized)) if generalized.size else 1.0
    if worst <= 0.0:
        raise MatrixDefinitenessError(
            f"mode {int(np.argmin(generalized)) + 1} has generalized mass {worst:.6g}; "
            "the mass matrix is not positive definite",
            matrix="M",
            value=worst,
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
