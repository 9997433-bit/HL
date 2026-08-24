#!/usr/bin/env python3
"""Switching-workflow validation B1/B2/B4 (state machine, no dedicated cal pause).

Segments: reflective large-vib -> black small-vib -> far small-vib.
B4 = factory g,delta (NVRAM sim from segment A fit) + rho-drop S3 reacq +
     arc-gated p refresh (fit_arc_gated on raw-sample buffer; q frozen).

Multi-seed hardening (xhigh audit): at 5 dB SNR (segment C) the full-rate
sample-to-sample phase differencing cycle-slips; each slip is a lambda/2
displacement step whose broadband energy leaks into the 500 Hz bin and biases
the single-bin amplitude estimate by a seed-dependent 30-70% (seeds 1/13/99
failed the old 25% gate) even though the state machine reacquired p correctly.
That is a raw-rate phase-detector property, not the ellipse correction under
test.  The asserted B/C amplitude metric therefore dephases AFTER DEC_BC-fold
block averaging of the corrected z (2.5 MHz -> 20 kHz: ~21 dB SNR gain kills
the slips; 500 Hz sinc loss < 0.1% and cancels anyway because the reference is
averaged identically).  The check runs over SEEDS with per-seed gates plus
cross-seed median gates.  Discrimination is preserved: freezing the factory p
(no S3 reacq) still fails at ~-33% (B) / ~-94% (C) on every seed.
Do NOT use the decimated metric on segment A: its fringe rate is ~2.5 rad per
20 kHz block and block averaging would smear the phase (weak-return small-vib
segments stay < 0.03 rad/block).
"""
from __future__ import annotations

import math
import sys
import time

import numpy as np

from ellipse_correction import (
    heydemann_fit, heydemann_apply, fit_arc_gated, ARC_MIN, arc_span_corrected,
)
from validate_ellipse_dynamic import (
    FS, LAMBDA, P_OFF0, movmean, to_disp, metrics,
)

PHASES = [
    dict(name='A反光膜', t0=0.0, dur=2.0, A=5e-6, f0=200.0, R=1.0, snr_db=30,
         p_off=P_OFF0 + 0.04, q_off=-0.05, drift=0.5),
    dict(name='B黑面', t0=2.0, dur=2.0, A=20e-9, f0=500.0, R=0.05, snr_db=10,
         p_off=P_OFF0, q_off=-0.05, drift=0.3),
    dict(name='C远距', t0=4.0, dur=2.0, A=20e-9, f0=500.0, R=0.02, snr_db=5,
         p_off=P_OFF0, q_off=-0.05, drift=1.5),
]
T_TOTAL = 6.0
T_TRIM = 0.15
S3_MIN = 18              # blocks @ 0.05 s: enough arc for fit_arc_gated gate
RHO_DROP = 0.55            # |z| drop fraction -> S3 (A->B ~20x, B->C ~2.5x)
JUMP_CONFIRM = 2
S3_COOLDOWN = 12           # blocks before next S3 (prevents weak-return re-entry)

SEEDS = [1, 7, 13, 42, 99]
REP_SEED = 7               # seed whose full B1/B2/B4 table is printed
DEC_BC = 125               # 2.5 MHz -> 20 kHz narrowband dephase for B/C metric
AMP_B_MAX, AMP_C_MAX = 20.0, 25.0   # per-seed gates; frozen-p failure: 33%/94%
AMP_B_MED, AMP_C_MED = 15.0, 10.0   # cross-seed median gates


def phase_cum_seg(z):
    """Segment-local phase integration (reset at each phase boundary)."""
    d = np.angle(z[1:] * np.conj(z[:-1]))
    return np.concatenate(([0.0], np.cumsum(d)))


