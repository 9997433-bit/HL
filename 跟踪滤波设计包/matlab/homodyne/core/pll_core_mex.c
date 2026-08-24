/* pll_core_mex.c -- scalar loop of pll_carrier_regen (C kernel).
 *
 * Faithful transcription of the per-sample loop in
 * homodyne_tracking_design/core.py::pll_carrier_regen (single-knob PLL
 * carrier regeneration, pure-NCO output, 3-state gate).  The MATLAB wrapper
 * pll_carrier_regen.m prepares the parameters and post-processes the
 * outputs; a pure-.m fallback (pll_core_m.m) implements the identical loop
 * for environments without a compiler.
 *
 * MEX API:
 *   [phi, state, diag] = pll_core_mex(zr, zi, params)
 *     zr, zi : N x 1 double, real/imag part of the complex baseband input
 *     params : 15 x 1 double
 *        [fs fn Nhat zeta tauP tauF snr_on snr_off reacq always ...
 *         rel_on rel_off tauRef acq_time drop_confirm]
 *        acq_time / drop_confirm may be NaN -> Python defaults
 *        (4*tauF and max(1/fs, 0.25*tauP)).
 *     phi    : N x 1 NCO phase
 *     state  : N x 1 gate state (0 HOLD / 1 ACQUIRE / 2 LOCK)
 *     diag   : 6 x 1 [near_pi_events n_hold n_acquire n_lock_entries ...
 *              n_reacq lock_frac]
 *
 * Compile:  mkoctfile --mex -O2 -ffp-contract=off pll_core_mex.c
 * (-ffp-contract=off keeps floating-point semantics identical to CPython.)
 */
#include "mex.h"
#include <math.h>

