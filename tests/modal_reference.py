"""Standalone spring-mass reference model used by the correlation/updating tests.

Deliberately independent of the FE core: a grounded chain of point masses and
springs whose stiffness and mass matrices are written down by hand and whose
normal modes are obtained from a dense NumPy eigensolve.  This keeps the
correlation and updating tests meaningful even when the FE solver changes, and
gives an exact reference for the 2-DOF closed-form solution.

    ground --k0-- m0 --k1-- m1 --k2-- ... --k(n-1)-- m(n-1)
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from openfemlab.updating.sensitivity import ModalData


@dataclass(frozen=True)
class SpringMassChain:
    """Grounded chain of ``n`` point masses connected by ``n`` springs."""

    masses: np.ndarray
    stiffnesses: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(self, "masses", np.asarray(self.masses, dtype=float).ravel())
        object.__setattr__(self, "stiffnesses", np.asarray(self.stiffnesses, dtype=float).ravel())
        if self.masses.size != self.stiffnesses.size:
            raise ValueError("the chain needs one spring per mass")

    @property
    def n_dof(self) -> int:
        return int(self.masses.size)

    def spring_matrices(self) -> list[np.ndarray]:
        """Per-spring stiffness contributions, i.e. ``dK/d(scale of spring i)``."""
        n = self.n_dof
        matrices = []
        for i, k in enumerate(self.stiffnesses):
            block = np.zeros((n, n))
            block[i, i] += k
            if i + 1 < n:
                block[i + 1, i + 1] += k
                block[i, i + 1] -= k
                block[i + 1, i] -= k
            matrices.append(block)
        return matrices

    def mass_matrices(self) -> list[np.ndarray]:
        """Per-DOF mass contributions, i.e. ``dM/d(scale of mass i)``."""
        n = self.n_dof
        matrices = []
        for i, m in enumerate(self.masses):
            block = np.zeros((n, n))
            block[i, i] = m
            matrices.append(block)
        return matrices

    def matrices(
        self,
        stiffness_scales: Sequence[float] | np.ndarray | None = None,
        mass_scales: Sequence[float] | np.ndarray | None = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Assemble ``(K, M)`` for the given per-spring / per-mass scale factors."""
        n = self.n_dof
        ks = np.ones(n) if stiffness_scales is None else np.asarray(stiffness_scales, float)
        ms = np.ones(n) if mass_scales is None else np.asarray(mass_scales, float)
        if ks.size != n or ms.size != n:
            raise ValueError("scale vectors must have one entry per spring / mass")
        K = np.zeros((n, n))
        for scale, block in zip(ks, self.spring_matrices(), strict=True):
            K += scale * block
        M = np.diag(ms * self.masses)
        return K, M

    def modes(
        self,
        n_modes: int | None = None,
        stiffness_scales: Sequence[float] | np.ndarray | None = None,
        mass_scales: Sequence[float] | np.ndarray | None = None,
        dofs: Sequence[int] | np.ndarray | None = None,
    ) -> ModalData:
        """Mass-normalised normal modes, optionally restricted to measured DOFs."""
        K, M = self.matrices(stiffness_scales, mass_scales)
        eigenvalues, shapes = solve_generalized_symmetric(K, M)
        if n_modes is not None:
            eigenvalues = eigenvalues[:n_modes]
            shapes = shapes[:, :n_modes]
        frequencies = np.sqrt(np.clip(eigenvalues, 0.0, None)) / (2.0 * np.pi)
        if dofs is not None:
            shapes = shapes[np.asarray(dofs, dtype=int), :]
        return ModalData(frequencies=frequencies, mode_shapes=shapes)


def solve_generalized_symmetric(K: np.ndarray, M: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Solve ``K phi = lambda M phi`` for a diagonal, positive definite ``M``.

    Uses the mass-orthonormal transform ``A = M^-1/2 K M^-1/2`` so that only a
    standard symmetric eigensolve is needed; mode shapes come back mass
    normalised with a deterministic sign convention.
    """
    diagonal = np.diag(M)
    if not np.allclose(M, np.diag(diagonal)) or np.any(diagonal <= 0.0):
        raise ValueError("this reference solver expects a positive diagonal mass matrix")
    inverse_sqrt = 1.0 / np.sqrt(diagonal)
    A = K * inverse_sqrt[:, None] * inverse_sqrt[None, :]
    eigenvalues, vectors = np.linalg.eigh(0.5 * (A + A.T))
    order = np.argsort(eigenvalues)
    eigenvalues = eigenvalues[order]
    shapes = (vectors[:, order]) * inverse_sqrt[:, None]
    dominant = np.argmax(np.abs(shapes), axis=0)
    signs = np.sign(shapes[dominant, np.arange(shapes.shape[1])])
    signs[signs == 0.0] = 1.0
    return eigenvalues, shapes * signs


def two_dof_chain() -> SpringMassChain:
    """The canonical 2-DOF test rig used across the tests."""
    return SpringMassChain(masses=[2.0, 1.0], stiffnesses=[1200.0, 800.0])


def uniform_chain(n_dof: int = 8, mass: float = 1.5, stiffness: float = 2500.0):
    """A longer chain, used for grouped-parameter and noisy-data tests."""
    return SpringMassChain(masses=np.full(n_dof, mass), stiffnesses=np.full(n_dof, stiffness))


def analytic_two_dof(m1: float, m2: float, k1: float, k2: float) -> tuple[np.ndarray, np.ndarray]:
    """Closed-form eigenvalues (ascending) and mode shapes of a 2-DOF chain."""
    b = (k1 + k2) * m2 + k2 * m1
    discriminant = np.sqrt(b * b - 4.0 * m1 * m2 * k1 * k2)
    lambdas = np.array(
        [(b - discriminant) / (2.0 * m1 * m2), (b + discriminant) / (2.0 * m1 * m2)]
    )
    shapes = np.array([[k2 - lam * m2, k2] for lam in lambdas]).T
    return lambdas, shapes


def make_model_function(
    chain: SpringMassChain,
    *,
    n_modes: int,
    stiffness_groups: Mapping[str, Sequence[int]] | None = None,
    mass_groups: Mapping[str, Sequence[int]] | None = None,
    dofs: Sequence[int] | None = None,
) -> Callable[[Mapping[str, float]], ModalData]:
    """Build the ``{parameter: value} -> ModalData`` callable the updater needs.

    ``stiffness_groups`` / ``mass_groups`` map a parameter name to the spring or
    mass indices it scales, which is how element groups are parameterised in a
    real updating run.
    """
    stiffness_groups = dict(stiffness_groups or {})
    mass_groups = dict(mass_groups or {})

    def model(parameters: Mapping[str, float]) -> ModalData:
        stiffness_scales = np.ones(chain.n_dof)
        mass_scales = np.ones(chain.n_dof)
        for name, indices in stiffness_groups.items():
            stiffness_scales[list(indices)] = float(parameters[name])
        for name, indices in mass_groups.items():
            mass_scales[list(indices)] = float(parameters[name])
        return chain.modes(
            n_modes=n_modes,
            stiffness_scales=stiffness_scales,
            mass_scales=mass_scales,
            dofs=dofs,
        )

    return model


def perturb(base: float, factors: Mapping[int, float], size: int) -> np.ndarray:
    """Scale vector of length ``size`` filled with ``base`` and patched entries."""
    values = np.full(size, float(base))
    for index, factor in factors.items():
        values[index] = factor
    return values
