#!/usr/bin/env python3
"""Realistic-scenario simulation suite: homodyne AND heterodyne tracking filters.

Purpose: validate filter performance on REALISTIC operating scenarios (not
only the spec-point checks of validate_tracking / validate_heterodyne) and
produce the measured numbers behind scenario_study/OPTIMIZATION_GUIDE.md.

Homodyne (1550 nm, user application: v_peak <= 30 m/s, f <= 100 kHz typical)
  S1  operating map      f={1,10,50,100} kHz x v={0.02,1,5,20,30} m/s x
                         CNR={3,6,12} dB: clean amp err (R1), SNR gain
                         (R3 = signal gain + R2 STATIC-CARRIER noise-floor
                         drop in the 10..100 kHz structure band -- labelled
                         as such, NOT a per-cell dynamic measurement),
                         selected gear, guard_ok / overrange flags; plus
                         the S1e dynamic spot check: 3 cells re-measured
                         with FULL noisy dynamic runs on the actual motion
                         (audit issue 3).
  S2  speckle matrix     tau_c={20,50,100} us x CNR={3,6,12} dB at
                         100 kHz / 20 mm/s: velocity spikes, disp rms err,
                         lock fraction (V3 methodology at the user point).
  S3  transients         frequency step 50 k->100 kHz @20 mm/s and velocity
                         step 5->30 m/s @100 kHz (5 seeds): selector trace,
                         amp err before/after the step, near-pi events;
                         upshift immediacy asserted on the T3 trace (SLOW
                         start, 20 mm/s -> 30 m/s: first selector update
                         after the step must be FAST -- the T2 trace is
                         FAST->FAST on both sides and proves nothing,
                         audit issue 2); plus the WRONG-gear
                         exposure-window measurement (SLOW held across a
                         20 mm/s -> 30 m/s step).
  S4  multi-surface      reflective -> black -> far segments (CNR 12/6/3 dB
                         with 10 us gaps at the boundaries), tracking ON:
                         per-segment lock%, relock time, amp err
                         (surface-switching concept of
                         validate_ellipse_switching, simplified to the IQ
                         tracking domain).
  S5  worst corner       100 kHz / 30 m/s + speckle tau_c=50 us + CNR=3 dB:
                         amp err, lock%, near-pi, sudden 2pi jumps, net
                         fringe error, disp rms (honest bounded report).

Heterodyne (HeNe 632.8 nm, Polytec-class, FS=50 MS/s, B_frontend=19 MHz)
  H1  range-velocity map v_range={0.1,1,3} m/s x f={50k,500k,5M} Hz x
                         CNR={0,4,12} dB: mode, |H_L|, raw ratio, corrected
                         amp err, line SNR gain, hard-limit margins.
  H2  beyond f_3dB       5 MHz with SLOW/MEDIUM/FAST: raw vs corrected amp
                         err (reproduces validate_heterodyne C24/C26).
  H3  bathtub boundary   v at 0.5*v_pi and 2*v_pi at f=fn for each gear
                         (pass/fail bracketing of the wrap line).
  H4  weak return        FAST @5 MHz, CNR sweep 0..8 dB: uncorrected noise
                         floor drop (PSV-500 weak-return reproduction).

Cross-comparison
  X1  same motion (100 kHz, 20 mm/s): homodyne SLOW vs heterodyne SLOW --
      with an honest apples/oranges note (different lambda, fs, front end,
      architecture; NOT a product ranking).

Methodology (R1-R4 fair-comparison rules of validate_tracking):
  R1  signal transfer (amp err) measured on a near-noiseless run;
  R2  noise ASD measured in a quiet window / quiet record;
  R3  SNR gain = signal gain dB + 20*log10(ASD_off/ASD_on);
  R4  medians [p10, p90] over seeds.

Physical front end (homodyne): the front end is fixed hardware, so the
model switch must follow the SIGNAL's optical Doppler extent, not the
mechanical vibration frequency (audit issue 1: the earlier
"v>10 m/s or f>50 kHz" trigger had no physical basis in f).  A cell uses
the physically consistent 86 MHz front end (B_FE = 2*F_SIGNAL_MAX
total-CNR noise + linear-phase LPF at B_FE/2, the A6 v2 model) exactly
when the homodyne Doppler peak fD_peak = 2*v_peak/LAMBDA exceeds the
40 MHz noise-band model's half-width B_NOISE_ENBW/2 = 20 MHz
(30 m/s -> 38.7 MHz; see validate_app_30ms_100khz A6).  All other cells
keep the validated 40 MHz noise-band model so the numbers stay comparable
with validate_tracking V1 -- at 100 kHz / 20 mm/s the Doppler peak is only
25.8 kHz, far inside 20 MHz, so vibration frequency alone never switches
the front-end model.

Cross-language contract: every random draw uses np.random.default_rng(seed)
with the documented seed formulas; the MATLAB port
(matlab/scenario_study/validate_realistic_scenarios.m) draws through the
numpy-exact np_rng_new kernel with the SAME seeds, so noise realizations are
bit-identical and each KEY metric matches within FP/FFT rounding (<< 5 %).
Both scripts print machine-readable "KEY," lines for the comparison.

Output: full tables on stdout + results_realistic_scenarios.txt next to
this script.  Exit code 0 iff all PASS/FAIL checks pass.
"""
import sys

# Windows consoles often run a legacy codepage (GBK/cp936); never crash on
# print (same guard as validate_app_30ms_100khz.py).
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import math
import time
from pathlib import Path

import numpy as np

import _pkgpath  # noqa: F401  (sys.path bootstrap)
from core import (
    complex_bandlimited_noise, make_speckle, fir_lp_same,
    fm_discriminator, lockin_amp, welch_psd, hl_response,
)
from design_params import (
    LAMBDA, FS, B_NOISE_ENBW, F_SIGNAL_MAX, BANDS, ORDER, PHI_GUARD,
    b_loop, select_band, select_band_hysteresis, tracking_error_rad,
    guard_flags, B_WIN,
)
from validate_tracking import gear_filter, stats
from heterodyne_tracking_design import design_params as het

TINY = 1e-300
FE_NT = 1025                    # front-end LPF taps (A6/A7/A8 model)
B_FE_PHYS = 2 * F_SIGNAL_MAX    # 86 MHz physically consistent front end
PAD = 1024                      # guard samples cut after the FE LPF so the
                                # linear-phase FIR edge taper never enters any
                                # measurement window or the PLL's gate/detector

LINES = []
CHECKS = []
KEYS = []


def out(s=''):
    print(s)
    LINES.append(s)


def key(name, value):
    """Machine-readable metric line for the Python<->MATLAB comparison."""
    KEYS.append((name, float(value)))


def check(cid, label, ok, detail):
    CHECKS.append((cid, label, bool(ok), detail))
    out(f"  [{'PASS' if ok else 'FAIL'}] {cid}  {label}  ({detail})")
    return ok


def header(title):
    out('\n' + '=' * 92)
    out(title)
    out('=' * 92)


def vdisc_h(y):
    return fm_discriminator(y, FS, LAMBDA)


def ls_amp(v, t, f_v, sel):
    """sin/cos least-squares amplitude (robust to phase / few cycles)."""
    X = np.column_stack([np.ones(int(sel.sum())),
                         np.sin(2 * np.pi * f_v * t[sel]),
                         np.cos(2 * np.pi * f_v * t[sel])])
    b, *_ = np.linalg.lstsq(X, v[sel], rcond=None)
    return float(np.hypot(b[1], b[2]))


def fe_rule(vpk):
    """(B_fe, lpf_on): physical 86 MHz front end iff the optical Doppler
    peak fD_peak = 2*v_peak/LAMBDA exceeds the 40 MHz noise-band model's
    half-width B_NOISE_ENBW/2.  The front end is fixed hardware: the
    trigger is the signal's Doppler extent (velocity), NEVER the
    mechanical vibration frequency (audit issue 1)."""
    if 2.0 * vpk / LAMBDA > B_NOISE_ENBW / 2:
        return B_FE_PHYS, True
    return B_NOISE_ENBW, False


def grid(T):
    """Padded time grid: build signals on te (Ne samples), then slice
    [PAD:PAD+N] after the front-end LPF -- measurement windows use t."""
    N = int(T * FS)
    Ne = N + 2 * PAD
    te = np.arange(Ne) / FS
    return N, Ne, te, te[PAD:PAD + N]


def fe_slice(z_ext, B_fe, lpf, N):
    z = fir_lp_same(z_ext, B_fe / 2, FS, FE_NT) if lpf else z_ext
    return z[PAD:PAD + N]


