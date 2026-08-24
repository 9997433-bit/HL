function validate_tracking()
%VALIDATE_TRACKING V1-V4 validation of the three-gear homodyne IQ tracking filter.
%   MATLAB/Octave port of homodyne_tracking_design/validate_tracking.py with
%   the same scenarios, seeds and PASS/FAIL criteria:
%     V1  weak light CNR=3 dB, 100k/1M/3M bursts, all gears (C1-C4)
%     V2  plain fixed complex LP vs tracking gears (C6, C7)
%     V3  speckle dropout (honest report, no hard criterion)
%     V4  gear selection by frequency + tracking-error guard (C5)
%   Noise realizations are IDENTICAL to Python (numpy-exact RNG kernel), so
%   metrics match the reference within FFT rounding.
%
%   Run:  cd matlab && octave --eval validate_tracking
%   Saves golden metrics to golden/validate_tracking_mat.mat and raises an
%   error (nonzero exit code) if any check fails.
  t_all = tic;
  sd = fileparts(mfilename('fullpath'));
  addpath(fullfile(sd, 'homodyne'));
  ensure_kernels();

  dp = design_params();
  c = vt_const();

  fprintf('三档零差IQ跟踪滤波方案 -- 仿真验证 (V1-V4)\n');
  fprintf(['reference core: pll_carrier_regen / residual-window, ' ...
           'fs=%.0fMS/s, lambda=%.0fnm, T=%.1fms/run\n'], ...
          dp.FS / 1e6, dp.LAMBDA * 1e9, c.T * 1e3);

  v0_table_();
  v1 = V1_(12, 3.0);
  fprintf('\n  -- V1 criteria --\n');
  CHECKS = struct('cid', {}, 'label', {}, 'ok', {}, 'detail', {});
  c1 = abs(v1.err_full(3, 3));
  CHECKS(end+1) = vt_check('C1', 'FAST档 @3MHz 幅值误差 < 3%', c1 < 3.0, ...
                           sprintf('%.2f%%', c1));
  m2 = vt_stats(v1.gains_full{3, 3});
  CHECKS(end+1) = vt_check('C2', 'FAST档 @3MHz SNR gain > 0 dB (CNR=3dB)', ...
                           m2 > 0.0, sprintf('%+.2f dB', m2));
  m3 = vt_stats(v1.gains_full{1, 1});
  CHECKS(end+1) = vt_check('C3', ...
      'SLOW档 @100kHz SNR gain > 10 dB (CNR=3dB, Bf=40MHz)', m3 > 10.0, ...
      sprintf('%+.2f dB', m3));
  worst = max(abs(v1.err_full(3, :)));
  CHECKS(end+1) = vt_check('C4', '三档 @3MHz 幅值误差均 < 5%', worst < 5.0, ...
                           sprintf('worst %.2f%%', worst));
  [v2, ck2] = V2_(8, 3.0);
  CHECKS = [CHECKS, ck2];
  v3 = V3_(12, 50e-6, 20e6);
  [ck4, v4_sel, v4_pe] = V4_(v1, v2);
  CHECKS = [CHECKS, ck4];

  vt_print_header('ASSERTION SUMMARY');
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
  blb = zeros(1, 3);
  for ib = 1:3
    blb(ib) = b_loop(dp.BANDS.(dp.ORDER{ib}).fn);
  end
  g.det = struct('v4_sel', v4_sel, 'v4_phierr', v4_pe, 'b_loop_bands', blb);
  nz = struct();
  nz.v1_err_full = v1.err_full;
  nz.v1_err_nco = v1.err_nco;
  [nz.v1_gain_full_med, nz.v1_gain_full_p10, nz.v1_gain_full_p90] = ...
      cellstats_(v1.gains_full);
  nz.v1_gain_nco_med = cellstats_(v1.gains_nco);
  nz.v1_lock_mean = cellfun(@mean, v1.lock);
  nz.v2_err_clean = v2.err_clean;
  nz.v2_err_noisy_med = cellstats_(v2.errs);
  nz.v2_gain_med = cellstats_(v2.gains);
  nz.v3_sp_med = cellstats_(v3.sp);
  nz.v3_sl_med = cellstats_(v3.sl);
  nz.v3_dr_med = cellstats_(v3.dr);
  g.noisy = nz;
  gdir = fullfile(sd, 'golden');
  if ~exist(gdir, 'dir'), mkdir(gdir); end
  gfile = fullfile(gdir, 'validate_tracking_mat.mat');
  save('-v7', gfile, '-struct', 'g');
  fprintf('[golden metrics saved to %s]\n', gfile);

  if ~allok
    error('validate_tracking: SOME CHECKS FAILED');
  end
