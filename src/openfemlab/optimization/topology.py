"""SIMP topology optimization (compliance minimization with volume constraint)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from ..exceptions import OptimizationError

__all__ = [
    "TopologyResult",
    "assemble_simp_stiffness",
    "element_strain_energy",
    "element_volumes",
    "oc_update",
    "run_simp_topology",
    "simp_penalized_modulus",
]


def simp_penalized_modulus(
    density: float,
    *,
    youngs_modulus: float,
    penalization: float = 3.0,
    e_min: float = 1e-9,
) -> float:
    """SIMP effective Young's modulus ``E_min + rho^p (E - E_min)``."""
    rho = float(np.clip(density, 0.0, 1.0))
    return float(e_min + (rho**penalization) * (youngs_modulus - e_min))


def element_volumes(model) -> np.ndarray:
    """Physical volume (or area×thickness proxy) per element."""
    volumes = np.zeros(model.num_elements, dtype=float)
    for index, element in enumerate(model.elements):
        coords = model.node_coords(element.node_ids)
        if hasattr(element, "area") and hasattr(element, "thickness"):
            volumes[index] = float(element.area(coords) * element.thickness)
        elif hasattr(element, "length"):
            area = float(getattr(getattr(element, "section", None), "area", 1.0))
            volumes[index] = float(element.length(coords) * area)
        else:
            volumes[index] = 1.0
    return volumes


def assemble_simp_stiffness(
    model,
    densities: np.ndarray,
    *,
    penalization: float = 3.0,
    e_min: float = 1e-9,
) -> sp.csr_matrix:
    """Assemble penalized stiffness for element densities ``rho_e in [0, 1]``."""
    rho = np.asarray(densities, dtype=float).reshape(-1)
    if rho.size != model.num_elements:
        raise OptimizationError(
            f"expected {model.num_elements} element densities, got {rho.size}"
        )
    num_dofs = model.num_dofs
    if model.num_elements == 0:
        raise OptimizationError("model has no elements for SIMP assembly")
    counts = np.fromiter(
        (element.num_dofs**2 for element in model.elements),
        dtype=np.intp,
        count=model.num_elements,
    )
    offsets = np.empty(model.num_elements + 1, dtype=np.intp)
    offsets[0] = 0
    np.cumsum(counts, out=offsets[1:])
    rows = np.empty(int(offsets[-1]), dtype=np.intp)
    cols = np.empty_like(rows)
    data = np.empty(rows.size, dtype=float)
    for index, element in enumerate(model.elements):
        coords = model.node_coords(element.node_ids)
        dofs = element.global_dofs(model)
        local = np.asarray(element.stiffness_matrix(coords), dtype=float)
        material = getattr(element, "material", None)
        youngs = float(getattr(material, "E", 1.0))
        scale = simp_penalized_modulus(
            rho[index], youngs_modulus=youngs, penalization=penalization, e_min=e_min
        ) / youngs
        start, stop = int(offsets[index]), int(offsets[index + 1])
        expected = (dofs.size, dofs.size)
        if local.shape != expected:
            raise OptimizationError(
                f"{type(element).__name__} returned unexpected local stiffness shape"
            )
        rows[start:stop] = np.repeat(dofs, dofs.size)
        cols[start:stop] = np.tile(dofs, dofs.size)
        data[start:stop] = (scale * local).reshape(-1)
    matrix = sp.coo_matrix((data, (rows, cols)), shape=(num_dofs, num_dofs)).tocsr()
    matrix = ((matrix + matrix.T) * 0.5).tocsr()
    matrix.eliminate_zeros()
    return matrix


def element_strain_energy(
    model,
    displacements: np.ndarray,
    densities: np.ndarray,
    *,
    penalization: float = 3.0,
    e_min: float = 1e-9,
) -> np.ndarray:
    """Per-element strain energy density proxy used by the OC update."""
    energies = np.zeros(model.num_elements, dtype=float)
    u = np.asarray(displacements, dtype=float).reshape(-1)
    for index, element in enumerate(model.elements):
        coords = model.node_coords(element.node_ids)
        dofs = element.global_dofs(model)
        local = np.asarray(element.stiffness_matrix(coords), dtype=float)
        ue = u[dofs]
        energies[index] = float(ue @ local @ ue)
    return energies


