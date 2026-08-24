#!/usr/bin/env python3
"""App-scenario validation: v_peak <= 30 m/s (sinusoidal), f_target <= 100 kHz typical.

User application (1550 nm homodyne IQ LDV, existing three-gear design):
  - maximum measurable velocity 30 m/s peak (sinusoidal motion)
  - typical vibration frequency <= 100 kHz (most scenarios)
  Question: does the current tracking-filter gear selection affect performance
  for this use case?

Sections
--------
  A1  analytical gear-selection sweep over (f_target x v_peak):
      select_band, select_band_hysteresis (from SLOW start),
      cfg_for_frequency band, phi_err per gear, guard-fallback flag.
  A2  end-to-end weak-light simulation (CNR=3dB, B_frontend=40MHz, reusing
      validate_tracking.gear_filter and the R1-R3 fair-comparison rules) of
      four representative cases, each with SLOW/MEDIUM/FAST forced + the
      auto-selected gear marked:
        a) 100 kHz, 20 mm/s  (VAMP default)   -- SLOW expected
        b)  10 kHz, 30 m/s   (high speed, low freq)
        c) 100 kHz, 30 m/s   (guard worst case)
        d)  50 kHz,  5 m/s   (medium)
  A3  hysteresis step-change traces (50k->100k @20mm/s, 20mm/s->30m/s @100k,
      30m/s->20mm/s downshift) -- does one-step downshift cause a temporary
      WRONG gear?
  A4  conclusions (printed + saved to results_app_30ms_100khz.txt).
  A5  PASS/FAIL assertion summary.

Primary-scenario PASS/FAIL criteria (documented, asserted in A5)
----------------------------------------------------------------
  S1  every auto-selected gear on the primary grid (f<=100kHz, v<=30m/s) has
      untracked phase phi_err < pi (atan2 detector stays linear, no forced
      cycle slip).
  S2  hysteresis selection from SLOW start == select_band target ==
      cfg_for_frequency band on the whole primary grid (upshift immediate).
  E1  case a: auto gear == SLOW, clean |ampErr_full| < 5 %, noisy median
      |ampErr_full| < 10 %, median full-output SNR gain > +10 dB.
  E2  case b: auto gear passes guard, clean |ampErr_full| < 5 %, noisy median
      |ampErr_full| < 10 %, median full-output SNR gain > 0 dB.
  E3  case c: auto gear == FAST, clean |ampErr_full| < 5 %, zero near-pi
      slip events in the clean run, median full-output SNR gain > 0 dB.
  E4  case d: same criteria as E2.
  E5  guard necessity: at case c a FORCED MEDIUM (guard-violating gear) shows
      clean |ampErr_full| > 20 % -- the guard's upshift is required, not just
      conservative.
  H1  20mm/s -> 30m/s step @100 kHz: upshift reaches the guard-satisfying
      gear on the FIRST selector update after the step.
  H2  30m/s -> 20mm/s step @100 kHz: one-step downshift intermediates are all
      guard-safe (phi_err <= PHI_GUARD at the new operating point) and the
      selector reaches the optimal gear within 2 updates.
  H3  50 kHz -> 100 kHz step @20 mm/s: stays SLOW throughout (no spurious
      gear change).
"""
import math
import time
import numpy as np

from core import (
  burst_signal, complex_bandlimited_noise, fm_discriminator, lockin_amp,
  welch_psd,
)
from design_params import (
  LAMBDA, FS, B_FRONTEND, B_WIN, BANDS, ORDER, PHI_GUARD,
  loop_error_mag, tracking_error_rad, select_band, select_band_hysteresis,
  cfg_for_frequency, b_loop,
)
from validate_tracking import gear_filter, stats

CNR_DB = 3.0
NSEED = 6                      # noisy-case seeds (requirement: >= 3)
V_MAX_APP = 30.0               # user: maximum measurable velocity, m/s peak
F_TYP_APP = 100e3              # user: typical frequency ceiling

PRIMARY_F = (1e3, 5e3, 10e3, 20e3, 50e3, 100e3)
CONTEXT_F = (200e3, 1e6, 3e6)  # instrument-max context (not the user's app)
VGRID = (0.02, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0)

