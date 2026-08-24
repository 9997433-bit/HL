"""Heydemann ellipse correction for homodyne IQ (software-only, hardware fixed).

Faithful Python port of the reference MATLAB:
  00_公共函数/heydemann_fit.m    -> heydemann_fit   (Halir-Flusser constrained
                                    direct ellipse LS + closed-form p,q,A,B,delta,
                                    98% robust arc-coverage validity check)
  00_公共函数/heydemann_apply.m  -> heydemann_apply (ellipse -> unit circle)

Plus the segmented-arc calibration used by the validation script (document M1
idea from small_signal_ellipse_calib.m): per-segment amplitude-gated fits with
"freeze last valid parameters when the arc is too short" (arc >= pi/2 rule).

Model:  u = A*cos(phi) + p,   v = B*sin(phi + delta) + q
Fit:    a*u^2 + b*u*v + c*v^2 + d*u + e*v + f = 0 with 4ac - b^2 > 0 enforced.

Notes carried over from the MATLAB headers:
  * This is an ALGEBRAIC-distance fit; short arcs remain biased/ill-posed.
    Validity is gated by the robust 98% arc coverage (>= pi/2), otherwise the
    caller must freeze previous parameters.
  * All points fed to one fit must lie on (approximately) ONE ellipse: if the
    return amplitude R varies during the fit window the cloud is an annulus,
    not an ellipse -> amplitude gating is mandatory (fit_arc_gated).
  * Uncorrected residuals (eps, delta) leave phase ripple
    dphi ~ (eps/2)*sin(2phi) + (delta/2)*cos(2phi), peak displacement error
    (lambda/8pi)*sqrt(eps^2+delta^2), and a 2*phi ripple on |z|^2 that pollutes
    power-based gating of the downstream tracking filter.
"""
import math
import warnings

import numpy as np

_EPS = np.finfo(float).eps
ARC_MIN = math.pi / 2      # below this coverage the fit is declared invalid
FIT_RMS_MAX = 0.05
FIT_COND_MAX = 1e6
EPS_MAX = 0.20             # |B/A - 1|
DEL_MAX = math.radians(15.0)
PAR_FIELDS = ('p', 'q', 'A', 'B', 'delta')


def _arc_span_angles(ang):
    """Robust 98% coverage arc from sorted angles in [0, 2pi)."""
    ang = np.sort(np.mod(ang, 2 * math.pi))
    gaps = np.diff(np.concatenate([ang, [ang[0] + 2 * math.pi]]))
    nang = ang.size
    if nang < 2:
        return 0.0
    mcover = max(2, int(math.ceil(0.98 * nang)))
    ang2 = np.concatenate([ang, ang + 2 * math.pi])
    idx = np.arange(nang)
    return float(np.min(ang2[idx + mcover - 1] - ang2[idx]))


def arc_span_corrected(u, v, par):
    """Arc coverage using corrected-plane angles (independent sanity check)."""
    _, _, z = heydemann_apply(u, v, par)
    return _arc_span_angles(np.angle(z))


def assess_fit(par, res):
    """Full acceptance gate (doc §2.4): arc, rms, cond, epsilon, delta, A/B."""
    reasons = []
    if not all(math.isfinite(par[k]) for k in PAR_FIELDS):
        reasons.append('non-finite parameters')
    if par.get('A', 0) <= 0 or par.get('B', 0) <= 0:
        reasons.append('A or B non-positive')
    if math.isfinite(par.get('A', float('nan'))) and par['A'] > 0:
        eps = abs(par['B'] / par['A'] - 1.0)
        if eps > EPS_MAX:
            reasons.append(f'|epsilon|={eps:.3f} > {EPS_MAX}')
    if abs(par.get('delta', 0)) > DEL_MAX:
        reasons.append(f'|delta|={math.degrees(par["delta"]):.1f}° > {math.degrees(DEL_MAX):.0f}°')
    if res.get('arc', 0) < ARC_MIN:
        reasons.append(f'arc={res.get("arc", float("nan")):.3f} < {ARC_MIN:.3f}')
    if res.get('rms', float('inf')) > FIT_RMS_MAX:
        reasons.append(f'rms={res.get("rms", float("nan")):.4f} > {FIT_RMS_MAX}')
    # cond(D) blows up when algebraic residuals ~ 0 (perfect ellipse); only
    # gate on it when rms indicates a noisy/ambiguous fit (doc §2.4 intent).
    if (res.get('rms', float('inf')) > 1e-3 and
            res.get('design_cond', float('inf')) > FIT_COND_MAX):
        reasons.append(f'cond={res.get("design_cond", float("nan")):.2e} > {FIT_COND_MAX:.0e}')
    ok = len(reasons) == 0
    res['ok'] = ok
    res['reject_reasons'] = reasons
    if not ok and not res.get('msg'):
        res['msg'] = '; '.join(reasons)
    return ok


