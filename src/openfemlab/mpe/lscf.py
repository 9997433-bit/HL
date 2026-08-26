"""LSCF / poly-reference curve fitting entry points (spec MS-10.2..MS-10.4).

The kernel is one weighted right-matrix-fraction fit in the discrete-time
basis ``Omega_f = exp(i omega_f dt)`` (MS-10.2): the per-channel numerator
coefficients are eliminated through the reduced normal equations, the
denominator block is solved globally under the constraint ``alpha_n = I``, and
the poles are the eigenvalues of its block companion matrix mapped back with
``s_r = ln(z_r) / dt``. The scalar-denominator LSCF is the ``e = 1``
degenerate case of the same code path, not a second implementation.

Everything here is a direct solve over the measured lines, so identical inputs
produce bitwise-identical results and no seed argument exists (MS-10.1).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

from ..correlation.mac import mac_value
from ..exceptions import MPEError
from .types import MPEResult, PoleEstimate, StabilizationDiagram

if TYPE_CHECKING:  # pragma: no cover
    from openfemlab.solver.dynamics import FrequencyResponse

__all__ = ["fit_lscf", "stabilization_diagram", "extract_shapes", "extract_modes"]

#: Physicality filter of MS-10.2: a root damped beyond this is computational.
MAX_DAMPING_RATIO = 0.2

#: Weighting functions the MS-10.2 estimator accepts.
WEIGHTINGS = ("unity", "inverse")

#: Residual terms the MS-10.4 LSFD step can carry.
RESIDUAL_MODES = ("both", "upper", "lower", "none")

#: Keyword tolerances :func:`extract_modes` forwards to the diagram.
_DIAGRAM_TOLERANCES = ("freq_tol", "damp_tol", "mac_tol")


# ==================================================================== inputs


class _Band:
    """The band-restricted receptance one fit runs on (MS-10.1 conventions)."""

    __slots__ = ("frequencies", "omega", "data", "dt", "limits", "response", "excitation")

    def __init__(self, frf: FrequencyResponse, band: tuple[float, float] | None) -> None:
        if frf is None:
            raise MPEError("an FRF is required; got None")
        if getattr(frf, "response_type", None) != "receptance":
            raise MPEError(
                f"modal parameter extraction needs receptance, got "
                f"{getattr(frf, 'response_type', None)!r}; convert the FRF first "
                "with FrequencyResponse.converted('receptance')"
            )
        line = np.asarray(frf.frequencies, dtype=float)
        if line.size == 0:
            raise MPEError("the FRF carries no frequency line")
        f_max = float(np.max(line))
        if f_max <= 0.0:
            raise MPEError("the FRF frequency line has no positive frequency")

        low, high = (float(line.min()), f_max) if band is None else (float(band[0]), float(band[1]))
        if not np.isfinite(low) or not np.isfinite(high) or low > high:
            raise MPEError(f"the estimation band ({low!r}, {high!r}) is not an interval")
        inside = (line >= low) & (line <= high)
        if not np.any(inside):
            raise MPEError(
                f"the estimation band [{low:g}, {high:g}] Hz contains none of the "
                f"{line.size} measured lines"
            )

        self.limits = (low, high)
        self.frequencies = line[inside]
        self.omega = 2.0 * np.pi * self.frequencies
        self.data = np.asarray(frf.data, dtype=complex)[inside]
        # MS-10.2: the z-domain basis is anchored on the measurement's own
        # top frequency, so the fitted arc never wraps past the unit circle.
        self.dt = 1.0 / (2.0 * f_max)
        self.response = np.asarray(frf.response_dofs, dtype=int)
        self.excitation = np.asarray(frf.excitation_dofs, dtype=int)

    @property
    def shape(self) -> tuple[int, int, int]:
        return self.data.shape  # type: ignore[return-value]

    def basis(self, order: int) -> npt.NDArray[np.complex128]:
        """``[Omega^0, ..., Omega^order]`` on the band lines."""
        z = np.exp(1j * self.omega * self.dt)
        return z[:, None] ** np.arange(order + 1)[None, :]

    def weights(self, weighting: str) -> npt.NDArray[np.float64]:
        """Per-line, per-channel weights ``W_o(f)`` of the MS-10.2 estimator."""
        if weighting not in WEIGHTINGS:
            raise MPEError(f"unknown weighting {weighting!r}; expected one of {WEIGHTINGS}")
        lines, channels, _ = self.data.shape
        if weighting == "unity":
            return np.ones((lines, channels))
        magnitude = np.linalg.norm(self.data, axis=2)
        scale = np.max(magnitude) if magnitude.size else 0.0
        floor = 1e-12 * (scale if scale > 0.0 else 1.0)
        return 1.0 / np.maximum(magnitude, floor)


def _check_order(band: _Band, order: int) -> None:
    """Refuse a model order the band's line count cannot support (MS-10.5)."""
    if order < 1:
        raise MPEError(f"the model order must be >= 1, got {order}")
    lines, channels, references = band.shape
    unknowns = (order + 1) * references * (channels + references)
    equations = 2 * lines * channels * references
    if equations < unknowns:
        raise MPEError(
            f"model order {order} needs {unknowns} real unknowns but the "
            f"{lines} band lines of a {channels}x{references} FRF supply only "
            f"{equations} equations"
        )


