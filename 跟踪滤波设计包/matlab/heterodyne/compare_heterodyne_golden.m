function rc = compare_heterodyne_golden(golden_file)
%COMPARE_HETERODYNE_GOLDEN Compare the MATLAB heterodyne port against Python golden data.
% Loads matlab/golden/heterodyne_golden.mat (written by
% export_heterodyne_qtec_golden.py), feeds the EXPORTED inputs through the
% ported functions and checks the outputs numerically.  Deterministic parts
% only -- randomness never crosses the language boundary.
% Returns rc = 0 iff every check passes.
  here = fileparts(mfilename('fullpath'));
  addpath(fullfile(here, '..', 'homodyne'));         % set_rng, hd_* helpers
  addpath(fullfile(here, '..', 'homodyne', 'core')); % canonical shared core
  addpath(here);
  if nargin < 1 || isempty(golden_file)
    golden_file = fullfile(here, '..', 'golden', 'heterodyne_golden.mat');
  end
  g = load(golden_file);
  P = het_params();
  n_pass = 0;
  n_fail = 0;

  fprintf('\n== compare_heterodyne_golden ==\n');

  % ---- design-parameter table -------------------------------------------
  T = g.mp_table;
  err = 0;
  for r = 1:size(T, 1)
    vr = T(r, 1);
    name = P.ORDER{T(r, 2)};
    m = het_mode_params(vr);
    m = m.(name);
    got = [m.fn, m.f_3db, m.B_loop, m.a_design, m.a_slip, m.valley_v, ...
           m.gain_db, m.noise_red_db, double(het_fn_discrete_ok(m.fn))];
    err = max(err, max(abs(got - T(r, 3:11)) ./ max(abs(T(r, 3:11)), 1e-300)));
  end
  [n_pass, n_fail] = chk('mode_params table (15 rows x 9 cols)', ...
                         err, 1e-12, n_pass, n_fail);

  [n_pass, n_fail] = chk('B_LOOP_COEF', ...
      relerr(P.B_LOOP_COEF, g.b_loop_coef), 1e-15, n_pass, n_fail);
  [n_pass, n_fail] = chk('F3DB_COEF', ...
      relerr(P.F3DB_COEF, g.f3db_coef), 1e-15, n_pass, n_fail);
  [n_pass, n_fail] = chk('v_if_limit', ...
      relerr(het_v_if_limit(), g.v_if), 1e-15, n_pass, n_fail);
  [n_pass, n_fail] = chk('v_alias_limit', ...
      relerr(het_v_alias_limit(), g.v_alias), 1e-15, n_pass, n_fail);

  % ---- select_mode demo cases --------------------------------------------
  S = g.selmode;
  bad = 0;
  for r = 1:size(S, 1)
    if isnan(S(r, 2))
      sel = het_select_mode(S(r, 1));
    else
      sel = het_select_mode(S(r, 1), S(r, 2));
    end
    idx = find(strcmp(P.ORDER, sel));
    bad = bad + double(idx ~= S(r, 3));
  end
  [n_pass, n_fail] = chk(sprintf('select_mode (%d cases)', size(S, 1)), ...
                         bad, 0.5, n_pass, n_fail);

  % ---- transfer-function grids -------------------------------------------
  f = g.tf_f(:);
  fn = g.tf_fn;
  [n_pass, n_fail] = chk('loop_error_mag grid', ...
      maxrel(het_loop_error_mag(f(2:end), fn), g.tf_lem), 1e-12, n_pass, n_fail);
  [n_pass, n_fail] = chk('loop_gain_mag grid', ...
      maxrel(het_loop_gain_mag(f(2:end), fn), g.tf_lgm), 1e-12, n_pass, n_fail);
  [n_pass, n_fail] = chk('v_pll_limit grid', ...
      maxrel(het_v_pll_limit(f(2:end), fn), g.tf_vpll), 1e-12, n_pass, n_fail);
  [n_pass, n_fail] = chk('tracking_error_rad grid', ...
      maxrel(het_tracking_error_rad(f(2:end), 0.1, fn), g.tf_terr), ...
      1e-12, n_pass, n_fail);
  [n_pass, n_fail] = chk('hl_response grid (complex)', ...
      maxrel(hl_response(f, P.FS, fn, P.ZETA), g.tf_hl), 1e-12, n_pass, n_fail);

  % ---- burst_signal --------------------------------------------------------
  tb = (0:numel(g.burst_x) - 1)' / P.FS;
  [xb, vb, eb] = burst_signal(tb, 50e3, 10e-3, 10, 5e-6);
  [n_pass, n_fail] = chk('burst_signal x', ...
      maxabs(xb - g.burst_x) / max(abs(g.burst_x)), 1e-12, n_pass, n_fail);
  [n_pass, n_fail] = chk('burst_signal v', ...
      maxabs(vb - g.burst_v) / max(abs(g.burst_v)), 1e-12, n_pass, n_fail);
  [n_pass, n_fail] = chk('burst_signal env', ...
      maxabs(eb - g.burst_env), 1e-12, n_pass, n_fail);

  % ---- PLL case A: burst + offset + noise (gate=always) --------------------
  [~, phiA, stA, dgA] = pll_carrier_regen(g.pllA_z, P.FS, g.pllA_fn, ...
      g.pllA_s2, struct('zeta', P.ZETA, 'gate', 'always'));
  eA = angle(exp(1i * (phiA - g.pllA_phi)));
  [n_pass, n_fail] = chk('pllA phi (wrapped max err, rad)', ...
                         maxabs(eA), 1e-8, n_pass, n_fail);
  [n_pass, n_fail] = chk('pllA state == LOCK everywhere', ...
                         maxabs(stA - 2), 0.5, n_pass, n_fail);
  dg_got = [dgA.near_pi_events, dgA.n_hold, dgA.n_acquire, ...
            dgA.n_lock_entries, dgA.lock_frac];
  [n_pass, n_fail] = chk('pllA diag counters', ...
                         maxabs(dg_got - g.pllA_diag'), 1e-9, n_pass, n_fail);

  % chain elements fed from the GOLDEN phi/vd (isolates each function)
  vd = fm_discriminator(exp(1i * g.pllA_phi), P.FS, P.LAMBDA);
  [n_pass, n_fail] = chk('fm_discriminator', ...
      maxabs(vd - g.pllA_vd) / max(abs(g.pllA_vd)), 1e-12, n_pass, n_fail);
  [n_pass, n_fail] = chk('fir_lp (257 taps)', ...
      maxabs(fir_lp(g.pllA_vd, 100e3, P.FS, 257) - g.pllA_fir) ...
      / max(abs(g.pllA_fir)), 1e-12, n_pass, n_fail);
  tA = (0:numel(g.pllA_z) - 1)' / P.FS;
  Pw = welch_psd(g.pllA_vd(tA > 0.4e-3), P.FS, 4096);
  [n_pass, n_fail] = chk('welch_psd', ...
      maxabs(Pw - g.pllA_psd) / max(abs(g.pllA_psd)), 1e-12, n_pass, n_fail);
  WmA = (tA > 0.15e-3) & (tA < 0.15e-3 + 10 / 50e3);
  [n_pass, n_fail] = chk('lockin_amp', ...
      relerr(lockin_amp(g.pllA_vd, tA, 50e3, WmA), g.pllA_lock), ...
      1e-12, n_pass, n_fail);
  ii = iir1_lowpass(abs(g.pllA_z) .^ 2, exp(-1.0 / (P.FS * 1e-6)));
  [n_pass, n_fail] = chk('iir1_lowpass', ...
      maxabs(ii - g.pllA_iir) / max(abs(g.pllA_iir)), 1e-12, n_pass, n_fail);

  % ---- PLL case B: near-boundary dynamics (near-pi events) -----------------
  [~, phiB, ~, dgB] = pll_carrier_regen(g.pllB_z, P.FS, g.pllB_fn, ...
      g.pllB_s2, struct('zeta', P.ZETA, 'gate', 'always'));
  eB = angle(exp(1i * (phiB - g.pllB_phi)));
  [n_pass, n_fail] = chk('pllB phi (wrapped max err, rad)', ...
                         maxabs(eB), 1e-8, n_pass, n_fail);
  [n_pass, n_fail] = chk('pllB near_pi_events', ...
      abs(dgB.near_pi_events - g.pllB_nearpi), 0.5, n_pass, n_fail);

  fprintf('  -> heterodyne golden: %d PASS, %d FAIL\n', n_pass, n_fail);
  rc = double(n_fail > 0);
end


function [n_pass, n_fail] = chk(label, err, tol, n_pass, n_fail)
  ok = err <= tol;
  if ok
    n_pass = n_pass + 1;
  else
    n_fail = n_fail + 1;
  end
  fprintf('  [%s] %-42s err=%.3e (tol %.1e)\n', ...
          merge_str(ok, 'PASS', 'FAIL'), label, err, tol);
end

function s = merge_str(cond, a, b)
  if cond
    s = a;
  else
    s = b;
  end
end

function e = maxabs(x)
  e = max(abs(x(:)));
  if isempty(e)
    e = 0;
  end
end

function e = maxrel(got, want)
  e = max(abs(got(:) - want(:)) ./ max(abs(want(:)), 1e-300));
end

function e = relerr(got, want)
  e = abs(got - want) / max(abs(want), 1e-300);
end
