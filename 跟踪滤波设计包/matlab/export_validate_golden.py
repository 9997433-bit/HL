#!/usr/bin/env python3
"""Run the Python homodyne validators and export golden metrics to .mat.

Writes matlab/golden/validate_<name>_py.mat for
    tracking, off_mode, zeta_sweep, residual_alignment, app_30ms_100khz
with the same field layout the corresponding MATLAB validator saves to
validate_<name>_mat.mat: check pass counts plus the key scalar metrics
(SNR gains, amplitude errors, selected bands, guard limits, ...), so that
matlab/compare_validate.m can report max relative errors pairwise.

Sections that keep their results in local variables of main() (off_mode,
residual_alignment, app A7/A8) are re-computed here with the exact same
seeds/criteria; sections with return values (tracking V1-V4, zeta Z0-Z2,
app A1/A2/A6) are called directly so the module CHECKS lists fill in the
same order as the validators' own main().

Run:  python3 matlab/export_validate_golden.py     (~2-3 min)
"""
import math
import os
import sys
import time

import numpy as np
from scipy.io import savemat

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(os.path.dirname(HERE), 'homodyne_tracking_design')
sys.path.insert(0, PKG)
GOLD = os.path.join(HERE, 'golden')
os.makedirs(GOLD, exist_ok=True)

# don't overwrite the tracked results_*.txt files while exporting
import _artifact_io
_artifact_io.write_results = lambda *a, **k: None

from design_params import (  # noqa: E402
  LAMBDA, FS, B_FRONTEND, B_WIN, NT_WIN, BANDS, ORDER, PHI_GUARD,
  b_loop, tracking_error_rad, select_band, cfg_for_frequency,
)

FREQS3 = (100e3, 1e6, 3e6)


def checks_ok(module):
  return np.array([1.0 if c[2] else 0.0 for c in module.CHECKS])


def save(name, oks, det, noisy):
  d = {'checks_ok': oks, 'checks_pass': float(oks.sum()),
       'checks_total': float(oks.size), 'noisy': noisy}
  if det:
    d['det'] = det
  path = os.path.join(GOLD, f'validate_{name}_py.mat')
  savemat(path, d, oned_as='row')
  print(f'[saved {path}]')


# ============================================================== tracking
def export_tracking():
  import validate_tracking as vt
  vt.CHECKS.clear()
  v1 = vt.V1()
  # V1 criteria exactly as validate_tracking.main()
  c1 = abs(v1[3e6]['FAST']['err_full'])
  vt.check('C1', 'FAST档 @3MHz 幅值误差 < 3%', c1 < 3.0, f'{c1:.2f}%')
  m2 = vt.stats(v1[3e6]['FAST']['gains_full'])[0]
  vt.check('C2', 'FAST档 @3MHz SNR gain > 0 dB (CNR=3dB)', m2 > 0.0,
           f'{m2:+.2f} dB')
  m3 = vt.stats(v1[100e3]['SLOW']['gains_full'])[0]
  vt.check('C3', 'SLOW档 @100kHz SNR gain > 10 dB (CNR=3dB, Bf=40MHz)',
           m3 > 10.0, f'{m3:+.2f} dB')
  worst = max(abs(v1[3e6][b]['err_full']) for b in ORDER)
  vt.check('C4', '三档 @3MHz 幅值误差均 < 5%', worst < 5.0, f'worst {worst:.2f}%')
  v2 = vt.V2()
  v3 = vt.V3()
  vt.V4(v1, v2)

  # ---- pack: freq x band ----
  def arr1(key):
    return np.array([[v1[f][b][key] for b in ORDER] for f in FREQS3])

  def stat1(key, idx):
    return np.array([[vt.stats(v1[f][b][key])[idx] for b in ORDER]
                     for f in FREQS3])

  nz = {
    'v1_err_full': arr1('err_full'), 'v1_err_nco': arr1('err_nco'),
    'v1_gain_full_med': stat1('gains_full', 0),
    'v1_gain_full_p10': stat1('gains_full', 1),
    'v1_gain_full_p90': stat1('gains_full', 2),
    'v1_gain_nco_med': stat1('gains_nco', 0),
    'v1_lock_mean': np.array([[np.mean(v1[f][b]['lock']) for b in ORDER]
                              for f in FREQS3]),
  }
  vamps = (0.02, 0.3, 1.0, 3.0, 6.0)
  paths = ('LP-Bloop', 'LP-Bwin', 'SLOW', 'MEDIUM', 'FAST')
  nz['v2_err_clean'] = np.array([[v2[v][p]['err_clean'] for p in paths]
                                 for v in vamps])
  nz['v2_err_noisy_med'] = np.array([[vt.stats(v2[v][p]['errs'])[0]
                                      for p in paths] for v in vamps])
  nz['v2_gain_med'] = np.array([[vt.stats(v2[v][p]['gains'])[0]
                                 for p in paths] for v in vamps])
  tags = ('off', 'gof', 'gon')
  for key, out_key in (('sp', 'v3_sp_med'), ('sl', 'v3_sl_med'),
                       ('dr', 'v3_dr_med')):
    nz[out_key] = np.array([[vt.stats(v3[cnr][key + tag])[0] for tag in tags]
                            for cnr in (6, 12)])

  cases = [(100e3, 0.02), (1e6, 0.02), (3e6, 0.02),
           (100e3, 1.0), (100e3, 6.0), (3e6, 0.1)]
  v4_sel = np.array([ORDER.index(select_band(f, v)) + 1 for f, v in cases],
                    float)
  v4_pe = np.array([[tracking_error_rad(f, v, BANDS[b]['fn']) for b in ORDER]
                    for f, v in cases])
  det = {'v4_sel': v4_sel, 'v4_phierr': v4_pe,
         'b_loop_bands': np.array([b_loop(BANDS[b]['fn']) for b in ORDER])}
  save('tracking', checks_ok(vt), det, nz)


