#!/usr/bin/env python3
"""V1-V4 validation of the three-gear (三档) homodyne IQ tracking filter.

Architecture under test (see design_params.py):
  carrier path   pll_carrier_regen (per-gear fn, zeta=1.2) -> y_nco = e^{j phi}
  measurement    residual window: r = z e^{-j phi}, rf = FIR_LP(r), where the
                 common FIR has its -6 dB cutoff at B_WIN=4MHz (flat <1 % to
                 ~3.6 MHz), y_full = e^{j phi} e^{j gs*angle(rf)}
                 (identical window in all gears)

Scenarios / printed PASS-FAIL criteria:
  V1  weak light CNR=3 dB (B_frontend=40 MHz), 100k/1M/3M sinusoidal velocity
      bursts, all three gears: SNR gain vs OFF and amplitude error.
        C1  FAST @3 MHz amplitude error < 3 %
        C2  FAST @3 MHz SNR gain > 0 dB at CNR=3 dB
        C3  SLOW @100 kHz SNR gain > 10 dB at CNR=3 dB
        C4  ALL gears @3 MHz amplitude error < 5 %
  V2  plain fixed complex LP (same B_loop / same B_WIN) vs the tracking gears
      over a Doppler-swing sweep -> the PLL value boundary.
        C6  static carrier: fixed LP ties the gear within 3 dB (PLL adds ~0)
        C7  fD > B_WIN: fixed LP collapses, FAST gear still < 10 % error
  V3  speckle dropout: velocity-spike suppression vs displacement error
      (honest report, no hard criterion).
  V4  gear selection by target frequency + tracking-error guard.
        C5  selector returns the expected gear on all cases

Methodology (from the reference t1_main.py, fair-comparison rules):
  R1  signal gain / amplitude error measured in a SEPARATE near-noiseless run
      (at CNR=3 dB a single 20 mm/s burst lock-in is noise-dominated);
  R2  noise ASD measured in a QUIET window (no burst present);
  R3  SNR gain = signal_gain_dB + 20*log10(ASD_off / ASD_on);
  R4  medians [p10, p90] over seeds.

NOTE the residual FIR window is applied group-delay-compensated ('same'
alignment); real-time hardware needs an NT_WIN/2-sample delay line on the
NCO path to match.
"""
import math
import time
import numpy as np

from core import (
  burst_signal, complex_bandlimited_noise, make_speckle,
  pll_carrier_regen, iir1_lowpass, fir_lp_same,
  fm_discriminator, lockin_amp, welch_psd,
)
from design_params import (
  LAMBDA, FS, B_FRONTEND, ZETA, B_WIN, NT_WIN, TAU_G, APP_V_PEAK_MAX,
  BANDS, ORDER, gate_params, b_loop, select_band, tracking_error_rad,
  cfg_for_frequency,
)

TINY = 1e-300
VAMP = 20e-3                     # default burst velocity amplitude
T = 5e-4
N = int(T * FS)
t = np.arange(N) / FS

# per test frequency: burst cycles, burst start, welch segment, ASD band
SCENES = {
  100e3: dict(ncyc=20, t0=0.02e-3, L=8192, band=60e3),
  1e6:   dict(ncyc=50, t0=0.05e-3, L=4096, band=150e3),
  3e6:   dict(ncyc=60, t0=0.05e-3, L=4096, band=150e3),
}


# ----------------------------------------------------------------- helpers
def fft_lp(x, fc, Nt):
  """Linear-phase FIR low-pass, group delay compensated ('same'), FFT conv.

  Thin wrapper over core.fir_lp_same -- the SAME design function used by
  core.residual_mode, so the validated window is the product window
  (review item #4; consistency asserted by validate_residual_alignment.py).
  """
  return fir_lp_same(x, fc, FS, Nt)


def gear_filter(z, band, Nhat, gate='auto'):
  """One gear: PLL carrier path + common residual measurement window."""
  gp = gate_params(band)
  y_nco, phi, st, dg = pll_carrier_regen(
      z, FS, BANDS[band]['fn'], Nhat, zeta=ZETA, gate=gate, **gp)
  rot = np.exp(-1j * phi)
  rf = fft_lp(z * rot, B_WIN, NT_WIN)
  if gate == 'always':
    gs = 1.0
  else:
    gs = iir1_lowpass((st == 2).astype(float), math.exp(-1.0 / (FS * TAU_G)))
  resph = np.where(np.abs(rf) > 1e-12, np.angle(rf), 0.0)
  y_full = np.conj(rot) * np.exp(1j * gs * resph)
  return y_full, y_nco, phi, st, dg


