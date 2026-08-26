"""Modal Assurance Criterion family of shape-correlation metrics.

Pure array functions (P3): they take shape matrices whose rows are already on
a common DOF set — DOF matching is a separate, explicit step provided by
:mod:`openfemlab.correlation.align`.

Every metric accepts an optional ``weights`` argument, either a per-DOF vector
(diagonal weighting, e.g. sensor confidence or tributary mass) or a full
``(ndof, ndof)`` matrix such as a Guyan-reduced mass matrix, which turns the
MAC into the mass-weighted MAC of MS-2.2.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import numpy.typing as npt

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids an import cycle
    from openfemlab.correlation.pairing import ModePairing

__all__ = [
    "auto_mac",
    "automac",
    "comac",
    "mac",
    "mac_matrix",
    "mac_value",
    "modal_scale_factor",
    "orthogonality",
]

Shapes = npt.NDArray[np.floating] | npt.NDArray[np.complexfloating]


def as_columns(shapes: Any, name: str = "shapes") -> np.ndarray:
    """Return ``shapes`` as a 2-D ``(ndof, m)`` array whose columns are modes."""
    arr = np.atleast_2d(np.asarray(shapes).T).T
    if arr.ndim != 2:
        raise ValueError(f"{name} must be 1-D or 2-D, got {arr.ndim}-D")
    if arr.size == 0:
        raise ValueError(f"{name} must contain at least one mode shape")
    if not np.issubdtype(arr.dtype, np.number):
        raise ValueError(f"{name} must be numeric")
    return arr


def prepare_weights(weights: Any, ndof: int) -> Any:
    """Validate a DOF weighting given as a diagonal vector or a full matrix.

    SciPy sparse weighting matrices are accepted and never densified.
    """
    if weights is None:
        return None
    if not isinstance(weights, np.ndarray) and getattr(weights, "ndim", None) == 2:
        if tuple(weights.shape) != (ndof, ndof):
            raise ValueError(f"weight matrix {tuple(weights.shape)} does not match {ndof} DOFs")
        return weights
    w = np.asarray(weights)
    if not np.issubdtype(w.dtype, np.number):
        raise ValueError("weights must be numeric")
    if w.ndim == 1:
        if w.size != ndof:
            raise ValueError(f"weights has {w.size} entries but the shapes have {ndof} DOFs")
        if np.any(w < 0.0):
            raise ValueError("diagonal DOF weights must be non-negative")
        return w.astype(np.float64, copy=False)
    if w.ndim == 2:
        if w.shape != (ndof, ndof):
            raise ValueError(f"weight matrix {w.shape} does not match {ndof} DOFs")
        return w
    raise ValueError("weights must be 1-D (diagonal) or 2-D (full weighting matrix)")


def apply_weights(weights: Any, shapes: np.ndarray) -> np.ndarray:
    """Return ``W @ shapes`` for a diagonal, full, or absent weighting."""
    if weights is None:
        return shapes
    if getattr(weights, "ndim", 2) == 1:
        return weights[:, None] * shapes
    return np.asarray(weights @ shapes)


def mac(
    shapes_a: Shapes,
    shapes_b: Shapes,
    weights: Any = None,
) -> npt.NDArray[np.float64]:
    """Modal Assurance Criterion matrix between two mode-shape sets.

    ``MAC[i, j] = |φ_aᵢᴴ W φ_bⱼ|² / ((φ_aᵢᴴ W φ_aᵢ)(φ_bⱼᴴ W φ_bⱼ))``

    Parameters
    ----------
    shapes_a, shapes_b:
        Shape matrices ``(ndof, ma)`` and ``(ndof, mb)`` on a **common** DOF
        set (real or complex). 1-D inputs are treated as single modes.
    weights:
        Optional DOF weighting ``W`` (diagonal vector or full matrix). With
        ``W = M`` and mass-normalized shapes the diagonal is 1 and the
        off-diagonal terms are the orthogonality defects.

    Returns
    -------
    Real matrix ``(ma, mb)`` with values in ``[0, 1]``; invariant to scaling
    and sign/phase of either set.
    """
    a = as_columns(shapes_a, "shapes_a")
    b = as_columns(shapes_b, "shapes_b")
    if a.shape[0] != b.shape[0]:
        raise ValueError(f"DOF mismatch: {a.shape[0]} vs {b.shape[0]}")
    w = prepare_weights(weights, a.shape[0])
    wa = apply_weights(w, a)
    wb = apply_weights(w, b)

    cross = a.conj().T @ wb                                     # (ma, mb)
    norm_a = np.einsum("ij,ij->j", a.conj(), wa).real           # (ma,)
    norm_b = np.einsum("ij,ij->j", b.conj(), wb).real           # (mb,)
    denom = np.outer(norm_a, norm_b)
    values = np.zeros_like(denom, dtype=np.float64)
    valid = denom > 0.0
    values[valid] = np.abs(cross[valid]) ** 2 / denom[valid]
    return np.clip(values, 0.0, 1.0)


def mac_value(phi_a: Shapes, phi_b: Shapes, weights: Any = None) -> float:
    """MAC of a single mode pair as a scalar (see :func:`mac`)."""
    a = np.asarray(phi_a).ravel()
    b = np.asarray(phi_b).ravel()
    if a.size != b.size:
        raise ValueError(f"DOF mismatch: {a.size} vs {b.size}")
    return float(mac(a, b, weights)[0, 0])


def automac(shapes: Shapes, weights: Any = None) -> npt.NDArray[np.float64]:
    """AutoMAC of one shape set: ``mac(shapes, shapes)``.

    Off-diagonal terms near 1 flag spatial aliasing — the sensor set cannot
    distinguish those modes (pretest quality check).
    """
    return mac(shapes, shapes, weights)


# Compatibility spellings retained for the original public API.
auto_mac = automac
mac_matrix = mac


def orthogonality(
    shapes_a: Shapes,
    shapes_b: Shapes,
    mass: Any,
) -> npt.NDArray[np.float64]:
    """Pseudo-orthogonality check ``POC = Φ_aᴴ M Φ_b`` (MS-2.2).

    Complementary to the MAC: it uses the mass distribution rather than pure
    shape collinearity, so for two mass-normalized, perfectly correlated sets
    the result is the identity matrix. Unlike the MAC it is *not* invariant to
    scaling — that is the point, it also checks the normalization.
    """
    a = as_columns(shapes_a, "shapes_a")
    b = as_columns(shapes_b, "shapes_b")
    if a.shape[0] != b.shape[0]:
        raise ValueError(f"DOF mismatch: {a.shape[0]} vs {b.shape[0]}")
    m = prepare_weights(mass, a.shape[0])
    if m is None:
        raise ValueError("orthogonality requires a mass (or weighting) matrix")
    return np.real(a.conj().T @ apply_weights(m, b)).astype(np.float64)


def modal_scale_factor(phi_reference: Shapes, phi_other: Shapes) -> float | complex:
    """Factor bringing ``phi_other`` onto the scale (and sign) of the reference.

    ``MSF = (φ_otherᴴ φ_ref) / (φ_otherᴴ φ_other)``, so ``MSF · φ_other`` is
    directly comparable to ``φ_ref`` component by component. Returns 0.0 for a
    null ``phi_other``.
    """
    ref = np.asarray(phi_reference).ravel()
    other = np.asarray(phi_other).ravel()
    if ref.size != other.size:
        raise ValueError(f"DOF mismatch: {ref.size} vs {other.size}")
    denominator = np.vdot(other, other)
    if abs(denominator) <= 0.0:
        return 0.0
    factor = np.vdot(other, ref) / denominator
    if np.isrealobj(ref) and np.isrealobj(other):
        return float(np.real(factor))
    return complex(factor)


def comac(
    shapes_a: Shapes,
    shapes_b: Shapes,
    pairing: ModePairing | None = None,
) -> npt.NDArray[np.float64]:
    """Coordinate MAC: per-DOF correlation across *paired* mode sets (MS-2.5).

    ``COMAC(d) = (Σ_i |φ_a,i(d) φ_b,i(d)|)² / (Σ_i |φ_a,i(d)|² · Σ_i |φ_b,i(d)|²)``

    Each pair is scaled by its modal scale factor first, so mode sets with
    arbitrary and mode-dependent normalization contribute consistently.

    Parameters
    ----------
    shapes_a, shapes_b:
        Shape matrices on a common DOF set. Without ``pairing`` they must have
        equal shape and their columns are taken as already paired.
    pairing:
        Optional :class:`~openfemlab.correlation.pairing.ModePairing`; only its
        pairs are accumulated, which is what a real test/FE comparison needs
        when the mode orders differ. ``shapes_a`` is then the test set and
        ``shapes_b`` the FE set, matching the pairing's index convention.

    Returns
    -------
    ``(ndof,)`` values in ``[0, 1]``; low values localize the DOFs responsible
    for poor correlation (sensor fault or local model error).
    """
    a = as_columns(shapes_a, "shapes_a")
    b = as_columns(shapes_b, "shapes_b")
    if a.shape[0] != b.shape[0]:
        raise ValueError(f"DOF mismatch: {a.shape[0]} vs {b.shape[0]}")
    if pairing is None:
        if a.shape != b.shape:
            raise ValueError("COMAC requires equal-shape, column-paired sets")
        columns = [(i, i) for i in range(a.shape[1])]
    else:
        columns = [(pair.test_index, pair.fe_index) for pair in pairing.pairs]
    if not columns:
        return np.zeros(a.shape[0], dtype=np.float64)

    numerator = np.zeros(a.shape[0], dtype=np.float64)
    sum_a = np.zeros(a.shape[0], dtype=np.float64)
    sum_b = np.zeros(a.shape[0], dtype=np.float64)
    for i, j in columns:
        phi_a = a[:, i]
        phi_b = b[:, j] * modal_scale_factor(phi_a, b[:, j])
        numerator += np.abs(phi_a * np.conj(phi_b))
        sum_a += np.abs(phi_a) ** 2
        sum_b += np.abs(phi_b) ** 2

    denominator = sum_a * sum_b
    out = np.zeros(a.shape[0], dtype=np.float64)
    nonzero = denominator > 0.0
    out[nonzero] = numerator[nonzero] ** 2 / denominator[nonzero]
    return np.clip(out, 0.0, 1.0)
