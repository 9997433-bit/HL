function rc = validate_heterodyne()
%VALIDATE_HETERODYNE H1-H6 外差电IQ (Polytec类) 跟踪滤波完整仿真验证.
% Faithful port of heterodyne_tracking_design/validate_heterodyne.py.
%
% 被测架构: 数字下变频后复基带 z(t), 单旋钮 II 型 arctan DPLL
% (pll_carrier_regen, 与零差共享同一实现 -- gate='always' 下两者逐位一致),
% 纯 NCO 输出 y = e^{j phi}.  档位由量程加速度推 fn, 同时决定测量带宽
% f_3dB = 2.058*fn 与跟踪动态 a_design/a_slip.
%
% 场景 / 断言: H0 (C01), H1 (C11-C14), H2 (C21-C26), H3 (C31-C33),
% H4 (C41-C43), H5 (C51-C53), H6 (C61-C62).
%
% RNG note: the Python source uses np.random.default_rng(seed) (PCG64).
% Octave cannot reproduce those streams, so each scenario seeds Octave's own
% RNG (set_rng) with the SAME seed numbers -- assertions are statistical
% with wide margins; the deterministic pipeline itself is covered separately
% by compare_heterodyne_golden.m against exported Python vectors.
%
% Exit code 0 iff all checks PASS (also returned as rc).
  here = fileparts(mfilename('fullpath'));
  addpath(fullfile(here, '..', 'homodyne'));         % set_rng, hd_* helpers
  addpath(fullfile(here, '..', 'homodyne', 'core')); % canonical shared core
  addpath(here);
  global VHET
  VHET = struct();
  VHET.P = het_params();
  VHET.MODES = het_mode_params(1.0);   % 演示统一取中间量程 1 m/s
  VHET.TINY = 1e-300;
  VHET.checks = {};

  t0 = tic;
  P = VHET.P;
  fprintf('外差电IQ (Polytec类) 跟踪滤波方案 -- 仿真验证 (H1-H6) [MATLAB port]\n');
  fprintf(['reference core: pll_carrier_regen 纯NCO (与零差共享实现), ' ...
           'lambda=%.1fnm, fs=%.0fMS/s, B_frontend=%.0fMHz, ' ...
           'f_dev_max=%.1fMHz, zeta=%g\n'], ...
          P.LAMBDA * 1e9, P.FS / 1e6, P.B_FRONTEND / 1e6, ...
          P.F_DEV_MAX / 1e6, P.ZETA);
  H0();
  H1();
  H2();
  H3();
  H4();
  H56();
  print_header('ASSERTION SUMMARY');
  allok = true;
  for i = 1:numel(VHET.checks)
    c = VHET.checks{i};
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
  fprintf('\n%s\n', repmat('=', 1, 92));
  fprintf('%s\n', title);
  fprintf('%s\n', repmat('=', 1, 92));
end

function ok = check(cid, label, ok, detail)
  global VHET
  VHET.checks{end + 1} = {cid, label, ok, detail};
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

function a = ls_amp(v, t, f_v, sel)
% sin/cos 最小二乘幅值 (对任意相位与少量周期稳健, 沿袭 t5).
  X = [ones(sum(sel), 1), sin(2 * pi * f_v * t(sel)), ...
       cos(2 * pi * f_v * t(sel))];
  b = X \ v(sel);
  a = hypot(b(2), b(3));
end

function a = asd_band(v, sel, fs, L, f_lo, f_hi)
% 速度 ASD: 频带内 PSD 中值的平方根 (R2).
  global VHET
  [Pw, f] = welch_psd(v(sel), fs, L);
  m = (f >= f_lo) & (f <= f_hi);
  a = max(sqrt(median(Pw(m))), VHET.TINY);
end

function y = complex_lp(z, B_pre, fs, Nt)
% 固定复数低通 (双边宽 B_pre), 沿袭 t5 的 preLP 对照.
  y = fir_lp(real(z), B_pre / 2, fs, Nt) ...
      + 1i * fir_lp(imag(z), B_pre / 2, fs, Nt);
end

function v = vdisc(y)
  global VHET
  v = fm_discriminator(y, VHET.P.FS, VHET.P.LAMBDA);
end

function H = hl_mag(f0, fn)
% 精确离散闭环 |H_L(f0)| -- 频响校正因子的倒数.
  global VHET
  H = abs(hl_response(f0, VHET.P.FS, fn, VHET.P.ZETA));
end

function [y, phi, state, dg] = run_pll(z, fs, fn, s2)
% 统一入口: gate='always' 纯 NCO (CNR sweep 的隔离门要求).
  global VHET
  [y, phi, state, dg] = pll_carrier_regen(z, fs, fn, max(s2, 1e-12), ...
      struct('zeta', VHET.P.ZETA, 'gate', 'always'));
end


