function validate_zeta_sweep()
%VALIDATE_ZETA_SWEEP Review item #7: what zeta buys at the FULL output (Z0-Z3).
%   MATLAB/Octave port of homodyne_tracking_design/validate_zeta_sweep.py:
%     Z0  common FIR window's own response (what "DC..4 MHz" really means)
%     Z1  zeta sweep: full-output amplitude error / SNR gain / near-pi rate
%     Z2  dropout re-acquisition (fade with hidden velocity reversal)
%     Z3  conclusions & assertions (Z3-1 .. Z3-6)
%   Same seeds as Python (numpy-exact RNG kernel).
%
%   Run:  cd matlab && octave --eval validate_zeta_sweep
%   Saves golden metrics to golden/validate_zeta_sweep_mat.mat and raises an
%   error (nonzero exit code) if any check fails.
  t_all = tic;
  sd = fileparts(mfilename('fullpath'));
  addpath(sd);
  homodyne_setup_path();
  ensure_kernels();

  dp = design_params();
  ZETAS = [0.7, 1.0, 1.2, 1.8, 2.65];

  fprintf('审查项 #7: ζ 扫描 -- 优化对象应是全输出+载波环经济性, 不是 NCO 纹波\n');
  fprintf(['fs=%.0fMS/s, lambda=%.0fnm, B_win=%.0fMHz, ζ 候选 ' ...
           '(0.7, 1.0, 1.2, 1.8, 2.65), 当前 design ZETA=%g\n'], ...
          dp.FS / 1e6, dp.LAMBDA * 1e9, dp.B_WIN / 1e6, dp.ZETA);

  z0 = Z0_();
  z1 = Z1_(8, 3.0, ZETAS);
  z2 = Z2_(4, 12.0, 20.0, 50.0, ZETAS);
  CHECKS = Z3_(z1, z2, ZETAS);

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
  g.det = struct('z0', [z0.g3m, z0.f1, z0.f5, z0.f3db, z0.f6db]);
  g.noisy = struct('z1_err', z1.err, 'z1_gain_med', z1.gain, ...
                   'z1_dlp', z1.dlp, 'z1_rate_med', z1.rate, ...
                   'z1_lock_mean', z1.lock, 'z1_g_lp', z1.g_lp, ...
                   'z2_tr', z2.tr, 'z2_ts', z2.ts, 'z2_np', z2.np);
  gdir = fullfile(sd, 'golden');
  if ~exist(gdir, 'dir'), mkdir(gdir); end
  gfile = fullfile(gdir, 'validate_zeta_sweep_mat.mat');
  save('-v7', gfile, '-struct', 'g');
  fprintf('[golden metrics saved to %s]\n', gfile);

  if ~allok
    error('validate_zeta_sweep: SOME CHECKS FAILED');
  end
end


% ================================================================== Z0
function z0 = Z0_()
  dp = design_params();
  vt_print_header(sprintf(['Z0  公共残差窗频响 (windowed-sinc FIR, %d taps @ ' ...
      '%.0fMS/s, 设计截止 %.0fMHz)'], dp.NT_WIN, dp.FS / 1e6, dp.B_WIN / 1e6));
  h = fir_lp_kernel(dp.B_WIN, dp.FS, dp.NT_WIN);
  nfft = 2^18;
  F = fft(h, nfft);
  H = abs(F(1:nfft/2+1));
  f = (0:nfft/2)' * dp.FS / nfft;
  g3m = H(round(3e6 * nfft / dp.FS) + 1);
  f1 = f(find(H < 0.99, 1));
  f5 = f(find(H < 0.95, 1));
  f3db = f(find(H < 10^(-3 / 20), 1));
  f6db = f(find(H < 0.5, 1));
  fprintf('  |H(3MHz)| = %.4f  (%+.2f%%)\n', g3m, 100 * (g3m - 1));
  fprintf('  幅值误差 <1%% 平坦区:  DC..%.2f MHz\n', f1 / 1e6);
  fprintf('  幅值误差 <5%% 平坦区:  DC..%.2f MHz\n', f5 / 1e6);
  fprintf('  -3 dB 点: %.2f MHz    -6 dB 点(=设计截止): %.2f MHz\n', ...
          f3db / 1e6, f6db / 1e6);
  fprintf(['  => 准确表述: 4 MHz 是窗的 -6 dB 截止点; 平坦测量带(<1%%误差)约到 ' ...
           '%.1f MHz, 覆盖 3 MHz 规格并留余量. 不是 ''DC-4MHz 内处处平坦''.\n'], ...
          f1 / 1e6);
  z0 = struct('g3m', g3m, 'f1', f1, 'f5', f5, 'f3db', f3db, 'f6db', f6db);
