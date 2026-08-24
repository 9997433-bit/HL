function [phi, state, diag] = pll_core_m(zr, zi, pp)
%PLL_CORE_M Pure-MATLAB fallback for pll_core_mex (identical scalar loop).
%   Much slower than the MEX kernel; numerically identical algorithm.
%   See pll_core_mex.c for the params layout.
  fs = pp(1); fn = pp(2); Nhat = pp(3); zeta = pp(4);
  tauP = pp(5); tauF = pp(6); snr_on = pp(7); snr_off = pp(8);
  reacq = pp(9) ~= 0; always = pp(10) ~= 0;
  rel_on = pp(11); rel_off = pp(12); tauRef = pp(13);
  acq_time = pp(14); drop_confirm = pp(15);

  N = numel(zr);
  th = 2 * pi * fn / fs;
  Kp = 2 * zeta * th;
  Ki = th * th;
  aP = exp(-1.0 / (fs * tauP));
  aF = exp(-1.0 / (fs * tauF));
  if isnan(acq_time), acq_time = 4 * tauF; end
  if isnan(drop_confirm), drop_confirm = max(1.0 / fs, 0.25 * tauP); end
  nAcq = max(2, floor(acq_time * fs + 0.5));
  nOff = max(1, floor(drop_confirm * fs + 0.5));
  aRef = exp(-1.0 / (fs * tauRef));
  aHold = exp(-1.0 / (fs * max(tauRef, tauP) * 8));
  twopi = 2 * pi;

  phi = zeros(N, 1);
  state = zeros(N, 1);
  ph = 0.0; om = 0.0; P = 0.0; dfa = 0.0; Cref = 0.0;
  if always, st = 2; else, st = 0; end
  good = 0; bad = 0; nearpi = 0; prevbig = false;
  n_hold = 0; n_acq = 0; n_lock_entries = 0; n_lock = 0;
  zpr = zr(1); zpi = zi(1);

  for n = 1:N
    xr = zr(n);
    xi_ = zi(n);
    mag2 = xr * xr + xi_ * xi_;
    P = (1.0 - aP) * mag2 + aP * P;
    C = P - Nhat;
    if C < 0.0, C = 0.0; end
    snr = C / Nhat;

    dr = xr * zpr + xi_ * zpi;
    di = xi_ * zpr - xr * zpi;
    dph = atan2(di, dr);
    if snr > snr_off
      dfa = (1.0 - aF) * dph + aF * dfa;
    end
    zpr = xr; zpi = xi_;

    if always
      st = 2;
    else
      open_ = (snr > snr_on) && (C > rel_on * Cref);
      shut_ = (snr < snr_off) || (C < rel_off * Cref);
      if st == 0                        % HOLD
        n_hold = n_hold + 1;
        bad = 0;
        if open_
          st = 1; good = 1; n_acq = n_acq + 1; dfa = dph;
        end
      elseif st == 1                    % ACQUIRE (loop frozen)
        n_acq = n_acq + 1;
        if shut_
          st = 0; good = 0;
        else
          good = good + 1;
          if good >= nAcq
            st = 2; n_lock_entries = n_lock_entries + 1; bad = 0;
            if reacq, om = dfa; end
          end
        end
      else                              % LOCK
        if shut_
          bad = bad + 1;
          if bad >= nOff
            st = 0; good = 0; bad = 0;
          end
        else
          bad = 0;
        end
      end
    end
    if st == 2
      Cref = (1.0 - aRef) * C + aRef * Cref;
    elseif st == 0 && C > 0
      Cref = (1.0 - aHold) * C + aHold * Cref;
    end
    state(n) = st;

    phi(n) = ph;                        % output is always the pure NCO

    if st == 2
      n_lock = n_lock + 1;
      c = cos(ph);
      s = sin(ph);
      rr = xr * c + xi_ * s;
      ri = xi_ * c - xr * s;
      e = atan2(ri, rr);
      big = abs(e) > 2.8;
      if big && ~prevbig, nearpi = nearpi + 1; end
      prevbig = big;
      om = om + Ki * e;
      ph = ph + om + Kp * e;
    else
      prevbig = false;
      ph = ph + om;
    end
    ph = mod(ph + pi, twopi) - pi;
  end

  diag = [nearpi; n_hold; n_acq; n_lock_entries; ...
          max(n_lock_entries - 1, 0); n_lock / max(N, 1)];
end
