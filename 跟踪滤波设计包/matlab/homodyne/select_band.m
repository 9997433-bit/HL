function name = select_band(f_target_hz, v_peak)
%SELECT_BAND Homodyne gear choice: narrowest band passing the guard.
%   v_peak = [] / NaN / omitted (Python None) -> evaluated CONSERVATIVELY at
%   dp.APP_V_PEAK_MAX (30 m/s, instrument maximum).  The old frequency-only
%   fallback is removed (audit: unknown-but-fast motion at 100 kHz must not
%   land in SLOW).  Pass the real v_peak to regain the narrow gears.
  dp = design_params();
  if nargin < 2 || isempty(v_peak) || (isnumeric(v_peak) && any(isnan(v_peak)))
    v_peak = dp.APP_V_PEAK_MAX;
  end
  for i = 1:numel(dp.ORDER)
    if tracking_error_rad(f_target_hz, v_peak, ...
                          dp.BANDS.(dp.ORDER{i}).fn) <= dp.PHI_GUARD
      name = dp.ORDER{i};
      return
    end
  end
  name = dp.ORDER{end};
end
