"""Turn an interchange :class:`NeutralModel` into a solver-ready :class:`Model`.

``docs/ARCHITECTURE.md`` §L1 splits the flat interchange representation
(:mod:`openfemlab.core.neutral`) from the internal solver model
(:mod:`openfemlab.core.model`), and puts the conversion between them in the io
layer.  This module is that conversion: it walks the neutral connectivity
blocks, resolves each element's material and section through the neutral
property tables, and hands the internal model bound
:class:`~openfemlab.core.elements.Element` instances so an imported mesh can be
*re-analyzed* rather than only correlated.

Supported blocks are the ones the element library formulates:

======================  ==========================================  ============
``ElementType``         element                                     DOFs per node
======================  ==========================================  ============
``ROD2``                :class:`~openfemlab.core.elements.TrussElement`   UX UY UZ
``BEAM2``               :class:`~openfemlab.core.elements.BeamElement3D`
                        (or ``BeamElement2D`` in a planar model)     UX..RZ
``TRI3``                :class:`~openfemlab.core.elements.Tri3Element`   UX UY
``QUAD4``               :class:`~openfemlab.core.elements.Quad4Element`  UX UY
                        (or :class:`~openfemlab.core.elements.ShellQuad4Element`
                        when ``quad4_as="shell"``)                         UX..RZ
``TET4``                :class:`~openfemlab.core.elements.Tet4Element`   UX UY UZ
``HEX8``                :class:`~openfemlab.core.elements.Hex8Element`   UX UY UZ
======================  ==========================================  ============

``MASS1`` and ``SPRING2`` have no formulation yet; a model carrying
them is rejected unless ``skip_unsupported=True``, which drops those blocks
with a warning the way the meshio bridge drops unknown cell types.

A mesh file carries geometry but no material data, so
:func:`~openfemlab.io.meshio_bridge.from_meshio` returns empty ``materials`` and
``properties``.  The ``material`` / ``section`` / ``thickness`` arguments cover
exactly that case: they are the fallback used whenever the neutral tables do not
resolve a block's property id.  Boundary conditions and point masses are applied
from preserved BDF ``SPC1`` / ``CONM2`` cards when present; otherwise call
:meth:`~openfemlab.core.model.Model.fix` before a modal solve.
"""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from typing import Any, Literal

import numpy as np
import numpy.typing as npt

from openfemlab.core.elements import (
    BeamElement2D,
    BeamElement3D,
    Element,
    Hex8Element,
    Quad4Element,
    ShellQuad4Element,
    Tet4Element,
    Tri3Element,
    TrussElement,
)
from openfemlab.core.model import DOF, TRANSLATIONAL_DOFS, Material, Model, Section
from openfemlab.core.mpc import RBE3Group, RBE3Tie, parse_nastran_components
from openfemlab.core.neutral import ElementType, NeutralMaterial, NeutralModel, NeutralProperty
from openfemlab.exceptions import OpenFEMLabError

from ._common import FormatError

Quad4Binding = Literal["membrane", "shell"]

__all__ = [
    "ELEMENT_DOFS",
    "ELEMENT_NODE_COUNTS",
    "Quad4Binding",
    "SUPPORTED_ELEMENT_TYPES",
    "infer_dofs",
    "material_from_neutral",
    "neutral_to_model",
    "apply_rbe2_from_neutral",
    "apply_rbe3_from_neutral",
    "apply_spc1_from_neutral",
    "apply_conm2_from_neutral",
    "apply_force_from_neutral",
    "apply_moment_from_neutral",
    "section_from_values",
    "to_model",
]

_SPATIAL_BEAM_DOFS: tuple[DOF, ...] = (DOF.UX, DOF.UY, DOF.UZ, DOF.RX, DOF.RY, DOF.RZ)
_PLANAR_BEAM_DOFS: tuple[DOF, ...] = (DOF.UX, DOF.UY, DOF.RZ)

