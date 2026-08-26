# OpenFEMLab

OpenFEMLab is an open-source, solver-independent Python toolkit for structural
dynamics. It connects finite-element modal analysis, FE/test correlation, and
sensitivity-based model updating in a reproducible CAE workflow.

The project is currently alpha software. Its APIs and interchange schemas may
change before the first stable release.

## Features

### Modal analysis

- Spring, truss/bar, and planar Euler-Bernoulli beam models with sparse global
  stiffness and mass assembly.
- Dense LAPACK and sparse shift-invert Lanczos eigensolvers, with automatic
  backend selection.
- Static condensation of massless DOFs, mass or maximum normalization, and
  deterministic mode-shape signs.
- Modal masses, participation factors, effective masses, rigid-body mode
  detection, and portable modal-result objects.

### FE/test correlation

- Test-channel alignment to analysis DOFs, including partial instrumentation
  and sensor orientation signs.
- MAC, weighted MAC, auto-MAC, COMAC, modal scale factors, and signed frequency
  errors.
- Greedy, frequency-only, and optimal (Hungarian) mode pairing with MAC and
  frequency acceptance limits.
- Schema-versioned correlation reports and command-line gates suitable for CI.

### Model updating

- Bounded stiffness, mass, damping, and generic scaling parameters, including
  fixed and logarithmically scaled variables.
- Analytical eigenvalue, frequency, mode-shape, and MAC sensitivities, plus
  finite-difference fallbacks.
- Gauss-Newton and Levenberg-Marquardt updating with regularization, adaptive
  damping, mode re-pairing, and iteration history.
- Parameter diagnosis for weakly observable, collinear, or ill-conditioned
  variables.

### Correction workflow

- Auditable six-stage pipeline: baseline analysis, pairing, diagnosis,
  updating, reanalysis, and validation.
- Sensor maps, held-out modes/channels, parameter plausibility checks, and
  configurable MAC/frequency validation gates.
- Reproducible, schema-versioned correction reports with stage outcomes,
  parameter changes, correlation metrics, and environment metadata.

### Input/output

- Versioned JSON and YAML for neutral FE models, modal results, and test data.
- Safe generic JSON/YAML document loading for model and updating
  specifications.
- Read support for ASCII UFF/UNV dataset 55 mode shapes and dataset 58
  functions/FRFs.
- A dependency-free Nastran BDF reader for the supported `GRID`, `CROD`,
  `CBAR`, `CQUAD4`, `CTETRA`, `CHEXA`, `MAT1`, `PSHELL` and `PSOLID` subset in
  free-field and small fixed-field form, continuation lines included.
- A `meshio` bridge (optional `[io]` extra) converting mesh files to and from
  the neutral model for the `vertex`/`line`/`triangle`/`quad`/`tetra`/
  `hexahedron` cell types.

## Installation

OpenFEMLab requires Python 3.10 or newer.

```bash
python -m pip install -e .
```

For contributor tools, rich CLI output, and the benchmark scripts:

```bash
python -m pip install -e ".[dev,cli]"
```

The optional `io` extra installs `meshio`, which the
`openfemlab.io.meshio_bridge` adapter uses to import Gmsh, Abaqus, VTK and the
other formats meshio reads:

```bash
python -m pip install -e ".[io]"
```

Install `openfemlab[plot]` for the optional Matplotlib mode-shape and MAC plotting helpers.

Read a supported mesh into the neutral model and write it in another format:

```python
from openfemlab.io import read_meshio, write_meshio

model = read_meshio("bracket.msh")
write_meshio(model, "bracket.vtu")
```

[`examples/04_imported_shell_modal.py`](examples/04_imported_shell_modal.py)
shows the complete analysis path for a QUAD4 plate:
`read_meshio` → `neutral_to_model(quad4_as="shell")` → `ModalSolver`. Run it
after installing the `[io]` extra:

```bash
python examples/04_imported_shell_modal.py
```

## Quickstart

Build a steel cantilever and extract its first five modes:

```python
from openfemlab import Material, ModalSolver, Section
from openfemlab.mesh.simple import beam_mesh

steel = Material(E=210e9, density=7850.0, nu=0.3)
section = Section(area=1.0e-4, inertia_z=8.333e-10)

model = beam_mesh(
    length=1.0,
    num_elements=20,
    material=steel,
    section=section,
    support="cantilever",
)
result = ModalSolver(model).solve(num_modes=5)

for mode, frequency in enumerate(result.frequencies, start=1):
    print(f"mode {mode}: {frequency:.3f} Hz")
```

See
[`examples/02_model_updating_workflow.py`](examples/02_model_updating_workflow.py)
for a complete model → synthetic test → correlation → update → validation
workflow.

For a detailed Chinese introduction and workflow reference, see the
[`中文用户指南`](docs/USER_GUIDE_zh.md).

## 5 分钟上手

用一个两自由度弹簧-质量模型依次完成模态分析、FE/试验相关和模型修正：

