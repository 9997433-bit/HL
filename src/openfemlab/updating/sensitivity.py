"""Eigenvalue / eigenfrequency sensitivity with respect to updating parameters.

Two complementary routes are provided:

* :func:`eigenvalue_sensitivity` — the analytical (Fox & Kapoor) derivative
  ``dλ_i/dp = φ_i^T (dK/dp - λ_i dM/dp) φ_i / (φ_i^T M φ_i)``, available when
  the assembled parameter-derivative matrices are known.  For a stiffness
  scaling factor ``α_k`` multiplying a substructure matrix ``K_k`` the
  derivative matrix is simply ``K_k`` itself.
* :func:`modal_sensitivity` — a solver-independent finite-difference sensitivity
  that only needs a callable returning frequencies (and optionally mode shapes)
  for a set of parameter values.  Perturbed modes are re-paired to the baseline
  modes with the MAC before differencing, so mode switching and eigenvector
  sign flips do not corrupt the matrix.
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Callable

import numpy as np

from ..correlation.mac import mac as mac_matrix

__all__ = [
    "ModalData",
    "as_modal_data",
    "SensitivityResult",
    "eigenvalue_sensitivity",
    "eigenvalue_to_frequency_sensitivity",
    "finite_difference_jacobian",
    "frequency_sensitivity",
    "mac_sensitivity",
    "modal_sensitivity",
    "mode_shape_sensitivity",
    "relative_sensitivity",
    "track_modes",
]

TWO_PI = 2.0 * np.pi


@dataclass
class ModalData:
    """Normal modes of a model: frequencies in Hz and optional mode shapes."""

    frequencies: np.ndarray
    mode_shapes: np.ndarray | None = None

    def __post_init__(self) -> None:
        self.frequencies = np.asarray(self.frequencies, dtype=float).ravel()
        if self.mode_shapes is not None:
            shapes = np.asarray(self.mode_shapes)
            if shapes.ndim == 1:
                shapes = shapes.reshape(-1, 1)
            if shapes.shape[1] != self.frequencies.size:
                raise ValueError(
                    f"mode shape matrix has {shapes.shape[1]} columns but "
                    f"{self.frequencies.size} frequencies were given"
                )
            self.mode_shapes = shapes

    @property
    def n_modes(self) -> int:
        return int(self.frequencies.size)

    @property
    def eigenvalues(self) -> np.ndarray:
        """Eigenvalues ``λ = (2πf)^2`` in ``(rad/s)^2``."""
        return (TWO_PI * self.frequencies) ** 2

    def select(self, indices: Sequence[int] | np.ndarray) -> ModalData:
        idx = np.asarray(indices, dtype=int)
        shapes = None if self.mode_shapes is None else self.mode_shapes[:, idx]
        return ModalData(frequencies=self.frequencies[idx], mode_shapes=shapes)


_FREQUENCY_ATTRIBUTES = ("frequencies", "natural_frequencies", "frequencies_hz", "freqs")
_SHAPE_ATTRIBUTES = ("mode_shapes", "modes", "eigenvectors", "shapes")


def as_modal_data(result: object) -> ModalData:
    """Normalise whatever a modal solver returned into a :class:`ModalData`.

    Accepts a :class:`ModalData`, a ``(frequencies, mode_shapes)`` pair, a
    mapping, a bare frequency array, or any object exposing frequency/mode
    shape attributes.  This keeps the updater usable with third-party solvers.
    """
    if isinstance(result, ModalData):
        return result
    if isinstance(result, Mapping):
        frequencies = next(
            (result[key] for key in _FREQUENCY_ATTRIBUTES if key in result), None
        )
        shapes = next((result[key] for key in _SHAPE_ATTRIBUTES if key in result), None)
        if frequencies is None:
            raise ValueError(f"mapping has no frequency entry (tried {_FREQUENCY_ATTRIBUTES})")
        return ModalData(np.asarray(frequencies, dtype=float), shapes)
    if isinstance(result, tuple) and len(result) == 2:
        return ModalData(np.asarray(result[0], dtype=float), result[1])
    if isinstance(result, (np.ndarray, Sequence)):
        return ModalData(np.asarray(result, dtype=float))

    frequencies = next(
        (getattr(result, name) for name in _FREQUENCY_ATTRIBUTES if hasattr(result, name)),
        None,
    )
    if frequencies is None:
        raise TypeError(f"cannot interpret {type(result).__name__} as modal data")
    shapes = next(
        (getattr(result, name) for name in _SHAPE_ATTRIBUTES if hasattr(result, name)), None
    )
    return ModalData(np.asarray(frequencies, dtype=float), shapes)


def track_modes(reference: ModalData, perturbed: ModalData) -> np.ndarray:
    """Indices reordering ``perturbed`` modes to follow the ``reference`` modes.

    Uses the MAC when both mode shape sets are available, otherwise keeps the
    frequency ordering.  Guarantees a permutation-like index array of length
    ``reference.n_modes`` (entries may repeat only if the perturbed set is
    shorter than the reference set).
    """
    n_reference = reference.n_modes
    n_perturbed = perturbed.n_modes
    if reference.mode_shapes is None or perturbed.mode_shapes is None:
        return np.arange(min(n_reference, n_perturbed))

    macs = mac_matrix(reference.mode_shapes, perturbed.mode_shapes)
    order = np.full(n_reference, -1, dtype=int)
    available = np.ones(n_perturbed, dtype=bool)
    for row in np.argsort(-macs.max(axis=1)):
        candidates = np.where(available, macs[row], -np.inf)
        best = int(np.argmax(candidates))
        if not np.isfinite(candidates[best]):
            continue
        order[row] = best
        available[best] = False
    missing = order < 0
    if missing.any():
        leftovers = list(np.where(available)[0])
        for row in np.where(missing)[0]:
            order[row] = leftovers.pop(0) if leftovers else int(np.argmax(macs[row]))
    return order


@dataclass
class SensitivityResult:
    """Sensitivity matrix of modal responses with respect to parameters."""

    matrix: np.ndarray
    parameter_names: list[str]
    response_labels: list[str]
    parameter_values: np.ndarray | None = None
    response_values: np.ndarray | None = None
    scheme: str = "central"

    @property
    def shape(self) -> tuple[int, int]:
        return self.matrix.shape  # type: ignore[return-value]

    def relative(self) -> np.ndarray:
        """Dimensionless sensitivities ``(p / r) * dr/dp``."""
        if self.parameter_values is None or self.response_values is None:
            raise ValueError("relative sensitivities need parameter and response values")
        return relative_sensitivity(self.matrix, self.parameter_values, self.response_values)

    def table(self) -> str:
        header = f"{'response':<16}" + "".join(f"{name:>14}" for name in self.parameter_names)
        lines = [header, "-" * len(header)]
        for label, row in zip(self.response_labels, self.matrix):
            lines.append(f"{label:<16}" + "".join(f"{value:14.6g}" for value in row))
        return "\n".join(lines)


def relative_sensitivity(
    matrix: np.ndarray,
    parameter_values: Sequence[float] | np.ndarray,
    response_values: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Normalise a sensitivity matrix to dimensionless relative sensitivities."""
    matrix = np.asarray(matrix, dtype=float)
    p = np.asarray(parameter_values, dtype=float).ravel()
    r = np.asarray(response_values, dtype=float).ravel()
    if matrix.shape != (r.size, p.size):
        raise ValueError(
            f"sensitivity matrix {matrix.shape} does not match "
            f"{r.size} responses and {p.size} parameters"
        )
    scaled = matrix * p[None, :]
    out = np.zeros_like(scaled)
    nonzero = np.abs(r) > 0.0
    out[nonzero, :] = scaled[nonzero, :] / r[nonzero, None]
    return out


