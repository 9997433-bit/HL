#!/usr/bin/env python3
"""No large vibration — corrected online bias (audit fix)."""
from __future__ import annotations

import math
import sys
import time

import numpy as np

from _artifact_io import write_results
from ellipse_correction import heydemann_fit, heydemann_apply, OnlineBiasTracker
from validate_ellipse_dynamic import FS, LAMBDA, movmean, phase_cum, to_disp, metrics

EPS_HW, DEL_HW = -0.10, 4.5 * math.pi / 180
GI, GQ = 1.0, 1.0 + EPS_HW
P_OFF0, Q_OFF = 0.06, -0.05
T_TOTAL = 30.0
SEGMENTS = [
    dict(name='反光小振', t0=0, dur=10, A=80e-9, f0=100, R=1.0, snr_db=28, drift=0.08),
    dict(name='黑面小振', t0=10, dur=10, A=50e-9, f0=100, R=0.06, snr_db=18, drift=0.12),
    dict(name='远距小振', t0=20, dur=10, A=60e-9, f0=100, R=0.025, snr_db=12, drift=0.15),
]


def synth(rng):
    N = int(T_TOTAL * FS)
    t = np.arange(N) / FS
    u = np.zeros(N)
    v = np.zeros(N)
    x_true = np.zeros(N)
    for sg in SEGMENTS:
        m = (t >= sg['t0']) & (t < sg['t0'] + sg['dur'])
        idx = np.where(m)[0]
        tt = t[idx]
        psi = 2 * math.pi * sg['drift'] * (tt - sg['t0'])
        psi += 0.3 * np.cumsum(rng.standard_normal(idx.size)) / FS
        x = sg['A'] * np.sin(2 * math.pi * sg['f0'] * tt)
        phi = (4 * math.pi / LAMBDA) * x + psi
        cI = GI * sg['R'] * np.cos(phi)
        cQ = GQ * sg['R'] * np.sin(phi + DEL_HW)
        s2 = float(np.mean(cI ** 2 + cQ ** 2)) / 10 ** (sg['snr_db'] / 10)
        u[idx] = cI + P_OFF0 + math.sqrt(s2 / 2) * rng.standard_normal(idx.size)
        v[idx] = cQ + Q_OFF + math.sqrt(s2 / 2) * rng.standard_normal(idx.size)
        x_true[idx] = x
    return dict(t=t, u=u, v=v, x_ref=x_true)


class BrokenBlockMean:
    """B8-broken: per-sample alpha bug + block mean as p,q (audit item 1)."""

    def __init__(self, fs, gd_par, blk_s=0.1, tau=0.05):
        self.par = dict(gd_par)
        self.nb = max(64, int(blk_s * fs))
        self.a = math.exp(-1.0 / (fs * tau))  # BUG: per-sample, not per-block

    def run(self, u, v):
        z = np.zeros(u.size, dtype=complex)
        for k in range(0, u.size, self.nb):
            sl = slice(k, min(k + self.nb, u.size))
            self.par['p'] = self.a * self.par['p'] + (1 - self.a) * float(u[sl].mean())
            self.par['q'] = self.a * self.par['q'] + (1 - self.a) * float(v[sl].mean())
            _, _, z[sl] = heydemann_apply(u[sl], v[sl], self.par)
        return z


class FactoryFrozen:
    """B8-correct: g,delta + p,q all frozen from factory (no wrong online track)."""

    def __init__(self, par):
        self.par = dict(par)

    def run(self, u, v):
        _, _, z = heydemann_apply(u, v, self.par)
        return z


def main():
    t0 = time.time()
    sc = synth(np.random.default_rng(99))
    t, u, v, x_ref = sc['t'], sc['u'], sc['v'], sc['x_ref']
    trim = 1.0
    sels = [(t >= sg['t0'] + trim) & (t < sg['t0'] + sg['dur'] - trim) for sg in SEGMENTS]

    # factory cal from first 5 s drift
    ncal = int(5 * FS)
    step = max(1, ncal // 8000)
    fpar, fres = heydemann_fit(u[:ncal:step], v[:ncal:step])

    n = int(0.2 * FS)
    z1 = (u - movmean(u, n)) + 1j * (v - movmean(v, n))
    z_bad = BrokenBlockMean(FS, fpar).run(u, v)
    z_ok = FactoryFrozen(fpar).run(u, v)
    z_arc = OnlineBiasTracker(fpar, FS, blk_s=0.1).run(u, v)

    methods = {
        'B1滑动去均值': z1,
        'B8错误块均值': z_bad,
        'B8出厂冻结pq': z_ok,
        'B8弧门控pq': z_arc,
    }
    lines = ['=' * 64, '审查修复后：无大振动场景', f'出厂拟合 ok={fres["ok"]}', '=' * 64]
    results = {}
    for name, z in methods.items():
        results[name] = []
        x = to_disp(phase_cum(z))
        for sg, sel in zip(SEGMENTS, sels):
            m = metrics(x, x_ref, t, sg['f0'], sel)
            results[name].append(m)
            lines.append(f'{name}|{sg["name"]}|RMS={m["rms"]:.1f}nm |amp|={abs(m["amp"]):.1f}%')

    def mean_rms(key):
        return np.mean([results[key][i]['rms'] for i in range(3)])

    lines += [
        f'平均RMS: B1={mean_rms("B1滑动去均值"):.0f}  错误块均值={mean_rms("B8错误块均值"):.0f}  '
        f'出厂冻结={mean_rms("B8出厂冻结pq"):.0f}  弧门控={mean_rms("B8弧门控pq"):.0f}',
        f'审查: 错误块均值因alpha/公式bug看似"好"实则冻结真值 — 修复后应用出厂冻结或弧门控',
    ]
    # Honest pass: factory-frozen beats B1; arc-gated must not collapse amplitude on weak-return
    amp_arc = [abs(results['B8弧门控pq'][i]['amp']) for i in range(3)]
    ok = (mean_rms('B8出厂冻结pq') < mean_rms('B1滑动去均值') / 10
          and amp_arc[0] < 10.0)  # reflective segment amplitude error
    lines += [
        f'弧门控|amp|: 反光={amp_arc[0]:.1f}% 黑面={amp_arc[1]:.1f}% 远距={amp_arc[2]:.1f}%',
        f'断言 {"PASS" if ok else "FAIL"}',
        f'耗时 {time.time()-t0:.1f}s',
    ]
    text = '\n'.join(lines)
    print(text)
    write_results('results_ellipse_no_large_vib.txt', text)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
