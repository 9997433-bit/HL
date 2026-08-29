#!/usr/bin/env python3
"""Switching-workflow validation B1/B2/B4 (state machine, no dedicated cal pause).

Segments: reflective large-vib -> black small-vib -> far small-vib.
B4 = factory g,delta (NVRAM sim from segment A fit; a failed factory fit
     raises, no truth-constant fallback) + rho-drop S3 reacq + arc-gated
     p,q refresh (fit_arc_gated on a chunk-mean buffer).

Adversarial working points (audit): segments B/C use p_off = P_OFF0+0.08 /
P_OFF0+0.12, so any nominal P_OFF0 seeding of the reacquisition would poison
it; S3 instead HOLDS the last trusted p,q (指南 3.2: S3 保持切换前最后可信值)
and exits only when an amplitude-gated fit on the post-jump buffer passes the
FULL quality gates (arc/rms/eps/delta, ellipse_correction.assess_fit) on two
consecutive blocks with a converged centre (指南 S3 出口: 弧 >= ARC_MIN 且
圆心收敛).  A fit that fails any gate is never accepted -- S3 keeps holding.
The buffer stores ~1.25 ms chunk means: raw 10/5 dB samples can never pass
the rms<=0.05 circularity gate (noise/radius is 0.2-0.4), which previously
forced accepting un-assessed fits; chunk averaging (sqrt(3125)~56x noise
reduction, <1% radial smear at 500 Hz vib / 1.5 Hz drift) makes the gates
meaningful while leaving the centre unbiased.

Metric windows: while S3 holds stale p,q the output is marked-invalid by
design (指南 3.2 S3 标记不连续; 故障排查 #7: 该窗口数据不用于评估), so the
asserted B/C amplitude metrics evaluate from S3 exit (reacq complete) to the
segment end.  A segment whose reacq never completes yields an empty window ->
nan -> per-seed FAIL: nothing is silently excluded.  The B1-vs-B4 RMS-ratio
gate (>3x) keeps the FULL trimmed windows, hold included.

Multi-seed hardening (xhigh audit): at 5 dB SNR (segment C) the full-rate
sample-to-sample phase differencing cycle-slips; each slip is a lambda/2
displacement step whose broadband energy leaks into the 500 Hz bin and biases
the single-bin amplitude estimate by a seed-dependent 30-70% even though the
state machine reacquired p,q correctly.  That is a raw-rate phase-detector
property, not the ellipse correction under test.  The asserted B/C amplitude
metric therefore dephases AFTER DEC_BC-fold block averaging of the corrected
z (2.5 MHz -> 20 kHz: ~21 dB SNR gain kills the slips; 500 Hz sinc loss
< 0.1% and cancels anyway because the reference is averaged identically).
The check runs over SEEDS with per-seed gates plus cross-seed median gates.
Discrimination is preserved: the frozen factory-p,q control (= B2 static cal,
printed per seed) evaluated on the SAME post-reacq windows still fails on
every seed (measured ampB +103..+112%, ampC ~ -99%: offset error exceeds the
segment-C radius, so the phase winding collapses).
Do NOT use the decimated metric on segment A: its fringe rate is ~2.5 rad per
20 kHz block and block averaging would smear the phase (weak-return small-vib
segments stay < 0.03 rad/block).
"""
from __future__ import annotations

import math
import sys
import time

import numpy as np

from ellipse_correction import heydemann_fit, heydemann_apply, fit_arc_gated
from validate_ellipse_dynamic import (
    FS, LAMBDA, P_OFF0, movmean, to_disp, metrics,
)

PHASES = [
    dict(name='A反光膜', t0=0.0, dur=2.0, A=5e-6, f0=200.0, R=1.0, snr_db=30,
         p_off=P_OFF0 + 0.04, q_off=-0.05, drift=0.5),
    dict(name='B黑面', t0=2.0, dur=2.0, A=20e-9, f0=500.0, R=0.05, snr_db=10,
         p_off=P_OFF0 + 0.08, q_off=-0.05, drift=0.3),
    dict(name='C远距', t0=4.0, dur=2.0, A=20e-9, f0=500.0, R=0.02, snr_db=5,
         p_off=P_OFF0 + 0.12, q_off=-0.05, drift=1.5),
]
T_TOTAL = 6.0
T_TRIM = 0.15
S3_MIN = 6               # blocks @ 0.05 s: earliest reacq fit attempt (guide
                         # N_acq 0.3 s); actual exit is governed by the
                         # arc/rms/eps/delta + centre-convergence gates