# ============================================================== off_mode
def export_off_mode():
  import validate_off_mode as vo
  from validate_tracking import N, make_scene, clean_z, amp_err_pct, vdisc, \
      asd_at
  from core import tracking_filter, complex_bandlimited_noise
  vo.CHECKS.clear()
  vo.LINES.clear()
  vo.main()
  oks = np.array([1.0 if ok else 0.0 for ok in vo.CHECKS])

  # re-compute the three saved metrics with the exact seeds of main()
  sc = make_scene(100e3)
  zc = clean_z(sc)
  cfg_off = cfg_for_frequency(100e3, tracking_mode='off')
  y, _, _, _ = tracking_filter(zc, FS, cfg_off)
  o2 = amp_err_pct(vdisc(y), sc)
  s2 = 10 ** (-3.0 / 10)
  cfg_gof = cfg_for_frequency(100e3, gate_policy='always')
  gains = []
  for s in range(2):
    rng = np.random.default_rng(50_000 + s)
    z = np.exp(1j * sc['ph']) + complex_bandlimited_noise(N, FS, B_FRONTEND,
                                                          s2, rng)
    y_off, _, _, _ = tracking_filter(z, FS, cfg_off)
    y_pll, _, _, _ = tracking_filter(z, FS, cfg_gof, Nhat=s2)
    gains.append(20 * math.log10(asd_at(vdisc(y_off), sc)
                                 / asd_at(vdisc(y_pll), sc)))
  o3 = float(np.median(gains))
  cfg_lp = cfg_for_frequency(100e3, tracking_mode='fixed_lp')
  rng = np.random.default_rng(50_002)
  zn = np.exp(1j * sc['ph']) + complex_bandlimited_noise(N, FS, B_FRONTEND,
                                                         s2, rng)
  y_lpn, _, _, _ = tracking_filter(zn, FS, cfg_lp)
  y_offn, _, _, _ = tracking_filter(zn, FS, cfg_off)
  o6b = 20 * math.log10(asd_at(vdisc(y_offn), sc) / asd_at(vdisc(y_lpn), sc))
  save('off_mode', oks, None,
       {'o2_amp_err': o2, 'o3_gain_med': o3, 'o6b_gain': o6b})


# ============================================================== zeta_sweep
def export_zeta_sweep():
  import validate_zeta_sweep as vz
  vz.CHECKS.clear()
  z0 = vz.Z0()
  z1 = vz.Z1()
  z2 = vz.Z2()
  vz.Z3(z1, z2)
  ZETAS = vz.ZETAS

  def a1(key):
    return np.array([[[z1[(f, b, z)][key] for z in ZETAS] for b in ORDER]
                     for f in FREQS3])

  def a2(key):
    return np.array([[z2[(b, z)][key] for z in ZETAS] for b in ORDER])

  det = {'z0': np.array([z0['g3m'], z0['f1'], z0['f5'], z0['f3db'],
                         z0['f6db']])}
  nz = {'z1_err': a1('err'), 'z1_gain_med': a1('gain'), 'z1_dlp': a1('dlp'),
        'z1_rate_med': a1('rate'), 'z1_lock_mean': a1('lock'),
        'z1_g_lp': np.array([z1[(f, 'LP')] for f in FREQS3]),
        'z2_tr': a2('tr'), 'z2_ts': a2('ts'), 'z2_np': a2('np')}
  save('zeta_sweep', checks_ok(vz), det, nz)