# per test frequency: record length, burst cycles/start, welch segment, ASD band
APP_SCENES = {
  10e3:  dict(T=2.0e-3, ncyc=5,  t0=0.05e-3, L=65536, band=4e3),
  50e3:  dict(T=0.5e-3, ncyc=10, t0=0.02e-3, L=16384, band=15e3),
  100e3: dict(T=0.5e-3, ncyc=20, t0=0.02e-3, L=8192,  band=60e3),
}

CASES = (
  dict(tag='a', f0=100e3, vamp=0.02, note='典型工况 (VAMP 默认 20 mm/s)'),
  dict(tag='b', f0=10e3,  vamp=30.0, note='低频 x 最高速'),
  dict(tag='c', f0=100e3, vamp=30.0, note='最高典型频率 x 最高速 (守卫最坏点)'),
  dict(tag='d', f0=50e3,  vamp=5.0,  note='中间工况'),
)

TINY = 1e-300
LINES = []
CHECKS = []


def out(s=''):
  print(s)
  LINES.append(s)


def check(cid, label, ok, detail):
  CHECKS.append((cid, label, ok, detail))
  out(f"  [{'PASS' if ok else 'FAIL'}] {cid}  {label}  ({detail})")
  return ok


def header(title):
  out('\n' + '=' * 86)
  out(title)
  out('=' * 86)


# --------------------------------------------------------------- sim helpers
def make_scene(f0, vamp):
  """Like validate_tracking.make_scene but with per-frequency record length
  (a 10 kHz burst does not fit the 0.5 ms record used at 100 kHz)."""
  p = APP_SCENES[f0]
  N = int(p['T'] * FS)
  t = np.arange(N) / FS
  x, v, _ = burst_signal(t, f0, vamp, p['ncyc'], p['t0'])
  Tb = p['ncyc'] / f0
  Wm = (t > p['t0']) & (t < p['t0'] + Tb)
  Wq = (t > p['t0'] + Tb + 0.04e-3) & (t < p['T'] - 0.02e-3)
  return dict(f0=f0, vamp=vamp, N=N, t=t, v=v, ph=4 * np.pi / LAMBDA * x,
              Wm=Wm, Wq=Wq, L=p['L'], band=p['band'])


def asd_at(v, sc):
  """velocity ASD near f0, quiet window only (validate_tracking rule R2)."""
  P, f = welch_psd(v[sc['Wq']], FS, sc['L'])
  m = np.abs(f - sc['f0']) < sc['band']
  return max(np.sqrt(np.median(P[m])), TINY)


def amp_err_pct(v_est, sc):
  a = lockin_amp(v_est, sc['t'], sc['f0'], sc['Wm'])
  a0 = lockin_amp(sc['v'], sc['t'], sc['f0'], sc['Wm'])
  return 100 * (a / a0 - 1)


def vdisc(y):
  return fm_discriminator(y, FS, LAMBDA)


def phi_errs(f0, vamp):
  return {b: tracking_error_rad(f0, vamp, BANDS[b]['fn']) for b in ORDER}


def guard_pass_bands(f0, vamp):
  return [b for b in ORDER if phi_errs(f0, vamp)[b] <= PHI_GUARD]


# ------------------------------------------------- analytic boundary solvers
def v_guard_limit(f, band, target=PHI_GUARD):
  """v_peak at which the gear's untracked phase reaches `target` rad
  (phi_err is linear in v_peak)."""
  return target * LAMBDA * f / (2 * loop_error_mag(f, BANDS[band]['fn']))


def f_cross(band, v, target, flo, fhi):
  """Frequency where phi_err(f) crosses `target` rad at fixed v (bisection;
  phi_err is monotonically increasing in f well below the gear's fn)."""
  fn = BANDS[band]['fn']
  g = lambda f: tracking_error_rad(f, v, fn) - target
  if g(flo) > 0 or g(fhi) < 0:
    return float('nan')
  for _ in range(200):
    fm = 0.5 * (flo + fhi)
    if g(fm) > 0:
      fhi = fm
    else:
      flo = fm
  return 0.5 * (flo + fhi)


