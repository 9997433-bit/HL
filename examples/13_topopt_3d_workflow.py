"""Round 16: 3D SIMP topology with density filter and Heaviside projection."""

from __future__ import annotations

from pathlib import Path

from openfemlab.core.model import DOF, Material
from openfemlab.mesh.simple import tet_block_mesh
from openfemlab.optimization.topology import run_simp_topology


def main() -> None:
    steel = Material(E=2.1e11, density=0.0, nu=0.3)
    model = tet_block_mesh(
        1.0,
        0.5,
        0.5,
        2,
        1,
        1,
        steel,
        support="cantilever",
        name="topopt demo",
    )
    tip = max(model.nodes, key=lambda node: node.coords[0])
    model.add_nodal_load(tip.id, -500.0, dof=DOF.UY)

    result = run_simp_topology(
        model,
        vol_frac=0.4,
        max_iter=30,
        move=0.2,
        tol=1e-2,
        filter_radius=0.35,
        heaviside_beta=32.0,
        heaviside_eta=0.5,
    )
    projected = result.projected_densities
    assert projected is not None
    print(f"SIMP topology finished in {result.iterations} iterations")
    print(f"mean physical density = {result.mean_density:.3f}")
    print(f"mean projected density = {float(projected.mean()):.3f}")
    print(f"final compliance = {result.compliance_history[-1]:.3e}")

    spec = Path(__file__).resolve().parent / "specs" / "topopt_tet_cantilever.yaml"
    print(f"CLI equivalent: openfemlab topopt {spec} --filter-radius 0.35 --heaviside-beta 32")


if __name__ == "__main__":
    main()
