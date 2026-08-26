"""Verification of the modal solver against closed-form solutions.

Analytic references used here
-----------------------------
2-DOF chain (ground-k1-m1-k2-m2), ``det(K - lambda M) = 0``::

    m1 m2 lambda^2 - [(k1 + k2) m2 + k2 m1] lambda + k1 k2 = 0
    phi ~ [k2 - lambda m2, k2]

Uniform N-DOF chain of masses ``m`` and springs ``k``::

    fixed-free   omega_i = 2 sqrt(k/m) sin((2i - 1) pi / (2 (2N + 1)))
                 phi_ij  = sin((2i - 1) j pi / (2N + 1))
    fixed-fixed  omega_i = 2 sqrt(k/m) sin(i pi / (2 (N + 1)))
                 phi_ij  = sin(i j pi / (N + 1))

Uniform axial bar (wave speed ``c = sqrt(E / rho)``)::

    fixed-free   f_i = (2i - 1) c / (4 L)
    free-free    f_i = i c / (2 L)

Uniform Euler-Bernoulli cantilever::

    f_i = beta_i^2 / (2 pi) sqrt(E I / (rho A L^4)),
    beta_i L = 1.875104, 4.694091, 7.854757, ...
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
import scipy.sparse as sp
import yaml

from openfemlab import DOF, Material, ModalSolver, Model, Section, SolverError
from openfemlab.mesh.simple import bar_mesh, beam_mesh, spring_mass_chain, truss_from_arrays

STEEL = Material(E=2.1e11, density=7850.0, nu=0.3, name="steel")
SQUARE = Section(area=1e-4, inertia_z=1e-4**2 / 12.0, name="10x10 mm")

FIXTURES = Path(__file__).parent / "fixtures"


# --------------------------------------------------------------------- helpers


def mac(a: np.ndarray, b: np.ndarray) -> float:
    """Modal Assurance Criterion between two mode shape vectors."""
    num = float(np.dot(a, b)) ** 2
    den = float(np.dot(a, a)) * float(np.dot(b, b))
    return num / den


def analytic_two_dof(m1: float, m2: float, k1: float, k2: float):
    """Exact eigenvalues (omega^2, ascending) and mode shapes of a 2-DOF chain."""
    b = (k1 + k2) * m2 + k2 * m1
    disc = math.sqrt(b * b - 4.0 * m1 * m2 * k1 * k2)
    lam = np.array([(b - disc) / (2.0 * m1 * m2), (b + disc) / (2.0 * m1 * m2)])
    shapes = np.array([[k2 - lam[i] * m2, k2] for i in range(2)]).T
    return lam, shapes


def analytic_chain_fixed_free(n: int, k: float, m: float):
    i = np.arange(1, n + 1)
    omega = 2.0 * math.sqrt(k / m) * np.sin((2 * i - 1) * np.pi / (2 * (2 * n + 1)))
    j = np.arange(1, n + 1)
    shapes = np.sin(np.outer(j, 2 * i - 1) * np.pi / (2 * n + 1))  # (dof, mode)
    return omega, shapes


def analytic_chain_fixed_fixed(n: int, k: float, m: float):
    i = np.arange(1, n + 1)
    omega = 2.0 * math.sqrt(k / m) * np.sin(i * np.pi / (2 * (n + 1)))
    j = np.arange(1, n + 1)
    shapes = np.sin(np.outer(j, i) * np.pi / (n + 1))
    return omega, shapes


# ------------------------------------------------------ reference fixtures
#
# ``tests/fixtures/*.yaml`` hold the two benchmark eigenproblems with their
# closed-form spectra. They are the shared reference for this suite and for the
# io/correlation suites, so the numbers live in data rather than in code.


def load_fixture(name: str) -> dict:
    with (FIXTURES / f"{name}.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def fixture_matrices(data: dict) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.array(data["stiffness_matrix"], dtype=float),
        np.array(data["mass_matrix"], dtype=float),
    )


def fixture_mode_shapes(data: dict) -> np.ndarray:
    """Reference shapes as ``(ndof, nmodes)``, i.e. the solver's own layout."""
    expected = data["expected"]
    shapes = np.array(expected["mass_normalized_mode_shapes"], dtype=float)
    if expected["mode_shape_layout"] == "modes_by_dof":
        shapes = shapes.T
    return shapes


