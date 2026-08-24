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
  A6  front-end consistency study at the worst point (100 kHz, 30 m/s)
      [audit issue 1]: at 30 m/s fD_peak = 38.7 MHz exceeds the +/-20 MHz
      noise band of B_NOISE_ENBW = 40 MHz, so the A2 model (signal NOT
      front-end limited) is not physically representative there.  A6
      parameterizes B_frontend in {B_NOISE_ENBW, 2*F_SIGNAL_MAX, 100 MHz}
      = {40, 86, 100} MHz, applies an optional linear-phase front-end LPF
      (cutoff B/2) to signal+noise, and runs two noise policies: const
      total CNR = 3 dB (PSD drops as B grows) vs const PSD (total noise
      grows with B -> effective CNR < 3 dB).
      NOTE this is still a simulation model with an explicit B_frontend
      parameter and an ideal linear-phase LPF: real hardware must use the
      MEASURED I/Q frequency response and noise spectrum instead.
  A7  deep-fade re-acquisition at (100 kHz, 30 m/s) [audit issue 3]:
      -30 dB fade of 2/10/50 us at CNR 12/6/3 dB (physically consistent
      B_frontend = 2*F_SIGNAL_MAX = 86 MHz front end) -- relock time after
      light returns,
      post-recovery speed RMS, invalid-flag (non-LOCK) coverage of the
      fade, and the measured phase slip across the gap (product
      requirement: HOLD/ACQUIRE => invalid flag, NO displacement
      integration across the gap).
  A8  noisy near-pi / phase-integrity statistics at case c [audit issue 4]:
      50 seeds at CNR = 3 dB with the physically consistent front end
      (B_FE_A8 = 2*F_SIGNAL_MAX = 86 MHz noise band + linear-phase LPF on
      signal+noise, same model as A6 v2 / A7 -- the old harness generated
      40 MHz noise with NO front-end LPF, which is not a realizable front
      end at 30 m/s).  p50/p90/p95/p99 of (i) near-pi detector events,
      (ii) sudden 2pi jumps of unwrap(angle(y_full)) vs the true phase
      (renamed from "true cycle slips": adjacent-sample |diff|>pi only
      catches ABRUPT jumps and is NOT a displacement-continuity proof) and
      (iii) the net integer fringe error at record end (fringe_slip_vs_true,
      catches slow whole-cycle drift that (ii) cannot see); clean-run and
      noisy-run assertions are SEPARATE -- with noise at CNR = 3 dB near-pi
      events are NOT required to be zero, only bounded (documented limits).
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
      slip events in the CLEAN run, median full-output SNR gain > 0 dB, and
      cfg_for_frequency(100e3, 30.0) reports guard_ok=False AND
      overrange=True (audit issue 2, option A adopted: FAST fn stays
      1.6 MHz and the degraded zone is surfaced through the cfg dict; the
      fn=2.1-2.2 MHz alternative is measured and rejected in
      study_fast_fn_options.py -- it costs ~3 dB weak-light SNR at the
      3 MHz spec point).  Noisy near-pi/slip limits are in A8 (N2), NOT
      here.
  E4  case d: same criteria as E2.
  E5  guard necessity: at case c a FORCED MEDIUM (guard-violating gear) shows
      clean |ampErr_full| > 20 % -- the guard's upshift is required, not just
      conservative.
  G1  guard flags API: cases a/b/d report guard_ok=True, overrange=False,
      and cfg phi_err matches tracking_error_rad of the applied gear.
  H1  20mm/s -> 30m/s step @100 kHz: upshift reaches the guard-satisfying
      gear on the FIRST selector update after the step.
  H2  30m/s -> 20mm/s step @100 kHz: one-step downshift intermediates are all
      guard-safe (phi_err <= PHI_GUARD at the new operating point) and the
      selector reaches the optimal gear within 2 updates.
  H3  50 kHz -> 100 kHz step @20 mm/s: stays SLOW throughout (no spurious
      gear change).
  F1  physically consistent front end (B_frontend in {86, 100} MHz, total
      CNR = 3 dB, front-end LPF ON): noisy median |ampErr_full| < 10 % --
      the case-c conclusion survives a representative front-end model.
  F2  a REAL 40 MHz front end (LPF applied to the signal) cannot pass
      30 m/s: clean |ampErr_full| > 20 % -- hardware must widen the
      analog/digital front end to at least +/-F_SIGNAL_MAX = +/-43 MHz.
  F3  const-PSD widening (same noise PSD as the 40 MHz baseline) drops the
      effective CNR below 3 dB and noisy median |ampErr_full| > 20 % --
      CNR must be specified/measured AT the actual front-end bandwidth.
  D1  every fade run relocks after light returns, relock time <= 20 us
      (FAST acq_time = 4*tauF = 4 us + gate detection latency).
  D2  per (duration x CNR): median post-relock speed RMS error <= 1.5x the
      pre-fade value (recovery restores the pre-fade noise floor).
  D3  fades >= 10 us: every seed has >= 60 % of fade samples non-LOCK
      (invalid flag available to the product).  2 us fades are shorter
      than the gate detection constant (tauP = 1 us IIR + 0.25 us confirm)
      and are NOT reliably flagged -- reported, and the phase slip across
      the gap (measured 10^1..10^3 cycles at 30 m/s) makes displacement
      integration across ANY fade invalid regardless of flagging.
  N1  A8 clean reference run: zero near-pi events, zero sudden 2pi jumps
      and zero net fringe error (same as E3's clean criterion, re-measured
      in the A8 harness with the physical 86 MHz front end).
  N2  A8 noisy (50 seeds, CNR = 3 dB, B_FE_A8 = 86 MHz + LPF): p95(sudden
      2pi jumps) <= 3 and p99 <= 5 per 0.5 ms record; p95(|net fringe
      error|) <= 300 and p99 <= 400 -- the fringe drift (measured
      10^1..10^2 cycles, from ~10 us tracking-loss episodes at velocity
      peaks that keep the gate in LOCK) means displacement integration is
      INVALID in the overrange zone even though sudden jumps stay ~0;
      p95(near-pi events) <= 700 (noise-driven detector excursions,
      deterministic peak is already 1.5 rad); median |ampErr_full| < 10 %
      and p90 |ampErr_full| < 20 %.
      These are DOCUMENTED bounded limits, not zero-defect claims.