end


% ================================================================== V0 table
function v0_table_()
  dp = design_params();
  vt_print_header(sprintf(['V0  三档参数表  (lambda=1550nm, fs=250MS/s, ' ...
      'zeta=%g, B_win=%.0fMHz common window, B_frontend=40MHz)'], ...
      dp.ZETA, dp.B_WIN / 1e6));
  fprintf('  %-7s %7s %7s %8s %8s %16s   note\n', ...
          'gear', 'f_max', 'fn', 'B_loop', 'ceil40', 'in-loop CNR@3dB');
  for ib = 1:3
    name = dp.ORDER{ib};
    fn = dp.BANDS.(name).fn;
    B = b_loop(fn);
    ceil40 = 10 * log10((dp.B_FRONTEND / 2) / B);
    fprintf('  %-7s %6.0fk %6.0fk %7.2fM %+7.1fdB %15.1fdB   %s\n', ...
            name, dp.BANDS.(name).f_target_max / 1e3, fn / 1e3, B / 1e6, ...
            ceil40, 3 + ceil40, dp.BANDS.(name).label);
  end
  fprintf(['  公共测量窗 (三档相同): -6dB 截止 %.0f MHz, 平坦(<1%%误差)区 ' ...
           'DC..~3.6 MHz (window ENBW %.1f MHz -> in-window CNR@3dB ~ ' ...
           '%.1f dB)\n'], dp.B_WIN / 1e6, 2 * 0.975 * dp.B_WIN / 1e6, ...
          3 + 10 * log10(dp.B_FRONTEND / (2 * 0.975 * dp.B_WIN)));
end