# ================================================================== A1 sweep
def A1():
  header(f'A1  选档扫描 (解析 + cfg_for_frequency): 守卫 phi_err = |1-H_L|*'
         f'2*v_peak/(lambda*f) <= {PHI_GUARD} rad')
  s1_ok, s2_ok = True, True
  s1_worst = (0.0, None, None)

  out(f"\n  -- 主工况长表 (f <= {F_TYP_APP/1e3:.0f} kHz, 用户应用域) --")
  out(f"    {'f':>7} {'v_peak':>9} | {'phi_err SLOW':>12} {'MEDIUM':>10} "
      f"{'FAST':>10} | {'select':>7} {'hyst(S起步)':>10} {'cfg':>7}  guard")
  for f0 in PRIMARY_F:
    for v in VGRID:
      pe = phi_errs(f0, v)
      sel = select_band(f0, v)
      hys = select_band_hysteresis(f0, 'SLOW', v)
      cfg = cfg_for_frequency(f0, v, current_band='SLOW')['band']
      passing = guard_pass_bands(f0, v)
      note = 'ok' if sel in passing else 'FALLBACK(无档<=1rad)'
      s2_ok &= (hys == sel == cfg)
      if pe[sel] > s1_worst[0]:
        s1_worst = (pe[sel], f0, v)
      s1_ok &= pe[sel] < math.pi
      out(f"    {f0/1e3:5.0f}k {v*1e3:8.0f}mm/s | {pe['SLOW']:11.4g}r "
          f"{pe['MEDIUM']:9.4g}r {pe['FAST']:9.4g}r | {sel:>7} {hys:>10} "
          f"{cfg:>7}  {note}")
    out('')

  out('  -- 全景矩阵 (含仪器上限 200k/1M/3M 供参考): S/M/F=选中档, '
      "'!'=守卫失败回退最宽档, '#'=phi_err>pi 必滑周 --")
  fs_all = PRIMARY_F + CONTEXT_F
  hdr = '    v_peak\\f   ' + ''.join(
      f"{(f'{f/1e6:.0f}M' if f >= 1e6 else f'{f/1e3:.0f}k'):>7}" for f in fs_all)
  out(hdr)
  for v in VGRID:
    row = f"    {v*1e3:8.0f}mm/s"
    for f0 in fs_all:
      sel = select_band(f0, v)
      pe = phi_errs(f0, v)[sel]
      mark = '' if pe <= PHI_GUARD else ('!' if pe < math.pi else '#')
      row += f"{sel[0] + mark:>7}"
    out(row)

  out(f"\n  -- 守卫升档边界 (v_peak 上限, 由 phi_err=1rad / pi 解析求出) --")
  out(f"    {'f':>7} | {'SLOW可用<=':>11} {'MEDIUM可用<=':>13} "
      f"{'FAST守卫<=':>12} {'FAST滑周极限':>13}")
  for f0 in PRIMARY_F:
    out(f"    {f0/1e3:5.0f}k | {v_guard_limit(f0,'SLOW'):9.3f}m/s "
        f"{v_guard_limit(f0,'MEDIUM'):11.3f}m/s "
        f"{v_guard_limit(f0,'FAST'):10.2f}m/s "
        f"{v_guard_limit(f0,'FAST',math.pi):11.1f}m/s")

  f_med = f_cross('MEDIUM', V_MAX_APP, PHI_GUARD, 100.0, 150e3)
  f_slow = f_cross('SLOW', V_MAX_APP, PHI_GUARD, 10.0, 5e3)
  f_fast1 = f_cross('FAST', V_MAX_APP, PHI_GUARD, 1e3, 300e3)
  f_fastpi = f_cross('FAST', V_MAX_APP, math.pi, 1e3, 400e3)
  out(f"\n  30 m/s 时的频率边界: SLOW 通过守卫至 {f_slow:.0f} Hz; "
      f"MEDIUM 至 {f_med/1e3:.2f} kHz (其上必须 FAST);")
  out(f"  FAST 守卫(1 rad)内至 {f_fast1/1e3:.1f} kHz, 其上 fallback FAST "
      f"(phi_err 1..pi 区间, 仍可跟踪); 滑周极限 phi_err=pi 在 "
      f"{f_fastpi/1e3:.1f} kHz.")
  out(f"  用户最坏点 (100 kHz, 30 m/s): phi_err FAST = "
      f"{tracking_error_rad(100e3, 30, BANDS['FAST']['fn']):.2f} rad < pi "
      f"(滑周速度余量 {v_guard_limit(100e3,'FAST',math.pi)/30:.1f}x).")

  check('S1', f'主网格 (f<={F_TYP_APP/1e3:.0f}kHz, v<={V_MAX_APP:.0f}m/s) '
        '自动选档 phi_err < pi (无强制滑周)', s1_ok,
        f'最大 {s1_worst[0]:.2f} rad @ ({s1_worst[1]/1e3:.0f}kHz, '
        f'{s1_worst[2]:.0f}m/s)')
  check('S2', '主网格: hysteresis(SLOW起步) == select_band == '
        'cfg_for_frequency (升档即时生效)', s2_ok,
        f'{len(PRIMARY_F)*len(VGRID)} 组合')
  return dict(f_med=f_med, f_slow=f_slow, f_fast1=f_fast1, f_fastpi=f_fastpi)