# ====================================================== residual_alignment
def export_residual_alignment():
  from validate_tracking import N, gear_filter, make_scene, clean_z, \
      amp_err_pct, vdisc
  from validate_residual_alignment import core_path, TOL_PP, FREQS
  from core import complex_bandlimited_noise
  err_gear, err_core = [], []
  for tag, gate, cnr_db in (('near-noiseless / gate=always', 'always', None),
                            ('CNR=3dB noisy / gate=auto', 'auto', 3.0)):
    print(f'  [{tag}]')
    for band in ORDER:
      for f0 in FREQS:
        sc = make_scene(f0)
        if gate == 'always':
          z, Nhat = clean_z(sc), 1e-10
        else:
          s2 = 10 ** (-cnr_db / 10)
          rng = np.random.default_rng(40_000 + int(f0 / 1e3))
          z = (np.exp(1j * sc['ph'])
               + complex_bandlimited_noise(N, FS, B_FRONTEND, s2, rng))
          Nhat = s2
        yg, _, _, _, _ = gear_filter(z, band, Nhat, gate=gate)
        yc = core_path(z, band, Nhat, gate)
        err_gear.append(amp_err_pct(vdisc(yg), sc))
        err_core.append(amp_err_pct(vdisc(yc), sc))
  err_gear = np.array(err_gear)
  err_core = np.array(err_core)
  adiff = np.abs(err_gear - err_core)
  oks = (adiff < TOL_PP).astype(float)
  save('residual_alignment', oks, None,
       {'err_gear': err_gear, 'err_core': err_core, 'adiff': adiff})


