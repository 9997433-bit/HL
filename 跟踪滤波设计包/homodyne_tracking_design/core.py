"""Faithful Python port of the homodyne tracking-filter chain.

Ported from:
  00_公共函数/pll_carrier_regen.m        (3-state gate, pure-NCO output)
  00_公共函数/make_speckle.m            (Gaussian Doppler spectrum)
  00_公共函数/complex_bandlimited_noise.m
  00_公共函数/burst_signal.m            (exact velocity incl. d(env)/dt)
  03_代码_零差IQ链路/homodyne_tracking_filter.m  (residual mode)

Only numpy is available (no scipy / numba), so the PLL is a tight scalar loop.

Deviation from the MATLAB source (review item #4): residual_mode's
measurement low-pass is now the 1025-tap linear-phase FIR window
(fir_lp_kernel / fir_lp_same) validated by validate_tracking.py, not the
original first-order IIR -- validated path == product path.
"""
import math
import numpy as np


# ----------------------------------------------------------------- signals
def burst_signal(t, f0, vamp, ncyc, t0):
    """Hann-enveloped burst: displacement and EXACT velocity (incl. d(env)/dt)."""
    X0 = vamp / (2 * np.pi * f0)
    Tb = ncyc / f0
    w = 2 * np.pi * f0
    u = (t - t0) / Tb
    inb = (u >= 0) & (u <= 1)
    env = np.where(inb, 0.5 * (1 - np.cos(2 * np.pi * u)), 0.0)
    edot = np.where(inb, (np.pi / Tb) * np.sin(2 * np.pi * u), 0.0)
    ph = w * (t - t0)
    x = X0 * np.sin(ph) * env
    v = X0 * w * np.cos(ph) * env + X0 * np.sin(ph) * edot
    return x, v, env