#: Nodal DOFs each supported block needs; :func:`infer_dofs` unions them.
ELEMENT_DOFS: dict[ElementType, tuple[DOF, ...]] = {
    ElementType.ROD2: TRANSLATIONAL_DOFS,
    ElementType.BEAM2: _SPATIAL_BEAM_DOFS,
    ElementType.TRI3: (DOF.UX, DOF.UY),
    ElementType.QUAD4: (DOF.UX, DOF.UY),
    ElementType.TET4: TRANSLATIONAL_DOFS,
    ElementType.HEX8: TRANSLATIONAL_DOFS,
}

#: Nodes per element of each supported block, checked before construction so a
#: malformed connectivity array reports its block rather than its first row.
ELEMENT_NODE_COUNTS: dict[ElementType, int] = {
    ElementType.ROD2: 2,
    ElementType.BEAM2: 2,
    ElementType.TRI3: 3,
    ElementType.QUAD4: 4,
    ElementType.TET4: 4,
    ElementType.HEX8: 8,
}

SUPPORTED_ELEMENT_TYPES: tuple[ElementType, ...] = tuple(ELEMENT_DOFS)

#: Property keys accepted for each :class:`~openfemlab.core.model.Section`
#: field, in order of preference and matched case-insensitively.  The Nastran
#: ``PBAR`` spellings ``I1``/``I2`` are accepted alongside the neutral ones.
_SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "area": ("a", "area"),
    "inertia_z": ("iz", "i1", "inertia_z"),
    "inertia_y": ("iy", "i2", "inertia_y"),
    "torsion_constant": ("j", "torsion_constant"),
}

#: Property keys accepted for the QUAD4 out-of-plane thickness.
_THICKNESS_ALIASES: tuple[str, ...] = ("t", "thickness")


def infer_dofs(model: NeutralModel, *, quad4_as: Quad4Binding = "membrane") -> tuple[DOF, ...]:
    """Smallest DOF signature that binds every supported block of ``model``.

    The union of :data:`ELEMENT_DOFS` over the non-empty blocks, in ascending
    :class:`~openfemlab.core.model.DOF` order: a quad-only mesh comes back
    planar ``(UX, UY)`` unless ``quad4_as="shell"``, a solid mesh translational,
    and anything containing a ``BEAM2`` gets the full six DOFs.  A model with no
    supported element block falls back to the three translations.
    """

    required: set[DOF] = set()
    for element_type, block in model.elements.items():
        if np.asarray(block).size == 0:
            continue
        if element_type is ElementType.QUAD4 and quad4_as == "shell":
            required.update(_SPATIAL_BEAM_DOFS)
        else:
            required.update(ELEMENT_DOFS.get(element_type, ()))
    if not required:
        return TRANSLATIONAL_DOFS
    return tuple(sorted(required))


def material_from_neutral(material: NeutralMaterial) -> Material:
    """Convert an interchange material to the solver's :class:`Material`."""

    try:
        return Material(
            E=float(material.E),
            density=float(material.rho),
            nu=float(material.nu),
            name=material.name,
        )
    except OpenFEMLabError as exc:
        raise FormatError(f"material {material.id} is not usable: {exc}") from exc


def section_from_values(values: dict[str, float], *, description: str = "property") -> Section:
    """Build a :class:`Section` from neutral property values.

    ``A`` is required; ``Iz``/``I1``, ``Iy``/``I2`` and ``J`` are optional and
    default to zero, which is what a rod carries and what
    :class:`~openfemlab.core.elements.BeamElement2D` and
    :class:`~openfemlab.core.elements.BeamElement3D` reject when they need them.
    """

    area = _lookup(values, _SECTION_ALIASES["area"])
    if area is None:
        keys = ", ".join(sorted(values)) or "none"
        raise FormatError(
            f"{description} defines no cross-section area A (keys: {keys}); "
            "pass section= to supply one"
        )
    try:
        return Section(
            area=area,
            inertia_z=_lookup(values, _SECTION_ALIASES["inertia_z"]) or 0.0,
            inertia_y=_lookup(values, _SECTION_ALIASES["inertia_y"]) or 0.0,
            torsion_constant=_lookup(values, _SECTION_ALIASES["torsion_constant"]) or 0.0,
        )
    except OpenFEMLabError as exc:
        raise FormatError(f"{description} is not a usable section: {exc}") from exc


