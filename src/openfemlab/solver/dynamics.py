"""Damped structural dynamics: damping models, complex modes and FRF synthesis.

The normal-mode solver in :mod:`openfemlab.solver.modal` stops at the undamped
eigenproblem ``K phi = omega^2 M phi``. This module carries the chain on to what
a test campaign actually measures:

* **Damping models** -- proportional (Rayleigh) ``C = alpha M + beta K``,
  explicit modal ratios, and structural (hysteretic) loss factors, together with
  fits from measured damping and the Caughey-O'Kelly proportionality check.
* **Complex modes** -- the quadratic eigenproblem ``(s^2 M + s C + K) phi = 0``
  solved through the symmetric state-space linearization

      A = [[C, M], [M, 0]],   B = [[K, 0], [0, -M]],   (s A + B) psi = 0

  with ``psi = [phi; s phi]``. Non-proportional damping makes ``phi`` genuinely
  complex, so the DOFs no longer pass through their extrema simultaneously.
* **Harmonic response** -- receptance/mobility/accelerance FRFs synthesized by
  real-mode superposition, by complex-mode (residue) superposition, or solved
  directly from the dynamic stiffness ``Z(omega) = K - omega^2 M + i omega C``.

Conventions
-----------
Frequencies are in Hz at the API boundary and ``omega = 2 pi f`` [rad/s]
internally. Receptance is displacement per unit force, so mobility is
``i omega H`` and accelerance ``-omega^2 H``. Real mode shapes are assumed
mass-normalized unless a ``modal_masses`` vector says otherwise; complex modes
carry their own state-space scaling factor ``a_r = phi_r^T C phi_r +
2 s_r phi_r^T M phi_r`` so the residue form

    H(i omega) = sum_r  phi_r phi_r^T / (a_r (i omega - s_r))  +  conjugate

holds whatever normalization was applied.
"""

from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np
import scipy.linalg as sla
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from ..core.assembly import AssembledSystem, assemble_system
from ..exceptions import SolverError

__all__ = [
    "RESPONSE_TYPES",
    "ComplexModalResult",
    "DampingModel",
    "FrequencyResponse",
    "ModalDamping",
    "RayleighDamping",
    "StructuralDamping",
    "complex_modal_frf",
    "complex_modes",
    "damped_matrices",
    "damping_matrix",
    "direct_frf",
    "fdac",
    "frac",
    "harmonic_response",
    "is_proportional",
    "modal_damping_matrix",
    "modal_frf",
    "modal_phase_collinearity",
    "proportionality_index",
    "residual_flexibility",
]

#: Response quantities an :class:`FrequencyResponse` can carry.
RESPONSE_TYPES = ("receptance", "mobility", "accelerance")

#: ``|Im(s)| <= OSCILLATORY_TOL * |s|`` marks a non-oscillatory (overdamped) root.
OSCILLATORY_TOL = 1e-10

#: Differentiation exponent of each response type with respect to ``i omega``.
_RESPONSE_ORDER = {"receptance": 0, "mobility": 1, "accelerance": 2}


# ============================================================ damping models


class DampingModel(ABC):
    """A viscous damping description that can be evaluated in the modal domain.

    Subclasses must provide :meth:`damping_ratios`; :meth:`matrix` is optional
    because not every model (modal ratios, hysteretic loss factors) has a
    natural physical-space matrix.
    """

    @abstractmethod
    def damping_ratios(self, angular_frequencies) -> np.ndarray:
        """Modal damping ratios ``zeta_r`` at the given ``omega_r`` [rad/s]."""

    def modal_coefficients(self, angular_frequencies) -> np.ndarray:
        """Modal damping coefficients ``2 zeta_r omega_r`` [1/s].

        This is the quantity the FRF denominator actually needs. Subclasses
        override it when a closed form avoids the ``zeta_r -> inf`` singularity
        of a rigid-body mode.
        """
        omega = _as_array(angular_frequencies, "angular_frequencies")
        return 2.0 * self.damping_ratios(omega) * omega

    def matrix(self, K, M):
        """Physical-space damping matrix ``C``."""
        raise SolverError(
            f"{type(self).__name__} has no physical-space damping matrix; "
            "use modal_damping_matrix() with a mode set instead"
        )


