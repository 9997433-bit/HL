"""Parametric model whose system matrices are affine in the updating factors.

The common substructuring parameterisation of model updating scales groups of
element matrices::

    K(θ) = K_0 + Σ_j θ_j K_j        M(θ) = M_0 + Σ_j θ_j M_j

Because the assembly is affine, ``∂K/∂θ_j = K_j`` and ``∂M/∂θ_j = M_j`` are
known exactly, which is what makes the analytical Fox & Kapoor sensitivities of
:mod:`openfemlab.updating.sensitivity` usable instead of finite differences:
one eigensolve per iteration rather than one per parameter.

:class:`ScalingModel` is callable, so it plugs straight into
:class:`~openfemlab.updating.updater.ModelUpdater` as the model, and it exposes
matching analytical sensitivities through :meth:`ScalingModel.sensitivity_function`.

Eigenvalue extraction goes through :class:`openfemlab.solver.modal.ModalSolver`
when that solver is importable, and falls back to a direct dense
``scipy.linalg.eigh`` otherwise, so the updating stack stays usable on its own.

Reanalysis
----------
An updating loop re-evaluates the same parameterisation hundreds of times, so
the model is built to make the repeat cheap rather than the first call fast:

* the affine sum is folded once onto a fixed sparsity pattern, after which a new
  ``θ`` only rewrites the CSR ``data`` array — no pattern merge and no
  re-assembly from the contributions (:class:`_AffineTerms`);
* one :class:`~openfemlab.solver.modal.ModalSolver` instance is kept for the
  lifetime of the model, so the DOF partition and label bookkeeping of
  ``from_matrices`` are paid once instead of once per iteration, and the
  solver's ``cache_factorization`` keeps the shift-invert LU alive across
  repeated solves of the same matrices;
* the eigensolution is memoised on ``θ``.  An updating iteration asks for the
  modal data, the frequency sensitivities and the mode-shape sensitivities at
  the same point — three requests, and with the cache one eigensolve.

All three are on by default; ``reanalysis=False`` restores the
assemble-and-solve-from-scratch behaviour, which is what the benchmarks compare
against.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp

from .sensitivity import (
    TWO_PI,
    ModalData,
    frequency_sensitivity,
    mac_sensitivity,
    mode_shape_sensitivity,
)

__all__ = ["ScalingModel"]


def _as_matrix(matrix: Any, size: int | None, name: str) -> Any:
    if sp.issparse(matrix):
        out: Any = matrix.tocsr()
    else:
        out = np.asarray(matrix, dtype=float)
    if out.ndim != 2 or out.shape[0] != out.shape[1]:
        raise ValueError(f"{name} must be square, got shape {out.shape}")
    if size is not None and out.shape[0] != size:
        raise ValueError(f"{name} has size {out.shape[0]} but the model has {size} DOFs")
    return out


def _dense(matrix: Any) -> np.ndarray:
    return matrix.toarray() if sp.issparse(matrix) else np.asarray(matrix, dtype=float)


def _fix_signs(vectors: np.ndarray) -> np.ndarray:
    """Largest-magnitude component positive, ties to the lowest DOF index.

    The same MS-1.3 convention (and the same near-tie tolerance) as
    :mod:`openfemlab.solver.modal`, restated here because the fallback path
    must not depend on the core solver stack.
    """
    if vectors.size == 0:
        return vectors
    magnitudes = np.abs(vectors)
    tied = magnitudes >= np.max(magnitudes, axis=0) * (1.0 - 1e-8)
    dominant = np.argmax(tied, axis=0)
    signs = np.sign(vectors[dominant, np.arange(vectors.shape[1])])
    signs[signs == 0.0] = 1.0
    return vectors * signs


# ------------------------------------------------------------------ reanalysis


def _canonical_csr(matrix: Any) -> sp.csr_matrix:
    """CSR with sorted, duplicate-free indices — what the alignment assumes."""
    out = matrix.tocsr()
    if not out.has_canonical_format:
        out = out.copy()
        out.sum_duplicates()
        out.sort_indices()
    return out


def _entry_keys(indptr: np.ndarray, indices: np.ndarray, num_columns: int) -> np.ndarray:
    """``row * n_cols + col`` per stored entry — increasing for a canonical CSR."""
    counts = np.diff(indptr).astype(np.int64)
    rows = np.repeat(np.arange(counts.size, dtype=np.int64), counts)
    return rows * np.int64(num_columns) + indices.astype(np.int64)


class _AffineTerms:
    """``A(θ) = A_0 + Σ_j θ_j A_j`` evaluated on one fixed sparsity pattern.

    The union of the patterns of ``A_0`` and every ``A_j`` is formed once and
    each term is stored as a ``data`` array laid out on it.  Evaluating a new
    ``θ`` is then a handful of AXPYs over ``nnz`` numbers sharing one set of
    index arrays, where ``A_0 + Σ θ_j A_j`` merges the patterns afresh for every
    term of every call.

    Terms are accumulated in parameter order, one scaled term at a time, which
    is the same sequence of floating-point operations the naive sum performs:
    the fast path is not merely close to it but bitwise equal, so switching the
    reanalysis on cannot move a converged updating run.
    """

    #: Above this DOF count a mixed dense/sparse group is left to the generic
    #: path rather than folded into a dense ``n²`` buffer.
    dense_fold_limit = 2000

    def __init__(
        self, base_data: np.ndarray, part_data: list[np.ndarray], template: Any
    ) -> None:
        self._base_data = base_data
        self._part_data = part_data
        self._template = template

    @classmethod
    def build(cls, base: Any, parts: Sequence[Any], size: int) -> _AffineTerms | None:
        """Fold ``base`` and ``parts``; ``None`` when the group is not foldable."""
        matrices = [base, *parts]
        sparse = [sp.issparse(matrix) for matrix in matrices]
        if all(sparse):
            return cls._build_sparse([_canonical_csr(matrix) for matrix in matrices], size)
        if not any(sparse):
            return cls._build_dense(matrices, size)
        # Mixing the two yields ``numpy.matrix`` from the generic sum anyway, so
        # the fold is also what gives the caller a plain array back. An all-zero
        # sparse term is the default base and costs nothing to densify; a
        # populated one is only worth it while the dense buffer stays small.
        zero_only = all(matrix.nnz == 0 for matrix in matrices if sp.issparse(matrix))
        if not zero_only and size > cls.dense_fold_limit:
            return None
        return cls._build_dense(matrices, size)

    @classmethod
    def _build_sparse(cls, matrices: list[sp.csr_matrix], size: int) -> _AffineTerms:
        # Summing ones keeps the union structural: no entry can cancel, so
        # SciPy cannot prune one out of the result.
        ones = [
            sp.csr_matrix(
                (np.ones(matrix.nnz), matrix.indices, matrix.indptr), shape=(size, size)
            )
            for matrix in matrices
        ]
        union = ones[0]
        for other in ones[1:]:
            union = union + other
        pattern = _canonical_csr(union)
        keys = _entry_keys(pattern.indptr, pattern.indices, size)
        aligned = [cls._align(matrix, keys, size) for matrix in matrices]
        template = sp.csr_matrix(
            (np.zeros(pattern.indices.size), pattern.indices, pattern.indptr),
            shape=(size, size),
        )
        return cls(aligned[0], aligned[1:], template)

    @staticmethod
    def _align(matrix: sp.csr_matrix, union_keys: np.ndarray, size: int) -> np.ndarray:
        """``matrix.data`` scattered onto the union pattern, zero elsewhere."""
        data = np.zeros(union_keys.size, dtype=float)
        if matrix.nnz:
            positions = np.searchsorted(
                union_keys, _entry_keys(matrix.indptr, matrix.indices, size)
            )
            data[positions] = matrix.data
        return data

    @classmethod
    def _build_dense(cls, matrices: Sequence[Any], size: int) -> _AffineTerms:
        flat = [
            np.ascontiguousarray(_dense(matrix), dtype=float).reshape(-1) for matrix in matrices
        ]
        return cls(flat[0], list(flat[1:]), (size, size))

    @property
    def is_sparse(self) -> bool:
        return sp.issparse(self._template)

    @property
    def pattern_size(self) -> int:
        """Entries the shared pattern stores (``n²`` for the dense fold)."""
        return int(self._base_data.size)

    def evaluate(self, coefficients: Sequence[float]) -> Any:
        """``A(θ)``; a fresh matrix over the shared, never-recomputed pattern."""
        data = self._base_data.copy()
        for coefficient, part in zip(coefficients, self._part_data, strict=True):
            data += coefficient * part
        if not self.is_sparse:
            return data.reshape(self._template)
        return sp.csr_matrix(
            (data, self._template.indices, self._template.indptr), shape=self._template.shape
        )


class ScalingModel:
    """FE model parameterised by stiffness and mass scaling factors.

    Parameters
    ----------
    stiffness_parts:
        ``{parameter name: K_j}``; ``K_j`` is the contribution the factor
        scales, i.e. exactly ``∂K/∂θ_j``.
    mass_parts:
        ``{parameter name: M_j}``, same convention.  A name may appear in both
        mappings (one factor scaling a substructure as a whole) or in only one.
    base_stiffness, base_mass:
        The unparameterised remainder ``K_0`` / ``M_0``.  Defaults to zero.
    num_modes:
        How many modes the model reports.  Defaults to every mode; the full set
        is also the superposition basis of the eigenvector sensitivities, so a
        small value trades sensitivity accuracy for speed.
    dof_selection:
        Row indices of the correlation (sensor) DOFs.  Reported mode shapes and
        eigenvector sensitivities are restricted to them, matching what a test
        mode set covers.
    use_solver:
        ``True`` forces :class:`openfemlab.solver.modal.ModalSolver`, ``False``
        forces the local dense fallback, ``None`` (default) prefers the solver
        and falls back when it cannot be imported.
    reanalysis:
        Reuse work across ``θ`` (see the module docstring): the folded affine
        pattern, one solver instance, and the eigensolution cache.  ``False``
        assembles and solves from scratch on every call, which is what a
        cold-start benchmark wants.
    cache_factorization:
        Let the reused solver keep its shift-invert factorization between solves
        of the same matrices.  Ignored when ``reanalysis`` is off, since a
        discarded solver has nothing to reuse.
    sparse:
        Backend the solver should use — ``None`` (default) leaves the choice to
        :class:`~openfemlab.solver.modal.ModalSolver`, which takes the sparse
        shift-invert path only when the problem is large enough to pay for it.
    """

    def __init__(
        self,
        stiffness_parts: Mapping[str, Any] | None = None,
        mass_parts: Mapping[str, Any] | None = None,
        *,
        base_stiffness: Any = None,
        base_mass: Any = None,
        num_modes: int | None = None,
        dof_selection: Sequence[int] | np.ndarray | None = None,
        use_solver: bool | None = None,
        reanalysis: bool = True,
        cache_factorization: bool = True,
        sparse: bool | None = None,
    ) -> None:
        stiffness_parts = dict(stiffness_parts or {})
        mass_parts = dict(mass_parts or {})
        if not stiffness_parts and not mass_parts:
            raise ValueError("a scaling model needs at least one parameterised contribution")

        probe = next(iter({**stiffness_parts, **mass_parts}.values()))
        size = _as_matrix(probe, None, "contribution").shape[0]

        self.stiffness_parts = {
            name: _as_matrix(value, size, f"stiffness part {name!r}")
            for name, value in stiffness_parts.items()
        }
        self.mass_parts = {
            name: _as_matrix(value, size, f"mass part {name!r}")
            for name, value in mass_parts.items()
        }
        zero = sp.csr_matrix((size, size))
        self.base_stiffness = (
            zero if base_stiffness is None else _as_matrix(base_stiffness, size, "base_stiffness")
        )
        self.base_mass = zero if base_mass is None else _as_matrix(base_mass, size, "base_mass")

        # Stable parameter order: stiffness names first, then mass-only names.
        names = list(self.stiffness_parts)
        names += [name for name in self.mass_parts if name not in self.stiffness_parts]
        self.parameter_names = names
        self.num_dofs = size
        self.num_modes = size if num_modes is None else min(int(num_modes), size)
        self.dof_selection = (
            None if dof_selection is None else np.asarray(dof_selection, dtype=int)
        )
        self.use_solver = use_solver
        self.reanalysis = bool(reanalysis)
        self.cache_factorization = bool(cache_factorization)
        self.sparse = sparse

        #: Eigensolves actually performed, i.e. requests that missed the cache.
        self.n_solves = 0
        #: Eigensolutions requested, cache hits included.
        self.n_eigen_calls = 0
        #: Assemblies actually performed, i.e. requests that missed the cache.
        self.n_assemblies = 0

        # The folds accumulate in each group's own order, which is the order the
        # generic sum uses, so the two agree bit for bit.
        self._stiffness_order = list(self.stiffness_parts)
        self._mass_order = list(self.mass_parts)
        self._affine_stiffness = _AffineTerms.build(
            self.base_stiffness, list(self.stiffness_parts.values()), size
        )
        self._affine_mass = _AffineTerms.build(
            self.base_mass, list(self.mass_parts.values()), size
        )
        self._solver: Any = None
        self._solver_key: tuple[float, ...] | None = None
        self._assembly_cache: tuple[tuple[float, ...], Any, Any] | None = None
        self._eigen_cache: tuple[tuple[float, ...], np.ndarray, np.ndarray] | None = None

    # ------------------------------------------------------------- assembly

    def _values(
        self, values: Mapping[str, float] | Sequence[float] | np.ndarray
    ) -> dict[str, float]:
        if isinstance(values, Mapping):
            missing = [name for name in self.parameter_names if name not in values]
            if missing:
                raise KeyError(f"missing values for parameters {missing}")
            return {name: float(values[name]) for name in self.parameter_names}
        array = np.asarray(values, dtype=float).ravel()
        if array.size != len(self.parameter_names):
            raise ValueError(
                f"expected {len(self.parameter_names)} values, got {array.size}"
            )
        return dict(zip(self.parameter_names, array.tolist(), strict=False))

    def clear_cache(self) -> None:
        """Drop the reused solver and everything memoised on ``θ``.

        Needed only after the parameterisation itself is changed in place — the
        caches key on ``θ``, not on the contributions.
        """
        self._solver = None
        self._solver_key = None
        self._assembly_cache = None
        self._eigen_cache = None

    def assemble(self, values: Mapping[str, float] | Sequence[float] | np.ndarray):
        """Return the assembled ``(K(θ), M(θ))``.

        With ``reanalysis`` on the matrices are rebuilt on the pre-folded
        sparsity pattern and the last result is memoised, so repeating a ``θ``
        is free.  The cached pair is handed out as is and must not be modified
        in place.
        """
        theta = self._values(values)
        key = tuple(theta[name] for name in self.parameter_names)
        cached = self._assembly_cache
        if self.reanalysis and cached is not None and cached[0] == key:
            return cached[1], cached[2]

        self.n_assemblies += 1
        K = self._assemble_group(
            self.base_stiffness, self.stiffness_parts, self._stiffness_order,
            self._affine_stiffness, theta,
        )
        M = self._assemble_group(
            self.base_mass, self.mass_parts, self._mass_order, self._affine_mass, theta
        )
        if self.reanalysis:
            self._assembly_cache = (key, K, M)
        return K, M

    def _assemble_group(
        self,
        base: Any,
        parts: Mapping[str, Any],
        order: Sequence[str],
        folded: _AffineTerms | None,
        theta: Mapping[str, float],
    ) -> Any:
        if self.reanalysis and folded is not None:
            return folded.evaluate([theta[name] for name in order])
        matrix = base
        for name in order:
            matrix = matrix + theta[name] * parts[name]
        return matrix

    def derivatives(
        self, names: Sequence[str] | None = None
    ) -> tuple[list[Any | None], list[Any | None]]:
        """``(∂K/∂θ, ∂M/∂θ)`` lists for ``names`` (all parameters by default)."""
        selected = list(self.parameter_names if names is None else names)
        unknown = [name for name in selected if name not in self.parameter_names]
        if unknown:
            raise KeyError(f"unknown parameters {unknown}")
        return (
            [self.stiffness_parts.get(name) for name in selected],
            [self.mass_parts.get(name) for name in selected],
        )

    # -------------------------------------------------------------- solving

    def _solver_class(self):
        if self.use_solver is False:
            return None
        try:
            from ..solver.modal import ModalSolver
        except Exception:  # pragma: no cover - depends on the core stack
            if self.use_solver:
                raise
            return None
        return ModalSolver

    @property
    def modal_solver(self):
        """The reused :class:`~openfemlab.solver.modal.ModalSolver`, if one exists.

        ``None`` until the first solve, and always ``None`` for a model running
        on the dense fallback or with ``reanalysis=False``.
        """
        return self._solver

    def _reused_solver(self, solver_class, K, M, key: tuple[float, ...]):
        """The solver instance to use for ``θ``, built once and then refreshed.

        Rebinding the matrices of the existing instance keeps the DOF partition
        and the label bookkeeping ``from_matrices`` does; the caches it holds
        describe the *old* matrices, so they go.
        """
        if not self.reanalysis:
            return solver_class.from_matrices(K, M)
        if self._solver is None:
            self._solver = solver_class.from_matrices(K, M)
            self._solver_key = key
        elif self._solver_key != key:
            self._solver.system.K = sp.csr_matrix(K)
            self._solver.system.M = sp.csr_matrix(M)
            self._solver.clear_cache()
            self._solver_key = key
        return self._solver

    def eigen(
        self, values: Mapping[str, float] | Sequence[float] | np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """``(λ, Φ)`` with mass-normalised ``Φ`` over *all* model DOFs."""
        theta = self._values(values)
        key = tuple(theta[name] for name in self.parameter_names)
        self.n_eigen_calls += 1

        cached = self._eigen_cache
        if self.reanalysis and cached is not None and cached[0] == key:
            return cached[1].copy(), cached[2].copy()

        K, M = self.assemble(theta)
        self.n_solves += 1

        solver_class = self._solver_class()
        if solver_class is not None:
            solver = self._reused_solver(solver_class, K, M, key)
            result = solver.solve(
                num_modes=self.num_modes,
                normalization="mass",
                sparse=self.sparse,
                cache_factorization=self.cache_factorization and self.reanalysis,
            )
            eigenvalues, shapes = result.eigenvalues, result.mode_shapes
        else:
            eigenvalues, vectors = sla.eigh(_dense(K), _dense(M))
            order = np.argsort(eigenvalues)[: self.num_modes]
            eigenvalues = np.clip(eigenvalues[order], 0.0, None)
            shapes = _fix_signs(vectors[:, order])

        if self.reanalysis:
            self._eigen_cache = (key, eigenvalues, shapes)
            return eigenvalues.copy(), shapes.copy()
        return eigenvalues, shapes

    def _select(self, shapes: np.ndarray) -> np.ndarray:
        return shapes if self.dof_selection is None else shapes[self.dof_selection, :]

    def modal_data(
        self, values: Mapping[str, float] | Sequence[float] | np.ndarray
    ) -> ModalData:
        """Frequencies in Hz and mode shapes restricted to the correlation DOFs."""
        eigenvalues, shapes = self.eigen(values)
        frequencies = np.sqrt(np.clip(eigenvalues, 0.0, None)) / TWO_PI
        return ModalData(frequencies=frequencies, mode_shapes=self._select(shapes))

    def __call__(
        self, values: Mapping[str, float] | Sequence[float] | np.ndarray
    ) -> ModalData:
        return self.modal_data(values)

    # --------------------------------------------------------- sensitivities

    def frequency_sensitivity(
        self,
        values: Mapping[str, float] | Sequence[float] | np.ndarray,
        names: Sequence[str] | None = None,
    ) -> np.ndarray:
        """Analytical ``df/dθ`` in Hz, shape ``(num_modes, len(names))``."""
        eigenvalues, shapes = self.eigen(values)
        dK, dM = self.derivatives(names)
        return frequency_sensitivity(shapes, eigenvalues, dK, dM)

    def mode_shape_sensitivity(
        self,
        values: Mapping[str, float] | Sequence[float] | np.ndarray,
        names: Sequence[str] | None = None,
    ) -> np.ndarray:
        """Analytical ``dΦ/dθ`` on the correlation DOFs.

        Shape ``(len(names), n_correlation_dofs, num_modes)``.
        """
        eigenvalues, shapes = self.eigen(values)
        dK, dM = self.derivatives(names)
        derivatives = mode_shape_sensitivity(shapes, eigenvalues, dK, dM)
        if self.dof_selection is None:
            return derivatives
        return derivatives[:, self.dof_selection, :]

    def mac_sensitivity(
        self,
        values: Mapping[str, float] | Sequence[float] | np.ndarray,
        reference_shapes: np.ndarray,
        names: Sequence[str] | None = None,
        *,
        weights: Sequence[float] | np.ndarray | None = None,
    ) -> np.ndarray:
        """Analytical ``dMAC_ii/dθ`` against ``reference_shapes``.

        ``reference_shapes`` must already be paired column by column with the
        model modes and expressed on the correlation DOFs.
        """
        eigenvalues, shapes = self.eigen(values)
        dK, dM = self.derivatives(names)
        derivatives = mode_shape_sensitivity(shapes, eigenvalues, dK, dM)
        selected = self._select(shapes)
        if self.dof_selection is not None:
            derivatives = derivatives[:, self.dof_selection, :]
        reference = np.asarray(reference_shapes)
        columns = reference.shape[1] if reference.ndim > 1 else 1
        return mac_sensitivity(
            reference,
            selected[:, :columns],
            derivatives[:, :, :columns],
            weights=weights,
        )

    def sensitivity_function(
        self, names: Sequence[str]
    ) -> Callable[[Mapping[str, float], ModalData], np.ndarray]:
        """Adapter for :class:`~openfemlab.updating.updater.ModelUpdater`.

        The returned callable has the ``(parameters, modal_data) -> df/dp``
        signature the updater expects for its analytical Jacobian path.
        """
        selected = list(names)

        def evaluate(parameters: Mapping[str, float], data: ModalData) -> np.ndarray:
            return self.frequency_sensitivity(parameters, selected)

        return evaluate

    def shape_sensitivity_function(
        self, names: Sequence[str]
    ) -> Callable[[Mapping[str, float], ModalData], np.ndarray]:
        """Adapter feeding ``dΦ/dθ`` to the updater's analytical MAC rows.

        Pass it as ``shape_sensitivity_function`` alongside
        :meth:`sensitivity_function` to keep a MAC shape residual off finite
        differences.
        """
        selected = list(names)

        def evaluate(parameters: Mapping[str, float], data: ModalData) -> np.ndarray:
            return self.mode_shape_sensitivity(parameters, selected)

        return evaluate