T_ON = 5e-6   # motion onset: after the PAD slice start, so the PLL always
              # sees the target start FROM REST inside the analysed record


def cos_start_motion(t, f0, vpk, t_on=T_ON):
    """Motion starting from rest at t_on: v = vpk*sin(2*pi*f0*(t-t_on))."""
    td = np.maximum(t - t_on, 0.0)
    v = vpk * np.sin(2 * np.pi * f0 * td)
    x = vpk / (2 * np.pi * f0) * (1 - np.cos(2 * np.pi * f0 * td))
    return x, v


def sudden_2pi_jumps(y, ph_true):
    ph = np.unwrap(np.angle(y))
    return int(np.sum(np.abs(np.diff(ph - ph_true)) > np.pi))


def fringe_slip(y, ph_true):
    dphi_end = float(np.unwrap(np.angle(y))[-1] - ph_true[-1])
    return int(round(dphi_end / (2 * np.pi)))


# ============================================================ S1 operating map
S1_F = (1e3, 10e3, 50e3, 100e3)
S1_V = (0.02, 1.0, 5.0, 20.0, 30.0)
S1_CNR = (3, 6, 12)
S1_T = {1e3: 3e-3, 10e3: 1e-3, 50e3: 0.5e-3, 100e3: 0.5e-3}
S1_SKIP = {1e3: 1.5e-3, 10e3: 0.4e-3, 50e3: 0.16e-3, 100e3: 0.1e-3}
S1_NSEED = 3


def s1_clean_cell(f0, vpk):
    """R1 near-noiseless run of the auto-selected gear on (f0, vpk)."""
    band = select_band(f0, vpk)
    gf = guard_flags(f0, vpk, band)
    B_fe, lpf = fe_rule(vpk)
    N, Ne, te, t = grid(S1_T[f0])
    xe, _ = cos_start_motion(te, f0, vpk)
    _, v = cos_start_motion(t, f0, vpk)
    z = fe_slice(np.exp(1j * 4 * np.pi / LAMBDA * xe), B_fe, lpf, N)
    yf, yn, _, _, dg = gear_filter(z, band, 1e-10, gate='always')
    sel = t > S1_SKIP[f0]
    a_true = max(ls_amp(v, t, f0, sel), TINY)
    err = 100 * (ls_amp(vdisc_h(yf), t, f0, sel) / a_true - 1)
    err_nco = 100 * (ls_amp(vdisc_h(yn), t, f0, sel) / a_true - 1)
    return dict(band=band, err=err, err_nco=err_nco,
                near_pi=dg['near_pi_events'], B_fe=B_fe, lpf=lpf, **gf)


def s1_noise_cache(needed):
    """Noise-floor reduction vs OFF (R2), static carrier, per (band,cnr,lpf).

    The R2 rule measures noise where the carrier is quiet/static, so the
    reduction is scene-independent; one cached measurement serves every map
    cell using that (gear, CNR, front-end) combination.  Eval band
    10..100 kHz (the structure band; click noise is white there).
    """
    T, L = 0.5e-3, 16384
    N, Ne, te, t = grid(T)
    W = t > 0.1e-3

    def asd(v):
        P, f = welch_psd(v[W], FS, L)
        m = (f >= 10e3) & (f <= 100e3)
        return max(math.sqrt(float(np.median(P[m]))), TINY)

    groups = {}
    for band, cnr, lpf in needed:
        groups.setdefault((cnr, lpf), set()).add(band)
    cache = {}
    for (cnr, lpf), bands in sorted(groups.items()):
        s2 = 10 ** (-cnr / 10)
        B_fe = B_FE_PHYS if lpf else B_NOISE_ENBW
        acc = {b: [] for b in bands}
        for s in range(S1_NSEED):
            seed = 210000 + (50000 if lpf else 0) + cnr * 1000 + s
            rng = np.random.default_rng(seed)
            z = fe_slice(1.0 + complex_bandlimited_noise(Ne, FS, B_fe, s2, rng),
                         B_fe, lpf, N)
            a_off = asd(vdisc_h(z))
            for b in sorted(bands):
                yf, _, _, _, _ = gear_filter(z, b, s2, gate='auto')
                acc[b].append(20 * math.log10(a_off / asd(vdisc_h(yf))))
        for b in bands:
            cache[(b, cnr, lpf)] = stats(acc[b])[0]
    return cache


def S1():
    header('S1  零差工况地图: f={1,10,50,100}kHz x v={0.02,1,5,20,30}m/s x '
           'CNR={3,6,12}dB\n    (amp err = R1 近无噪 LS 幅值; stG = R3 信号增益'
           ' + R2 静态载波底噪下降中值 (结构带 10..100kHz, %d seeds) -- 非逐格'
           '动态实测, 动态抽查见 S1e;\n    前端: fD_peak=2*v/lambda > '
           'B_NOISE_ENBW/2=20MHz (即 v_peak > 15.5 m/s) 的格点用 B_FE=86MHz '
           '总CNR + 线性相位 LPF, 其余 40MHz 噪声带模型)' % S1_NSEED)
    cells = {}
    needed = set()
    for f0 in S1_F:
        for vpk in S1_V:
            c = s1_clean_cell(f0, vpk)
            cells[(f0, vpk)] = c
            for cnr in S1_CNR:
                needed.add((c['band'], cnr, c['lpf']))
    cache = s1_noise_cache(needed)

    out(f"\n    {'f':>6} {'v_peak':>9} {'gear':>7} {'phi_err':>8} {'guard':>10}"
        f" {'FE':>6} | {'ampErr':>8} {'ampErrNCO':>9} {'np':>3} |"
        + ''.join(f"{'stG@' + str(c) + 'dB':>10}" for c in S1_CNR))
    ok_a, ok_b, ok_c1, ok_c2 = True, True, True, True
    worst_a, worst_b = 0.0, 0.0
    for f0 in S1_F:
        for vpk in S1_V:
            c = cells[(f0, vpk)]
            gtag = 'ok' if c['guard_ok'] else 'OVERRANGE'
            fetag = '86M+L' if c['lpf'] else '40M'
            gains = []
            for cnr in S1_CNR:
                g_sig = 20 * math.log10(max(1 + c['err'] / 100, 1e-12))
                gains.append(g_sig + cache[(c['band'], cnr, c['lpf'])])
            out(f"    {f0/1e3:4.0f}k {vpk*1e3:7.0f}mm {c['band']:>7} "
                f"{c['phi_err']:7.3f}r {gtag:>10} {fetag:>6} | "
                f"{c['err']:+7.2f}% {c['err_nco']:+8.2f}% {c['near_pi']:3d} |"
                + ''.join(f"{g:+9.2f} " for g in gains))
            key(f"S1_err_f{f0/1e3:.0f}k_v{vpk*1e3:.0f}", c['err'])
            key(f"S1_nco_f{f0/1e3:.0f}k_v{vpk*1e3:.0f}", c['err_nco'])
            key(f"S1_gain3_f{f0/1e3:.0f}k_v{vpk*1e3:.0f}", gains[0])
            if c['guard_ok']:
                ok_a &= abs(c['err']) < 5.0 and c['near_pi'] == 0
                worst_a = max(worst_a, abs(c['err']))
            else:
                ok_b &= abs(c['err']) < 10.0 and c['near_pi'] == 0
                worst_b = max(worst_b, abs(c['err']))
            if c['band'] == 'SLOW':
                ok_c1 &= gains[0] > 10.0
            ok_c2 &= gains[0] > 0.0
        out('')
    out('  说明1: (100kHz, 20m/s) 的 phi_err=1.001 rad 恰好压在守卫线上 -- '
        '守卫边界实测就在用户 20..30 m/s 高速区内.')
    out('  说明2: ampErr(full输出) 由公共 4MHz 残差窗定标, 与档位/phi_err 几乎'
        '无关 (设计意图); ampErrNCO 是载波路径单独的\n  幅值误差, 随 phi_err '
        '增大而恶化 -- 档位动态只影响载波路径与噪声, 不影响 full 输出的幅值'
        '刻度 (validate_zeta_sweep 结论).')
    out('  说明3: 40M 与 86M+L 格点的 OFF 参考不同 (同总CNR下更宽前端点击更多, '
        'PSD 更低), 增益不可跨前端相减.\n  FAST 在 40M/CNR3 处于环内点击门限'
        '之下 (feed-through, 增益 ~+12dB), 在 86M 同总CNR 环内CNR 高 3.3dB '
        '越过门限\n  (滑周率对环内CNR指数敏感) -- 全输出噪声底由公共窗决定, '
        '三档增益趋同 ~+50dB. CNR 指标必须在实际前端带宽上定义 (A6).')
    out('  说明4: stG 列是 R2 静态载波方法的底噪下降 (刻意与运动场景无关, 每个 '
        '(档位, CNR, 前端) 组合一个缓存值),\n  不是该格点真实运动下的逐格实测 '
        '-- 动态实测抽查见下方 S1e (audit issue 3).')
    check('S1a', '守卫内 (guard_ok) 全部格点: clean |ampErr| < 5% 且 0 near-pi',
          ok_a, f'worst {worst_a:.2f}%')
    check('S1b', 'OVERRANGE 格点 (100kHz x 20/30m/s): clean |ampErr| < 10% 且 '
          '0 near-pi (降级区仍可测幅值)', ok_b, f'worst {worst_b:.2f}%')
    check('S1c', 'SLOW 档格点 CNR=3dB SNR gain > +10 dB (门限扩展)', ok_c1,
          'see table')
    check('S1d', '全部格点 CNR=3dB SNR gain > 0 dB', ok_c2, 'see table')
    s1_dynamic_spot(cells, cache)
    return cells, cache


