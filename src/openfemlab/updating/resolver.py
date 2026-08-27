"""Resolve declarative :class:`~openfemlab.updating.parameters.Parameter` targets
against a solver :class:`~openfemlab.core.model.Model`.

A project file — or an importer — declares *what* is uncertain by dotted path::

    Parameter("E.steel", "materials.steel.E", reference=2.1e11)
    Parameter("rho.steel", "materials.steel.density", reference=7850.0)
    Parameter("A.web", "sections.web.area", reference=1.0e-4)

This module turns such declarations into the affine parameterisation
:class:`~openfemlab.updating.scaling_model.ScalingModel` runs on::

    K(θ) = K_0 + Σ_j θ_j K_j        M(θ) = M_0 + Σ_j θ_j M_j

Two things have to be worked out for every parameter: *which elements* the
dotted target selects, and *what part of their matrices* the quantity scales.

Selection
---------
``<domain>.<key>.<attribute>`` with ``domain`` one of ``materials``,
``sections`` or ``elements`` (the singular spellings and the Nastran-flavoured
``properties`` alias are accepted too).  ``key`` is matched against
``Material.name`` / ``Section.name`` / ``Element.id``, and ``*`` selects every
element carrying the addressed quantity.  ``Parameter.element_ids``, when
given, intersects the selection, which is how one material is split into
substructures.

Decomposition
-------------
The contribution ``K_j`` is *measured*, not tabulated: the group's element
matrices are re-evaluated with the addressed quantity scaled by 1, 2 and 3, and
the affine model ``G(s) = C + s S`` is fitted to the first two probes and
verified against the third.  That keeps the resolver honest about what is
really affine — ``E`` and ``density`` are for every element in the library,
a beam ``area`` is (it scales the axial block and leaves bending alone), and a
shell ``thickness`` is *not* (membrane goes with ``t``, bending with ``t³``), so
the last case is rejected with :class:`NonAffineTargetError` instead of
silently linearising.  Whether a quantity lands in ``K``, in ``M`` or in both
follows from which probe moved, so no attribute table has to encode it.

Normalisation follows :class:`~openfemlab.updating.parameters.Parameter`:
``θ_j = value / reference``.  With the usual spec, whose ``reference`` is the
value already in the model, the nominal state is ``θ = 1``; when the two
disagree the resolver keeps ``θ`` in the declared normalisation and reports the
nominal iterate through :attr:`ResolvedParameter.initial_value`.

Constrained DOFs are dropped: the matrices handed to the scaling model span the
free DOFs only, since ``ScalingModel`` eigensolves them as they are.  Sensor
DOFs are therefore given in model DOF space and translated by
:func:`resolve_scaling_spec`.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Any

import numpy as np
import scipy.sparse as sp

from ..exceptions import OpenFEMLabError
from .parameters import Parameter, ParameterSet, ParameterType, UpdatableParameter
from .scaling_model import ScalingModel

__all__ = [
    "TargetError",
    "NonAffineTargetError",
    "ParameterTarget",
    "ResolvedParameter",
    "ScalingSpec",
    "parameters_from_mapping",
    "parse_target",
    "resolve_parameters",
    "resolve_scaling_spec",
    "scaling_model_from_spec",
]


class TargetError(OpenFEMLabError):
    """A dotted parameter target does not address anything in the model."""


class NonAffineTargetError(TargetError):
    """The addressed quantity does not scale the element matrices affinely."""


#: Accepted domain spellings mapped to the canonical one.
_DOMAINS: dict[str, str] = {
    "material": "materials",
    "materials": "materials",
    "section": "sections",
    "sections": "sections",
    "property": "sections",
    "properties": "sections",
    "element": "elements",
    "elements": "elements",
}

#: Attribute aliases per domain, mapped to the attribute actually carried by
#: :class:`~openfemlab.core.model.Material`, :class:`~openfemlab.core.model.Section`
#: or the element object.
_MATERIAL_ATTRIBUTES = {"e": "E", "young": "E", "density": "density", "rho": "density"}
_SECTION_ATTRIBUTES = {
    "a": "area",
    "area": "area",
    "iz": "inertia_z",
    "i1": "inertia_z",
    "inertia_z": "inertia_z",
    "iy": "inertia_y",
    "i2": "inertia_y",
    "inertia_y": "inertia_y",
    "j": "torsion_constant",
    "torsion_constant": "torsion_constant",
}
_ELEMENT_ATTRIBUTES = {
    "t": "thickness",
    "thickness": "thickness",
    "k": "stiffness",
    "stiffness": "stiffness",
}

#: Probe factors of the affine fit: two to determine ``C + s S``, one to check it.
_PROBES: tuple[float, float, float] = (1.0, 2.0, 3.0)

#: Relative tolerance of the affinity check, against the largest probe entry.
_AFFINE_TOLERANCE = 1.0e-9

#: A contribution whose norm falls this far below the nominal matrix is treated
#: as absent rather than as a parameterised part.
_NEGLIGIBLE = 1.0e-14


@dataclass(frozen=True)
class ParameterTarget:
    """The parsed form of a dotted target, e.g. ``materials.steel.E``."""

    domain: str
    key: str
    attribute: str

    @property
    def selects_all(self) -> bool:
        return self.key == "*"

    def __str__(self) -> str:
        return f"{self.domain}.{self.key}.{self.attribute}"


@dataclass(frozen=True)
class ResolvedParameter:
    """One declaration bound to a model: its elements and its matrix parts."""

    parameter: Parameter
    target: ParameterTarget
    #: Positions in ``Model.elements`` the parameter scales.
    element_indices: tuple[int, ...]
    #: The value the model currently carries for the addressed quantity.
    nominal_value: float
    #: ``∂K/∂θ`` over the free DOFs, ``None`` when the quantity leaves ``K`` alone.
    stiffness_part: Any | None
    #: ``∂M/∂θ`` over the free DOFs, ``None`` when the quantity leaves ``M`` alone.
    mass_part: Any | None

    @property
    def name(self) -> str:
        return self.parameter.name

    @property
    def initial_value(self) -> float:
        """``θ`` reproducing the model as built, i.e. ``nominal / reference``."""
        return self.nominal_value / self.parameter.reference

    @property
    def kind(self) -> ParameterType:
        """The declared kind, or the one the decomposition implies."""
        if self.parameter.kind is not ParameterType.GENERIC:
            return self.parameter.kind
        if self.stiffness_part is not None:
            return ParameterType.STIFFNESS
        return ParameterType.MASS

    def to_updatable(self, **overrides: object) -> UpdatableParameter:
        """The mutable design variable, started at the model's nominal ``θ``."""
        settings: dict[str, object] = {"value": self.initial_value, "kind": self.kind}
        settings.update(overrides)
        return self.parameter.to_updatable(**settings)


