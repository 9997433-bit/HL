#!/usr/bin/env python3
"""Validate the 1550 nm / 250 MS/s homodyne IQ multi-band tracking filter.

Printed PASS/FAIL criteria:
  - every band: max |H_L| amplitude error <= 3 % over [0, f_max] (exact
    discrete response), in particular FAST @ 3 MHz;
  - measured (time-domain) amplitude error @ 3 MHz < 3 %;
  - weak light CNR = 3 dB / B_frontend = 40 MHz local SNR gain vs OFF:
    SLOW > 10 dB, MEDIUM > 5 dB;
  - legacy zeta=1.2 plan violates the 3 % budget (both edge and peaking).
"""
import math
import time
import numpy as np

from core import (
  burst_signal, complex_bandlimited_noise, pll_carrier_regen,
  fm_discriminator, hl_response, lockin_amp, welch_psd, make_speckle,
)
from design_params import (
  LAMBDA, FS, B_FRONTEND, ZETA, BANDS, LEGACY_ZETA, LEGACY_FN,
  select_band, band_specs, gate_params,
)

TINY = 1e-300
VAMP = 20e-3
NCYC = 20


# ----------------------------------------------------------------- helpers
def make_quiet_burst_sim(f0, fs=FS, T=5e-4, t_burst=0.10e-3):
  N = int(T * fs)
  t = np.arange(N) / fs
  x, v, _ = burst_signal(t, f0, VAMP, NCYC, t_burst)
  quiet = (t > 0.33e-3) & (t < 0.49e-3)
  win = (t > t_burst) & (t < t_burst + NCYC / f0)
  ph = 4 * np.pi / LAMBDA * x
  return t, ph, v, quiet, win


def asd_at(v, fs, f0, quiet, band=0.12e6):
  P, f = welch_psd(v[quiet], fs, 1024)
  m = np.abs(f - f0) < band
  return max(np.sqrt(np.median(P[m])), TINY)


def run_pll(ph_true, fs, fn, zeta, cnr_db, B_frontend, seed, gate, gp):
  rng = np.random.default_rng(seed)
  s2 = 10 ** (-cnr_db / 10)
  z = np.exp(1j * ph_true) + complex_bandlimited_noise(
      ph_true.size, fs, B_frontend, s2, rng)
  v_off = fm_discriminator(z, fs, LAMBDA)
  y, _, st, diag = pll_carrier_regen(z, fs, fn, s2, zeta=zeta, gate=gate, **gp)
  v_on = fm_discriminator(y, fs, LAMBDA)
  return v_off, v_on, diag


def sim_amp_ratio(ph_true, v_true, t, fn, zeta, f0, win, gp, fs=FS):
  """Measured |H| at f0: nearly noise-free run, lock-in vs exact reference."""
  s2 = 1e-10
  rng = np.random.default_rng(42)
  z = np.exp(1j * ph_true) + complex_bandlimited_noise(
      len(t), fs, B_FRONTEND, s2, rng)
  y, _, _, _ = pll_carrier_regen(z, fs, fn, s2, zeta=zeta, gate='always', **gp)
  a_on = lockin_amp(fm_discriminator(y, fs, LAMBDA), t, f0, win)
  a_tr = lockin_amp(v_true, t, f0, win)
  return a_on / a_tr


def mc_snr_gain(ph_true, v_true, t, quiet, win, fn, zeta, f0, cnr_db, gp,
                nseed=32, gate='always'):
  g_sig = 20 * np.log10(sim_amp_ratio(ph_true, v_true, t, fn, zeta, f0, win, gp))
  gains = []
  for s in range(nseed):
    vo, vn, _ = run_pll(ph_true, FS, fn, zeta, cnr_db, B_FRONTEND,
                        1000 + s, gate, gp)
    gains.append(g_sig + 20 * np.log10(
        asd_at(vo, FS, f0, quiet) / asd_at(vn, FS, f0, quiet)))
  g = np.asarray(gains)
  return float(np.median(g)), float(np.percentile(g, 10)), float(np.percentile(g, 90))


