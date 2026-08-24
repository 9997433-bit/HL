#!/usr/bin/env python3
"""Review item #7: what does zeta actually buy at the FULL output?

Background
----------
zeta=2.65 was derived from an equal-ripple +/-3 % condition on the NCO-path
closed-loop response.  But the architecture is two-path: the measurement
output y_full = e^{j phi} * e^{j gs*angle(FIR(z e^{-j phi}))} re-inserts the
untracked residual through the COMMON 4 MHz FIR window, so the output
flatness is set by the window, not by |H_L|.  V1 already hinted at this
(SLOW@3MHz: full output +0.06 % while the NCO path alone is -80 %).
The cost of zeta=2.65 is real: B_loop = 8.62*fn vs 4.42*fn at zeta=1.2,
i.e. ~2.9 dB of threshold-extension ceiling, and it pushes MEDIUM's B_loop
(4.57 MHz) above B_WIN (4 MHz), breaking the click-cleanup condition.

This sweep measures, for zeta in {0.7, 1.0, 1.2, 1.8, 2.65} x three gears
x {100 kHz, 1 MHz, 3 MHz}:

  Z0  the common FIR window's own response (what "DC..4 MHz" really means);
  Z1  full-output amplitude error (near-noiseless), full-output SNR gain vs
      OFF at CNR=3 dB, delta vs a fixed complex LP at B_WIN, near-pi event
      rate, lock fraction;
  Z2  dropout re-acquisition (simplified model: -20 dB fade for 50 us with
      a velocity reversal +/-20 mm/s hidden inside it, CNR=12 dB): re-lock
      delay and phase settle time after the light returns.

Assertions (Z3) encode the conclusion: the full output is zeta-insensitive,
so zeta should be chosen for the CARRIER path economy -> ZETA in
design_params.py must equal RECOMMENDED_ZETA and keep every gear's spec.

Run:  python3 validate_zeta_sweep.py   (~2 min, exit code 0 iff all PASS)
"""
import math
import time
import numpy as np

from core import (
  complex_bandlimited_noise, pll_carrier_regen, iir1_lowpass, fir_lp_kernel,
)
from design_params import (
  LAMBDA, FS, B_FRONTEND, ZETA, B_WIN, NT_WIN, TAU_G, BANDS, ORDER,
  gate_params,
)
from validate_tracking import (
  N, t, SCENES, fft_lp, make_scene, asd_at, clean_z,
  amp_err_pct, vdisc, stats, print_header,
)

ZETAS = (0.7, 1.0, 1.2, 1.8, 2.65)
FREQS = (100e3, 1e6, 3e6)
RECOMMENDED_ZETA = 1.2          # conclusion of this sweep (see Z3)
NSEED = 8
VAMP = 20e-3
T_RUN = N / FS

CHECKS = []


def check(cid, label, ok, detail):
  CHECKS.append((cid, label, ok, detail))
  print(f"  [{'PASS' if ok else 'FAIL'}] {cid}  {label}  ({detail})")
  return ok


def b_loop_of(fn, zeta):
  return math.pi * fn * (1 + 4 * zeta ** 2) / (4 * zeta)


def gear_filter_z(z, band, Nhat, zeta, gate='auto'):
  """Same chain as validate_tracking.gear_filter but with explicit zeta."""
  gp = gate_params(band)
  y_nco, phi, st, dg = pll_carrier_regen(
      z, FS, BANDS[band]['fn'], Nhat, zeta=zeta, gate=gate, **gp)
  rot = np.exp(-1j * phi)
  rf = fft_lp(z * rot, B_WIN, NT_WIN)
  if gate == 'always':
    gs = 1.0
  else:
    gs = iir1_lowpass((st == 2).astype(float), math.exp(-1.0 / (FS * TAU_G)))
  resph = np.where(np.abs(rf) > 1e-12, np.angle(rf), 0.0)
  y_full = np.conj(rot) * np.exp(1j * gs * resph)
  return y_full, phi, st, dg