# --------------------------------------------- S1e dynamic spot check (issue 3)
S1E_PTS = ((100e3, 0.02), (10e3, 30.0), (100e3, 30.0))
S1E_CNR = 3
S1E_NSEED = 3


def s1_dynamic_spot(cells, cache):
    """R1+R3 on ACTUAL motion: full dynamic noisy runs on 3 map cells.

    Noise on each output = (chain output of signal+noise) - (chain output
    of the clean signal), both with the SAME gate policy, so the
    deterministic motion cancels and the residual is the true dynamic
    output noise (clicks, slip transients, dropout flywheel included).
    ASD in
    the structure band 10..100 kHz, median over seeds; compared against
    the S1 static-carrier cached value of the same (gear, CNR, FE)."""
    out('\n  S1e 动态抽查 (audit issue 3): 3 个格点在真实运动 + CNR='
        f'{S1E_CNR}dB 噪声下全动态实测底噪下降 ({S1E_NSEED} seeds 中值);')
    out('  噪声 = 含噪运行输出 - 同链路清洁运行输出 (gate=auto 两者一致), '
        '评估带同缓存 (10..100kHz).')
    out(f"    {'cell':<22} {'gear':>7} {'FE':>6} | {'dynGain@3dB':>12} "
        f"{'statGain@3dB':>13} {'dyn-stat':>9} {'np中':>6}")
    L = 16384
    rows = []
    for ipt, (f0, vpk) in enumerate(S1E_PTS):
        c = cells[(f0, vpk)]
        band = c['band']
        B_fe, lpf = fe_rule(vpk)
        N, Ne, te, t = grid(S1_T[f0])
        xe, _ = cos_start_motion(te, f0, vpk)
        ph_e = 4 * np.pi / LAMBDA * xe
        s2 = 10 ** (-S1E_CNR / 10)
        W = t > S1_SKIP[f0]

        def asd(v):
            P, f = welch_psd(v[W], FS, L)
            m = (f >= 10e3) & (f <= 100e3)
            return max(math.sqrt(float(np.median(P[m]))), TINY)

        zc = fe_slice(np.exp(1j * ph_e), B_fe, lpf, N)
        ycf, _, _, _, _ = gear_filter(zc, band, s2, gate='auto')
        v_off_c, v_on_c = vdisc_h(zc), vdisc_h(ycf)
        vals, nps = [], []
        for s in range(S1E_NSEED):
            rng = np.random.default_rng(215000 + ipt * 1000 + s)
            z = fe_slice(np.exp(1j * ph_e)
                         + complex_bandlimited_noise(Ne, FS, B_fe, s2, rng),
                         B_fe, lpf, N)
            yf, _, _, _, dg = gear_filter(z, band, s2, gate='auto')
            vals.append(20 * math.log10(asd(vdisc_h(z) - v_off_c)
                                        / asd(vdisc_h(yf) - v_on_c)))
            nps.append(dg['near_pi_events'])
        g_sig = 20 * math.log10(max(1 + c['err'] / 100, 1e-12))
        g_dyn = g_sig + stats(vals)[0]
        g_stat = g_sig + cache[(band, S1E_CNR, lpf)]
        np_med = stats(nps)[0]
        fetag = '86M+L' if lpf else '40M'
        out(f"    {f0/1e3:4.0f}kHz/{vpk*1e3:6.0f}mm/s     {band:>7} "
            f"{fetag:>6} | {g_dyn:+11.2f} {g_stat:+12.2f} "
            f"{g_dyn - g_stat:+8.2f} {np_med:6.0f}")
        key(f"S1e_dyn_f{f0/1e3:.0f}k_v{vpk*1e3:.0f}", g_dyn)
        rows.append((g_dyn, g_stat))
    out('  解读: 用户点 (100kHz/20mm/s, SLOW) 动态实测与静态缓存一致 (差 ~1 dB'
        ', SLOW 的 B_loop=0.49MHz < B_WIN, 点击被公共窗清除) --\n  缓存方法在窄'
        '档格点成立; 30 m/s FAST 格点动态增益坍缩: 真实运动把环路推入点击高发区'
        ' (np 中值数百..数千, 静态载波下 ~0),\n  且 FAST 的 B_loop=7.1MHz > '
        'B_WIN=4MHz 点击直通全输出 (说明3 的 feed-through 同机理) -- 静态缓存值'
        '在高速 FAST 格点只是\n  场景无关上界, 不可当动态 SNR 读 (S1 表因此'
        '标注 stG; 产品在 OVERRANGE 角点必须按 S5 的降级语义上报).')
    check('S1e', '动态抽查: 用户点 (100k/20mm) dyn > +30 dB 且 |dyn-stat| < '
          '6 dB; 30m/s FAST 格点 dyn 比 stat 低 > 20 dB (静态缓存=上界)',
          rows[0][0] > 30.0 and abs(rows[0][0] - rows[0][1]) < 6.0
          and all(gs - g > 20.0 for g, gs in rows[1:]),
          ', '.join(f'{g:+.1f}/{gs:+.1f}' for g, gs in rows))


# ============================================================ S2 speckle matrix
S2_TAU = (20e-6, 50e-6, 100e-6)
S2_CNR = (3, 6, 12)
S2_NSEED = 4


