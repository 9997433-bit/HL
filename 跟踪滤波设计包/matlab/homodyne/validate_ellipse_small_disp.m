function rc = validate_ellipse_small_disp(cnr_db)
%VALIDATE_ELLIPSE_SMALL_DISP Homodyne IQ small-displacement ellipse validation (B0-B4).
%   rc = validate_ellipse_small_disp()          % front-end CNR = 20 dB
%   rc = validate_ellipse_small_disp(cnr_db)
%   MATLAB/Octave port of validate_ellipse_small_disp.py with the same
%   scenarios (numpy-exact RNG kernel), methods and PASS criterion:
%     B0  OFF             angle(u + j*v) directly, no correction
%     B1  sliding demean  window swept, best window as baseline
%     B2  static Heydemann (first 0.4 s calibration)
%     B3  segmented-arc Heydemann (0.5 s segments, +-2% amplitude gate)
%     B4  B3 + SLOW-gear tracking filter (fn=110 kHz, zeta=design_params)
%   Assertion (spec): at A=100 nm, f=100 Hz the best corrected method must
%   beat best-window B1 by >10 dB line SNR OR reduce RMS error by >3x.
%   Saves golden metrics to golden/validate_ellipse_small_disp_mat.mat and
%   returns rc = 0 iff the assertion holds.
  if nargin < 1 || isempty(cnr_db), cnr_db = 20.0; end
  t_start = tic;
  sd = fileparts(mfilename('fullpath'));          % matlab/homodyne
  addpath(fileparts(sd));                         % matlab/ (homodyne_setup_path)
  homodyne_setup_path();
  ensure_kernels();
  k = sd_const_();
  dp = design_params();

  fprintf('%s\n', repmat('=', 1, 78));
  fprintf('零差 IQ 小位移椭圆校正验证  (B0-B4, 软件方案对比, 硬件不可改)\n');
  fprintf('%s\n', repmat('=', 1, 78));
  fprintf(['lambda = %.0f nm | 名义 fs = %.0f MS/s, 仿真在 /%d 降采样 = ' ...
           '%.1f MS/s, 记录 %.1f s\n'], k.LAMBDA * 1e9, k.FS_FULL / 1e6, ...
          k.DECIM, k.FS / 1e6, k.T_REC);
  fprintf(['椭圆真值(慢漂): eps %+.0f%% → %+.0f%%, delta %.0f° → %.0f°, ' ...
           '偏置 p=%g(+%g漂移) q=%g, 回光幅度 ±%.0f%% 慢漂\n'], ...
          k.EPS_T0 * 100, k.EPS_T1 * 100, k.DEL_T0, k.DEL_T1, k.P_OFF0, ...
          k.P_DRIFT, k.Q_OFF, k.R_SWING * 100);
  fprintf('工作点漂移: %.1f 条纹/s 线性 + %.1f rad 平滑游走\n', ...
          k.FRINGE_RATE, k.PSI_WANDER);
  fprintf(['噪声: 复高斯, 前端 CNR = %.0f dB @250 MS/s (降采样后 %.0f dB)\n'], ...
          cnr_db, cnr_db + 20);
  fprintf(['指标评估: t∈[%g,%g) s, 降到 %.0f kS/s; 谱线SNR = |f-f0|≤%.0f Hz ' ...
           '带功率 / %.0f–%.0f Hz 偏移底板 (全段Hann周期图)\n\n'], k.T_TRIM, ...
          k.T_REC - k.T_TRIM, k.FS2 / 1e3, k.SNR_SIG_HZ, ...
          k.SNR_FLOOR_HZ(1), k.SNR_FLOOR_HZ(2));
  fprintf(['方法: B0 OFF=angle(z) | B1 滑动去均值(窗扫描, 取最优窗) | ' ...
           'B2 静态Heydemann(前0.4 s标定)\n']);
  fprintf(['      B3 分段弧Heydemann(段长%gs, 幅度门±%.0f%%, 弧<π/2冻结) | ' ...
           'B4 = B3 + SLOW跟踪滤波(fn=110 kHz, ζ=%g)\n'], k.SEG_B3, ...
          k.GATE_B3 * 100, dp.ZETA);

  ncase = size(k.CASES, 1);
  results = cell(1, ncase);
  for i = 1:ncase
    A = k.CASES(i, 1);
    f0 = k.CASES(i, 2);
    rh = np_rng_new(1000 + i - 1);
    sc = make_scenario_(A, f0, cnr_db, rh);
    results{i} = run_methods_(sc, A, f0, true);
    fprintf(2, '  case A=%g nm f=%g Hz done (%.0f s)\n', A * 1e9, f0, ...
            toc(t_start));
  end

  % ------------------------------------------------- per-case result table
  fprintf('\n--- 结果表 (幅值误差%% | 位移RMS误差 nm | 谱线SNR@f dB) ---\n');
  hdr = sprintf('%7s %7s |', 'A', 'f');
  for im = 1:numel(k.METHODS)
    hdr = [hdr, sprintf('%26s', k.METHODS{im})];
  end
  fprintf('%s\n', hdr);
  fprintf('%7s %7s |%s\n', '', '', ...
          repmat(sprintf('%26s', 'amp%   rms_nm   snr_dB'), 1, ...
                 numel(k.METHODS)));
  tbl = zeros(ncase, 3 * numel(k.METHODS));
  for i = 1:ncase
    r = results{i};
    cells = '';
    for im = 1:numel(k.METHODS)
      d = r.(k.METHODS{im});
      cells = [cells, sprintf('%9.2f %8.1f %7.1f', ...
                              min(max(d.amp, -999.9), 999.9), ...
                              min(d.rms, 99999.9), d.snr)];
      tbl(i, (im-1)*3 + (1:3)) = [d.amp, d.rms, d.snr];
    end
    fprintf('%5.0fnm %5.0fHz |%s\n', k.CASES(i, 1) * 1e9, k.CASES(i, 2), cells);
  end

  % ------------------------------------------------- B1 window sweep detail
  rA = results{k.ASSERT_IDX};
  fprintf('\n--- B1 窗口扫描 @ 断言场景 A=%.0f nm, f=%.0f Hz ---\n', ...
          k.CASES(k.ASSERT_IDX, 1) * 1e9, k.CASES(k.ASSERT_IDX, 2));
  fprintf('%8s %12s %10s %8s\n', '窗口/s', '幅值误差%', 'RMS/nm', 'SNR/dB');
  b1sweep = zeros(numel(rA.B1_sweep), 4);
  for j = 1:numel(rA.B1_sweep)
    m = rA.B1_sweep(j);
    b1sweep(j, :) = [m.win, m.amp, m.rms, m.snr];
    fprintf('%8.2f %12.2f %10.1f %8.1f\n', m.win, ...
            min(max(m.amp, -999.9), 999.9), min(m.rms, 99999.9), m.snr);
  end
  fprintf(['  → B1 最优窗 = %.2f s (按SNR); RMS 取各窗最小值 %.1f nm ' ...
           '作保守基线\n'], rA.B1.win, rA.B1_min_rms);

  % ------------------------------------------------- B3 parameter tracking
  tk = rA.B3_track;
  fprintf('\n--- B3 分段参数跟踪 @ 断言场景 (真值 ε/δ 随时间线性漂移) ---\n');
  fprintf('%6s %4s %7s %8s %7s %7s %6s\n', 't/s', '拟合', '弧/rad', ...
          'ε̂%', 'ε真%', 'δ̂°', 'δ真°');
  Kseg = numel(tk.t_c);
  b3trk = zeros(Kseg, 7);
  for kk = 1:Kseg
    pk = tk.pars{kk};
    eps_hat = 100 * (pk.B / pk.A - 1);
    del_hat = pk.delta * 180 / pi;
    frac = tk.t_c(kk) / k.T_REC;
    eps_true = 100 * (k.EPS_T0 + (k.EPS_T1 - k.EPS_T0) * frac);
    del_true = k.DEL_T0 + (k.DEL_T1 - k.DEL_T0) * frac;
    if tk.oks(kk), oks = 'OK'; else, oks = '冻结'; end
    fprintf('%6.2f %4s %7.2f %8.2f %7.2f %7.2f %6.2f\n', tk.t_c(kk), oks, ...
            tk.arcs(kk), eps_hat, eps_true, del_hat, del_true);
    b3trk(kk, :) = [tk.t_c(kk), double(tk.oks(kk)), tk.arcs(kk), ...
                    eps_hat, eps_true, del_hat, del_true];
  end
  p2 = rA.B2_par;
  fprintf(['  B2 静态参数(前%gs): ε̂=%+.2f%%, δ̂=%.2f° — 记录末端真值 ' ...
           'ε=%+.1f%%, δ=%.1f° (静态参数已过时)\n'], k.T_CAL_B2, ...
          100 * (p2.B / p2.A - 1), p2.delta * 180 / pi, ...
          k.EPS_T1 * 100, k.DEL_T1);

  % ------------------------------------------------- CNR sensitivity sweep
  fprintf('\n--- CNR 敏感性 @ 断言场景 (B1 最优窗 vs B3) ---\n');
  fprintf('%10s %10s %10s %10s %10s\n', '前端CNR/dB', 'B1 rms/nm', ...
          'B1 snr/dB', 'B3 rms/nm', 'B3 snr/dB');
  cnrs = [10.0, 20.0, 30.0];
  cnrtbl = zeros(numel(cnrs), 5);
  for j = 1:numel(cnrs)
    rh = np_rng_new(2000 + j - 1);
    scj = make_scenario_(k.CASES(k.ASSERT_IDX, 1), k.CASES(k.ASSERT_IDX, 2), ...
                         cnrs(j), rh);
    rj = run_methods_(scj, k.CASES(k.ASSERT_IDX, 1), ...
                      k.CASES(k.ASSERT_IDX, 2), false);
    cnrtbl(j, :) = [cnrs(j), rj.B1_min_rms, rj.B1.snr, rj.B3.rms, rj.B3.snr];
    fprintf('%10.0f %10.1f %10.1f %10.1f %10.1f\n', cnrs(j), ...
            rj.B1_min_rms, rj.B1.snr, rj.B3.rms, rj.B3.snr);
  end

  % -------------------------------------------------------------- assertion
  fprintf('\n%s\n', repmat('=', 1, 78));
  fprintf('断言 (规格): A=100 nm @ 100 Hz, 最优校正方法 vs B1(最优窗):\n');
  fprintf('           谱线SNR改善 > 10 dB  或  RMS误差降低 > 3x\n');
  cnames = {'B2', 'B3', 'B4'};
  snrs = cellfun(@(nm) rA.(nm).snr, cnames);
  rmss = cellfun(@(nm) rA.(nm).rms, cnames);
  [~, ibs] = max(snrs);
  [~, ibr] = min(rmss);
  d_snr = snrs(ibs) - rA.B1.snr;
  r_rms = rA.B1_min_rms / max(rmss(ibr), 1e-12);
  if d_snr > 10, s1 = '满足'; else, s1 = '不满足'; end
  fprintf('  SNR:  %s %.1f dB vs B1 %.1f dB → 改善 %+.1f dB (%s >10 dB)\n', ...
          cnames{ibs}, snrs(ibs), rA.B1.snr, d_snr, s1);
  if r_rms > 3, s2 = '满足'; else, s2 = '不满足'; end
  fprintf(['  RMS:  %s %.2f nm vs B1(各窗最小) %.2f nm → 降低 %.1fx ' ...
           '(%s >3x)\n'], cnames{ibr}, rmss(ibr), rA.B1_min_rms, r_rms, s2);
  ok = (d_snr > 10.0) || (r_rms > 3.0);
  if ok, tag = 'PASS'; else, tag = 'FAIL'; end
  fprintf('\n  ====>  %s  <====\n%s\n', tag, repmat('=', 1, 78));

  % ------------------------------------------------------- recommendation
  fprintf('\n--- 推荐最优可实现软件方案 (硬件不可改) ---\n');
  fprintf('推荐: B3 分段弧 Heydemann 校正 (参数与理由见 Python 版 ');
  fprintf('validate_ellipse_small_disp.py 输出/文档)\n');
  fprintf('\n总耗时 %.0f s\n', toc(t_start));

  % ------------------------------------------------- golden metrics (.mat)
  g = struct();
  g.sd_table = tbl;
  g.sd_b1sweep = b1sweep;
  g.sd_b1best = [rA.B1.win, rA.B1.amp, rA.B1.rms, rA.B1.snr, rA.B1_min_rms];
  g.sd_b2par = [p2.p, p2.q, p2.A, p2.B, p2.delta];
  g.sd_b3trk = b3trk;
  g.sd_cnr = cnrtbl;
  g.sd_sum = [d_snr, r_rms, double(ok)];
  gdir = fullfile(sd, '..', 'golden');
  if ~exist(gdir, 'dir'), mkdir(gdir); end
  gfile = fullfile(gdir, 'validate_ellipse_small_disp_mat.mat');
  save('-v7', gfile, '-struct', 'g');
  fprintf('[golden metrics saved to %s]\n', gfile);

  rc = double(~ok);
