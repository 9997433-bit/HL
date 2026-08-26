"""Sensitivity-based iterative FE model updating.

The updater minimises a weighted least-squares residual between measured
(test) modal data and the modal data predicted by a parametric FE model::

    r = [ w_f (f_fe - f_test) / f_test ,  w_s (1 - sqrt(MAC)) ]

with respect to bounded scaling parameters (see
:mod:`openfemlab.updating.parameters`).  Each iteration builds the sensitivity
matrix ``J = dr/dx`` (finite differences by default, or a user supplied
analytical callback), then solves the damped normal equations

    (J^T J + λ diag(J^T J) + β I) Δx = -(J^T r + β (x - x0))

where ``λ`` is the Levenberg-Marquardt damping (adapted from the achieved cost
reduction, ``λ = 0`` reduces the step to plain Gauss-Newton) and ``β`` is an
optional Tikhonov regularisation pulling the parameters towards their initial
values.  Steps are projected onto the parameter bounds, and modes are re-paired
by MAC at every iteration so that mode switching during updating is handled.

The loop reports *why* it stopped through a closed vocabulary
(:data:`STOP_REASONS`) rather than through prose, and MS-3.4's divergence guard
aborts a run whose objective rises over
:attr:`UpdatingOptions.divergence_patience` consecutive accepted steps.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np

from ..correlation.mac import mac_value, modal_scale_factor
from ..correlation.pairing import pair_modes
from ..correlation.summary import CorrelationSummary, correlation_summary
from ..exceptions import UpdatingDivergenceError
from .parameters import ParameterSet, UpdatableParameter
from .sensitivity import ModalData, SensitivityResult, as_modal_data

__all__ = [
    "CONVERGED_REASONS",
    "STOP_REASONS",
    "UpdatingOptions",
    "IterationRecord",
    "UpdatingResult",
    "ModelUpdater",
    "update_model",
]

ModelCallable = Callable[[Mapping[str, float]], object]

#: Machine-readable stop reasons an :class:`UpdatingResult` may carry (MS-3.4).
#:
#: The first three plus ``max_iter`` are the MS-3.4 termination criteria —
#: parameter step, cost decrease, correlation gates, iteration cap.
#: ``gradient_tol`` is the stationary point the same convergence test reaches
#: when the gradient vanishes first, and ``no_step`` is the one non-convergent
#: exit: the line search ran out of damping without finding a decrease.
STOP_REASONS = ("step_tol", "cost_tol", "gates_met", "gradient_tol", "max_iter", "no_step")

#: The reasons that mean the run converged rather than merely stopped.
CONVERGED_REASONS = ("step_tol", "cost_tol", "gates_met", "gradient_tol")


@dataclass
class UpdatingOptions:
    """Numerical settings of an updating run.

    ``mode_pairing`` selects how the target modes are matched to the model
    modes at every iteration: ``"mac"`` is the greedy max-MAC pass classic
    tools use, ``"optimal"`` is the Hungarian assignment maximising the total
    MAC over all pairs, ``"frequency"`` pairs on frequency proximity, and
    ``"order"`` freezes the pairing to the mode order.

    ``target_min_mac`` and ``target_max_freq_error_pct`` are the optional
    correlation gates of MS-3.4: once the paired modes satisfy them there is
    nothing left to update, so the loop exits with ``gates_met`` rather than
    grinding on to a tolerance. ``line_search`` and ``divergence_patience``
    govern the two lines of defence against a diverging run — the inner search
    that refuses an uphill step, and the guard that aborts when uphill steps
    are accepted anyway.
    """

    method: str = "levenberg-marquardt"
    max_iterations: int = 30
    frequency_weight: float = 1.0
    shape_weight: float = 1.0
    shape_residual: str = "mac"
    mode_weights: np.ndarray | None = None
    regularization: float = 0.0
    initial_damping: float = 1.0e-3
    damping_increase: float = 10.0
    damping_decrease: float = 0.2
    max_damping: float = 1.0e10
    max_inner_iterations: int = 10
    cost_tolerance: float = 1.0e-10
    parameter_tolerance: float = 1.0e-8
    gradient_tolerance: float = 1.0e-12
    fd_scheme: str = "central"
    mode_pairing: str = "mac"
    mac_threshold: float = 0.0
    frequency_tolerance_pct: float | None = None
    line_search: bool = True
    divergence_patience: int = 3
    target_min_mac: float | None = None
    target_max_freq_error_pct: float | None = None

    def __post_init__(self) -> None:
        if self.method not in {"levenberg-marquardt", "lm", "gauss-newton", "gn"}:
            raise ValueError(f"unknown updating method {self.method!r}")
        if self.shape_residual not in {"mac", "difference"}:
            raise ValueError(f"unknown shape residual {self.shape_residual!r}")
        if self.mode_pairing not in {"mac", "optimal", "frequency", "order"}:
            raise ValueError(f"unknown mode pairing strategy {self.mode_pairing!r}")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        if self.divergence_patience < 1:
            raise ValueError("divergence_patience must be at least 1")

    @property
    def has_correlation_gates(self) -> bool:
        """Whether any MS-3.4 correlation gate was requested."""
        return self.target_min_mac is not None or self.target_max_freq_error_pct is not None

    def gates_met(self, correlation: CorrelationSummary) -> bool:
        """Whether ``correlation`` satisfies the requested gates."""
        if not self.has_correlation_gates or correlation.n_paired == 0:
            return False
        if self.target_min_mac is not None and correlation.min_mac < self.target_min_mac:
            return False
        return not (
            self.target_max_freq_error_pct is not None
            and correlation.max_abs_freq_error_pct > self.target_max_freq_error_pct
        )

    @property
    def is_gauss_newton(self) -> bool:
        return self.method in {"gauss-newton", "gn"}

    @property
    def pairing_method(self) -> str:
        """The :func:`~openfemlab.correlation.pairing.pair_modes` method to use."""
        return {"mac": "greedy", "optimal": "optimal"}.get(self.mode_pairing, "frequency")


@dataclass
class IterationRecord:
    """State of the updating loop after one accepted iteration."""

    iteration: int
    cost: float
    residual_norm: float
    mean_mac: float
    min_mac: float
    max_abs_freq_error_pct: float
    damping: float
    parameters: dict[str, float]
    step_norm: float = 0.0
    accepted: bool = True


@dataclass
class UpdatingResult:
    """Outcome of :meth:`ModelUpdater.run`."""

    converged: bool
    message: str
    iterations: int
    parameters: dict[str, float]
    parameter_set: ParameterSet
    initial_correlation: CorrelationSummary
    final_correlation: CorrelationSummary
    initial_cost: float
    final_cost: float
    history: list[IterationRecord] = field(default_factory=list)
    sensitivity: SensitivityResult | None = None
    modal_data: ModalData | None = None
    stop_reason: str = "max_iter"

    @property
    def accepted_costs(self) -> list[float]:
        """Objective after every accepted step, oldest first (MS-3.4)."""
        return [record.cost for record in self.history if record.accepted]

    @property
    def cost_reduction(self) -> float:
        """Fraction of the initial cost that was removed by updating."""
        if self.initial_cost <= 0.0:
            return 0.0
        return 1.0 - self.final_cost / self.initial_cost

    def report(self) -> str:
        lines = [
            f"converged   : {self.converged} ({self.stop_reason}: {self.message})",
            f"iterations  : {self.iterations}",
            f"cost        : {self.initial_cost:.6e} -> {self.final_cost:.6e} "
            f"({100.0 * self.cost_reduction:.2f}% reduction)",
            f"mean MAC    : {self.initial_correlation.mean_mac:.4f} -> "
            f"{self.final_correlation.mean_mac:.4f}",
            f"max |df| [%]: {self.initial_correlation.max_abs_freq_error_pct:.3f} -> "
            f"{self.final_correlation.max_abs_freq_error_pct:.3f}",
            "",
            self.parameter_set.table(),
        ]
        return "\n".join(lines)

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.report()


class ModelUpdater:
    """Iterative sensitivity-based model updater.

    Parameters
    ----------
    model:
        Callable mapping ``{parameter name: value}`` to modal data.  Anything
        :func:`~openfemlab.updating.sensitivity.as_modal_data` understands is
        accepted, so the updater works with the built-in solver as well as with
        an external one.
    parameters:
        The updating parameters (a :class:`ParameterSet` or any iterable of
        :class:`UpdatableParameter`).
    target_frequencies:
        Measured natural frequencies in Hz.
    target_shapes:
        Optional ``(n_dof, n_modes)`` measured mode shapes expressed in the
        correlation DOFs returned by ``model``.
    dof_weights:
        Optional per-DOF weighting used by the MAC and the shape residual.
    sensitivity_function:
        Optional analytical sensitivity ``f(params, modal_data) -> (n_modes,
        n_free_parameters)`` array of ``df/dp`` in Hz.  When given it replaces
        the finite-difference frequency sensitivities (shape residuals, if any,
        still use finite differences).
    """

    def __init__(
        self,
        model: ModelCallable,
        parameters: ParameterSet | Sequence[UpdatableParameter],
        target_frequencies: Sequence[float] | np.ndarray,
        target_shapes: np.ndarray | None = None,
        *,
        dof_weights: Sequence[float] | np.ndarray | None = None,
        sensitivity_function: Callable[[Mapping[str, float], ModalData], np.ndarray] | None = None,
        options: UpdatingOptions | None = None,
        **option_overrides: object,
    ) -> None:
        self.model = model
        # The updater works on its own copy so that repeated runs always start
        # from the same state and the caller's parameter objects stay intact.
        self.parameters = (
            parameters if isinstance(parameters, ParameterSet) else ParameterSet(parameters)
        ).copy()
        self.target = ModalData(
            np.asarray(target_frequencies, dtype=float), target_shapes
        )
        if self.target.n_modes == 0:
            raise ValueError("at least one target frequency is required")
        self.dof_weights = None if dof_weights is None else np.asarray(dof_weights, dtype=float)
        self.sensitivity_function = sensitivity_function
        self.options = options or UpdatingOptions()
        for key, value in option_overrides.items():
            if not hasattr(self.options, key):
                raise TypeError(f"unknown updating option {key!r}")
            setattr(self.options, key, value)
        self.options.__post_init__()
        if not self.parameters.free:
            raise ValueError("all parameters are fixed, nothing to update")
        self._evaluations = 0

    # ------------------------------------------------------------------
    # model evaluation and residual assembly
    # ------------------------------------------------------------------
    def evaluate(self, design_values: np.ndarray) -> ModalData:
        """Run the model for design-space values and return its modal data."""
        physical = self.parameters.design_to_physical(design_values)
        self._evaluations += 1
        return as_modal_data(self.model(physical))

    @property
    def n_evaluations(self) -> int:
        return self._evaluations

    def _mode_weights(self, pairs: list[tuple[int, int]]) -> np.ndarray:
        weights = self.options.mode_weights
        if weights is None:
            return np.ones(len(pairs))
        weights = np.asarray(weights, dtype=float).ravel()
        if weights.size != self.target.n_modes:
            raise ValueError("mode_weights must have one entry per target mode")
        return np.array([weights[i] for i, _ in pairs], dtype=float)

    def pair(self, data: ModalData) -> list[tuple[int, int]]:
        """Pair target modes with model modes for the current model state."""
        strategy = self.options.mode_pairing
        if strategy == "order" or data.mode_shapes is None or self.target.mode_shapes is None:
            if strategy == "order":
                n = min(self.target.n_modes, data.n_modes)
                return [(i, i) for i in range(n)]
            strategy = "frequency"
        pairing = pair_modes(
            test_shapes=self.target.mode_shapes,
            fe_shapes=data.mode_shapes,
            test_frequencies=self.target.frequencies,
            fe_frequencies=data.frequencies,
            method="frequency" if strategy == "frequency" else self.options.pairing_method,
            mac_threshold=self.options.mac_threshold,
            frequency_tolerance_pct=self.options.frequency_tolerance_pct,
            weights=self.dof_weights,
        )
        return [(p.test_index, p.fe_index) for p in pairing.pairs]

    def residual(self, data: ModalData, pairs: list[tuple[int, int]]) -> np.ndarray:
        """Weighted residual vector for a fixed mode pairing."""
        if not pairs:
            raise ValueError("no correlated mode pairs; cannot form a residual")
        options = self.options
        mode_weights = self._mode_weights(pairs)

        blocks: list[np.ndarray] = []
        f_test = self.target.frequencies
        f_fe = data.frequencies
        blocks.append(
            options.frequency_weight
            * mode_weights
            * np.array([(f_fe[j] - f_test[i]) / f_test[i] for i, j in pairs])
        )

        if (
            options.shape_weight > 0.0
            and self.target.mode_shapes is not None
            and data.mode_shapes is not None
        ):
            test_shapes = self.target.mode_shapes
            fe_shapes = data.mode_shapes
            if options.shape_residual == "mac":
                mac_terms = np.array(
                    [
                        1.0
                        - np.sqrt(
                            mac_value(test_shapes[:, i], fe_shapes[:, j], self.dof_weights)
                        )
                        for i, j in pairs
                    ]
                )
                blocks.append(options.shape_weight * mode_weights * mac_terms)
            else:
                for weight, (i, j) in zip(mode_weights, pairs, strict=True):
                    phi_test = test_shapes[:, i]
                    phi_fe = fe_shapes[:, j]
                    scaled = phi_fe * modal_scale_factor(phi_test, phi_fe)
                    norm = np.linalg.norm(phi_test)
                    if norm <= 0.0:
                        continue
                    difference = np.real(scaled - phi_test) / (norm * np.sqrt(phi_test.size))
                    blocks.append(options.shape_weight * weight * difference)

        return np.concatenate(blocks)

    def cost(self, residual: np.ndarray) -> float:
        return 0.5 * float(residual @ residual)

    def penalty(self, design_values: np.ndarray, reference_values: np.ndarray) -> float:
        """Regularisation term added to the data-misfit cost."""
        beta = float(self.options.regularization)
        if beta <= 0.0:
            return 0.0
        offset = design_values - reference_values
        return 0.5 * beta * float(offset @ offset)

    def normal_equations(
        self,
        jacobian: np.ndarray,
        residual: np.ndarray,
        design_values: np.ndarray,
        reference_values: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Gauss-Newton Hessian and gradient of ``cost + penalty``.

        Subclasses override this to change the estimator without touching the
        loop; :mod:`openfemlab.updating.bayesian` swaps in the MAP system.
        """
        hessian = jacobian.T @ jacobian
        gradient = jacobian.T @ residual
        beta = float(self.options.regularization)
        if beta > 0.0:
            hessian = hessian + beta * np.eye(hessian.shape[0])
            gradient = gradient + beta * (design_values - reference_values)
        return hessian, gradient

    # ------------------------------------------------------------------
    # sensitivity matrix
    # ------------------------------------------------------------------
    def jacobian(
        self,
        design_values: np.ndarray,
        pairs: list[tuple[int, int]],
        baseline_residual: np.ndarray,
        baseline_data: ModalData,
    ) -> np.ndarray:
        """Sensitivity matrix ``dr/dx`` of the residual at the current point."""
        analytical = self._analytical_frequency_jacobian(design_values, pairs, baseline_data)
        if analytical is not None:
            return analytical

        steps = self.parameters.design_steps()
        columns = []
        for k in range(design_values.size):
            forward = design_values.copy()
            forward[k] += steps[k]
            r_plus = self.residual(self.evaluate(forward), pairs)
            if self.options.fd_scheme == "forward":
                columns.append((r_plus - baseline_residual) / steps[k])
            else:
                backward = design_values.copy()
                backward[k] -= steps[k]
                r_minus = self.residual(self.evaluate(backward), pairs)
                columns.append((r_plus - r_minus) / (2.0 * steps[k]))
        return np.column_stack(columns)

    def _analytical_frequency_jacobian(
        self,
        design_values: np.ndarray,
        pairs: list[tuple[int, int]],
        data: ModalData,
    ) -> np.ndarray | None:
        """Residual Jacobian from a user supplied ``df/dp`` matrix, if usable."""
        if self.sensitivity_function is None:
            return None
        uses_shapes = (
            self.options.shape_weight > 0.0
            and self.target.mode_shapes is not None
            and data.mode_shapes is not None
        )
        if uses_shapes:
            return None  # shape residuals require finite differences

        physical = self.parameters.design_to_physical(design_values)
        df_dp = np.atleast_2d(np.asarray(self.sensitivity_function(physical, data), dtype=float))
        free = self.parameters.free
        if df_dp.shape != (data.n_modes, len(free)):
            raise ValueError(
                f"sensitivity_function returned {df_dp.shape}, expected "
                f"({data.n_modes}, {len(free)})"
            )
        mode_weights = self._mode_weights(pairs)
        rows = []
        for weight, (i, j) in zip(mode_weights, pairs, strict=True):
            row = df_dp[j, :] / self.target.frequencies[i]
            rows.append(self.options.frequency_weight * weight * row)
        jacobian = np.array(rows, dtype=float)
        # Chain rule for log-scaled design variables: dr/dx = dr/dp * p.
        chain = np.array(
            [parameter.value if parameter.log_scaled else 1.0 for parameter in free], dtype=float
        )
        return jacobian * chain[None, :]

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------
    def correlation(self, data: ModalData) -> CorrelationSummary:
        """Correlation summary of model data against the measured target."""
        return correlation_summary(
            test_frequencies=self.target.frequencies,
            fe_frequencies=data.frequencies,
            test_shapes=self.target.mode_shapes,
            fe_shapes=data.mode_shapes,
            weights=self.dof_weights,
            method=self.options.pairing_method,
        )

    def run(self) -> UpdatingResult:
        """Execute the updating loop and return the result."""
        options = self.options
        x = self.parameters.design_values()

        data = self.evaluate(x)
        pairs = self.pair(data)
        residual = self.residual(data, pairs)
        x0 = x.copy()
        # Penalized, so that the starting cost measures the same objective as
        # the trial costs it is compared against. It only differs from the bare
        # misfit when the penalty is off-centre at the starting point, which of
        # the estimators here means a Gaussian prior with an explicit mean.
        cost = self.cost(residual) + self.penalty(x, x0)

        initial_correlation = self.correlation(data)
        initial_cost = cost
        damping = 0.0 if options.is_gauss_newton else options.initial_damping

        history: list[IterationRecord] = []
        sensitivity: SensitivityResult | None = None
        stop_reason = "max_iter"
        message = "maximum number of iterations reached"
        iteration = 0
        accepted_costs: list[float] = []
        rising_steps = 0

        if options.gates_met(initial_correlation):
            return self._result(
                stop_reason="gates_met",
                message="the correlation gates are already met at the initial model",
                iteration=0,
                x=x,
                initial_correlation=initial_correlation,
                initial_cost=initial_cost,
                cost=cost,
                history=history,
                sensitivity=None,
                data=data,
            )

        for iteration in range(1, options.max_iterations + 1):
            jacobian = self.jacobian(x, pairs, residual, data)
            sensitivity = SensitivityResult(
                matrix=jacobian,
                parameter_names=self.parameters.free_names,
                response_labels=[f"r{i}" for i in range(jacobian.shape[0])],
                parameter_values=x.copy(),
                response_values=residual.copy(),
                scheme=options.fd_scheme,
            )

            hessian, gradient = self.normal_equations(jacobian, residual, x, x0)

            if np.max(np.abs(gradient)) <= options.gradient_tolerance:
                stop_reason = "gradient_tol"
                message = "gradient below tolerance"
                break

            accepted = False
            step_norm = 0.0
            previous_cost = cost
            for _ in range(options.max_inner_iterations):
                step = self._solve_step(hessian, gradient, damping)
                trial_x = self.parameters.clip_design(x + step)
                step_norm = float(np.max(np.abs(trial_x - x)))
                if step_norm == 0.0:
                    break

                trial_data = self.evaluate(trial_x)
                trial_pairs = self.pair(trial_data)
                if not trial_pairs:
                    damping = min(damping * options.damping_increase, options.max_damping)
                    continue
                trial_residual = self.residual(trial_data, trial_pairs)
                trial_cost = self.cost(trial_residual) + self.penalty(trial_x, x0)

                if trial_cost < cost or not options.line_search:
                    accepted = True
                    x, data, pairs = trial_x, trial_data, trial_pairs
                    previous_cost, cost = cost, trial_cost
                    residual = trial_residual
                    if options.is_gauss_newton:
                        damping = 0.0
                    else:
                        damping = max(damping * options.damping_decrease, 1.0e-12)
                    break

                if options.is_gauss_newton:
                    # Damped Gauss-Newton: fall back to a shorter step.
                    damping = options.initial_damping if damping == 0.0 else damping * 4.0
                else:
                    damping = min(damping * options.damping_increase, options.max_damping)
                if damping >= options.max_damping:
                    break

            self.parameters.apply_design(x)
            correlation = self.correlation(data)
            history.append(
                IterationRecord(
                    iteration=iteration,
                    cost=cost,
                    residual_norm=float(np.linalg.norm(residual)),
                    mean_mac=correlation.mean_mac,
                    min_mac=correlation.min_mac,
                    max_abs_freq_error_pct=correlation.max_abs_freq_error_pct,
                    damping=damping,
                    parameters=self.parameters.as_dict(),
                    step_norm=step_norm,
                    accepted=accepted,
                )
            )

            if not accepted:
                stop_reason = "no_step"
                message = "no cost reduction possible (damping limit reached)"
                break

            accepted_costs.append(cost)
            rising_steps = rising_steps + 1 if cost > previous_cost else 0
            if rising_steps >= options.divergence_patience:
                raise UpdatingDivergenceError(
                    f"the objective rose on {rising_steps} consecutive accepted steps "
                    f"(iteration {iteration}, J {cost:.6e}); the updating problem is "
                    "diverging",
                    costs=accepted_costs,
                    iteration=iteration,
                )

            if options.gates_met(correlation):
                stop_reason = "gates_met"
                message = "correlation gates met"
                break
            if step_norm <= options.parameter_tolerance * (1.0 + float(np.max(np.abs(x)))):
                stop_reason = "step_tol"
                message = "parameter step below tolerance"
                break
            if abs(previous_cost - cost) <= options.cost_tolerance * max(previous_cost, 1.0e-30):
                stop_reason = "cost_tol"
                message = "cost reduction below tolerance"
                break

        return self._result(
            stop_reason=stop_reason,
            message=message,
            iteration=iteration,
            x=x,
            initial_correlation=initial_correlation,
            initial_cost=initial_cost,
            cost=cost,
            history=history,
            sensitivity=sensitivity,
            data=data,
        )

    def _result(
        self,
        *,
        stop_reason: str,
        message: str,
        iteration: int,
        x: np.ndarray,
        initial_correlation: CorrelationSummary,
        initial_cost: float,
        cost: float,
        history: list[IterationRecord],
        sensitivity: SensitivityResult | None,
        data: ModalData,
    ) -> UpdatingResult:
        self.parameters.apply_design(x)
        return UpdatingResult(
            converged=stop_reason in CONVERGED_REASONS,
            message=message,
            iterations=iteration,
            parameters=self.parameters.as_dict(),
            parameter_set=self.parameters,
            initial_correlation=initial_correlation,
            final_correlation=self.correlation(data),
            initial_cost=initial_cost,
            final_cost=cost,
            history=history,
            sensitivity=sensitivity,
            modal_data=data,
            stop_reason=stop_reason,
        )

    @staticmethod
    def _solve_step(hessian: np.ndarray, gradient: np.ndarray, damping: float) -> np.ndarray:
        """Solve the damped normal equations for the parameter increment."""
        n = hessian.shape[0]
        diagonal = np.diag(hessian).copy()
        scale = np.where(diagonal > 0.0, diagonal, 1.0)
        augmented = hessian + damping * np.diag(scale)
        # Keep the system solvable for rank-deficient sensitivity matrices.
        augmented = augmented + 1.0e-12 * np.trace(augmented) / max(n, 1) * np.eye(n)
        try:
            step = np.linalg.solve(augmented, -gradient)
        except np.linalg.LinAlgError:  # pragma: no cover - singular fallback
            step = -np.linalg.lstsq(augmented, gradient, rcond=None)[0]
        if not np.all(np.isfinite(step)):  # pragma: no cover - numerical safety net
            step = -np.linalg.lstsq(augmented, gradient, rcond=None)[0]
        return step


def update_model(
    model: ModelCallable,
    parameters: ParameterSet | Sequence[UpdatableParameter],
    target_frequencies: Sequence[float] | np.ndarray,
    target_shapes: np.ndarray | None = None,
    **kwargs: object,
) -> UpdatingResult:
    """Convenience wrapper: build a :class:`ModelUpdater` and run it."""
    updater = ModelUpdater(
        model,
        parameters,
        target_frequencies,
        target_shapes,
        **kwargs,  # type: ignore[arg-type]
    )
    return updater.run()
