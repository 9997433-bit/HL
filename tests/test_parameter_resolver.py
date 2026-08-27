"""Resolution of dotted parameter targets against a solver model.

The resolver's contract is that the parameterisation it builds is *the same
model*: at the nominal scaling factors the scaling model must reproduce the
modes of a direct solve, and every declared factor must move the matrices the
way the physics says it does.
"""

from __future__ import annotations

import numpy as np
import pytest

from openfemlab.core.elements import TrussElement
from openfemlab.core.model import DOF, Material, Model, Section
from openfemlab.mesh.simple import beam_mesh, quad_plate_mesh, shell_plate_mesh
from openfemlab.solver.modal import ModalSolver
from openfemlab.updating import Parameter, ParameterType, ScalingModel, update_model
from openfemlab.updating.resolver import (
    NonAffineTargetError,
    TargetError,
    parameters_from_mapping,
    parse_target,
    resolve_parameters,
    resolve_scaling_spec,
    scaling_model_from_spec,
)

STEEL = Material(E=2.1e11, density=7850.0, name="steel")
STRIP = Section(area=1.0e-4, inertia_z=8.333e-10, name="strip")


@pytest.fixture
def beam() -> Model:
    """Cantilever with a named material and a named section."""
    return beam_mesh(1.0, 8, STEEL, STRIP, support="cantilever")


def young_modulus(name: str = "E.steel", **overrides) -> Parameter:
    settings = {"reference": STEEL.E, "lower": 0.5, "upper": 2.0}
    settings.update(overrides)
    return Parameter(name, "materials.steel.E", **settings)


def direct_frequencies(model: Model, num_modes: int) -> np.ndarray:
    return ModalSolver(system=model.assemble()).solve(num_modes=num_modes).frequencies


# ---------------------------------------------------------------- target parsing


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("materials.steel.E", ("materials", "steel", "E")),
        ("material.steel.young", ("materials", "steel", "E")),
        ("materials.steel.rho", ("materials", "steel", "density")),
        ("sections.strip.A", ("sections", "strip", "area")),
        ("properties.strip.Iz", ("sections", "strip", "inertia_z")),
        ("elements.4.t", ("elements", "4", "thickness")),
        ("elements.*.E", ("elements", "*", "E")),
    ],
)
def test_targets_parse_into_domain_key_attribute(target, expected) -> None:
    parsed = parse_target(target)
    assert (parsed.domain, parsed.key, parsed.attribute) == expected


@pytest.mark.parametrize(
    ("target", "message"),
    [
        ("materials.steel", "must read"),
        ("materials.steel.E.extra", "must read"),
        ("bogus.steel.E", "unknown domain"),
        ("materials.steel.nu", "no updatable attribute"),
        ("sections.strip.thickness", "no updatable attribute"),
    ],
)
def test_malformed_targets_are_rejected(target, message) -> None:
    with pytest.raises(TargetError, match=message):
        parse_target(target)


# ------------------------------------------------------------------- resolution


def test_nominal_factors_reproduce_the_model(beam: Model) -> None:
    spec = resolve_scaling_spec(beam, [young_modulus()], num_modes=4)

    assert spec.initial_values == {"E.steel": pytest.approx(1.0)}
    assert spec.scaling_model.num_dofs == beam.free_dofs.size
    assert spec.scaling_model(spec.initial_values).frequencies == pytest.approx(
        direct_frequencies(beam, 4)
    )


def test_youngs_modulus_scales_stiffness_only(beam: Model) -> None:
    """``f ∝ sqrt(E)``: four times the modulus doubles every frequency."""
    spec = resolve_scaling_spec(beam, [young_modulus()], num_modes=4)
    resolved = spec.resolved[0]

    assert resolved.stiffness_part is not None
    assert resolved.mass_part is None
    assert resolved.kind is ParameterType.STIFFNESS
    assert resolved.element_indices == tuple(range(beam.num_elements))

    nominal = spec.scaling_model({"E.steel": 1.0}).frequencies
    stiffened = spec.scaling_model({"E.steel": 4.0}).frequencies
    assert stiffened == pytest.approx(2.0 * nominal)


def test_density_scales_mass_only(beam: Model) -> None:
    """``f ∝ 1/sqrt(rho)``, and a mass-only factor needs no stiffness part."""
    parameter = Parameter("rho.steel", "materials.steel.density", reference=STEEL.density)
    spec = resolve_scaling_spec(beam, [parameter], num_modes=4)
    resolved = spec.resolved[0]

    assert resolved.stiffness_part is None
    assert resolved.mass_part is not None
    assert resolved.kind is ParameterType.MASS

    nominal = spec.scaling_model({"rho.steel": 1.0}).frequencies
    heavier = spec.scaling_model({"rho.steel": 4.0}).frequencies
    assert heavier == pytest.approx(0.5 * nominal)


