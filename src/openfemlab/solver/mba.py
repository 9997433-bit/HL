"""Modal-Based Assembly (MBA) and FRF-Based Assembly (FBA) — Wave 2 stubs.

FEMtools Dynamics extends SDM with substructure coupling in the modal domain
(MBA) and in the FRF domain (FBA).  Wave 1 lands the specification anchor;
implementation follows in Round 7 Wave 2.
"""

from __future__ import annotations

from ..exceptions import SolverError

__all__ = ["mba_couple", "fba_assemble"]


def mba_couple(*_args, **_kwargs):
    """Couple two modal component models at shared connection DOFs (MS-7.7)."""
    raise SolverError(
        "Modal-Based Assembly (MBA) is specified for Round 7 Wave 2; "
        "use solver.sdm.modified_frequencies_hz for SDM today"
    )


def fba_assemble(*_args, **_kwargs):
    """Assemble component FRFs through connection impedances (MS-7.8)."""
    raise SolverError(
        "FRF-Based Assembly (FBA) is specified for Round 7 Wave 2; "
        "use solver.dynamics.modal_frf for single-model synthesis today"
    )
