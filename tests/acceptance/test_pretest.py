"""M10 pretest planning acceptance suite (``docs/ACCEPTANCE_CRITERIA.md`` section 11).

Gates the Effective Independence sensor-placement contract of
``docs/MODULE_SPEC.md`` MS-11 on the ten-DOF chain twin and the layouts the
AC-CORR-009 suite already pins.
"""

from __future__ import annotations

import itertools
from math import comb

import numpy as np
import pytest

from openfemlab.exceptions import PretestError
from openfemlab.pretest import (
    ei_leverage,
    modal_kinetic_energy,
    placement_quality,
    select_sensors,
    to_sensor_map,
)
from openfemlab.solver import ModalSolver

from ._support import criterion, fixture_matrices, load_fixture

REL_DET = 1e-12
LEVERAGE_SUM_TOL = 1e-10
LEVERAGE_UNIT_TOL = 1e-12

# AC-CORR-009 chain twin layouts (four target modes, five channels).
SPREAD_LAYOUT = (1, 3, 5, 7, 9)
ADVERSARIAL_LAYOUT = (0, 2, 5, 7, 9)
CONTIGUOUS_LAYOUT = (0, 1, 2, 3, 4)

# Pinned (m, s) cases for exhaustive det-FIM agreement on the 10-DOF chain.
PINNED_CASES = (
    (3, 3),
    (3, 4),
    (3, 5),
    (4, 5),
    (5, 5),
    (5, 6),
    (5, 7),
)


def _chain_modes(num_modes: int) -> np.ndarray:
    stiffness, mass = fixture_matrices(load_fixture("ten_dof_chain"))
    result = ModalSolver.from_matrices(stiffness, mass).solve(
        num_modes=num_modes,
        sparse=False,
    )
    return np.asarray(result.mode_shapes[:, :num_modes], dtype=float)


def _exhaustive_det_argmax(shapes: np.ndarray, num_sensors: int) -> tuple[int, ...]:
    n_rows = shapes.shape[0]
    best_det = -np.inf
    best_subset: tuple[int, ...] | None = None
    for subset in itertools.combinations(range(n_rows), num_sensors):
        gram = shapes[list(subset), :].T @ shapes[list(subset), :]
        det = float(np.linalg.det(gram))
        if det > best_det + 1e-15:
            best_det = det
            best_subset = subset
        elif abs(det - best_det) <= 1e-15 and best_subset is not None:
            # Deterministic tie-break: prefer ascending tuple (stable oracle).
            if tuple(subset) < best_subset:
                best_subset = subset
    assert best_subset is not None
    return tuple(sorted(best_subset))


def _run_backward_elimination_trace(
    shapes: np.ndarray,
    num_sensors: int,
) -> list[dict[str, object]]:
    active = list(range(shapes.shape[0]))
    trace: list[dict[str, object]] = []
    while len(active) > num_sensors:
        phi = shapes[active, :]
        leverages = ei_leverage(phi)
        minimum = float(np.min(leverages))
        tied_indices = [
            index for index, value in enumerate(leverages) if value <= minimum + 1e-12
        ]
        remove_index = max(tied_indices)
        e_d = float(leverages[remove_index])
        det_before = float(np.linalg.det(phi.T @ phi))
        trace.append(
            {
                "leverages": leverages.copy(),
                "sum_leverage": float(np.sum(leverages)),
                "removed": active[remove_index],
                "e_d": e_d,
                "det_before": det_before,
            }
        )
        active.pop(remove_index)
        det_after = float(np.linalg.det(shapes[active, :].T @ shapes[active, :]))
        np.testing.assert_allclose(det_after, (1.0 - e_d) * det_before, rtol=REL_DET)
        trace[-1]["det_after"] = det_after
    return trace


# ---------------------------------------------------------------- AC-PRETEST-001


@criterion("AC-PRETEST-001")
def test_ac_pretest_001_leverage_conservation_and_det_downdate_on_chain():
    shapes = _chain_modes(4)
    trace = _run_backward_elimination_trace(shapes, num_sensors=5)
    for step in trace:
        leverages = step["leverages"]
        assert np.all(leverages >= -1e-12)
        assert np.all(leverages <= 1.0 + 1e-12)
        np.testing.assert_allclose(float(np.sum(leverages)), 4.0, atol=LEVERAGE_SUM_TOL)


@criterion("AC-PRETEST-001")
def test_ac_pretest_001_full_orthonormal_basis_has_unit_leverage():
    identity = np.eye(8)
    leverages = ei_leverage(identity)
    np.testing.assert_allclose(leverages, 1.0, atol=LEVERAGE_UNIT_TOL)


# ---------------------------------------------------------------- AC-PRETEST-002


@criterion("AC-PRETEST-002")
@pytest.mark.parametrize(("num_modes", "num_sensors"), PINNED_CASES)
def test_ac_pretest_002_ei_matches_exhaustive_det_optimum(num_modes, num_sensors):
    shapes = _chain_modes(num_modes)
    expected = _exhaustive_det_argmax(shapes, num_sensors)
    selected = select_sensors(shapes, num_sensors).selected
    assert selected == expected
    gram = shapes[list(selected), :].T @ shapes[list(selected), :]
    oracle = shapes[list(expected), :].T @ shapes[list(expected), :]
    np.testing.assert_allclose(np.linalg.det(gram), np.linalg.det(oracle), rtol=0.0, atol=0.0)


