function rc = validate_ellipse_audit()
%VALIDATE_ELLIPSE_AUDIT Audit fixes for ellipse correction (review items 1-3).
%   rc = validate_ellipse_audit()
%   MATLAB/Octave port of homodyne_tracking_design/validate_ellipse_audit.py
%   with the same random draws (numpy-exact RNG kernel) and assertions:
%     1. pure Gaussian noise must NOT pass heydemann_fit
%     2. noiseless short arc must NOT pass (biased centre)
%     3. noisy short arc through fit_arc_gated must NOT pass (pre-fit arc gate)
%     4. good full circle must pass
%   Saves golden metrics to golden/validate_ellipse_audit_mat.mat and returns
%   rc = 0 iff all four assertions hold.
  sd = fileparts(mfilename('fullpath'));          % matlab/homodyne
  addpath(sd);
  addpath(fullfile(sd, 'core'));
  addpath(fullfile(sd, 'ellipse'));
  ensure_kernels();
  E = ellipse_constants();

  rh = np_rng_new(0);
  fprintf('椭圆校正审查回归测试\n%s\n', repmat('=', 1, 40));

  % 1) Random noise must NOT pass
  u = np_rng_randn(rh, 500);
  v = np_rng_randn(rh, 500);
  [~, res1] = heydemann_fit(u, v);
  ok_noise = res1.ok;
  fprintf('1. 纯高斯噪声 ok=%s (应为 False)  rms=%.3f\n', ...
          pybool_(ok_noise), res1.rms);

  % 2) Short arc (noiseless) should fail
  psi = linspace(0, 1.2, 80)';
  u_short = cos(psi) + 0.35;
  v_short = 0.9 * sin(psi + 0.08) + 0.30;
  [par_short, res_short] = heydemann_fit(u_short, v_short);
  ctr_err = hypot(par_short.p, par_short.q);
  fprintf('2. 无噪短弧 ok=%s (应为 False)  中心误差=%.3f  rms=%.3f\n', ...
          pybool_(res_short.ok), ctr_err, res_short.rms);

  % 3) Noisy short arc via fit_arc_gated must fail (pre-fit arc gate)
  prev = struct('p', 0.35, 'q', 0.30, 'A', 1.0, 'B', 0.9, ...
                'delta', 4.58 * pi / 180);
  psi3 = linspace(0, 1.2, 300)';
  u3 = cos(psi3) + prev.p + 0.002 * np_rng_randn(rh, 300);
  v3 = 0.9 * sin(psi3 + prev.delta) + prev.q + 0.002 * np_rng_randn(rh, 300);
  [~, res_noisy] = fit_arc_gated(u3, v3, prev, 0.15);
  msg3 = '';
  if isfield(res_noisy, 'msg'), msg3 = res_noisy.msg; end
  fprintf('3. 带噪短弧 fit_arc_gated ok=%s (应为 False)  msg=%s\n', ...
          pybool_(res_noisy.ok), msg3(1:min(60, numel(msg3))));

  % 4) Good full circle should pass
  phi = 2 * pi * (0:399)' / 400;                  % linspace endpoint=False
  u4 = cos(phi) + 0.06;
  v4 = 0.88 * sin(phi + 4.5 * pi / 180) - 0.05;
  [par4, res4] = heydemann_fit(u4, v4);
  fprintf('4. 整圆 ok=%s (应为 True)  eps=%+.3f  rms=%.4f\n', ...
          pybool_(res4.ok), par4.B / par4.A - 1, res4.rms);

  pass_all = ~ok_noise && ~res_short.ok && ~res_noisy.ok && res4.ok;
  if pass_all, tag = 'PASS'; else, tag = 'FAIL'; end
  fprintf('\n%s\n', tag);

  % ------------------------------------------------- golden metrics (.mat)
  g = struct();
  g.au_flags = double([ok_noise, res_short.ok, res_noisy.ok, res4.ok, pass_all]);
  g.au_vals = [res1.rms, ctr_err, res_short.rms, ...
               par4.B / par4.A - 1, res4.rms];
  gdir = fullfile(sd, '..', 'golden');
  if ~exist(gdir, 'dir'), mkdir(gdir); end
  gfile = fullfile(gdir, 'validate_ellipse_audit_mat.mat');
  save('-v7', gfile, '-struct', 'g');
  fprintf('[golden metrics saved to %s]\n', gfile);

  rc = double(~pass_all);
end

function s = pybool_(x)
  if x, s = 'True'; else, s = 'False'; end
end
