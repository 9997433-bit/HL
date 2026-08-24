#!/usr/bin/env python3
"""No large vibration ever — only small displacement + natural drift.

Tests what is achievable when there is NEVER a rich-arc calibration opportunity:
  B1  sliding demean (user baseline)
  B8  factory g,delta (frozen hardware) + online p,q only
  B9  M1 natural drift: block-mean trajectory + Heydemann when arc>=pi/2
  B10 B8 + B9 hybrid: factory g,delta until drift arc updates, always track p,q
"""
from __future__ import annotations

import math
import sys
import time

import numpy as np

from ellipse_correction import heydemann_fit, heydemann_apply, fit_arc_gated
from validate_ellipse_dynamic import FS, LAMBDA, movmean, phase_cum, to_disp, metrics

EPS_HW, DEL_HW = -0.10, 4.5 * math.pi / 180
GI, GQ = 1.0, 1.0 + EPS_HW
P_OFF0, Q_OFF = 0.06, -0.05

# 30 s record: ONLY small vibration, slow drift, surface switch mid-way
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
        # slow working-point drift (fringes/s) — the ONLY source of arc without large vib
        psi = 2 * math.pi * sg['drift'] * (tt - sg['t0'])
        psi += 0.3 * np.cumsum(rng.standard_normal(idx.size)) / FS  # random walk
        x = sg['A'] * np.sin(2 * math.pi * sg['f0'] * tt)
        phi = (4 * math.pi / LAMBDA) * x + psi
        cI = GI * sg['R'] * np.cos(phi)
        cQ = GQ * sg['R'] * np.sin(phi + DEL_HW)
        s2 = float(np.mean(cI ** 2 + cQ ** 2)) / 10 ** (sg['snr_db'] / 10)
        u[idx] = cI + P_OFF0 + math.sqrt(s2 / 2) * rng.standard_normal(idx.size)
        v[idx] = cQ + Q_OFF + math.sqrt(s2 / 2) * rng.standard_normal(idx.size)
        x_true[idx] = x
    return dict(t=t, u=u, v=v, x_ref=x_true)


class FactoryBias:
    """B8: correct g,delta from factory; online p,q via sliding block mean."""

    def __init__(self, fs, tau=0.05):
        self.par = dict(p=P_OFF0, q=Q_OFF, A=1.0, B=1.0 + EPS_HW, delta=DEL_HW)
        self.nb = max(64, int(0.1 * fs))  # 100ms block, 10 cycles @100Hz
        self.a = math.exp(-1.0 / (fs * tau))

    def run(self, u, v):
        z = np.zeros(u.size, dtype=complex)
        for k in range(0, u.size, self.nb):
            sl = slice(k, min(k + self.nb, u.size))
            self.par['p'] = self.a * self.par['p'] + (1 - self.a) * float(u[sl].mean())
            self.par['q'] = self.a * self.par['q'] + (1 - self.a) * float(v[sl].mean())
            _, _, z[sl] = heydemann_apply(u[sl], v[sl], self.par)
        return z


class DriftArcM1:
    """B9: block-mean points when amp stable; Heydemann when arc>=pi/2."""

    def __init__(self, fs, blk=0.1, gate=0.06):
        self.nb = max(64, int(blk * fs))
        self.gate = gate
        self.par = dict(p=P_OFF0, q=Q_OFF, A=1.0, B=1.0, delta=0.0)
        self.ok = False
        self.buf_u, self.buf_v = [], []

    def _try_fit(self):
        if len(self.buf_u) < 12:
            return
        us, vs = np.array(self.buf_u), np.array(self.buf_v)
        par, res = heydemann_fit(us, vs)
        if res.get('ok'):
            self.par = par
            self.ok = True

    def run(self, u, v):
        z = np.zeros(u.size, dtype=complex)
        for k in range(0, u.size, self.nb):
            sl = slice(k, min(k + self.nb, u.size))
            ub, vb = u[sl], v[sl]
            self.buf_u.append(float(ub.mean()))
            self.buf_v.append(float(vb.mean()))
            if len(self.buf_u) > 200:
                self.buf_u.pop(0)
                self.buf_v.pop(0)
            self._try_fit()
            p = self.par if self.ok else dict(p=float(ub.mean()), q=float(vb.mean()),
                                               A=1.0, B=1.0, delta=0.0)
            _, _, z[sl] = heydemann_apply(ub, vb, p)
        return z, self.ok


def main():
    t0 = time.time()
    sc = synth(np.random.default_rng(99))
    t, u, v, x_ref = sc['t'], sc['u'], sc['v'], sc['x_ref']
    trim = 1.0
    sels = [(t >= sg['t0'] + trim) & (t < sg['t0'] + sg['dur'] - trim) for sg in SEGMENTS]

    n = int(0.2 * FS)
    z1 = (u - movmean(u, n)) + 1j * (v - movmean(v, n))
    z8 = FactoryBias(FS).run(u, v)
    z9, m1_ok = DriftArcM1(FS).run(u, v)

    methods = {'B1': z1, 'B8出厂gδ+在线pq': z8, 'B9纯漂移弧M1': z9}
    lines = ['=' * 64, '无大振动场景（全程 50-80nm @100Hz，仅靠慢漂移）', '=' * 64,
             f'M1漂移弧拟合成功: {m1_ok}']
    for name, z in methods.items():
        x = to_disp(phase_cum(z))
        for sg, sel in zip(SEGMENTS, sels):
            m = metrics(x, x_ref, t, sg['f0'], sel)
            lines.append(f'{name}|{sg["name"]}|RMS={m["rms"]:.1f}nm |amp|={abs(m["amp"]):.1f}%')

    b1 = np.mean([metrics(to_disp(phase_cum(z1)), x_ref, t, 100, s)['rms'] for s in sels])
    b8 = np.mean([metrics(to_disp(phase_cum(z8)), x_ref, t, 100, s)['rms'] for s in sels])
    b9 = np.mean([metrics(to_disp(phase_cum(z9)), x_ref, t, 100, s)['rms'] for s in sels])
    lines += [
        f'全段平均RMS: B1={b1:.0f}nm  B8={b8:.0f}nm  B9={b9:.0f}nm',
        f'B8相对B1改善 {b1/max(b8,0.1):.1f}x',
        '结论: 无大振动时 g,delta 只能靠出厂/漂移弧; 漂移够慢则M1可收敛',
        f'耗时 {time.time()-t0:.1f}s',
    ]
    text = '\n'.join(lines)
    print(text)
    with open('/opt/cursor/artifacts/results_ellipse_no_large_vib.txt', 'w') as f:
        f.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
