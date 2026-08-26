"""Smoke tests for the spec-first M9 placeholder package (MS-10, GAP-06).

These are scaffold guards, not acceptance gates: no test here carries a
``@criterion`` tag, because every AC-MPE row is ``specified``. They pin the
two things the spec-first landing does promise — the package imports with the
MS-10.6 surface, and every placeholder refuses to run with a
``NotImplementedError`` naming its spec anchor instead of returning junk.
"""

from __future__ import annotations

import numpy as np
import pytest

import openfemlab.mpe as mpe
from openfemlab.exceptions import MPEError, OpenFEMLabError


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


@pytest.mark.parametrize(
    ("call", "anchor"),
    [
        (lambda: mpe.fit_lscf(None, 8), "MS-10.2"),
        (lambda: mpe.stabilization_diagram(None, range(2, 12)), "MS-10.3"),
        (lambda: mpe.extract_shapes(None, ()), "MS-10.4"),
        (lambda: mpe.extract_modes(None, range(2, 12)), "MS-10.6"),
    ],
)
def test_placeholders_raise_not_implemented_naming_their_anchor(call, anchor) -> None:
    with pytest.raises(NotImplementedError, match=anchor):
        call()


def test_result_types_construct_but_their_bridges_refuse_to_run() -> None:
    pole = mpe.PoleEstimate(
        frequency_hz=12.5, damping_ratio=0.01, pole=-0.785 + 78.5j, order=8
    )
    diagram = mpe.StabilizationDiagram(orders=(8,), poles=((pole,),))
    with pytest.raises(NotImplementedError, match="MS-10.3"):
        diagram.select()

    result = mpe.MPEResult(
        frequencies_hz=np.array([12.5]),
        damping_ratios=np.array([0.01]),
        poles=np.array([-0.785 + 78.5j]),
        shapes=np.ones((3, 1), dtype=complex),
        participation=np.ones((1, 1), dtype=complex),
        frac=np.ones(3),
    )
    with pytest.raises(NotImplementedError, match="MS-10.5"):
        result.to_test_data(None)