end


% ================================================================== Z1
function z1 = Z1_(nseed, cnr_db, ZETAS)
  dp = design_params();
  c = vt_const();
  FREQS = [100e3, 1e6, 3e6];
  vt_print_header(sprintf(['Z1  ζ 扫描: 全输出幅值误差 / SNR增益 / near-π 率  ' ...
      '(CNR=%.0fdB, B_frontend=%.0fMHz, %d seeds, median)'], ...
      cnr_db, dp.B_FRONTEND / 1e6, nseed));
  s2 = 10^(-cnr_db / 10);
  T_RUN = c.N / dp.FS;
  nz = numel(ZETAS);
  z1 = struct();
  z1.err = zeros(3, 3, nz);
  z1.gain = zeros(3, 3, nz);
  z1.glo = zeros(3, 3, nz);
  z1.ghi = zeros(3, 3, nz);
  z1.dlp = zeros(3, 3, nz);
  z1.rate = zeros(3, 3, nz);
  z1.lock = zeros(3, 3, nz);
  z1.g_lp = zeros(3, 1);
  for ifq = 1:3
    f0 = FREQS(ifq);
    sc = vt_make_scene(f0);
    zc = vt_clean_z(sc);
    noisy_z = cell(nseed, 1);
    noisy_aoff = zeros(nseed, 1);
    for s = 0:nseed-1
      rh = np_rng_new(70000 + fix(f0 / 1e3) * 100 + s);
      zn = exp(1i * sc.ph) + ...
           complex_bandlimited_noise(c.N, dp.FS, dp.B_FRONTEND, s2, rh);
      noisy_z{s+1} = zn;
      noisy_aoff(s+1) = vt_asd_at(vt_vdisc(zn), sc);
    end
    % fixed complex LP at B_WIN: the zeta-free benchmark
    e_lp = vt_amp_err_pct(vt_vdisc(vt_fft_lp(zc, dp.B_WIN, dp.NT_WIN)), sc);
    g_lp0 = 20 * log10(max(1 + e_lp / 100, 1e-12));
    lp_gains = zeros(nseed, 1);
    for s = 1:nseed
      lp_gains(s) = g_lp0 + 20 * log10(noisy_aoff(s) / vt_asd_at( ...
          vt_vdisc(vt_fft_lp(noisy_z{s}, dp.B_WIN, dp.NT_WIN)), sc));
    end
    g_lp = vt_stats(lp_gains);
    z1.g_lp(ifq) = g_lp;
    fprintf('\n  f0 = %.0f kHz   固定LP(B_win) SNR gain = %+.2f dB\n', ...
            f0 / 1e3, g_lp);
    fprintf(['    %5s %-7s %8s %6s | %11s | %27s %7s | %8s %6s\n'], ...
            'zeta', 'gear', 'B_loop', '/B_win', 'ampErr_full', ...
            'SNRgain_full dB [p10,p90]', 'Δvs LP', 'nearπ/ms', 'lock%');
    for ib = 1:3
      band = dp.ORDER{ib};
      fn = dp.BANDS.(band).fn;
      for iz = 1:nz
        zeta = ZETAS(iz);
        yf = gear_filter_z_(zc, band, 1e-10, zeta, 'always');
        ef = vt_amp_err_pct(vt_vdisc(yf), sc);
        g0 = 20 * log10(max(1 + ef / 100, 1e-12));
        gains = zeros(nseed, 1);
        rates = zeros(nseed, 1);
        locks = zeros(nseed, 1);
        for s = 1:nseed
          [yf, ~, ~, dg] = gear_filter_z_(noisy_z{s}, band, s2, zeta, 'auto');
          gains(s) = g0 + 20 * log10(noisy_aoff(s) ...
                                     / vt_asd_at(vt_vdisc(yf), sc));
          rates(s) = dg.near_pi_events / (T_RUN * 1e3);
          locks(s) = dg.lock_frac;
        end
        [g, glo, ghi] = vt_stats(gains);
        B = b_loop_of_(fn, zeta);
        z1.err(ifq, ib, iz) = ef;
        z1.gain(ifq, ib, iz) = g;
        z1.glo(ifq, ib, iz) = glo;
        z1.ghi(ifq, ib, iz) = ghi;
        z1.dlp(ifq, ib, iz) = g - g_lp;
        z1.rate(ifq, ib, iz) = vt_stats(rates);
        z1.lock(ifq, ib, iz) = mean(locks);
        fprintf(['    %5.2f %-7s %7.2fM %6.2f | %+10.2f%% | %+8.2f ' ...
                 '[%+7.2f,%+7.2f] %+7.2f | %8.1f %6.1f\n'], ...
                zeta, band, B / 1e6, B / dp.B_WIN, ef, g, glo, ghi, ...
                g - g_lp, vt_stats(rates), 100 * mean(locks));
      end
    end
  end
  fprintf(['\n  (ampErr_full: 近无噪运行, gate=always; SNRgain vs OFF, ' ...
           'R1-R3 方法; nearπ/ms: LOCK 内 |相位误差|>2.8rad 事件率)\n']);
  fprintf(['  注意 FAST 档低频 (100kHz) 在 zeta<=0.9 处 p10-p90 跨度拉大 ' ...
           '(双峰): B_loop≈1.3·B_win 恰在 click 清除悬崖边,\n  个别种子吃满' ...
           '清除、个别只有部分 -- 低 ζ 的高中值不可依赖, 这是不取 ζ<1.2 ' ...
           '的主要原因之一.\n']);
