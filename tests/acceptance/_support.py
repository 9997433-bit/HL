"""Shared helpers for the acceptance suites of ``docs/ACCEPTANCE_CRITERIA.md``.

Every acceptance test is tagged with the registry ID it verifies through
:func:`criterion`. The decorator rejects IDs the registry does not define, and
``test_criteria_registry.py`` enforces the reverse direction: a criterion may
only claim status ``implemented`` once the suite it declares carries a test
tagged with its ID.

The reference models below are the fixtures named in section 1.4 of the
criteria document (``tests/fixtures/*.yaml``) plus the procedurally generated
spring-mass chain and Euler-Bernoulli cantilever, whose closed-form spectra are
reproduced here so the gates compare against theory rather than against a
previous run of the code under test.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from openfemlab import Material, Section

from .test_criteria_registry import get_criterion

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

#: Reference material/section of the cantilever oracle (10 x 10 mm steel bar).
STEEL = Material(E=2.1e11, density=7850.0, nu=0.3, name="steel")
SQUARE = Section(area=1e-4, inertia_z=1e-4**2 / 12.0, name="10x10 mm")

#: ``beta_i L`` roots of ``cos(beta L) cosh(beta L) + 1 = 0`` (cantilever beam).
CANTILEVER_BETA_L = (
    1.8751040687,
    4.6940911330,
    7.8547574382,
    10.9955407349,
    14.1371683910,
)


def criterion(test_id: str) -> Callable[[Any], Any]:
    """Tag a test with the acceptance criterion it verifies.

    Raises ``KeyError`` at import time for an ID the registry does not know,
    so a mistyped tag fails collection instead of silently claiming coverage.
    """
    entry = get_criterion(test_id)

    def decorate(function: Any) -> Any:
        marked = pytest.mark.acceptance(function)
        return pytest.mark.criterion(test_id, priority=entry.priority)(marked)

    return decorate


# --------------------------------------------------------------- fixtures


def load_fixture(name: str) -> dict[str, Any]:
    """Parse ``tests/fixtures/<name>.yaml`` with the safe YAML loader."""
    with (FIXTURES / f"{name}.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def fixture_matrices(data: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    """``(K, M)`` of a matrix fixture."""
    return (
        np.array(data["stiffness_matrix"], dtype=float),
        np.array(data["mass_matrix"], dtype=float),
    )


# ----------------------------------------------------------- closed forms


def chain_eigenvalues_fixed_free(n: int, stiffness: float = 1.0, mass: float = 1.0):
    """``lambda_j`` of a fixed-free chain: ``2 k/m (1 - cos((2j-1) pi/(2n+1)))``."""
    j = np.arange(1, n + 1)
    ratio = stiffness / mass
    return 2.0 * ratio * (1.0 - np.cos((2 * j - 1) * np.pi / (2 * n + 1)))


def chain_eigenvalues_fixed_fixed(n: int, stiffness: float = 1.0, mass: float = 1.0):
    """``lambda_j`` of a fixed-fixed chain: ``2 k/m (1 - cos(j pi/(n+1)))``."""
    j = np.arange(1, n + 1)
    return 2.0 * (stiffness / mass) * (1.0 - np.cos(j * np.pi / (n + 1)))


def cantilever_frequencies(
    length: float,
    material: Material = STEEL,
    section: Section = SQUARE,
    count: int = len(CANTILEVER_BETA_L),
) -> np.ndarray:
    """``f_i = (beta_i L)^2 / (2 pi L^2) sqrt(E I / (rho A))`` [Hz]."""
    scale = math.sqrt(
        material.E * section.inertia_z / (material.density * section.area * length**4)
    )
    betas = np.array(CANTILEVER_BETA_L[:count], dtype=float)
    return betas**2 / (2.0 * math.pi) * scale


# --------------------------------------------------- affine parameterization


def spring_chain_parts(
    num_masses: int,
    stiffness_groups: Sequence[Sequence[int]],
    mass_groups: Sequence[Sequence[int]],
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Contribution matrices of a grouped unit fixed-free spring-mass chain.

    Spring ``1`` ties mass ``1`` to ground and spring ``j > 1`` ties mass
    ``j - 1`` to mass ``j``; groups are given as 1-based spring/mass numbers.
    Because the assembly is affine in the group scaling factors, the returned
    ``K_j``/``M_j`` are exactly ``dK/dtheta_j`` and ``dM/dtheta_j``, and their
    sums are the nominal ``K``/``M`` of the chain.
    """
    stiffness_parts: dict[str, np.ndarray] = {}
    for index, springs in enumerate(stiffness_groups, start=1):
        part = np.zeros((num_masses, num_masses))
        for spring in springs:
            dof = spring - 1
            part[dof, dof] += 1.0
            if spring > 1:
                part[dof - 1, dof - 1] += 1.0
                part[dof - 1, dof] -= 1.0
                part[dof, dof - 1] -= 1.0
        stiffness_parts[f"k{index}"] = part

    mass_parts: dict[str, np.ndarray] = {}
    for index, masses in enumerate(mass_groups, start=1):
        part = np.zeros((num_masses, num_masses))
        for mass in masses:
            part[mass - 1, mass - 1] += 1.0
        mass_parts[f"m{index}"] = part
    return stiffness_parts, mass_parts


# ------------------------------------------------------------- assertions


def dense(matrix: Any) -> np.ndarray:
    """Plain ``(n, n)`` array from a dense, ``np.matrix`` or SciPy sparse input."""
    if hasattr(matrix, "toarray"):
        matrix = matrix.toarray()
    return np.asarray(matrix, dtype=float)


def mass_orthonormality_error(shapes: np.ndarray, mass: Any) -> float:
    """``max |Phi^T M Phi - I|`` — the MS-1.3 mass-normalization defect."""
    gram = np.asarray(shapes).conj().T @ (mass @ np.asarray(shapes))
    return float(np.max(np.abs(np.asarray(gram) - np.eye(gram.shape[0]))))


def relative_error(actual, expected) -> np.ndarray:
    """Elementwise ``|actual - expected| / |expected|``."""
    actual = np.asarray(actual, dtype=float)
    expected = np.asarray(expected, dtype=float)
    return np.abs(actual - expected) / np.abs(expected)
