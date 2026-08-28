# OpenFEMLab Stability Policy

**Version:** `0.3.1` · **Status:** Stable release · **Date:** 2026-08-28

OpenFEMLab `0.3.1` adds full Craig-Bampton fixed-interface modes and a first
stress-aware SIMP topology path with p-norm von Mises aggregation.

## What `0.2.x` guarantees

| Area | Commitment |
|------|------------|
| Core workflow | Model → modal solve → correlate → update → validate is covered by **104/104** acceptance criteria (`verified`) |
| Interchange | Native JSON/YAML schemas are versioned; readers reject unknown major versions |
| CLI gates | `--require-*` exit codes and JSON report shapes are treated as stable within `0.2.x` |
| Industrial I/O | BDF subset, OP2, UFF-55/58, FRD, **RST**, **ODB sidecar**, assembled RBE2/RBE3 |
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

- **`0.2.0b1`** — Round 9 product hardening (beta policy, migration guide, examples 07–09)
- **`0.2.0`** — Round 10: solver-assembled `RBE2`, example 10, first non-beta `0.2.x`
- **`0.2.1`** — Round 11: `RBE3` assembly, `PBAR`, shape-morph evaluation, wizard FRF/bench
- **`0.2.2`** — Round 12: TRI3/CTRIA3, SPC1/CONM2, truss geometric `dK/da`, driver dry-run
- **`0.2.3`** — Round 13: static solver + FORCE, UFF→MPE CLI, RSM, shell `dK/da`, FRD/locator
- **`0.3.1`** — Round 18: Craig-Bampton CMS modes, stress-constrained topopt
- **`0.3.0`** — Round 17: multi-load topopt, VTU export, geometry map, CMS skeleton, CI golden
- **`0.2.6`** — Round 16: Heaviside projection, `tet_block`/`hex_block` topopt specs
- **`0.2.5`** — Round 15: 3D SIMP topology (TET4/HEX8), Sigmund density filter
- **`0.2.4`** — Round 14: SIMP topology (`topopt`), native RST reader, ODB NPZ + extract
- **`1.0.0`** — semver-stable schemas and CLI, documented LTS support window

See also [`MIGRATION.md`](MIGRATION.md) for upgrade steps from `0.1.0` alpha builds.