void mexFunction(int nlhs, mxArray *plhs[], int nrhs, const mxArray *prhs[])
{
    const double *zr, *zi, *pp;
    double *phi, *state, *diag;
    mwSize N, n;
    double fs, fn, Nhat, zeta, tauP, tauF, snr_on, snr_off;
    double rel_on, rel_off, tauRef, acq_time, drop_confirm;
    int reacq, always;
    double th, Kp, Ki, aP, aF, aRef, aHold;
    long nAcq, nOff;
    double ph, om, P, dfa, Cref, zpr, zpi;
    int st, prevbig;
    long good, bad, nearpi, n_hold, n_acq, n_lock_entries, n_lock_samples;
    const double twopi = 2.0 * M_PI;

    if (nrhs != 3)
        mexErrMsgTxt("usage: [phi,state,diag] = pll_core_mex(zr, zi, params)");
    N = mxGetNumberOfElements(prhs[0]);
    if (mxGetNumberOfElements(prhs[1]) != N)
        mexErrMsgTxt("zr and zi must have the same length");
    if (mxGetNumberOfElements(prhs[2]) != 15)
        mexErrMsgTxt("params must have 15 elements");
    zr = mxGetPr(prhs[0]);
    zi = mxGetPr(prhs[1]);
    pp = mxGetPr(prhs[2]);

    fs = pp[0]; fn = pp[1]; Nhat = pp[2]; zeta = pp[3];
    tauP = pp[4]; tauF = pp[5]; snr_on = pp[6]; snr_off = pp[7];
    reacq = pp[8] != 0.0; always = pp[9] != 0.0;
    rel_on = pp[10]; rel_off = pp[11]; tauRef = pp[12];
    acq_time = pp[13]; drop_confirm = pp[14];

    th = 2.0 * M_PI * fn / fs;
    Kp = 2.0 * zeta * th;
    Ki = th * th;
    aP = exp(-1.0 / (fs * tauP));
    aF = exp(-1.0 / (fs * tauF));
    if (mxIsNaN(acq_time))
        acq_time = 4.0 * tauF;
    if (mxIsNaN(drop_confirm)) {
        drop_confirm = 0.25 * tauP;
        if (1.0 / fs > drop_confirm)
            drop_confirm = 1.0 / fs;
    }
    /* Python: max(2, int(round(acq_time*fs))); values never land on .5 */
    nAcq = (long)floor(acq_time * fs + 0.5);
    if (nAcq < 2) nAcq = 2;
    nOff = (long)floor(drop_confirm * fs + 0.5);
    if (nOff < 1) nOff = 1;

    aRef = exp(-1.0 / (fs * tauRef));
    aHold = exp(-1.0 / (fs * (tauRef > tauP ? tauRef : tauP) * 8.0));

    plhs[0] = mxCreateDoubleMatrix(N, 1, mxREAL);
    plhs[1] = mxCreateDoubleMatrix(N, 1, mxREAL);
    plhs[2] = mxCreateDoubleMatrix(6, 1, mxREAL);
    phi = mxGetPr(plhs[0]);
    state = mxGetPr(plhs[1]);
    diag = mxGetPr(plhs[2]);

    ph = 0.0; om = 0.0; P = 0.0; dfa = 0.0; Cref = 0.0;
    st = always ? 2 : 0;
    good = 0; bad = 0; nearpi = 0; prevbig = 0;
    n_hold = 0; n_acq = 0; n_lock_entries = 0; n_lock_samples = 0;
    zpr = N > 0 ? zr[0] : 0.0;
    zpi = N > 0 ? zi[0] : 0.0;

    for (n = 0; n < N; n++) {
        double xr = zr[n];
        double xi_ = zi[n];
        double mag2 = xr * xr + xi_ * xi_;
        double C, snr, dr, di, dph;

        P = (1.0 - aP) * mag2 + aP * P;
        C = P - Nhat;
        if (C < 0.0)
            C = 0.0;
        snr = C / Nhat;

        /* coarse frequency from differential discriminator */
        dr = xr * zpr + xi_ * zpi;
        di = xi_ * zpr - xr * zpi;
        dph = atan2(di, dr);
        if (snr > snr_off)
            dfa = (1.0 - aF) * dph + aF * dfa;
        zpr = xr;
        zpi = xi_;

        /* 3-state gate: absolute floor AND relative-drop criterion */
        if (always) {
            st = 2;
        } else {
            int open_ = (snr > snr_on) && (C > rel_on * Cref);
            int shut_ = (snr < snr_off) || (C < rel_off * Cref);
            if (st == 0) {                    /* HOLD */
                n_hold++;
                bad = 0;
                if (open_) {
                    st = 1;
                    good = 1;
                    n_acq++;
                    dfa = dph;
                }
            } else if (st == 1) {             /* ACQUIRE (loop frozen) */
                n_acq++;
                if (shut_) {
                    st = 0;
                    good = 0;
                } else {
                    good++;
                    if (good >= nAcq) {
                        st = 2;
                        n_lock_entries++;
                        bad = 0;
                        if (reacq)
                            om = dfa;
                    }
                }
            } else {                          /* LOCK */
                if (shut_) {
                    bad++;
                    if (bad >= nOff) {
                        st = 0;
                        good = 0;
                        bad = 0;
                    }
                } else {
                    bad = 0;
                }
            }
        }
        if (st == 2) {
            Cref = (1.0 - aRef) * C + aRef * Cref;
        } else if (st == 0 && C > 0.0) {
            /* HOLD: slow Cref decay so a permanent power drop can re-lock */
            Cref = (1.0 - aHold) * C + aHold * Cref;
        }
        state[n] = (double)st;

        phi[n] = ph;                      /* output is always the pure NCO */

        if (st == 2) {
            double c = cos(ph);
            double s = sin(ph);
            double rr2 = xr * c + xi_ * s;
            double ri2 = xi_ * c - xr * s;
            double e = atan2(ri2, rr2);
            int big = fabs(e) > 2.8;
            n_lock_samples++;
            if (big && !prevbig)
                nearpi++;
            prevbig = big;
            om += Ki * e;
            ph += om + Kp * e;
        } else {
            prevbig = 0;
            ph += om;
        }
        /* Python: ph = (ph + pi) % (2*pi) - pi  (non-negative modulo) */
        ph = fmod(ph + M_PI, twopi);
        if (ph < 0.0)
            ph += twopi;
        ph -= M_PI;
    }

    diag[0] = (double)nearpi;
    diag[1] = (double)n_hold;
    diag[2] = (double)n_acq;
    diag[3] = (double)n_lock_entries;
    diag[4] = (double)(n_lock_entries > 1 ? n_lock_entries - 1 : 0);
    diag[5] = N > 0 ? (double)n_lock_samples / (double)N : 0.0;
}
