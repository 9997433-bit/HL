"""FRF correlation, reduced to the block the report carries (MS-7.4).

:func:`~openfemlab.solver.dynamics.frac` and
:func:`~openfemlab.solver.dynamics.fdac` are the kernels — the frequency-domain
counterparts of MAC and of the MAC matrix. This module wires them into the
correlation layer: it resolves a reference/comparison FRF pair (measured versus
synthesized, in either order) onto a common frequency line and channel set, and
reduces the result to the per-channel FRAC vector, the FDAC matrix and the
scalars a gate reads. :class:`~openfemlab.correlation.report.CorrelationReport`
carries the outcome as its ``frf`` block, so an FRF comparison travels in the
same schema-versioned artifact as the modal correlation instead of a parallel
one — and the kernel still exists only once (the GAP-01 rule).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import numpy.typing as npt

from ..solver.dynamics import fdac as fdac_matrix
from ..solver.dynamics import frac as frac_values

__all__ = [
    "FRFCorrelation",
    "frf_correlation",
]

FloatArray = npt.NDArray[np.float64]
ComplexArray = npt.NDArray[np.complex128]

#: Two frequency lines count as the same line within this relative tolerance.
_FREQUENCY_RTOL = 1.0e-9


@dataclass
class FRFCorrelation:
    """FRAC/FDAC outcome of one reference-versus-comparison FRF pair.

    ``frac[c]`` correlates the two FRFs of channel ``c`` over the whole
    frequency line — the FRF analogue of a diagonal MAC value. ``fdac[p, q]``
    correlates the reference deflection shape at line ``p`` with the comparison
    shape at line ``q``, so its diagonal grades shape agreement per frequency
    and an off-diagonal ridge exposes a frequency shift.
    """

    frequencies: FloatArray
    frac: FloatArray
    fdac: FloatArray | None = None
    channels: tuple[str, ...] | None = None
    response_type: str = "receptance"
    excitation: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.frequencies = np.asarray(self.frequencies, dtype=np.float64).ravel()
        self.frac = np.atleast_1d(np.asarray(self.frac, dtype=np.float64)).ravel()
        if self.frac.size == 0:
            raise ValueError("an FRF correlation needs at least one channel")
        if self.channels is not None:
            self.channels = tuple(str(label) for label in self.channels)
            if len(self.channels) != self.frac.size:
                raise ValueError(
                    f"{len(self.channels)} channel labels for {self.frac.size} FRAC values"
                )
        if self.fdac is not None:
            self.fdac = np.asarray(self.fdac, dtype=np.float64)
            expected = (self.frequencies.size, self.frequencies.size)
            if self.fdac.shape != expected:
                raise ValueError(f"FDAC matrix {self.fdac.shape} does not match {expected}")

    # ------------------------------------------------------------------ shape

    @property
    def n_frequencies(self) -> int:
        return int(self.frequencies.size)

    @property
    def n_channels(self) -> int:
        return int(self.frac.size)

    # ---------------------------------------------------------------- scalars

    @property
    def mean_frac(self) -> float:
        return float(self.frac.mean())

    @property
    def min_frac(self) -> float:
        return float(self.frac.min())

    @property
    def max_frac(self) -> float:
        return float(self.frac.max())

    @property
    def fdac_diagonal(self) -> FloatArray:
        """Shape agreement at each frequency line, empty without an FDAC."""
        if self.fdac is None:
            return np.empty(0)
        return np.asarray(np.diag(self.fdac), dtype=np.float64)

    @property
    def min_fdac_diagonal(self) -> float | None:
        diagonal = self.fdac_diagonal
        return float(diagonal.min()) if diagonal.size else None

    def worst_channel(self) -> tuple[int, float]:
        """``(index, value)`` of the least correlated response channel."""
        index = int(np.argmin(self.frac))
        return index, float(self.frac[index])

    def channel_label(self, index: int) -> str:
        return self.channels[index] if self.channels else f"channel {index}"

    def is_correlated(self, frac_threshold: float = 0.9) -> bool:
        """True when every channel meets the FRAC acceptance limit."""
        return bool(self.min_frac >= frac_threshold)

    # -------------------------------------------------------------- artifacts

    def as_dict(self) -> dict[str, Any]:
        """Plain-Python view of the block (JSON ready, no NumPy scalars)."""
        return {
            "response_type": self.response_type,
            "excitation": self.excitation,
            "n_frequencies": self.n_frequencies,
            "n_channels": self.n_channels,
            "mean_frac": self.mean_frac,
            "min_frac": self.min_frac,
            "max_frac": self.max_frac,
            "min_fdac_diagonal": self.min_fdac_diagonal,
            "frequencies": self.frequencies.tolist(),
            "frac": self.frac.tolist(),
            "channels": None if self.channels is None else list(self.channels),
            "fdac": None if self.fdac is None else self.fdac.tolist(),
            "meta": dict(self.meta),
        }

    def report(self) -> str:
        index, value = self.worst_channel()
        lines = [
            f"FRF correlation         : {self.response_type}, "
            f"{self.n_channels} channels x {self.n_frequencies} lines",
            f"mean / min FRAC         : {self.mean_frac:.4f} / {self.min_frac:.4f}",
            f"worst FRAC channel      : {self.channel_label(index)} ({value:.4f})",
        ]
        worst_diagonal = self.min_fdac_diagonal
        if worst_diagonal is not None:
            lines.append(f"min FDAC diagonal       : {worst_diagonal:.4f}")
        return "\n".join(lines)

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.report()


def frf_correlation(
    reference: Any,
    comparison: Any,
    *,
    excitation_dof: int | None = None,
    frequencies: Any = None,
    channels: Any = None,
    response_type: str | None = None,
    with_fdac: bool = True,
    meta: dict[str, Any] | None = None,
) -> FRFCorrelation:
    """Correlate two FRF sets over a shared frequency line.

    Parameters
    ----------
    reference, comparison:
        Either :class:`~openfemlab.solver.dynamics.FrequencyResponse` objects or
        ``(n_frequencies, n_channels)`` complex arrays. By MS-2.4 convention the
        measured set is the reference and the FE model is judged against it, but
        FRAC and FDAC are symmetric so the order only sets the labels.
    excitation_dof:
        Which exciter column to correlate. Required when a
        ``FrequencyResponse`` carries more than one excitation DOF.
    frequencies:
        The frequency line [Hz], required only when neither input carries one.
    channels:
        Labels for the response channels; taken from the response DOFs of a
        ``FrequencyResponse`` when not given.
    with_fdac:
        Also build the ``(n_frequencies, n_frequencies)`` FDAC matrix. Turn it
        off for long frequency lines, where the matrix dominates the artifact.
    """
    ref, ref_line, ref_labels, ref_type = _extract(reference, excitation_dof, "reference")
    cmp_, cmp_line, cmp_labels, cmp_type = _extract(comparison, excitation_dof, "comparison")
    if ref.shape != cmp_.shape:
        raise ValueError(
            f"the two FRF sets must have the same shape, got {ref.shape} and {cmp_.shape}"
        )

    line = _resolve_frequencies(frequencies, ref_line, cmp_line, ref.shape[0])
    kind = _resolve_response_type(response_type, ref_type, cmp_type)
    labels = _resolve_channels(channels, ref_labels, cmp_labels, ref.shape[1])

    return FRFCorrelation(
        frequencies=line,
        frac=np.atleast_1d(np.asarray(frac_values(ref, cmp_, axis=0), dtype=np.float64)),
        fdac=fdac_matrix(ref, cmp_) if with_fdac else None,
        channels=labels,
        response_type=kind,
        excitation=None if excitation_dof is None else f"dof {int(excitation_dof)}",
        meta=dict(meta or {}),
    )


# ==================================================================== helpers


def _extract(
    response: Any,
    excitation_dof: int | None,
    name: str,
) -> tuple[ComplexArray, FloatArray | None, tuple[str, ...] | None, str | None]:
    """``(block, frequency line, channel labels, response type)`` of one input.

    ``block`` is the ``(n_frequencies, n_channels)`` slice both kernels consume;
    everything else is metadata that may be absent for a raw array.
    """
    if hasattr(response, "data") and hasattr(response, "excitation_dofs"):
        data = np.asarray(response.data, dtype=complex)
        exciters = np.asarray(response.excitation_dofs, dtype=int).ravel()
        column = _excitation_column(exciters, excitation_dof, name)
        labels = tuple(f"dof {int(dof)}" for dof in np.asarray(response.response_dofs).ravel())
        return (
            data[:, :, column],
            np.asarray(response.frequencies, dtype=np.float64).ravel(),
            labels,
            getattr(response, "response_type", None),
        )

    block = np.asarray(response, dtype=complex)
    if block.ndim == 1:
        block = block[:, None]
    if block.ndim != 2:
        raise ValueError(
            f"{name} must be a FrequencyResponse or an (n_frequencies, n_channels) "
            f"array, got shape {block.shape}"
        )
    return block, None, None, None


def _excitation_column(exciters: np.ndarray, excitation_dof: int | None, name: str) -> int:
    if excitation_dof is None:
        if exciters.size != 1:
            raise ValueError(
                f"{name} carries {exciters.size} excitation DOFs "
                f"({exciters.tolist()}); name one with excitation_dof="
            )
        return 0
    matches = np.flatnonzero(exciters == int(excitation_dof))
    if matches.size == 0:
        raise ValueError(
            f"{name} was not excited at DOF {excitation_dof}; available: {exciters.tolist()}"
        )
    return int(matches[0])


def _resolve_frequencies(
    explicit: Any,
    reference: FloatArray | None,
    comparison: FloatArray | None,
    count: int,
) -> FloatArray:
    if explicit is not None:
        line = np.asarray(explicit, dtype=np.float64).ravel()
    elif reference is not None:
        line = reference
    elif comparison is not None:
        line = comparison
    else:
        raise ValueError("the frequency line is unknown for plain arrays; pass frequencies=[...]")
    if line.size != count:
        raise ValueError(f"the frequency line has {line.size} entries for {count} FRF lines")
    for other in (reference, comparison):
        if other is not None and not np.allclose(line, other, rtol=_FREQUENCY_RTOL, atol=0.0):
            raise ValueError(
                "the two FRF sets are sampled on different frequency lines; "
                "resample them onto a common line before correlating"
            )
    return line


def _resolve_response_type(
    explicit: str | None,
    reference: str | None,
    comparison: str | None,
) -> str:
    if explicit is not None:
        return explicit
    if reference is not None and comparison is not None and reference != comparison:
        raise ValueError(
            f"cannot correlate {reference} against {comparison}; convert one set "
            "with FrequencyResponse.converted(...) first"
        )
    return reference or comparison or "receptance"


def _resolve_channels(
    explicit: Any,
    reference: tuple[str, ...] | None,
    comparison: tuple[str, ...] | None,
    count: int,
) -> tuple[str, ...] | None:
    labels = explicit if explicit is not None else (reference or comparison)
    if labels is None:
        return None
    resolved = tuple(str(label) for label in labels)
    if len(resolved) != count:
        raise ValueError(f"{len(resolved)} channel labels for {count} FRF channels")
    return resolved
