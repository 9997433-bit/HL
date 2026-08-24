#!/usr/bin/env python3
"""Export golden (reference) vectors from the Python packages for the MATLAB port.

Writes MAT v4 files (readable natively by Octave/MATLAB `load`) into
matlab/golden/:

  heterodyne_golden.mat   design-parameter tables, transfer functions and a
                          PLL/discriminator chain driven by an EXPORTED input
                          (heterodyne core, gate='always')
  qtec_golden.mat         speckle statistics helpers on an EXPORTED field and
                          the full P1 diversity chain (channel_demod with the
                          gate='auto' 3-state PLL + block weights + combine)
                          driven by an EXPORTED multi-channel observation

Every random quantity is GENERATED here with seeded numpy PCG64 generators
and exported next to the outputs, so the Octave compare scripts feed the
EXACT same inputs into the ported functions: the comparison covers the
deterministic pipeline, never the RNG (which cannot match across languages).

No third-party dependency beyond numpy (MAT v4 writer is inlined).

Usage:  python3 matlab/export_heterodyne_qtec_golden.py
"""
import importlib.util
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent          # .../matlab
ROOT = HERE.parent                              # .../跟踪滤波设计包
OUT = HERE / 'golden'


# ------------------------------------------------------------- module loading
def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# heterodyne package (its module names 'core'/'design_params' would clash with
# the homodyne package, so load by explicit path under private names)
het_dp = _load('het_dp', ROOT / 'heterodyne_tracking_design/design_params.py')
het_core = _load('het_core', ROOT / 'heterodyne_tracking_design/core.py')

# homodyne + qtec (qtec reuses homodyne_tracking_design as a package)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'qtec_diversity_design'))
from homodyne_tracking_design import core as hom_core          # noqa: E402
from homodyne_tracking_design import design_params as hom_dp   # noqa: E402
import speckle_multi                                           # noqa: E402
import synth_multichannel as synth_mc                          # noqa: E402
import diversity_combine as divc                               # noqa: E402


# ------------------------------------------------------------- MAT v4 writer
def _mat4_matrix(fh, name, arr):
    a = np.asarray(arr)
    if a.dtype == bool:
        a = a.astype(np.float64)
    if a.ndim == 0:
        a = a.reshape(1, 1)
    elif a.ndim == 1:
        a = a.reshape(-1, 1)
    if a.ndim != 2:
        raise ValueError(f'{name}: only 0/1/2-D arrays supported')
    if len(name) > 19:
        raise ValueError(f'{name}: MAT v4 names limited to 19 chars')
    cplx = np.iscomplexobj(a)
    nm = name.encode('ascii') + b'\0'
    # type 0000: little-endian IEEE double, full numeric matrix
    fh.write(struct.pack('<5i', 0, a.shape[0], a.shape[1],
                         1 if cplx else 0, len(nm)))
    fh.write(nm)
    fh.write(np.real(a).astype('<f8').tobytes(order='F'))
    if cplx:
        fh.write(np.imag(a).astype('<f8').tobytes(order='F'))


def save_mat4(path, d):
    with open(path, 'wb') as fh:
        for k, v in d.items():
            _mat4_matrix(fh, k, v)
    print(f'  wrote {path}  ({path.stat().st_size / 1e6:.2f} MB, '
          f'{len(d)} variables)')