def make_scene(f0, vamp=VAMP):
  p = SCENES[f0]
  x, v, _ = burst_signal(t, f0, vamp, p['ncyc'], p['t0'])
  Tb = p['ncyc'] / f0
  Wm = (t > p['t0']) & (t < p['t0'] + Tb)
  Wq = (t > p['t0'] + Tb + 0.04e-3) & (t < 0.48e-3)
  return dict(f0=f0, vamp=vamp, x=x, v=v, ph=4 * np.pi / LAMBDA * x,
              Wm=Wm, Wq=Wq, L=p['L'], band=p['band'])


def asd_at(v, sc):
  """velocity ASD near f0, quiet window only (rule R2)."""
  P, f = welch_psd(v[sc['Wq']], FS, sc['L'])
  m = np.abs(f - sc['f0']) < sc['band']
  return max(np.sqrt(np.median(P[m])), TINY)


def clean_z(sc, seed=777):
  rng = np.random.default_rng(seed)
  return np.exp(1j * sc['ph']) + complex_bandlimited_noise(N, FS, 20e6, 1e-10, rng)


def amp_err_pct(v_est, sc):
  a = lockin_amp(v_est, t, sc['f0'], sc['Wm'])
  a0 = lockin_amp(sc['v'], t, sc['f0'], sc['Wm'])
  return 100 * (a / a0 - 1)


def vdisc(y):
  return fm_discriminator(y, FS, LAMBDA)


def stats(a):
  a = np.asarray([x for x in a if np.isfinite(x)])
  if a.size == 0:
    return (np.nan,) * 3
  s = np.sort(a)
  q = lambda p: s[max(0, min(s.size - 1, int(np.ceil(p / 100 * s.size)) - 1))]
  return float(np.median(s)), float(q(10)), float(q(90))


def print_header(title):
  print('\n' + '=' * 86)
  print(title)
  print('=' * 86)


CHECKS = []


def check(cid, label, ok, detail):
  CHECKS.append((cid, label, ok, detail))
  print(f"  [{'PASS' if ok else 'FAIL'}] {cid}  {label}  ({detail})")
  return ok


# ================================================================== V0 table
def v0_table():
  print_header(f'V0  三档参数表  (lambda=1550nm, fs=250MS/s, zeta={ZETA}, '
               f'B_win={B_WIN/1e6:.0f}MHz common window, B_frontend=40MHz)')
  print(f"  {'gear':<7} {'f_max':>7} {'fn':>7} {'B_loop':>8} {'ceil40':>8} "
        f"{'in-loop CNR@3dB':>16}   note")
  for name in ORDER:
    fn = BANDS[name]['fn']
    B = b_loop(fn)
    ceil = 10 * math.log10((B_FRONTEND / 2) / B)
    print(f"  {name:<7} {BANDS[name]['f_target_max']/1e3:6.0f}k {fn/1e3:6.0f}k "
          f"{B/1e6:7.2f}M {ceil:+7.1f}dB {3+ceil:15.1f}dB   {BANDS[name]['label']}")
  print(f"  公共测量窗 (三档相同): -6dB 截止 {B_WIN/1e6:.0f} MHz, "
        f"平坦(<1%误差)区 DC..~3.6 MHz "
        f"(window ENBW {2*0.975*B_WIN/1e6:.1f} MHz -> in-window CNR@3dB ~ "
        f"{3+10*math.log10(B_FRONTEND/(2*0.975*B_WIN)):.1f} dB)")