@dataclass(frozen=True)
class ScalingSpec:
    """A resolved specification: the scaling model plus the bookkeeping around it."""

    scaling_model: ScalingModel
    resolved: tuple[ResolvedParameter, ...]
    #: Model DOF indices spanned by the scaling model's matrices, in order.
    free_dofs: np.ndarray

    @property
    def initial_values(self) -> dict[str, float]:
        """``θ`` reproducing the model as built."""
        return {item.name: item.initial_value for item in self.resolved}

    def parameter_set(self, **overrides: object) -> ParameterSet:
        """Design variables for :class:`~openfemlab.updating.updater.ModelUpdater`."""
        return ParameterSet([item.to_updatable(**overrides) for item in self.resolved])

    def dof_row(self, dof_index: int) -> int:
        """Row of a model DOF index inside the scaling model's matrices."""
        return _free_row(self.free_dofs, dof_index)


def _free_row(free: np.ndarray, dof_index: int) -> int:
    position = int(np.searchsorted(free, int(dof_index)))
    if position >= free.size or int(free[position]) != int(dof_index):
        raise TargetError(f"model DOF {dof_index} is constrained and carries no equation")
    return position


# ------------------------------------------------------------------- parsing


def parse_target(target: str) -> ParameterTarget:
    """Split ``"materials.steel.E"`` into its domain, key and attribute."""
    tokens = [token for token in str(target).split(".") if token]
    if len(tokens) != 3:
        raise TargetError(
            f"target {target!r} must read '<domain>.<key>.<attribute>', "
            f"for example 'materials.steel.E'"
        )
    domain_token, key, attribute = tokens
    domain = _DOMAINS.get(domain_token.strip().lower())
    if domain is None:
        raise TargetError(
            f"target {target!r}: unknown domain {domain_token!r} "
            f"(expected one of {sorted(set(_DOMAINS))})"
        )
    table = {
        "materials": _MATERIAL_ATTRIBUTES,
        "sections": _SECTION_ATTRIBUTES,
        "elements": {**_ELEMENT_ATTRIBUTES, **_MATERIAL_ATTRIBUTES, **_SECTION_ATTRIBUTES},
    }[domain]
    resolved = table.get(attribute.strip().lower())
    if resolved is None:
        raise TargetError(
            f"target {target!r}: {domain} carry no updatable attribute {attribute!r} "
            f"(expected one of {sorted(set(table.values()))})"
        )
    return ParameterTarget(domain=domain, key=key, attribute=resolved, raw_attribute=attribute)