def _nan_par():
    return dict(p=np.nan, q=np.nan, A=np.nan, B=np.nan, delta=np.nan)


# --------------------------------------------------------------------- fit
def heydemann_fit(u, v):
    """Constrained direct algebraic ellipse fit + closed-form parameters.

    Returns (par, res):
      par  dict p,q,A,B,delta  (delta in rad)
      res  dict ok, theta (raw conic coeffs), rms, algebraic_rms,
                arc (98% robust coverage, rad), arc_all, design_cond, msg
    """
    u = np.asarray(u, float).ravel()
    v = np.asarray(v, float).ravel()
    if (u.size != v.size or u.size < 6 or
            not (np.all(np.isfinite(u)) and np.all(np.isfinite(v)))):
        raise ValueError('heydemann_fit: u, v must be equal-length finite '
                         'real vectors with >= 6 points')

    # centre + common scale preconditioning (large DC bias -> ill-posed conic)
    mu = np.array([u.mean(), v.mean()])
    sc = max(u.std(), v.std(), _EPS)
    un = (u - mu[0]) / sc
    vn = (v - mu[1]) / sc
    D1 = np.column_stack([un * un, un * vn, vn * vn])
    D2 = np.column_stack([un, vn, np.ones(un.size)])
    D = np.hstack([D1, D2])

    res = dict(ok=False, theta=np.full(6, np.nan), rms=np.nan,
               algebraic_rms=np.nan, arc=np.nan, arc_all=np.nan,
               design_cond=float(np.linalg.cond(D)),
               method='direct-ellipse-LS', msg='')
    par = _nan_par()

    if np.linalg.matrix_rank(D) < 5:
        res['msg'] = 'rank-deficient design matrix (arc/diversity too small)'
        return par, res

    S1 = D1.T @ D1
    S2 = D1.T @ D2
    S3 = D2.T @ D2
    if 1.0 / np.linalg.cond(S3) < 1e-14:
        res['msg'] = 'linear-part scatter matrix ill-conditioned'
        return par, res
    T = -np.linalg.solve(S3, S2.T)
    C1 = np.array([[0.0, 0.0, 2.0], [0.0, -1.0, 0.0], [2.0, 0.0, 0.0]])
    _, E = np.linalg.eig(np.linalg.solve(C1, S1 + S2 @ T))

    best, best_cost = None, np.inf
    for k in range(E.shape[1]):
        q3 = E[:, k]
        if np.max(np.abs(q3.imag)) > 1e-8 * max(1.0, np.max(np.abs(q3.real))):
            continue
        q3 = q3.real
        if 4 * q3[0] * q3[2] - q3[1] ** 2 <= 0:
            continue
        ck = np.concatenate([q3, T @ q3])
        cost = np.linalg.norm(D @ ck) / max(np.linalg.norm(ck), _EPS)
        if cost < best_cost:
            best, best_cost = ck, cost
    if best is None:
        res['msg'] = 'constrained fit produced no real ellipse'
        return par, res

    a, b, c, d, e, f = best
    Q = np.array([[a, b / 2], [b / 2, c]])
    if np.all(np.linalg.eigvalsh(Q) < 0):
        best = -best
        a, b, c, d, e, f = best
        Q = -Q
    if np.any(np.linalg.eigvalsh(Q) <= 0) or 1.0 / np.linalg.cond(Q) < 1e-14:
        res['msg'] = 'quadratic form not a positive-definite ellipse'
        return par, res
    ctr = -0.5 * np.linalg.solve(Q, np.array([d, e]))
    K = float(ctr @ Q @ ctr - f)
    if not np.isfinite(K) or K <= 0:
        res['msg'] = 'ellipse scale K non-positive'
        return par, res

    best = best / K                       # centred equation normalised to 1
    a, b, c = best[0], best[1], best[2]
    sd = float(np.clip(-b / (2 * math.sqrt(a * c)), -1 + 1e-12, 1 - 1e-12))
    delta = math.asin(sd)
    A_n = math.sqrt(1.0 / (a * math.cos(delta) ** 2))
    B_n = math.sqrt(1.0 / (c * math.cos(delta) ** 2))

    par = dict(p=float(mu[0] + sc * ctr[0]), q=float(mu[1] + sc * ctr[1]),
               A=float(sc * A_n), B=float(sc * B_n), delta=float(delta))

    # raw-coordinate conic coefficients (diagnostics / reproducibility)
    a, b, c, d, e, f = best
    raw = np.array([
        a / sc ** 2, b / sc ** 2, c / sc ** 2,
        d / sc - 2 * a * mu[0] / sc ** 2 - b * mu[1] / sc ** 2,
        e / sc - b * mu[0] / sc ** 2 - 2 * c * mu[1] / sc ** 2,
        f - d * mu[0] / sc - e * mu[1] / sc
        + a * mu[0] ** 2 / sc ** 2 + b * mu[0] * mu[1] / sc ** 2
        + c * mu[1] ** 2 / sc ** 2])

    Ic = (u - par['p']) / par['A']
    Qc = ((v - par['q']) / par['B'] - Ic * math.sin(par['delta'])) \
        / math.cos(par['delta'])
    rho = np.hypot(Ic, Qc)
    ang = np.sort(np.mod(np.arctan2(Qc, Ic), 2 * math.pi))
    gaps = np.diff(np.concatenate([ang, [ang[0] + 2 * math.pi]]))
    nang = ang.size
    mcover = max(2, int(math.ceil(0.98 * nang)))
    ang2 = np.concatenate([ang, ang + 2 * math.pi])
    idx = np.arange(nang)
    span98 = ang2[idx + mcover - 1] - ang2[idx]

    res['theta'] = raw
    res['rms'] = float(np.sqrt(np.mean((rho - 1.0) ** 2)))
    res['algebraic_rms'] = float(np.sqrt(np.mean((D @ best) ** 2)))
    res['arc_all'] = float(2 * math.pi - gaps.max())   # wrap-safe coverage
    res['arc'] = float(span98.min())                   # robust to outliers
    assess_fit(par, res)
    return par, res