def to_model(
    neutral: NeutralModel,
    *,
    dofs: Sequence[DOF | str | int] | None = None,
    name: str | None = None,
    material: Material | None = None,
    section: Section | None = None,
    thickness: float | None = None,
    plane: str = "stress",
    lumped_mass: bool = False,
    beam_orientation: Sequence[float] | None = None,
    integration_order: int = 2,
    quad4_as: Quad4Binding = "membrane",
    skip_unsupported: bool = False,
) -> Model:
    """Convert ``neutral`` into an internal :class:`Model` with bound elements.

    Parameters
    ----------
    dofs:
        Active DOF signature of the model.  ``None`` calls :func:`infer_dofs`.
    name:
        Model label; defaults to ``meta["name"]`` when the neutral model
        carries one, otherwise ``"model"``.
    material, section, thickness:
        Fallbacks used for blocks whose property id resolves to nothing, which
        is the normal case for a mesh file.  A property that *is* defined wins
        over them, field by field: its ``values`` supply the section only when
        they carry an area, and the thickness only when they carry ``t``.
    plane, lumped_mass, beam_orientation, integration_order:
        Passed through to the element constructors; the interchange contract
        has nowhere to record them.
    quad4_as:
        ``"membrane"`` binds ``QUAD4`` to the plane-stress
        :class:`~openfemlab.core.elements.Quad4Element`; ``"shell"`` binds it
        to the six-DOF :class:`~openfemlab.core.elements.ShellQuad4Element`.
    skip_unsupported:
        Drop blocks with no formulation (``TRI3``, ``MASS1``, ``SPRING2``) with
        a warning instead of raising.

    Notes
    -----
    Node ids survive the conversion, so DOF indices can be addressed by the
    labels the source file used.  ``NeutralModel.dof_map`` is *not* honoured:
    the internal model numbers its DOFs node-major from its own signature.
    Every failure -- unknown node id, unresolvable property, degenerate section
    -- is reported as :class:`~openfemlab.io.FormatError`.
    """

    signature = infer_dofs(neutral, quad4_as=quad4_as) if dofs is None else tuple(dofs)
    label = name if name is not None else str(_meta(neutral).get("name", "model"))
    try:
        model = Model(dofs=signature, name=label)
    except OpenFEMLabError as exc:
        raise FormatError(f"invalid DOF signature: {exc}") from exc

    _add_nodes(model, neutral)

    defaults = _Defaults(
        material=material,
        section=section,
        thickness=thickness,
        plane=plane,
        lumped_mass=lumped_mass,
        beam_orientation=beam_orientation,
        integration_order=integration_order,
        quad4_as=quad4_as,
    )
    cache: dict[tuple[ElementType, int], tuple[Material, Section | None, float]] = {}
    skipped: dict[str, int] = {}

    for element_type, block in neutral.elements.items():
        connectivity = _connectivity(element_type, block)
        if element_type not in ELEMENT_DOFS:
            if not skip_unsupported:
                supported = ", ".join(sorted(t.value for t in SUPPORTED_ELEMENT_TYPES))
                raise FormatError(
                    f"element type {element_type.value!r} has no formulation yet "
                    f"(supported: {supported}); pass skip_unsupported=True to drop it"
                )
            skipped[element_type.value] = connectivity.shape[0]
            continue
        property_ids = _property_ids(neutral, element_type, connectivity.shape[0])
        labels = _element_labels(neutral, element_type, connectivity.shape[0])
        for row, property_id, element_id in zip(connectivity, property_ids, labels, strict=True):
            key = (element_type, int(property_id))
            if key not in cache:
                cache[key] = _resolve_property(neutral, element_type, int(property_id), defaults)
            element = _build_element(
                element_type,
                [int(node_id) for node_id in row],
                *cache[key],
                element_id,
                model.dofs,
                defaults,
            )
            try:
                model.add_element(element)
            except OpenFEMLabError as exc:
                raise FormatError(
                    f"{element_type.value} element {element_id} cannot be bound: {exc}"
                ) from exc

    if skipped:
        joined = ", ".join(f"{key} ({count})" for key, count in sorted(skipped.items()))
        warnings.warn(f"skipped element types with no formulation: {joined}", stacklevel=2)
    apply_rbe2_from_neutral(model, neutral)
    apply_rbe3_from_neutral(model, neutral)
    apply_spc1_from_neutral(model, neutral)
    apply_conm2_from_neutral(model, neutral)
    apply_force_from_neutral(model, neutral)
    apply_moment_from_neutral(model, neutral)
    return model