@dataclass(frozen=True)
class RayleighDamping(DampingModel):
    """Proportional damping ``C = alpha M + beta K``.

    The modal ratios follow ``zeta_r = alpha / (2 omega_r) + beta omega_r / 2``:
    the mass term dominates at low frequency, the stiffness term at high
    frequency, and the curve bottoms out at ``zeta = sqrt(alpha beta)`` at
    ``omega = sqrt(alpha / beta)``.
    """

    alpha: float = 0.0
    beta: float = 0.0

    def __post_init__(self) -> None:
        for name in ("alpha", "beta"):
            value = float(getattr(self, name))
            if not np.isfinite(value):
                raise SolverError(f"Rayleigh {name} must be finite, got {value}")
            object.__setattr__(self, name, value)
        if self.alpha < 0.0 or self.beta < 0.0:
            warnings.warn(
                f"negative Rayleigh coefficients (alpha={self.alpha:g}, beta={self.beta:g}) "
                "give negative damping ratios over part of the spectrum",
                RuntimeWarning,
                stacklevel=3,
            )

    # ------------------------------------------------------------- evaluation

    def matrix(self, K, M):
        """``alpha M + beta K``, keeping the sparsity of the inputs."""
        if sp.issparse(K) or sp.issparse(M):
            return (self.alpha * sp.csr_matrix(M) + self.beta * sp.csr_matrix(K)).tocsr()
        return self.alpha * np.asarray(M, dtype=float) + self.beta * np.asarray(K, dtype=float)

    def damping_ratios(self, angular_frequencies) -> np.ndarray:
        omega = _as_array(angular_frequencies, "angular_frequencies")
        stiffness_part = 0.5 * self.beta * omega
        with np.errstate(divide="ignore", invalid="ignore"):
            mass_part = np.where(omega > 0.0, 0.5 * self.alpha / omega, 0.0)
        if self.alpha != 0.0:
            mass_part = np.where(omega > 0.0, mass_part, np.inf)
        return mass_part + stiffness_part

    def modal_coefficients(self, angular_frequencies) -> np.ndarray:
        """``2 zeta_r omega_r = alpha + beta omega_r^2`` -- finite at ``omega = 0``."""
        omega = _as_array(angular_frequencies, "angular_frequencies")
        return self.alpha + self.beta * omega**2

    @property
    def minimum_ratio(self) -> float:
        """Smallest damping ratio the model can produce, ``sqrt(alpha beta)``."""
        return float(np.sqrt(self.alpha * self.beta))

    @property
    def critical_angular_frequency(self) -> float:
        """``omega`` [rad/s] where the ratio curve reaches :attr:`minimum_ratio`."""
        if self.beta == 0.0:
            return float("inf")
        return float(np.sqrt(self.alpha / self.beta))

    # ----------------------------------------------------------------- fits

    @classmethod
    def from_frequencies(
        cls,
        f1: float,
        f2: float,
        zeta1: float,
        zeta2: float | None = None,
    ) -> RayleighDamping:
        """Match ``zeta1`` at ``f1`` [Hz] and ``zeta2`` at ``f2`` [Hz] exactly."""
        if zeta2 is None:
            zeta2 = zeta1
        w1, w2 = 2.0 * np.pi * float(f1), 2.0 * np.pi * float(f2)
        if w1 <= 0.0 or w2 <= 0.0:
            raise SolverError("Rayleigh anchor frequencies must be positive")
        if np.isclose(w1, w2):
            raise SolverError(
                f"the two anchor frequencies must differ, got f1={f1:g} Hz and f2={f2:g} Hz"
            )
        denominator = w2**2 - w1**2
        alpha = 2.0 * w1 * w2 * (zeta1 * w2 - zeta2 * w1) / denominator
        beta = 2.0 * (zeta2 * w2 - zeta1 * w1) / denominator
        return cls(alpha=float(alpha), beta=float(beta))

    @classmethod
    def from_modal_damping(cls, frequencies, ratios) -> RayleighDamping:
        """Least-squares fit of ``(alpha, beta)`` to measured modal damping.

        ``frequencies`` are in Hz; two or more modes are required, and the fit
        is the standard normal-equation solution of the overdetermined system
        ``[1/(2 omega), omega/2] (alpha, beta)^T = zeta``.
        """
        omega = 2.0 * np.pi * _as_array(frequencies, "frequencies")
        zeta = _as_array(ratios, "ratios")
        if omega.size != zeta.size:
            raise SolverError(
                f"got {omega.size} frequencies but {zeta.size} damping ratios"
            )
        if omega.size < 2:
            raise SolverError("fitting Rayleigh damping needs at least two modes")
        if np.any(omega <= 0.0):
            raise SolverError("Rayleigh fitting needs strictly positive frequencies")
        basis = np.column_stack((0.5 / omega, 0.5 * omega))
        coefficients, *_ = np.linalg.lstsq(basis, zeta, rcond=None)
        return cls(alpha=float(coefficients[0]), beta=float(coefficients[1]))

    @classmethod
    def mass_proportional(cls, frequency: float, ratio: float) -> RayleighDamping:
        """``C = alpha M`` giving ``ratio`` at ``frequency`` [Hz]."""
        omega = 2.0 * np.pi * float(frequency)
        if omega <= 0.0:
            raise SolverError("frequency must be positive")
        return cls(alpha=2.0 * float(ratio) * omega, beta=0.0)

    @classmethod
    def stiffness_proportional(cls, frequency: float, ratio: float) -> RayleighDamping:
        """``C = beta K`` giving ``ratio`` at ``frequency`` [Hz]."""
        omega = 2.0 * np.pi * float(frequency)
        if omega <= 0.0:
            raise SolverError("frequency must be positive")
        return cls(alpha=0.0, beta=2.0 * float(ratio) / omega)


@dataclass(frozen=True, eq=False)
class ModalDamping(DampingModel):
    """Explicit damping ratio per mode (a scalar broadcasts to every mode)."""

    ratios: np.ndarray

    def __post_init__(self) -> None:
        values = _as_array(self.ratios, "ratios")
        if np.any(values < 0.0):
            warnings.warn(
                "negative modal damping ratios describe an unstable structure",
                RuntimeWarning,
                stacklevel=3,
            )
        object.__setattr__(self, "ratios", values)

    def damping_ratios(self, angular_frequencies) -> np.ndarray:
        omega = _as_array(angular_frequencies, "angular_frequencies")
        if self.ratios.size == 1:
            return np.full(omega.size, float(self.ratios[0]))
        if self.ratios.size != omega.size:
            raise SolverError(
                f"{self.ratios.size} modal damping ratios do not match {omega.size} modes"
            )
        return self.ratios.copy()


@dataclass(frozen=True)
class StructuralDamping(DampingModel):
    """Hysteretic damping through a complex stiffness ``K (1 + i eta)``.

    Structural damping is a frequency-domain construct: the equivalent viscous
    ratio is ``zeta = eta / 2`` at every frequency, and an equivalent viscous
    matrix ``C = eta K / omega_ref`` only exists once a reference frequency is
    named.
    """

    loss_factor: float
    reference_frequency: float | None = None

    def __post_init__(self) -> None:
        value = float(self.loss_factor)
        if not np.isfinite(value):
            raise SolverError(f"loss factor must be finite, got {value}")
        object.__setattr__(self, "loss_factor", value)

    def damping_ratios(self, angular_frequencies) -> np.ndarray:
        omega = _as_array(angular_frequencies, "angular_frequencies")
        return np.full(omega.size, 0.5 * self.loss_factor)

    def complex_stiffness(self, K):
        """``(1 + i eta) K``."""
        if sp.issparse(K):
            return (sp.csr_matrix(K) * (1.0 + 1j * self.loss_factor)).tocsr()
        return np.asarray(K) * (1.0 + 1j * self.loss_factor)

    def matrix(self, K, M):
        if self.reference_frequency is None:
            raise SolverError(
                "an equivalent viscous matrix for structural damping needs a "
                "reference_frequency; use complex_stiffness(K) for the exact "
                "frequency-domain form"
            )
        omega_ref = 2.0 * np.pi * float(self.reference_frequency)
        if omega_ref <= 0.0:
            raise SolverError("reference_frequency must be positive")
        factor = self.loss_factor / omega_ref
        if sp.issparse(K):
            return (sp.csr_matrix(K) * factor).tocsr()
        return np.asarray(K, dtype=float) * factor


def damping_matrix(damping, K, M):
    """Resolve ``damping`` to a physical-space ``C`` (``None`` stays ``None``).

    Accepts a :class:`DampingModel`, an explicit matrix, or ``None``.
    """
    if damping is None:
        return None
    if isinstance(damping, DampingModel):
        return damping.matrix(K, M)
    if sp.issparse(damping):
        matrix = sp.csr_matrix(damping)
    else:
        matrix = np.asarray(damping, dtype=float)
    if matrix.shape != K.shape:
        raise SolverError(f"damping matrix {matrix.shape} does not match K {K.shape}")
    return matrix