```bash
PYTHONPATH=src python examples/05_five_minute_workflow.py
```

[`examples/05_five_minute_workflow.py`](examples/05_five_minute_workflow.py)
先把刚度降低 19% 的模型结果当作合成实测数据，再从名义模型出发，通过频率与 MAC
相关定位偏差并修正刚度缩放因子。脚本最后重新相关，直接显示修正前后的最大频率误差。

## Command-line interface

Install the CLI extras for coloured tables and the interactive wizard:

```bash
python -m pip install -e ".[cli]"
```

**Zero setup** — run the built-in demo (no YAML files):

```bash
openfemlab quickstart
openfemlab wizard    # menu-driven: modal, correlate, update, HTML report
```

Turn a JSON correlation or correction artifact into a browser report:

```bash
openfemlab correlate model.yaml measured.yaml -o corr.json --format json
openfemlab report corr.json -o corr.html --open
```

The CLI consumes JSON or YAML specifications and can emit tables, JSON, or
YAML. Show all commands with:

```bash
openfemlab info
openfemlab --help
openfemlab modal --help
```

The end-to-end example generates a model specification, measured modal data,
and an updating configuration:

```bash
python examples/02_model_updating_workflow.py --output-dir run
```

Use those files for the four principal commands:

```bash
# Solve and save a portable modal result.
openfemlab modal run/cantilever.yaml -n 6 \
  --normalization mass --output run/modes.yaml

# Correlate FE modes with partially instrumented measured data.
openfemlab correlate run/cantilever.yaml run/measured.yaml \
  --partial-dofs --pairing optimal --matrix \
  --require-mac 0.95 --require-frequency 2.0 \
  --output run/correlation.json

# Correlate a measured FRF against one synthesized from the damped model.
openfemlab correlate-frf measured.unv run/cantilever.yaml \
  --rayleigh 0.02 0.004 --require-frac 0.9 \
  --output run/frf-correlation.json

# Update bounded model parameters and save both model and run report.
openfemlab update run/updating.yaml \
  --output run/cantilever.updated.yaml \
  --report run/updating-report.json --strict

# Re-run the acceptance check on the corrected model.
openfemlab correlate run/cantilever.updated.yaml run/measured.yaml \
  --partial-dofs --require-mac 0.95 --require-frequency 1.0
```

`correlate-frf` takes the measurement as a UFF/UNV dataset-58 file — one record
per response channel, as a test campaign delivers it — or as the equivalent
JSON/YAML document (`frequencies_hz`, an `excitation` DOF, and one `channels`
entry per response DOF with its `real`/`imag` ordinate). It synthesizes the same
channels on the measured frequency line and reports FRAC per channel plus the
FDAC matrix; the damping may also live in the model spec as a `damping:` block
(`ratio`, `ratios`, or `alpha`/`beta`) instead of on the command line.

`update` runs the deterministic Levenberg-Marquardt loop by default and the
Bayesian (maximum-a-posteriori) one as soon as the configuration carries a
`prior` or a `noise` section:

```yaml
prior:
  std: {stiffness: 0.05, mass: 0.02}   # or a scalar, a list, variance:, covariance:
  mean: 1.0                            # optional; defaults to the starting point
noise:
  std: 0.005                           # measurement noise over the residual entries
```

Both are covariances over the updater's design space, so a `log_scaled`
parameter takes its prior on `log(factor)`. The report then gains a `bayesian`
block with the resolved prior, the noise model and the Laplace posterior
`(JᵀC_ε⁻¹J + C_p⁻¹)⁻¹`, and every parameter entry carries the posterior
standard deviation `sigma_post` next to its `sigma_prior`. A deterministic run
reports `sigma_post` too, from the least-squares covariance `σ²(JᵀJ)⁻¹`.

Global `--quiet`, `--no-color`, and `--traceback` options support scripts and
diagnostics.

## Tests and quality checks

```bash
# Complete suite
python -m pytest

# Focused numerical suites
python -m pytest tests/test_modal_solver.py tests/test_correlation.py tests/test_updating.py

# Static checks
python -m ruff check .
```

The equivalent convenience targets are `make test` and `make lint`.
See the [orchestrator report](.agent_workspace/ORCHESTRATOR_REPORT.md) for the
full delivery status and 876-test verification record.

## Benchmarks

For comparable timings, pin BLAS to one thread:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python benchmarks/bench_modal.py --repeats 7

OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python benchmarks/bench_updating.py --repeats 5 --dof 100
```

`make bench` runs both benchmarks with their default settings. Benchmark
results depend on the Python, NumPy/SciPy, BLAS, CPU, and thread configuration;
record those details when comparing runs.

## Architecture

OpenFEMLab keeps model construction and solvers separate from neutral
interchange contracts. Correlation and updating operate on portable modal data,
which allows the same workflow to drive the built-in solver or an external CAE
solver adapter. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the
module boundaries and data flow.

OpenFEMLab is licensed under the MIT License.
