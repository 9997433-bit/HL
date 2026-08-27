# OP2 corpus validation

OpenFEMLab validates the OP2 reader against two layers:

1. **Synthetic fixtures** (`tests/_op2.py`) — always run in CI.
2. **Opt-in corpus** — real MSC/NX output when available.

## Corpus layout

The corpus root carries a vendor manifest:

```text
/path/to/corpus/
  manifest.json
  msc/
    panel_geometry.op2
    panel_geometry.bdf
  nx/
    bracket_modes.op2
```

For CI-generated fixtures the generator writes vendor trees under
`synthetic/msc` and `synthetic/nx`:

```text
.corpus/op2/
  manifest.json
  synthetic/msc/
    rod_geometry.op2
    rod_geometry.bdf
    ...
  synthetic/nx/
    rod_modes.op2
    shell_properties.op2
    ...
```

`manifest.json` schema version `1.0` lists every vendor directory and the
sample filenames it is expected to contain. The acceptance gate AC-IO-016
checks that layout for generated corpora; opt-in tests in
`tests/test_op2_corpus.py` walk every `*.op2` file recursively regardless of
vendor folder.

## Generate the synthetic corpus

```bash
python scripts/generate_op2_corpus.py .corpus/op2
export OPENFEMLAB_OP2_CORPUS=.corpus/op2
python3 -m pytest tests/test_op2_corpus.py -q
```

The generator writes rod, CBAR, rotated-grid, shell-property, and quad4 samples
split across the synthetic MSC/NX vendor trees. Geometry OP2 files include a
same-stem `.bdf` sidecar for bulk-data parity.

## Real Nastran output

Real OP2 files require a Nastran licence and cannot be committed here. To run
the corpus gate against production solver output:

1. Export OP2 from MSC Nastran or Siemens NX for a small model (rod, beam,
   shell, or quad4) with `PARAM,POST,-1`.
2. Place MSC output under `<corpus>/msc/` and NX output under `<corpus>/nx/`.
   For geometry parity, add a matching bulk-data deck with the same stem, e.g.
   `panel_modes.op2` and `panel_modes.bdf`.
3. Add or update `manifest.json` at the corpus root:

```json
{
  "schema_version": "1.0",
  "vendors": {
    "msc": {
      "solver": "MSC Nastran",
      "description": "Production rod/beam sample",
      "samples": ["panel_geometry.op2"]
    },
    "nx": {
      "solver": "Siemens NX Nastran",
      "description": "Production shell sample",
      "samples": ["bracket_modes.op2"]
    }
  }
}
```

4. Point the environment variable at the corpus root:

```bash
export OPENFEMLAB_OP2_CORPUS=/path/to/nastran/op2/files
python3 -m pytest tests/test_op2_corpus.py -q
```

The corpus tests list tables, read geometry when `GEOM1` is present, read modes
when `LAMA` is present, and compare geometry to a sidecar BDF when one exists.
Failures name the file and the missing contract.

## Rust assembly extension (optional)

```bash
pip install maturin
maturin develop --release -m rust/openfemlab_asm/Cargo.toml
export OPENFEMLAB_USE_RUST_ASM=1
python3 -m pytest tests/test_rust_assembly.py tests/acceptance/test_performance.py -k AC-PERF-006 -q
```

When the extension is absent, AC-PERF-006 skips and Python assembly remains the
supported path.
