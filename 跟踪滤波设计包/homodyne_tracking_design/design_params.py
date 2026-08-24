"""1550 nm homodyne IQ three-gear (三档) tracking-filter parameter set.

Architecture (per gear)
-----------------------
  carrier path   PLL carrier regeneration (core.pll_carrier_regen) with the
                 gear's natural frequency fn -> pure-NCO phase phi.
                 Narrowband: gives the threshold extension (weak-light SNR
                 gain) and the dropout flywheel.
  measurement    residual window: r = z * e^{-j phi} is low-passed by a
                 COMMON linear-phase FIR window (B_WIN = 4 MHz is the
                 window's -6 dB cutoff) and recombined,
                 y_full = e^{j phi} * e^{j gs*angle(LP(r))}.
                 The window is centred on the tracked carrier and is
                 IDENTICAL in every gear, so switching gears never changes
                 the ultrasound bandwidth (this is what makes "all gears
                 <5 % amplitude error at 3 MHz" possible).  The flat
                 (<1 % amplitude error) measurement band is DC..~3.6 MHz;
                 4 MHz is the -6 dB point, NOT a flat-band edge
                 (validate_zeta_sweep.py Z0).

Click-cleanup condition (measured in V1 / zeta sweep): FM clicks are
removed by the COMPLEX low-pass inside the window only if the carrier loop
is slower than the window, B_loop < B_WIN.  With zeta = 1.2 SLOW
(0.49 MHz) and MEDIUM (2.34 MHz) satisfy it and reach the full threshold
extension at low frequency; FAST (B_loop = 7.1 MHz) tracks part of the
click energy into the NCO, so its low-frequency gain saturates near
+12 dB -- one more reason low-frequency targets MUST run in a low gear
(select_band enforces this).

Loop design rule (carrier path economy, review item #7)
-------------------------------------------------------
Closed-loop response of the II-type loop (continuous approx., x = f/fn):

    |H_L(x)|^2 = (1 + 4*zeta^2*x^2) / ((1 - x^2)^2 + 4*zeta^2*x^2)

The FULL measurement output y_full re-inserts the untracked residual
through the common FIR window, so output flatness does NOT depend on
|H_L|: the zeta sweep (validate_zeta_sweep.py, Z3-1) measures < 0.05 pp
amplitude-error spread across zeta in {0.7..2.65} on every gear x
frequency.  zeta therefore buys nothing at the output and only costs loop
bandwidth: B_loop = pi*fn*(1+4*zeta^2)/(4*zeta) = 8.62*fn at the earlier
zeta = 2.65 (chosen for +/-3 % NCO-path ripple -- the wrong object) vs
4.42*fn at zeta = 1.2, i.e. ~2.9 dB of threshold-extension ceiling.
zeta = 1.2 restores B_loop < B_WIN for MEDIUM (click cleanup, 100 kHz
gain +36.2 -> +38.1 dB) and lifts FAST@3MHz gain +2.2 -> +7.8 dB.  Lower
zeta (0.7/1.0) adds only ~1 dB more at FAST's 3 MHz design point but puts
FAST's low-frequency behaviour on the bimodal click-cleanup cliff
(B_loop ~ 1.3*B_WIN) and is underdamped -- rejected.  The NCO-path ripple
at zeta = 1.2 (+11 %/-11 % over the gear band) affects only the carrier
path alone (dropout flywheel, gear guard), which is insensitive to it.
fn = f_max / 1.875 is kept from the earlier plan: with the window-defined
output it no longer sets flatness, only the guard and B_loop scale.

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
ZETA = 1.2                 # carrier-loop economy; output flatness is set by
                           # the common FIR window, NOT |H_L| (review item #7,
                           # zeta sweep in validate_zeta_sweep.py)

# common residual measurement window (identical in every gear)
B_WIN = 4e6                # FIR -6 dB cutoff; flat (<1 % err) band DC..~3.6 MHz
# NT_WIN: linear-phase Hann-window FIR taps referenced to fs=250 MS/s
# (transition ~0.8 MHz).  A single-stage 1025-tap FIR at the full 250 MS/s
# rate is NOT practical in hardware; the real-time implementation must be a
# multirate equivalent (polyphase decimation to a lower rate, short FIR,
# interpolate back) with the same DC..B_WIN response and an NT_WIN/2-sample
# group-delay line on the NCO phase path.  Simulation (core.residual_mode
# and validate_tracking.gear_filter) runs the full-rate reference filter
# directly; both build it from core.fir_lp_kernel, so the validated window
# IS the product window (review item #4, see validate_residual_alignment.py).
NT_WIN = 1025
TAU_G = 2e-6               # residual soft-gate smoothing (dropout blanking)

_B_LOOP_COEF = math.pi * (1 + 4 * ZETA ** 2) / (4 * ZETA)   # 4.4244 (zeta=1.2)
# -3 dB closed-loop frequency coefficient: solve |H_L|^2 = 1/2 ->
# x^2 = ((2+4z^2) + sqrt((2+4z^2)^2+4))/2;  2.808 at zeta=1.2
_F3DB_COEF = math.sqrt(((2 + 4 * ZETA ** 2)
                        + math.hypot(2 + 4 * ZETA ** 2, 2)) / 2)

BANDS = {
  # fn = f_max / 1.875, rounded (kept from the earlier plan: output flatness
  # is window-defined, fn only scales the guard and B_loop -- see docstring);
  # gate constants scale with band dynamics.
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
    f_3db=_F3DB_COEF * fn,
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
  """Homodyne gear choice: narrowest band passing the tracking-error guard.

  Measurement bandwidth is set by the common B_WIN residual window, not by the
  gear's f_target_max.  Among gears whose untracked Doppler phase
  |1-H_L(f)| * phi_amp stays below PHI_GUARD, pick the narrowest (lowest
  B_loop) for best weak-light SNR.  If none pass, use the widest gear.
  """
  if v_peak is None:
    idx = next((i for i, n in enumerate(ORDER)
                if f_target_hz <= BANDS[n]['f_target_max']), len(ORDER) - 1)
    return ORDER[idx]
  for name in ORDER:
    if tracking_error_rad(f_target_hz, v_peak, BANDS[name]['fn']) <= PHI_GUARD:
      return name
  return ORDER[-1]


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
