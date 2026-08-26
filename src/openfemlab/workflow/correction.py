"""The six-stage simulation-correction workflow (MS-4).

``S1 BASELINE -> S2 PAIRING -> S3 DIAGNOSIS -> S4 UPDATING -> S5 REANALYSIS ->
S6 VALIDATION`` is the loop a user actually runs; the modal solver, the
correlation metrics and the updating engine are its engines.  Orchestrating
them here — rather than leaving it to a script per project — is what makes a
correction auditable: every stage has a gate, a failed gate halts the pipeline
with a machine-readable reason, and the whole run condenses into one
schema-versioned :class:`~openfemlab.workflow.report.CorrectionReport`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from ..correlation.report import CorrelationReport, correlation_report
from ..updating.parameters import Parameter, ParameterSet, UpdatableParameter
from ..updating.sensitivity import ModalData, as_modal_data, modal_sensitivity
from ..updating.updater import ModelUpdater, UpdatingOptions, UpdatingResult
from .gates import GateResult, HoldoutSpec, ValidationGates, evaluate_gates
from .report import CorrectionReport, ParameterEntry, environment_block
from .selection import ParameterSelection, select_parameters
from .sensors import SensorMap
from .stages import (
    Stage,
    StageGateError,
    StageStatus,
    StageTimer,
)

__all__ = ["CorrectionWorkflow", "run_correction"]

ParameterInput = ParameterSet | Sequence[UpdatableParameter | Parameter]


def _as_parameter_set(params: ParameterInput) -> ParameterSet:
    """Own a private, mutable copy so a run never mutates the caller's objects."""
    if isinstance(params, ParameterSet):
        return params.copy()
    updatable = [p.to_updatable() if isinstance(p, Parameter) else p.copy() for p in params]
    return ParameterSet(updatable)


class _SensorModel:
    """The user model with its shapes reduced onto the sensor channels."""

    def __init__(self, model: Any, sensor_map: SensorMap | None) -> None:
        self._model = model
        self._sensor_map = sensor_map
        self.n_evaluations = 0

    def __call__(self, values: Mapping[str, float]) -> ModalData:
        self.n_evaluations += 1
        data = as_modal_data(self._model(values))
        if self._sensor_map is None or data.mode_shapes is None:
            return data
        return ModalData(data.frequencies, self._sensor_map.reduce(data.mode_shapes))


def _posterior_sigma(result: UpdatingResult) -> dict[str, float]:
    """Linearized least-squares standard deviations of the updated parameters.

    ``C_post ≈ σ² (JᵀJ)⁻¹`` with ``σ²`` estimated from the final residual.  It
    is the Gauss-Newton counterpart of the MS-3.5 posterior covariance, so a
    deterministic run still reports parameter uncertainty.
    """
    sensitivity = result.sensitivity
    if sensitivity is None or sensitivity.matrix.size == 0:
        return {}
    jacobian = np.asarray(sensitivity.matrix, dtype=float)
    n_residuals, n_parameters = jacobian.shape
    dof = max(n_residuals - n_parameters, 1)
    variance = 2.0 * result.final_cost / dof
    covariance = np.linalg.pinv(jacobian.T @ jacobian) * variance
    diagonal = np.clip(np.diag(covariance), 0.0, None)
    return {
        name: float(np.sqrt(value))
        for name, value in zip(sensitivity.parameter_names, diagonal, strict=False)
    }


