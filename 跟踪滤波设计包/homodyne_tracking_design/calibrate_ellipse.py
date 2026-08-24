#!/usr/bin/env python3
"""Offline ellipse calibration tool for homodyne IQ.

Reads I/Q from CSV or numpy .npz, runs block-mean drift arc (method B) or
direct Heydemann (method A/C), writes NVRAM JSON.

Example:
  python calibrate_ellipse.py --csv iq_data.csv --fs 2.5e6 --block-ms 100 \\
      --out ellipse_cal.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date

import numpy as np

from ellipse_correction import heydemann_fit, fit_arc_gated, ARC_MIN

PAR_FIELDS = ('p', 'q', 'A', 'B', 'delta')


def load_iq(path: str):
    if path.endswith('.npz'):
        d = np.load(path)
        u = np.asarray(d['u'], float).ravel()
        v = np.asarray(d['v'], float).ravel()
    elif path.endswith('.csv'):
        arr = np.loadtxt(path, delimiter=',', skiprows=1)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        u, v = arr[:, 0], arr[:, 1]
    else:
        raise ValueError('unsupported format: use .csv or .npz')
    return u, v


def block_means(u, v, nb):
    K = u.size // nb
    mu = np.zeros((K, 2))
    pw = np.zeros(K)
    for k in range(K):
        sl = slice(k * nb, (k + 1) * nb)
        mu[k, 0] = u[sl].mean()
        mu[k, 1] = v[sl].mean()
        pw[k] = u[sl].mean() ** 2 + v[sl].mean() ** 2
    return mu, pw


def gate_blocks(mu, pw, frac=0.05):
    med = np.median(pw)
    lo, hi = med * (1 - frac), med * (1 + frac)
    m = (pw >= lo) & (pw <= hi)
    return mu[m, 0], mu[m, 1], int(m.sum())


def calibrate_drift(u, v, fs, block_ms=100.0, gate_frac=0.05):
    nb = max(64, int(block_ms * 1e-3 * fs))
    mu, pw = block_means(u, v, nb)
    bu, bv, n = gate_blocks(mu, pw, gate_frac)
    if n < 12:
        raise RuntimeError(f'only {n} gated blocks (need >=12); extend record or relax gate')
    par, res = heydemann_fit(bu, bv)
    return par, res, dict(method='drift_block_mean', n_blocks=n, block_ms=block_ms)


def calibrate_direct(u, v, max_pts=8000):
    step = max(1, u.size // max_pts)
    par, res = heydemann_fit(u[::step], v[::step])
    return par, res, dict(method='direct', n_samples=u.size // step)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Homodyne IQ ellipse calibration')
    ap.add_argument('--csv', help='CSV with columns u,v (header row skipped)')
    ap.add_argument('--npz', help='NPZ with arrays u, v')
    ap.add_argument('--fs', type=float, default=2.5e6, help='sample rate (Hz)')
    ap.add_argument('--mode', choices=('drift', 'direct'), default='drift',
                    help='drift=block-mean arc (no large vib); direct=full record')
    ap.add_argument('--block-ms', type=float, default=100.0)
    ap.add_argument('--gate-frac', type=float, default=0.05)
    ap.add_argument('--lambda-nm', type=float, default=1550.0)
    ap.add_argument('--out', default='ellipse_cal.json')
    args = ap.parse_args(argv)

    path = args.csv or args.npz
    if not path:
        ap.error('provide --csv or --npz')
    u, v = load_iq(path)
    if args.mode == 'drift':
        par, res, meta = calibrate_drift(u, v, args.fs, args.block_ms, args.gate_frac)
    else:
        par, res, meta = calibrate_direct(u, v)

    ok = res.get('ok', False)
    lines = [
        f'method: {meta["method"]}',
        f'ok: {ok}  arc={res.get("arc", float("nan")):.3f} rad  '
        f'rms={res.get("rms", float("nan")):.4f}  cond={res.get("design_cond", float("nan")):.2e}',
        f'A={par["A"]:.6f}  B={par["B"]:.6f}  g=B/A={par["B"]/par["A"]:.6f}',
        f'epsilon={par["B"]/par["A"]-1:+.4f}  delta={math.degrees(par["delta"]):.3f} deg',
        f'p={par["p"]:.6f}  q={par["q"]:.6f}  (p,q not saved to NVRAM)',
    ]
    print('\n'.join(lines))

    if not ok:
        print('\nFAIL: arc < pi/2 or fit invalid — extend drift time or check amplitude stability',
              file=sys.stderr)
        return 1

    nvram = {
        'version': 1,
        'lambda_nm': args.lambda_nm,
        'cal_method': meta['method'],
        'cal_date': str(date.today()),
        'A': par['A'],
        'B': par['B'],
        'delta_rad': par['delta'],
        'epsilon': par['B'] / par['A'] - 1,
        'fit_arc_rad': res['arc'],
        'fit_rms': res['rms'],
    }
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(nvram, f, indent=2, ensure_ascii=False)
    print(f'\nNVRAM written: {args.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
