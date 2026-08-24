function name = select_band_hysteresis(f_target_hz, current_band, v_peak)
%SELECT_BAND_HYSTERESIS Guard-first gear select with one-step downshift.
  dp = design_params();
  if nargin < 2 || isempty(current_band), current_band = 'SLOW'; end
  if nargin < 3, v_peak = []; end
  target = select_band(f_target_hz, v_peak);
  cur_i = find(strcmp(dp.ORDER, current_band), 1);
  if isempty(cur_i)
    name = target;
    return
  end
  tgt_i = find(strcmp(dp.ORDER, target), 1);
  if tgt_i >= cur_i
    name = target;
    return
  end
  if cur_i - tgt_i >= 1
    name = dp.ORDER{cur_i - 1};
    return
  end
  name = target;
end