% ================================================================== H0
function H0()
  global VHET
  P = VHET.P;
  MODES = VHET.MODES;
  print_header(sprintf(['H0  三档参数表 [自研规则] + 硬边界   (lambda=632.8nm, ' ...
      'fs=%.0fMHz, B_frontend=%.1fMHz, f_dev_max=%.1fMHz, zeta=%g)'], ...
      P.FS / 1e6, P.B_FRONTEND / 1e6, P.F_DEV_MAX / 1e6, P.ZETA));
  fprintf(['  混叠极限 v_alias = lambda*fs/4      = %.3f m/s   ' ...
           '(fs 只决定这一条, 不是噪声带宽 -- H1 验证)\n'], het_v_alias_limit());
  fprintf(['  IF 硬窗  v_if    = lambda*f_dev/2   = %.3f m/s   ' ...
           '(与 ENBW 是两个参数)\n'], het_v_if_limit());
  fprintf(['  B_loop = %.4f*fn (单边 ENBW), f_3dB = %.4f*fn' ...
           ' = 纯 NCO 架构的测量带宽\n'], P.B_LOOP_COEF, P.F3DB_COEF);
  fprintf('\n  fn(mode, v_range, acq_bw=1MHz, f_acc_cap=100kHz):\n');
  fprintf(['  %9s | %6s %9s %9s %9s %13s %12s %13s %9s %6s\n'], ...
          'v_range', '档', 'fn', 'f_3dB', 'B_loop', 'a_design(e=1)', ...
          'a_slip(e=pi)', '浴缸谷(e=pi)', '降噪vsOFF', 'fs/50');
  ok_guard = true;
  vrs = [0.01, 0.1, 1.0, 3.0, 10.0];
  for iv = 1:numel(vrs)
    vr = vrs(iv);
    modes = het_mode_params(vr);
    for im = 1:numel(P.ORDER)
      name = P.ORDER{im};
      m = modes.(name);
      okd = het_fn_discrete_ok(m.fn);
      if vr <= 3.0 && ~okd
        ok_guard = false;
      end
      if vr == 10.0 && strcmp(name, 'FAST') && okd
        ok_guard = false;
      end
      if strcmp(name, 'SLOW')
        head = sprintf('  %7.2fm/s |', vr);
      else
        head = sprintf('  %9s |', '');
      end
      if okd
        oks = 'ok';
      else
        oks = 'FAIL';
      end
      fprintf('%s %6s %7.1fk %7.1fk %7.1fk %13.3g %12.3g %9.2fmm/s %+8.1fdB %6s\n', ...
              head, name, m.fn / 1e3, m.f_3db / 1e3, m.B_loop / 1e3, ...
              m.a_design, m.a_slip, m.valley_v * 1e3, m.noise_red_db, oks);
    end
  end
  mp10 = het_mode_params(10.0);
  check('C01', ['离散稳定守卫 fn<=fs/50: v_range<=3 m/s 全过, 10 m/s FAST 触发' ...
        ' (实机需提高 fs 或降 f_acc_cap)'], ok_guard, ...
        sprintf('fn(FAST,10m/s)=%.0fk vs fs/50=%.0fk', ...
                mp10.FAST.fn / 1e3, P.FS / 50 / 1e3));
  fprintf('\n  选档演示 (外差: 档位同时定测量带宽与动态, f_3dB 是硬约束):\n');
  demo = [20e3, 0.05; 100e3, 0.05; 100e3, 1.0; 5e6, 0.01];
  for r = 1:size(demo, 1)
    f0 = demo(r, 1);
    vp = demo(r, 2);
    sel = het_select_mode(f0, vp);
    extra = '';
    if f0 > MODES.FAST.f_3db
      extra = ', 5MHz>f_3dB(FAST): 只能 FAST+频响校正';
    end
    fprintf('    f_target=%7.0fkHz, v_peak=%5.0fmm/s -> %s   (f_3dB=%.0fk%s)\n', ...
            f0 / 1e3, vp * 1e3, sel, MODES.(sel).f_3db / 1e3, extra);
  end
end


