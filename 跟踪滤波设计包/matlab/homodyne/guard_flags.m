function gf = guard_flags(f_target_hz, v_peak, band)
%GUARD_FLAGS Tracking-error guard status of `band` at (f_target_hz, v_peak).
%   v_peak = [] (Python None) -> all three flags are [].
  dp = design_params();
  if isempty(v_peak)
    gf = struct('phi_err', [], 'guard_ok', [], 'overrange', []);
    return
  end
  pe = tracking_error_rad(f_target_hz, v_peak, dp.BANDS.(band).fn);
  gf = struct('phi_err', pe, 'guard_ok', pe <= dp.PHI_GUARD, ...
              'overrange', pe > dp.PHI_GUARD);
end
