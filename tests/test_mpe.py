"""Unit tests for the M9 modal-parameter-extraction package (MS-10).

The acceptance gates live in ``tests/acceptance/test_mpe.py``; these are the
surface, validation and serialization checks that sit below them — the public
API of MS-10.6, the argument validation each entry point owes its caller, and
the parts of :class:`~openfemlab.mpe.StabilizationDiagram` a notebook depends
on when it renders a diagram without refitting.
"""

from __future__ import annotations

import numpy as np
import pytest

import openfemlab.mpe as mpe
from openfemlab.core.dofs import DofMap, DofType
from openfemlab.exceptions import MPEError, OpenFEMLabError
from openfemlab.solver.dynamics import FrequencyResponse, modal_frf

#: A two-mode oracle small enough to fit in a unit test.
FREQUENCIES = (3.0, 7.0)
RATIOS = (0.02, 0.015)
SHAPES = np.array([[1.0, 1.0], [1.5, -0.8], [0.6, 0.9]])


def _response(*, references=(0,), response_type="receptance") -> FrequencyResponse:
    line = np.linspace(0.05, 30.0, 200)
    frf = modal_frf(
        line,
        (2.0 * np.pi * np.array(FREQUENCIES), SHAPES),
        np.array(RATIOS),
        response_dofs=[0, 1, 2],
        excitation_dofs=list(references),
    )
    return frf if response_type == "receptance" else frf.converted(response_type)


def test_package_exposes_the_ms_10_6_surface() -> None:
    for name in (
        "MPEResult",
        "PoleEstimate",
        "StabilizationDiagram",
        "extract_modes",
        "extract_shapes",
        "fit_lscf",
        "stabilization_diagram",
    ):
        assert hasattr(mpe, name), name
        assert name in mpe.__all__


def test_mpe_error_is_a_typed_openfemlab_failure() -> None:
    assert issubclass(MPEError, OpenFEMLabError)


def test_the_fitter_recovers_a_two_mode_oracle() -> None:
    poles = mpe.fit_lscf(_response(), 6, band=(1.0, 12.0))
    assert [round(pole.frequency_hz, 6) for pole in poles] == list(FREQUENCIES)
    assert [round(pole.damping_ratio, 6) for pole in poles] == list(RATIOS)
    assert all(pole.order == 6 and pole.label == "new" for pole in poles)


def test_inverse_weighting_reaches_the_same_poles_as_unity() -> None:
    """The weighting rescales the residual, it does not change the oracle."""
    band = (1.0, 12.0)
    unity = mpe.fit_lscf(_response(), 6, band=band, weighting="unity")
    inverse = mpe.fit_lscf(_response(), 6, band=band, weighting="inverse")
    assert [pole.frequency_hz for pole in inverse] == pytest.approx(
        [pole.frequency_hz for pole in unity], rel=1e-6
    )


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: mpe.fit_lscf(None, 6), "an FRF is required"),
        (lambda: mpe.fit_lscf(_response(response_type="mobility"), 6), "receptance"),
        (lambda: mpe.fit_lscf(_response(), 0), "model order"),
        (lambda: mpe.fit_lscf(_response(), 6, band=(90.0, 99.0)), "none of the"),
        (lambda: mpe.fit_lscf(_response(), 6, band=(9.0, 1.0)), "not an interval"),
        (lambda: mpe.fit_lscf(_response(), 6, weighting="hann"), "unknown weighting"),
        (lambda: mpe.stabilization_diagram(_response(), ()), "at least one model order"),
        (lambda: mpe.stabilization_diagram(_response(), (6, 4)), "strictly increasing"),
        (lambda: mpe.extract_shapes(_response(), ()), "at least one pole"),
        (lambda: mpe.extract_modes(_response(), (4, 6), spam=1), "unknown tolerance"),
    ],
)
def test_validation_failures_are_typed(call, message) -> None:
    with pytest.raises(MPEError, match=message):
        call()


def test_the_lower_residual_refuses_a_band_containing_dc() -> None:
    frf = _response()
    with_dc = FrequencyResponse(
        np.concatenate(([0.0], frf.frequencies)),
        np.concatenate((frf.data[:1], frf.data)),
        frf.response_dofs,
        frf.excitation_dofs,
    )
    poles = mpe.fit_lscf(with_dc, 6, band=(1.0, 12.0))
    with pytest.raises(MPEError, match="singular at 0 Hz"):
        mpe.extract_shapes(with_dc, poles, band=(0.0, 12.0))
    assert mpe.extract_shapes(with_dc, poles, band=(0.0, 12.0), residuals="upper")


def test_the_diagram_records_its_settings_for_a_later_render() -> None:
    diagram = mpe.stabilization_diagram(_response(), range(4, 9), band=(1.0, 12.0))
    assert diagram.orders == (4, 5, 6, 7, 8)
    assert len(diagram.poles) == 5
    assert diagram.settings["schema"] == "openfemlab.mpe.stabilization/1"
    assert diagram.settings["tolerances"] == {
        "freq_tol": 0.01,
        "damp_tol": 0.05,
        "mac_tol": 0.95,
    }
    assert all(label in ("new", "freq", "damp", "stable")
               for level in diagram.poles for label in (pole.label for pole in level))
    assert diagram.select(min_count=2)


def test_select_rejects_a_nonsensical_minimum_count() -> None:
    diagram = mpe.stabilization_diagram(_response(), range(4, 9), band=(1.0, 12.0))
    with pytest.raises(MPEError, match="min_count"):
        diagram.select(min_count=0)


def test_to_test_data_checks_the_dof_map_against_the_channels() -> None:
    result = mpe.extract_modes(_response(), range(4, 9), band=(1.0, 12.0), min_count=2)
    assert result.num_modes == 2

    with pytest.raises(MPEError, match="DofMap"):
        result.to_test_data(None)
    with pytest.raises(MPEError, match="DofMap"):
        result.to_test_data(DofMap([0], [int(DofType.UX)]))

    test_data = result.to_test_data(DofMap([0, 1, 2], [int(DofType.UX)] * 3))
    assert test_data.shapes.shape == (3, 2)
    assert test_data.damping == pytest.approx(RATIOS, rel=1e-2)
    assert test_data.meta["source"] == "openfemlab.mpe"