% ================================================================== H1
function out = H1()
  global VHET
  P = VHET.P;
  MODES = VHET.MODES;
  nseed = 3;
  cnr_db = 20.0;
  df_off = 20e3;
  fnM = MODES.MEDIUM.fn;
  print_header(sprintf(['H1  四层带宽敏感性: fs vs B_frontend vs B_loop  ' ...
      '(CNR=%.0fdB, 载波偏 %.0fkHz, %d seeds, 环内相位噪声方差)'], ...
      cnr_db, df_off / 1e3, nseed));
  s2 = 10 ^ (-cnr_db / 10);

  keys = {'base', 'fs', 'Bf', 'SLOW', 'FAST'};
  labels = {'base  fs=50M  Bf=19M   fn=MED', ...
            'fs x2 fs=100M Bf=19M   fn=MED', ...
            'Bf /2 fs=50M  Bf=9.5M  fn=MED', ...
            'SLOW  fs=50M  Bf=19M   fn=SLOW', ...
            'FAST  fs=50M  Bf=19M   fn=FAST'};
  fss = [P.FS, 100e6, P.FS, P.FS, P.FS];
  Bfs = [P.B_FRONTEND, P.B_FRONTEND, 9.5e6, P.B_FRONTEND, P.B_FRONTEND];
  fns = [fnM, fnM, fnM, MODES.SLOW.fn, MODES.FAST.fn];
  out = struct();
  fprintf('\n  %-34s %8s %9s %12s %12s %7s\n', ...
          '配置', 'fn', 'B_loop', 'sigma2 理论', 'sigma2 实测', '偏差');
  for i = 1:5
    th = s2 * het_b_loop(fns(i)) / Bfs(i);
    me = sigma2_phi(fss(i), Bfs(i), fns(i), df_off, nseed, s2);
    out.(keys{i}) = [th, me];
    fprintf('  %-34s %6.1fk %7.1fk %12.3e %12.3e %+6.2fdB\n', ...
            labels{i}, fns(i) / 1e3, het_b_loop(fns(i)) / 1e3, th, me, ...
            10 * log10(me / th));
  end

  d_base = 10 * log10(out.base(2) / out.base(1));
  check('C11', 'sigma_phi^2 与理论 s2*B_loop/B_frontend 吻合 (+-2dB)', ...
        abs(d_base) < 2.0, sprintf('base 偏差 %+.2f dB', d_base));
  d_fs = 10 * log10(out.fs(2) / out.base(2));
  check('C12', ['fs 50->100MHz (同 B_frontend): sigma_phi^2 不变 (<1.5dB) ' ...
        '-- fs 不是噪声带宽'], abs(d_fs) < 1.5, sprintf('%+.2f dB', d_fs));
  r_bf = out.Bf(2) / out.base(2);
  check('C13', 'B_frontend 19->9.5MHz (同带内CNR): 方差 x2 (N0 翻倍)', ...
        1.5 < r_bf && r_bf < 2.7, sprintf('x%.2f', r_bf));
  r1 = out.FAST(2) / out.base(2);
  r2 = out.base(2) / out.SLOW(2);
  check('C14', '三档方差比 = B_loop 比 = sqrt(10) 每档 (x2.2..4.5)', ...
        2.2 < r1 && r1 < 4.5 && 2.2 < r2 && r2 < 4.5, ...
        sprintf('FAST/MED x%.2f, MED/SLOW x%.2f', r1, r2));
  fprintf(['  结论: 环内噪声只看 B_frontend 与 B_loop; 采样率翻倍不改变任何噪声,' ...
           ' 三档灵敏度差每档 5 dB。\n']);
end

function m = sigma2_phi(fs, Bf, fn, df_off, nseed, s2)
  global VHET
  T = 1.5e-3;
  skip = 0.7e-3;
  N = floor(T * fs);
  t = (0:N - 1)' / fs;
  ph = 2 * pi * df_off * t;
  vs = zeros(nseed, 1);
  for s = 0:nseed - 1
    set_rng(41000 + s);
    z = exp(1i * ph) + complex_bandlimited_noise(N, fs, Bf, s2, ...
                                                 @(k) randn(k, 1));
    [~, phi, ~, ~] = pll_carrier_regen(z, fs, fn, s2, ...
        struct('zeta', VHET.P.ZETA, 'gate', 'always'));
    e = angle(exp(1i * (phi - ph)));
    e = e(t > skip);
    vs(s + 1) = mean((e - mean(e)) .^ 2);
  end
  m = stats(vs);
end


% ================================================================== H2
function p = scene_params(f0)
  if f0 == 50e3
    p = struct('ncyc', 10, 't0', 0.15e-3, 'T', 0.8e-3, 'L', 8192, ...
               'band', [10e3, 90e3], 'q0', 0.40e-3, 'q1', 0.78e-3);
  else
    p = struct('ncyc', 40, 't0', 0.10e-3, 'T', 0.3e-3, 'L', 4096, ...
               'band', [4e6, 6e6], 'q0', 0.13e-3, 'q1', 0.29e-3);
  end
end

function sc = make_scene(f0, VAMP, DF_OFF)
  global VHET
  P = VHET.P;
  p = scene_params(f0);
  N = floor(p.T * P.FS);
  t = (0:N - 1)' / P.FS;
  [x, v, ~] = burst_signal(t, f0, VAMP, p.ncyc, p.t0);
  ph = 4 * pi / P.LAMBDA * x + 2 * pi * DF_OFF * t;
  Wm = (t > p.t0) & (t < p.t0 + p.ncyc / f0);
  Wq = (t > p.q0) & (t < p.q1);
  sc = struct('f0', f0, 'N', N, 't', t, 'v', v, 'ph', ph, ...
              'Wm', Wm, 'Wq', Wq, 'p', p);
end