def amp_dec(z_seg, x_ref_seg, t_seg, f0, dec=DEC_BC):
    """Single-bin amplitude error (%) from decimated dephasing.

    Block-average corrected z by `dec` before phase integration: narrowbanding
    ahead of the phase detector removes the 5 dB SNR cycle slips whose
    broadband steps otherwise bias the f0 bin (see module docstring).  The
    reference displacement is block-averaged identically so the sinc
    attenuation at f0 cancels in the ratio.
    """
    n = (z_seg.size // dec) * dec
    zb = z_seg[:n].reshape(-1, dec).mean(axis=1)
    d = np.angle(zb[1:] * np.conj(zb[:-1]))
    x = to_disp(np.concatenate(([0.0], np.cumsum(d))))
    td = t_seg[:n].reshape(-1, dec).mean(axis=1)
    xr = x_ref_seg[:n].reshape(-1, dec).mean(axis=1)
    xs, xrr = x - x.mean(), xr - xr.mean()
    c_e = 2 * np.mean(xs * np.exp(-1j * 2 * math.pi * f0 * td))
    c_r = 2 * np.mean(xrr * np.exp(-1j * 2 * math.pi * f0 * td))
    return 100 * (abs(c_e) / max(abs(c_r), 1e-30) - 1)


def synth_switching(rng):
    N = int(T_TOTAL * FS)
    t = np.arange(N) / FS
    u = np.zeros(N)
    v = np.zeros(N)
    x_true = np.zeros(N)
    from validate_ellipse_dynamic import EPS_HW, DEL_HW, GI, GQ
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


def factory_nvram_sim(u, v, t_cal=1.5):
    """Simulate NVRAM factory cal from segment-A data (not simulation truth constants)."""
    n = min(int(t_cal * FS), u.size)
    step = max(1, n // 8000)
    par, res = heydemann_fit(u[:n:step], v[:n:step])
    if not res.get('ok'):
        from validate_ellipse_dynamic import EPS_HW, DEL_HW
        par = dict(p=0.0, q=0.0, A=1.0, B=1.0 + EPS_HW, delta=DEL_HW)
    return par


class SwitchingStateMachine:
    """S2 track with factory g,d; rho-drop -> S3 reacq -> fit_arc_gated p refresh.

    On major |z| drop (surface/distance change) enter S3, seed p with the nominal
    hardware offset P_OFF0 so amplitude gating in fit_arc_gated converges on weak
    return, accumulate raw subsamples (not block means), then accept p from
    fit_arc_gated when arc coverage is sufficient.  q and g,delta stay at factory.
    """

    def __init__(self, fs, factory_par, blk_s=0.05):
        self.fs = fs
        self.nb = max(64, int(blk_s * fs))
        self.gd = {k: float(factory_par[k]) for k in ('A', 'B', 'delta')}
        self.p = float(factory_par['p'])
        self.q = float(factory_par['q'])
        self.q0 = float(factory_par['q'])
        self.state = 'S2'
        self.rho_ref = 1.0
        self.raw_u: list = []
        self.raw_v: list = []
        self.s3_blocks = 0
        self.jump_streak = 0
        self.cooldown = 0
        self.discontinuities: list = []

    def _par(self):
        return dict(p=self.p, q=self.q, **self.gd)

    def _push_raw(self, ub, vb, cap=10000):
        step = max(1, len(ub) // 40)
        self.raw_u.extend(map(float, ub[::step]))
        self.raw_v.extend(map(float, vb[::step]))
        if len(self.raw_u) > cap:
            d = len(self.raw_u) - cap
            self.raw_u = self.raw_u[d:]
            self.raw_v = self.raw_v[d:]

    def _try_fit_p(self):
        us = np.array(self.raw_u)
        vs = np.array(self.raw_v)
        if us.size < 600:
            return False
        if arc_span_corrected(us, vs, self._par()) < ARC_MIN:
            return False
        par, _res = fit_arc_gated(us, vs, self._par())
        if not math.isfinite(par.get('p', float('nan'))):
            return False
        self.p = float(par['p'])
        self.q = self.q0
        return True

    def process(self, u, v):
        z_out = np.zeros(u.size, dtype=complex)
        for k in range(0, u.size, self.nb):
            sl = slice(k, min(k + self.nb, u.size))
            ub, vb = u[sl], v[sl]
            _, _, z = heydemann_apply(ub, vb, self._par())
            rho_med = float(np.median(np.abs(z)))
            ratio = rho_med / self.rho_ref if self.rho_ref > 0 else 1.0
            jumped = ratio < RHO_DROP
            self.jump_streak = self.jump_streak + 1 if jumped else 0
            if (self.jump_streak >= JUMP_CONFIRM and self.state != 'S3'
                    and self.cooldown <= 0):
                self.state = 'S3'
                self.s3_blocks = 0
                self.jump_streak = 0
                self.raw_u.clear()
                self.raw_v.clear()
                self.p = float(P_OFF0)
                self.q = self.q0
                self.discontinuities.append(k / self.fs)
            self.rho_ref = 0.9 * self.rho_ref + 0.1 * max(rho_med, 1e-9)
            self._push_raw(ub, vb)
            if self.state == 'S3':
                self.s3_blocks += 1
                if self.s3_blocks >= S3_MIN and self._try_fit_p():
                    self.state = 'S2'
                    self.cooldown = S3_COOLDOWN
                    self.raw_u.clear()
                    self.raw_v.clear()
            elif self.cooldown > 0:
                self.cooldown -= 1
            _, _, z_out[sl] = heydemann_apply(ub, vb, self._par())
        return z_out


def run_once(seed):
    """One full B1/B2/B4 pass; returns full-rate metrics + decimated B/C amps."""
    sc = synth_switching(np.random.default_rng(seed))
    t, u, v, x_ref = sc['t'], sc['u'], sc['v'], sc['x_ref']
    sels = [(t >= ph['t0'] + T_TRIM) & (t < ph['t0'] + ph['dur'] - T_TRIM)
            for ph in PHASES]

    n = int(0.1 * FS)
    z1 = (u - movmean(u, n)) + 1j * (v - movmean(v, n))
    n1 = int(1.5 * FS)
    par2, _ = heydemann_fit(u[:n1:max(1, n1 // 8000)], v[:n1:max(1, n1 // 8000)])
    _, _, z2 = heydemann_apply(u, v, par2)

    fpar = factory_nvram_sim(u, v)
    sm = SwitchingStateMachine(FS, fpar)
    z4 = sm.process(u, v)

    results = {}
    for name, z in (('B1', z1), ('B2', z2), ('B4', z4)):
        results[name] = []
        for ph, sel in zip(PHASES, sels):
            m = metrics(to_disp(phase_cum_seg(z[sel])), x_ref[sel], t[sel],
                        ph['f0'], np.ones(sel.sum(), bool))
            results[name].append(m)

    amp_b, amp_c = (amp_dec(z4[sels[i]], x_ref[sels[i]], t[sels[i]],
                            PHASES[i]['f0']) for i in (1, 2))
    return dict(seed=seed, fpar=fpar, disc=list(sm.discontinuities),
                results=results, amp_b_dec=amp_b, amp_c_dec=amp_c)


def main():
    t0 = time.time()
    runs = [run_once(s) for s in SEEDS]
    rep = next(r for r in runs if r['seed'] == REP_SEED)
    fpar = rep['fpar']
    lines = ['=' * 60, '工况切换仿真 B1/B2/B4 (NVRAM+S3重捕, 多种子加固)', '=' * 60,
             f'代表种子 seed={REP_SEED} (全速率解相指标):',
             f'出厂拟合(A段): p={fpar["p"]:.3f} q={fpar["q"]:.3f} '
             f'g={fpar["B"]/fpar["A"]:.3f} delta={math.degrees(fpar["delta"]):.1f}deg',
             f'S3不连续时刻: {[f"{x:.2f}s" for x in rep["disc"]]}']
    for name in ('B1', 'B2', 'B4'):
        for ph, m in zip(PHASES, rep['results'][name]):
            lines.append(f'{name}|{ph["name"]}|RMS={m["rms"]:.1f}nm amp={m["amp"]:+.1f}%')

    fs_dec = FS / DEC_BC / 1e3
    lines += ['-' * 60,
              f'多种子断言 seeds={SEEDS}: B/C幅值用{fs_dec:.0f}kHz降采样解相'
              '(消除5dB周跳对500Hz单bin的宽带泄漏; 全速率值仅列作参考)']
    per_ok = []
    abs_b, abs_c = [], []
    for r in runs:
        res = r['results']
        b1bc = float(np.mean([res['B1'][1]['rms'], res['B1'][2]['rms']]))
        b4bc = float(np.mean([res['B4'][1]['rms'], res['B4'][2]['rms']]))
        ratio = b1bc / max(b4bc, 0.1)
        ab, ac = abs(r['amp_b_dec']), abs(r['amp_c_dec'])
        ok_s = (b4bc < b1bc / 3 and ab < AMP_B_MAX and ac < AMP_C_MAX)
        per_ok.append(ok_s)
        abs_b.append(ab)
        abs_c.append(ac)
        lines.append(
            f'seed={r["seed"]:<3d} RMS比={ratio:5.1f}x '
            f'ampB={r["amp_b_dec"]:+6.1f}% ampC={r["amp_c_dec"]:+6.1f}% '
            f'(全速率参考 ampB={res["B4"][1]["amp"]:+6.1f}% '
            f'ampC={res["B4"][2]["amp"]:+6.1f}%) {"ok" if ok_s else "FAIL"}')
    med_b = float(np.median(abs_b))
    med_c = float(np.median(abs_c))
    ok = all(per_ok) and med_b < AMP_B_MED and med_c < AMP_C_MED
    lines += [
        f'每seed门限: RMS比>3x  |ampB|<{AMP_B_MAX:.0f}%  |ampC|<{AMP_C_MAX:.0f}% '
        f'-> {"全部ok" if all(per_ok) else "有FAIL"}',
        f'跨seed中位数: |ampB|={med_b:.1f}% (<{AMP_B_MED:.0f}%)  '
        f'|ampC|={med_c:.1f}% (<{AMP_C_MED:.0f}%)',
        f'断言 {"PASS" if ok else "FAIL"}',
        f'耗时 {time.time()-t0:.1f}s',
    ]
    text = '\n'.join(lines)
    print(text)
    from _artifact_io import write_results
    write_results('results_ellipse_switching.txt', text)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