def test_beam_area_is_affine_and_touches_both_matrices(beam: Model) -> None:
    """A beam's area scales the axial block and the mass, never the bending."""
    parameter = Parameter("A.strip", "sections.strip.area", reference=STRIP.area)
    spec = resolve_scaling_spec(beam, [parameter], num_modes=4)
    resolved = spec.resolved[0]

    assert resolved.stiffness_part is not None
    assert resolved.mass_part is not None

    # Bending frequencies scale as sqrt(EI / rho A) and I is untouched, so
    # doubling the area alone drops them by sqrt(2) even though K moved too.
    nominal = spec.scaling_model({"A.strip": 1.0}).frequencies
    doubled = spec.scaling_model({"A.strip": 2.0}).frequencies
    assert doubled[1:] == pytest.approx(nominal[1:] / np.sqrt(2.0), rel=1e-9)


def test_quad4_thickness_is_affine() -> None:
    """A membrane's stiffness and mass are both linear in ``t``, so ``f`` is flat."""
    plate = quad_plate_mesh(0.4, 0.3, 2, 2, STEEL, thickness=2.0e-3, support="cantilever")
    parameter = Parameter("t", "elements.*.thickness", reference=2.0e-3)
    spec = resolve_scaling_spec(plate, [parameter], num_modes=3)

    nominal = spec.scaling_model({"t": 1.0}).frequencies
    thicker = spec.scaling_model({"t": 3.0}).frequencies
    assert thicker == pytest.approx(nominal)


def test_shell_thickness_is_rejected_as_non_affine() -> None:
    """Membrane goes with ``t`` and bending with ``t³``; no affine part fits both."""
    plate = shell_plate_mesh(0.4, 0.3, 2, 2, STEEL, thickness=2.0e-3, support="cantilever")
    parameter = Parameter("t", "elements.*.thickness", reference=2.0e-3)

    with pytest.raises(NonAffineTargetError, match="not affine in thickness"):
        resolve_scaling_spec(plate, [parameter])


def test_shell_material_still_resolves() -> None:
    """The facet's nested membrane must be scaled along with the facet itself."""
    plate = shell_plate_mesh(0.4, 0.3, 2, 2, STEEL, thickness=2.0e-3, support="cantilever")
    spec = resolve_scaling_spec(plate, [young_modulus()], num_modes=3)

    assert spec.scaling_model({"E.steel": 1.0}).frequencies == pytest.approx(
        direct_frequencies(plate, 3)
    )
    stiffened = spec.scaling_model({"E.steel": 4.0}).frequencies
    assert stiffened == pytest.approx(2.0 * spec.scaling_model({"E.steel": 1.0}).frequencies)


# -------------------------------------------------------------------- selection


def test_element_ids_split_one_material_into_substructures(beam: Model) -> None:
    parameters = [
        young_modulus("E.root", element_ids=(0, 1, 2, 3)),
        young_modulus("E.tip", element_ids=(4, 5, 6, 7)),
    ]
    resolved = resolve_parameters(beam, parameters)

    assert [item.element_indices for item in resolved] == [(0, 1, 2, 3), (4, 5, 6, 7)]


def test_element_domain_addresses_a_single_element(beam: Model) -> None:
    parameter = Parameter("E.0", "elements.0.E", reference=STEEL.E)
    resolved = resolve_parameters(beam, [parameter])[0]

    assert resolved.element_indices == (0,)
    # Elements share one Material instance; scaling one must not move the rest.
    assert beam.elements[1].material.E == pytest.approx(STEEL.E)


def test_unmatched_targets_name_what_the_model_knows(beam: Model) -> None:
    with pytest.raises(TargetError, match="known materials: steel"):
        resolve_parameters(beam, [Parameter("x", "materials.aluminium.E", reference=7.0e10)])


def test_element_ids_outside_the_target_are_rejected(beam: Model) -> None:
    with pytest.raises(TargetError, match="select none of the elements"):
        resolve_parameters(beam, [young_modulus(element_ids=(99,))])


def test_a_group_with_two_nominal_values_is_ambiguous() -> None:
    model = Model(dofs=(DOF.UX, DOF.UY), name="two-bar")
    model.add_nodes([(1, 0.0, 0.0), (2, 1.0, 0.0), (3, 2.0, 0.0)])
    model.add_element(TrussElement((1, 2), STEEL, Section(area=1.0e-4, name="strip")))
    model.add_element(TrussElement((2, 3), STEEL, Section(area=3.0e-4, name="strip")))

    with pytest.raises(TargetError, match="different area values"):
        resolve_parameters(model, [Parameter("A", "sections.strip.area", reference=1.0e-4)])


def test_two_factors_on_one_element_matrix_are_rejected(beam: Model) -> None:
    parameters = [young_modulus("E.all"), Parameter("E.0", "elements.0.E", reference=STEEL.E)]

    with pytest.raises(TargetError, match="both scale the stiffness"):
        resolve_parameters(beam, parameters)


