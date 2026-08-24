function name = hd_select_band(f_target_hz, v_peak)
%HD_SELECT_BAND Homodyne gear choice: narrowest band passing the tracking-error guard.
% Port of design_params.py::select_band.  v_peak = [] / NaN (or omitted,
% Python None) is evaluated CONSERVATIVELY at P.APP_V_PEAK_MAX (30 m/s);
% the old frequency-only rule is removed (audit: unknown-but-fast motion at
% 100 kHz must not land in SLOW).
  P = hd_params();
  if nargin < 2 || isempty(v_peak) || (isnumeric(v_peak) && any(isnan(v_peak)))
    v_peak = P.APP_V_PEAK_MAX;
  end
  for i = 1:numel(P.ORDER)
    if hd_tracking_error_rad(f_target_hz, v_peak, ...
                             P.BANDS.(P.ORDER{i}).fn) <= P.PHI_GUARD
      name = P.ORDER{i};
      return;
    end
  end
  name = P.ORDER{end};
end