# ----------------------------------------------------------------- selection


def _owner(element: Any, target: ParameterTarget) -> tuple[str, Any] | None:
    """``(holder, object)`` carrying the addressed attribute, or ``None``."""
    material = getattr(element, "material", None)
    section = getattr(element, "section", None)
    if target.attribute in _MATERIAL_ATTRIBUTES.values():
        return None if material is None else ("material", material)
    if target.attribute in _SECTION_ATTRIBUTES.values():
        return None if section is None else ("section", section)
    return None if not hasattr(element, target.attribute) else ("element", element)


def _matches(element: Any, index: int, target: ParameterTarget) -> bool:
    if target.domain == "materials":
        material = getattr(element, "material", None)
        return material is not None and (
            target.selects_all or str(getattr(material, "name", "")) == target.key
        )
    if target.domain == "sections":
        section = getattr(element, "section", None)
        return section is not None and (
            target.selects_all or str(getattr(section, "name", "")) == target.key
        )
    label = element.id if element.id is not None else index
    return target.selects_all or str(label) == target.key


def _select(model: Any, parameter: Parameter, target: ParameterTarget) -> tuple[int, ...]:
    """Element positions the target addresses, intersected with ``element_ids``."""
    elements = model.elements
    selected = [
        index
        for index, element in enumerate(elements)
        if _matches(element, index, target) and _owner(element, target) is not None
    ]
    if not selected:
        raise TargetError(
            f"parameter {parameter.name!r}: target {parameter.target!r} matches no element "
            f"of model {getattr(model, 'name', '?')!r} carrying {target.attribute!r} "
            f"(known {target.domain}: {_known(model, target)})"
        )
    if parameter.element_ids is not None:
        wanted = {str(eid) for eid in parameter.element_ids}
        selected = [
            index
            for index in selected
            if str(elements[index].id if elements[index].id is not None else index) in wanted
        ]
        if not selected:
            raise TargetError(
                f"parameter {parameter.name!r}: element_ids "
                f"{list(parameter.element_ids)} select none of the elements matched by "
                f"{parameter.target!r}"
            )
    return tuple(selected)


def _known(model: Any, target: ParameterTarget) -> str:
    if target.domain == "materials":
        names = {str(getattr(e.material, "name", "")) for e in model.elements
                 if getattr(e, "material", None) is not None}
    elif target.domain == "sections":
        names = {str(getattr(e.section, "name", "")) for e in model.elements
                 if getattr(e, "section", None) is not None}
    else:
        names = {str(e.id) for e in model.elements if e.id is not None}
    listed = sorted(name for name in names if name)
    return ", ".join(listed) if listed else "unnamed"