end


% ------------------------------------------------------------------ constants
function k = sd_const_()
  persistent kk
  if isempty(kk)
    kk.LAMBDA = 1550e-9;
    kk.FS_FULL = 250e6;
    kk.DECIM = 100;
    kk.FS = kk.FS_FULL / kk.DECIM;      % 2.5 MS/s simulation rate
    kk.T_REC = 2.0;
    kk.DEC2 = 100;                      % metric decimation -> 25 kS/s
    kk.FS2 = kk.FS / kk.DEC2;
    kk.T_TRIM = 0.1;
    kk.SNR_SIG_HZ = 2.0;
    kk.SNR_FLOOR_HZ = [3.0, 48.0];
    kk.EPS_T0 = -0.08;  kk.EPS_T1 = -0.12;
    kk.DEL_T0 = 3.0;    kk.DEL_T1 = 6.0;
    kk.P_OFF0 = 0.06;   kk.P_DRIFT = 0.01;
    kk.Q_OFF = -0.05;
    kk.FRINGE_RATE = 1.5;
    kk.PSI_WANDER = 0.8;
    kk.R_SWING = 0.04;
    kk.R_BW = 0.5;
    kk.B1_WINDOWS = [0.05, 0.1, 0.2, 0.5, 1.0];
    kk.T_CAL_B2 = 0.4;
    kk.SEG_B3 = 0.5;
    kk.GATE_B3 = 0.02;
    kk.B1_AMP_SANE = 20.0;
    kk.FN_SLOW = 110e3;
    As = [10e-9, 100e-9, 500e-9, 1e-6];
    f0s = [100.0, 1000.0];
    cases = zeros(numel(As) * numel(f0s), 2);
    r = 0;
    for ia = 1:numel(As)
      for jf = 1:numel(f0s)
        r = r + 1;
        cases(r, :) = [As(ia), f0s(jf)];
      end
    end
    kk.CASES = cases;
    kk.ASSERT_IDX = find(cases(:, 1) == 100e-9 & cases(:, 2) == 100.0, 1);
    kk.METHODS = {'B0', 'B1', 'B2', 'B3', 'B4'};
  end
  k = kk;
