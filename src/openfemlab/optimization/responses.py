"""Structural responses, objectives and constraints with a gradient interface.

A :class:`Response` maps one evaluated design point (:class:`DesignState`) to a
scalar, and optionally to its analytic gradient with respect to the *physical*
parameters.  The problem compiler converts physical gradients to design space
with :meth:`~openfemlab.optimization.variables.DesignSpace.chain` and falls
back to tracked central finite differences when :meth:`Response.gradient`
returns ``None`` (spec MS-5.2 forbids numerical differentiation *inside* the
backend; the fallback is an explicit, mode-tracked jacobian owned by this
package).

One modal solve per design point is the cardinal rule: every response reads
the shared, cached :class:`DesignState` produced by the evaluator in
:mod:`openfemlab.optimization.sizing` instead of triggering solves itself.

Mode-indexed responses (:class:`NaturalFrequency`) address modes in the
*tracked* order: ``state.tracking`` re-labels the current iterate's modes to
follow the reference (baseline or previous accepted iterate) shapes by MAC,
so a constraint on "mode 1" stays attached to the physical bending branch
even when modes cross along the design path (AC-OPT-004).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

from ..exceptions import OptimizationError
from ..updating.sensitivity import ModalData

__all__ = [
    "DesignState",
    "Response",
    "TotalMass",
    "NaturalFrequency",
    "Objective",
    "Constraint",
    "frequency_floor",
]


@dataclass
class DesignState:
    """Everything known about one evaluated design point.

    Produced once per design vector by the evaluator and shared by the
    objective and all constraints, so the modal solve is never repeated.

    Attributes
    ----------
    x:
        Design vector in design space.
    parameters:
        Physical parameter mapping handed to the model callable.
    modal:
        Modal solution at this point (None until a modal response is needed).
    tracking:
        ``tracking[i]`` is the column of ``modal`` following reference mode
        ``i`` (MAC tracking; identity when shapes are unavailable).
    gradients:
        Analytic ``(n_modes, n_params)`` frequency sensitivities ``df/dp`` in
        the *reference* mode order, or None when no analytic provider exists.
    mass:
        Total structural mass, when the model exposes its mass matrix.
    mass_gradient:
        Analytic ``dm/dp`` per physical parameter, or None.
    """

    x: np.ndarray
    parameters: dict[str, float]
    modal: ModalData | None = None
    tracking: np.ndarray | None = None
    gradients: np.ndarray | None = None
    mass: float | None = None
    mass_gradient: np.ndarray | None = None
    meta: dict = field(default_factory=dict)

    def tracked_frequency(self, mode: int) -> float:
        """Frequency [Hz] of reference mode ``mode`` at this design point."""
        if self.modal is None:
            raise OptimizationError("design state carries no modal solution")
        if self.tracking is not None and mode >= self.tracking.size:
            raise OptimizationError(
                f"mode {mode} outside the {self.tracking.size} tracked reference modes"
            )
        column = mode if self.tracking is None else int(self.tracking[mode])
        if not 0 <= column < self.modal.n_modes:
            raise OptimizationError(
                f"tracked mode {mode} maps to column {column}, outside the "
                f"{self.modal.n_modes} solved modes"
            )
        return float(self.modal.frequencies[column])


class Response(ABC):
    """One scalar structural response of a design point."""

    #: Human-readable identifier used in reports and constraint names.
    name: str = "response"

    @abstractmethod
    def value(self, state: DesignState) -> float:
        """Response value at an evaluated design point."""

    def gradient(self, state: DesignState) -> np.ndarray | None:
        """Analytic ``d(value)/dp`` over the physical parameters, or ``None``.

        Returning ``None`` requests the tracked finite-difference fallback.
        Implementations must return the gradient in the parameter order of
        ``state.parameters`` restricted to the design variables.
        """
        return None


class TotalMass(Response):
    """Total structural mass, the canonical sizing objective (spec MS-5.1).

    Reads ``state.mass`` / ``state.mass_gradient`` as filled by the evaluator:
    for an affine parameterisation ``M(p) = M_0 + sum_j p_j M_j`` the analytic
    gradient is exact, ``dm/dp_j = mass(M_j)``.
    """

    name = "total_mass"

    def value(self, state: DesignState) -> float:
        if state.mass is None:
            raise OptimizationError(
                "the model does not expose its mass matrix; TotalMass needs a "
                "parametric model with an 'assemble' method"
            )
        return float(state.mass)

    def gradient(self, state: DesignState) -> np.ndarray | None:
        return state.mass_gradient


class NaturalFrequency(Response):
    """Natural frequency [Hz] of one MAC-tracked mode.

    Parameters
    ----------
    mode:
        0-based index into the *reference* mode order (the baseline design's
        modes).  Tracking keeps the index attached to the physical branch
        across mode crossings (AC-OPT-004).
    """

    def __init__(self, mode: int) -> None:
        if mode < 0:
            raise OptimizationError("mode index must be non-negative")
        self.mode = int(mode)
        self.name = f"f{self.mode + 1}"

    def value(self, state: DesignState) -> float:
        return state.tracked_frequency(self.mode)

    def gradient(self, state: DesignState) -> np.ndarray | None:
        if state.gradients is None:
            return None
        if self.mode >= state.gradients.shape[0]:
            raise OptimizationError(
                f"analytic sensitivities cover {state.gradients.shape[0]} modes; "
                f"mode {self.mode} was requested"
            )
        return np.asarray(state.gradients[self.mode, :], dtype=float)


@dataclass
class Objective:
    """Minimization objective: ``minimize scale * response`` (``scale < 0`` maximizes)."""

    response: Response
    scale: float = 1.0

    def __post_init__(self) -> None:
        if self.scale == 0.0:
            raise OptimizationError("objective scale must be nonzero")

    @property
    def name(self) -> str:
        return self.response.name

    def value(self, state: DesignState) -> float:
        return self.scale * self.response.value(state)

    def gradient(self, state: DesignState) -> np.ndarray | None:
        g = self.response.gradient(state)
        return None if g is None else self.scale * g


@dataclass
class Constraint:
    """Scalar inequality constraint in standardized ``g(x) <= 0`` form.

    ``kind=">="`` states ``response >= bound``, ``"<="`` states
    ``response <= bound``.  With ``normalize=True`` (default, requires a
    nonzero bound) the standardized function is dimensionless, e.g. the spec
    MS-5.1 frequency floor ``f_1 >= f_min`` becomes ``g = 1 - f_1/f_min <= 0``,
    which keeps constraint scales comparable across physical quantities.
    """

    response: Response
    bound: float
    kind: str = ">="
    normalize: bool = True
    label: str = ""

    def __post_init__(self) -> None:
        if self.kind not in {">=", "<="}:
            raise OptimizationError(f"unknown constraint kind {self.kind!r}")
        if self.normalize and self.bound == 0.0:
            raise OptimizationError("normalized constraints need a nonzero bound")
        if not self.label:
            self.label = f"{self.response.name} {self.kind} {self.bound:g}"

    @property
    def name(self) -> str:
        return self.label

    def _sign(self) -> float:
        return -1.0 if self.kind == ">=" else 1.0

    def standardized(self, state: DesignState) -> float:
        """Constraint value in ``g <= 0`` form (feasible iff nonpositive)."""
        v = self.response.value(state)
        sign = self._sign()
        if self.normalize:
            return sign * (v / self.bound - 1.0)
        return sign * (v - self.bound)

    def standardized_gradient(self, state: DesignState) -> np.ndarray | None:
        """Gradient of :meth:`standardized` over the physical parameters."""
        g = self.response.gradient(state)
        if g is None:
            return None
        factor = self._sign() / self.bound if self.normalize else self._sign()
        return factor * g

    def is_active(self, state: DesignState, tolerance: float = 1.0e-6) -> bool:
        """Whether the constraint is active (|g| within tolerance) at a point."""
        return abs(self.standardized(state)) <= tolerance


def frequency_floor(mode: int, f_min: float) -> Constraint:
    """Spec MS-5.1 reference constraint: ``f_mode >= f_min`` as ``1 - f/f_min <= 0``."""
    if f_min <= 0.0:
        raise OptimizationError("frequency floor must be positive")
    return Constraint(NaturalFrequency(mode), bound=float(f_min), kind=">=")
