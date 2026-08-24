# MATLAB / Octave ports (heterodyne + qtec)

Octave-compatible faithful ports of the Python packages in this repo:

| MATLAB | Python source |
|---|---|
| `homodyne/core/` | `homodyne_tracking_design/core.py` (canonical shared core: PLL, signals, filters, numpy-exact RNG) |
| `homodyne/design_params/` | `homodyne_tracking_design/design_params.py` (canonical parameter functions + constants) |
| `homodyne/ellipse/` | ellipse / Heydemann correction port |
| `homodyne/` (flat) | validator-only helpers (`hd_*`, `np_*`, `set_rng`, `vt_*`, `ve_*`) -- no DSP/param duplicates |
| `heterodyne/` | `heterodyne_tracking_design/core.py` + `design_params.py` + `validate_heterodyne.py` |
| `qtec/` | `qtec_diversity_design/speckle_multi.py` + `synth_multichannel.py` + `diversity_combine.py` + `validate_diversity_p0_p1.py` |

Every shared function exists exactly once: DSP in `homodyne/core/`,
design-parameter functions in `homodyne/design_params/`.
`homodyne_setup_path.m` adds the folders in canonical-last order, and every
validator calls it, so only one implementation is ever visible on the path.

Key sharing decision (mirrors the Python layering): `pll_carrier_regen` lives
once in `homodyne/core/` and is reused by heterodyne and qtec.  The heterodyne
Python core's PLL is a subset of the homodyne one (it lacks the audit-item-5
HOLD-state Cref decay, which only matters for `gate='auto'`); heterodyne
validation uses `gate='always'` exclusively, where both are bit-identical.
Heterodyne keeps only its own extras (`het_*` design parameters and the
IIR-window `het_residual_mode`); qtec builds its channel demodulator on the
shared PLL plus the common FIR residual window.

## Verification

Two independent layers:

1. **Golden compares** (deterministic, fast):
   `export_heterodyne_qtec_golden.py` runs the *Python* code on seeded inputs
   and writes both inputs and outputs to `golden/*.mat` (MAT v4, loadable by
   Octave without any package).  `heterodyne/compare_heterodyne_golden.m` and
   `qtec/compare_qtec_golden.m` feed the exported inputs through the ported
   functions and compare numerically (PLL phase agrees to ~1e-14 rad; the
   gate-auto 3-state trajectory matches exactly).  Randomness never crosses
   the language boundary.
2. **Statistical validators** (slow, Octave RNG):
   `heterodyne/validate_heterodyne.m` (H0–H6, checks C01–C62) and
   `qtec/validate_diversity_p0_p1.m` (P0+P1, checks Q0-1..Q1-5) are full
   ports of the Python validators; they seed Octave's own RNG with the same
   seed numbers (PCG64 streams cannot be reproduced) and assert the same
   statistical bounds.

Run everything:

```sh
cd matlab
octave --no-gui --eval "rc = run_all_verify(); exit(rc)"          # 'compare': golden compares only (fast)
octave --no-gui --eval "rc = run_all_verify('full'); exit(rc)"    # + ALL validators (~10 min)
```

`run_all_verify('compare')` (the default) runs the golden compares:
`compare_heterodyne_golden`, `compare_qtec_golden`, the homodyne core smoke
(`compare_with_python`) and `compare_validate` (committed per-validator
golden metric pairs).

`run_all_verify('full')` first re-runs ALL statistical validators --
`validate_heterodyne`, `validate_diversity_p0_p1`, `validate_tracking`,
`validate_off_mode`, `validate_zeta_sweep`, `validate_residual_alignment`,
`validate_app_30ms_100khz` and the three ellipse validators -- and then the
golden compares; the homodyne validators rewrite their
`golden/validate_*_mat.mat` metrics, so the final `compare_validate` checks
the fresh outputs against the committed Python goldens.

## MEX kernels are optional (pure-M fallback)

Two optional compiled kernels accelerate the homodyne validators:
`homodyne/core/homodyne_rng_mex.c` (numpy-exact RNG: PCG64 + ziggurat) and
`homodyne/core/pll_core_mex.c` (PLL scalar loop).  `ensure_kernels` tries to
build them on first use (Octave: `mkoctfile --mex`; MATLAB: `mex`); if no
compiler is available it prints a warning and everything transparently falls
back to the pure-M twins `np_rng_m.m` / `pll_core_m.m`, which produce
**bit-identical** results (only slower).  No `.mex` binaries are committed
(they are platform-specific; see `.gitignore`); set `HOMODYNE_NO_MEX=1` to
force the pure-M paths even when the kernels are compiled.

### Windows / MATLAB notes

- Runs on MATLAB R2020b+ and GNU Octave >= 8; no toolboxes needed.
- The pure-M path is the portable default: nothing needs to be compiled to
  run the validators or the golden compares on Windows.
