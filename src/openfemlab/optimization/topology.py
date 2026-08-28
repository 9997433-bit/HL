"""SIMP topology optimization (compliance minimization with volume constraint)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from ..exceptions import OptimizationError

__all__ = [
    "TopologyResult",
    "apply_density_filter",
    "assemble_simp_stiffness",
    "build_density_filter",
    "effective_heaviside_beta",
    "element_centroids",
    "element_strain_energy",
    "element_volumes",
    "filter_sensitivities",
    "heaviside_projection",
    "heaviside_projection_derivative",
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
        elif hasattr(element, "volume"):
            volumes[index] = float(element.volume(coords))
        else:
            volumes[index] = 1.0
    return volumes


def element_centroids(model) -> np.ndarray:
    """Element centroids as ``(num_elements, spatial_dim)`` coordinates."""
    if model.num_elements == 0:
        return np.zeros((0, 3), dtype=float)
    spatial_dim = max(len(node.coords) for node in model.nodes) if model.nodes else 3
    centroids = np.zeros((model.num_elements, spatial_dim), dtype=float)
    for index, element in enumerate(model.elements):
        coords = np.asarray(model.node_coords(element.node_ids), dtype=float)
        centroids[index] = coords.mean(axis=0)
    return centroids


def build_density_filter(
    model,
    radius: float,
    *,
    volumes: np.ndarray | None = None,
) -> tuple[sp.csr_matrix, np.ndarray]:
    """Build the Sigmund density filter ``W`` and row sums ``S``.

    ``W_ij = max(0, r_min - ||c_i - c_j||) * V_j`` with element centroids ``c``
    and physical volumes ``V``.  Filtered densities follow
    ``rho_tilde = (W @ rho) / S``.
    """
    radius = float(radius)
    if radius <= 0.0:
        raise OptimizationError("filter radius must be positive")
    if model.num_elements == 0:
        raise OptimizationError("model has no elements for density filtering")
    vols = np.asarray(volumes if volumes is not None else element_volumes(model), dtype=float)
    if vols.size != model.num_elements:
        raise OptimizationError(
            f"expected {model.num_elements} element volumes, got {vols.size}"
        )
    centroids = element_centroids(model)
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    for index_i, center_i in enumerate(centroids):
        for index_j, center_j in enumerate(centroids):
            distance = float(np.linalg.norm(center_i - center_j))
            weight = max(0.0, radius - distance)
            if weight <= 0.0:
                continue
            rows.append(index_i)
            cols.append(index_j)
            data.append(weight * float(vols[index_j]))
    matrix = sp.coo_matrix(
        (data, (rows, cols)), shape=(model.num_elements, model.num_elements)
    ).tocsr()
    row_sums = np.asarray(matrix.sum(axis=1)).reshape(-1)
    if np.any(row_sums <= 0.0):
        raise OptimizationError("density filter produced a zero row sum; increase filter radius")
    return matrix, row_sums


def apply_density_filter(
    densities: np.ndarray,
    filter_matrix: sp.csr_matrix,
    row_sums: np.ndarray,
) -> np.ndarray:
    """Apply the Sigmund density filter to physical element densities."""
    rho = np.asarray(densities, dtype=float).reshape(-1)
    filtered = filter_matrix @ rho
    return np.asarray(filtered / row_sums, dtype=float).reshape(-1)


def filter_sensitivities(
    sensitivities: np.ndarray,
    filter_matrix: sp.csr_matrix,
    row_sums: np.ndarray,
) -> np.ndarray:
    """Chain-rule map of filtered sensitivities back to physical densities."""
    dc = np.asarray(sensitivities, dtype=float).reshape(-1)
    mapped = filter_matrix.T @ (dc / row_sums)
    return np.asarray(mapped, dtype=float).reshape(-1)


def heaviside_projection(
    densities: np.ndarray,
    *,
    beta: float,
    eta: float = 0.5,
) -> np.ndarray:
    """Sigmund Heaviside projection for sharper 0/1 material layouts."""
    rho = np.clip(np.asarray(densities, dtype=float).reshape(-1), 0.0, 1.0)
    beta = float(beta)
    eta = float(eta)
    if beta <= 0.0:
        raise OptimizationError("Heaviside beta must be positive")
    numerator = np.tanh(beta * eta) + np.tanh(beta * (rho - eta))
    denominator = np.tanh(beta * eta) + np.tanh(beta * (1.0 - eta))
    return np.asarray(numerator / denominator, dtype=float)


def heaviside_projection_derivative(
    densities: np.ndarray,
    *,
    beta: float,
    eta: float = 0.5,
) -> np.ndarray:
    """Element-wise ``d rho_bar / d rho_tilde`` for the Heaviside projection."""
    rho = np.clip(np.asarray(densities, dtype=float).reshape(-1), 0.0, 1.0)
    beta = float(beta)
    eta = float(eta)
    if beta <= 0.0:
        raise OptimizationError("Heaviside beta must be positive")
    denominator = np.tanh(beta * eta) + np.tanh(beta * (1.0 - eta))
    return np.asarray(
        beta * (1.0 - np.tanh(beta * (rho - eta)) ** 2) / denominator,
        dtype=float,
    )


def effective_heaviside_beta(
    iteration: int,
    max_iter: int,
    *,
    beta_max: float,
    beta_min: float = 1.0,
    continuation: bool = True,
) -> float:
    """Continuation schedule ramping Heaviside sharpness across iterations."""
    beta_max = float(beta_max)
    beta_min = float(beta_min)
    if beta_max <= 0.0 or beta_min <= 0.0:
        raise OptimizationError("Heaviside beta values must be positive")
    if not continuation or max_iter <= 1:
        return beta_max
    progress = float(iteration) / float(max_iter - 1)
    return float(beta_min * (beta_max / beta_min) ** progress)


def _design_densities(
    rho: np.ndarray,
    *,
    filter_matrix: sp.csr_matrix | None,
    row_sums: np.ndarray | None,
    heaviside_beta: float | None,
    heaviside_eta: float,
    iteration: int,
    max_iter: int,
    heaviside_continuation: bool,
    heaviside_beta_min: float,
) -> tuple[np.ndarray, np.ndarray | None]:
    """Map physical densities to filtered/projected design variables."""
    rho_filtered = (
        apply_density_filter(rho, filter_matrix, row_sums)
        if filter_matrix is not None and row_sums is not None
        else rho
    )
    if heaviside_beta is None:
        return rho_filtered, None
    beta = effective_heaviside_beta(
        iteration,
        max_iter,
        beta_max=heaviside_beta,
        beta_min=heaviside_beta_min,
        continuation=heaviside_continuation,
    )
    rho_design = heaviside_projection(rho_filtered, beta=beta, eta=heaviside_eta)
    projection_deriv = heaviside_projection_derivative(
        rho_filtered, beta=beta, eta=heaviside_eta
    )
    return rho_design, projection_deriv


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
    sensitivity: np.ndarray | None = None,
    design_densities: np.ndarray | None = None,
) -> np.ndarray:
    """Classic optimality-criteria density update with move limit."""
    rho = np.asarray(densities, dtype=float).reshape(-1)
    if sensitivity is not None:
        dc = np.asarray(sensitivity, dtype=float).reshape(-1)
    else:
        design = (
            np.asarray(design_densities, dtype=float).reshape(-1)
            if design_densities is not None
            else rho
        )
        dc = -float(penalization) * np.power(
            np.maximum(design, 1e-3), penalization - 1.0
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
    projected_densities: np.ndarray | None = None
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
    filter_radius: float | None = None,
    heaviside_beta: float | None = None,
    heaviside_eta: float = 0.5,
    heaviside_continuation: bool = True,
    heaviside_beta_min: float = 1.0,
) -> TopologyResult:
    """Minimize compliance with a SIMP penalization and OC updates."""
    if not 0.0 < vol_frac <= 1.0:
        raise OptimizationError("vol_frac must lie in (0, 1]")
    if model.load_vector().sum() == 0.0:
        raise OptimizationError("topology optimization requires non-zero nodal loads")
    if heaviside_beta is not None and filter_radius is None:
        raise OptimizationError(
            "Heaviside projection requires a density filter; set filter_radius"
        )
    volumes = element_volumes(model)
    filter_matrix: sp.csr_matrix | None = None
    row_sums: np.ndarray | None = None
    if filter_radius is not None:
        filter_matrix, row_sums = build_density_filter(model, filter_radius, volumes=volumes)
    rho = np.full(model.num_elements, float(vol_frac), dtype=float)
    history_c: list[float] = []
    history_v: list[float] = []
    last_u: np.ndarray | None = None

    def _finish(iteration: int) -> TopologyResult:
        rho_design, _ = _design_densities(
            rho,
            filter_matrix=filter_matrix,
            row_sums=row_sums,
            heaviside_beta=heaviside_beta,
            heaviside_eta=heaviside_eta,
            iteration=iteration,
            max_iter=max_iter,
            heaviside_continuation=heaviside_continuation,
            heaviside_beta_min=heaviside_beta_min,
        )
        return TopologyResult(
            densities=rho,
            compliance_history=history_c,
            volume_history=history_v,
            displacements=last_u,
            projected_densities=rho_design,
            iterations=iteration + 1,
            meta={
                "penalization": penalization,
                "vol_frac": vol_frac,
                "filter_radius": filter_radius,
                "heaviside_beta": heaviside_beta,
                "heaviside_eta": heaviside_eta,
                "heaviside_continuation": heaviside_continuation,
            },
        )

    for iteration in range(max_iter):
        rho_design, projection_deriv = _design_densities(
            rho,
            filter_matrix=filter_matrix,
            row_sums=row_sums,
            heaviside_beta=heaviside_beta,
            heaviside_eta=heaviside_eta,
            iteration=iteration,
            max_iter=max_iter,
            heaviside_continuation=heaviside_continuation,
            heaviside_beta_min=heaviside_beta_min,
        )
        k = assemble_simp_stiffness(
            model, rho_design, penalization=penalization, e_min=e_min
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
            model, u, rho_design, penalization=penalization, e_min=e_min
        )
        compliance = float(f_f @ u_f)
        volume = float((rho * volumes).sum() / (volumes.sum() or 1.0))
        history_c.append(compliance)
        history_v.append(volume)
        dc_design = -float(penalization) * np.power(
            np.maximum(rho_design, 1e-3), penalization - 1.0
        ) * np.maximum(energies, 0.0)
        if projection_deriv is not None:
            dc_design = dc_design * projection_deriv
        dc = (
            filter_sensitivities(dc_design, filter_matrix, row_sums)
            if filter_matrix is not None and row_sums is not None
            else dc_design
        )
        rho_new = oc_update(
            rho,
            energies,
            volumes,
            vol_frac=vol_frac,
            move=move,
            penalization=penalization,
            e_min=e_min,
            sensitivity=dc,
        )
        change = float(np.max(np.abs(rho_new - rho)))
        rho = rho_new
        if iteration > 5 and change < tol:
            return _finish(iteration)
    result = _finish(max_iter - 1)
    return result
