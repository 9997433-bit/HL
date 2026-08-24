function [y, phi, state, diag] = het_residual_mode(z, fs, fn, Nhat, Bwin, varargin)
%HET_RESIDUAL_MODE Two-pass residual window architecture (heterodyne core variant).
% Port of heterodyne_tracking_design/core.py::residual_mode, which keeps the
% ORIGINAL first-order IIR residual window (the homodyne core has since moved
% to the 1025-tap FIR window -- see matlab/homodyne/residual_mode.m).  Kept
% for completeness of the heterodyne core port; the heterodyne validator does
% not use it (pure-NCO architecture).
%
% Options: 'zeta' (default 1.2), 'tauG' (default 2e-6); the rest forwarded to
% pll_carrier_regen.
  zeta = 1.2;
  tauG = 2e-6;
  fwd = {};
  for k = 1:2:numel(varargin)
    switch varargin{k}
      case 'zeta'
        zeta = varargin{k + 1};
      case 'tauG'
        tauG = varargin{k + 1};
      otherwise
        fwd(end + 1:end + 2) = varargin(k:k + 1);
    end
  end
  z = z(:);
  [~, phi, state, diag] = pll_carrier_regen(z, fs, fn, Nhat, ...
                                            'zeta', zeta, fwd{:});
  rot = exp(-1i * phi);
  r = z .* rot;
  aw = exp(-2 * pi * Bwin / fs);
  rf = iir1_lowpass(r, aw);
  aG = exp(-1.0 / (fs * tauG));
  gs = iir1_lowpass(double(state == 2), aG);
  resph = angle(rf) .* (abs(rf) > 1e-12);
  y = conj(rot) .* exp(1i * (gs .* resph));
end