function res = H2()
  global VHET
  P = VHET.P;
  MODES = VHET.MODES;
  nseed = 6;
  cnrs = [0, 4, 10, 20];
  VAMP = 10e-3;
  DF_OFF = 20e3;
  print_header(sprintf(['H2  三档弱光 CNR sweep -- 50 kHz 结构 burst + 5 MHz ' ...
      'PSV类超声 burst (vamp=%.0fmm/s, 载波偏 %.0fkHz, B_frontend=%.0fMHz, ' ...
      '%d seeds, R1-R4 规则, gate=always)'], VAMP * 1e3, DF_OFF / 1e3, ...
      P.B_FRONTEND / 1e6, nseed));
  f0s = [50e3, 5e6];
  res = struct();
  scen_keys = {'f50k', 'f5M'};
  for fi = 1:2
    f0 = f0s(fi);
    sc = make_scene(f0, VAMP, DF_OFF);
    t = sc.t;
    p = sc.p;
    % ---- R1: 近无噪信号传递 (含 |H_L| 频响信息) ----
    zc = exp(1i * sc.ph);
    a_true = lockin_amp(sc.v, t, f0, sc.Wm);
    a_off_c = lockin_amp(vdisc(zc), t, f0, sc.Wm);
    row = struct();
    for im = 1:numel(P.ORDER)
      name = P.ORDER{im};
      fn = MODES.(name).fn;
      y = run_pll(zc, P.FS, fn, 1e-10);
      a_on_c = lockin_amp(vdisc(y), t, f0, sc.Wm);
      H = hl_mag(f0, fn);
      r = struct('ratio_raw', a_on_c / a_true, ...
                 'err_corr', 100 * (a_on_c / H / a_true - 1), ...
                 'g_sig', 20 * log10(max(a_on_c, VHET.TINY) ...
                                     / max(a_off_c, VHET.TINY)), ...
                 'H', H);
      for c = cnrs
        r.(sprintf('gains_c%d', c)) = [];
        r.(sprintf('nred_c%d', c)) = [];
      end
      row.(name) = r;
    end
    % ---- R2/R3/R4: 噪声窗 + 多种子 ----
    for c = cnrs
      s2 = 10 ^ (-c / 10);
      for s = 0:nseed - 1
        set_rng(42000 + floor(f0 / 1e3) + 97 * s);
        z = exp(1i * sc.ph) ...
            + complex_bandlimited_noise(sc.N, P.FS, P.B_FRONTEND, s2, ...
                                        @(k) randn(k, 1));
        a_off = asd_band(vdisc(z), sc.Wq, P.FS, p.L, p.band(1), p.band(2));
        for im = 1:numel(P.ORDER)
          name = P.ORDER{im};
          y = run_pll(z, P.FS, MODES.(name).fn, s2);
          a_on = asd_band(vdisc(y), sc.Wq, P.FS, p.L, p.band(1), p.band(2));
          nr = 20 * log10(a_off / a_on);
          row.(name).(sprintf('nred_c%d', c))(end + 1) = nr;
          row.(name).(sprintf('gains_c%d', c))(end + 1) = row.(name).g_sig + nr;
        end
      end
    end
    fprintf(['\n  f0 = %.0f kHz burst (%d cyc), 谱线 SNR 增益 vs OFF ' ...
             '(R3 = R1信号传递 + R2噪声窗中值, R4 中值[p10,p90]):\n'], ...
            f0 / 1e3, p.ncyc);
    fprintf('    %6s %8s %9s %11s %9s |', '档', 'fn', '|H_L(f0)|', ...
            '未校正幅值比', '校正后err');
    for c = cnrs
      fprintf('%24s', sprintf('CNR%ddB', c));
    end
    fprintf('\n');
    for im = 1:numel(P.ORDER)
      name = P.ORDER{im};
      r = row.(name);
      cells = '';
      for c = cnrs
        [m, lo, hi] = stats(r.(sprintf('gains_c%d', c)));
        cells = [cells, sprintf('  %+6.1f[%+6.1f,%+6.1f]', m, lo, hi)];
      end
      fprintf('    %6s %6.1fk %9.4f %11.4f %+8.2f%% |%s\n', ...
              name, MODES.(name).fn / 1e3, r.H, r.ratio_raw, r.err_corr, cells);
    end
    fprintf('    未校正底噪下降 (raw ASD_off/ASD_on, 中值):');
    for im = 1:numel(P.ORDER)
      name = P.ORDER{im};
      fprintf('  %s %+.1fdB@CNR4', name, stats(row.(name).nred_c4));
    end
    fprintf('\n');
    res.(scen_keys{fi}) = row;
  end
  fprintf(['\n  物理解读: 档位=测量带宽 (纯NCO无残差窗): SLOW/MED 在 5 MHz 幅值' ...
           '结构性塌掉 (|H_L|),\n  FAST 衰减数倍但可用已知 |H_L| 校正 -- 复现用户' ...
           ' PSV-500 ''10 MHz FAST 幅值衰减数倍'' 现象;\n  增益本质是 FM 门限扩展:' ...
           ' 高 CNR 下 OFF 无点击, 谱线增益归零 (校正不改变 SNR)。\n']);

  r50 = res.f50k;
  r5M = res.f5M;
  g0 = stats(r50.SLOW.gains_c0);
  g4 = stats(r50.SLOW.gains_c4);
  g20 = stats(r50.SLOW.gains_c20);
  check('C21', 'SLOW@50kHz: 谱线SNR增益 CNR=0 >10dB 且 CNR=4 >6dB (门限扩展)', ...
        g0 > 10.0 && g4 > 6.0, ...
        sprintf('CNR0 %+.1f dB, CNR4 %+.1f dB', g0, g4));
  check('C22', 'SLOW@50kHz: 增益(CNR0)-增益(CNR20) >6dB -- 增益只在门限以下', ...
        g0 - g20 > 6.0, sprintf('%+.1f - (%+.1f) = %.1f dB', g0, g20, g0 - g20));
  nF4 = stats(r5M.FAST.nred_c4);
  gF4 = stats(r5M.FAST.gains_c4);
  check('C23', ['FAST@5MHz CNR=4: 未校正底噪下降 >10dB (复现用户 PSV-500 ' ...
        '弱回光实测) 且谱线SNR增益 |中值|<3dB (底噪下降与信号衰减同源 |H_L|, ' ...
        '点击增益只在低频)'], nF4 > 10.0 && abs(gF4) < 3.0, ...
        sprintf('底噪 %+.1f dB, 谱线SNR %+.1f dB', nF4, gF4));
  rr = r5M.FAST.ratio_raw;
  ec = r5M.FAST.err_corr;
  check('C24', ['FAST@5MHz: 未校正幅值衰减数倍 (0.1<比<0.5) 且频响校正后 ' ...
        '|err|<10%'], 0.1 < rr && rr < 0.5 && abs(ec) < 10.0, ...
        sprintf('比 %.3f (x%.1f 衰减), 校正后 %+.2f%%', rr, 1 / rr, ec));
  worst50 = 0;
  for im = 1:numel(P.ORDER)
    worst50 = max(worst50, abs(r50.(P.ORDER{im}).err_corr));
  end
  check('C25', '50kHz 谱线: 三档频响校正后 |err|<5% (校正用精确离散 H_L)', ...
        worst50 < 5.0, sprintf('worst %.2f%%', worst50));
  rs = r5M.SLOW.ratio_raw;
  check('C26', ['SLOW@5MHz: 未校正幅值比 <0.05 -- 外差档位=测量带宽, ' ...
        '无零差残差窗兜底'], rs < 0.05, sprintf('%.4f', rs));
