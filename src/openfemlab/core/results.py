"""Analysis-result and test-data contracts.

These are the currency exchanged between ``modal``/``solver`` (producers),
``io`` (import/export), and ``correlation``/``updating`` (consumers). A result
carries its own :class:`~openfemlab.core.dofs.DofMap`, so it stays
interpretable when detached from the model that produced it — the property
that makes the platform solver-independent.

:class:`ModalResult` is the *single* result contract: the internal solver
(:mod:`openfemlab.solver.modal`) and external importers construct the same
object. Producers that own an assembled system attach it, which unlocks the
generalized quantities (modal masses, participation factors, ...); producers
that only know frequencies and shapes leave those fields empty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

from openfemlab.core.dofs import DofMap
from openfemlab.core.model import DOF
from openfemlab.exceptions import SolverError

if TYPE_CHECKING:
    from openfemlab.core.assembly import AssembledSystem

__all__ = ["NORMALIZATIONS", "RIGID_BODY_TOL", "ModalResult", "TestData"]

#: Mode-shape scalings a producer may report through ``ModalResult.normalization``.
NORMALIZATIONS = ("mass", "max", "none")

#: Eigenvalues below ``RIGID_BODY_TOL * max(|lambda|)`` are treated as rigid-body modes.
RIGID_BODY_TOL = 1e-8

_TWO_PI = 2.0 * np.pi


class ModalResult:
    """Eigen-solution of an undamped (or proportionally damped) model.

    The spectrum can be supplied either as ``frequencies`` [Hz] or as
    ``eigenvalues`` (``omega^2``) — exactly one of the two — and the shapes
    either as ``shapes`` or under the solver-side name ``mode_shapes``. The
    other member of each pair is derived, so consumers may use whichever
    vocabulary suits them.

    Parameters
    ----------
    frequencies:
        Natural frequencies in Hz, shape ``(m,)``, ascending.
    shapes:
        Mode shapes, shape ``(ndof, m)``; column ``j`` corresponds to
        ``frequencies[j]``. Real for undamped FE modes, complex allowed for
        imported/experimental modes. Solver results span the *full* model DOF
        space, with zeros at the constrained DOFs.
    dof_map:
        Meaning of the ``ndof`` rows. ``None`` when the producer has no nodal
        interpretation for them (e.g. modes of bare ``(K, M)`` matrices);
        :mod:`openfemlab.io` and :mod:`openfemlab.correlation` require one.
    meta:
        Provenance: producing solver, normalization, units, timestamps.
    eigenvalues:
        ``omega^2`` in ascending order (rigid-body modes clipped to exactly 0),
        as an alternative to ``frequencies``.
    mode_shapes:
        Alternative spelling of ``shapes``.
    free_dofs:
        Equation numbers the producer actually solved for, if it partitioned.
    normalization:
        Which scaling was applied (``"mass"``, ``"max"`` or ``"none"``).
    system:
        The :class:`~openfemlab.core.assembly.AssembledSystem` behind the
        result; required by the generalized-quantity properties.
    num_condensed_dofs:
        How many massless DOFs were statically condensed before the eigensolve
        and recovered afterwards.
    """

    __slots__ = (
        "frequencies",
        "eigenvalues",
        "shapes",
        "dof_map",
        "meta",
        "free_dofs",
        "normalization",
        "system",
        "num_condensed_dofs",
    )

    def __init__(
        self,
        frequencies: npt.ArrayLike | None = None,
        shapes: npt.ArrayLike | None = None,
        dof_map: DofMap | None = None,
        meta: dict[str, Any] | None = None,
        *,
        eigenvalues: npt.ArrayLike | None = None,
        mode_shapes: npt.ArrayLike | None = None,
        free_dofs: npt.ArrayLike | None = None,
        normalization: str = "mass",
        system: AssembledSystem | None = None,
        num_condensed_dofs: int = 0,
    ) -> None:
        if (frequencies is None) == (eigenvalues is None):
            raise ValueError(
                "provide exactly one of 'frequencies' [Hz] or 'eigenvalues' [omega^2]"
            )
        if (shapes is None) == (mode_shapes is None):
            raise ValueError("provide exactly one of 'shapes' or 'mode_shapes'")

        if eigenvalues is None:
            self.frequencies = np.asarray(frequencies, dtype=np.float64)
            self.eigenvalues = (_TWO_PI * self.frequencies) ** 2
        else:
            self.eigenvalues = np.asarray(eigenvalues, dtype=np.float64)
            self.frequencies = np.sqrt(np.clip(self.eigenvalues, 0.0, None)) / _TWO_PI
        if self.frequencies.ndim != 1:
            raise ValueError("the spectrum must be 1-D (m,)")

        self.shapes = np.asarray(shapes if shapes is not None else mode_shapes)
        if self.shapes.ndim != 2:
            raise ValueError("shapes must be 2-D (ndof, m)")
        if self.shapes.shape[1] != self.frequencies.size:
            raise ValueError(
                f"shapes {self.shapes.shape} inconsistent with m={self.frequencies.size}"
            )
        if dof_map is not None and self.shapes.shape[0] != dof_map.ndof:
            raise ValueError(
                f"shapes {self.shapes.shape} inconsistent with "
                f"ndof={dof_map.ndof}, m={self.frequencies.size}"
            )

        self.dof_map = dof_map
        self.meta = dict(meta) if meta is not None else {}
        self.free_dofs = None if free_dofs is None else np.asarray(free_dofs, dtype=int)
        self.normalization = normalization
        self.system = system
        self.num_condensed_dofs = int(num_condensed_dofs)

    # ------------------------------------------------------------- spectrum

    @property
    def mode_shapes(self) -> npt.NDArray[np.float64] | npt.NDArray[np.complex128]:
        """Solver-side spelling of :attr:`shapes`."""
        return self.shapes

    @property
    def n_modes(self) -> int:
        return int(self.frequencies.size)

    @property
    def num_modes(self) -> int:
        """Solver-side spelling of :attr:`n_modes`."""
        return self.n_modes

    @property
    def angular_frequencies(self) -> npt.NDArray[np.float64]:
        """Circular natural frequencies ``omega`` [rad/s]."""
        return np.sqrt(np.clip(self.eigenvalues, 0.0, None))

    @property
    def periods(self) -> npt.NDArray[np.float64]:
        """Modal periods [s]; ``inf`` for rigid-body modes."""
        with np.errstate(divide="ignore"):
            return np.where(self.frequencies > 0.0, 1.0 / self.frequencies, np.inf)

    @property
    def rigid_body_modes(self) -> npt.NDArray[np.bool_]:
        """Boolean mask flagging (numerically) zero-frequency modes."""
        scale = float(np.max(np.abs(self.eigenvalues))) if self.n_modes else 0.0
        return self.eigenvalues <= max(RIGID_BODY_TOL * scale, 0.0)

    @property
    def is_rigid(self) -> npt.NDArray[np.bool_]:
        """MS-1.5 spelling of :attr:`rigid_body_modes`."""
        return self.rigid_body_modes

    def mode(self, index: int) -> np.ndarray:
        """Mode shape ``index`` as a full-length DOF vector."""
        return self.shapes[:, index]

    # ------------------------------------------------ generalized quantities

    def _assembled_system(self) -> AssembledSystem:
        if self.system is None:
            raise SolverError(
                "modal result carries no assembled system; solve from a Model or system"
            )
        return self.system

    def _mass_matrix(self):
        return self._assembled_system().M

    @property
    def modal_masses(self) -> np.ndarray:
        """Generalized masses ``diag(phi^T M phi)`` (all ones for mass normalization)."""
        M = self._mass_matrix()
        return np.einsum("ij,ij->j", self.shapes, M @ self.shapes)

    @property
    def modal_stiffnesses(self) -> np.ndarray:
        """Generalized stiffnesses ``diag(phi^T K phi) = lambda * modal mass``."""
        K = self._assembled_system().K
        return np.einsum("ij,ij->j", self.shapes, K @ self.shapes)

    def orthogonality_error(self) -> float:
        """Max off-diagonal magnitude of ``phi^T M phi`` (a solver quality check)."""
        M = self._mass_matrix()
        gram = self.shapes.T @ (M @ self.shapes)
        off = gram - np.diag(np.diag(gram))
        return float(np.max(np.abs(off))) if off.size else 0.0

    def _influence_vector(self, direction: DOF | str | int) -> np.ndarray:
        system = self._assembled_system()
        if system.dof_types is None:
            raise SolverError("participation factors need an assembled system with DOF types")
        target = DOF.parse(direction)
        vector = np.zeros(system.num_dofs, dtype=float)
        vector[np.asarray(system.dof_types) == int(target)] = 1.0
        vector[system.constrained_dofs] = 0.0
        return vector

    def participation_factors(self, direction: DOF | str | int = DOF.UX) -> np.ndarray:
        """Modal participation factors ``L_j = phi_j^T M r / (phi_j^T M phi_j)``."""
        M = self._mass_matrix()
        r = self._influence_vector(direction)
        numerator = self.shapes.T @ (M @ r)
        return numerator / self.modal_masses

    def effective_masses(self, direction: DOF | str | int = DOF.UX) -> np.ndarray:
        """Effective modal masses ``L_j^2 * m_j``; they sum to the total mass."""
        factors = self.participation_factors(direction)
        return factors**2 * self.modal_masses

    # ---------------------------------------------------------------- output

    def with_dof_map(
        self,
        dof_map: DofMap,
        *,
        meta: dict[str, Any] | None = None,
    ) -> ModalResult:
        """Same result, reinterpreted through ``dof_map``, with ``meta`` merged in.

        This is how a solver-produced result becomes exportable without going
        through a second result type: nothing is recomputed and the solver
        provenance (eigenvalues, normalization, assembled system) is kept.
        """
        merged = dict(self.meta)
        if meta:
            merged.update(meta)
        return ModalResult(
            eigenvalues=self.eigenvalues,
            shapes=self.shapes,
            dof_map=dof_map,
            meta=merged,
            free_dofs=self.free_dofs,
            normalization=self.normalization,
            system=self.system,
            num_condensed_dofs=self.num_condensed_dofs,
        )

    def summary(self, max_rows: int = 20) -> str:
        lines = [
            f"{'mode':>5} {'f [Hz]':>14} {'omega [rad/s]':>16} {'lambda':>16}",
            "-" * 55,
        ]
        omega = self.angular_frequencies
        for i in range(min(self.n_modes, max_rows)):
            lines.append(
                f"{i + 1:>5} {self.frequencies[i]:>14.6g} "
                f"{omega[i]:>16.6g} {self.eigenvalues[i]:>16.6g}"
            )
        if self.n_modes > max_rows:
            lines.append(f"... {self.n_modes - max_rows} more modes")
        return "\n".join(lines)

    def __repr__(self) -> str:
        lo = float(self.frequencies[0]) if self.n_modes else float("nan")
        hi = float(self.frequencies[-1]) if self.n_modes else float("nan")
        return f"ModalResult(n_modes={self.n_modes}, f=[{lo:.4g}..{hi:.4g}] Hz)"


@dataclass(slots=True)
class TestData:
    """Experimental modal model measured on a (sparse) sensor set.

    Same layout as :class:`ModalResult` plus modal damping and sensor
    geometry. ``dof_map`` refers to the *test* geometry; matching against an
    FE model is done in ``openfemlab.correlation``.
    """

    frequencies: npt.NDArray[np.float64]
    shapes: npt.NDArray[np.float64] | npt.NDArray[np.complex128]
    dof_map: DofMap
    damping: npt.NDArray[np.float64] | None = None  # modal damping ratios (m,)
    geometry: npt.NDArray[np.float64] | None = None  # sensor coords (n_meas, 3)
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.frequencies = np.asarray(self.frequencies, dtype=np.float64)
        self.shapes = np.asarray(self.shapes)
        if self.shapes.shape != (self.dof_map.ndof, self.frequencies.size):
            raise ValueError("shapes inconsistent with dof_map/frequencies")

    @property
    def n_modes(self) -> int:
        return self.frequencies.size
