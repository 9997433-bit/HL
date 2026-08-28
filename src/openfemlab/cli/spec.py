"""Declarative model specification read by the OpenFEMLab CLI.

A *spec* is a JSON/YAML mapping describing one structure together with the
boundary conditions and concentrated masses that the neutral interchange
format of :mod:`openfemlab.core.neutral` deliberately does not carry. It is
the CLI's project file: the same document drives ``openfemlab modal`` and the
model rebuilt at every iteration of ``openfemlab update``.

``mesh.type`` selects a generator from :mod:`openfemlab.mesh.simple`, or
``custom`` for an explicit node/element listing::

    name: cantilever
    materials:
      steel: {E: 2.1e11, density: 7850.0}
    sections:
      strip: {area: 1.0e-4, inertia_z: 8.333e-10}
    mesh:
      type: beam
      length: 1.0
      num_elements: 20
      support: cantilever
      material: steel
      section: strip
    point_masses:
      - {node: 20, mass: 0.5}

Updating addresses individual numbers in this document by dotted path
(``mesh.material.E``, ``mesh.elements.2.stiffness``), which is what
:func:`lookup` and :func:`scaled` implement.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from os import PathLike
from typing import Any

from ..core.elements import BeamElement2D, SpringElement, TrussElement
from ..core.model import DOF, Material, Model, Section
from ..exceptions import OpenFEMLabError
from ..mesh.simple import bar_mesh, beam_mesh, spring_mass_chain, truss_from_arrays

__all__ = ["SpecError", "MESH_TYPES", "load_spec", "build_model", "lookup", "scaled"]


class SpecError(OpenFEMLabError):
    """A CLI model specification is malformed or references unknown entries."""


MESH_TYPES = ("bar", "beam", "chain", "truss", "custom")


def load_spec(source: str | PathLike[str]) -> dict[str, Any]:
    """Read a spec document from a JSON or YAML file."""
    from ..io import read_data

    document = read_data(source)
    if not isinstance(document, Mapping):
        raise SpecError(f"{source}: a model spec must be a mapping")
    return dict(document)


def build_model(spec: Mapping[str, Any]) -> Model:
    """Instantiate the solver model described by ``spec``."""
    mesh = _mapping(spec.get("mesh", spec), "mesh")
    kind = str(mesh.get("type", "")).strip().lower()
    builder = _BUILDERS.get(kind)
    if builder is None:
        raise SpecError(
            f"unknown mesh type {kind!r}; expected one of {', '.join(MESH_TYPES)}"
        )
    model = builder(mesh, spec)
    _apply_supports(model, spec.get("supports", ()))
    _apply_point_masses(model, spec.get("point_masses", ()))
    _apply_rotary_inertias(model, spec.get("rotary_inertias", ()))
    _apply_loads(model, spec.get("loads", ()))
    return model


# --------------------------------------------------------------- dotted paths


def lookup(document: Any, path: str) -> Any:
    """Resolve a dotted ``path`` against a nested mapping/sequence document."""
    node = document
    for token in _tokens(path):
        node = _descend(node, token, path)
    return node


def scaled(spec: Mapping[str, Any], factors: Mapping[str, float]) -> dict[str, Any]:
    """Copy ``spec`` with every addressed value multiplied by its factor.

    Updating parameters are dimensionless scaling factors, so the nominal
    values in the original document always stay the reference: repeated calls
    with the same factors give the same model.
    """
    patched = copy.deepcopy(dict(spec))
    for path, factor in factors.items():
        nominal = lookup(spec, path)
        try:
            value = float(nominal) * float(factor)
        except (TypeError, ValueError) as exc:
            raise SpecError(f"{path} is not a number and cannot be scaled") from exc
        _assign(patched, path, value)
    return patched


def _tokens(path: str) -> list[str]:
    tokens = [token for token in str(path).split(".") if token]
    if not tokens:
        raise SpecError("an empty parameter target cannot be resolved")
    return tokens


def _descend(node: Any, token: str, path: str) -> Any:
    if isinstance(node, Mapping):
        if token not in node:
            raise SpecError(f"{path}: the spec has no entry {token!r}")
        return node[token]
    if isinstance(node, Sequence) and not isinstance(node, (str, bytes)):
        index = _index(token, path)
        if not -len(node) <= index < len(node):
            raise SpecError(f"{path}: index {index} is out of range")
        return node[index]
    raise SpecError(f"{path}: {token!r} cannot be resolved inside a {type(node).__name__}")


def _assign(document: Any, path: str, value: Any) -> None:
    tokens = _tokens(path)
    node = document
    for token in tokens[:-1]:
        node = _descend(node, token, path)
    leaf = tokens[-1]
    if isinstance(node, Mapping):
        node[leaf] = value  # type: ignore[index]
        return
    if isinstance(node, list):
        node[_index(leaf, path)] = value
        return
    raise SpecError(f"{path}: cannot assign into a {type(node).__name__}")


def _index(token: str, path: str) -> int:
    try:
        return int(token)
    except ValueError as exc:
        raise SpecError(f"{path}: {token!r} is not a sequence index") from exc


# ------------------------------------------------------------------ builders


def _build_bar(mesh: Mapping[str, Any], spec: Mapping[str, Any]) -> Model:
    return bar_mesh(
        length=_number(mesh, "length"),
        num_elements=_count(mesh, "num_elements", default=10),
        material=_material(mesh.get("material"), spec),
        section=_section(mesh.get("section"), spec),
        dofs=_dofs(mesh.get("dofs", ("UX",))),
        fixed_start=bool(mesh.get("fixed_start", True)),
        fixed_end=bool(mesh.get("fixed_end", False)),
        direction=_point(mesh.get("direction", (1.0, 0.0, 0.0)), "direction"),
        origin=_point(mesh.get("origin", (0.0, 0.0, 0.0)), "origin"),
        lumped_mass=bool(mesh.get("lumped_mass", False)),
        tip_mass=_optional_number(mesh.get("tip_mass"), "tip_mass"),
        name=_name(spec, "bar"),
    )


def _build_beam(mesh: Mapping[str, Any], spec: Mapping[str, Any]) -> Model:
    return beam_mesh(
        length=_number(mesh, "length"),
        num_elements=_count(mesh, "num_elements", default=10),
        material=_material(mesh.get("material"), spec),
        section=_section(mesh.get("section"), spec),
        support=str(mesh.get("support", "cantilever")),
        origin=_point(mesh.get("origin", (0.0, 0.0, 0.0)), "origin"),
        lumped_mass=bool(mesh.get("lumped_mass", False)),
        tip_mass=_optional_number(mesh.get("tip_mass"), "tip_mass"),
        name=_name(spec, "beam"),
    )


def _build_chain(mesh: Mapping[str, Any], spec: Mapping[str, Any]) -> Model:
    return spring_mass_chain(
        num_masses=_count(mesh, "num_masses", default=None),
        stiffness=_numbers(mesh.get("stiffness"), "stiffness"),
        mass=_numbers(mesh.get("mass"), "mass"),
        fixed_start=bool(mesh.get("fixed_start", True)),
        fixed_end=bool(mesh.get("fixed_end", False)),
        spacing=float(mesh.get("spacing", 1.0)),
        name=_name(spec, "chain"),
    )


def _build_truss(mesh: Mapping[str, Any], spec: Mapping[str, Any]) -> Model:
    for key in ("coordinates", "connectivity"):
        if mesh.get(key) is None:
            raise SpecError(f"a truss mesh requires {key!r}")
    return truss_from_arrays(
        mesh["coordinates"],
        mesh["connectivity"],
        material=_material(mesh.get("material"), spec),
        section=_section(mesh.get("section"), spec),
        dofs=_dofs(mesh.get("dofs", ("UX", "UY"))),
        lumped_mass=bool(mesh.get("lumped_mass", False)),
        name=_name(spec, "truss"),
    )


def _build_custom(mesh: Mapping[str, Any], spec: Mapping[str, Any]) -> Model:
    model = Model(dofs=_dofs(mesh.get("dofs", ("UX", "UY", "UZ"))), name=_name(spec, "model"))
    for entry in _sequence(mesh.get("nodes"), "nodes"):
        node_id, coords = _node_entry(entry)
        model.add_node(node_id, coords)
    for entry in _sequence(mesh.get("elements"), "elements"):
        model.add_element(_element(_mapping(entry, "element"), spec))
    return model


_BUILDERS = {
    "bar": _build_bar,
    "beam": _build_beam,
    "chain": _build_chain,
    "truss": _build_truss,
    "custom": _build_custom,
}


def _element(entry: Mapping[str, Any], spec: Mapping[str, Any]):
    kind = str(entry.get("type", "")).strip().lower()
    nodes = _sequence(entry.get("nodes"), "element nodes")
    eid = entry.get("id")
    if kind == "spring":
        return SpringElement(
            nodes,
            _number(entry, "stiffness"),
            dof=DOF.parse(entry.get("dof", "UX")),
            eid=eid,
        )
    if kind in {"truss", "bar", "rod"}:
        return TrussElement(
            nodes,
            _material(entry.get("material"), spec),
            _section(entry.get("section"), spec),
            lumped_mass=bool(entry.get("lumped_mass", False)),
            eid=eid,
        )
    if kind in {"beam", "beam2d"}:
        return BeamElement2D(
            nodes,
            _material(entry.get("material"), spec),
            _section(entry.get("section"), spec),
            lumped_mass=bool(entry.get("lumped_mass", False)),
            eid=eid,
        )
    raise SpecError(f"unknown element type {kind!r}; expected spring, truss or beam")


# -------------------------------------------------- boundary conditions/mass


def _apply_supports(model: Model, entries: Any) -> None:
    for entry in _sequence(entries, "supports", allow_empty=True):
        data = _mapping(entry, "support")
        dofs = data.get("dofs")
        for node_id in _node_ids(data, "support"):
            model.fix(node_id, None if dofs is None else _dofs(dofs))


def _apply_point_masses(model: Model, entries: Any) -> None:
    for entry in _sequence(entries, "point_masses", allow_empty=True):
        data = _mapping(entry, "point mass")
        dofs = data.get("dofs")
        for node_id in _node_ids(data, "point mass"):
            model.add_point_mass(
                node_id, _number(data, "mass"), None if dofs is None else _dofs(dofs)
            )


def _apply_rotary_inertias(model: Model, entries: Any) -> None:
    for entry in _sequence(entries, "rotary_inertias", allow_empty=True):
        data = _mapping(entry, "rotary inertia")
        dofs = data.get("dofs")
        for node_id in _node_ids(data, "rotary inertia"):
            model.add_rotary_inertia(
                node_id, _number(data, "inertia"), None if dofs is None else _dofs(dofs)
            )


def _apply_loads(model: Model, entries: Any) -> None:
    for entry in _sequence(entries, "loads", allow_empty=True):
        data = _mapping(entry, "load")
        if "magnitude" in data:
            magnitude = _number(data, "magnitude")
        elif "force" in data:
            magnitude = _number(data, "force")
        else:
            raise SpecError("load entry requires 'magnitude' or 'force'")
        for node_id in _node_ids(data, "load"):
            if "direction" in data:
                direction = data["direction"]
                if isinstance(direction, str):
                    model.add_nodal_load(node_id, magnitude, dof=direction)
                else:
                    model.add_nodal_load(node_id, magnitude, direction=direction)
            elif "dof" in data:
                model.add_nodal_load(node_id, magnitude, dof=data["dof"])
            else:
                model.add_nodal_load(node_id, magnitude)


# -------------------------------------------------------------- value parsing


def _mapping(value: Any, description: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SpecError(f"{description} must be a mapping, got {type(value).__name__}")
    return value


def _sequence(value: Any, description: str, *, allow_empty: bool = False) -> list[Any]:
    if value is None:
        if allow_empty:
            return []
        raise SpecError(f"the spec is missing required entry {description!r}")
    if isinstance(value, Mapping) or isinstance(value, (str, bytes)):
        raise SpecError(f"{description} must be a sequence")
    return list(value)


def _name(spec: Mapping[str, Any], fallback: str) -> str:
    return str(spec.get("name", fallback))


def _number(data: Mapping[str, Any], key: str) -> float:
    if key not in data:
        raise SpecError(f"missing required entry {key!r}")
    try:
        return float(data[key])
    except (TypeError, ValueError) as exc:
        raise SpecError(f"{key} must be a number, got {data[key]!r}") from exc


def _optional_number(value: Any, description: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise SpecError(f"{description} must be a number, got {value!r}") from exc


def _numbers(value: Any, description: str) -> Any:
    """Pass a scalar or a per-item sequence straight through to the builder."""
    if value is None:
        raise SpecError(f"the spec is missing required entry {description!r}")
    if isinstance(value, (str, bytes)) or isinstance(value, Mapping):
        raise SpecError(f"{description} must be a number or a sequence of numbers")
    return value


def _count(data: Mapping[str, Any], key: str, *, default: int | None) -> int:
    raw = data.get(key, data.get(key.replace("num_", "n_"), default))
    if raw is None:
        raise SpecError(f"missing required entry {key!r}")
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise SpecError(f"{key} must be an integer, got {raw!r}") from exc


def _point(value: Any, description: str) -> tuple[float, ...]:
    try:
        return tuple(float(item) for item in value)
    except (TypeError, ValueError) as exc:
        raise SpecError(f"{description} must be a sequence of numbers, got {value!r}") from exc


def _dofs(value: Any) -> tuple[DOF, ...]:
    items = [value] if isinstance(value, (str, int)) else list(value)
    return tuple(DOF.parse(item) for item in items)


def _node_ids(data: Mapping[str, Any], description: str) -> list[Any]:
    if "nodes" in data:
        return _sequence(data["nodes"], f"{description} nodes")
    if "node" in data:
        return [data["node"]]
    raise SpecError(f"a {description} entry needs 'node' or 'nodes'")


def _node_entry(entry: Any) -> tuple[Any, tuple[float, ...]]:
    if isinstance(entry, Mapping):
        if "id" not in entry:
            raise SpecError("a node entry needs an 'id'")
        coords = entry.get("coords", entry.get("coordinates"))
        if coords is None:
            coords = [entry.get(axis, 0.0) for axis in ("x", "y", "z")]
        return entry["id"], _point(coords, "node coordinates")
    items = _sequence(entry, "node entry")
    if len(items) < 2:
        raise SpecError("a node entry needs an id followed by its coordinates")
    return items[0], _point(items[1:], "node coordinates")


def _material(value: Any, spec: Mapping[str, Any]) -> Material:
    data = _mapping(_resolve_named(value, spec, "materials"), "material")
    return Material(
        E=_number(data, "E"),
        density=float(data.get("density", data.get("rho", 0.0))),
        nu=float(data.get("nu", 0.3)),
        name=str(data.get("name", "")),
    )


def _section(value: Any, spec: Mapping[str, Any]) -> Section:
    data = _mapping(_resolve_named(value, spec, "sections"), "section")
    return Section(
        area=_number(data, "area"),
        inertia_z=float(data.get("inertia_z", data.get("Iz", 0.0))),
        inertia_y=float(data.get("inertia_y", data.get("Iy", 0.0))),
        torsion_constant=float(data.get("torsion_constant", data.get("J", 0.0))),
        name=str(data.get("name", "")),
    )


def _resolve_named(value: Any, spec: Mapping[str, Any], table_key: str) -> Any:
    """Expand a ``"steel"``-style reference into the matching root-level table."""
    if value is None:
        raise SpecError(f"missing required entry {table_key[:-1]!r}")
    if not isinstance(value, str):
        return value
    table = _mapping(spec.get(table_key, {}), table_key)
    if value not in table:
        known = ", ".join(sorted(table)) or "none defined"
        raise SpecError(f"unknown {table_key[:-1]} {value!r} (known: {known})")
    return table[value]
