#!/usr/bin/env python3
"""Heterodyne electrical-IQ (Polytec-class) tracking filter validation.

Signal model: z = exp(j*phi(t)) + n,  phi = 4*pi*x/lambda + 2*pi*f_IF*t
For constant-velocity sinusoid: f_D(t) = 2*v(t)/lambda walks with velocity.
Front end forced wide: B_frontend = 2*|f_D|_max (two-sided ENBW).

Fair comparison (R1-R4 style from homodyne suite):
  R1 signal gain from near-noiseless run
  R2 noise ASD in quiet band away from signal
  R3 SNR gain = signal_gain + 20*log10(ASD_off/ASD_on)
"""
import math
import time
import numpy as np

from core import (
  burst_signal, complex_bandlimited_noise, pll_carrier_regen,
  fm_discriminator, fir_lp, welch_psd,
)
from design_params import (
  LAMBDA, FS, ZETA, mode_params, select_gear, b_loop,
  ceiling_db, ACQ_BW, F_ACC_CAP,
)

TINY = 1e-300


def complex_lp(z, B_pre, fs=FS, Nt=401):
  return (fir_lp(z.real, B_pre / 2, fs, Nt)
          + 1j * fir_lp(z.imag, B_pre / 2, fs, Nt))


def heterodyne_phase(t, x, f_if0=0.0):
  """Phase including IF carrier at f_if0 (mean Doppler can be non-zero)."""
  return 4 * np.pi / LAMBDA * x + 2 * np.pi * f_if0 * t


def make_record(f_v, vamp, v_range, ncyc=20, t0=0.1e-3, T=0.5e-3, fs=FS, f_if0=None):
  N = int(T * fs)
  t = np.arange(N) / fs
  x, v, _ = burst_signal(t, f_v, vamp, ncyc, t0)
  # add mean velocity component for Doppler walk (velocity range)
  v_mean = 0.0
  v_tot = v + v_mean
  x_tot = np.cumsum(v_tot) * (t[1] - t[0])
  x_tot = x_tot - x_tot[0] + x[0]
  if f_if0 is None:
    f_if0 = 2 * v_range / LAMBDA * 0.5   # centre of IF window
  ph = heterodyne_phase(t, x_tot, f_if0)
  fD_max = 2 * v_range / LAMBDA
  Bf = min(2 * fD_max, fs * 0.45)
  quiet = (t > 0.35e-3) & (t < 0.48e-3)
  win = (t > t0) & (t < t0 + ncyc / f_v)
  return dict(t=t, ph=ph, v=v_tot, x=x_tot, quiet=quiet, win=win,
              f_v=f_v, vamp=vamp, v_range=v_range, B_frontend=Bf, f_if0=f_if0)


def asd_away(v, fs, f_v, quiet, f_lo=3.0, f_hi=30.0):
  P, f = welch_psd(v[quiet], fs, 2048)
  m = (f > f_lo * f_v) & (f < f_hi * f_v)
  return max(np.sqrt(np.median(P[m])), TINY) if m.any() else TINY


def ls_amp(v, t, f_v, win):
  sel = win
  X = np.column_stack([np.ones(sel.sum()),
                       np.sin(2 * np.pi * f_v * t[sel]),
                       np.cos(2 * np.pi * f_v * t[sel])])
  b, *_ = np.linalg.lstsq(X, v[sel], rcond=None)
  return np.hypot(b[1], b[2])


def run_pll(ph, fs, fn, s2, Bf, gate='always'):
  z = np.exp(1j * ph) + complex_bandlimited_noise(len(ph), fs, Bf, s2, np.random.default_rng())
  v_off = fm_discriminator(z, fs, LAMBDA)
  y, _, _, dg = pll_carrier_regen(z, fs, fn, s2, zeta=ZETA, gate=gate, **{
    k: v for k, v in dict(snr_on=1.0, snr_off=0.3, tauP=1e-6, tauF=1e-6,
                          rel_on=0.20, rel_off=0.08, tauRef=200e-6, reacq=True).items()})
  v_on = fm_discriminator(y, fs, LAMBDA)
  return v_off, v_on, dg