def _nominal_value(model: Any, indices: Sequence[int], target: ParameterTarget) -> float:
    """The single value the group carries for the addressed quantity."""
    elements = model.elements
    values = []
    for index in indices:
        owner = _owner(elements[index], target)
        assert owner is not None  # guaranteed by _select
        values.append(float(getattr(owner[1], target.attribute)))
    first = values[0]
    if not np.allclose(values, first, rtol=1e-12, atol=0.0):
        raise TargetError(
            f"target {target} spans elements with different {target.attribute} values "
            f"({min(values):g} … {max(values):g}); a scaling factor needs one nominal "
            "value, so split the parameter per group"
        )
    if first == 0.0:
        raise TargetError(f"target {target} is zero in the model and cannot be scaled")
    return first


# --------------------------------------------------------------- probe matrices


@contextmanager
def _scaled(element: Any, target: ParameterTarget, factor: float) -> Iterator[None]:
    """Scale the addressed quantity of ``element`` for the duration of the block."""
    holders: list[Any] = [element]
    # A shell facet delegates its membrane to a nested element holding the same
    # material and thickness; both copies have to move together.
    nested = getattr(element, "membrane", None)
    if nested is not None:
        holders.append(nested)

    undo: list[tuple[Any, str, Any]] = []
    try:
        for holder in holders:
            owner = _owner(holder, target)
            if owner is None:
                continue
            kind, obj = owner
            if kind == "element":
                current = float(getattr(holder, target.attribute))
                undo.append((holder, target.attribute, getattr(holder, target.attribute)))
                setattr(holder, target.attribute, current * factor)
                continue
            attribute = "material" if kind == "material" else "section"
            undo.append((holder, attribute, obj))
            scaled_value = float(getattr(obj, target.attribute)) * factor
            setattr(holder, attribute, replace(obj, **{target.attribute: scaled_value}))
        yield
    finally:
        for holder, attribute, value in reversed(undo):
            setattr(holder, attribute, value)


def _group_matrices(
    model: Any, indices: Sequence[int], target: ParameterTarget, factor: float
) -> tuple[sp.csr_matrix, sp.csr_matrix]:
    """``(K, M)`` of the group alone, with the addressed quantity scaled."""
    elements = model.elements
    size = model.num_dofs
    rows: list[np.ndarray] = []
    cols: list[np.ndarray] = []
    stiffness: list[np.ndarray] = []
    mass: list[np.ndarray] = []

    for index in indices:
        element = elements[index]
        with _scaled(element, target, factor):
            coords = model.node_coords(element.node_ids)
            local_k = np.asarray(element.stiffness_matrix(coords), dtype=float)
            local_m = np.asarray(element.mass_matrix(coords), dtype=float)
        dofs = element.global_dofs(model)
        rows.append(np.repeat(dofs, dofs.size))
        cols.append(np.tile(dofs, dofs.size))
        stiffness.append(local_k.reshape(-1))
        mass.append(local_m.reshape(-1))

    row = np.concatenate(rows)
    col = np.concatenate(cols)

    def build(data: list[np.ndarray]) -> sp.csr_matrix:
        matrix = sp.coo_matrix(
            (np.concatenate(data), (row, col)), shape=(size, size)
        ).tocsr()
        return ((matrix + matrix.T) * 0.5).tocsr()

    return build(stiffness), build(mass)


