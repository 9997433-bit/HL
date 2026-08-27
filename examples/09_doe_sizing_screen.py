"""DOE screening bridged into the optimization design space.

Builds a two-spring chain, runs a full factorial over stiffness scales, ranks
the first-mode frequency response, and prints the best design point.  The same
:class:`~openfemlab.optimization.variables.DesignSpace` object can feed
:func:`~openfemlab.optimization.minimize_sizing` after screening.

Run::

    python examples/09_doe_sizing_screen.py
"""

from __future__ import annotations

import numpy as np

from openfemlab.optimization import DesignSpace, run_factorial_screen
from openfemlab.updating import ScalingModel, UpdatableParameter

K1 = np.array([[1.0, 0.0], [0.0, 0.0]])
K2 = np.array([[1.0, -1.0], [-1.0, 1.0]])


def build_space() -> tuple[ScalingModel, DesignSpace]:
    model = ScalingModel(
        stiffness_parts={"k1": K1, "k2": K2},
        base_mass=np.eye(2),
    )
    parameters = [
        UpdatableParameter("k1", value=1.0, lower=0.2, upper=5.0, kind="stiffness"),
        UpdatableParameter("k2", value=1.0, lower=0.2, upper=5.0, kind="stiffness"),
    ]
    return model, DesignSpace(parameters)


def main() -> None:
    model, space = build_space()
    factors = {"k1": (0.8, 1.0, 1.2), "k2": (0.8, 1.0, 1.2)}

    def first_frequency(theta: dict[str, float]) -> np.ndarray:
        modal = model.modal_data(theta)
        return np.asarray([modal.frequencies[0]], dtype=float)

    screen = run_factorial_screen(space, factors, first_frequency)
    best = int(np.argmax(screen.responses[:, 0]))
    print("DOE stiffness screening (full factorial)")
    print(f"  samples : {screen.count}")
    print(f"  best k1/k2 : {screen.physical[best, 0]:.2f} / {screen.physical[best, 1]:.2f}")
    print(f"  f1       : {screen.responses[best, 0]:.4f} Hz")
    print(f"  design x : {screen.design[best].tolist()}")


if __name__ == "__main__":
    main()