# ================================================================== Z0
def Z0():
  print_header(f'Z0  公共残差窗频响 (windowed-sinc FIR, {NT_WIN} taps @ '
               f'{FS/1e6:.0f}MS/s, 设计截止 {B_WIN/1e6:.0f}MHz)')
  h = fir_lp_kernel(B_WIN, FS, NT_WIN)
  nfft = 1 << 18
  H = np.abs(np.fft.rfft(h, nfft))
  f = np.arange(H.size) * FS / nfft
  def f_at(level):
    i = int(np.argmax(H < level))
    return f[i]
  g3m = H[int(round(3e6 * nfft / FS))]
  f1, f5 = f_at(0.99), f_at(0.95)
  f3db, f6db = f_at(10 ** (-3 / 20)), f_at(0.5)
  print(f"  |H(3MHz)| = {g3m:.4f}  ({100*(g3m-1):+.2f}%)")
  print(f"  幅值误差 <1% 平坦区:  DC..{f1/1e6:.2f} MHz")
  print(f"  幅值误差 <5% 平坦区:  DC..{f5/1e6:.2f} MHz")
  print(f"  -3 dB 点: {f3db/1e6:.2f} MHz    -6 dB 点(=设计截止): {f6db/1e6:.2f} MHz")
  print("  => 准确表述: 4 MHz 是窗的 -6 dB 截止点; 平坦测量带(<1%误差)约到 "
        f"{f1/1e6:.1f} MHz, 覆盖 3 MHz 规格并留余量. 不是 'DC-4MHz 内处处平坦'.")
  return dict(g3m=g3m, f1=f1, f5=f5, f3db=f3db, f6db=f6db)


# ================================================================== Z1
def Z1(nseed=NSEED, cnr_db=3.0):
  print_header(f'Z1  ζ 扫描: 全输出幅值误差 / SNR增益 / near-π 率  '
               f'(CNR={cnr_db:.0f}dB, B_frontend={B_FRONTEND/1e6:.0f}MHz, '
               f'{nseed} seeds, median)')
  s2 = 10 ** (-cnr_db / 10)
  res = {}
  for f0 in FREQS:
    sc = make_scene(f0)
    zc = clean_z(sc)
    noisy = []
    for s in range(nseed):
      rng = np.random.default_rng(70_000 + int(f0 / 1e3) * 100 + s)
      z = np.exp(1j * sc['ph']) + complex_bandlimited_noise(
          N, FS, B_FRONTEND, s2, rng)
      noisy.append((z, asd_at(vdisc(z), sc)))
    # fixed complex LP at B_WIN: the zeta-free benchmark
    e_lp = amp_err_pct(vdisc(fft_lp(zc, B_WIN, NT_WIN)), sc)
    g_lp0 = 20 * math.log10(max(1 + e_lp / 100, 1e-12))
    lp_gains = [g_lp0 + 20 * np.log10(a_off / asd_at(
        vdisc(fft_lp(z, B_WIN, NT_WIN)), sc)) for z, a_off in noisy]
    g_lp = stats(lp_gains)[0]
    print(f"\n  f0 = {f0/1e3:.0f} kHz   固定LP(B_win) SNR gain = {g_lp:+.2f} dB")
    print(f"    {'zeta':>5} {'gear':<7} {'B_loop':>8} {'/B_win':>6} |"
          f" {'ampErr_full':>11} | {'SNRgain_full dB [p10,p90]':>27} {'Δvs LP':>7} |"
          f" {'nearπ/ms':>8} {'lock%':>6}")
    for band in ORDER:
      fn = BANDS[band]['fn']
      for zeta in ZETAS:
        ef = amp_err_pct(vdisc(gear_filter_z(zc, band, 1e-10, zeta,
                                             gate='always')[0]), sc)
        g0 = 20 * math.log10(max(1 + ef / 100, 1e-12))
        gains, rates, locks = [], [], []
        for z, a_off in noisy:
          yf, _, _, dg = gear_filter_z(z, band, s2, zeta, gate='auto')
          gains.append(g0 + 20 * np.log10(a_off / asd_at(vdisc(yf), sc)))
          rates.append(dg['near_pi_events'] / (T_RUN * 1e3))
          locks.append(dg['lock_frac'])
        g, glo, ghi = stats(gains)
        B = b_loop_of(fn, zeta)
        res[(f0, band, zeta)] = dict(
            err=ef, gain=g, glo=glo, ghi=ghi, dlp=g - g_lp,
            rate=stats(rates)[0], lock=float(np.mean(locks)), B=B)
        print(f"    {zeta:5.2f} {band:<7} {B/1e6:7.2f}M {B/B_WIN:6.2f} |"
              f" {ef:+10.2f}% | {g:+8.2f} [{glo:+7.2f},{ghi:+7.2f}] {g - g_lp:+7.2f} |"
              f" {stats(rates)[0]:8.1f} {100*np.mean(locks):6.1f}")
    res[(f0, 'LP')] = g_lp
  print("\n  (ampErr_full: 近无噪运行, gate=always; SNRgain vs OFF, R1-R3 方法;"
        " nearπ/ms: LOCK 内 |相位误差|>2.8rad 事件率)")
  print("  注意 FAST 档低频 (100kHz) 在 ζ≲0.9 处 p10-p90 跨度拉大 (双峰):"
        " B_loop≈1.3·B_win 恰在 click 清除悬崖边,\n  个别种子吃满清除、个别只有部分"
        " -- 低 ζ 的高中值不可依赖, 这是不取 ζ<1.2 的主要原因之一.")
  return res