def modal_damping_matrix(M, mode_shapes, angular_frequencies, ratios, *, modal_masses=None):
    """Build ``C`` that realizes prescribed modal ratios on the given modes.

    ``C = M Phi diag(2 zeta_r omega_r / m_r) Phi^T M``. The result is
    proportional in the Caughey sense (``Phi`` diagonalizes it) and leaves any
    mode outside ``Phi`` undamped.
    """
    M_d = _dense(M, "M")
    shapes = np.asarray(mode_shapes, dtype=float)
    omega = _as_array(angular_frequencies, "angular_frequencies")
    if shapes.ndim != 2 or shapes.shape[0] != M_d.shape[0]:
        raise SolverError(
            f"mode shapes {shapes.shape} do not span the {M_d.shape[0]} DOFs of M"
        )
    if shapes.shape[1] != omega.size:
        raise SolverError(
            f"{shapes.shape[1]} mode shapes but {omega.size} angular frequencies"
        )
    zeta = ModalDamping(np.asarray(ratios, dtype=float)).damping_ratios(omega)
    masses = _modal_masses(modal_masses, omega.size)
    scaled = shapes * (2.0 * zeta * omega / masses)
    return (M_d @ scaled) @ (shapes.T @ M_d)


def proportionality_index(K, M, C) -> float:
    """Relative Caughey-O'Kelly residual ``||C M^-1 K - K M^-1 C||``.

    Zero (to round-off) exactly when the undamped modes also diagonalize ``C``,
    i.e. when the damping is classical/proportional.
    """
    K_d, M_d, C_d = _dense(K, "K"), _dense(M, "M"), _dense(C, "C")
    try:
        left = C_d @ sla.solve(M_d, K_d, assume_a="sym")
        right = K_d @ sla.solve(M_d, C_d, assume_a="sym")
    except (np.linalg.LinAlgError, ValueError) as exc:
        raise SolverError("the proportionality check needs a non-singular mass matrix") from exc
    scale = max(np.linalg.norm(left), np.linalg.norm(right))
    if scale == 0.0:
        return 0.0
    return float(np.linalg.norm(left - right) / scale)


def is_proportional(K, M, C, *, tol: float = 1e-10) -> bool:
    """True when ``C`` is classically damped, i.e. diagonalized by the real modes."""
    return proportionality_index(K, M, C) <= tol


def damped_matrices(model=None, *, system: AssembledSystem | None = None, damping=None):
    """Assemble ``(K, M, C, free_dofs)`` for a model or a pre-assembled system.

    ``C`` is ``None`` when no damping is supplied. All matrices span the full
    DOF space; ``free_dofs`` is the partition the dynamics routines restrict to.
    """
    if (model is None) == (system is None):
        raise SolverError("provide exactly one of 'model' or 'system'")
    assembled = system if system is not None else assemble_system(model)
    return (
        assembled.K,
        assembled.M,
        damping_matrix(damping, assembled.K, assembled.M),
        assembled.free_dofs,
    )


# ============================================================== complex modes


@dataclass
class ComplexModalResult:
    """Eigen-solutions of ``(s^2 M + s C + K) phi = 0``.

    Only one member of each conjugate pair is retained; overdamped (real, purely
    decaying) roots have no conjugate partner and are both kept, which is why
    :attr:`is_oscillatory` exists.

    Attributes
    ----------
    eigenvalues:
        Complex poles ``s_r``; ``Re(s_r) < 0`` for a stable structure.
    mode_shapes:
        ``(num_dofs, num_modes)`` complex displacement partition of the
        state-space eigenvectors, in *full* model DOF space.
    scaling:
        ``a_r = phi_r^T C phi_r + 2 s_r phi_r^T M phi_r``, the state-space
        modal constant the residue form divides by.
    """

    eigenvalues: np.ndarray
    mode_shapes: np.ndarray
    scaling: np.ndarray
    normalization: str = "state"
    free_dofs: np.ndarray | None = None
    matrices: tuple | None = field(default=None, repr=False)

    # ------------------------------------------------------------- spectrum

    @property
    def num_modes(self) -> int:
        return int(self.eigenvalues.size)

    @property
    def num_dofs(self) -> int:
        return int(self.mode_shapes.shape[0])

    @property
    def angular_frequencies(self) -> np.ndarray:
        """Undamped natural frequencies ``omega_r = |s_r|`` [rad/s]."""
        return np.abs(self.eigenvalues)

    @property
    def frequencies(self) -> np.ndarray:
        """Undamped natural frequencies ``|s_r| / (2 pi)`` [Hz]."""
        return self.angular_frequencies / (2.0 * np.pi)

    @property
    def damped_angular_frequencies(self) -> np.ndarray:
        """``omega_d = |Im(s_r)|`` [rad/s]; zero for overdamped roots."""
        return np.abs(np.imag(self.eigenvalues))

    @property
    def damped_frequencies(self) -> np.ndarray:
        """``omega_d / (2 pi)`` [Hz]."""
        return self.damped_angular_frequencies / (2.0 * np.pi)

    @property
    def damping_ratios(self) -> np.ndarray:
        """``zeta_r = -Re(s_r) / |s_r|``; saturates at 1 for real roots."""
        magnitude = self.angular_frequencies
        with np.errstate(divide="ignore", invalid="ignore"):
            ratios = np.where(magnitude > 0.0, -np.real(self.eigenvalues) / magnitude, 0.0)
        return ratios

    @property
    def is_oscillatory(self) -> np.ndarray:
        """Mask of underdamped roots (the ones with a conjugate partner)."""
        magnitude = self.angular_frequencies
        floor = OSCILLATORY_TOL * np.where(magnitude > 0.0, magnitude, 1.0)
        return np.abs(np.imag(self.eigenvalues)) > floor

    # -------------------------------------------------------- shape quality

    @property
    def modal_phase_collinearity(self) -> np.ndarray:
        """Per-mode MPC; 1 for a monophase (effectively real) mode."""
        return modal_phase_collinearity(self.mode_shapes)

    def real_modes(self) -> np.ndarray:
        """Best real approximation: rotate the dominant component onto the real axis."""
        shapes = self.mode_shapes
        if shapes.size == 0:
            return np.zeros(shapes.shape, dtype=float)
        dominant = np.argmax(np.abs(shapes), axis=0)
        peak = shapes[dominant, np.arange(shapes.shape[1])]
        phase = np.where(np.abs(peak) > 0.0, np.angle(peak), 0.0)
        return np.real(shapes * np.exp(-1j * phase))

    def residuals(self) -> np.ndarray:
        """Relative quadratic-eigenproblem residual per mode (a solver quality check)."""
        if self.matrices is None:
            raise SolverError("this result carries no matrices; residuals cannot be evaluated")
        K, M, C = self.matrices
        shapes = self.reduced_shapes()
        out = np.empty(self.num_modes, dtype=float)
        for index in range(self.num_modes):
            s = self.eigenvalues[index]
            phi = shapes[:, index]
            k_phi, c_phi, m_phi = K @ phi, C @ phi, M @ phi
            residual = s**2 * m_phi + s * c_phi + k_phi
            scale = (
                abs(s) ** 2 * np.linalg.norm(m_phi)
                + abs(s) * np.linalg.norm(c_phi)
                + np.linalg.norm(k_phi)
            )
            out[index] = np.linalg.norm(residual) / scale if scale > 0.0 else 0.0
        return out

    def reduced_shapes(self) -> np.ndarray:
        """Mode shapes restricted to the DOFs the eigenproblem was solved on."""
        if self.free_dofs is None:
            return self.mode_shapes
        return self.mode_shapes[self.free_dofs, :]

    # ---------------------------------------------------------------- output

    def summary(self, max_rows: int = 20) -> str:
        mpc = self.modal_phase_collinearity
        lines = [
            f"{'mode':>5} {'f [Hz]':>14} {'fd [Hz]':>14} {'zeta [%]':>12} {'MPC':>8}",
            "-" * 57,
        ]
        for i in range(min(self.num_modes, max_rows)):
            lines.append(
                f"{i + 1:>5} {self.frequencies[i]:>14.6g} {self.damped_frequencies[i]:>14.6g} "
                f"{100.0 * self.damping_ratios[i]:>12.4f} {mpc[i]:>8.4f}"
            )
        if self.num_modes > max_rows:
            lines.append(f"... {self.num_modes - max_rows} more modes")
        return "\n".join(lines)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        freqs = np.array2string(self.frequencies[:5], precision=4)
        return f"<ComplexModalResult {self.num_modes} modes, f[Hz]={freqs}>"


