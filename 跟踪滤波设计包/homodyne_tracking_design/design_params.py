"""1550 nm homodyne IQ three-gear (三档) tracking-filter parameter set.

Architecture (per gear)
-----------------------
  carrier path   PLL carrier regeneration (core.pll_carrier_regen) with the
                 gear's natural frequency fn -> pure-NCO phase phi.
                 Narrowband: gives the threshold extension (weak-light SNR
                 gain) and the dropout flywheel.
  measurement    residual window: r = z * e^{-j phi} is low-passed by a
                 COMMON linear-phase FIR window (cutoff B_WIN = 4 MHz) and
                 recombined,  y_full = e^{j phi} * e^{j gs*angle(LP(r))}.
                 The window is centred on the tracked carrier, so the
                 measurement band is DC..B_WIN in EVERY gear: switching
                 gears never changes the ultrasound bandwidth (this is what
                 makes "all gears <5 % amplitude error at 3 MHz" possible).

Click-cleanup condition (measured in V1): FM clicks are removed by the
COMPLEX low-pass inside the window only if the carrier loop is slower than
the window, B_loop < B_WIN.  SLOW (0.95 MHz) and MEDIUM (4.6 MHz) satisfy
it and reach the full threshold extension at low frequency; FAST
(B_loop = 13.8 MHz) tracks part of the click energy into the NCO, so its
low-frequency gain saturates near +2.5 dB -- one more reason low-frequency
targets MUST run in a low gear (select_band enforces this).

Loop design rule (carrier path, equal-ripple)
---------------------------------------------
Closed-loop response of the II-type loop (continuous approx., x = f/fn):

    |H_L(x)|^2 = (1 + 4*zeta^2*x^2) / ((1 - x^2)^2 + 4*zeta^2*x^2)

zeta = 2.65 keeps the NCO-path in-band ripple inside +/-3 % and
fn = f_max / 1.875 puts the band edge at the -3 % crossing, so the
carrier path itself is calibration-free over each gear's target band.
Cost: B_loop = pi*fn*(1+4*zeta^2)/(4*zeta) = 8.62*fn.

Gear selection rule (V4)
------------------------
Frequency-first, then a linear tracking-error guard for large motion:
for a sinusoidal velocity v_peak at f_target the Doppler phase amplitude
is phi_amp = 2*v_peak/(lambda*f_target) and the loop's untracked phase is

    phi_err = |1 - H_L(f_target)| * phi_amp    [rad]

The PLL phase detector wraps at +/-pi, so we require phi_err <= PHI_GUARD
(= 1.0 rad, safety margin below pi) and shift up one gear until it fits.
This replaces the earlier constant-acceleration guard, which is far too
pessimistic for sinusoidal motion reversing faster than the loop settles.
"""
import math

LAMBDA = 1550e-9
FS = 250e6
B_FRONTEND = 40e6          # complex-baseband two-sided ENBW (20e6 also legal)
ZETA = 2.65                # equal-ripple +/-3 % NCO path (see docstring)

# common residual measurement window (identical in every gear)
B_WIN = 4e6                # FIR cutoff: measurement band DC..4 MHz
NT_WIN = 1025              # FIR taps at 250 MS/s (transition ~0.8 MHz)
TAU_G = 2e-6               # residual soft-gate smoothing (dropout blanking)

_B_LOOP_COEF = math.pi * (1 + 4 * ZETA ** 2) / (4 * ZETA)   # 8.6215 (zeta=2.65)

