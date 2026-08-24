function P = hd_params()
%HD_PARAMS 1550 nm homodyne IQ three-gear tracking-filter parameter set.
% Port of homodyne_tracking_design/design_params.py (constants + BANDS +
% GATE_COMMON).  Returned as a struct so callers read P.FS, P.BANDS.SLOW.fn, ...
  P.LAMBDA = 1550e-9;
  P.FS = 250e6;
  P.B_FRONTEND = 40e6;       % complex-baseband two-sided ENBW
  P.ZETA = 1.2;              % carrier-loop economy (flatness set by the window)

  % common residual measurement window (identical in every gear)
  P.B_WIN = 4e6;             % FIR -6 dB cutoff; flat band DC..~3.6 MHz
  P.NT_WIN = 1025;           % linear-phase Hann FIR taps at fs = 250 MS/s
  P.TAU_G = 2e-6;            % residual soft-gate smoothing (dropout blanking)

  P.B_LOOP_COEF = pi * (1 + 4 * P.ZETA ^ 2) / (4 * P.ZETA);   % 4.4244 (zeta=1.2)
  b = 2 + 4 * P.ZETA ^ 2;
  P.F3DB_COEF = sqrt((b + hypot(b, 2)) / 2);                  % 2.808 (zeta=1.2)

  P.BANDS.SLOW = struct('f_target_max', 200e3, 'fn', 110e3, ...
                        'tauP', 4e-6, 'tauF', 8e-6);
  P.BANDS.MEDIUM = struct('f_target_max', 1e6, 'fn', 530e3, ...
                          'tauP', 2e-6, 'tauF', 2e-6);
  P.BANDS.FAST = struct('f_target_max', 3e6, 'fn', 1.60e6, ...
                        'tauP', 1e-6, 'tauF', 1e-6);
  P.ORDER = {'SLOW', 'MEDIUM', 'FAST'};

  % Gate = dropout detector (NOT an FM-threshold detector)
  P.GATE_COMMON = struct('snr_on', 1.0, 'snr_off', 0.3, ...
                         'rel_on', 0.20, 'rel_off', 0.08, ...
                         'tauRef', 200e-6, 'reacq', true);

  P.PHI_GUARD = 1.0;         % rad, max allowed untracked Doppler phase
end
