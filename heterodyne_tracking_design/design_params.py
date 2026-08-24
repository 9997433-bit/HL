"""Heterodyne (electrical IQ) Polytec-class tracking filter parameters.

Architecture: RF -> downconvert -> complex baseband z(t) -> PLL carrier regen
(pure NCO exp(j*phi_hat)) -> FM discriminator.  NO homodyne residual window;
gear fn sets BOTH tracking dynamics AND measurement bandwidth.

Gear rule [自研], mirrors polytec_tracking_filter_sim.m mode_params:
  a_design(FAST) = 2*pi*f_acc*v_range,  f_acc = min(acq_bw, f_acc_cap)
  SLOW/MEDIUM/FAST = FAST/100, /10, /1
  fn = sqrt(a_design / (pi*lambda))     (e_ss = 1 rad design line)
"""
import math

LAMBDA = 632.8e-9          # HeNe (PSV-class); set 1550e-9 for IR systems
FS = 50e6                  # matches reference polytec sim / t5
ZETA = 0.707
ACQ_BW = 1e6               # acquisition bandwidth (Hz)
F_ACC_CAP = 100e3          # cap: "full-scale * MHz" acceleration not physical

BANDS = ('SLOW', 'MEDIUM', 'FAST')
RATIOS = {'SLOW': 1/100, 'MEDIUM': 1/10, 'FAST': 1.0}

GATE = dict(
  snr_on=1.0, snr_off=0.3, tauP=1e-6, tauF=1e-6,
  rel_on=0.20, rel_off=0.08, tauRef=200e-6, reacq=True,
)


def f3db_coef(zeta=ZETA):
  b = 2 + 4 * zeta ** 2
  return math.sqrt((b + math.sqrt(b ** 2 + 4)) / 2)


def b_loop(fn, zeta=ZETA):
  return math.pi * fn * (1 + 4 * zeta ** 2) / (4 * zeta)


def mode_params(v_range, acq_bw=ACQ_BW, f_acc_cap=F_ACC_CAP, lam=LAMBDA, zeta=ZETA):
  """Return dict per gear: a_design, fn, f_3db, B_loop."""
  f_acc = min(acq_bw, f_acc_cap)
  a_fast = 2 * math.pi * f_acc * v_range
  x3 = f3db_coef(zeta)
  out = {}
  for name in BANDS:
    a = a_fast * RATIOS[name]
    fn = math.sqrt(a / (math.pi * lam))
    out[name] = dict(
      v_range=v_range,
      a_design=a,
      fn=fn,
      f_3db=x3 * fn,
      B_loop=b_loop(fn, zeta),
      f_D_max=2 * v_range / lam,
      B_frontend=2 * 2 * v_range / lam,   # two-sided ENBW ~ 2*|f_D|_max
    )
  return out


def select_gear(v_range, f_vib, e_crit=1.0, acq_bw=ACQ_BW, f_acc_cap=F_ACC_CAP,
                  lam=LAMBDA, zeta=ZETA):
  """Pick gear from velocity range + vibration frequency (acceleration guard).

  1) Compute fn trio from v_range (Polytec rule).
  2) Required fn from vibration: fn_req = sqrt(2*f_v*v_range/(e_crit*pi*lam))
     (same as t5_heterodyne when e_crit=1 design line).
  3) Choose narrowest gear whose fn >= fn_req (else FAST).
  """
  mp = mode_params(v_range, acq_bw, f_acc_cap, lam, zeta)
  fn_req = math.sqrt(2 * f_vib * v_range / (e_crit * math.pi * lam))
  for name in BANDS:
    if mp[name]['fn'] >= fn_req * 0.95:
      return name, mp[name], fn_req
  return 'FAST', mp['FAST'], fn_req


def ceiling_db(v_range, fn, zeta=ZETA, lam=LAMBDA):
  """Heterodyne threshold-extension ceiling: 10*log10(f_D_max / B_loop)."""
  fD = 2 * v_range / lam
  return 10 * math.log10(fD / b_loop(fn, zeta))