def S2():
    from core import burst_signal
    band = select_band(100e3, 0.02)
    B_OUT, vamp = 1e6, 0.02
    thr = 20 * vamp
    B_fe, lpf = fe_rule(vamp)     # fD_peak=25.8kHz << 20MHz -> 40MHz 噪声带
    fetag = f'{B_fe/1e6:.0f}MHz' + ('+LPF' if lpf else '')
    header(f'S2  散斑矩阵 @100kHz/20mm/s (gear={band}, gate=auto, '
           f'B_FE={fetag}, 输出滤到 {B_OUT/1e6:.0f}MHz, '
           f'{S2_NSEED} seeds) -- V3 方法在用户工况点')
    # validate_tracking 100 kHz scene (T=0.5 ms, 20-cycle burst @0.02 ms),
    # rebuilt on the padded grid so the FE LPF edges stay outside the record.
    N, Ne, te, t = grid(5e-4)
    xe, _, _ = burst_signal(te, 100e3, vamp, 20, 0.02e-3)
    ph_e = 4 * np.pi / LAMBDA * xe
    Wq = (t > 0.26e-3) & (t < 0.48e-3)
    res = {}
    for itau, tau in enumerate(S2_TAU):
        for cnr in S2_CNR:
            s2 = 10 ** (-cnr / 10)
            acc = dict(sp_off=[], sp_on=[], dr_off=[], dr_on=[], lock=[])
            for s in range(S2_NSEED):
                seed = 220000 + itau * 3000 + cnr * 100 + s
                rng = np.random.default_rng(seed)
                h_e = make_speckle(Ne, FS, tau, rng)
                z = fe_slice(h_e * np.exp(1j * ph_e)
                             + complex_bandlimited_noise(Ne, FS, B_fe, s2, rng),
                             B_fe, lpf, N)
                ph_ref = (ph_e[PAD:PAD + N]
                          + np.unwrap(np.angle(h_e[PAD:PAD + N])))
                ph_ref -= ph_ref[0]
                xref = fir_lp_same(LAMBDA / (4 * np.pi) * ph_ref, B_OUT, FS, 2049)
                yf, _, _, _, dg = gear_filter(z, band, s2, gate='auto')
                acc['lock'].append(dg['lock_frac'])
                for tag, y in (('off', z), ('on', yf)):
                    v = vdisc_h(y)
                    vlp = fir_lp_same(v, B_OUT, FS, 2049)
                    ex = np.abs(vlp[Wq]) > thr
                    acc['sp_' + tag].append(int(np.sum(
                        np.diff(np.concatenate(([False], ex)).astype(int)) == 1)))
                    ph = np.unwrap(np.angle(y))
                    ph -= ph[0]
                    xh = fir_lp_same(LAMBDA / (4 * np.pi) * ph, B_OUT, FS, 2049)
                    e = xh - xref
                    acc['dr_' + tag].append(1e9 * float(np.std(e - e.mean())))
            res[(tau, cnr)] = acc
    out(f"\n    {'tau_c':>6} {'CNR':>5} | {'spikes OFF':>11} {'spikes ON':>10} |"
        f" {'disp rms OFF nm':>15} {'disp rms ON nm':>15} | {'lock%':>6}")
    ok_sp, ok_lk = True, True
    for tau in S2_TAU:
        for cnr in S2_CNR:
            a = res[(tau, cnr)]
            spo, spn = stats(a['sp_off'])[0], stats(a['sp_on'])[0]
            dro, drn = stats(a['dr_off'])[0], stats(a['dr_on'])[0]
            lk = 100 * float(np.mean(a['lock']))
            out(f"    {tau*1e6:4.0f}us {cnr:3d}dB | {spo:11.0f} {spn:10.0f} | "
                f"{dro:15.0f} {drn:15.0f} | {lk:6.1f}")
            key(f"S2_lock_t{tau*1e6:.0f}_c{cnr}", lk)
            key(f"S2_dron_t{tau*1e6:.0f}_c{cnr}", drn)
            ok_sp &= spn <= spo
            if cnr == 12:
                ok_lk &= lk > 75.0
        out('')
    out('  诚实注记: 掉落期间 NCO 飞轮只能外推, 位移连续性无法承诺 (同 V3); '
        'ON 的位移 rms 含掉落期外推误差;\n  lock% 不到 100 是门控按设计在散斑'
        '深衰落中放开 (invalid 标志), 不是缺陷 -- 见 OPTIMIZATION_GUIDE 门控节.')
    check('S2a', '全部 (tau_c x CNR): gate-on 速度尖峰中值 <= OFF (尖峰不恶化)',
          ok_sp, 'see table')
    check('S2b', 'CNR=12dB: lock fraction > 75% (全部 tau_c; 余量在散斑衰落'
          '统计内)', ok_lk, 'see table')
    return res


# ============================================================ S3 transients
S3_NSEED = 5
S3_CNR = 6.0


def selector_trace(name, seq, start):
    out(f'\n  {name} (选档状态机, 每行=一次选档更新, 起始档 {start})')
    out(f"    {'update':>6} {'f':>7} {'v_peak':>9} | {'target':>7} "
        f"{'applied':>8} {'phi_err(applied)':>16}")
    band = start
    hist = []
    for i, (f0, v) in enumerate(seq):
        tgt = select_band(f0, v)
        band = select_band_hysteresis(f0, band, v)
        pe = tracking_error_rad(f0, v, BANDS[band]['fn'])
        out(f"    {i:>6} {f0/1e3:5.0f}k {v*1e3:8.0f}mm/s | {tgt:>7} "
            f"{band:>8} {pe:15.4g}r")
        hist.append((band, tgt, pe))
    return hist


def s3_freq_step_motion(t, ts, f1, f2, vp):
    """Velocity-continuous frequency step at ts; motion from rest at T_ON."""
    td = np.maximum(t - T_ON, 0.0)
    td_s = ts - T_ON
    th_s = 2 * np.pi * f1 * td_s
    pre = t < ts
    v = np.where(pre, vp * np.sin(2 * np.pi * f1 * td),
                 vp * np.sin(th_s + 2 * np.pi * f2 * (td - td_s)))
    x = np.where(pre, vp / (2 * np.pi * f1) * (1 - np.cos(2 * np.pi * f1 * td)),
                 vp / (2 * np.pi * f1) * (1 - math.cos(th_s))
                 + vp / (2 * np.pi * f2) * (math.cos(th_s)
                                            - np.cos(th_s + 2 * np.pi * f2 * (td - td_s))))
    return x, v


def s3_vel_step_motion(t, ts, f0, v1, v2, tr=20e-6):
    """Amplitude step v1->v2 (raised-cosine ramp tr at ts), rest until T_ON."""
    td = np.maximum(t - T_ON, 0.0)
    u = np.clip((t - ts) / tr, 0.0, 1.0)
    A = v1 + (v2 - v1) * 0.5 * (1 - np.cos(np.pi * u))
    v = A * np.sin(2 * np.pi * f0 * td)
    x = np.cumsum(v) / FS
    return x, v


def s3_run(tag, band, xe, v, N, Ne, t, f_pre, f_post, Wpre, Wpost,
           B_fe, lpf, iscen):
    ph_e = 4 * np.pi / LAMBDA * xe
    zc = fe_slice(np.exp(1j * ph_e), B_fe, lpf, N)
    yf, _, _, _, dg = gear_filter(zc, band, 1e-10, gate='always')
    vd = vdisc_h(yf)
    e_pre_c = 100 * (ls_amp(vd, t, f_pre, Wpre)
                     / max(ls_amp(v, t, f_pre, Wpre), TINY) - 1)
    e_post_c = 100 * (ls_amp(vd, t, f_post, Wpost)
                      / max(ls_amp(v, t, f_post, Wpost), TINY) - 1)
    np_c = dg['near_pi_events']
    s2 = 10 ** (-S3_CNR / 10)
    E_pre, E_post, NP, LK = [], [], [], []
    for s in range(S3_NSEED):
        rng = np.random.default_rng(230000 + iscen * 5000 + s)
        z = fe_slice(np.exp(1j * ph_e)
                     + complex_bandlimited_noise(Ne, FS, B_fe, s2, rng),
                     B_fe, lpf, N)
        yf, _, _, _, dg = gear_filter(z, band, s2, gate='auto')
        vd = vdisc_h(yf)
        E_pre.append(100 * (ls_amp(vd, t, f_pre, Wpre)
                            / max(ls_amp(v, t, f_pre, Wpre), TINY) - 1))
        E_post.append(100 * (ls_amp(vd, t, f_post, Wpost)
                             / max(ls_amp(v, t, f_post, Wpost), TINY) - 1))
        NP.append(dg['near_pi_events'])
        LK.append(dg['lock_frac'])
    out(f"    {tag:<34} {band:>6} | {e_pre_c:+8.2f}% {e_post_c:+8.2f}% "
        f"{np_c:4d} | {stats(E_pre)[0]:+8.2f}% {stats(E_post)[0]:+8.2f}% "
        f"{stats(NP)[0]:5.0f} {100*float(np.mean(LK)):6.1f}")
    return dict(e_pre_c=e_pre_c, e_post_c=e_post_c, np_c=np_c,
                e_pre=stats(E_pre)[0], e_post=stats(E_post)[0])


