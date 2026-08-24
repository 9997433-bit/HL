function [y, phi, state, diag] = residual_mode(z, fs, fn, Nhat, Bwin, opts)
%RESIDUAL_MODE Two-pass residual window architecture (port of core.residual_mode).
%   opts: zeta (1.2), tauG (2e-6), Nt_win (1025) plus any pll_carrier_regen
%   options (gate, tauP, tauF, snr_on, snr_off, reacq, rel_on, rel_off,
%   tauRef, acq_time, drop_confirm).
  if nargin < 6 || isempty(opts), opts = struct(); end
  zeta = 1.2;  if isfield(opts, 'zeta'),   zeta = opts.zeta;    end
  tauG = 2e-6; if isfield(opts, 'tauG'),   tauG = opts.tauG;    end
  Ntw = 1025;  if isfield(opts, 'Nt_win'), Ntw = opts.Nt_win;   end
  gate = 'auto'; if isfield(opts, 'gate'), gate = opts.gate;    end

  po = struct('zeta', zeta, 'gate', gate);
  keys = {'tauP', 'tauF', 'snr_on', 'snr_off', 'reacq', ...
          'rel_on', 'rel_off', 'tauRef', 'acq_time', 'drop_confirm'};
  for i = 1:numel(keys)
    if isfield(opts, keys{i})
      po.(keys{i}) = opts.(keys{i});
    end
  end

  [~, phi, state, diag] = pll_carrier_regen(z, fs, fn, Nhat, po);
  z = z(:);
  rot = exp(-1i * phi);
  rf = fir_lp_same(z .* rot, Bwin, fs, Ntw);
  if strcmp(gate, 'always')
    gs = 1.0;
  else
    aG = exp(-1.0 / (fs * tauG));
    gs = iir1_lowpass(double(state == 2), aG);
  end
  resph = zeros(size(rf));
  m = abs(rf) > 1e-12;
  resph(m) = angle(rf(m));
  y = conj(rot) .* exp(1i * (gs .* resph));
end