def _affine_slopes(
    model: Any, indices: Sequence[int], target: ParameterTarget, parameter: Parameter
) -> list[sp.csr_matrix | None]:
    """``S`` of ``G(s) = C + s S`` for the group's stiffness and mass.

    ``None`` marks a matrix the quantity does not move at all, which is the
    normal case for one of the two: ``E`` leaves ``M`` alone and ``density``
    leaves ``K`` alone.
    """
    probes = [_group_matrices(model, indices, target, factor) for factor in _PROBES]
    slopes: list[sp.csr_matrix | None] = []
    for position, label in ((0, "stiffness"), (1, "mass")):
        first, second, third = (probe[position] for probe in probes)
        slope = (second - first).tocsr()
        residual = (third - second - slope).tocsr()
        scale = max(_norm(third), _norm(slope))
        if scale == 0.0:
            slopes.append(None)
            continue
        if _norm(residual) > _AFFINE_TOLERANCE * scale:
            raise NonAffineTargetError(
                f"parameter {parameter.name!r}: the {label} of the elements selected by "
                f"{parameter.target!r} is not affine in {target.attribute} "
                f"(probing 1x, 2x and 3x leaves a residual of "
                f"{_norm(residual) / scale:.3g}); parameterise a quantity the element "
                "matrices scale linearly, such as the material E or density"
            )
        slopes.append(slope if _norm(slope) > _NEGLIGIBLE * scale else None)
    return slopes


def _norm(matrix: Any) -> float:
    if sp.issparse(matrix):
        return float(np.abs(matrix.data).max()) if matrix.nnz else 0.0
    values = np.asarray(matrix, dtype=float)
    return float(np.abs(values).max()) if values.size else 0.0


def _restrict(matrix: sp.csr_matrix, free: np.ndarray) -> sp.csr_matrix:
    if free.size == matrix.shape[0]:
        return matrix.tocsr()
    return matrix[free, :][:, free].tocsr()


# ------------------------------------------------------------------ resolution


def resolve_parameters(
    model: Any, parameters: Iterable[Parameter]
) -> list[ResolvedParameter]:
    """Bind every declaration to its elements and its free-DOF matrix parts."""
    declarations = list(parameters)
    if not declarations:
        raise TargetError("a scaling specification needs at least one parameter")
    names = [parameter.name for parameter in declarations]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise TargetError(f"duplicate parameter names: {duplicates}")

    free = np.asarray(model.free_dofs, dtype=int)
    resolved: list[ResolvedParameter] = []
    for parameter in declarations:
        target = parse_target(parameter.target)
        indices = _select(model, parameter, target)
        nominal = _nominal_value(model, indices, target)
        slope_k, slope_m = _affine_slopes(model, indices, target, parameter)
        if slope_k is None and slope_m is None:
            raise TargetError(
                f"parameter {parameter.name!r}: scaling {parameter.target!r} leaves both "
                "the stiffness and the mass of its elements unchanged, so it cannot be "
                "identified"
            )
        # θ is the normalized value, so the physical multiplier of the model's
        # own value is θ * reference / nominal.
        gain = parameter.reference / nominal
        resolved.append(
            ResolvedParameter(
                parameter=parameter,
                target=target,
                element_indices=indices,
                nominal_value=nominal,
                stiffness_part=None
                if slope_k is None
                else _restrict((slope_k * gain).tocsr(), free),
                mass_part=None if slope_m is None else _restrict((slope_m * gain).tocsr(), free),
            )
        )
    _reject_overlaps(model, resolved)
    return resolved


def _reject_overlaps(model: Any, resolved: Sequence[ResolvedParameter]) -> None:
    """Two factors on one element matrix would multiply, not add."""
    for attribute, label in (("stiffness_part", "stiffness"), ("mass_part", "mass")):
        seen: dict[int, str] = {}
        for item in resolved:
            if getattr(item, attribute) is None:
                continue
            for index in item.element_indices:
                other = seen.get(index)
                if other is not None:
                    element = model.elements[index]
                    raise TargetError(
                        f"parameters {other!r} and {item.name!r} both scale the {label} of "
                        f"element {element.id if element.id is not None else index!r}; the "
                        "affine parameterisation cannot represent their product, so give "
                        "them disjoint element sets"
                    )
                seen[index] = item.name


