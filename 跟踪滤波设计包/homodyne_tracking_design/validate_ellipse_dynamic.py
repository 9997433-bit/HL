#!/usr/bin/env python3
"""Dynamic workflow ellipse correction — no dedicated calibration pause."""
from __future__ import annotations

import math
import sys
import time

import numpy as np

from core import welch_psd
from ellipse_correction import heydemann_fit, heydemann_apply, fit_arc_gated, OnlineBiasTracker

LAMBDA = 1550e-9
FS = 2.5e6
T_TRIM = 0.05
EPS_HW = -0.10
DEL_HW = 4.5 * math.pi / 180
GI, GQ = 1.0, 1.0 + EPS_HW
P_OFF0, Q_OFF = 0.06, -0.05
P_DRIFT = 0.008
FRINGE_RATE = 1.2

PHASES = [
    dict(name='反光膜大振', t0=0.0, dur=0.8, A=500e-9, f0=200.0, R=1.0, snr_db=35),
    dict(name='黑面小振', t0=0.8, dur=0.8, A=50e-9, f0=100.0, R=0.08, snr_db=22),
    dict(name='远距小振', t0=1.6, dur=0.8, A=80e-9, f0=100.0, R=0.03, snr_db=18),
]
T_TOTAL = 2.4


def movmean(x, n):
    n = max(1, int(n))
    h = n // 2
    c = np.concatenate(([0.0], np.cumsum(x)))
    i = np.arange(x.size)
    lo, hi = np.clip(i - h, 0, None), np.clip(i + h + 1, None, x.size)
    return (c[hi] - c[lo]) / (hi - lo)


def phase_cum(z):
    d = np.angle(z[1:] * np.conj(z[:-1]))
    return np.concatenate(([0.0], np.cumsum(d)))


def to_disp(ph):
    return ph * LAMBDA / (4 * math.pi)


def synth_record(rng):
    N = int(T_TOTAL * FS)
    t = np.arange(N) / FS
    u = np.zeros(N)
    v = np.zeros(N)
    x_true = np.zeros(N)
    psi = 2 * math.pi * FRINGE_RATE * t
    p_t = P_OFF0 + P_DRIFT * t / T_TOTAL
    for ph in PHASES:
        mask = (t >= ph['t0']) & (t < ph['t0'] + ph['dur'])
        idx = np.where(mask)[0]
        tt = t[idx]
        x = ph['A'] * np.sin(2 * math.pi * ph['f0'] * tt)
        phi = (4 * math.pi / LAMBDA) * x + psi[idx]
        R = ph['R']
        cI, cQ = GI * R * np.cos(phi), GQ * R * np.sin(phi + DEL_HW)
        s2 = float(np.mean(cI ** 2 + cQ ** 2)) / 10 ** (ph['snr_db'] / 10)
        u[idx] = cI + p_t[idx] + math.sqrt(s2 / 2) * rng.standard_normal(idx.size)
        v[idx] = cQ + Q_OFF + math.sqrt(s2 / 2) * rng.standard_normal(idx.size)
        x_true[idx] = x
    return dict(t=t, u=u, v=v, x_ref=x_true)


def metrics(x_est, x_ref, t, f0, sel):
    ts, xs, xr = t[sel], x_est[sel], x_ref[sel]
    xs, xr = xs - xs.mean(), xr - xr.mean()
    c_est = 2 * np.mean(xs * np.exp(-1j * 2 * math.pi * f0 * ts))
    c_ref = 2 * np.mean(xr * np.exp(-1j * 2 * math.pi * f0 * ts))
    amp_err = 100 * (abs(c_est) / max(abs(c_ref), 1e-30) - 1)
    sine = c_est.real * np.cos(2 * math.pi * f0 * ts) - c_est.imag * np.sin(2 * math.pi * f0 * ts)
    e = xs - sine
    rms = float(np.sqrt(np.mean(e ** 2))) * 1e9
    P, fx = welch_psd(e, FS, L=4096)
    off = np.abs(fx - f0)
    sig, flo = off <= 3, (off >= 8) & (off <= 40)
    snr = 10 * math.log10(max(P[sig].sum(), 1e-30) /
                          max(P[flo].sum() * sig.sum() / max(flo.sum(), 1), 1e-30))
    return dict(rms=rms, amp=amp_err, snr=snr)