# ============================================================ MS-10.2 kernel


def _denominator(band: _Band, order: int, weighting: str) -> npt.NDArray[np.float64]:
    """Denominator coefficients ``[alpha_0; ...; alpha_{n-1}]`` (``alpha_n = I``).

    The per-channel numerators are eliminated analytically, so only the
    ``(order * e) x e`` denominator block is solved globally.
    """
    lines, channels, references = band.shape
    powers = band.basis(order)
    weights = band.weights(weighting)
    size = (order + 1) * references

    reduced = np.zeros((size, size))
    for channel in range(channels):
        weight = weights[:, channel]
        numerator = powers * weight[:, None]
        denominator = -(
            numerator[:, :, None] * band.data[:, channel, :][:, None, :]
        ).reshape(lines, size)
        gram = np.real(numerator.conj().T @ numerator)
        cross = np.real(numerator.conj().T @ denominator)
        square = np.real(denominator.conj().T @ denominator)
        reduced += square - cross.T @ np.linalg.lstsq(gram, cross, rcond=None)[0]
    reduced = 0.5 * (reduced + reduced.T)

    free = order * references
    solution = -np.linalg.lstsq(reduced[:free, :free], reduced[:free, free:], rcond=None)[0]
    return np.asarray(solution, dtype=float)


def _companion(alpha: npt.NDArray[np.float64], references: int) -> npt.NDArray[np.float64]:
    """Block companion matrix of ``A(z) = sum_r alpha_r z^r`` with ``alpha_n = I``."""
    size = alpha.shape[0]
    matrix = np.zeros((size, size))
    matrix[: size - references, references:] = np.eye(size - references)
    matrix[size - references :, :] = -alpha.T
    return matrix


def _participation(
    alpha: npt.NDArray[np.float64], references: int, z: complex
) -> npt.NDArray[np.complex128]:
    """Reference participation ``L_r`` at the root ``z`` (MS-10.2).

    ``H = B A^-1`` puts the residue's reference direction in the *left* null
    space of ``A(z_r)``: with ``adj(A) = v u^T`` the residue matrix factors as
    ``(B v) u^T``, so ``u`` is the participation column.
    """
    order = alpha.shape[0] // references
    powers = z ** np.arange(order + 1)
    blocks = [alpha[r * references : (r + 1) * references, :] for r in range(order)]
    blocks.append(np.eye(references))
    matrix = sum(power * block for power, block in zip(powers, blocks, strict=True))
    left = np.linalg.svd(np.asarray(matrix, dtype=complex))[0][:, -1].conj()
    return _fix_phase(left)