# ================================================================== V1
def V1(nseed=12, cnr_db=3.0):
  print_header(f'V1  弱光 CNR={cnr_db:.0f}dB, B_frontend={B_FRONTEND/1e6:.0f}MHz'
               f' -- 100k/1M/3M 正弦速度burst, 三档 x 三频  '
               f'({nseed} seeds, median [p10,p90])')
  s2 = 10 ** (-cnr_db / 10)
  res = {}
  for f0 in (100e3, 1e6, 3e6):
    sc = make_scene(f0)
    zc = clean_z(sc)
    row = {}
    for band in ORDER:
      yf, yn, _, _, _ = gear_filter(zc, band, 1e-10, gate='always')
      ef = amp_err_pct(vdisc(yf), sc)
      en = amp_err_pct(vdisc(yn), sc)
      row[band] = dict(
          err_full=ef, err_nco=en,
          g_full=20 * math.log10(max(1 + ef / 100, 1e-12)),
          g_nco=20 * math.log10(max(1 + en / 100, 1e-12)),
          gains_full=[], gains_nco=[], lock=[])
    for s in range(nseed):
      rng = np.random.default_rng(10_000 + int(f0 / 1e3) * 100 + s)
      z = np.exp(1j * sc['ph']) + complex_bandlimited_noise(N, FS, B_FRONTEND, s2, rng)
      a_off = asd_at(vdisc(z), sc)
      for band in ORDER:
        yf, yn, _, _, dg = gear_filter(z, band, s2, gate='auto')
        r = row[band]
        r['gains_full'].append(r['g_full'] + 20 * np.log10(a_off / asd_at(vdisc(yf), sc)))
        r['gains_nco'].append(r['g_nco'] + 20 * np.log10(a_off / asd_at(vdisc(yn), sc)))
        r['lock'].append(dg['lock_frac'])
    print(f"\n  f0 = {f0/1e3:.0f} kHz  (burst {SCENES[f0]['ncyc']} cyc, "
          f"vamp {VAMP*1e3:.0f} mm/s)")
    print(f"    {'gear':<7} {'fn':>6} | {'ampErr full':>11} {'ampErr NCO':>11} |"
          f" {'SNRgain full dB':>24} | {'SNRgain NCO dB':>16} | {'lock%':>6}")
    for band in ORDER:
      r = row[band]
      m, lo, hi = stats(r['gains_full'])
      mn, _, _ = stats(r['gains_nco'])
      print(f"    {band:<7} {BANDS[band]['fn']/1e3:5.0f}k | {r['err_full']:+10.2f}% "
            f"{r['err_nco']:+10.2f}% | {m:+7.2f} [{lo:+7.2f},{hi:+7.2f}] "
            f"| {mn:+15.2f} | {100*np.mean(r['lock']):5.1f}")
    res[f0] = row
  print("\n  (ampErr = R1 near-noiseless transfer; full = NCO+residual-window"
        " output, NCO = carrier path alone)")
  Bf = b_loop(BANDS['FAST']['fn'])
  print("  物理解释: 点击(click)清除发生在复域残差窗内, 要求载波环比窗慢"
        " (B_loop < B_win).\n  SLOW/MEDIUM (ζ=1.2 下 0.49M/2.34M) 满足, 故低频增益"
        "达到甚至超过窗的门限扩展;\n  FAST 档 B_loop="
        f"{Bf/1e6:.1f}M > {B_WIN/1e6:.0f}M, NCO 把部分点击跟进输出, 低频增益只剩"
        " ~+12dB (部分清除)\n  -- 所以低频目标必须用低档 (V4选档保证)."
        " ζ 的选择依据见 validate_zeta_sweep.py (审查项#7).")
  return res


