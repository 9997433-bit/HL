function dp = design_params()
%DESIGN_PARAMS 1550 nm homodyne IQ three-gear tracking-filter parameter set.
%   Port of homodyne_tracking_design/design_params.py (constants).
%   Returns a struct with the module-level constants; the module functions
%   are separate .m files (gate_params, loop_gains, b_loop, band_specs,
%   loop_error_mag, tracking_error_rad, guard_flags, select_band,
%   select_band_hysteresis, cfg_for_frequency).
  persistent cache
  if isempty(cache)
    d = struct();
    d.LAMBDA = 1550e-9;
    d.FS = 250e6;
    % Front-end bandwidth split (audit): F_SIGNAL_MAX = single-sided hard
    % signal passband (30 m/s -> fD_peak 38.7 MHz + margin); B_NOISE_ENBW =
    % two-sided noise ENBW of the measured AFE.  B_FRONTEND stays as the
    % backward-compat alias of the NOISE bandwidth.
    d.F_SIGNAL_MAX = 43e6;
    d.B_NOISE_ENBW = 40e6;
    d.B_FRONTEND = d.B_NOISE_ENBW;   % alias (noise ENBW, NOT signal passband)
    d.ZETA = 1.2;          % carrier-loop economy (see validate_zeta_sweep)

    % common residual measurement window (identical in every gear)
    d.B_WIN = 4e6;         % FIR -6 dB cutoff; flat (<1% err) band DC..~3.6 MHz
    d.NT_WIN = 1025;       % linear-phase Hann-window FIR taps @ fs=250 MS/s
    d.TAU_G = 2e-6;        % residual soft-gate smoothing (dropout blanking)

    d.B_LOOP_COEF = pi * (1 + 4 * d.ZETA^2) / (4 * d.ZETA);   % 4.4244 @ zeta=1.2
    d.F3DB_COEF = sqrt(((2 + 4 * d.ZETA^2) ...
                        + hypot(2 + 4 * d.ZETA^2, 2)) / 2);

    d.BANDS = struct( ...
      'SLOW',   struct('f_target_max', 200e3, 'fn', 110e3, ...
                       'label', '结构/低频, 最高灵敏度', ...
                       'tauP', 4e-6, 'tauF', 8e-6), ...
      'MEDIUM', struct('f_target_max', 1e6, 'fn', 530e3, ...
                       'label', '常用 ≤1 MHz', ...
                       'tauP', 2e-6, 'tauF', 2e-6), ...
      'FAST',   struct('f_target_max', 3e6, 'fn', 1.60e6, ...
                       'label', '最高 3 MHz', ...
                       'tauP', 1e-6, 'tauF', 1e-6));
    d.ORDER = {'SLOW', 'MEDIUM', 'FAST'};

    d.GATE_COMMON = struct('snr_on', 1.0, 'snr_off', 0.3, ...
                           'rel_on', 0.20, 'rel_off', 0.08, ...
                           'tauRef', 200e-6, 'reacq', true);

    d.PHI_GUARD = 1.0;     % rad, max allowed untracked Doppler phase

    % Unknown v_peak ([]/NaN, Python None) is evaluated CONSERVATIVELY at
    % the instrument maximum (30 m/s); the frequency-only fallback is
    % removed (audit: 100 kHz @ 30 m/s must not land in SLOW).
    d.APP_V_PEAK_MAX = 30.0;

    d.TRACKING_MODES = {'pll', 'off', 'fixed_lp'};
    d.GATE_POLICIES = {'auto', 'always'};

    d.APP_HYBRID = struct('typical_f_max', 100e3, 'instrument_f_max', 3e6, ...
                          'default_band', 'SLOW');
    d.BAND_HYSTERESIS = struct( ...
      'SLOW_MEDIUM', struct('rise', 200e3, 'fall', 150e3), ...
      'MEDIUM_FAST', struct('rise', 1e6, 'fall', 800e3));
    cache = d;
  end
  dp = cache;
end