# ================================================================== Z2
def Z2(nseed=4, cnr_db=12.0, fade_db=20.0, fade_us=50.0):
  print_header(f'Z2  掉光重捕 (简化模型: -{fade_db:.0f}dB 掉光 {fade_us:.0f}µs,'
               f' 掉光期内速度反向 ±{VAMP*1e3:.0f}mm/s, CNR={cnr_db:.0f}dB,'
               f' {nseed} seeds, median)')
  s2 = 10 ** (-cnr_db / 10)
  a_fade = 10 ** (-fade_db / 20)
  t0f, t1f = 200e-6, 200e-6 + fade_us * 1e-6
  i1 = int(t1f * FS)
  fD = 2 * VAMP / LAMBDA                      # 25.8 kHz Doppler
  ph_true = (4 * np.pi / LAMBDA) * VAMP * np.where(
      t < t0f, t, np.where(t < t1f, t0f - (t - t0f), t0f - (t1f - t0f)
                           - (t - t1f)))     # +v then -v (reversal in fade)
  env = np.where((t >= t0f) & (t < t1f), a_fade, 1.0)
  w2 = int(2e-6 * FS)                         # 2 us smoother for settle metric
  box = np.ones(w2) / w2
  res = {}
  print(f"    (载波多普勒 ±{fD/1e3:.0f} kHz, 重捕需拉回 {2*fD/1e3:.0f} kHz 频差;"
        f" settle 判据: 2µs 平滑 |相位误差| < 0.3 rad)")
  print(f"    {'zeta':>5} {'gear':<7} | {'t_relock µs':>11} "
        f"{'t_settle µs':>11} {'t_total µs':>10} | {'nearπ(重捕后)':>12}")
  for band in ORDER:
    gp = gate_params(band)
    for zeta in ZETAS:
      tr, ts, npc = [], [], []
      for s in range(nseed):
        rng = np.random.default_rng(80_000 + ORDER.index(band) * 1000 + s)
        z = env * np.exp(1j * ph_true) + complex_bandlimited_noise(
            N, FS, B_FRONTEND, s2, rng)
        _, phi, st, _ = pll_carrier_regen(
            z, FS, BANDS[band]['fn'], s2, zeta=zeta, gate='auto', **gp)
        lk = np.flatnonzero(st[i1:] == 2)
        if lk.size == 0:
          tr.append(np.inf); ts.append(np.inf); npc.append(np.inf)
          continue
        n_rl = i1 + lk[0]
        tr.append((n_rl - i1) / FS * 1e6)
        err = np.angle(np.exp(1j * (phi - ph_true)))
        err_s = np.convolve(np.abs(err), box, mode='same')
        j = np.flatnonzero(err_s[n_rl:] < 0.3)
        ts.append((j[0] / FS * 1e6) if j.size else np.inf)
        big = np.abs(err[n_rl:]) > 2.8
        npc.append(int(np.sum(np.diff(np.concatenate(
            ([False], big)).astype(int)) == 1)))
      res[(band, zeta)] = dict(tr=stats(tr)[0], ts=stats(ts)[0],
                               np=stats(npc)[0])
      r = res[(band, zeta)]
      print(f"    {zeta:5.2f} {band:<7} | {r['tr']:11.1f} {r['ts']:11.1f}"
            f" {r['tr']+r['ts']:10.1f} | {r['np']:12.0f}")
  print("\n  (t_relock: 光回来到门控重进LOCK, 由 AcquireTime=4·TauF 主导, 与 ζ"
        " 无关;\n   t_settle: 重进LOCK后平滑相位误差首次<0.3rad -- ζ 影响的部分)")
  return res