def eigenvalue_sensitivity(
    mode_shapes: np.ndarray,
    eigenvalues: Sequence[float] | np.ndarray,
    stiffness_derivatives: Sequence[np.ndarray | None],
    mass_derivatives: Sequence[np.ndarray | None] | None = None,
    mass_matrix: np.ndarray | None = None,
) -> np.ndarray:
    """Analytical eigenvalue sensitivity (Fox & Kapoor, 1968).

    ``dλ_i/dp_k = φ_i^T (dK/dp_k - λ_i dM/dp_k) φ_i / (φ_i^T M φ_i)``

    Parameters
    ----------
    mode_shapes:
        ``(n_dof, n_modes)`` eigenvectors of the full (unreduced) model.
    eigenvalues:
        ``λ_i = ω_i^2`` matching the mode shape columns.
    stiffness_derivatives:
        One ``dK/dp_k`` matrix per parameter; ``None`` for parameters that do
        not affect the stiffness.  For a factor scaling a substructure matrix
        ``K_k`` this is ``K_k``.
    mass_derivatives:
        Optional ``dM/dp_k`` matrices, same convention.
    mass_matrix:
        Global mass matrix used for normalisation; omit when the mode shapes
        are already mass normalised.

    Returns
    -------
    ``(n_modes, n_parameters)`` sensitivity matrix.
    """
    phi = np.asarray(mode_shapes)
    if phi.ndim == 1:
        phi = phi.reshape(-1, 1)
    lambdas = np.asarray(eigenvalues, dtype=float).ravel()
    if lambdas.size != phi.shape[1]:
        raise ValueError(
            f"{lambdas.size} eigenvalues do not match {phi.shape[1]} mode shape columns"
        )
    dK = list(stiffness_derivatives)
    dM = list(mass_derivatives) if mass_derivatives is not None else [None] * len(dK)
    if len(dM) != len(dK):
        raise ValueError("stiffness and mass derivative lists must have equal length")

    if mass_matrix is None:
        norms = np.ones(phi.shape[1])
    else:
        mass_matrix = np.asarray(mass_matrix, dtype=float)
        norms = np.real(np.einsum("ij,ij->j", phi.conj(), mass_matrix @ phi))
    if np.any(norms <= 0.0):
        raise ValueError("mode shapes must have positive generalised mass")

    sensitivity = np.zeros((phi.shape[1], len(dK)))
    for k, (dk, dm) in enumerate(zip(dK, dM)):
        for i in range(phi.shape[1]):
            vector = phi[:, i]
            value = 0.0
            if dk is not None:
                value += float(np.real(np.vdot(vector, np.asarray(dk) @ vector)))
            if dm is not None:
                value -= lambdas[i] * float(np.real(np.vdot(vector, np.asarray(dm) @ vector)))
            sensitivity[i, k] = value / norms[i]
    return sensitivity