end


% ================================================================== H3
function res = H3()
  global VHET
  P = VHET.P;
  nseed = 4;
  cnr_db = 10.0;
  f_v = 1e5;
  fixed_fn = 400e3;
  print_header(sprintf(['H3  量程扫描: fn 参数化 vs 固定 fn=%.0fk ' ...
      '(旧硬编码 FAST)  -- 正弦 v_range@%.0fkHz (=f_acc 设计点), ' ...
      'CNR=%.0fdB, %d seeds'], fixed_fn / 1e3, f_v / 1e3, cnr_db, nseed));
  s2 = 10 ^ (-cnr_db / 10);
  t_pre = 0.20e-3;               % 先静止入锁, 再从 v=0 起振 (解耦捕获)
  T = t_pre + 8 / f_v;
  N = floor(T * P.FS);
  t = (0:N - 1)' / P.FS;
  td = max(t - t_pre, 0.0);
  on = double(t >= t_pre);
  sel = t > t_pre + 3 / f_v;
  fprintf('\n  %9s %10s | %-10s %8s %10s %13s %5s %17s\n', ...
          'v_range', 'a_pk', '方案', 'fn', 'a_slip', '幅值err(校正)', ...
          '周跳', '噪声增益dB');
  vrs = [0.01, 0.1, 0.3, 1.0, 3.0];
  res = struct('param', cell(1, numel(vrs)), 'fixed', cell(1, numel(vrs)));
  for iv = 1:numel(vrs)
    vr = vrs(iv);
    a_pk = 2 * pi * f_v * vr;
    x = on .* (vr / (2 * pi * f_v)) .* (1 - cos(2 * pi * f_v * td));
    v_true = on .* vr .* sin(2 * pi * f_v * td);
    ph = 4 * pi / P.LAMBDA * x;
    a_true = ls_amp(v_true, t, f_v, sel);
    mp = het_mode_params(vr);
    fn_par = mp.FAST.fn;
    tags = {'param', 'fixed'};
    fnv = [fn_par, fixed_fn];
    for it = 1:2
      fn = fnv(it);
      errs = zeros(nseed, 1);
      slips = zeros(nseed, 1);
      gains = zeros(nseed, 1);
      H = hl_mag(f_v, fn);
      for s = 0:nseed - 1
        set_rng(43000 + floor(vr * 1e4) + 31 * s);
        z = exp(1i * ph) ...
            + complex_bandlimited_noise(N, P.FS, P.B_FRONTEND, s2, ...
                                        @(k) randn(k, 1));
        a_off = asd_band(vdisc(z), sel, P.FS, 4096, 0.45e6, 2.9e6);
        [y, ~, ~, dg] = run_pll(z, P.FS, fn, s2);
        v_on = vdisc(y);
        errs(s + 1) = 100 * (ls_amp(v_on, t, f_v, sel) / H / a_true - 1);
        slips(s + 1) = dg.near_pi_events;
        gains(s + 1) = 20 * log10( ...
            a_off / asd_band(v_on, sel, P.FS, 4096, 0.45e6, 2.9e6));
      end
      [gm, gl, gh] = stats(gains);
      row = struct('fn', fn, 'err', stats(errs), 'slip', stats(slips), ...
                   'gain', [gm, gl, gh]);
      res(iv).(tags{it}) = row;
      a_sl = pi ^ 2 * P.LAMBDA * fn ^ 2;
      if it == 1
        head = sprintf('  %6.0fmm/s %10.3g |', vr * 1e3, a_pk);
      else
        head = sprintf('  %9s %10s |', '', '');
      end
      fprintf('%s %-10s %6.1fk %10.3g %+12.1f%% %5.0f %+6.1f[%+5.1f,%+5.1f]\n', ...
              head, tags{it}, fn / 1e3, a_sl, row.err, row.slip, ...
              gm, gl, gh);
    end
  end
  fprintf(['\n  解读: 固定 400k 档在小量程浪费 8.5dB(B_loop 比) 灵敏度, 在 3 m/s' ...
           ' (a_pk=1.9e6 > a_slip=1.0e6) 失锁;\n  参数化 fn 全量程贴着 e=1 设计线' ...
           ' (a_pk = a_design), 幅值与锁定都保持。\n']);
  ok31 = true;
  det = '';
  for iv = 1:numel(vrs)
    ok31 = ok31 && abs(res(iv).param.err) < 10 && res(iv).param.slip == 0;
    det = [det, sprintf('%g:%+.1f%%, ', vrs(iv), res(iv).param.err)];
  end
  check('C31', '参数化 fn: 全量程 |校正幅值误差|<10% 且 0 周跳 (e=1 设计线可用)', ...
        ok31, det(1:end - 2));
  fx3 = res(5).fixed;
  check('C32', '3 m/s: 固定 fn=400k 失锁 (周跳>0 或 |err|>30%), 参数化保持<10%', ...
        (fx3.slip > 0 || abs(fx3.err) > 30) && abs(res(5).param.err) < 10, ...
        sprintf('fixed err %+.1f%% slip %.0f vs param %+.1f%%', ...
                fx3.err, fx3.slip, res(5).param.err));
  dg33 = res(1).param.gain(1) - res(1).fixed.gain(1);
  mp001 = het_mode_params(0.01);
  check('C33', '10 mm/s: 参数化 fn 噪声增益比固定 fn 高 >5dB (量程小 -> 环窄)', ...
        dg33 > 5.0, sprintf('%+.1f dB (理论 B_loop 比 %.1f dB)', dg33, ...
        10 * log10(fixed_fn / mp001.FAST.fn)));