def S3():
    header(f'S3  瞬态: 频率阶跃 50k->100kHz @20mm/s 与速度阶跃 5->30m/s '
           f'@100kHz (CNR={S3_CNR:.0f}dB, {S3_NSEED} seeds)\n    换档只发生在'
           '选档更新时刻 (离散状态机); 本节先给选档轨迹, 再给 "阶跃两侧同一档" '
           'PLL 实测 (T1/T2 阶跃前后选档不变),\n    最后实测 "旧档暴露窗" '
           '(T3: SLOW 被 20mm/s->30m/s 阶跃甩在错档上).')
    selector_trace('T1 选档轨迹: 50 kHz -> 100 kHz @ 20 mm/s',
                   [(50e3, 0.02)] * 2 + [(100e3, 0.02)] * 3, 'SLOW')
    selector_trace('T2 选档轨迹: 5 m/s -> 30 m/s @ 100 kHz',
                   [(100e3, 5.0)] * 2 + [(100e3, 30.0)] * 3, 'FAST')
    tr3 = selector_trace('T3 选档轨迹: 20 mm/s -> 30 m/s @ 100 kHz (SLOW 起)',
                         [(100e3, 0.02)] * 2 + [(100e3, 30.0)] * 3, 'SLOW')

    T, ts = 0.5e-3, 0.25e-3
    N, Ne, te, t = grid(T)
    out(f"\n    {'scenario':<34} {'gear':>6} | {'pre清洁':>8} {'post清洁':>8} "
        f"{'np':>4} | {'pre噪中值':>8} {'post噪中值':>8} {'np中':>5} {'lock%':>6}")

    xe, _ = s3_freq_step_motion(te, ts, 50e3, 100e3, 0.02)
    _, v = s3_freq_step_motion(t, ts, 50e3, 100e3, 0.02)
    W1p = (t > 0.10e-3) & (t < 0.24e-3)
    W1q = (t > 0.30e-3) & (t < 0.48e-3)
    B_fe, lpf = fe_rule(0.02)
    r1 = s3_run('T1 freq step 50k->100k @20mm/s', 'SLOW', xe, v, N, Ne, t,
                50e3, 100e3, W1p, W1q, B_fe, lpf, 0)

    xe, ve = s3_vel_step_motion(te, ts, 100e3, 5.0, 30.0)
    v = ve[PAD:PAD + N]
    B_fe, lpf = fe_rule(30.0)
    r2 = s3_run('T2 vel step 5->30m/s @100k', 'FAST', xe, v, N, Ne, t,
                100e3, 100e3, W1p, W1q, B_fe, lpf, 1)

    xe, ve = s3_vel_step_motion(te, ts, 100e3, 0.02, 30.0)
    v = ve[PAD:PAD + N]
    zc = fe_slice(np.exp(1j * 4 * np.pi / LAMBDA * xe), B_fe, lpf, N)
    yf, _, _, _, dg = gear_filter(zc, 'SLOW', 1e-10, gate='always')
    vd = vdisc_h(yf)
    e3 = 100 * (ls_amp(vd, t, 100e3, W1q)
                / max(ls_amp(v, t, 100e3, W1q), TINY) - 1)
    out(f"    {'T3 WRONG gear (SLOW跨 20mm->30m/s)':<33} {'SLOW':>6} | "
        f"{'--':>8} {e3:+8.2f}% {dg['near_pi_events']:4d} | (clean only: "
        '暴露窗内旧档的实测破坏)')

    key('S3_T1_post', r1['e_post_c'])
    key('S3_T2_post', r2['e_post_c'])
    key('S3_T3_post', e3)
    out('\n  解读: T1/T2 阶跃前后选档不变 (SLOW/FAST), 环路自身跟过阶跃, '
        '幅值误差保持; T3 显示若选档更新慢了,\n  旧档 (SLOW) 在 30 m/s 上'
        f'幅值误差 {e3:+.0f}% 且 near-pi {dg["near_pi_events"]} 次 -- '
        '选档更新周期就是唯一暴露窗 (validate_app A3 结论的实测版).')
    check('S3a', 'T1 (SLOW 跨频率阶跃): 清洁 pre/post |ampErr| < 5%',
          abs(r1['e_pre_c']) < 5 and abs(r1['e_post_c']) < 5,
          f"pre {r1['e_pre_c']:+.2f}%, post {r1['e_post_c']:+.2f}%")
    check('S3b', 'T2 (FAST 跨 5->30m/s 阶跃): 清洁 post |ampErr| < 10% 且 '
          '0 near-pi', abs(r2['e_post_c']) < 10 and r2['np_c'] == 0,
          f"post {r2['e_post_c']:+.2f}%, np {r2['np_c']}")
    check('S3c', 'T3 升档即时性 (选档轨迹): SLOW 起, 20mm/s->30m/s 阶跃后第 1 '
          '次选档更新即 FAST (真 SLOW->FAST 升档; T2 的 FAST->FAST 不构成检验)',
          tr3[1][0] == 'SLOW' and tr3[2][0] == 'FAST',
          f'update1 {tr3[1][0]} -> update2 {tr3[2][0]}')
    check('S3d', 'T3 旧档暴露窗: SLOW 在 30 m/s 上 |ampErr| > 50% '
          '(升档必须即时生效)', abs(e3) > 50, f'{e3:+.1f}%')
    return r1, r2, e3


# ============================================================ S4 multi-surface
S4_SEGS = ((12, '反光膜(强回光)'), (6, '黑面(弱回光)'), (3, '远距(更弱)'))
S4_TSEG = 0.15e-3
S4_GAP = 20e-6
S4_GAPDROP = 10 ** (-30 / 20)
S4_NSEED = 4


def S4():
    band = select_band(100e3, 0.02)
    B_fe, lpf = fe_rule(0.02)
    header(f'S4  多表面切换 (反光->黑面->远距, 段CNR=12/6/3dB, 段边界 '
           f'{S4_GAP*1e6:.0f}us -30dB 缝隙, gear={band}, gate=auto, '
           f'{S4_NSEED} seeds)\n    -- validate_ellipse_switching 的表面切换'
           '概念移植到 IQ 跟踪域: 噪声底恒定, 回光幅值分段跳变.')
    T = 3 * S4_TSEG
    N, Ne, te, t = grid(T)
    xe, _ = cos_start_motion(te, 100e3, 0.02)
    _, v = cos_start_motion(t, 100e3, 0.02)
    ph_e = 4 * np.pi / LAMBDA * xe
    s2N = 10 ** (-3 / 10)      # constant receiver noise power; CNR by amplitude
    env = np.zeros(Ne)
    for i, (cnr, _) in enumerate(S4_SEGS):
        m = (te >= i * S4_TSEG) & (te < (i + 1) * S4_TSEG)
        env[m] = math.sqrt(s2N * 10 ** (cnr / 10))
    env[te >= 3 * S4_TSEG] = math.sqrt(s2N * 10 ** (S4_SEGS[-1][0] / 10))
    for ts in (S4_TSEG, 2 * S4_TSEG):
        env[(te >= ts) & (te < ts + S4_GAP)] *= S4_GAPDROP

    res = dict(lock=[[] for _ in S4_SEGS], err=[[] for _ in S4_SEGS],
               relock=[[], []], inv=[[], []])
    for s in range(S4_NSEED):
        rng = np.random.default_rng(240000 + s)
        z = fe_slice(env * np.exp(1j * ph_e)
                     + complex_bandlimited_noise(Ne, FS, B_fe, s2N, rng),
                     B_fe, lpf, N)
        yf, _, _, st, _ = gear_filter(z, band, s2N, gate='auto')
        vd = vdisc_h(yf)
        for i in range(3):
            t0s, t1s = i * S4_TSEG, (i + 1) * S4_TSEG
            Wl = (t >= t0s + 70e-6) & (t < t1s)      # post-acquisition window
            res['lock'][i].append(100 * float(np.mean(st[Wl] == 2)))
            res['err'][i].append(100 * (
                ls_amp(vd, t, 100e3, Wl) / max(ls_amp(v, t, 100e3, Wl), TINY) - 1))
        for j, ts in enumerate((S4_TSEG, 2 * S4_TSEG)):
            gw = (t >= ts) & (t < ts + S4_GAP)
            res['inv'][j].append(100 * float(np.mean(st[gw] != 2)))
            after = np.where((t >= ts + S4_GAP) & (st == 2))[0]
            res['relock'][j].append(
                (t[after[0]] - (ts + S4_GAP)) * 1e6 if after.size else float('inf'))
    out(f"\n    {'segment':<18} {'CNR':>5} | {'lock% 中值':>10} "
        f"{'ampErr% 中值':>12}")
    for i, (cnr, name) in enumerate(S4_SEGS):
        lk = stats(res['lock'][i])[0]
        er = stats(res['err'][i])[0]
        out(f"    {name:<18} {cnr:3d}dB | {lk:10.1f} {er:+12.2f}")
        key(f'S4_lock_seg{i}', lk)
        key(f'S4_err_seg{i}', er)
    out(f"\n    {'boundary':<18} | {'gap invalid% 中值':>17} "
        f"{'relock us 中值':>14}")
    for j, nm in enumerate(('反光->黑面', '黑面->远距')):
        out(f"    {nm:<18} | {stats(res['inv'][j])[0]:17.0f} "
            f"{stats(res['relock'][j])[0]:14.1f}")
    ok_rl = all(np.isfinite(r) and r <= 80.0
                for j in range(2) for r in res['relock'][j])
    ok_er = all(abs(stats(res['err'][i])[0]) < 10.0 for i in range(3))
    ok_lk = stats(res['lock'][2])[0] > 80.0
    out('\n  解读: 段间 6dB 幅值跳变本身不触发门控 (rel_off=0.08 容忍), '
        '边界缝隙触发 HOLD->ACQUIRE->LOCK 重捕;\n  SLOW 档重捕时间由 '
        'acq_time=4*tauF=32us + 门控检测延迟决定.')
    check('S4a', '每个边界每个 seed 都重捕, relock <= 80 us', ok_rl,
          f"medians {stats(res['relock'][0])[0]:.1f} / "
          f"{stats(res['relock'][1])[0]:.1f} us")
    check('S4b', '三段 (12/6/3dB) 幅值误差中值 |err| < 10%', ok_er,
          ', '.join(f"{stats(res['err'][i])[0]:+.1f}%" for i in range(3)))
    check('S4c', '最弱段 (远距 3dB) lock% 中值 > 80%', ok_lk,
          f"{stats(res['lock'][2])[0]:.1f}%")
    return res