def eigenvalue_to_frequency_sensitivity(
    eigenvalue_sensitivities: np.ndarray,
    frequencies: Sequence[float] | np.ndarray,
) -> np.ndarray:
    """Convert ``dλ/dp`` to ``df/dp`` in Hz using ``λ = (2πf)^2``."""
    matrix = np.asarray(eigenvalue_sensitivities, dtype=float)
    f = np.asarray(frequencies, dtype=float).ravel()
    if matrix.shape[0] != f.size:
        raise ValueError("sensitivity rows must match the number of frequencies")
    factor = np.zeros_like(f)
    nonzero = f > 0.0
    factor[nonzero] = 1.0 / (2.0 * TWO_PI**2 * f[nonzero])
    return matrix * factor[:, None]


def frequency_sensitivity(
    mode_shapes: np.ndarray,
    eigenvalues: Sequence[float] | np.ndarray,
    stiffness_derivatives: Sequence[np.ndarray | None],
    mass_derivatives: Sequence[np.ndarray | None] | None = None,
    mass_matrix: np.ndarray | None = None,
) -> np.ndarray:
    """Analytical ``df/dp`` in Hz for the scaling parameters of ``K`` and ``M``.

    Convenience composition of :func:`eigenvalue_sensitivity` and
    :func:`eigenvalue_to_frequency_sensitivity`.
    """
    lambdas = np.asarray(eigenvalues, dtype=float).ravel()
    dlambda = eigenvalue_sensitivity(
        mode_shapes, lambdas, stiffness_derivatives, mass_derivatives, mass_matrix
    )
    frequencies = np.sqrt(np.clip(lambdas, 0.0, None)) / TWO_PI
    return eigenvalue_to_frequency_sensitivity(dlambda, frequencies)


