function C = homodyne_constants()
%HOMODYNE_CONSTANTS 1550 nm homodyne IQ three-gear tracking-filter parameter set.
%   C = homodyne_constants()
%   Faithful port of homodyne_tracking_design/design_params.py module-level
%   constants (see that file's docstring for the full architecture,
%   click-cleanup condition, loop design rule and gear selection rule).
%
%   Fields:
%     LAMBDA, FS, B_FRONTEND, ZETA, B_WIN, NT_WIN, TAU_G
%     B_LOOP_COEF, F3DB_COEF        (private _B_LOOP_COEF/_F3DB_COEF in Python)
%     BANDS   struct SLOW/MEDIUM/FAST, each with f_target_max, fn, label,
%             tauP, tauF
%     ORDER   {'SLOW','MEDIUM','FAST'}
%     GATE_COMMON  snr_on, snr_off, rel_on, rel_off, tauRef, reacq
%     PHI_GUARD
%     TRACKING_MODES {'pll','off','fixed_lp'}, GATE_POLICIES {'auto','always'}
%     APP_HYBRID, BAND_HYSTERESIS
  C.LAMBDA = 1550e-9;
  C.FS = 250e6;
  % Front-end bandwidth split (audit): F_SIGNAL_MAX = single-sided hard
  % signal passband (30 m/s -> fD_peak 38.7 MHz + margin); B_NOISE_ENBW =
  % two-sided noise ENBW of the measured AFE.  B_FRONTEND stays as the
  % backward-compat alias of the NOISE bandwidth.
  C.F_SIGNAL_MAX = 43e6;
  C.B_NOISE_ENBW = 40e6;
  C.B_FRONTEND = C.B_NOISE_ENBW;  % alias (noise ENBW, NOT signal passband)
  C.ZETA = 1.2;              % carrier-loop economy; output flatness is set by
                             % the common FIR window, NOT |H_L| (review item #7)

  % common residual measurement window (identical in every gear)
  C.B_WIN = 4e6;             % FIR -6 dB cutoff; flat (<1% err) band DC..~3.6 MHz
  % NT_WIN: linear-phase Hann-window FIR taps referenced to fs=250 MS/s.
  % Hardware must implement a multirate equivalent (see design_params.py note).
  C.NT_WIN = 1025;
  C.TAU_G = 2e-6;            % residual soft-gate smoothing (dropout blanking)

  C.B_LOOP_COEF = pi * (1 + 4 * C.ZETA ^ 2) / (4 * C.ZETA);  % 4.4244 (zeta=1.2)
  % -3 dB closed-loop frequency coefficient: solve |H_L|^2 = 1/2 ->
  % x^2 = ((2+4z^2) + sqrt((2+4z^2)^2+4))/2;  2.808 at zeta=1.2
  C.F3DB_COEF = sqrt(((2 + 4 * C.ZETA ^ 2) ...
                      + hypot(2 + 4 * C.ZETA ^ 2, 2)) / 2);

  % fn = f_max / 1.875, rounded (output flatness is window-defined, fn only
  % scales the guard and B_loop); gate constants scale with band dynamics.
  C.BANDS = struct( ...
    'SLOW', struct('f_target_max', 200e3, 'fn', 110e3, ...
                   'label', '结构/低频, 最高灵敏度', ...
                   'tauP', 4e-6, 'tauF', 8e-6), ...
    'MEDIUM', struct('f_target_max', 1e6, 'fn', 530e3, ...
                     'label', '常用 ≤1 MHz', ...
                     'tauP', 2e-6, 'tauF', 2e-6), ...
    'FAST', struct('f_target_max', 3e6, 'fn', 1.60e6, ...
                   'label', '最高 3 MHz', ...
                   'tauP', 1e-6, 'tauF', 1e-6));
  C.ORDER = {'SLOW', 'MEDIUM', 'FAST'};

  % Gate = dropout detector (NOT an FM-threshold detector).
  C.GATE_COMMON = struct('snr_on', 1.0, 'snr_off', 0.3, ...
                         'rel_on', 0.20, 'rel_off', 0.08, ...
                         'tauRef', 200e-6, 'reacq', true);

  C.PHI_GUARD = 1.0;         % rad, max allowed untracked Doppler phase

  % Unknown v_peak ([]/NaN, Python None) is evaluated CONSERVATIVELY at the
  % instrument maximum (30 m/s); the frequency-only fallback is removed
  % (audit: 100 kHz @ 30 m/s must not land in SLOW).
  C.APP_V_PEAK_MAX = 30.0;

  % Product-level operating modes.  OFF is NOT a fourth gear.
  C.TRACKING_MODES = {'pll', 'off', 'fixed_lp'};
  C.GATE_POLICIES = {'auto', 'always'};  % PLL only

  % Application: mostly <100 kHz, instrument max 3 MHz
  C.APP_HYBRID = struct('typical_f_max', 100e3, ...
                        'instrument_f_max', 3e6, ...
                        'default_band', 'SLOW');

  C.BAND_HYSTERESIS = struct( ...
    'SLOW_MEDIUM', struct('rise', 200e3, 'fall', 150e3), ...
    'MEDIUM_FAST', struct('rise', 1e6, 'fall', 800e3));
end
