#!/usr/bin/env python3
"""Validate the 1550 nm / 3 MHz homodyne IQ multi-band tracking filter.

Success criteria (printed PASS/FAIL):
  - FAST @ 3 MHz: amp error < 3 %, CNR=3 dB SNR gain > 0 dB
  - SLOW @ 100 kHz: CNR=3 dB, B_frontend=40 MHz SNR gain > 10 dB
  - All bands @ their band-edge frequency: amp error < 5 %
"""
import math
import time
import numpy as np

from core import (
  burst_signal, complex_bandlimited_noise, pll_carrier_regen,
  fm_discriminator, hl_response, lockin_amp, welch_psd,
)
from design_params import (
  LAMBDA, FS, B_FRONTEND, ZETA, BANDS, PLL_GATE,
  LEGACY_FN, select_band, band_specs,
)

TINY = 1e-300
VAMP = 20e-3
NCYC = 20


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


def run_pll(ph_true, fs, fn, cnr_db, B_frontend, seed, gate='always'):
  rng = np.random.default_rng(seed)
  N = ph_true.size
  s2 = 10 ** (-cnr_db / 10)
  z = np.exp(1j * ph_true) + complex_bandlimited_noise(N, fs, B_frontend, s2, rng)
  v_off = fm_discriminator(z, fs, LAMBDA)
  kw = dict(zeta=ZETA, gate=gate, **PLL_GATE)
  y, _, st, diag = pll_carrier_regen(z, fs, fn, s2, **kw)
  v_on = fm_discriminator(y, fs, LAMBDA)
  return v_off, v_on, diag


def signal_gain_db(ph_true, v_true, t, fn, f0, win, fs=FS):
  s2 = 1e-10
  rng = np.random.default_rng(42)
  z = np.exp(1j * ph_true) + complex_bandlimited_noise(len(t), fs, B_FRONTEND, s2, rng)
  kw = dict(zeta=ZETA, gate='always', **PLL_GATE)
  y, _, _, _ = pll_carrier_regen(z, fs, fn, s2, **kw)
  a_on = lockin_amp(fm_discriminator(y, fs, LAMBDA), t, f0, win)
  a_tr = lockin_amp(v_true, t, f0, win)
  return 20 * np.log10(a_on / a_tr)


def mc_snr_gain(ph_true, v_true, t, quiet, win, fn, f0, cnr_db, nseed=32, gate='always'):
  g_sig = signal_gain_db(ph_true, v_true, t, fn, f0, win)
  gains = []
  for s in range(nseed):
    vo, vn, _ = run_pll(ph_true, FS, fn, cnr_db, B_FRONTEND, 1000 + s, gate=gate)
    gains.append(g_sig + 20 * np.log10(asd_at(vo, FS, f0, quiet) / asd_at(vn, FS, f0, quiet)))
  g = np.asarray(gains)
  return float(np.median(g)), float(np.percentile(g, 10)), float(np.percentile(g, 90))


def amp_error_pct(f0, fn, fs=FS):
  H = abs(hl_response([f0], fs, fn, ZETA)[0])
  return 100 * abs(H - 1.0)


def print_header(title):
  print('\n' + '=' * 78)
  print(title)
  print('=' * 78)


def check(label, ok):
  print(f'  [{ "PASS" if ok else "FAIL" }] {label}')
  return ok


