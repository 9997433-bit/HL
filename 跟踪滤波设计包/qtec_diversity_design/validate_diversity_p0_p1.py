#!/usr/bin/env python3
"""QTec diversity P0+P1 validation with PASS/FAIL assertions.

P0  multi-channel speckle infrastructure
    joint deep-fade statistics of M independent Rayleigh channels follow
    p^M (M = 1, 3, 4; rho = 0; tau_c = 50 us), plus a correlated-channel
    (rho = 0.5) sanity check of the correlation machinery.

P1  non-coherent SNR-weighted velocity-domain combining baseline
    M = 3 channels, mean CNR = 6 dB/channel, speckle tau_c = 50 us,
    3 MHz burst (the validate_tracking V3 dropout scene).  Every channel is
    demodulated independently (homodyne FAST gear: PLL + common residual
    window) and FM-discriminated; block-wise weights
    q_k = (C_k/Nhat)^alpha * LOCK * gs with cross-channel relative gate and
    all-dark HOLD flywheel.  Combined output is compared against the
    PER-SEED ORACLE best single channel (per metric!) -- a baseline
    strictly stronger than any real single-channel instrument.

Exit code 0 iff all checks PASS.  Full output is tee'd to
results_diversity.txt next to this script; set QTEC_ARTIFACTS_DIR to also
copy the results file there (defaults to /opt/cursor/artifacts if it
exists; failures to copy are ignored).
"""
import math
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

import _pkgpath  # noqa: F401  (sys.path bootstrap for the sibling package)
from homodyne_tracking_design.core import (
    burst_signal, welch_psd, lockin_amp, fir_lp_same,
)
from homodyne_tracking_design.design_params import FS, LAMBDA, select_band
from speckle_multi import (
    make_speckle_multi, fade_prob_theory, joint_fade_fraction,
    channel_correlation,
)
from synth_multichannel import synth_multichannel, doppler_phase
from diversity_combine import channel_demod, diversity_combine

CHECKS = []