# ================================================================== V2
def V2(nseed=8, cnr_db=3.0):
  Bp = b_loop(BANDS['SLOW']['fn'])
  print_header(f'V2  plain LP 对照 (同 B_loop={Bp/1e6:.2f}M / 同 B_win='
               f'{B_WIN/1e6:.0f}M 固定复数低通) vs 跟踪档 -- PLL价值边界\n'
               f'    100 kHz burst, 速度幅值扫描, CNR={cnr_db:.0f}dB, '
               f'B_frontend={B_FRONTEND/1e6:.0f}MHz ({nseed} seeds)')
  s2 = 10 ** (-cnr_db / 10)
  paths = [('LP-Bloop', None), ('LP-Bwin', None),
           ('SLOW', 'SLOW'), ('MEDIUM', 'MEDIUM'), ('FAST', 'FAST')]
  res = {}
  print(f"\n    {'vamp':>7} {'fD_peak':>8} | {'path':<9} {'ampErr clean':>12} "
        f"{'ampErr noisy':>12} | {'SNRgain@100k dB':>24}")
  for vamp in (0.02, 0.3, 1.0, 3.0, 6.0):
    sc = make_scene(100e3, vamp)
    fD = 2 * vamp / LAMBDA
    zc = clean_z(sc)
    row = {}
    for name, band in paths:
      if band is None:
        cut = Bp if name == 'LP-Bloop' else B_WIN
        vcl = vdisc(fft_lp(zc, cut, 2049 if name == 'LP-Bloop' else NT_WIN))
      else:
        yf, _, _, _, _ = gear_filter(zc, band, 1e-10, gate='always')
        vcl = vdisc(yf)
      e = amp_err_pct(vcl, sc)
      row[name] = dict(err_clean=e, g=20 * math.log10(max(1 + e / 100, 1e-12)),
                       errs=[], gains=[])
    for s in range(nseed):
      rng = np.random.default_rng(20_000 + int(vamp * 1000) + s)
      z = np.exp(1j * sc['ph']) + complex_bandlimited_noise(N, FS, B_FRONTEND, s2, rng)
      a_off = asd_at(vdisc(z), sc)
      for name, band in paths:
        if band is None:
          cut = Bp if name == 'LP-Bloop' else B_WIN
          v = vdisc(fft_lp(z, cut, 2049 if name == 'LP-Bloop' else NT_WIN))
        else:
          yf, _, _, _, _ = gear_filter(z, band, s2, gate='auto')
          v = vdisc(yf)
        row[name]['errs'].append(amp_err_pct(v, sc))
        row[name]['gains'].append(row[name]['g'] + 20 * np.log10(a_off / asd_at(v, sc)))
    for i, (name, _) in enumerate(paths):
      r = row[name]
      m, lo, hi = stats(r['gains'])
      em, _, _ = stats(r['errs'])
      head = (f"    {vamp*1e3:5.0f}mm/s {fD/1e6:7.2f}M |" if i == 0
              else f"    {'':>7} {'':>8} |")
      print(f"{head} {name:<9} {r['err_clean']:+11.1f}% {em:+11.1f}% "
            f"| {m:+7.2f} [{lo:+7.2f},{hi:+7.2f}]")
    res[vamp] = row
  print("\n    边界结论: 固定LP在 fD_peak 超出其通带后幅值崩溃; 跟踪档把边界推到"
        "环路失锁点\n    |1-H_L(f_v)|*phi_amp > pi (SLOW档先失效 -> 需升档, 见V4);"
        " 静止载波下固定LP与(正确选档的)跟踪档等价 -- 这就是PLL的价值边界.")
  sel = select_band(100e3, 0.02)          # the gear the selector actually picks
  g_lp = stats(res[0.02]['LP-Bwin']['gains'])[0]
  g_sel = stats(res[0.02][sel]['gains'])[0]
  check('C6', f'静止载波: 固定LP(B_win) 与选定档({sel}) SNR gain 差 < 3 dB '
        '(PLL无增值 -- 价值边界的诚实面)',
        abs(g_lp - g_sel) < 3.0, f'LP {g_lp:+.2f} dB vs {sel} {g_sel:+.2f} dB')
  e_lp = res[6.0]['LP-Bwin']['err_clean']
  e_lpn = stats(res[6.0]['LP-Bwin']['errs'])[0]
  e_fast = res[6.0]['FAST']['err_clean']
  e_fastn = stats(res[6.0]['FAST']['errs'])[0]
  check('C7', 'fD=7.7M > B_win: 固定LP严重超出5%预算(清洁<-15%) 而 FAST档 <5% '
        '(跟踪的价值面)',
        e_lp < -15 and abs(e_fast) < 5,
        f'LP-Bwin {e_lp:+.1f}% (含噪 {e_lpn:+.1f}%) vs '
        f'FAST {e_fast:+.1f}% (含噪 {e_fastn:+.1f}%)')
  return res