def mode_shape_sensitivity(
    mode_shapes: np.ndarray,
    eigenvalues: Sequence[float] | np.ndarray,
    stiffness_derivatives: Sequence[np.ndarray | None],
    mass_derivatives: Sequence[np.ndarray | None] | None = None,
    *,
    modes: Sequence[int] | np.ndarray | None = None,
    cluster_tolerance: float = 1.0e-6,
) -> np.ndarray:
    """Eigenvector derivatives by Fox & Kapoor modal superposition.

    ``dφ_i/dp = Σ_{r≠i} [ φ_r^T (dK/dp - λ_i dM/dp) φ_i / (λ_i - λ_r) ] φ_r
    - ½ (φ_i^T dM/dp φ_i) φ_i``

    Parameters
    ----------
    mode_shapes:
        ``(n_dof, n_basis)`` **mass normalised** eigenvectors.  The whole set
        is used as the superposition basis, so a truncated set gives a
        truncated (and biased) derivative — supply as many modes as affordable.
    eigenvalues:
        ``λ_r = ω_r^2`` for every basis mode.
    stiffness_derivatives, mass_derivatives:
        One ``dK/dp_k`` / ``dM/dp_k`` matrix per parameter, ``None`` where the
        parameter does not touch that matrix.
    modes:
        Which modes to differentiate; defaults to the whole basis.
    cluster_tolerance:
        Basis modes closer than ``cluster_tolerance * max(|λ_i|, 1)`` to the
        differentiated mode are dropped from the superposition and a warning is
        issued: the individual eigenvectors of a degenerate cluster are not
        differentiable, only the cluster subspace is.

    Returns
    -------
    ``(n_parameters, n_dof, n_modes)`` array of eigenvector derivatives.
    """
    phi = np.asarray(mode_shapes)
    if phi.ndim == 1:
        phi = phi.reshape(-1, 1)
    lambdas = np.asarray(eigenvalues, dtype=float).ravel()
    if lambdas.size != phi.shape[1]:
        raise ValueError(
            f"{lambdas.size} eigenvalues do not match {phi.shape[1]} mode shape columns"
        )
    dK = list(stiffness_derivatives)
    dM = list(mass_derivatives) if mass_derivatives is not None else [None] * len(dK)
    if len(dM) != len(dK):
        raise ValueError("stiffness and mass derivative lists must have equal length")
    indices = np.arange(phi.shape[1]) if modes is None else np.asarray(modes, dtype=int)

    out = np.zeros((len(dK), phi.shape[0], indices.size), dtype=phi.dtype)
    degenerate: set[int] = set()
    for k, (dk, dm) in enumerate(zip(dK, dM)):
        if dk is None and dm is None:
            continue
        for column, i in enumerate(indices):
            phi_i = phi[:, i]
            residual = np.zeros_like(phi_i)
            if dk is not None:
                residual = residual + np.asarray(dk) @ phi_i
            if dm is not None:
                residual = residual - lambdas[i] * (np.asarray(dm) @ phi_i)

            projections = phi.conj().T @ residual
            gaps = lambdas[i] - lambdas
            close = np.abs(gaps) < cluster_tolerance * max(abs(lambdas[i]), 1.0)
            coefficients = np.zeros_like(projections)
            usable = ~close
            coefficients[usable] = projections[usable] / gaps[usable]
            if close.sum() > 1:
                degenerate.add(int(i))

            # The φ_i component is fixed by the mass-normalisation constraint.
            coefficients[i] = 0.0
            if dm is not None:
                coefficients[i] = -0.5 * np.vdot(phi_i, np.asarray(dm) @ phi_i)
            out[k, :, column] = phi @ coefficients

    if degenerate:
        warnings.warn(
            f"modes {sorted(degenerate)} belong to a degenerate eigenvalue cluster; "
            "their individual eigenvector sensitivities are unreliable and the cluster "
            "contributions were dropped",
            RuntimeWarning,
            stacklevel=2,
        )
    return out


def mac_sensitivity(
    reference_shapes: np.ndarray,
    shapes: np.ndarray,
    shape_derivatives: np.ndarray,
    weights: Sequence[float] | np.ndarray | None = None,
) -> np.ndarray:
    """Derivative of the diagonal MAC with respect to the parameters.

    Parameters
    ----------
    reference_shapes:
        ``(n_dof, n_modes)`` measured shapes; they do not depend on ``p``.
    shapes:
        ``(n_dof, n_modes)`` analysis shapes, column ``i`` already paired with
        column ``i`` of ``reference_shapes``.
    shape_derivatives:
        ``(n_parameters, n_dof, n_modes)`` eigenvector derivatives, e.g. from
        :func:`mode_shape_sensitivity` restricted to the correlation DOFs.
    weights:
        Optional per-DOF weighting, the same one used to evaluate the MAC.

    Returns
    -------
    ``(n_modes, n_parameters)`` matrix of ``dMAC_ii/dp_k``.
    """
    a = np.asarray(reference_shapes)
    b = np.asarray(shapes)
    if a.ndim == 1:
        a = a.reshape(-1, 1)
    if b.ndim == 1:
        b = b.reshape(-1, 1)
    if a.shape != b.shape:
        raise ValueError(f"shape sets must match, got {a.shape} and {b.shape}")
    derivatives = np.asarray(shape_derivatives)
    if derivatives.ndim != 3 or derivatives.shape[1:] != b.shape:
        raise ValueError(
            f"shape_derivatives must have shape (n_parameters, {b.shape[0]}, {b.shape[1]}), "
            f"got {derivatives.shape}"
        )
    if weights is None:
        w = np.ones(a.shape[0])
    else:
        w = np.asarray(weights, dtype=float).ravel()
        if w.size != a.shape[0]:
            raise ValueError(f"weights has {w.size} entries but the shapes have {a.shape[0]} DOFs")

    out = np.zeros((b.shape[1], derivatives.shape[0]))
    for i in range(b.shape[1]):
        ai, bi = a[:, i], b[:, i]
        cross = np.vdot(ai, w * bi)
        norm_a = float(np.real(np.vdot(ai, w * ai)))
        norm_b = float(np.real(np.vdot(bi, w * bi)))
        if norm_a <= 0.0 or norm_b <= 0.0:
            continue
        for k in range(derivatives.shape[0]):
            db = derivatives[k, :, i]
            d_cross = np.real(np.conj(cross) * np.vdot(ai, w * db))
            d_norm_b = float(np.real(np.vdot(bi, w * db)))
            out[i, k] = (
                2.0
                / (norm_a * norm_b)
                * (d_cross - abs(cross) ** 2 / norm_b * d_norm_b)
            )
    return out


