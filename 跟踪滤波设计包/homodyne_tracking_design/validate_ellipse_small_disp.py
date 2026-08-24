#!/usr/bin/env python3
"""Homodyne IQ small-displacement ellipse-correction validation (B0-B4).

Hardware is fixed; only the software chain may change. This script simulates
the analog IQ ellipse (gain imbalance eps + quadrature error delta, both
slowly drifting), a slowly drifting interferometric working point, adjustable
CNR complex-Gaussian noise, and sinusoidal true displacement, then compares:

  B0  OFF            angle(u + j*v) directly, no correction
  B1  sliding demean subtract a sliding-window mean from u,v (user's current
                     method; window swept, the best window is used as baseline)
  B2  static Heydemann   one fit on the first T_CAL seconds, applied globally
  B3  segmented-arc Heydemann  per-segment amplitude-gated fit with freeze on
                     invalid arc (document M1), parameters interpolated in time
  B4  B3 + SLOW-gear tracking filter (pll_carrier_regen, fn=110 kHz, zeta=2.65)

Metrics (per case, evaluated on t in [0.1, 1.9) s, decimated to 25 kS/s):
  * amplitude error [%]  lock-in at f vs true A
  * displacement RMS error [nm] vs the true optical-phase displacement
  * spectral line SNR at f [dB]: band power |f-f0|<=5 Hz over the mean floor
    at 8..48 Hz offsets (same estimator for every method)

Assertion (spec): at A=100 nm, f=100 Hz the best corrected method must beat
best-window B1 by >10 dB line SNR OR reduce RMS error by >3x.

Nominal front end: lambda=1550 nm, fs=250 MS/s. The record is simulated at
the decimated rate 2.5 MS/s with the noise power scaled as an ideal /100
decimation (CNR_dec = CNR_frontend + 20 dB), which is equivalent for every
signal here (all displacement signals <= 1 kHz).

Run:  python3 validate_ellipse_small_disp.py [--cnr-db 20] [--out FILE]
"""
import argparse
import math
import os
import sys
import time

import numpy as np

from core import pll_carrier_regen, welch_psd
from ellipse_correction import (heydemann_fit, heydemann_apply,
                                segmented_heydemann, interp_par_track,
                                apply_par_track)

LAMBDA = 1550e-9
FS_FULL = 250e6                  # nominal ADC rate
DECIM = 100
FS = FS_FULL / DECIM             # 2.5 MS/s simulation rate (long records)
T_REC = 2.0                      # record length (s)
DEC2 = 100                       # metric decimation -> 25 kS/s
FS2 = FS / DEC2
T_TRIM = 0.1                     # settle/edge trim on both ends (s)
WELCH_L = 16384
SNR_SIG_HZ = 2.0                 # line band: |f - f0| <= 2 Hz
SNR_FLOOR_HZ = (3.0, 48.0)       # floor band: 3..48 Hz offsets (both sides)

# --- true ellipse + drift scenario (all software-uncorrectable in hardware)
EPS_T0, EPS_T1 = -0.08, -0.12        # gain imbalance gQ/gI-1: -8% -> -12%
DEL_T0, DEL_T1 = 3.0, 6.0            # quadrature error (deg): 3 -> 6
P_OFF0, P_DRIFT = 0.06, 0.01         # I offset + slow drift
Q_OFF = -0.05                        # Q offset
FRINGE_RATE = 1.5                    # working-point drift (fringes/s)
PSI_WANDER = 0.8                     # extra smooth phase wander (rad rms)
R_SWING = 0.04                       # slow return-amplitude wander (+-4%)

# --- method parameters
B1_WINDOWS = (0.05, 0.1, 0.2, 0.5, 1.0)   # sliding-demean windows (s)
T_CAL_B2 = 0.4                            # static calibration segment (s)
SEG_B3 = 0.25                             # B3 segment length (s)
GATE_B3 = 0.05                            # B3 amplitude gate (+-5% radius)
FN_SLOW, ZETA_SLOW = 110e3, 2.65          # SLOW gear (design_params.py)

CASES = [(A, f0) for A in (10e-9, 100e-9, 500e-9, 1e-6)
         for f0 in (100.0, 1000.0)]
ASSERT_CASE = (100e-9, 100.0)
METHODS = ('B0', 'B1', 'B2', 'B3', 'B4')


# ------------------------------------------------------------------ helpers
def smooth_noise(N, fs, fc, rng):
    """Unit-rms Gaussian noise low-passed (brick wall) at fc."""
    W = np.fft.rfft(rng.standard_normal(N))
    fr = np.fft.rfftfreq(N, 1.0 / fs)
    W[fr > fc] = 0.0
    s = np.fft.irfft(W, N)
    return s / max(s.std(), 1e-300)


