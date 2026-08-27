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

The generator writes rod geometry, modes, rotated grids, shell properties, and
quad4 connectivity samples.

## Real Nastran output

Real OP2 files require a Nastran licence and cannot be committed here. To run
the corpus gate against production solver output:

1. Export OP2 from MSC Nastran or Siemens NX for a small model (rod, shell,
   or quad4) with `PARAM,POST,-1`.
2. Place the files under a directory outside the repository.
3. Point the environment variable at that directory:

```bash
export OPENFEMLAB_OP2_CORPUS=/path/to/nastran/op2/files
python3 -m pytest tests/test_op2_corpus.py -q
```

The corpus tests list tables, read geometry when `GEOM1` is present, and read
modes when `LAMA` is present. Failures name the file and the missing contract.

## Rust assembly extension (optional)

```bash
pip install maturin
maturin develop --release -m rust/openfemlab_asm/Cargo.toml
python3 -m pytest tests/test_rust_assembly.py -q
```

When the extension is absent, the spike test skips and Python assembly remains
the supported path.