- Optional MEX speedup on Windows MATLAB requires a GCC-compatible compiler
  (install the *MATLAB Support for MinGW-w64 C/C++ Compiler* add-on and
  select it with `mex -setup`).  MSVC cannot build `homodyne_rng_mex.c`
  because it lacks the `__uint128_t` type.
- On Octave (any platform) `mkoctfile --mex` with the bundled GCC works.

## Homodyne validators (full ports)

The five Python homodyne validators are ported one-to-one at the `matlab/`
top level; the three ellipse-correction validators live in `matlab/homodyne/`.
All of them draw noise through the numpy-exact RNG (`np_rng_new`: the
`homodyne_rng_mex` kernel or the pure-M `np_rng_m` fallback, PCG64 +
ziggurat), so every noise realization is bit-identical to the Python
reference, and each script saves its key metrics to
`golden/validate_<name>_mat.mat`:

| Script | Checks | Python source |
|---|---|---|
| `validate_tracking.m` | V1–V4 (C1–C7) | `validate_tracking.py` |
| `validate_off_mode.m` | O1–O6b | `validate_off_mode.py` |
| `validate_zeta_sweep.m` | Z0–Z3 | `validate_zeta_sweep.py` |
| `validate_residual_alignment.m` | 18 combos, <1 pp | `validate_residual_alignment.py` |
| `validate_app_30ms_100khz.m` | A1–A8 (S/E/G/H/F/D/N) | `validate_app_30ms_100khz.py` |
| `homodyne/validate_ellipse_small_disp.m` | B0–B4 + spec assertion | `validate_ellipse_small_disp.py` |
| `homodyne/validate_ellipse_dynamic.m` | B0/B1/B2/B7 assertion | `validate_ellipse_dynamic.py` |
| `homodyne/validate_ellipse_audit.m` | review items 1–4 | `validate_ellipse_audit.py` |

Each validator prints the same report as its Python counterpart, raises an
error (nonzero exit code) on any failing check, e.g.:

```sh
cd matlab
octave --no-gui --eval "validate_tracking"
octave --no-gui --eval "cd homodyne; rc = validate_ellipse_small_disp(); exit(rc)"
```

`run_all_verify('full')` runs all of them automatically (plus the ellipse
validators: small_disp E-checks, dynamic D-checks, audit items 1–4).

### Cross-language golden compare (`compare_validate`)

`export_validate_golden.py` runs the *Python* validators (tracking, off_mode,
zeta_sweep, residual_alignment, app_30ms_100khz) with the exact seeds/criteria
of their `main()` and writes `golden/validate_<name>_py.mat` (~2–3 min,
needs numpy + scipy).  The MATLAB validators write the matching
`golden/validate_<name>_mat.mat`.  `compare_validate.m` then compares each
pair metric-by-metric:

- check outcomes (`checks_ok`) must match **exactly**;
- `det` group (deterministic grids, guard limits, phi_err tables): 1e-6
  relative tolerance;
- `noisy` group (simulation statistics): 1% relative tolerance;
- a few threshold-quantized metrics (event counts, first-crossing times) get
  documented absolute tolerances because a 1e-13 FP difference can move a
  threshold crossing by a whole count/sample.

```sh
cd matlab
python3 export_validate_golden.py           # refresh the Python side (optional)
octave --no-gui --eval "compare_validate"   # errors on any mismatch
```

Both sides of the golden pairs are committed under `golden/`, so
`compare_validate` runs out of the box without Python.

The golden `.mat` files are committed under `golden/`; `run_all_verify`
regenerates the heterodyne/qtec ones automatically (needs `python3` + numpy)
when missing.  It also runs the homodyne core smoke compare
(`compare_with_python`, LCG-based bit-exact goldens) when present.

Individual entry points:

```sh
octave --no-gui --eval "rc = validate_heterodyne(); exit(rc)"        # in matlab/heterodyne
octave --no-gui --eval "rc = validate_diversity_p0_p1(); exit(rc)"   # in matlab/qtec
```

## Porting conventions

- One function per `.m` file; core DSP helpers keep their Python names
  (`pll_carrier_regen`, `fir_lp_same`, ...); package-specific design-parameter
  functions get `hd_` (homodyne) / `het_` (heterodyne) prefixes because
  MATLAB's namespace is flat and the packages define e.g. `b_loop` /
  `loop_error_mag` with different constants.
- `pll_carrier_regen(z, fs, fn, Nhat, opts)` takes an options struct whose
  fields mirror the Python keyword arguments.
- Python `rng` arguments: the deterministic golden path feeds exported arrays
  (or the portable LCG in `homodyne/core/`); the statistical validators use
  the global Octave RNG, seeded with `set_rng(seed)` (defined in `homodyne/`)
  and passed into core functions as `@(k) randn(k, 1)` handles.
- Python `int()` truncation is ported as `floor()`; the quantile convention of
  the Python `stats()` helper (ceil-based, clipped) is reproduced exactly.
- Everything runs on plain GNU Octave >= 8 (no toolboxes, no packages).