def snr_gain(rec, fn, cnr_db, nseed=16, gate='always'):
  f_v, win, quiet, Bf = rec['f_v'], rec['win'], rec['quiet'], rec['B_frontend']
  t, ph, v = rec['t'], rec['ph'], rec['v']
  s2 = 10 ** (-cnr_db / 10)
  # R1 signal gain (noiseless)
  rng = np.random.default_rng(42)
  z0 = np.exp(1j * ph) + complex_bandlimited_noise(len(t), FS, Bf, 1e-10, rng)
  y0, _, _, _ = pll_carrier_regen(z0, FS, fn, 1e-10, zeta=ZETA, gate='always',
    snr_on=1.0, snr_off=0.3, tauP=1e-6, tauF=1e-6, rel_on=0.20, rel_off=0.08,
    tauRef=200e-6, reacq=True)
  g_sig = 20 * math.log10(ls_amp(fm_discriminator(y0, FS, LAMBDA), t, f_v, win)
                           / max(ls_amp(v, t, f_v, win), TINY))
  gains = []
  for s in range(nseed):
    rng = np.random.default_rng(1000 + s)
    z = np.exp(1j * ph) + complex_bandlimited_noise(len(t), FS, Bf, s2, rng)
    vo = fm_discriminator(z, FS, LAMBDA)
    y, _, _, _ = pll_carrier_regen(z, FS, fn, s2, zeta=ZETA, gate=gate,
      snr_on=1.0, snr_off=0.3, tauP=1e-6, tauF=1e-6, rel_on=0.20, rel_off=0.08,
      tauRef=200e-6, reacq=True)
    vn = fm_discriminator(y, FS, LAMBDA)
    gains.append(g_sig + 20 * math.log10(asd_away(vo, FS, f_v, quiet) / asd_away(vn, FS, f_v, quiet)))
  g = np.asarray(gains)
  return float(np.median(g)), float(np.percentile(g, 10)), float(np.percentile(g, 90)), g_sig


def header(t):
  print('\n' + '=' * 88)
  print(t)
  print('=' * 88)


def H1_bandwidth_layers():
  header('H1  Four bandwidth layers (heterodyne, v_range=1.5 m/s)')
  vr = 1.5
  mp = mode_params(vr)
  fD = 2 * vr / LAMBDA
  print(f"  fs={FS/1e6:.0f} MHz | f_D,max={fD/1e6:.2f} MHz | B_frontend(forced)={mp['FAST']['B_frontend']/1e6:.2f} MHz")
  for g in ('SLOW', 'MEDIUM', 'FAST'):
    p = mp[g]
    print(f"  {g:6s} fn={p['fn']/1e3:7.1f}kHz B_loop={p['B_loop']/1e6:.3f}MHz "
          f"f_3dB={p['f_3db']/1e6:.3f}MHz ceiling={ceiling_db(vr,p['fn']):+.1f}dB")
  # sensitivity: conflate fs with B_frontend
  fn = mp['FAST']['fn']
  Bl = b_loop(fn)
  for label, Bn in [('B_frontend correct', mp['FAST']['B_frontend']),
                    ('use fs as noise BW (WRONG)', FS)]:
    print(f"  noise metric if {label}: 10log10(Bn/2/Bl) = "
          f"{10*math.log10((Bn/2)/Bl):+.1f} dB")


