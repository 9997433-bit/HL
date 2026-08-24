#!/usr/bin/env python3
"""Switching-workflow validation B0-B4 (state machine, no dedicated cal pause).

Segments: reflective large-vib -> black small-vib -> far small-vib.
B4 = opportunistic g,delta from rich arc + rho-jump reacq + window-mean
     circle centre tracking (g,delta frozen).
"""
from __future__ import annotations

import math
import sys
import time

import numpy as np

from core import welch_psd
from ellipse_correction import heydemann_fit, heydemann_apply, fit_arc_gated
from validate_ellipse_dynamic import (
    FS, LAMBDA, EPS_HW, DEL_HW, GI, GQ, P_OFF0, Q_OFF,
    movmean, phase_cum, to_disp, metrics,
)

# 6 s three-segment record (subagent spec, scaled)
PHASES = [
    dict(name='A反光膜', t0=0.0, dur=2.0, A=5e-6, f0=200.0, R=1.0, snr_db=30,
         p_off=P_OFF0 + 0.04, q_off=Q_OFF, drift=0.5),
    dict(name='B黑面', t0=2.0, dur=2.0, A=20e-9, f0=500.0, R=0.05, snr_db=10,
         p_off=P_OFF0, q_off=Q_OFF, drift=0.3),
    dict(name='C远距', t0=4.0, dur=2.0, A=20e-9, f0=500.0, R=0.02, snr_db=5,
         p_off=P_OFF0, q_off=Q_OFF, drift=1.5),
]
T_TOTAL = 6.0
T_TRIM = 0.15


def synth_switching(rng):
    N = int(T_TOTAL * FS)
    t = np.arange(N) / FS
    u = np.zeros(N)
    v = np.zeros(N)
    x_true = np.zeros(N)
    for ph in PHASES:
        mask = (t >= ph['t0']) & (t < ph['t0'] + ph['dur'])
        idx = np.where(mask)[0]
        tt = t[idx]
        psi = 2 * math.pi * ph['drift'] * (tt - ph['t0'])
        x = ph['A'] * np.sin(2 * math.pi * ph['f0'] * tt)
        phi = (4 * math.pi / LAMBDA) * x + psi
        cI = GI * ph['R'] * np.cos(phi)
        cQ = GQ * ph['R'] * np.sin(phi + DEL_HW)
        s2 = float(np.mean(cI ** 2 + cQ ** 2)) / 10 ** (ph['snr_db'] / 10)
        u[idx] = (cI + ph['p_off'] + math.sqrt(s2 / 2) * rng.standard_normal(idx.size))
        v[idx] = (cQ + ph['q_off'] + math.sqrt(s2 / 2) * rng.standard_normal(idx.size))
        x_true[idx] = x
    return dict(t=t, u=u, v=v, x_ref=x_true)


def circle_center(xs, ys):
    """Algebraic circle centre (Kasa), radius ignored."""
    A = np.column_stack([2 * xs, 2 * ys, np.ones(xs.size)])
    b = xs ** 2 + ys ** 2
    c, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    return float(c[0]), float(c[1])