end


% ================================================================== H4
function [err, slips, e_off] = h4_one(f_v, vamp, t_pre, s2, fn)
  global VHET
  P = VHET.P;
  T = t_pre + max(8 / f_v, 60e-6);
  N = floor(T * P.FS);
  t = (0:N - 1)' / P.FS;
  td = max(t - t_pre, 0.0);
  on = double(t >= t_pre);
  sel = t > t_pre + max(3 / f_v, 25e-6);
  x = on .* (vamp / (2 * pi * f_v)) .* (1 - cos(2 * pi * f_v * td));
  v_true = on .* vamp .* sin(2 * pi * f_v * td);
  ph = 4 * pi / P.LAMBDA * x;
  z = exp(1i * ph) + complex_bandlimited_noise(N, P.FS, P.B_FRONTEND, s2, ...
                                               @(k) randn(k, 1));
  a_true = ls_amp(v_true, t, f_v, sel);
  [y, ~, ~, dg] = run_pll(z, P.FS, fn, s2);
  err = 100 * (ls_amp(vdisc(y), t, f_v, sel) / hl_mag(f_v, fn) / a_true - 1);
  e_off = 100 * (ls_amp(vdisc(z), t, f_v, sel) / a_true - 1);
  slips = dg.near_pi_events;
end