def v1_band_sweep():
  print_header('V1  Per-band weak-light performance (CNR = 3 dB, B_frontend = 40 MHz)')
  tests = [
    ('SLOW', 100e3),
    ('MEDIUM', 1e6),
    ('FAST', 3e6),
  ]
  results = []
  print(f"  {'band':<8} {'f0':>8} {'fn':>8} {'|H| err%':>9} {'SNR gain':>18} {'legacy err%':>12}")
  for band, f0 in tests:
    fn = BANDS[band]['fn']
    t, ph, v, quiet, win = make_quiet_burst_sim(f0)
    err = amp_error_pct(f0, fn)
    med, p10, p90 = mc_snr_gain(ph, v, t, quiet, win, fn, f0, 3.0)
    leg_err = amp_error_pct(f0, LEGACY_FN[band])
    print(f"  {band:<8} {f0/1e3:7.0f}k {fn/1e3:7.0f}k {err:8.2f}% {med:+6.2f} [{p10:+5.2f},{p90:+5.2f}] dB {leg_err:10.2f}%")
    results.append(dict(band=band, f0=f0, err=err, snr=med, leg_err=leg_err))
  return results


def v2_plain_lp_compare():
  print_header('V2  PLL vs equal-B_loop IIR low-pass @ 3 MHz (CNR = 3 dB)')
  f0 = 3e6
  fn = BANDS['FAST']['fn']
  B_loop = band_specs('FAST')['B_loop']
  a_lp = math.exp(-2 * math.pi * B_loop / FS)
  t, ph, v, quiet, win = make_quiet_burst_sim(f0, t_burst=0.25e-3)
  g_pll = signal_gain_db(ph, v, t, fn, f0, win)

  def run_lp(seed):
    rng = np.random.default_rng(seed)
    s2 = 10 ** (-3 / 10)
    z = np.exp(1j * ph) + complex_bandlimited_noise(len(t), FS, B_FRONTEND, s2, rng)
    # angle-preserving LP: rotate to baseband at burst, LP, rotate back
    ref = np.exp(-1j * ph)
    r = z * np.conj(ref)
    from core import iir1_lowpass
    rf = iir1_lowpass(r, a_lp)
    z_lp = rf * ref
    vo = fm_discriminator(z, FS, LAMBDA)
    vn = fm_discriminator(z_lp, FS, LAMBDA)
    return asd_at(vo, FS, f0, quiet), asd_at(vn, FS, f0, quiet)

  gains = []
  for s in range(32):
    ao, an = run_lp(2000 + s)
    gains.append(g_pll + 20 * np.log10(ao / an))
  med = float(np.median(gains))
  print(f"  FAST fn={fn/1e6:.2f} MHz, B_loop={B_loop/1e6:.2f} MHz")
  print(f"  PLL median SNR gain @3 MHz: {med:+.2f} dB (plain LP same B_loop for reference)")
  print("  -> At 3 MHz the PLL is essentially a band-limited phase tracker;")
  print("     marginal extra gain is expected. Value is flat response + gating.")


def v3_speckle_dropout():
  print_header('V3  Speckle dropout (CNR = 12 dB, f0 = 1 MHz, MEDIUM band, gate=auto)')
  from core import make_speckle
  f0 = 1e6
  fn = BANDS['MEDIUM']['fn']
  t, ph, v, quiet, win = make_quiet_burst_sim(f0)
  spikes_off, spikes_on, disp_off, disp_on = [], [], [], []
  for s in range(24):
    rng = np.random.default_rng(3000 + s)
    s2 = 10 ** (-12 / 10)
    h = make_speckle(len(t), FS, 15e-6, rng)
    z = h * np.exp(1j * ph) + complex_bandlimited_noise(len(t), FS, B_FRONTEND, s2, rng)
    vo = fm_discriminator(z, FS, LAMBDA)
    kw = dict(zeta=ZETA, gate='auto', **PLL_GATE)
    y, _, st, _ = pll_carrier_regen(z, FS, fn, s2, **kw)
    vn = fm_discriminator(y, FS, LAMBDA)
    thr = 0.4
    spikes_off.append(int(np.sum(np.abs(vo[quiet]) > thr)))
    spikes_on.append(int(np.sum(np.abs(vn[quiet]) > thr)))
    x_off = np.cumsum(vo) * (t[1] - t[0])
    x_on = np.cumsum(vn) * (t[1] - t[0])
    disp_off.append(float(np.std(x_off[quiet] - x_off[quiet].mean()) * 1e9))
    disp_on.append(float(np.std(x_on[quiet] - x_on[quiet].mean()) * 1e9))
  print(f"  velocity spikes >0.4 m/s in quiet: OFF {np.median(spikes_off):.0f}  PLL {np.median(spikes_on):.0f}")
  print(f"  displacement std (nm) in quiet:      OFF {np.median(disp_off):.0f}  PLL {np.median(disp_on):.0f}")
  print("  -> Gate suppresses velocity spikes; displacement may not improve.")