def H2_gear_sweep():
  header('H2  Three gears @ design vibration, CNR=6dB, v_range=1.5m/s, f_v=10kHz')
  vr, fv, vamp = 1.5, 10e3, 20e-3
  rec = make_record(fv, vamp, vr)
  mp = mode_params(vr)
  print(f"  {'gear':6s} {'fn':>8} {'ceiling':>8} {'SNRgain':>18} {'sigG':>6} {'ampErr%':>8}")
  ok = True
  for g in ('SLOW', 'MEDIUM', 'FAST'):
    fn = mp[g]['fn']
    med, p10, p90, gs = snr_gain(rec, fn, 6.0)
    # amp error
    s2 = 10 ** (-6 / 10)
    rng = np.random.default_rng(1)
    z = np.exp(1j * rec['ph']) + complex_bandlimited_noise(len(rec['t']), FS, rec['B_frontend'], s2, rng)
    y, _, _, _ = pll_carrier_regen(z, FS, fn, s2, zeta=ZETA, gate='always',
      snr_on=1.0, snr_off=0.3, tauP=1e-6, tauF=1e-6, rel_on=0.20, rel_off=0.08,
      tauRef=200e-6, reacq=True)
    ae = 100 * (ls_amp(fm_discriminator(y, FS, LAMBDA), rec['t'], fv, rec['win'])
                / ls_amp(rec['v'], rec['t'], fv, rec['win']) - 1)
    print(f"  {g:6s} {fn/1e3:7.0f}k {ceiling_db(vr,fn):+7.1f}dB {med:+6.2f} [{p10:+5.2f},{p90:+5.2f}] "
          f"{gs:+5.2f} {ae:+7.2f}")
  return ok


def H3_vrange_param():
  header('H3  Velocity-range sweep (f_v=10kHz fixed) — parametric fn vs fixed fn=400kHz')
  fv, vamp = 10e3, 20e-3
  print(f"  {'v_range':>8} {'f_Dmax':>8} {'fn_FAST':>8} {'ceiling':>8} | {'SNR param':>10} {'SNR fix400k':>10} | {'amp% param':>9} {'amp% fix':>9}")
  for vr in [0.05, 0.2, 0.6, 1.5, 3.0]:
    rec = make_record(fv, vamp, vr)
    mp = mode_params(vr)
    fn_p = mp['FAST']['fn']
    fn_f = 400e3
    med_p, _, _, _ = snr_gain(rec, fn_p, 6.0, nseed=12)
    med_f, _, _, _ = snr_gain(rec, fn_f, 6.0, nseed=12)
  # recompute amp for table
    def amp_e(fn):
      s2 = 10 ** (-6 / 10)
      rng = np.random.default_rng(1)
      z = np.exp(1j * rec['ph']) + complex_bandlimited_noise(len(rec['t']), FS, rec['B_frontend'], s2, rng)
      y, _, _, _ = pll_carrier_regen(z, FS, fn, s2, zeta=ZETA, gate='always',
        snr_on=1.0, snr_off=0.3, tauP=1e-6, tauF=1e-6, rel_on=0.20, rel_off=0.08,
        tauRef=200e-6, reacq=True)
      return 100 * (ls_amp(fm_discriminator(y, FS, LAMBDA), rec['t'], fv, rec['win'])
                    / ls_amp(rec['v'], rec['t'], fv, rec['win']) - 1)
    fD = 2 * vr / LAMBDA
    print(f"  {vr:7.2f}m/s {fD/1e6:7.2f}M {fn_p/1e3:7.0f}k {ceiling_db(vr,fn_p):+7.1f}dB | "
          f"{med_p:+9.2f}dB {med_f:+9.2f}dB | {amp_e(fn_p):+8.2f} {amp_e(fn_f):+8.2f}")