"""
import sys

# Windows consoles often run a legacy codepage (GBK, cp936, ...) that cannot
# encode every symbol below; never crash on print (audit issue 1).
if hasattr(sys.stdout, 'reconfigure'):
  try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
  except Exception:
    pass

import math
import time
import numpy as np

from core import (
  burst_signal, complex_bandlimited_noise, fir_lp_same, fm_discriminator,
  lockin_amp, welch_psd,
)
from design_params import (
  LAMBDA, FS, B_NOISE_ENBW, F_SIGNAL_MAX, B_WIN, BANDS, ORDER, PHI_GUARD,
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


def sudden_2pi_jumps_vs_true(y, ph_true):
  """Sudden 2pi jumps of unwrap(angle(y)) - ph_true between ADJACENT samples.

  Renamed from slips_vs_true (audit issue 2): a per-sample |diff| > pi test
  only catches ABRUPT jumps; a slowly accumulating whole-cycle drift never
  trips it, so this count alone is NOT a displacement-continuity proof --
  fringe_slip_vs_true() covers the net whole-cycle error.  The adjacent-
  sample test is valid because per-sample increments of both phases stay
  < pi (fD_peak = 38.7 MHz -> 0.97 rad/sample at fs = 250 MS/s; the full
  output's residual phase is limited by the 4 MHz window)."""
  ph = np.unwrap(np.angle(y))
  return int(np.sum(np.abs(np.diff(ph - ph_true)) > np.pi))


def fringe_slip_vs_true(y, ph_true, lam=LAMBDA):
  """Net integer fringe error at the end of the record (audit issue 2).

  Complements sudden_2pi_jumps_vs_true: catches the slow accumulating
  whole-cycle drift that adjacent-sample jump detection cannot see.  The
  end-of-record phase error unwrap(angle(y))[-1] - ph_true[-1] is converted
  to displacement (homodyne: ph = 4*pi/lam * x  =>  x_err = dphi*lam/(4*pi))
  and counted in integer fringes (1 fringe = lam/2 displacement = 2*pi of
  phase).  Robust here because the record ends in the post-burst quiet
  window (true phase at rest), so filter group delay contributes ~0 to the
  end-of-record error."""
  dphi_end = float(np.unwrap(np.angle(y))[-1] - ph_true[-1])
  x_err = dphi_end * lam / (4 * np.pi)
  return int(round(x_err / (lam / 2)))   # == round(dphi_end / (2*pi))


def pctile(a, p):
  """Empirical percentile with ceil indexing (same convention as stats())."""
  s = np.sort(np.asarray(a))
  return float(s[max(0, min(s.size - 1, int(np.ceil(p / 100 * s.size)) - 1))])


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
        errs_noisy=[], gains_full=[], gains_nco=[], lock=[],
        nps_noisy=[], slips_noisy=[])
  for s in range(NSEED):
    rng = np.random.default_rng(
        50_000 + int(f0 / 1e3) * 1000 + int(vamp * 10) * 37 + s)
    z = (np.exp(1j * sc['ph'])
         + complex_bandlimited_noise(sc['N'], FS, B_NOISE_ENBW, s2, rng))
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
      r['nps_noisy'].append(dg['near_pi_events'])
      if band == sel:
        r['slips_noisy'].append(sudden_2pi_jumps_vs_true(yf, sc['ph']))

  fD = 2 * vamp / LAMBDA
  out(f"\n  案例 {case['tag']})  f0={f0/1e3:.0f} kHz, v_peak={vamp:g} m/s "
      f"(fD_peak={fD/1e6:.2f} MHz) -- {case['note']}")
  out(f"      select_band={sel}"
      + ('' if pe[sel] <= PHI_GUARD else ' [守卫fallback: 无档<=1rad]')
      + f", hysteresis(SLOW起步)={select_band_hysteresis(f0, 'SLOW', vamp)}")
  out(f"    {'gear':<8} {'phi_err':>9} | {'ampErr full':>11} {'ampErr NCO':>11} "
      f"{'slips':>6} | {'ampErr noisy':>12} {'np噪中值':>7} | "
      f"{'SNRgain full dB':>24} | {'NCO dB':>7} | {'lock%':>5}")
  for band in ORDER:
    r = row[band]
    m, lo, hi = stats(r['gains_full'])
    mn = stats(r['gains_nco'])[0]
    em = stats(r['errs_noisy'])[0]
    mark = '  <== auto' if band == sel else ''
    out(f"    {band:<8} {pe[band]:8.3g}r | {r['err_full']:+10.2f}% "
        f"{r['err_nco']:+10.2f}% {r['slips']:6d} | {em:+11.2f}% "
        f"{np.median(r['nps_noisy']):7.0f} | "
        f"{m:+7.2f} [{lo:+7.2f},{hi:+7.2f}] | {mn:+6.2f} | "
        f"{100*np.mean(r['lock']):5.1f}{mark}")
  return dict(row=row, sel=sel, pe=pe)