CHUNK_S = 1.25e-3          # S3 buffer chunk-mean length (sqrt(3125)~56x noise cut)
CTR_CONV = 0.05            # S3 exit: consecutive fitted centres within 5% of radius
RHO_DROP = 0.55            # |z| drop fraction -> S3 (A->B ~20x, B->C ~2.5x)
JUMP_CONFIRM = 2
S3_COOLDOWN = 12           # blocks before next S3 (prevents weak-return re-entry)

SEEDS = [1, 7, 13, 42, 99]
REP_SEED = 7               # seed whose full B1/B2/B4 table is printed
DEC_BC = 125               # 2.5 MHz -> 20 kHz narrowband dephase for B/C metric
AMP_B_MAX, AMP_C_MAX = 20.0, 25.0   # per-seed gates (frozen-B2 control fails
                                    # far outside; measured values printed)
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
    if n < 2 * dec:                      # empty window (reacq never completed)
        return float('nan')
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
        # No silent fallback to simulation truth constants: a failed factory
        # cal must abort, otherwise B4 would be validated against oracle values.
        raise RuntimeError('factory_nvram_sim: segment-A calibration fit '
                           'failed: ' + (res.get('msg') or 'unknown reason'))
    return par


class SwitchingStateMachine:
    """S2 track with factory g,d; rho-drop -> S3 reacq -> fit_arc_gated p,q refresh.

    On major |z| drop (surface/distance change) enter S3 HOLDING the last
    trusted p,q (guide 3.2; a nominal P_OFF0 seed would poison reacquisition
    whenever the new working point's offset differs from nominal, as the
    adversarial B/C segments do), accumulate ~1.25 ms chunk means of the
    post-jump samples, then exit only when fit_arc_gated on that buffer
    passes the FULL acceptance gates on two consecutive blocks with a
    converged centre (guide S3 exit: arc >= ARC_MIN and centre converged).
    g,delta stay at factory.
    """

    def __init__(self, fs, factory_par, blk_s=0.05):
        self.fs = fs
        self.nb = max(64, int(blk_s * fs))
        self.chunk = max(1, int(CHUNK_S * fs))
        self.gd = {k: float(factory_par[k]) for k in ('A', 'B', 'delta')}
        self.p = float(factory_par['p'])
        self.q = float(factory_par['q'])
        self.state = 'S2'
        self.rho_ref = 1.0
        self.bm_u: list = []
        self.bm_v: list = []
        self.cand = None           # last passing fit centre (p, q, A)
        self.s3_blocks = 0
        self.jump_streak = 0
        self.cooldown = 0
        self.discontinuities: list = []
        self.reacq_times: list = []

    def _par(self):
        return dict(p=self.p, q=self.q, **self.gd)

    def _push_chunks(self, ub, vb):
        nc = (ub.size // self.chunk) * self.chunk
        if nc:
            self.bm_u.extend(ub[:nc].reshape(-1, self.chunk).mean(axis=1))
            self.bm_v.extend(vb[:nc].reshape(-1, self.chunk).mean(axis=1))

    def _try_fit(self):
        """Reacquire p,q from fit_arc_gated on the S3 chunk-mean buffer.

        The held p,q may be arbitrarily stale after the switch (adversarial
        offsets), so a gate referenced to them is meaningless; and raw
        10/5 dB samples can never pass the rms circularity gate.  Chunk
        means (~56x noise cut, centre-unbiased) make the gates meaningful:
        bootstrap an ungated fit, refit amplitude-gated with it, and require
        BOTH to pass the full acceptance gate (arc/rms/eps/delta).  p,q are
        committed only after two consecutive passing fits whose centres
        agree within CTR_CONV of the fitted radius (centre convergence).
        g,delta stay at factory.
        """
        mu = np.array(self.bm_u)
        mv = np.array(self.bm_v)
        if mu.size < 100:
            return False
        boot, res = heydemann_fit(mu, mv)
        if not res.get('ok'):
            self.cand = None
            return False
        par, res2 = fit_arc_gated(mu, mv, boot)
        if not (res2.get('ok') and
                all(math.isfinite(par.get(k, float('nan'))) for k in ('p', 'q'))):
            self.cand = None
            return False
        prev, self.cand = self.cand, (par['p'], par['q'], par['A'])
        if prev is None:
            return False
        if math.hypot(par['p'] - prev[0], par['q'] - prev[1]) > CTR_CONV * par['A']:
            return False
        self.p = float(par['p'])
        self.q = float(par['q'])
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
                self.bm_u.clear()
                self.bm_v.clear()
                self.cand = None
                # p,q hold the last trusted values until the gated fit accepts
                # fresh ones (guide 3.2 S3 row); no nominal-offset seeding.
                self.discontinuities.append(k / self.fs)
            self.rho_ref = 0.9 * self.rho_ref + 0.1 * max(rho_med, 1e-9)
            if self.state == 'S3':
                self.s3_blocks += 1
                self._push_chunks(ub, vb)
                if self.s3_blocks >= S3_MIN and self._try_fit():
                    self.state = 'S2'
                    self.cooldown = S3_COOLDOWN
                    self.bm_u.clear()
                    self.bm_v.clear()
                    self.cand = None
                    self.reacq_times.append(sl.stop / self.fs)
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

    # Guide 3.2 (S3 row) / failure mode #7: samples inside the S3 window are
    # marked discontinuous and excluded from evaluation — with adversarial
    # p offsets the new centre is physically unidentifiable until ~pi/2 of
    # fresh arc has accrued, so in-S3 output is necessarily distorted.  The
    # decimated amplitude metric runs from S3 exit (reacq complete) to the
    # segment end; a segment whose reacq never completed yields an EMPTY
    # window -> nan -> per-seed FAIL (nothing silently excluded).
    def amp_sel(i):
        ph = PHASES[i]
        hi = ph['t0'] + ph['dur'] - T_TRIM
        tr = [x for x in sm.reacq_times if ph['t0'] <= x < ph['t0'] + ph['dur']]
        if not tr:
            return np.zeros(t.size, bool)
        lo = max(ph['t0'] + T_TRIM, max(tr))
        return (t >= lo) & (t < hi)

    sel_b, sel_c = amp_sel(1), amp_sel(2)
    amp_b, amp_c = (amp_dec(z4[s], x_ref[s], t[s], PHASES[i]['f0'])
                    for i, s in ((1, sel_b), (2, sel_c)))
    # Frozen factory-p,q control (= B2 static cal) on the SAME windows:
    # demonstrates the S3 reacq is what recovers the amplitude metric.
    ctl_b, ctl_c = (amp_dec(z2[s], x_ref[s], t[s], PHASES[i]['f0'])
                    for i, s in ((1, sel_b), (2, sel_c)))
    return dict(seed=seed, fpar=fpar, disc=list(sm.discontinuities),
                reacq=list(sm.reacq_times),
                results=results, amp_b_dec=amp_b, amp_c_dec=amp_c,
                ctl_b_dec=ctl_b, ctl_c_dec=ctl_c)


def main():
    t0 = time.time()
    runs = [run_once(s) for s in SEEDS]
    rep = next(r for r in runs if r['seed'] == REP_SEED)
    fpar = rep['fpar']
    lines = ['=' * 60, '工况切换仿真 B1/B2/B4 (NVRAM+S3重捕, 多种子加固)', '=' * 60,
             f'代表种子 seed={REP_SEED} (全速率解相指标):',
             f'出厂拟合(A段): p={fpar["p"]:.3f} q={fpar["q"]:.3f} '
             f'g={fpar["B"]/fpar["A"]:.3f} delta={math.degrees(fpar["delta"]):.1f}deg',
             f'S3不连续时刻: {[f"{x:.2f}s" for x in rep["disc"]]}'
             f'  重捕完成: {[f"{x:.2f}s" for x in rep["reacq"]]}'
             ' (S3窗内数据按指南3.2标记不连续, 不计入B/C幅值评估)']
    for name in ('B1', 'B2', 'B4'):
        for ph, m in zip(PHASES, rep['results'][name]):
            lines.append(f'{name}|{ph["name"]}|RMS={m["rms"]:.1f}nm amp={m["amp"]:+.1f}%')

    fs_dec = FS / DEC_BC / 1e3
    lines += ['-' * 60,
              f'多种子断言 seeds={SEEDS}: B/C幅值用{fs_dec:.0f}kHz降采样解相, '
              '重捕完成后窗口 (消除5dB周跳对500Hz单bin的宽带泄漏); '
              '冻结对照=B2静态标定在同一窗口的测量值']
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
            f'(冻结对照 ampB={r["ctl_b_dec"]:+6.1f}% '
            f'ampC={r["ctl_c_dec"]:+6.1f}%) {"ok" if ok_s else "FAIL"}')
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
