function name = select_band_hysteresis(f_target_hz, current_band, v_peak)
%SELECT_BAND_HYSTERESIS Guard-first gear select with one-step downshift anti-chatter.
%   name = select_band_hysteresis(f_target_hz, current_band, v_peak)
%   Faithful port of design_params.py select_band_hysteresis.
%   current_band defaults to 'SLOW'; pass [] or NaN for an unknown v_peak.
%
%   Target band comes from select_band (phase-error guard, narrowest pass).
%   Upshifts to satisfy the guard take effect immediately.  Downshifts are
%   limited to one gear step per update so f_target / v_peak dither does
%   not bounce SLOW<->FAST.
  C = homodyne_constants();
  if nargin < 2 || isempty(current_band)
    current_band = 'SLOW';
  end
  if nargin < 3
    v_peak = [];
  end
  target = select_band(f_target_hz, v_peak);
  cur_i = find(strcmp(C.ORDER, current_band), 1);
  if isempty(cur_i)
    name = target;
    return
  end
  tgt_i = find(strcmp(C.ORDER, target), 1);
  if tgt_i >= cur_i
    name = target;
    return
  end
  if cur_i - tgt_i >= 1
    name = C.ORDER{cur_i - 1};
    return
  end
  name = target;
end
