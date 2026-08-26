---
name: openfemlab-workflow
description: Run OpenFEMLab modal analysis, FE-test correlation, model updating, and HTML reports via CLI. Use when the user asks about OpenFEMLab, modal MAC, model updating, sensor placement, MPE from FRFs, or wants a quick structural dynamics demo without writing Python.
---

# OpenFEMLab workflow skill

OpenFEMLab is a Python CAE toolkit (modal solve → correlate → update). Prefer the **CLI** for user-facing tasks; use Python only when the CLI cannot express the workflow.

## First-time users (no files)

```bash
pip install -e ".[cli,plot,io]"
openfemlab quickstart
openfemlab wizard
```

`quickstart` runs a two-DOF demo in ~10s. `wizard` is an interactive menu.

## Standard CLI paths

| Goal | Command |
|------|---------|
| Modal analysis | `openfemlab modal model.yaml -n 8` |
| Correlate | `openfemlab correlate model.yaml measured.yaml` |
| Save JSON + HTML | `correlate ... -o corr.json --format json` then `openfemlab report corr.json -o corr.html --open` |
| Update parameters | `openfemlab update updating.yaml -o model.updated.yaml` |
| FRF correlation | `openfemlab correlate-frf measured.unv model.yaml` |
| Package overview | `openfemlab info` |

Model and updating specs are JSON or YAML. See `examples/` and `docs/USER_GUIDE_zh.md`.

## Python API (when scripting)

```python
from openfemlab import ModalSolver, correlation_summary, update_model
from openfemlab.mesh.simple import beam_mesh
```

Full workflow example: `examples/05_five_minute_workflow.py`.

## Modules map

- `solver` — modal and damped dynamics / FRF
- `correlation` — MAC, pairing, reports
- `updating` — GN/LM updater, Bayesian MAP, **FRF updating** (`update_model_frf`)
- `workflow` — six-stage correction pipeline
- `mpe` — extract modes from measured FRFs (LSCF)
- `pretest` — Effective Independence sensor placement
- `io` — JSON/YAML, UFF, BDF, meshio; `io.op2.read_op2_modes` for Nastran OP2 modes

## When NOT to use this skill

- General FEM pre/post unrelated to OpenFEMLab
- Installing Nastran or commercial solvers
- Writing new acceptance criteria (see `docs/ACCEPTANCE_CRITERIA.md` in-repo)

## Reporting to humans

After `correlate` or `update` with JSON output, always suggest:

```bash
openfemlab report artifact.json -o review.html --open
```

HTML reports are self-contained (no server).
