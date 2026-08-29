#!/usr/bin/env python3
"""Audit issue 2: FAST fn options at the guard-fallback point (100 kHz, 30 m/s).

At (100 kHz, 30 m/s) FAST (fn = 1.6 MHz) has phi_err = 1.50 rad > the
1 rad guard; select_band falls back to FAST (widest gear).  Two options:

  A) keep fn = 1.6 MHz, surface guard_ok=False / overrange=True through
     cfg_for_frequency (degraded-zone flag, implemented in design_params);
  B) raise FAST fn to ~2.1-2.2 MHz so the guard passes at 30 m/s / 100 kHz.

This study measures BOTH at the two points that matter:
  P1  case c (100 kHz, 30 m/s): clean/noisy amplitude error, true cycle
      slips vs truth, near-pi events (CNR = 3 dB, B_frontend = 40 MHz,
      same harness as validate_app A2);
  P2  the 3 MHz instrument spec point (20 mm/s, validate_tracking V1
      scene): clean amplitude error and weak-light SNR gain -- FAST's
      design point, guarded by validate_tracking C1/C2.

Decision criteria (from the audit): option B is adopted only if it is
BETTER at P1 AND does not break the 3 MHz cases.  Measured outcome
(results_fast_fn_options.txt): B does pass the guard and slightly improves
P1 noisy error, but costs ~2..3 dB of weak-light SNR at P2 (B_loop grows
4.42*fn -> further beyond B_WIN, worse click cleanup + higher in-loop
noise) while option A's P1 performance is already within spec (clean
error ~0, noisy median < 10 %, slips p95 <= 3 per 0.5 ms -- see
validate_app A8).  RECOMMENDATION: option A (keep fn = 1.6 MHz, flag the
degraded zone).  Assertions FN1-FN3 pin the measured basis of this
decision so a regression that changes it is caught.
"""
import math
import time
import numpy as np

from core import (
  complex_bandlimited_noise, pll_carrier_regen, iir1_lowpass, fir_lp_same,
  fm_discriminator,
)
from design_params import (
  LAMBDA, FS, B_FRONTEND, ZETA, B_WIN, NT_WIN, TAU_G, PHI_GUARD,
  gate_params, b_loop, tracking_error_rad,
)
from validate_tracking import (
  make_scene as vt_scene, clean_z, amp_err_pct as vt_err, asd_at as vt_asd,
)
from validate_app_30ms_100khz import (
  make_scene as app_scene, amp_err_pct as app_err, slips_vs_true,
)

FN_GRID = (1.60e6, 2.0e6, 2.1e6, 2.2e6)
NSEED = 6
CNR_DB = 3.0

LINES = []
CHECKS = []


def out(s=''):
  print(s)
  LINES.append(s)


def check(cid, label, ok, detail):
  CHECKS.append(ok)
  out(f"  [{'PASS' if ok else 'FAIL'}] {cid}  {label}  ({detail})")
  return ok


def gear_filter_fn(z, fn, Nhat, gate='auto'):
  """validate_tracking.gear_filter with fn override (FAST gate constants)."""
  gp = gate_params('FAST')
  y_nco, phi, st, dg = pll_carrier_regen(z, FS, fn, Nhat, zeta=ZETA,
                                         gate=gate, **gp)
  rot = np.exp(-1j * phi)
  rf = fir_lp_same(z * rot, B_WIN, FS, NT_WIN)
  if gate == 'always':
    gs = 1.0
  else:
    gs = iir1_lowpass((st == 2).astype(float), math.exp(-1.0 / (FS * TAU_G)))
  resph = np.where(np.abs(rf) > 1e-12, np.angle(rf), 0.0)
  return np.conj(rot) * np.exp(1j * gs * resph), dg


def vdisc(y):
  return fm_discriminator(y, FS, LAMBDA)