#: The verb the io namespace exports, where ``to_model`` alone would be vague.
neutral_to_model = to_model


class _Defaults:
    """Converter-wide settings the interchange contract cannot carry."""

    __slots__ = (
        "beam_orientation",
        "integration_order",
        "lumped_mass",
        "material",
        "plane",
        "quad4_as",
        "section",
        "thickness",
    )

    def __init__(
        self,
        *,
        material: Material | None,
        section: Section | None,
        thickness: float | None,
        plane: str,
        lumped_mass: bool,
        beam_orientation: Sequence[float] | None,
        integration_order: int,
        quad4_as: Quad4Binding,
    ) -> None:
        self.material = material
        self.section = section
        self.thickness = 1.0 if thickness is None else float(thickness)
        self.plane = plane
        self.lumped_mass = bool(lumped_mass)
        self.beam_orientation = beam_orientation
        self.integration_order = int(integration_order)
        self.quad4_as = quad4_as


def _add_nodes(model: Model, neutral: NeutralModel) -> None:
    coordinates = np.asarray(neutral.nodes, dtype=float)
    for node_id, coords in zip(neutral.node_ids, coordinates, strict=True):
        try:
            model.add_node(int(node_id), coords)
        except OpenFEMLabError as exc:
            raise FormatError(f"cannot add node {int(node_id)}: {exc}") from exc


def _connectivity(element_type: ElementType, block: Any) -> npt.NDArray[np.int64]:
    array = np.asarray(block, dtype=np.int64)
    if array.ndim != 2:
        raise FormatError(
            f"{element_type.value} connectivity must have shape (n_elements, nodes_per_element), "
            f"got {array.shape}"
        )
    expected = ELEMENT_NODE_COUNTS.get(element_type)
    if expected is not None and array.shape[1] != expected:
        raise FormatError(
            f"{element_type.value} connectivity must have {expected} nodes per element, "
            f"got {array.shape[1]}"
        )
    return array


def _property_ids(
    neutral: NeutralModel, element_type: ElementType, n_elements: int
) -> npt.NDArray[np.int64]:
    values = neutral.element_property_ids.get(element_type)
    if values is None:
        return np.zeros(n_elements, dtype=np.int64)
    ids = np.asarray(values, dtype=np.int64).reshape(-1)
    if ids.shape != (n_elements,):
        raise FormatError(
            f"{element_type.value} property ids must have shape ({n_elements},), got {ids.shape}"
        )
    return ids


def _element_labels(neutral: NeutralModel, element_type: ElementType, n_elements: int) -> list[int]:
    raw = _meta(neutral).get("element_ids", {})
    values = raw.get(element_type.value) if isinstance(raw, dict) else None
    if values is None:
        return list(range(1, n_elements + 1))
    labels = [int(value) for value in values]
    if len(labels) != n_elements:
        raise FormatError(
            f"meta['element_ids'][{element_type.value!r}] has {len(labels)} labels for "
            f"{n_elements} elements"
        )
    return labels


