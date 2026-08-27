# OpenFEMLab Beta Stability Policy

**Version:** `0.2.0b1` · **Status:** Public beta · **Date:** 2026-08-27

OpenFEMLab `0.2.x` beta releases target engineers who want a reproducible,
solver-independent modal correlation and model-updating workflow.  Beta means
the core workflow is exercised end-to-end in CI, but schema and CLI details may
still change before `1.0.0`.

## What “beta” guarantees

| Area | Commitment |
|------|------------|
| Core workflow | Model → modal solve → correlate → update → validate is covered by **104/104** acceptance criteria (`verified`) |
| Interchange | Native JSON/YAML schemas are versioned; readers reject unknown major versions |
| CLI gates | `--require-*` exit codes and JSON report shapes are treated as stable within `0.2.x` |
| Industrial I/O | BDF subset (`GRID`, connectivity, `MAT1`, `PSHELL`/`PSOLID`/`PROD`, preserved `RBE2`/`RBE3`), OP2 geometry/modes, UFF-55/58 |
| Performance | AC-PERF-001 (50k-DOF sparse modal, no full densification, ≤120 s) enforced in CI |

## What may still change before 1.0

- Minor CLI flag renames or additional subcommands (`pipeline`, `sdm`, `wizard` menus)
- Optional dependency groups (`[io]`, `[plot]`, `[gui]`, `[accel]`)
- Dashboard HTML layout and animation controls
- External solver driver environment variables (names are documented, behaviour is stable)

## Supported Python versions

Python **3.10**, **3.11**, and **3.12** (see `pyproject.toml` classifiers).

## Reporting issues

File reproducible cases with:

1. `openfemlab --version`
2. Minimal model/spec YAML or Python snippet
3. Expected vs actual correlation or updating metric
4. Full pytest output when reporting a regression

## Release cadence

- **`0.2.0b1`** — Round 9 product hardening (this document, migration guide, examples 07–09)
- **`0.2.0`** — first non-beta when migration notes are empty for two consecutive minor releases
- **`1.0.0`** — semver-stable schemas and CLI, documented LTS support window

See also [`MIGRATION.md`](MIGRATION.md) for upgrade steps from `0.1.0` alpha builds.
