"""OpenFEMLab -- open-source structural dynamics, correlation and model updating.

Quick start::

    from openfemlab import Material, Section, ModalSolver
    from openfemlab.mesh.simple import bar_mesh

    model = bar_mesh(1.0, 20, Material(2.1e11, 7850.0), Section(1e-4))
    result = ModalSolver(model).solve(num_modes=5)
    print(result.frequencies)

Top-level names are resolved lazily (PEP 562).  Importing a leaf subpackage
such as ``openfemlab.updating`` therefore only pays for the modules that
subpackage actually needs, and a subpackage stays usable while another one is
still being built out.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__version__ = "0.1.0"

#: Public name -> defining submodule, resolved on first attribute access.
_EXPORTS: dict[str, str] = {
    # core model
    "DOF": "openfemlab.core.model",
    "Material": "openfemlab.core.model",
    "Model": "openfemlab.core.model",
    "Node": "openfemlab.core.model",
    "Section": "openfemlab.core.model",
    # elements
    "Element": "openfemlab.core.elements",
    "SpringElement": "openfemlab.core.elements",
    "TrussElement": "openfemlab.core.elements",
    "BarElement": "openfemlab.core.elements",
    "BeamElement2D": "openfemlab.core.elements",
    # assembly
    "AssembledSystem": "openfemlab.core.assembly",
    "assemble_system": "openfemlab.core.assembly",
    "assemble_stiffness": "openfemlab.core.assembly",
    "assemble_mass": "openfemlab.core.assembly",
    # solver
    "ModalSolver": "openfemlab.solver.modal",
    "ModalResult": "openfemlab.solver.modal",
    # correlation
    "mac": "openfemlab.correlation",
    "mac_matrix": "openfemlab.correlation",
    "pair_modes": "openfemlab.correlation",
    "correlation_summary": "openfemlab.correlation",
    # updating
    "ModelUpdater": "openfemlab.updating",
    "ParameterSet": "openfemlab.updating",
    "UpdatableParameter": "openfemlab.updating",
    "update_model": "openfemlab.updating",
    # errors
    "OpenFEMLabError": "openfemlab.exceptions",
    "ModelError": "openfemlab.exceptions",
    "ElementError": "openfemlab.exceptions",
    "SolverError": "openfemlab.exceptions",
}

__all__ = ["__version__", *sorted(_EXPORTS)]


def __getattr__(name: str) -> object:
    try:
        module_name = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module 'openfemlab' has no attribute {name!r}") from None
    from importlib import import_module

    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_EXPORTS))


if TYPE_CHECKING:  # pragma: no cover - import-time cost avoided at runtime
    from .core.assembly import (
        AssembledSystem,
        assemble_mass,
        assemble_stiffness,
        assemble_system,
    )
    from .core.elements import BarElement, BeamElement2D, Element, SpringElement, TrussElement
    from .core.model import DOF, Material, Model, Node, Section
    from .correlation import correlation_summary, mac, mac_matrix, pair_modes
    from .exceptions import ElementError, ModelError, OpenFEMLabError, SolverError
    from .solver.modal import ModalResult, ModalSolver
    from .updating import ModelUpdater, ParameterSet, UpdatableParameter, update_model