def oc_update(
    densities: np.ndarray,
    strain_energy: np.ndarray,
    volumes: np.ndarray,
    *,
    vol_frac: float,
    move: float = 0.2,
    penalization: float = 3.0,
    e_min: float = 1e-9,
) -> np.ndarray:
    """Classic optimality-criteria density update with move limit."""
    rho = np.asarray(densities, dtype=float).reshape(-1)
    dc = -float(penalization) * np.power(
        np.maximum(rho, 1e-3), penalization - 1.0
    ) * np.maximum(strain_energy, 0.0)
    dv = np.asarray(volumes, dtype=float).reshape(-1)
    total = float(dv.sum()) or 1.0
    target = float(vol_frac) * total
    lo, hi = 0.0, 1e20
    rho_min = 0.001
    candidate = rho.copy()
    while hi - lo > 1e-4:
        mid = 0.5 * (lo + hi)
        ratio = np.maximum(-dc / np.maximum(dv, 1e-30), 0.0) / mid
        candidate = np.maximum(
            rho_min,
            np.maximum(
                rho - move,
                np.minimum(1.0, np.minimum(rho + move, rho * np.sqrt(ratio))),
            ),
        )
        if float((candidate * dv).sum()) - target > 0.0:
            lo = mid
        else:
            hi = mid
    return candidate


@dataclass
class TopologyResult:
    """Outcome of a SIMP OC topology optimization run."""

    densities: np.ndarray
    compliance_history: list[float] = field(default_factory=list)
    volume_history: list[float] = field(default_factory=list)
    displacements: np.ndarray | None = None
    iterations: int = 0
    meta: dict[str, object] = field(default_factory=dict)

    @property
    def mean_density(self) -> float:
        return float(np.mean(self.densities))


def run_simp_topology(
    model,
    *,
    vol_frac: float = 0.4,
    penalization: float = 3.0,
    e_min: float = 1e-9,
    max_iter: int = 50,
    move: float = 0.2,
    tol: float = 1e-3,
) -> TopologyResult:
    """Minimize compliance with a SIMP penalization and OC updates."""
    if not 0.0 < vol_frac <= 1.0:
        raise OptimizationError("vol_frac must lie in (0, 1]")
    if model.load_vector().sum() == 0.0:
        raise OptimizationError("topology optimization requires non-zero nodal loads")
    volumes = element_volumes(model)
    rho = np.full(model.num_elements, float(vol_frac), dtype=float)
    history_c: list[float] = []
    history_v: list[float] = []
    last_u: np.ndarray | None = None
    for iteration in range(max_iter):
        k = assemble_simp_stiffness(
            model, rho, penalization=penalization, e_min=e_min
        )
        load = model.load_vector()
        free = model.free_dofs
        k_ff = k[free, :][:, free].tocsr()
        f_f = load[free]
        u_f = spla.spsolve(k_ff, f_f)
        u = np.zeros(model.num_dofs, dtype=float)
        u[free] = np.asarray(u_f, dtype=float).reshape(-1)
        last_u = u
        energies = element_strain_energy(
            model, u, rho, penalization=penalization, e_min=e_min
        )
        compliance = float(f_f @ u_f)
        volume = float((rho * volumes).sum() / (volumes.sum() or 1.0))
        history_c.append(compliance)
        history_v.append(volume)
        rho_new = oc_update(
            rho,
            energies,
            volumes,
            vol_frac=vol_frac,
            move=move,
            penalization=penalization,
            e_min=e_min,
        )
        change = float(np.max(np.abs(rho_new - rho)))
        rho = rho_new
        if iteration > 5 and change < tol:
            return TopologyResult(
                densities=rho,
                compliance_history=history_c,
                volume_history=history_v,
                displacements=last_u,
                iterations=iteration + 1,
                meta={"penalization": penalization, "vol_frac": vol_frac},
            )
    return TopologyResult(
        densities=rho,
        compliance_history=history_c,
        volume_history=history_v,
        displacements=last_u,
        iterations=max_iter,
        meta={"penalization": penalization, "vol_frac": vol_frac},
    )