# ================================================================== V3
def V3(nseed=12, tau_sp=50e-6, Bf=20e6):
  band = select_band(3e6, VAMP)
  B_OUT, thr = 1e6, 20 * VAMP
  print_header(f'V3  散斑掉落 (tau_c={tau_sp*1e6:.0f}us, gear={band}, '
               f'B_frontend={Bf/1e6:.0f}MHz, 输出统一滤到 {B_OUT/1e6:.0f}MHz, '
               f'{nseed} seeds) -- 诚实报告')
  sc = make_scene(3e6)
  out = {}
  for cnr in (6, 12):
    s2 = 10 ** (-cnr / 10)
    acc = {k + tag: [] for k in ('sp', 'dr', 'sl') for tag in ('off', 'gof', 'gon')}
    lock = []
    for s in range(nseed):
      rng = np.random.default_rng(30_000 + cnr * 100 + s)
      h = make_speckle(N, FS, tau_sp, rng)
      z = h * np.exp(1j * sc['ph']) + complex_bandlimited_noise(N, FS, Bf, s2, rng)
      ph_ref = sc['ph'] + np.unwrap(np.angle(h))
      ph_ref -= ph_ref[0]
      xref_lp = fft_lp(LAMBDA / (4 * np.pi) * ph_ref, B_OUT, 2049)
      runs = {'off': (vdisc(z), np.unwrap(np.angle(z)))}
      for tag, gate in (('gof', 'always'), ('gon', 'auto')):
        yf, _, _, _, dg = gear_filter(z, band, s2, gate=gate)
        runs[tag] = (vdisc(yf), np.unwrap(np.angle(yf)))
        if gate == 'auto':
          lock.append(dg['lock_frac'])
      for tag, (v, ph) in runs.items():
        ph = ph - ph[0]
        vlp = fft_lp(v, B_OUT, 2049)
        ex = np.abs(vlp[sc['Wq']]) > thr
        acc['sp' + tag].append(
            int(np.sum(np.diff(np.concatenate(([False], ex)).astype(int)) == 1)))
        xh = fft_lp(LAMBDA / (4 * np.pi) * ph, B_OUT, 2049)
        e = xh - xref_lp
        acc['dr' + tag].append(1e9 * float(np.std(e - e.mean())))
        acc['sl' + tag].append(int(np.sum(np.abs(np.diff(ph - ph_ref)) > np.pi)))
    print(f"\n  mean CNR = {cnr} dB   (gate-on lock fraction "
          f"{100*np.mean(lock):.1f}%)")
    print(f"    {'metric':<30}{'OFF':>20}{'gear gate-off':>20}{'gear gate-on':>20}")
    for lbl, key in ((f'velocity spikes >{thr:.1f} m/s', 'sp'),
                     ('phase slips (2pi events)', 'sl'),
                     ('disp rms err (nm, in 1 MHz)', 'dr')):
      line = f"    {lbl:<30}"
      for tag in ('off', 'gof', 'gon'):
        m, lo, hi = stats(acc[key + tag])
        line += f"{m:8.0f} [{lo:4.0f},{hi:5.0f}]"
      print(line)
    out[cnr] = acc
  sp_off = stats(out[6]['spoff'])[0]
  sp_on = stats(out[6]['spgon'])[0]
  dr_off = stats(out[6]['droff'])[0]
  dr_on = stats(out[6]['drgon'])[0]
  worse = dr_on > dr_off
  ratio = dr_on / max(dr_off, 1e-9) if worse else dr_off / max(dr_on, 1e-9)
  print(f"\n  诚实结论: CNR=6dB 时 gate-on 把速度尖峰中值 {sp_off:.0f} -> {sp_on:.0f}"
        f" 个, 位移rms误差 {dr_off:.0f} -> {dr_on:.0f} nm"
        f" ({'恶化' if worse else '改善'} {ratio:.1f}x).")
  if worse:
    print("  本组实测: 尖峰抑制以位移精度为代价 -- 掉落期间NCO飞轮只能外推,"
          " 位移连续性无法承诺.")
  else:
    print("  本组实测: 尖峰抑制未付出位移精度代价 (位移误差持平或改善);"
          " 但掉落期间NCO飞轮只能外推, 位移连续性仍无法承诺.")
  return out


