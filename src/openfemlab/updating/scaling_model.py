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
        self.n_solves = 0

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

    def assemble(self, values: Mapping[str, float] | Sequence[float] | np.ndarray):
        """Return the assembled ``(K(θ), M(θ))``."""
        theta = self._values(values)
        K = self.base_stiffness
        for name, part in self.stiffness_parts.items():
            K = K + theta[name] * part
        M = self.base_mass
        for name, part in self.mass_parts.items():
            M = M + theta[name] * part
        return K, M

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

    def eigen(
        self, values: Mapping[str, float] | Sequence[float] | np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """``(λ, Φ)`` with mass-normalised ``Φ`` over *all* model DOFs."""
        K, M = self.assemble(values)
        self.n_solves += 1

        solver_class = self._solver_class()
        if solver_class is not None:
            result = solver_class.from_matrices(K, M).solve(
                num_modes=self.num_modes, normalization="mass", sparse=False
            )
            return result.eigenvalues, result.mode_shapes

        eigenvalues, vectors = sla.eigh(_dense(K), _dense(M))
        order = np.argsort(eigenvalues)[: self.num_modes]
        eigenvalues = np.clip(eigenvalues[order], 0.0, None)
        return eigenvalues, _fix_signs(vectors[:, order])

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