% ================================================================== V1
function v1 = V1_(nseed, cnr_db)
  dp = design_params();
  c = vt_const();
  vt_print_header(sprintf(['V1  弱光 CNR=%.0fdB, B_frontend=%.0fMHz -- ' ...
      '100k/1M/3M 正弦速度burst, 三档 x 三频  (%d seeds, median [p10,p90])'], ...
      cnr_db, dp.B_FRONTEND / 1e6, nseed));
  s2 = 10^(-cnr_db / 10);
  FREQS = [100e3, 1e6, 3e6];
  v1 = struct();
  v1.err_full = zeros(3, 3);
  v1.err_nco = zeros(3, 3);
  v1.g_full = zeros(3, 3);
  v1.g_nco = zeros(3, 3);
  v1.gains_full = cell(3, 3);
  v1.gains_nco = cell(3, 3);
  v1.lock = cell(3, 3);
  for ifq = 1:3
    f0 = FREQS(ifq);
    sc = vt_make_scene(f0);
    zc = vt_clean_z(sc);
    for ib = 1:3
      band = dp.ORDER{ib};
      [yf, yn] = vt_gear_filter(zc, band, 1e-10, 'always');
      ef = vt_amp_err_pct(vt_vdisc(yf), sc);
      en = vt_amp_err_pct(vt_vdisc(yn), sc);
      v1.err_full(ifq, ib) = ef;
      v1.err_nco(ifq, ib) = en;
      v1.g_full(ifq, ib) = 20 * log10(max(1 + ef / 100, 1e-12));
      v1.g_nco(ifq, ib) = 20 * log10(max(1 + en / 100, 1e-12));
    end
    for s = 0:nseed-1
      rh = np_rng_new(10000 + fix(f0 / 1e3) * 100 + s);
      z = exp(1i * sc.ph) + ...
          complex_bandlimited_noise(c.N, dp.FS, dp.B_FRONTEND, s2, rh);
      a_off = vt_asd_at(vt_vdisc(z), sc);
      for ib = 1:3
        band = dp.ORDER{ib};
        [yf, yn, ~, ~, dg] = vt_gear_filter(z, band, s2, 'auto');
        v1.gains_full{ifq, ib}(end+1) = v1.g_full(ifq, ib) ...
            + 20 * log10(a_off / vt_asd_at(vt_vdisc(yf), sc));
        v1.gains_nco{ifq, ib}(end+1) = v1.g_nco(ifq, ib) ...
            + 20 * log10(a_off / vt_asd_at(vt_vdisc(yn), sc));
        v1.lock{ifq, ib}(end+1) = dg.lock_frac;
      end
    end
    p = vt_scene_params(f0);
    fprintf('\n  f0 = %.0f kHz  (burst %d cyc, vamp %.0f mm/s)\n', ...
            f0 / 1e3, p.ncyc, c.VAMP * 1e3);
    fprintf('    %-7s %6s | %11s %11s | %24s | %16s | %6s\n', ...
            'gear', 'fn', 'ampErr full', 'ampErr NCO', ...
            'SNRgain full dB', 'SNRgain NCO dB', 'lock%');
    for ib = 1:3
      band = dp.ORDER{ib};
      [m, lo, hi] = vt_stats(v1.gains_full{ifq, ib});
      mn = vt_stats(v1.gains_nco{ifq, ib});
      fprintf(['    %-7s %5.0fk | %+10.2f%% %+10.2f%% | %+7.2f ' ...
               '[%+7.2f,%+7.2f] | %+15.2f | %5.1f\n'], ...
              band, dp.BANDS.(band).fn / 1e3, v1.err_full(ifq, ib), ...
              v1.err_nco(ifq, ib), m, lo, hi, mn, ...
              100 * mean(v1.lock{ifq, ib}));
    end
  end
  fprintf(['\n  (ampErr = R1 near-noiseless transfer; full = ' ...
           'NCO+residual-window output, NCO = carrier path alone)\n']);
  Bf = b_loop(dp.BANDS.FAST.fn);
  fprintf(['  物理解释: 点击(click)清除发生在复域残差窗内, 要求载波环比窗慢' ...
           ' (B_loop < B_win).\n  SLOW/MEDIUM (ζ=1.2 下 0.49M/2.34M) 满足, ' ...
           '故低频增益达到甚至超过窗的门限扩展;\n  FAST 档 B_loop=' ...
           '%.1fM > %.0fM, NCO 把部分点击跟进输出, 低频增益只剩 ~+12dB ' ...
           '(部分清除)\n  -- 所以低频目标必须用低档 (V4选档保证).' ...
           ' ζ 的选择依据见 validate_zeta_sweep (审查项#7).\n'], ...
          Bf / 1e6, dp.B_WIN / 1e6);
end