def check(cid, label, ok, detail):
    CHECKS.append((cid, label, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {cid}  {label}  ({detail})")
    return ok


def print_header(title):
    print('\n' + '=' * 86)
    print(title)
    print('=' * 86)


def stats(a):
    a = np.asarray([x for x in a if np.isfinite(x)])
    if a.size == 0:
        return (np.nan,) * 3
    s = np.sort(a)
    q = lambda p: s[max(0, min(s.size - 1, int(np.ceil(p / 100 * s.size)) - 1))]  # noqa: E731
    return float(np.median(s)), float(q(10)), float(q(90))


# ================================================================== P0
def P0(nseed=6):
    tau_c = 50e-6
    fs_stat = 400e3            # 20 samples per tau_c -- ample for fade stats
    T = 2.5                    # 50 000 tau_c per seed per channel
    N = int(T * fs_stat)
    F_MOD, F_DEEP = 0.3567, 0.105     # -4.5 dB / -9.8 dB intensity fades
    p_mod, p_deep = fade_prob_theory(F_MOD), fade_prob_theory(F_DEEP)
    print_header(f'P0  多路散斑联合深衰落统计  (tau_c={tau_c*1e6:.0f}us, rho=0, '
                 f'{nseed} seeds x {T:.1f}s @ {fs_stat/1e3:.0f}kS/s '
                 f'= {nseed*T/tau_c:,.0f} tau_c/通道)')
    print(f'  衰落定义: 通道强度 I_k < F*<I_k>;  F={F_MOD} (-4.5dB, p1理论 '
          f'{p_mod:.4f}) 与 F={F_DEEP} (-9.8dB 深衰落, p1理论 {p_deep:.4f})')
    res = {}
    for M in (1, 3, 4):
        acc = dict(r_mod=[], r_deep=[], p1_mod=[], p1_deep=[])
        for s in range(nseed):
            rng = np.random.default_rng(40_000 + 97 * M + s)
            h = make_speckle_multi(N, fs_stat, tau_c, M, rho=0.0, rng=rng)
            acc['r_mod'].append(joint_fade_fraction(h, F_MOD))
            acc['r_deep'].append(joint_fade_fraction(h, F_DEEP))
            for k in range(M):
                acc['p1_mod'].append(joint_fade_fraction(h[k:k + 1], F_MOD))
                acc['p1_deep'].append(joint_fade_fraction(h[k:k + 1], F_DEEP))
        res[M] = {k: float(np.mean(v)) for k, v in acc.items()}

    print(f"\n    {'M':>3} {'F':>7} | {'联合衰落率(实测)':>16} {'p1^M(实测外推)':>15} "
          f"{'p^M(理论)':>12} {'实测/外推':>9}")
    for M in (1, 3, 4):
        r = res[M]
        for tag, F, pth in (('mod', F_MOD, p_mod), ('deep', F_DEEP, p_deep)):
            rm, p1 = r['r_' + tag], r['p1_' + tag]
            ratio = rm / p1 ** M if p1 ** M > 0 else np.nan
            print(f"    {M:>3} {F:>7.4f} | {rm:>16.3e} {p1 ** M:>15.3e} "
                  f"{pth ** M:>12.3e} {ratio:>9.2f}")

    p1_meas = res[4]['p1_mod']
    p1d_meas = res[4]['p1_deep']
    check('Q0-1', '单路衰落率符合 Rayleigh 理论 (两个门限, M=4 组, ±10%)',
          abs(p1_meas / p_mod - 1) < 0.10 and abs(p1d_meas / p_deep - 1) < 0.10,
          f'F={F_MOD}: {p1_meas:.4f} vs {p_mod:.4f}; '
          f'F={F_DEEP}: {p1d_meas:.4f} vs {p_deep:.4f}')
    r3 = res[3]['r_mod'] / res[3]['p1_mod'] ** 3
    check('Q0-2', 'M=3 联合衰落率 ~ p^3 (F=-4.5dB, 比值 0.7..1.4)',
          0.7 < r3 < 1.4, f'实测/p1^3 = {r3:.2f}')
    r4 = res[4]['r_mod'] / res[4]['p1_mod'] ** 4
    check('Q0-3', 'M=4 联合衰落率 ~ p^4 (F=-4.5dB, 比值 0.6..1.7)',
          0.6 < r4 < 1.7, f'实测/p1^4 = {r4:.2f}')
    r3d = res[3]['r_deep'] / res[3]['p1_deep'] ** 3
    check('Q0-4', 'M=3 深衰落 (-9.8dB) 联合率 ~ p^3 (比值 0.4..2.2, 事件较少)',
          0.4 < r3d < 2.2, f'实测/p1^3 = {r3d:.2f}')
    print(f'  [info] M=4 深衰落联合率实测 {res[4]["r_deep"]:.2e} '
          f'(理论 p^4 = {p_deep ** 4:.2e}; 本时长下事件过少, 只作参考不断言)')

    # correlated channels: the rho machinery itself
    corr_acc, enh_acc = [], []
    for s in range(3):
        rng = np.random.default_rng(43_000 + s)
        h = make_speckle_multi(N, fs_stat, tau_c, 3, rho=0.5, rng=rng)
        Cm = np.real(channel_correlation(h))
        corr_acc.append(np.mean(Cm[np.triu_indices(3, k=1)]))
        p1 = np.mean([joint_fade_fraction(h[k:k + 1], F_MOD) for k in range(3)])
        enh_acc.append(joint_fade_fraction(h, F_MOD) / p1 ** 3)
    corr_m, enh_m = float(np.mean(corr_acc)), float(np.mean(enh_acc))
    check('Q0-5', 'rho=0.5: 实测场相关 0.4..0.6 且联合衰落率显著高于独立外推 (>1.3x)',
          0.4 < corr_m < 0.6 and enh_m > 1.3,
          f'corr={corr_m:.3f}, 联合率/独立外推 = {enh_m:.2f}x')
    print('  物理结论: 独立通道联合深衰落 ~ p^M -- 分集接收把掉光概率指数压低;'
          ' 通道相关 (rho>0) 会侵蚀该增益, 故 P1 用 rho=0 做上限 baseline.')
    return res


# ================================================================== P1
VAMP = 20e-3


def P1(nseed=10, cnr_db=6.0, M=3, tau_c=50e-6):
    T = 5e-4
    N = int(T * FS)
    t = np.arange(N) / FS
    f0, ncyc, t0 = 3e6, 60, 0.05e-3
    x, v_true, _ = burst_signal(t, f0, VAMP, ncyc, t0)
    phi = doppler_phase(x)
    Tb = ncyc / f0
    Wm = (t > t0) & (t < t0 + Tb)
    Wq = (t > t0 + Tb + 0.04e-3) & (t < 0.48e-3)
    band = select_band(f0, VAMP)
    s2 = 10.0 ** (-cnr_db / 10.0)
    thr = 20 * VAMP
    a0 = lockin_amp(v_true, t, f0, Wm)
    alphas = (1.0, 2.0, math.inf)
    print_header(f'P1  非相干 SNR 加权速度域合成 (M={M}, 每路平均 CNR='
                 f'{cnr_db:.0f}dB, tau_c={tau_c*1e6:.0f}us, gear={band}, '
                 f'B_noise=20MHz, 3MHz burst, {nseed} seeds)')
    print(f'  每路: pll_carrier_regen + 公共残差窗 (gear_filter 全输出路径) + FM 鉴频;'
          f' 块长 2us, rel_x=0.05\n  对照: 每 seed 每指标取最优单路 (oracle,'
          ' 比任何真实单路仪器更强的 baseline)')

    def spike_count(v):
        vlp = fir_lp_same(v, 1e6, FS, 2049)
        ex = np.abs(vlp[Wq]) > thr
        return int(np.sum(np.diff(np.concatenate(([False], ex)).astype(int)) == 1))

    def asd_q(v):
        P, f = welch_psd(v[Wq], FS, 4096)
        m = np.abs(f - f0) < 150e3
        return float(np.sqrt(np.median(P[m])))

    def amp_err_pct(v):
        return 100.0 * (lockin_amp(v, t, f0, Wm) / a0 - 1.0)

    # amplitude-transfer unbiasedness (rule R1 of validate_tracking): at
    # CNR=6dB the 20 us burst lock-in is noise-dominated, so the weighted
    # sum's bias is measured in a separate near-noiseless run -- WITH
    # speckle, so the weights actually move -- and asserted < 5 %.
    print('\n  -- 幅值传递 (R1: 近无噪 CNR=60dB + 散斑, 权重照常工作, 4 seeds) --')
    amp_clean = {a: [] for a in alphas}
    s2c = 10.0 ** (-60.0 / 10.0)
    for s in range(4):
        rng = np.random.default_rng(48_000 + s)
        syn = synth_multichannel(phi, FS, M, 60.0, rng,
                                 tau_c=tau_c, B_noise=20e6)
        chans = [channel_demod(syn['z'][k], FS, band, s2c) for k in range(M)]
        for a in alphas:
            res = diversity_combine(syn['z'], FS, band=band, Nhat=s2c,
                                    alpha=a, chans=chans)
            amp_clean[a].append(amp_err_pct(res['v']))
    for a in alphas:
        aname = 'inf' if math.isinf(a) else f'{a:.0f}'
        m, lo, hi = stats(amp_clean[a])
        print(f'    alpha={aname:<4} burst 幅值误差 {m:+6.2f}%  [{lo:+.2f},{hi:+.2f}]')

    agg = dict(ch_spk=[], ch_asd=[], ch_unlock=[],
               best_spk=[], best_asd=[], best_unlock=[], joint_unlock=[])
    for a in alphas:
        agg[('spk', a)] = []
        agg[('gain', a)] = []
        agg[('dark', a)] = []
    for s in range(nseed):
        rng = np.random.default_rng(50_000 + s)
        syn = synth_multichannel(phi, FS, M, cnr_db, rng,
                                 tau_c=tau_c, B_noise=20e6)
        chans = [channel_demod(syn['z'][k], FS, band, s2) for k in range(M)]
        spk = [spike_count(c['v']) for c in chans]
        asd = [asd_q(c['v']) for c in chans]
        unl = [float(np.mean(c['state'] != 2)) for c in chans]
        agg['ch_spk'] += spk
        agg['ch_asd'] += asd
        agg['ch_unlock'] += unl
        agg['best_spk'].append(min(spk))
        agg['best_asd'].append(min(asd))
        agg['best_unlock'].append(min(unl))
        st = np.stack([c['state'] for c in chans])
        agg['joint_unlock'].append(float(np.mean(np.all(st != 2, axis=0))))
        for a in alphas:
            res = diversity_combine(syn['z'], FS, band=band, Nhat=s2,
                                    alpha=a, chans=chans)
            agg[('spk', a)].append(spike_count(res['v']))
            agg[('gain', a)].append(
                20.0 * math.log10(min(asd) / asd_q(res['v'])))
            agg[('dark', a)].append(res['dark_frac'])

    def row(label, vals, fmt='{:8.1f}'):
        m, lo, hi = stats(vals)
        return f"    {label:<34}" + fmt.format(m) + f"  [{fmt.format(lo).strip():>8},{fmt.format(hi).strip():>8}]"

    print('\n  -- 单路 (所有通道合并) 与最优单路 (per-seed oracle) --')
    print(row('单路 velocity spikes (>0.4m/s)', agg['ch_spk']))
    print(row('最优单路 spikes', agg['best_spk']))
    print(row('单路失锁时间 %', [100 * u for u in agg['ch_unlock']]))
    print(row('最优单路失锁 %', [100 * u for u in agg['best_unlock']]))
    print(row('全通道同时失锁 (联合) %', [100 * u for u in agg['joint_unlock']], '{:8.2f}'))
    print(row('单路速度ASD @3MHz (um/s/rtHz)', [1e6 * a for a in agg['ch_asd']]))
    print(row('最优单路 ASD (um/s/rtHz)', [1e6 * a for a in agg['best_asd']]))
    print('\n  -- 合成输出 (中值 [p10,p90]) --')
    print(f"    {'alpha':<8} {'spikes':>16} {'SNRgain vs 最优单路':>22} "
          f"{'全暗HOLD %':>12}")
    for a in alphas:
        sm, sl, sh = stats(agg[('spk', a)])
        gm, gl, gh = stats(agg[('gain', a)])
        dm = stats([100 * d for d in agg[('dark', a)]])[0]
        aname = 'inf' if math.isinf(a) else f'{a:.0f}'
        print(f"    {aname:<8} {sm:7.1f} [{sl:3.0f},{sh:4.0f}] "
              f"{gm:+11.2f} [{gl:+5.2f},{gh:+5.2f}] dB {dm:11.2f}")

    best_spk_med = stats(agg['best_spk'])[0]
    spk2_med = stats(agg[('spk', 2.0)])[0]
    check('Q1-1', '合成(α=2, 推荐默认) 速度尖峰中值 <= 0.6x 最优单路 (掉落抑制)',
          spk2_med <= 0.6 * best_spk_med,
          f'{spk2_med:.0f} vs 最优单路 {best_spk_med:.0f}')
    g2_med = stats(agg[('gain', 2.0)])[0]
    check('Q1-2', '合成(α=2) 静默段速度ASD SNR增益 vs 最优单路 > +2 dB',
          g2_med > 2.0, f'{g2_med:+.2f} dB (α=1 速度域MRC: '
          f'{stats(agg[("gain", 1.0)])[0]:+.2f} dB; 理想等权上限 '
          f'{10 * math.log10(M):.1f} dB)')
    dark_med = stats(agg[('dark', 2.0)])[0]
    unlock_med = stats(agg['best_unlock'])[0]
    check('Q1-3', '合成 全暗HOLD时间 <= 0.5x 最优单路失锁时间 (可用性)',
          dark_med <= 0.5 * unlock_med,
          f'{100 * dark_med:.2f}% vs 最优单路失锁 {100 * unlock_med:.2f}%')
    worst = max(stats(agg[('spk', a)])[0] for a in alphas)
    check('Q1-4', '全部 α∈{1,2,∞} 的合成尖峰中值均 <= 最优单路 (权重律稳健)',
          worst <= best_spk_med, f'最差 α 的中值 {worst:.0f} vs {best_spk_med:.0f}')
    amp_worst = max(abs(stats(amp_clean[a])[0]) for a in (1.0, 2.0))
    check('Q1-5', '加权和无系统性幅值偏置: R1 近无噪+散斑 burst 幅值误差 '
          '|中值| < 5% (α=1,2)',
          amp_worst < 5.0, f'worst |err| = {amp_worst:.2f}%')
    print('\n  诚实说明: 速度域非相干合成不改变单路 FM 门限本身, 它买到的是'
          ' (a) 联合掉光率 ~p^M,\n  (b) 静默段噪声按权重平均下降, (c) 尖峰只在'
          '全通道同弱时出现. 更低 CNR 的门限扩展\n  需要 IQ 域相干合成 (P2 路线).'
          ' α=1 为速度域 MRC (平稳噪声方差最优) 但对非高斯 click\n  尖峰欠抑制;'
          ' α=∞ 纯选路尖峰最少但放弃平均增益 (~-1.6 dB); α=2 为推荐默认折中.'
          '\n  CNR=6dB 下 burst 幅值在单 seed 上被 FM 噪声主导 (R1 规则),'
          ' 故幅值无偏性在近无噪+散斑运行中断言.')
    return agg


# ================================================================== main
def run_all():
    t0 = time.time()
    print('QTec 多路散斑分集 P0+P1 -- 仿真验证')
    print(f'per-channel demod: homodyne pll_carrier_regen + 公共残差窗, '
          f'fs={FS/1e6:.0f}MS/s, lambda={LAMBDA*1e9:.0f}nm')
    P0()
    P1()
    print_header('ASSERTION SUMMARY')
    allok = True
    for cid, label, ok, detail in CHECKS:
        allok &= ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {cid}  {label}  ({detail})")
    print('\n' + ('ALL CHECKS PASSED' if allok else 'SOME CHECKS FAILED'))
    print(f'[elapsed {time.time() - t0:.1f} s]')
    return 0 if allok else 1


class _Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)

    def flush(self):
        for st in self.streams:
            st.flush()


def main():
    out_path = Path(__file__).resolve().parent / 'results_diversity.txt'
    old = sys.stdout
    with open(out_path, 'w') as fh:
        sys.stdout = _Tee(old, fh)
        try:
            rc = run_all()
        finally:
            sys.stdout = old
    art_dir = os.environ.get('QTEC_ARTIFACTS_DIR', '/opt/cursor/artifacts')
    try:
        shutil.copy2(out_path, Path(art_dir) / out_path.name)
        print(f'[artifacts] results copied to {art_dir}')
    except OSError:
        pass
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
