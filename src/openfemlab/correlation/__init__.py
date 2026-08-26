"""FE-test correlation layer (L3).

Quantifies agreement between an FE :class:`~openfemlab.core.results.ModalResult`
and measured :class:`~openfemlab.core.results.TestData`:

- :mod:`~openfemlab.correlation.align` — DOF matching between the model and the
  sensor set (reduction; SEREP expansion in Round 3).
- :mod:`~openfemlab.correlation.mac` — ``mac`` / ``automac`` / ``comac`` /
  ``orthogonality`` shape-correlation metrics, optionally mass weighted.
- :mod:`~openfemlab.correlation.metrics` — frequency-error metrics, with the
  test set as the reference: ``Δf% = 100 (f_fe − f_test) / f_test``.
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

from .align import (
    AlignedShapes,
    align_by_labels,
    align_dof_maps,
    align_modal_data,
    align_shapes,
    selection_matrix,
)
from .mac import automac, comac, mac, mac_value, modal_scale_factor, orthogonality
from .metrics import (
    FrequencyDifference,
    frequency_difference,
    frequency_error_matrix,
    relative_frequency_error,
)
from .pairing import ModePair, ModePairing, pair_modes
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
    "automac",
    "comac",
    "mac",
    "mac_value",
    "modal_scale_factor",
    "orthogonality",
    # frequency metrics
    "FrequencyDifference",
    "frequency_difference",
    "frequency_error_matrix",
    "relative_frequency_error",
    # pairing
    "ModePair",
    "ModePairing",
    "pair_modes",
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