def H4_prelp_vs_pll():
  header('H4  Fixed preLP (B_loop) vs tracking PLL — heterodyne value boundary (from t5)')
  fv = 10e3
  cnr = 6.0
  print('  e_crit=1.0 design line:')
  print(f"  {'v_range':>8} {'f_D':>8} {'B_front':>8} {'fn':>8} {'ceil':>6} | {'PLL gain':>8} {'preLP':>8} | {'amp% PLL':>8} {'preLP':>8}")
  for vr in [0.05, 0.2, 0.6, 1.5, 3.0]:
    a_pk = 2 * math.pi * fv * vr
    fn = math.sqrt(a_pk / (math.pi * LAMBDA))
    Bl = b_loop(fn)
    fD = 2 * vr / LAMBDA
    Bf = 2 * fD
    if Bf > FS * 0.45:
      continue
    T = 0.5e-3
    N = int(T * FS)
    t = np.arange(N) / FS
    x = vr / (2 * math.pi * fv) * (1 - np.cos(2 * math.pi * fv * t))
    v_t = vr * np.sin(2 * math.pi * fv * t)
    ph = 4 * math.pi / LAMBDA * x + 2 * math.pi * (fD * 0.5) * t
    sel = t > 1.5 / fv
    s2 = 10 ** (-cnr / 10)
    a_true = ls_amp(v_t, t, fv, sel)
    ao, ap, ep, ee = [], [], [], []
    for s in range(12):
      rng = np.random.default_rng(3000 + s)
      z = np.exp(1j * ph) + complex_bandlimited_noise(N, FS, Bf, s2, rng)
      vo = fm_discriminator(z, FS, LAMBDA)
      vp = fm_discriminator(complex_lp(z, Bl), FS, LAMBDA)
      y, _, _, _ = pll_carrier_regen(z, FS, fn, s2, zeta=ZETA, gate='always',
        snr_on=1.0, snr_off=0.3, tauP=1e-6, tauF=1e-6, rel_on=0.20, rel_off=0.08,
        tauRef=200e-6, reacq=True)
      vn = fm_discriminator(y, FS, LAMBDA)
      def asd(v):
        P, f = welch_psd(v[sel], FS, 4096)
        m = (f > 3 * fv) & (f < 30 * fv)
        return max(np.sqrt(np.median(P[m])), TINY)
      ao.append(asd(vo)); ap.append(asd(vn))
      ep.append(100 * (ls_amp(vp, t, fv, sel) / a_true - 1))
      ee.append(100 * (ls_amp(vn, t, fv, sel) / a_true - 1))
    g_pll = 20 * math.log10(np.median(ao) / np.median(ap))
    print(f"  {vr:7.2f}m/s {fD/1e6:7.2f}M {Bf/1e6:7.2f}M {fn/1e3:7.0f}k {10*math.log10(fD/Bl):+5.1f} | "
          f"{g_pll:+7.2f}dB {0:+7.2f}dB | {np.median(ee):+7.2f} {np.median(ep):+7.2f}")


def H5_ecrit_boundary():
  header('H5  e_crit = 1 (design) vs pi (wrap line) — must fail on pi')
  fv = 10e3
  vr = 1.5
  for ec, label in [(1.0, 'e_crit=1 design'), (math.pi, 'e_crit=pi WRAP')]:
    fn = math.sqrt(2 * fv * vr / (ec * math.pi * LAMBDA))
    rec = make_record(fv, 20e-3, vr)
    med, _, _, gs = snr_gain(rec, fn, 6.0, nseed=12)
    s2 = 10 ** (-6 / 10)
    rng = np.random.default_rng(1)
    z = np.exp(1j * rec['ph']) + complex_bandlimited_noise(len(rec['t']), FS, rec['B_frontend'], s2, rng)
    y, _, _, _ = pll_carrier_regen(z, FS, fn, s2, zeta=ZETA, gate='always',
      snr_on=1.0, snr_off=0.3, tauP=1e-6, tauF=1e-6, rel_on=0.20, rel_off=0.08,
      tauRef=200e-6, reacq=True)
    ae = 100 * (ls_amp(fm_discriminator(y, FS, LAMBDA), rec['t'], fv, rec['win'])
                / ls_amp(rec['v'], rec['t'], fv, rec['win']) - 1)
    print(f"  {label}: fn={fn/1e3:.0f}kHz ampErr={ae:+.1f}% SNRgain={med:+.2f}dB")


