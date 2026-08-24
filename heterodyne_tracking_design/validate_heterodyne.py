#!/usr/bin/env python3
"""H1-H6 外差电IQ (Polytec类) 跟踪滤波完整仿真验证.

被测架构 (见 design_params.py):
  数字下变频后复基带 z(t), 单旋钮 II 型 arctan DPLL (core.pll_carrier_regen),
  纯 NCO 输出 y = e^{j phi} -- 对齐 OFV-3001 附录 D.2 (无零差残差窗)。
  档位 (SLOW/MEDIUM/FAST) 由量程加速度推 fn, 同时决定测量带宽 f_3dB=2.058*fn
  与跟踪动态 a_design/a_slip -- 与零差设计哲学的根本不同点。

场景 / 断言:
  H0  三档参数表 + 硬边界 (fs 混叠 / IF 频偏窗 / fs/50 离散约束)
  H1  四层带宽敏感性: fs vs B_frontend vs B_loop -> 环内相位噪声 sigma_phi^2
        C11 sigma_phi^2 与理论 s2*B_loop/B_frontend 吻合 (+-2 dB)
        C12 fs 50->100 MHz (同 B_frontend): sigma_phi 不变 (fs 不是噪声带宽)
        C13 B_frontend 19->9.5 MHz (同带内 CNR): 方差 x2
        C14 三档方差比 = B_loop 比 = sqrt(10)/档
  H2  三档弱光 CNR sweep (50 kHz 结构 + 5 MHz PSV类超声), R1-R4 公平规则
        C21 SLOW@50k: CNR=0 增益>10dB, CNR=4 >6dB (FM 门限扩展)
        C22 SLOW@50k: 增益(CNR0) - 增益(CNR20) > 6 dB (增益本质是门限扩展)
        C23 FAST@5M: CNR=4 谱线 SNR 增益 > 0 dB (复现用户 PSV-500 实测)
        C24 FAST@5M: 未校正幅值衰减数倍(|H_L|), 频响校正后 |err|<10%
        C25 50k 谱线: 三档频响校正后 |err|<5%
        C26 SLOW@5M: 未校正幅值比 <0.05 -- 档位=测量带宽 (无残差窗兜底)
  H3  量程/速度扫描: fn 参数化 vs 固定 fn=400k (旧硬编码)
        C31 参数化 fn: 全量程 |校正幅值误差|<10% 且 0 周跳
        C32 3 m/s: 固定 fn 失锁(周跳/幅值崩), 参数化 fn 保持
        C33 10 mm/s: 参数化 fn 噪声增益比固定 fn 高 >5 dB
  H4  浴缸形动态边界复现 (纯 PLL, 频响校正后测幅, OFF 对照)
        C41 5 个频点: 0.5*v_pi 通过 / 2*v_pi 失败 (边界夹在理论 2 倍内)
        C42 浴缸形: 边界谷底在 f=fn (低/高频侧均更高)
        C43 OFF 鉴频器在 f=fn, 2*v_pi 无边界 (<5% 误差) -- 边界是环的属性
  H5  e_crit=1 vs pi (来自 t5/o5): 设计线可用 / 卷绕线必败
        C51 e=1: 全部量程 |幅值误差|<10%
        C52 e=pi: 全部量程 幅值误差 < -30% (在卷绕线上设计必失败)
        C53 e=1: PLL 谱线噪声增益 > +3 dB (全量程)
  H6  与固定 preLP 同 B_loop 对照 (外差大频偏场景, 与 H5 同一扫描)
        C61 固定 preLP: v>=0.2 m/s 幅值 < -80% 崩溃 (载波走出通带)
        C62 v=1.5 m/s: PLL |err|<10% 而 preLP <-80% -- 跟踪的唯一价值面

公平比较规则 (R1-R4, 沿袭参考 t1_main.py):
  R1 信号传递(幅值误差)在近无噪独立运行测定 (弱光单 burst 锁相被噪声支配);
  R2 噪声 ASD 在安静窗口/远离信号谐波的频带取中值;
  R3 谱线 SNR 增益 = 信号传递增益 + 20*log10(ASD_off/ASD_on);
  R4 多种子取中值 [p10, p90]。
CNR sweep 全部用 gate='always' (core.py 文档: 绝对门限门无法区分
"暗而稳定的光"与"掉落", 干净的 CNR sweep 必须隔离门)。
"""
import math
import time
import numpy as np

from core import (
    burst_signal, complex_bandlimited_noise, pll_carrier_regen,
    fm_discriminator, fir_lp, welch_psd, lockin_amp, hl_response,
)
from design_params import (
    LAMBDA, FS, B_FRONTEND, F_DEV_MAX, ZETA, ORDER,
    mode_params, b_loop, f_3db, v_pll_limit, v_if_limit, v_alias_limit,
    fn_discrete_ok, loop_gain_mag, tracking_error_rad, select_mode,
    a_design_fast, fn_from_a, FIXED_FN_LEGACY, B_LOOP_COEF, F3DB_COEF,
)