# ================================================================ heterodyne
def export_heterodyne():
    d = {}
    FS, LAM, BF = het_dp.FS, het_dp.LAMBDA, het_dp.B_FRONTEND
    ORDER = het_dp.ORDER

    # -- design-parameter table over v_range x mode ---------------------------
    rows = []
    for vr in (0.01, 0.1, 1.0, 3.0, 10.0):
        modes = het_dp.mode_params(vr)
        for i, name in enumerate(ORDER):
            m = modes[name]
            rows.append([vr, i + 1, m['fn'], m['f_3db'], m['B_loop'],
                         m['a_design'], m['a_slip'], m['valley_v'],
                         m['gain_db'], m['noise_red_db'],
                         1.0 if het_dp.fn_discrete_ok(m['fn']) else 0.0])
    d['mp_table'] = np.array(rows)
    d['b_loop_coef'] = het_dp.B_LOOP_COEF
    d['f3db_coef'] = het_dp.F3DB_COEF
    d['v_if'] = het_dp.v_if_limit()
    d['v_alias'] = het_dp.v_alias_limit()

    # -- select_mode demo cases (index into ORDER; v_peak NaN = None) ---------
    cases = [(20e3, 0.05), (100e3, 0.05), (100e3, 1.0), (5e6, 0.01),
             (150e3, float('nan')), (2e6, float('nan'))]
    sel = []
    for f0, vp in cases:
        s = het_dp.select_mode(f0, None if np.isnan(vp) else vp)
        sel.append([f0, vp, ORDER.index(s) + 1])
    d['selmode'] = np.array(sel)

    # -- transfer-function grids (MEDIUM fn, default v_range 1.0) -------------
    fnM = het_dp.mode_params(1.0)['MEDIUM']['fn']
    fgrid = np.concatenate(([0.0], np.logspace(3, 7, 41)))
    d['tf_f'] = fgrid
    d['tf_fn'] = fnM
    d['tf_lem'] = np.array([het_dp.loop_error_mag(f, fnM) for f in fgrid[1:]])
    d['tf_lgm'] = np.array([het_dp.loop_gain_mag(f, fnM) for f in fgrid[1:]])
    d['tf_vpll'] = np.array([het_dp.v_pll_limit(f, fnM) for f in fgrid[1:]])
    d['tf_terr'] = np.array([het_dp.tracking_error_rad(f, 0.1, fnM)
                             for f in fgrid[1:]])
    d['tf_hl'] = het_core.hl_response(fgrid, FS, fnM, het_dp.ZETA)

    # -- burst_signal (pure function of t) ------------------------------------
    Nb = 2000
    tb = np.arange(Nb) / FS
    xb, vb, eb = het_core.burst_signal(tb, 50e3, 10e-3, 10, 5e-6)
    d['burst_x'] = xb
    d['burst_v'] = vb
    d['burst_env'] = eb

    # -- PLL chain, case A: 50 kHz burst + 20 kHz carrier offset + noise ------
    # (heterodyne core, gate='always' -- the only gate mode heterodyne uses;
    # the MATLAB port shares the homodyne pll_carrier_regen, bit-identical in
    # this mode)
    N = 40000
    t = np.arange(N) / FS
    x, v, _ = het_core.burst_signal(t, 50e3, 10e-3, 10, 0.15e-3)
    ph = 4 * np.pi / LAM * x + 2 * np.pi * 20e3 * t
    s2 = 10 ** (-10 / 10)
    rng = np.random.default_rng(123456)
    z = np.exp(1j * ph) + het_core.complex_bandlimited_noise(N, FS, BF, s2, rng)
    d['pllA_z'] = z
    d['pllA_fn'] = fnM
    d['pllA_s2'] = s2
    y, phi, state, dg = het_core.pll_carrier_regen(
        z, FS, fnM, s2, zeta=het_dp.ZETA, gate='always')
    d['pllA_phi'] = phi
    d['pllA_diag'] = np.array([dg['near_pi_events'], dg['n_hold'],
                               dg['n_acquire'], dg['n_lock_entries'],
                               dg['lock_frac']])
    vd = het_core.fm_discriminator(y, FS, LAM)
    d['pllA_vd'] = vd
    d['pllA_fir'] = het_core.fir_lp(vd, 100e3, FS, 257)
    Pw, fw = het_core.welch_psd(vd[t > 0.4e-3], FS, 4096)
    d['pllA_psd'] = Pw
    Wm = (t > 0.15e-3) & (t < 0.15e-3 + 10 / 50e3)
    d['pllA_lock'] = het_core.lockin_amp(vd, t, 50e3, Wm)
    d['pllA_iir'] = het_core.iir1_lowpass(
        np.abs(z) ** 2, float(np.exp(-1.0 / (FS * 1e-6))))

    # -- PLL chain, case B: large dynamics near the bathtub boundary ----------
    # (sine at f_v = fn, vamp = 0.5 * v_pi: big phase errors, near-pi events)
    N2 = 20000
    t2 = np.arange(N2) / FS
    f_v = fnM
    vamp = 0.5 * het_dp.v_pll_limit(f_v, fnM)
    x2 = vamp / (2 * np.pi * f_v) * (1 - np.cos(2 * np.pi * f_v * t2))
    ph2 = 4 * np.pi / LAM * x2
    rng2 = np.random.default_rng(654321)
    s2b = 10 ** (-30 / 10)
    z2 = (np.exp(1j * ph2)
          + het_core.complex_bandlimited_noise(N2, FS, BF, s2b, rng2))
    d['pllB_z'] = z2
    d['pllB_fn'] = fnM
    d['pllB_s2'] = s2b
    y2, phi2, _, dg2 = het_core.pll_carrier_regen(
        z2, FS, fnM, s2b, zeta=het_dp.ZETA, gate='always')
    d['pllB_phi'] = phi2
    d['pllB_nearpi'] = dg2['near_pi_events']

    save_mat4(OUT / 'heterodyne_golden.mat', d)


