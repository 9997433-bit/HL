function name = select_band(f_target_hz, v_peak)
%SELECT_BAND Homodyne gear choice: narrowest band passing the guard.
%   v_peak = [] or omitted (Python None) -> frequency-first selection.
  dp = design_params();
  if nargin < 2, v_peak = []; end
  if isempty(v_peak)
    idx = numel(dp.ORDER);
    for i = 1:numel(dp.ORDER)
      if f_target_hz <= dp.BANDS.(dp.ORDER{i}).f_target_max
        idx = i;
        break
      end
    end
    name = dp.ORDER{idx};
    return
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
