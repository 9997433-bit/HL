"""Analysis-result and test-data contracts.

These are the currency exchanged between ``modal``/``solver`` (producers),
``io`` (import/export), and ``correlation``/``updating`` (consumers). A result
carries its own :class:`~openfemlab.core.dofs.DofMap`, so it stays
interpretable when detached from the model that produced it — the property
that makes the platform solver-independent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

from openfemlab.core.dofs import DofMap


@dataclass(slots=True)
class ModalResult:
    """Eigen-solution of an undamped (or proportionally damped) model.

    Attributes
    ----------
    frequencies:
        Natural frequencies in Hz, shape ``(m,)``, ascending.
    shapes:
        Mode shapes, shape ``(ndof, m)``; column ``j`` corresponds to
        ``frequencies[j]``. Real for undamped FE modes, complex allowed for
        imported/experimental modes.
    dof_map:
        Meaning of the ``ndof`` rows.
    meta:
        Provenance: producing solver, normalization, units, timestamps.
    """

    frequencies: npt.NDArray[np.float64]
    shapes: npt.NDArray[np.float64] | npt.NDArray[np.complex128]
    dof_map: DofMap
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.frequencies = np.asarray(self.frequencies, dtype=np.float64)
        self.shapes = np.asarray(self.shapes)
        if self.shapes.ndim != 2:
            raise ValueError("shapes must be 2-D (ndof, m)")
        if self.shapes.shape != (self.dof_map.ndof, self.frequencies.size):
            raise ValueError(
                f"shapes {self.shapes.shape} inconsistent with "
                f"ndof={self.dof_map.ndof}, m={self.frequencies.size}"
            )

    @property
    def n_modes(self) -> int:
        return self.frequencies.size

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