end


% ------------------------------------------------------------------ helpers
function W = rfft_(x)
%numpy.fft.rfft of a real vector.
  x = x(:);
  N = numel(x);
  F = fft(x);
  W = F(1:floor(N / 2) + 1);
end

function x = irfft_(W, N)
%numpy.fft.irfft(W, N): Hermitian-symmetric inverse (DC/Nyquist imag dropped).
  W = W(:);
  if mod(N, 2) == 0
    full = [W; conj(W(end-1:-1:2))];
  else
    full = [W; conj(W(end:-1:2))];
  end
  x = real(ifft(full));
end

function s = smooth_noise_(N, fs, fc, rh)
%Unit-rms Gaussian noise low-passed (brick wall) at fc.
  W = rfft_(np_rng_randn(rh, N));
  fr = (0:floor(N / 2))' * (fs / N);
  W(fr > fc) = 0;
  s = irfft_(W, N);
  s = s / max(std(s, 1), 1e-300);       % population std as numpy
end

function x = to_disp_(ph)
  k = sd_const_();
  x = ph * (k.LAMBDA / (4 * pi));
end

function y = decimate_fft_(x, dec)
%Brick-wall low-pass at 0.4*fs/dec then subsample by dec.
  x = x(:);
  N = numel(x);
  X = rfft_(x);
  fr = (0:floor(N / 2))' / N;           % rfftfreq(N, 1.0), cycles/sample
  X(fr > 0.4 / dec) = 0;
  xf = irfft_(X, N);
  y = xf(1:dec:end);
