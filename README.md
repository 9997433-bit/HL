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
- A dependency-free Nastran BDF reader for the supported `GRID`, `CROD`, and
  `MAT1` subset in free-field and small fixed-field form.

## Installation

OpenFEMLab requires Python 3.10 or newer.

```bash
python -m pip install -e .
```

For contributor tools, rich CLI output, and the benchmark scripts:

```bash
python -m pip install -e ".[dev,cli]"
```

The optional `io` extra installs `meshio` for future format adapters:

```bash
python -m pip install -e ".[io]"
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

## Command-line interface

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

Use those files for the three principal commands:

```bash
# Solve and save a portable modal result.
openfemlab modal run/cantilever.yaml -n 6 \
  --normalization mass --output run/modes.yaml

# Correlate FE modes with partially instrumented measured data.
openfemlab correlate run/cantilever.yaml run/measured.yaml \
  --partial-dofs --pairing optimal --matrix \
  --require-mac 0.95 --require-frequency 2.0 \
  --output run/correlation.json

# Update bounded model parameters and save both model and run report.
openfemlab update run/updating.yaml \
  --output run/cantilever.updated.yaml \
  --report run/updating-report.json --strict

# Re-run the acceptance check on the corrected model.
openfemlab correlate run/cantilever.updated.yaml run/measured.yaml \
  --partial-dofs --require-mac 0.95 --require-frequency 1.0
```

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