def main():
  t0 = time.time()
  out('审计项2: FAST fn 选项研究 -- (100 kHz, 30 m/s) 守卫回退点')
  out(f'  选项A: 保持 fn=1.6M + cfg 上报 guard_ok/overrange; '
      f'选项B: fn 提高到 2.1-2.2M 使守卫通过')
  out(f'  P1 = 案例c (100 kHz, 30 m/s, CNR={CNR_DB:.0f}dB, '
      f'B_frontend={B_FRONTEND/1e6:.0f}MHz); P2 = 3 MHz 规格点 (20 mm/s), '
      f'{NSEED} seeds')

  sc_c = app_scene(100e3, 30.0)
  sc_3m = vt_scene(3e6)
  zc_c = np.exp(1j * sc_c['ph']) + complex_bandlimited_noise(
      sc_c['N'], FS, 20e6, 1e-10, np.random.default_rng(777))
  zc_3m = clean_z(sc_3m)
  s2 = 10 ** (-CNR_DB / 10)

  out(f"\n  {'fn':>6} {'B_loop':>7} {'B_l/B_win':>9} {'phi_err(c)':>10} "
      f"{'guard':>5} | {'P1 clean':>9} {'P1噪中值':>9} {'滑周max':>7} "
      f"{'near_pi中值':>10} | {'P2 clean':>9} {'P2增益中值':>10}")
  res = {}
  for fn in FN_GRID:
    pe = tracking_error_rad(100e3, 30.0, fn)
    yf, dg = gear_filter_fn(zc_c, fn, 1e-10, gate='always')
    ec = app_err(vdisc(yf), sc_c)
    errs, nps, sls = [], [], []
    for s in range(NSEED):
      rng = np.random.default_rng(50_000 + 100 * 1000 + 300 * 37 + s)
      z = (np.exp(1j * sc_c['ph'])
           + complex_bandlimited_noise(sc_c['N'], FS, B_FRONTEND, s2, rng))
      yf, dg = gear_filter_fn(z, fn, s2, gate='auto')
      errs.append(app_err(vdisc(yf), sc_c))
      nps.append(dg['near_pi_events'])
      sls.append(slips_vs_true(yf, sc_c['ph']))
    yf, _ = gear_filter_fn(zc_3m, fn, 1e-10, gate='always')
    e3 = vt_err(vdisc(yf), sc_3m)
    g0 = 20 * math.log10(max(1 + e3 / 100, 1e-12))
    g3 = []
    for s in range(NSEED):
      rng = np.random.default_rng(10_000 + 3000 * 100 + s)
      z = np.exp(1j * sc_3m['ph']) + complex_bandlimited_noise(
          len(sc_3m['v']), FS, B_FRONTEND, s2, rng)
      a_off = vt_asd(vdisc(z), sc_3m)
      yf, _ = gear_filter_fn(z, fn, s2, gate='auto')
      g3.append(g0 + 20 * np.log10(a_off / vt_asd(vdisc(yf), sc_3m)))
    res[fn] = dict(pe=pe, ec=ec, err_med=float(np.median(errs)),
                   slip_max=max(sls), np_med=float(np.median(nps)),
                   e3=e3, g3_med=float(np.median(g3)))
    out(f"  {fn/1e6:5.2f}M {b_loop(fn)/1e6:6.2f}M {b_loop(fn)/B_WIN:9.2f} "
        f"{pe:9.3f}r {'OK' if pe <= PHI_GUARD else 'FAIL':>5} | "
        f"{ec:+8.2f}% {np.median(errs):+8.2f}% {max(sls):7d} "
        f"{np.median(nps):10.0f} | {e3:+8.2f}% {np.median(g3):+9.2f}dB")

  a, b = res[1.60e6], res[2.2e6]
  out(f"""
  结论 (实测):
  - 选项B (fn=2.1/2.2M) 确实通过守卫 (phi_err {res[2.1e6]['pe']:.2f}/"""
      f"""{b['pe']:.2f} rad ≤ 1) 且 P1 含噪误差略优 """
      f"""({b['err_med']:+.1f}% vs {a['err_med']:+.1f}%), 滑周 0;
  - 但 P2 (3 MHz 规格点, FAST 存在的理由) 弱光 SNR 增益损失 """
      f"""{a['g3_med']-b['g3_med']:.1f} dB ({a['g3_med']:+.2f} -> """
      f"""{b['g3_med']:+.2f} dB @ fn=2.2M): B_loop 从 """
      f"""{b_loop(1.6e6)/1e6:.1f}M 增到 {b_loop(2.2e6)/1e6:.1f}M, 进一步"""
      f"""超出 B_win={B_WIN/1e6:.0f}M (click 清除更差 + 环内噪声更大);
  - 选项A 在 P1 已满足产品判据 (clean {a['ec']:+.2f}%, 含噪中值 """
      f"""{a['err_med']:+.1f}% < 10%, 滑周 max {a['slip_max']} 每 0.5 ms 记录,"""
      f""" 50-seed 分位数见 validate_app A8).
  推荐: 选项A -- 保持 FAST fn=1.6M, 通过 cfg_for_frequency 的
  guard_ok=False/overrange=True 把 66-100 kHz × 高速降级区上报给产品.
  (若未来规格要求 f>100 kHz 同时 30 m/s, 再重开本研究: 滑周极限
  phi_err=pi 在 fn=1.6M 时为 215 kHz @30 m/s.)""")

  check('FN1', '选项B 守卫: fn=2.1/2.2M 在 (100kHz, 30m/s) phi_err ≤ 1 rad',
        res[2.1e6]['pe'] <= PHI_GUARD and b['pe'] <= PHI_GUARD,
        f"2.1M: {res[2.1e6]['pe']:.3f}r, 2.2M: {b['pe']:.3f}r")
  check('FN2', '选项B 代价: fn=2.2M 在 3 MHz 规格点损失 ≥ 2 dB 弱光 SNR 增益 '
        '(决策依据)', a['g3_med'] - b['g3_med'] >= 2.0,
        f"{a['g3_med']:+.2f} -> {b['g3_med']:+.2f} dB "
        f"(Δ={a['g3_med']-b['g3_med']:.2f} dB)")
  check('FN3', '选项A 可用性: fn=1.6M 在案例c clean |err|<5%, '
        '含噪中值 |err|<10% (含噪滑周分位数由 validate_app A8/N2 断言)',
        abs(a['ec']) < 5.0 and abs(a['err_med']) < 10.0,
        f"clean {a['ec']:+.2f}%, 含噪中值 {a['err_med']:+.2f}%, "
        f"含噪滑周max {a['slip_max']}")

  allok = all(CHECKS)
  out('\n' + ('ALL CHECKS PASSED' if allok else 'SOME CHECKS FAILED')
      + f'  ({sum(CHECKS)}/{len(CHECKS)})')
  out(f'[elapsed {time.time()-t0:.1f} s]')
  from _artifact_io import write_results
  write_results('results_fast_fn_options.txt', '\n'.join(LINES) + '\n')
  return 0 if allok else 1


if __name__ == '__main__':
  raise SystemExit(main())
