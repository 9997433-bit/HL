"""FRF residual provider for the updating loop — spec anchors MS-3.2, MS-7.3.

The deterministic loop of :mod:`openfemlab.updating.updater` minimises modal
residuals: relative frequency errors and ``1 - sqrt(MAC)``. That needs an
extracted mode table, which is one modal-parameter estimation step away from
what a shaker test actually records. This module closes the remaining gap by
fitting the model directly to a **measured frequency response function**::

    r(omega_l; theta) = W_l [ H_synth(omega_l; theta) - H_meas(omega_l) ]

stacked as ``[Re r, Im r]`` over the selected frequency lines and the measured
response/excitation channels.

Why real/imag and not log-magnitude
-----------------------------------
Both stackings appear in the literature. Real/imaginary parts are used here
because they keep the residual an *analytic* function of the parameters — the
Jacobian below is exact — and because they retain phase, which is what
distinguishes a stiffness error from a damping error near a resonance. A
log-magnitude residual throws the phase away and is not differentiable at the
antiresonances, where ``|H|`` passes through zero. The price of real/imag is
dynamic range: the residual is dominated by the resonance peaks unless it is
weighted, which is what ``weighting="magnitude"`` (the default) is for.

Sensitivities
-------------
The dynamic stiffness ``Z(omega; theta) = K(theta) - omega^2 M(theta)
+ i omega C(theta)`` is affine in the scaling factors, and differentiating
``H = Z^-1`` gives the exact derivative

    dH/dtheta_j = -H (dK/dtheta_j - omega^2 dM/dtheta_j
                      + i omega dC/dtheta_j) H

so an iteration costs one factorization per frequency line rather than one per
line *per parameter*. The provider reuses the ``dK/dtheta``/``dM/dtheta``
matrices a :class:`~openfemlab.updating.scaling_model.ScalingModel` already
exposes, and the direct dynamic-stiffness inversion of
:func:`~openfemlab.solver.dynamics.direct_frf`, so neither the FRF kernel nor
the derivative matrices exist twice.

Limitations
-----------
The frequency-line subset is the caller's choice: ``lines=`` selects it and
``weighting=`` rescales it, but nothing here *picks* the lines for you. An
off-resonance-only selection, a damping floor, or a coherence-driven weighting
would all be built on top of this seam rather than inside it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields
from typing import Any

import numpy as np
import scipy.sparse as sp

from ..correlation.frf import FRFCorrelation, frf_correlation
from ..correlation.summary import CorrelationSummary
from ..solver.dynamics import (
    RESPONSE_TYPES,
    FrequencyResponse,
    RayleighDamping,
    damping_matrix,
    direct_frf,
)
from .parameters import ParameterSet, UpdatableParameter
from .sensitivity import ModalData
from .updater import ModelUpdater, UpdatingResult

__all__ = [
    "FRF_WEIGHTINGS",
    "FRFResidual",
    "FRFState",
    "FRFUpdater",
    "FRFUpdatingResult",
    "update_model_frf",
]

#: How the complex residual is rescaled before the real/imaginary split.
#:
#: ``"magnitude"`` divides every entry by ``|H_meas|`` (floored, see
#: ``magnitude_floor``), which turns the residual into a *relative* error and
#: gives every frequency line the same say in the fit — the right choice for
#: multiplicative measurement noise. ``"unit"`` keeps the raw complex
#: difference, normalised only by the overall RMS level so the cost stays
#: dimensionless; the resonance peaks then dominate the fit.
FRF_WEIGHTINGS = ("magnitude", "unit")


@dataclass
class FRFState(ModalData):
    """One FRF model evaluation: what the updater's ``model`` callable returns.

    It *is* a :class:`~openfemlab.updating.sensitivity.ModalData` — with no
    modal content — so the shared loop, its result object and the σ_post
    plumbing carry it unchanged. ``columns`` caches the receptance columns the
    synthesis already solved for, which is exactly what the analytic
    ``dH/dtheta`` needs, so the Jacobian costs no extra factorization.
    """

    response: FrequencyResponse | None = None
    columns: np.ndarray | None = None
    values: dict[str, float] = field(default_factory=dict)

    @property
    def block(self) -> np.ndarray:
        """``(n_lines, n_response, n_excitation)`` synthesized FRF block."""
        if self.response is None:  # pragma: no cover - constructed with one
            raise ValueError("this state carries no synthesized FRF")
        return self.response.data


class FRFResidual:
    """Measured-versus-synthesized FRF residual and its analytic Jacobian.

    Parameters
    ----------
    model:
        Anything exposing the affine parameterisation contract of
        :class:`~openfemlab.updating.scaling_model.ScalingModel`:
        ``assemble(values) -> (K, M)``, ``derivatives(names) -> (dK, dM)``
        and ``parameter_names``.
    measured:
        The measured :class:`~openfemlab.solver.dynamics.FrequencyResponse`.
        Its frequency line, response/excitation DOFs and response type define
        what the model is asked to reproduce.
    damping:
        Damping of the *synthesized* model: a
        :class:`~openfemlab.solver.dynamics.DampingModel` or an explicit ``C``.
        A :class:`~openfemlab.solver.dynamics.RayleighDamping` model follows
        the parameters (``dC/dtheta = alpha dM/dtheta + beta dK/dtheta``); any
        other model or an explicit matrix is treated as parameter independent.
    damping_parts:
        ``{parameter name: C_j}`` making damping updatable the same way
        stiffness is: ``C(theta) += sum_j theta_j C_j`` with
        ``dC/dtheta_j = C_j``.
    free_dofs:
        DOF partition the dynamic stiffness is inverted on; ``None`` uses all.
    lines:
        Indices of the ``measured`` frequency lines to fit. ``None`` fits all
        of them. Holding lines back here is how a run gets an independent set
        to validate on.
    weighting, magnitude_floor:
        See :data:`FRF_WEIGHTINGS`. ``magnitude_floor`` is relative to the
        largest measured magnitude and caps how far the ``"magnitude"``
        weighting may amplify an antiresonance.
    weights:
        Optional extra weights broadcast onto the ``(n_lines, n_response,
        n_excitation)`` block, applied on top of the weighting above.
    """

    def __init__(
        self,
        model: Any,
        measured: FrequencyResponse,
        *,
        damping: Any = None,
        damping_parts: Mapping[str, Any] | None = None,
        free_dofs: Sequence[int] | np.ndarray | None = None,
        lines: Sequence[int] | np.ndarray | None = None,
        weighting: str = "magnitude",
        magnitude_floor: float = 1.0e-3,
        weights: np.ndarray | None = None,
    ) -> None:
        if not isinstance(measured, FrequencyResponse):
            raise TypeError("measured must be a FrequencyResponse")
        if weighting not in FRF_WEIGHTINGS:
            raise ValueError(
                f"unknown FRF weighting {weighting!r}; expected one of {FRF_WEIGHTINGS}"
            )
        if not 0.0 < magnitude_floor <= 1.0:
            raise ValueError("magnitude_floor must lie in (0, 1]")

        self.model = model
        self.measured = measured
        self.damping = damping
        self.damping_parts = dict(damping_parts or {})
        self.free_dofs = None if free_dofs is None else np.asarray(free_dofs, dtype=int)
        self.weighting = weighting
        self.magnitude_floor = float(magnitude_floor)

        self.lines = (
            np.arange(measured.num_frequencies)
            if lines is None
            else np.asarray(lines, dtype=int).ravel()
        )
        if self.lines.size == 0:
            raise ValueError("at least one frequency line is required")
        if self.lines.min() < 0 or self.lines.max() >= measured.num_frequencies:
            raise ValueError("lines references a frequency outside the measured line")

        self.frequencies = measured.frequencies[self.lines]
        self.measured_block = measured.data[self.lines]
        self.response_dofs = measured.response_dofs
        self.excitation_dofs = measured.excitation_dofs
        self.response_type = measured.response_type

        # One receptance solve per line covers both the synthesis and the
        # derivative, so both DOF sets are driven at once.
        self._columns = np.unique(np.concatenate((self.response_dofs, self.excitation_dofs)))
        self._response_columns = np.searchsorted(self._columns, self.response_dofs)
        self._excitation_columns = np.searchsorted(self._columns, self.excitation_dofs)
        # RESPONSE_TYPES is ordered by differentiation order with respect to
        # i*omega, so its index is the exponent taking a receptance to it.
        self._response_order = RESPONSE_TYPES.index(self.response_type)
        self.weights = self._build_weights(weights)

    # ------------------------------------------------------------------ shape

    @property
    def n_lines(self) -> int:
        return int(self.lines.size)

    @property
    def n_channels(self) -> int:
        """Response/excitation pairs, i.e. FRFs compared at every line."""
        return int(self.response_dofs.size * self.excitation_dofs.size)

    @property
    def n_residuals(self) -> int:
        """Rows the stacked real/imaginary residual contributes."""
        return 2 * self.n_lines * self.n_channels

    def _build_weights(self, extra: np.ndarray | None) -> np.ndarray:
        magnitude = np.abs(self.measured_block)
        peak = float(magnitude.max()) if magnitude.size else 0.0
        if peak <= 0.0:
            raise ValueError("the measured FRF is identically zero")
        if self.weighting == "magnitude":
            weights = 1.0 / np.maximum(magnitude, self.magnitude_floor * peak)
        else:
            weights = np.full(magnitude.shape, 1.0 / np.sqrt(np.mean(magnitude**2)))
        if extra is not None:
            weights = weights * np.asarray(extra, dtype=float)
        return np.asarray(weights, dtype=float)

    # --------------------------------------------------------------- assembly

    def matrices(self, values: Mapping[str, float]) -> tuple[Any, Any, Any]:
        """``(K, M, C)`` of the parameterised model at ``values``."""
        K, M = self.model.assemble(values)
        K, M = _operator(K), _operator(M)
        return K, M, self._damping(values, K, M)

    def _damping(self, values: Mapping[str, float], K: Any, M: Any) -> Any:
        total = damping_matrix(self.damping, K, M)
        for name, part in self.damping_parts.items():
            contribution = float(values[name]) * _operator(part)
            total = contribution if total is None else total + contribution
        return None if total is None else _operator(total)

    def _model_derivatives(
        self, names: Sequence[str]
    ) -> tuple[list[Any | None], list[Any | None]]:
        """``(dK/dtheta, dM/dtheta)`` per name, ``None`` for damping-only names.

        A parameter that only enters through ``damping_parts`` is unknown to
        the stiffness/mass parameterisation, so it is not asked about.
        """
        known = set(getattr(self.model, "parameter_names", names))
        requested = [name for name in names if name in known]
        stiffness, mass = self.model.derivatives(requested)
        lookup = dict(zip(requested, zip(stiffness, mass, strict=True), strict=True))
        pairs = [lookup.get(name, (None, None)) for name in names]
        return [pair[0] for pair in pairs], [pair[1] for pair in pairs]

    def _damping_derivatives(
        self,
        names: Sequence[str],
        stiffness: Sequence[Any | None],
        mass: Sequence[Any | None],
    ) -> list[Any | None]:
        """``dC/dtheta`` per parameter, ``None`` where damping does not move."""
        rayleigh = self.damping if isinstance(self.damping, RayleighDamping) else None
        out: list[Any | None] = []
        for name, dK, dM in zip(names, stiffness, mass, strict=True):
            derivative = None
            if rayleigh is not None:
                if dM is not None and rayleigh.alpha != 0.0:
                    derivative = rayleigh.alpha * _operator(dM)
                if dK is not None and rayleigh.beta != 0.0:
                    term = rayleigh.beta * _operator(dK)
                    derivative = term if derivative is None else derivative + term
            part = self.damping_parts.get(name)
            if part is not None:
                term = _operator(part)
                derivative = term if derivative is None else derivative + term
            out.append(derivative)
        return out

    # -------------------------------------------------------------- synthesis

    def _receptance_columns(
        self, values: Mapping[str, float], frequencies: np.ndarray
    ) -> np.ndarray:
        """``Z(omega)^-1`` columns at the driven DOFs, ``(n_lines, n_dof, n_columns)``."""
        K, M, C = self.matrices(values)
        response = direct_frf(
            frequencies,
            K,
            M,
            C,
            free_dofs=self.free_dofs,
            excitation_dofs=self._columns,
            response_type="receptance",
        )
        return response.data

    def _response_factor(self, frequencies: np.ndarray) -> np.ndarray:
        if self._response_order == 0:
            return np.ones(frequencies.size, dtype=complex)
        return (2.0j * np.pi * frequencies) ** self._response_order

    def transfer(
        self, values: Mapping[str, float], frequencies: np.ndarray | None = None
    ) -> FrequencyResponse:
        """Synthesize the measured channels at ``frequencies`` (default: the fitted lines)."""
        line = self.frequencies if frequencies is None else np.atleast_1d(
            np.asarray(frequencies, dtype=float)
        )
        columns = self._receptance_columns(values, line)
        return self._assemble_response(columns, line)

    def _assemble_response(
        self, columns: np.ndarray, frequencies: np.ndarray
    ) -> FrequencyResponse:
        block = columns[:, self.response_dofs, :][:, :, self._excitation_columns]
        block = block * self._response_factor(frequencies)[:, None, None]
        return FrequencyResponse(
            frequencies, block, self.response_dofs, self.excitation_dofs, self.response_type
        )

    def state(self, values: Mapping[str, float]) -> FRFState:
        """The model evaluation the updating loop consumes."""
        columns = self._receptance_columns(values, self.frequencies)
        return FRFState(
            frequencies=np.empty(0),
            mode_shapes=None,
            response=self._assemble_response(columns, self.frequencies),
            columns=columns,
            values=dict(values),
        )

    __call__ = state

    # --------------------------------------------------------------- residual

    def residual(self, state: FRFState) -> np.ndarray:
        """``[Re, Im]`` of the weighted complex misfit, flattened."""
        difference = (state.block - self.measured_block) * self.weights
        return np.concatenate((difference.real.ravel(), difference.imag.ravel()))

    def jacobian(
        self,
        values: Mapping[str, float],
        names: Sequence[str],
        state: FRFState | None = None,
    ) -> np.ndarray:
        """Analytic ``dr/dtheta`` — ``(n_residuals, len(names))``.

        ``-H (dK - omega^2 dM + i omega dC) H`` evaluated on the driven columns
        of ``Z^-1``. Reuses ``state.columns`` when the state was produced at
        the same point, so the whole Jacobian is free of extra factorizations.
        """
        selected = list(names)
        columns = (
            state.columns
            if state is not None and state.columns is not None
            else self._receptance_columns(values, self.frequencies)
        )
        stiffness, mass = self._model_derivatives(selected)
        damping = self._damping_derivatives(selected, stiffness, mass)

        omega = 2.0 * np.pi * self.frequencies
        factor = self._response_factor(self.frequencies)[:, None, None] * self.weights
        derivative = np.zeros(
            (self.n_lines, self.response_dofs.size, self.excitation_dofs.size, len(selected)),
            dtype=complex,
        )
        for index in range(len(selected)):
            dK, dM, dC = stiffness[index], mass[index], damping[index]
            if dK is None and dM is None and dC is None:
                continue
            for line in range(self.n_lines):
                dZ = _dynamic_stiffness_derivative(dK, dM, dC, omega[line])
                left = columns[line][:, self._response_columns]
                right = columns[line][:, self._excitation_columns]
                derivative[line, :, :, index] = -(left.T @ (dZ @ right))
        derivative *= factor[:, :, :, None]

        rows = derivative.reshape(-1, len(selected))
        return np.vstack((rows.real, rows.imag))

    # ------------------------------------------------------------ correlation

    def correlation(self, state: FRFState) -> FRFCorrelation:
        """FRAC/FDAC of the synthesized block against the measurement (MS-7.4)."""
        return self.correlate(state.block)

    def correlate(self, block: np.ndarray, measured: np.ndarray | None = None) -> FRFCorrelation:
        """FRAC/FDAC of any block shaped like the fitted one."""
        reference = self.measured_block if measured is None else np.asarray(measured)
        return frf_correlation(
            _flatten_channels(reference),
            _flatten_channels(np.asarray(block)),
            frequencies=self.frequencies,
            channels=self.channel_labels,
            response_type=self.response_type,
        )

    @property
    def channel_labels(self) -> tuple[str, ...]:
        """``"dof <out>/<in>"`` label per response/excitation pair."""
        return tuple(
            f"dof {int(out)}/{int(inp)}"
            for out in self.response_dofs
            for inp in self.excitation_dofs
        )


@dataclass
class FRFUpdatingResult(UpdatingResult):
    """:class:`~openfemlab.updating.updater.UpdatingResult` plus the FRF blocks.

    ``initial_correlation`` / ``final_correlation`` stay empty: an FRF run has
    no measured mode table to correlate against, and inventing one would make
    the modal gates of MS-4.2 report on data nobody supplied. The FRAC/FDAC
    blocks below are the correlation an FRF run does have.
    """

    initial_frf_correlation: FRFCorrelation | None = None
    final_frf_correlation: FRFCorrelation | None = None

    def report(self) -> str:
        base = super().report()
        if self.final_frf_correlation is None:  # pragma: no cover - always set by run()
            return base
        return f"{base}\n\n{self.final_frf_correlation.report()}"


class FRFUpdater(ModelUpdater):
    """The MS-3.4 loop driven by an :class:`FRFResidual` instead of mode data.

    Only the residual and its Jacobian change: the Levenberg-Marquardt
    estimator, the line search, the bound projection, the divergence guard and
    the σ_post extractor are the inherited ones, so an FRF run reports through
    the same vocabulary as a modal run.

    Parameters
    ----------
    residual:
        The :class:`FRFResidual` provider. It doubles as the model callable —
        the loop evaluates it to get an :class:`FRFState`.
    parameters:
        The updating parameters, as for
        :class:`~openfemlab.updating.updater.ModelUpdater`.
    analytic_jacobian:
        ``True`` (default) uses the exact ``dH/dtheta``; ``False`` falls back
        to central finite differences of the whole residual vector, which is
        the route for a model without derivative matrices.
    """

    #: An FRF run has no measured mode table, so the base class must not insist.
    requires_modal_targets = False

    def __init__(
        self,
        residual: FRFResidual,
        parameters: ParameterSet | Sequence[UpdatableParameter],
        *,
        analytic_jacobian: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(residual, parameters, None, None, **kwargs)
        self.frf = residual
        self.analytic_jacobian = bool(analytic_jacobian)

    # ------------------------------------------------------------------
    # residual assembly
    # ------------------------------------------------------------------
    def pair(self, data: ModalData) -> list[tuple[int, int]]:
        """Identity matching of the measured and synthesized frequency lines.

        The FRF residual needs no mode pairing — both sides are sampled on the
        same frequency line — but the loop treats an empty pairing as "this
        trial point produced nothing comparable", so the line matching takes
        that slot.
        """
        return [(index, index) for index in range(self.frf.n_lines)]

    def residual(self, data: ModalData, pairs: list[tuple[int, int]]) -> np.ndarray:
        if not pairs:  # pragma: no cover - pair() never returns an empty list
            raise ValueError("no matched frequency lines; cannot form a residual")
        if not isinstance(data, FRFState):
            raise TypeError("the FRF updater needs an FRFState from its residual provider")
        return self.frf.residual(data)

    def jacobian(
        self,
        design_values: np.ndarray,
        pairs: list[tuple[int, int]],
        baseline_residual: np.ndarray,
        baseline_data: ModalData,
    ) -> np.ndarray:
        if not self.analytic_jacobian:
            return super().jacobian(design_values, pairs, baseline_residual, baseline_data)
        physical = self.parameters.design_to_physical(design_values)
        free = self.parameters.free
        state = baseline_data if isinstance(baseline_data, FRFState) else None
        matrix = self.frf.jacobian(physical, [p.name for p in free], state)
        # Chain rule for log-scaled design variables: dr/dx = dr/dp * p.
        chain = np.array(
            [physical[p.name] if p.log_scaled else 1.0 for p in free], dtype=float
        )
        return matrix * chain[None, :]

    def correlation(self, data: ModalData) -> CorrelationSummary:
        """An empty modal summary — see :class:`FRFUpdatingResult`."""
        return _empty_correlation()

    # ------------------------------------------------------------------
    # run
    # ------------------------------------------------------------------
    def run(self) -> FRFUpdatingResult:
        """Run the loop and attach the FRAC/FDAC blocks before and after."""
        initial = self.frf.correlation(self.frf.state(self.parameters.as_dict()))
        result = super().run()
        final = None
        if isinstance(result.modal_data, FRFState):
            final = self.frf.correlation(result.modal_data)
        payload = {f.name: getattr(result, f.name) for f in fields(UpdatingResult)}
        return FRFUpdatingResult(
            **payload, initial_frf_correlation=initial, final_frf_correlation=final
        )


def update_model_frf(
    residual: FRFResidual,
    parameters: ParameterSet | Sequence[UpdatableParameter],
    **kwargs: Any,
) -> FRFUpdatingResult:
    """Convenience wrapper: build an :class:`FRFUpdater` and run it."""
    return FRFUpdater(residual, parameters, **kwargs).run()


# ==================================================================== helpers


def _operator(matrix: Any) -> Any:
    """Keep sparse inputs sparse, and normalise everything else to an ndarray.

    Mixing a SciPy sparse matrix with a dense one yields ``numpy.matrix``,
    whose ``@`` semantics differ; this is the one place that has to care.
    """
    if sp.issparse(matrix):
        return matrix
    return np.asarray(matrix)


def _dynamic_stiffness_derivative(dK: Any, dM: Any, dC: Any, omega: float) -> Any:
    """``dZ/dtheta = dK/dtheta - omega^2 dM/dtheta + i omega dC/dtheta``."""
    total: Any = None
    if dK is not None:
        total = _operator(dK).astype(complex)
    if dM is not None:
        term = -(omega**2) * _operator(dM).astype(complex)
        total = term if total is None else total + term
    if dC is not None:
        term = 1j * omega * _operator(dC).astype(complex)
        total = term if total is None else total + term
    return total


def _flatten_channels(block: np.ndarray) -> np.ndarray:
    """``(n_lines, n_out, n_in)`` -> ``(n_lines, n_out * n_in)`` for the M2 kernel."""
    array = np.asarray(block)
    return array.reshape(array.shape[0], -1)


def _empty_correlation() -> CorrelationSummary:
    """The "no modal targets were supplied" summary."""
    return CorrelationSummary(
        n_test_modes=0,
        n_fe_modes=0,
        n_paired=0,
        mean_mac=0.0,
        min_mac=0.0,
        max_mac=0.0,
        mean_abs_freq_error_pct=0.0,
        max_abs_freq_error_pct=0.0,
        rms_freq_error_pct=0.0,
        mean_signed_freq_error_pct=0.0,
        max_off_diagonal_mac=0.0,
    )
