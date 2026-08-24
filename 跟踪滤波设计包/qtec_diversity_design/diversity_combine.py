"""QTec P1 baseline: non-coherent SNR-weighted velocity-domain combining.

Draebenstedt-style diversity route: every receiver channel is demodulated
INDEPENDENTLY (homodyne PLL carrier regeneration + optional common residual
window, i.e. exactly the gear_filter path of homodyne_tracking_design) and
FM-discriminated to a velocity v_k(t).  The M velocities are then combined
block-wise with SNR weights -- no cross-channel phase alignment is needed,
which is what makes this the pragmatic P1 baseline (coherent IQ-domain
combining is the P2 roadmap item).

Weight law (per block b, channel k):

    q_k = (C_k / Nhat_k)^alpha * LOCK_k * gs_k        alpha in {1, 2, inf}
    q_k < rel_x * max_j(q_j)  ->  q_k = 0             (cross-channel gate)
    w_k = q_k / sum_j(q_j)                            (normalisation)
    sum_j(q_j) == 0           ->  hold previous w     (all-dark HOLD flywheel)

alpha = 1 is velocity-domain MRC (post-FM noise variance ~ 1/SNR, so the
variance-optimal weight is ~ SNR for stationary Gaussian noise); alpha = 2
over-weights strong channels; alpha = inf is pure max-select (switching
diversity).  alpha = 2 is the recommended DEFAULT: FM click spikes from a
fading-but-still-locked channel are strongly non-Gaussian, and alpha = 1
under-suppresses them (validated at M=3 / CNR 6 dB, SLOW gear from
select_band(3 MHz, 20 mm/s): alpha=2 spike median 5.0 vs 5.5 for alpha=1
at a ~0.8 dB quiet-window SNR-gain cost, +2.75 vs +3.54 dB; alpha=inf has
the fewest spikes but keeps only +0.69 dB of averaging gain -- see
validate_diversity_p0_p1.py P1 table / results_diversity.txt).

C_k is NOT exposed by pll_carrier_regen, so estimate_C re-computes the
loop's internal carrier-power estimate outside the PLL: the same one-pole
IIR of |z|^2 with the same tauP, minus Nhat, clamped at 0 (wrapper
re-calculation, bit-compatible with the in-loop estimator up to the FFT
convolution's zero initial state).
"""
import math

import numpy as np

import _pkgpath  # noqa: F401  (sys.path bootstrap for the sibling package)
from homodyne_tracking_design.core import (
    pll_carrier_regen, iir1_lowpass, fir_lp_same, fm_discriminator,
)
from homodyne_tracking_design.design_params import (
    FS, LAMBDA, ZETA, B_WIN, NT_WIN, TAU_G, BANDS, gate_params,
)


def estimate_C(z, fs, Nhat, tauP):
    """Re-computed carrier power estimate C(t) = max(IIR(|z|^2, tauP) - Nhat, 0).

    Mirrors the P/C estimator inside pll_carrier_regen (same tauP one-pole
    IIR) so block weights use the same quantity the gate uses.
    """
    a = math.exp(-1.0 / (fs * tauP))
    P = iir1_lowpass(np.abs(z) ** 2, a)
    return np.maximum(P - Nhat, 0.0)


def channel_demod(z, fs, band, Nhat, gate='auto', use_residual=True):
    """One diversity channel: homodyne gear path + FM discriminator.

    use_residual=True runs the full gear_filter path (PLL carrier + common
    B_WIN residual window); False keeps the pure-NCO carrier path only.
    Returns dict(y, v, phi, state, gs, C, diag).
    """
    gp = gate_params(band)
    fn = BANDS[band]['fn']
    y_nco, phi, st, dg = pll_carrier_regen(z, fs, fn, Nhat, zeta=ZETA,
                                           gate=gate, **gp)
    if gate == 'always':
        gs = np.ones(z.size)
    else:
        gs = iir1_lowpass((st == 2).astype(float),
                          math.exp(-1.0 / (fs * TAU_G)))
    if use_residual:
        rot = np.exp(-1j * phi)
        rf = fir_lp_same(z * rot, B_WIN, fs, NT_WIN)
        resph = np.where(np.abs(rf) > 1e-12, np.angle(rf), 0.0)
        y = np.conj(rot) * np.exp(1j * gs * resph)
    else:
        y = y_nco
    C = estimate_C(z, fs, Nhat, gp['tauP'])
    v = fm_discriminator(y, fs, LAMBDA)
    return dict(y=y, v=v, phi=phi, state=st, gs=gs, C=C, diag=dg)


