"""Synthesize M-channel homodyne IQ observations for diversity simulation.

Each receiver channel k sees the SAME optical Doppler phase phi(t) through
its own speckle field h_k(t) (amplitude a_k and speckle phase), an own
static phase offset psi_k, and its own independent front-end noise:

    z_k(t) = h_k(t) * exp(j*(phi(t) + psi_k)) + n_k(t)

Constants (FS, LAMBDA, B_FRONTEND) are imported from
homodyne_tracking_design.design_params -- single source of truth, no fork.
"""
import numpy as np

import _pkgpath  # noqa: F401  (sys.path bootstrap for the sibling package)
from homodyne_tracking_design.core import complex_bandlimited_noise
from homodyne_tracking_design.design_params import FS, LAMBDA, B_FRONTEND  # noqa: F401 (re-export)
from speckle_multi import make_speckle_multi


def doppler_phase(x, lam=LAMBDA):
    """Optical Doppler phase of a homodyne IQ link for displacement x(t)."""
    return 4.0 * np.pi / lam * x


def synth_multichannel(phi, fs, M, cnr_db, rng, tau_c=None, rho=0.0,
                       B_noise=20e6, psi=None):
    """M-channel IQ synthesis  z_k = h_k * exp(j(phi + psi_k)) + n_k.

    phi     (N,) optical Doppler phase [rad] (use doppler_phase(x))
    tau_c   speckle correlation time [s]; None -> static unit-amplitude
            channels (a_k = 1, only the psi_k offsets differ)
    rho     pairwise speckle field correlation (see make_speckle_multi)
    cnr_db  mean per-channel CNR [dB]: E|h_k|^2 = 1, noise power = 10^(-CNR/10)
    B_noise two-sided noise ENBW [Hz] per channel
    psi     (M,) static per-channel phase offsets [rad]; None -> uniform random

    Returns dict(z=(M,N) complex, h=(M,N), psi=(M,), s2=noise power/channel).
    """
    phi = np.asarray(phi, dtype=float)
    N = phi.size
    s2 = 10.0 ** (-cnr_db / 10.0)
    if psi is None:
        psi = rng.uniform(-np.pi, np.pi, M)
    else:
        psi = np.asarray(psi, dtype=float)
    if tau_c is None:
        h = np.ones((M, N), dtype=complex)
    else:
        h = make_speckle_multi(N, fs, tau_c, M, rho=rho, rng=rng)
    carrier = np.exp(1j * phi)
    z = np.empty((M, N), dtype=complex)
    for k in range(M):
        n = complex_bandlimited_noise(N, fs, B_noise, s2, rng)
        z[k] = h[k] * carrier * np.exp(1j * psi[k]) + n
    return dict(z=z, h=h, psi=psi, s2=s2)