def _fix_phase(vector: npt.NDArray[np.complex128]) -> npt.NDArray[np.complex128]:
    """Unit vector with its dominant component rotated onto the positive real axis."""
    norm = np.linalg.norm(vector)
    if norm == 0.0:  # pragma: no cover - a null vector always has unit norm
        return vector
    scaled = vector / norm
    dominant = scaled[int(np.argmax(np.abs(scaled)))]
    return scaled * np.exp(-1j * np.angle(dominant))


def fit_lscf(
    frf: FrequencyResponse,
    order: int,
    *,
    band: tuple[float, float] | None = None,
    weighting: str = "unity",
) -> tuple[PoleEstimate, ...]:
    """Poles of one weighted LSCF / poly-reference fit at ``order`` (MS-10.2).

    Parameters
    ----------
    frf:
        Measured or synthesized **receptance** over a frequency line; other
        response types must be converted by the caller (MS-10.1).
    order:
        Order of the matrix-polynomial denominator. With ``e`` references it
        carries ``order * e`` roots, so ``order * e >= 2 n`` is needed to
        represent ``n`` modes.
    band:
        Estimation band ``(f_lo, f_hi)`` [Hz]; poles are reported only inside
        it. ``None`` uses the whole line.
    weighting:
        ``"unity"`` or ``"inverse"`` (per-line ``1 / |H|``, which levels the
        anti-resonances against the peaks).

    Returns
    -------
    The physical poles, sorted by frequency. The MS-10.2 filter has already
    discarded the unstable mirror roots, the out-of-band roots, and anything
    damped beyond :data:`MAX_DAMPING_RATIO`.
    """
    prepared = _Band(frf, band)
    _check_order(prepared, order)
    references = prepared.shape[2]

    alpha = _denominator(prepared, order, weighting)
    roots = np.linalg.eigvals(_companion(alpha, references))

    low, high = prepared.limits
    estimates = []
    for root in roots:
        if not np.isfinite(root) or root == 0.0:
            continue
        pole = complex(np.log(root) / prepared.dt)
        if pole.imag <= 0.0 or pole.real >= 0.0:
            continue
        magnitude = abs(pole)
        frequency = magnitude / (2.0 * np.pi)
        damping = -pole.real / magnitude
        if not low <= frequency <= high or damping > MAX_DAMPING_RATIO:
            continue
        estimates.append(
            PoleEstimate(
                frequency_hz=float(frequency),
                damping_ratio=float(damping),
                pole=pole,
                order=int(order),
                participation=_participation(alpha, references, complex(root)),
            )
        )
    estimates.sort(key=lambda p: (p.frequency_hz, p.damping_ratio))
    return tuple(estimates)


# ========================================================== MS-10.3 diagram


def _classify(
    pole: PoleEstimate,
    previous: Sequence[PoleEstimate],
    freq_tol: float,
    damp_tol: float,
    mac_tol: float,
) -> tuple[str, int]:
    """MS-10.3 label of ``pole`` against the nearest pole one order below."""
    if not previous:
        return "new", -1
    distances = [
        abs(pole.frequency_hz - other.frequency_hz) / max(other.frequency_hz, 1e-30)
        for other in previous
    ]
    index = int(np.argmin(distances))
    nearest = previous[index]
    if distances[index] > freq_tol:
        return "new", index
    reference = max(abs(nearest.damping_ratio), 1e-30)
    if abs(pole.damping_ratio - nearest.damping_ratio) / reference > damp_tol:
        return "freq", index
    if pole.participation is None or nearest.participation is None:
        return "stable", index
    if mac_value(pole.participation, nearest.participation) < mac_tol:
        return "damp", index
    return "stable", index