def complex_modes(
    K,
    M,
    C=None,
    num_modes: int | None = None,
    *,
    free_dofs=None,
    normalization: str = "state",
) -> ComplexModalResult:
    """Solve the damped (quadratic) eigenproblem ``(s^2 M + s C + K) phi = 0``.

    Parameters
    ----------
    K, M, C:
        Symmetric system matrices; ``C = 0`` when omitted, in which case the
        poles come out purely imaginary and reproduce the undamped spectrum.
    num_modes:
        Keep the ``num_modes`` roots of smallest ``|s|`` after conjugate
        reduction. ``None`` keeps them all.
    free_dofs:
        Solve on this DOF subset and scatter the shapes back to full DOF space.
    normalization:
        ``"state"`` scales each mode so ``a_r = 1`` (unit modal-A, the form that
        makes residues equal ``phi_r phi_r^T``), ``"max"`` puts the dominant
        component at ``1 + 0j``, ``"none"`` leaves the LAPACK scaling.

    Notes
    -----
    The state-space pencil is singular when any retained DOF is massless, so
    such DOFs must be condensed out before calling this (the undamped solver
    does it automatically; there is no exact equivalent once ``C`` is present).
    """
    allowed = ("state", "max", "none")
    if normalization not in allowed:
        raise SolverError(f"unknown normalization {normalization!r}; expected one of {allowed}")

    K_full, M_full = _dense(K, "K"), _dense(M, "M")
    if K_full.shape != M_full.shape:
        raise SolverError(f"K {K_full.shape} and M {M_full.shape} must have the same shape")
    num_dofs = K_full.shape[0]
    C_full = np.zeros((num_dofs, num_dofs)) if C is None else _dense(C, "C")
    if C_full.shape != K_full.shape:
        raise SolverError(f"C {C_full.shape} and K {K_full.shape} must have the same shape")

    free = None if free_dofs is None else np.unique(np.asarray(free_dofs, dtype=int))
    if free is not None and free.size == 0:
        raise SolverError("free_dofs is empty: every equation is constrained")
    grid = None if free is None else np.ix_(free, free)
    K_r = K_full if grid is None else K_full[grid]
    M_r = M_full if grid is None else M_full[grid]
    C_r = C_full if grid is None else C_full[grid]
    K_r, M_r, C_r = _symmetrize(K_r), _symmetrize(M_r), _symmetrize(C_r)

    size = K_r.shape[0]
    if size == 0:
        raise SolverError("the damped eigenproblem is empty")
    if np.any(np.abs(M_r).sum(axis=1) <= 0.0):
        raise SolverError(
            "the mass matrix has empty rows, so the state-space pencil is singular; "
            "condense the massless DOFs before solving the damped eigenproblem"
        )

    zero = np.zeros((size, size))
    A = np.block([[C_r, M_r], [M_r, zero]])
    B = np.block([[K_r, zero], [zero, -M_r]])
    try:
        values, vectors = sla.eig(-B, A)
    except (np.linalg.LinAlgError, ValueError) as exc:  # pragma: no cover - LAPACK dependent
        raise SolverError("the damped eigensolver failed on the state-space pencil") from exc

    finite = np.isfinite(values)
    if not np.all(finite):
        warnings.warn(
            f"discarded {int((~finite).sum())} infinite state-space eigenvalues; "
            "the mass matrix is close to singular",
            RuntimeWarning,
            stacklevel=2,
        )
        values, vectors = values[finite], vectors[:, finite]

    order = np.argsort(np.abs(values), kind="stable")
    values, vectors = values[order], vectors[:, order]
    keep = np.imag(values) >= 0.0
    values, vectors = values[keep], vectors[:, keep]
    if num_modes is not None:
        if num_modes < 1:
            raise SolverError(f"num_modes must be >= 1, got {num_modes}")
        values, vectors = values[:num_modes], vectors[:, :num_modes]

    shapes = np.array(vectors[:size, :], dtype=complex, copy=True)
    shapes, scaling = _normalize_complex_modes(shapes, values, M_r, C_r, normalization)

    if free is None:
        full_shapes = shapes
    else:
        full_shapes = np.zeros((num_dofs, shapes.shape[1]), dtype=complex)
        full_shapes[free, :] = shapes

    return ComplexModalResult(
        eigenvalues=values,
        mode_shapes=full_shapes,
        scaling=scaling,
        normalization=normalization,
        free_dofs=free,
        matrices=(K_r, M_r, C_r),
    )


def modal_phase_collinearity(mode_shapes) -> np.ndarray:
    """Modal Phase Collinearity of each column of ``mode_shapes``.

    MPC compares the two principal variances of the ``(Re, Im)`` scatter of a
    complex mode: 1 means every DOF shares one phase (a real mode up to a global
    rotation, i.e. classical damping), 0 means the phases are spread evenly.
    """
    shapes = np.asarray(mode_shapes, dtype=complex)
    single = shapes.ndim == 1
    if single:
        shapes = shapes.reshape(-1, 1)
    if shapes.ndim != 2:
        raise SolverError(f"expected a vector or a (dof, mode) matrix, got {shapes.shape}")
    x, y = shapes.real, shapes.imag
    sxx = np.einsum("ir,ir->r", x, x)
    syy = np.einsum("ir,ir->r", y, y)
    sxy = np.einsum("ir,ir->r", x, y)
    total = sxx + syy
    radius = np.sqrt((0.5 * (sxx - syy)) ** 2 + sxy**2)
    values = _safe_ratio(4.0 * radius**2, total**2, fallback=1.0)
    return float(values[0]) if single else values


