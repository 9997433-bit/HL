function [y, phi, state, diag] = off_mode(z)
%OFF_MODE Tracking bypass (tracking_mode='off'): no PLL, no residual window.
%   [y, phi, state, diag] = off_mode(z)
%   Faithful port of core.py off_mode.  OFF removes the whole tracking
%   chain: the instrument output is the raw interferometric phase angle(z),
%   demodulated downstream by fm_discriminator.
%   y = z/|z| (unit modulus), phi = angle(z), state = [] (no gate exists).
  z = z(:);
  phi = angle(z);
  y = exp(1i * phi);
  state = [];
  diag = struct('mode', 'off');
end
