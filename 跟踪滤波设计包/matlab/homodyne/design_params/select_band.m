function name = select_band(f_target_hz, v_peak)
%SELECT_BAND Homodyne gear choice: narrowest band passing the tracking-error guard.
%   name = select_band(f_target_hz)          frequency-only rule
%   name = select_band(f_target_hz, v_peak)  guard-first rule
%   Faithful port of design_params.py select_band.  Pass [] or NaN for an
%   unknown v_peak (Python None).
%
%   Among gears whose untracked Doppler phase |1-H_L(f)| * phi_amp stays
%   below PHI_GUARD, pick the narrowest (lowest B_loop) for best weak-light
%   SNR.  If none pass, use the widest gear.
  C = homodyne_constants();
  if nargin < 2 || isempty(v_peak) || (isnumeric(v_peak) && any(isnan(v_peak)))
    idx = numel(C.ORDER);
    for i = 1:numel(C.ORDER)
      if f_target_hz <= C.BANDS.(C.ORDER{i}).f_target_max
        idx = i;
        break
      end
    end
    name = C.ORDER{idx};
    return
  end
  for i = 1:numel(C.ORDER)
    if tracking_error_rad(f_target_hz, v_peak, ...
                          C.BANDS.(C.ORDER{i}).fn) <= C.PHI_GUARD
      name = C.ORDER{i};
      return
    end
  end
  name = C.ORDER{end};
end
