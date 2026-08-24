function [y, phi, state, diag] = pll_carrier_regen(z, fs, fn, Nhat, opts)
%PLL_CARRIER_REGEN Single-knob PLL carrier regeneration, pure-NCO output, 3-state gate.
%   [y, phi, state, diag] = pll_carrier_regen(z, fs, fn, Nhat, opts)
%   Faithful port of core.py pll_carrier_regen (scalar per-sample loop,
%   same update ordering).  z is treated as a column vector; y and phi are
%   N-by-1, state is N-by-1 (0 HOLD / 1 ACQUIRE / 2 LOCK).
%
%   opts (struct, all fields optional; Python keyword defaults):
%     zeta=1.2, tauP=1e-6, tauF=1e-6, snr_on=1.0, snr_off=0.3, reacq=true,
%     acq_time=[] (-> 4*tauF), drop_confirm=[] (-> max(1/fs, 0.25*tauP)),
%     gate='auto' ('always' forces LOCK every sample), rel_on=0.20,
%     rel_off=0.08, tauRef=200e-6.
%
%   diag: struct with near_pi_events, n_hold, n_acquire, n_lock_entries,
%   n_reacq, lock_frac.
%
%   The scalar loop runs in the compiled kernel pll_core_mex when available
%   (built by ensure_kernels; large speedup) and otherwise falls back to the
%   pure-M twin pll_core_m -- both implement the identical algorithm.
  if nargin < 5 || isempty(opts)
    opts = struct();
  end
  o = struct('zeta', 1.2, 'tauP', 1e-6, 'tauF', 1e-6, ...
             'snr_on', 1.0, 'snr_off', 0.3, 'reacq', true, ...
             'acq_time', NaN, 'drop_confirm', NaN, 'gate', 'auto', ...
             'rel_on', 0.20, 'rel_off', 0.08, 'tauRef', 200e-6);
  fns = fieldnames(opts);
  for i = 1:numel(fns)
    if ~isempty(opts.(fns{i}))
      o.(fns{i}) = opts.(fns{i});
    end
  end
  params = [fs; fn; Nhat; o.zeta; o.tauP; o.tauF; o.snr_on; o.snr_off; ...
            double(o.reacq); double(strcmp(o.gate, 'always')); ...
            o.rel_on; o.rel_off; o.tauRef; o.acq_time; o.drop_confirm];
  zr = real(z(:));
  zi = imag(z(:));
  if homodyne_use_mex('pll_core_mex')
    [phi, state, dg] = pll_core_mex(zr, zi, params);
  else
    [phi, state, dg] = pll_core_m(zr, zi, params);
  end
  y = exp(1i * phi);
  diag = struct('near_pi_events', dg(1), 'n_hold', dg(2), ...
                'n_acquire', dg(3), 'n_lock_entries', dg(4), ...
                'n_reacq', dg(5), 'lock_frac', dg(6));
end