class SplitCalBroken:
    """Control group: wrong block-mean IIR (audit item 1) — do not use in product."""

    def __init__(self, fs, gd_par, blk=0.05, tau=0.05):
        self.nb = max(64, int(blk * fs))
        self.gd = {k: gd_par[k] for k in ('A', 'B', 'delta')}
        self.p, self.q = 0.0, 0.0
        self.a = math.exp(-1.0 / (fs * tau))

    def apply(self, u, v):
        z = np.zeros(u.size, dtype=complex)
        for k in range(0, u.size, self.nb):
            sl = slice(k, min(k + self.nb, u.size))
            self.p = self.a * self.p + (1 - self.a) * float(u[sl].mean())
            self.q = self.a * self.q + (1 - self.a) * float(v[sl].mean())
            par = dict(p=self.p, q=self.q, **self.gd)
            _, _, z[sl] = heydemann_apply(u[sl], v[sl], par)
        return z


def main():
    t0 = time.time()
    sc = synth_record(np.random.default_rng(42))
    t, u, v, x_ref = sc['t'], sc['u'], sc['v'], sc['x_ref']
    sels = [(t >= ph['t0'] + T_TRIM) & (t < ph['t0'] + ph['dur'] - T_TRIM) for ph in PHASES]

    # B1 sliding demean
    n = int(0.1 * FS)
    z1 = (u - movmean(u, n)) + 1j * (v - movmean(v, n))

    # B2 static from phase1
    n1 = int(0.6 * FS)
    par2, _ = heydemann_fit(u[:n1:max(1, n1 // 8000)], v[:n1:max(1, n1 // 8000)])
    _, _, z2 = heydemann_apply(u, v, par2)

    # B7: g,delta from phase1 fit; online p,q via arc-gated tracker (not block mean)
    par7, res7 = heydemann_fit(u[:n1:max(1, n1 // 8000)], v[:n1:max(1, n1 // 8000)])
    z7 = OnlineBiasTracker(par7, FS, blk_s=0.05).run(u, v)

    methods = {
        'B0': u + 1j * v,
        'B1': z1,
        'B2': z2,
        'B7': z7,
    }
    lines = ['=' * 68, '动态工况仿真（无专用标定暂停）', '=' * 68,
             f'{"方法":<4}|{"阶段":<10}{"RMS/nm":>9}{"幅值误差%":>11}{"SNR/dB":>9}']
    results = {}
    for name, z in methods.items():
        results[name] = []
        x = to_disp(phase_cum(z))
        for ph, sel in zip(PHASES, sels):
            m = metrics(x, x_ref, t, ph['f0'], sel)
            results[name].append(m)
            lines.append(f'{name:<4}|{ph["name"]:<10}{m["rms"]:>9.1f}{m["amp"]:>11.1f}{m["snr"]:>9.1f}')

    b1s = np.mean([results['B1'][1]['rms'], results['B1'][2]['rms']])
    b7s = np.mean([results['B7'][1]['rms'], results['B7'][2]['rms']])
    b1a = np.mean([abs(results['B1'][1]['amp']), abs(results['B1'][2]['amp'])])
    b7a = np.mean([abs(results['B7'][1]['amp']), abs(results['B7'][2]['amp'])])
    ok = b7s < b1s / 2 and b7a < b1a / 2
    lines += [
        '',
        f'小振动段(黑+远) 平均RMS: B1={b1s:.1f}nm  B7={b7s:.1f}nm  改善={b1s/max(b7s,0.1):.1f}x',
        f'小振动段 平均|幅值误差|: B1={b1a:.1f}%  B7={b7a:.1f}%',
        f'阶段1 g,delta估计: eps_hat={100*(par7["B"]/par7["A"]-1):+.1f}% '
        f'delta_hat={math.degrees(par7["delta"]):.1f} deg (真值 eps={EPS_HW*100:.1f}% delta={math.degrees(DEL_HW):.1f} deg)',
        f'断言 {"PASS" if ok else "FAIL"}',
        f'耗时 {time.time()-t0:.1f}s',
    ]
    text = '\n'.join(lines)
    print(text)
    from _artifact_io import write_results
    write_results('results_ellipse_dynamic.txt', text)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
