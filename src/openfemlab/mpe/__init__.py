"""Experimental modal parameter extraction — module M9, spec MS-10 (GAP-06).

**Spec-first placeholder package.** The MS-10 section of
``docs/MODULE_SPEC.md`` and the AC-MPE-001..005 rows of
``docs/ACCEPTANCE_CRITERIA.md`` are binding specification; nothing here is
implemented. Every callable raises :class:`NotImplementedError` naming its
spec anchor, and the result dataclasses exist so downstream signatures can
already be typed against them. Do not treat importability as capability:
every M9 acceptance row is ``specified``, none is implemented or verified.

Planned surface (MS-10.6): the LSCF / poly-reference curve fitter
(:func:`fit_lscf`), the stabilization diagram over model orders
(:func:`stabilization_diagram`), LSFD residue/shape estimation
(:func:`extract_shapes`), the one-call driver (:func:`extract_modes`), and
the ``MPEResult.to_test_data`` bridge into the M2 correlation input.
"""

from __future__ import annotations

from .lscf import extract_modes, extract_shapes, fit_lscf, stabilization_diagram
from .types import MPEResult, PoleEstimate, StabilizationDiagram

__all__ = [
    "MPEResult",
    "PoleEstimate",
    "StabilizationDiagram",
    "extract_modes",
    "extract_shapes",
    "fit_lscf",
    "stabilization_diagram",
]
