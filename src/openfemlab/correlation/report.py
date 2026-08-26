"""The serializable correlation artifact (MS-2.6).

:mod:`~openfemlab.correlation.summary` reduces a pairing to the scalars an
updater steers on; this module packages those scalars together with the MAC
matrix, the pairing table, the COMAC vector and — since schema 1.1 — the
optional FRF block of :mod:`~openfemlab.correlation.frf` into a
schema-versioned, JSON-serializable :class:`CorrelationReport`: the exchange
currency between the correlation, updating and workflow layers, and the
artifact the CLI and CI publish.

Serialization is a round trip, not an export: :meth:`CorrelationReport.to_json`
and :meth:`CorrelationReport.from_json` are inverses (AC-CORR-008), so a
published artifact can be read back into the same objects the analysis
produced instead of only being looked at.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

from .align import AlignedShapes, align_modal_data
from .frf import FRFCorrelation
from .mac import comac as comac_vector
from .pairing import ModePairing, pair_modes
from .summary import CorrelationSummary, correlation_summary

if TYPE_CHECKING:  # pragma: no cover - typing only, keeps correlation core-free
    from .align import HasShapesAndDofMap

__all__ = [
    "SCHEMA_KEYS",
    "SCHEMA_VERSION",
    "CorrelationReport",
    "correlate_modal_data",
    "correlation_report",
]

#: 1.1 added the optional ``frf`` block (MS-7.4); a report without an FRF
#: comparison still serializes it as ``null``, so the key set does not depend
#: on which analyses were run.
SCHEMA_VERSION = "1.1"

#: Every key :meth:`CorrelationReport.to_dict` writes. A consumer may rely on
#: all of them being present: an analysis that did not run emits ``null``
#: rather than dropping its block, and :meth:`CorrelationReport.from_dict`
#: rejects a payload that is missing any of them.
SCHEMA_KEYS = (
    "schema_version",
    "summary",
    "pairs",
    "unpaired_test",
    "unpaired_fe",
    "pairing_method",
    "mac_matrix",
    "comac",
    "dof_labels",
    "frf",
    "settings",
    "meta",
)


@dataclass
class CorrelationReport:
    """Complete, serializable outcome of one FE/test correlation."""

    summary: CorrelationSummary
    pairing: ModePairing
    mac_matrix: npt.NDArray[np.float64] | None = None
    comac: npt.NDArray[np.float64] | None = None
    dof_labels: tuple[str, ...] | None = None
    frf: FRFCorrelation | None = None
    settings: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    @property
    def mean_mac(self) -> float:
        return self.summary.mean_mac

    @property
    def min_mac(self) -> float:
        return self.summary.min_mac

    @property
    def max_abs_freq_error_pct(self) -> float:
        return self.summary.max_abs_freq_error_pct

    @property
    def mean_frac(self) -> float | None:
        return None if self.frf is None else self.frf.mean_frac

    @property
    def min_frac(self) -> float | None:
        return None if self.frf is None else self.frf.min_frac

    def is_correlated(
        self,
        mac_threshold: float = 0.9,
        freq_tolerance_pct: float = 2.0,
        frac_threshold: float | None = None,
    ) -> bool:
        """Apply the MS-4.2 validation gates to every paired mode.

        Naming ``frac_threshold`` adds the MS-7.4 frequency-domain gate to the
        modal ones; asking for it without an FRF block is a caller error rather
        than a silently failed gate.
        """
        modal = self.summary.is_correlated(mac_threshold, freq_tolerance_pct)
        if frac_threshold is None:
            return modal
        if self.frf is None:
            raise ValueError("this report carries no FRF block, so FRAC cannot be gated")
        return modal and self.frf.is_correlated(frac_threshold)

    def worst_comac_dof(self) -> tuple[int, float] | None:
        """``(dof_index, value)`` of the least consistent correlation DOF."""
        if self.comac is None or self.comac.size == 0:
            return None
        index = int(np.argmin(self.comac))
        return index, float(self.comac[index])

    def to_dict(self) -> dict[str, Any]:
        """Plain-Python view of the report (JSON ready, no NumPy scalars)."""
        return {
            "schema_version": self.schema_version,
            "summary": self.summary.as_dict(),
            "pairs": [pair.as_dict() for pair in self.pairing.pairs],
            "unpaired_test": list(self.pairing.unpaired_test),
            "unpaired_fe": list(self.pairing.unpaired_fe),
            "pairing_method": self.pairing.method,
            "mac_matrix": None if self.mac_matrix is None else self.mac_matrix.tolist(),
            "comac": None if self.comac is None else self.comac.tolist(),
            "dof_labels": None if self.dof_labels is None else list(self.dof_labels),
            "frf": None if self.frf is None else self.frf.as_dict(),
            "settings": dict(self.settings),
            "meta": dict(self.meta),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> CorrelationReport:
        """Rebuild a report from :meth:`to_dict` (MS-2.6, AC-CORR-008).

        This is the strict inverse of the serialization, not a lenient
        importer: a payload missing a schema key, or written by a schema this
        build does not know, is a corrupt artifact and is refused here rather
        than silently turned into a report with an empty block.
        """
        missing = [key for key in SCHEMA_KEYS if key not in payload]
        if missing:
            raise ValueError(f"correlation report payload is missing keys: {missing}")
        version = str(payload["schema_version"])
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"cannot read a schema {version!r} correlation report; "
                f"this build writes and reads {SCHEMA_VERSION!r}"
            )

        pairing = ModePairing.from_dict(
            {
                "pairs": payload["pairs"],
                "unpaired_test": payload["unpaired_test"],
                "unpaired_fe": payload["unpaired_fe"],
                "mac_matrix": payload["mac_matrix"],
                "method": payload["pairing_method"],
            }
        )
        comac = payload["comac"]
        labels = payload["dof_labels"]
        frf = payload["frf"]
        return cls(
            summary=CorrelationSummary.from_dict(payload["summary"], pairing),
            pairing=pairing,
            mac_matrix=pairing.mac_matrix,
            comac=None if comac is None else np.asarray(comac, dtype=np.float64),
            dof_labels=None if labels is None else tuple(str(label) for label in labels),
            frf=None if frf is None else FRFCorrelation.from_dict(frf),
            settings=dict(payload["settings"]),
            meta=dict(payload["meta"]),
            schema_version=version,
        )

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, text: str) -> CorrelationReport:
        """Rebuild a report from the text :meth:`to_json` produced."""
        return cls.from_dict(json.loads(text))

    def report(self) -> str:
        lines = [self.summary.report()]
        worst = self.worst_comac_dof()
        if worst is not None:
            index, value = worst
            label = self.dof_labels[index] if self.dof_labels else f"dof {index}"
            lines.append(f"\nworst COMAC DOF         : {label} ({value:.4f})")
        if self.frf is not None:
            lines.append(f"\n{self.frf.report()}")
        return "\n".join(lines)

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.report()


def correlation_report(
    test_frequencies: Any = None,
    fe_frequencies: Any = None,
    test_shapes: Any = None,
    fe_shapes: Any = None,
    *,
    aligned: AlignedShapes | None = None,
    dof_labels: Any = None,
    weights: Any = None,
    pairing: ModePairing | None = None,
    with_comac: bool = True,
    frf: FRFCorrelation | None = None,
    meta: dict[str, Any] | None = None,
    **pairing_kwargs: Any,
) -> CorrelationReport:
    """Pair two mode sets on a common DOF set and build the full report.

    Parameters
    ----------
    test_shapes, fe_shapes:
        ``(ndof, m)`` shape matrices on a **common** DOF set, or ``None`` to
        correlate on frequencies alone.
    aligned:
        Result of :mod:`openfemlab.correlation.align`, used in place of
        ``test_shapes`` / ``fe_shapes`` / ``dof_labels`` when given.
    with_comac:
        Also compute the per-DOF COMAC over the paired modes.
    frf:
        FRF correlation block from
        :func:`~openfemlab.correlation.frf.frf_correlation`, carried alongside
        the modal correlation in the same artifact (schema 1.1).
    **pairing_kwargs:
        Forwarded to :func:`~openfemlab.correlation.pairing.pair_modes`
        (``method``, ``mac_threshold``, ``frequency_tolerance_pct``,
        ``freq_penalty``, ``max_pairs``).
    """
    if aligned is not None:
        test_shapes = aligned.test
        fe_shapes = aligned.fe
        if dof_labels is None:
            dof_labels = aligned.labels

    if pairing is None:
        pairing = pair_modes(
            test_shapes=test_shapes,
            fe_shapes=fe_shapes,
            test_frequencies=test_frequencies,
            fe_frequencies=fe_frequencies,
            weights=weights,
            **pairing_kwargs,
        )
    summary = correlation_summary(pairing=pairing)

    comac = None
    if with_comac and test_shapes is not None and fe_shapes is not None and pairing.pairs:
        comac = comac_vector(test_shapes, fe_shapes, pairing)

    settings: dict[str, Any] = {
        "method": pairing.method,
        "weighted": weights is not None,
        **pairing_kwargs,
    }
    return CorrelationReport(
        summary=summary,
        pairing=pairing,
        mac_matrix=pairing.mac_matrix,
        comac=comac,
        dof_labels=None if dof_labels is None else tuple(str(label) for label in dof_labels),
        frf=frf,
        settings=settings,
        meta=dict(meta or {}),
    )


def correlate_modal_data(
    fe_result: HasShapesAndDofMap,
    test_data: HasShapesAndDofMap,
    *,
    strict: bool = True,
    weights: Any = None,
    **kwargs: Any,
) -> CorrelationReport:
    """Full pipeline for two result objects: DOF alignment, pairing, report.

    ``fe_result`` and ``test_data`` are any objects carrying ``frequencies``,
    ``shapes`` and a ``dof_map`` — in practice
    :class:`~openfemlab.core.results.ModalResult` and
    :class:`~openfemlab.core.results.TestData`, whatever solver or file they
    came from.
    """
    aligned = align_modal_data(fe_result, test_data, strict=strict)
    return correlation_report(
        test_frequencies=test_data.frequencies,  # type: ignore[attr-defined]
        fe_frequencies=fe_result.frequencies,  # type: ignore[attr-defined]
        aligned=aligned,
        weights=weights,
        meta={
            "n_correlation_dofs": aligned.n_dof,
            "n_unmatched_test_dofs": int(aligned.unmatched_test.size),
            "n_unmatched_fe_dofs": int(aligned.unmatched_fe.size),
        },
        **kwargs,
    )
