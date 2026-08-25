function rc = validate_realistic_scenarios(mode)
%VALIDATE_REALISTIC_SCENARIOS Realistic-scenario study -- STUB (interface spec).
%
%   rc = validate_realistic_scenarios()        quick study (default)
%   rc = validate_realistic_scenarios('full')  reserved for the full study
%
%   *** THIS FILE IS CURRENTLY A STUB. ***
%   The full realistic-scenario validator (Monte-Carlo time-domain runs of
%   the three ported designs under application-like conditions) is being
%   developed in a parallel task and will REPLACE this file, keeping the
%   same name, call signature and output contract described below.  The
%   stub already fills every documented field using the committed
%   deterministic design functions plus a small speckle Monte-Carlo, so the
%   downstream plotting pipeline (scenario_study/plot_scenario_results.m)
%   can be exercised end-to-end today.
%
%   OUTPUT CONTRACT
%   ---------------
%   Saves  matlab/scenario_study/results_realistic_scenarios.mat  (MAT v7,
%   flat variables, loadable by MATLAB R2020b+ and GNU Octave >= 8) with AT
%   LEAST the fields below; the full implementation may append more fields
%   but must not rename or reshape these.  plot_scenario_results.m consumes
%   exactly this set.
%
%   Provenance
%     schema_version   1
%     is_stub          1 = placeholder data (this stub), 0 = full study
%     created          char, datestr of generation time
%
%   S1  Homodyne operating map  (1550 nm, three-gear auto selection)
%     map_f_hz         1 x Nf   vibration frequency grid (log spaced)
%     map_v_mps        1 x Nv   peak velocity grid (log spaced)
%     map_phi_err_rad  Nv x Nf  untracked Doppler phase of the gear chosen
%                               by select_band(f, v) at each grid point
%     map_band_idx     Nv x Nf  chosen gear: 1=SLOW 2=MEDIUM 3=FAST
%     map_band_order   1 x 3 cellstr {'SLOW','MEDIUM','FAST'}
%     map_phi_guard_rad  scalar PHI_GUARD (1 rad)
%
%   S2  QTec speckle-diversity tradeoff  (joint deep-fade prob. vs M)
%     spk_M            1 x Nm   channel counts (e.g. 1..6)
%     spk_F            1 x NF   fade thresholds I < F*<I> (e.g. 0.3567, 0.105)
%     spk_p_theory     NF x Nm  theory (1 - exp(-F))^M
%     spk_p_mc         NF x Nm  Monte-Carlo joint fade fraction (NaN allowed)
%     spk_rho          scalar   pairwise field correlation used in the MC
%     spk_tau_c_s, spk_fs_hz, spk_T_s, spk_nseed   MC conditions
%
%   S3  Heterodyne velocity bathtub  (HeNe 632.8 nm, pure NCO)
%     bath_f_hz        1 x Nb   vibration frequency grid
%     bath_v_pll_mps   3 x Nb   per-gear trackable velocity limit
%                               v_pll_limit(f, fn), rows follow bath_gear_order
%     bath_fn_hz       1 x 3    per-gear loop natural frequency
%     bath_gear_order  1 x 3 cellstr {'SLOW','MEDIUM','FAST'}
%     bath_v_if_mps    scalar   IF hard-window velocity limit
%     bath_v_alias_mps scalar   sampling alias velocity limit
%     bath_v_range_mps scalar   v_range used for the gear table
%     bath_lambda_m    scalar   wavelength
%     bath_e_crit_rad  scalar   phase-error criterion of the pll limit (pi)
%
%   Returns rc = 0 on success (nonzero / error on failure), same convention
%   as the other validators, so it can slot into run_all_verify later.
  if nargin < 1 || isempty(mode)
    mode = 'quick';
  end
  here = fileparts(mfilename('fullpath'));
  addpath(here);
  homodyne_setup_path();
  addpath(fullfile(here, 'heterodyne'));
  addpath(fullfile(here, 'qtec'));

  fprintf(['validate_realistic_scenarios: STUB (deterministic design maps + ' ...
           'small speckle MC).\n  The full Monte-Carlo scenario study will ' ...
           'replace this file with the same interface.\n']);
  t0 = tic;

  R = struct();
  R.schema_version = 1;
  R.is_stub = 1;
  R.created = datestr(now, 'yyyy-mm-dd HH:MM:SS');

  % -- S1: homodyne operating map -------------------------------------------
  C = homodyne_constants();
  Nf = 61;
  Nv = 41;
  R.map_f_hz = logspace(3, log10(3e6), Nf);          % 1 kHz .. 3 MHz
  R.map_v_mps = logspace(-3, log10(30), Nv);         % 1 mm/s .. 30 m/s
  R.map_band_order = {'SLOW', 'MEDIUM', 'FAST'};
  R.map_phi_guard_rad = C.PHI_GUARD;
  R.map_phi_err_rad = zeros(Nv, Nf);
  R.map_band_idx = zeros(Nv, Nf);
  for iv = 1:Nv
    for jf = 1:Nf
      f = R.map_f_hz(jf);
      v = R.map_v_mps(iv);
      band = select_band(f, v);
      idx = find(strcmp(band, R.map_band_order));
      R.map_band_idx(iv, jf) = idx;
      R.map_phi_err_rad(iv, jf) = ...
          tracking_error_rad(f, v, C.BANDS.(band).fn);
    end
  end
  fprintf('  S1 homodyne operating map: %d x %d grid done\n', Nv, Nf);

  % -- S2: speckle-diversity tradeoff ----------------------------------------
  % Same fade definitions as validate_diversity_p0_p1 P0 (-4.5 dB / -9.8 dB);
  % stub MC is one seed x 1 s per M (P0 itself uses 6 seeds x 2.5 s).
  R.spk_M = 1:6;
  R.spk_F = [0.3567, 0.105];
  R.spk_rho = 0.0;
  R.spk_tau_c_s = 50e-6;
  R.spk_fs_hz = 400e3;
  R.spk_T_s = 1.0;
  R.spk_nseed = 1;
  R.spk_p_theory = zeros(numel(R.spk_F), numel(R.spk_M));
  R.spk_p_mc = nan(numel(R.spk_F), numel(R.spk_M));
  Nmc = floor(R.spk_T_s * R.spk_fs_hz);
  for im = 1:numel(R.spk_M)
    M = R.spk_M(im);
    set_rng(40000 + 97 * M);
    h = make_speckle_multi(Nmc, R.spk_fs_hz, R.spk_tau_c_s, M, R.spk_rho);
    for kf = 1:numel(R.spk_F)
      R.spk_p_theory(kf, im) = fade_prob_theory(R.spk_F(kf), M);
      R.spk_p_mc(kf, im) = joint_fade_fraction(h, R.spk_F(kf));
    end
  end
  fprintf('  S2 speckle tradeoff: M = 1..%d, %d thresholds done\n', ...
          max(R.spk_M), numel(R.spk_F));

  % -- S3: heterodyne velocity bathtub ---------------------------------------
  P = het_params();
  R.bath_v_range_mps = P.V_RANGE_DEFAULT;
  R.bath_lambda_m = P.LAMBDA;
  R.bath_e_crit_rad = pi;
  R.bath_gear_order = P.ORDER;
  modes = het_mode_params(R.bath_v_range_mps);
  Nb = 121;
  R.bath_f_hz = logspace(2, log10(2e6), Nb);         % 100 Hz .. 2 MHz
  R.bath_fn_hz = zeros(1, 3);
  R.bath_v_pll_mps = zeros(3, Nb);
  for ig = 1:numel(P.ORDER)
    fn = modes.(P.ORDER{ig}).fn;
    R.bath_fn_hz(ig) = fn;
    R.bath_v_pll_mps(ig, :) = het_v_pll_limit(R.bath_f_hz, fn);
  end
  R.bath_v_if_mps = het_v_if_limit();
  R.bath_v_alias_mps = het_v_alias_limit();
  fprintf('  S3 heterodyne bathtub: 3 gears x %d freqs done\n', Nb);

  % -- save -------------------------------------------------------------------
  out_dir = fullfile(here, 'scenario_study');
  if ~exist(out_dir, 'dir')
    mkdir(out_dir);
  end
  out_mat = fullfile(out_dir, 'results_realistic_scenarios.mat');
  if exist('OCTAVE_VERSION', 'builtin') ~= 0
    save('-v7', out_mat, '-struct', 'R');
  else
    save(out_mat, '-struct', 'R', '-v7');
  end
  fprintf('  saved %s  [elapsed %.1f s]\n', out_mat, toc(t0));
  fprintf(['  next: cd scenario_study; plot_scenario_results   ' ...
           '(figures -> scenario_study/figs/)\n']);
  if strcmp(mode, 'full')
    fprintf(['  NOTE: ''full'' mode is reserved for the complete Monte-Carlo ' ...
             'study (parallel task);\n  the stub output is identical in both ' ...
             'modes.\n']);
  end
  rc = 0;
end
