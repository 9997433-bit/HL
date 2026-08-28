"""Design variables: sizing scalars shared with updating, plus shape-basis hooks.

Sizing variables *are* updating parameters.  A model that was calibrated with
:class:`~openfemlab.updating.updater.ModelUpdater` can be optimized without
re-declaring anything: the same :class:`~openfemlab.updating.parameters.UpdatableParameter`
objects (bounds, log scaling, finite-difference steps, element targets) define
the sizing design space, and the optimizer walks the same *design space*
(identity for linear parameters, ``log(value)`` for logarithmic ones).

Shape variables are amplitudes of node-coordinate perturbation fields
(mesh-morphing basis vectors)::

    X(a) = X_0 + sum_j a_j V_j            V_j : (n_nodes, 3) velocity field

The linear morph and its geometry gradient ``dX/da_j = V_j`` are exact and
implemented here.  Pass the FE :class:`~openfemlab.core.model.Model` as
``geometry=`` to :class:`~openfemlab.optimization.sizing.ModalDesignEvaluator`
(or :func:`~openfemlab.optimization.sizing.compile_sizing_problem`) so each
design point remeshes ``X = X0 + Σ a_j V_j`` before the modal solve; response
gradients then use tracked finite differences.  Analytic geometric ``dK/da``
remains a follow-on.

:class:`DesignSpace` concatenates both kinds into one bounded design vector
``x = [x_sizing, a_shape]`` with a single bounds/clip/step/chain-rule contract,
which is all the problem compiler and the backends ever see.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from ..exceptions import OptimizationError
from ..updating.parameters import ParameterSet, UpdatableParameter

__all__ = ["ShapeVariable", "DesignSpace"]


@dataclass
class ShapeVariable:
    """Amplitude of one node-coordinate perturbation field (mesh morph).

    Parameters
    ----------
    name:
        Unique identifier; also the key under which the amplitude appears in
        the physical parameter mapping handed to the model callable.
    basis:
        ``(n_nodes, 3)`` displacement field ``V_j`` applied per unit amplitude.
        This is the design *velocity field* of shape optimization; the geometry
        gradient of the morph is exactly ``dX/da = basis``.
    value:
        Current amplitude (0.0 means "as designed").
    lower, upper:
        Box constraints on the amplitude.
    step:
        Absolute finite-difference step for gradient fallbacks.
    """

    name: str
    basis: np.ndarray
    value: float = 0.0
    lower: float = -1.0
    upper: float = 1.0
    step: float = 1.0e-6
    initial: float = field(init=False)

    def __post_init__(self) -> None:
        self.basis = np.asarray(self.basis, dtype=float)
        if self.basis.ndim != 2 or self.basis.shape[1] != 3:
            raise OptimizationError(
                f"shape variable {self.name!r}: basis must be (n_nodes, 3), "
                f"got {self.basis.shape}"
            )
        if not self.name:
            raise OptimizationError("shape variable name must not be empty")
        if self.lower > self.upper:
            raise OptimizationError(
                f"{self.name}: lower bound {self.lower} exceeds upper {self.upper}"
            )
        if not self.lower <= self.value <= self.upper:
            raise OptimizationError(
                f"{self.name}: initial amplitude {self.value} outside "
                f"[{self.lower}, {self.upper}]"
            )
        if self.step <= 0.0:
            raise OptimizationError(f"{self.name}: finite-difference step must be positive")
        self.initial = float(self.value)

    @property
    def n_nodes(self) -> int:
        return int(self.basis.shape[0])

    def displacement(self, amplitude: float | None = None) -> np.ndarray:
        """Node displacement field ``a * V`` for an amplitude (current by default)."""
        a = self.value if amplitude is None else float(amplitude)
        return a * self.basis


class DesignSpace:
    """Unified bounded design vector over sizing parameters and shape amplitudes.

    The vector layout is ``x = [sizing design values..., shape amplitudes...]``
    where the sizing block uses the *design-space* mapping of
    :class:`~openfemlab.updating.parameters.ParameterSet` (log for log-scaled
    parameters) and the shape block is linear.

    Parameters
    ----------
    sizing:
        Updating-style parameters (fixed ones are excluded from the vector).
    shape:
        Shape-basis variables; all bases must agree on ``n_nodes``.
    """

    def __init__(
        self,
        sizing: ParameterSet | Sequence[UpdatableParameter] | None = None,
        shape: Sequence[ShapeVariable] | None = None,
    ) -> None:
        if sizing is None:
            self.sizing: ParameterSet | None = None
        elif isinstance(sizing, ParameterSet):
            self.sizing = sizing
        else:
            self.sizing = ParameterSet(sizing)
        self.shape: list[ShapeVariable] = list(shape or [])

        names = ([] if self.sizing is None else self.sizing.free_names) + [
            v.name for v in self.shape
        ]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise OptimizationError(f"duplicate design variable names: {sorted(duplicates)}")
        if not names:
            raise OptimizationError("a design space needs at least one free variable")
        node_counts = {v.n_nodes for v in self.shape}
        if len(node_counts) > 1:
            raise OptimizationError(
                f"shape bases disagree on the node count: {sorted(node_counts)}"
            )
        self._names = names

    # ------------------------------------------------------------- structure

    @property
    def names(self) -> list[str]:
        return list(self._names)

    @property
    def n_sizing(self) -> int:
        return 0 if self.sizing is None else len(self.sizing.free)

    @property
    def n_shape(self) -> int:
        return len(self.shape)

    @property
    def n_variables(self) -> int:
        return self.n_sizing + self.n_shape

    def split(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """``(sizing design block, shape amplitude block)`` of a design vector."""
        x = self._as_vector(x)
        return x[: self.n_sizing], x[self.n_sizing :]

    def _as_vector(self, x: Sequence[float] | np.ndarray) -> np.ndarray:
        array = np.asarray(x, dtype=float).ravel()
        if array.size != self.n_variables:
            raise OptimizationError(
                f"design vector has {array.size} entries, expected {self.n_variables}"
            )
        return array

    # ----------------------------------------------------------- vector maps

    def x0(self) -> np.ndarray:
        """Current design vector."""
        sizing = (
            np.empty(0) if self.sizing is None else self.sizing.design_values()
        )
        return np.concatenate([sizing, [v.value for v in self.shape]])

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """``(lower, upper)`` box bounds in design space."""
        if self.sizing is None:
            lo = np.empty(0)
            hi = np.empty(0)
        else:
            lo, hi = self.sizing.design_bounds()
        lo = np.concatenate([lo, [v.lower for v in self.shape]])
        hi = np.concatenate([hi, [v.upper for v in self.shape]])
        return lo, hi

    def steps(self) -> np.ndarray:
        """Finite-difference perturbations per design variable."""
        sizing = np.empty(0) if self.sizing is None else self.sizing.design_steps()
        return np.concatenate([sizing, [v.step for v in self.shape]])

    def clip(self, x: Sequence[float] | np.ndarray) -> np.ndarray:
        """Project a design vector onto the box bounds (AC-OPT-003 contract)."""
        lo, hi = self.bounds()
        return np.clip(self._as_vector(x), lo, hi)

    def chain(self, x: Sequence[float] | np.ndarray) -> np.ndarray:
        """Diagonal ``dp/dx`` converting physical-space gradients to design space.

        ``p`` for log-scaled sizing parameters is ``exp(x)``, so ``dp/dx = p``;
        every other variable is identity.  Multiply a ``dr/dp`` row by this
        vector to obtain ``dr/dx``.
        """
        x = self._as_vector(x)
        chain = np.ones(self.n_variables)
        if self.sizing is not None:
            for k, parameter in enumerate(self.sizing.free):
                if parameter.log_scaled:
                    chain[k] = parameter.from_design(float(x[k]))
        return chain

    # -------------------------------------------------------- physical state

    def to_physical(self, x: Sequence[float] | np.ndarray) -> dict[str, float]:
        """Physical parameter mapping for a design vector, without mutating state.

        Sizing entries follow the updating convention (scaling factors keyed by
        parameter name, fixed parameters included at their held values); shape
        amplitudes are appended under their variable names.  The result is what
        the model callable receives, so the contract is identical to
        :class:`~openfemlab.updating.updater.ModelUpdater`'s.
        """
        sizing_x, shape_a = self.split(self._as_vector(x))
        physical: dict[str, float] = (
            {} if self.sizing is None else self.sizing.design_to_physical(sizing_x)
        )
        for variable, amplitude in zip(self.shape, shape_a, strict=True):
            physical[variable.name] = float(
                min(max(amplitude, variable.lower), variable.upper)
            )
        return physical

    def morph_displacement(self, x: Sequence[float] | np.ndarray) -> np.ndarray | None:
        """Total node displacement field ``sum_j a_j V_j``; None without shape vars."""
        if not self.shape:
            return None
        _, amplitudes = self.split(self._as_vector(x))
        out = np.zeros_like(self.shape[0].basis)
        for variable, amplitude in zip(self.shape, amplitudes, strict=True):
            out += variable.displacement(float(amplitude))
        return out

    def apply_to_coordinates(
        self, coordinates: np.ndarray, x: Sequence[float] | np.ndarray
    ) -> np.ndarray:
        """Morphed node coordinates ``X_0 + sum_j a_j V_j``."""
        coords = np.asarray(coordinates, dtype=float)
        displacement = self.morph_displacement(x)
        if displacement is None:
            return coords
        if coords.shape != displacement.shape:
            raise OptimizationError(
                f"coordinates {coords.shape} do not match the shape basis "
                f"{displacement.shape}"
            )
        return coords + displacement

    def apply(self, x: Sequence[float] | np.ndarray) -> dict[str, float]:
        """Write a design vector back into the variables (mutating), return physicals."""
        sizing_x, shape_a = self.split(self._as_vector(x))
        if self.sizing is not None:
            self.sizing.apply_design(sizing_x)
        for variable, amplitude in zip(self.shape, shape_a, strict=True):
            variable.value = float(min(max(amplitude, variable.lower), variable.upper))
        return self.to_physical(self._as_vector(x))

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"DesignSpace(n_sizing={self.n_sizing}, n_shape={self.n_shape}, "
            f"names={self._names})"
        )