def stabilization_diagram(
    frf: FrequencyResponse,
    orders: Sequence[int],
    *,
    band: tuple[float, float] | None = None,
    freq_tol: float = 0.01,
    damp_tol: float = 0.05,
    mac_tol: float = 0.95,
    weighting: str = "unity",
) -> StabilizationDiagram:
    """Fit over ``orders`` and classify poles across them (MS-10.3).

    Every pole at one order is compared against the nearest pole at the order
    below and escalated ``new -> freq -> damp -> stable`` as it passes the
    frequency, damping, and participation-MAC tests in turn. The links the
    comparison establishes are kept in ``settings`` so
    :meth:`~openfemlab.mpe.StabilizationDiagram.select` can walk the
    alignments without refitting.
    """
    requested = [int(value) for value in orders]
    if not requested:
        raise MPEError("a stabilization diagram needs at least one model order")
    if sorted(set(requested)) != requested:
        raise MPEError(f"the model orders must be strictly increasing, got {requested}")

    levels: list[tuple[PoleEstimate, ...]] = []
    links: list[tuple[int, ...]] = []
    previous: tuple[PoleEstimate, ...] = ()
    for order in requested:
        fitted = fit_lscf(frf, order, band=band, weighting=weighting)
        labelled, parents = [], []
        for pole in fitted:
            label, parent = _classify(pole, previous, freq_tol, damp_tol, mac_tol)
            labelled.append(
                PoleEstimate(
                    frequency_hz=pole.frequency_hz,
                    damping_ratio=pole.damping_ratio,
                    pole=pole.pole,
                    order=pole.order,
                    participation=pole.participation,
                    label=label,
                )
            )
            parents.append(parent if levels else -1)
        levels.append(tuple(labelled))
        links.append(tuple(parents))
        previous = tuple(labelled)

    settings = {
        "schema": "openfemlab.mpe.stabilization/1",
        "band_hz": None if band is None else (float(band[0]), float(band[1])),
        "weighting": weighting,
        "tolerances": {
            "freq_tol": float(freq_tol),
            "damp_tol": float(damp_tol),
            "mac_tol": float(mac_tol),
        },
        "links": tuple(links),
    }
    return StabilizationDiagram(tuple(requested), tuple(levels), settings)


# ============================================================= MS-10.4 LSFD


def _lsfd_basis(
    band: _Band, poles: Sequence[complex], residuals: str
) -> tuple[npt.NDArray[np.complex128], int]:
    """Complex LSFD basis with real unknowns, and the count of residual columns.

    Each mode contributes the two columns that a *conjugate pair* of residues
    spans, so the conjugacy of the physical model is enforced by construction
    rather than hoped for.
    """
    if residuals not in RESIDUAL_MODES:
        raise MPEError(f"unknown residuals mode {residuals!r}; expected one of {RESIDUAL_MODES}")
    j_omega = 1j * band.omega
    columns = []
    for pole in poles:
        direct = 1.0 / (j_omega - pole)
        conjugate = 1.0 / (j_omega - np.conjugate(pole))
        columns.append(direct + conjugate)
        columns.append(1j * (direct - conjugate))
    extra = 0
    if residuals in ("both", "upper"):
        columns.append(np.ones_like(j_omega))
        extra += 1
    if residuals in ("both", "lower"):
        if np.any(band.omega == 0.0):
            raise MPEError(
                "the lower-residual term is singular at 0 Hz; exclude the DC "
                "line from the band or use residuals='upper'"
            )
        columns.append(-1.0 / band.omega**2)
        extra += 1
    return np.column_stack(columns), extra


def _rank_one(
    residue: npt.NDArray[np.complex128], participation: npt.NDArray[np.complex128] | None
) -> tuple[npt.NDArray[np.complex128], npt.NDArray[np.complex128]]:
    """Split ``A_r = psi_r L_r^T`` (MS-10.4), unit-max shape, phase pinned."""
    if participation is not None and residue.shape[1] > 1:
        weight = participation.conj()
        shape = residue @ weight / float(np.real(weight.conj() @ weight))
        reference = np.asarray(participation, dtype=complex)
    else:
        left, singular, right = np.linalg.svd(residue)
        shape = left[:, 0]
        reference = (singular[0] * right[0, :].conj()).astype(complex)
    shape = _fix_phase(shape)
    peak = np.max(np.abs(shape))
    if peak > 0.0:
        shape = shape / peak
    return shape, reference