def complex_bandlimited_noise(N, fs, B_enbw, power, rng):
    """Flat two-sided complex Gaussian noise occupying |f| <= B_enbw/2."""
    Nf = 1 << (int(np.ceil(np.log2(2 * N))))
    f = (np.arange(Nf) - Nf // 2) * (fs / Nf)
    mask = np.abs(f) <= B_enbw / 2
    X = np.zeros(Nf, dtype=complex)
    k = int(mask.sum())
    X[mask] = (rng.standard_normal(k) + 1j * rng.standard_normal(k)) / np.sqrt(2)
    x = np.fft.ifft(np.fft.ifftshift(X))
    i0 = (Nf - N) // 2
    n = x[i0:i0 + N]
    n = n - n.mean()
    if power > 0:
        n = n * np.sqrt(power / max(np.mean(np.abs(n) ** 2), 1e-300))
    return n


def make_speckle(N, fs, tau_c, rng, K=0.0):
    """Band-limited complex speckle, Gaussian Doppler spectrum, R(tau_c)=1/e."""
    Nf = 1 << (int(np.ceil(np.log2(2 * N))))
    f = (np.arange(Nf) - Nf // 2) * (fs / Nf)
    sf = 1.0 / (np.pi * tau_c * np.sqrt(2))
    S = np.exp(-f ** 2 / (2 * sf ** 2))
    A = np.sqrt(S)
    xi = (rng.standard_normal(Nf) + 1j * rng.standard_normal(Nf)) / np.sqrt(2)
    hf = np.fft.ifft(np.fft.ifftshift(A) * xi)
    h = hf[:N]
    h = h / np.sqrt(np.mean(np.abs(h) ** 2))
    if K > 0:
        h = (np.sqrt(K) + h) / np.sqrt(1 + K)
        h = h / np.sqrt(np.mean(np.abs(h) ** 2))
    return h


# ----------------------------------------------------------------- PLL core
def pll_carrier_regen(z, fs, fn, Nhat, zeta=1.2, tauP=1e-6, tauF=1e-6,
                      snr_on=1.0, snr_off=0.3, reacq=True,
                      acq_time=None, drop_confirm=None,
                      gate='auto', rel_on=0.20, rel_off=0.08, tauRef=200e-6):
    """Single-knob PLL carrier regeneration, pure-NCO output, 3-state gate.

    gate='always'  : force LOCK every sample (no gate). Isolates the LOOP's
                     own behaviour from the gate's -- required for a clean
                     CNR sweep, because an absolute Chat/Nhat gate cannot
                     tell "dim but steady light" from "dropout" and simply
                     refuses to lock below SnrOn.
    gate='auto'    : absolute floor AND relative-drop criterion.
                     absolute  Chat > snr_on * Nhat      ("there is light")
                     relative  Chat > rel_on * Cref      ("not in a deep fade")
                     Cref is a slow IIR of Chat updated only while LOCK, so a
                     dropout cannot drag the reference down with it.

    Returns y (regenerated carrier), phi (NCO phase), state (0/1/2), diag dict.
    """
    N = z.size
    th = 2 * np.pi * fn / fs
    Kp, Ki = 2 * zeta * th, th * th
    aP = math.exp(-1.0 / (fs * tauP))
    aF = math.exp(-1.0 / (fs * tauF))
    if acq_time is None:
        acq_time = 4 * tauF
    if drop_confirm is None:
        drop_confirm = max(1.0 / fs, 0.25 * tauP)
    nAcq = max(2, int(round(acq_time * fs)))
    nOff = max(1, int(round(drop_confirm * fs)))

    zr = np.ascontiguousarray(z.real).tolist()
    zi = np.ascontiguousarray(z.imag).tolist()

    aRef = math.exp(-1.0 / (fs * tauRef))
    always = (gate == 'always')

    phi = np.empty(N)
    state = np.empty(N, dtype=np.int8)
    ph = 0.0
    om = 0.0
    P = 0.0
    dfa = 0.0
    Cref = 0.0
    st = 2 if always else 0
    good = 0
    bad = 0
    nearpi = 0
    prevbig = False
    n_hold = 0
    n_acq = 0
    n_lock_entries = 0
    zpr, zpi = zr[0], zi[0]
    twopi = 2 * math.pi

    for n in range(N):
        xr = zr[n]
        xi_ = zi[n]
        mag2 = xr * xr + xi_ * xi_
        P = (1.0 - aP) * mag2 + aP * P
        C = P - Nhat
        if C < 0.0:
            C = 0.0
        snr = C / Nhat

        # coarse frequency from differential discriminator (no capture limit)
        dr = xr * zpr + xi_ * zpi
        di = xi_ * zpr - xr * zpi
        dph = math.atan2(di, dr)
        if snr > snr_off:
            dfa = (1.0 - aF) * dph + aF * dfa
        zpr, zpi = xr, xi_

        # 3-state gate: absolute floor AND relative-drop criterion
        if always:
            st = 2
        else:
            open_ = (snr > snr_on) and (C > rel_on * Cref)
            shut_ = (snr < snr_off) or (C < rel_off * Cref)
            if st == 0:                       # HOLD
                n_hold += 1
                bad = 0
                if open_:
                    st = 1
                    good = 1
                    n_acq += 1
                    dfa = dph
            elif st == 1:                     # ACQUIRE (loop frozen)
                n_acq += 1
                if shut_:
                    st = 0
                    good = 0
                else:
                    good += 1
                    if good >= nAcq:
                        st = 2
                        n_lock_entries += 1
                        bad = 0
                        if reacq:
                            om = dfa
            else:                             # LOCK
                if shut_:
                    bad += 1
                    if bad >= nOff:
                        st = 0
                        good = 0
                        bad = 0
                else:
                    bad = 0
        if st == 2:
            Cref = (1.0 - aRef) * C + aRef * Cref
        elif st == 0 and C > 0:
            # HOLD: slow Cref decay so permanent power drop can re-lock (audit item 5)
            aHold = math.exp(-1.0 / (fs * max(tauRef, tauP) * 8))
            Cref = (1.0 - aHold) * C + aHold * Cref
        state[n] = st

        phi[n] = ph                       # output is always the pure NCO

        if st == 2:
            c = math.cos(ph)
            s = math.sin(ph)
            rr = xr * c + xi_ * s
            ri = xi_ * c - xr * s
            e = math.atan2(ri, rr)
            big = abs(e) > 2.8
            if big and not prevbig:
                nearpi += 1
            prevbig = big
            om += Ki * e
            ph += om + Kp * e
        else:
            prevbig = False
            ph += om
        ph = (ph + math.pi) % twopi - math.pi

    y = np.exp(1j * phi)
    diag = dict(near_pi_events=nearpi, n_hold=n_hold, n_acquire=n_acq,
                n_lock_entries=n_lock_entries,
                n_reacq=max(n_lock_entries - 1, 0),
                lock_frac=float(np.mean(state == 2)))
    return y, phi, state, diag


def iir1_lowpass(x, a):
    """y[n] = (1-a)x[n] + a y[n-1], done as FFT convolution with the exact kernel."""
    L = int(min(len(x), max(8, math.ceil(math.log(1e-16) / math.log(a)))))
    k = (1 - a) * a ** np.arange(L)
    n = len(x)
    nfft = 1 << int(np.ceil(np.log2(n + L)))
    Y = np.fft.ifft(np.fft.fft(x, nfft) * np.fft.fft(k, nfft))[:n]
    return Y if np.iscomplexobj(x) else Y.real


_FIR_KERN = {}


def fir_lp_kernel(fc, fs, Nt):
    """Hann-windowed-sinc linear-phase low-pass kernel, DC-normalised.

    Single source of truth for the residual measurement window: both
    residual_mode (product path) and validate_tracking.gear_filter
    (validation path) build their FIR from this function, so the validated
    filter IS the product filter (review item #4).
    """
    key = (fc, fs, Nt)
    if key not in _FIR_KERN:
        n = np.arange(Nt) - (Nt - 1) / 2
        u = 2 * fc / fs * n
        h = np.ones(Nt)
        nz = u != 0
        h[nz] = np.sin(np.pi * u[nz]) / (np.pi * u[nz])
        h *= (2 * fc / fs) * (0.5 * (1 - np.cos(2 * np.pi * np.arange(Nt) / (Nt - 1))))
        _FIR_KERN[key] = h / h.sum()
    return _FIR_KERN[key]


def fir_lp_same(x, fc, fs, Nt):
    """Linear-phase FIR low-pass via FFT convolution, group-delay compensated.

    Off-line the (Nt-1)/2-sample group delay is removed by slicing ('same'
    alignment).  Real-time hardware cannot look ahead: it must instead put an
    NT_WIN/2-sample delay line on the NCO phase path so that e^{-j*phi} stays
    aligned with the FIR output (see validate_tracking.py header note).
    """
    h = fir_lp_kernel(fc, fs, Nt)
    nfft = 1 << int(np.ceil(np.log2(x.size + Nt)))
    y = np.fft.ifft(np.fft.fft(x, nfft) * np.fft.fft(h, nfft))
    y = y[(Nt - 1) // 2:(Nt - 1) // 2 + x.size]
    return y if np.iscomplexobj(x) else y.real


def residual_mode(z, fs, fn, Nhat, Bwin, zeta=1.2, tauG=2e-6, Nt_win=1025,
                  **kw):  # noqa: D401
    """Two-pass residual window architecture (self-designed, NOT a Polytec model).

    Measurement low-pass = 1025-tap (design_params.NT_WIN) Hann-windowed-sinc
    linear-phase FIR from fir_lp_kernel -- the SAME design function used by
    validate_tracking.gear_filter, so validation covers this product path.
    The original first-order IIR residual window (iir1_lowpass on r) was
    never exercised by validation and has been retired (review item #4);
    iir1_lowpass is kept only for the soft-gate smoothing gs below.

    Group delay: fir_lp_same removes the (Nt_win-1)/2-sample FIR delay
    off-line; real-time hardware needs an NT_WIN/2-sample delay line on the
    NCO phase path to keep e^{-j*phi} aligned with the window.  A 1025-tap
    FIR at the full 250 MS/s rate is not practical in a single stage; the
    hardware implementation is a multirate (polyphase decimation) equivalent
    with the same DC..Bwin response (see design_params.NT_WIN note).
    """
    y_pll, phi, state, diag = pll_carrier_regen(z, fs, fn, Nhat, zeta=zeta, **kw)
    rot = np.exp(-1j * phi)
    rf = fir_lp_same(z * rot, Bwin, fs, Nt_win)
    if kw.get('gate') == 'always':
        gs = 1.0
    else:
        aG = math.exp(-1.0 / (fs * tauG))
        gs = iir1_lowpass((state == 2).astype(float), aG)
    resph = np.where(np.abs(rf) > 1e-12, np.angle(rf), 0.0)
    y = np.conj(rot) * np.exp(1j * gs * resph)
    return y, phi, state, diag


# ------------------------------------------------------------ product entry
def off_mode(z):
    """Tracking bypass (tracking_mode='off'): no PLL, no residual window.

    OFF is NOT a fourth gear and NOT gate='always' (which only bypasses the
    dropout gate while the PLL keeps tracking).  OFF removes the whole
    tracking chain: the instrument output is the raw interferometric phase
    angle(z), demodulated downstream by fm_discriminator -- exactly the OFF
    reference column of the V1/V3 comparisons.

    Returns (y, phi, state, diag) shaped like residual_mode:
      y = z/|z| (unit modulus, so downstream angle/FM handling is identical
      to the PLL modes), phi = angle(z), state = None (no gate exists here).
    """
    phi = np.angle(z)
    return np.exp(1j * phi), phi, None, dict(mode='off')


_PLL_CFG_KEYS = ('tauP', 'tauF', 'snr_on', 'snr_off', 'reacq', 'gate',
                 'rel_on', 'rel_off', 'tauRef')


def tracking_filter(z, fs, cfg, Nhat=None):
    """Product entry point, driven by design_params.cfg_for_frequency dicts.

    cfg['tracking_mode'] == 'off': tracking bypass (off_mode); Nhat unused.
    cfg['tracking_mode'] == 'pll' (or absent, for legacy cfg dicts):
        gear PLL + common residual window (residual_mode) with the gear's
        fn / B_win / gate parameters taken from cfg; Nhat is the mandatory
        dark-calibrated noise floor.

    Returns (y, phi, state, diag) in both modes.
    """
    if cfg.get('tracking_mode', 'pll') == 'off':
        return off_mode(z)
    if Nhat is None:
        raise ValueError("tracking_mode='pll' requires the dark-calibrated "
                         "noise floor Nhat")
    kw = {k: cfg[k] for k in _PLL_CFG_KEYS if k in cfg}
    return residual_mode(z, fs, cfg['fn'], Nhat, cfg['B_win'],
                         zeta=cfg.get('zeta', 1.2), **kw)


# ----------------------------------------------------------------- utilities
def fm_discriminator(z, fs, lam):
    d = np.angle(z[1:] * np.conj(z[:-1]))
    return np.concatenate(([0.0], d)) * fs * lam / (4 * np.pi)


def fir_lp(x, fc, fs, Nt=257):
    if Nt % 2 == 0:
        Nt += 1
    h = fir_lp_kernel(fc, fs, Nt)
    return np.convolve(x, h, mode='same')


def hl_response(f, fs, fn, zeta):
    """Exact discrete closed-loop phase response of this update ordering."""
    th = 2 * np.pi * fn / fs
    Kp, Ki = 2 * zeta * th, th * th
    q = np.exp(1j * 2 * np.pi * np.asarray(f) / fs) - 1
    H = (Ki + (Ki + Kp) * q) / (q ** 2 + (Ki + Kp) * q + Ki)
    H = np.where(np.asarray(f) == 0, 1.0 + 0j, H)
    return H


def lockin_amp(v, t, f0, win):
    k = np.exp(-1j * 2 * np.pi * f0 * t)
    seg = v[win] - v[win].mean()
    return 2 * np.abs(np.mean(seg * k[win]))


def welch_psd(x, fs, L=1024):
    L = min(L, x.size)
    win = 0.5 - 0.5 * np.cos(2 * np.pi * np.arange(L) / (L - 1))
    U = np.sum(win ** 2)
    P = np.zeros(L)
    K = 0
    for i in range(0, x.size - L + 1, L // 2):
        P += np.abs(np.fft.fft(x[i:i + L] * win)) ** 2 / (fs * U)
        K += 1
    P /= max(K, 1)
    P = P[:L // 2 + 1]
    P[1:-1] *= 2
    return P, np.arange(L // 2 + 1) * fs / L