# ============================================================ S5 worst corner
S5_NSEED = 6


def S5():
    band = 'FAST'
    tau, cnr = 50e-6, 3.0
    B_fe, lpf = B_FE_PHYS, True
    header(f'S5  最坏角点: 100kHz/30m/s + 散斑 tau_c={tau*1e6:.0f}us + '
           f'CNR={cnr:.0f}dB (gear={band} fallback, B_FE=86MHz+LPF, '
           f'gate=auto, {S5_NSEED} seeds) -- 有界诚实报告')
    T = 0.5e-3
    N, Ne, te, t = grid(T)
    xe, _ = cos_start_motion(te, 100e3, 30.0)
    _, v = cos_start_motion(t, 100e3, 30.0)
    ph_e = 4 * np.pi / LAMBDA * xe
    s2 = 10 ** (-cnr / 10)
    W = t > 0.15e-3
    B_OUT = 1e6
    acc = dict(err=[], errl=[], lock=[], np=[], j2=[], fr=[], dr=[])
    for s in range(S5_NSEED):
        rng = np.random.default_rng(250000 + s)
        h_e = make_speckle(Ne, FS, tau, rng)
        z = fe_slice(h_e * np.exp(1j * ph_e)
                     + complex_bandlimited_noise(Ne, FS, B_fe, s2, rng),
                     B_fe, lpf, N)
        ph_ref = ph_e[PAD:PAD + N] + np.unwrap(np.angle(h_e[PAD:PAD + N]))
        ph_ref -= ph_ref[0]
        yf, _, _, st, dg = gear_filter(z, band, s2, gate='auto')
        vd = vdisc_h(yf)
        acc['err'].append(100 * (ls_amp(vd, t, 100e3, W)
                                 / max(ls_amp(v, t, 100e3, W), TINY) - 1))
        Wl = W & (st == 2)     # product-meaningful: invalid samples excluded
        acc['errl'].append(100 * (ls_amp(vd, t, 100e3, Wl)
                                  / max(ls_amp(v, t, 100e3, Wl), TINY) - 1))
        acc['lock'].append(100 * dg['lock_frac'])
        acc['np'].append(dg['near_pi_events'])
        acc['j2'].append(sudden_2pi_jumps(yf, ph_ref))
        acc['fr'].append(abs(fringe_slip(yf, ph_ref)))
        phh = np.unwrap(np.angle(yf))
        phh -= phh[0]
        e = (fir_lp_same(LAMBDA / (4 * np.pi) * phh, B_OUT, FS, 2049)
             - fir_lp_same(LAMBDA / (4 * np.pi) * ph_ref, B_OUT, FS, 2049))
        acc['dr'].append(1e9 * float(np.std(e - e.mean())))
    out(f"\n    {'metric':<34} {'median':>10} {'p10':>10} {'p90':>10}")
    for lbl, k in (('ampErr % (全窗含掉落)', 'err'),
                   ('ampErr % (仅 LOCK 有效样本)', 'errl'),
                   ('lock %', 'lock'),
                   ('near-pi events', 'np'), ('sudden 2pi jumps', 'j2'),
                   ('|net fringe err| (cycles)', 'fr'),
                   ('disp rms err nm (1MHz)', 'dr')):
        m, lo, hi = stats(acc[k])
        out(f"    {lbl:<34} {m:10.1f} {lo:10.1f} {hi:10.1f}")
    key('S5_err_med', stats(acc['err'])[0])
    key('S5_errl_med', stats(acc['errl'])[0])
    key('S5_lock_med', stats(acc['lock'])[0])
    out('\n  诚实结论: 最坏角点三重叠加 (fallback 档 phi_err=1.5 rad + 散斑'
        '掉落 + 3dB 弱光): 全窗幅值被掉落期 NCO 外推稀释 (invalid 期数据本就'
        '不该计入);\n  仅取 LOCK 有效样本后幅值刻度有界可用. 净条纹漂移 '
        '10^1..10^2 周/0.5ms -- 位移积分在该角点无效 (与 validate_app A8/N2 '
        '一致),\n  产品须按 overrange + 散斑 invalid 同时上报.')
    m_errl = stats(acc['errl'])[0]
    m_lock = stats(acc['lock'])[0]
    check('S5a', '最坏角点 LOCK 有效样本 ampErr 中值 |err| < 40% '
          '(有界降级 -- 实测约 -33%, 全窗则 ~-50%)', abs(m_errl) < 40.0,
          f'{m_errl:+.1f}%')
    check('S5b', '最坏角点 lock fraction 中值 > 50% (可用数据比例)',
          m_lock > 50.0, f'{m_lock:.1f}%')
    return acc


# ======================================================= heterodyne scenarios
HFS = het.FS
HLAM = het.LAMBDA
HZ = het.ZETA
HBF = het.B_FRONTEND
H_DF = 20e3
H_VAMP = 10e-3
H_SCENES = {
    50e3: dict(ncyc=10, t0=0.15e-3, T=0.8e-3, L=8192, band=(10e3, 90e3),
               q0=0.40e-3, q1=0.78e-3),
    100e3: dict(ncyc=15, t0=0.10e-3, T=0.5e-3, L=8192, band=(50e3, 150e3),
                q0=0.28e-3, q1=0.48e-3),
    500e3: dict(ncyc=25, t0=0.10e-3, T=0.4e-3, L=4096, band=(0.3e6, 0.7e6),
                q0=0.17e-3, q1=0.39e-3),
    5e6: dict(ncyc=40, t0=0.10e-3, T=0.3e-3, L=4096, band=(4e6, 6e6),
              q0=0.13e-3, q1=0.29e-3),
}


def het_scene(f0):
    from core import burst_signal
    p = H_SCENES[f0]
    N = int(p['T'] * HFS)
    t = np.arange(N) / HFS
    x, v, _ = burst_signal(t, f0, H_VAMP, p['ncyc'], p['t0'])
    ph = 4 * np.pi / HLAM * x + 2 * np.pi * H_DF * t
    Wm = (t > p['t0']) & (t < p['t0'] + p['ncyc'] / f0)
    Wq = (t > p['q0']) & (t < p['q1'])
    return dict(f0=f0, N=N, t=t, v=v, ph=ph, Wm=Wm, Wq=Wq, p=p)


def het_vdisc(y):
    return fm_discriminator(y, HFS, HLAM)


def het_hl_mag(f0, fn):
    return float(np.abs(hl_response(np.array([f0]), HFS, fn, HZ))[0])


def het_run_pll(z, fn, s2):
    from core import pll_carrier_regen
    return pll_carrier_regen(z, HFS, fn, max(s2, 1e-12), zeta=HZ,
                             gate='always')


def het_asd(v, sel, L, band):
    P, f = welch_psd(v[sel], HFS, L)
    m = (f >= band[0]) & (f <= band[1])
    return max(math.sqrt(float(np.median(P[m]))), TINY)


def het_pick_mode(f0, modes):
    for name in het.ORDER:
        if f0 <= modes[name]['f_3db']:
            return name
    return het.ORDER[-1]


def het_clean(sc, fn):
    """R1 clean transfer: raw ratio, corrected err, signal gain vs OFF."""
    zc = np.exp(1j * sc['ph'])
    t = sc['t']
    a_true = lockin_amp(sc['v'], t, sc['f0'], sc['Wm'])
    a_off = lockin_amp(het_vdisc(zc), t, sc['f0'], sc['Wm'])
    y, _, _, _ = het_run_pll(zc, fn, 1e-10)
    a_on = lockin_amp(het_vdisc(y), t, sc['f0'], sc['Wm'])
    H = het_hl_mag(sc['f0'], fn)
    return dict(ratio=a_on / a_true, err=100 * (a_on / H / a_true - 1),
                g_sig=20 * math.log10(max(a_on, TINY) / max(a_off, TINY)), H=H)