def test_stiffness_and_mass_factors_may_share_elements(beam: Model) -> None:
    """``E`` and ``density`` act on different matrices, so the overlap is affine."""
    parameters = [
        young_modulus(),
        Parameter("rho.steel", "materials.steel.density", reference=STEEL.density),
    ]
    spec = resolve_scaling_spec(beam, parameters, num_modes=3)

    unchanged = spec.scaling_model({"E.steel": 1.0, "rho.steel": 1.0}).frequencies
    scaled = spec.scaling_model({"E.steel": 4.0, "rho.steel": 4.0}).frequencies
    assert scaled == pytest.approx(unchanged)


def test_duplicate_names_and_empty_specifications_are_rejected(beam: Model) -> None:
    with pytest.raises(TargetError, match="duplicate parameter names"):
        resolve_parameters(beam, [young_modulus(), young_modulus()])
    with pytest.raises(TargetError, match="at least one parameter"):
        resolve_parameters(beam, [])


# ---------------------------------------------------------------- normalisation


def test_theta_is_the_declared_normalisation(beam: Model) -> None:
    """``θ = value / reference``, so a reference below the model's value lifts θ."""
    spec = resolve_scaling_spec(beam, [young_modulus(reference=1.0e11)], num_modes=3)
    resolved = spec.resolved[0]

    assert resolved.nominal_value == pytest.approx(STEEL.E)
    assert resolved.initial_value == pytest.approx(2.1)
    assert spec.scaling_model({"E.steel": 2.1}).frequencies == pytest.approx(
        direct_frequencies(beam, 3)
    )


def test_parameter_set_starts_at_the_nominal_factor(beam: Model) -> None:
    spec = resolve_scaling_spec(beam, [young_modulus(lower=0.25, upper=4.0)], num_modes=3)
    parameters = spec.parameter_set()

    assert parameters.names == ["E.steel"]
    assert parameters["E.steel"].value == pytest.approx(1.0)
    assert parameters["E.steel"].design_bounds == (0.25, 4.0)
    assert parameters["E.steel"].kind is ParameterType.STIFFNESS


# -------------------------------------------------------------------- sensors


def test_sensor_dofs_restrict_the_reported_shapes(beam: Model) -> None:
    sensors = [(2, "UY"), (4, "UY"), (8, "UY")]
    spec = resolve_scaling_spec(beam, [young_modulus()], num_modes=3, sensor_dofs=sensors)

    data = spec.scaling_model({"E.steel": 1.0})
    assert data.mode_shapes.shape == (3, 3)

    rows = [spec.dof_row(beam.dof_index(node, dof)) for node, dof in sensors]
    full = ModalSolver(system=beam.assemble()).solve(num_modes=3).mode_shapes
    expected = full[[beam.dof_index(node, dof) for node, dof in sensors], :]
    assert np.abs(data.mode_shapes) == pytest.approx(np.abs(expected), abs=1e-8)
    assert rows == sorted(rows)


def test_constrained_sensor_dofs_are_rejected(beam: Model) -> None:
    with pytest.raises(TargetError, match="constrained"):
        resolve_scaling_spec(beam, [young_modulus()], sensor_dofs=[(0, "UY")])


# ------------------------------------------------------------------- end to end


def test_scaling_model_from_spec_returns_a_scaling_model(beam: Model) -> None:
    model = scaling_model_from_spec(beam, [young_modulus()], num_modes=3)

    assert isinstance(model, ScalingModel)
    assert model.parameter_names == ["E.steel"]


def test_updating_recovers_a_perturbed_substructure(beam: Model) -> None:
    parameters = [
        young_modulus("E.root", element_ids=(0, 1, 2, 3)),
        young_modulus("E.tip", element_ids=(4, 5, 6, 7)),
    ]
    spec = resolve_scaling_spec(beam, parameters, num_modes=4)
    truth = {"E.root": 1.25, "E.tip": 0.85}
    target = spec.scaling_model(truth)

    result = update_model(
        spec.scaling_model,
        spec.parameter_set(),
        target.frequencies,
        target.mode_shapes,
    )

    assert result.converged
    for name, value in truth.items():
        assert result.parameters[name] == pytest.approx(value, rel=1e-4)


def test_parameters_can_be_declared_as_a_mapping(beam: Model) -> None:
    declarations = parameters_from_mapping(
        {
            "E.steel": {"target": "materials.steel.E", "reference": STEEL.E},
            "rho.steel": {"target": "materials.steel.density", "reference": STEEL.density},
        }
    )
    spec = resolve_scaling_spec(beam, declarations, num_modes=3)

    assert spec.scaling_model.parameter_names == ["E.steel", "rho.steel"]
    assert spec.initial_values == {"E.steel": pytest.approx(1.0), "rho.steel": pytest.approx(1.0)}