% ================================================================== V2
function [v2, ck] = V2_(nseed, cnr_db)
  dp = design_params();
  c = vt_const();
  Bp = b_loop(dp.BANDS.SLOW.fn);
  vt_print_header(sprintf(['V2  plain LP 对照 (同 B_loop=%.2fM / 同 B_win=' ...
      '%.0fM 固定复数低通) vs 跟踪档 -- PLL价值边界\n    100 kHz burst, ' ...
      '速度幅值扫描, CNR=%.0fdB, B_frontend=%.0fMHz (%d seeds)'], ...
      Bp / 1e6, dp.B_WIN / 1e6, cnr_db, dp.B_FRONTEND / 1e6, nseed));
  s2 = 10^(-cnr_db / 10);
  pathnames = {'LP-Bloop', 'LP-Bwin', 'SLOW', 'MEDIUM', 'FAST'};
  pathband = {'', '', 'SLOW', 'MEDIUM', 'FAST'};
  vamps = [0.02, 0.3, 1.0, 3.0, 6.0];
  v2 = struct();
  v2.err_clean = zeros(5, 5);
  v2.g0 = zeros(5, 5);
  v2.errs = cell(5, 5);
  v2.gains = cell(5, 5);
  fprintf('\n    %7s %8s | %-9s %12s %12s | %24s\n', 'vamp', 'fD_peak', ...
          'path', 'ampErr clean', 'ampErr noisy', 'SNRgain@100k dB');
  for iv = 1:5
    vamp = vamps(iv);
    sc = vt_make_scene(100e3, vamp);
    fD = 2 * vamp / dp.LAMBDA;
    zc = vt_clean_z(sc);
    for ip = 1:5
      if isempty(pathband{ip})
        if ip == 1, cut = Bp; Nt = 2049; else, cut = dp.B_WIN; Nt = dp.NT_WIN; end
        vcl = vt_vdisc(vt_fft_lp(zc, cut, Nt));
      else
        yf = vt_gear_filter(zc, pathband{ip}, 1e-10, 'always');
        vcl = vt_vdisc(yf);
      end
      e = vt_amp_err_pct(vcl, sc);
      v2.err_clean(iv, ip) = e;
      v2.g0(iv, ip) = 20 * log10(max(1 + e / 100, 1e-12));
    end
    for s = 0:nseed-1
      rh = np_rng_new(20000 + fix(vamp * 1000) + s);
      z = exp(1i * sc.ph) + ...
          complex_bandlimited_noise(c.N, dp.FS, dp.B_FRONTEND, s2, rh);
      a_off = vt_asd_at(vt_vdisc(z), sc);
      for ip = 1:5
        if isempty(pathband{ip})
          if ip == 1, cut = Bp; Nt = 2049; else, cut = dp.B_WIN; Nt = dp.NT_WIN; end
          v = vt_vdisc(vt_fft_lp(z, cut, Nt));
        else
          yf = vt_gear_filter(z, pathband{ip}, s2, 'auto');
          v = vt_vdisc(yf);
        end
        v2.errs{iv, ip}(end+1) = vt_amp_err_pct(v, sc);
        v2.gains{iv, ip}(end+1) = v2.g0(iv, ip) ...
            + 20 * log10(a_off / vt_asd_at(v, sc));
      end
    end
    for ip = 1:5
      [m, lo, hi] = vt_stats(v2.gains{iv, ip});
      em = vt_stats(v2.errs{iv, ip});
      if ip == 1
        head = sprintf('    %5.0fmm/s %7.2fM |', vamp * 1e3, fD / 1e6);
      else
        head = sprintf('    %7s %8s |', '', '');
      end
      fprintf('%s %-9s %+11.1f%% %+11.1f%% | %+7.2f [%+7.2f,%+7.2f]\n', ...
              head, pathnames{ip}, v2.err_clean(iv, ip), em, m, lo, hi);
    end
  end
  fprintf(['\n    边界结论: 固定LP在 fD_peak 超出其通带后幅值崩溃; ' ...
           '跟踪档把边界推到环路失锁点\n    |1-H_L(f_v)|*phi_amp > pi ' ...
           '(SLOW档先失效 -> 需升档, 见V4); 静止载波下固定LP与(正确选档的)' ...
           '跟踪档等价 -- 这就是PLL的价值边界.\n']);
  sel = select_band(100e3, 0.02);
  isel = find(strcmp(pathnames, sel), 1);
  g_lp = vt_stats(v2.gains{1, 2});
  g_sel = vt_stats(v2.gains{1, isel});
  ck = struct('cid', {}, 'label', {}, 'ok', {}, 'detail', {});
  ck(end+1) = vt_check('C6', sprintf(['静止载波: 固定LP(B_win) 与选定档(%s) ' ...
      'SNR gain 差 < 3 dB (PLL无增值 -- 价值边界的诚实面)'], sel), ...
      abs(g_lp - g_sel) < 3.0, ...
      sprintf('LP %+.2f dB vs %s %+.2f dB', g_lp, sel, g_sel));
  e_lp = v2.err_clean(5, 2);
  e_lpn = vt_stats(v2.errs{5, 2});
  e_fast = v2.err_clean(5, 5);
  e_fastn = vt_stats(v2.errs{5, 5});
  ck(end+1) = vt_check('C7', ['fD=7.7M > B_win: 固定LP严重超出5%预算' ...
      '(清洁<-15%) 而 FAST档 <5% (跟踪的价值面)'], ...
      e_lp < -15 && abs(e_fast) < 5, ...
      sprintf('LP-Bwin %+.1f%% (含噪 %+.1f%%) vs FAST %+.1f%% (含噪 %+.1f%%)', ...
              e_lp, e_lpn, e_fast, e_fastn));