def _normalize_complex_modes(shapes, values, M, C, normalization):
    if shapes.size == 0:
        return shapes, np.zeros(0, dtype=complex)
    scaling = _state_space_scaling(shapes, values, M, C)
    if normalization == "max":
        dominant = np.argmax(np.abs(shapes), axis=0)
        peak = shapes[dominant, np.arange(shapes.shape[1])]
        peak = np.where(np.abs(peak) > 0.0, peak, 1.0)
        shapes = shapes / peak
        scaling = scaling / peak**2
    elif normalization == "state":
        reference = np.max(np.abs(scaling)) if scaling.size else 0.0
        degenerate = np.abs(scaling) <= 1e-14 * max(reference, 1.0)
        if np.any(degenerate):
            warnings.warn(
                f"{int(degenerate.sum())} modes have a vanishing modal-A constant "
                "(undamped rigid-body roots) and were left unscaled",
                RuntimeWarning,
                stacklevel=3,
            )
        factors = np.where(degenerate, 1.0, np.sqrt(np.where(degenerate, 1.0, scaling)))
        shapes = shapes / factors
        scaling = np.where(degenerate, scaling, 1.0 + 0.0j)
    return shapes, scaling


def _state_space_scaling(shapes, values, M, C):
    """``a_r = phi_r^T C phi_r + 2 s_r phi_r^T M phi_r`` (bilinear, not Hermitian)."""
    damping_term = np.einsum("ir,ij,jr->r", shapes, C, shapes)
    mass_term = np.einsum("ir,ij,jr->r", shapes, M, shapes)
    return damping_term + 2.0 * values * mass_term


# ========================================================== frequency response


@dataclass
class FrequencyResponse:
    """A synthesized or measured FRF matrix over a frequency line.

    ``data[f, j, k]`` is the response at ``response_dofs[j]`` due to a unit
    harmonic force at ``excitation_dofs[k]``, at ``frequencies[f]`` [Hz].
    """

    frequencies: np.ndarray
    data: np.ndarray
    response_dofs: np.ndarray
    excitation_dofs: np.ndarray
    response_type: str = "receptance"

    def __post_init__(self) -> None:
        self.frequencies = _as_array(self.frequencies, "frequencies")
        self.response_dofs = np.asarray(self.response_dofs, dtype=int).reshape(-1)
        self.excitation_dofs = np.asarray(self.excitation_dofs, dtype=int).reshape(-1)
        self.data = np.asarray(self.data, dtype=complex)
        expected = (
            self.frequencies.size,
            self.response_dofs.size,
            self.excitation_dofs.size,
        )
        if self.data.shape != expected:
            raise SolverError(f"FRF data {self.data.shape} does not match {expected}")
        if self.response_type not in RESPONSE_TYPES:
            raise SolverError(
                f"unknown response type {self.response_type!r}; expected one of {RESPONSE_TYPES}"
            )

    # ------------------------------------------------------------- geometry

    @property
    def num_frequencies(self) -> int:
        return int(self.frequencies.size)

    @property
    def num_response_dofs(self) -> int:
        return int(self.response_dofs.size)

    @property
    def num_excitation_dofs(self) -> int:
        return int(self.excitation_dofs.size)

    @property
    def angular_frequencies(self) -> np.ndarray:
        return 2.0 * np.pi * self.frequencies

    # --------------------------------------------------------------- access

    @property
    def magnitude(self) -> np.ndarray:
        return np.abs(self.data)

    @property
    def phase(self) -> np.ndarray:
        """Phase [degrees] in ``(-180, 180]``."""
        return np.degrees(np.angle(self.data))

    def matrix_at(self, index: int) -> np.ndarray:
        """The full FRF matrix at frequency line ``index``."""
        return self.data[index]

    def nearest(self, frequency: float) -> int:
        """Index of the frequency line closest to ``frequency`` [Hz]."""
        if self.num_frequencies == 0:
            raise SolverError("the frequency line is empty")
        return int(np.argmin(np.abs(self.frequencies - float(frequency))))

    def column(self, excitation_dof: int) -> np.ndarray:
        """``(num_frequencies, num_response_dofs)`` response to one exciter."""
        return self.data[:, :, _locate(self.excitation_dofs, excitation_dof, "excitation")]

    def row(self, response_dof: int) -> np.ndarray:
        """``(num_frequencies, num_excitation_dofs)`` seen by one sensor."""
        return self.data[:, _locate(self.response_dofs, response_dof, "response"), :]

    def drive_point(self, dof: int) -> np.ndarray:
        """The collocated ``H_jj(omega)`` line for ``dof``."""
        return self.data[
            :,
            _locate(self.response_dofs, dof, "response"),
            _locate(self.excitation_dofs, dof, "excitation"),
        ]

    # ---------------------------------------------------------- conversions

    def converted(self, response_type: str) -> FrequencyResponse:
        """The same FRF expressed as receptance, mobility or accelerance."""
        if response_type not in RESPONSE_TYPES:
            raise SolverError(
                f"unknown response type {response_type!r}; expected one of {RESPONSE_TYPES}"
            )
        exponent = _RESPONSE_ORDER[response_type] - _RESPONSE_ORDER[self.response_type]
        if exponent == 0:
            data = self.data.copy()
        else:
            omega = self.angular_frequencies
            if exponent < 0 and np.any(omega == 0.0):
                raise SolverError(
                    f"cannot convert {self.response_type} to {response_type} at 0 Hz: "
                    "the integration is singular there"
                )
            data = self.data * ((1j * omega) ** exponent)[:, None, None]
        return FrequencyResponse(
            frequencies=self.frequencies.copy(),
            data=data,
            response_dofs=self.response_dofs.copy(),
            excitation_dofs=self.excitation_dofs.copy(),
            response_type=response_type,
        )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<FrequencyResponse {self.response_type} "
            f"{self.num_frequencies}x{self.num_response_dofs}x{self.num_excitation_dofs}>"
        )