def numeric_loop_specs(fn, zeta, fs=FS, npts=1 << 20):
  """Exact discrete |H_L|: single-sided ENBW, f_3dB, in-band ripple."""
  f = np.linspace(0, fs / 2, npts + 1)
  H = np.abs(hl_response(f, fs, fn, zeta))
  B_loop = np.trapezoid(H ** 2, f)
  i3 = np.argmax(H < 1 / math.sqrt(2))
  f3 = f[i3]
  return B_loop, f3, f, H


def band_ripple(f, H, f_max):
  m = f <= f_max
  return 100 * float(np.max(np.abs(H[m] - 1.0)))


def print_header(title):
  print('\n' + '=' * 78)
  print(title)
  print('=' * 78)


def check(label, ok):
  print(f'  [{"PASS" if ok else "FAIL"}] {label}')
  return ok


# ----------------------------------------------------------------- sections
def v0_design_table():
  print_header('V0  DESIGN TABLE  (lambda=1550 nm, fs=250 MS/s, zeta=2.65, '
               'B_frontend=40 MHz)')
  print(f"  {'band':<7} {'f_max':>7} {'fn':>7} {'Kp':>9} {'Ki':>9} "
        f"{'B_loop':>8} {'f_3dB':>7} {'ripple':>7} {'|H|@3M':>8} "
        f"{'ceil40':>7} {'ceil20':>7} {'a_dsgn':>9} {'sig_phi':>8}")
  rows = {}
  for name in ('SLOW', 'MEDIUM', 'FAST'):
    sp = band_specs(name)
    B_num, f3_num, f, H = numeric_loop_specs(sp['fn'], ZETA)
    rip = band_ripple(f, H, sp['f_target_max'])
    h3 = abs(hl_response([3e6], FS, sp['fn'], ZETA)[0])
    ceil20 = 10 * math.log10((20e6 / 2) / B_num)
    ceil40 = 10 * math.log10((40e6 / 2) / B_num)
    print(f"  {name:<7} {sp['f_target_max']/1e3:6.0f}k {sp['fn']/1e3:6.0f}k "
          f"{sp['Kp']:9.3e} {sp['Ki']:9.3e} {B_num/1e6:7.3f}M "
          f"{f3_num/1e6:6.2f}M {rip:6.2f}% {20*math.log10(h3):+7.2f}dB "
          f"{ceil40:+6.1f} {ceil20:+6.1f} {sp['a_design']:9.3g} "
          f"{sp['sigma_phi_at_cnr']:7.3f}")
    rows[name] = dict(sp, B_num=B_num, f3_num=f3_num, ripple=rip, h3=h3)
  print("  (ripple = max |H|-error over [0,f_max], exact discrete response;")
  print("   ceil40/ceil20 = 10log10((B_frontend/2)/B_loop); sig_phi @CNR 3 dB, rad)")
  return rows


def v1_legacy_analytic():
  print_header('V1  New (zeta=2.65) vs legacy (zeta=1.2, -1dB-edge fn) '
               'amplitude budget')
  print(f"  {'band':<7} {'edge':>7} | {'new edge%':>9} {'new peak%':>9} "
        f"| {'leg edge%':>9} {'leg peak%':>9} {'leg B_loop':>10}")
  worst_leg = 0.0
  for name in ('SLOW', 'MEDIUM', 'FAST'):
    fe = BANDS[name]['f_target_max']
    _, _, f, Hn = numeric_loop_specs(BANDS[name]['fn'], ZETA, npts=1 << 18)
    _, _, fl, Hl = numeric_loop_specs(LEGACY_FN[name], LEGACY_ZETA, npts=1 << 18)
    e_new = 100 * abs(abs(hl_response([fe], FS, BANDS[name]['fn'], ZETA)[0]) - 1)
    e_leg = 100 * abs(abs(hl_response([fe], FS, LEGACY_FN[name], LEGACY_ZETA)[0]) - 1)
    p_new = band_ripple(f, Hn, fe)
    p_leg = band_ripple(fl, Hl, fe)
    Bl = math.pi * LEGACY_FN[name] * (1 + 4 * LEGACY_ZETA ** 2) / (4 * LEGACY_ZETA)
    worst_leg = max(worst_leg, e_leg, p_leg)
    print(f"  {name:<7} {fe/1e3:6.0f}k | {e_new:8.2f}% {p_new:8.2f}% "
          f"| {e_leg:8.2f}% {p_leg:8.2f}% {Bl/1e6:8.2f}M")
  print("  -> legacy: about -11 % at every band edge PLUS +11 % mid-band "
        "peaking;")
  print("     new: whole band inside +/-3 % without any calibration.")
  return worst_leg