# ====================================================== app_30ms_100khz
def export_app():
  import validate_app_30ms_100khz as va
  from core import complex_bandlimited_noise
  va.CHECKS.clear()
  va.LINES.clear()
  bounds = va.A1()
  e2e = va.A2()
  va.A3()
  a6 = va.A6()
  va.A7()
  va.A8()
  oks = checks_ok(va)

  # ---- A1 deterministic grids ----
  nf, nv = len(va.PRIMARY_F), len(va.VGRID)
  pe_grid = np.zeros((nf, nv, 3))
  sel_grid = np.zeros((nf, nv))
  s1_worst = 0.0
  for i, f0 in enumerate(va.PRIMARY_F):
    for j, v in enumerate(va.VGRID):
      pe = va.phi_errs(f0, v)
      pe_grid[i, j, :] = [pe[b] for b in ORDER]
      sel = select_band(f0, v)
      sel_grid[i, j] = ORDER.index(sel) + 1
      s1_worst = max(s1_worst, pe[sel])
  vgl = np.array([[va.v_guard_limit(f, 'SLOW'), va.v_guard_limit(f, 'MEDIUM'),
                   va.v_guard_limit(f, 'FAST'),
                   va.v_guard_limit(f, 'FAST', math.pi)]
                  for f in va.PRIMARY_F])
  det = {'a1_pe': pe_grid, 'a1_sel': sel_grid, 'a1_vgl': vgl,
         'a1_bounds': np.array([bounds['f_slow'], bounds['f_med'],
                                bounds['f_fast1'], bounds['f_fastpi']]),
         'a1_s1_worst': s1_worst}

  # ---- A2: cases x bands ----
  tags = ('a', 'b', 'c', 'd')

  def a2arr(fn):
    return np.array([[fn(e2e[t]['row'][b]) for b in ORDER] for t in tags])

  nz = {
    'a2_err_full': a2arr(lambda r: r['err_full']),
    'a2_err_nco': a2arr(lambda r: r['err_nco']),
    'a2_slips_clean': a2arr(lambda r: r['slips']),
    'a2_err_noisy_med': a2arr(lambda r: va.stats(r['errs_noisy'])[0]),
    'a2_gain_full_med': a2arr(lambda r: va.stats(r['gains_full'])[0]),
    'a2_gain_nco_med': a2arr(lambda r: va.stats(r['gains_nco'])[0]),
    'a2_lock_mean': a2arr(lambda r: float(np.mean(r['lock']))),
    'a2_np_med': a2arr(lambda r: float(np.median(r['nps_noisy']))),
    'a2_slips_noisy_max': np.array(
        [max(e2e[t]['row'][e2e[t]['sel']]['slips_noisy']) for t in tags],
        float),
  }
  det['a2_sel'] = np.array([ORDER.index(e2e[t]['sel']) + 1 for t in tags],
                           float)
  det['a2_pe'] = np.array([[e2e[t]['pe'][b] for b in ORDER] for t in tags])

  # ---- A6: variants v0..v5 ----
  vids = ('v0', 'v1', 'v2', 'v3', 'v4', 'v5')
  nz['a6_err_clean'] = np.array([a6[v]['err_clean'] for v in vids])
  nz['a6_err_med'] = np.array([float(np.median(a6[v]['errs'])) for v in vids])
  nz['a6_lock'] = np.array([a6[v]['lock'] for v in vids])
  nz['a6_np_med'] = np.array([float(np.median(a6[v]['nps'])) for v in vids])

  # ---- A7: re-run the fade grid (A7() keeps results local) ----
  rel_med, ratio, gap_med, inv_med = [], [], [], []
  for dur in (2e-6, 10e-6, 50e-6):
    for cnr in (12, 6, 3):
      rr = [va.a7_run(dur, cnr, s) for s in range(va.NSEED_FADE)]
      rel_med.append(float(np.median([r['rel'] for r in rr])))
      ratio.append(float(np.median([r['rms_post'] for r in rr])
                         / np.median([r['rms_pre'] for r in rr])))
      gap_med.append(float(np.median([r['gap_cyc'] for r in rr])))
      inv_med.append(float(np.median([r['inv'] for r in rr])))
  nz['a7_rel_med'] = np.array(rel_med)
  nz['a7_ratio'] = np.array(ratio)
  nz['a7_gap_med'] = np.array(gap_med)
  nz['a7_inv_med'] = np.array(inv_med)

  # ---- A8: re-run the 50-seed statistics (A8() keeps results local) ----
  sc = va.make_scene(100e3, va.V_MAX_APP)
  s2 = 10 ** (-va.CNR_DB / 10)
  zc = np.exp(1j * sc['ph']) + complex_bandlimited_noise(
      sc['N'], FS, 20e6, 1e-10, np.random.default_rng(777))
  yf, _, _, _, dg = va.gear_filter(zc, 'FAST', 1e-10, gate='always')
  np_clean = dg['near_pi_events']
  sl_clean = va.slips_vs_true(yf, sc['ph'])
  nps, sls, errs = [], [], []
  for s in range(va.NSEED_STATS):
    rng = np.random.default_rng(90_000 + s)
    z = (np.exp(1j * sc['ph'])
         + complex_bandlimited_noise(sc['N'], FS, B_FRONTEND, s2, rng))
    yf, _, _, _, dg = va.gear_filter(z, 'FAST', s2, gate='auto')
    nps.append(dg['near_pi_events'])
    sls.append(va.slips_vs_true(yf, sc['ph']))
    errs.append(va.amp_err_pct(va.vdisc(yf), sc))

  def pcts(a):
    return np.array([va.pctile(a, 50), va.pctile(a, 90), va.pctile(a, 95),
                     va.pctile(a, 99), float(np.max(a))])

  nz['a8_clean'] = np.array([np_clean, sl_clean], float)
  nz['a8_np_pct'] = pcts(nps)
  nz['a8_sl_pct'] = pcts(sls)
  nz['a8_err_pct'] = pcts(np.abs(errs))
  save('app_30ms_100khz', oks, det, nz)


# ==================================================================== main
def main():
  t0 = time.time()
  jobs = (('tracking', export_tracking), ('off_mode', export_off_mode),
          ('zeta_sweep', export_zeta_sweep),
          ('residual_alignment', export_residual_alignment),
          ('app_30ms_100khz', export_app))
  only = set(sys.argv[1:])
  for name, fn in jobs:
    if only and name not in only:
      continue
    print(f'\n===== exporting {name} =====')
    fn()
  print(f'\n[export done, {time.time()-t0:.1f} s]')
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