function bounds = H4()
  global VHET
  P = VHET.P;
  fn = VHET.MODES.MEDIUM.fn;
  cnr_db = 30.0;
  print_header(sprintf(['H4  浴缸形动态边界复现 (MEDIUM fn=%.1fk, 纯PLL, ' ...
      'e_crit=pi 卷绕线理论 vs 实测夹逼, CNR=%.0fdB, 频响校正测幅)'], ...
      fn / 1e3, cnr_db));
  s2 = 10 ^ (-cnr_db / 10);
  t_pre = 0.20e-3;
  mults = [0.5, 0.71, 1.0, 1.41, 2.0];
  freqs = [fn / 8, fn / 3, fn, 3 * fn, 8 * fn];
  set_rng(44000);        % Python: single rng shared across all one() calls

  fprintf(['\n  理论: v_pi(f) = pi*lambda*f/2/|1-H_L|, 谷底 (f=fn, ' ...
           '%.0f mm/s = pi*lambda*fn/sqrt2)\n'], het_v_pll_limit(fn, fn) * 1e3);
  fprintf('  %9s %7s %10s |', 'f_v', 'x=f/fn', 'v_pi 理论');
  for m = mults
    fprintf('%14s', sprintf('%.2fv_pi', m));
  end
  fprintf(' | %9s\n', '实测边界');
  bounds = zeros(1, numel(freqs));
  ok41 = true;
  e_off_ref = NaN;
  for fi = 1:numel(freqs)
    f_v = freqs(fi);
    v_pi = het_v_pll_limit(f_v, fn);
    cells = '';
    passed = 0.0;
    for mi = 1:numel(mults)
      mlt = mults(mi);
      [err, slips, e_off] = h4_one(f_v, mlt * v_pi, t_pre, s2, fn);
      good = (slips == 0) && (abs(err) < 25);
      if good
        passed = mlt * v_pi;
      end
      cells = [cells, sprintf('  %+7.1f%%/%ds', err, slips)];
      if f_v == fn && abs(mlt - 2.0) < 1e-9
        e_off_ref = e_off;
      end
    end
    [e1, s1] = h4_one(f_v, 0.5 * v_pi, t_pre, s2, fn);
    [e2, s2b] = h4_one(f_v, 2.0 * v_pi, t_pre, s2, fn);
    ok_f = (s1 == 0 && abs(e1) < 25) && (s2b > 0 || abs(e2) > 25);
    ok41 = ok41 && ok_f;
    bounds(fi) = passed;
    if ok_f
      mark = '';
    else
      mark = '  <-- 未夹住';
    end
    fprintf('  %7.1fk %7.2f %8.1fmm |%s | %7.1fmm%s\n', ...
            f_v / 1e3, f_v / fn, v_pi * 1e3, cells, passed * 1e3, mark);
  end
  check('C41', ['5 个频点: 0.5*v_pi 全通过 且 2*v_pi 全失败 -- 实测边界夹在' ...
        '理论卷绕线 2 倍以内'], ok41, 'err<25% 且 0 周跳 为通过判据');
  ok42 = bounds(3) < bounds(1) && bounds(3) < bounds(end);
  check('C42', ['浴缸形: 谷底在 f=fn (低频侧受 a_slip, 高频侧受相位摆幅, ' ...
        '谷值 pi*lambda*fn/sqrt2)'], ok42, ...
        sprintf('边界 %.0f / %.0f / %.0f mm/s @ fn/8, fn, 8fn', ...
                bounds(1) * 1e3, bounds(3) * 1e3, bounds(end) * 1e3));
  check('C43', ['OFF 鉴频器 @f=fn, v=2*v_pi 无边界 (|err|<5%) -- 浴缸边界是' ...
        '跟踪环自身的代价'], abs(e_off_ref) < 5.0, ...
        sprintf('OFF err %+.2f%%', e_off_ref));
  fprintf(['  整机包络 = min(纯PLL边界, v_if=%.2f m/s, v_alias=%.2f m/s)' ...
           ' -- 高频翼被 IF 硬窗截平。\n'], het_v_if_limit(), het_v_alias_limit());
end