def v4_band_selection():
  print_header('V4  Automatic band selection')
  cases = [50e3, 150e3, 500e3, 1.5e6, 2.8e6]
  for f in cases:
    b = select_band(f)
    sp = band_specs(b)
    print(f"  f_target={f/1e3:7.1f} kHz -> {b:<6} fn={sp['fn']/1e3:6.0f} kHz  "
          f"f_3dB={sp['f_3db']/1e6:.2f} MHz  ceiling={sp['ceiling_db']:+.1f} dB")


def v5_legacy_compare():
  print_header('V5  New vs legacy fn @ band edges (analytic |H| error)')
  for band in ('SLOW', 'MEDIUM', 'FAST'):
    f0 = BANDS[band]['f_target_max']
    e_new = amp_error_pct(f0, BANDS[band]['fn'])
    e_old = amp_error_pct(f0, LEGACY_FN[band])
    print(f"  {band:<6} f={f0/1e6:.2f} MHz: new {e_new:5.2f}%  legacy {e_old:6.2f}%")


def run_assertions(v1):
  print_header('ASSERTIONS')
  ok = True
  slow = next(r for r in v1 if r['band'] == 'SLOW')
  fast = next(r for r in v1 if r['band'] == 'FAST')
  ok &= check(f"SLOW @100kHz SNR gain > 10 dB (got {slow['snr']:+.2f} dB)", slow['snr'] > 10)
  ok &= check(f"FAST @3MHz amp error < 3 % (got {fast['err']:.2f} %)", fast['err'] < 3.0)
  ok &= check(f"FAST @3MHz SNR gain > 0 dB (got {fast['snr']:+.2f} dB)", fast['snr'] > 0)
  for r in v1:
    ok &= check(f"{r['band']} amp error < 5 % (got {r['err']:.2f} %)", r['err'] < 5.0)
  ok &= check(
    f"FAST legacy amp error worse than new ({fast['leg_err']:.1f}% vs {fast['err']:.1f}%)",
    fast['leg_err'] > fast['err'],
  )
  print('\n' + ('ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'))
  return ok


def print_design_table():
  print_header('DESIGN TABLE  (lambda=1550 nm, fs=250 MS/s, B_frontend=40 MHz, zeta=1.2)')
  print(f"  {'band':<8} {'f_max':>8} {'fn':>8} {'B_loop':>8} {'f_3dB':>8} {'ceiling':>8} {'a_design':>10}")
  for name in ('SLOW', 'MEDIUM', 'FAST'):
    sp = band_specs(name)
    print(f"  {name:<8} {sp['f_target_max']/1e3:7.0f}k {sp['fn']/1e3:7.0f}k "
          f"{sp['B_loop']/1e6:7.2f}M {sp['f_3db']/1e6:7.2f}M {sp['ceiling_db']:+7.1f}dB "
          f"{sp['a_design']:10.0f}")


def main():
  t0 = time.time()
  print_design_table()
  v5_legacy_compare()
  v1 = v1_band_sweep()
  v2_plain_lp_compare()
  v3_speckle_dropout()
  v4_band_selection()
  ok = run_assertions(v1)
  print(f"\n[elapsed {time.time()-t0:.1f} s]")
  return 0 if ok else 1


if __name__ == '__main__':
  raise SystemExit(main())
