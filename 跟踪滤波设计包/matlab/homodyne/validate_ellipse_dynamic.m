function rc = validate_ellipse_dynamic()
%VALIDATE_ELLIPSE_DYNAMIC Dynamic-workflow ellipse correction (no cal pause).
%   rc = validate_ellipse_dynamic()
%   MATLAB/Octave port of homodyne_tracking_design/validate_ellipse_dynamic.py
%   with the same scenario (numpy-exact RNG kernel), methods and assertion:
%     B0  raw angle(u + j*v)
%     B1  sliding demean (0.1 s window)
%     B2  static Heydemann from phase 1
%     B7  phase-1 g,delta + online arc-gated p,q tracker (OnlineBiasTracker)
%   Assertion: on the small-vibration phases (black + far) B7 must at least
%   halve both the mean RMS and the mean |amplitude error| of B1.
%   Saves golden metrics to golden/validate_ellipse_dynamic_mat.mat and
%   returns rc = 0 iff the assertion holds.
  t0 = tic;
  sd = fileparts(mfilename('fullpath'));          % matlab/homodyne
  addpath(sd);
  addpath(fullfile(sd, 'core'));
  addpath(fullfile(sd, 'ellipse'));
  ensure_kernels();
  c = ve_const();
  ph = ve_phases_dynamic();
  T_TOTAL = 2.4;

  sc = synth_record_(np_rng_new(42), ph, T_TOTAL);
  t = sc.t; u = sc.u; v = sc.v; x_ref = sc.x_ref;
  nph = numel(ph);
  sels = cell(1, nph);
  for i = 1:nph
    sels{i} = (t >= ph(i).t0 + c.T_TRIM) & (t < ph(i).t0 + ph(i).dur - c.T_TRIM);
  end

  % B1 sliding demean
  n = floor(0.1 * c.FS);
  z1 = (u - ve_movmean(u, n)) + 1i * (v - ve_movmean(v, n));

  % B2 static from phase1
  n1 = floor(0.6 * c.FS);
  step = max(1, floor(n1 / 8000));
  par2 = heydemann_fit(u(1:step:n1), v(1:step:n1));
  [~, ~, z2] = heydemann_apply(u, v, par2);

  % B7: g,delta from phase1 fit; online p,q via arc-gated tracker
  [par7, ~] = heydemann_fit(u(1:step:n1), v(1:step:n1));
  st7 = online_bias_tracker_init(par7, c.FS, 0.05);
  z7 = online_bias_tracker_run(st7, u, v);

  mnames = {'B0', 'B1', 'B2', 'B7'};
  zs = {u + 1i * v, z1, z2, z7};
  fprintf('%s\n动态工况仿真（无专用标定暂停）\n%s\n', ...
          repmat('=', 1, 68), repmat('=', 1, 68));
  fprintf('%-4s|%-10s%9s%11s%9s\n', '方法', '阶段', 'RMS/nm', '幅值误差%', 'SNR/dB');
  results = nan(numel(mnames), nph, 3);           % rms, amp, snr
  for im = 1:numel(mnames)
    x = ve_to_disp(ve_phase_cum(zs{im}));
    for ip = 1:nph
      m = ve_metrics(x, x_ref, t, ph(ip).f0, sels{ip});
      results(im, ip, :) = [m.rms, m.amp, m.snr];
      fprintf('%-4s|%-10s%9.1f%11.1f%9.1f\n', mnames{im}, ph(ip).name, ...
              m.rms, m.amp, m.snr);
    end
  end

  b1s = mean([results(2, 2, 1), results(2, 3, 1)]);
  b7s = mean([results(4, 2, 1), results(4, 3, 1)]);
  b1a = mean([abs(results(2, 2, 2)), abs(results(2, 3, 2))]);
  b7a = mean([abs(results(4, 2, 2)), abs(results(4, 3, 2))]);
  ok = (b7s < b1s / 2) && (b7a < b1a / 2);
  fprintf('\n小振动段(黑+远) 平均RMS: B1=%.1fnm  B7=%.1fnm  改善=%.1fx\n', ...
          b1s, b7s, b1s / max(b7s, 0.1));
  fprintf('小振动段 平均|幅值误差|: B1=%.1f%%  B7=%.1f%%\n', b1a, b7a);
  fprintf(['阶段1 g,delta估计: eps_hat=%+.1f%% delta_hat=%.1f deg ' ...
           '(真值 eps=%.1f%% delta=%.1f deg)\n'], ...
          100 * (par7.B / par7.A - 1), par7.delta * 180 / pi, ...
          c.EPS_HW * 100, c.DEL_HW * 180 / pi);
  if ok, tag = 'PASS'; else, tag = 'FAIL'; end
  fprintf('断言 %s\n耗时 %.1fs\n', tag, toc(t0));

  % ------------------------------------------------- golden metrics (.mat)
  g = struct();
  g.dy_table = reshape(results, numel(mnames), nph * 3);  % [rms3 amp3 snr3]
  g.dy_sum = [b1s, b7s, b1a, b7a, double(ok)];
  g.dy_par7 = [par7.p, par7.q, par7.A, par7.B, par7.delta];
  gdir = fullfile(sd, '..', 'golden');
  if ~exist(gdir, 'dir'), mkdir(gdir); end
  gfile = fullfile(gdir, 'validate_ellipse_dynamic_mat.mat');
  save('-v7', gfile, '-struct', 'g');
  fprintf('[golden metrics saved to %s]\n', gfile);

  rc = double(~ok);
end


function sc = synth_record_(rh, ph, T_TOTAL)
%Port of validate_ellipse_dynamic.synth_record (same RNG draw order).
  c = ve_const();
  N = floor(T_TOTAL * c.FS);
  t = (0:N-1)' / c.FS;
  u = zeros(N, 1);
  v = zeros(N, 1);
  x_true = zeros(N, 1);
  psi = 2 * pi * c.FRINGE_RATE * t;
  p_t = c.P_OFF0 + c.P_DRIFT * t / T_TOTAL;
  for i = 1:numel(ph)
    idx = find((t >= ph(i).t0) & (t < ph(i).t0 + ph(i).dur));
    tt = t(idx);
    x = ph(i).A * sin(2 * pi * ph(i).f0 * tt);
    phi = (4 * pi / c.LAMBDA) * x + psi(idx);
    R = ph(i).R;
    cI = c.GI * R * cos(phi);
    cQ = c.GQ * R * sin(phi + c.DEL_HW);
    s2 = mean(cI .^ 2 + cQ .^ 2) / 10 ^ (ph(i).snr_db / 10);
    u(idx) = cI + p_t(idx) + sqrt(s2 / 2) * np_rng_randn(rh, numel(idx));
    v(idx) = cQ + c.Q_OFF + sqrt(s2 / 2) * np_rng_randn(rh, numel(idx));
    x_true(idx) = x;
  end
  sc = struct('t', t, 'u', u, 'v', v, 'x_ref', x_true);
end
