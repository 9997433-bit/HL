function e = het_tracking_error_rad(f_v, v_peak, fn, lam, zeta)
%HET_TRACKING_ERROR_RAD 正弦运动 v_peak@f_v 的未跟踪多普勒相位 (rad).
% Port of heterodyne design_params.py::tracking_error_rad.
  P = het_params();
  if nargin < 4 || isempty(lam)
    lam = P.LAMBDA;
  end
  if nargin < 5 || isempty(zeta)
    zeta = P.ZETA;
  end
  e = het_loop_error_mag(f_v, fn, zeta) .* (2 * v_peak ./ (lam * f_v));
end