def het_nred(sc, fn, cnr, nseed, seed0):
    """R2 noise-floor drop vs OFF in the scene quiet window (median)."""
    s2 = 10 ** (-cnr / 10)
    p = sc['p']
    vals = []
    for s in range(nseed):
        rng = np.random.default_rng(seed0 + s)
        z = np.exp(1j * sc['ph']) + complex_bandlimited_noise(
            sc['N'], HFS, HBF, s2, rng)
        a_off = het_asd(het_vdisc(z), sc['Wq'], p['L'], p['band'])
        y, _, _, _ = het_run_pll(z, fn, s2)
        vals.append(20 * math.log10(
            a_off / het_asd(het_vdisc(y), sc['Wq'], p['L'], p['band'])))
    return stats(vals)[0]


H1_VR = (0.1, 1.0, 3.0)
H1_F = (50e3, 500e3, 5e6)
H1_CNR = (0, 4, 12)
H1_NSEED = 3


def H1():
    header('H1  外差量程-速度地图: v_range={0.1,1,3}m/s x f={50k,500k,5M}Hz x '
           'CNR={0,4,12}dB\n    (外差档位同时决定测量带宽 f_3dB=2.058*fn 与'
           '动态; 5MHz > f_3dB 时只能 FAST+频响校正; R1-R4 规则, gate=always)')
    out(f"  硬边界: v_if = {het.v_if_limit():.2f} m/s (IF 频偏窗), v_alias = "
        f"{het.v_alias_limit():.2f} m/s (fs 混叠), fn <= fs/50 = "
        f"{HFS/50/1e3:.0f}k (离散稳定)")
    scs = {f0: het_scene(f0) for f0 in H1_F}
    ok_cov, ok_5m, ok_gain = True, True, True
    res = {}
    out(f"\n    {'v_range':>8} {'f':>6} {'mode':>7} {'fn':>8} {'f_3dB':>8} "
        f"{'|H_L|':>7} {'raw比':>7} {'corr err':>9} {'fn<=fs/50':>9} |"
        + ''.join(f"{'gain@' + str(c) + 'dB':>10}" for c in H1_CNR))
    for ivr, vr in enumerate(H1_VR):
        modes = het.mode_params(vr)
        for i_f, f0 in enumerate(H1_F):
            mode = het_pick_mode(f0, modes)
            fn = modes[mode]['fn']
            sc = scs[f0]
            c = het_clean(sc, fn)
            gains = []
            for cnr in H1_CNR:
                seed0 = 260000 + ivr * 10000 + i_f * 1000 + cnr * 10
                nr = het_nred(sc, fn, cnr, H1_NSEED, seed0)
                gains.append(c['g_sig'] + nr)
            covered = f0 <= modes[mode]['f_3db']
            okd = het.fn_discrete_ok(fn, HFS)
            out(f"    {vr:6.1f}m {f0/1e3:5.0f}k {mode:>7} {fn/1e3:6.1f}k "
                f"{modes[mode]['f_3db']/1e3:6.1f}k {c['H']:7.4f} "
                f"{c['ratio']:7.4f} {c['err']:+8.2f}% {'ok' if okd else 'FAIL':>9} |"
                + ''.join(f"{g:+9.2f} " for g in gains))
            res[(vr, f0)] = dict(mode=mode, fn=fn, clean=c, gains=gains)
            key(f"H1_err_vr{vr:g}_f{f0/1e3:.0f}k", c['err'])
            key(f"H1_gain0_vr{vr:g}_f{f0/1e3:.0f}k", gains[0])
            if covered:
                ok_cov &= abs(c['err']) < 10.0
            elif c['H'] >= 0.1:
                ok_5m &= abs(c['err']) < 15.0
        out('')
    g50 = res[(1.0, 50e3)]['gains'][0]
    ok_gain = g50 > 10.0
    out('  解读: 档内 (f<=f_3dB) 频响校正后幅值刻度保持; 5 MHz 超出所有档的 '
        'f_3dB, 只有 FAST 的 |H_L| 足够校正;\n  增益本质是 FM 门限扩展, '
        '高 CNR 时归零 (校正不改变谱线 SNR).')
    check('H1a', '档内格点 (f <= f_3dB): 频响校正后 |err| < 10%', ok_cov,
          'see table')
    check('H1b', '5MHz 格点 |H_L|>=0.1 者: 校正后 |err| < 15% (FAST+校正可用)',
          ok_5m, 'see table')
    check('H1c', 'v_range=1, f=50kHz (SLOW) CNR=0dB 线SNR增益 > +10 dB '
          '(门限扩展)', ok_gain, f'{g50:+.1f} dB')
    return res


def H2():
    header('H2  超出 f_3dB: 5MHz 三档 raw vs corrected (复现 '
           'validate_heterodyne C24/C26 -- 外差档位=测量带宽, 无残差窗兜底)')
    modes = het.mode_params(1.0)
    sc = het_scene(5e6)
    out(f"\n    {'mode':>7} {'fn':>8} {'f_3dB':>8} {'|H_L(5M)|':>10} "
        f"{'raw幅值比':>10} {'corr err':>9}")
    rows = {}
    for name in het.ORDER:
        fn = modes[name]['fn']
        c = het_clean(sc, fn)
        rows[name] = c
        out(f"    {name:>7} {fn/1e3:6.1f}k {modes[name]['f_3db']/1e3:6.1f}k "
            f"{c['H']:10.4f} {c['ratio']:10.4f} {c['err']:+8.2f}%")
        key(f'H2_ratio_{name}', c['ratio'])
    check('H2a', 'SLOW@5MHz 未校正幅值比 < 0.05 (C26 复现: 档位=测量带宽)',
          rows['SLOW']['ratio'] < 0.05, f"{rows['SLOW']['ratio']:.4f}")
    check('H2b', 'FAST@5MHz: 0.1 < raw比 < 0.5 且校正后 |err| < 10% '
          '(C24 复现)', 0.1 < rows['FAST']['ratio'] < 0.5
          and abs(rows['FAST']['err']) < 10.0,
          f"比 {rows['FAST']['ratio']:.3f}, 校正后 {rows['FAST']['err']:+.2f}%")
    return rows


def h3_one(fn, f_v, vamp, seed):
    """One bathtub point: corrected amp err + slips at (f_v, vamp)."""
    t_pre = 0.2e-3
    T = t_pre + max(8 / f_v, 60e-6)
    N = int(T * HFS)
    t = np.arange(N) / HFS
    td = np.maximum(t - t_pre, 0.0)
    on = (t >= t_pre).astype(float)
    sel = t > t_pre + max(3 / f_v, 25e-6)
    x = on * vamp / (2 * np.pi * f_v) * (1 - np.cos(2 * np.pi * f_v * td))
    v_true = on * vamp * np.sin(2 * np.pi * f_v * td)
    ph = 4 * np.pi / HLAM * x
    s2 = 10 ** (-30 / 10)
    rng = np.random.default_rng(seed)
    z = np.exp(1j * ph) + complex_bandlimited_noise(N, HFS, HBF, s2, rng)
    a_true = ls_amp(v_true, t, f_v, sel)
    y, _, _, dg = het_run_pll(z, fn, s2)
    err = 100 * (ls_amp(het_vdisc(y), t, f_v, sel)
                 / het_hl_mag(f_v, fn) / a_true - 1)
    return err, dg['near_pi_events']


def H3():
    header('H3  浴缸谷底夹逼: 每档在 f=fn 处测 0.5*v_pi (应过) 与 2*v_pi '
           '(应败)  (v_pi = pi*lambda*fn/sqrt2 卷绕线谷值, CNR=30dB)')
    modes = het.mode_params(1.0)
    out(f"\n    {'mode':>7} {'fn':>8} {'v_pi':>10} | {'0.5*v_pi err/slips':>19}"
        f" | {'2*v_pi err/slips':>17}")
    ok = True
    valleys = []
    for im, name in enumerate(het.ORDER):
        fn = modes[name]['fn']
        v_pi = het.v_pll_limit(fn, fn)
        valleys.append(v_pi)
        e1, s1_ = h3_one(fn, fn, 0.5 * v_pi, 265000 + im * 100 + 1)
        e2, s2_ = h3_one(fn, fn, 2.0 * v_pi, 265000 + im * 100 + 2)
        good1 = s1_ == 0 and abs(e1) < 25
        bad2 = s2_ > 0 or abs(e2) > 25
        ok &= good1 and bad2
        out(f"    {name:>7} {fn/1e3:6.1f}k {v_pi*1e3:8.2f}mm | "
            f"{e1:+9.1f}%/{s1_:<4d}{'pass' if good1 else 'FAIL':>5} | "
            f"{e2:+8.1f}%/{s2_:<4d}{'fail(期望)' if bad2 else 'PASS?!':>9}")
        key(f'H3_e1_{name}', e1)
    check('H3a', '三档: 0.5*v_pi 通过 (|err|<25%, 0 slips) 且 2*v_pi 失败 '
          '-- 实测边界夹在卷绕线 2 倍以内', ok, 'see table')
    check('H3b', '谷值随档单调上升 (SLOW < MEDIUM < FAST)',
          valleys[0] < valleys[1] < valleys[2],
          ' / '.join(f'{v*1e3:.2f}mm' for v in valleys))
    return valleys