# ================================================================== V4
def V4(v1res, v2res):
  print_header('V4  档位切换: 按目标频率选档 + 跟踪误差守卫 (phi_err <= 1 rad)')
  cases = [(100e3, 0.02, 'SLOW'), (1e6, 0.02, 'SLOW'), (3e6, 0.02, 'SLOW'),
           (100e3, 1.0, 'MEDIUM'), (100e3, 6.0, 'FAST'), (3e6, 0.1, 'SLOW')]
  print(f"    {'f_target':>9} {'v_peak':>8} | "
        f"{'phi_err SLOW':>12} {'MEDIUM':>8} {'FAST':>8} | {'selected':>9} {'expect':>7}")
  ok = True
  for f0, vpk, exp in cases:
    sel = select_band(f0, vpk)
    errs = [tracking_error_rad(f0, vpk, BANDS[b]['fn']) for b in ORDER]
    ok &= (sel == exp)
    print(f"    {f0/1e3:7.0f}kHz {vpk*1e3:6.0f}mm/s | "
          f"{errs[0]:11.2f}r {errs[1]:7.2f}r {errs[2]:7.2f}r | {sel:>9} {exp:>7}"
          f"{'' if sel == exp else '   <-- MISMATCH'}")
  check('C5', '选档逻辑: 全部场景返回期望档位', ok,
        f'{len(cases)} cases, guard-pass narrowest gear')
  # V5 (审计: v_peak=None 错档): v_peak 未知时不再用频段规则 (100 kHz -> SLOW
  # 在 30 m/s 实际运动下幅值误差 ~-90%), 而按仪器最大速度 APP_V_PEAK_MAX
  # 保守评估守卫 -- cfg_for_frequency(100e3) 默认 v_peak 必须选 FAST 并上报
  # overrange (无档过守卫的 fallback 降级区).
  cfg_def = cfg_for_frequency(100e3)
  pe_def = tracking_error_rad(100e3, APP_V_PEAK_MAX,
                              BANDS[cfg_def['band']]['fn'])
  ok5 = (cfg_def['band'] == 'FAST'
         and select_band(100e3) == select_band(100e3, APP_V_PEAK_MAX) == 'FAST'
         and cfg_def['guard_ok'] is False and cfg_def['overrange'] is True
         and abs(cfg_def['phi_err'] - pe_def) < 1e-12)
  print(f"\n  v_peak 未知 (None) 的保守默认: 按 APP_V_PEAK_MAX="
        f"{APP_V_PEAK_MAX:.0f} m/s 评估守卫 -> cfg_for_frequency(100e3): "
        f"band={cfg_def['band']}, phi_err={cfg_def['phi_err']:.2f} rad, "
        f"overrange={cfg_def['overrange']} (频段规则已废除)")
  check('V5', 'v_peak 未知默认 APP_V_PEAK_MAX=30 m/s 保守守卫: '
        'cfg_for_frequency(100e3) 选 FAST 且 overrange=True (非频段规则)',
        ok5, f"band={cfg_def['band']}, phi_err={cfg_def['phi_err']:.2f}r, "
        f"guard_ok={cfg_def['guard_ok']}, overrange={cfg_def['overrange']}")
  g_s = stats(v1res[100e3]['SLOW']['gains_nco'])[0]
  g_f = stats(v1res[100e3]['FAST']['gains_nco'])[0]
  print(f"\n  为什么低频选低档: 载波路径(NCO) @100kHz 的弱光SNR增益 "
        f"SLOW {g_s:+.1f} dB vs FAST {g_f:+.1f} dB (V1实测)")
  e_s = v2res[6.0]['SLOW']['err_clean']
  e_f = v2res[6.0]['FAST']['err_clean']
  print(f"  为什么大动态升档: vamp=6 m/s @100kHz 时幅值误差 "
        f"SLOW {e_s:+.1f}% vs FAST {e_f:+.1f}% (V2实测)")
  print("  测量带宽在换档时不变 (公共4MHz残差窗), 换档只改变载波环动态 -- "
        "见V1: 三档3MHz幅值误差均合格.")


# ================================================================== main
def main():
  t0 = time.time()
  print('三档零差IQ跟踪滤波方案 -- 仿真验证 (V1-V4)')
  print(f'reference core: pll_carrier_regen / residual-window, '
        f'fs={FS/1e6:.0f}MS/s, lambda={LAMBDA*1e9:.0f}nm, T={T*1e3:.1f}ms/run')
  v0_table()
  v1 = V1()
  print('\n  -- V1 criteria --')
  c1 = abs(v1[3e6]['FAST']['err_full'])
  check('C1', 'FAST档 @3MHz 幅值误差 < 3%', c1 < 3.0, f'{c1:.2f}%')
  m2 = stats(v1[3e6]['FAST']['gains_full'])[0]
  check('C2', 'FAST档 @3MHz SNR gain > 0 dB (CNR=3dB)', m2 > 0.0, f'{m2:+.2f} dB')
  m3 = stats(v1[100e3]['SLOW']['gains_full'])[0]
  check('C3', 'SLOW档 @100kHz SNR gain > 10 dB (CNR=3dB, Bf=40MHz)',
        m3 > 10.0, f'{m3:+.2f} dB')
  worst = max(abs(v1[3e6][b]['err_full']) for b in ORDER)
  check('C4', '三档 @3MHz 幅值误差均 < 5%', worst < 5.0, f'worst {worst:.2f}%')
  v2 = V2()
  V3()
  V4(v1, v2)
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