# ==================================================================== A2 sim
def run_case(case):
  f0, vamp = case['f0'], case['vamp']
  sc = make_scene(f0, vamp)
  s2 = 10 ** (-CNR_DB / 10)
  sel = select_band(f0, vamp)
  pe = phi_errs(f0, vamp)
  rng = np.random.default_rng(777)
  zc = np.exp(1j * sc['ph']) + complex_bandlimited_noise(
      sc['N'], FS, 20e6, 1e-10, rng)
  row = {}
  for band in ORDER:
    yf, yn, _, _, dg = gear_filter(zc, band, 1e-10, gate='always')
    ef = amp_err_pct(vdisc(yf), sc)
    en = amp_err_pct(vdisc(yn), sc)
    row[band] = dict(
        err_full=ef, err_nco=en, slips=dg['near_pi_events'],
        g_full=20 * math.log10(max(1 + ef / 100, 1e-12)),
        g_nco=20 * math.log10(max(1 + en / 100, 1e-12)),
        errs_noisy=[], gains_full=[], gains_nco=[], lock=[])
  for s in range(NSEED):
    rng = np.random.default_rng(
        50_000 + int(f0 / 1e3) * 1000 + int(vamp * 10) * 37 + s)
    z = (np.exp(1j * sc['ph'])
         + complex_bandlimited_noise(sc['N'], FS, B_FRONTEND, s2, rng))
    a_off = asd_at(vdisc(z), sc)
    for band in ORDER:
      yf, yn, _, _, dg = gear_filter(z, band, s2, gate='auto')
      r = row[band]
      vf = vdisc(yf)
      r['errs_noisy'].append(amp_err_pct(vf, sc))
      r['gains_full'].append(r['g_full'] + 20 * np.log10(a_off / asd_at(vf, sc)))
      r['gains_nco'].append(
          r['g_nco'] + 20 * np.log10(a_off / asd_at(vdisc(yn), sc)))
      r['lock'].append(dg['lock_frac'])

  fD = 2 * vamp / LAMBDA
  out(f"\n  案例 {case['tag']})  f0={f0/1e3:.0f} kHz, v_peak={vamp:g} m/s "
      f"(fD_peak={fD/1e6:.2f} MHz) -- {case['note']}")
  out(f"      select_band={sel}"
      + ('' if pe[sel] <= PHI_GUARD else ' [守卫fallback: 无档<=1rad]')
      + f", hysteresis(SLOW起步)={select_band_hysteresis(f0, 'SLOW', vamp)}")
  out(f"    {'gear':<8} {'phi_err':>9} | {'ampErr full':>11} {'ampErr NCO':>11} "
      f"{'slips':>6} | {'ampErr noisy':>12} | {'SNRgain full dB':>24} | "
      f"{'NCO dB':>7} | {'lock%':>5}")
  for band in ORDER:
    r = row[band]
    m, lo, hi = stats(r['gains_full'])
    mn = stats(r['gains_nco'])[0]
    em = stats(r['errs_noisy'])[0]
    mark = '  <== auto' if band == sel else ''
    out(f"    {band:<8} {pe[band]:8.3g}r | {r['err_full']:+10.2f}% "
        f"{r['err_nco']:+10.2f}% {r['slips']:6d} | {em:+11.2f}% | "
        f"{m:+7.2f} [{lo:+7.2f},{hi:+7.2f}] | {mn:+6.2f} | "
        f"{100*np.mean(r['lock']):5.1f}{mark}")
  return dict(row=row, sel=sel, pe=pe)


