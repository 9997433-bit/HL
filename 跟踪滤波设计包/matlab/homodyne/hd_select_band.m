function name = hd_select_band(f_target_hz, v_peak)
%HD_SELECT_BAND Homodyne gear choice: narrowest band passing the tracking-error guard.
% Port of design_params.py::select_band.  v_peak = [] (or omitted) uses the
% frequency-only rule.
  P = hd_params();
  if nargin < 2 || isempty(v_peak)
    idx = numel(P.ORDER);
    for i = 1:numel(P.ORDER)
      if f_target_hz <= P.BANDS.(P.ORDER{i}).f_target_max
        idx = i;
        break;
      end
    end
    name = P.ORDER{idx};
    return;
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
