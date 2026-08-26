"""FE-test correlation layer (L3).

Quantifies agreement between an FE :class:`~openfemlab.core.results.ModalResult`
and measured :class:`~openfemlab.core.results.TestData`:

- :mod:`~openfemlab.correlation.align` — DOF matching between the model and the
  sensor set.
- :mod:`~openfemlab.correlation.reduction` — Guyan / IRS / SEREP bases, the TAM
  mass matrix, and SEREP expansion of measured shapes to the full FE space.
- :mod:`~openfemlab.correlation.mac` — ``mac`` / ``automac`` / ``comac`` /
  ``orthogonality`` shape-correlation metrics, optionally mass weighted.
- :mod:`~openfemlab.correlation.metrics` — frequency-error metrics, with the
  test set as the reference: ``Δf% = 100 (f_fe − f_test) / f_test``.
- ``frac`` / ``fdac`` — the frequency-domain counterparts of MAC, re-exported
  from :mod:`openfemlab.solver.dynamics` so FRF correlation is reachable from
  this namespace without a second implementation of the kernel.
- :mod:`~openfemlab.correlation.pairing` — ``pair_modes``, globally optimal
  FE/test pairing via Hungarian assignment on a combined MAC + frequency cost,
  instead of the greedy max-MAC pass classic tools use.
- :mod:`~openfemlab.correlation.summary` — the scalar quality indicators an
  updating run steers on.
- :mod:`~openfemlab.correlation.report` — ``CorrelationReport``, the paired
  table (f_FE, f_test, Δf%, MAC) plus MAC matrix and COMAC, serializable to
  JSON for the CLI and CI artifacts.

The layer works on plain arrays, so results from any solver — internal or
imported through :mod:`openfemlab.io` — correlate the same way::

    from openfemlab.correlation import correlate_modal_data

    report = correlate_modal_data(fe_modes, measured)
    print(report.report())
"""

from ..solver.dynamics import fdac, frac
from .align import (
    AlignedShapes,
    align_by_labels,
    align_dof_maps,
    align_modal_data,
    align_shapes,
    selection_matrix,
)
from .mac import (
    auto_mac,
    automac,
    comac,
    mac,
    mac_matrix,
    mac_value,
    modal_scale_factor,
    orthogonality,
)
from .metrics import (
    FrequencyDifference,
    frequency_difference,
    frequency_error_matrix,
    relative_frequency_error,
)
from .pairing import ModePair, ModePairing, pair_modes
from .reduction import (
    ReductionBasis,
    expand_shapes,
    guyan_reduction,
    irs_reduction,
    serep_basis,
    tam_mass,
)
from .report import CorrelationReport, correlate_modal_data, correlation_report
from .summary import (
    CorrelationSummary,
    correlate,
    correlation_summary,
    normalized_frequency_residual,
    off_diagonal_mac,
)

__all__ = [
    # DOF alignment
    "AlignedShapes",
    "align_by_labels",
    "align_dof_maps",
    "align_modal_data",
    "align_shapes",
    "selection_matrix",
    # shape metrics
    "auto_mac",
    "automac",
    "comac",
    "mac",
    "mac_matrix",
    "mac_value",
    "modal_scale_factor",
    "orthogonality",
    # frequency metrics
    "FrequencyDifference",
    "frequency_difference",
    "frequency_error_matrix",
    "relative_frequency_error",
    # FRF metrics (implemented in openfemlab.solver.dynamics)
    "fdac",
    "frac",
    # pairing
    "ModePair",
    "ModePairing",
    "pair_modes",
    # reduction / expansion
    "ReductionBasis",
    "expand_shapes",
    "guyan_reduction",
    "irs_reduction",
    "serep_basis",
    "tam_mass",
    # aggregated results
    "CorrelationReport",
    "CorrelationSummary",
    "correlate",
    "correlate_modal_data",
    "correlation_report",
    "correlation_summary",
    "normalized_frequency_residual",
    "off_diagonal_mac",
]
