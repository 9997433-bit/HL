"""1550 nm homodyne IQ tracking-filter band plan.

Design rule: decouple per-band natural frequency fn from the usage-band
edge.  The old rule fn = f_max / x_3dB forces FAST fn too low for a flat
3 MHz response.  Here each band picks the smallest fn that still meets the
amplitude budget at its upper frequency, maximising weak-light SNR gain.
"""
import math

LAMBDA = 1550e-9
FS = 250e6
B_FRONTEND = 40e6
ZETA = 1.2

# Closed-loop -3 dB edge coefficient for this discrete II-type loop (zeta=1.2)
_X3DB = 2.8083
_B_LOOP_COEF = math.pi * (1 + 4 * ZETA ** 2) / (4 * ZETA)  # 4.4244

BANDS = {
  # Target band edge (Hz) | fn (Hz) | analytic |H| at band edge | role
  'SLOW': {
    'f_target_max': 100e3,
    'fn': 80e3,
    'label': '结构/低频 ≤100 kHz',
  },
  'MEDIUM': {
    'f_target_max': 1e6,
    'fn': 680e3,
    'label': '常用 ≤1 MHz',
  },
  'FAST': {
    'f_target_max': 3e6,
    'fn': 1.85e6,
    'label': '最高 3 MHz',
  },
}

PLL_GATE = dict(
  snr_on=1.0,
  snr_off=0.3,
  tauP=1e-6,
  tauF=1e-6,
  tauRef=200e-6,
  rel_on=0.20,
  rel_off=0.08,
  reacq=True,
)

# Legacy equal-edge plan (for comparison in validation)
LEGACY_FN = {k: BANDS[k]['f_target_max'] / _X3DB for k in BANDS}


def select_band(f_target_hz):
  """Pick the narrowest band that still covers the target frequency."""
  order = ('SLOW', 'MEDIUM', 'FAST')
  for name in order:
    if f_target_hz <= BANDS[name]['f_target_max']:
      return name
  return 'FAST'


def band_specs(name, B_frontend=B_FRONTEND):
  b = BANDS[name]
  fn = b['fn']
  B_loop = _B_LOOP_COEF * fn
  f_3db = _X3DB * fn
  a_design = math.pi * LAMBDA * fn ** 2
  ceiling_db = 10 * math.log10((B_frontend / 2) / B_loop)
  return dict(
    name=name,
    fn=fn,
    f_target_max=b['f_target_max'],
    B_loop=B_loop,
    f_3db=f_3db,
    a_design=a_design,
    ceiling_db=ceiling_db,
  )
