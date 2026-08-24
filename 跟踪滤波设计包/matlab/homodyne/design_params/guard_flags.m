function g = guard_flags(f_target_hz, v_peak, band)
%GUARD_FLAGS Tracking-error guard status of `band` at (f_target_hz, v_peak).
%   g = guard_flags(f_target_hz, v_peak, band)
%   Faithful port of design_params.py guard_flags.
%
%   v_peak = [] or NaN (Python None) is evaluated CONSERVATIVELY at
%   C.APP_V_PEAK_MAX (30 m/s): the flags are then the worst-case guard
%   status, never NaN.
%
%   g.phi_err    untracked Doppler phase (rad).
%   g.guard_ok   phi_err <= PHI_GUARD.
%   g.overrange  true when the applied gear exceeds the 1 rad guard (the
%                documented degraded zone -- see the Python docstring).
  C = homodyne_constants();
  if isempty(v_peak) || (isnumeric(v_peak) && any(isnan(v_peak)))
    v_peak = C.APP_V_PEAK_MAX;
  end
  pe = tracking_error_rad(f_target_hz, v_peak, C.BANDS.(band).fn);
  g = struct('phi_err', pe, 'guard_ok', pe <= C.PHI_GUARD, ...
             'overrange', pe > C.PHI_GUARD);
end