def finite_difference_jacobian(
    function: Callable[[np.ndarray], np.ndarray],
    x: Sequence[float] | np.ndarray,
    steps: Sequence[float] | np.ndarray | float = 1.0e-5,
    scheme: str = "central",
    baseline: np.ndarray | None = None,
) -> np.ndarray:
    """Finite-difference Jacobian ``dfunction/dx`` (columns = variables)."""
    if scheme not in {"central", "forward"}:
        raise ValueError(f"unknown finite-difference scheme {scheme!r}")
    x = np.asarray(x, dtype=float).ravel()
    h = np.broadcast_to(np.asarray(steps, dtype=float), x.shape).astype(float)
    if np.any(h <= 0.0):
        raise ValueError("finite-difference steps must be positive")

    if scheme == "forward" and baseline is None:
        baseline = np.asarray(function(x), dtype=float).ravel()

    columns = []
    for k in range(x.size):
        forward = x.copy()
        forward[k] += h[k]
        f_plus = np.asarray(function(forward), dtype=float).ravel()
        if scheme == "forward":
            columns.append((f_plus - baseline) / h[k])  # type: ignore[operator]
        else:
            backward = x.copy()
            backward[k] -= h[k]
            f_minus = np.asarray(function(backward), dtype=float).ravel()
            columns.append((f_plus - f_minus) / (2.0 * h[k]))
    return np.column_stack(columns) if columns else np.empty((0, 0))


def modal_sensitivity(
    response: Callable[[np.ndarray], object],
    x: Sequence[float] | np.ndarray,
    *,
    parameter_names: Sequence[str] | None = None,
    steps: Sequence[float] | np.ndarray | float = 1.0e-4,
    scheme: str = "central",
    baseline: object | None = None,
    relative_step: bool = True,
) -> SensitivityResult:
    """Finite-difference sensitivity of eigenfrequencies to parameters.

    ``response`` maps a parameter vector to anything :func:`as_modal_data` can
    interpret.  Perturbed modes are tracked back onto the baseline modes with
    the MAC before differencing, which keeps the matrix meaningful even when a
    perturbation reorders closely spaced modes.
    """
    x = np.asarray(x, dtype=float).ravel()
    base = as_modal_data(baseline) if baseline is not None else as_modal_data(response(x))
    n_modes = base.n_modes

    h = np.broadcast_to(np.asarray(steps, dtype=float), x.shape).astype(float)
    if relative_step:
        h = h * np.maximum(np.abs(x), 1.0)
    if np.any(h <= 0.0):
        raise ValueError("finite-difference steps must be positive")

    def tracked_frequencies(point: np.ndarray) -> np.ndarray:
        data = as_modal_data(response(point))
        order = track_modes(base, data)
        frequencies = np.full(n_modes, np.nan)
        take = min(n_modes, order.size)
        frequencies[:take] = data.frequencies[order[:take]]
        if np.isnan(frequencies).any():
            raise ValueError("perturbed model returned fewer modes than the baseline")
        return frequencies

    columns = []
    for k in range(x.size):
        forward = x.copy()
        forward[k] += h[k]
        f_plus = tracked_frequencies(forward)
        if scheme == "forward":
            columns.append((f_plus - base.frequencies) / h[k])
        elif scheme == "central":
            backward = x.copy()
            backward[k] -= h[k]
            f_minus = tracked_frequencies(backward)
            columns.append((f_plus - f_minus) / (2.0 * h[k]))
        else:
            raise ValueError(f"unknown finite-difference scheme {scheme!r}")

    matrix = np.column_stack(columns) if columns else np.zeros((n_modes, 0))
    names = list(parameter_names) if parameter_names is not None else [
        f"p{k}" for k in range(x.size)
    ]
    return SensitivityResult(
        matrix=matrix,
        parameter_names=names,
        response_labels=[f"f{i + 1}" for i in range(n_modes)],
        parameter_values=x,
        response_values=base.frequencies,
        scheme=scheme,
    )
