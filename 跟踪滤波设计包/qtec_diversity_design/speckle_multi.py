"""M-channel speckle fields for QTec-style diversity simulation (P0).

Builds on homodyne_tracking_design.core.make_speckle (band-limited complex
Rayleigh speckle, Gaussian Doppler spectrum, R(tau_c) = 1/e) and adds:

  make_speckle_multi    M channels, independent (rho = 0) or with pairwise
                        complex FIELD correlation rho (common + independent
                        mixture: h_k = sqrt(rho) h_c + sqrt(1-rho) g_k)
  fade_prob_theory      Rayleigh: P(I < F*<I>) = 1 - exp(-F); joint fade of
                        M independent channels = (1 - exp(-F))^M
  joint_fade_fraction   measured time fraction where ALL channels fade
  channel_correlation   empirical pairwise complex field correlation matrix

Physics behind QTec diversity: a single-detector LDV drops out whenever its
one speckle realisation fades.  M spatially separated receivers see
(near-)independent speckle patterns, so they fade JOINTLY only with
probability ~ p^M.  This p^M law is the entire value proposition of the
diversity receiver and is what validate_diversity_p0_p1.py (P0) asserts.
"""
import numpy as np

import _pkgpath  # noqa: F401  (sys.path bootstrap for the sibling package)
from homodyne_tracking_design.core import make_speckle


def make_speckle_multi(N, fs, tau_c, M, rho=0.0, rng=None):
    """M-channel band-limited Rayleigh speckle, shape (M, N) complex.

    rho is the pairwise complex FIELD correlation E[h_j h_k*] (j != k),
    built as h_k = sqrt(rho)*h_common + sqrt(1-rho)*g_k with h_common and
    g_k independent make_speckle draws.  The corresponding INTENSITY
    correlation is |rho|^2 (jointly-Gaussian speckle).  Each channel is
    re-normalised to unit sample mean power so per-channel CNR definitions
    stay exact.  rho = 0 gives fully independent channels.
    """
    if rng is None:
        rng = np.random.default_rng()
    if not (0.0 <= rho < 1.0):
        raise ValueError('rho must be in [0, 1)')
    common = make_speckle(N, fs, tau_c, rng) if rho > 0.0 else None
    h = np.empty((M, N), dtype=complex)
    for k in range(M):
        g = make_speckle(N, fs, tau_c, rng)
        hk = np.sqrt(rho) * common + np.sqrt(1.0 - rho) * g if rho > 0.0 else g
        h[k] = hk / np.sqrt(np.mean(np.abs(hk) ** 2))
    return h


def fade_prob_theory(F, M=1):
    """Joint deep-fade probability of M INDEPENDENT Rayleigh channels.

    F is the intensity threshold relative to the per-channel mean intensity
    (e.g. F = 0.105 is a ~ -9.8 dB deep fade).  Single channel:
    p = P(I < F*<I>) = 1 - exp(-F);  M independent channels: p^M.
    """
    return (1.0 - np.exp(-F)) ** M


def joint_fade_fraction(h, F):
    """Measured fraction of samples where ALL channels' intensity < F*<I_k>.

    h: (M, N) complex (a 1-D array is treated as a single channel).
    """
    h = np.atleast_2d(h)
    I = np.abs(h) ** 2
    thr = F * I.mean(axis=1, keepdims=True)
    return float(np.all(I < thr, axis=0).mean())


def channel_correlation(h):
    """Empirical pairwise complex field correlation matrix (M, M).

    C[j, k] = <h_j h_k*> / sqrt(<|h_j|^2><|h_k|^2>).  For the
    make_speckle_multi construction the off-diagonal entries converge to
    rho (real) as N/tau_c -> inf.
    """
    h = np.atleast_2d(h)
    G = h @ h.conj().T / h.shape[1]
    d = np.sqrt(np.real(np.diag(G)))
    return G / np.outer(d, d)
