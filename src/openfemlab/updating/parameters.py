"""Updating parameters: bounded design variables driving an FE model.

An :class:`UpdatableParameter` is a *scaling factor* applied to a physical
property of a group of elements (stiffness, mass, ...).  Working with
dimensionless factors keeps the sensitivity matrix well scaled and makes bounds
such as "no property may change by more than 50%" easy to express.

Optimisation is carried out in *design space*: identity for linear parameters
and ``log(value)`` for logarithmic ones, the latter guaranteeing positive
physical properties whatever step the optimiser takes.

:class:`Parameter` is the declarative counterpart used by the model/IO layer: it
names a physical quantity by dotted path plus a nominal reference value, and is
turned into an :class:`UpdatableParameter` by :meth:`Parameter.to_updatable`.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

__all__ = ["ParameterType", "UpdatableParameter", "ParameterSet", "Parameter"]


class ParameterType(str, Enum):
    """Physical property a parameter scales."""

    STIFFNESS = "stiffness"
    MASS = "mass"
    DAMPING = "damping"
    GENERIC = "generic"


@dataclass
class UpdatableParameter:
    """A single bounded updating parameter.

    Parameters
    ----------
    name:
        Unique identifier, also used as the key handed to the model callable.
    value:
        Current scaling factor (1.0 means "as designed").
    lower, upper:
        Box constraints on ``value``.
    kind:
        Which property the factor scales, see :class:`ParameterType`.
    targets:
        Element ids, property ids or group names the factor applies to.  The
        model callable decides how to interpret them; the updater only carries
        them along.
    fixed:
        When True the parameter is held at its current value.
    step:
        Relative finite-difference step used to build the sensitivity matrix.
    log_scaled:
        Optimise ``log(value)`` instead of ``value``.
    """

    name: str
    value: float = 1.0
    lower: float = 0.5
    upper: float = 2.0
    kind: ParameterType = ParameterType.STIFFNESS
    targets: tuple[object, ...] = ()
    fixed: bool = False
    step: float = 1.0e-4
    log_scaled: bool = False
    initial: float = field(init=False)

    def __post_init__(self) -> None:
        self.kind = ParameterType(self.kind)
        self.targets = tuple(self.targets)
        self.value = float(self.value)
        self.lower = float(self.lower)
        self.upper = float(self.upper)
        if not self.name:
            raise ValueError("parameter name must not be empty")
        if self.lower > self.upper:
            raise ValueError(f"{self.name}: lower bound {self.lower} exceeds upper {self.upper}")
        if not self.lower <= self.value <= self.upper:
            raise ValueError(
                f"{self.name}: initial value {self.value} outside bounds "
                f"[{self.lower}, {self.upper}]"
            )
        if self.log_scaled and self.lower <= 0.0:
            raise ValueError(f"{self.name}: log-scaled parameters need a positive lower bound")
        if self.step <= 0.0:
            raise ValueError(f"{self.name}: finite-difference step must be positive")
        self.initial = self.value

    def clip(self, value: float) -> float:
        """Return ``value`` projected onto the parameter bounds."""
        return float(min(max(value, self.lower), self.upper))

    def set_value(self, value: float) -> float:
        self.value = self.clip(value)
        return self.value

    def reset(self) -> None:
        self.value = self.initial

    @property
    def change_pct(self) -> float:
        """Change with respect to the initial value, in percent."""
        if self.initial == 0.0:
            return math.inf if self.value != 0.0 else 0.0
        return 100.0 * (self.value - self.initial) / self.initial

    def to_design(self, value: float | None = None) -> float:
        """Map a physical value to the optimiser's design space."""
        v = self.value if value is None else float(value)
        return math.log(v) if self.log_scaled else v

    def from_design(self, design_value: float) -> float:
        """Map a design-space value back to the physical scaling factor."""
        v = math.exp(design_value) if self.log_scaled else float(design_value)
        return self.clip(v)

    @property
    def design_bounds(self) -> tuple[float, float]:
        if self.log_scaled:
            return math.log(self.lower), math.log(self.upper)
        return self.lower, self.upper

    def design_step(self) -> float:
        """Finite-difference perturbation in design space."""
        if self.log_scaled:
            return self.step
        return self.step * max(abs(self.value), 1.0)

    def copy(self) -> UpdatableParameter:
        clone = UpdatableParameter(
            name=self.name,
            value=self.value,
            lower=self.lower,
            upper=self.upper,
            kind=self.kind,
            targets=self.targets,
            fixed=self.fixed,
            step=self.step,
            log_scaled=self.log_scaled,
        )
        clone.initial = self.initial
        return clone


