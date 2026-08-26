"""Model reduction and mode-shape expansion between FE and sensor space (MS-2.1).

Correlation needs both mode sets on one DOF set. :mod:`~openfemlab.correlation.align`
covers the easy direction — pick the instrumented rows out of the FE shapes — but a
real test-analysis model also needs the *matrices* on the sensor set (for
mass-weighted metrics and pseudo-orthogonality) and the measured shapes back in the
full FE space (for the updating shape residual and animation). Both directions are a
single ``(n, m)`` transformation ``T`` with ``u_full ≈ T u_master``:

- **Guyan** (static condensation, :func:`guyan_reduction`) — neglects slave-DOF
  inertia, ``T_s = [I; -K_ss⁻¹ K_sm]``. Exact when the slave DOFs are massless,
  which is why the eigensolver already uses this kernel
  (``solver/modal.py::_MasslessCondensation``); otherwise accurate for the lowest
  modes only.
- **IRS** (:func:`irs_reduction`) — one inertia correction on top of Guyan, so the
  slave DOFs see a first-order dynamic contribution.
- **SEREP** (:func:`serep_basis`) — ``T = Φ_full (Φ_sensor)⁺`` over a chosen mode
  band. Reproduces those modes *exactly* in the reduced model, which makes it the
  expansion operator of choice (AC-CORR-006).

The reduced mass matrix ``M_r = Tᵀ M T`` is the TAM mass: feeding it to
:func:`~openfemlab.correlation.mac.orthogonality` (or as ``weights`` to
:func:`~openfemlab.correlation.mac.mac`) gives pseudo-orthogonality and the
mass-weighted MAC on the sensor set.

The master set is given either as explicit row indices or as anything carrying
``rows`` and ``signs`` — :class:`~openfemlab.workflow.sensors.SensorMap` is the
intended source. Passing the map rather than its ``rows`` puts the basis in
*channel* coordinates: an accelerometer mounted against the model axis reads
``q_i = s_i u[row_i]``, so ``T`` is post-scaled by ``diag(1/s)`` and reducing a
shape applies ``s``, which is exactly what ``SensorMap.reduce`` returns.
Everything built from the basis — the TAM mass, expanded shapes — is then
consistent with measured data as the rig delivers it, signs included.

Round-2 scope note (R2-T03): Craig-Bampton CMS and geometry-based sensor mapping
stay out.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
import numpy.typing as npt

from openfemlab.correlation.mac import as_columns
from openfemlab.exceptions import SolverError

__all__ = [
    "ReductionBasis",
    "guyan_reduction",
    "irs_reduction",
    "serep_basis",
    "expand_shapes",
    "tam_mass",
]


class SensorRows(Protocol):
    """The part of :class:`~openfemlab.workflow.sensors.SensorMap` used here."""

    rows: tuple[int, ...]
    signs: tuple[float, ...]


#: Master DOFs as plain rows, or as a sensor map that also carries orientations.
Masters = Sequence[int] | npt.NDArray[np.intp] | SensorRows


def _dense(matrix: Any, name: str) -> npt.NDArray[np.float64]:
    """Densify a possibly sparse square matrix and check it is square."""
    dense = matrix.toarray() if hasattr(matrix, "toarray") else np.asarray(matrix, dtype=float)
    dense = np.asarray(dense, dtype=float)
    if dense.ndim != 2 or dense.shape[0] != dense.shape[1]:
        raise ValueError(f"{name} must be a square matrix, got shape {dense.shape}")
    return dense


def _rows_and_signs(master: Masters):
    """Split a master specification into row indices and channel signs.

    A sensor map contributes both; a plain index sequence has no orientation
    information, so the signs come back as ``None`` and the basis stays in
    master-DOF coordinates.
    """
    rows = getattr(master, "rows", None)
    if rows is None:
        return master, None
    signs = np.asarray(getattr(master, "signs", None) or (), dtype=float).ravel()
    if signs.size == 0:
        return rows, None
    if signs.size != len(tuple(rows)):
        raise ValueError("signs must have one entry per master DOF")
    if np.any(signs == 0.0):
        raise ValueError("sensor signs must be nonzero")
    return rows, signs


def _oriented(
    transformation: npt.NDArray[np.float64],
    master: npt.NDArray[np.intp],
    signs: npt.NDArray[np.float64] | None,
    kind: str,
) -> ReductionBasis:
    """Wrap a master-coordinate ``T`` as a basis, in channel coordinates if signed."""
    if signs is not None:
        transformation = transformation / signs[None, :]
    return ReductionBasis(
        transformation=transformation, master=master, kind=kind, signs=signs
    )


def _master_slave(ndof: int, master: Sequence[int] | npt.NDArray[np.intp]):
    """Validate the master rows and return ``(master, slave)`` index arrays."""
    rows = np.asarray(master, dtype=np.intp).ravel()
    if rows.size == 0:
        raise ValueError("at least one master DOF is required")
    if np.unique(rows).size != rows.size:
        raise ValueError("master DOFs must be unique")
    if rows.min() < 0 or rows.max() >= ndof:
        raise IndexError(f"master DOF indices out of range for {ndof} DOFs")
    slave = np.setdiff1d(np.arange(ndof, dtype=np.intp), rows)
    return rows, slave


@dataclass(frozen=True)
class ReductionBasis:
    """A transformation ``u_full = T u_master`` plus the rows it was built for.

    Attributes
    ----------
    transformation:
        ``(n, m)`` matrix mapping master (sensor) coordinates to the full FE
        space. Its master rows form the identity for the condensation methods,
        so reducing and expanding are mutually consistent.
    master:
        Full-space row index of each master DOF, in master order.
    kind:
        ``"guyan"``, ``"irs"`` or ``"serep"`` — recorded for reports and so a
        consumer can tell an exact-in-band basis from an approximate one.
    signs:
        Channel orientation per master DOF when the basis was built from a
        sensor map, else ``None``. When present the reduced coordinates are
        measured channels rather than raw model DOFs.
    """

    transformation: npt.NDArray[np.float64]
    master: npt.NDArray[np.intp]
    kind: str
    signs: npt.NDArray[np.float64] | None = None

    @property
    def n_full(self) -> int:
        return int(self.transformation.shape[0])

    @property
    def n_master(self) -> int:
        return int(self.transformation.shape[1])

    def __repr__(self) -> str:
        oriented = "" if self.signs is None else ", oriented"
        return (
            f"ReductionBasis(kind={self.kind!r}, n_full={self.n_full}, "
            f"n_master={self.n_master}{oriented})"
        )

    def reduce_matrix(self, matrix: Any) -> npt.NDArray[np.float64]:
        """Project a full-space system matrix: ``Tᵀ A T``, symmetrized."""
        A = _dense(matrix, "matrix")
        if A.shape[0] != self.n_full:
            raise ValueError(f"matrix has {A.shape[0]} rows but the basis spans {self.n_full}")
        reduced = self.transformation.T @ A @ self.transformation
        return 0.5 * (reduced + reduced.T)

    def reduce_shapes(self, shapes: Any) -> npt.NDArray[Any]:
        """Pick the master rows out of full-space shapes ``(n, k)``.

        With channel signs the picked rows are oriented as the sensors read
        them, so the result is directly comparable to measured shapes.
        """
        full = as_columns(shapes, "shapes")
        if full.shape[0] != self.n_full:
            raise ValueError(f"shapes have {full.shape[0]} rows but the basis spans {self.n_full}")
        picked = full[self.master, :]
        return picked if self.signs is None else picked * self.signs[:, None]

    def expand(self, shapes: Any) -> npt.NDArray[Any]:
        """Expand master-space shapes ``(m, k)`` to the full space: ``T Φ_m``."""
        reduced = as_columns(shapes, "shapes")
        if reduced.shape[0] != self.n_master:
            raise ValueError(
                f"shapes have {reduced.shape[0]} rows but the basis has "
                f"{self.n_master} master DOFs"
            )
        return self.transformation @ reduced


def _static_transformation(
    K: npt.NDArray[np.float64],
    master: npt.NDArray[np.intp],
    slave: npt.NDArray[np.intp],
) -> npt.NDArray[np.float64]:
    """``T_s`` with identity on the masters and ``-K_ss⁻¹ K_sm`` on the slaves."""
    n = K.shape[0]
    T = np.zeros((n, master.size))
    T[master, np.arange(master.size)] = 1.0
    if slave.size:
        K_ss = K[np.ix_(slave, slave)]
        K_sm = K[np.ix_(slave, master)]
        try:
            T[slave, :] = -np.linalg.solve(K_ss, K_sm)
        except np.linalg.LinAlgError as exc:
            raise SolverError(
                "cannot condense onto the master DOFs: the slave stiffness sub-matrix "
                "is singular (the slave partition contains a mechanism)"
            ) from exc
    return T


def guyan_reduction(
    stiffness: Any,
    master: Masters,
) -> ReductionBasis:
    """Static (Guyan) condensation onto ``master`` DOFs.

    Solves the slave partition of ``K u = 0`` for the slave displacements,
    ``u_s = -K_ss⁻¹ K_sm u_m``, so the reduced stiffness ``Tᵀ K T`` is exact and
    the reduced mass ``Tᵀ M T`` carries the slave inertia along the static shapes.
    Exact for the eigenproblem only when the slave DOFs are massless; otherwise it
    overestimates the frequencies, increasingly so with mode order.

    Raises
    ------
    SolverError
        When ``K_ss`` is singular.
    """
    K = _dense(stiffness, "stiffness")
    rows, signs = _rows_and_signs(master)
    master_rows, slave_rows = _master_slave(K.shape[0], rows)
    return _oriented(
        _static_transformation(K, master_rows, slave_rows), master_rows, signs, "guyan"
    )


def irs_reduction(
    stiffness: Any,
    mass: Any,
    master: Masters,
) -> ReductionBasis:
    """Improved Reduced System basis: Guyan plus one inertia correction.

    ``T_IRS = T_s + S M T_s M_r⁻¹ K_r`` with ``S`` the slave-block inverse
    stiffness (zero elsewhere) and ``K_r``/``M_r`` the Guyan-reduced matrices.
    The correction is first order in ``ω²``, so the reduced eigenvalues sit
    between the Guyan estimate and the exact ones.
    """
    K = _dense(stiffness, "stiffness")
    M = _dense(mass, "mass")
    if M.shape != K.shape:
        raise ValueError(f"mass {M.shape} and stiffness {K.shape} must have the same shape")
    rows, signs = _rows_and_signs(master)
    master_rows, slave_rows = _master_slave(K.shape[0], rows)
    T_s = _static_transformation(K, master_rows, slave_rows)

    K_r = T_s.T @ K @ T_s
    M_r = T_s.T @ M @ T_s
    S = np.zeros_like(K)
    if slave_rows.size:
        S[np.ix_(slave_rows, slave_rows)] = np.linalg.inv(K[np.ix_(slave_rows, slave_rows)])
    try:
        correction = S @ M @ T_s @ np.linalg.solve(M_r, K_r)
    except np.linalg.LinAlgError as exc:
        raise SolverError(
            "cannot form the IRS correction: the Guyan-reduced mass matrix is singular"
        ) from exc
    return _oriented(T_s + correction, master_rows, signs, "irs")


def serep_basis(
    shapes: Any,
    master: Masters,
    *,
    rcond: float | None = None,
) -> ReductionBasis:
    """SEREP basis ``T = Φ_full (Φ_master)⁺`` from a full-space mode set.

    Unlike the condensation methods this is exact — in the band spanned by
    ``shapes`` — because the reduced model is the modal model itself: any
    combination of those modes measured at the master DOFs is expanded back to
    the full space without error. Outside the band it is a projection, so the
    mode set must cover the frequency range of interest and the master set must
    be large enough (``m >= k``) to keep ``Φ_master`` full column rank, which is
    the pretest sensor-placement question (GAP-07, Round 3).

    Parameters
    ----------
    shapes:
        ``(n, k)`` full-space mode shapes, e.g. ``ModalResult.shapes``.
    master:
        Full-space rows the sensors observe, or a sensor map carrying those
        rows and their orientation signs.
    rcond:
        Cutoff passed to :func:`numpy.linalg.pinv`; the default follows NumPy.

    Raises
    ------
    SolverError
        When the master partition is rank deficient, i.e. the sensor set cannot
        distinguish the requested modes.
    """
    full = as_columns(shapes, "shapes")
    if np.iscomplexobj(full):
        raise ValueError("SEREP expects real mode shapes; use the real modal basis")
    rows, signs = _rows_and_signs(master)
    master_rows, _ = _master_slave(full.shape[0], rows)
    sensor_block = full[master_rows, :]
    if master_rows.size < full.shape[1]:
        raise SolverError(
            f"SEREP needs at least as many master DOFs as modes: {master_rows.size} "
            f"sensors for {full.shape[1]} modes"
        )
    rank = int(np.linalg.matrix_rank(sensor_block))
    if rank < full.shape[1]:
        raise SolverError(
            f"the sensor partition of the mode set has rank {rank} for {full.shape[1]} "
            "modes: those modes are indistinguishable at the chosen DOFs"
        )
    if rcond is None:
        pseudo_inverse = np.linalg.pinv(sensor_block)
    else:
        pseudo_inverse = np.linalg.pinv(sensor_block, rcond=rcond)
    return _oriented(full @ pseudo_inverse, master_rows, signs, "serep")


def expand_shapes(
    fe_shapes: Any,
    master: Masters,
    measured_shapes: Any,
    *,
    rcond: float | None = None,
) -> npt.NDArray[np.float64]:
    """Expand measured shapes from sensor DOFs to the full FE space (SEREP).

    ``Φ_test^full = Φ_fe (T Φ_fe)⁺ Φ_test`` — the MS-2.1 expansion. The measured
    rows must be ordered like ``master``; passing the
    :class:`~openfemlab.workflow.sensors.SensorMap` itself supplies that
    ordering *and* undoes the channel orientations, so shapes measured against
    the model axis expand to the same full-space result as unflipped ones.
    """
    basis = serep_basis(fe_shapes, master, rcond=rcond)
    return np.asarray(basis.expand(measured_shapes), dtype=float)


def tam_mass(basis: ReductionBasis, mass: Any) -> npt.NDArray[np.float64]:
    """Test-analysis-model mass ``Tᵀ M T`` on the master DOFs.

    The weighting matrix for pseudo-orthogonality
    (:func:`~openfemlab.correlation.mac.orthogonality`) and the mass-weighted MAC
    of MS-2.2 on the sensor set. For a mass-normalized FE mode set reduced with a
    SEREP basis built from those same modes, ``Φ_masterᵀ M_TAM Φ_master`` is the
    identity — the exactness property the AC-CORR-009 pseudo-orthogonality gate
    relies on. A Guyan or IRS TAM only approximates it, by an amount that
    depends on where the sensors sit.
    """
    return basis.reduce_matrix(mass)