def block_weights(C, state, gs, Nhat, block, alpha=1.0, rel_x=0.05):
    """Block-wise combining weights with cross-channel gate and HOLD flywheel.

    C, state, gs : (M, N) arrays;  Nhat : (M,) per-channel noise power
    block        : block length in samples
    Returns w (M, nblk) normalised weights and dark (nblk,) bool -- blocks
    where every channel was gated out (weights held from the previous
    block: the all-dark HOLD flywheel; each channel's own NCO freewheels
    inside the PLL at the same time).
    """
    M, N = C.shape
    nblk = (N + block - 1) // block
    w = np.zeros((M, nblk))
    dark = np.zeros(nblk, dtype=bool)
    w_prev = np.full(M, 1.0 / M)          # cold-start: equal weights
    for b in range(nblk):
        s = slice(b * block, min((b + 1) * block, N))
        snr = C[:, s].mean(axis=1) / Nhat
        lockf = (state[:, s] == 2).mean(axis=1)
        gsf = gs[:, s].mean(axis=1)
        base = snr * lockf * gsf
        if math.isinf(alpha):
            q = np.zeros(M)
            if base.max() > 0.0:
                q[int(np.argmax(base))] = 1.0
        else:
            q = snr ** alpha * lockf * gsf
            qmax = q.max()
            if qmax > 0.0:
                q[q < rel_x * qmax] = 0.0
        tot = q.sum()
        if tot <= 0.0:
            w[:, b] = w_prev              # all-dark HOLD flywheel
            dark[b] = True
        else:
            w[:, b] = q / tot
            w_prev = w[:, b]
    return w, dark


def expand_weights(w, block, N):
    """(M, nblk) block weights -> (M, N) per-sample weights (zero-order hold)."""
    return np.repeat(w, block, axis=1)[:, :N]


def diversity_combine(z, fs=FS, band='FAST', Nhat=None, gate='auto',
                      use_residual=True, alpha=2.0, rel_x=0.05,
                      block_s=2e-6, chans=None):
    """Full P1 pipeline: M independent demodulators + weighted velocity sum.

    z      (M, N) complex IQ observations (1-D input = single channel)
    Nhat   scalar or (M,) per-channel noise power estimate
    chans  optional pre-computed [channel_demod(...)] list to reuse (lets a
           caller sweep alpha/rel_x/block_s without re-running the PLLs)

    Returns dict with the combined velocity v, block weights w, per-sample
    weights ws, dark (HOLD) blocks, dark_frac, block size, and chans.
    """
    z = np.atleast_2d(z)
    M, N = z.shape
    Nh = np.asarray(Nhat, dtype=float)
    if Nh.ndim == 0:
        Nh = np.full(M, float(Nh))
    if chans is None:
        chans = [channel_demod(z[k], fs, band, Nh[k], gate=gate,
                               use_residual=use_residual) for k in range(M)]
    C = np.stack([c['C'] for c in chans])
    st = np.stack([c['state'] for c in chans])
    gs = np.stack([np.broadcast_to(c['gs'], (N,)) for c in chans])
    block = max(1, int(round(block_s * fs)))
    w, dark = block_weights(C, st, gs, Nh, block, alpha=alpha, rel_x=rel_x)
    ws = expand_weights(w, block, N)
    vch = np.stack([c['v'] for c in chans])
    v = (ws * vch).sum(axis=0)
    return dict(v=v, w=w, ws=ws, dark=dark, dark_frac=float(dark.mean()),
                block=block, chans=chans)