class ParameterSet:
    """Ordered collection of :class:`UpdatableParameter` objects."""

    def __init__(self, parameters: Iterable[UpdatableParameter]) -> None:
        params = list(parameters)
        if not params:
            raise ValueError("a parameter set needs at least one parameter")
        names = [p.name for p in params]
        duplicates = {n for n in names if names.count(n) > 1}
        if duplicates:
            raise ValueError(f"duplicate parameter names: {sorted(duplicates)}")
        self._parameters = params

    def __len__(self) -> int:
        return len(self._parameters)

    def __iter__(self) -> Iterator[UpdatableParameter]:
        return iter(self._parameters)

    def __getitem__(self, key: int | str) -> UpdatableParameter:
        if isinstance(key, str):
            for parameter in self._parameters:
                if parameter.name == key:
                    return parameter
            raise KeyError(f"no parameter named {key!r}")
        return self._parameters[key]

    def __contains__(self, name: object) -> bool:
        return any(p.name == name for p in self._parameters)

    @property
    def names(self) -> list[str]:
        return [p.name for p in self._parameters]

    @property
    def free(self) -> list[UpdatableParameter]:
        return [p for p in self._parameters if not p.fixed]

    @property
    def free_indices(self) -> list[int]:
        return [i for i, p in enumerate(self._parameters) if not p.fixed]

    @property
    def free_names(self) -> list[str]:
        return [p.name for p in self.free]

    @property
    def values(self) -> np.ndarray:
        return np.array([p.value for p in self._parameters], dtype=float)

    @property
    def initial_values(self) -> np.ndarray:
        return np.array([p.initial for p in self._parameters], dtype=float)

    def of_kind(self, kind: ParameterType | str) -> list[UpdatableParameter]:
        kind = ParameterType(kind)
        return [p for p in self._parameters if p.kind is kind]

    def as_dict(self) -> dict[str, float]:
        return {p.name: p.value for p in self._parameters}

    def set_values(self, values: Mapping[str, float] | Sequence[float] | np.ndarray) -> None:
        """Assign new physical values (clipped to bounds) to every parameter."""
        if isinstance(values, Mapping):
            for name, value in values.items():
                self[name].set_value(float(value))
            return
        array = np.asarray(values, dtype=float).ravel()
        if array.size != len(self._parameters):
            raise ValueError(
                f"expected {len(self._parameters)} values, got {array.size}"
            )
        for parameter, value in zip(self._parameters, array, strict=True):
            parameter.set_value(float(value))

    def design_values(self) -> np.ndarray:
        """Free parameters expressed in design space."""
        return np.array([p.to_design() for p in self.free], dtype=float)

    def design_bounds(self) -> tuple[np.ndarray, np.ndarray]:
        bounds = [p.design_bounds for p in self.free]
        lower = np.array([b[0] for b in bounds], dtype=float)
        upper = np.array([b[1] for b in bounds], dtype=float)
        return lower, upper

    def design_steps(self) -> np.ndarray:
        return np.array([p.design_step() for p in self.free], dtype=float)

    def clip_design(self, design_values: Sequence[float] | np.ndarray) -> np.ndarray:
        lower, upper = self.design_bounds()
        return np.clip(np.asarray(design_values, dtype=float).ravel(), lower, upper)

    def apply_design(self, design_values: Sequence[float] | np.ndarray) -> dict[str, float]:
        """Write design-space values back into the free parameters."""
        array = self.clip_design(design_values)
        free = self.free
        if array.size != len(free):
            raise ValueError(f"expected {len(free)} free values, got {array.size}")
        for parameter, value in zip(free, array, strict=True):
            parameter.value = parameter.from_design(float(value))
        return self.as_dict()

    def design_to_physical(self, design_values: Sequence[float] | np.ndarray) -> dict[str, float]:
        """Physical parameter dictionary for design values, without mutating state."""
        array = self.clip_design(design_values)
        free = self.free
        if array.size != len(free):
            raise ValueError(f"expected {len(free)} free values, got {array.size}")
        physical = self.as_dict()
        for parameter, value in zip(free, array, strict=True):
            physical[parameter.name] = parameter.from_design(float(value))
        return physical

    def reset(self) -> None:
        for parameter in self._parameters:
            parameter.reset()

    def copy(self) -> ParameterSet:
        return ParameterSet([p.copy() for p in self._parameters])

    def table(self) -> str:
        header = (
            f"{'name':<20} {'kind':<10} {'initial':>10} {'value':>10} "
            f"{'change [%]':>11} {'bounds':>18}"
        )
        lines = [header, "-" * len(header)]
        for p in self._parameters:
            bounds = f"[{p.lower:.3g}, {p.upper:.3g}]"
            flag = " (fixed)" if p.fixed else ""
            lines.append(
                f"{p.name + flag:<20} {p.kind.value:<10} {p.initial:10.4f} {p.value:10.4f} "
                f"{p.change_pct:11.3f} {bounds:>18}"
            )
        return "\n".join(lines)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"ParameterSet({self.as_dict()})"