def _resolve_property(
    neutral: NeutralModel,
    element_type: ElementType,
    property_id: int,
    defaults: _Defaults,
) -> tuple[Material, Section | None, float]:
    """``(material, section, thickness)`` for one property id of one block."""

    property_ = neutral.properties.get(property_id)
    values = dict(property_.values) if property_ is not None else {}
    where = f"{element_type.value} property {property_id}"

    material = _resolve_material(neutral, property_, defaults, where)
    section: Section | None = None
    if element_type in (ElementType.ROD2, ElementType.BEAM2):
        if _lookup(values, _SECTION_ALIASES["area"]) is not None:
            section = section_from_values(values, description=where)
        elif defaults.section is not None:
            section = defaults.section
        else:
            raise FormatError(
                f"{where} defines no cross-section and no section= fallback was given"
            )
    thickness = _lookup(values, _THICKNESS_ALIASES)
    return material, section, defaults.thickness if thickness is None else thickness


def _resolve_material(
    neutral: NeutralModel,
    property_: NeutralProperty | None,
    defaults: _Defaults,
    where: str,
) -> Material:
    if property_ is not None:
        neutral_material = neutral.materials.get(property_.material_id)
        if neutral_material is not None:
            return material_from_neutral(neutral_material)
        if defaults.material is None:
            raise FormatError(
                f"{where} references material {property_.material_id}, which the model does "
                "not define, and no material= fallback was given"
            )
        return defaults.material
    if defaults.material is None:
        raise FormatError(
            f"{where} is not defined by the model and no material= fallback was given"
        )
    return defaults.material


def _build_element(
    element_type: ElementType,
    node_ids: list[int],
    material: Material,
    section: Section | None,
    thickness: float,
    element_id: int,
    signature: tuple[DOF, ...],
    defaults: _Defaults,
) -> Element:
    try:
        if element_type is ElementType.ROD2:
            return TrussElement(
                node_ids,
                material,
                _required_section(section, element_type, element_id),
                lumped_mass=defaults.lumped_mass,
                eid=element_id,
            )
        if element_type is ElementType.TRI3:
            return Tri3Element(
                node_ids,
                material,
                thickness=thickness,
                plane=defaults.plane,
                lumped_mass=defaults.lumped_mass,
                eid=element_id,
            )
        if element_type is ElementType.BEAM2:
            return _build_beam(
                node_ids,
                material,
                _required_section(section, element_type, element_id),
                element_id,
                signature,
                defaults,
            )
        if element_type is ElementType.QUAD4:
            if defaults.quad4_as == "shell":
                return ShellQuad4Element(
                    node_ids,
                    material,
                    thickness=thickness,
                    lumped_mass=defaults.lumped_mass,
                    integration_order=defaults.integration_order,
                    eid=element_id,
                )
            return Quad4Element(
                node_ids,
                material,
                thickness=thickness,
                plane=defaults.plane,
                lumped_mass=defaults.lumped_mass,
                integration_order=defaults.integration_order,
                eid=element_id,
            )
        if element_type is ElementType.TET4:
            return Tet4Element(
                node_ids, material, lumped_mass=defaults.lumped_mass, eid=element_id
            )
        return Hex8Element(
            node_ids,
            material,
            lumped_mass=defaults.lumped_mass,
            integration_order=defaults.integration_order,
            eid=element_id,
        )
    except OpenFEMLabError as exc:
        raise FormatError(
            f"{element_type.value} element {element_id} {tuple(node_ids)} is invalid: {exc}"
        ) from exc


def _required_section(
    section: Section | None, element_type: ElementType, element_id: int
) -> Section:
    if section is None:
        raise FormatError(f"{element_type.value} element {element_id} has no cross-section")
    return section