BANDS = {
  # fn = f_max / 1.875 (equal-ripple edge), rounded; gate constants scale
  # with band dynamics.
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
ORDER = ('SLOW', 'MEDIUM', 'FAST')

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

PHI_GUARD = 1.0            # rad, max allowed untracked Doppler phase

# Legacy tentative plan (zeta=1.2) for regression checks in validate_tracking.py
LEGACY_ZETA = 1.2
LEGACY_FN = {'SLOW': 106e3, 'MEDIUM': 529e3, 'FAST': 1.589e6}


def gate_params(name):
  b = BANDS[name]
  return dict(tauP=b['tauP'], tauF=b['tauF'], **GATE_COMMON)


def loop_gains(fn, fs=FS, zeta=ZETA):
  th = 2 * math.pi * fn / fs
  return 2 * zeta * th, th * th          # Kp, Ki


def b_loop(fn):
  return _B_LOOP_COEF * fn


def band_specs(name, B_frontend=B_FRONTEND, cnr_db=3.0):
  b = BANDS[name]
  fn = b['fn']
  Kp, Ki = loop_gains(fn)
  B = b_loop(fn)
  cnr = 10 ** (cnr_db / 10)
  return dict(
    name=name, fn=fn, zeta=ZETA, Kp=Kp, Ki=Ki,
    f_target_max=b['f_target_max'],
    B_loop=B,
    f_3db=5.489 * fn,
    a_design=math.pi * LAMBDA * fn ** 2,
    B_win=B_WIN,
    ceiling_db=10 * math.log10((B_frontend / 2) / B),
    sigma_phi_at_cnr=math.sqrt(B / (cnr * B_frontend)),
    **gate_params(name),
  )


def loop_error_mag(f, fn, zeta=ZETA):
  """|1 - H_L| of the II-type loop at frequency f (continuous approx.)."""
  x = f / fn
  return x * x / math.sqrt((1 - x * x) ** 2 + (2 * zeta * x) ** 2)


def tracking_error_rad(f_target, v_peak, fn, lam=LAMBDA):
  """Untracked Doppler phase (rad) for sinusoidal motion v_peak @ f_target."""
  phi_amp = 2 * v_peak / (lam * f_target)
  return loop_error_mag(f_target, fn) * phi_amp


def select_band(f_target_hz, v_peak=None):
  """Frequency-first gear choice with a tracking-error guard.

  1. narrowest gear whose f_target_max covers the target frequency
     (lowest gear = largest carrier-path threshold extension);
  2. if the untracked Doppler phase |1-H_L(f_target)| * phi_amp exceeds
     PHI_GUARD rad (phase detector wraps at pi), shift up until it fits.
  """
  idx = next((i for i, n in enumerate(ORDER)
              if f_target_hz <= BANDS[n]['f_target_max']), len(ORDER) - 1)
  if v_peak is not None:
    while idx < len(ORDER) - 1 and tracking_error_rad(
        f_target_hz, v_peak, BANDS[ORDER[idx]]['fn']) > PHI_GUARD:
      idx += 1
  return ORDER[idx]


def as_struct_table():
  """Code-ready parameter table (mirrors the MATLAB struct in the docs)."""
  return {name: band_specs(name) for name in ORDER}


# --- Application: mostly <100 kHz, instrument max 3 MHz ---
APP_HYBRID = dict(
  typical_f_max=100e3,
  instrument_f_max=3e6,
  default_band='SLOW',
)

BAND_HYSTERESIS = {
  'SLOW_MEDIUM': dict(rise=200e3, fall=150e3),
  'MEDIUM_FAST': dict(rise=1e6, fall=800e3),
}


def select_band_hysteresis(f_target_hz, current_band='SLOW', v_peak=None):
  """Gear select with hysteresis: explicit fall from FAST/MEDIUM (audit item 6)."""
  idx = ORDER.index(current_band) if current_band in ORDER else 0

  if f_target_hz >= BAND_HYSTERESIS['MEDIUM_FAST']['rise']:
    idx = max(idx, 2)
  elif f_target_hz >= BAND_HYSTERESIS['SLOW_MEDIUM']['rise']:
    idx = max(idx, 1)

  if idx >= 2 and f_target_hz < BAND_HYSTERESIS['MEDIUM_FAST']['fall']:
    idx = 1
  if idx >= 1 and f_target_hz < BAND_HYSTERESIS['SLOW_MEDIUM']['fall']:
    idx = 0

  if v_peak is not None:
    guarded = select_band(f_target_hz, v_peak=v_peak)
    idx = max(idx, ORDER.index(guarded))
  return ORDER[idx]


def cfg_for_frequency(f_target_hz, current_band='SLOW', v_peak=None,
                      hysteresis=True):
  """Full config dict for the current measurement frequency."""
  band = (select_band_hysteresis(f_target_hz, current_band, v_peak)
          if hysteresis else select_band(f_target_hz, v_peak))
  return dict(band=band, f_target_hz=f_target_hz, **band_specs(band))