# ---------------------------------------------------------------- AC-PRETEST-003


@criterion("AC-PRETEST-003")
def test_ac_pretest_003_quality_metrics_rank_spread_above_adversarial():
    shapes = _chain_modes(4)
    spread = placement_quality(shapes, SPREAD_LAYOUT)
    adversarial = placement_quality(shapes, ADVERSARIAL_LAYOUT)
    assert spread.det_fim > adversarial.det_fim
    assert spread.condition < adversarial.condition
    assert spread.min_singular_value > adversarial.min_singular_value
    assert spread.automac_off_diagonal < adversarial.automac_off_diagonal
    np.testing.assert_allclose(spread.det_fim, 0.091, rtol=0.05)
    np.testing.assert_allclose(adversarial.det_fim, 0.045, rtol=0.05)


@criterion("AC-PRETEST-003")
def test_ac_pretest_003_ei_det_dominates_both_layouts_and_contiguous_aliases():
    shapes = _chain_modes(4)
    ei = select_sensors(shapes, 5)
    spread = placement_quality(shapes, SPREAD_LAYOUT)
    adversarial = placement_quality(shapes, ADVERSARIAL_LAYOUT)
    contiguous = placement_quality(shapes, CONTIGUOUS_LAYOUT)
    assert ei.det_fim >= spread.det_fim
    assert ei.det_fim >= adversarial.det_fim
    assert contiguous.automac_off_diagonal >= 0.9
    assert ei.quality.automac_off_diagonal <= 0.10


# ---------------------------------------------------------------- AC-PRETEST-004


@criterion("AC-PRETEST-004")
def test_ac_pretest_004_typed_failures_and_keep_constraints():
    shapes = _chain_modes(4)
    with pytest.raises(PretestError):
        select_sensors(shapes, 3)
    rank_deficient = np.vstack([shapes[:, 0], shapes[:, 0]])
    with pytest.raises(PretestError):
        ei_leverage(rank_deficient)
    kept = select_sensors(shapes, 5, keep=(1, 3))
    assert 1 in kept.selected and 3 in kept.selected
    assert 1 not in kept.eliminated and 3 not in kept.eliminated
    restricted = select_sensors(shapes, 4, candidates=(2, 4, 6, 8))
    assert set(restricted.selected) <= {2, 4, 6, 8}


@criterion("AC-PRETEST-004")
def test_ac_pretest_004_reruns_are_bitwise_identical():
    shapes = _chain_modes(4)
    first = select_sensors(shapes, 5, keep=(2,))
    second = select_sensors(shapes, 5, keep=(2,))
    assert first.selected == second.selected
    assert first.eliminated == second.eliminated
    np.testing.assert_array_equal(first.leverage, second.leverage)
    np.testing.assert_array_equal(first.det_history, second.det_history)


@criterion("AC-PRETEST-004")
def test_ac_pretest_004_to_sensor_map_preserves_selected_rows():
    placement = select_sensors(_chain_modes(4), 5)
    labels = tuple(f"ch{index}" for index in placement.selected)
    sensor_map = to_sensor_map(placement, labels=labels)
    assert sensor_map.rows == placement.selected
    assert sensor_map.labels == labels


# ---------------------------------------------------------------- AC-PRETEST-005


@criterion("AC-PRETEST-005")
def test_ac_pretest_005_mode_one_mke_increases_toward_the_free_end():
    shapes = _chain_modes(1)
    _, mass = fixture_matrices(load_fixture("ten_dof_chain"))
    mke = modal_kinetic_energy(shapes, np.diag(mass))
    column = mke[:, 0]
    assert np.all(np.diff(column) > 0.0)
    assert int(np.argmax(column)) == shapes.shape[0] - 1


@criterion("AC-PRETEST-005")
def test_ac_pretest_005_uniform_mass_scaling_is_selection_invariant():
    shapes = _chain_modes(4)
    baseline = select_sensors(shapes, 5)
    scaled = select_sensors(shapes, 5, mass=3.5 * np.ones(shapes.shape[0]))
    assert baseline.selected == scaled.selected


# ---------------------------------------------------------------- AC-PRETEST-006


@criterion("AC-PRETEST-006")
def test_ac_pretest_006_accelerometer_mass_lowers_the_predicted_frequency() -> None:
    from openfemlab.pretest.mass_loading import accelerometer_frequency_shift

    shapes = _chain_modes(1)
    _, mass = fixture_matrices(load_fixture("ten_dof_chain"))
    modal_mass = float(shapes[:, 0].T @ mass @ shapes[:, 0])
    base_frequency = 4.0
    shifted = accelerometer_frequency_shift(
        [base_frequency],
        shapes,
        dof_index=shapes.shape[0] - 1,
        modal_masses=[modal_mass],
        accelerometer_mass=0.05,
    )
    assert shifted[0] < base_frequency


# ---------------------------------------------------------------- helpers


def test_exhaustive_search_covers_expected_combination_counts():
    assert comb(10, 5) == 252
    assert comb(10, 7) == 120