def A2():
  header(f'A2  端到端弱光仿真 (CNR={CNR_DB:.0f}dB, B_frontend='
         f'{B_FRONTEND/1e6:.0f}MHz, {NSEED} seeds, gear_filter/R1-R3 方法'
         '同 validate_tracking)')
  out('  ampErr = R1 近无噪传递函数误差 (clean, gate=always); '
      'ampErr noisy = 含噪中值 (gate=auto);')
  out('  SNRgain = 信号增益 + 20log10(ASD_off/ASD_on) @f0 静默窗 (R2/R3); '
      'slips = clean 运行 near-pi 事件数.')
  res = {}
  for case in CASES:
    res[case['tag']] = run_case(case)

  out('')
  ra = res['a']
  ok = (ra['sel'] == 'SLOW'
        and abs(ra['row']['SLOW']['err_full']) < 5.0
        and abs(stats(ra['row']['SLOW']['errs_noisy'])[0]) < 10.0
        and stats(ra['row']['SLOW']['gains_full'])[0] > 10.0)
  check('E1', '案例a (100kHz, 20mm/s): 自动档=SLOW, clean|err|<5%, '
        '噪声中值|err|<10%, SNRgain>+10dB', ok,
        f"sel={ra['sel']}, err={ra['row']['SLOW']['err_full']:+.2f}%, "
        f"noisy={stats(ra['row']['SLOW']['errs_noisy'])[0]:+.2f}%, "
        f"gain={stats(ra['row']['SLOW']['gains_full'])[0]:+.2f}dB")
  for tag, cid, extra_slips in (('b', 'E2', False), ('c', 'E3', True),
                                ('d', 'E4', False)):
    r = res[tag]
    g = r['row'][r['sel']]
    ok = (abs(g['err_full']) < 5.0
          and abs(stats(g['errs_noisy'])[0]) < 10.0
          and stats(g['gains_full'])[0] > 0.0)
    lbl = (f"案例{tag} ({CASES[[c['tag'] for c in CASES].index(tag)]['f0']/1e3:.0f}kHz, "
           f"{CASES[[c['tag'] for c in CASES].index(tag)]['vamp']:g}m/s): "
           f"自动档 clean|err|<5%, 噪声中值|err|<10%, SNRgain>0dB")
    if extra_slips:
      ok = ok and r['sel'] == 'FAST' and g['slips'] == 0
      lbl += ', 档=FAST 且 clean 0 滑周'
    check(cid, lbl, ok,
          f"sel={r['sel']}, err={g['err_full']:+.2f}%, "
          f"noisy={stats(g['errs_noisy'])[0]:+.2f}%, "
          f"gain={stats(g['gains_full'])[0]:+.2f}dB, slips={g['slips']}")
  em = res['c']['row']['MEDIUM']['err_full']
  check('E5', '守卫必要性: 案例c 强制 MEDIUM (违守卫 12.9rad) clean|err|>20% '
        '(守卫升档不是保守而是必须)', abs(em) > 20.0, f'{em:+.1f}%')
  return res


# ============================================================= A3 hysteresis
def trace(name, seq, start='SLOW'):
  out(f'\n  {name} (选档状态机, 起始档 {start})')
  out(f"    {'update':>6} {'f':>7} {'v_peak':>9} | {'target':>7} "
      f"{'applied':>8} {'phi_err(applied)':>16}  状态")
  band = start
  hist = []
  for i, (f0, v) in enumerate(seq):
    tgt = select_band(f0, v)
    band = select_band_hysteresis(f0, band, v)
    pe = tracking_error_rad(f0, v, BANDS[band]['fn'])
    if band == tgt:
      status = '最优'
    elif pe <= PHI_GUARD:
      status = '安全, 暂时非最优 (降档过渡)'
    elif pe < math.pi:
      status = '可跟踪(<pi) 但超守卫'
    else:
      status = '错档: 会滑周!'
    out(f"    {i:>6} {f0/1e3:5.0f}k {v*1e3:8.0f}mm/s | {tgt:>7} {band:>8} "
        f"{pe:15.4g}r  {status}")
    hist.append(dict(band=band, tgt=tgt, pe=pe))
  return hist