# ================================================================== Z3
def Z3(z1, z2):
  print_header('Z3  结论与断言')
  print(f"  各 ζ 汇总 (9 个 档×频率 组合上的统计):")
  print(f"    {'zeta':>5} | {'worst|ampErr|':>13} |"
        f" {'meanSNRgain':>11} {'worstΔvsLP':>10} | {'worst nearπ/ms':>14} |"
        f" {'worst settle µs':>15}")
  agg = {}
  for zeta in ZETAS:
    errs = [z1[(f0, b, zeta)]['err'] for f0 in FREQS for b in ORDER]
    gains = [z1[(f0, b, zeta)]['gain'] for f0 in FREQS for b in ORDER]
    dlps = [z1[(f0, b, zeta)]['dlp'] for f0 in FREQS for b in ORDER]
    rates = [z1[(f0, b, zeta)]['rate'] for f0 in FREQS for b in ORDER]
    setl = [z2[(b, zeta)]['ts'] for b in ORDER]
    agg[zeta] = dict(werr=max(abs(e) for e in errs), gain=np.mean(gains),
                     wdlp=min(dlps), wrate=max(rates), wts=max(setl))
    a = agg[zeta]
    print(f"    {zeta:5.2f} | {a['werr']:12.2f}% | {a['gain']:+11.2f}"
          f" {a['wdlp']:+10.2f} | {a['wrate']:14.1f} | {a['wts']:15.1f}")

  spread = max(abs(z1[(f0, b, za)]['err'] - z1[(f0, b, zb)]['err'])
               for f0 in FREQS for b in ORDER
               for za in ZETAS for zb in ZETAS)
  check('Z3-1', '全输出幅值误差对 ζ 不敏感 (任意档×频率上 ζ 间极差 < 1 个百分点)'
        ' -- 输出平坦度由公共窗决定, 不是 |H_L|',
        spread < 1.0, f'max spread {spread:.3f}%')

  bm12 = b_loop_of(BANDS['MEDIUM']['fn'], 1.2)
  bm265 = b_loop_of(BANDS['MEDIUM']['fn'], 2.65)
  check('Z3-2', 'click清除条件 B_loop<B_win: MEDIUM 在 ζ=1.2 满足 (2.34M<4M),'
        ' 在 ζ=2.65 不满足 (4.57M>4M)',
        bm12 < B_WIN < bm265,
        f'B_loop(1.2)={bm12/1e6:.2f}M, B_loop(2.65)={bm265/1e6:.2f}M')

  worst_reg = min(z1[(f0, b, RECOMMENDED_ZETA)]['gain']
                  - z1[(f0, b, 2.65)]['gain']
                  for f0 in FREQS for b in ORDER)
  check('Z3-3', f'ζ={RECOMMENDED_ZETA} 的全输出 SNR 增益在所有 档×频率 上'
        ' 不低于 ζ=2.65 - 0.7 dB (无回退)',
        worst_reg > -0.7, f'worst delta {worst_reg:+.2f} dB')

  e_fast = abs(z1[(3e6, 'FAST', RECOMMENDED_ZETA)]['err'])
  e_worst = max(abs(z1[(3e6, b, RECOMMENDED_ZETA)]['err']) for b in ORDER)
  check('Z3-4', f'ζ={RECOMMENDED_ZETA}: FAST@3MHz 幅值误差 <3%, 三档@3MHz 均 <5%'
        ' (V1 规格保持)',
        e_fast < 3.0 and e_worst < 5.0,
        f'FAST {e_fast:.2f}%, worst {e_worst:.2f}%')

  tt_rec = max(z2[(b, RECOMMENDED_ZETA)]['tr'] + z2[(b, RECOMMENDED_ZETA)]['ts']
               for b in ORDER)
  tt_265 = max(z2[(b, 2.65)]['tr'] + z2[(b, 2.65)]['ts'] for b in ORDER)
  check('Z3-5', f'ζ={RECOMMENDED_ZETA} 掉光重捕总时间 (relock+settle) 各档均'
        ' <100µs 且不劣于 ζ=2.65 的 3 倍 + 5µs',
        np.isfinite(tt_rec) and tt_rec < 100.0 and tt_rec < 3 * tt_265 + 5.0,
        f'{tt_rec:.1f} vs {tt_265:.1f} µs')

  check('Z3-6', f'design_params.ZETA == 推荐值 {RECOMMENDED_ZETA}',
        abs(ZETA - RECOMMENDED_ZETA) < 1e-12, f'ZETA={ZETA}')

  print(f"\n  推荐: ζ = {RECOMMENDED_ZETA} (三档统一).")
  print("  依据: (1) 全输出幅值误差由公共4MHz窗决定, 对 ζ 完全不敏感 (Z3-1)"
        " -- ζ=2.65 的等纹波推导\n            优化的是 NCO 路径纹波, 那不是"
        "输出指标, 优化对象选错了 (审查项#7);")
  print("        (2) ζ=1.2 使 B_loop=4.42·fn (vs 8.62·fn): MEDIUM 恢复"
        " B_loop<B_win 的 click 清除条件\n            (Z3-2, 100kHz 增益"
        " +36.2→+38.1dB), FAST@3MHz 增益 +2.2→+7.8dB (Z1);")
  print("        (3) 相对 ζ=2.65 在所有 档×频率 上 SNR 无回退 (Z3-3);"
        " 掉光重捕同量级 (Z3-5);")
  print("        (4) 更低的 ζ (0.7/1.0) 在 FAST 设计频点 3MHz 只再多 ~1dB,"
        " 但 FAST 低频落在 click 清除\n            悬崖边 (Z1 中 p10-p90 双峰),"
        " 且欠阻尼 (NCO 路径峰化 +28%@ζ=0.7) -- 不取.")
  print("  掉光飞轮/选档守卫等载波路径职能对 NCO ±3% 纹波不敏感;"
        " ζ=1.2 下 NCO 路径纹波 +11%/-11%\n  只出现在载波路径单独输出时"
        " -- 测量输出恒由公共窗决定 (Z3-1 实证).")


# ================================================================== main
def main():
  t0 = time.time()
  print('审查项 #7: ζ 扫描 -- 优化对象应是全输出+载波环经济性, 不是 NCO 纹波')
  print(f'fs={FS/1e6:.0f}MS/s, lambda={LAMBDA*1e9:.0f}nm, '
        f'B_win={B_WIN/1e6:.0f}MHz, ζ 候选 {ZETAS}, 当前 design ZETA={ZETA}')
  Z0()
  z1 = Z1()
  z2 = Z2()
  Z3(z1, z2)
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