class StateMachineB4:
    """S1 rich Heydemann -> freeze g,delta; S3 rho jump; S2 circle centre on win means."""

    def __init__(self, fs, win=0.1, rho_jump=0.20, lms_mu=0.02):
        self.fs = fs
        self.nw = max(64, int(win * fs))
        self.rho_jump = rho_jump
        self.mu = lms_mu
        self.gd = dict(A=1.0, B=1.0 + EPS_HW, delta=DEL_HW)
        self.gd_locked = False
        self.p, self.q = P_OFF0, Q_OFF
        self.rho_ref = 1.0
        self.buf_u, self.buf_v = [], []
        self.state = 'S0'

    def _par(self):
        return dict(p=self.p, q=self.q, **self.gd)

    def _apply_blk(self, u, v):
        _, _, z = heydemann_apply(u, v, self._par())
        return z

    def _update_circle(self):
        if len(self.buf_u) < 8:
            return
        mu = np.array([np.mean(self.buf_u), np.mean(self.buf_v)])
        # transform block means to corrected plane (g,delta fixed)
        us = np.array(self.buf_u)
        vs = np.array(self.buf_v)
        Ic = (us - self.p) / self.gd['A']
        Qc = ((vs - self.q) / self.gd['B'] - Ic * math.sin(self.gd['delta'])) / math.cos(self.gd['delta'])
        ang = np.mod(np.arctan2(Qc, Ic), 2 * math.pi)
        if (ang.max() - ang.min()) < 1.0:
            return
        cx, cy = circle_center(us, vs)
        self.p = 0.7 * self.p + 0.3 * cx
        self.q = 0.7 * self.q + 0.3 * cy

    def _lms_bias(self, z):
        ph = np.angle(z)
        rho = np.abs(z)
        r0 = float(np.median(rho))
        if r0 < 1e-9:
            return
        cph, sph = np.cos(ph), np.sin(ph)
        dp = self.mu * float(np.mean((rho - r0) * cph))
        dq = self.mu * float(np.mean((rho - r0) * sph))
        self.p += dp * self.gd['A']
        self.q += dq * self.gd['B']

    def process(self, u, v):
        z_out = np.zeros(u.size, dtype=complex)
        for k in range(0, u.size, self.nw):
            sl = slice(k, min(k + self.nw, u.size))
            ub, vb = u[sl], v[sl]
            z = self._apply_blk(ub, vb)
            rho_med = float(np.median(np.abs(z)))
            if self.rho_ref > 0 and abs(rho_med / self.rho_ref - 1) > self.rho_jump:
                self.state = 'S3'
                self.buf_u.clear()
                self.buf_v.clear()
            self.rho_ref = 0.9 * self.rho_ref + 0.1 * max(rho_med, 1e-9)

            # S1: opportunistic full fit on rich arc
            if not self.gd_locked:
                cand, res = fit_arc_gated(ub, vb, self._par(), gate_tol=0.08)
                if res.get('ok') and res.get('arc', 0) > math.pi:
                    self.gd = {k: cand[k] for k in ('A', 'B', 'delta')}
                    self.p, self.q = cand['p'], cand['q']
                    self.gd_locked = True
                    self.state = 'S1'
            else:
                self._lms_bias(z)
                self.buf_u.append(float(ub.mean()))
                self.buf_v.append(float(vb.mean()))
                if len(self.buf_u) > 40:
                    self.buf_u.pop(0)
                    self.buf_v.pop(0)
                self._update_circle()
                self.state = 'S2' if self.state != 'S3' else 'S3'

            z_out[sl] = self._apply_blk(ub, vb)
        return z_out


def main():
    t0 = time.time()
    sc = synth_switching(np.random.default_rng(7))
    t, u, v, x_ref = sc['t'], sc['u'], sc['v'], sc['x_ref']
    sels = [(t >= ph['t0'] + T_TRIM) & (t < ph['t0'] + ph['dur'] - T_TRIM) for ph in PHASES]

    n = int(0.1 * FS)
    z1 = (u - movmean(u, n)) + 1j * (v - movmean(v, n))
    n1 = int(1.5 * FS)
    par2, _ = heydemann_fit(u[:n1:max(1, n1 // 8000)], v[:n1:max(1, n1 // 8000)])
    _, _, z2 = heydemann_apply(u, v, par2)
    z4 = StateMachineB4(FS).process(u, v)

    methods = {'B1': z1, 'B2': z2, 'B4': z4}
    lines = ['=' * 60, '工况切换仿真 B1/B2/B4', '=' * 60]
    results = {}
    for name, z in methods.items():
        results[name] = []
        x = to_disp(phase_cum(z))
        for ph, sel in zip(PHASES, sels):
            m = metrics(x, x_ref, t, ph['f0'], sel)
            results[name].append(m)
            lines.append(f'{name}|{ph["name"]}|RMS={m["rms"]:.1f}nm amp={m["amp"]:+.1f}%')

    b1bc = np.mean([results['B1'][1]['rms'], results['B1'][2]['rms']])
    b4bc = np.mean([results['B4'][1]['rms'], results['B4'][2]['rms']])
    ok = b4bc < b1bc / 3
    lines += [f'B/C段 RMS: B1={b1bc:.0f}nm B4={b4bc:.0f}nm ratio={b1bc/max(b4bc,0.1):.1f}x',
              f'断言 {"PASS" if ok else "FAIL"}', f'耗时 {time.time()-t0:.1f}s']
    text = '\n'.join(lines)
    print(text)
    with open('/opt/cursor/artifacts/results_ellipse_switching.txt', 'w') as f:
        f.write(text)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
