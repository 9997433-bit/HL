"""Round 17: topology export, multi-load SIMP, and CI-friendly workflow."""

from __future__ import annotations

from pathlib import Path

from openfemlab.cli.spec import build_load_cases, build_model, load_spec
from openfemlab.io import write_data
from openfemlab.io.topology_export import write_topology_vtu
from openfemlab.optimization.topology import run_simp_topology


def main() -> None:
    spec_path = Path(__file__).resolve().parent / "specs" / "topopt_plate_multi_load.yaml"
    spec = load_spec(spec_path)
    model = build_model(spec)
    load_cases = build_load_cases(spec, model)
    assert load_cases is not None
    vectors, weights = load_cases
    result = run_simp_topology(
        model,
        vol_frac=0.5,
        max_iter=25,
        move=0.2,
        tol=1e-2,
        filter_radius=0.75,
        load_vectors=vectors,
        load_weights=weights,
    )
    report = {
        "kind": "topology",
        "source": str(spec_path),
        "summary": {
            "iterations": result.iterations,
            "mean_density": result.mean_density,
            "num_load_cases": len(vectors),
        },
        "densities": [
            {"element": index, "density": float(value)}
            for index, value in enumerate(result.densities)
        ],
    }
    json_path = Path("example14_topology_report.json")
    vtu_path = Path("example14_topology_density.vtu")
    write_data(report, json_path)
    write_topology_vtu(
        model,
        result.densities,
        vtu_path,
        use_projected=result.projected_densities,
    )
    print(f"multi-load topology finished in {result.iterations} iterations")
    print(f"report -> {json_path.resolve()}")
    print(f"density VTU -> {vtu_path.resolve()}")


if __name__ == "__main__":
    main()