H4_CNR = (0, 2, 4, 6, 8)
H4_NSEED = 4


def H4():
    modes = het.mode_params(1.0)
    fn = modes['FAST']['fn']
    header(f'H4  弱回光 PSV 类: FAST@5MHz (fn={fn/1e3:.0f}k), CNR 0..8dB 扫描 '
           f'({H4_NSEED} seeds) -- 未校正底噪下降 (复现 PSV-500 弱回光实测) '
           '与线 SNR 增益 (诚实面)')
    sc = het_scene(5e6)
    c = het_clean(sc, fn)
    out(f"\n    {'CNR':>5} | {'底噪下降 dB (raw)':>17} {'线SNR增益 dB':>13}")
    nreds = {}
    for cnr in H4_CNR:
        nr = het_nred(sc, fn, cnr, H4_NSEED, 270000 + cnr * 100)
        nreds[cnr] = nr
        out(f"    {cnr:3d}dB | {nr:17.1f} {c['g_sig'] + nr:13.1f}")
        key(f'H4_nred_c{cnr}', nr)
    out('\n  解读: 底噪下降与信号衰减同源于 |H_L| -- 校正恢复刻度但不改变谱线 '
        'SNR; 0..8dB 全程在 FM 门限过渡区内,\n  下降量 ~15.2..15.8 dB 近乎平坦 '
        '(非单调, 逐点差在 seed 统计噪声量级), 仅端点呈弱收缩趋势;\n  门限以上 '
        '(CNR>=12dB) OFF/ON 同为相位噪声, 下降才真正归零 -- 见 H1 表 5MHz 行的 '
        'gain@12dB 列 (~0 dB).')
    check('H4a', 'CNR<=4dB: 未校正底噪下降 > +10 dB (C23 复现)',
          all(nreds[c_] > 10.0 for c_ in (0, 2, 4)),
          ', '.join(f'{c_}dB:{nreds[c_]:+.1f}' for c_ in (0, 2, 4)))
    check('H4b', '端点弱收缩: nred(0dB) > nred(8dB) (0..8dB 区间实测近乎平坦, '
          '不断言逐点单调)',
          nreds[0] > nreds[8], f'{nreds[0]:+.1f} vs {nreds[8]:+.1f} dB')
    return nreds


# ============================================================ X1 cross-compare
def X1(s1_cells, s1_cache):
    header('X1  同一运动 (100 kHz, 20 mm/s): 零差 SLOW vs 外差 SLOW -- '
           '诚实的苹果/橘子对照 (非产品排名)')
    hc = s1_cells[(100e3, 0.02)]
    g_h = (20 * math.log10(max(1 + hc['err'] / 100, 1e-12))
           + s1_cache[(hc['band'], 3, hc['lpf'])])
    modes = het.mode_params(1.0)
    mode = het_pick_mode(100e3, modes)
    fn = modes[mode]['fn']
    sc = het_scene(100e3)
    c = het_clean(sc, fn)
    nr = het_nred(sc, fn, 3, 3, 280000)
    g_t = c['g_sig'] + nr
    out(f"\n    {'':<26} {'零差 (homodyne)':>22} {'外差 (heterodyne)':>22}")
    rows = (
        ('波长 / 采样率', f'1550nm / {FS/1e6:.0f}MS/s',
         f'{HLAM*1e9:.1f}nm / {HFS/1e6:.0f}MS/s'),
        ('前端 (噪声 ENBW)', f"{hc['B_fe']/1e6:.0f} MHz"
         + ('+LPF' if hc['lpf'] else ''), f'{HBF/1e6:.0f} MHz'),
        ('档 / fn', f"{hc['band']} / {BANDS[hc['band']]['fn']/1e3:.0f}k",
         f'{mode} / {fn/1e3:.1f}k'),
        ('B_loop', f"{b_loop(BANDS[hc['band']]['fn'])/1e6:.2f} MHz",
         f"{het.b_loop(fn)/1e3:.0f} kHz"),
        ('测量带宽', f'{B_WIN/1e6:.0f} MHz 公共残差窗',
         f"f_3dB = {modes[mode]['f_3db']/1e3:.0f} kHz (档定)"),
        ('clean ampErr', f"{hc['err']:+.2f}%",
         f"{c['err']:+.2f}% (频响校正后)"),
        ('SNR gain @CNR=3dB', f'{g_h:+.1f} dB', f'{g_t:+.1f} dB'),
    )
    for name, a, b in rows:
        out(f'    {name:<26} {a:>22} {b:>22}')
    out('    (零差数字与 validate_tracking V1 的 SLOW +38dB 同一物理, 评估带'
        '不同: 此处为 10..100kHz 结构带的静态载波底噪下降)')
    key('X1_gain_homodyne', g_h)
    key('X1_gain_heterodyne', g_t)
    out("""
  苹果/橘子注记 (必须读):
    - 波长不同: 同一 20 mm/s 在 1550 nm 是 25.8 kHz 多普勒, 在 632.8 nm 是
      63.2 kHz -- 相位摆幅差 2.45x, 两环工作点并不相同.
    - 前端不同: 零差 40 MHz 噪声带 (fD=25.8kHz << 20MHz, 物理规则不触发 86M
      前端) vs 外差 19 MHz, "CNR=3dB" 的
      噪声 PSD 完全不同; 增益各自相对自己的 OFF 参考, 不能跨列相减.
    - 架构不同: 零差增益含残差窗点击清除 (B_loop < B_win 条件), 换档不改
      测量带宽; 外差增益是纯 NCO 的 FM 门限扩展, 换档同时改变测量带宽.
    - 结论只有一个是公平的: 两种架构在各自设计域内都给出 >+10dB 量级的
      弱光门限扩展, 且幅值刻度保持 -- 选型依据见 OPTIMIZATION_GUIDE 决策树.""")
    check('X1a', '两架构在该工况各自 SNR gain > +10 dB (各自参考系内)',
          g_h > 10.0 and g_t > 10.0, f'homo {g_h:+.1f}, het {g_t:+.1f} dB')


# ==================================================================== main
def main():
    t0 = time.time()
    out('真实场景仿真套件: 零差(S1-S5) + 外差(H1-H4) + 交叉对照(X1)')
    out(f'homodyne: lambda=1550nm fs={FS/1e6:.0f}MS/s 三档 fn=110k/530k/1.6M '
        f'zeta=1.2 公共窗 {B_WIN/1e6:.0f}MHz | heterodyne: lambda='
        f'{HLAM*1e9:.1f}nm fs={HFS/1e6:.0f}MS/s zeta={HZ} 档位=f(v_range)')
    out('规则: R1-R4 公平比较 (validate_tracking); 零差 fD_peak=2*v/lambda > '
        '20MHz 的高速格点用 B_FE=86MHz+LPF 物理前端 (validate_app A6 v2 模型)')
    s1_cells, s1_cache = S1()
    S2()
    S3()
    S4()
    S5()
    H1()
    H2()
    H3()
    H4()
    X1(s1_cells, s1_cache)

    header('ASSERTION SUMMARY')
    allok = True
    for cid, label, ok, detail in CHECKS:
        allok &= ok
        out(f"  [{'PASS' if ok else 'FAIL'}] {cid}  {label}  ({detail})")
    out('\n' + ('ALL CHECKS PASSED' if allok else 'SOME CHECKS FAILED'))
    out(f'[elapsed {time.time()-t0:.1f} s]')

    out('\n' + '-' * 92)
    out('KEY metrics (machine readable, for the Python<->MATLAB comparison):')
    for name, value in KEYS:
        out(f'KEY,{name},{value:.6g}')

    (Path(__file__).resolve().parent / 'results_realistic_scenarios.txt'
     ).write_text('\n'.join(LINES) + '\n', encoding='utf-8')
    return 0 if allok else 1


if __name__ == '__main__':
    raise SystemExit(main())
