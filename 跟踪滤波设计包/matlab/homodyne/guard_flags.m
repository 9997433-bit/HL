function gf = guard_flags(f_target_hz, v_peak, band)
%GUARD_FLAGS Tracking-error guard status of `band` at (f_target_hz, v_peak).
%   v_peak = [] / NaN (Python None) -> evaluated CONSERVATIVELY at
%   dp.APP_V_PEAK_MAX (30 m/s); the flags are then the worst-case guard
%   status, never [].
  dp = design_params();
  if isempty(v_peak) || (isnumeric(v_peak) && any(isnan(v_peak)))
    v_peak = dp.APP_V_PEAK_MAX;
  end
  pe = tracking_error_rad(f_target_hz, v_peak, dp.BANDS.(band).fn);
  gf = struct('phi_err', pe, 'guard_ok', pe <= dp.PHI_GUARD, ...
              'overrange', pe > dp.PHI_GUARD);
end
