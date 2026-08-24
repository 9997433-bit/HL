function pe = tracking_error_rad(f_target, v_peak, fn, lam)
%TRACKING_ERROR_RAD Untracked Doppler phase (rad) for sinusoidal motion v_peak @ f_target.
%   pe = tracking_error_rad(f_target, v_peak, fn, lam)
%   Faithful port of design_params.py.  lam defaults to LAMBDA (1550 nm).
  if nargin < 4 || isempty(lam)
    C = homodyne_constants();
    lam = C.LAMBDA;
  end
  phi_amp = 2 * v_peak / (lam * f_target);
  pe = loop_error_mag(f_target, fn) * phi_amp;
end
