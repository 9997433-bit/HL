function validate_residual_alignment()
%VALIDATE_RESIDUAL_ALIGNMENT Review item #4: residual_mode == gear_filter.
%   MATLAB/Octave port of validate_residual_alignment.py: end-to-end
%   consistency of the product path (residual_mode) vs the validation path
%   (vt_gear_filter) over 3 gears x 3 frequencies x {near-noiseless/always,
%   CNR=3dB/auto}; asserts |err_gear - err_core| < 1 percentage point.
%
%   Run:  cd matlab && octave --eval validate_residual_alignment
%   Saves golden metrics to golden/validate_residual_alignment_mat.mat and
%   raises an error (nonzero exit code) if any combination fails.
  t_all = tic;
  sd = fileparts(mfilename('fullpath'));
  addpath(fullfile(sd, 'homodyne'));
  ensure_kernels();

  dp = design_params();
  c = vt_const();
  TOL_PP = 1.0;
  FREQS = [100e3, 1e6, 3e6];

  fprintf(['残差窗一致性验证 (审查项 #4): core.residual_mode vs ' ...
           'validate_tracking.gear_filter\n']);
  fprintf('  fs=%.0fMS/s, B_win=%.0fMHz, NT_WIN=%d taps, 容差 |Δerr| < %.0fpp\n', ...
          dp.FS / 1e6, dp.B_WIN / 1e6, dp.NT_WIN, TOL_PP);

  tags = {'near-noiseless / gate=always', 'CNR=3dB noisy / gate=auto'};
  gates = {'always', 'auto'};
  cnr_dbs = [NaN, 3.0];
  n_cases = 2 * 3 * 3;
  err_gear = zeros(n_cases, 1);
  err_core = zeros(n_cases, 1);
  adiff = zeros(n_cases, 1);
  okv = false(n_cases, 1);
  idx = 0;
  nfail = 0;
  for it = 1:2
    gate = gates{it};
    fprintf('\n  [%s]\n', tags{it});
    fprintf('    %-7s %7s | %15s %17s | %9s\n', 'gear', 'f0', ...
            'err gear_filter', 'err residual_mode', '|diff| pp');
    for ib = 1:3
      band = dp.ORDER{ib};
      for ifq = 1:3
        f0 = FREQS(ifq);
        sc = vt_make_scene(f0);
        if strcmp(gate, 'always')
          z = vt_clean_z(sc);
          Nhat = 1e-10;
        else
          s2 = 10^(-cnr_dbs(it) / 10);
          rh = np_rng_new(40000 + fix(f0 / 1e3));
          z = exp(1i * sc.ph) + ...
              complex_bandlimited_noise(c.N, dp.FS, dp.B_FRONTEND, s2, rh);
          Nhat = s2;
        end
        yg = vt_gear_filter(z, band, Nhat, gate);
        ropts = gate_params(band);
        ropts.zeta = dp.ZETA;
        ropts.tauG = dp.TAU_G;
        ropts.Nt_win = dp.NT_WIN;
        ropts.gate = gate;
        yc = residual_mode(z, dp.FS, dp.BANDS.(band).fn, Nhat, ...
                           dp.B_WIN, ropts);
        eg = vt_amp_err_pct(vt_vdisc(yg), sc);
        ec = vt_amp_err_pct(vt_vdisc(yc), sc);
        d = abs(eg - ec);
        ok = d < TOL_PP;
        idx = idx + 1;
        err_gear(idx) = eg;
        err_core(idx) = ec;
        adiff(idx) = d;
        okv(idx) = ok;
        if ok, mark = ''; else, mark = '   <-- FAIL'; nfail = nfail + 1; end
        fprintf('    %-7s %5.0fk | %+14.3f%% %+16.3f%% | %9.4f%s\n', ...
                band, f0 / 1e3, eg, ec, d, mark);
      end
    end
  end

  fprintf('\n%s\n', repmat('=', 1, 70));
  if nfail > 0
    fprintf('FAIL: %d/%d 组合差异 >= %.0fpp\n', nfail, n_cases, TOL_PP);
  else
    fprintf(['PASS: 全部 %d 组合 (三档 x 三频 x 无噪/含噪) 幅度误差差异 < ' ...
             '%.0fpp -- 验证路径 = 产品路径\n'], n_cases, TOL_PP);
  end
  fprintf('[elapsed %.1f s]\n', toc(t_all));

  % ------------------------------------------------- golden metrics (.mat)
  g = struct();
  g.checks_ok = double(okv(:)');
  g.checks_pass = sum(g.checks_ok);
  g.checks_total = n_cases;
  g.noisy = struct('err_gear', err_gear, 'err_core', err_core, ...
                   'adiff', adiff);
  gdir = fullfile(sd, 'golden');
  if ~exist(gdir, 'dir'), mkdir(gdir); end
  gfile = fullfile(gdir, 'validate_residual_alignment_mat.mat');
  save('-v7', gfile, '-struct', 'g');
  fprintf('[golden metrics saved to %s]\n', gfile);

  if nfail > 0
    error('validate_residual_alignment: SOME CHECKS FAILED');
  end
end
