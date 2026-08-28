# OpenFEMLab 0.3.3 Release Notes

**Date:** 2026-08-28  
**Tag:** `v0.3.3`

## Highlights

This release merges the R10–R20 development stack into `main`, completing the
scriptable CAE core and a desktop GUI shell for end-to-end workflows.

### Core platform (R10–R17)

- RBE2/RBE3 assembly, TRI3/shell/solid elements, static analysis
- SIMP topology optimization (2D/3D), density filter, Heaviside projection
- Multi-load topopt, VTU export, native RST/ODB readers, FRD/locator I/O
- Golden correlation CI, geometry mapping, multi-load specs

### Advanced analysis (R18–R19)

- Full Craig-Bampton CMS + `reduce cms` CLI
- Stress-constrained SIMP (p-norm von Mises)
- MMA topology optimizer (`--optimizer mma`)
- Superelement NPZ export (`reduce cms --output`)
- BDF `MOMENT` card support

### Desktop product (R20)

- **`openfemlab desktop`** — native window via pywebview
- Project navigator, workflow buttons (modal → correlate → update → topopt)
- Job console with live CLI output (`POST /api/run`)
- `project init` generates sample measurement for immediate correlate闭环

## Upgrade

```bash
pip install -U 'openfemlab[cli,plot,gui]'
openfemlab --version   # 0.3.3
```

## Quick validation

```bash
openfemlab project init /tmp/ofl-demo
cd /tmp/ofl-demo
openfemlab modal models/cantilever.yaml -n 6 -o reports/modes.json --format json
openfemlab correlate models/cantilever.yaml measurements/test.yaml \
  -o reports/corr.json --format json
openfemlab desktop --browser
```

## Superseded draft PRs

PRs #29–#38 are superseded by this single merge (#39 / R20 branch).