# ------------------------------------------------------------------- apply
def heydemann_apply(u, v, par):
    """Ellipse -> unit circle inverse transform.

      Ic = (u - p)/A
      Qc = ((v - q)/B - Ic*sin(delta))/cos(delta)
      z  = Ic + 1j*Qc
    """
    u = np.asarray(u, float).ravel()
    v = np.asarray(v, float).ravel()
    if not all(k in par for k in PAR_FIELDS):
        raise ValueError('heydemann_apply: par must contain p,q,A,B,delta')
    pv = np.array([par[k] for k in PAR_FIELDS], float)
    if (u.size != v.size or not np.all(np.isfinite(pv)) or
            par['A'] <= 0 or par['B'] <= 0 or
            abs(math.cos(par['delta'])) < 1e-6):
        raise ValueError('heydemann_apply: invalid inputs or delta ~ +/-90 deg')
    Ic = (u - par['p']) / par['A']
    Qc = ((v - par['q']) / par['B'] - Ic * math.sin(par['delta'])) \
        / math.cos(par['delta'])
    return Ic, Qc, Ic + 1j * Qc


# -------------------------------------------- segmented arc calibration (M1)
def _subsample(u, v, max_pts):
    step = max(1, u.size // int(max_pts))
    return u[::step], v[::step]


def fit_arc_gated(u, v, prev_par, gate_tol=0.05, max_pts=8000, min_pts=100):
    """Amplitude-gated Heydemann fit (document M1: stable-amplitude arc only).

    The gate must NOT use the raw radius to the centre: an ellipse itself has
    an eps-sized radius swing versus angle, so a raw-radius gate keeps only a
    narrow angle subset and poisons the fit. Instead the points are circular-
    ised with the PREVIOUS parameters `prev_par`; the corrected modulus rho is
    ~R/const, so gating |rho/median - 1| <= gate_tol keeps exactly the stable-
    return-amplitude points at every angle (annulus rejection). The gate is
    relaxed once (2x) if it keeps too few points.
    """
    us, vs = _subsample(u, v, max_pts)
    _, _, zc = heydemann_apply(us, vs, prev_par)
    rho = np.abs(zc)
    med = max(float(np.median(rho)), _EPS)
    keep = np.abs(rho / med - 1.0) <= gate_tol
    if keep.sum() < max(min_pts, int(0.05 * us.size)):
        keep = np.abs(rho / med - 1.0) <= 2 * gate_tol
    if keep.sum() < min_pts:
        return _nan_par(), dict(ok=False, arc=np.nan,
                                msg='amplitude gate kept too few points')
    return heydemann_fit(us[keep], vs[keep])


def segmented_heydemann(u, v, fs, seg_len=0.25, gate_tol=0.05, max_pts=8000):
    """Per-segment amplitude-gated Heydemann with parameter freeze on failure.

    Segment k is fitted from its own samples (gated on radius w.r.t. the
    previous segment's centre); if the fit is invalid (arc < pi/2, gate kept
    too few points, degenerate conic) the previous parameters are held.

    Returns (t_c, pars, oks, arcs):
      t_c   segment-centre times (s)
      pars  list of parameter dicts (held values filled in)
      oks   bool array, True where the segment produced a fresh valid fit
      arcs  robust 98% coverage arc of each attempted fit (rad)
    """
    u = np.asarray(u, float).ravel()
    v = np.asarray(v, float).ravel()
    N = u.size
    ns = max(64, int(round(seg_len * fs)))
    K = max(1, N // ns)
    t_c = np.zeros(K)
    pars = [None] * K
    oks = np.zeros(K, bool)
    arcs = np.full(K, np.nan)
    prev = None
    for k in range(K):
        i0 = k * ns
        i1 = N if k == K - 1 else (k + 1) * ns
        uu, vv = u[i0:i1], v[i0:i1]
        t_c[k] = 0.5 * (i0 + i1) / fs
        if prev is None:
            # bootstrap: ungated fit for rough parameters (annulus-biased),
            # then two gated refit passes to wash the bias out
            cand, res = heydemann_fit(*_subsample(uu, vv, max_pts))
            for _ in range(2):
                if not res['ok']:
                    break
                par1, res1 = fit_arc_gated(uu, vv, cand, gate_tol, max_pts)
                if res1['ok']:
                    cand, res = par1, res1
            if not res['ok']:
                cand = None
        else:
            par1, res = fit_arc_gated(uu, vv, prev, gate_tol, max_pts)
            cand = par1 if res['ok'] else None
        arcs[k] = res.get('arc', np.nan)
        if cand is not None:
            prev = cand
            oks[k] = True
        pars[k] = dict(prev) if prev is not None else None

    first = next((k for k in range(K) if pars[k] is not None), None)
    if first is None:
        raise RuntimeError('segmented_heydemann: no segment produced a valid '
                           'ellipse fit (drift arc coverage insufficient?)')
    if first > 0:
        warnings.warn('segmented_heydemann: first %d segment(s) back-filled '
                      'from segment %d' % (first, first))
        for k in range(first):
            pars[k] = dict(pars[first])
    return t_c, pars, oks, arcs


def interp_par_track(t, t_c, pars):
    """Sample-wise linear interpolation of segment parameters (edge-hold)."""
    return {f: np.interp(t, t_c, np.array([pk[f] for pk in pars]))
            for f in PAR_FIELDS}


def apply_par_track(u, v, trk):
    """heydemann_apply with time-varying (per-sample) parameters."""
    Ic = (u - trk['p']) / trk['A']
    Qc = ((v - trk['q']) / trk['B'] - Ic * np.sin(trk['delta'])) \
        / np.cos(trk['delta'])
    return Ic + 1j * Qc


# ---------------------------------------- online bias (arc-gated, NOT block mean)
class OnlineBiasTracker:
    """Frozen g,delta (A,B,δ); update p,q only when block-mean arc is sufficient.

    Block-mean IIR of raw u,v is WRONG at a fixed working point because
    mean(u) ≈ p + A·cos ψ, not p.  Instead accumulate block means and fit
    the circle centre only when the corrected-plane arc exceeds ARC_MIN.
  On ρ jump (surface/distance switch) clear the buffer and hold p,q.
    """

    def __init__(self, gd_par, fs, blk_s=0.1, rho_jump=0.20, arc_min=ARC_MIN):
        self.gd = {k: float(gd_par[k]) for k in ('A', 'B', 'delta')}
        self.p = float(gd_par.get('p', 0.0))
        self.q = float(gd_par.get('q', 0.0))
        self.nb = max(64, int(blk_s * fs))
        self.rho_jump = rho_jump
        self.arc_min = arc_min
        self.buf_u: list = []
        self.buf_v: list = []
        self.rho_ref = 1.0

    def _par(self):
        return dict(p=self.p, q=self.q, **self.gd)

    def _try_center(self):
        if len(self.buf_u) < 12:
            return
        us = np.array(self.buf_u)
        vs = np.array(self.buf_v)
        if arc_span_corrected(us, vs, self._par()) < self.arc_min:
            return
        # Scale factory A,B by current |z|: heydemann_apply with frozen A,B
        # gives |z|≈R/R_cal, so A_eff=A·ρ recovers the true interference radius.
        # Without this, weak-return segments subtract a factory-sized vector and
        # drive amplitude error → 100% (audit residual after item 1).
        _, _, z = heydemann_apply(us, vs, self._par())
        rho_med = max(float(np.median(np.abs(z))), 1e-9)
        Ae = self.gd['A'] * rho_med
        Be = self.gd['B'] * rho_med
        ang = np.angle(z)
        c = np.mean((us - Ae * np.cos(ang))
                    + 1j * (vs - Be * np.sin(ang + self.gd['delta'])))
        self.p = 0.8 * self.p + 0.2 * float(c.real)
        self.q = 0.8 * self.q + 0.2 * float(c.imag)

    def process_block(self, u, v):
        _, _, z = heydemann_apply(u, v, self._par())
        rho = float(np.median(np.abs(z)))
        if self.rho_ref > 0 and abs(rho / self.rho_ref - 1.0) > self.rho_jump:
            self.buf_u.clear()
            self.buf_v.clear()
        self.rho_ref = 0.9 * self.rho_ref + 0.1 * max(rho, 1e-9)
        self.buf_u.append(float(u.mean()))
        self.buf_v.append(float(v.mean()))
        if len(self.buf_u) > 120:
            self.buf_u.pop(0)
            self.buf_v.pop(0)
        self._try_center()
        return self._par()

    def run(self, u, v):
        z = np.zeros(u.size, dtype=complex)
        for k in range(0, u.size, self.nb):
            sl = slice(k, min(k + self.nb, u.size))
            par = self.process_block(u[sl], v[sl])
            _, _, z[sl] = heydemann_apply(u[sl], v[sl], par)
        return z
