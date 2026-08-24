#!/usr/bin/env python3
"""Python golden export for the MATLAB/Octave homodyne port smoke tests.

Runs the SAME fixed-seed smoke suite as matlab/export_golden_core.m against
the reference Python implementation (homodyne_tracking_design: core,
design_params, ellipse_correction) and writes matlab/golden/core_smoke_py.mat
via scipy.io.savemat -- or matlab/golden/core_smoke_py.json (loaded on the
Octave side with jsondecode) when scipy is unavailable.

Cross-language determinism: numpy's default_rng (PCG64) stream cannot be
reproduced by MATLAB rng(seed), so all noise comes from PortableLCG below --
a Park-Miller minstd LCG + Box-Muller identical to matlab/homodyne/core/
lcg_init.m + lcg_randn.m (exact in double precision on both sides).  Test
signals are additionally built sample-wise with math.* so the byte streams
feeding the scalar PLL loop and the ellipse fits are bit-identical, and the
comparison (matlab/compare_with_python.m) holds at rtol = 1e-10.

Encoding conventions (shared with export_golden_core.m):
  band names  -> gear index, SLOW=1, MEDIUM=2, FAST=3
  Python None -> -1
  booleans    -> 1/0

Usage (from the package root, or anywhere):
  python3 matlab/export_python_golden.py
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

_PKG_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_PKG_ROOT))

from homodyne_tracking_design import core, design_params  # noqa: E402
from homodyne_tracking_design import ellipse_correction as ec  # noqa: E402


class PortableLCG:
    """minstd LCG + Box-Muller; twin of matlab lcg_init/lcg_randn.

    Each normal consumes exactly two uniforms (cos branch only, no spare
    caching).  48271*(2^31-2) < 2^53 so the recurrence is exact in doubles.
    Exposes standard_normal(k) so it can stand in for a numpy Generator in
    core.complex_bandlimited_noise / core.make_speckle.
    """

    M = 2147483647
    A = 48271

    def __init__(self, seed):
        s = int(seed) % self.M
        self.s = 1 if s == 0 else s

    def _u(self):
        self.s = (self.A * self.s) % self.M
        return self.s / self.M

    def standard_normal(self, n):
        out = np.empty(int(n))
        for i in range(int(n)):
            u1 = self._u()
            u2 = self._u()
            out[i] = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
        return out


ORDER = design_params.ORDER


def bidx(name):
    return float(ORDER.index(name) + 1)


def enc(v):
    """None -> -1 (also NaN, for symmetry with the MATLAB port); bool -> 1/0."""
    if v is None:
        return -1.0
    if isinstance(v, float) and math.isnan(v):
        return -1.0
    return float(v)


def spec_vec(s):
    return np.array([s['fn'], s['zeta'], s['Kp'], s['Ki'], s['f_target_max'],
                     s['B_loop'], s['f_3db'], s['a_design'], s['B_win'],
                     s['ceiling_db'], s['sigma_phi_at_cnr'],
                     s['snr_on'], s['snr_off'], s['rel_on'], s['rel_off'],
                     s['tauRef'], float(s['reacq']), s['tauP'], s['tauF']])


def main():
    G = {}

    # ---------------------------------------------------------- S1 FIR kernel
    G['fir_kernel'] = np.array(core.fir_lp_kernel(4e6, 250e6, 1025), copy=True)

    # ---------------------------------------------------------- S2/S3 burst
    fs_b = 10e6
    Nb = 4000
    t_b = np.arange(Nb) / fs_b
    bx, bv, be = core.burst_signal(t_b, 1e5, 0.02, 5, 5e-5)
    G['burst_x'] = bx
    G['burst_v'] = bv
    G['burst_env'] = be
    G['lockin_val'] = np.array([core.lockin_amp(bv, t_b, 1e5, be > 0)])
    G['fir_lp_y'] = core.fir_lp(bx, 2e5, fs_b)[:1000]

    # ---------------------------------------------------------- S4 H_L(f)
    f_hl = np.array([0, 1e3, 1e4, 1e5, 2e5, 5e5, 1e6, 2e6, 3e6])
    H = core.hl_response(f_hl, 250e6, 110e3, 1.2)
    G['hl_slow_re'], G['hl_slow_im'] = H.real, H.imag
    H = core.hl_response(f_hl, 250e6, 530e3, 1.2)
    G['hl_med_re'], G['hl_med_im'] = H.real, H.imag
    H = core.hl_response(f_hl, 250e6, 1.6e6, 1.2)
    G['hl_fast_re'], G['hl_fast_im'] = H.real, H.imag

    # ---------------------------------------------------------- S5 gear select
    f_nov = [50e3, 150e3, 200e3, 250e3, 500e3, 1e6, 1.5e6, 3e6, 5e6]
    G['selband_nov'] = np.array([bidx(design_params.select_band(f))
                                 for f in f_nov])
    fv = [(100e3, 30.0), (3e6, 0.02), (1e6, 1.0), (200e3, 0.5),
          (100e3, 0.001), (500e3, 0.05)]
    G['selband_v'] = np.array([bidx(design_params.select_band(f, v))
                               for f, v in fv])
    hy = [(50e3, 'FAST', None), (3e6, 'SLOW', None), (50e3, 'MEDIUM', None),
          (1e6, 'SLOW', None), (100e3, 'BOGUS', None), (200e3, 'FAST', 0.5)]
    G['selband_hyst'] = np.array(
        [bidx(design_params.select_band_hysteresis(f, cb, v))
         for f, cb, v in hy])

    # ---------------------------------------------------------- S6 band specs
    G['specs_slow'] = spec_vec(design_params.band_specs('SLOW'))
    G['specs_med'] = spec_vec(design_params.band_specs('MEDIUM'))
    G['specs_fast'] = spec_vec(design_params.band_specs('FAST'))
    G['loop_misc'] = np.array([
        design_params._B_LOOP_COEF, design_params._F3DB_COEF,
        design_params.loop_error_mag(1e5, 110e3),
        design_params.tracking_error_rad(1e5, 0.5, 530e3),
        design_params.PHI_GUARD])
    gf = design_params.guard_flags(1e5, 30.0, 'FAST')
    G['guard_fast'] = np.array([gf['phi_err'], float(gf['guard_ok']),
                                float(gf['overrange'])])
    T = design_params.as_struct_table()
    G['table_val'] = np.array([T['SLOW']['fn'], T['MEDIUM']['Kp'],
                               T['FAST']['B_loop']])

    # ---------------------------------------------------------- S7 cfg structs
    cfgs = [design_params.cfg_for_frequency(3e6, 0.02),
            design_params.cfg_for_frequency(100e3, 30.0),
            design_params.cfg_for_frequency(150e3),
            design_params.cfg_for_frequency(3e6, None, 'SLOW', True),
            design_params.cfg_for_frequency(50e3, None, 'FAST', True)]
    flags = []
    for c in cfgs:
        flags += [bidx(c['band']), enc(c['phi_err']), enc(c['guard_ok']),
                  enc(c['overrange'])]
    G['cfg_flags'] = np.array(flags)
    cfl = design_params.cfg_for_frequency(1e6, None, 'SLOW', True, 'fixed_lp')
    G['cfg_fixed'] = np.array([cfl['B_win'], float(cfl['NT_win'])])

    # ---------------------------------------------------------- S8 PLL smoke
    fs = 10e6
    Npll = 20000
    sigma = 0.05
    Nhat = sigma ** 2
    lcg = PortableLCG(12345)
    nr = lcg.standard_normal(Npll)
    ni = lcg.standard_normal(Npll)
    s2 = sigma / math.sqrt(2)
    z = np.empty(Npll, complex)
    for i in range(Npll):
        t = i / fs
        ph = (2 * math.pi * 200e3) * t + 0.8 * math.sin((2 * math.pi * 5e3) * t)
        env = 0.02 if 8000 <= i < 9000 else 1.0
        z[i] = complex(env * math.cos(ph) + s2 * nr[i],
                       env * math.sin(ph) + s2 * ni[i])

    _, phi_p, state_p, dg = core.pll_carrier_regen(
        z, fs, 530e3, Nhat, zeta=1.2, tauP=2e-6, tauF=2e-6, gate='auto')
    G['pll_phi_head'] = phi_p[:2000]
    G['pll_phi_tail'] = phi_p[-2000:]
    G['pll_state_counts'] = np.array([float(np.sum(state_p == 0)),
                                      float(np.sum(state_p == 1)),
                                      float(np.sum(state_p == 2))])
    G['pll_diag'] = np.array([dg['near_pi_events'], dg['n_hold'],
                              dg['n_acquire'], dg['n_lock_entries'],
                              dg['n_reacq'], dg['lock_frac']], float)
    _, phi_a, _, _ = core.pll_carrier_regen(
        z, fs, 530e3, Nhat, zeta=1.2, tauP=2e-6, tauF=2e-6, gate='always')
    G['pll_always_phi'] = phi_a[:2000]

    # ------------------------------------------------- S9 tracking_filter smoke
    # explicit v_peak=0.02 keeps SLOW: v_peak=None now defaults to
    # APP_V_PEAK_MAX=30 m/s -> FAST in overrange, where cycle-slip timing
    # amplifies 1-ulp cross-language differences (S7 already covers the
    # None-default selection logic bit-exactly).
    cfg = design_params.cfg_for_frequency(200e3, 0.02, 'SLOW', True,
                                          'pll', 'auto')
    y_t, phi_t, state_t, _ = core.tracking_filter(z, fs, cfg, Nhat)
    G['trk_y_re'] = y_t[5000:6000].real
    G['trk_y_im'] = y_t[5000:6000].imag
    G['trk_phi'] = phi_t[5000:6000]
    G['trk_state_counts'] = np.array([float(np.sum(state_t == 0)),
                                      float(np.sum(state_t == 1)),
                                      float(np.sum(state_t == 2))])
    fmv = core.fm_discriminator(y_t, fs, 1550e-9)
    G['trk_fm'] = fmv[5000:6000]

    # ------------------------------------------------- S10 off / fixed_lp modes
    _, phi_off, _, _ = core.off_mode(z)
    G['off_phi'] = phi_off[:1000]
    y_fx, _, _, _ = core.fixed_lp_mode(z, fs, 4e6, 1025)
    G['fx_y_re'] = y_fx[5000:6000].real
    G['fx_y_im'] = y_fx[5000:6000].imag

    # ---------------------------------------------------------- S11 iir1 / welch
    x_iir = np.array([math.sin((2 * math.pi * 3e3) * (i / fs))
                      + (1.0 if i % 7 == 0 else 0.0) for i in range(5000)])
    y_iir = core.iir1_lowpass(x_iir, math.exp(-1 / (fs * 2e-6)))
    G['iir1_y'] = y_iir[:1000]
    Pw, fw = core.welch_psd(z, fs, 1024)
    G['welch_P'] = Pw
    G['welch_f'] = fw

    # --------------------------------------------------- S12 LCG noise / speckle
    nb_ = core.complex_bandlimited_noise(4096, 10e6, 2e6, 0.5,
                                         PortableLCG(4242))
    G['noise_re'] = nb_[:500].real
    G['noise_im'] = nb_[:500].imag
    sp = core.make_speckle(4096, 10e6, 1e-4, PortableLCG(999), 0.5)
    G['speckle_re'] = sp[:500].real
    G['speckle_im'] = sp[:500].imag

    # ---------------------------------------------------------- S13 Heydemann fit
    Ne = 6000
    d0 = 8 * math.pi / 180
    lcg = PortableLCG(777)
    n1 = lcg.standard_normal(Ne)
    n2 = lcg.standard_normal(Ne)
    u_e = np.empty(Ne)
    v_e = np.empty(Ne)
    for i in range(Ne):
        a = (0.85 * 2 * math.pi) * i / Ne
        u_e[i] = (0.12 + 1.05 * math.cos(a)) + 0.01 * n1[i]
        v_e[i] = (-0.08 + 0.92 * math.sin(a + d0)) + 0.01 * n2[i]
    par, res = ec.heydemann_fit(u_e, v_e)
    G['hey_par'] = np.array([par['p'], par['q'], par['A'], par['B'],
                             par['delta']])
    G['hey_res'] = np.array([res['rms'], res['algebraic_rms'], res['arc'],
                             res['arc_all'], res['design_cond'],
                             float(res['ok'])])
    G['hey_theta'] = np.asarray(res['theta'], float)
    _, _, z_h = ec.heydemann_apply(u_e, v_e, par)
    G['hey_z_re'] = z_h[:500].real
    G['hey_z_im'] = z_h[:500].imag
    G['hey_arc_corr'] = np.array([ec.arc_span_corrected(u_e, v_e, par)])

    # ---------------------------------------------------------- S14 gated fit
    prev = dict(p=0.13, q=-0.09, A=1.071, B=0.9016, delta=d0 + 0.01)
    gp, gres = ec.fit_arc_gated(u_e, v_e, prev)
    G['gated_par'] = np.array([gp['p'], gp['q'], gp['A'], gp['B'],
                               gp['delta']])
    G['gated_flags'] = np.array([float(gres['ok']), gres['arc']])

    # --------------------------------------- S15 segmented / interp / online p,q
    Nl = 12000
    fs_e = 1000.0
    lcg = PortableLCG(2024)
    m1 = lcg.standard_normal(Nl)
    m2 = lcg.standard_normal(Nl)
    u_l = np.empty(Nl)
    v_l = np.empty(Nl)
    for i in range(Nl):
        a = (2 * math.pi * 6) * i / Nl
        u_l[i] = ((0.12 + 0.05 * i / Nl) + 1.05 * math.cos(a)) + 0.008 * m1[i]
        v_l[i] = (-0.08 + 0.92 * math.sin(a + d0)) + 0.008 * m2[i]
    t_c, pars, oks, arcs = ec.segmented_heydemann(u_l, v_l, fs_e, seg_len=2.0)
    G['seg_t_c'] = t_c
    G['seg_oks'] = oks.astype(float)
    G['seg_arcs'] = arcs
    G['seg_p'] = np.array([pk['p'] for pk in pars])
    G['seg_q'] = np.array([pk['q'] for pk in pars])
    G['seg_A'] = np.array([pk['A'] for pk in pars])
    G['seg_B'] = np.array([pk['B'] for pk in pars])
    G['seg_delta'] = np.array([pk['delta'] for pk in pars])
    t_q = np.arange(Nl) / fs_e
    trk = ec.interp_par_track(t_q, t_c, pars)
    G['interp_p'] = trk['p'][::50]
    z_a = ec.apply_par_track(u_l, v_l, trk)
    G['apl_z_re'] = z_a[:500].real
    G['apl_z_im'] = z_a[:500].imag

    gd0 = dict(p=0.12, q=-0.08, A=1.05, B=0.92, delta=d0)
    ob = ec.OnlineBiasTracker(gd0, fs_e, blk_s=0.1)
    z_o = ob.run(u_l, v_l)
    G['obt_pq'] = np.array([ob.p, ob.q])
    G['obt_z_re'] = z_o[-500:].real
    G['obt_z_im'] = z_o[-500:].imag

    # ---------------------------------------------------------------- save
    gdir = Path(__file__).resolve().parent / 'golden'
    gdir.mkdir(parents=True, exist_ok=True)
    G = {k: np.asarray(v, float) for k, v in G.items()}
    try:
        from scipy.io import savemat
        out = gdir / 'core_smoke_py.mat'
        savemat(str(out), G, oned_as='column')
    except ImportError:
        out = gdir / 'core_smoke_py.json'
        payload = {k: [None if math.isnan(x) else x for x in v.ravel()]
                   for k, v in G.items()}
        with open(out, 'w') as fh:
            json.dump(payload, fh)
    print(f'export_python_golden: wrote {out} ({len(G)} fields)')


if __name__ == '__main__':
    main()
