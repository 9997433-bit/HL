function cfg = cfg_for_frequency(f_target_hz, v_peak, current_band, ...
                                 hysteresis, tracking_mode, gate_policy)
%CFG_FOR_FREQUENCY Full config struct for the current measurement frequency.
%   Port of design_params.cfg_for_frequency.  v_peak = [] means Python None.
%   band = [] mirrors Python band=None for the off / fixed_lp modes.
%   Raises an error (Python ValueError) on illegal tracking_mode/gate_policy.
  dp = design_params();
  if nargin < 2, v_peak = []; end
  if nargin < 3 || isempty(current_band), current_band = 'SLOW'; end
  if nargin < 4 || isempty(hysteresis), hysteresis = true; end
  if nargin < 5 || isempty(tracking_mode), tracking_mode = 'pll'; end
  if nargin < 6 || isempty(gate_policy), gate_policy = 'auto'; end

  if ~any(strcmp(dp.TRACKING_MODES, tracking_mode))
    error('homodyne:ValueError', ...
          'tracking_mode must be one of {pll, off, fixed_lp}, got %s', ...
          tracking_mode);
  end
  if ~any(strcmp(dp.GATE_POLICIES, gate_policy))
    error('homodyne:ValueError', ...
          'gate_policy must be one of {auto, always}, got %s', gate_policy);
  end
  if strcmp(tracking_mode, 'off')
    cfg = struct('tracking_mode', 'off', 'band', [], ...
                 'f_target_hz', f_target_hz);
    return
  end
  if strcmp(tracking_mode, 'fixed_lp')
    cfg = struct('tracking_mode', 'fixed_lp', 'band', [], ...
                 'f_target_hz', f_target_hz, ...
                 'B_win', dp.B_WIN, 'NT_win', dp.NT_WIN);
    return
  end
  if hysteresis
    band = select_band_hysteresis(f_target_hz, current_band, v_peak);
  else
    band = select_band(f_target_hz, v_peak);
  end
  cfg = struct('tracking_mode', 'pll', 'gate', gate_policy, 'band', band, ...
               'f_target_hz', f_target_hz);
  cfg = merge_struct(cfg, band_specs(band));
  cfg = merge_struct(cfg, guard_flags(f_target_hz, v_peak, band));
end

function s = merge_struct(s, t)
  fns = fieldnames(t);
  for i = 1:numel(fns)
    s.(fns{i}) = t.(fns{i});
  end
end
