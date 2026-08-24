function validate_app_30ms_100khz()
%VALIDATE_APP_30MS_100KHZ App-scenario validation: v_peak<=30 m/s, f<=100 kHz.
%   MATLAB/Octave port of homodyne_tracking_design/validate_app_30ms_100khz.py
%   with the same scenarios, seeds and PASS/FAIL criteria:
%     A1  analytical gear-selection sweep (S1, S2)
%     A2  end-to-end weak-light simulation of 4 cases (E1-E5, G1)
%     A3  hysteresis step-change traces (H1-H3)
%     A6  front-end consistency study (F1-F3)
%     A7  deep-fade re-acquisition (D1-D3)
%     A8  noisy near-pi / cycle-slip statistics (N1, N2)
%     A4  conclusions,  A5  assertion summary
%   Noise realizations are IDENTICAL to Python (numpy-exact RNG kernel).
%
%   Run:  cd matlab && octave --eval validate_app_30ms_100khz
%   Saves golden metrics to golden/validate_app_30ms_100khz_mat.mat and
%   raises an error (nonzero exit code) if any check fails.
  t_all = tic;
  sd = fileparts(mfilename('fullpath'));
  addpath(fullfile(sd, 'homodyne'));
  ensure_kernels();

  dp = design_params();
  k = kconst_();

  fprintf(['用户应用场景验证: v_peak<=30 m/s (正弦), 典型 f<=100 kHz -- ' ...
           '现有三档选档是否影响性能?\n']);
  bl = '';
  for ib = 1:3
    bl = [bl, sprintf('%.2fM', b_loop(dp.BANDS.(dp.ORDER{ib}).fn) / 1e6)];
    if ib < 3, bl = [bl, '/']; end
  end
  fprintf(['reference: design_params 三档 (fn=110k/530k/1.6M, zeta=1.2, ' ...
           '公共窗 B_win=%.0fMHz, 守卫 %.1f rad), B_loop=%s\n'], ...
          dp.B_WIN / 1e6, dp.PHI_GUARD, bl);

  [bounds, ck1, det1] = A1_();
  [e2e, ck2] = A2_();
  ck3 = A3_();
  [a6, ck6] = A6_();
  [a7, ck7] = A7_();
  [a8, ck8] = A8_();
  A4_(bounds, e2e);
  CHECKS = [ck1, ck2, ck3, ck6, ck7, ck8];

  vt_print_header('A5  ASSERTION SUMMARY (主场景 PASS/FAIL 判据见文件头 docstring)');
  allok = true;
  for i = 1:numel(CHECKS)
    allok = allok && CHECKS(i).ok;
    if CHECKS(i).ok, tag = 'PASS'; else, tag = 'FAIL'; end
    fprintf('  [%s] %s  %s  (%s)\n', tag, CHECKS(i).cid, CHECKS(i).label, ...
            CHECKS(i).detail);
  end
  if allok, msg = 'ALL CHECKS PASSED'; else, msg = 'SOME CHECKS FAILED'; end
  fprintf('\n%s\n', msg);
  fprintf('[elapsed %.1f s]\n', toc(t_all));

  % ------------------------------------------------- golden metrics (.mat)
  g = struct();
  g.checks_ok = double([CHECKS.ok]);
  g.checks_pass = sum(g.checks_ok);
  g.checks_total = numel(g.checks_ok);
  g.det = struct('a1_pe', det1.pe, 'a1_sel', det1.sel, 'a1_vgl', det1.vgl, ...
                 'a1_bounds', [bounds.f_slow, bounds.f_med, ...
                               bounds.f_fast1, bounds.f_fastpi], ...
                 'a1_s1_worst', det1.s1_worst, ...
                 'a2_sel', e2e.sel_idx, 'a2_pe', e2e.pe);
  nz = struct();
  nz.a2_err_full = e2e.err_full;
  nz.a2_err_nco = e2e.err_nco;
  nz.a2_slips_clean = e2e.slips_clean;
  nz.a2_err_noisy_med = e2e.err_noisy_med;
  nz.a2_gain_full_med = e2e.gain_full_med;
  nz.a2_gain_nco_med = e2e.gain_nco_med;
  nz.a2_lock_mean = e2e.lock_mean;
  nz.a2_np_med = e2e.np_med;
  nz.a2_slips_noisy_max = e2e.slips_noisy_max;
  nz.a6_err_clean = a6.err_clean;
  nz.a6_err_med = a6.err_med;
  nz.a6_lock = a6.lock;
  nz.a6_np_med = a6.np_med;
  nz.a7_rel_med = a7.rel_med;
  nz.a7_ratio = a7.ratio;
  nz.a7_gap_med = a7.gap_med;
  nz.a7_inv_med = a7.inv_med;
  nz.a8_clean = [a8.np_clean, a8.sl_clean];
  nz.a8_np_pct = a8.np_pct;
  nz.a8_sl_pct = a8.sl_pct;
  nz.a8_err_pct = a8.err_pct;
  g.noisy = nz;
  gdir = fullfile(sd, 'golden');
  if ~exist(gdir, 'dir'), mkdir(gdir); end
  gfile = fullfile(gdir, 'validate_app_30ms_100khz_mat.mat');
  save('-v7', gfile, '-struct', 'g');
  fprintf('[golden metrics saved to %s]\n', gfile);

  if ~allok
    error('validate_app_30ms_100khz: SOME CHECKS FAILED');
  end
end


% ------------------------------------------------------------- constants
function k = kconst_()
  k.CNR_DB = 3.0;
  k.NSEED = 6;
  k.V_MAX_APP = 30.0;
  k.F_TYP_APP = 100e3;
  k.PRIMARY_F = [1e3, 5e3, 10e3, 20e3, 50e3, 100e3];
  k.CONTEXT_F = [200e3, 1e6, 3e6];
  k.VGRID = [0.02, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0];
  k.FE_NT = 1025;
  k.B_FE_A7 = 86e6;
  k.FADE_DB = -30.0;
  k.NSEED_FADE = 4;
  k.NSEED_STATS = 50;
  k.TINY = 1e-300;
  k.CASES = struct('tag', {'a', 'b', 'c', 'd'}, ...
                   'f0', {100e3, 10e3, 100e3, 50e3}, ...
                   'vamp', {0.02, 30.0, 30.0, 5.0}, ...
                   'note', {'典型工况 (VAMP 默认 20 mm/s)', '低频 x 最高速', ...
                            '最高典型频率 x 最高速 (守卫最坏点)', '中间工况'});
end


% ----------------------------------------------------------- sim helpers
function sc = make_scene_(f0, vamp)
%Per-frequency record length (a 10 kHz burst does not fit the 0.5 ms record).
  dp = design_params();
  switch f0
    case 10e3
      p = struct('T', 2.0e-3, 'ncyc', 5, 't0', 0.05e-3, 'L', 65536, 'band', 4e3);
    case 50e3
      p = struct('T', 0.5e-3, 'ncyc', 10, 't0', 0.02e-3, 'L', 16384, 'band', 15e3);
    case 100e3
      p = struct('T', 0.5e-3, 'ncyc', 20, 't0', 0.02e-3, 'L', 8192, 'band', 60e3);
    otherwise
      error('no APP_SCENES entry for f0=%g', f0);
  end
  N = fix(p.T * dp.FS);
  t = (0:N-1)' / dp.FS;
  [x, v, ~] = burst_signal(t, f0, vamp, p.ncyc, p.t0);
  Tb = p.ncyc / f0;
  Wm = (t > p.t0) & (t < p.t0 + Tb);
  Wq = (t > p.t0 + Tb + 0.04e-3) & (t < p.T - 0.02e-3);
  sc = struct('f0', f0, 'vamp', vamp, 'N', N, 't', t, 'v', v, ...
              'ph', 4 * pi / dp.LAMBDA * x, 'Wm', Wm, 'Wq', Wq, ...
              'L', p.L, 'band', p.band);
