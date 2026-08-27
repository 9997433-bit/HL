# Migration Guide — 0.1.0 Alpha → 0.2.0 Beta

This note covers breaking or behaviour-visible changes when upgrading from early
alpha snapshots to **`0.2.0b1`** (Round 8 + Round 9 product hardening).

## Install / version pin

```bash
python -m pip install -e ".[dev,cli,io]"
openfemlab --version   # expect 0.2.0b1
```

PyPI publication is planned for `0.2.0`; until then install from the repository
tag or wheel artifact attached to the release PR.

## Package metadata

| Item | 0.1.0 alpha | 0.2.0b1 beta |
|------|-------------|--------------|
| `Development Status` classifier | Alpha | **Beta** |
| Documented stability | “API may change anytime” | See [`STABILITY.md`](STABILITY.md) |
| Registry | partial `verified` | **104/104 verified** |

## CLI additions (non-breaking)

New commands are additive; existing scripts keep working:

| Command | Purpose |
|---------|---------|
| `openfemlab pipeline run <config.yaml>` | Six-stage correction workflow (S1–S6) |
| `openfemlab sdm scan <model>` | Stiffness spring SDM scan (AC-DYN-010) |
| `openfemlab wizard` | Menu now includes pipeline / SDM entries |

## BDF reader extensions

- **`PROD`** rod sections import into `NeutralProperty.values["A"]`.
- **`RBE2` / `RBE3`** cards round-trip via `NeutralModel.meta["bdf_preserve"]`.
  They are **not** expanded into solver constraints yet; re-analysis still uses
  the element connectivity subset.

If you previously ignored `PROD` as an unsupported card, update any custom
parsers that counted it as “skipped bulk data”.

## External Nastran driver

Set one of:

```bash
export OPENFEMLAB_NASTRAN_EXE=/path/to/nastran
# or NASTRAN_EXE / NASTRAN / `nastran` on PATH
```

`openfemlab.io.drivers.nastran.run_nastran` raises `FormatError` when no binary
is found (AC-IO-015).  CI does not require a licence.

## New examples

| Script | Topic |
|--------|-------|
| `examples/06_bdf_op2_industrial_loop.py` | BDF ↔ OP2 ↔ update ↔ export |
| `examples/07_external_nastran_loop.py` | Optional external Nastran batch |
| `examples/08_ssi_oma.py` | SSI-COV operational modal analysis |
| `examples/09_doe_sizing_screen.py` | DOE factorial → optimization design space |

## DOE → optimization bridge

Import screening helpers from the optimization layer:

```python
from openfemlab.optimization import DesignSpace, run_factorial_screen
```

They wrap `openfemlab.uq.doe` and emit design vectors compatible with
`minimize_sizing`.

## Dashboard animation

`openfemlab serve` / `--desktop` viewer exposes an **Animate** checkbox
(`dashboard/static/index.html`).  Animation is client-side sinusoidal phase
modulation of the displayed mode shape; no server API change is required.

## Deprecated / removed

Nothing was removed in `0.2.0b1`.  The following alpha-era workarounds are no
longer needed:

- Hand-rolling OP2 fixtures for industrial demos — use `examples/06` and
  `scripts/generate_op2_corpus.py`.
- Importing `FrequencyDifference` from `correlation.mac` — use
  `correlation.metrics`.

## Verification after upgrade

```bash
python -m pytest -q
python examples/05_five_minute_workflow.py
python examples/06_bdf_op2_industrial_loop.py
openfemlab quickstart
```

For OP2 corpus opt-in tests:

```bash
python scripts/generate_op2_corpus.py .corpus/op2
OPENFEMLAB_OP2_CORPUS=.corpus/op2 python -m pytest tests/test_op2_corpus.py -q
```

## Getting help

- [`USER_GUIDE_zh.md`](USER_GUIDE_zh.md) — Chinese workflow reference
- [`SOTA_GAP_ANALYSIS.md`](SOTA_GAP_ANALYSIS.md) — parity vs FEMtools / 2026 SOTA
- [`STABILITY.md`](STABILITY.md) — beta support policy