def resolve_scaling_spec(
    model: Any,
    parameters: Iterable[Parameter],
    *,
    num_modes: int | None = None,
    sensor_dofs: Sequence[int | tuple[Hashable, Any]] | None = None,
    **options: Any,
) -> ScalingSpec:
    """Resolve ``parameters`` and build the scaling model plus its bookkeeping.

    Parameters
    ----------
    model:
        A solver :class:`~openfemlab.core.model.Model` with its elements bound.
    parameters:
        The :class:`~openfemlab.updating.parameters.Parameter` declarations.
    num_modes:
        Modes the scaling model reports; every mode by default.
    sensor_dofs:
        Correlation DOFs, either as model DOF indices or as ``(node_id, dof)``
        pairs.  They are translated into rows of the free-DOF matrices.
    options:
        Forwarded to :class:`~openfemlab.updating.scaling_model.ScalingModel`
        (``use_solver``, ``reanalysis``, ``sparse``, ...).
    """
    resolved = resolve_parameters(model, parameters)
    free = np.asarray(model.free_dofs, dtype=int)

    system = model.assemble()
    base_stiffness = _restrict(system.K.tocsr(), free)
    base_mass = _restrict(system.M.tocsr(), free)
    stiffness_parts: dict[str, Any] = {}
    mass_parts: dict[str, Any] = {}
    for item in resolved:
        # K_0 carries what θ does not scale, so what each part contributes at
        # the nominal θ comes back out of the assembled matrix.
        if item.stiffness_part is not None:
            stiffness_parts[item.name] = item.stiffness_part
            base_stiffness = (
                base_stiffness - item.stiffness_part * item.initial_value
            ).tocsr()
        if item.mass_part is not None:
            mass_parts[item.name] = item.mass_part
            base_mass = (base_mass - item.mass_part * item.initial_value).tocsr()

    selection = None
    if sensor_dofs is not None:
        selection = np.array(
            [_free_row(free, _dof_index(model, entry)) for entry in sensor_dofs], dtype=int
        )

    return ScalingSpec(
        scaling_model=ScalingModel(
            stiffness_parts,
            mass_parts,
            base_stiffness=base_stiffness,
            base_mass=base_mass,
            num_modes=num_modes,
            dof_selection=selection,
            **options,
        ),
        resolved=tuple(resolved),
        free_dofs=free,
    )


def _dof_index(model: Any, entry: int | tuple[Hashable, Any]) -> int:
    if isinstance(entry, tuple):
        node_id, dof = entry
        return int(model.dof_index(node_id, dof))
    return int(entry)


def scaling_model_from_spec(
    model: Any,
    parameters: Iterable[Parameter],
    *,
    num_modes: int | None = None,
    sensor_dofs: Sequence[int | tuple[Hashable, Any]] | None = None,
    **options: Any,
) -> ScalingModel:
    """Build the affine :class:`~openfemlab.updating.scaling_model.ScalingModel`
    a model and its dotted parameter declarations describe.

    The scaling factors are the normalised values of
    :class:`~openfemlab.updating.parameters.Parameter`, ``θ = value / reference``,
    and the matrices span the model's free DOFs.  Use
    :func:`resolve_scaling_spec` when the element selection, the nominal ``θ``
    or the free-DOF map is needed as well.

    Examples
    --------
    >>> from openfemlab.mesh.simple import beam_mesh              # doctest: +SKIP
    >>> parameters = [Parameter("E", "materials.steel.E", reference=2.1e11)]
    >>> scaling = scaling_model_from_spec(model, parameters)      # doctest: +SKIP
    >>> scaling({"E": 1.1}).frequencies[:3]                       # doctest: +SKIP
    """
    return resolve_scaling_spec(
        model, parameters, num_modes=num_modes, sensor_dofs=sensor_dofs, **options
    ).scaling_model


def parameters_from_mapping(entries: Mapping[str, Mapping[str, Any]]) -> list[Parameter]:
    """Build declarations from a ``{name: {target, reference, ...}}`` mapping.

    The shape a project file carries; unknown keys are rejected by
    :class:`~openfemlab.updating.parameters.Parameter` itself.
    """
    return [Parameter(name=name, **dict(fields)) for name, fields in entries.items()]
