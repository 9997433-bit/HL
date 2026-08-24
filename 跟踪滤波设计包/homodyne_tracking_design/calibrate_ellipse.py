#!/usr/bin/env python3
"""Offline ellipse calibration tool for homodyne IQ."""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date

import numpy as np

from ellipse_correction import (
    heydemann_fit, heydemann_apply, arc_span_corrected, FIT_RMS_MAX,
)

BOOTSTRAP_PAR = dict(p=0.0, q=0.0, A=1.0, B=1.0, delta=0.0)


def load_iq(path: str):
    if path.endswith('.npz'):
        d = np.load(path)
        return np.asarray(d['u'], float).ravel(), np.asarray(d['v'], float).ravel()
    if path.endswith('.csv'):
        arr = np.loadtxt(path, delimiter=',', skiprows=1)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        return arr[:, 0], arr[:, 1]
    raise ValueError('use .csv or .npz')


def block_means(u, v, nb):
    K = u.size // nb
    mu = np.zeros((K, 2))
    for k in range(K):
        sl = slice(k * nb, (k + 1) * nb)
        mu[k, 0] = u[sl].mean()
        mu[k, 1] = v[sl].mean()
    return mu


def gate_blocks_circular(mu, par, frac=0.05):
    """Gate block means by |z| after circularising with `par` (audit item 3)."""
    _, _, z = heydemann_apply(mu[:, 0], mu[:, 1], par)
    rho = np.abs(z)
    med = max(float(np.median(rho)), 1e-12)
    m = (rho >= med * (1 - frac)) & (rho <= med * (1 + frac))
    return mu[m, 0], mu[m, 1], int(m.sum())


def calibrate_drift(u, v, fs, block_ms=100.0, gate_frac=0.05, holdout_frac=0.3):
    """Two-pass drift-arc calibration: coarse fit → circularise-gate → refit.

    The record is split chronologically: the first (1 - holdout_frac) of the
    block means form the fit segment; the last holdout_frac are NEVER seen by
    either fit pass and validate that the calibration generalises.  The
    fitted parameters are applied to the held-out block means and the
    validation coverage arc / circularity rms are reported (val_arc /
    val_rms in res).  val_rms above FIT_RMS_MAX rejects the calibration
    (a fit that only circularises its own training arc must not reach
    NVRAM); val_arc is informational -- a short held-out tail legitimately
    covers a small arc.
    """
    if not 0.0 <= holdout_frac < 1.0:
        raise ValueError(f'holdout_frac={holdout_frac} not in [0, 1)')
    nb = max(64, int(block_ms * 1e-3 * fs))
    mu = block_means(u, v, nb)
    n_hold = int(round(mu.shape[0] * holdout_frac))
    mu_fit, mu_val = mu[:mu.shape[0] - n_hold], mu[mu.shape[0] - n_hold:]
    if mu_fit.shape[0] < 12:
        raise RuntimeError(f'only {mu_fit.shape[0]} fit blocks after holdout '
                           f'split; extend record')

    # Pass 1: bootstrap p,q = first block mean, ungated / loose gate
    boot = dict(BOOTSTRAP_PAR)
    boot['p'] = float(mu_fit[0, 0])
    boot['q'] = float(mu_fit[0, 1])
    bu, bv, n = gate_blocks_circular(mu_fit, boot, frac=max(gate_frac * 2, 0.10))
    if n < 12:
        bu, bv = mu_fit[:, 0], mu_fit[:, 1]
        n = mu_fit.shape[0]
    coarse, _ = heydemann_fit(bu, bv)

    # Pass 2: circularise with coarse parameters, tight gate, refit
    bu, bv, n = gate_blocks_circular(mu_fit, coarse, frac=gate_frac)
    if n < 12:
        bu, bv, n = gate_blocks_circular(mu_fit, coarse, frac=2 * gate_frac)
    if n < 12:
        raise RuntimeError(f'only {n} gated blocks after circularise; extend record')
    par, res = heydemann_fit(bu, bv)

    # Held-out validation: apply (never refit) on the unseen tail blocks.
    res['val_arc'] = float('nan')
    res['val_rms'] = float('nan')
    if mu_val.shape[0] and res.get('ok'):
        _, _, zv = heydemann_apply(mu_val[:, 0], mu_val[:, 1], par)
        res['val_rms'] = float(np.sqrt(np.mean((np.abs(zv) - 1.0) ** 2)))
        res['val_arc'] = arc_span_corrected(mu_val[:, 0], mu_val[:, 1], par)
        if res['val_rms'] > FIT_RMS_MAX:
            res['ok'] = False
            res.setdefault('reject_reasons', []).append(
                f'holdout rms={res["val_rms"]:.4f} > {FIT_RMS_MAX}')
            res['msg'] = '; '.join(res['reject_reasons'])
    return par, res, dict(method='drift_block_mean_2pass', n_blocks=n,
                          n_blocks_holdout=int(mu_val.shape[0]),
                          holdout_frac=holdout_frac,
                          block_ms=block_ms, gate_frac=gate_frac)


def calibrate_direct(u, v, max_pts=8000):
    step = max(1, u.size // max_pts)
    return (*heydemann_fit(u[::step], v[::step]),
            dict(method='direct', n_samples=u.size // step))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv')
    ap.add_argument('--npz')
    ap.add_argument('--fs', type=float, default=2.5e6)
    ap.add_argument('--mode', choices=('drift', 'direct'), default='drift')
    ap.add_argument('--block-ms', type=float, default=100.0)
    ap.add_argument('--gate-frac', type=float, default=0.05)
    ap.add_argument('--holdout-frac', type=float, default=0.3,
                    help='drift mode: fraction of trailing blocks held out '
                         'for validation (fit uses the leading 1-frac)')
    ap.add_argument('--lambda-nm', type=float, default=1550.0)
    ap.add_argument('--out', default='ellipse_cal.json')
    args = ap.parse_args(argv)
    path = args.csv or args.npz
    if not path:
        ap.error('provide --csv or --npz')
    u, v = load_iq(path)
    if args.mode == 'drift':
        par, res, meta = calibrate_drift(u, v, args.fs, args.block_ms,
                                         args.gate_frac, args.holdout_frac)
    else:
        par, res, meta = calibrate_direct(u, v)
    print(f'ok={res["ok"]} arc={res.get("arc", float("nan")):.3f} rms={res.get("rms", float("nan")):.4f}')
    if math.isfinite(res.get('val_rms', float('nan'))):
        print(f'holdout({meta["n_blocks_holdout"]} blocks, '
              f'{100 * meta["holdout_frac"]:.0f}%): '
              f'val_arc={res["val_arc"]:.3f} val_rms={res["val_rms"]:.4f}')
    if res.get('reject_reasons'):
        print('reject:', res['reject_reasons'])
    if not res['ok']:
        return 1
    nvram = dict(version=1, lambda_nm=args.lambda_nm, cal_method=meta['method'],
                 cal_date=str(date.today()), A=par['A'], B=par['B'],
                 delta_rad=par['delta'], epsilon=par['B'] / par['A'] - 1,
                 fit_arc_rad=res['arc'], fit_rms=res['rms'])
    if math.isfinite(res.get('val_rms', float('nan'))):
        nvram.update(holdout_frac=meta['holdout_frac'],
                     val_arc_rad=res['val_arc'], val_rms=res['val_rms'])
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(nvram, f, indent=2)
    print(f'written {args.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