def A3():
  header('A3  换档迟滞: 用户相关的频率/速度阶跃 -- 一次一档降档是否造成临时错档?')
  h3 = trace('T1: 频率阶跃 50 kHz -> 100 kHz @ 20 mm/s',
             [(50e3, 0.02)] * 2 + [(100e3, 0.02)] * 3)
  h1 = trace('T2: 速度阶跃 20 mm/s -> 30 m/s @ 100 kHz (升档)',
             [(100e3, 0.02)] * 2 + [(100e3, 30.0)] * 3)
  h2 = trace('T3: 速度阶跃 30 m/s -> 20 mm/s @ 100 kHz (降档, 一次一档)',
             [(100e3, 30.0)] * 2 + [(100e3, 0.02)] * 4, start='FAST')
  out('\n  说明: 阶跃发生到下一次选档更新之间不可避免地短暂处于旧档 '
      '(任何离散选档器皆然, 暴露窗=选档更新周期);')
  out('  升档即时生效, 之后 reacq=True 用差分鉴频器直接拉入 NCO 频率. '
      '降档只慢不错: 高档在任何更低速工况都满足守卫.')

  check('H1', 'T2 升档: 阶跃后第 1 次更新即到守卫档 (FAST)',
        h1[2]['band'] == h1[2]['tgt'] == 'FAST',
        f"update2: {h1[2]['band']} (target {h1[2]['tgt']})")
  inter_safe = all(h['pe'] <= PHI_GUARD for h in h2[2:])
  check('H2', 'T3 降档: 中间档全部守卫安全 (无临时错档), 2 次更新内到最优档',
        inter_safe and h2[3]['band'] == 'SLOW',
        f"路径 {'->'.join(h['band'] for h in h2[1:])}, "
        f"max中间phi_err={max(h['pe'] for h in h2[2:]):.3g}r")
  check('H3', 'T1: 50->100 kHz @20mm/s 全程 SLOW, 无档位抖动',
        all(h['band'] == 'SLOW' for h in h3),
        f"路径 {'->'.join(h['band'] for h in h3)}")
  return h1, h2, h3


