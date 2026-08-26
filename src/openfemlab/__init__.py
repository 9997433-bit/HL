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
    "Quad4Element": "openfemlab.core.elements",
    "Tet4Element": "openfemlab.core.elements",
    "plane_constitutive_matrix": "openfemlab.core.elements",
    "solid_constitutive_matrix": "openfemlab.core.elements",
    # assembly
    "AssembledSystem": "openfemlab.core.assembly",
    "assemble_system": "openfemlab.core.assembly",
    "assemble_stiffness": "openfemlab.core.assembly",
    "assemble_mass": "openfemlab.core.assembly",
    # solver
    "ModalSolver": "openfemlab.solver.modal",
    "ModalResult": "openfemlab.solver.modal",
    # dynamics
    "ComplexModalResult": "openfemlab.solver.dynamics",
    "FrequencyResponse": "openfemlab.solver.dynamics",
    "ModalDamping": "openfemlab.solver.dynamics",
    "RayleighDamping": "openfemlab.solver.dynamics",
    "StructuralDamping": "openfemlab.solver.dynamics",
    "complex_modal_frf": "openfemlab.solver.dynamics",
    "complex_modes": "openfemlab.solver.dynamics",
    "direct_frf": "openfemlab.solver.dynamics",
    "fdac": "openfemlab.solver.dynamics",
    "frac": "openfemlab.solver.dynamics",
    "harmonic_response": "openfemlab.solver.dynamics",
    "modal_frf": "openfemlab.solver.dynamics",
    # correlation
    "mac": "openfemlab.correlation",
    "mac_value": "openfemlab.correlation",
    "pair_modes": "openfemlab.correlation",
    "correlation_summary": "openfemlab.correlation",
    # updating
    "BayesianUpdater": "openfemlab.updating",
    "GaussianPrior": "openfemlab.updating",
    "ModelUpdater": "openfemlab.updating",
    "ParameterSet": "openfemlab.updating",
    "ScalingModel": "openfemlab.updating",
    "UpdatableParameter": "openfemlab.updating",
    "update_model": "openfemlab.updating",
    "update_model_bayesian": "openfemlab.updating",
    # correction workflow
    "CorrectionReport": "openfemlab.workflow",
    "HoldoutSpec": "openfemlab.workflow",
    "SensorMap": "openfemlab.workflow",
    "ValidationGates": "openfemlab.workflow",
    "run_correction": "openfemlab.workflow",
    # optimization
    "OptimizationProblem": "openfemlab.optimization",
    "OptimizationResult": "openfemlab.optimization",
    "minimize_sizing": "openfemlab.optimization",
    # errors
    "OpenFEMLabError": "openfemlab.exceptions",
    "ModelError": "openfemlab.exceptions",
    "ElementError": "openfemlab.exceptions",
    "SolverError": "openfemlab.exceptions",
    "SolverConvergenceError": "openfemlab.exceptions",
    "MatrixSymmetryError": "openfemlab.exceptions",
    "MatrixDefinitenessError": "openfemlab.exceptions",
    "MissedModesWarning": "openfemlab.exceptions",
    "UpdatingError": "openfemlab.exceptions",
    "UpdatingDivergenceError": "openfemlab.exceptions",
    "OptimizationError": "openfemlab.exceptions",
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


# Type checkers cannot follow a module-level ``__getattr__``, so the same names
# are re-exported here (redundant aliases, never executed at runtime).
if TYPE_CHECKING:  # pragma: no cover
    from .core.assembly import AssembledSystem as AssembledSystem
    from .core.assembly import assemble_mass as assemble_mass
    from .core.assembly import assemble_stiffness as assemble_stiffness
    from .core.assembly import assemble_system as assemble_system
    from .core.elements import BarElement as BarElement
    from .core.elements import BeamElement2D as BeamElement2D
    from .core.elements import Element as Element
    from .core.elements import Quad4Element as Quad4Element
    from .core.elements import SpringElement as SpringElement
    from .core.elements import Tet4Element as Tet4Element
    from .core.elements import TrussElement as TrussElement
    from .core.elements import plane_constitutive_matrix as plane_constitutive_matrix
    from .core.elements import solid_constitutive_matrix as solid_constitutive_matrix
    from .core.model import DOF as DOF
    from .core.model import Material as Material
    from .core.model import Model as Model
    from .core.model import Node as Node
    from .core.model import Section as Section
    from .correlation import correlation_summary as correlation_summary
    from .correlation import mac as mac
    from .correlation import mac_value as mac_value
    from .correlation import pair_modes as pair_modes
    from .exceptions import ElementError as ElementError
    from .exceptions import MatrixDefinitenessError as MatrixDefinitenessError
    from .exceptions import MatrixSymmetryError as MatrixSymmetryError
    from .exceptions import MissedModesWarning as MissedModesWarning
    from .exceptions import ModelError as ModelError
    from .exceptions import OpenFEMLabError as OpenFEMLabError
    from .exceptions import OptimizationError as OptimizationError
    from .exceptions import SolverConvergenceError as SolverConvergenceError
    from .exceptions import SolverError as SolverError
    from .exceptions import UpdatingDivergenceError as UpdatingDivergenceError
    from .exceptions import UpdatingError as UpdatingError
    from .optimization import OptimizationProblem as OptimizationProblem
    from .optimization import OptimizationResult as OptimizationResult
    from .optimization import minimize_sizing as minimize_sizing
    from .solver.dynamics import ComplexModalResult as ComplexModalResult
    from .solver.dynamics import FrequencyResponse as FrequencyResponse
    from .solver.dynamics import ModalDamping as ModalDamping
    from .solver.dynamics import RayleighDamping as RayleighDamping
    from .solver.dynamics import StructuralDamping as StructuralDamping
    from .solver.dynamics import complex_modal_frf as complex_modal_frf
    from .solver.dynamics import complex_modes as complex_modes
    from .solver.dynamics import direct_frf as direct_frf
    from .solver.dynamics import fdac as fdac
    from .solver.dynamics import frac as frac
    from .solver.dynamics import harmonic_response as harmonic_response
    from .solver.dynamics import modal_frf as modal_frf
    from .solver.modal import ModalResult as ModalResult
    from .solver.modal import ModalSolver as ModalSolver
    from .updating import BayesianUpdater as BayesianUpdater
    from .updating import GaussianPrior as GaussianPrior
    from .updating import ModelUpdater as ModelUpdater
    from .updating import ParameterSet as ParameterSet
    from .updating import ScalingModel as ScalingModel
    from .updating import UpdatableParameter as UpdatableParameter
    from .updating import update_model as update_model
    from .updating import update_model_bayesian as update_model_bayesian
    from .workflow import CorrectionReport as CorrectionReport
    from .workflow import HoldoutSpec as HoldoutSpec
    from .workflow import SensorMap as SensorMap
    from .workflow import ValidationGates as ValidationGates
    from .workflow import run_correction as run_correction
