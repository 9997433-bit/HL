function rc = validate_diversity_p0_p1()
%VALIDATE_DIVERSITY_P0_P1 QTec diversity P0+P1 validation with PASS/FAIL assertions.
% Faithful port of qtec_diversity_design/validate_diversity_p0_p1.py.
%
% P0  multi-channel speckle infrastructure: joint deep-fade statistics of M
%     independent Rayleigh channels follow p^M (M = 1, 3, 4; rho = 0;
%     tau_c = 50 us), plus a correlated-channel (rho = 0.5) sanity check.
% P1  non-coherent SNR-weighted velocity-domain combining baseline:
%     M = 3 channels, mean CNR = 6 dB/channel, speckle tau_c = 50 us,
%     3 MHz burst.  Every channel demodulated independently (homodyne gear
%     from select_band(3 MHz, 20 mm/s) = SLOW: PLL + common residual window)
%     and FM-discriminated; block-wise weights with cross-channel gate and
%     all-dark HOLD flywheel.  Combined output compared against the PER-SEED
%     ORACLE best single channel (per metric).
%
% RNG note: same policy as validate_heterodyne.m -- Octave's own RNG is
% seeded with the Python seed numbers; assertions are statistical, the
% deterministic chain is covered by compare_qtec_golden.m.
%
% Exit code 0 iff all checks PASS (also returned as rc).
  here = fileparts(mfilename('fullpath'));
  addpath(fullfile(here, '..', 'homodyne'));         % set_rng, hd_* helpers
  addpath(fullfile(here, '..', 'homodyne', 'core')); % canonical shared core
  addpath(here);
  global VQTC
  VQTC = struct();
  VQTC.P = hd_params();
  VQTC.checks = {};

  t0 = tic;
  fprintf('QTec 多路散斑分集 P0+P1 -- 仿真验证 [MATLAB port]\n');
  fprintf(['per-channel demod: homodyne pll_carrier_regen + 公共残差窗, ' ...
           'fs=%.0fMS/s, lambda=%.0fnm\n'], ...
          VQTC.P.FS / 1e6, VQTC.P.LAMBDA * 1e9);
  P0();
  P1();
  print_header('ASSERTION SUMMARY');
  allok = true;
  for i = 1:numel(VQTC.checks)
    c = VQTC.checks{i};
    allok = allok && c{3};
    fprintf('  [%s] %s  %s  (%s)\n', passfail(c{3}), c{1}, c{2}, c{4});
  end
  if allok
    fprintf('\nALL CHECKS PASSED\n');
  else
    fprintf('\nSOME CHECKS FAILED\n');
  end
  fprintf('[elapsed %.1f s]\n', toc(t0));
  rc = double(~allok);
end


% ================================================================== helpers
function s = passfail(ok)
  if ok
    s = 'PASS';
  else
    s = 'FAIL';
  end
end

function print_header(title)
  fprintf('\n%s\n', repmat('=', 1, 86));
  fprintf('%s\n', title);
  fprintf('%s\n', repmat('=', 1, 86));
end

function ok = check(cid, label, ok, detail)
  global VQTC
  VQTC.checks{end + 1} = {cid, label, ok, detail};
  fprintf('  [%s] %s  %s  (%s)\n', passfail(ok), cid, label, detail);
end

function [m, lo, hi] = stats(a)
  a = a(isfinite(a));
  if isempty(a)
    m = NaN; lo = NaN; hi = NaN;
    return;
  end
  s = sort(a(:));
  n = numel(s);
  m = median(s);
  lo = s(max(1, min(n, ceil(10 / 100 * n))));
  hi = s(max(1, min(n, ceil(90 / 100 * n))));
end