def v2_band_sweep():
  print_header('V2  Per-band weak light, B_frontend = 40 MHz '
               '(median [p10,p90] over 32 seeds)')
  tests = [('SLOW', 100e3), ('MEDIUM', 1e6), ('FAST', 3e6)]
  results = []
  print(f"  {'band':<7} {'f0':>7} {'fn':>7} {'amp err%':>9} "
        f"{'SNRgain@3dB':>22} {'SNRgain@6dB':>22}")
  for band, f0 in tests:
    fn, zeta = BANDS[band]['fn'], ZETA
    gp = gate_params(band)
    t, ph, v, quiet, win = make_quiet_burst_sim(f0)
    a_ratio = sim_amp_ratio(ph, v, t, fn, zeta, f0, win, gp)
    err = 100 * abs(a_ratio - 1)
    g3 = mc_snr_gain(ph, v, t, quiet, win, fn, zeta, f0, 3.0, gp)
    g6 = mc_snr_gain(ph, v, t, quiet, win, fn, zeta, f0, 6.0, gp)
    print(f"  {band:<7} {f0/1e3:6.0f}k {fn/1e3:6.0f}k {err:8.2f}% "
          f"{g3[0]:+6.2f} [{g3[1]:+6.2f},{g3[2]:+6.2f}] dB "
          f"{g6[0]:+6.2f} [{g6[1]:+6.2f},{g6[2]:+6.2f}] dB")
    results.append(dict(band=band, f0=f0, err=err, snr3=g3[0], snr6=g6[0]))
  return results


def v2b_legacy_fast_sim():
  print_header('V2b Legacy FAST (fn=1.589M, zeta=1.2) @ 3 MHz, CNR 3 dB '
               '(reference)')
  f0 = 3e6
  gp = gate_params('FAST')
  t, ph, v, quiet, win = make_quiet_burst_sim(f0)
  a = sim_amp_ratio(ph, v, t, LEGACY_FN['FAST'], LEGACY_ZETA, f0, win, gp)
  g = mc_snr_gain(ph, v, t, quiet, win, LEGACY_FN['FAST'], LEGACY_ZETA,
                  f0, 3.0, gp, nseed=16)
  print(f"  amp ratio {a:.4f} ({100*abs(a-1):.1f} % error), "
        f"SNR gain {g[0]:+.2f} dB")
  print("  -> legacy buys ~2 dB more noise gain but breaks the 3 % budget.")
  return a


def v3_broadband_noise():
  print_header('V3  Broadband velocity-noise reduction (quiet segment std, '
               'CNR = 3 dB)')
  t, ph, v, quiet, win = make_quiet_burst_sim(1e6)
  for band in ('SLOW', 'MEDIUM', 'FAST'):
    gp = gate_params(band)
    r = []
    for s in range(8):
      vo, vn, _ = run_pll(ph, FS, BANDS[band]['fn'], ZETA, 3.0, B_FRONTEND,
                          5000 + s, 'always', gp)
      r.append(np.std(vo[quiet]) / max(np.std(vn[quiet]), TINY))
    print(f"  {band:<7} OFF/ON velocity std ratio: {np.median(r):7.1f}x "
          f"({20*np.log10(np.median(r)):+.1f} dB)")


