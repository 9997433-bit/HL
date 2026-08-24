function [y, phi, state, diag] = residual_mode(z, fs, fn, Nhat, Bwin, varargin)
%RESIDUAL_MODE Two-pass residual window architecture (homodyne, FIR window).
% Port of homodyne_tracking_design/core.py::residual_mode: PLL carrier
% regeneration + common NT_WIN-tap linear-phase FIR residual window.
%
%   [y, phi, state, diag] = residual_mode(z, fs, fn, Nhat, Bwin, 'name', value, ...)
%
% Extra options here: 'zeta' (default 1.2), 'tauG' (default 2e-6),
% 'Nt_win' (default 1025).  All remaining options are forwarded to
% pll_carrier_regen (tauP, tauF, gate, ...).
  zeta = 1.2;
  tauG = 2e-6;
  Nt_win = 1025;
  fwd = {};
  gate = 'auto';
  for k = 1:2:numel(varargin)
    switch varargin{k}
      case 'zeta'
        zeta = varargin{k + 1};
      case 'tauG'
        tauG = varargin{k + 1};
      case 'Nt_win'
        Nt_win = varargin{k + 1};
      otherwise
        if strcmp(varargin{k}, 'gate')
          gate = varargin{k + 1};
        end
        fwd(end + 1:end + 2) = varargin(k:k + 1);
    end
  end
  z = z(:);
  [~, phi, state, diag] = pll_carrier_regen(z, fs, fn, Nhat, ...
                                            'zeta', zeta, fwd{:});
  rot = exp(-1i * phi);
  rf = fir_lp_same(z .* rot, Bwin, fs, Nt_win);
  if strcmp(gate, 'always')
    gs = 1.0;
  else
    aG = exp(-1.0 / (fs * tauG));
    gs = iir1_lowpass(double(state == 2), aG);
  end
  resph = angle(rf) .* (abs(rf) > 1e-12);
  y = conj(rot) .* exp(1i * (gs .* resph));
end
