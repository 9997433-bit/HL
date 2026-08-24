function [y, phi, state, diag] = residual_mode(z, fs, fn, Nhat, Bwin, opts)
%RESIDUAL_MODE Two-pass residual window architecture (self-designed, NOT a Polytec model).
%   [y, phi, state, diag] = residual_mode(z, fs, fn, Nhat, Bwin, opts)
%   Faithful port of core.py residual_mode.  Measurement low-pass is the
%   NT_WIN-tap Hann-windowed-sinc linear-phase FIR from fir_lp_kernel --
%   the SAME design function used by the validation path (review item #4).
%   iir1_lowpass is kept only for the soft-gate smoothing gs.
%
%   opts (struct, optional): zeta=1.2, tauG=2e-6, Nt_win=1025, plus any
%   pll_carrier_regen option (tauP, tauF, snr_on, snr_off, reacq,
%   acq_time, drop_confirm, gate, rel_on, rel_off, tauRef).
  if nargin < 6
    opts = struct();
  end
  zeta = 1.2;
  tauG = 2e-6;
  Nt_win = 1025;
  if isfield(opts, 'zeta'),   zeta = opts.zeta;     end
  if isfield(opts, 'tauG'),   tauG = opts.tauG;     end
  if isfield(opts, 'Nt_win'), Nt_win = opts.Nt_win; end
  kw = rmfield_if(opts, {'zeta', 'tauG', 'Nt_win'});
  kw.zeta = zeta;

  z = z(:);
  [~, phi, state, diag] = pll_carrier_regen(z, fs, fn, Nhat, kw);
  rot = exp(-1i * phi);
  rf = fir_lp_same(z .* rot, Bwin, fs, Nt_win);
  if isfield(kw, 'gate') && strcmp(kw.gate, 'always')
    gs = 1.0;
  else
    aG = exp(-1.0 / (fs * tauG));
    gs = iir1_lowpass(double(state == 2), aG);
  end
  resph = zeros(numel(z), 1);
  big = abs(rf) > 1e-12;
  resph(big) = angle(rf(big));
  y = conj(rot) .* exp(1i * (gs .* resph));
end

function s = rmfield_if(s, names)
  for i = 1:numel(names)
    if isfield(s, names{i})
      s = rmfield(s, names{i});
    end
  end
end