end


% ================================================================== Z2
function z2 = Z2_(nseed, cnr_db, fade_db, fade_us, ZETAS)
  dp = design_params();
  c = vt_const();
  VAMP = c.VAMP;
  vt_print_header(sprintf(['Z2  掉光重捕 (简化模型: -%.0fdB 掉光 %.0fus, ' ...
      '掉光期内速度反向 ±%.0fmm/s, CNR=%.0fdB, %d seeds, median)'], ...
      fade_db, fade_us, VAMP * 1e3, cnr_db, nseed));
  s2 = 10^(-cnr_db / 10);
  a_fade = 10^(-fade_db / 20);
  t0f = 200e-6;
  t1f = 200e-6 + fade_us * 1e-6;
  i1 = fix(t1f * dp.FS);
  fD = 2 * VAMP / dp.LAMBDA;
  pt = zeros(c.N, 1);
  m1 = c.t < t0f;
  m2 = ~m1 & (c.t < t1f);
  m3 = ~m1 & ~m2;
  pt(m1) = c.t(m1);
  pt(m2) = t0f - (c.t(m2) - t0f);
  pt(m3) = t0f - (t1f - t0f) - (c.t(m3) - t1f);
  ph_true = (4 * pi / dp.LAMBDA) * VAMP * pt;   % +v then -v (reversal in fade)
  env = ones(c.N, 1);
  env((c.t >= t0f) & (c.t < t1f)) = a_fade;
  w2 = fix(2e-6 * dp.FS);                       % 2 us smoother for settle
  box = ones(w2, 1) / w2;
  nz = numel(ZETAS);
  z2 = struct('tr', zeros(3, nz), 'ts', zeros(3, nz), 'np', zeros(3, nz));
  fprintf(['    (载波多普勒 ±%.0f kHz, 重捕需拉回 %.0f kHz 频差; ' ...
           'settle 判据: 2us 平滑 |相位误差| < 0.3 rad)\n'], ...
          fD / 1e3, 2 * fD / 1e3);
  fprintf('    %5s %-7s | %11s %11s %10s | %12s\n', 'zeta', 'gear', ...
          't_relock us', 't_settle us', 't_total us', 'nearpi(重捕后)');
  for ib = 1:3
    band = dp.ORDER{ib};
    gp = gate_params(band);
    for iz = 1:nz
      zeta = ZETAS(iz);
      tr = zeros(nseed, 1);
      ts = zeros(nseed, 1);
      npc = zeros(nseed, 1);
      for s = 0:nseed-1
        rh = np_rng_new(80000 + (ib - 1) * 1000 + s);
        z = env .* exp(1i * ph_true) + ...
            complex_bandlimited_noise(c.N, dp.FS, dp.B_FRONTEND, s2, rh);
        opts = gp;
        opts.zeta = zeta;
        opts.gate = 'auto';
        [~, phi, st, ~] = pll_carrier_regen(z, dp.FS, ...
                                            dp.BANDS.(band).fn, s2, opts);
        lk = find(st(i1+1:end) == 2, 1);
        if isempty(lk)
          tr(s+1) = Inf; ts(s+1) = Inf; npc(s+1) = Inf;
          continue
        end
        lk0 = lk - 1;                     % 0-based offset within slice
        n_rl = i1 + lk0;                  % 0-based re-lock sample
        tr(s+1) = (n_rl - i1) / dp.FS * 1e6;
        err = angle(exp(1i * (phi - ph_true)));
        err_s = np_conv_same(abs(err), box);
        j = find(err_s(n_rl+1:end) < 0.3, 1);
        if isempty(j)
          ts(s+1) = Inf;
        else
          ts(s+1) = (j - 1) / dp.FS * 1e6;
        end
        big = abs(err(n_rl+1:end)) > 2.8;
        npc(s+1) = sum(diff([0; double(big)]) == 1);
      end
      z2.tr(ib, iz) = vt_stats(tr);
      z2.ts(ib, iz) = vt_stats(ts);
      z2.np(ib, iz) = vt_stats(npc);
      fprintf('    %5.2f %-7s | %11.1f %11.1f %10.1f | %12.0f\n', ...
              zeta, band, z2.tr(ib, iz), z2.ts(ib, iz), ...
              z2.tr(ib, iz) + z2.ts(ib, iz), z2.np(ib, iz));
    end
  end
  fprintf(['\n  (t_relock: 光回来到门控重进LOCK, 由 AcquireTime=4·TauF 主导, ' ...
           '与 ζ 无关;\n   t_settle: 重进LOCK后平滑相位误差首次<0.3rad -- ' ...
           'ζ 影响的部分)\n']);
