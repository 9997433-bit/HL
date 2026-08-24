function [y, phi, state, diag] = fixed_lp_mode(z, fs, Bwin, Nt_win)
%FIXED_LP_MODE Fixed measurement window only (tracking_mode='fixed_lp'): no PLL.
%   [y, phi, state, diag] = fixed_lp_mode(z, fs, Bwin, Nt_win)
%   Faithful port of core.py fixed_lp_mode: applies the common B_WIN
%   linear-phase FIR complex low-pass (fir_lp_same) directly to z -- the
%   V2 'LP-Bwin' reference path.  y is the raw window output (NOT
%   unit-modulus normalised), phi = angle(y), state = [].
  y = fir_lp_same(z(:), Bwin, fs, Nt_win);
  phi = angle(y);
  state = [];
  diag = struct('mode', 'fixed_lp');
end