% ================================================================== P0
function res = P0()
  nseed = 6;
  tau_c = 50e-6;
  fs_stat = 400e3;           % 20 samples per tau_c -- ample for fade stats
  T = 2.5;                   % 50 000 tau_c per seed per channel
  N = floor(T * fs_stat);
  F_MOD = 0.3567;
  F_DEEP = 0.105;            % -4.5 dB / -9.8 dB intensity fades
  p_mod = fade_prob_theory(F_MOD);
  p_deep = fade_prob_theory(F_DEEP);
  print_header(sprintf(['P0  多路散斑联合深衰落统计  (tau_c=%.0fus, rho=0, ' ...
      '%d seeds x %.1fs @ %.0fkS/s = %s tau_c/通道)'], tau_c * 1e6, nseed, ...
      T, fs_stat / 1e3, sprintf('%.0f', nseed * T / tau_c)));
  fprintf(['  衰落定义: 通道强度 I_k < F*<I_k>;  F=%g (-4.5dB, p1理论 %.4f) ' ...
           '与 F=%g (-9.8dB 深衰落, p1理论 %.4f)\n'], ...
          F_MOD, p_mod, F_DEEP, p_deep);
  Ms = [1, 3, 4];
  res = struct();
  for mi = 1:numel(Ms)
    M = Ms(mi);
    r_mod = zeros(nseed, 1);
    r_deep = zeros(nseed, 1);
    p1_mod = [];
    p1_deep = [];
    for s = 0:nseed - 1
      set_rng(40000 + 97 * M + s);
      h = make_speckle_multi(N, fs_stat, tau_c, M, 0.0);
      r_mod(s + 1) = joint_fade_fraction(h, F_MOD);
      r_deep(s + 1) = joint_fade_fraction(h, F_DEEP);
      for k = 1:M
        p1_mod(end + 1) = joint_fade_fraction(h(k, :), F_MOD);      %#ok<AGROW>
        p1_deep(end + 1) = joint_fade_fraction(h(k, :), F_DEEP);    %#ok<AGROW>
      end
    end
    res.(sprintf('M%d', M)) = struct( ...
        'r_mod', mean(r_mod), 'r_deep', mean(r_deep), ...
        'p1_mod', mean(p1_mod), 'p1_deep', mean(p1_deep));
  end

  fprintf('\n    %3s %7s | %16s %15s %12s %9s\n', 'M', 'F', ...
          '联合衰落率(实测)', 'p1^M(实测外推)', 'p^M(理论)', '实测/外推');
  for mi = 1:numel(Ms)
    M = Ms(mi);
    r = res.(sprintf('M%d', M));
    tags = {'mod', 'deep'};
    Fv = [F_MOD, F_DEEP];
    pth = [p_mod, p_deep];
    for ti = 1:2
      rm = r.(['r_' tags{ti}]);
      p1 = r.(['p1_' tags{ti}]);
      if p1 ^ M > 0
        ratio = rm / p1 ^ M;
      else
        ratio = NaN;
      end
      fprintf('    %3d %7.4f | %16.3e %15.3e %12.3e %9.2f\n', ...
              M, Fv(ti), rm, p1 ^ M, pth(ti) ^ M, ratio);
    end
  end

  p1_meas = res.M4.p1_mod;
  p1d_meas = res.M4.p1_deep;
  check('Q0-1', '单路衰落率符合 Rayleigh 理论 (两个门限, M=4 组, ±10%)', ...
        abs(p1_meas / p_mod - 1) < 0.10 && abs(p1d_meas / p_deep - 1) < 0.10, ...
        sprintf('F=%g: %.4f vs %.4f; F=%g: %.4f vs %.4f', ...
                F_MOD, p1_meas, p_mod, F_DEEP, p1d_meas, p_deep));
  r3 = res.M3.r_mod / res.M3.p1_mod ^ 3;
  check('Q0-2', 'M=3 联合衰落率 ~ p^3 (F=-4.5dB, 比值 0.7..1.4)', ...
        0.7 < r3 && r3 < 1.4, sprintf('实测/p1^3 = %.2f', r3));
  r4 = res.M4.r_mod / res.M4.p1_mod ^ 4;
  check('Q0-3', 'M=4 联合衰落率 ~ p^4 (F=-4.5dB, 比值 0.6..1.7)', ...
        0.6 < r4 && r4 < 1.7, sprintf('实测/p1^4 = %.2f', r4));
  r3d = res.M3.r_deep / res.M3.p1_deep ^ 3;
  check('Q0-4', 'M=3 深衰落 (-9.8dB) 联合率 ~ p^3 (比值 0.4..2.2, 事件较少)', ...
        0.4 < r3d && r3d < 2.2, sprintf('实测/p1^3 = %.2f', r3d));
  fprintf(['  [info] M=4 深衰落联合率实测 %.2e (理论 p^4 = %.2e; ' ...
           '本时长下事件过少, 只作参考不断言)\n'], ...
          res.M4.r_deep, p_deep ^ 4);

  % correlated channels: the rho machinery itself
  corr_acc = zeros(3, 1);
  enh_acc = zeros(3, 1);
  for s = 0:2
    set_rng(43000 + s);
    h = make_speckle_multi(N, fs_stat, tau_c, 3, 0.5);
    Cm = real(channel_correlation(h));
    mask = triu(true(3), 1);
    corr_acc(s + 1) = mean(Cm(mask));
    p1 = mean([joint_fade_fraction(h(1, :), F_MOD), ...
               joint_fade_fraction(h(2, :), F_MOD), ...
               joint_fade_fraction(h(3, :), F_MOD)]);
    enh_acc(s + 1) = joint_fade_fraction(h, F_MOD) / p1 ^ 3;
  end
  corr_m = mean(corr_acc);
  enh_m = mean(enh_acc);
  check('Q0-5', ['rho=0.5: 实测场相关 0.4..0.6 且联合衰落率显著高于独立外推 ' ...
        '(>1.3x)'], 0.4 < corr_m && corr_m < 0.6 && enh_m > 1.3, ...
        sprintf('corr=%.3f, 联合率/独立外推 = %.2fx', corr_m, enh_m));
  fprintf(['  物理结论: 独立通道联合深衰落 ~ p^M -- 分集接收把掉光概率指数压低;' ...
           ' 通道相关 (rho>0) 会侵蚀该增益, 故 P1 用 rho=0 做上限 baseline.\n']);