def _drive_point(band: _Band) -> tuple[int, int] | None:
    """Indices ``(response, excitation)`` of the lowest collocated DOF, if any."""
    shared = np.intersect1d(band.response, band.excitation)
    if shared.size == 0:
        return None
    dof = int(shared[0])
    return int(np.flatnonzero(band.response == dof)[0]), int(
        np.flatnonzero(band.excitation == dof)[0]
    )


def _scale_unity_modal_a(
    residues: npt.NDArray[np.complex128], drive: tuple[int, int]
) -> tuple[npt.NDArray[np.complex128], npt.NDArray[np.complex128]] | None:
    """Unity-modal-A shapes/participation from the driving-point residues.

    With ``A_r = psi_r psi_r^T`` at unit modal A, the collocated entry is
    ``psi_{j*}^2``; dividing the driving-point row and column by its square
    root reproduces the MS-7.2 residue convention exactly.
    """
    response, excitation = drive
    collocated = residues[:, response, excitation]
    scale = np.max(np.abs(residues), axis=(1, 2))
    if np.any(np.abs(collocated) <= 1e-10 * np.maximum(scale, 1e-30)):
        return None
    root = np.sqrt(collocated)
    shapes = (residues[:, :, excitation] / root[:, None]).T
    participation = (residues[:, response, :] / root[:, None]).T
    return shapes, participation


def extract_shapes(
    frf: FrequencyResponse,
    poles: Sequence[PoleEstimate],
    *,
    band: tuple[float, float] | None = None,
    residuals: str = "both",
) -> MPEResult:
    """LSFD residue/shape estimation with the poles frozen (MS-10.4).

    The residues, the upper residual ``UR`` and the lower residual ``LR`` are
    one real linear least-squares problem over the band; the residue matrices
    are then split ``A_r = psi_r L_r^T``. When the channel set contains a
    driving point the shapes come out in unity-modal-A scaling; otherwise they
    are unit-max and ``diagnostics["scaling"]`` reads ``"arbitrary"``.
    """
    prepared = _Band(frf, band)
    estimates = tuple(poles)
    if not estimates:
        raise MPEError("residue estimation needs at least one pole")
    values = [complex(pole.pole) for pole in estimates]

    lines, channels, references = prepared.shape
    basis, extra = _lsfd_basis(prepared, values, residuals)
    unknowns = basis.shape[1]
    if 2 * lines < unknowns:
        raise MPEError(
            f"{len(estimates)} poles and {extra} residual terms need {unknowns} "
            f"real unknowns but the band has only {lines} lines"
        )

    matrix = np.vstack((basis.real, basis.imag))
    observed = prepared.data.reshape(lines, channels * references)
    rhs = np.vstack((observed.real, observed.imag))
    coefficients = np.linalg.lstsq(matrix, rhs, rcond=None)[0]

    count = len(estimates)
    residues = (
        coefficients[0 : 2 * count : 2] + 1j * coefficients[1 : 2 * count : 2]
    ).reshape(count, channels, references)
    upper, lower = _residual_terms(coefficients, count, residuals, channels, references)

    scaled = None
    drive = _drive_point(prepared)
    if drive is not None:
        scaled = _scale_unity_modal_a(residues, drive)
    if scaled is not None:
        shapes, participation = scaled
        scaling = "unity-modal-A"
    else:
        split = [
            _rank_one(residues[index], estimates[index].participation)
            for index in range(count)
        ]
        shapes = np.column_stack([pair[0] for pair in split])
        participation = np.column_stack([pair[1] for pair in split])
        scaling = "arbitrary"

    synthesized = (basis @ coefficients).reshape(lines, channels, references)
    quality = _channel_frac(prepared.data, synthesized)

    diagnostics = {
        "method": "pLSCF/LSFD",
        "orders": tuple(sorted({pole.order for pole in estimates})),
        "band_hz": prepared.limits,
        "num_lines": int(lines),
        "residuals": residuals,
        "scaling": scaling,
        "time_step": float(prepared.dt),
        "upper_residual": upper,
        "lower_residual": lower,
        "response_dofs": prepared.response.copy(),
        "excitation_dofs": prepared.excitation.copy(),
        "drive_point": None if drive is None else int(prepared.response[drive[0]]),
    }
    return MPEResult(
        frequencies_hz=np.array([pole.frequency_hz for pole in estimates], dtype=float),
        damping_ratios=np.array([pole.damping_ratio for pole in estimates], dtype=float),
        poles=np.array(values, dtype=complex),
        shapes=np.asarray(shapes, dtype=complex),
        participation=np.asarray(participation, dtype=complex),
        frac=quality,
        diagnostics=diagnostics,
    )