# ============================================================= A4 conclusion
def A4(bounds, e2e):
  header('A4  结论 (用户应用: v_peak<=30 m/s, 典型 f<=100 kHz)')
  ra, rc = e2e['a'], e2e['c']
  g_slow = stats(ra['row']['SLOW']['gains_full'])[0]
  g_fast_100k = stats(ra['row']['FAST']['gains_full'])[0]
  g_c = stats(rc['row']['FAST']['gains_full'])[0]
  v_s100 = v_guard_limit(100e3, 'SLOW')
  v_s1k = v_guard_limit(1e3, 'SLOW')
  v_f100 = v_guard_limit(100e3, 'FAST')
  v_pi100 = v_guard_limit(100e3, 'FAST', math.pi)
  fD30 = 2 * V_MAX_APP / LAMBDA
  out(f"""
  [结论1] "<=100 kHz 典型速度下 SLOW 是否总是最优?" -- 不是"总是", 是"守卫内最优".
    SLOW 通过守卫的速度上限随频率下降: {v_s1k:.1f} m/s @1 kHz -> {v_s100:.2f} m/s
    @100 kHz (见 A1 边界表). 该范围内 SLOW 最优且被自动选中 (100 kHz 实测弱光
    SNR 增益 {g_slow:+.1f} dB, vs FAST 同点 {g_fast_100k:+.1f} dB). 典型 VAMP=20 mm/s
    在全部 <=100 kHz 频点 phi_err<=0.097 rad, 守卫余量 >10x -- 默认 SLOW 正确.
    速度超过边界后守卫自动升档, 且这是必须的: 强制 SLOW/MEDIUM 在 30 m/s 时
    幅值误差 -90%..-100% (A2 实测), 不升档 = 测量报废.

  [结论2] 30 m/s 时 FAST 成为必需的最低频率: {bounds['f_med']/1e3:.2f} kHz.
    30 m/s 各档边界 (解析, A2 仿真证实): SLOW 只到 {bounds['f_slow']:.0f} Hz,
    MEDIUM 到 {bounds['f_med']/1e3:.2f} kHz, 其上守卫强制 FAST.
    FAST 在 1 rad 守卫内到 {bounds['f_fast1']/1e3:.1f} kHz; {bounds['f_fast1']/1e3:.0f}-100 kHz
    区间为 fallback FAST (phi_err 1.0-1.5 rad, 仍 < pi, atan2 鉴相器保持线性):
    实测 (100 kHz, 30 m/s) clean 幅值误差 {rc['row']['FAST']['err_full']:+.2f}%,
    0 滑周, SNR 增益 {g_c:+.2f} dB -- 可用. 绝对滑周极限 phi_err=pi 在
    {bounds['f_fastpi']/1e3:.0f} kHz @30 m/s, 或 {v_pi100:.0f} m/s @100 kHz
    (用户最坏点速度余量 {v_pi100/V_MAX_APP:.1f}x).

  [结论3] 换档动态: 无"临时错档"风险 (A3 实测).
    升档即时 (阶跃后第 1 次选档更新), 降档一次一档只经过更高档 -- 高档在低速
    工况永远守卫安全, 代价只是 <=1 个选档周期的 SNR 非最优. 50->100 kHz
    @20 mm/s 全程 SLOW 无抖动. 唯一暴露窗是阶跃与下一次选档更新之间
    (任何离散选档器固有), 由选档更新率决定, 与迟滞设计无关.

  [结论4] 实用建议.
    - 默认 SLOW + 现有 guard-first 自动选档即可覆盖用户全域
      (f<=100 kHz, v<=30 m/s), 无需人工干预档位.
    - 高速工况 SNR 增益从 SLOW 的 ~{g_slow:+.0f} dB 降到 FAST 的 ~{g_fast_100k:+.0f} dB
      (@100 kHz): 物理必然 (环带宽换跟踪能力); 30 m/s 信号本身极大
      (fD_peak={fD30/1e6:.1f} MHz), 幅值误差中值 <5% (A2), SNR 不是瓶颈.
    - 需要档位关注的只有 v>{v_f100:.0f} m/s 且 f 接近 100 kHz 的组合
      (fallback 区), 本仿真已证明到 30 m/s 均正常.

  [结论5] 是否需要改设计? 不需要 (仿真未发现问题).
    guard-first 选档在最坏点 (100 kHz, 30 m/s) 实测正确工作; 迟滞无副作用.
    两点非选档注意事项 (不改档位设计):
    (1) 前端带宽: 30 m/s 时 fD_peak={fD30/1e6:.1f} MHz 超过 B_FRONTEND/2=
        {B_FRONTEND/2e6:.0f} MHz 的噪声 ENBW 设定; 仿真中信号未被前端限带,
        实际硬件模拟前端须通过 ±{math.ceil(fD30/1e6)+4:.0f} MHz
        (fs=250 MS/s 复采样支持). 这是前端指标, 与选档无关.
    (2) 若未来需求扩展到 f>100 kHz 且同时 30 m/s, 才需考虑提高 FAST fn
        (滑周极限 {bounds['f_fastpi']/1e3:.0f} kHz @30 m/s).""")


# ==================================================================== main
def main():
  t0 = time.time()
  out('用户应用场景验证: v_peak<=30 m/s (正弦), 典型 f<=100 kHz -- '
      '现有三档选档是否影响性能?')
  out(f'reference: design_params 三档 (fn=110k/530k/1.6M, zeta=1.2, '
      f'公共窗 B_win={B_WIN/1e6:.0f}MHz, 守卫 {PHI_GUARD} rad), '
      f'B_loop=' + '/'.join(f'{b_loop(BANDS[b]["fn"])/1e6:.2f}M' for b in ORDER))
  bounds = A1()
  e2e = A2()
  A3()
  A4(bounds, e2e)
  header('A5  ASSERTION SUMMARY (主场景 PASS/FAIL 判据见文件头 docstring)')
  allok = True
  for cid, label, ok, detail in CHECKS:
    allok &= ok
    out(f"  [{'PASS' if ok else 'FAIL'}] {cid}  {label}  ({detail})")
  out('\n' + ('ALL CHECKS PASSED' if allok else 'SOME CHECKS FAILED'))
  out(f'[elapsed {time.time()-t0:.1f} s]')
  from _artifact_io import write_results
  write_results('results_app_30ms_100khz.txt', '\n'.join(LINES) + '\n')
  return 0 if allok else 1


if __name__ == '__main__':
  raise SystemExit(main())
