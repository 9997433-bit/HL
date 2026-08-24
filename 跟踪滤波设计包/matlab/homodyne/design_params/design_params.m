function dp = design_params()
%DESIGN_PARAMS 1550 nm homodyne IQ three-gear tracking-filter parameter set.
%   Alias of homodyne_constants() (the canonical port of the module-level
%   constants in homodyne_tracking_design/design_params.py), kept for the
%   validators which read dp = design_params().  The module FUNCTIONS are
%   the separate .m files in this folder (gate_params, loop_gains, b_loop,
%   band_specs, loop_error_mag, tracking_error_rad, guard_flags,
%   select_band, select_band_hysteresis, cfg_for_frequency).
  persistent cache
  if isempty(cache)
    cache = homodyne_constants();
  end
  dp = cache;
end
