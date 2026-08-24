function pe = tracking_error_rad(f_target, v_peak, fn, lam)
%TRACKING_ERROR_RAD Untracked Doppler phase (rad) for sinusoidal motion.
  if nargin < 4 || isempty(lam)
    dp = design_params();
    lam = dp.LAMBDA;
  end
  phi_amp = 2 * v_peak ./ (lam * f_target);
  pe = loop_error_mag(f_target, fn) .* phi_amp;
end