def H6_user_scenario():
  header('H6  User scenario: mostly 100kHz structural, v_range up to 3m/s')
  for fv, vr, label in [(100e3, 0.1, 'daily 100kHz @0.1m/s range'),
                         (100e3, 3.0, '100kHz @3m/s range'),
                         (3e6, 3.0, '3MHz ultrasound @3m/s')]:
    gear, spec, fn_req = select_gear(vr, fv)
    rec = make_record(fv, 20e-3, vr, ncyc=10 if fv > 1e6 else 20)
    med, p10, p90, _ = snr_gain(rec, spec['fn'], 6.0, nseed=12)
    print(f"  {label}")
    print(f"    selected={gear} fn={spec['fn']/1e3:.0f}kHz (req {fn_req/1e3:.0f}kHz) "
          f"ceiling={ceiling_db(vr,spec['fn']):+.1f}dB SNRgain={med:+.2f} [{p10:+.1f},{p90:+.1f}]")


def run_assertions():
  header('ASSERTIONS')
  ok = True
  vr, fv = 1.5, 10e3
  mp = mode_params(vr)
  # FAST gear should beat OFF in SNR at moderate CNR
  rec = make_record(fv, 20e-3, vr)
  med, _, _, _ = snr_gain(rec, mp['FAST']['fn'], 6.0)
  ok &= print_pass('FAST gear SNR gain > 3 dB @CNR6', med > 3, f'{med:+.2f} dB')
  # pi line must have large amp error
  fn_pi = math.sqrt(2 * fv * vr / (math.pi * math.pi * LAMBDA))
  s2 = 10 ** (-6 / 10)
  rng = np.random.default_rng(1)
  z = np.exp(1j * rec['ph']) + complex_bandlimited_noise(len(rec['t']), FS, rec['B_frontend'], s2, rng)
  y, _, _, _ = pll_carrier_regen(z, FS, fn_pi, s2, zeta=ZETA, gate='always',
    snr_on=1.0, snr_off=0.3, tauP=1e-6, tauF=1e-6, rel_on=0.20, rel_off=0.08,
    tauRef=200e-6, reacq=True)
  ae_pi = abs(100 * (ls_amp(fm_discriminator(y, FS, LAMBDA), rec['t'], fv, rec['win'])
                      / ls_amp(rec['v'], rec['t'], fv, rec['win']) - 1))
  ok &= print_pass('e_crit=pi amp error > 20%', ae_pi > 20, f'{ae_pi:.1f}%')
  # parametric fn better amp than fixed 400k at vr=3
  rec3 = make_record(fv, 20e-3, 3.0)
  mp3 = mode_params(3.0)
  def ae(fn):
    rng = np.random.default_rng(1)
    z = np.exp(1j * rec3['ph']) + complex_bandlimited_noise(len(rec3['t']), FS, rec3['B_frontend'], s2, rng)
    y, _, _, _ = pll_carrier_regen(z, FS, fn, s2, zeta=ZETA, gate='always',
      snr_on=1.0, snr_off=0.3, tauP=1e-6, tauF=1e-6, rel_on=0.20, rel_off=0.08,
      tauRef=200e-6, reacq=True)
    return abs(100 * (ls_amp(fm_discriminator(y, FS, LAMBDA), rec3['t'], fv, rec3['win'])
                      / ls_amp(rec3['v'], rec3['t'], fv, rec3['win']) - 1))
  ok &= print_pass('parametric fn amp <= fixed 400k @vr=3', ae(mp3['FAST']['fn']) <= ae(400e3) + 1,
                   f"param {ae(mp3['FAST']['fn']):.1f}% vs fix {ae(400e3):.1f}%")
  print('\n' + ('ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'))
  return ok


def print_pass(label, cond, detail=''):
  status = 'PASS' if cond else 'FAIL'
  print(f"  [{status}] {label}  ({detail})")
  return cond


def main():
  t0 = time.time()
  print('Heterodyne electrical-IQ tracking filter validation (Polytec-class)')
  print(f'lambda={LAMBDA*1e9:.1f}nm fs={FS/1e6:.0f}MHz zeta={ZETA}')
  H1_bandwidth_layers()
  H2_gear_sweep()
  H3_vrange_param()
  H4_prelp_vs_pll()
  H5_ecrit_boundary()
  H6_user_scenario()
  ok = run_assertions()
  print(f'\n[elapsed {time.time()-t0:.1f}s]')
  return 0 if ok else 1


if __name__ == '__main__':
  raise SystemExit(main())