def align_signs(computed: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Flip whole columns so that sign-arbitrary shapes become comparable."""
    signs = np.sign(np.einsum("ij,ij->j", computed, reference))
    signs[signs == 0.0] = 1.0
    return computed * signs


#: Fixture name and the ``mesh.simple`` model that must reproduce it.
FIXTURE_CASES = [
    ("two_dof_analytic", lambda: spring_mass_chain(2, 1.0, 1.0, fixed_end=True)),
    ("ten_dof_chain", lambda: spring_mass_chain(10, 1.0, 1.0)),
]
FIXTURE_NAMES = [name for name, _ in FIXTURE_CASES]


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixture_spectrum_matches_the_reference_values(name):
    data = load_fixture(name)
    K, M = fixture_matrices(data)
    expected = data["expected"]
    rtol = float(data["tolerances"]["eigenvalue_relative"])

    result = ModalSolver.from_matrices(K, M).solve(num_modes=K.shape[0])

    assert result.num_modes == K.shape[0]
    np.testing.assert_allclose(result.eigenvalues, expected["eigenvalues"], rtol=rtol)
    np.testing.assert_allclose(
        result.angular_frequencies, expected["angular_frequencies"], rtol=rtol
    )
    np.testing.assert_allclose(result.frequencies, expected["frequencies_hz"], rtol=rtol)
    assert not np.any(result.rigid_body_modes)


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixture_eigenpairs_satisfy_the_residual_and_orthogonality_contract(name):
    """``K phi = lambda M phi`` to machine precision, with ``phi^T M phi = I``."""
    data = load_fixture(name)
    K, M = fixture_matrices(data)
    ndof = K.shape[0]

    result = ModalSolver.from_matrices(K, M).solve(num_modes=ndof)
    phi = result.mode_shapes

    np.testing.assert_allclose(phi.T @ M @ phi, np.eye(ndof), atol=1e-12)
    np.testing.assert_allclose(phi.T @ K @ phi, np.diag(result.eigenvalues), atol=1e-12)
    residual = K @ phi - (M @ phi) * result.eigenvalues
    relative = np.linalg.norm(residual, axis=0) / np.linalg.norm(K @ phi, axis=0)
    assert np.max(relative) < 1e-12


def test_two_dof_fixture_mode_shapes_match_the_reference():
    data = load_fixture("two_dof_analytic")
    K, M = fixture_matrices(data)
    reference = fixture_mode_shapes(data)
    atol = float(data["tolerances"]["mode_shape_absolute"])

    result = ModalSolver.from_matrices(K, M).solve(num_modes=2, normalization="mass")

    assert data["expected"]["mode_shape_sign_is_arbitrary"]
    np.testing.assert_allclose(align_signs(result.mode_shapes, reference), reference, atol=atol)
    for mode in range(2):
        assert mac(result.mode_shapes[:, mode], reference[:, mode]) == pytest.approx(1.0, abs=1e-12)


def test_ten_dof_fixture_shapes_follow_the_fixed_free_sine_law():
    """``phi_ij = sin((2i - 1) j pi / (2N + 1))`` for the unit fixed-free chain."""
    data = load_fixture("ten_dof_chain")
    K, M = fixture_matrices(data)
    ndof = K.shape[0]
    assert data["boundary_condition"] == "fixed_free"

    result = ModalSolver.from_matrices(K, M).solve(num_modes=ndof)
    reference = analytic_chain_fixed_free(ndof, 1.0, 1.0)[1]

    for mode in range(ndof):
        assert mac(result.mode_shapes[:, mode], reference[:, mode]) == pytest.approx(1.0, abs=1e-9)


@pytest.mark.parametrize(("name", "model_factory"), FIXTURE_CASES, ids=FIXTURE_NAMES)
def test_mesh_builder_assembles_the_fixture_eigenproblem(name, model_factory):
    """``mesh.simple`` + ``core.assembly`` must produce the fixture's K and M."""
    data = load_fixture(name)
    K, M = fixture_matrices(data)

    system = model_factory().assemble()
    K_ff, M_ff = system.reduced()

    assert system.num_free_dofs == len(data["dof_labels"])
    np.testing.assert_allclose(K_ff.toarray(), K, atol=1e-12)
    np.testing.assert_allclose(M_ff.toarray(), M, atol=1e-12)


@pytest.mark.parametrize(("name", "model_factory"), FIXTURE_CASES, ids=FIXTURE_NAMES)
def test_meshed_model_reproduces_the_fixture_spectrum_end_to_end(name, model_factory):
    """Model -> assembly -> eigensolve agrees with the closed-form reference."""
    data = load_fixture(name)
    expected = data["expected"]
    rtol = float(data["tolerances"]["eigenvalue_relative"])
    ndof = len(data["dof_labels"])

    result = ModalSolver(model_factory()).solve(num_modes=ndof)

    np.testing.assert_allclose(result.eigenvalues, expected["eigenvalues"], rtol=rtol)
    np.testing.assert_allclose(result.frequencies, expected["frequencies_hz"], rtol=rtol)
    # the ground node is constrained, so the full-space shapes carry a zero row
    assert result.mode_shapes.shape[0] > ndof
    np.testing.assert_allclose(result.mode_shapes[result.system.constrained_dofs], 0.0, atol=0.0)


def test_ten_dof_fixture_sparse_backend_matches_the_reference():
    data = load_fixture("ten_dof_chain")
    K, M = fixture_matrices(data)
    solver = ModalSolver.from_matrices(K, M)

    result = solver.solve(num_modes=4, sparse=True)

    np.testing.assert_allclose(
        result.eigenvalues, data["expected"]["eigenvalues"][:4], rtol=1e-9
    )


# ------------------------------------------------------------------- 2 DOF


def test_two_dof_uniform_chain_matches_closed_form():
    k, m = 1000.0, 2.0
    model = spring_mass_chain(2, k, m)
    result = ModalSolver(model).solve(num_modes=2)

    ratios = np.array([(3.0 - math.sqrt(5.0)) / 2.0, (3.0 + math.sqrt(5.0)) / 2.0])
    expected = np.sqrt(ratios * k / m)
    assert result.num_modes == 2
    np.testing.assert_allclose(result.angular_frequencies, expected, rtol=1e-10)
    np.testing.assert_allclose(result.frequencies, expected / (2.0 * np.pi), rtol=1e-10)


def test_two_dof_non_uniform_frequencies_and_shapes():
    m1, m2, k1, k2 = 3.0, 1.5, 2500.0, 900.0
    model = Model(dofs=(DOF.UX,), name="2dof")
    for i in range(3):
        model.add_node(i, float(i), 0.0, 0.0)
    model.add_spring(0, 1, k1)
    model.add_spring(1, 2, k2)
    model.add_point_mass(1, m1)
    model.add_point_mass(2, m2)
    model.fix(0)

    result = ModalSolver(model).solve(num_modes=2)
    lam, shapes = analytic_two_dof(m1, m2, k1, k2)

    np.testing.assert_allclose(result.eigenvalues, lam, rtol=1e-10)
    for mode in range(2):
        assert mac(result.mode_shapes[1:, mode], shapes[:, mode]) == pytest.approx(1.0, abs=1e-12)


def test_two_dof_mode_shape_ratio():
    """Second mode of a uniform 2-DOF chain is out of phase with ratio -1/phi."""
    result = ModalSolver(spring_mass_chain(2, 1.0, 1.0)).solve(num_modes=2, normalization="max")
    first = result.mode_shapes[1:, 0]
    second = result.mode_shapes[1:, 1]
    golden = (1.0 + math.sqrt(5.0)) / 2.0
    assert first[1] / first[0] == pytest.approx(golden, rel=1e-10)
    assert second[1] / second[0] == pytest.approx(-1.0 / golden, rel=1e-10)


# ------------------------------------------------------------------ 10 DOF


def test_ten_dof_chain_fixed_free():
    n, k, m = 10, 1500.0, 0.75
    model = spring_mass_chain(n, k, m)
    result = ModalSolver(model).solve(num_modes=n)

    omega, shapes = analytic_chain_fixed_free(n, k, m)
    np.testing.assert_allclose(result.angular_frequencies, omega, rtol=1e-9)
    np.testing.assert_allclose(result.frequencies, omega / (2.0 * np.pi), rtol=1e-9)
    for mode in range(n):
        assert mac(result.mode_shapes[1:, mode], shapes[:, mode]) == pytest.approx(1.0, abs=1e-9)


def test_ten_dof_chain_fixed_fixed():
    n, k, m = 10, 900.0, 1.25
    model = spring_mass_chain(n, k, m, fixed_end=True)
    result = ModalSolver(model).solve(num_modes=n)

    omega, shapes = analytic_chain_fixed_fixed(n, k, m)
    np.testing.assert_allclose(result.angular_frequencies, omega, rtol=1e-9)
    for mode in range(n):
        assert mac(result.mode_shapes[1:-1, mode], shapes[:, mode]) == pytest.approx(1.0, abs=1e-9)


def test_ten_dof_chain_non_uniform_matches_dense_reference():
    """Non-uniform chain checked against an independently built dense eigenproblem."""
    n = 10
    rng = np.random.default_rng(20240607)
    k = rng.uniform(500.0, 5000.0, size=n)
    m = rng.uniform(0.5, 4.0, size=n)
    result = ModalSolver(spring_mass_chain(n, k, m)).solve(num_modes=n)

    K = np.zeros((n, n))
    for i in range(n):
        K[i, i] += k[i]
        if i + 1 < n:
            K[i, i] += k[i + 1]
            K[i, i + 1] = K[i + 1, i] = -k[i + 1]
    reference = np.sort(np.linalg.eigvals(np.linalg.solve(np.diag(m), K)).real)
    np.testing.assert_allclose(result.eigenvalues, reference, rtol=1e-9)


# ------------------------------------------------------- orthogonality / scaling


def test_mass_normalization_gives_orthonormal_modes():
    model = spring_mass_chain(10, 1500.0, 0.75)
    system = model.assemble()
    result = ModalSolver(system=system).solve(num_modes=10, normalization="mass")

    phi = result.mode_shapes
    gram = phi.T @ (system.M @ phi)
    np.testing.assert_allclose(gram, np.eye(10), atol=1e-9)

    modal_k = phi.T @ (system.K @ phi)
    np.testing.assert_allclose(np.diag(modal_k), result.eigenvalues, rtol=1e-9)
    np.testing.assert_allclose(modal_k - np.diag(np.diag(modal_k)), 0.0, atol=1e-6)
    np.testing.assert_allclose(result.modal_masses, np.ones(10), atol=1e-9)
    assert result.orthogonality_error() < 1e-9


def test_max_and_none_normalizations():
    model = spring_mass_chain(5, 1000.0, 1.0)
    solver = ModalSolver(model)

    scaled = solver.solve(num_modes=5, normalization="max")
    np.testing.assert_allclose(np.max(np.abs(scaled.mode_shapes), axis=0), np.ones(5), rtol=1e-12)

    raw = solver.solve(num_modes=5, normalization="none")
    normalized = solver.solve(num_modes=5, normalization="mass")
    np.testing.assert_allclose(raw.eigenvalues, normalized.eigenvalues, rtol=1e-12)
    for mode in range(5):
        assert mac(raw.mode_shapes[:, mode], normalized.mode_shapes[:, mode]) == pytest.approx(
            1.0, abs=1e-12
        )


def test_mode_shape_sign_convention_is_deterministic():
    model = spring_mass_chain(6, 1000.0, 1.0)
    result = ModalSolver(model).solve(num_modes=6)
    dominant = np.argmax(np.abs(result.mode_shapes), axis=0)
    peaks = result.mode_shapes[dominant, np.arange(6)]
    assert np.all(peaks > 0.0)


# ----------------------------------------------------------- solver back-ends


def test_sparse_and_dense_paths_agree():
    n = 500
    k, m = 2000.0, 1.5
    model = spring_mass_chain(n, k, m)
    solver = ModalSolver(model)

    dense = solver.solve(num_modes=8, sparse=False)
    sparse = solver.solve(num_modes=8, sparse=True)

    omega = analytic_chain_fixed_free(n, k, m)[0][:8]
    np.testing.assert_allclose(dense.angular_frequencies, omega, rtol=1e-8)
    np.testing.assert_allclose(sparse.angular_frequencies, omega, rtol=1e-8)
    np.testing.assert_allclose(sparse.frequencies, dense.frequencies, rtol=1e-8)
    for mode in range(8):
        assert mac(sparse.mode_shapes[:, mode], dense.mode_shapes[:, mode]) == pytest.approx(
            1.0, abs=1e-8
        )


def test_sparse_path_selected_automatically_for_large_models():
    solver = ModalSolver(spring_mass_chain(1000, 2000.0, 1.5))
    assert solver._choose_sparse(solver.system.num_free_dofs, 5) is True
    assert solver._choose_sparse(50, 5) is False
    result = solver.solve(num_modes=5)
    omega = analytic_chain_fixed_free(1000, 2000.0, 1.5)[0][:5]
    np.testing.assert_allclose(result.angular_frequencies, omega, rtol=1e-7)


def test_from_matrices_entry_point():
    K = sp.csr_matrix(np.array([[2.0, -1.0], [-1.0, 1.0]]) * 1000.0)
    M = sp.csr_matrix(np.eye(2) * 2.0)
    result = ModalSolver.from_matrices(K, M).solve(num_modes=2)
    expected = np.array([(3.0 - math.sqrt(5.0)) / 2.0, (3.0 + math.sqrt(5.0)) / 2.0]) * 500.0
    np.testing.assert_allclose(result.eigenvalues, expected, rtol=1e-10)


# ---------------------------------------------------------------- continuum


@pytest.mark.parametrize(("num_elements", "rtol"), [(20, 7e-3), (60, 8e-4)])
def test_axial_bar_matches_continuum_solution(num_elements, rtol):
    length = 2.5
    model = bar_mesh(length, num_elements, STEEL, SQUARE)
    result = ModalSolver(model).solve(num_modes=3)

    c = math.sqrt(STEEL.E / STEEL.density)
    exact = np.array([(2 * i - 1) * c / (4.0 * length) for i in (1, 2, 3)])
    np.testing.assert_allclose(result.frequencies, exact, rtol=rtol)
    # the consistent mass formulation is an upper bound on the exact spectrum
    assert np.all(result.frequencies >= exact * (1.0 - 1e-12))


def test_axial_bar_converges_quadratically():
    """Halving the element size must quarter the discretization error."""
    length = 1.0
    exact = math.sqrt(STEEL.E / STEEL.density) / (4.0 * length)
    errors = []
    for n in (10, 20, 40):
        f = ModalSolver(bar_mesh(length, n, STEEL, SQUARE)).solve(num_modes=1).frequencies[0]
        errors.append(abs(f - exact) / exact)
    ratios = [errors[i] / errors[i + 1] for i in range(2)]
    assert all(3.5 < r < 4.5 for r in ratios), ratios


def test_lumped_mass_brackets_the_exact_bar_frequency():
    length, n = 1.0, 20
    exact = math.sqrt(STEEL.E / STEEL.density) / (4.0 * length)
    consistent = ModalSolver(bar_mesh(length, n, STEEL, SQUARE)).solve(num_modes=1).frequencies[0]
    lumped = (
        ModalSolver(bar_mesh(length, n, STEEL, SQUARE, lumped_mass=True))
        .solve(num_modes=1)
        .frequencies[0]
    )
    assert lumped < exact < consistent
    assert abs(consistent - exact) / exact < 1e-3
    assert abs(lumped - exact) / exact < 1e-3


def test_free_free_bar_has_one_rigid_body_mode():
    length = 1.8
    model = bar_mesh(length, 30, STEEL, SQUARE, fixed_start=False)
    result = ModalSolver(model).solve(num_modes=3)

    c = math.sqrt(STEEL.E / STEEL.density)
    assert result.rigid_body_modes[0]
    assert result.frequencies[0] < 1e-6 * result.frequencies[1]
    np.testing.assert_allclose(
        result.frequencies[1:], np.array([c / (2.0 * length), c / length]), rtol=5e-3
    )


def test_cantilever_beam_bending_frequencies():
    length, n = 1.0, 20
    model = beam_mesh(length, n, STEEL, SQUARE)
    result = ModalSolver(model).solve(num_modes=3)

    beta = np.array([1.875104068711961, 4.694091132974175, 7.854757438237613])
    reference = (
        beta**2
        / (2.0 * np.pi)
        * math.sqrt(STEEL.E * SQUARE.inertia_z / (STEEL.density * SQUARE.area * length**4))
    )
    np.testing.assert_allclose(result.frequencies, reference, rtol=2e-3)


def test_simply_supported_beam_frequencies():
    length, n = 1.5, 24
    model = beam_mesh(length, n, STEEL, SQUARE, support="simply-supported")
    result = ModalSolver(model).solve(num_modes=2)

    i = np.array([1.0, 2.0])
    reference = (
        (i * np.pi) ** 2
        / (2.0 * np.pi)
        * math.sqrt(STEEL.E * SQUARE.inertia_z / (STEEL.density * SQUARE.area * length**4))
    )
    np.testing.assert_allclose(result.frequencies, reference, rtol=2e-3)


# ------------------------------------------------- point masses / condensation


def test_tip_mass_on_massless_bar_condenses_interior_dofs():
    """Massless interior DOFs are removed exactly: omega = sqrt(EA / (L m))."""
    length, tip = 2.0, 12.0
    massless = Material(E=STEEL.E, density=0.0)
    model = bar_mesh(length, 4, massless, SQUARE, tip_mass=tip)
    result = ModalSolver(model).solve(num_modes=1)

    assert result.num_condensed_dofs == 3
    expected = math.sqrt(massless.E * SQUARE.area / (length * tip))
    assert result.angular_frequencies[0] == pytest.approx(expected, rel=1e-10)
    # statically recovered interior DOFs vary linearly along the bar
    shape = result.mode_shapes[:, 0]
    np.testing.assert_allclose(shape / shape[-1], np.linspace(0.0, 1.0, 5), atol=1e-10)


def test_singular_mass_matrix_reported_when_condensation_disabled():
    massless = Material(E=STEEL.E, density=0.0)
    model = bar_mesh(1.0, 3, massless, SQUARE, tip_mass=5.0)
    with pytest.raises(SolverError, match="zero mass"):
        ModalSolver(model).solve(num_modes=1, condense_massless=False)


def test_tip_mass_lowers_cantilever_frequency():
    length, n = 1.0, 16
    bare = ModalSolver(beam_mesh(length, n, STEEL, SQUARE)).solve(num_modes=1).frequencies[0]
    loaded = (
        ModalSolver(beam_mesh(length, n, STEEL, SQUARE, tip_mass=0.5))
        .solve(num_modes=1)
        .frequencies[0]
    )
    assert loaded < bare

    # heavy tip mass -> massless-beam limit f = sqrt(3EI/L^3 / M) / (2 pi)
    heavy = 500.0 * STEEL.density * SQUARE.area * length
    result = ModalSolver(beam_mesh(length, n, STEEL, SQUARE, tip_mass=heavy)).solve(num_modes=1)
    limit = math.sqrt(3.0 * STEEL.E * SQUARE.inertia_z / length**3 / heavy) / (2.0 * np.pi)
    assert result.frequencies[0] == pytest.approx(limit, rel=5e-3)


# ------------------------------------------------------ modal post-processing


def test_effective_masses_sum_to_total_mass():
    """A complete modal basis recovers the rigid-body mass ``r^T M r``."""
    n, k, m = 10, 1000.0, 2.0
    result = ModalSolver(spring_mass_chain(n, k, m)).solve(num_modes=n)
    assert float(np.sum(result.effective_masses(DOF.UX))) == pytest.approx(n * m, rel=1e-9)

    system = bar_mesh(1.0, 12, STEEL, SQUARE).assemble()
    bar_result = ModalSolver(system=system).solve(num_modes=12)
    influence = np.zeros(system.num_dofs)
    influence[system.free_dofs] = 1.0
    expected = float(influence @ (system.M @ influence))
    assert float(np.sum(bar_result.effective_masses("UX"))) == pytest.approx(expected, rel=1e-9)


def test_participation_factors_of_first_mode_dominate():
    """The fundamental mode of a fixed-free chain carries ~8/pi^2 of the mass."""
    result = ModalSolver(spring_mass_chain(10, 1000.0, 2.0)).solve(num_modes=10)
    effective = result.effective_masses(DOF.UX)
    assert effective[0] / effective.sum() == pytest.approx(8.0 / np.pi**2, rel=0.05)
    assert np.all(effective >= -1e-12)


def test_modal_stiffness_equals_eigenvalue_times_modal_mass():
    result = ModalSolver(spring_mass_chain(8, 1234.0, 0.9)).solve(num_modes=8, normalization="max")
    np.testing.assert_allclose(
        result.modal_stiffnesses, result.eigenvalues * result.modal_masses, rtol=1e-9
    )


def test_periods_and_summary():
    result = ModalSolver(spring_mass_chain(3, 1000.0, 1.0)).solve(num_modes=3)
    np.testing.assert_allclose(result.periods, 1.0 / result.frequencies, rtol=1e-12)
    text = result.summary()
    assert "f [Hz]" in text and text.count("\n") >= 4


# ------------------------------------------------------------------ geometry


def test_frequencies_are_invariant_under_rigid_rotation():
    """A free-free space truss keeps its spectrum when the whole model is rotated."""
    coords = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.5, 0.9, 0.0]])
    conn = [(0, 1), (1, 2), (2, 0)]
    base = ModalSolver(truss_from_arrays(coords, conn, STEEL, SQUARE)).solve(num_modes=9)

    angle = 0.7
    rz = np.array(
        [
            [math.cos(angle), -math.sin(angle), 0.0],
            [math.sin(angle), math.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    ry = np.array(
        [
            [math.cos(0.35), 0.0, math.sin(0.35)],
            [0.0, 1.0, 0.0],
            [-math.sin(0.35), 0.0, math.cos(0.35)],
        ]
    )
    rotated = ModalSolver(
        truss_from_arrays(coords @ rz.T @ ry.T, conn, STEEL, SQUARE)
    ).solve(num_modes=9)

    assert int(np.sum(base.rigid_body_modes)) == 6
    np.testing.assert_allclose(rotated.frequencies[6:], base.frequencies[6:], rtol=1e-8)


def test_bar_orientation_does_not_change_axial_spectrum():
    length = 1.3
    axial = ModalSolver(bar_mesh(length, 10, STEEL, SQUARE, dofs=(DOF.UX,))).solve(num_modes=4)
    skewed = ModalSolver(
        bar_mesh(length, 10, STEEL, SQUARE, dofs=(DOF.UY,), direction=(0.0, 1.0, 0.0))
    ).solve(num_modes=4)
    np.testing.assert_allclose(skewed.frequencies, axial.frequencies, rtol=1e-10)


# -------------------------------------------------------------- filters/errors


def test_max_frequency_filter():
    n, k, m = 10, 1000.0, 2.0
    omega = analytic_chain_fixed_free(n, k, m)[0]
    cutoff = float(omega[3] / (2.0 * np.pi)) * 1.001
    result = ModalSolver(spring_mass_chain(n, k, m)).solve(num_modes=n, max_frequency=cutoff)
    assert result.num_modes == 4
    np.testing.assert_allclose(result.angular_frequencies, omega[:4], rtol=1e-9)


def test_num_modes_is_capped_at_the_available_dof_count():
    result = ModalSolver(spring_mass_chain(4, 1000.0, 1.0)).solve(num_modes=25)
    assert result.num_modes == 4


def test_invalid_inputs_raise_solver_errors():
    model = spring_mass_chain(3, 1000.0, 1.0)
    solver = ModalSolver(model)
    with pytest.raises(SolverError, match="normalization"):
        solver.solve(num_modes=1, normalization="unit")
    with pytest.raises(SolverError, match="num_modes"):
        solver.solve(num_modes=0)
    with pytest.raises(SolverError, match="exactly one"):
        ModalSolver(model, system=model.assemble())
    with pytest.raises(SolverError, match="exactly one"):
        ModalSolver()

    fully_fixed = spring_mass_chain(1, 1000.0, 1.0)
    fully_fixed.fix(1)
    with pytest.raises(SolverError, match="no free DOF"):
        ModalSolver(fully_fixed)


def test_massless_mechanism_is_reported():
    """A massless DOF with no stiffness path cannot be condensed."""
    model = Model(dofs=(DOF.UX,))
    model.add_node(0, 0.0)
    model.add_node(1, 1.0)
    model.add_node(2, 2.0)
    model.add_spring(0, 1, 1000.0)
    model.add_point_mass(1, 2.0)
    model.add_spring(1, 2, 1000.0)
    model.add_spring(1, 2, 1000.0)  # node 2 is massless but supported -> fine
    model.fix(0)
    assert ModalSolver(model).solve(num_modes=1).num_condensed_dofs == 1

    detached = Model(dofs=(DOF.UX,))
    detached.add_node(0, 0.0)
    detached.add_node(1, 1.0)
    detached.add_node(2, 2.0)  # neither stiffness nor mass: a free-floating DOF
    detached.add_spring(0, 1, 1000.0)
    detached.add_point_mass(1, 2.0)
    detached.fix(0)
    with pytest.raises(SolverError, match="massless mechanism"):
        ModalSolver(detached).solve(num_modes=1)


def test_negative_stiffness_matrix_warns():
    K = np.array([[1.0, 0.0], [0.0, -1.0]])
    M = np.eye(2)
    solver = ModalSolver.from_matrices(K, M)
    with pytest.warns(RuntimeWarning, match="negative eigenvalues"):
        result = solver.solve(num_modes=2, normalization="none")
    assert result.eigenvalues[0] == 0.0