end


% ================================================================== V3
function v3 = V3_(nseed, tau_sp, Bf)
  dp = design_params();
  c = vt_const();
  band = select_band(3e6, c.VAMP);
  B_OUT = 1e6;
  thr = 20 * c.VAMP;
  vt_print_header(sprintf(['V3  散斑掉落 (tau_c=%.0fus, gear=%s, ' ...
      'B_frontend=%.0fMHz, 输出统一滤到 %.0fMHz, %d seeds) -- 诚实报告'], ...
      tau_sp * 1e6, band, Bf / 1e6, B_OUT / 1e6, nseed));
  sc = vt_make_scene(3e6);
  cnrs = [6, 12];
  v3 = struct();
  v3.sp = cell(2, 3);
  v3.sl = cell(2, 3);
  v3.dr = cell(2, 3);
  for ic = 1:2
    cnr = cnrs(ic);
    s2 = 10^(-cnr / 10);
    lock = [];
    for s = 0:nseed-1
      rh = np_rng_new(30000 + cnr * 100 + s);
      h = make_speckle(c.N, dp.FS, tau_sp, rh);
      z = h .* exp(1i * sc.ph) + ...
          complex_bandlimited_noise(c.N, dp.FS, Bf, s2, rh);
      ph_ref = sc.ph + np_unwrap(angle(h));
      ph_ref = ph_ref - ph_ref(1);
      xref_lp = vt_fft_lp(dp.LAMBDA / (4 * pi) * ph_ref, B_OUT, 2049);
      for it = 1:3
        if it == 1
          v = vt_vdisc(z);
          ph = np_unwrap(angle(z));
        else
          if it == 2, gate = 'always'; else, gate = 'auto'; end
          [yf, ~, ~, ~, dg] = vt_gear_filter(z, band, s2, gate);
          v = vt_vdisc(yf);
          ph = np_unwrap(angle(yf));
          if it == 3
            lock(end+1) = dg.lock_frac;
          end
        end
        ph = ph - ph(1);
        vlp = vt_fft_lp(v, B_OUT, 2049);
        ex = abs(vlp(sc.Wq)) > thr;
        v3.sp{ic, it}(end+1) = sum(diff([0; double(ex)]) == 1);
        xh = vt_fft_lp(dp.LAMBDA / (4 * pi) * ph, B_OUT, 2049);
        e = xh - xref_lp;
        v3.dr{ic, it}(end+1) = 1e9 * std(e - mean(e), 1);
        v3.sl{ic, it}(end+1) = sum(abs(diff(ph - ph_ref)) > pi);
      end
    end
    fprintf('\n  mean CNR = %d dB   (gate-on lock fraction %.1f%%)\n', ...
            cnr, 100 * mean(lock));
    fprintf('    %-30s%20s%20s%20s\n', 'metric', 'OFF', ...
            'gear gate-off', 'gear gate-on');
    labels = {sprintf('velocity spikes >%.1f m/s', thr), ...
              'phase slips (2pi events)', 'disp rms err (nm, in 1 MHz)'};
    dat = {v3.sp, v3.sl, v3.dr};
    for il = 1:3
      fprintf('    %-30s', labels{il});
      for it = 1:3
        [m, lo, hi] = vt_stats(dat{il}{ic, it});
        fprintf('%8.0f [%4.0f,%5.0f]', m, lo, hi);
      end
      fprintf('\n');
    end
  end
  sp_off = vt_stats(v3.sp{1, 1});
  sp_on = vt_stats(v3.sp{1, 3});
  dr_off = vt_stats(v3.dr{1, 1});
  dr_on = vt_stats(v3.dr{1, 3});
  worse = dr_on > dr_off;
  if worse
    ratio = dr_on / max(dr_off, 1e-9);
    word = '恶化';
  else
    ratio = dr_off / max(dr_on, 1e-9);
    word = '改善';
  end
  fprintf(['\n  诚实结论: CNR=6dB 时 gate-on 把速度尖峰中值 %.0f -> %.0f 个, ' ...
           '位移rms误差 %.0f -> %.0f nm (%s %.1fx).\n'], ...
          sp_off, sp_on, dr_off, dr_on, word, ratio);
  if worse
    fprintf(['  本组实测: 尖峰抑制以位移精度为代价 -- 掉落期间NCO飞轮只能外推,' ...
             ' 位移连续性无法承诺.\n']);
  else
    fprintf(['  本组实测: 尖峰抑制未付出位移精度代价 (位移误差持平或改善);' ...
             ' 但掉落期间NCO飞轮只能外推, 位移连续性仍无法承诺.\n']);
  end