def _build_beam(
    node_ids: list[int],
    material: Material,
    section: Section,
    element_id: int,
    signature: tuple[DOF, ...],
    defaults: _Defaults,
) -> Element:
    if all(dof in signature for dof in _SPATIAL_BEAM_DOFS):
        return BeamElement3D(
            node_ids,
            material,
            section,
            orientation=defaults.beam_orientation,
            lumped_mass=defaults.lumped_mass,
            eid=element_id,
        )
    if all(dof in signature for dof in _PLANAR_BEAM_DOFS):
        return BeamElement2D(
            node_ids, material, section, lumped_mass=defaults.lumped_mass, eid=element_id
        )
    raise FormatError(
        f"beam2 element {element_id} needs either the six spatial DOFs or the planar "
        f"(UX, UY, RZ) set, but the model is active in {[d.name for d in signature]}"
    )


def _meta(neutral: NeutralModel) -> dict[str, Any]:
    return neutral.meta if isinstance(neutral.meta, dict) else {}


def apply_rbe2_from_neutral(model: Model, neutral: NeutralModel) -> None:
    """Register ``RBE2`` cards preserved in ``meta['bdf_preserve']`` on ``model``."""

    for fields in _meta(neutral).get("bdf_preserve", ()):
        if not fields or str(fields[0]).upper() != "RBE2":
            continue
        if len(fields) < 5:
            raise FormatError(f"RBE2 card {fields!r} is incomplete")
        _, eid, master, cm, *slaves = fields
        if not slaves:
            raise FormatError(f"RBE2 {eid} has no slave nodes")
        try:
            components = parse_nastran_components(cm)
        except OpenFEMLabError as exc:
            raise FormatError(f"RBE2 {eid}: {exc}") from exc
        active = tuple(dof for dof in components if model.has_dof(dof))
        if not active:
            raise FormatError(
                f"RBE2 {eid} CM={cm!r} does not overlap the model DOF signature "
                f"{[d.name for d in model.dofs]}"
            )
        model.tie_rbe2(
            int(master),
            [int(node_id) for node_id in slaves],
            components=active,
            eid=int(eid),
        )


def apply_rbe3_from_neutral(model: Model, neutral: NeutralModel) -> None:
    """Register ``RBE3`` cards preserved in ``meta['bdf_preserve']`` on ``model``."""

    for fields in _meta(neutral).get("bdf_preserve", ()):
        if not fields or str(fields[0]).upper() != "RBE3":
            continue
        try:
            eid, dependent, refc, groups = _parse_rbe3_preserve_fields(fields)
        except (OpenFEMLabError, ValueError, IndexError) as exc:
            raise FormatError(f"RBE3 card {fields!r} is invalid: {exc}") from exc
        active_dep = tuple(dof for dof in refc if model.has_dof(dof))
        if not active_dep:
            raise FormatError(
                f"RBE3 {eid} REFC does not overlap the model DOF signature "
                f"{[d.name for d in model.dofs]}"
            )
        active_groups: list[RBE3Group] = []
        for weight, components, independents in groups:
            active_c = tuple(dof for dof in components if model.has_dof(dof))
            if not active_c or not independents:
                continue
            active_groups.append(
                RBE3Group(weight=weight, components=active_c, independents=tuple(independents))
            )
        if not active_groups:
            raise FormatError(f"RBE3 {eid} has no usable independent groups")
        model._rbe3_ties.append(  # noqa: SLF001 — converter registers structured ties
            RBE3Tie(
                dependent=dependent,
                dependent_components=active_dep,
                groups=tuple(active_groups),
                eid=eid,
            )
        )


