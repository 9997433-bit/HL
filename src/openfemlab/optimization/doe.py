"""Design-of-experiments bridge from :mod:`openfemlab.uq` to optimization.

Full-factorial and Latin-hypercube grids declared in physical parameter space
are lowered to :class:`~openfemlab.optimization.variables.DesignSpace` design
vectors so screening studies reuse the same model callable as sizing
optimization.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

import numpy as np
import numpy.typing as npt

from ..uq.doe import doe_box_run, doe_levels
from .variables import DesignSpace

__all__ = [
    "DesignOfExperimentsResult",
    "factorial_design_vectors",
    "run_factorial_screen",
    "run_lhs_screen",
]


class DesignOfExperimentsResult:
    """Factorial or LHS screen over a :class:`DesignSpace`."""

    __slots__ = ("names", "physical", "design", "responses", "diagnostics")

    def __init__(
        self,
        *,
        names: tuple[str, ...],
        physical: npt.NDArray[np.float64],
        design: npt.NDArray[np.float64],
        responses: npt.NDArray[np.float64],
        diagnostics: Mapping[str, object],
    ) -> None:
        self.names = names
        self.physical = physical
        self.design = design
        self.responses = responses
        self.diagnostics = dict(diagnostics)

    @property
    def count(self) -> int:
        return int(self.design.shape[0])

    def to_dict(self) -> dict[str, object]:
        rows: list[dict[str, object]] = []
        for index in range(self.count):
            row: dict[str, object] = {
                name: float(self.physical[index, j]) for j, name in enumerate(self.names)
            }
            row["design_vector"] = self.design[index].tolist()
            row["response"] = self.responses[index].tolist()
            rows.append(row)
        return {
            "names": list(self.names),
            "count": self.count,
            "diagnostics": self.diagnostics,
            "samples": rows,
        }


def _physical_to_design(
    space: DesignSpace, samples: npt.NDArray[np.float64], names: tuple[str, ...]
) -> npt.NDArray[np.float64]:
    if space.sizing is None:
        raise ValueError("factorial screening requires at least one sizing parameter")
    free_names = space.sizing.free_names
    design_rows: list[npt.NDArray[np.float64]] = []
    for row in samples:
        physical = space.sizing.as_dict()
        for index, name in enumerate(names):
            if name not in free_names:
                raise ValueError(
                    f"DOE factor {name!r} is not a free sizing variable "
                    f"(expected one of {free_names})"
                )
            physical[name] = float(row[index])
        design_rows.append(
            np.asarray(
                [parameter.to_design(physical[parameter.name]) for parameter in space.sizing.free],
                dtype=float,
            )
        )
    return np.vstack(design_rows)


def factorial_design_vectors(
    space: DesignSpace,
    factors: Mapping[str, Sequence[float]],
) -> tuple[tuple[str, ...], npt.NDArray[np.float64], npt.NDArray[np.float64]]:
    """Map a full factorial over ``factors`` to design-space rows."""
    names, samples = doe_levels(factors)
    design = _physical_to_design(space, samples, names)
    return names, samples, design


def run_factorial_screen(
    space: DesignSpace,
    factors: Mapping[str, Sequence[float]],
    evaluate: Callable[[Mapping[str, float]], npt.NDArray[np.floating]],
    *,
    nominal: Mapping[str, float] | None = None,
) -> DesignOfExperimentsResult:
    """Evaluate a full factorial grid through ``evaluate`` in physical space."""
    base = dict(nominal or {})
    if space.sizing is not None:
        base.update(space.sizing.as_dict())

    def wrapped(theta: Mapping[str, float]) -> npt.NDArray[np.floating]:
        merged = dict(base)
        merged.update(theta)
        return evaluate(merged)

    raw = doe_box_run(wrapped, base, factors)
    names, physical, design = factorial_design_vectors(space, factors)
    return DesignOfExperimentsResult(
        names=names,
        physical=physical,
        design=design,
        responses=raw.samples,
        diagnostics=raw.diagnostics,
    )


def run_lhs_screen(
    space: DesignSpace,
    bounds: Mapping[str, tuple[float, float]],
    evaluate: Callable[[Mapping[str, float]], npt.NDArray[np.floating]],
    count: int,
    *,
    nominal: Mapping[str, float] | None = None,
    seed: int | None = None,
) -> DesignOfExperimentsResult:
    """Evaluate an LHS sample over bounded physical factors."""
    base = dict(nominal or {})
    if space.sizing is not None:
        base.update(space.sizing.as_dict())

    def wrapped(theta: Mapping[str, float]) -> npt.NDArray[np.floating]:
        merged = dict(base)
        merged.update(theta)
        return evaluate(merged)

    from ..uq.monte_carlo import latin_hypercube_samples

    names = tuple(sorted(bounds))
    unit = latin_hypercube_samples(count, len(names), seed=seed)
    physical = np.zeros((count, len(names)), dtype=float)
    for index, name in enumerate(names):
        low, high = bounds[name]
        physical[:, index] = low + unit[:, index] * (high - low)
    responses: list[npt.NDArray[np.float64]] = []
    for row in physical:
        theta = dict(base)
        for index, name in enumerate(names):
            theta[name] = float(row[index])
        responses.append(np.asarray(wrapped(theta), dtype=float).reshape(-1))
    stacked = np.vstack(responses)
    design = _physical_to_design(space, physical, names)
    return DesignOfExperimentsResult(
        names=names,
        physical=physical,
        design=design,
        responses=stacked,
        diagnostics={"count": count, "sampler": "lhs_box", "seed": seed},
    )