def modal_frf(
    frequencies,
    modes,
    damping=0.0,
    *,
    modal_masses=None,
    num_modes: int | None = None,
    response_dofs=None,
    excitation_dofs=None,
    residual: np.ndarray | None = None,
    response_type: str = "receptance",
) -> FrequencyResponse:
    """Synthesize an FRF by real-mode superposition.

    ``H_jk(omega) = sum_r phi_jr phi_kr / (m_r [(omega_r^2 - omega^2)
    + i omega (2 zeta_r omega_r)])``, optionally plus a residual flexibility
    matrix that restores the static contribution of the discarded modes (see
    :func:`residual_flexibility`).

    Parameters
    ----------
    modes:
        A :class:`~openfemlab.solver.modal.ModalResult` (or anything exposing
        ``angular_frequencies``/``frequencies`` plus ``mode_shapes``), a
        ``(angular_frequencies, mode_shapes)`` pair, or a
        :class:`ComplexModalResult` -- which is forwarded to
        :func:`complex_modal_frf`.
    damping:
        A :class:`DampingModel`, a per-mode array of ratios, or a scalar ratio.
    """
    if isinstance(modes, ComplexModalResult):
        return complex_modal_frf(
            frequencies,
            modes,
            num_modes=num_modes,
            response_dofs=response_dofs,
            excitation_dofs=excitation_dofs,
            residual=residual,
            response_type=response_type,
        )

    omega_r, shapes = _modal_data(modes)
    if num_modes is not None:
        omega_r, shapes = omega_r[:num_modes], shapes[:, :num_modes]
    masses = _modal_masses(modal_masses, omega_r.size)
    coefficients = _modal_coefficients(damping, omega_r)

    freq = _as_array(frequencies, "frequencies")
    omega = 2.0 * np.pi * freq
    num_dofs = shapes.shape[0]
    out = _dof_selection(response_dofs, num_dofs, "response_dofs")
    inp = _dof_selection(excitation_dofs, num_dofs, "excitation_dofs")

    denominator = masses * (
        (omega_r**2 - omega[:, None] ** 2) + 1j * omega[:, None] * coefficients
    )
    if np.any(denominator == 0.0):
        raise SolverError(
            "an undamped mode sits exactly on a requested frequency line; "
            "add damping or offset the frequency grid"
        )
    weights = 1.0 / denominator
    data = np.einsum("om,fm,im->foi", shapes[out, :], weights, shapes[inp, :])
    data = _apply_residual(data, residual, out, inp)
    data *= _response_factor(omega, response_type)[:, None, None]
    return FrequencyResponse(freq, data, out, inp, response_type)


def complex_modal_frf(
    frequencies,
    result: ComplexModalResult,
    *,
    num_modes: int | None = None,
    response_dofs=None,
    excitation_dofs=None,
    residual: np.ndarray | None = None,
    response_type: str = "receptance",
) -> FrequencyResponse:
    """Synthesize an FRF from complex modes through the residue expansion.

    ``H(i omega) = sum_r [phi_r phi_r^T / (a_r (i omega - s_r))
    + conj(phi_r) conj(phi_r)^T / (conj(a_r) (i omega - conj(s_r)))]``, where the
    conjugate term is present only for the underdamped (oscillatory) roots. With
    every root retained this reproduces the direct inversion of the dynamic
    stiffness exactly, for proportional *and* non-proportional damping.
    """
    if not isinstance(result, ComplexModalResult):
        raise SolverError("complex_modal_frf expects a ComplexModalResult")
    poles = result.eigenvalues
    shapes = result.mode_shapes
    scaling = result.scaling
    oscillatory = result.is_oscillatory
    if num_modes is not None:
        poles = poles[:num_modes]
        shapes = shapes[:, :num_modes]
        scaling = scaling[:num_modes]
        oscillatory = oscillatory[:num_modes]
    if np.any(scaling == 0.0):
        raise SolverError(
            "a retained mode has a zero modal-A constant, so its residue is undefined; "
            "drop the undamped rigid-body roots before synthesizing"
        )

    freq = _as_array(frequencies, "frequencies")
    omega = 2.0 * np.pi * freq
    num_dofs = shapes.shape[0]
    out = _dof_selection(response_dofs, num_dofs, "response_dofs")
    inp = _dof_selection(excitation_dofs, num_dofs, "excitation_dofs")

    j_omega = 1j * omega[:, None]
    weights = 1.0 / (scaling * (j_omega - poles))
    conjugate_weights = np.where(
        oscillatory,
        1.0 / (np.conjugate(scaling) * (j_omega - np.conjugate(poles))),
        0.0,
    )
    data = np.einsum("om,fm,im->foi", shapes[out, :], weights, shapes[inp, :])
    data += np.einsum(
        "om,fm,im->foi",
        np.conjugate(shapes[out, :]),
        conjugate_weights,
        np.conjugate(shapes[inp, :]),
    )
    data = _apply_residual(data, residual, out, inp)
    data *= _response_factor(omega, response_type)[:, None, None]
    return FrequencyResponse(freq, data, out, inp, response_type)


def direct_frf(
    frequencies,
    K,
    M,
    C=None,
    *,
    free_dofs=None,
    structural_damping: float | None = None,
    response_dofs=None,
    excitation_dofs=None,
    response_type: str = "receptance",
) -> FrequencyResponse:
    """Invert the dynamic stiffness ``Z = (1 + i eta) K - omega^2 M + i omega C``.

    This is the reference the modal syntheses are checked against: it makes no
    truncation and no proportionality assumption, at the cost of one factorization
    per frequency line.
    """
    K_full, M_full, C_full, free, num_dofs = _dynamic_matrices(K, M, C, free_dofs)
    freq = _as_array(frequencies, "frequencies")
    omega = 2.0 * np.pi * freq
    out = _dof_selection(response_dofs, num_dofs, "response_dofs")
    inp = _dof_selection(excitation_dofs, num_dofs, "excitation_dofs")

    loads = np.zeros((num_dofs, inp.size))
    loads[inp, np.arange(inp.size)] = 1.0
    responses = _solve_over_frequencies(
        omega, K_full, M_full, C_full, free, loads, structural_damping
    )
    data = responses[:, out, :]
    data = data * _response_factor(omega, response_type)[:, None, None]
    return FrequencyResponse(freq, data, out, inp, response_type)


def harmonic_response(
    frequencies,
    K,
    M,
    C=None,
    *,
    load,
    free_dofs=None,
    structural_damping: float | None = None,
) -> np.ndarray:
    """Steady-state complex amplitudes for a harmonic load.

    ``load`` is either one ``(num_dofs,)`` vector applied at every frequency or a
    ``(num_frequencies, num_dofs)`` array of frequency-dependent amplitudes.
    Returns the ``(num_frequencies, num_dofs)`` complex displacement amplitudes.
    """
    K_full, M_full, C_full, free, num_dofs = _dynamic_matrices(K, M, C, free_dofs)
    freq = _as_array(frequencies, "frequencies")
    omega = 2.0 * np.pi * freq

    forces = np.atleast_2d(np.asarray(load, dtype=complex))
    if forces.shape == (1, num_dofs):
        forces = np.repeat(forces, freq.size, axis=0)
    if forces.shape != (freq.size, num_dofs):
        raise SolverError(
            f"load {np.shape(load)} must be ({num_dofs},) or ({freq.size}, {num_dofs})"
        )

    responses = _solve_over_frequencies(
        omega, K_full, M_full, C_full, free, forces[:, :, None], structural_damping
    )
    return responses[:, :, 0]