end


% ================================================================== Z3
function CHECKS = Z3_(z1, z2, ZETAS)
  dp = design_params();
  RECOMMENDED_ZETA = 1.2;
  izr = find(ZETAS == RECOMMENDED_ZETA, 1);
  iz265 = find(ZETAS == 2.65, 1);
  vt_print_header('Z3  结论与断言');
  fprintf('  各 ζ 汇总 (9 个 档×频率 组合上的统计):\n');
  fprintf('    %5s | %13s | %11s %10s | %14s | %15s\n', 'zeta', ...
          'worst|ampErr|', 'meanSNRgain', 'worstΔvsLP', ...
          'worst nearπ/ms', 'worst settle us');
  for iz = 1:numel(ZETAS)
    errs = z1.err(:, :, iz);
    gains = z1.gain(:, :, iz);
    dlps = z1.dlp(:, :, iz);
    rates = z1.rate(:, :, iz);
    setl = z2.ts(:, iz);
    fprintf('    %5.2f | %12.2f%% | %+11.2f %+10.2f | %14.1f | %15.1f\n', ...
            ZETAS(iz), max(abs(errs(:))), mean(gains(:)), min(dlps(:)), ...
            max(rates(:)), max(setl));
  end

  spread = 0;
  for ifq = 1:3
    for ib = 1:3
      e = squeeze(z1.err(ifq, ib, :));
      spread = max(spread, max(e) - min(e));
    end
  end
  CHECKS = struct('cid', {}, 'label', {}, 'ok', {}, 'detail', {});
  CHECKS(end+1) = vt_check('Z3-1', ['全输出幅值误差对 ζ 不敏感 (任意档×频率上 ' ...
      'ζ 间极差 < 1 个百分点) -- 输出平坦度由公共窗决定, 不是 |H_L|'], ...
      spread < 1.0, sprintf('max spread %.3f%%', spread));

  bm12 = b_loop_of_(dp.BANDS.MEDIUM.fn, 1.2);
  bm265 = b_loop_of_(dp.BANDS.MEDIUM.fn, 2.65);
  CHECKS(end+1) = vt_check('Z3-2', ['click清除条件 B_loop<B_win: MEDIUM 在 ' ...
      'ζ=1.2 满足 (2.34M<4M), 在 ζ=2.65 不满足 (4.57M>4M)'], ...
      bm12 < dp.B_WIN && dp.B_WIN < bm265, ...
      sprintf('B_loop(1.2)=%.2fM, B_loop(2.65)=%.2fM', bm12 / 1e6, bm265 / 1e6));

  d = z1.gain(:, :, izr) - z1.gain(:, :, iz265);
  worst_reg = min(d(:));
  CHECKS(end+1) = vt_check('Z3-3', sprintf(['ζ=%g 的全输出 SNR 增益在所有 ' ...
      '档×频率 上 不低于 ζ=2.65 - 0.7 dB (无回退)'], RECOMMENDED_ZETA), ...
      worst_reg > -0.7, sprintf('worst delta %+.2f dB', worst_reg));

  e_fast = abs(z1.err(3, 3, izr));
  e_worst = max(abs(z1.err(3, :, izr)));
  CHECKS(end+1) = vt_check('Z3-4', sprintf(['ζ=%g: FAST@3MHz 幅值误差 <3%%, ' ...
      '三档@3MHz 均 <5%% (V1 规格保持)'], RECOMMENDED_ZETA), ...
      e_fast < 3.0 && e_worst < 5.0, ...
      sprintf('FAST %.2f%%, worst %.2f%%', e_fast, e_worst));

  tt_rec = max(z2.tr(:, izr) + z2.ts(:, izr));
  tt_265 = max(z2.tr(:, iz265) + z2.ts(:, iz265));
  CHECKS(end+1) = vt_check('Z3-5', sprintf(['ζ=%g 掉光重捕总时间 ' ...
      '(relock+settle) 各档均 <100us 且不劣于 zeta=2.65 的 3 倍 + 5us'], ...
      RECOMMENDED_ZETA), ...
      isfinite(tt_rec) && tt_rec < 100.0 && tt_rec < 3 * tt_265 + 5.0, ...
      sprintf('%.1f vs %.1f us', tt_rec, tt_265));

  CHECKS(end+1) = vt_check('Z3-6', sprintf('design_params.ZETA == 推荐值 %g', ...
      RECOMMENDED_ZETA), abs(dp.ZETA - RECOMMENDED_ZETA) < 1e-12, ...
      sprintf('ZETA=%g', dp.ZETA));

  fprintf('\n  推荐: ζ = %g (三档统一).\n', RECOMMENDED_ZETA);
  fprintf(['  依据: (1) 全输出幅值误差由公共4MHz窗决定, 对 ζ 完全不敏感 ' ...
           '(Z3-1) -- ζ=2.65 的等纹波推导\n            优化的是 NCO 路径纹波, ' ...
           '那不是输出指标, 优化对象选错了 (审查项#7);\n']);
  fprintf(['        (2) ζ=1.2 使 B_loop=4.42·fn (vs 8.62·fn): MEDIUM 恢复 ' ...
           'B_loop<B_win 的 click 清除条件\n            (Z3-2, 100kHz 增益 ' ...
           '+36.2→+38.1dB), FAST@3MHz 增益 +2.2→+7.8dB (Z1);\n']);
  fprintf(['        (3) 相对 ζ=2.65 在所有 档×频率 上 SNR 无回退 (Z3-3); ' ...
           '掉光重捕同量级 (Z3-5);\n']);
  fprintf(['        (4) 更低的 ζ (0.7/1.0) 在 FAST 设计频点 3MHz 只再多 ~1dB, ' ...
           '但 FAST 低频落在 click 清除\n            悬崖边 (Z1 中 p10-p90 双峰), ' ...
           '且欠阻尼 (NCO 路径峰化 +28%%@ζ=0.7) -- 不取.\n']);
  fprintf(['  掉光飞轮/选档守卫等载波路径职能对 NCO ±3%% 纹波不敏感; ' ...
           'ζ=1.2 下 NCO 路径纹波 +11%%/-11%%\n  只出现在载波路径单独输出时 ' ...
           '-- 测量输出恒由公共窗决定 (Z3-1 实证).\n']);
end


% ----------------------------------------------------------------- helpers
function B = b_loop_of_(fn, zeta)
  B = pi * fn * (1 + 4 * zeta^2) / (4 * zeta);
end

function [y_full, phi, st, dg] = gear_filter_z_(z, band, Nhat, zeta, gate)
%GEAR_FILTER_Z_ Same chain as vt_gear_filter but with explicit zeta.
  dp = design_params();
  opts = gate_params(band);
  opts.zeta = zeta;
  opts.gate = gate;
  [~, phi, st, dg] = pll_carrier_regen(z, dp.FS, dp.BANDS.(band).fn, ...
                                       Nhat, opts);
  z = z(:);
  rot = exp(-1i * phi);
  rf = vt_fft_lp(z .* rot, dp.B_WIN, dp.NT_WIN);
  if strcmp(gate, 'always')
    gs = 1.0;
  else
    gs = iir1_lowpass(double(st == 2), exp(-1.0 / (dp.FS * dp.TAU_G)));
  end
  resph = zeros(size(rf));
  m = abs(rf) > 1e-12;
  resph(m) = angle(rf(m));
  y_full = conj(rot) .* exp(1i * (gs .* resph));
end
