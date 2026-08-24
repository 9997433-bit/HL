function [y, phi, state, diag] = fixed_lp_mode(z, fs, Bwin, Nt_win)
%FIXED_LP_MODE Fixed measurement window only (tracking_mode='fixed_lp').
%   Port of core.fixed_lp_mode: y = LP(z) (raw window output, NOT unit
%   modulus), phi = angle(y), state = [] (Python None).
  y = fir_lp_same(z(:), Bwin, fs, Nt_win);
  phi = angle(y);
  state = [];
  diag = struct('mode', 'fixed_lp');
end