def residual_flexibility(K, modes, *, modal_masses=None, num_modes=None, free_dofs=None):
    """Static contribution of the modes *not* retained in a truncated synthesis.

    ``R = K^-1 - sum_r phi_r phi_r^T / (m_r omega_r^2)`` over the retained modes.
    Adding ``R`` to a truncated receptance restores the exact static (0 Hz)
    response and greatly improves the low-frequency band. The model must be
    statically determinate: with rigid-body modes ``K`` is singular and inertia
    relief is needed instead.
    """
    K_full = _dense(K, "K")
    num_dofs = K_full.shape[0]
    omega_r, shapes = _modal_data(modes)
    if num_modes is not None:
        omega_r, shapes = omega_r[:num_modes], shapes[:, :num_modes]
    if shapes.shape[0] != num_dofs:
        raise SolverError(
            f"mode shapes span {shapes.shape[0]} DOFs but K has {num_dofs}"
        )
    masses = _modal_masses(modal_masses, omega_r.size)
    if np.any(omega_r <= 0.0):
        raise SolverError(
            "residual flexibility is undefined for a model with rigid-body modes"
        )

    free = np.arange(num_dofs) if free_dofs is None else np.unique(np.asarray(free_dofs, dtype=int))
    grid = np.ix_(free, free)
    try:
        inverse = sla.solve(K_full[grid], np.eye(free.size), assume_a="sym")
    except (np.linalg.LinAlgError, ValueError) as exc:
        raise SolverError("the stiffness matrix is singular on the free DOFs") from exc

    flexibility = np.zeros((num_dofs, num_dofs))
    flexibility[grid] = inverse
    modal_part = (shapes / (masses * omega_r**2)) @ shapes.T
    return flexibility - modal_part


# =========================================================== FRF correlation


def frac(reference, comparison, *, axis: int = 0):
    """Frequency Response Assurance Criterion between two FRF lines.

    ``FRAC = |h_a^H h_b|^2 / ((h_a^H h_a)(h_b^H h_b))``, summed over ``axis``
    (the frequency axis by default). It is 1 for FRFs that differ only by a
    complex scale factor, and drops as their shape over frequency diverges.
    """
    a = np.asarray(reference, dtype=complex)
    b = np.asarray(comparison, dtype=complex)
    if a.shape != b.shape:
        raise SolverError(f"FRAC needs matching shapes, got {a.shape} and {b.shape}")
    numerator = np.abs(np.sum(np.conjugate(a) * b, axis=axis)) ** 2
    denominator = np.sum(np.abs(a) ** 2, axis=axis) * np.sum(np.abs(b) ** 2, axis=axis)
    values = _safe_ratio(numerator, denominator)
    return float(values) if np.ndim(values) == 0 else values


def fdac(reference, comparison) -> np.ndarray:
    """Frequency Domain Assurance Criterion matrix between two FRF sets.

    Both inputs are ``(num_frequencies, num_dofs)`` response vectors for one
    excitation. Entry ``(p, q)`` correlates the deflection shape of the reference
    at line ``p`` with that of the comparison at line ``q``; a clean diagonal
    means the two models resonate in the same shapes at the same frequencies,
    and an off-diagonal ridge exposes a frequency shift.
    """
    a = np.atleast_2d(np.asarray(reference, dtype=complex))
    b = np.atleast_2d(np.asarray(comparison, dtype=complex))
    if a.shape[1] != b.shape[1]:
        raise SolverError(
            f"FDAC needs the same DOF count, got {a.shape[1]} and {b.shape[1]}"
        )
    numerator = np.abs(np.conjugate(a) @ b.T) ** 2
    denominator = np.outer(np.sum(np.abs(a) ** 2, axis=1), np.sum(np.abs(b) ** 2, axis=1))
    return _safe_ratio(numerator, denominator)


def sac(reference, comparison) -> np.ndarray:
    """Spectral Assurance Criterion — amplitude-only FRAC per frequency line.

    At each frequency, correlates the *amplitude* shapes ``|H(f, :)|`` across
  channels (FEMtools SAC).  Returns ``(n_frequencies,)`` values in ``[0, 1]``.
    """
    magnitude_a = np.abs(np.asarray(reference, dtype=complex))
    magnitude_b = np.abs(np.asarray(comparison, dtype=complex))
    if magnitude_a.shape != magnitude_b.shape:
        raise SolverError(
            f"SAC needs matching shapes, got {magnitude_a.shape} and {magnitude_b.shape}"
        )
    return np.atleast_1d(
        np.asarray(frac(magnitude_a, magnitude_b, axis=1), dtype=np.float64)
    )


def csac(reference, comparison) -> np.ndarray:
    """Complex Spectral Assurance Criterion per frequency line (FEMtools CSAC = FRAC).

    At each frequency, correlates the complex channel vector ``H(f, :)``.  This
    is the line-wise FRAC that FEMtools labels CSAC.
    """
    a = np.asarray(reference, dtype=complex)
    b = np.asarray(comparison, dtype=complex)
    if a.shape != b.shape:
        raise SolverError(f"CSAC needs matching shapes, got {a.shape} and {b.shape}")
    return np.atleast_1d(np.asarray(frac(a, b, axis=1), dtype=np.float64))


def csf(reference, comparison) -> np.ndarray:
    """Correlation Spectral Function — FDAC diagonal (shape agreement per line).

    Entry ``csf[f]`` is the FDAC diagonal at frequency line ``f`` (FEMtools CSF).
    """
    matrix = fdac(reference, comparison)
    return np.asarray(np.diag(matrix), dtype=np.float64)


# ==================================================================== helpers


def _safe_ratio(numerator, denominator, fallback: float = 0.0) -> np.ndarray:
    """``numerator / denominator``, substituting ``fallback`` where it degenerates."""
    positive = denominator > 0.0
    return np.where(positive, numerator / np.where(positive, denominator, 1.0), fallback)


def _as_array(values, name: str) -> np.ndarray:
    array = np.atleast_1d(np.asarray(values, dtype=float))
    if array.ndim != 1:
        raise SolverError(f"{name} must be a scalar or a 1-D sequence, got shape {array.shape}")
    if not np.all(np.isfinite(array)):
        raise SolverError(f"{name} contains non-finite values")
    return array


def _dense(matrix, name: str) -> np.ndarray:
    if matrix is None:
        raise SolverError(f"{name} is required")
    array = matrix.toarray() if sp.issparse(matrix) else np.asarray(matrix)
    if array.ndim != 2 or array.shape[0] != array.shape[1]:
        raise SolverError(f"{name} must be a square matrix, got shape {array.shape}")
    return np.asarray(array, dtype=float)


