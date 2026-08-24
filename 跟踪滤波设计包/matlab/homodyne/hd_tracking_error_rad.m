function e = hd_tracking_error_rad(f_target, v_peak, fn, lam)
%HD_TRACKING_ERROR_RAD Untracked Doppler phase (rad) for sinusoidal motion.
% Port of design_params.py::tracking_error_rad (homodyne lambda default).
  if nargin < 4
    P = hd_params();
    lam = P.LAMBDA;
  end
  phi_amp = 2 * v_peak ./ (lam * f_target);
  e = hd_loop_error_mag(f_target, fn) .* phi_amp;
end
