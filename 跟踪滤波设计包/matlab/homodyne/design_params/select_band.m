function name = select_band(f_target_hz, v_peak)
%SELECT_BAND Homodyne gear choice: narrowest band passing the tracking-error guard.
%   name = select_band(f_target_hz)          conservative default (see below)
%   name = select_band(f_target_hz, v_peak)  guard-first rule
%   Faithful port of design_params.py select_band.  Pass [] or NaN for an
%   unknown v_peak (Python None): it is then evaluated CONSERVATIVELY at
%   C.APP_V_PEAK_MAX (30 m/s, instrument maximum).  The old frequency-only
%   fallback is removed (audit: unknown-but-fast motion at 100 kHz must not
%   land in SLOW).  Pass the real v_peak to regain the narrow gears.
%
%   Among gears whose untracked Doppler phase |1-H_L(f)| * phi_amp stays
%   below PHI_GUARD, pick the narrowest (lowest B_loop) for best weak-light
%   SNR.  If none pass, use the widest gear.
  C = homodyne_constants();
  if nargin < 2 || isempty(v_peak) || (isnumeric(v_peak) && any(isnan(v_peak)))
    v_peak = C.APP_V_PEAK_MAX;
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