def movmean(x, n):
    """Centered moving average with shrinking edge windows, O(N)."""
    n = int(n)
    h = max(1, n // 2)
    c = np.concatenate(([0.0], np.cumsum(x)))
    i = np.arange(x.size)
    lo = np.clip(i - h, 0, None)
    hi = np.clip(i + h + 1, None, x.size)
    return (c[hi] - c[lo]) / (hi - lo)


def phase_cum(z):
    """Unwrapped phase from complex samples via increment accumulation."""
    d = np.angle(z[1:] * np.conj(z[:-1]))
    return np.concatenate(([0.0], np.cumsum(d)))


def to_disp(phase):
    return phase * (LAMBDA / (4 * math.pi))


def decimate_fft(x, dec=DEC2):
    """Brick-wall low-pass at 0.4*fs/dec then subsample by dec."""
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(x.size, 1.0)
    X[fr > 0.4 / dec] = 0.0
    return np.fft.irfft(X, x.size)[::dec]


def line_snr(xd, fs, f0):
    """Line SNR at f0 from a single Hann periodogram of the whole segment.

    Full-record resolution (df = fs/N ~ 0.56 Hz) so that drift-ripple
    sidebands only a few Hz from the line land in the FLOOR band instead of
    being absorbed into the line, while the Hann main lobe (+-2 bins) stays
    inside the +-SNR_SIG_HZ signal band.
    """
    n = xd.size
    win = 0.5 - 0.5 * np.cos(2 * math.pi * np.arange(n) / (n - 1))
    P = np.abs(np.fft.rfft(xd * win)) ** 2
    fx = np.fft.rfftfreq(n, 1.0 / fs)
    off = np.abs(fx - f0)
    sig = off <= SNR_SIG_HZ
    flo = (off >= SNR_FLOOR_HZ[0]) & (off <= SNR_FLOOR_HZ[1])
    p_sig = float(P[sig].sum())
    p_flo = float(P[flo].sum()) * sig.sum() / max(flo.sum(), 1)
    return 10 * math.log10(max(p_sig, 1e-300) / max(p_flo, 1e-300))


# ----------------------------------------------------------------- scenario
def make_scenario(A, f0, cnr_frontend_db, rng, T=T_REC):
    N = int(round(T * FS))
    t = np.arange(N) / FS
    x_true = A * np.sin(2 * math.pi * f0 * t)
    psi = (2 * math.pi * FRINGE_RATE * t
           + PSI_WANDER * smooth_noise(N, FS, 1.0, rng))
    eps_t = EPS_T0 + (EPS_T1 - EPS_T0) * t / T
    del_t = np.deg2rad(DEL_T0 + (DEL_T1 - DEL_T0) * t / T)
    R = 1.0 + R_SWING * smooth_noise(N, FS, 2.0, rng)
    p_t = P_OFF0 + P_DRIFT * t / T

    phi = (4 * math.pi / LAMBDA) * x_true + psi
    gI = 1.0
    gQ = gI * (1.0 + eps_t)
    cI = gI * R * np.cos(phi)
    cQ = gQ * R * np.sin(phi + del_t)
    Pc = float(np.mean(cI ** 2 + cQ ** 2))          # carrier power
    cnr_dec_db = cnr_frontend_db + 10 * math.log10(DECIM)
    s2 = Pc / 10 ** (cnr_dec_db / 10)               # complex noise power
    u = cI + p_t + math.sqrt(s2 / 2) * rng.standard_normal(N)
    v = cQ + Q_OFF + math.sqrt(s2 / 2) * rng.standard_normal(N)
    x_ref = x_true + to_disp(psi)                   # true optical-phase displ.
    return dict(t=t, u=u, v=v, x_ref=x_ref, s2=s2, Pc=Pc,
                eps_t=eps_t, del_t=del_t, cnr_dec_db=cnr_dec_db)


# ------------------------------------------------------------------ metrics
class CaseEval:
    """Common decimated reference + metric estimator for one scenario."""

    def __init__(self, sc, A, f0):
        self.A, self.f0 = A, f0
        self.x_ref2 = decimate_fft(sc['x_ref'])
        n2 = self.x_ref2.size
        self.t2 = np.arange(n2) / FS2
        self.sel = (self.t2 >= T_TRIM) & (self.t2 < T_REC - T_TRIM)
        self.n_dt = int(round(0.25 * FS2))   # detrend window: f0*0.25 integer

    def __call__(self, x_est):
        x2 = decimate_fft(x_est)
        xs = x2[self.sel]
        e = xs - self.x_ref2[self.sel]
        e -= e.mean()
        rms_nm = float(np.sqrt(np.mean(e ** 2))) * 1e9

        xd = xs - movmean(xs, self.n_dt)     # kill drift (gain=1 at f0 exactly)
        ts = self.t2[self.sel]
        amp = 2 * abs(np.mean(xd * np.exp(-1j * 2 * math.pi * self.f0 * ts)))
        amp_err = 100.0 * (amp / self.A - 1.0)
        snr = line_snr(xd, FS2, self.f0)
        return dict(amp=amp_err, rms=rms_nm, snr=snr)


# ------------------------------------------------------------------ methods
def run_methods(sc, A, f0, include_b4=True):
    u, v, t = sc['u'], sc['v'], sc['t']
    ev = CaseEval(sc, A, f0)
    out = {}

    # B0: raw angle(z)
    out['B0'] = ev(to_disp(phase_cum(u + 1j * v)))

    # B1: sliding demean, window swept
    sweep = []
    for w in B1_WINDOWS:
        n = int(round(w * FS))
        zc = (u - movmean(u, n)) + 1j * (v - movmean(v, n))
        m = ev(to_disp(phase_cum(zc)))
        m['win'] = w
        sweep.append(m)
    out['B1_sweep'] = sweep
    out['B1'] = max(sweep, key=lambda m: m['snr'])          # best window
    out['B1_min_rms'] = min(m['rms'] for m in sweep)

    # B2: static Heydemann from the first T_CAL_B2 seconds
    ncal = int(round(T_CAL_B2 * FS))
    step = max(1, ncal // 20000)
    par2, res2 = heydemann_fit(u[:ncal:step], v[:ncal:step])
    _, _, z2 = heydemann_apply(u, v, par2)
    out['B2'] = ev(to_disp(phase_cum(z2)))
    out['B2_par'], out['B2_res'] = par2, res2
    del z2

    # B3: segmented-arc Heydemann (amplitude-gated, freeze on short arc)
    t_c, pars, oks, arcs = segmented_heydemann(u, v, FS, seg_len=SEG_B3,
                                               gate_tol=GATE_B3)
    trk = interp_par_track(t, t_c, pars)
    z3 = apply_par_track(u, v, trk)
    del trk
    out['B3'] = ev(to_disp(phase_cum(z3)))
    out['B3_track'] = (t_c, pars, oks, arcs)

    # B4: B3-corrected z through the SLOW-gear carrier loop (pure NCO phase)
    if include_b4:
        _, phi_nco, _, _ = pll_carrier_regen(z3, FS, FN_SLOW, sc['s2'],
                                             zeta=ZETA_SLOW, gate='always')
        out['B4'] = ev(to_disp(np.unwrap(phi_nco)))
    del z3
    return out


# --------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--cnr-db', type=float, default=20.0,
                    help='front-end CNR at 250 MS/s (dB); +20 dB after /100')
    ap.add_argument('--out', default='/opt/cursor/artifacts/results_ellipse.txt')
    args = ap.parse_args(argv)
    t_start = time.time()

    lines = []
    w = lines.append
    w('=' * 78)
    w('零差 IQ 小位移椭圆校正验证  (B0-B4, 软件方案对比, 硬件不可改)')
    w('=' * 78)
    w(f'lambda = {LAMBDA*1e9:.0f} nm | 名义 fs = {FS_FULL/1e6:.0f} MS/s, '
      f'仿真在 /{DECIM} 降采样 = {FS/1e6:.1f} MS/s, 记录 {T_REC:.1f} s')
    w(f'椭圆真值(慢漂): eps {EPS_T0*100:+.0f}% → {EPS_T1*100:+.0f}%, '
      f'delta {DEL_T0:.0f}° → {DEL_T1:.0f}°, 偏置 p={P_OFF0}(+{P_DRIFT}漂移) '
      f'q={Q_OFF}, 回光幅度 ±{R_SWING*100:.0f}% 慢漂')
    w(f'工作点漂移: {FRINGE_RATE:.1f} 条纹/s 线性 + {PSI_WANDER:.1f} rad 平滑游走')
    w(f'噪声: 复高斯, 前端 CNR = {args.cnr_db:.0f} dB @250 MS/s '
      f'(降采样后 {args.cnr_db+20:.0f} dB)')
    w(f'指标评估: t∈[{T_TRIM},{T_REC-T_TRIM}) s, 降到 {FS2/1e3:.0f} kS/s; '
      f'谱线SNR = |f-f0|≤{SNR_SIG_HZ:.0f} Hz 带功率 / '
      f'{SNR_FLOOR_HZ[0]:.0f}–{SNR_FLOOR_HZ[1]:.0f} Hz 偏移底板 (全段Hann周期图)')
    w('')
    w('方法: B0 OFF=angle(z) | B1 滑动去均值(窗扫描, 取最优窗) | '
      'B2 静态Heydemann(前0.4 s标定)')
    w(f'      B3 分段弧Heydemann(段长{SEG_B3}s, 幅度门±{GATE_B3*100:.0f}%, '
      f'弧<π/2冻结) | B4 = B3 + SLOW跟踪滤波(fn=110 kHz, ζ=2.65)')

    results = {}
    for i, (A, f0) in enumerate(CASES):
        rng = np.random.default_rng(1000 + i)
        sc = make_scenario(A, f0, args.cnr_db, rng)
        results[(A, f0)] = run_methods(sc, A, f0)
        if (A, f0) == ASSERT_CASE:
            assert_sc = sc
        print(f'  case A={A*1e9:g} nm f={f0:g} Hz done '
              f'({time.time()-t_start:.0f} s)', file=sys.stderr)

    # ------------------------------------------------- per-case result table
    w('')
    w('--- 结果表 (幅值误差% | 位移RMS误差 nm | 谱线SNR@f dB) ---')
    hdr = f'{"A":>7} {"f":>7} |' + ''.join(f'{m:>26}' for m in METHODS)
    w(hdr)
    w(f'{"":>7} {"":>7} |' + f'{"amp%   rms_nm   snr_dB":>26}' * len(METHODS))
    for (A, f0) in CASES:
        r = results[(A, f0)]
        cells = ''
        for m in METHODS:
            d = r[m]
            cells += (f'{min(max(d["amp"],-999.9),999.9):>9.2f} '
                      f'{min(d["rms"],99999.9):>8.1f} {d["snr"]:>7.1f}')
        w(f'{A*1e9:>5.0f}nm {f0:>5.0f}Hz |{cells}')

    # ------------------------------------------------- B1 window sweep detail
    rA = results[ASSERT_CASE]
    w('')
    w(f'--- B1 窗口扫描 @ 断言场景 A={ASSERT_CASE[0]*1e9:.0f} nm, '
      f'f={ASSERT_CASE[1]:.0f} Hz ---')
    w(f'{"窗口/s":>8} {"幅值误差%":>12} {"RMS/nm":>10} {"SNR/dB":>8}')
    for m in rA['B1_sweep']:
        w(f'{m["win"]:>8.2f} {min(max(m["amp"],-999.9),999.9):>12.2f} '
          f'{min(m["rms"],99999.9):>10.1f} {m["snr"]:>8.1f}')
    w(f'  → B1 最优窗 = {rA["B1"]["win"]:.2f} s (按SNR); '
      f'RMS 取各窗最小值 {rA["B1_min_rms"]:.1f} nm 作保守基线')

    # ------------------------------------------------- B3 parameter tracking
    t_c, pars, oks, arcs = rA['B3_track']
    w('')
    w('--- B3 分段参数跟踪 @ 断言场景 (真值 ε/δ 随时间线性漂移) ---')
    w(f'{"t/s":>6} {"拟合":>4} {"弧/rad":>7} {"ε̂%":>8} {"ε真%":>7} '
      f'{"δ̂°":>7} {"δ真°":>6}')
    for k in range(len(t_c)):
        eps_hat = 100 * (pars[k]['B'] / pars[k]['A'] - 1)
        del_hat = math.degrees(pars[k]['delta'])
        frac = t_c[k] / T_REC
        eps_true = 100 * (EPS_T0 + (EPS_T1 - EPS_T0) * frac)
        del_true = DEL_T0 + (DEL_T1 - DEL_T0) * frac
        w(f'{t_c[k]:>6.2f} {"OK" if oks[k] else "冻结":>4} {arcs[k]:>7.2f} '
          f'{eps_hat:>8.2f} {eps_true:>7.2f} {del_hat:>7.2f} {del_true:>6.2f}')
    p2 = rA['B2_par']
    w(f'  B2 静态参数(前{T_CAL_B2}s): ε̂={100*(p2["B"]/p2["A"]-1):+.2f}%, '
      f'δ̂={math.degrees(p2["delta"]):.2f}° — 记录末端真值 '
      f'ε={EPS_T1*100:+.1f}%, δ={DEL_T1:.1f}° (静态参数已过时)')

    # ------------------------------------------------- CNR sensitivity sweep
    w('')
    w('--- CNR 敏感性 @ 断言场景 (B1 最优窗 vs B3) ---')
    w(f'{"前端CNR/dB":>10} {"B1 rms/nm":>10} {"B1 snr/dB":>10} '
      f'{"B3 rms/nm":>10} {"B3 snr/dB":>10}')
    for j, cnr in enumerate((10.0, 20.0, 30.0)):
        rng = np.random.default_rng(2000 + j)
        sc = make_scenario(*ASSERT_CASE, cnr, rng)
        r = run_methods(sc, *ASSERT_CASE, include_b4=False)
        w(f'{cnr:>10.0f} {r["B1_min_rms"]:>10.1f} {r["B1"]["snr"]:>10.1f} '
          f'{r["B3"]["rms"]:>10.1f} {r["B3"]["snr"]:>10.1f}')

    # -------------------------------------------------------------- assertion
    w('')
    w('=' * 78)
    w('断言 (规格): A=100 nm @ 100 Hz, 最优校正方法 vs B1(最优窗):')
    w('           谱线SNR改善 > 10 dB  或  RMS误差降低 > 3x')
    cands = {m: rA[m] for m in ('B2', 'B3', 'B4') if m in rA}
    best_snr_m = max(cands, key=lambda m: cands[m]['snr'])
    best_rms_m = min(cands, key=lambda m: cands[m]['rms'])
    d_snr = cands[best_snr_m]['snr'] - rA['B1']['snr']
    r_rms = rA['B1_min_rms'] / max(cands[best_rms_m]['rms'], 1e-12)
    w(f'  SNR:  {best_snr_m} {cands[best_snr_m]["snr"]:.1f} dB vs '
      f'B1 {rA["B1"]["snr"]:.1f} dB → 改善 {d_snr:+.1f} dB '
      f'({"满足" if d_snr > 10 else "不满足"} >10 dB)')
    w(f'  RMS:  {best_rms_m} {cands[best_rms_m]["rms"]:.2f} nm vs '
      f'B1(各窗最小) {rA["B1_min_rms"]:.2f} nm → 降低 {r_rms:.1f}x '
      f'({"满足" if r_rms > 3 else "不满足"} >3x)')
    ok = (d_snr > 10.0) or (r_rms > 3.0)
    w('')
    w(f'  ====>  {"PASS" if ok else "FAIL"}  <====')
    w('=' * 78)

    # ------------------------------------------------------- recommendation
    w('')
    w('--- 推荐最优可实现软件方案 (硬件不可改) ---')
    w('推荐: B3 分段弧 Heydemann 校正, 参数:')
    w(f'  * 标定段长 {SEG_B3} s (2.5 MS/s 下 {int(SEG_B3*FS):d} 样本, '
      f'均匀抽取 ≤8000 点入拟合)')
    w(f'  * 幅度门: 以上一段中心为参考, 保留半径偏离中位数 ≤±{GATE_B3*100:.0f}% '
      f'的点 (不足时放宽到±{2*GATE_B3*100:.0f}%), 防止变幅环带污染拟合')
    w('  * 有效性: 98%稳健覆盖弧 ≥ π/2 才更新参数, 否则冻结上一组 (M1/M4 规则)')
    w('  * 应用: p,q,A,B,δ 在段中心间线性内插逐样本应用 '
      '(实时实现= 用上一段参数, 滞后一段长)')
    w(f'  * 前置条件: 工作点漂移覆盖弧 (本场景 {FRINGE_RATE:.1f} 条纹/s 自然漂移'
      '已足够); 若漂移不足, 退回 B2 静态标定并定期(激光微调频/温漂窗口)重标')
    w('  * B4 (B3+SLOW跟踪滤波) 与 B3 同级: 跟踪滤波不能修椭圆, 只在掉光/'
      '门控上有价值; 椭圆校正必须放在跟踪滤波之前 (|z|² 2φ纹波会污染门控)')
    w('  * 不推荐: B0 直接鉴相 (偏置→大幅值误差); B1 滑动去均值只能去偏置, '
      '修不了 ε/δ, 且小位移+慢漂下窗内均值≠椭圆中心')
    w('')
    w(f'总耗时 {time.time()-t_start:.0f} s')

    text = '\n'.join(lines)
    print(text)
    for path in (args.out,
                 os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'results_ellipse.txt')):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(text + '\n')
        except OSError as exc:
            print(f'warn: cannot write {path}: {exc}', file=sys.stderr)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