end


% ================================================================== P1
function agg = P1()
  global VQTC
  P = VQTC.P;
  FS = P.FS;
  nseed = 10;
  cnr_db = 6.0;
  M = 3;
  tau_c = 50e-6;
  VAMP = 20e-3;
  T = 5e-4;
  N = floor(T * FS);
  t = (0:N - 1)' / FS;
  f0 = 3e6;
  ncyc = 60;
  t0 = 0.05e-3;
  [x, v_true, ~] = burst_signal(t, f0, VAMP, ncyc, t0);
  phi = doppler_phase(x);
  Tb = ncyc / f0;
  Wm = (t > t0) & (t < t0 + Tb);
  Wq = (t > t0 + Tb + 0.04e-3) & (t < 0.48e-3);
  band = hd_select_band(f0, VAMP);
  s2 = 10.0 ^ (-cnr_db / 10.0);
  thr = 20 * VAMP;
  a0 = lockin_amp(v_true, t, f0, Wm);
  alphas = [1.0, 2.0, Inf];
  anames = {'1', '2', 'inf'};
  print_header(sprintf(['P1  非相干 SNR 加权速度域合成 (M=%d, 每路平均 CNR=' ...
      '%.0fdB, tau_c=%.0fus, gear=%s, B_noise=20MHz, 3MHz burst, %d seeds)'], ...
      M, cnr_db, tau_c * 1e6, band, nseed));
  fprintf(['  每路: pll_carrier_regen + 公共残差窗 (gear_filter 全输出路径) ' ...
           '+ FM 鉴频; 块长 2us, rel_x=0.05\n  对照: 每 seed 每指标取最优单路 ' ...
           '(oracle, 比任何真实单路仪器更强的 baseline)\n']);

  % -- 幅值传递 (R1: 近无噪 CNR=60dB + 散斑, 权重照常工作, 4 seeds) --
  fprintf('\n  -- 幅值传递 (R1: 近无噪 CNR=60dB + 散斑, 权重照常工作, 4 seeds) --\n');
  amp_clean = cell(1, 3);
  s2c = 10.0 ^ (-60.0 / 10.0);
  for s = 0:3
    set_rng(48000 + s);
    syn = synth_multichannel(phi, FS, M, 60.0, 'tau_c', tau_c, ...
                             'B_noise', 20e6);
    chans = cell(1, M);
    for k = 1:M
      chans{k} = channel_demod(syn.z(k, :), FS, band, s2c);
    end
    for ai = 1:3
      res = diversity_combine(syn.z, FS, 'band', band, 'Nhat', s2c, ...
                              'alpha', alphas(ai), 'chans', chans);
      amp_clean{ai}(end + 1) = amp_err_pct(res.v, t, f0, Wm, a0);
    end
  end
  for ai = 1:3
    [m, lo, hi] = stats(amp_clean{ai});
    fprintf('    alpha=%-4s burst 幅值误差 %+6.2f%%  [%+.2f,%+.2f]\n', ...
            anames{ai}, m, lo, hi);
  end

  agg = struct('ch_spk', [], 'ch_asd', [], 'ch_unlock', [], ...
               'best_spk', [], 'best_asd', [], 'best_unlock', [], ...
               'joint_unlock', []);
  for ai = 1:3
    agg.(['spk_a' anames{ai}]) = [];
    agg.(['gain_a' anames{ai}]) = [];
    agg.(['dark_a' anames{ai}]) = [];
  end
  for s = 0:nseed - 1
    set_rng(50000 + s);
    syn = synth_multichannel(phi, FS, M, cnr_db, 'tau_c', tau_c, ...
                             'B_noise', 20e6);
    chans = cell(1, M);
    spk = zeros(1, M);
    asd = zeros(1, M);
    unl = zeros(1, M);
    st = zeros(M, N);
    for k = 1:M
      chans{k} = channel_demod(syn.z(k, :), FS, band, s2);
      spk(k) = spike_count(chans{k}.v, Wq, thr, FS);
      asd(k) = asd_q(chans{k}.v, Wq, f0, FS);
      unl(k) = mean(chans{k}.state ~= 2);
      st(k, :) = chans{k}.state.';
    end
    agg.ch_spk = [agg.ch_spk, spk];
    agg.ch_asd = [agg.ch_asd, asd];
    agg.ch_unlock = [agg.ch_unlock, unl];
    agg.best_spk(end + 1) = min(spk);
    agg.best_asd(end + 1) = min(asd);
    agg.best_unlock(end + 1) = min(unl);
    agg.joint_unlock(end + 1) = mean(all(st ~= 2, 1));
    for ai = 1:3
      res = diversity_combine(syn.z, FS, 'band', band, 'Nhat', s2, ...
                              'alpha', alphas(ai), 'chans', chans);
      agg.(['spk_a' anames{ai}])(end + 1) = spike_count(res.v, Wq, thr, FS);
      agg.(['gain_a' anames{ai}])(end + 1) = ...
          20.0 * log10(min(asd) / asd_q(res.v, Wq, f0, FS));
      agg.(['dark_a' anames{ai}])(end + 1) = res.dark_frac;
    end
  end

  fprintf('\n  -- 单路 (所有通道合并) 与最优单路 (per-seed oracle) --\n');
  print_row('单路 velocity spikes (>0.4m/s)', agg.ch_spk, '%8.1f');
  print_row('最优单路 spikes', agg.best_spk, '%8.1f');
  print_row('单路失锁时间 %', 100 * agg.ch_unlock, '%8.1f');
  print_row('最优单路失锁 %', 100 * agg.best_unlock, '%8.1f');
  print_row('全通道同时失锁 (联合) %', 100 * agg.joint_unlock, '%8.2f');
  print_row('单路速度ASD @3MHz (um/s/rtHz)', 1e6 * agg.ch_asd, '%8.1f');
  print_row('最优单路 ASD (um/s/rtHz)', 1e6 * agg.best_asd, '%8.1f');
  fprintf('\n  -- 合成输出 (中值 [p10,p90]) --\n');
  fprintf('    %-8s %16s %22s %12s\n', 'alpha', 'spikes', ...
          'SNRgain vs 最优单路', '全暗HOLD %');
  for ai = 1:3
    [sm, sl, sh] = stats(agg.(['spk_a' anames{ai}]));
    [gm, gl, gh] = stats(agg.(['gain_a' anames{ai}]));
    dm = stats(100 * agg.(['dark_a' anames{ai}]));
    fprintf('    %-8s %7.1f [%3.0f,%4.0f] %+11.2f [%+5.2f,%+5.2f] dB %11.2f\n', ...
            anames{ai}, sm, sl, sh, gm, gl, gh, dm);
  end

  best_spk_med = stats(agg.best_spk);
  spk2_med = stats(agg.spk_a2);
  check('Q1-1', '合成(α=2, 推荐默认) 速度尖峰中值 <= 0.6x 最优单路 (掉落抑制)', ...
        spk2_med <= 0.6 * best_spk_med, ...
        sprintf('%.0f vs 最优单路 %.0f', spk2_med, best_spk_med));
  g2_med = stats(agg.gain_a2);
  check('Q1-2', '合成(α=2) 静默段速度ASD SNR增益 vs 最优单路 > +2 dB', ...
        g2_med > 2.0, sprintf(['%+.2f dB (α=1 速度域MRC: %+.2f dB; ' ...
        '理想等权上限 %.1f dB)'], g2_med, stats(agg.gain_a1), ...
        10 * log10(M)));
  dark_med = stats(agg.dark_a2);
  unlock_med = stats(agg.best_unlock);
  check('Q1-3', '合成 全暗HOLD时间 <= 0.5x 最优单路失锁时间 (可用性)', ...
        dark_med <= 0.5 * unlock_med, ...
        sprintf('%.2f%% vs 最优单路失锁 %.2f%%', ...
                100 * dark_med, 100 * unlock_med));
  worst = max([stats(agg.spk_a1), stats(agg.spk_a2), stats(agg.spk_ainf)]);
  check('Q1-4', '全部 α∈{1,2,∞} 的合成尖峰中值均 <= 最优单路 (权重律稳健)', ...
        worst <= best_spk_med, ...
        sprintf('最差 α 的中值 %.0f vs %.0f', worst, best_spk_med));
  amp_worst = max(abs([stats(amp_clean{1}), stats(amp_clean{2})]));
  check('Q1-5', ['加权和无系统性幅值偏置: R1 近无噪+散斑 burst 幅值误差 ' ...
        '|中值| < 5% (α=1,2)'], amp_worst < 5.0, ...
        sprintf('worst |err| = %.2f%%', amp_worst));
  g2_m = stats(agg.gain_a2);
  ginf_m = stats(agg.gain_ainf);
  fprintf(['\n  诚实说明: 速度域非相干合成不改变单路 FM 门限本身, 它买到的是' ...
           ' (a) 联合掉光率 ~p^M,\n  (b) 静默段噪声按权重平均下降, (c) 尖峰只在' ...
           '全通道同弱时出现. 更低 CNR 的门限扩展\n  需要 IQ 域相干合成 (P2 路线).' ...
           ' α=1 为速度域 MRC (平稳噪声方差最优) 但对非高斯 click\n  尖峰欠抑制;' ...
           ' α=∞ 纯选路尖峰最少但放弃平均增益 (%+.1f dB vs α=2); α=2 为推荐默认折中.' ...
           '\n  CNR=6dB 下 burst 幅值在单 seed 上被 FM 噪声主导 (R1 规则),' ...
           ' 故幅值无偏性在近无噪+散斑运行中断言.\n'], ginf_m - g2_m);
end


function n = spike_count(v, Wq, thr, FS)
  vlp = fir_lp_same(v(:), 1e6, FS, 2049);
  ex = abs(vlp(Wq)) > thr;
  n = sum(diff(double([false; ex])) == 1);
end

function a = asd_q(v, Wq, f0, FS)
  v = v(:);
  [Pw, f] = welch_psd(v(Wq), FS, 4096);
  m = abs(f - f0) < 150e3;
  a = sqrt(median(Pw(m)));
end

function e = amp_err_pct(v, t, f0, Wm, a0)
  e = 100.0 * (lockin_amp(v(:), t, f0, Wm) / a0 - 1.0);
end

function print_row(label, vals, fmt)
  [m, lo, hi] = stats(vals);
  fprintf(['    %-34s', fmt, '  [', fmt, ',', fmt, ']\n'], label, m, lo, hi);
end