def apply_spc1_from_neutral(model: Model, neutral: NeutralModel) -> None:
    """Apply ``SPC1`` cards stored in ``meta['bdf_spc1']`` or ``bdf_preserve``."""

    for entry in _meta(neutral).get("bdf_spc1", ()):
        components = parse_nastran_components(entry["components"])
        active = tuple(dof for dof in components if model.has_dof(dof))
        if not active:
            continue
        for node_id in entry["nodes"]:
            model.fix(int(node_id), active)
    for fields in _meta(neutral).get("bdf_preserve", ()):
        if not fields or str(fields[0]).upper() != "SPC1":
            continue
        if len(fields) < 4:
            raise FormatError(f"SPC1 card {fields!r} is incomplete")
        # SPC1, SID, C, G1, G2, ...
        _, _sid, cm, *nodes = fields
        if not nodes:
            raise FormatError(f"SPC1 {_sid} has no grid ids")
        try:
            components = parse_nastran_components(cm)
        except OpenFEMLabError as exc:
            raise FormatError(f"SPC1 {_sid}: {exc}") from exc
        active = tuple(dof for dof in components if model.has_dof(dof))
        if not active:
            continue
        for node_id in nodes:
            model.fix(int(node_id), active)


def apply_conm2_from_neutral(model: Model, neutral: NeutralModel) -> None:
    """Apply ``CONM2`` concentrated masses from ``meta['bdf_conm2']`` or preserve."""

    for entry in _meta(neutral).get("bdf_conm2", ()):
        node_id = int(entry["node"])
        mass = float(entry["mass"])
        if mass > 0.0:
            model.add_point_mass(node_id, mass)
        inertia = entry.get("inertia") or {}
        mapping = {
            "I11": DOF.RX,
            "I22": DOF.RY,
            "I33": DOF.RZ,
        }
        for key, dof in mapping.items():
            value = float(inertia.get(key, 0.0))
            if value > 0.0 and model.has_dof(dof):
                model.add_rotary_inertia(node_id, value, dofs=(dof,))
    for fields in _meta(neutral).get("bdf_preserve", ()):
        if not fields or str(fields[0]).upper() != "CONM2":
            continue
        # CONM2, EID, G, CID, M, X1, X2, X3, I11, I21, I22, ...
        if len(fields) < 5:
            raise FormatError(f"CONM2 card {fields!r} is incomplete")
        node_id = int(fields[2])
        mass = float(fields[4])
        if mass > 0.0:
            model.add_point_mass(node_id, mass)
        if len(fields) >= 9:
            i11 = float(fields[8]) if fields[8] not in ("",) else 0.0
            if i11 > 0.0 and model.has_dof(DOF.RX):
                model.add_rotary_inertia(node_id, i11, dofs=(DOF.RX,))
        if len(fields) >= 11:
            i22 = float(fields[10]) if fields[10] not in ("",) else 0.0
            if i22 > 0.0 and model.has_dof(DOF.RY):
                model.add_rotary_inertia(node_id, i22, dofs=(DOF.RY,))
        if len(fields) >= 14:
            i33 = float(fields[13]) if fields[13] not in ("",) else 0.0
            if i33 > 0.0 and model.has_dof(DOF.RZ):
                model.add_rotary_inertia(node_id, i33, dofs=(DOF.RZ,))


def apply_force_from_neutral(model: Model, neutral: NeutralModel) -> None:
    """Apply ``FORCE`` cards stored in ``meta['bdf_force']`` or ``bdf_preserve``."""

    for entry in _meta(neutral).get("bdf_force", ()):
        model.add_nodal_load(
            int(entry["node"]),
            float(entry["magnitude"]),
            direction=tuple(entry["direction"]),
        )
    for fields in _meta(neutral).get("bdf_preserve", ()):
        if not fields or str(fields[0]).upper() != "FORCE":
            continue
        if len(fields) < 5:
            raise FormatError(f"FORCE card {fields!r} is incomplete")
        node_id = int(fields[2])
        magnitude = float(fields[4])
        direction = [0.0, 0.0, 0.0]
        for index, offset in enumerate((5, 6, 7)):
            if len(fields) > offset and str(fields[offset]).strip():
                direction[index] = float(fields[offset])
        model.add_nodal_load(node_id, magnitude, direction=direction)


