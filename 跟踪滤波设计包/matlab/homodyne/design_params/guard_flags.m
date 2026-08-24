function g = guard_flags(f_target_hz, v_peak, band)
%GUARD_FLAGS Tracking-error guard status of `band` at (f_target_hz, v_peak).
%   g = guard_flags(f_target_hz, v_peak, band)
%   Faithful port of design_params.py guard_flags.
%
%   g.phi_err    untracked Doppler phase (rad); NaN when v_peak is unknown
%                (Python None <-> [] or NaN here).
%   g.guard_ok   phi_err <= PHI_GUARD; NaN when unknown.
%   g.overrange  true when the applied gear exceeds the 1 rad guard (the
%                documented degraded zone -- see the Python docstring);
%                NaN when unknown.
  C = homodyne_constants();
  if isempty(v_peak) || (isnumeric(v_peak) && any(isnan(v_peak)))
    g = struct('phi_err', NaN, 'guard_ok', NaN, 'overrange', NaN);
    return
  end
  pe = tracking_error_rad(f_target_hz, v_peak, C.BANDS.(band).fn);
  g = struct('phi_err', pe, 'guard_ok', pe <= C.PHI_GUARD, ...
             'overrange', pe > C.PHI_GUARD);
end