TINY = 1e-300
MODES = mode_params(1.0)          # 演示统一取中间量程 1 m/s (对齐 .m)


# ----------------------------------------------------------------- helpers
def stats(a):
    a = np.asarray([x for x in a if np.isfinite(x)])
    if a.size == 0:
        return (np.nan,) * 3
    s = np.sort(a)
    q = lambda p: s[max(0, min(s.size - 1, int(np.ceil(p / 100 * s.size)) - 1))]
    return float(np.median(s)), float(q(10)), float(q(90))


def print_header(title):
    print('\n' + '=' * 92)
    print(title)
    print('=' * 92)


CHECKS = []


def check(cid, label, ok, detail):
    CHECKS.append((cid, label, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {cid}  {label}  ({detail})")
    return ok


def ls_amp(v, t, f_v, sel):
    """sin/cos 最小二乘幅值 (对任意相位与少量周期稳健, 沿袭 t5)."""
    X = np.column_stack([np.ones(int(sel.sum())),
                         np.sin(2 * np.pi * f_v * t[sel]),
                         np.cos(2 * np.pi * f_v * t[sel])])
    b, *_ = np.linalg.lstsq(X, v[sel], rcond=None)
    return float(np.hypot(b[1], b[2]))


def asd_band(v, sel, fs, L, f_lo, f_hi):
    """速度 ASD: 频带内 PSD 中值的平方根 (R2)."""
    P, f = welch_psd(v[sel], fs, L)
    m = (f >= f_lo) & (f <= f_hi)
    return max(math.sqrt(float(np.median(P[m]))), TINY)


def complex_lp(z, B_pre, fs, Nt=401):
    """固定复数低通 (双边宽 B_pre), 沿袭 t5 的 preLP 对照."""
    return (fir_lp(z.real, B_pre / 2, fs, Nt)
            + 1j * fir_lp(z.imag, B_pre / 2, fs, Nt))


def vdisc(y, fs=FS):
    return fm_discriminator(y, fs, LAMBDA)


def hl_mag(f0, fn, fs=FS):
    """精确离散闭环 |H_L(f0)| -- 频响校正因子的倒数."""
    return float(np.abs(hl_response(np.array([f0]), fs, fn, ZETA))[0])


def run_pll(z, fs, fn, s2):
    """统一入口: gate='always' 纯 NCO (CNR sweep 的隔离门要求)."""
    return pll_carrier_regen(z, fs, fn, max(s2, 1e-12), zeta=ZETA,
                             gate='always')


# ================================================================== H0
def H0():
    print_header('H0  三档参数表 [自研规则] + 硬边界   (lambda=632.8nm, '
                 f'fs={FS/1e6:.0f}MHz, B_frontend={B_FRONTEND/1e6:.1f}MHz, '
                 f'f_dev_max={F_DEV_MAX/1e6:.1f}MHz, zeta={ZETA})')
    print(f"  混叠极限 v_alias = lambda*fs/4      = {v_alias_limit():.3f} m/s"
          f"   (fs 只决定这一条, 不是噪声带宽 -- H1 验证)")
    print(f"  IF 硬窗  v_if    = lambda*f_dev/2   = {v_if_limit():.3f} m/s"
          f"   (与 ENBW 是两个参数)")
    print(f"  B_loop = {B_LOOP_COEF:.4f}*fn (单边 ENBW), f_3dB = {F3DB_COEF:.4f}*fn"
          f" = 纯 NCO 架构的测量带宽")
    print('\n  fn(mode, v_range, acq_bw=1MHz, f_acc_cap=100kHz):')
    print(f"  {'v_range':>9} | {'档':>6} {'fn':>9} {'f_3dB':>9} {'B_loop':>9} "
          f"{'a_design(e=1)':>13} {'a_slip(e=pi)':>12} {'浴缸谷(e=pi)':>13} "
          f"{'降噪vsOFF':>9} {'fs/50':>6}")
    ok_guard = True
    for vr in (0.01, 0.1, 1.0, 3.0, 10.0):
        modes = mode_params(vr)
        for name in ORDER:
            m = modes[name]
            okd = fn_discrete_ok(m['fn'])
            if vr <= 3.0 and not okd:
                ok_guard = False
            if vr == 10.0 and name == 'FAST' and okd:
                ok_guard = False
            head = f"  {vr:7.2f}m/s |" if name == 'SLOW' else f"  {'':>9} |"
            print(f"{head} {name:>6} {m['fn']/1e3:7.1f}k {m['f_3db']/1e3:7.1f}k "
                  f"{m['B_loop']/1e3:7.1f}k {m['a_design']:13.3g} "
                  f"{m['a_slip']:12.3g} {m['valley_v']*1e3:9.2f}mm/s "
                  f"{m['noise_red_db']:+8.1f}dB {'ok' if okd else 'FAIL':>6}")
    check('C01', '离散稳定守卫 fn<=fs/50: v_range<=3 m/s 全过, 10 m/s FAST 触发'
          ' (实机需提高 fs 或降 f_acc_cap)', ok_guard,
          f"fn(FAST,10m/s)={mode_params(10.0)['FAST']['fn']/1e3:.0f}k vs "
          f"fs/50={FS/50/1e3:.0f}k")
    print('\n  选档演示 (外差: 档位同时定测量带宽与动态, f_3dB 是硬约束):')
    for f0, vp in ((20e3, 0.05), (100e3, 0.05), (100e3, 1.0), (5e6, 0.01)):
        sel = select_mode(f0, vp)
        print(f"    f_target={f0/1e3:7.0f}kHz, v_peak={vp*1e3:5.0f}mm/s -> {sel}"
              f"   (f_3dB={MODES[sel]['f_3db']/1e3:.0f}k"
              f"{', 5MHz>f_3dB(FAST): 只能 FAST+频响校正' if f0 > MODES['FAST']['f_3db'] else ''})")


# ================================================================== H1
def H1(nseed=3, cnr_db=20.0, df_off=20e3):
    fnM = MODES['MEDIUM']['fn']
    print_header(f'H1  四层带宽敏感性: fs vs B_frontend vs B_loop  '
                 f'(CNR={cnr_db:.0f}dB, 载波偏 {df_off/1e3:.0f}kHz, '
                 f'{nseed} seeds, 环内相位噪声方差)')
    s2 = 10 ** (-cnr_db / 10)

    def sigma2_phi(fs, Bf, fn, T=1.5e-3, skip=0.7e-3):
        N = int(T * fs)
        t = np.arange(N) / fs
        ph = 2 * np.pi * df_off * t
        vs = []
        for s in range(nseed):
            rng = np.random.default_rng(41_000 + s)
            z = np.exp(1j * ph) + complex_bandlimited_noise(N, fs, Bf, s2, rng)
            _, phi, _, _ = pll_carrier_regen(z, fs, fn, s2, zeta=ZETA,
                                             gate='always')
            e = np.angle(np.exp(1j * (phi - ph)))[t > skip]
            vs.append(float(np.mean((e - e.mean()) ** 2)))
        return stats(vs)[0]

    cfgs = [('base  fs=50M  Bf=19M   fn=MED', FS, B_FRONTEND, fnM),
            ('fs x2 fs=100M Bf=19M   fn=MED', 100e6, B_FRONTEND, fnM),
            ('Bf /2 fs=50M  Bf=9.5M  fn=MED', FS, 9.5e6, fnM),
            ('SLOW  fs=50M  Bf=19M   fn=SLOW', FS, B_FRONTEND, MODES['SLOW']['fn']),
            ('FAST  fs=50M  Bf=19M   fn=FAST', FS, B_FRONTEND, MODES['FAST']['fn'])]
    out = {}
    print(f"\n  {'配置':<34} {'fn':>8} {'B_loop':>9} {'sigma2 理论':>12} "
          f"{'sigma2 实测':>12} {'偏差':>7}")
    for label, fs, Bf, fn in cfgs:
        th = s2 * b_loop(fn) / Bf
        me = sigma2_phi(fs, Bf, fn)
        out[label.split()[0]] = (th, me)
        print(f"  {label:<34} {fn/1e3:6.1f}k {b_loop(fn)/1e3:7.1f}k "
              f"{th:12.3e} {me:12.3e} {10*math.log10(me/th):+6.2f}dB")

    d_base = 10 * math.log10(out['base'][1] / out['base'][0])
    check('C11', 'sigma_phi^2 与理论 s2*B_loop/B_frontend 吻合 (+-2dB)',
          abs(d_base) < 2.0, f'base 偏差 {d_base:+.2f} dB')
    d_fs = 10 * math.log10(out['fs'][1] / out['base'][1])
    check('C12', 'fs 50->100MHz (同 B_frontend): sigma_phi^2 不变 (<1.5dB) '
          '-- fs 不是噪声带宽', abs(d_fs) < 1.5, f'{d_fs:+.2f} dB')
    r_bf = out['Bf'][1] / out['base'][1]
    check('C13', 'B_frontend 19->9.5MHz (同带内CNR): 方差 x2 (N0 翻倍)',
          1.5 < r_bf < 2.7, f'x{r_bf:.2f}')
    r1 = out['FAST'][1] / out['base'][1]
    r2 = out['base'][1] / out['SLOW'][1]
    check('C14', '三档方差比 = B_loop 比 = sqrt(10) 每档 (x2.2..4.5)',
          2.2 < r1 < 4.5 and 2.2 < r2 < 4.5,
          f'FAST/MED x{r1:.2f}, MED/SLOW x{r2:.2f}')
    print('  结论: 环内噪声只看 B_frontend 与 B_loop; 采样率翻倍不改变任何噪声,'
          ' 三档灵敏度差每档 5 dB。')
    return out


# ================================================================== H2
SCENES = {
    50e3: dict(ncyc=10, t0=0.15e-3, T=0.8e-3, L=8192, band=(10e3, 90e3),
               q0=0.40e-3, q1=0.78e-3),
    5e6: dict(ncyc=40, t0=0.10e-3, T=0.3e-3, L=4096, band=(4e6, 6e6),
              q0=0.13e-3, q1=0.29e-3),
}
VAMP = 10e-3
DF_OFF = 20e3


def make_scene(f0):
    p = SCENES[f0]
    N = int(p['T'] * FS)
    t = np.arange(N) / FS
    x, v, _ = burst_signal(t, f0, VAMP, p['ncyc'], p['t0'])
    ph = 4 * np.pi / LAMBDA * x + 2 * np.pi * DF_OFF * t
    Wm = (t > p['t0']) & (t < p['t0'] + p['ncyc'] / f0)
    Wq = (t > p['q0']) & (t < p['q1'])
    return dict(f0=f0, N=N, t=t, v=v, ph=ph, Wm=Wm, Wq=Wq, p=p)


def H2(nseed=6, cnrs=(0, 4, 10, 20)):
    print_header(f'H2  三档弱光 CNR sweep -- 50 kHz 结构 burst + 5 MHz PSV类'
                 f'超声 burst (vamp={VAMP*1e3:.0f}mm/s, 载波偏 '
                 f'{DF_OFF/1e3:.0f}kHz, B_frontend={B_FRONTEND/1e6:.0f}MHz, '
                 f'{nseed} seeds, R1-R4 规则, gate=always)')
    res = {}
    for f0 in (50e3, 5e6):
        sc = make_scene(f0)
        t, p = sc['t'], sc['p']
        # ---- R1: 近无噪信号传递 (含 |H_L| 频响信息) ----
        zc = np.exp(1j * sc['ph'])
        a_true = lockin_amp(sc['v'], t, f0, sc['Wm'])
        a_off_c = lockin_amp(vdisc(zc), t, f0, sc['Wm'])
        row = {}
        for name in ORDER:
            fn = MODES[name]['fn']
            y, _, _, _ = run_pll(zc, FS, fn, 1e-10)
            a_on_c = lockin_amp(vdisc(y), t, f0, sc['Wm'])
            H = hl_mag(f0, fn)
            row[name] = dict(
                ratio_raw=a_on_c / a_true,
                err_corr=100 * (a_on_c / H / a_true - 1),
                g_sig=20 * math.log10(max(a_on_c, TINY) / max(a_off_c, TINY)),
                H=H, gains={c: [] for c in cnrs}, slips={c: [] for c in cnrs})
        # ---- R2/R3/R4: 噪声窗 + 多种子 ----
        for cnr in cnrs:
            s2 = 10 ** (-cnr / 10)
            for s in range(nseed):
                rng = np.random.default_rng(42_000 + int(f0 / 1e3) + 97 * s)
                z = np.exp(1j * sc['ph']) + complex_bandlimited_noise(
                    sc['N'], FS, B_FRONTEND, s2, rng)
                a_off = asd_band(vdisc(z), sc['Wq'], FS, p['L'], *p['band'])
                for name in ORDER:
                    y, _, _, dg = run_pll(z, FS, MODES[name]['fn'], s2)
                    a_on = asd_band(vdisc(y), sc['Wq'], FS, p['L'], *p['band'])
                    row[name]['gains'][cnr].append(
                        row[name]['g_sig'] + 20 * math.log10(a_off / a_on))
                    row[name]['slips'][cnr].append(dg['near_pi_events'])
        print(f"\n  f0 = {f0/1e3:.0f} kHz burst ({p['ncyc']} cyc), 谱线 SNR 增益"
              f" vs OFF (R3 = R1信号传递 + R2噪声窗中值, R4 中值):")
        print(f"    {'档':>6} {'fn':>8} {'|H_L(f0)|':>9} {'未校正幅值比':>11} "
              f"{'校正后err':>9} |" + ''.join(f"  {'CNR'+str(c)+'dB':>15}" for c in cnrs))
        for name in ORDER:
            r = row[name]
            cells = ''
            for c in cnrs:
                m, lo, hi = stats(r['gains'][c])
                cells += f"  {m:+6.1f}[{lo:+5.1f},{hi:+5.1f}]"[:17].rjust(17)
            print(f"    {name:>6} {MODES[name]['fn']/1e3:6.1f}k {r['H']:9.4f} "
                  f"{r['ratio_raw']:11.4f} {r['err_corr']:+8.2f}% |{cells}")
        res[f0] = row
    print("\n  物理解读: 档位=测量带宽 (纯NCO无残差窗): SLOW/MED 在 5 MHz 幅值"
          "结构性塌掉 (|H_L|),\n  FAST 衰减数倍但可用已知 |H_L| 校正 -- 复现用户"
          " PSV-500 '10 MHz FAST 幅值衰减数倍' 现象;\n  增益本质是 FM 门限扩展:"
          " 高 CNR 下 OFF 无点击, 谱线增益归零 (校正不改变 SNR)。")

    r50, r5M = res[50e3], res[5e6]
    g0 = stats(r50['SLOW']['gains'][0])[0]
    g4 = stats(r50['SLOW']['gains'][4])[0]
    g20 = stats(r50['SLOW']['gains'][20])[0]
    check('C21', 'SLOW@50kHz: 谱线SNR增益 CNR=0 >10dB 且 CNR=4 >6dB (门限扩展)',
          g0 > 10.0 and g4 > 6.0, f'CNR0 {g0:+.1f} dB, CNR4 {g4:+.1f} dB')
    check('C22', 'SLOW@50kHz: 增益(CNR0)-增益(CNR20) >6dB -- 增益只在门限以下',
          g0 - g20 > 6.0, f'{g0:+.1f} - ({g20:+.1f}) = {g0-g20:.1f} dB')
    gF4 = stats(r5M['FAST']['gains'][4])[0]
    check('C23', 'FAST@5MHz: CNR=4 谱线SNR增益 >0dB (复现用户 PSV-500 弱回光'
          '底噪下降实测)', gF4 > 0.0, f'{gF4:+.1f} dB')
    rr = r5M['FAST']['ratio_raw']
    ec = r5M['FAST']['err_corr']
    check('C24', 'FAST@5MHz: 未校正幅值衰减数倍 (0.1<比<0.5) 且频响校正后 '
          '|err|<10%', 0.1 < rr < 0.5 and abs(ec) < 10.0,
          f'比 {rr:.3f} (x{1/rr:.1f} 衰减), 校正后 {ec:+.2f}%')
    worst50 = max(abs(r50[n]['err_corr']) for n in ORDER)
    check('C25', '50kHz 谱线: 三档频响校正后 |err|<5% (校正用精确离散 H_L)',
          worst50 < 5.0, f'worst {worst50:.2f}%')
    rs = r5M['SLOW']['ratio_raw']
    check('C26', 'SLOW@5MHz: 未校正幅值比 <0.05 -- 外差档位=测量带宽, '
          '无零差残差窗兜底', rs < 0.05, f'{rs:.4f}')
    return res


# ================================================================== H3
def H3(nseed=4, cnr_db=10.0, f_v=1e5, fixed_fn=400e3):
    print_header(f'H3  量程扫描: fn 参数化 vs 固定 fn={fixed_fn/1e3:.0f}k '
                 f'(旧硬编码 FAST)  -- 正弦 v_range@{f_v/1e3:.0f}kHz '
                 f'(=f_acc 设计点), CNR={cnr_db:.0f}dB, {nseed} seeds')
    s2 = 10 ** (-cnr_db / 10)
    t_pre = 0.20e-3                       # 先静止入锁, 再从 v=0 起振 (解耦捕获)
    T = t_pre + 8 / f_v
    N = int(T * FS)
    t = np.arange(N) / FS
    td = np.maximum(t - t_pre, 0.0)
    on = (t >= t_pre).astype(float)
    sel = t > t_pre + 3 / f_v
    print(f"\n  {'v_range':>9} {'a_pk':>10} | {'方案':<10} {'fn':>8} "
          f"{'a_slip':>10} {'幅值err(校正)':>13} {'周跳':>5} {'噪声增益dB':>17}")
    res = {}
    for vr in (0.01, 0.1, 0.3, 1.0, 3.0):
        a_pk = 2 * np.pi * f_v * vr
        x = on * vr / (2 * np.pi * f_v) * (1 - np.cos(2 * np.pi * f_v * td))
        v_true = on * vr * np.sin(2 * np.pi * f_v * td)
        ph = 4 * np.pi / LAMBDA * x
        a_true = ls_amp(v_true, t, f_v, sel)
        fn_par = mode_params(vr)['FAST']['fn']
        row = {}
        for tag, fn in (('param', fn_par), ('fixed', fixed_fn)):
            errs, slips, gains = [], [], []
            H = hl_mag(f_v, fn)
            for s in range(nseed):
                rng = np.random.default_rng(43_000 + int(vr * 1e4) + 31 * s)
                z = np.exp(1j * ph) + complex_bandlimited_noise(
                    N, FS, B_FRONTEND, s2, rng)
                a_off = asd_band(vdisc(z), sel, FS, 4096, 0.45e6, 2.9e6)
                y, _, _, dg = run_pll(z, FS, fn, s2)
                v_on = vdisc(y)
                errs.append(100 * (ls_amp(v_on, t, f_v, sel) / H / a_true - 1))
                slips.append(dg['near_pi_events'])
                gains.append(20 * math.log10(
                    a_off / asd_band(v_on, sel, FS, 4096, 0.45e6, 2.9e6)))
            row[tag] = dict(fn=fn, err=stats(errs)[0], slip=stats(slips)[0],
                            gain=stats(gains))
            g = row[tag]['gain']
            a_sl = math.pi ** 2 * LAMBDA * fn ** 2
            head = (f"  {vr*1e3:6.0f}mm/s {a_pk:10.3g} |" if tag == 'param'
                    else f"  {'':>9} {'':>10} |")
            print(f"{head} {tag:<10} {fn/1e3:6.1f}k {a_sl:10.3g} "
                  f"{row[tag]['err']:+12.1f}% {row[tag]['slip']:5.0f} "
                  f"{g[0]:+6.1f}[{g[1]:+5.1f},{g[2]:+5.1f}]")
        res[vr] = row
    print("\n  解读: 固定 400k 档在小量程浪费 8.5dB(B_loop 比) 灵敏度, 在 3 m/s"
          " (a_pk=1.9e6 > a_slip=1.0e6) 失锁;\n  参数化 fn 全量程贴着 e=1 设计线"
          " (a_pk = a_design), 幅值与锁定都保持。")
    ok31 = all(abs(res[vr]['param']['err']) < 10 and res[vr]['param']['slip'] == 0
               for vr in res)
    check('C31', '参数化 fn: 全量程 |校正幅值误差|<10% 且 0 周跳 (e=1 设计线可用)',
          ok31, ', '.join(f"{vr}:{res[vr]['param']['err']:+.1f}%" for vr in res))
    fx3 = res[3.0]['fixed']
    check('C32', '3 m/s: 固定 fn=400k 失锁 (周跳>0 或 |err|>30%), 参数化保持<10%',
          (fx3['slip'] > 0 or abs(fx3['err']) > 30)
          and abs(res[3.0]['param']['err']) < 10,
          f"fixed err {fx3['err']:+.1f}% slip {fx3['slip']:.0f} vs "
          f"param {res[3.0]['param']['err']:+.1f}%")
    dg33 = res[0.01]['param']['gain'][0] - res[0.01]['fixed']['gain'][0]
    check('C33', '10 mm/s: 参数化 fn 噪声增益比固定 fn 高 >5dB (量程小 -> 环窄)',
          dg33 > 5.0, f'{dg33:+.1f} dB (理论 B_loop 比 '
          f"{10*math.log10(fixed_fn/mode_params(0.01)['FAST']['fn']):.1f} dB)")
    return res


# ================================================================== H4
def H4(cnr_db=30.0):
    fn = MODES['MEDIUM']['fn']
    print_header(f'H4  浴缸形动态边界复现 (MEDIUM fn={fn/1e3:.1f}k, 纯PLL, '
                 f'e_crit=pi 卷绕线理论 vs 实测夹逼, CNR={cnr_db:.0f}dB, '
                 f'频响校正测幅)')
    s2 = 10 ** (-cnr_db / 10)
    t_pre = 0.20e-3
    mults = (0.5, 0.71, 1.0, 1.41, 2.0)
    freqs = [fn / 8, fn / 3, fn, 3 * fn, 8 * fn]
    rng = np.random.default_rng(44_000)

    def one(f_v, vamp):
        T = t_pre + max(8 / f_v, 60e-6)
        N = int(T * FS)
        t = np.arange(N) / FS
        td = np.maximum(t - t_pre, 0.0)
        on = (t >= t_pre).astype(float)
        sel = t > t_pre + max(3 / f_v, 25e-6)
        x = on * vamp / (2 * np.pi * f_v) * (1 - np.cos(2 * np.pi * f_v * td))
        v_true = on * vamp * np.sin(2 * np.pi * f_v * td)
        ph = 4 * np.pi / LAMBDA * x
        z = np.exp(1j * ph) + complex_bandlimited_noise(N, FS, B_FRONTEND, s2, rng)
        a_true = ls_amp(v_true, t, f_v, sel)
        y, _, _, dg = run_pll(z, FS, fn, s2)
        err = 100 * (ls_amp(vdisc(y), t, f_v, sel) / hl_mag(f_v, fn) / a_true - 1)
        e_off = 100 * (ls_amp(vdisc(z), t, f_v, sel) / a_true - 1)
        return err, dg['near_pi_events'], e_off

    print(f"\n  理论: v_pi(f) = pi*lambda*f/2/|1-H_L|, 谷底 (f=fn, "
          f"{v_pll_limit(fn, fn)*1e3:.0f} mm/s = pi*lambda*fn/sqrt2)")
    print(f"  {'f_v':>9} {'x=f/fn':>7} {'v_pi 理论':>10} | " +
          ''.join(f"{f'{m:.2f}v_pi':>14}" for m in mults) + f" | {'实测边界':>9}")
    bounds = {}
    ok41 = True
    e_off_ref = None
    for f_v in freqs:
        v_pi = v_pll_limit(f_v, fn)
        cells, passed = '', 0.0
        for mlt in mults:
            err, slips, e_off = one(f_v, mlt * v_pi)
            good = slips == 0 and abs(err) < 25
            if good:
                passed = mlt * v_pi
            cells += f"  {err:+7.1f}%{'/' + str(int(slips)) + 's':>4}"[:14].rjust(14)
            if f_v == fn and abs(mlt - 2.0) < 1e-9:
                e_off_ref = e_off
        first, last = one(f_v, 0.5 * v_pi), one(f_v, 2.0 * v_pi)
        ok_f = (first[1] == 0 and abs(first[0]) < 25) and \
               (last[1] > 0 or abs(last[0]) > 25)
        ok41 &= ok_f
        bounds[f_v] = passed
        print(f"  {f_v/1e3:7.1f}k {f_v/fn:7.2f} {v_pi*1e3:8.1f}mm |{cells} | "
              f"{passed*1e3:7.1f}mm{'' if ok_f else '  <-- 未夹住'}")
    check('C41', '5 个频点: 0.5*v_pi 全通过 且 2*v_pi 全失败 -- 实测边界夹在'
          '理论卷绕线 2 倍以内', ok41,
          'err<25% 且 0 周跳 为通过判据')
    ok42 = bounds[fn] < bounds[freqs[0]] and bounds[fn] < bounds[freqs[-1]]
    check('C42', '浴缸形: 谷底在 f=fn (低频侧受 a_slip, 高频侧受相位摆幅, '
          '谷值 pi*lambda*fn/sqrt2)', ok42,
          f'边界 {bounds[freqs[0]]*1e3:.0f} / {bounds[fn]*1e3:.0f} / '
          f'{bounds[freqs[-1]]*1e3:.0f} mm/s @ fn/8, fn, 8fn')
    check('C43', 'OFF 鉴频器 @f=fn, v=2*v_pi 无边界 (|err|<5%) -- 浴缸边界是'
          '跟踪环自身的代价', abs(e_off_ref) < 5.0, f'OFF err {e_off_ref:+.2f}%')
    print(f"  整机包络 = min(纯PLL边界, v_if={v_if_limit():.2f} m/s, "
          f"v_alias={v_alias_limit():.2f} m/s) -- 高频翼被 IF 硬窗截平。")
    return bounds


# ================================================================== H5+H6
def H56(nseed=6, cnr_db=6.0, f_v=10e3, T=0.6e-3):
    print_header(f'H5+H6  e_crit=1 vs pi 边界 + 固定 preLP(同 B_loop) 对照 '
                 f'(t5/o5 复现: 振动 {f_v/1e3:.0f}kHz, 前端被量程强制 '
                 f'B_front=2*f_D, CNR={cnr_db:.0f}dB, {nseed} seeds)')
    s2 = 10 ** (-cnr_db / 10)
    N = int(T * FS)
    t = np.arange(N) / FS
    sel = t > 1.5 / f_v
    res = {}
    print(f"\n  {'v_range':>8} {'f_D':>7} {'B_front':>8} {'fn(e1)':>8} "
          f"{'B_loop':>8} {'ceil':>6} | {'err e1':>8} {'err epi':>9} "
          f"{'err preLP':>10} | {'PLL增益':>8} {'preLP增益':>9}")
    for vr in (0.05, 0.2, 0.6, 1.5, 3.0):
        fD = 2 * vr / LAMBDA
        B_front = 2 * fD                    # 前端被速度量程强制, 不可收窄
        if B_front > FS / 2:
            continue
        a_pk = 2 * np.pi * f_v * vr
        fn1 = fn_from_a(a_pk, e_crit=1.0)
        fnp = fn_from_a(a_pk, e_crit=math.pi)
        B_loop1 = b_loop(fn1)
        x = vr / (2 * np.pi * f_v) * (1 - np.cos(2 * np.pi * f_v * t))
        v_true = vr * np.sin(2 * np.pi * f_v * t)
        ph = 4 * np.pi / LAMBDA * x
        a_true = ls_amp(v_true, t, f_v, sel)

        def asd(v):
            return asd_band(v, sel, FS, 4096, 3 * f_v, 30 * f_v)

        E1, EP, EL, G1, GL, SP = [], [], [], [], [], []
        for s in range(nseed):
            rng = np.random.default_rng(45_000 + int(vr * 100) + 13 * s)
            z = np.exp(1j * ph) + complex_bandlimited_noise(N, FS, B_front,
                                                            s2, rng)
            v_off = vdisc(z)
            v_pre = vdisc(complex_lp(z, B_loop1, FS))
            y1, _, _, _ = run_pll(z, FS, fn1, s2)
            yp, _, _, dgp = run_pll(z, FS, fnp, s2)
            E1.append(100 * (ls_amp(vdisc(y1), t, f_v, sel) / a_true - 1))
            EP.append(100 * (ls_amp(vdisc(yp), t, f_v, sel) / a_true - 1))
            EL.append(100 * (ls_amp(v_pre, t, f_v, sel) / a_true - 1))
            a_off = asd(v_off)
            G1.append(20 * math.log10(a_off / asd(vdisc(y1))))
            GL.append(20 * math.log10(a_off / asd(v_pre)))
            SP.append(dgp['near_pi_events'])
        r = dict(fD=fD, B_front=B_front, fn1=fn1, B_loop=B_loop1,
                 ceil=10 * math.log10(fD / B_loop1),
                 e1=stats(E1)[0], epi=stats(EP)[0], epre=stats(EL)[0],
                 g1=stats(G1)[0], gl=stats(GL)[0], sp=stats(SP)[0])
        res[vr] = r
        print(f"  {vr:6.2f}m {r['fD']/1e6:6.2f}M {r['B_front']/1e6:7.1f}M "
              f"{fn1/1e3:6.1f}k {B_loop1/1e3:6.1f}k {r['ceil']:+5.1f} | "
              f"{r['e1']:+7.1f}% {r['epi']:+8.1f}% {r['epre']:+9.1f}% | "
              f"{r['g1']:+7.2f} {r['gl']:+8.2f}")
    print("\n  解读 (o5 已证, 此处以本三档规则复核): e_crit=pi 是卷绕线 -- 在"
          "边界上设计必失败;\n  e_crit=1 是设计线 -- 幅值保持且拿到谱线增益。"
          "外差前端被量程强制到 2*f_D 宽,\n  固定 preLP 收窄到 B_loop 会让走动"
          "的载波出通带 -> 幅值崩溃; 这就是外差跟踪滤波\n  相对固定滤波的唯一"
          "结构性价值 (零差场景里固定 LP 反而够用, 见 homodyne V2/o4-E8)。")
    ok51 = all(abs(res[vr]['e1']) < 10 for vr in res)
    check('C51', 'e_crit=1 设计线: 全部量程 |幅值误差|<10% (o5: 最大 +5.8%)',
          ok51, ', '.join(f"{vr}:{res[vr]['e1']:+.1f}%" for vr in res))
    ok52 = all(res[vr]['epi'] < -30 for vr in res)
    check('C52', 'e_crit=pi 卷绕线: 全部量程幅值误差 <-30% -- 在失败边界上'
          '设计保证失败 (o5: -47..-96%)', ok52,
          ', '.join(f"{vr}:{res[vr]['epi']:+.0f}%" for vr in res))
    ok53 = all(res[vr]['g1'] > 3.0 for vr in res)
    check('C53', 'e_crit=1: PLL 谱线噪声增益 >+3dB 全量程 (o5: +7.8..+25.3)',
          ok53, ', '.join(f"{vr}:{res[vr]['g1']:+.1f}" for vr in res))
    ok61 = all(res[vr]['epre'] < -15 for vr in res) and \
        all(res[vr]['epre'] < -80 for vr in res if vr >= 0.2)
    check('C61', '固定 preLP(同 B_loop): 全量程 <-15%, v>=0.2 m/s <-80% 崩溃 '
          '(载波走出固定通带)', ok61,
          ', '.join(f"{vr}:{res[vr]['epre']:+.0f}%" for vr in res))
    check('C62', 'v=1.5 m/s: PLL |err|<10% 而 preLP <-80% -- 同噪声带宽下'
          '只有跟踪能保住信号 (外差大频偏场景)',
          abs(res[1.5]['e1']) < 10 and res[1.5]['epre'] < -80,
          f"PLL {res[1.5]['e1']:+.1f}% vs preLP {res[1.5]['epre']:+.1f}%")
    return res


# ================================================================== main
def main():
    t0 = time.time()
    print('外差电IQ (Polytec类) 跟踪滤波方案 -- 仿真验证 (H1-H6)')
    print(f'reference core: pll_carrier_regen 纯NCO (逐行移植, 未改动), '
          f'lambda={LAMBDA*1e9:.1f}nm, fs={FS/1e6:.0f}MS/s, '
          f'B_frontend={B_FRONTEND/1e6:.0f}MHz, f_dev_max={F_DEV_MAX/1e6:.1f}MHz,'
          f' zeta={ZETA}')
    H0()
    H1()
    H2()
    H3()
    H4()
    H56()
    print_header('ASSERTION SUMMARY')
    allok = True
    for cid, label, ok, detail in CHECKS:
        allok &= ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {cid}  {label}  ({detail})")
    print('\n' + ('ALL CHECKS PASSED' if allok else 'SOME CHECKS FAILED'))
    print(f'[elapsed {time.time()-t0:.1f} s]')
    return 0 if allok else 1


if __name__ == '__main__':
    raise SystemExit(main())