def apply_moment_from_neutral(model: Model, neutral: NeutralModel) -> None:
    """Apply ``MOMENT`` cards stored in ``meta['bdf_moment']`` or ``bdf_preserve``."""

    for entry in _meta(neutral).get("bdf_moment", ()):
        _apply_nodal_moment(
            model,
            int(entry["node"]),
            float(entry["magnitude"]),
            direction=tuple(entry["direction"]),
        )
    for fields in _meta(neutral).get("bdf_preserve", ()):
        if not fields or str(fields[0]).upper() != "MOMENT":
            continue
        if len(fields) < 5:
            raise FormatError(f"MOMENT card {fields!r} is incomplete")
        node_id = int(fields[2])
        magnitude = float(fields[4])
        direction = [0.0, 0.0, 0.0]
        for index, offset in enumerate((5, 6, 7)):
            if len(fields) > offset and str(fields[offset]).strip():
                direction[index] = float(fields[offset])
        _apply_nodal_moment(model, node_id, magnitude, direction=direction)


def _apply_nodal_moment(
    model: Model,
    node_id: int,
    magnitude: float,
    *,
    direction: Sequence[float],
) -> None:
    components = np.asarray(direction, dtype=float).reshape(-1)
    if components.size > 3:
        raise FormatError(f"moment direction must have at most 3 components, got {components.size}")
    norm = float(np.linalg.norm(components))
    if norm <= 0.0:
        raise FormatError("moment direction vector must be non-zero")
    unit = components / norm
    rotational = model.rotational_dofs
    if not rotational:
        raise FormatError("model has no rotational DOFs for MOMENT loads")
    for active in rotational:
        axis = int(active) - int(DOF.RX)
        if axis < 0 or axis >= unit.size:
            continue
        component = unit[axis]
        if component == 0.0:
            continue
        index = model.dof_index(node_id, active)
        model._nodal_loads[index] = (
            model._nodal_loads.get(index, 0.0) + float(magnitude) * component
        )


def _parse_rbe3_preserve_fields(
    fields: Sequence[Any],
) -> tuple[int, int, tuple[DOF, ...], list[tuple[float, tuple[DOF, ...], list[int]]]]:
    """Parse a preserved free-field ``RBE3`` card into structured pieces.

    Supports the common single-group form::

        RBE3,eid[,blank],refgrid,refc,wt,c,g1,g2,...

    and multi-group cards when each subsequent weight is written with a decimal
    (``1.0``) so it can be distinguished from a grid id.
    """

    tokens = [str(item).strip() for item in fields[1:]]
    if not tokens:
        raise ValueError("missing fields")
    eid = int(tokens.pop(0))
    if tokens and tokens[0] == "":
        tokens.pop(0)
    if len(tokens) < 4:
        raise ValueError("expected REFGRID, REFC, WT, C, G...")
    dependent = int(tokens.pop(0))
    refc = parse_nastran_components(tokens.pop(0))
    groups: list[tuple[float, tuple[DOF, ...], list[int]]] = []
    while tokens:
        weight = float(tokens.pop(0))
        if not tokens:
            raise ValueError("weight without component code")
        components = parse_nastran_components(tokens.pop(0))
        independents: list[int] = []
        while tokens:
            peek = tokens[0]
            if "." in peek or "e" in peek.lower():
                break
            independents.append(int(peek))
            tokens.pop(0)
        if not independents:
            raise ValueError("independent group has no grid ids")
        groups.append((weight, components, independents))
    return eid, dependent, refc, groups


def _lookup(values: dict[str, float], aliases: Sequence[str]) -> float | None:
    folded = {str(key).strip().lower(): value for key, value in values.items()}
    for alias in aliases:
        if alias in folded:
            try:
                return float(folded[alias])
            except (TypeError, ValueError) as exc:
                raise FormatError(f"property value {alias!r} is not a number") from exc
    return None
