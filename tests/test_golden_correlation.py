"""Golden correlation regression for CI pipelines."""

from __future__ import annotations

import json

import pytest

from openfemlab.cli.analysis import dof_map_of
from openfemlab.cli.spec import build_model
from openfemlab.core.dofs import DofMap, DofType
from openfemlab.core.results import TestData
from openfemlab.correlation.report import correlate_modal_data
from openfemlab.solver.modal import ModalSolver

CANTILEVER = {
    "name": "golden cantilever",
    "materials": {"steel": {"E": 2.1e11, "density": 7850.0, "nu": 0.3}},
    "sections": {"strip": {"area": 1.0e-4, "inertia_z": 8.3333333e-10}},
    "mesh": {
        "type": "beam",
        "length": 1.0,
        "num_elements": 12,
        "support": "cantilever",
        "material": "steel",
        "section": "strip",
    },
}


def test_golden_correlation_report_summary():
    """Pinned MAC summary for a fixed model/test pair (CI regression gate)."""
    model = build_model(CANTILEVER)
    dof_map = dof_map_of(model)
    reference = ModalSolver(model).solve(num_modes=4).with_dof_map(dof_map)
    perturbed = build_model(
        {
            **CANTILEVER,
            "materials": {"steel": {"E": 1.85e11, "density": 7850.0, "nu": 0.3}},
        }
    )
    measured = ModalSolver(perturbed).solve(num_modes=4)
    sensor_nodes = (4, 8, 12)
    rows = [dof_map_of(perturbed).index_of(node, DofType.UY) for node in sensor_nodes]
    test = TestData(
        frequencies=measured.frequencies,
        shapes=measured.mode_shapes[rows, :],
        dof_map=DofMap(sensor_nodes, [int(DofType.UY)] * len(sensor_nodes)),
    )
    report = correlate_modal_data(reference, test)
    payload = json.loads(report.to_json())
    assert payload["summary"]["n_paired"] == 4
    assert payload["summary"]["min_mac"] == pytest.approx(0.999, abs=0.01)
    assert payload["summary"]["mean_mac"] == pytest.approx(1.0, abs=0.01)
    assert payload["summary"]["max_abs_freq_error_pct"] == pytest.approx(6.54, abs=0.2)
    roundtrip = json.loads(json.dumps(payload))
    assert roundtrip["summary"]["min_mac"] == payload["summary"]["min_mac"]