end

function e = amp_err_pct_(v_est, sc)
  a = lockin_amp(v_est, sc.t, sc.f0, sc.Wm);
  a0 = lockin_amp(sc.v, sc.t, sc.f0, sc.Wm);
  e = 100 * (a / a0 - 1);
end

function v = vdisc_(y)
  dp = design_params();
  v = fm_discriminator(y, dp.FS, dp.LAMBDA);
end

function n = slips_vs_true_(y, ph_true)
%True cycle slips: 2pi jumps of unwrap(angle(y)) - ph_true (V3 metric).
  ph = np_unwrap(angle(y(:)));
  n = sum(abs(diff(ph - ph_true(:))) > pi);
end

function v = pctile_(a, p)
%Empirical percentile with ceil indexing (same convention as vt_stats).
  s = sort(a(:));
  n = numel(s);
  v = s(max(1, min(n, ceil(p / 100 * n))));
end

function pe = phi_errs_(f0, vamp)
  dp = design_params();
  pe = zeros(1, 3);
  for ib = 1:3
    pe(ib) = tracking_error_rad(f0, vamp, dp.BANDS.(dp.ORDER{ib}).fn);
  end
end

function v = v_guard_limit_(f, band, target)
%v_peak at which the gear's untracked phase reaches `target` rad.
  dp = design_params();
  if nargin < 3, target = dp.PHI_GUARD; end
  v = target * dp.LAMBDA * f / (2 * loop_error_mag(f, dp.BANDS.(band).fn));
end

function fm = f_cross_(band, v, target, flo, fhi)
%Frequency where phi_err(f) crosses `target` rad at fixed v (bisection).
  dp = design_params();
  fn = dp.BANDS.(band).fn;
  g = @(f) tracking_error_rad(f, v, fn) - target;
  if g(flo) > 0 || g(fhi) < 0
    fm = NaN;
    return
  end
  for it = 1:200
    fm = 0.5 * (flo + fhi);
    if g(fm) > 0
      fhi = fm;
    else
      flo = fm;
    end
  end
  fm = 0.5 * (flo + fhi);
end

function s = pybool_(x)
  if x, s = 'True'; else, s = 'False'; end
end

function s = padr_(s, w)
%Left-justify to `w` CODE POINTS (Python str padding counts characters).
  n = sum(bitand(double(s), 192) ~= 128);
  if n < w, s = [s, repmat(' ', 1, w - n)]; end
end


