function rc = compare_qtec_golden(golden_file)
%COMPARE_QTEC_GOLDEN Compare the MATLAB qtec diversity port against Python golden data.
% Loads matlab/golden/qtec_golden.mat (written by
% export_heterodyne_qtec_golden.py) and re-runs the ported P0 statistics
% helpers and the full P1 chain (channel_demod with the gate='auto' 3-state
% PLL, block weights, diversity combine) on the EXPORTED inputs.
% Returns rc = 0 iff every check passes.
  here = fileparts(mfilename('fullpath'));
  addpath(fullfile(here, '..', 'homodyne'));
  addpath(here);
  if nargin < 1 || isempty(golden_file)
    golden_file = fullfile(here, '..', 'golden', 'qtec_golden.mat');
  end
  g = load(golden_file);
  P = hd_params();
  n_pass = 0;
  n_fail = 0;

  fprintf('\n== compare_qtec_golden ==\n');

  % ---- P0: fade theory + statistics helpers on the exported field ---------
  T = g.fade_theory;
  err = 0;
  for r = 1:size(T, 1)
    err = max(err, abs(fade_prob_theory(T(r, 1), T(r, 2)) - T(r, 3)));
  end
  [n_pass, n_fail] = chk('fade_prob_theory (6 cases)', err, 1e-15, ...
                         n_pass, n_fail);

  h = g.h_field;
  J = g.h_jff;
  err = 0;
  for r = 1:size(J, 1)
    F = J(r, 1);
    got = [joint_fade_fraction(h, F), joint_fade_fraction(h(1, :), F), ...
           joint_fade_fraction(h(2, :), F), joint_fade_fraction(h(3, :), F)];
    err = max(err, max(abs(got - J(r, 2:5))));
  end
  [n_pass, n_fail] = chk('joint_fade_fraction (joint + per-ch)', err, ...
                         1e-12, n_pass, n_fail);
  Cc = channel_correlation(h);
  [n_pass, n_fail] = chk('channel_correlation (3x3 complex)', ...
      max(abs(Cc(:) - g.h_corr(:))), 1e-12, n_pass, n_fail);

  % ---- P1: gear selection --------------------------------------------------
  band = P.ORDER{g.band_idx};
  sel = hd_select_band(3e6, 20e-3);
  [n_pass, n_fail] = chk('select_band(3MHz, 20mm/s)', ...
      double(~strcmp(sel, band)), 0.5, n_pass, n_fail);

  % ---- P1: per-channel demodulation (gate=auto 3-state PLL) ----------------
  z = g.p1_z;
  s2 = g.p1_s2;
  M = size(z, 1);
  N = size(z, 2);
  vch = zeros(M, N);
  stm = zeros(M, N);
  Cm = zeros(M, N);
  gsm = zeros(M, N);
  chans = cell(1, M);
  for k = 1:M
    chans{k} = channel_demod(z(k, :), P.FS, band, s2);
    vch(k, :) = chans{k}.v.';
    stm(k, :) = chans{k}.state.';
    Cm(k, :) = chans{k}.C.';
    gsm(k, :) = chans{k}.gs.';
  end
  [n_pass, n_fail] = chk('channel state trajectory (exact)', ...
      mean(stm(:) ~= g.p1_state(:)), 1e-4, n_pass, n_fail);
  [n_pass, n_fail] = chk('channel C estimate', ...
      max(abs(Cm(:) - g.p1_C(:))) / max(abs(g.p1_C(:))), 1e-9, ...
      n_pass, n_fail);
  [n_pass, n_fail] = chk('channel soft gate gs', ...
      max(abs(gsm(:) - g.p1_gs(:))), 1e-9, n_pass, n_fail);
  [n_pass, n_fail] = chk('channel velocity v', ...
      max(abs(vch(:) - g.p1_v(:))) / max(abs(g.p1_v(:))), 1e-6, ...
      n_pass, n_fail);
  dgot = zeros(M, 5);
  for k = 1:M
    dgot(k, :) = [chans{k}.diag.near_pi_events, chans{k}.diag.n_hold, ...
                  chans{k}.diag.n_acquire, chans{k}.diag.n_lock_entries, ...
                  chans{k}.diag.lock_frac];
  end
  [n_pass, n_fail] = chk('channel diag counters', ...
      max(abs(dgot(:) - g.p1_diag(:))), 1e-9, n_pass, n_fail);

  % ---- P1: block weights + combined velocity -------------------------------
  tags = {'a1', 'a2', 'ainf'};
  alphas = [1.0, 2.0, Inf];
  for i = 1:3
    res = diversity_combine(z, P.FS, 'band', band, 'Nhat', s2, ...
                            'alpha', alphas(i), 'chans', chans);
    if i == 1
      [n_pass, n_fail] = chk('block size', ...
          abs(res.block - g.p1_block), 0.5, n_pass, n_fail);
    end
    w_g = g.(['p1_w_' tags{i}]);
    vc_g = g.(['p1_vc_' tags{i}]);
    dk_g = g.(['p1_dark_' tags{i}]);
    [n_pass, n_fail] = chk(sprintf('weights w (alpha=%s)', tags{i}), ...
        max(abs(res.w(:) - w_g(:))), 1e-9, n_pass, n_fail);
    [n_pass, n_fail] = chk(sprintf('dark blocks (alpha=%s)', tags{i}), ...
        max(abs(double(res.dark(:)) - dk_g(:))), 0.5, n_pass, n_fail);
    [n_pass, n_fail] = chk(sprintf('combined v (alpha=%s)', tags{i}), ...
        max(abs(res.v(:) - vc_g(:))) / max(abs(vc_g(:))), 1e-6, ...
        n_pass, n_fail);
  end

  fprintf('  -> qtec golden: %d PASS, %d FAIL\n', n_pass, n_fail);
  rc = double(n_fail > 0);
end


function [n_pass, n_fail] = chk(label, err, tol, n_pass, n_fail)
  ok = err <= tol;
  if ok
    n_pass = n_pass + 1;
    tag = 'PASS';
  else
    n_fail = n_fail + 1;
    tag = 'FAIL';
  end
  fprintf('  [%s] %-42s err=%.3e (tol %.1e)\n', tag, label, err, tol);
end