end


% ================================================================== V4
function [ck, v4_sel, v4_pe] = V4_(v1, v2)
  dp = design_params();
  vt_print_header('V4  档位切换: 按目标频率选档 + 跟踪误差守卫 (phi_err <= 1 rad)');
  cases_f = [100e3, 1e6, 3e6, 100e3, 100e3, 3e6];
  cases_v = [0.02, 0.02, 0.02, 1.0, 6.0, 0.1];
  cases_exp = {'SLOW', 'SLOW', 'SLOW', 'MEDIUM', 'FAST', 'SLOW'};
  fprintf('    %9s %8s | %12s %8s %8s | %9s %7s\n', 'f_target', 'v_peak', ...
          'phi_err SLOW', 'MEDIUM', 'FAST', 'selected', 'expect');
  ok = true;
  v4_sel = zeros(6, 1);
  v4_pe = zeros(6, 3);
  for i = 1:6
    sel = select_band(cases_f(i), cases_v(i));
    for ib = 1:3
      v4_pe(i, ib) = tracking_error_rad(cases_f(i), cases_v(i), ...
                                        dp.BANDS.(dp.ORDER{ib}).fn);
    end
    ok = ok && strcmp(sel, cases_exp{i});
    v4_sel(i) = find(strcmp(dp.ORDER, sel), 1);
    if strcmp(sel, cases_exp{i}), mism = ''; else, mism = '   <-- MISMATCH'; end
    fprintf('    %7.0fkHz %6.0fmm/s | %11.2fr %7.2fr %7.2fr | %9s %7s%s\n', ...
            cases_f(i) / 1e3, cases_v(i) * 1e3, v4_pe(i, 1), v4_pe(i, 2), ...
            v4_pe(i, 3), sel, cases_exp{i}, mism);
  end
  ck = struct('cid', {}, 'label', {}, 'ok', {}, 'detail', {});
  ck(end+1) = vt_check('C5', '选档逻辑: 全部场景返回期望档位', ok, ...
                       sprintf('%d cases, guard-pass narrowest gear', 6));
  g_s = vt_stats(v1.gains_nco{1, 1});
  g_f = vt_stats(v1.gains_nco{1, 3});
  fprintf(['\n  为什么低频选低档: 载波路径(NCO) @100kHz 的弱光SNR增益 ' ...
           'SLOW %+.1f dB vs FAST %+.1f dB (V1实测)\n'], g_s, g_f);
  e_s = v2.err_clean(5, 3);
  e_f = v2.err_clean(5, 5);
  fprintf(['  为什么大动态升档: vamp=6 m/s @100kHz 时幅值误差 ' ...
           'SLOW %+.1f%% vs FAST %+.1f%% (V2实测)\n'], e_s, e_f);
  fprintf(['  测量带宽在换档时不变 (公共4MHz残差窗), 换档只改变载波环动态 -- ' ...
           '见V1: 三档3MHz幅值误差均合格.\n']);
end


% ----------------------------------------------------------------- helpers
function [med, p10, p90] = cellstats_(cc)
  med = zeros(size(cc));
  p10 = zeros(size(cc));
  p90 = zeros(size(cc));
  for i = 1:numel(cc)
    [med(i), p10(i), p90(i)] = vt_stats(cc{i});
  end
end
