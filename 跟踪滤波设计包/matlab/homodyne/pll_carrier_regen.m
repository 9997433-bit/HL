function [y, phi, state, diag] = pll_carrier_regen(z, fs, fn, Nhat, varargin)
%PLL_CARRIER_REGEN Single-knob PLL carrier regeneration, pure-NCO output, 3-state gate.
%
% Faithful port of homodyne_tracking_design/core.py::pll_carrier_regen
% (which itself is the Python port of the original 00_公共函数/pll_carrier_regen.m,
% including the audit-item-5 slow Cref decay in HOLD).  The heterodyne core's
% pll_carrier_regen is a subset of this one (it lacks the HOLD Cref decay,
% which only matters for gate='auto'); heterodyne validation uses
% gate='always' exclusively, where both are bit-identical, so this single
% implementation is shared (requirement: reuse, do not fork).
%
%   [y, phi, state, diag] = pll_carrier_regen(z, fs, fn, Nhat, 'name', value, ...)
%
% Options (defaults match the Python source):
%   'zeta' 1.2, 'tauP' 1e-6, 'tauF' 1e-6, 'snr_on' 1.0, 'snr_off' 0.3,
%   'reacq' true, 'acq_time' [] (-> 4*tauF), 'drop_confirm' [] (-> max(1/fs, 0.25*tauP)),
%   'gate' 'auto' | 'always', 'rel_on' 0.20, 'rel_off' 0.08, 'tauRef' 200e-6
%
% gate='always' : force LOCK every sample (no gate) -- isolates the LOOP's
%                 behaviour from the gate's (required for a clean CNR sweep).
% gate='auto'   : absolute floor AND relative-drop criterion (3-state gate).
%
% Returns y (regenerated carrier, column), phi (NCO phase, column),
% state (0/1/2, column) and a diag struct.

  o = struct('zeta', 1.2, 'tauP', 1e-6, 'tauF', 1e-6, ...
             'snr_on', 1.0, 'snr_off', 0.3, 'reacq', true, ...
             'acq_time', [], 'drop_confirm', [], ...
             'gate', 'auto', 'rel_on', 0.20, 'rel_off', 0.08, ...
             'tauRef', 200e-6);
  for k = 1:2:numel(varargin)
    o.(varargin{k}) = varargin{k + 1};
  end

  z = z(:);
  N = numel(z);
  th = 2 * pi * fn / fs;
  Kp = 2 * o.zeta * th;
  Ki = th * th;
  aP = exp(-1.0 / (fs * o.tauP));
  aF = exp(-1.0 / (fs * o.tauF));
  if isempty(o.acq_time)
    o.acq_time = 4 * o.tauF;
  end
  if isempty(o.drop_confirm)
    o.drop_confirm = max(1.0 / fs, 0.25 * o.tauP);
  end
  nAcq = max(2, round(o.acq_time * fs));
  nOff = max(1, round(o.drop_confirm * fs));

  zr = real(z);
  zi = imag(z);

  aRef = exp(-1.0 / (fs * o.tauRef));
  % HOLD-state slow Cref decay constant (audit item 5) -- constant, hoisted.
  aHold = exp(-1.0 / (fs * max(o.tauRef, o.tauP) * 8));
  always = strcmp(o.gate, 'always');
  Nh = Nhat;
  snr_on = o.snr_on;
  snr_off = o.snr_off;
  rel_on = o.rel_on;
  rel_off = o.rel_off;
  reacq = o.reacq;

  phi = zeros(N, 1);
  state = zeros(N, 1);
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
    C = P - Nh;
    if C < 0.0
      C = 0.0;
    end
    snr = C / Nh;

    % coarse frequency from differential discriminator (no capture limit)
    dr = xr * zpr + xi_ * zpi;
    di = xi_ * zpr - xr * zpi;
    dph = atan2(di, dr);
    if snr > snr_off
      dfa = (1.0 - aF) * dph + aF * dfa;
    end
    zpr = xr;
    zpi = xi_;

    % 3-state gate: absolute floor AND relative-drop criterion
    if always
      st = 2;
    else
      open_ = (snr > snr_on) && (C > rel_on * Cref);
      shut_ = (snr < snr_off) || (C < rel_off * Cref);
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
            if reacq
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
      % HOLD: slow Cref decay so a permanent power drop can re-lock (audit item 5)
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
