function cfg = cfg_for_frequency(f_target_hz, v_peak, current_band, ...
                                 hysteresis, tracking_mode, gate_policy)
%CFG_FOR_FREQUENCY Full config struct for the current measurement frequency.
%   cfg = cfg_for_frequency(f_target_hz, v_peak, current_band, hysteresis,
%                           tracking_mode, gate_policy)
%   Faithful port of design_params.py cfg_for_frequency.  Defaults:
%   v_peak=[] (unknown), current_band='SLOW', hysteresis=true,
%   tracking_mode='pll', gate_policy='auto'.
%
%   tracking_mode='pll': gear-selected PLL carrier path + common residual
%       window.  gate_policy='auto' runs the 3-state dropout gate;
%       gate_policy='always' bypasses the gate (loop always closed) -- the
%       PLL still tracks, this is NOT the OFF mode.
%   tracking_mode='off': tracking bypass -- output is angle(z) / FM
%       discrimination (off_mode).  gate_policy is irrelevant and ignored.
%   tracking_mode='fixed_lp': no PLL; output is the common B_WIN complex
%       low-pass of z (fixed_lp_mode).
%
%   PLL cfg structs also carry the guard status of the applied gear:
%   phi_err (rad), guard_ok, overrange -- see guard_flags.  v_peak = []
%   (Python None) is evaluated CONSERVATIVELY at C.APP_V_PEAK_MAX (30 m/s),
%   e.g. cfg_for_frequency(100e3) selects FAST with overrange=true.
%   band is '' for off / fixed_lp (Python uses None).
%
%   Feed the returned struct to tracking_filter.
  C = homodyne_constants();
  if nargin < 2, v_peak = []; end
  if nargin < 3 || isempty(current_band), current_band = 'SLOW'; end
  if nargin < 4 || isempty(hysteresis), hysteresis = true; end
  if nargin < 5 || isempty(tracking_mode), tracking_mode = 'pll'; end
  if nargin < 6 || isempty(gate_policy), gate_policy = 'auto'; end

  if ~any(strcmp(C.TRACKING_MODES, tracking_mode))
    error('homodyne:ValueError', ...
          'tracking_mode must be one of {pll, off, fixed_lp}, got %s', ...
          tracking_mode);
  end
  if ~any(strcmp(C.GATE_POLICIES, gate_policy))
    error('homodyne:ValueError', ...
          'gate_policy must be one of {auto, always}, got %s', gate_policy);
  end
  if strcmp(tracking_mode, 'off')
    cfg = struct('tracking_mode', 'off', 'band', '', ...
                 'f_target_hz', f_target_hz);
    return
  end
  if strcmp(tracking_mode, 'fixed_lp')
    cfg = struct('tracking_mode', 'fixed_lp', 'band', '', ...
                 'f_target_hz', f_target_hz, ...
                 'B_win', C.B_WIN, 'NT_win', C.NT_WIN);
    return
  end
  if hysteresis
    band = select_band_hysteresis(f_target_hz, current_band, v_peak);
  else
    band = select_band(f_target_hz, v_peak);
  end
  cfg = struct('tracking_mode', 'pll', 'gate', gate_policy, ...
               'band', band, 'f_target_hz', f_target_hz);
  s = band_specs(band);
  sf = fieldnames(s);
  for i = 1:numel(sf)
    cfg.(sf{i}) = s.(sf{i});
  end
  g = guard_flags(f_target_hz, v_peak, band);
  gf = fieldnames(g);
  for i = 1:numel(gf)
    cfg.(gf{i}) = g.(gf{i});
  end
end
