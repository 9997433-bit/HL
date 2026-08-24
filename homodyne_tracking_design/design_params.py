"""1550 nm homodyne IQ tracking-filter band plan (equal-ripple design).

Design rule (derivation summary)
--------------------------------
Closed-loop response of the II-type loop (continuous approx., x = f/fn):

    |H_L(x)|^2 = (1 + 4*zeta^2*x^2) / ((1 - x^2)^2 + 4*zeta^2*x^2)

The PI zero produces mid-band peaking.  Amplitude error <= 3 % over the
whole usage band therefore needs BOTH:

  (1) peak |H_L| <= 1.03  ->  zeta >= 2.575.  We use zeta = 2.65
      (continuous peak +2.85 % at x ~= 0.62) so that the exact discrete
      response at fs = 250 MS/s (peaking slightly above the continuous
      value for FAST) still stays inside 3 %: measured discrete ripple
      2.85 / 2.87 / 2.92 % for SLOW / MEDIUM / FAST.
  (2) |H_L(x_edge)| >= 0.97  ->  x_edge <= 1.944  (zeta = 2.65)

So each band picks   fn = f_max / 1.875   (margin inside 1.944), giving an
equal-ripple -2.2 % / +2.9 % response across [0, f_max].  Compare the old
zeta = 1.2 plan: -10.9 % at the band edge and +11.4 % peaking at 0.66*fn.

Cost of flatness:  B_loop = pi*fn*(1+4*zeta^2)/(4*zeta) = 8.62*fn
(zeta = 2.65) instead of 4.424*fn (zeta = 1.2) -- about 2.9 dB of the
weak-light ceiling is traded for a calibration-free +/-3 % band.
(The exact discrete single-sided ENBW integrated to fs/2 is slightly
larger: 8.69 / 8.95 / 9.69 * fn for SLOW / MEDIUM / FAST.)

Other spec formulas (per band):
    f_3dB    = 5.49 * fn                     (zeta = 2.65)
    a_design = pi * lambda * fn^2            (e_ss = 1 rad)
    ceiling  = 10*log10((B_frontend/2) / B_loop)   vs-OFF phase-noise gain
    sigma_phi^2 = B_loop / (CNR_lin * B_frontend)  in-lock phase jitter
"""
import math

LAMBDA = 1550e-9
FS = 250e6
B_FRONTEND = 40e6          # complex-baseband two-sided ENBW (20e6 also legal)
ZETA = 2.65                # equal-ripple +/-3 % (see module docstring)

_B_LOOP_COEF = math.pi * (1 + 4 * ZETA ** 2) / (4 * ZETA)   # 8.6215 (zeta=2.65)
_X_EDGE = 1.875            # f_max / fn (inside the 1.944 = -3 % crossing)
_X_3DB = 5.489             # |H_L| = -3 dB crossing for zeta = 2.65

BANDS = {
  # fn = f_max / 1.875, rounded; gate constants scale with band dynamics.
  'SLOW': dict(
    f_target_max=200e3, fn=110e3, label='结构/低频, 最高灵敏度',
    tauP=4e-6, tauF=8e-6,
  ),
  'MEDIUM': dict(
    f_target_max=1e6, fn=530e3, label='常用 ≤1 MHz',
    tauP=2e-6, tauF=2e-6,
  ),
  'FAST': dict(
    f_target_max=3e6, fn=1.60e6, label='最高 3 MHz',
    tauP=1e-6, tauF=1e-6,
  ),
}

# Gate = dropout detector (NOT an FM-threshold detector): weakest specified
# light is CNR 3 dB -> snr_hat = 2.0 > SnrOn = 1.0 enters LOCK; a 10 dB fade
# drops snr_hat below SnrOff = 0.3.  rel_on/rel_off track relative fades.
GATE_COMMON = dict(
  snr_on=1.0,
  snr_off=0.3,
  rel_on=0.20,
  rel_off=0.08,
  tauRef=200e-6,
  reacq=True,
)

# Legacy tentative plan: zeta = 1.2, fn set for about -1 dB at the band edge
LEGACY_ZETA = 1.2
LEGACY_FN = {'SLOW': 106e3, 'MEDIUM': 529e3, 'FAST': 1.589e6}

# Acceleration guard: keep steady-state phase error e_ss <= 0.3 rad
ACC_GUARD = 0.3


def gate_params(name):
  b = BANDS[name]
  return dict(tauP=b['tauP'], tauF=b['tauF'], **GATE_COMMON)


def loop_gains(fn, fs=FS, zeta=ZETA):
  th = 2 * math.pi * fn / fs
  return 2 * zeta * th, th * th          # Kp, Ki


def band_specs(name, B_frontend=B_FRONTEND, cnr_db=3.0):
  b = BANDS[name]
  fn = b['fn']
  Kp, Ki = loop_gains(fn)
  B_loop = _B_LOOP_COEF * fn
  cnr = 10 ** (cnr_db / 10)
  sigma_phi = math.sqrt(B_loop / (cnr * B_frontend))
  return dict(
    name=name, fn=fn, zeta=ZETA, Kp=Kp, Ki=Ki,
    f_target_max=b['f_target_max'],
    B_loop=B_loop,
    f_3db=_X_3DB * fn,
    a_design=math.pi * LAMBDA * fn ** 2,
    ceiling_db=10 * math.log10((B_frontend / 2) / B_loop),
    sigma_phi_at_cnr=sigma_phi,
    **gate_params(name),
  )


def select_band(f_target_hz, v_peak=None):
  """Frequency-first band choice with an acceleration guard.

  1. narrowest band whose f_target_max covers the target frequency;
  2. if the expected peak acceleration a = 2*pi*f*v exceeds
     ACC_GUARD * a_design of that band, shift up until it fits.
  """
  order = ('SLOW', 'MEDIUM', 'FAST')
  idx = next((i for i, n in enumerate(order)
              if f_target_hz <= BANDS[n]['f_target_max']), len(order) - 1)
  if v_peak is not None:
    a_pk = 2 * math.pi * f_target_hz * v_peak
    while idx < len(order) - 1:
      a_design = math.pi * LAMBDA * BANDS[order[idx]]['fn'] ** 2
      if a_pk <= ACC_GUARD * a_design:
        break
      idx += 1
  return order[idx]


def as_struct_table():
  """Code-ready parameter table (mirrors the MATLAB struct in the docs)."""
  return {name: band_specs(name) for name in ('SLOW', 'MEDIUM', 'FAST')}