def v4_speckle_dropout():
  print_header('V4  Speckle dropout, gate=auto (CNR = 12 dB, f0 = 1 MHz, '
               'MEDIUM)')
  f0 = 1e6
  fn = BANDS['MEDIUM']['fn']
  gp = gate_params('MEDIUM')
  t, ph, v, quiet, win = make_quiet_burst_sim(f0)
  sp_off, sp_on, lock = [], [], []
  for s in range(16):
    rng = np.random.default_rng(3000 + s)
    s2 = 10 ** (-12 / 10)
    h = make_speckle(len(t), FS, 15e-6, rng)
    z = h * np.exp(1j * ph) + complex_bandlimited_noise(
        len(t), FS, B_FRONTEND, s2, rng)
    vo = fm_discriminator(z, FS, LAMBDA)
    y, _, st, diag = pll_carrier_regen(z, FS, fn, s2, zeta=ZETA,
                                       gate='auto', **gp)
    vn = fm_discriminator(y, FS, LAMBDA)
    thr = 0.4
    sp_off.append(int(np.sum(np.abs(vo[quiet]) > thr)))
    sp_on.append(int(np.sum(np.abs(vn[quiet]) > thr)))
    lock.append(diag['lock_frac'])
  print(f"  velocity spikes >0.4 m/s in quiet: OFF {np.median(sp_off):.0f}  "
        f"PLL {np.median(sp_on):.0f}   (lock fraction {np.median(lock):.2f})")
  print("  -> gate suppresses fade spikes; displacement continuity is NOT "
        "promised.")
  return float(np.median(sp_off)), float(np.median(sp_on))


def v5_band_selection():
  print_header('V5  Band selection: frequency-first + acceleration guard')
  cases = [(50e3, 0.02), (150e3, 0.02), (500e3, 0.02), (1.5e6, 0.02),
           (2.8e6, 0.02), (150e3, 0.5), (1e6, 0.2)]
  for f, vpk in cases:
    b = select_band(f, vpk)
    a_pk = 2 * math.pi * f * vpk
    sp = band_specs(b)
    print(f"  f={f/1e3:7.0f} kHz  v_pk={vpk*1e3:6.0f} mm/s  "
          f"a_pk={a_pk:9.3g} m/s^2 -> {b:<6} "
          f"(a_design={sp['a_design']:9.3g}, guard=0.3)")


def run_assertions(rows, v2, worst_leg, amp_leg, spikes):
  print_header('ASSERTIONS')
  ok = True
  for name in ('SLOW', 'MEDIUM', 'FAST'):
    ok &= check(f"{name} in-band ripple <= 3 % (got {rows[name]['ripple']:.2f} %)",
                rows[name]['ripple'] <= 3.0)
  fast = next(r for r in v2 if r['band'] == 'FAST')
  slow = next(r for r in v2 if r['band'] == 'SLOW')
  med = next(r for r in v2 if r['band'] == 'MEDIUM')
  ok &= check(f"FAST measured amp error @3 MHz < 3 % (got {fast['err']:.2f} %)",
              fast['err'] < 3.0)
  ok &= check(f"SLOW SNR gain @CNR3dB > 10 dB (got {slow['snr3']:+.2f} dB)",
              slow['snr3'] > 10)
  ok &= check(f"MEDIUM SNR gain @CNR3dB > 5 dB (got {med['snr3']:+.2f} dB)",
              med['snr3'] > 5)
  ok &= check(f"FAST SNR gain @CNR6dB > 0 dB (got {fast['snr6']:+.2f} dB)",
              fast['snr6'] > 0)
  ok &= check(f"legacy plan violates 3 % budget (worst {worst_leg:.1f} %)",
              worst_leg > 3.0)
  ok &= check(f"speckle spikes reduced (OFF {spikes[0]:.0f} -> ON {spikes[1]:.0f})",
              spikes[1] < spikes[0])
  print('\n' + ('ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'))
  return ok


def main():
  t0 = time.time()
  rows = v0_design_table()
  worst_leg = v1_legacy_analytic()
  v2 = v2_band_sweep()
  amp_leg = v2b_legacy_fast_sim()
  v3_broadband_noise()
  spikes = v4_speckle_dropout()
  v5_band_selection()
  ok = run_assertions(rows, v2, worst_leg, amp_leg, spikes)
  print(f"\n[elapsed {time.time()-t0:.1f} s]")
  return 0 if ok else 1


if __name__ == '__main__':
  raise SystemExit(main())