def _symmetrize(matrix: np.ndarray) -> np.ndarray:
    return 0.5 * (matrix + matrix.T)


def _restrict(matrix, free: np.ndarray | None):
    if free is None:
        return matrix
    if sp.issparse(matrix):
        return matrix[free, :][:, free].tocsc()
    return np.asarray(matrix)[np.ix_(free, free)]


def _dof_selection(dofs, num_dofs: int, name: str) -> np.ndarray:
    if dofs is None:
        return np.arange(num_dofs, dtype=int)
    index = np.atleast_1d(np.asarray(dofs, dtype=int)).reshape(-1)
    if index.size and (index.min() < 0 or index.max() >= num_dofs):
        raise SolverError(f"{name} references a DOF outside the {num_dofs}-DOF model")
    return index


def _locate(available: np.ndarray, dof: int, kind: str) -> int:
    matches = np.flatnonzero(available == int(dof))
    if matches.size == 0:
        raise SolverError(f"DOF {dof} is not among the {kind} DOFs of this FRF")
    return int(matches[0])


def _response_factor(omega: np.ndarray, response_type: str) -> np.ndarray:
    if response_type not in RESPONSE_TYPES:
        raise SolverError(
            f"unknown response type {response_type!r}; expected one of {RESPONSE_TYPES}"
        )
    exponent = _RESPONSE_ORDER[response_type]
    if exponent == 0:
        return np.ones(omega.size, dtype=complex)
    return (1j * omega) ** exponent


def _modal_data(modes) -> tuple[np.ndarray, np.ndarray]:
    if isinstance(modes, tuple) and len(modes) == 2:
        angular, shapes = modes
    else:
        shapes = getattr(modes, "mode_shapes", None)
        if shapes is None:
            raise SolverError(
                "modes must be a (angular_frequencies, mode_shapes) pair or expose "
                "'mode_shapes' together with 'angular_frequencies' or 'frequencies'"
            )
        if hasattr(modes, "angular_frequencies"):
            angular = modes.angular_frequencies
        elif hasattr(modes, "frequencies"):
            angular = 2.0 * np.pi * np.asarray(modes.frequencies, dtype=float)
        else:
            raise SolverError("modes expose 'mode_shapes' but no frequency information")
    omega = _as_array(angular, "angular_frequencies")
    array = np.atleast_2d(np.asarray(shapes, dtype=float))
    if array.shape[1] != omega.size:
        raise SolverError(
            f"{array.shape[1]} mode shape columns do not match {omega.size} frequencies"
        )
    return omega, array


def _modal_masses(modal_masses, num_modes: int) -> np.ndarray:
    if modal_masses is None:
        return np.ones(num_modes)
    masses = _as_array(modal_masses, "modal_masses")
    if masses.size == 1:
        masses = np.full(num_modes, float(masses[0]))
    if masses.size != num_modes:
        raise SolverError(f"{masses.size} modal masses but {num_modes} modes")
    if np.any(masses <= 0.0):
        raise SolverError("modal masses must be positive")
    return masses


def _modal_coefficients(damping, omega_r: np.ndarray) -> np.ndarray:
    """Resolve ``damping`` to the ``2 zeta_r omega_r`` array the FRF needs."""
    if damping is None:
        return np.zeros(omega_r.size)
    if isinstance(damping, DampingModel):
        coefficients = np.asarray(damping.modal_coefficients(omega_r), dtype=float)
    else:
        ratios = _as_array(damping, "damping")
        if ratios.size == 1:
            ratios = np.full(omega_r.size, float(ratios[0]))
        if ratios.size != omega_r.size:
            raise SolverError(f"{ratios.size} damping ratios but {omega_r.size} modes")
        coefficients = 2.0 * ratios * omega_r
    if coefficients.size != omega_r.size:
        raise SolverError(
            f"the damping model returned {coefficients.size} coefficients for {omega_r.size} modes"
        )
    return coefficients


def _apply_residual(data, residual, out: np.ndarray, inp: np.ndarray):
    if residual is None:
        return data
    matrix = np.asarray(residual)
    if matrix.ndim != 2:
        raise SolverError(f"the residual must be a matrix, got shape {matrix.shape}")
    return data + matrix[np.ix_(out, inp)][None, :, :]


def _dynamic_matrices(K, M, C, free_dofs):
    num_dofs = K.shape[0]
    if M.shape != K.shape:
        raise SolverError(f"K {K.shape} and M {M.shape} must have the same shape")
    if C is not None and C.shape != K.shape:
        raise SolverError(f"C {C.shape} and K {K.shape} must have the same shape")
    free = None if free_dofs is None else np.unique(np.asarray(free_dofs, dtype=int))
    if free is not None and free.size == 0:
        raise SolverError("free_dofs is empty: every equation is constrained")
    return K, M, C, free, num_dofs


def _solve_over_frequencies(omega, K, M, C, free, loads, structural_damping):
    """Solve ``Z(omega) x = loads`` on the free DOFs for every ``omega``.

    ``loads`` is either one ``(num_dofs, num_rhs)`` block reused at every
    frequency or a ``(num_frequencies, num_dofs, num_rhs)`` stack.
    """
    K_r = _restrict(K, free)
    M_r = _restrict(M, free)
    C_r = None if C is None else _restrict(C, free)

    forces = np.asarray(loads, dtype=complex)
    per_frequency = forces.ndim == 3
    rhs = forces if free is None else forces[..., free, :]

    num_dofs = K.shape[0]
    size = K_r.shape[0]
    sparse_path = sp.issparse(K_r) and size > 400
    if not sparse_path:
        K_r = K_r.toarray() if sp.issparse(K_r) else np.asarray(K_r)
        M_r = M_r.toarray() if sp.issparse(M_r) else np.asarray(M_r)
        if C_r is not None:
            C_r = C_r.toarray() if sp.issparse(C_r) else np.asarray(C_r)

    stiffness = K_r
    if structural_damping:
        stiffness = K_r * (1.0 + 1j * float(structural_damping))

    out = np.zeros((omega.size, num_dofs, rhs.shape[-1]), dtype=complex)
    for index, w in enumerate(omega):
        impedance = stiffness - (w**2) * M_r
        if C_r is not None:
            impedance = impedance + 1j * w * C_r
        block = rhs[index] if per_frequency else rhs
        try:
            if sparse_path:
                solution = spla.splu(sp.csc_matrix(impedance)).solve(block)
            else:
                solution = sla.solve(np.asarray(impedance, dtype=complex), block)
        except (np.linalg.LinAlgError, RuntimeError, ValueError) as exc:
            raise SolverError(
                f"the dynamic stiffness is singular at {w / (2.0 * np.pi):g} Hz; "
                "add damping or move the frequency line off the resonance"
            ) from exc
        if free is None:
            out[index] = solution
        else:
            out[index][free, :] = solution
    return out
