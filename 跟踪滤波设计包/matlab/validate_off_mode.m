function validate_off_mode()
%VALIDATE_OFF_MODE OFF-mode product wrapper smoke regression (O1-O6b).
%   MATLAB/Octave port of homodyne_tracking_design/validate_off_mode.py.
%   OFF is NOT a fourth gear and NOT gate='always': it bypasses the whole
%   tracking chain (no PLL, no residual window), output = angle(z)/FM.
%   Same seeds and assertions as the Python reference.
%
%   Run:  cd matlab && octave --eval validate_off_mode
%   Saves golden metrics to golden/validate_off_mode_mat.mat and raises an
%   error (nonzero exit code) if any check fails.
  t_all = tic;
  sd = fileparts(mfilename('fullpath'));
  addpath(fullfile(sd, 'homodyne'));
  ensure_kernels();

  dp = design_params();
  c = vt_const();
  CHECKS = struct('cid', {}, 'label', {}, 'ok', {}, 'detail', {});

  fprintf('OFF 模式产品封装冒烟回归 (tracking_mode in {pll, off, fixed_lp})\n');
  fprintf(['  fs=%.0fMS/s; OFF = 跟踪旁路: 输出 angle(z)/FM 鉴频, ' ...
           '无 PLL 无残差窗; gate-off (gate_policy=always) 仍是 PLL 模式\n'], ...
          dp.FS / 1e6);

  sc = vt_make_scene(100e3);
  zc = vt_clean_z(sc);

  % ---- O1: routing / bypass identity -------------------------------------
  cfg_off = cfg_for_frequency(100e3, [], 'SLOW', true, 'off');
  [y, phi, st, dg] = tracking_filter(zc, dp.FS, cfg_off);
  ok1 = strcmp(cfg_off.tracking_mode, 'off') && isempty(cfg_off.band) ...
        && isempty(st) && strcmp(dg.mode, 'off') ...
        && isequal(phi, angle(zc(:))) ...
        && np_allclose(abs(y), ones(size(y)), 1e-5, 1e-12);
  CHECKS(end+1) = vt_check('O1', ['cfg(tracking_mode=''off'') 路由到旁路: ' ...
      'band=None, phi==angle(z), |y|=1, state=None'], ok1, ...
      sprintf('band=None, mode=%s', dg.mode));

  % ---- O2: bypass fidelity (near-noiseless) -------------------------------
  v_off = vt_vdisc(y);
  e = vt_amp_err_pct(v_off, sc);
  same = np_allclose(v_off, vt_vdisc(zc), 1e-5, 1e-6);
  CHECKS(end+1) = vt_check('O2', ...
      'OFF 旁路保真: FM 鉴频与 raw z 一致, 近无噪幅值误差 < 0.5 %', ...
      same && abs(e) < 0.5, ...
      sprintf('ampErr %+.3f%%, v_off==v_raw: %s', e, bool2str_(same)));

  % ---- O3: gate-off != OFF (weak light, SLOW @100 kHz) --------------------
  s2 = 10^(-3.0 / 10);                        % CNR = 3 dB
  cfg_gof = cfg_for_frequency(100e3, [], 'SLOW', true, 'pll', 'always');
  gains = [];
  off_is_raw = true;
  for s = 0:1
    rh = np_rng_new(50000 + s);
    z = exp(1i * sc.ph) + ...
        complex_bandlimited_noise(c.N, dp.FS, dp.B_FRONTEND, s2, rh);
    y_off = tracking_filter(z, dp.FS, cfg_off);
    off_is_raw = off_is_raw && np_allclose(vt_vdisc(y_off), vt_vdisc(z), ...
                                           1e-5, 1e-6);
    y_pll = tracking_filter(z, dp.FS, cfg_gof, s2);
    gains(end+1) = 20 * log10(vt_asd_at(vt_vdisc(y_off), sc) ...
                              / vt_asd_at(vt_vdisc(y_pll), sc));
  end
  g = median(gains);
  ok3 = g > 10.0 && off_is_raw && strcmp(cfg_gof.tracking_mode, 'pll') ...
        && strcmp(cfg_gof.gate, 'always');
  CHECKS(end+1) = vt_check('O3', ['gate-off != OFF: gate_policy=''always'' ' ...
      '仍在跟踪 (弱光 ASD 改善 > 10 dB), OFF 恒 0 dB (输出==输入)'], ok3, ...
      sprintf(['PLL(SLOW, gate=always) vs OFF: %+.1f dB @100kHz CNR=3dB ' ...
               '(2 seeds); OFF==raw: %s'], g, bool2str_(off_is_raw)));

  % ---- O4: pll path of tracking_filter == residual_mode -------------------
  rh = np_rng_new(50000);
  z = exp(1i * sc.ph) + ...
      complex_bandlimited_noise(c.N, dp.FS, dp.B_FRONTEND, s2, rh);
  ok4 = true;
  gates = {'auto', 'always'};
  for ig = 1:2
    gate = gates{ig};
    cfg = cfg_for_frequency(100e3, [], 'SLOW', true, 'pll', gate);
    [ya, pa, sa] = tracking_filter(z, dp.FS, cfg, s2);
    ropts = gate_params('SLOW');
    ropts.zeta = dp.ZETA;
    ropts.gate = gate;
    [yb, pb, sb] = residual_mode(z, dp.FS, dp.BANDS.SLOW.fn, s2, ...
                                 dp.B_WIN, ropts);
    ok4 = ok4 && isequal(ya, yb) && isequal(pa, pb) && isequal(sa, sb);
  end
  CHECKS(end+1) = vt_check('O4', ['PLL 路径一致: tracking_filter == ' ...
      'residual_mode 逐样本 (gate auto/always)'], ok4, ...
      'y/phi/state 全部 array_equal');

  % ---- O5: parameter guards ------------------------------------------------
  ok5 = raises_(@() cfg_for_frequency(1e5, [], 'SLOW', true, 'bogus')) ...
        && raises_(@() cfg_for_frequency(1e5, [], 'SLOW', true, 'pll', 'off')) ...
        && raises_(@() tracking_filter(zc, dp.FS, cfg_for_frequency(1e5)));
  CHECKS(end+1) = vt_check('O5', ['参数守卫: 非法 tracking_mode / ' ...
      'gate_policy=off 误用 / pll 缺 Nhat 均 ValueError'], ok5, '3/3 raised');

  % ---- O6: fixed_lp = fixed common window, no PLL --------------------------
  cfg_lp = cfg_for_frequency(100e3, [], 'SLOW', true, 'fixed_lp');
  [y_lp, phi_lp, st_lp, dg_lp] = tracking_filter(zc, dp.FS, cfg_lp);
  ref = fir_lp_same(zc, dp.B_WIN, dp.FS, dp.NT_WIN);
  ok6a = strcmp(cfg_lp.tracking_mode, 'fixed_lp') && isempty(cfg_lp.band) ...
         && cfg_lp.B_win == dp.B_WIN && cfg_lp.NT_win == dp.NT_WIN ...
         && isempty(st_lp) && strcmp(dg_lp.mode, 'fixed_lp') ...
         && isequal(y_lp, ref) && isequal(phi_lp, angle(ref));
  CHECKS(end+1) = vt_check('O6a', ['cfg(tracking_mode=''fixed_lp'') ' ...
      '路由到固定窗: band=None, y==fir_lp_same(z,B_WIN,FS,NT_WIN), ' ...
      'phi==angle(y), state=None'], ok6a, ...
      sprintf('band=None, mode=%s, B_win=%.0fMHz, NT_win=%d', ...
              dg_lp.mode, cfg_lp.B_win / 1e6, cfg_lp.NT_win));

  rh = np_rng_new(50002);
  zn = exp(1i * sc.ph) + ...
       complex_bandlimited_noise(c.N, dp.FS, dp.B_FRONTEND, s2, rh);
  y_lpn = tracking_filter(zn, dp.FS, cfg_lp);
  y_offn = tracking_filter(zn, dp.FS, cfg_off);
  differs = ~np_allclose(vt_vdisc(y_lpn), vt_vdisc(y_offn), 1e-5, 1e-6);
  g_lp = 20 * log10(vt_asd_at(vt_vdisc(y_offn), sc) ...
                    / vt_asd_at(vt_vdisc(y_lpn), sc));
  CHECKS(end+1) = vt_check('O6b', ['fixed_lp != OFF: 弱光下鉴频输出不同, ' ...
      '固定窗 ASD 优于 OFF (去掉窗外噪声/点击, 但仍无 PLL 门限扩展)'], ...
      differs && g_lp > 0.0, ...
      sprintf('differs: %s, fixed_lp vs OFF: %+.1f dB @100kHz CNR=3dB', ...
              bool2str_(differs), g_lp));

  allok = all([CHECKS.ok]);
  fprintf('\n');
  if allok, msg = 'ALL CHECKS PASSED'; else, msg = 'SOME CHECKS FAILED'; end
  fprintf('%s  (%d/%d)\n', msg, sum([CHECKS.ok]), numel(CHECKS));
  fprintf('[elapsed %.1f s]\n', toc(t_all));

  % ------------------------------------------------- golden metrics (.mat)
  gl = struct();
  gl.checks_ok = double([CHECKS.ok]);
  gl.checks_pass = sum(gl.checks_ok);
  gl.checks_total = numel(gl.checks_ok);
  gl.noisy = struct('o2_amp_err', e, 'o3_gain_med', g, 'o6b_gain', g_lp);
  gdir = fullfile(sd, 'golden');
  if ~exist(gdir, 'dir'), mkdir(gdir); end
  gfile = fullfile(gdir, 'validate_off_mode_mat.mat');
  save('-v7', gfile, '-struct', 'gl');
  fprintf('[golden metrics saved to %s]\n', gfile);

  if ~allok
    error('validate_off_mode: SOME CHECKS FAILED');
  end
end


function s = bool2str_(b)
  if b, s = 'True'; else, s = 'False'; end
end

function ok = raises_(fn)
%RAISES_ True iff fn() throws the homodyne ValueError-equivalent.
  ok = false;
  try
    fn();
  catch err
    ok = strcmp(err.identifier, 'homodyne:ValueError');
  end
end