@dataclass(frozen=True, slots=True)
class Parameter:
    """Declarative description of one updatable scalar of a model.

    Where :class:`UpdatableParameter` is the mutable state the optimiser walks
    over, ``Parameter`` is the *declaration* that an importer or a project file
    carries: which physical quantity is being updated, its nominal value, and
    the element selection it applies to.  Updating always runs on the
    normalized quantity ``x = value / reference`` so that parameters of wildly
    different magnitudes (``E ~ 1e11``, ``t ~ 1e-3``) condition the sensitivity
    matrix equally.

    Attributes
    ----------
    name:
        Unique label used in reports and the audit trail (e.g. ``"E.steel"``).
    target:
        Dotted path selecting what to modify: ``"material.<id>.<attr>"`` or
        ``"property.<id>.<key>"``.
    reference:
        Nominal value; defines the normalization ``x = value / reference``.
    lower, upper:
        Bounds on the *normalized* value (defaults ``[0.1, 10]``).
    element_ids:
        Optional element selection the parameter applies to (substructuring).
    kind:
        Which property the quantity belongs to, see :class:`ParameterType`.
    """

    name: str
    target: str
    reference: float
    lower: float = 0.1
    upper: float = 10.0
    element_ids: tuple[int, ...] | None = None
    kind: ParameterType = ParameterType.GENERIC
    meta: dict = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if not np.isfinite(self.reference) or self.reference == 0.0:
            raise ValueError(f"parameter {self.name!r}: reference must be finite, nonzero")
        if not self.lower < self.upper:
            raise ValueError(f"parameter {self.name!r}: need lower < upper")

    def normalize(self, value: float) -> float:
        """Normalized iterate ``x`` for a physical ``value``."""
        return float(value) / self.reference

    def denormalize(self, x: float) -> float:
        """Physical value for a normalized iterate ``x``."""
        return float(x) * self.reference

    def to_updatable(self, *, value: float = 1.0, **overrides: object) -> UpdatableParameter:
        """Build the mutable design variable the updater iterates on."""
        settings: dict[str, object] = {
            "name": self.name,
            "value": value,
            "lower": self.lower,
            "upper": self.upper,
            "kind": self.kind,
            "targets": () if self.element_ids is None else tuple(self.element_ids),
        }
        settings.update(overrides)
        return UpdatableParameter(**settings)  # type: ignore[arg-type]