def A2():
  header(f'A2  端到端弱光仿真 (CNR={CNR_DB:.0f}dB, 噪声带宽 B_NOISE_ENBW='
         f'{B_NOISE_ENBW/1e6:.0f}MHz, {NSEED} seeds, gear_filter/R1-R3 方法'
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
    cs = CASES[[c['tag'] for c in CASES].index(tag)]
    g = r['row'][r['sel']]
    ok = (abs(g['err_full']) < 5.0
          and abs(stats(g['errs_noisy'])[0]) < 10.0
          and stats(g['gains_full'])[0] > 0.0)
    lbl = (f"案例{tag} ({cs['f0']/1e3:.0f}kHz, {cs['vamp']:g}m/s): "
           f"自动档 clean|err|<5%, 噪声中值|err|<10%, SNRgain>0dB")
    detail = (f"sel={r['sel']}, err={g['err_full']:+.2f}%, "
              f"noisy={stats(g['errs_noisy'])[0]:+.2f}%, "
              f"gain={stats(g['gains_full'])[0]:+.2f}dB, slips={g['slips']}, "
              f"noisy slips max={max(g['slips_noisy'])}")
    if extra_slips:
      cfgc = cfg_for_frequency(cs['f0'], cs['vamp'], current_band='SLOW')
      ok = (ok and r['sel'] == 'FAST' and g['slips'] == 0
            and cfgc['guard_ok'] is False and cfgc['overrange'] is True)
      lbl += (', 档=FAST 且 clean 0 滑周, cfg guard_ok=False/overrange=True '
              '(审计项2, 选项A: 保持 fn=1.6M 并上报降级区)')
      detail += (f", guard_ok={cfgc['guard_ok']}, "
                 f"overrange={cfgc['overrange']}, "
                 f"cfg phi_err={cfgc['phi_err']:.3f}r (噪声滑周界限见 A8/N2)")
    check(cid, lbl, ok, detail)
  em = res['c']['row']['MEDIUM']['err_full']
  check('E5', '守卫必要性: 案例c 强制 MEDIUM (违守卫 12.9rad) clean|err|>20% '
        '(守卫升档不是保守而是必须)', abs(em) > 20.0, f'{em:+.1f}%')
  g1ok, g1det = True, []
  for cs in CASES:
    if cs['tag'] == 'c':
      continue
    cfg = cfg_for_frequency(cs['f0'], cs['vamp'], current_band='SLOW')
    pe_ref = tracking_error_rad(cs['f0'], cs['vamp'], BANDS[cfg['band']]['fn'])
    g1ok &= (cfg['guard_ok'] is True and cfg['overrange'] is False
             and abs(cfg['phi_err'] - pe_ref) < 1e-12)
    g1det.append(f"{cs['tag']}:{cfg['band']} {cfg['phi_err']:.3g}r")
  check('G1', '守卫标志 API: 案例a/b/d cfg guard_ok=True/overrange=False, '
        'phi_err 与解析一致 (审计项2)', g1ok, '; '.join(g1det))
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


# ========================================================== A6 front-end study
FE_NT = 1025    # front-end LPF model taps (linear phase, transition ~0.8 MHz)


def a6_variant(sc, B_fe, pw, lpf):
  """One front-end variant at case c (FAST gear): clean + NSEED noisy runs.

  lpf=True applies an ideal linear-phase LPF (cutoff B_fe/2) to
  signal+noise -- a MODEL of the front end with an explicit B_frontend
  parameter.  Real hardware must substitute the measured I/Q frequency
  response and noise spectrum.
  """
  def fe(z):
    return fir_lp_same(z, B_fe / 2, FS, FE_NT) if lpf else z

  zc = np.exp(1j * sc['ph']) + complex_bandlimited_noise(
      sc['N'], FS, 20e6, 1e-10, np.random.default_rng(777))
  yf, _, _, _, _ = gear_filter(fe(zc), 'FAST', 1e-10, gate='always')
  ec = amp_err_pct(vdisc(yf), sc)
  errs, locks, nps = [], [], []
  for s in range(NSEED):
    rng = np.random.default_rng(60_000 + int(B_fe / 1e6) * 97
                                + int(pw * 1000) * 3 + (13 if lpf else 0) + s)
    z = fe(np.exp(1j * sc['ph'])
           + complex_bandlimited_noise(sc['N'], FS, B_fe, pw, rng))
    yf, _, _, _, dg = gear_filter(z, 'FAST', pw, gate='auto')
    errs.append(amp_err_pct(vdisc(yf), sc))
    locks.append(dg['lock_frac'])
    nps.append(dg['near_pi_events'])
  return dict(err_clean=ec, errs=errs, lock=float(np.mean(locks)), nps=nps,
              cnr_eff=-10 * math.log10(pw))


def A6():
  fD = 2 * V_MAX_APP / LAMBDA
  header(f'A6  前端模型一致性 (审计项1): 30 m/s 时 fD_peak={fD/1e6:.1f} MHz > '
         f'B_NOISE_ENBW/2={B_NOISE_ENBW/2e6:.0f} MHz -- 参数化 B_frontend, '
         f'前端LPF作用于信号+噪声')
  out('  A2 现模型: 噪声限带 ±20 MHz, 信号不限带 -- 在 30 m/s 处信号大部分时间'
      '位于噪声带外, "CNR=3dB" 不代表真实前端.')
  out('  变体: 前端LPF = 线性相位 FIR (截止 B/2, 1025 taps, 理想模型 -- 实际硬件'
      '须用实测 I/Q 频响与噪声谱替代);')
  out('  噪声策略: 总CNR恒定 3dB (扩带时 PSD 下降) vs PSD恒定 (扩带时总噪声功率'
      '增大, 等效CNR<3dB).')
  sc = make_scene(100e3, V_MAX_APP)
  s2 = 10 ** (-CNR_DB / 10)
  B_sig = 2 * F_SIGNAL_MAX          # 86 MHz: two-sided band passing +/-43 MHz
  variants = (
    ('v0', B_NOISE_ENBW, s2, False, 'B40 噪声±20M 信号不限带 (A2 现模型, 对照)'),
    ('v1', B_NOISE_ENBW, s2, True, 'B40 + 前端LPF (真实 40 MHz 前端)'),
    ('v2', B_sig, s2, True, 'B86 总CNR=3dB + LPF (物理一致, 推荐指标)'),
    ('v3', 100e6, s2, True, 'B100 总CNR=3dB + LPF (物理一致)'),
    ('v4', B_sig, s2 * B_sig / B_NOISE_ENBW, True,
     'B86 PSD恒定 + LPF (同光功率, 前端更宽)'),
    ('v5', 100e6, s2 * 100e6 / B_NOISE_ENBW, True, 'B100 PSD恒定 + LPF'),
  )
  out(f"\n  案例c (100 kHz, 30 m/s), FAST 档, {NSEED} seeds:")
  out(f"    {'id':<3} {'变体':<38} {'CNR_eff':>8} | {'clean err':>10} "
      f"{'noisy err 中值':>13} {'lock%':>6} {'near_pi 中值':>11}")
  res = {}
  for vid, B, pw, lpf, label in variants:
    r = a6_variant(sc, B, pw, lpf)
    res[vid] = r
    out(f"    {vid:<3} {label:<38} {r['cnr_eff']:+7.1f}dB | "
        f"{r['err_clean']:+9.2f}% {np.median(r['errs']):+12.2f}% "
        f"{100*r['lock']:6.1f} {np.median(r['nps']):11.0f}")
  out('\n  解读: v0 (现模型) 与 v2/v3 (物理一致, 总CNR=3dB) 的含噪误差同量级 --'
      ' A2 的结论在代表性前端模型下成立;')
  out('  v1: 真实 40 MHz 前端把 30 m/s 信号削掉 (clean 已坏) -- 硬件前端必须'
      f' ≥ ±F_SIGNAL_MAX = ±{F_SIGNAL_MAX/1e6:.0f} MHz;')
  out('  v4/v5: 同光功率下扩带引入更多噪声, 等效 CNR 掉到 3dB 以下, 误差急剧'
      '恶化 -- CNR 指标必须在实际前端带宽上定义/实测.')
  ok = all(abs(np.median(res[v]['errs'])) < 10.0 for v in ('v2', 'v3'))
  check('F1', '物理一致前端 (B=86/100MHz, 总CNR=3dB, LPF on): FAST 含噪中值 '
        '|err| < 10% (案例c结论在代表性模型下成立)', ok,
        f"v2 {np.median(res['v2']['errs']):+.2f}%, "
        f"v3 {np.median(res['v3']['errs']):+.2f}%")
  check('F2', '真实 40 MHz 前端 (LPF 作用于信号) 无法通过 30 m/s: clean '
        f'|err| > 20% (前端须扩至 ≥ ±F_SIGNAL_MAX={F_SIGNAL_MAX/1e6:.0f}MHz)',
        abs(res['v1']['err_clean']) > 20.0,
        f"clean {res['v1']['err_clean']:+.2f}%, "
        f"noisy 中值 {np.median(res['v1']['errs']):+.2f}%")
  ok = all(res[v]['cnr_eff'] < CNR_DB - 0.2
           and abs(np.median(res[v]['errs'])) > 20.0 for v in ('v4', 'v5'))
  check('F3', 'PSD恒定扩带: 等效CNR < 3dB 且含噪中值 |err| > 20% '
        '(CNR 必须在实际前端带宽上定义/实测)', ok,
        f"v4 CNR{res['v4']['cnr_eff']:+.1f}dB "
        f"err{np.median(res['v4']['errs']):+.1f}%, "
        f"v5 CNR{res['v5']['cnr_eff']:+.1f}dB "
        f"err{np.median(res['v5']['errs']):+.1f}%")
  return res


# ====================================================== A7 fade re-acquisition
B_FE_A7 = 2 * F_SIGNAL_MAX   # physically consistent 86 MHz front end (A6 v2)
FADE_DB = -30.0           # deep-fade amplitude drop
NSEED_FADE = 4


def a7_run(dur, cnr_db, seed):
  """One fade run at (100 kHz, 30 m/s), FAST gear, gate='auto'."""
  f0, vpk = 100e3, V_MAX_APP
  T = 0.5e-3
  N = int(T * FS)
  t = np.arange(N) / FS
  x = vpk / (2 * np.pi * f0) * np.sin(2 * np.pi * f0 * t)
  v = vpk * np.cos(2 * np.pi * f0 * t)
  ph = 4 * np.pi / LAMBDA * x
  t_f = 0.15e-3           # fade start = velocity peak (+38.7 MHz Doppler)
  s2 = 10 ** (-cnr_db / 10)
  rng = np.random.default_rng(80_000 + int(dur * 1e6) * 91
                              + int(cnr_db) * 7 + seed)
  env = np.where((t >= t_f) & (t < t_f + dur), 10 ** (FADE_DB / 20), 1.0)
  z = env * np.exp(1j * ph) + complex_bandlimited_noise(N, FS, B_FE_A7, s2, rng)
  z = fir_lp_same(z, B_FE_A7 / 2, FS, FE_NT)
  yf, _, _, st, _ = gear_filter(z, 'FAST', s2, gate='auto')
  fw = (t >= t_f) & (t < t_f + dur)
  inv = float(np.mean(st[fw] != 2))
  after = np.where((t >= t_f + dur) & (st == 2))[0]
  rel = (t[after[0]] - (t_f + dur)) * 1e6 if after.size else float('inf')
  ve = vdisc(yf)
  Wpre = (t > 50e-6) & (t < t_f - 5e-6)
  Wpost = t > (t_f + dur + rel * 1e-6 + 20e-6) if np.isfinite(rel) else \
      np.zeros(N, bool)
  rms_pre = float(np.sqrt(np.mean((ve[Wpre] - v[Wpre]) ** 2)))
  rms_post = (float(np.sqrt(np.mean((ve[Wpost] - v[Wpost]) ** 2)))
              if Wpost.any() else float('inf'))
  dphi = np.unwrap(np.angle(yf)) - ph
  gap_cyc = (abs(float(dphi[Wpost].mean() - dphi[Wpre].mean())) / (2 * math.pi)
             if Wpost.any() else float('inf'))
  return dict(inv=inv, rel=rel, rms_pre=rms_pre, rms_post=rms_post,
              gap_cyc=gap_cyc)


def A7():
  header(f'A7  掉光重捕获 (审计项3): 30 m/s @ 100 kHz, 深衰落 {FADE_DB:.0f} dB, '
         f'时长 2/10/50 us, CNR 12/6/3 dB (B_frontend={B_FE_A7/1e6:.0f}MHz '
         f'物理一致前端, {NSEED_FADE} seeds)')
  out('  指标: invalid% = 衰落窗内非 LOCK 样本占比 (产品 invalid 标志的可用性); '
      'relock = 光恢复到重新 LOCK 的时间;')
  out('  rms_pre/post = 衰落前/重锁后+20us 的速度 RMS 误差; gap = 跨衰落相位'
      '滑移 (周). 衰落起点取速度峰值 (+38.7 MHz Doppler, 最坏).')
  out(f"\n    {'时长':>6} {'CNR':>5} | {'invalid%':>16} {'relock us':>16} "
      f"{'rms_pre m/s':>11} {'rms_post m/s':>12} {'post/pre':>8} "
      f"{'gap 周(中值)':>11}")
  d1_ok, d2_ok, d3_ok = True, True, True
  d1_worst, d2_worst = 0.0, 0.0
  gap_lo, gap_hi = float('inf'), 0.0
  inv_2us = []
  for dur in (2e-6, 10e-6, 50e-6):
    for cnr in (12, 6, 3):
      rr = [a7_run(dur, cnr, s) for s in range(NSEED_FADE)]
      inv = [r['inv'] for r in rr]
      rel = [r['rel'] for r in rr]
      ratio = np.median([r['rms_post'] for r in rr]) / \
          np.median([r['rms_pre'] for r in rr])
      gap = float(np.median([r['gap_cyc'] for r in rr]))
      gap_lo, gap_hi = min(gap_lo, gap), max(gap_hi, gap)
      out(f"    {dur*1e6:4.0f}us {cnr:3d}dB | "
          f"{' '.join(f'{100*i:3.0f}' for i in inv):>16} "
          f"{' '.join(f'{r:4.1f}' for r in rel):>16} "
          f"{np.median([r['rms_pre'] for r in rr]):11.2f} "
          f"{np.median([r['rms_post'] for r in rr]):12.2f} "
          f"{ratio:8.2f} {gap:11.0f}")
      d1_ok &= all(np.isfinite(r) and r <= 20.0 for r in rel)
      d1_worst = max(d1_worst, max(rel))
      d2_ok &= ratio <= 1.5
      d2_worst = max(d2_worst, ratio)
      if dur >= 10e-6:
        d3_ok &= all(i >= 0.6 for i in inv)
      else:
        inv_2us.extend(inv)
  out('\n  产品需求 (本仿真文档化, 不是完整产品状态机): HOLD/ACQUIRE 期间必须'
      '置 invalid 标志; 任何衰落间隙上禁止位移积分 --')
  out(f'  跨衰落相位滑移实测 {gap_lo:.0f}..{gap_hi:.0f} 周 (30 m/s 时 NCO 飞轮'
      '只能外推, 位移连续性无法承诺, 即使 2 us 衰落亦然);')
  out(f'  2 us 衰落短于门控检测常数 (tauP=1us IIR + 0.25us 确认), invalid 标志'
      f'覆盖率实测 {100*min(inv_2us):.0f}-{100*max(inv_2us):.0f}% -- 不可靠;'
      ' 若产品需要标记亚微秒级衰落, 须另加快速幅度监测通道.')
  check('D1', '全部 (时长×CNR×seed) 光恢复后重锁, relock ≤ 20 us',
        d1_ok, f'最大 {d1_worst:.1f} us (FAST acq_time=4us + 门控检测延迟)')
  check('D2', '重锁后速度 RMS 误差恢复: 每组中值 post ≤ 1.5× pre',
        d2_ok, f'最坏 post/pre = {d2_worst:.2f}')
  check('D3', '衰落 ≥ 10 us: 全部 seed invalid 覆盖率 ≥ 60% '
        '(HOLD/ACQUIRE => invalid 标志可用; 2 us 衰落仅报告不断言)',
        d3_ok, f'2us 覆盖率 {100*min(inv_2us):.0f}-{100*max(inv_2us):.0f}% '
        '(短于检测常数)')


# =================================================== A8 noisy slip statistics
NSEED_STATS = 50
B_FE_A8 = 2 * F_SIGNAL_MAX   # physically consistent 86 MHz front end
                             # (same model as A6 v2 / A7 -- audit issue 1)
# A8 metrics, old (B_NOISE_ENBW=40 MHz noise, NO front-end LPF) vs new
# (B_FE_A8=86 MHz noise + linear-phase LPF on signal+noise), 50 seeds:
#   sudden 2pi jumps: old p50/p90/p95/p99/max = 0/1/1/2/2
#                     new p50/p90/p95/p99/max = 0/1/1/1/1
#   |net fringe err|: old p50/p90/p95/p99/max = 38/80/102/170/170
#                     new p50/p90/p95/p99/max = 33/121/132/198/198
#   near_pi events:   old p95 = 452            new p95 = 515
#   |ampErr full| %:  old p50/p90 = 7.49/10.69 new p50/p90 = 4.79/8.59
# The fringe drift is NOT introduced by the front-end change (old model
# measures p95=102 as well) -- it was simply never measured before: brief
# (~10 us) tracking-loss episodes at the velocity peaks (gate stays LOCK,
# NCO phase continuous -> no adjacent-sample jump) accumulate 10^1..10^2
# whole cycles.  Displacement integration is therefore INVALID in the
# overrange zone; velocity/amplitude metrics stay valid (|err| p50 < 5%).
# Documented ceilings below keep headroom over the measured draw (sudden
# p95<=3/p99<=5, |fringe| p95<=300/p99<=400, near_pi p95<=700).


def A8():
  header(f'A8  案例c 含噪 near-pi / 相位完整性统计 (审计项4): {NSEED_STATS} '
         f'seeds, CNR={CNR_DB:.0f}dB, FAST 档, gate=auto, B_frontend='
         f'{B_FE_A8/1e6:.0f}MHz+前端LPF (物理一致前端, 同 A6 v2/A7)')
  out('  区分三种事件: near_pi = 鉴相器 |e|>2.8 rad 的噪声激励瞬时越界 (代理量, '
      '确定性峰值已达 1.5 rad);')
  out('  sudden_2pi_jumps = unwrap(angle(y_full)) 相对真实相位的相邻样本 >π '
      '突跳 (突发2π跳变, 原名"真滑周");')
  out('  fringe_slip = 记录末端净整周条纹误差 round(Δφ_end/2π) '
      '(慢累积整周漂移, 突跳检测不可见).')
  out('  诚实声明: 突发2π跳变=0 只排除突跳, 不构成位移连续性证明 -- 慢漂移由 '
      'fringe_slip 度量; clean 与含噪分开断言, 含噪下只要求有界.')
  sc = make_scene(100e3, V_MAX_APP)
  s2 = 10 ** (-CNR_DB / 10)

  def fe(z):
    """Front-end LPF on signal+noise, same model as A6 v2 / A7."""
    return fir_lp_same(z, B_FE_A8 / 2, FS, FE_NT)

  zc = fe(np.exp(1j * sc['ph']) + complex_bandlimited_noise(
      sc['N'], FS, 20e6, 1e-10, np.random.default_rng(777)))
  yf, _, _, _, dg = gear_filter(zc, 'FAST', 1e-10, gate='always')
  np_clean = dg['near_pi_events']
  sl_clean = sudden_2pi_jumps_vs_true(yf, sc['ph'])
  fr_clean = fringe_slip_vs_true(yf, sc['ph'], LAMBDA)
  nps, sls, frs, errs = [], [], [], []
  for s in range(NSEED_STATS):
    rng = np.random.default_rng(90_000 + s)
    z = fe(np.exp(1j * sc['ph'])
           + complex_bandlimited_noise(sc['N'], FS, B_FE_A8, s2, rng))
    yf, _, _, _, dg = gear_filter(z, 'FAST', s2, gate='auto')
    nps.append(dg['near_pi_events'])
    sls.append(sudden_2pi_jumps_vs_true(yf, sc['ph']))
    frs.append(fringe_slip_vs_true(yf, sc['ph'], LAMBDA))
    errs.append(amp_err_pct(vdisc(yf), sc))
  out(f"\n  clean 参考: near_pi={np_clean}, sudden_2pi_jumps={sl_clean}, "
      f"fringe_slip={fr_clean}")
  out(f"  含噪分位数 (每 0.5 ms 记录, {NSEED_STATS} seeds):")
  out(f"    {'量':<22} {'p50':>7} {'p90':>7} {'p95':>7} {'p99':>7} {'max':>7}")
  for name, a in (('near_pi 事件数', nps), ('突发2π跳变 sudden_2pi', sls),
                  ('|净条纹误差| fringe', np.abs(frs))):
    out(f"    {name:<22} {pctile(a, 50):7.0f} {pctile(a, 90):7.0f} "
        f"{pctile(a, 95):7.0f} {pctile(a, 99):7.0f} {max(a):7.0f}")
  out(f"    {'|ampErr full| %':<22} {pctile(np.abs(errs), 50):7.2f} "
      f"{pctile(np.abs(errs), 90):7.2f} {pctile(np.abs(errs), 95):7.2f} "
      f"{pctile(np.abs(errs), 99):7.2f} {max(np.abs(errs)):7.2f}")
  out('\n  文档化限值 (fallback 区 100 kHz/30 m/s, phi_err=1.5 rad, CNR=3dB, '
      'B=86MHz+LPF): 突发2π跳变 p95 ≤ 3 / p99 ≤ 5 每 0.5 ms;')
  out('  |净条纹误差| p95 ≤ 300 / p99 ≤ 400 (实测 10^1..10^2 周: 速度峰值处 '
      '~10 us 级短暂失跟踪 (门控仍 LOCK, NCO 相位连续, 无相邻样本突跳)')
  out('  累积整周漂移 -- 降级区 (overrange=True) 位移积分无效, 幅值/速度指标'
      '仍有效); near_pi 代理 p95 ≤ 700; 幅值误差中值 < 10% (与 E3 一致),')
  out('  p90 < 20%. 案例b (10 kHz, 30 m/s) phi_err=0.151 rad 守卫内, 其含噪'
      '突跳见 E2 detail (noisy slips max).')
  check('N1', 'A8 clean 参考: near_pi=0, 突发2π跳变=0, 净条纹误差=0 '
        '(与 E3 clean 判据一致, 物理一致前端下重测)',
        np_clean == 0 and sl_clean == 0 and fr_clean == 0,
        f'near_pi={np_clean}, sudden_2pi_jumps={sl_clean}, '
        f'fringe_slip={fr_clean}')
  ok = (pctile(sls, 95) <= 3 and pctile(sls, 99) <= 5
        and pctile(np.abs(frs), 95) <= 300 and pctile(np.abs(frs), 99) <= 400
        and pctile(nps, 95) <= 700
        and pctile(np.abs(errs), 50) < 10.0
        and pctile(np.abs(errs), 90) < 20.0)
  check('N2', f'含噪 {NSEED_STATS} seeds: 突发2π跳变 p95≤3/p99≤5, |净条纹误差| '
        'p95≤300/p99≤400 (位移积分在降级区无效, 见上), near_pi p95≤700, '
        '|err| p50<10%/p90<20% (有界文档化限值, 非零缺陷)', ok,
        f'sudden_2pi p95={pctile(sls, 95):.0f} p99={pctile(sls, 99):.0f} '
        f'max={max(sls)}, |fringe| p95={pctile(np.abs(frs), 95):.0f} '
        f'p99={pctile(np.abs(frs), 99):.0f} max={max(np.abs(frs))}, '
        f'near_pi p95={pctile(nps, 95):.0f}, '
        f'|err| p50={pctile(np.abs(errs), 50):.2f}% '
        f'p90={pctile(np.abs(errs), 90):.2f}%')


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
      (@100 kHz): 物理必然 (环带宽换跟踪能力). 注意: 高速度不增加回光功率;
      CNR 由表面回光决定, 30 m/s 与弱回光可同时存在 -- 本节高速结论均在
      CNR=3 dB 弱光下实测 (fD_peak={fD30/1e6:.1f} MHz, 幅值误差中值 <5%, A2),
      更弱回光时 FAST 的 SNR 余量收窄 (建议 CNR >= 6 dB, 见设计方案 §2).
    - 需要档位关注的只有 v>{v_f100:.0f} m/s 且 f 接近 100 kHz 的组合
      (fallback 区), 本仿真已证明到 30 m/s 均正常.

  [结论5] 是否需要改设计? 档位设计不需要; 有三点已实测/文档化的注意事项.
    guard-first 选档在最坏点 (100 kHz, 30 m/s) 实测正确工作; 迟滞无副作用.
    (1) 前端带宽 (A6 实测, 审计项1): 30 m/s 时 fD_peak={fD30/1e6:.1f} MHz 超过
        B_NOISE_ENBW/2={B_NOISE_ENBW/2e6:.0f} MHz; 真实 40 MHz 前端会削掉信号
        (A6 v1: clean 误差已 >20%), 硬件前端必须通过
        ±F_SIGNAL_MAX=±{F_SIGNAL_MAX/1e6:.0f} MHz (fs=250 MS/s 复采样支持), 且 CNR 指标
        必须在实际前端带宽上定义/实测 (A6 v4/v5: 同 PSD 扩带等效 CNR<3dB,
        误差 -39%/-47%). 物理一致模型下 (总CNR=3dB, B=86/100 MHz) 案例c 结论
        成立 (A6 v2/v3 中值误差 -3..-5%).
    (2) fallback 降级区 (审计项2, 选项A): 66-100 kHz × 高速组合超出 1 rad
        守卫 (最坏 1.5 rad < pi), cfg_for_frequency 现返回
        guard_ok=False/overrange=True 供产品上报; 保持 FAST fn=1.6M --
        提高到 2.1-2.2 MHz 虽可满足守卫但在 3 MHz 规格点损失 ~2..3 dB 弱光
        SNR (见 study_fast_fn_options.py). 含噪突发2π跳变有界 (A8 实测
        p95≤3 每 0.5 ms), 但净条纹漂移实测 10^1..10^2 周/0.5 ms (A8
        fringe_slip) -- 降级区位移积分无效, 幅值/速度指标仍有效, 产品须按
        overrange 上报. 若未来需求扩展到 f>100 kHz 且同时 30 m/s, 再评估
        提高 FAST fn (滑周极限 {bounds['f_fastpi']/1e3:.0f} kHz @30 m/s).
    (3) 掉光行为 (A7 实测, 审计项3): 光恢复后 ~5 us 重锁, 速度精度恢复;
        但跨衰落相位滑移 10^1..10^3 周 -- HOLD/ACQUIRE 期间必须置 invalid
        标志, 任何衰落间隙上禁止位移积分; 短于 ~2 us 的深衰落不能保证被门控
        标记 (检测常数限制).""")


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
  A6()
  A7()
  A8()
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
