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
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np

from ..correlation.mac import mac_value, modal_scale_factor
from ..correlation.pairing import pair_modes
from ..correlation.summary import CorrelationSummary, correlation_summary
from .parameters import ParameterSet, UpdatableParameter
from .sensitivity import ModalData, SensitivityResult, as_modal_data

__all__ = [
    "UpdatingOptions",
    "IterationRecord",
    "UpdatingResult",
    "ModelUpdater",
    "update_model",
]

ModelCallable = Callable[[Mapping[str, float]], object]


@dataclass
class UpdatingOptions:
    """Numerical settings of an updating run."""

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

    def __post_init__(self) -> None:
        if self.method not in {"levenberg-marquardt", "lm", "gauss-newton", "gn"}:
            raise ValueError(f"unknown updating method {self.method!r}")
        if self.shape_residual not in {"mac", "difference"}:
            raise ValueError(f"unknown shape residual {self.shape_residual!r}")
        if self.mode_pairing not in {"mac", "frequency", "order"}:
            raise ValueError(f"unknown mode pairing strategy {self.mode_pairing!r}")
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")

    @property
    def is_gauss_newton(self) -> bool:
        return self.method in {"gauss-newton", "gn"}


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

    @property
    def cost_reduction(self) -> float:
        """Fraction of the initial cost that was removed by updating."""
        if self.initial_cost <= 0.0:
            return 0.0
        return 1.0 - self.final_cost / self.initial_cost

    def report(self) -> str:
        lines = [
            f"converged   : {self.converged} ({self.message})",
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
        self.parameters = (
            parameters if isinstance(parameters, ParameterSet) else ParameterSet(parameters)
        )
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
            method="greedy" if strategy == "mac" else "frequency",
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
                for weight, (i, j) in zip(mode_weights, pairs, strict=False):
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
        for weight, (i, j) in zip(mode_weights, pairs, strict=False):
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
            method="greedy" if self.options.mode_pairing == "mac" else "frequency",
        )

    def run(self) -> UpdatingResult:
        """Execute the updating loop and return the result."""
        options = self.options
        x = self.parameters.design_values()

        data = self.evaluate(x)
        pairs = self.pair(data)
        residual = self.residual(data, pairs)
        cost = self.cost(residual)

        initial_correlation = self.correlation(data)
        initial_cost = cost
        x0 = x.copy()
        damping = 0.0 if options.is_gauss_newton else options.initial_damping
        beta = float(options.regularization)

        history: list[IterationRecord] = []
        sensitivity: SensitivityResult | None = None
        converged = False
        message = "maximum number of iterations reached"
        iteration = 0

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

            hessian = jacobian.T @ jacobian
            gradient = jacobian.T @ residual
            if beta > 0.0:
                hessian = hessian + beta * np.eye(hessian.shape[0])
                gradient = gradient + beta * (x - x0)

            if np.max(np.abs(gradient)) <= options.gradient_tolerance:
                converged = True
                message = "gradient below tolerance"
                break

            accepted = False
            step_norm = 0.0
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
                trial_cost = self.cost(trial_residual)
                if beta > 0.0:
                    trial_cost += 0.5 * beta * float((trial_x - x0) @ (trial_x - x0))

                if trial_cost < cost:
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
                message = "no cost reduction possible (damping limit reached)"
                break
            if step_norm <= options.parameter_tolerance * (1.0 + float(np.max(np.abs(x)))):
                converged = True
                message = "parameter step below tolerance"
                break
            if abs(previous_cost - cost) <= options.cost_tolerance * max(previous_cost, 1.0e-30):
                converged = True
                message = "cost reduction below tolerance"
                break

        self.parameters.apply_design(x)
        final_data = data
        final_correlation = self.correlation(final_data)
        return UpdatingResult(
            converged=converged,
            message=message,
            iterations=iteration,
            parameters=self.parameters.as_dict(),
            parameter_set=self.parameters,
            initial_correlation=initial_correlation,
            final_correlation=final_correlation,
            initial_cost=initial_cost,
            final_cost=cost,
            history=history,
            sensitivity=sensitivity,
            modal_data=final_data,
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
