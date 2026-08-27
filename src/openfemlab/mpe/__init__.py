"""Experimental modal parameter extraction — module M9, spec MS-10 (GAP-06).

Every other module of the platform ends at a synthesized FRF; this one runs
the arrow the other way, estimating an experimental modal model from a
measured (or synthesized) receptance matrix and handing it to the M2
correlation input. Together with the M8 dataset-58 reader it closes the raw
measurement → correlation loop GAP-06 named.

Surface (MS-10.6): the LSCF / poly-reference curve fitter (:func:`fit_lscf`),
the stabilization diagram over model orders
(:func:`stabilization_diagram`), LSFD residue/shape estimation
(:func:`extract_shapes`), the one-call driver (:func:`extract_modes`), and
the ``MPEResult.to_test_data`` bridge into the M2 correlation input.  The
output-only :func:`ssi_cov` API is reserved explicitly and currently raises
``NotImplementedError`` until its numerical backend lands.

The estimators are direct solves over the measured lines, so they take no
seed and identical inputs produce bitwise-identical results (MS-10.1). Input
must be receptance in the MS-7.3 ``FrequencyResponse`` contract; mobility and
accelerance are converted by the caller.

    from openfemlab.mpe import extract_modes

    result = extract_modes(frf, range(4, 17, 2), band=(5.0, 120.0))
    test_data = result.to_test_data(sensor_dof_map)
"""

from __future__ import annotations

from .lscf import extract_modes, extract_shapes, fit_lscf, stabilization_diagram
from .ssi import ssi_cov
from .types import MPEResult, PoleEstimate, StabilizationDiagram

__all__ = [
    "MPEResult",
    "PoleEstimate",
    "StabilizationDiagram",
    "extract_modes",
    "extract_shapes",
    "fit_lscf",
    "ssi_cov",
    "stabilization_diagram",
]
