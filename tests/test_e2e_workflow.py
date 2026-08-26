"""End-to-end model validation and updating workflow."""

from __future__ import annotations

from collections.abc import Mapping

from openfemlab import ModalSolver
from openfemlab.correlation import correlation_summary
from openfemlab.mesh.simple import spring_mass_chain
from openfemlab.updating import UpdatableParameter, update_model


def test_model_modal_correlation_update_and_resolve() -> None:
    """A biased FE model is updated back to synthetic measured modes."""

    n_modes = 4
    nominal_stiffness = 2400.0
    target_scale = 1.21

    def solve(scale: float):
        model = spring_mass_chain(
            num_masses=n_modes,
            stiffness=nominal_stiffness * scale,
            mass=1.8,
        )
        return ModalSolver(model).solve(num_modes=n_modes)

    target = solve(target_scale)
    initial = solve(0.72)
    initial_correlation = correlation_summary(
        test_frequencies=target.frequencies,
        fe_frequencies=initial.frequencies,
        test_shapes=target.mode_shapes,
        fe_shapes=initial.mode_shapes,
    )
    assert initial_correlation.max_abs_freq_error_pct > 10.0

    def solve_parameters(parameters: Mapping[str, float]):
        return solve(parameters["stiffness_scale"])

    updating = update_model(
        solve_parameters,
        [
            UpdatableParameter(
                "stiffness_scale",
                value=0.72,
                lower=0.5,
                upper=1.5,
                step=1.0e-4,
            )
        ],
        target.frequencies,
        target.mode_shapes,
        max_iterations=15,
        shape_weight=0.25,
        parameter_tolerance=1.0e-10,
    )

    updated = solve(updating.parameters["stiffness_scale"])
    final_correlation = correlation_summary(
        test_frequencies=target.frequencies,
        fe_frequencies=updated.frequencies,
        test_shapes=target.mode_shapes,
        fe_shapes=updated.mode_shapes,
    )

    assert final_correlation.n_paired == n_modes
    assert final_correlation.max_abs_freq_error_pct < 1.0
    assert final_correlation.min_mac > 0.95
