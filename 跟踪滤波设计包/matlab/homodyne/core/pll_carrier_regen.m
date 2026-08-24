function [y, phi, state, diag] = pll_carrier_regen(z, fs, fn, Nhat, opts)
%PLL_CARRIER_REGEN Single-knob PLL carrier regeneration, pure-NCO output, 3-state gate.
%   [y, phi, state, diag] = pll_carrier_regen(z, fs, fn, Nhat, opts)
%   Faithful port of core.py pll_carrier_regen (scalar per-sample loop,
%   same update ordering).  z is treated as a column vector; y and phi are
%   N-by-1, state is N-by-1 int8 (0 HOLD / 1 ACQUIRE / 2 LOCK).
%
%   opts (struct, all fields optional; Python keyword defaults):
%     zeta=1.2, tauP=1e-6, tauF=1e-6, snr_on=1.0, snr_off=0.3, reacq=true,
%     acq_time=[] (-> 4*tauF), drop_confirm=[] (-> max(1/fs, 0.25*tauP)),
%     gate='auto' ('always' forces LOCK every sample), rel_on=0.20,
%     rel_off=0.08, tauRef=200e-6.
%
%   diag: struct with near_pi_events, n_hold, n_acquire, n_lock_entries,
%   n_reacq, lock_frac.
  if nargin < 5
    opts = struct();
  end
  o = fill_defaults(opts, fs);

  z = z(:);
  N = numel(z);
  th = 2 * pi * fn / fs;
  Kp = 2 * o.zeta * th;
  Ki = th * th;
  aP = exp(-1.0 / (fs * o.tauP));
  aF = exp(-1.0 / (fs * o.tauF));
  nAcq = max(2, round(o.acq_time * fs));
  nOff = max(1, round(o.drop_confirm * fs));

  zr = real(z);
  zi = imag(z);

  aRef = exp(-1.0 / (fs * o.tauRef));
  always = strcmp(o.gate, 'always');
  aHold = exp(-1.0 / (fs * max(o.tauRef, o.tauP) * 8));

  phi = zeros(N, 1);
  state = zeros(N, 1, 'int8');
  ph = 0.0;
  om = 0.0;
  P = 0.0;
  dfa = 0.0;
  Cref = 0.0;
  if always
    st = 2;
  else
    st = 0;
  end
  good = 0;
  bad = 0;
  nearpi = 0;
  prevbig = false;
  n_hold = 0;
  n_acq = 0;
  n_lock_entries = 0;
  zpr = zr(1);
  zpi = zi(1);
  twopi = 2 * pi;

  for n = 1:N
    xr = zr(n);
    xi_ = zi(n);
    mag2 = xr * xr + xi_ * xi_;
    P = (1.0 - aP) * mag2 + aP * P;
    C = P - Nhat;
    if C < 0.0
      C = 0.0;
    end
    snr = C / Nhat;

    % coarse frequency from differential discriminator (no capture limit)
    dr = xr * zpr + xi_ * zpi;
    di = xi_ * zpr - xr * zpi;
    dph = atan2(di, dr);
    if snr > o.snr_off
      dfa = (1.0 - aF) * dph + aF * dfa;
    end
    zpr = xr;
    zpi = xi_;

    % 3-state gate: absolute floor AND relative-drop criterion
    if always
      st = 2;
    else
      open_ = (snr > o.snr_on) && (C > o.rel_on * Cref);
      shut_ = (snr < o.snr_off) || (C < o.rel_off * Cref);
      if st == 0                          % HOLD
        n_hold = n_hold + 1;
        bad = 0;
        if open_
          st = 1;
          good = 1;
          n_acq = n_acq + 1;
          dfa = dph;
        end
      elseif st == 1                      % ACQUIRE (loop frozen)
        n_acq = n_acq + 1;
        if shut_
          st = 0;
          good = 0;
        else
          good = good + 1;
          if good >= nAcq
            st = 2;
            n_lock_entries = n_lock_entries + 1;
            bad = 0;
            if o.reacq
              om = dfa;
            end
          end
        end
      else                                % LOCK
        if shut_
          bad = bad + 1;
          if bad >= nOff
            st = 0;
            good = 0;
            bad = 0;
          end
        else
          bad = 0;
        end
      end
    end
    if st == 2
      Cref = (1.0 - aRef) * C + aRef * Cref;
    elseif st == 0 && C > 0
      % HOLD: slow Cref decay so permanent power drop can re-lock (audit item 5)
      Cref = (1.0 - aHold) * C + aHold * Cref;
    end
    state(n) = st;

    phi(n) = ph;                          % output is always the pure NCO

    if st == 2
      c = cos(ph);
      s = sin(ph);
      rr = xr * c + xi_ * s;
      ri = xi_ * c - xr * s;
      e = atan2(ri, rr);
      big = abs(e) > 2.8;
      if big && ~prevbig
        nearpi = nearpi + 1;
      end
      prevbig = big;
      om = om + Ki * e;
      ph = ph + om + Kp * e;
    else
      prevbig = false;
      ph = ph + om;
    end
    ph = mod(ph + pi, twopi) - pi;
  end

  y = exp(1i * phi);
  diag = struct('near_pi_events', nearpi, 'n_hold', n_hold, ...
                'n_acquire', n_acq, 'n_lock_entries', n_lock_entries, ...
                'n_reacq', max(n_lock_entries - 1, 0), ...
                'lock_frac', mean(state == 2));
end

function o = fill_defaults(opts, fs)
  o = struct('zeta', 1.2, 'tauP', 1e-6, 'tauF', 1e-6, ...
             'snr_on', 1.0, 'snr_off', 0.3, 'reacq', true, ...
             'acq_time', [], 'drop_confirm', [], ...
             'gate', 'auto', 'rel_on', 0.20, 'rel_off', 0.08, ...
             'tauRef', 200e-6);
  fn_in = fieldnames(opts);
  for i = 1:numel(fn_in)
    o.(fn_in{i}) = opts.(fn_in{i});
  end
  if isempty(o.acq_time)
    o.acq_time = 4 * o.tauF;
  end
  if isempty(o.drop_confirm)
    o.drop_confirm = max(1.0 / fs, 0.25 * o.tauP);
  end
end
