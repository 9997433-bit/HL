function [y, phi, state, diag] = off_mode(z)
%OFF_MODE Tracking bypass (tracking_mode='off'): no PLL, no residual window.
%   Port of core.off_mode: y = z/|z| (unit modulus), phi = angle(z),
%   state = [] (Python None -- no gate exists here).
  z = z(:);
  phi = angle(z);
  y = exp(1i * phi);
  state = [];
  diag = struct('mode', 'off');
end