# ================================================================ qtec
def export_qtec():
    d = {}
    FS, LAM = hom_dp.FS, hom_dp.LAMBDA

    # -- P0 statistics helpers on an EXPORTED field ---------------------------
    d['fade_theory'] = np.array(
        [[F, M, speckle_multi.fade_prob_theory(F, M)]
         for F in (0.3567, 0.105) for M in (1, 3, 4)])
    rng = np.random.default_rng(777)
    h = speckle_multi.make_speckle_multi(20000, 400e3, 50e-6, 3,
                                         rho=0.5, rng=rng)
    d['h_field'] = h
    d['h_jff'] = np.array(
        [[F,
          speckle_multi.joint_fade_fraction(h, F),
          speckle_multi.joint_fade_fraction(h[0:1], F),
          speckle_multi.joint_fade_fraction(h[1:2], F),
          speckle_multi.joint_fade_fraction(h[2:3], F)]
         for F in (0.3567, 0.105)])
    d['h_corr'] = speckle_multi.channel_correlation(h)

    # -- P1 chain on an EXPORTED multi-channel observation --------------------
    # 3 MHz burst through 3 speckle channels at CNR 6 dB (the validator's
    # scene, shortened to 0.2 ms), demodulated with the SLOW gear
    # (select_band(3 MHz, 20 mm/s), guard-first) and combined for
    # alpha in {1, 2, inf}.
    T = 0.2e-3
    N = int(T * FS)
    t = np.arange(N) / FS
    x, v_true, _ = hom_core.burst_signal(t, 3e6, 20e-3, 60, 0.05e-3)
    phi = synth_mc.doppler_phase(x)
    band = hom_dp.select_band(3e6, 20e-3)
    d['band_idx'] = hom_dp.ORDER.index(band) + 1
    cnr_db = 6.0
    s2 = 10.0 ** (-cnr_db / 10.0)
    rng = np.random.default_rng(999)
    syn = synth_mc.synth_multichannel(phi, FS, 3, cnr_db, rng,
                                      tau_c=50e-6, B_noise=20e6)
    z = syn['z']
    d['p1_z'] = z
    d['p1_psi'] = syn['psi']
    d['p1_s2'] = s2

    chans = [divc.channel_demod(z[k], FS, band, s2) for k in range(3)]
    d['p1_v'] = np.stack([c['v'] for c in chans])
    d['p1_state'] = np.stack([c['state'].astype(float) for c in chans])
    d['p1_C'] = np.stack([c['C'] for c in chans])
    d['p1_gs'] = np.stack([c['gs'] for c in chans])
    d['p1_diag'] = np.array([[c['diag']['near_pi_events'],
                              c['diag']['n_hold'],
                              c['diag']['n_acquire'],
                              c['diag']['n_lock_entries'],
                              c['diag']['lock_frac']] for c in chans])

    import math
    for tag, a in (('a1', 1.0), ('a2', 2.0), ('ainf', math.inf)):
        res = divc.diversity_combine(z, FS, band=band, Nhat=s2,
                                     alpha=a, chans=chans)
        d[f'p1_w_{tag}'] = res['w']
        d[f'p1_vc_{tag}'] = res['v']
        d[f'p1_dark_{tag}'] = res['dark'].astype(float)
    d['p1_block'] = res['block']

    save_mat4(OUT / 'qtec_golden.mat', d)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print('exporting heterodyne golden ...')
    export_heterodyne()
    print('exporting qtec golden ...')
    export_qtec()
    print('done.')


if __name__ == '__main__':
    main()