end

function snr = line_snr_(xd, fs, f0)
%Line SNR at f0 from a single Hann periodogram of the whole segment.
  k = sd_const_();
  xd = xd(:);
  n = numel(xd);
  win = 0.5 - 0.5 * cos(2 * pi * (0:n-1)' / (n - 1));
  F = fft(xd .* win);
  P = abs(F(1:floor(n / 2) + 1)) .^ 2;
  fx = (0:floor(n / 2))' * (fs / n);
  off = abs(fx - f0);
  sig = off <= k.SNR_SIG_HZ;
  flo = (off >= k.SNR_FLOOR_HZ(1)) & (off <= k.SNR_FLOOR_HZ(2));
  p_sig = sum(P(sig));
  p_flo = sum(P(flo)) * sum(sig) / max(sum(flo), 1);
  snr = 10 * log10(max(p_sig, 1e-300) / max(p_flo, 1e-300));
end


% ----------------------------------------------------------------- scenario
function sc = make_scenario_(A, f0, cnr_frontend_db, rh)
  k = sd_const_();
  N = round(k.T_REC * k.FS);
  t = (0:N-1)' / k.FS;
  x_true = A * sin(2 * pi * f0 * t);
  psi = 2 * pi * k.FRINGE_RATE * t ...
        + k.PSI_WANDER * smooth_noise_(N, k.FS, 1.0, rh);
  eps_t = k.EPS_T0 + (k.EPS_T1 - k.EPS_T0) * t / k.T_REC;
  del_t = (pi / 180) * (k.DEL_T0 + (k.DEL_T1 - k.DEL_T0) * t / k.T_REC);
  R = 1.0 + k.R_SWING * smooth_noise_(N, k.FS, k.R_BW, rh);
  p_t = k.P_OFF0 + k.P_DRIFT * t / k.T_REC;

  phi = (4 * pi / k.LAMBDA) * x_true + psi;
  gI = 1.0;
  gQ = gI * (1.0 + eps_t);
  cI = gI * R .* cos(phi);
  cQ = gQ .* R .* sin(phi + del_t);
  Pc = mean(cI .^ 2 + cQ .^ 2);
  cnr_dec_db = cnr_frontend_db + 10 * log10(k.DECIM);
  s2 = Pc / 10 ^ (cnr_dec_db / 10);
  u = cI + p_t + sqrt(s2 / 2) * np_rng_randn(rh, N);
  v = cQ + k.Q_OFF + sqrt(s2 / 2) * np_rng_randn(rh, N);
  x_ref = x_true + to_disp_(psi);
  sc = struct('t', t, 'u', u, 'v', v, 'x_ref', x_ref, 's2', s2, 'Pc', Pc, ...
              'cnr_dec_db', cnr_dec_db);
end


% ------------------------------------------------------------------ metrics
function ev = case_eval_new_(sc, A, f0)
%Common decimated reference + metric estimator for one scenario.
  k = sd_const_();
  ev = struct();
  ev.A = A;
  ev.f0 = f0;
  ev.x_ref2 = decimate_fft_(sc.x_ref, k.DEC2);
  n2 = numel(ev.x_ref2);
  ev.t2 = (0:n2-1)' / k.FS2;
  ev.sel = (ev.t2 >= k.T_TRIM) & (ev.t2 < k.T_REC - k.T_TRIM);
  ev.n_dt = round(0.25 * k.FS2);        % detrend window: f0*0.25 integer
end

function m = case_eval_(ev, x_est)
  k = sd_const_();
  x2 = decimate_fft_(x_est, k.DEC2);
  xs = x2(ev.sel);
  e = xs - ev.x_ref2(ev.sel);
  e = e - mean(e);
  rms_nm = sqrt(mean(e .^ 2)) * 1e9;
  xd = xs - ve_movmean(xs, ev.n_dt);    % kill drift (gain=1 at f0 exactly)
  ts = ev.t2(ev.sel);
  amp = 2 * abs(mean(xd .* exp(-1i * 2 * pi * ev.f0 * ts)));
  m = struct('amp', 100 * (amp / ev.A - 1), 'rms', rms_nm, ...
             'snr', line_snr_(xd, k.FS2, ev.f0));
end


% ------------------------------------------------------------------ methods
function out = run_methods_(sc, A, f0, include_b4)
  k = sd_const_();
  dp = design_params();
  u = sc.u;
  v = sc.v;
  t = sc.t;
  ev = case_eval_new_(sc, A, f0);
  out = struct();

  % B0: raw angle(z)
  out.B0 = case_eval_(ev, to_disp_(ve_phase_cum(u + 1i * v)));

  % B1: sliding demean, window swept
  sweep = struct('amp', {}, 'rms', {}, 'snr', {}, 'win', {});
  for iw = 1:numel(k.B1_WINDOWS)
    w = k.B1_WINDOWS(iw);
    n = round(w * k.FS);
    zc = (u - ve_movmean(u, n)) + 1i * (v - ve_movmean(v, n));
    m = case_eval_(ev, to_disp_(ve_phase_cum(zc)));
    m.win = w;
    sweep(end+1) = m;
  end
  out.B1_sweep = sweep;
  % best window: highest line SNR among windows with sane amplitude;
  % fall back to min-RMS if no window is sane.
  sane = sweep(abs([sweep.amp]) < k.B1_AMP_SANE);
  if ~isempty(sane)
    [~, ib] = max([sane.snr]);
    out.B1 = sane(ib);
  else
    [~, ib] = min([sweep.rms]);
    out.B1 = sweep(ib);
  end
  out.B1_min_rms = min([sweep.rms]);

  % B2: static Heydemann from the first T_CAL_B2 seconds
  ncal = round(k.T_CAL_B2 * k.FS);
  step = max(1, floor(ncal / 20000));
  [par2, res2] = heydemann_fit(u(1:step:ncal), v(1:step:ncal));
  [~, ~, z2] = heydemann_apply(u, v, par2);
  out.B2 = case_eval_(ev, to_disp_(ve_phase_cum(z2)));
  out.B2_par = par2;
  out.B2_res = res2;
  clear z2

  % B3: segmented-arc Heydemann (amplitude-gated, freeze on short arc)
  [t_c, pars, oks, arcs] = segmented_heydemann(u, v, k.FS, k.SEG_B3, ...
                                               k.GATE_B3);
  trk = interp_par_track(t, t_c, pars);
  z3 = apply_par_track(u, v, trk);
  clear trk
  out.B3 = case_eval_(ev, to_disp_(ve_phase_cum(z3)));
  out.B3_track = struct('t_c', t_c, 'pars', {pars}, 'oks', oks, 'arcs', arcs);

  % B4: B3-corrected z through the SLOW-gear carrier loop (pure NCO phase)
  if include_b4
    opts = struct('zeta', dp.ZETA, 'gate', 'always');
    [~, phi_nco] = pll_carrier_regen(z3, k.FS, k.FN_SLOW, sc.s2, opts);
    out.B4 = case_eval_(ev, to_disp_(np_unwrap(phi_nco)));
  end
end