def _residual_terms(
    coefficients: npt.NDArray[np.float64],
    count: int,
    residuals: str,
    channels: int,
    references: int,
) -> tuple[npt.NDArray[np.float64] | None, npt.NDArray[np.float64] | None]:
    """The ``UR`` / ``LR`` blocks of an LSFD solution, reshaped to the FRF grid."""
    rows = iter(coefficients[2 * count :])
    upper = next(rows).reshape(channels, references) if residuals in ("both", "upper") else None
    lower = next(rows).reshape(channels, references) if residuals in ("both", "lower") else None
    return upper, lower


def _channel_frac(
    measured: npt.NDArray[np.complex128], synthesized: npt.NDArray[np.complex128]
) -> npt.NDArray[np.float64]:
    """Per-channel resynthesis FRAC over the band and every reference (MS-10.4)."""
    from ..solver.dynamics import frac

    lines, channels, references = measured.shape
    stacked = np.transpose(measured, (0, 2, 1)).reshape(lines * references, channels)
    model = np.transpose(synthesized, (0, 2, 1)).reshape(lines * references, channels)
    return np.atleast_1d(np.asarray(frac(stacked, model), dtype=float))


# =========================================================== MS-10.6 driver


def extract_modes(
    frf: FrequencyResponse,
    orders: Sequence[int],
    *,
    band: tuple[float, float] | None = None,
    min_count: int = 3,
    **tolerances: Any,
) -> MPEResult:
    """One-call driver: stabilization diagram, automatic pick, LSFD (MS-10.6).

    ``tolerances`` accepts the diagram settings (``freq_tol``, ``damp_tol``,
    ``mac_tol``), the estimator ``weighting``, and the LSFD ``residuals``
    mode; anything else is a typed failure rather than a silent no-op.
    """
    unknown = set(tolerances) - set(_DIAGRAM_TOLERANCES) - {"weighting", "residuals"}
    if unknown:
        raise MPEError(f"unknown tolerance arguments: {sorted(unknown)}")
    diagram_kwargs = {name: tolerances[name] for name in _DIAGRAM_TOLERANCES if name in tolerances}
    weighting = tolerances.get("weighting", "unity")

    diagram = stabilization_diagram(
        frf, orders, band=band, weighting=weighting, **diagram_kwargs
    )
    picked = diagram.select(min_count=min_count)
    result = extract_shapes(
        frf, picked, band=band, residuals=tolerances.get("residuals", "both")
    )
    result.diagnostics.update(
        {
            "orders": diagram.orders,
            "min_count": int(min_count),
            "weighting": weighting,
            "tolerances": diagram.settings["tolerances"],
            "labels": tuple(pole.label for pole in picked),
            "picked_orders": tuple(pole.order for pole in picked),
        }
    )
    return result
