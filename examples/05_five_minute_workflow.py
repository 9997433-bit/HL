"""Five-minute modal -> correlate -> update workflow on a two-DOF model.

Run from the repository root with::

    PYTHONPATH=src python examples/05_five_minute_workflow.py
"""

from __future__ import annotations

from collections.abc import Mapping

from openfemlab import ModalSolver, UpdatableParameter, correlation_summary, update_model
from openfemlab.mesh.simple import spring_mass_chain

NUM_MODES = 2
NOMINAL_STIFFNESS = 1_000.0
MASS = 1.0
TRUE_STIFFNESS_SCALE = 0.81


def solve(stiffness_scale: float):
    """Solve the tiny spring-mass model at one stiffness scale."""
    model = spring_mass_chain(
        num_masses=NUM_MODES,
        stiffness=NOMINAL_STIFFNESS * stiffness_scale,
        mass=MASS,
    )
    return ModalSolver(model).solve(num_modes=NUM_MODES)


def correlate(fe_modes, measured_modes):
    """Correlate one FE prediction with the synthetic measurement."""
    return correlation_summary(
        test_frequencies=measured_modes.frequencies,
        fe_frequencies=fe_modes.frequencies,
        test_shapes=measured_modes.mode_shapes,
        fe_shapes=fe_modes.mode_shapes,
        method="optimal",
    )


def main() -> None:
    # Treat a softer copy of the model as a small, reproducible modal test.
    measured = solve(TRUE_STIFFNESS_SCALE)
    baseline = solve(1.0)
    before = correlate(baseline, measured)

    frequencies = ", ".join(f"{frequency:.3f}" for frequency in baseline.frequencies)
    print("modal     baseline frequencies [Hz]:", frequencies)
    print(
        f"correlate before update: min MAC={before.min_mac:.4f}, "
        f"max |df|={before.max_abs_freq_error_pct:.3f}%"
    )

    def evaluate(parameters: Mapping[str, float]):
        return solve(parameters["stiffness_scale"])

    result = update_model(
        evaluate,
        [UpdatableParameter("stiffness_scale", lower=0.5, upper=1.5)],
        measured.frequencies,
        measured.mode_shapes,
        max_iterations=15,
        shape_weight=0.25,
        parameter_tolerance=1.0e-10,
    )

    updated_scale = result.parameters["stiffness_scale"]
    after = correlate(solve(updated_scale), measured)
    print(
        f"update    stiffness scale: 1.0000 -> {updated_scale:.4f} "
        f"({result.iterations} iterations)"
    )
    print(
        f"verify    after update: min MAC={after.min_mac:.4f}, "
        f"max |df|={after.max_abs_freq_error_pct:.3f}%"
    )


if __name__ == "__main__":
    main()