class CorrectionWorkflow:
    """Stateful driver of the ``S1..S6`` correction pipeline.

    Parameters
    ----------
    model:
        Callable mapping ``{parameter name: value}`` to modal data — anything
        :func:`~openfemlab.updating.sensitivity.as_modal_data` understands, so
        the internal solver and an external one are equally acceptable.
    test:
        Measured mode set: frequencies in Hz and, normally, mode shapes on the
        sensor channels.
    sensor_map:
        Reduction from analysis DOFs to test channels.  ``None`` means the
        model already reports shapes on the channel set.
    params:
        Updating parameters.  The workflow works on a private copy.
    gates:
        S6 acceptance limits, see :class:`~openfemlab.workflow.gates.ValidationGates`.
    holdout:
        Targets reserved from S4 and checked at S6.
    channel_weights:
        Optional per-channel measurement weighting for every MAC in the run.
    updating_options:
        Numerical settings forwarded to
        :class:`~openfemlab.updating.updater.ModelUpdater`.
    strict:
        Raise :class:`~openfemlab.workflow.stages.StageGateError` on a failed
        gate instead of returning a report marked ``FAIL``.
    """

    def __init__(
        self,
        model: Any,
        test: Any,
        sensor_map: SensorMap | None = None,
        params: ParameterInput | None = None,
        *,
        gates: ValidationGates | None = None,
        holdout: HoldoutSpec | None = None,
        channel_weights: Sequence[float] | np.ndarray | None = None,
        updating_options: UpdatingOptions | None = None,
        collinearity_threshold: float = 0.99,
        low_sensitivity_ratio: float = 1.0e-3,
        max_condition: float = 1.0e6,
        pairing_method: str = "optimal",
        freq_penalty: float = 0.1,
        seed: int = 0,
        strict: bool = False,
    ) -> None:
        if params is None:
            raise ValueError("at least one updating parameter is required")
        self.model = _SensorModel(model, sensor_map)
        self.test = as_modal_data(test)
        if self.test.n_modes == 0:
            raise ValueError("the test mode set is empty")
        self.sensor_map = sensor_map
        self.parameters = _as_parameter_set(params)
        self.gates = gates or ValidationGates()
        self.holdout = holdout or HoldoutSpec()
        self.channel_weights = (
            None if channel_weights is None else np.asarray(channel_weights, dtype=float)
        )
        self.updating_options = updating_options
        self.collinearity_threshold = collinearity_threshold
        self.low_sensitivity_ratio = low_sensitivity_ratio
        self.max_condition = max_condition
        self.pairing_method = pairing_method
        self.freq_penalty = freq_penalty
        self.seed = int(seed)
        self.strict = strict

        self._timer = StageTimer()
        self._baseline: ModalData | None = None
        self._final: ModalData | None = None
        self._baseline_correlation: CorrelationReport | None = None
        self._final_correlation: CorrelationReport | None = None
        self._holdout_modes: tuple[int, ...] = ()
        self._selection: ParameterSelection | None = None
        self._updating: UpdatingResult | None = None
        self._gate_results: list[GateResult] = []

    # ------------------------------------------------------------- utilities

    @property
    def n_model_evaluations(self) -> int:
        return self.model.n_evaluations

    def _weights(self, *, exclude_channels: bool) -> np.ndarray | None:
        """Per-channel MAC weights, optionally zeroing the held-out channels."""
        if self.test.mode_shapes is not None:
            n_channels = int(self.test.mode_shapes.shape[0])
        elif self.sensor_map is not None:
            n_channels = self.sensor_map.n_channels
        else:
            return None

        drop = exclude_channels and bool(self.holdout.channels)
        if self.channel_weights is None and not drop:
            return None

        weights = (
            np.ones(n_channels) if self.channel_weights is None else self.channel_weights.copy()
        )
        if weights.size != n_channels:
            raise ValueError(
                f"channel_weights has {weights.size} entries but the test set has "
                f"{n_channels} channels"
            )
        if drop:
            invalid = [c for c in self.holdout.channels if c >= n_channels]
            if invalid:
                raise ValueError(f"held-out channels out of range: {invalid}")
            weights[list(self.holdout.channels)] = 0.0
        return weights

    def _correlate(
        self,
        test: ModalData,
        analysis: ModalData,
        *,
        weights: np.ndarray | None = None,
        meta: dict[str, Any] | None = None,
    ) -> CorrelationReport:
        return correlation_report(
            test_frequencies=test.frequencies,
            fe_frequencies=analysis.frequencies,
            test_shapes=test.mode_shapes,
            fe_shapes=analysis.mode_shapes,
            dof_labels=None if self.sensor_map is None else self.sensor_map.channel_labels(),
            weights=weights,
            method=self.pairing_method,
            mac_threshold=self.gates.pairing_mac_min,
            freq_penalty=self.freq_penalty,
            meta=dict(meta or {}),
        )

    def _fail(self, stage: Stage, reason: str, message: str, **details: Any) -> StageGateError:
        error = StageGateError(stage, reason, message, details)
        self._timer.finish(
            StageStatus.FAILED, reason=reason, message=message, details=dict(details)
        )
        self._timer.skip_remaining(stage, reason)
        return error

    # ---------------------------------------------------------------- stages

    def _stage_baseline(self) -> None:
        self._timer.start(Stage.BASELINE)
        try:
            data = self.model(self.parameters.as_dict())
        except Exception as exc:  # noqa: BLE001 - reported as a stage failure
            raise self._fail(
                Stage.BASELINE,
                "baseline_solve_failed",
                f"the baseline modal solve raised {type(exc).__name__}: {exc}",
            ) from exc

        if data.n_modes == 0:
            raise self._fail(
                Stage.BASELINE, "no_modes", "the baseline solve returned no modes"
            )
        if not np.all(np.isfinite(data.frequencies)):
            raise self._fail(
                Stage.BASELINE,
                "non_finite_frequencies",
                "the baseline solve returned non-finite frequencies",
            )
        if data.n_modes < self.gates.min_pairs:
            raise self._fail(
                Stage.BASELINE,
                "insufficient_modes",
                f"the baseline solve returned {data.n_modes} modes, "
                f"fewer than the {self.gates.min_pairs} required pairs",
                n_modes=data.n_modes,
                min_pairs=self.gates.min_pairs,
            )

        self._baseline = data
        self._timer.finish(
            StageStatus.PASSED,
            message=f"{data.n_modes} baseline modes solved",
            details={
                "n_modes": data.n_modes,
                "frequencies_hz": [float(f) for f in data.frequencies],
            },
        )

    def _stage_pairing(self) -> None:
        self._timer.start(Stage.PAIRING)
        assert self._baseline is not None
        report = self._correlate(
            self.test,
            self._baseline,
            weights=self._weights(exclude_channels=False),
            meta={"stage": Stage.PAIRING.value},
        )
        summary = report.summary
        if summary.n_paired < self.gates.min_pairs:
            raise self._fail(
                Stage.PAIRING,
                "insufficient_pairs",
                f"{summary.n_paired} modes paired at MAC >= "
                f"{self.gates.pairing_mac_min}, fewer than the required "
                f"{self.gates.min_pairs}",
                n_paired=summary.n_paired,
                min_pairs=self.gates.min_pairs,
                mac_threshold=self.gates.pairing_mac_min,
            )

        self._baseline_correlation = report
        self._holdout_modes = self.holdout.resolve_modes(report.pairing)
        self._timer.finish(
            StageStatus.PASSED,
            message=f"{summary.n_paired} modes paired",
            details={
                "n_paired": summary.n_paired,
                "min_mac": summary.min_mac,
                "max_abs_freq_error_pct": summary.max_abs_freq_error_pct,
                "holdout_modes": list(self._holdout_modes),
            },
        )

    def _fit_indices(self) -> list[int]:
        """Test modes entering the S4 residuals (everything not held out)."""
        return [i for i in range(self.test.n_modes) if i not in set(self._holdout_modes)]

    def _initial_sensitivity(self) -> tuple[np.ndarray, list[str]]:
        """Relative sensitivity ``∂(f_a/f_e)/∂θ · θ`` of the fitted pairs."""
        assert self._baseline_correlation is not None
        free = self.parameters.free
        names = [p.name for p in free]
        theta = np.array([p.value for p in free], dtype=float)
        steps = np.array([max(p.step, 1.0e-6) for p in free], dtype=float)

        def response(values: np.ndarray) -> ModalData:
            physical = self.parameters.as_dict()
            physical.update(dict(zip(names, values.tolist(), strict=False)))
            return self.model(physical)

        result = modal_sensitivity(
            response,
            theta,
            parameter_names=names,
            steps=steps,
            scheme="central",
            baseline=self._baseline,
            relative_step=True,
        )

        held_out = set(self._holdout_modes)
        rows = []
        for pair in self._baseline_correlation.pairing.pairs:
            if pair.test_index in held_out:
                continue
            f_test = pair.test_frequency
            if not f_test:
                continue
            rows.append(result.matrix[pair.fe_index, :] * theta / f_test)
        if not rows:
            return np.zeros((0, len(names))), names
        return np.vstack(rows), names

    def _stage_diagnosis(self) -> None:
        self._timer.start(Stage.DIAGNOSIS)
        try:
            sensitivity, names = self._initial_sensitivity()
        except Exception as exc:  # noqa: BLE001 - reported as a stage failure
            raise self._fail(
                Stage.DIAGNOSIS,
                "sensitivity_failed",
                f"the initial sensitivity matrix raised {type(exc).__name__}: {exc}",
            ) from exc

        if sensitivity.shape[0] == 0:
            raise self._fail(
                Stage.DIAGNOSIS,
                "no_fitted_targets",
                "every paired mode was reserved for validation; nothing is left to fit",
                holdout_modes=list(self._holdout_modes),
            )

        selection = select_parameters(
            sensitivity,
            names,
            collinearity_threshold=self.collinearity_threshold,
            low_sensitivity_ratio=self.low_sensitivity_ratio,
            max_condition=self.max_condition,
        )
        if not selection.selected:
            raise self._fail(
                Stage.DIAGNOSIS,
                "no_identifiable_parameters",
                "no parameter is observable in the measured targets",
                frozen=selection.frozen,
            )

        for parameter in self.parameters:
            if parameter.name in names and parameter.name not in selection.selected:
                parameter.fixed = True

        self._selection = selection
        self._timer.finish(
            StageStatus.PASSED,
            message=f"{len(selection.selected)} of {len(names)} parameters selected",
            details={
                "selected": selection.selected,
                "frozen": selection.frozen,
                "condition_number": selection.condition_number,
                "selected_condition_number": selection.selected_condition_number,
            },
        )

    def _stage_updating(self) -> None:
        self._timer.start(Stage.UPDATING)
        fit = self.test.select(self._fit_indices())
        options = self.updating_options or UpdatingOptions(
            mac_threshold=self.gates.pairing_mac_min
        )
        try:
            updater = ModelUpdater(
                self.model,
                self.parameters,
                fit.frequencies,
                fit.mode_shapes,
                dof_weights=self._weights(exclude_channels=True),
                options=options,
            )
            result = updater.run()
        except Exception as exc:  # noqa: BLE001 - reported as a stage failure
            raise self._fail(
                Stage.UPDATING,
                "updating_failed",
                f"the updating loop raised {type(exc).__name__}: {exc}",
            ) from exc

        if result.final_cost > result.initial_cost * (1.0 + 1.0e-12):
            raise self._fail(
                Stage.UPDATING,
                "updating_diverged",
                f"the objective grew from {result.initial_cost:.6e} to "
                f"{result.final_cost:.6e}",
                initial_cost=result.initial_cost,
                final_cost=result.final_cost,
            )

        # The updater optimises its own copy, so S5/S6 read the corrected
        # parameters back from the result rather than from the set handed in.
        self.parameters = result.parameter_set
        self._updating = result
        self._timer.finish(
            StageStatus.PASSED,
            message=(
                f"{result.iterations} iterations, cost {result.initial_cost:.4e} -> "
                f"{result.final_cost:.4e}"
            ),
            details={
                "converged": result.converged,
                "reason": result.message,
                "iterations": result.iterations,
                "initial_cost": result.initial_cost,
                "final_cost": result.final_cost,
                "n_fitted_modes": len(self._fit_indices()),
            },
        )

    def _stage_reanalysis(self) -> None:
        self._timer.start(Stage.REANALYSIS)
        try:
            data = self.model(self.parameters.as_dict())
        except Exception as exc:  # noqa: BLE001 - reported as a stage failure
            raise self._fail(
                Stage.REANALYSIS,
                "reanalysis_solve_failed",
                f"the re-analysis modal solve raised {type(exc).__name__}: {exc}",
            ) from exc

        self._final = data
        self._final_correlation = self._correlate(
            self.test,
            data,
            weights=self._weights(exclude_channels=False),
            meta={"stage": Stage.REANALYSIS.value},
        )
        summary = self._final_correlation.summary
        self._timer.finish(
            StageStatus.PASSED,
            message=(
                f"re-analysis at the updated parameters: min MAC {summary.min_mac:.4f}, "
                f"max |Δf| {summary.max_abs_freq_error_pct:.4f} %"
            ),
            details={
                "n_paired": summary.n_paired,
                "min_mac": summary.min_mac,
                "max_abs_freq_error_pct": summary.max_abs_freq_error_pct,
                "frequencies_hz": [float(f) for f in data.frequencies],
            },
        )

    def _holdout_correlation(self, analysis: ModalData | None) -> CorrelationReport | None:
        if not self._holdout_modes or analysis is None:
            return None
        reserved = self.test.select(list(self._holdout_modes))
        return self._correlate(
            reserved,
            analysis,
            weights=self._weights(exclude_channels=False),
            meta={"holdout_modes": list(self._holdout_modes)},
        )

    def _stage_validation(
        self,
    ) -> tuple[list[GateResult], CorrelationReport | None, CorrelationReport | None]:
        self._timer.start(Stage.VALIDATION)
        assert self._final_correlation is not None
        holdout_baseline = self._holdout_correlation(self._baseline)
        holdout_final = self._holdout_correlation(self._final)

        results = evaluate_gates(
            self._final_correlation.summary,
            self.gates,
            parameters=self.parameters,
            holdout_baseline=None if holdout_baseline is None else holdout_baseline.summary,
            holdout_final=None if holdout_final is None else holdout_final.summary,
        )
        self._gate_results = results
        failing = [result.name for result in results if result.is_blocking]
        if failing:
            raise self._fail(
                Stage.VALIDATION,
                "gate_failed",
                f"validation gates not met: {', '.join(failing)}",
                failed_gates=failing,
            )
        warnings = [r.name for r in results if r.severity == "warning" and not r.passed]
        self._timer.finish(
            StageStatus.PASSED,
            message="all validation gates met"
            + (f" (warnings: {', '.join(warnings)})" if warnings else ""),
            details={"warnings": warnings},
        )
        return results, holdout_baseline, holdout_final

    # ------------------------------------------------------------------- run

    def run(self) -> CorrectionReport:
        """Execute the pipeline and return the report, passing or failing."""
        holdout_baseline: CorrelationReport | None = None
        holdout_final: CorrelationReport | None = None
        failure: dict[str, Any] | None = None
        try:
            self._stage_baseline()
            self._stage_pairing()
            self._stage_diagnosis()
            self._stage_updating()
            self._stage_reanalysis()
            _, holdout_baseline, holdout_final = self._stage_validation()
        except StageGateError as error:
            if self.strict:
                raise
            failure = error.as_dict()
            if self._holdout_modes:
                holdout_baseline = self._holdout_correlation(self._baseline)
                holdout_final = self._holdout_correlation(self._final)

        return self._build_report(failure, holdout_baseline, holdout_final)

    def _parameter_entries(self) -> list[ParameterEntry]:
        sigma = _posterior_sigma(self._updating) if self._updating is not None else {}
        diagnosed = set() if self._selection is None else set(self._selection.parameter_names)
        entries = []
        for parameter in self.parameters:
            selected = not parameter.fixed
            if selected:
                reason = None
            elif parameter.name in diagnosed and self._selection is not None:
                reason = self._selection.reason_for(parameter.name)
            else:
                reason = "user_fixed"
            entries.append(
                ParameterEntry(
                    name=parameter.name,
                    kind=parameter.kind.value,
                    initial=parameter.initial,
                    final=parameter.value,
                    lower=parameter.lower,
                    upper=parameter.upper,
                    change_pct=parameter.change_pct,
                    selected=selected,
                    freeze_reason=reason,
                    sigma_post=sigma.get(parameter.name),
                )
            )
        return entries

    def _iteration_history(self) -> list[dict[str, Any]]:
        if self._updating is None:
            return []
        return [
            {
                "iteration": record.iteration,
                "cost": record.cost,
                "residual_norm": record.residual_norm,
                "mean_mac": record.mean_mac,
                "min_mac": record.min_mac,
                "max_abs_freq_error_pct": record.max_abs_freq_error_pct,
                "damping": record.damping,
                "step_norm": record.step_norm,
                "accepted": record.accepted,
                "parameters": dict(record.parameters),
            }
            for record in self._updating.history
        ]

    def _build_report(
        self,
        failure: dict[str, Any] | None,
        holdout_baseline: CorrelationReport | None,
        holdout_final: CorrelationReport | None,
    ) -> CorrectionReport:
        stages = self._timer.records
        passed = failure is None and all(
            record.status is StageStatus.PASSED for record in stages
        )
        return CorrectionReport(
            status="PASS" if passed else "FAIL",
            stages=stages,
            baseline_correlation=self._baseline_correlation,
            final_correlation=self._final_correlation,
            holdout_baseline=holdout_baseline,
            holdout_final=holdout_final,
            iterations=self._iteration_history(),
            parameters=self._parameter_entries(),
            parameter_selection=self._selection,
            gates=self._gate_results,
            holdout_modes=self._holdout_modes,
            failure=failure,
            settings={
                "gates": self.gates.to_dict(),
                "holdout": self.holdout.to_dict(),
                "pairing_method": self.pairing_method,
                "freq_penalty": self.freq_penalty,
                "collinearity_threshold": self.collinearity_threshold,
                "low_sensitivity_ratio": self.low_sensitivity_ratio,
                "max_condition": self.max_condition,
                "sensor_map": None if self.sensor_map is None else self.sensor_map.to_dict(),
                "n_model_evaluations": self.model.n_evaluations,
                "n_test_modes": self.test.n_modes,
                "seed": self.seed,
            },
            environment=environment_block(self.seed),
        )


def run_correction(
    model: Any,
    test: Any,
    sensor_map: SensorMap | None = None,
    params: ParameterInput | None = None,
    *,
    gates: ValidationGates | None = None,
    holdout: HoldoutSpec | None = None,
    seed: int = 0,
    **kwargs: Any,
) -> CorrectionReport:
    """Run ``S1..S6`` on one model/test pair (MS-4.4).

    Returns the :class:`~openfemlab.workflow.report.CorrectionReport` whether
    the run passed or failed; a failed gate leaves ``status == "FAIL"``, the
    failing stage recorded and the stages behind it marked ``SKIPPED``.  Pass
    ``strict=True`` to raise
    :class:`~openfemlab.workflow.stages.StageGateError` instead.
    """
    workflow = CorrectionWorkflow(
        model,
        test,
        sensor_map,
        params,
        gates=gates,
        holdout=holdout,
        seed=seed,
        **kwargs,
    )
    return workflow.run()
