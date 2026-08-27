# OP2 corpus validation

OpenFEMLab validates the OP2 reader against two layers:

1. **Synthetic fixtures** (`tests/_op2.py`) — always run in CI.
2. **Opt-in corpus** — real MSC/NX output when available.

## Generate the synthetic corpus

```bash
python scripts/generate_op2_corpus.py .corpus/op2
export OPENFEMLAB_OP2_CORPUS=.corpus/op2
python3 -m pytest tests/test_op2_corpus.py -q
```

The generator writes rod, CBAR, rotated-grid, shell-property, and quad4 samples.
Geometry OP2 files include a same-stem `.bdf` sidecar for bulk-data parity.

## Real Nastran output

Real OP2 files require a Nastran licence and cannot be committed here. To run
the corpus gate against production solver output:

1. Export OP2 from MSC Nastran or Siemens NX for a small model (rod, beam,
   shell, or quad4) with `PARAM,POST,-1`.
2. Place the files under a directory outside the repository. For geometry
   parity, add a matching bulk-data deck with the same stem, e.g.
   `panel_modes.op2` and `panel_modes.bdf`.
3. Point the environment variable at that directory:

```bash
export OPENFEMLAB_OP2_CORPUS=/path/to/nastran/op2/files
python3 -m pytest tests/test_op2_corpus.py -q
```

Organize vendor-specific trees as you like (`msc/`, `nx/`, etc.); the corpus
tests walk all `*.op2` files recursively.

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