% ================================================================== H5+H6
function res = H56()
  global VHET
  P = VHET.P;
  nseed = 6;
  cnr_db = 6.0;
  f_v = 10e3;
  T = 0.6e-3;
  print_header(sprintf(['H5+H6  e_crit=1 vs pi 边界 + 固定 preLP(同 B_loop) ' ...
      '对照 (t5/o5 复现: 振动 %.0fkHz, 前端被量程强制 B_front=2*f_D, ' ...
      'CNR=%.0fdB, %d seeds)'], f_v / 1e3, cnr_db, nseed));
  s2 = 10 ^ (-cnr_db / 10);
  N = floor(T * P.FS);
  t = (0:N - 1)' / P.FS;
  sel = t > 1.5 / f_v;
  vrs = [0.05, 0.2, 0.6, 1.5, 3.0];
  res = [];   % struct array built below (identical fields every iteration)
  fprintf('\n  %8s %7s %8s %8s %8s %6s | %8s %9s %10s | %8s %9s\n', ...
          'v_range', 'f_D', 'B_front', 'fn(e1)', 'B_loop', 'ceil', ...
          'err e1', 'err epi', 'err preLP', 'PLL增益', 'preLP增益');
  for iv = 1:numel(vrs)
    vr = vrs(iv);
    fD = 2 * vr / P.LAMBDA;
    B_front = 2 * fD;              % 前端被速度量程强制, 不可收窄
    if B_front > P.FS / 2
      continue;
    end
    a_pk = 2 * pi * f_v * vr;
    fn1 = het_fn_from_a(a_pk, [], 1.0);
    fnp = het_fn_from_a(a_pk, [], pi);
    B_loop1 = het_b_loop(fn1);
    x = (vr / (2 * pi * f_v)) * (1 - cos(2 * pi * f_v * t));
    v_true = vr * sin(2 * pi * f_v * t);
    ph = 4 * pi / P.LAMBDA * x;
    a_true = ls_amp(v_true, t, f_v, sel);

    E1 = zeros(nseed, 1); EP = zeros(nseed, 1); EL = zeros(nseed, 1);
    G1 = zeros(nseed, 1); GL = zeros(nseed, 1); SP = zeros(nseed, 1);
    for s = 0:nseed - 1
      set_rng(45000 + floor(vr * 100) + 13 * s);
      z = exp(1i * ph) + complex_bandlimited_noise(N, P.FS, B_front, s2, ...
                                                   @(k) randn(k, 1));
      v_off = vdisc(z);
      v_pre = vdisc(complex_lp(z, B_loop1, P.FS, 401));
      y1 = run_pll(z, P.FS, fn1, s2);
      [yp, ~, ~, dgp] = run_pll(z, P.FS, fnp, s2);
      E1(s + 1) = 100 * (ls_amp(vdisc(y1), t, f_v, sel) / a_true - 1);
      EP(s + 1) = 100 * (ls_amp(vdisc(yp), t, f_v, sel) / a_true - 1);
      EL(s + 1) = 100 * (ls_amp(v_pre, t, f_v, sel) / a_true - 1);
      a_off = asd_band(v_off, sel, P.FS, 4096, 3 * f_v, 30 * f_v);
      G1(s + 1) = 20 * log10(a_off / asd_band(vdisc(y1), sel, P.FS, 4096, ...
                                              3 * f_v, 30 * f_v));
      GL(s + 1) = 20 * log10(a_off / asd_band(v_pre, sel, P.FS, 4096, ...
                                              3 * f_v, 30 * f_v));
      SP(s + 1) = dgp.near_pi_events;
    end
    r = struct('fD', fD, 'B_front', B_front, 'fn1', fn1, 'B_loop', B_loop1, ...
               'ceil', 10 * log10(fD / B_loop1), ...
               'e1', stats(E1), 'epi', stats(EP), 'epre', stats(EL), ...
               'g1', stats(G1), 'gl', stats(GL), 'sp', stats(SP));
    if isempty(res)
      res = r;
    else
      res(iv) = r;
    end
    fprintf(['  %6.2fm %6.2fM %7.1fM %6.1fk %6.1fk %+5.1f | %+7.1f%% ' ...
             '%+8.1f%% %+9.1f%% | %+7.2f %+8.2f\n'], ...
            vr, r.fD / 1e6, r.B_front / 1e6, fn1 / 1e3, B_loop1 / 1e3, ...
            r.ceil, r.e1, r.epi, r.epre, r.g1, r.gl);
  end
  fprintf(['\n  解读 (o5 已证, 此处以本三档规则复核): e_crit=pi 是卷绕线 -- 在' ...
           '边界上设计必失败;\n  e_crit=1 是设计线 -- 幅值保持且拿到谱线增益。' ...
           '外差前端被量程强制到 2*f_D 宽,\n  固定 preLP 收窄到 B_loop 会让走动' ...
           '的载波出通带 -> 幅值崩溃; 这就是外差跟踪滤波\n  相对固定滤波的唯一' ...
           '结构性价值 (零差场景里固定 LP 反而够用, 见 homodyne V2/o4-E8)。\n']);
  ok51 = true; ok52 = true; ok53 = true; ok61 = true;
  d51 = ''; d52 = ''; d53 = ''; d61 = '';
  for iv = 1:numel(vrs)
    ok51 = ok51 && abs(res(iv).e1) < 10;
    ok52 = ok52 && res(iv).epi < -30;
    ok53 = ok53 && res(iv).g1 > 3.0;
    ok61 = ok61 && res(iv).epre < -15 ...
           && (vrs(iv) < 0.2 || res(iv).epre < -80);
    d51 = [d51, sprintf('%g:%+.1f%%, ', vrs(iv), res(iv).e1)];
    d52 = [d52, sprintf('%g:%+.0f%%, ', vrs(iv), res(iv).epi)];
    d53 = [d53, sprintf('%g:%+.1f, ', vrs(iv), res(iv).g1)];
    d61 = [d61, sprintf('%g:%+.0f%%, ', vrs(iv), res(iv).epre)];
  end
  check('C51', 'e_crit=1 设计线: 全部量程 |幅值误差|<10% (o5: 最大 +5.8%)', ...
        ok51, d51(1:end - 2));
  check('C52', ['e_crit=pi 卷绕线: 全部量程幅值误差 <-30% -- 在失败边界上' ...
        '设计保证失败 (o5: -47..-96%)'], ok52, d52(1:end - 2));
  check('C53', 'e_crit=1: PLL 谱线噪声增益 >+3dB 全量程 (o5: +7.8..+25.3)', ...
        ok53, d53(1:end - 2));
  check('C61', ['固定 preLP(同 B_loop): 全量程 <-15%, v>=0.2 m/s <-80% 崩溃 ' ...
        '(载波走出固定通带)'], ok61, d61(1:end - 2));
  i15 = find(vrs == 1.5);
  check('C62', ['v=1.5 m/s: PLL |err|<10% 而 preLP <-80% -- 同噪声带宽下' ...
        '只有跟踪能保住信号 (外差大频偏场景)'], ...
        abs(res(i15).e1) < 10 && res(i15).epre < -80, ...
        sprintf('PLL %+.1f%% vs preLP %+.1f%%', res(i15).e1, res(i15).epre));
end