% ================================================================== A1 sweep
function [bounds, ck, det] = A1_()
  dp = design_params();
  k = kconst_();
  vt_print_header(sprintf(['A1  选档扫描 (解析 + cfg_for_frequency): 守卫 ' ...
      'phi_err = |1-H_L|*2*v_peak/(lambda*f) <= %.1f rad'], dp.PHI_GUARD));
  s1_ok = true;
  s2_ok = true;
  s1_worst = [0.0, NaN, NaN];
  nf = numel(k.PRIMARY_F);
  nv = numel(k.VGRID);
  det = struct();
  det.pe = zeros(nf, nv, 3);
  det.sel = zeros(nf, nv);

  fprintf('\n  -- 主工况长表 (f <= %.0f kHz, 用户应用域) --\n', k.F_TYP_APP / 1e3);
  fprintf('          f    v_peak | phi_err SLOW     MEDIUM       FAST |  select  hyst(S起步)     cfg  guard\n');
  for i_f = 1:nf
    f0 = k.PRIMARY_F(i_f);
    for iv = 1:nv
      v = k.VGRID(iv);
      pe = phi_errs_(f0, v);
      sel = select_band(f0, v);
      hys = select_band_hysteresis(f0, 'SLOW', v);
      cfg = cfg_for_frequency(f0, v, 'SLOW');
      isel = find(strcmp(dp.ORDER, sel), 1);
      if pe(isel) <= dp.PHI_GUARD
        note = 'ok';
      else
        note = 'FALLBACK(无档<=1rad)';
      end
      s2_ok = s2_ok && strcmp(hys, sel) && strcmp(sel, cfg.band);
      if pe(isel) > s1_worst(1), s1_worst = [pe(isel), f0, v]; end
      s1_ok = s1_ok && pe(isel) < pi;
      det.pe(i_f, iv, :) = pe;
      det.sel(i_f, iv) = isel;
      fprintf('    %5.0fk %8.0fmm/s | %11.4gr %9.4gr %9.4gr | %7s %10s %7s  %s\n', ...
              f0 / 1e3, v * 1e3, pe(1), pe(2), pe(3), sel, hys, cfg.band, note);
    end
    fprintf('\n');
  end

  fprintf(['  -- 全景矩阵 (含仪器上限 200k/1M/3M 供参考): S/M/F=选中档, ' ...
           '''!''=守卫失败回退最宽档, ''#''=phi_err>pi 必滑周 --\n']);
  fs_all = [k.PRIMARY_F, k.CONTEXT_F];
  hdr = '    v_peak\f   ';
  for j = 1:numel(fs_all)
    f = fs_all(j);
    if f >= 1e6, lbl = sprintf('%.0fM', f / 1e6); else, lbl = sprintf('%.0fk', f / 1e3); end
    hdr = [hdr, sprintf('%7s', lbl)];
  end
  fprintf('%s\n', hdr);
  for iv = 1:nv
    v = k.VGRID(iv);
    row = sprintf('    %8.0fmm/s', v * 1e3);
    for j = 1:numel(fs_all)
      f0 = fs_all(j);
      sel = select_band(f0, v);
      pe = phi_errs_(f0, v);
      pesel = pe(find(strcmp(dp.ORDER, sel), 1));
      if pesel <= dp.PHI_GUARD
        mark = '';
      elseif pesel < pi
        mark = '!';
      else
        mark = '#';
      end
      row = [row, sprintf('%7s', [sel(1), mark])];
    end
    fprintf('%s\n', row);
  end

  fprintf('\n  -- 守卫升档边界 (v_peak 上限, 由 phi_err=1rad / pi 解析求出) --\n');
  fprintf('          f |    SLOW可用<=    MEDIUM可用<=     FAST守卫<=      FAST滑周极限\n');
  det.vgl = zeros(nf, 4);
  for i_f = 1:nf
    f0 = k.PRIMARY_F(i_f);
    det.vgl(i_f, :) = [v_guard_limit_(f0, 'SLOW'), v_guard_limit_(f0, 'MEDIUM'), ...
                       v_guard_limit_(f0, 'FAST'), v_guard_limit_(f0, 'FAST', pi)];
    fprintf('    %5.0fk | %9.3fm/s %11.3fm/s %10.2fm/s %11.1fm/s\n', ...
            f0 / 1e3, det.vgl(i_f, 1), det.vgl(i_f, 2), det.vgl(i_f, 3), ...
            det.vgl(i_f, 4));
  end

  f_med = f_cross_('MEDIUM', k.V_MAX_APP, dp.PHI_GUARD, 100.0, 150e3);
  f_slow = f_cross_('SLOW', k.V_MAX_APP, dp.PHI_GUARD, 10.0, 5e3);
  f_fast1 = f_cross_('FAST', k.V_MAX_APP, dp.PHI_GUARD, 1e3, 300e3);
  f_fastpi = f_cross_('FAST', k.V_MAX_APP, pi, 1e3, 400e3);
  fprintf(['\n  30 m/s 时的频率边界: SLOW 通过守卫至 %.0f Hz; ' ...
           'MEDIUM 至 %.2f kHz (其上必须 FAST);\n'], f_slow, f_med / 1e3);
  fprintf(['  FAST 守卫(1 rad)内至 %.1f kHz, 其上 fallback FAST ' ...
           '(phi_err 1..pi 区间, 仍可跟踪); 滑周极限 phi_err=pi 在 %.1f kHz.\n'], ...
          f_fast1 / 1e3, f_fastpi / 1e3);
  fprintf(['  用户最坏点 (100 kHz, 30 m/s): phi_err FAST = %.2f rad < pi ' ...
           '(滑周速度余量 %.1fx).\n'], ...
          tracking_error_rad(100e3, 30, dp.BANDS.FAST.fn), ...
          v_guard_limit_(100e3, 'FAST', pi) / 30);

  ck = struct('cid', {}, 'label', {}, 'ok', {}, 'detail', {});
  ck(end+1) = vt_check('S1', sprintf(['主网格 (f<=%.0fkHz, v<=%.0fm/s) ' ...
      '自动选档 phi_err < pi (无强制滑周)'], k.F_TYP_APP / 1e3, k.V_MAX_APP), ...
      s1_ok, sprintf('最大 %.2f rad @ (%.0fkHz, %.0fm/s)', s1_worst(1), ...
                     s1_worst(2) / 1e3, s1_worst(3)));
  ck(end+1) = vt_check('S2', ['主网格: hysteresis(SLOW起步) == select_band ' ...
      '== cfg_for_frequency (升档即时生效)'], s2_ok, ...
      sprintf('%d 组合', nf * nv));
  det.s1_worst = s1_worst(1);
  bounds = struct('f_med', f_med, 'f_slow', f_slow, 'f_fast1', f_fast1, ...
                  'f_fastpi', f_fastpi);
end


% ==================================================================== A2 sim
function r = run_case_(cs)
  dp = design_params();
  k = kconst_();
  f0 = cs.f0;
  vamp = cs.vamp;
  sc = make_scene_(f0, vamp);
  s2 = 10^(-k.CNR_DB / 10);
  sel = select_band(f0, vamp);
  isel = find(strcmp(dp.ORDER, sel), 1);
  pe = phi_errs_(f0, vamp);
  rh = np_rng_new(777);
  zc = exp(1i * sc.ph) + complex_bandlimited_noise(sc.N, dp.FS, 20e6, 1e-10, rh);
  row = struct();
  for ib = 1:3
    band = dp.ORDER{ib};
    [yf, yn, ~, ~, dg] = vt_gear_filter(zc, band, 1e-10, 'always');
    ef = amp_err_pct_(vdisc_(yf), sc);
    en = amp_err_pct_(vdisc_(yn), sc);
    row.(band) = struct('err_full', ef, 'err_nco', en, ...
        'slips', dg.near_pi_events, ...
        'g_full', 20 * log10(max(1 + ef / 100, 1e-12)), ...
        'g_nco', 20 * log10(max(1 + en / 100, 1e-12)), ...
        'errs_noisy', [], 'gains_full', [], 'gains_nco', [], 'lock', [], ...
        'nps_noisy', [], 'slips_noisy', []);
  end
  for s = 0:k.NSEED-1
    rh = np_rng_new(50000 + fix(f0 / 1e3) * 1000 + fix(vamp * 10) * 37 + s);
    z = exp(1i * sc.ph) + ...
        complex_bandlimited_noise(sc.N, dp.FS, dp.B_FRONTEND, s2, rh);
    a_off = vt_asd_at(vdisc_(z), sc);
    for ib = 1:3
      band = dp.ORDER{ib};
      [yf, yn, ~, ~, dg] = vt_gear_filter(z, band, s2, 'auto');
      vf = vdisc_(yf);
      row.(band).errs_noisy(end+1) = amp_err_pct_(vf, sc);
      row.(band).gains_full(end+1) = row.(band).g_full ...
          + 20 * log10(a_off / vt_asd_at(vf, sc));
      row.(band).gains_nco(end+1) = row.(band).g_nco ...
          + 20 * log10(a_off / vt_asd_at(vdisc_(yn), sc));
      row.(band).lock(end+1) = dg.lock_frac;
      row.(band).nps_noisy(end+1) = dg.near_pi_events;
      if strcmp(band, sel)
        row.(band).slips_noisy(end+1) = slips_vs_true_(yf, sc.ph);
      end
    end
  end

  fD = 2 * vamp / dp.LAMBDA;
  fprintf('\n  案例 %s)  f0=%.0f kHz, v_peak=%g m/s (fD_peak=%.2f MHz) -- %s\n', ...
          cs.tag, f0 / 1e3, vamp, fD / 1e6, cs.note);
  if pe(isel) <= dp.PHI_GUARD, fb = ''; else, fb = ' [守卫fallback: 无档<=1rad]'; end
  fprintf('      select_band=%s%s, hysteresis(SLOW起步)=%s\n', sel, fb, ...
          select_band_hysteresis(f0, 'SLOW', vamp));
  fprintf(['    gear       phi_err | ampErr full  ampErr NCO  slips | ' ...
           'ampErr noisy   np噪中值 |          SNRgain full dB |  NCO dB | lock%%\n']);
  for ib = 1:3
    band = dp.ORDER{ib};
    rb = row.(band);
    [m, lo, hi] = vt_stats(rb.gains_full);
    mn = vt_stats(rb.gains_nco);
    em = vt_stats(rb.errs_noisy);
    if strcmp(band, sel), mark = '  <== auto'; else, mark = ''; end
    fprintf(['    %-8s %8.3gr | %+10.2f%% %+10.2f%% %6.0f | %+11.2f%% ' ...
             '%7.0f | %+7.2f [%+7.2f,%+7.2f] | %+6.2f | %5.1f%s\n'], ...
            band, pe(ib), rb.err_full, rb.err_nco, rb.slips, em, ...
            median(rb.nps_noisy), m, lo, hi, mn, 100 * mean(rb.lock), mark);
  end
  r = struct('row', row, 'sel', sel, 'isel', isel, 'pe', pe);
end


function [e2e, ck] = A2_()
  dp = design_params();
  k = kconst_();
  vt_print_header(sprintf(['A2  端到端弱光仿真 (CNR=%.0fdB, B_frontend=' ...
      '%.0fMHz, %d seeds, gear_filter/R1-R3 方法同 validate_tracking)'], ...
      k.CNR_DB, dp.B_FRONTEND / 1e6, k.NSEED));
  fprintf(['  ampErr = R1 近无噪传递函数误差 (clean, gate=always); ' ...
           'ampErr noisy = 含噪中值 (gate=auto);\n']);
  fprintf(['  SNRgain = 信号增益 + 20log10(ASD_off/ASD_on) @f0 静默窗 (R2/R3); ' ...
           'slips = clean 运行 near-pi 事件数.\n']);
  res = struct();
  for ic = 1:4
    res.(k.CASES(ic).tag) = run_case_(k.CASES(ic));
  end

  fprintf('\n');
  ck = struct('cid', {}, 'label', {}, 'ok', {}, 'detail', {});
  ra = res.a;
  ok = strcmp(ra.sel, 'SLOW') ...
       && abs(ra.row.SLOW.err_full) < 5.0 ...
       && abs(vt_stats(ra.row.SLOW.errs_noisy)) < 10.0 ...
       && vt_stats(ra.row.SLOW.gains_full) > 10.0;
  ck(end+1) = vt_check('E1', ['案例a (100kHz, 20mm/s): 自动档=SLOW, ' ...
      'clean|err|<5%, 噪声中值|err|<10%, SNRgain>+10dB'], ok, ...
      sprintf('sel=%s, err=%+.2f%%, noisy=%+.2f%%, gain=%+.2fdB', ...
              ra.sel, ra.row.SLOW.err_full, vt_stats(ra.row.SLOW.errs_noisy), ...
              vt_stats(ra.row.SLOW.gains_full)));
  tags = {'b', 'c', 'd'};
  cids = {'E2', 'E3', 'E4'};
  extras = [false, true, false];
  for it = 1:3
    tag = tags{it};
    r = res.(tag);
    cs = k.CASES(find(strcmp({k.CASES.tag}, tag), 1));
    gg = r.row.(r.sel);
    ok = abs(gg.err_full) < 5.0 ...
         && abs(vt_stats(gg.errs_noisy)) < 10.0 ...
         && vt_stats(gg.gains_full) > 0.0;
    lbl = sprintf(['案例%s (%.0fkHz, %gm/s): 自动档 clean|err|<5%%, ' ...
                   '噪声中值|err|<10%%, SNRgain>0dB'], tag, cs.f0 / 1e3, cs.vamp);
    detail = sprintf(['sel=%s, err=%+.2f%%, noisy=%+.2f%%, gain=%+.2fdB, ' ...
                      'slips=%.0f, noisy slips max=%.0f'], r.sel, ...
                     gg.err_full, vt_stats(gg.errs_noisy), ...
                     vt_stats(gg.gains_full), gg.slips, max(gg.slips_noisy));
    if extras(it)
      cfgc = cfg_for_frequency(cs.f0, cs.vamp, 'SLOW');
      ok = ok && strcmp(r.sel, 'FAST') && gg.slips == 0 ...
           && ~cfgc.guard_ok && cfgc.overrange;
      lbl = [lbl, ', 档=FAST 且 clean 0 滑周, cfg guard_ok=False/' ...
             'overrange=True (审计项2, 选项A: 保持 fn=1.6M 并上报降级区)'];
      detail = [detail, sprintf([', guard_ok=%s, overrange=%s, ' ...
                'cfg phi_err=%.3fr (噪声滑周界限见 A8/N2)'], ...
                pybool_(cfgc.guard_ok), pybool_(cfgc.overrange), cfgc.phi_err)];
    end
    ck(end+1) = vt_check(cids{it}, lbl, ok, detail);
  end
  em = res.c.row.MEDIUM.err_full;
  ck(end+1) = vt_check('E5', ['守卫必要性: 案例c 强制 MEDIUM (违守卫 12.9rad) ' ...
      'clean|err|>20% (守卫升档不是保守而是必须)'], abs(em) > 20.0, ...
      sprintf('%+.1f%%', em));
  g1ok = true;
  g1det = '';
  for ic = 1:4
    cs = k.CASES(ic);
    if strcmp(cs.tag, 'c'), continue; end
    cfg = cfg_for_frequency(cs.f0, cs.vamp, 'SLOW');
    pe_ref = tracking_error_rad(cs.f0, cs.vamp, dp.BANDS.(cfg.band).fn);
    g1ok = g1ok && cfg.guard_ok && ~cfg.overrange ...
           && abs(cfg.phi_err - pe_ref) < 1e-12;
    if ~isempty(g1det), g1det = [g1det, '; ']; end
    g1det = [g1det, sprintf('%s:%s %.3gr', cs.tag, cfg.band, cfg.phi_err)];
  end
  ck(end+1) = vt_check('G1', ['守卫标志 API: 案例a/b/d cfg guard_ok=True/' ...
      'overrange=False, phi_err 与解析一致 (审计项2)'], g1ok, g1det);

  % pack metrics (cases x bands)
  e2e = res;
  e2e.sel_idx = zeros(1, 4);
  e2e.pe = zeros(4, 3);
  e2e.err_full = zeros(4, 3);
  e2e.err_nco = zeros(4, 3);
  e2e.slips_clean = zeros(4, 3);
  e2e.err_noisy_med = zeros(4, 3);
  e2e.gain_full_med = zeros(4, 3);
  e2e.gain_nco_med = zeros(4, 3);
  e2e.lock_mean = zeros(4, 3);
  e2e.np_med = zeros(4, 3);
  e2e.slips_noisy_max = zeros(1, 4);
  for ic = 1:4
    r = res.(k.CASES(ic).tag);
    e2e.sel_idx(ic) = r.isel;
    e2e.pe(ic, :) = r.pe;
    for ib = 1:3
      rb = r.row.(dp.ORDER{ib});
      e2e.err_full(ic, ib) = rb.err_full;
      e2e.err_nco(ic, ib) = rb.err_nco;
      e2e.slips_clean(ic, ib) = rb.slips;
      e2e.err_noisy_med(ic, ib) = vt_stats(rb.errs_noisy);
      e2e.gain_full_med(ic, ib) = vt_stats(rb.gains_full);
      e2e.gain_nco_med(ic, ib) = vt_stats(rb.gains_nco);
      e2e.lock_mean(ic, ib) = mean(rb.lock);
      e2e.np_med(ic, ib) = median(rb.nps_noisy);
    end
    e2e.slips_noisy_max(ic) = max(r.row.(r.sel).slips_noisy);
  end
end


% ============================================================= A3 hysteresis
function hist = trace_(name, seq, start)
  dp = design_params();
  if nargin < 3, start = 'SLOW'; end
  fprintf('\n  %s (选档状态机, 起始档 %s)\n', name, start);
  fprintf('    update       f    v_peak |  target  applied phi_err(applied)  状态\n');
  band = start;
  n = size(seq, 1);
  hist = struct('band', {}, 'tgt', {}, 'pe', {});
  for i = 1:n
    f0 = seq(i, 1);
    v = seq(i, 2);
    tgt = select_band(f0, v);
    band = select_band_hysteresis(f0, band, v);
    pe = tracking_error_rad(f0, v, dp.BANDS.(band).fn);
    if strcmp(band, tgt)
      status = '最优';
    elseif pe <= dp.PHI_GUARD
      status = '安全, 暂时非最优 (降档过渡)';
    elseif pe < pi
      status = '可跟踪(<pi) 但超守卫';
    else
      status = '错档: 会滑周!';
    end
    fprintf('    %6d %5.0fk %8.0fmm/s | %7s %8s %15.4gr  %s\n', ...
            i - 1, f0 / 1e3, v * 1e3, tgt, band, pe, status);
    hist(end+1) = struct('band', band, 'tgt', tgt, 'pe', pe);
  end
end


function ck = A3_()
  dp = design_params();
  vt_print_header(['A3  换档迟滞: 用户相关的频率/速度阶跃 -- ' ...
                   '一次一档降档是否造成临时错档?']);
  h3 = trace_('T1: 频率阶跃 50 kHz -> 100 kHz @ 20 mm/s', ...
              [repmat([50e3, 0.02], 2, 1); repmat([100e3, 0.02], 3, 1)]);
  h1 = trace_('T2: 速度阶跃 20 mm/s -> 30 m/s @ 100 kHz (升档)', ...
              [repmat([100e3, 0.02], 2, 1); repmat([100e3, 30.0], 3, 1)]);
  h2 = trace_('T3: 速度阶跃 30 m/s -> 20 mm/s @ 100 kHz (降档, 一次一档)', ...
              [repmat([100e3, 30.0], 2, 1); repmat([100e3, 0.02], 4, 1)], 'FAST');
  fprintf(['\n  说明: 阶跃发生到下一次选档更新之间不可避免地短暂处于旧档 ' ...
           '(任何离散选档器皆然, 暴露窗=选档更新周期);\n']);
  fprintf(['  升档即时生效, 之后 reacq=True 用差分鉴频器直接拉入 NCO 频率. ' ...
           '降档只慢不错: 高档在任何更低速工况都满足守卫.\n']);

  ck = struct('cid', {}, 'label', {}, 'ok', {}, 'detail', {});
  ck(end+1) = vt_check('H1', 'T2 升档: 阶跃后第 1 次更新即到守卫档 (FAST)', ...
      strcmp(h1(3).band, h1(3).tgt) && strcmp(h1(3).band, 'FAST'), ...
      sprintf('update2: %s (target %s)', h1(3).band, h1(3).tgt));
  inter_safe = all(arrayfun(@(h) h.pe <= dp.PHI_GUARD, h2(3:end)));
  path2 = strjoin({h2(2:end).band}, '->');
  ck(end+1) = vt_check('H2', ['T3 降档: 中间档全部守卫安全 (无临时错档), ' ...
      '2 次更新内到最优档'], inter_safe && strcmp(h2(4).band, 'SLOW'), ...
      sprintf('路径 %s, max中间phi_err=%.3gr', path2, max([h2(3:end).pe])));
  ck(end+1) = vt_check('H3', 'T1: 50->100 kHz @20mm/s 全程 SLOW, 无档位抖动', ...
      all(strcmp({h3.band}, 'SLOW')), ...
      sprintf('路径 %s', strjoin({h3.band}, '->')));
end


% ========================================================== A6 front-end study
function r = a6_variant_(sc, B_fe, pw, lpf)
%One front-end variant at case c (FAST gear): clean + NSEED noisy runs.
  dp = design_params();
  k = kconst_();
  zc = exp(1i * sc.ph) + ...
       complex_bandlimited_noise(sc.N, dp.FS, 20e6, 1e-10, np_rng_new(777));
  if lpf
    zc = fir_lp_same(zc, B_fe / 2, dp.FS, k.FE_NT);
    lpf13 = 13;
  else
    lpf13 = 0;
  end
  yf = vt_gear_filter(zc, 'FAST', 1e-10, 'always');
  ec = amp_err_pct_(vdisc_(yf), sc);
  errs = [];
  locks = [];
  nps = [];
  for s = 0:k.NSEED-1
    rh = np_rng_new(60000 + fix(B_fe / 1e6) * 97 + fix(pw * 1000) * 3 + lpf13 + s);
    z = exp(1i * sc.ph) + complex_bandlimited_noise(sc.N, dp.FS, B_fe, pw, rh);
    if lpf
      z = fir_lp_same(z, B_fe / 2, dp.FS, k.FE_NT);
    end
    [yf, ~, ~, ~, dg] = vt_gear_filter(z, 'FAST', pw, 'auto');
    errs(end+1) = amp_err_pct_(vdisc_(yf), sc);
    locks(end+1) = dg.lock_frac;
    nps(end+1) = dg.near_pi_events;
  end
  r = struct('err_clean', ec, 'errs', errs, 'lock', mean(locks), 'nps', nps, ...
             'cnr_eff', -10 * log10(pw));
end


function [a6, ck] = A6_()
  dp = design_params();
  k = kconst_();
  fD = 2 * k.V_MAX_APP / dp.LAMBDA;
  vt_print_header(sprintf(['A6  前端模型一致性 (审计项1): 30 m/s 时 fD_peak=' ...
      '%.1f MHz > B_FRONTEND/2=%.0f MHz -- 参数化 B_frontend, ' ...
      '前端LPF作用于信号+噪声'], fD / 1e6, dp.B_FRONTEND / 2e6));
  fprintf(['  A2 现模型: 噪声限带 ±20 MHz, 信号不限带 -- 在 30 m/s 处信号大部分时间' ...
           '位于噪声带外, "CNR=3dB" 不代表真实前端.\n']);
  fprintf(['  变体: 前端LPF = 线性相位 FIR (截止 B/2, 1025 taps, 理想模型 -- 实际硬件' ...
           '须用实测 I/Q 频响与噪声谱替代);\n']);
  fprintf(['  噪声策略: 总CNR恒定 3dB (扩带时 PSD 下降) vs PSD恒定 (扩带时总噪声功率' ...
           '增大, 等效CNR<3dB).\n']);
  sc = make_scene_(100e3, k.V_MAX_APP);
  s2 = 10^(-k.CNR_DB / 10);
  vids = {'v0', 'v1', 'v2', 'v3', 'v4', 'v5'};
  Bs = [40e6, 40e6, 86e6, 100e6, 86e6, 100e6];
  pws = [s2, s2, s2, s2, s2 * 86 / 40, s2 * 100 / 40];
  lpfs = [false, true, true, true, true, true];
  labels = {'B40 噪声±20M 信号不限带 (A2 现模型, 对照)', ...
            'B40 + 前端LPF (真实 40 MHz 前端)', ...
            'B86 总CNR=3dB + LPF (物理一致, 推荐指标)', ...
            'B100 总CNR=3dB + LPF (物理一致)', ...
            'B86 PSD恒定 + LPF (同光功率, 前端更宽)', ...
            'B100 PSD恒定 + LPF'};
  fprintf('\n  案例c (100 kHz, 30 m/s), FAST 档, %d seeds:\n', k.NSEED);
  fprintf(['    id  变体                                      CNR_eff | ' ...
           ' clean err  noisy err 中值  lock%%  near_pi 中值\n']);
  res = struct();
  a6 = struct('err_clean', zeros(1, 6), 'err_med', zeros(1, 6), ...
              'lock', zeros(1, 6), 'np_med', zeros(1, 6));
  for j = 1:6
    r = a6_variant_(sc, Bs(j), pws(j), lpfs(j));
    res.(vids{j}) = r;
    a6.err_clean(j) = r.err_clean;
    a6.err_med(j) = median(r.errs);
    a6.lock(j) = r.lock;
    a6.np_med(j) = median(r.nps);
    fprintf('    %s %s %+7.1fdB | %+9.2f%% %+12.2f%% %6.1f %11.0f\n', ...
            padr_(vids{j}, 3), padr_(labels{j}, 38), r.cnr_eff, ...
            r.err_clean, median(r.errs), 100 * r.lock, median(r.nps));
  end
  fprintf(['\n  解读: v0 (现模型) 与 v2/v3 (物理一致, 总CNR=3dB) 的含噪误差同量级 --' ...
           ' A2 的结论在代表性前端模型下成立;\n']);
  fprintf(['  v1: 真实 40 MHz 前端把 30 m/s 信号削掉 (clean 已坏) -- 硬件前端必须' ...
           ' ≥ ±%.0f MHz;\n'], ceil(fD / 1e6) + 4);
  fprintf(['  v4/v5: 同光功率下扩带引入更多噪声, 等效 CNR 掉到 3dB 以下, 误差急剧' ...
           '恶化 -- CNR 指标必须在实际前端带宽上定义/实测.\n']);
  ck = struct('cid', {}, 'label', {}, 'ok', {}, 'detail', {});
  ok = abs(median(res.v2.errs)) < 10.0 && abs(median(res.v3.errs)) < 10.0;
  ck(end+1) = vt_check('F1', ['物理一致前端 (B=86/100MHz, 总CNR=3dB, LPF on): ' ...
      'FAST 含噪中值 |err| < 10% (案例c结论在代表性模型下成立)'], ok, ...
      sprintf('v2 %+.2f%%, v3 %+.2f%%', median(res.v2.errs), median(res.v3.errs)));
  ck(end+1) = vt_check('F2', ['真实 40 MHz 前端 (LPF 作用于信号) 无法通过 ' ...
      '30 m/s: clean |err| > 20% (前端须扩至 ≥ ±43 MHz)'], ...
      abs(res.v1.err_clean) > 20.0, ...
      sprintf('clean %+.2f%%, noisy 中值 %+.2f%%', res.v1.err_clean, ...
              median(res.v1.errs)));
  ok = res.v4.cnr_eff < k.CNR_DB - 0.2 && abs(median(res.v4.errs)) > 20.0 ...
       && res.v5.cnr_eff < k.CNR_DB - 0.2 && abs(median(res.v5.errs)) > 20.0;
  ck(end+1) = vt_check('F3', ['PSD恒定扩带: 等效CNR < 3dB 且含噪中值 ' ...
      '|err| > 20% (CNR 必须在实际前端带宽上定义/实测)'], ok, ...
      sprintf('v4 CNR%+.1fdB err%+.1f%%, v5 CNR%+.1fdB err%+.1f%%', ...
              res.v4.cnr_eff, median(res.v4.errs), res.v5.cnr_eff, ...
              median(res.v5.errs)));
end


% ====================================================== A7 fade re-acquisition
function r = a7_run_(dur, cnr_db, seed)
%One fade run at (100 kHz, 30 m/s), FAST gear, gate='auto'.
  dp = design_params();
  k = kconst_();
  f0 = 100e3;
  vpk = k.V_MAX_APP;
  T = 0.5e-3;
  N = fix(T * dp.FS);
  t = (0:N-1)' / dp.FS;
  x = vpk / (2 * pi * f0) * sin(2 * pi * f0 * t);
  v = vpk * cos(2 * pi * f0 * t);
  ph = 4 * pi / dp.LAMBDA * x;
  t_f = 0.15e-3;
  s2 = 10^(-cnr_db / 10);
  rh = np_rng_new(80000 + fix(dur * 1e6) * 91 + fix(cnr_db) * 7 + seed);
  env = ones(N, 1);
  env((t >= t_f) & (t < t_f + dur)) = 10^(k.FADE_DB / 20);
  z = env .* exp(1i * ph) + ...
      complex_bandlimited_noise(N, dp.FS, k.B_FE_A7, s2, rh);
  z = fir_lp_same(z, k.B_FE_A7 / 2, dp.FS, k.FE_NT);
  [yf, ~, ~, st] = vt_gear_filter(z, 'FAST', s2, 'auto');
  st = st(:);
  fw = (t >= t_f) & (t < t_f + dur);
  inv = mean(st(fw) ~= 2);
  after = find((t >= t_f + dur) & (st == 2));
  if isempty(after)
    rel = Inf;
  else
    rel = (t(after(1)) - (t_f + dur)) * 1e6;
  end
  ve = vdisc_(yf);
  Wpre = (t > 50e-6) & (t < t_f - 5e-6);
  if isfinite(rel)
    Wpost = t > (t_f + dur + rel * 1e-6 + 20e-6);
  else
    Wpost = false(N, 1);
  end
  rms_pre = sqrt(mean((ve(Wpre) - v(Wpre)).^2));
  if any(Wpost)
    rms_post = sqrt(mean((ve(Wpost) - v(Wpost)).^2));
    dphi = np_unwrap(angle(yf(:))) - ph;
    gap_cyc = abs(mean(dphi(Wpost)) - mean(dphi(Wpre))) / (2 * pi);
  else
    rms_post = Inf;
    gap_cyc = Inf;
  end
  r = struct('inv', inv, 'rel', rel, 'rms_pre', rms_pre, ...
             'rms_post', rms_post, 'gap_cyc', gap_cyc);
end


function [a7, ck] = A7_()
  k = kconst_();
  vt_print_header(sprintf(['A7  掉光重捕获 (审计项3): 30 m/s @ 100 kHz, ' ...
      '深衰落 %.0f dB, 时长 2/10/50 µs, CNR 12/6/3 dB (B_frontend=%.0fMHz ' ...
      '物理一致前端, %d seeds)'], k.FADE_DB, k.B_FE_A7 / 1e6, k.NSEED_FADE));
  fprintf(['  指标: invalid%% = 衰落窗内非 LOCK 样本占比 (产品 invalid 标志的可用性); ' ...
           'relock = 光恢复到重新 LOCK 的时间;\n']);
  fprintf(['  rms_pre/post = 衰落前/重锁后+20µs 的速度 RMS 误差; gap = 跨衰落相位' ...
           '滑移 (周). 衰落起点取速度峰值 (+38.7 MHz Doppler, 最坏).\n']);
  fprintf(['\n        时长   CNR |         invalid%%        relock µs ' ...
           'rms_pre m/s rms_post m/s post/pre   gap 周(中值)\n']);
  d1_ok = true;
  d2_ok = true;
  d3_ok = true;
  d1_worst = 0.0;
  d2_worst = 0.0;
  gap_lo = Inf;
  gap_hi = 0.0;
  inv_2us = [];
  durs = [2e-6, 10e-6, 50e-6];
  cnrs = [12, 6, 3];
  a7 = struct('rel_med', zeros(1, 9), 'ratio', zeros(1, 9), ...
              'gap_med', zeros(1, 9), 'inv_med', zeros(1, 9));
  ig = 0;
  for idur = 1:3
    dur = durs(idur);
    for icnr = 1:3
      cnr = cnrs(icnr);
      ig = ig + 1;
      rr = struct('inv', {}, 'rel', {}, 'rms_pre', {}, 'rms_post', {}, ...
                  'gap_cyc', {});
      for s = 0:k.NSEED_FADE-1
        rr(end+1) = a7_run_(dur, cnr, s);
      end
      inv = [rr.inv];
      rel = [rr.rel];
      ratio = median([rr.rms_post]) / median([rr.rms_pre]);
      gap = median([rr.gap_cyc]);
      gap_lo = min(gap_lo, gap);
      gap_hi = max(gap_hi, gap);
      si = '';
      sr = '';
      for j = 1:k.NSEED_FADE
        si = [si, sprintf('%3.0f', 100 * inv(j))];
        sr = [sr, sprintf('%4.1f', rel(j))];
        if j < k.NSEED_FADE, si = [si, ' ']; sr = [sr, ' ']; end
      end
      fprintf('    %4.0fµs %3ddB | %16s %16s %11.2f %12.2f %8.2f %11.0f\n', ...
              dur * 1e6, cnr, si, sr, median([rr.rms_pre]), ...
              median([rr.rms_post]), ratio, gap);
      d1_ok = d1_ok && all(isfinite(rel) & (rel <= 20.0));
      d1_worst = max(d1_worst, max(rel));
      d2_ok = d2_ok && (ratio <= 1.5);
      d2_worst = max(d2_worst, ratio);
      if dur >= 10e-6
        d3_ok = d3_ok && all(inv >= 0.6);
      else
        inv_2us = [inv_2us, inv];
      end
      a7.rel_med(ig) = median(rel);
      a7.ratio(ig) = ratio;
      a7.gap_med(ig) = gap;
      a7.inv_med(ig) = median(inv);
    end
  end
  fprintf(['\n  产品需求 (本仿真文档化, 不是完整产品状态机): HOLD/ACQUIRE 期间必须' ...
           '置 invalid 标志; 任何衰落间隙上禁止位移积分 --\n']);
  fprintf(['  跨衰落相位滑移实测 %.0f..%.0f 周 (30 m/s 时 NCO 飞轮' ...
           '只能外推, 位移连续性无法承诺, 即使 2 µs 衰落亦然);\n'], gap_lo, gap_hi);
  fprintf(['  2 µs 衰落短于门控检测常数 (tauP=1µs IIR + 0.25µs 确认), invalid 标志' ...
           '覆盖率实测 %.0f-%.0f%% -- 不可靠;' ...
           ' 若产品需要标记亚微秒级衰落, 须另加快速幅度监测通道.\n'], ...
          100 * min(inv_2us), 100 * max(inv_2us));
  ck = struct('cid', {}, 'label', {}, 'ok', {}, 'detail', {});
  ck(end+1) = vt_check('D1', '全部 (时长×CNR×seed) 光恢复后重锁, relock ≤ 20 µs', ...
      d1_ok, sprintf('最大 %.1f µs (FAST acq_time=4µs + 门控检测延迟)', d1_worst));
  ck(end+1) = vt_check('D2', '重锁后速度 RMS 误差恢复: 每组中值 post ≤ 1.5× pre', ...
      d2_ok, sprintf('最坏 post/pre = %.2f', d2_worst));
  ck(end+1) = vt_check('D3', ['衰落 ≥ 10 µs: 全部 seed invalid 覆盖率 ≥ 60% ' ...
      '(HOLD/ACQUIRE ⇒ invalid 标志可用; 2 µs 衰落仅报告不断言)'], d3_ok, ...
      sprintf('2µs 覆盖率 %.0f-%.0f%% (短于检测常数)', ...
              100 * min(inv_2us), 100 * max(inv_2us)));
end


% =================================================== A8 noisy slip statistics
function [a8, ck] = A8_()
  dp = design_params();
  k = kconst_();
  vt_print_header(sprintf(['A8  案例c 含噪 near-pi / 滑周统计 (审计项4): ' ...
      '%d seeds, CNR=%.0fdB, FAST 档, gate=auto'], k.NSEED_STATS, k.CNR_DB));
  fprintf(['  区分两种事件: near_pi = 鉴相器 |e|>2.8 rad 的噪声激励瞬时越界 ' ...
           '(代理量, 确定性峰值已达 1.5 rad);\n']);
  fprintf(['  slips = unwrap(angle(y_full)) 相对真实相位的 2π 跳变 (真滑周, 产品' ...
           '相关量). clean 与含噪分开断言: 含噪下不要求 near_pi=0, 只要求有界.\n']);
  sc = make_scene_(100e3, k.V_MAX_APP);
  s2 = 10^(-k.CNR_DB / 10);
  zc = exp(1i * sc.ph) + ...
       complex_bandlimited_noise(sc.N, dp.FS, 20e6, 1e-10, np_rng_new(777));
  [yf, ~, ~, ~, dg] = vt_gear_filter(zc, 'FAST', 1e-10, 'always');
  np_clean = dg.near_pi_events;
  sl_clean = slips_vs_true_(yf, sc.ph);
  nps = [];
  sls = [];
  errs = [];
  for s = 0:k.NSEED_STATS-1
    rh = np_rng_new(90000 + s);
    z = exp(1i * sc.ph) + ...
        complex_bandlimited_noise(sc.N, dp.FS, dp.B_FRONTEND, s2, rh);
    [yf, ~, ~, ~, dg] = vt_gear_filter(z, 'FAST', s2, 'auto');
    nps(end+1) = dg.near_pi_events;
    sls(end+1) = slips_vs_true_(yf, sc.ph);
    errs(end+1) = amp_err_pct_(vdisc_(yf), sc);
  end
  fprintf('\n  clean 参考: near_pi=%.0f, slips=%.0f\n', np_clean, sl_clean);
  fprintf('  含噪分位数 (每 0.5 ms 记录, %d seeds):\n', k.NSEED_STATS);
  fprintf('    量                          p50     p90     p95     p99     max\n');
  fprintf('    %s %7.0f %7.0f %7.0f %7.0f %7.0f\n', padr_('near_pi 事件数', 22), ...
          pctile_(nps, 50), pctile_(nps, 90), pctile_(nps, 95), ...
          pctile_(nps, 99), max(nps));
  fprintf('    %s %7.0f %7.0f %7.0f %7.0f %7.0f\n', padr_('真滑周 slips', 22), ...
          pctile_(sls, 50), pctile_(sls, 90), pctile_(sls, 95), ...
          pctile_(sls, 99), max(sls));
  fprintf('    %s %7.2f %7.2f %7.2f %7.2f %7.2f\n', padr_('|ampErr full| %', 22), ...
          pctile_(abs(errs), 50), pctile_(abs(errs), 90), ...
          pctile_(abs(errs), 95), pctile_(abs(errs), 99), max(abs(errs)));
  fprintf(['\n  文档化限值 (fallback 区 100 kHz/30 m/s, phi_err=1.5 rad, ' ...
           'CNR=3dB): 真滑周 p95 ≤ 3 / p99 ≤ 5 每 0.5 ms; near_pi 代理 p95 ≤ 700;\n']);
  fprintf(['  幅值误差中值 < 10%% (与 E3 一致), p90 < 20%%. 案例b (10 kHz, 30 m/s) ' ...
           'phi_err=0.151 rad 守卫内, 其含噪滑周见 E2 detail (noisy slips max).\n']);
  ck = struct('cid', {}, 'label', {}, 'ok', {}, 'detail', {});
  ck(end+1) = vt_check('N1', ['A8 clean 参考: near_pi=0 且真滑周=0 ' ...
      '(与 E3 clean 判据一致)'], np_clean == 0 && sl_clean == 0, ...
      sprintf('near_pi=%.0f, slips=%.0f', np_clean, sl_clean));
  ok = pctile_(sls, 95) <= 3 && pctile_(sls, 99) <= 5 ...
       && pctile_(nps, 95) <= 700 ...
       && pctile_(abs(errs), 50) < 10.0 ...
       && pctile_(abs(errs), 90) < 20.0;
  ck(end+1) = vt_check('N2', sprintf(['含噪 %d seeds: 真滑周 p95≤3/p99≤5, ' ...
      'near_pi p95≤700, |err| p50<10%%/p90<20%% (有界文档化限值, 非零缺陷)'], ...
      k.NSEED_STATS), ok, ...
      sprintf(['slips p95=%.0f p99=%.0f max=%.0f, near_pi p95=%.0f, ' ...
               '|err| p50=%.2f%% p90=%.2f%%'], pctile_(sls, 95), ...
              pctile_(sls, 99), max(sls), pctile_(nps, 95), ...
              pctile_(abs(errs), 50), pctile_(abs(errs), 90)));
  a8 = struct('np_clean', np_clean, 'sl_clean', sl_clean, ...
      'np_pct', [pctile_(nps, 50), pctile_(nps, 90), pctile_(nps, 95), ...
                 pctile_(nps, 99), max(nps)], ...
      'sl_pct', [pctile_(sls, 50), pctile_(sls, 90), pctile_(sls, 95), ...
                 pctile_(sls, 99), max(sls)], ...
      'err_pct', [pctile_(abs(errs), 50), pctile_(abs(errs), 90), ...
                  pctile_(abs(errs), 95), pctile_(abs(errs), 99), ...
                  max(abs(errs))]);
end


% ============================================================= A4 conclusion
function A4_(bounds, e2e)
  dp = design_params();
  k = kconst_();
  vt_print_header('A4  结论 (用户应用: v_peak<=30 m/s, 典型 f<=100 kHz)');
  ra = e2e.a;
  rc = e2e.c;
  g_slow = vt_stats(ra.row.SLOW.gains_full);
  g_fast_100k = vt_stats(ra.row.FAST.gains_full);
  g_c = vt_stats(rc.row.FAST.gains_full);
  v_s100 = v_guard_limit_(100e3, 'SLOW');
  v_s1k = v_guard_limit_(1e3, 'SLOW');
  v_f100 = v_guard_limit_(100e3, 'FAST');
  v_pi100 = v_guard_limit_(100e3, 'FAST', pi);
  fD30 = 2 * k.V_MAX_APP / dp.LAMBDA;
  fprintf('\n');
  fprintf('  [结论1] "<=100 kHz 典型速度下 SLOW 是否总是最优?" -- 不是"总是", 是"守卫内最优".\n');
  fprintf('    SLOW 通过守卫的速度上限随频率下降: %.1f m/s @1 kHz -> %.2f m/s\n', ...
          v_s1k, v_s100);
  fprintf('    @100 kHz (见 A1 边界表). 该范围内 SLOW 最优且被自动选中 (100 kHz 实测弱光\n');
  fprintf('    SNR 增益 %+.1f dB, vs FAST 同点 %+.1f dB). 典型 VAMP=20 mm/s\n', ...
          g_slow, g_fast_100k);
  fprintf('    在全部 <=100 kHz 频点 phi_err<=0.097 rad, 守卫余量 >10x -- 默认 SLOW 正确.\n');
  fprintf('    速度超过边界后守卫自动升档, 且这是必须的: 强制 SLOW/MEDIUM 在 30 m/s 时\n');
  fprintf('    幅值误差 -90%%..-100%% (A2 实测), 不升档 = 测量报废.\n');
  fprintf('\n');
  fprintf('  [结论2] 30 m/s 时 FAST 成为必需的最低频率: %.2f kHz.\n', ...
          bounds.f_med / 1e3);
  fprintf('    30 m/s 各档边界 (解析, A2 仿真证实): SLOW 只到 %.0f Hz,\n', ...
          bounds.f_slow);
  fprintf('    MEDIUM 到 %.2f kHz, 其上守卫强制 FAST.\n', bounds.f_med / 1e3);
  fprintf('    FAST 在 1 rad 守卫内到 %.1f kHz; %.0f-100 kHz\n', ...
          bounds.f_fast1 / 1e3, bounds.f_fast1 / 1e3);
  fprintf('    区间为 fallback FAST (phi_err 1.0-1.5 rad, 仍 < pi, atan2 鉴相器保持线性):\n');
  fprintf('    实测 (100 kHz, 30 m/s) clean 幅值误差 %+.2f%%,\n', ...
          rc.row.FAST.err_full);
  fprintf('    0 滑周, SNR 增益 %+.2f dB -- 可用. 绝对滑周极限 phi_err=pi 在\n', g_c);
  fprintf('    %.0f kHz @30 m/s, 或 %.0f m/s @100 kHz\n', ...
          bounds.f_fastpi / 1e3, v_pi100);
  fprintf('    (用户最坏点速度余量 %.1fx).\n', v_pi100 / k.V_MAX_APP);
  fprintf('\n');
  fprintf('  [结论3] 换档动态: 无"临时错档"风险 (A3 实测).\n');
  fprintf('    升档即时 (阶跃后第 1 次选档更新), 降档一次一档只经过更高档 -- 高档在低速\n');
  fprintf('    工况永远守卫安全, 代价只是 <=1 个选档周期的 SNR 非最优. 50->100 kHz\n');
  fprintf('    @20 mm/s 全程 SLOW 无抖动. 唯一暴露窗是阶跃与下一次选档更新之间\n');
  fprintf('    (任何离散选档器固有), 由选档更新率决定, 与迟滞设计无关.\n');
  fprintf('\n');
  fprintf('  [结论4] 实用建议.\n');
  fprintf('    - 默认 SLOW + 现有 guard-first 自动选档即可覆盖用户全域\n');
  fprintf('      (f<=100 kHz, v<=30 m/s), 无需人工干预档位.\n');
  fprintf('    - 高速工况 SNR 增益从 SLOW 的 ~%+.0f dB 降到 FAST 的 ~%+.0f dB\n', ...
          g_slow, g_fast_100k);
  fprintf('      (@100 kHz): 物理必然 (环带宽换跟踪能力); 30 m/s 信号本身极大\n');
  fprintf('      (fD_peak=%.1f MHz), 幅值误差中值 <5%% (A2), SNR 不是瓶颈.\n', ...
          fD30 / 1e6);
  fprintf('    - 需要档位关注的只有 v>%.0f m/s 且 f 接近 100 kHz 的组合\n', v_f100);
  fprintf('      (fallback 区), 本仿真已证明到 30 m/s 均正常.\n');
  fprintf('\n');
  fprintf('  [结论5] 是否需要改设计? 档位设计不需要; 有三点已实测/文档化的注意事项.\n');
  fprintf('    guard-first 选档在最坏点 (100 kHz, 30 m/s) 实测正确工作; 迟滞无副作用.\n');
  fprintf('    (1) 前端带宽 (A6 实测, 审计项1): 30 m/s 时 fD_peak=%.1f MHz 超过\n', ...
          fD30 / 1e6);
  fprintf('        B_FRONTEND/2=%.0f MHz; 真实 40 MHz 前端会削掉信号\n', ...
          dp.B_FRONTEND / 2e6);
  fprintf('        (A6 v1: clean 误差已 >20%%), 硬件前端必须通过\n');
  fprintf('        ±%.0f MHz (fs=250 MS/s 复采样支持), 且 CNR 指标\n', ...
          ceil(fD30 / 1e6) + 4);
  fprintf('        必须在实际前端带宽上定义/实测 (A6 v4/v5: 同 PSD 扩带等效 CNR<3dB,\n');
  fprintf('        误差 -39%%/-47%%). 物理一致模型下 (总CNR=3dB, B=86/100 MHz) 案例c 结论\n');
  fprintf('        成立 (A6 v2/v3 中值误差 -3..-5%%).\n');
  fprintf('    (2) fallback 降级区 (审计项2, 选项A): 66-100 kHz × 高速组合超出 1 rad\n');
  fprintf('        守卫 (最坏 1.5 rad < pi), cfg_for_frequency 现返回\n');
  fprintf('        guard_ok=False/overrange=True 供产品上报; 保持 FAST fn=1.6M --\n');
  fprintf('        提高到 2.1-2.2 MHz 虽可满足守卫但在 3 MHz 规格点损失 ~2..3 dB 弱光\n');
  fprintf('        SNR (见 study_fast_fn_options.py). 含噪滑周有界: A8 实测 p95≤3 每\n');
  fprintf('        0.5 ms. 若未来需求扩展到 f>100 kHz 且同时 30 m/s, 再评估提高 FAST fn\n');
  fprintf('        (滑周极限 %.0f kHz @30 m/s).\n', bounds.f_fastpi / 1e3);
  fprintf('    (3) 掉光行为 (A7 实测, 审计项3): 光恢复后 ~5 µs 重锁, 速度精度恢复;\n');
  fprintf('        但跨衰落相位滑移 10^1..10^3 周 -- HOLD/ACQUIRE 期间必须置 invalid\n');
  fprintf('        标志, 任何衰落间隙上禁止位移积分; 短于 ~2 µs 的深衰落不能保证被门控\n');
  fprintf('        标记 (检测常数限制).\n');
end
