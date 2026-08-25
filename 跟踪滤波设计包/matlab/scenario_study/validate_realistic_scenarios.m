function rc = validate_realistic_scenarios(mode)
%VALIDATE_REALISTIC_SCENARIOS Realistic-scenario study: homodyne + heterodyne (FULL).
%
%   rc = validate_realistic_scenarios()        full study (only mode)
%   rc = validate_realistic_scenarios('full')  same (interface compat)
%
%   Full MATLAB/Octave port of scenario_study/validate_realistic_scenarios.py
%   (this file REPLACES the earlier interface stub, same name / call
%   signature / output contract).  Same scenarios, same seeds, same
%   PASS/FAIL criteria:
%
%   Homodyne (1550 nm, user app v_peak <= 30 m/s, f <= 100 kHz typical)
%     S1  operating map   f={1,10,50,100}k x v={0.02,1,5,20,30}m/s x
%                         CNR={3,6,12}dB: clean amp err, SNR gain (R2
%                         static-carrier noise drop, labelled as such),
%                         gear, guard flags; 86 MHz+LPF physical front end
%                         exactly on the cells where the Doppler peak
%                         fD = 2*v_peak/LAMBDA exceeds B_NOISE_ENBW/2
%                         (fixed hardware -- velocity, NOT vibration
%                         frequency, sets the front-end model); plus the
%                         S1e dynamic spot check (3 cells, full noisy
%                         dynamic runs on the actual motion).
%     S2  speckle matrix  tau_c={20,50,100}us x CNR={3,6,12}dB @100kHz/20mm/s.
%     S3  transients      freq step 50k->100kHz, vel step 5->30 m/s (5 seeds)
%                         + WRONG-gear exposure window measurement; upshift
%                         immediacy asserted on the T3 SLOW->FAST trace
%                         (T2 is FAST->FAST on both sides, audit issue 2).
%     S4  multi-surface   reflective -> black -> far (CNR 12/6/3 dB, 20 us
%                         gaps), relock time / per-segment lock% and amp err.
%     S5  worst corner    100kHz/30m/s + speckle 50us + CNR=3dB (honest).
%
%   Heterodyne (HeNe 632.8 nm, fs=50 MS/s, B_frontend=19 MHz)
%     H1  range-velocity map  v_range={0.1,1,3} x f={50k,500k,5M} x CNR.
%     H2  beyond f_3dB        5 MHz all gears, raw vs corrected (C24/C26).
%     H3  bathtub bracketing  0.5*v_pi pass / 2*v_pi fail at f=fn per gear.
%     H4  weak return         FAST@5MHz CNR 0..8 dB noise-floor drop.
%
%   Cross-comparison
%     X1  same motion (100 kHz, 20 mm/s) homodyne SLOW vs heterodyne SLOW
%         with the honest apples/oranges note.
%
%   Noise realizations are IDENTICAL to Python (numpy-exact np_rng_new
%   kernel, same seed formulas), so every "KEY," metric matches the Python
%   reference within FP/FFT rounding (<< 5%).  No MEX required: everything
%   falls back to the pure-M twins (np_rng_m / pll_core_m) when no compiler
%   is available (set HOMODYNE_NO_MEX=1 to force that).
%
%   OUTPUT
%     - full tables on stdout (identical structure to the Python script),
%       plus machine-readable "KEY,name,value" lines;
%     - scenario_study/results_realistic_scenarios.txt   (this table text);
%     - scenario_study/results_realistic_scenarios.mat   (plotting contract
%       of plot_scenario_results.m: map_* / spk_* / bath_* fields, now with
%       is_stub=0, plus key_names/key_values of the full study).
%
%   Run (Octave):   cd matlab/scenario_study
%                   octave --no-gui --eval "rc=validate_realistic_scenarios(); exit(rc)"
%   Run (MATLAB):   cd matlab\scenario_study; rc = validate_realistic_scenarios
%
%   Returns rc = 0 iff all checks pass (same convention as the Python exit
%   code), so it can slot into CI / run_all_verify wrappers.
  if nargin < 1 || isempty(mode)
    mode = 'full';
  end %#ok<NASGU>  % single-mode interface kept for compatibility
  here = fileparts(mfilename('fullpath'));
  mroot = fileparts(here);
  addpath(mroot);
  homodyne_setup_path();
  addpath(fullfile(mroot, 'heterodyne'));
  addpath(fullfile(mroot, 'qtec'));
  ensure_kernels();

  reg_('reset');
  t0 = tic;
  K = consts_();

  out_('真实场景仿真套件: 零差(S1-S5) + 外差(H1-H4) + 交叉对照(X1)');
  out_(sprintf(['homodyne: lambda=1550nm fs=%.0fMS/s 三档 fn=110k/530k/1.6M ' ...
                'zeta=1.2 公共窗 %.0fMHz | heterodyne: lambda=%.1fnm ' ...
                'fs=%.0fMS/s zeta=%g 档位=f(v_range)'], K.FS / 1e6, ...
               K.B_WIN / 1e6, K.HLAM * 1e9, K.HFS / 1e6, K.HZ));
  out_(['规则: R1-R4 公平比较 (validate_tracking); 零差 fD_peak=2*v/lambda > ' ...
        '20MHz 的高速格点用 B_FE=86MHz+LPF 物理前端 (validate_app A6 v2 模型)']);

  [s1_cells, s1_cache] = S1_(K);
  S2_(K);
  S3_(K);
  S4_(K);
  S5_(K);
  H1_(K);
  H2_(K);
  H3_(K);
  H4_(K);
  X1_(K, s1_cells, s1_cache);

  header_('ASSERTION SUMMARY');
  CH = reg_('checks');
  allok = true;
  for i = 1:numel(CH)
    allok = allok && CH(i).ok;
    if CH(i).ok, tag = 'PASS'; else, tag = 'FAIL'; end
    out_(sprintf('  [%s] %s  %s  (%s)', tag, CH(i).cid, CH(i).label, ...
                 CH(i).detail));
  end
  if allok, msg = 'ALL CHECKS PASSED'; else, msg = 'SOME CHECKS FAILED'; end
  out_('');
  out_(msg);
  out_(sprintf('[elapsed %.1f s]', toc(t0)));

  out_('');
  out_(repmat('-', 1, 92));
  out_('KEY metrics (machine readable, for the Python<->MATLAB comparison):');
  KY = reg_('keys');
  for i = 1:numel(KY)
    out_(sprintf('KEY,%s,%.6g', KY(i).name, KY(i).val));
  end

  % ---------------------------------------------------------- results .txt
  txt = fullfile(here, 'results_realistic_scenarios.txt');
  fid = -1;
  try
    fid = fopen(txt, 'w', 'n', 'UTF-8');
  catch
  end
  if fid < 0
    fid = fopen(txt, 'w');
  end
  L = reg_('lines');
  for i = 1:numel(L)
    fprintf(fid, '%s\n', L{i});
  end
  fclose(fid);
  fprintf('[results saved to %s]\n', txt);

  % ------------------------------------- results .mat (plotting contract)
  save_contract_mat_(here, KY, CH);

  rc = double(~allok);
end


% ========================================================= shared constants
function K = consts_()
  dp = design_params();
  K.FS = dp.FS;
  K.LAMBDA = dp.LAMBDA;
  K.B_NOISE_ENBW = dp.B_NOISE_ENBW;
  K.B_WIN = dp.B_WIN;
  K.BANDS = dp.BANDS;
  K.ORDER = dp.ORDER;
  K.TINY = 1e-300;
  K.FE_NT = 1025;                       % front-end LPF taps (A6/A7/A8 model)
  K.B_FE_PHYS = 2 * dp.F_SIGNAL_MAX;    % 86 MHz physically consistent FE
  K.PAD = 1024;                         % FE-LPF edge guard cut after slicing
  K.T_ON = 5e-6;                        % motion onset: target starts FROM REST
  P = het_params();
  K.HFS = P.FS;
  K.HLAM = P.LAMBDA;
  K.HZ = P.ZETA;
  K.HBF = P.B_FRONTEND;
  K.HORDER = P.ORDER;
  K.H_DF = 20e3;
  K.H_VAMP = 10e-3;
end


% ============================================== output / check / key harness
function r = reg_(op, a, b, c, d)
  persistent LINES CHECKS KEYS
  r = [];
  switch op
    case 'reset'
      LINES = {};
      CHECKS = struct('cid', {}, 'label', {}, 'ok', {}, 'detail', {});
      KEYS = struct('name', {}, 'val', {});
    case 'line'
      LINES{end + 1} = a;
    case 'check'
      CHECKS(end + 1) = struct('cid', a, 'label', b, 'ok', logical(c), ...
                               'detail', d);
    case 'key'
      KEYS(end + 1) = struct('name', a, 'val', double(b));
    case 'lines'
      r = LINES;
    case 'checks'
      r = CHECKS;
    case 'keys'
      r = KEYS;
  end
end

function out_(s)
  if nargin < 1
    s = '';
  end
  fprintf('%s\n', s);
  reg_('line', s);
end

function key_(name, v)
  reg_('key', name, v);
end

function ok = check_(cid, label, ok, detail)
  reg_('check', cid, label, ok, detail);
  if ok, tag = 'PASS'; else, tag = 'FAIL'; end
  out_(sprintf('  [%s] %s  %s  (%s)', tag, cid, label, detail));
end

function header_(title)
  out_('');
  out_(repmat('=', 1, 92));
  out_(title);
  out_(repmat('=', 1, 92));
end


% ================================================== shared numeric helpers
function v = vdisc_h_(K, y)
  v = fm_discriminator(y, K.FS, K.LAMBDA);
end

function a = ls_amp_(v, t, f_v, sel)
%LS_AMP_ sin/cos least-squares amplitude (robust to phase / few cycles).
  v = v(:);
  t = t(:);
  sel = sel(:);
  ts = t(sel);
  X = [ones(numel(ts), 1), sin(2 * pi * f_v * ts), cos(2 * pi * f_v * ts)];
  b = X \ v(sel);
  a = hypot(b(2), b(3));
end

function [B_fe, lpf] = fe_rule_(K, vpk)
%FE_RULE_ physical 86 MHz front end iff the optical Doppler peak
%   fD_peak = 2*v_peak/LAMBDA exceeds the 40 MHz noise-band model's
%   half-width B_NOISE_ENBW/2.  The front end is fixed hardware: the
%   trigger is the signal's Doppler extent (velocity), NEVER the
%   mechanical vibration frequency (audit issue 1).
  if 2.0 * vpk / K.LAMBDA > K.B_NOISE_ENBW / 2
    B_fe = K.B_FE_PHYS;
    lpf = true;
  else
    B_fe = K.B_NOISE_ENBW;
    lpf = false;
  end
end

function [N, Ne, te, t] = grid_(K, T)
%GRID_ padded time grid: build on te (Ne), slice [PAD+1..PAD+N] after FE LPF.
  N = floor(T * K.FS);
  Ne = N + 2 * K.PAD;
  te = (0:Ne-1).' / K.FS;
  t = te(K.PAD+1 : K.PAD+N);
end

function z = fe_slice_(K, z_ext, B_fe, lpf, N)
  if lpf
    z_ext = fir_lp_same(z_ext, B_fe / 2, K.FS, K.FE_NT);
  end
  z_ext = z_ext(:);
  z = z_ext(K.PAD+1 : K.PAD+N);
end

function [x, v] = cos_start_motion_(K, t, f0, vpk)
%COS_START_MOTION_ motion from rest at T_ON: v = vpk*sin(2*pi*f0*(t-T_ON)).
  td = max(t - K.T_ON, 0.0);
  v = vpk * sin(2 * pi * f0 * td);
  x = vpk / (2 * pi * f0) * (1 - cos(2 * pi * f0 * td));
end

function n = sudden_2pi_jumps_(y, ph_true)
  ph = np_unwrap(angle(y(:)));
  n = sum(abs(diff(ph - ph_true(:))) > pi);
end

function n = fringe_slip_(y, ph_true)
  ph = np_unwrap(angle(y(:)));
  n = round((ph(end) - ph_true(end)) / (2 * pi));
end

function k = ckey_(band, cnr, lpf)
  k = sprintf('%s|%d|%d', band, cnr, double(lpf));
end


% ============================================================ S1 operating map
function T = s1T_(f0)
  switch f0
    case 1e3,   T = 3e-3;
    case 10e3,  T = 1e-3;
    case 50e3,  T = 0.5e-3;
    otherwise,  T = 0.5e-3;
  end
end

function s = s1skip_(f0)
  switch f0
    case 1e3,   s = 1.5e-3;
    case 10e3,  s = 0.4e-3;
    case 50e3,  s = 0.16e-3;
    otherwise,  s = 0.1e-3;
  end
end

function c = s1_clean_cell_(K, f0, vpk)
%S1_CLEAN_CELL_ R1 near-noiseless run of the auto-selected gear on (f0, vpk).
  band = select_band(f0, vpk);
  gf = guard_flags(f0, vpk, band);
  [B_fe, lpf] = fe_rule_(K, vpk);
  [N, ~, te, t] = grid_(K, s1T_(f0));
  xe = cos_start_motion_(K, te, f0, vpk);
  [~, v] = cos_start_motion_(K, t, f0, vpk);
  z = fe_slice_(K, exp(1i * 4 * pi / K.LAMBDA * xe), B_fe, lpf, N);
  [yf, yn, ~, ~, dg] = vt_gear_filter(z, band, 1e-10, 'always');
  sel = t > s1skip_(f0);
  a_true = max(ls_amp_(v, t, f0, sel), K.TINY);
  err = 100 * (ls_amp_(vdisc_h_(K, yf), t, f0, sel) / a_true - 1);
  err_nco = 100 * (ls_amp_(vdisc_h_(K, yn), t, f0, sel) / a_true - 1);
  c = struct('band', band, 'err', err, 'err_nco', err_nco, ...
             'near_pi', dg.near_pi_events, 'B_fe', B_fe, 'lpf', lpf, ...
             'phi_err', gf.phi_err, 'guard_ok', gf.guard_ok, ...
             'overrange', gf.overrange);
end

function cache = s1_noise_cache_(K, cells, S1CNR, nseed)
%S1_NOISE_CACHE_ noise-floor reduction vs OFF (R2), per (band, cnr, lpf).
%   Static-carrier measurement, eval band 10..100 kHz -- scene-independent,
%   one cached value serves every map cell with that combination.
  T = 0.5e-3;
  L = 16384;
  [N, Ne, ~, t] = grid_(K, T);
  W = t > 0.1e-3;
  cache = containers.Map('KeyType', 'char', 'ValueType', 'double');
  for lpfv = [false true]
    bands = {};
    for i = 1:numel(cells)
      if cells{i}.lpf == lpfv
        bands{end + 1} = cells{i}.band; %#ok<AGROW>
      end
    end
    bands = unique(bands);              % alphabetical == Python sorted()
    if isempty(bands)
      continue
    end
    if lpfv, B_fe = K.B_FE_PHYS; else, B_fe = K.B_NOISE_ENBW; end
    for icnr = 1:numel(S1CNR)
      cnr = S1CNR(icnr);
      s2 = 10 ^ (-cnr / 10);
      acc = zeros(numel(bands), nseed);
      for s = 0:nseed-1
        seed = 210000 + 50000 * double(lpfv) + cnr * 1000 + s;
        rng = np_rng_new(seed);
        z = fe_slice_(K, 1.0 + complex_bandlimited_noise(Ne, K.FS, B_fe, ...
                                                         s2, rng), ...
                      B_fe, lpfv, N);
        a_off = s1_asd_(K, vdisc_h_(K, z), W, L);
        for ib = 1:numel(bands)
          yf = vt_gear_filter(z, bands{ib}, s2, 'auto');
          acc(ib, s + 1) = 20 * log10(a_off / ...
                                      s1_asd_(K, vdisc_h_(K, yf), W, L));
        end
      end
      for ib = 1:numel(bands)
        cache(ckey_(bands{ib}, cnr, lpfv)) = vt_stats(acc(ib, :));
      end
    end
  end
end

function a = s1_asd_(K, v, W, L)
  [P, f] = welch_psd(v(W), K.FS, L);
  m = (f >= 10e3) & (f <= 100e3);
  a = max(sqrt(median(P(m))), K.TINY);
end

function [cells_map, cache] = S1_(K)
  S1F = [1e3, 10e3, 50e3, 100e3];
  S1V = [0.02, 1.0, 5.0, 20.0, 30.0];
  S1CNR = [3, 6, 12];
  nseed = 3;
  header_(sprintf(['S1  零差工况地图: f={1,10,50,100}kHz x ' ...
      'v={0.02,1,5,20,30}m/s x CNR={3,6,12}dB\n    (amp err = R1 近无噪 LS ' ...
      '幅值; stG = R3 信号增益 + R2 静态载波底噪下降中值 (结构带 ' ...
      '10..100kHz, %d seeds) -- 非逐格动态实测, 动态抽查见 S1e;\n    前端: ' ...
      'fD_peak=2*v/lambda > B_NOISE_ENBW/2=20MHz (即 v_peak > 15.5 m/s) ' ...
      '的格点用 B_FE=86MHz 总CNR + 线性相位 LPF, 其余 40MHz 噪声带模型)'], ...
      nseed));
  cells = cell(numel(S1F), numel(S1V));
  flat = {};
  for i = 1:numel(S1F)
    for j = 1:numel(S1V)
      cells{i, j} = s1_clean_cell_(K, S1F(i), S1V(j));
      flat{end + 1} = cells{i, j}; %#ok<AGROW>
    end
  end
  cache = s1_noise_cache_(K, flat, S1CNR, nseed);

  gh = '';
  for icnr = 1:numel(S1CNR)
    gh = [gh, sprintf('%10s', sprintf('stG@%ddB', S1CNR(icnr)))]; %#ok<AGROW>
  end
  out_(sprintf(['\n    %6s %9s %7s %8s %10s %6s | %8s %9s %3s |%s'], ...
               'f', 'v_peak', 'gear', 'phi_err', 'guard', 'FE', ...
               'ampErr', 'ampErrNCO', 'np', gh));
  ok_a = true; ok_b = true; ok_c1 = true; ok_c2 = true;
  worst_a = 0.0; worst_b = 0.0;
  for i = 1:numel(S1F)
    f0 = S1F(i);
    for j = 1:numel(S1V)
      vpk = S1V(j);
      c = cells{i, j};
      if c.guard_ok, gtag = 'ok'; else, gtag = 'OVERRANGE'; end
      if c.lpf, fetag = '86M+L'; else, fetag = '40M'; end
      gains = zeros(1, numel(S1CNR));
      for icnr = 1:numel(S1CNR)
        g_sig = 20 * log10(max(1 + c.err / 100, 1e-12));
        gains(icnr) = g_sig + cache(ckey_(c.band, S1CNR(icnr), c.lpf));
      end
      out_(sprintf(['    %4.0fk %7.0fmm %7s %7.3fr %10s %6s | %+7.2f%% ' ...
                    '%+8.2f%% %3d |%s'], f0 / 1e3, vpk * 1e3, c.band, ...
                   c.phi_err, gtag, fetag, c.err, c.err_nco, c.near_pi, ...
                   sprintf('%+9.2f ', gains)));
      key_(sprintf('S1_err_f%.0fk_v%.0f', f0 / 1e3, vpk * 1e3), c.err);
      key_(sprintf('S1_nco_f%.0fk_v%.0f', f0 / 1e3, vpk * 1e3), c.err_nco);
      key_(sprintf('S1_gain3_f%.0fk_v%.0f', f0 / 1e3, vpk * 1e3), gains(1));
      if c.guard_ok
        ok_a = ok_a && abs(c.err) < 5.0 && c.near_pi == 0;
        worst_a = max(worst_a, abs(c.err));
      else
        ok_b = ok_b && abs(c.err) < 10.0 && c.near_pi == 0;
        worst_b = max(worst_b, abs(c.err));
      end
      if strcmp(c.band, 'SLOW')
        ok_c1 = ok_c1 && gains(1) > 10.0;
      end
      ok_c2 = ok_c2 && gains(1) > 0.0;
    end
    out_('');
  end
  out_(['  说明1: (100kHz, 20m/s) 的 phi_err=1.001 rad 恰好压在守卫线上 -- ' ...
        '守卫边界实测就在用户 20..30 m/s 高速区内.']);
  out_(sprintf(['  说明2: ampErr(full输出) 由公共 4MHz 残差窗定标, 与档位/' ...
        'phi_err 几乎无关 (设计意图); ampErrNCO 是载波路径单独的\n  幅值误差, ' ...
        '随 phi_err 增大而恶化 -- 档位动态只影响载波路径与噪声, 不影响 full ' ...
        '输出的幅值刻度 (validate_zeta_sweep 结论).']));
  out_(sprintf(['  说明3: 40M 与 86M+L 格点的 OFF 参考不同 (同总CNR下更宽前端' ...
        '点击更多, PSD 更低), 增益不可跨前端相减.\n  FAST 在 40M/CNR3 处于环内' ...
        '点击门限之下 (feed-through, 增益 ~+12dB), 在 86M 同总CNR 环内CNR 高 ' ...
        '3.3dB 越过门限\n  (滑周率对环内CNR指数敏感) -- 全输出噪声底由公共窗' ...
        '决定, 三档增益趋同 ~+50dB. CNR 指标必须在实际前端带宽上定义 (A6).']));
  out_(sprintf(['  说明4: stG 列是 R2 静态载波方法的底噪下降 (刻意与运动场景' ...
        '无关, 每个 (档位, CNR, 前端) 组合一个缓存值),\n  不是该格点真实运动下' ...
        '的逐格实测 -- 动态实测抽查见下方 S1e (audit issue 3).']));
  check_('S1a', '守卫内 (guard_ok) 全部格点: clean |ampErr| < 5% 且 0 near-pi', ...
         ok_a, sprintf('worst %.2f%%', worst_a));
  check_('S1b', ['OVERRANGE 格点 (100kHz x 20/30m/s): clean |ampErr| < 10% ' ...
         '且 0 near-pi (降级区仍可测幅值)'], ok_b, ...
         sprintf('worst %.2f%%', worst_b));
  check_('S1c', 'SLOW 档格点 CNR=3dB SNR gain > +10 dB (门限扩展)', ok_c1, ...
         'see table');
  check_('S1d', '全部格点 CNR=3dB SNR gain > 0 dB', ok_c2, 'see table');
  s1_dynamic_spot_(K, cells, cache);
  cells_map = cells;
end


% --------------------------------------------- S1e dynamic spot check (issue 3)
function s1_dynamic_spot_(K, cells, cache)
%S1_DYNAMIC_SPOT_ R1+R3 on ACTUAL motion: full dynamic noisy runs on 3 cells.
%   Noise on each output = (chain output of signal+noise) - (chain output
%   of the clean signal), both with the SAME gate policy, so the
%   deterministic motion cancels and the residual is the true dynamic
%   output noise (clicks, slip transients, dropout flywheel included).
%   ASD in the structure band 10..100 kHz, median over seeds; compared
%   against the S1 static-carrier cached value of the same (gear, CNR, FE).
  PTS = [100e3, 0.02; 10e3, 30.0; 100e3, 30.0];   % (f0, v_peak) spot cells
  IJ = [4, 1; 2, 5; 4, 5];                        % indices into cells{i,j}
  CNR = 3;
  nseed = 3;
  L = 16384;
  out_('');
  out_(sprintf(['  S1e 动态抽查 (audit issue 3): 3 个格点在真实运动 + ' ...
                'CNR=%ddB 噪声下全动态实测底噪下降 (%d seeds 中值);'], ...
               CNR, nseed));
  out_(['  噪声 = 含噪运行输出 - 同链路清洁运行输出 (gate=auto 两者一致), ' ...
        '评估带同缓存 (10..100kHz).']);
  out_(sprintf('    %-22s %7s %6s | %12s %13s %9s %6s', 'cell', 'gear', ...
               'FE', 'dynGain@3dB', 'statGain@3dB', 'dyn-stat', 'np中'));
  G = zeros(size(PTS, 1), 2);
  for ipt = 0:size(PTS, 1)-1
    f0 = PTS(ipt + 1, 1);
    vpk = PTS(ipt + 1, 2);
    c = cells{IJ(ipt + 1, 1), IJ(ipt + 1, 2)};
    band = c.band;
    [B_fe, lpf] = fe_rule_(K, vpk);
    [N, Ne, te, t] = grid_(K, s1T_(f0));
    xe = cos_start_motion_(K, te, f0, vpk);
    ph_e = 4 * pi / K.LAMBDA * xe(:);
    s2 = 10 ^ (-CNR / 10);
    W = t > s1skip_(f0);
    zc = fe_slice_(K, exp(1i * ph_e), B_fe, lpf, N);
    ycf = vt_gear_filter(zc, band, s2, 'auto');
    v_off_c = vdisc_h_(K, zc);
    v_on_c = vdisc_h_(K, ycf);
    vals = zeros(1, nseed);
    nps = zeros(1, nseed);
    for s = 0:nseed-1
      rng = np_rng_new(215000 + ipt * 1000 + s);
      z = fe_slice_(K, exp(1i * ph_e) + ...
                    complex_bandlimited_noise(Ne, K.FS, B_fe, s2, rng), ...
                    B_fe, lpf, N);
      [yf, ~, ~, ~, dg] = vt_gear_filter(z, band, s2, 'auto');
      vals(s + 1) = 20 * log10( ...
          s1_asd_(K, vdisc_h_(K, z) - v_off_c, W, L) / ...
          s1_asd_(K, vdisc_h_(K, yf) - v_on_c, W, L));
      nps(s + 1) = dg.near_pi_events;
    end
    g_sig = 20 * log10(max(1 + c.err / 100, 1e-12));
    g_dyn = g_sig + vt_stats(vals);
    g_stat = g_sig + cache(ckey_(band, CNR, lpf));
    np_med = vt_stats(nps);
    if lpf, fetag = '86M+L'; else, fetag = '40M'; end
    out_(sprintf(['    %4.0fkHz/%6.0fmm/s     %7s %6s | %+11.2f %+12.2f ' ...
                  '%+8.2f %6.0f'], f0 / 1e3, vpk * 1e3, band, fetag, ...
                 g_dyn, g_stat, g_dyn - g_stat, np_med));
    key_(sprintf('S1e_dyn_f%.0fk_v%.0f', f0 / 1e3, vpk * 1e3), g_dyn);
    G(ipt + 1, :) = [g_dyn, g_stat];
  end
  out_(sprintf(['  解读: 用户点 (100kHz/20mm/s, SLOW) 动态实测与静态缓存一致 ' ...
        '(差 ~1 dB, SLOW 的 B_loop=0.49MHz < B_WIN, 点击被公共窗清除) --\n  ' ...
        '缓存方法在窄档格点成立; 30 m/s FAST 格点动态增益坍缩: 真实运动把环路' ...
        '推入点击高发区 (np 中值数百..数千, 静态载波下 ~0),\n  且 FAST 的 ' ...
        'B_loop=7.1MHz > B_WIN=4MHz 点击直通全输出 (说明3 的 feed-through ' ...
        '同机理) -- 静态缓存值在高速 FAST 格点只是\n  场景无关上界, 不可当动态 ' ...
        'SNR 读 (S1 表因此标注 stG; 产品在 OVERRANGE 角点必须按 S5 的降级语义' ...
        '上报).']));
  det = sprintf('%+.1f/%+.1f, ', G.');
  check_('S1e', ['动态抽查: 用户点 (100k/20mm) dyn > +30 dB 且 |dyn-stat| < ' ...
         '6 dB; 30m/s FAST 格点 dyn 比 stat 低 > 20 dB (静态缓存=上界)'], ...
         G(1, 1) > 30.0 && abs(G(1, 1) - G(1, 2)) < 6.0 && ...
         all(G(2:end, 2) - G(2:end, 1) > 20.0), det(1:end-2));
end


% ============================================================ S2 speckle matrix
function S2_(K)
  S2TAU = [20e-6, 50e-6, 100e-6];
  S2CNR = [3, 6, 12];
  nseed = 4;
  band = select_band(100e3, 0.02);
  B_OUT = 1e6;
  vamp = 0.02;
  thr = 20 * vamp;
  [B_fe, lpf] = fe_rule_(K, vamp);   % fD_peak=25.8kHz << 20MHz -> 40MHz 噪声带
  if lpf, fetag = sprintf('%.0fMHz+LPF', B_fe / 1e6);
  else, fetag = sprintf('%.0fMHz', B_fe / 1e6); end
  header_(sprintf(['S2  散斑矩阵 @100kHz/20mm/s (gear=%s, gate=auto, ' ...
      'B_FE=%s, 输出滤到 %.0fMHz, %d seeds) -- V3 方法在用户工况点'], ...
      band, fetag, B_OUT / 1e6, nseed));
  [N, Ne, te, t] = grid_(K, 5e-4);
  xe = burst_signal(te, 100e3, vamp, 20, 0.02e-3);
  ph_e = 4 * pi / K.LAMBDA * xe(:);
  Wq = (t > 0.26e-3) & (t < 0.48e-3);
  med = struct('spo', zeros(3, 3), 'spn', zeros(3, 3), 'dro', zeros(3, 3), ...
               'drn', zeros(3, 3), 'lk', zeros(3, 3));
  for itau = 0:numel(S2TAU)-1
    tau = S2TAU(itau + 1);
    for icnr = 1:numel(S2CNR)
      cnr = S2CNR(icnr);
      s2 = 10 ^ (-cnr / 10);
      sp_off = zeros(1, nseed); sp_on = zeros(1, nseed);
      dr_off = zeros(1, nseed); dr_on = zeros(1, nseed);
      lock = zeros(1, nseed);
      for s = 0:nseed-1
        seed = 220000 + itau * 3000 + cnr * 100 + s;
        rng = np_rng_new(seed);
        h_e = make_speckle(Ne, K.FS, tau, rng);
        z = fe_slice_(K, h_e .* exp(1i * ph_e) + ...
                      complex_bandlimited_noise(Ne, K.FS, B_fe, s2, rng), ...
                      B_fe, lpf, N);
        hs = h_e(K.PAD+1 : K.PAD+N);
        ph_ref = ph_e(K.PAD+1 : K.PAD+N) + np_unwrap(angle(hs));
        ph_ref = ph_ref - ph_ref(1);
        xref = fir_lp_same(K.LAMBDA / (4 * pi) * ph_ref, B_OUT, K.FS, 2049);
        [yf, ~, ~, ~, dg] = vt_gear_filter(z, band, s2, 'auto');
        lock(s + 1) = dg.lock_frac;
        for pass = 1:2
          if pass == 1, y = z; else, y = yf; end
          v = vdisc_h_(K, y);
          vlp = fir_lp_same(v, B_OUT, K.FS, 2049);
          ex = abs(vlp(Wq)) > thr;
          nsp = sum(diff([false; ex(:)]) == 1);
          ph = np_unwrap(angle(y));
          ph = ph - ph(1);
          xh = fir_lp_same(K.LAMBDA / (4 * pi) * ph, B_OUT, K.FS, 2049);
          e = xh - xref;
          drv = 1e9 * std(e - mean(e), 1);
          if pass == 1
            sp_off(s + 1) = nsp; dr_off(s + 1) = drv;
          else
            sp_on(s + 1) = nsp; dr_on(s + 1) = drv;
          end
        end
      end
      med.spo(itau + 1, icnr) = vt_stats(sp_off);
      med.spn(itau + 1, icnr) = vt_stats(sp_on);
      med.dro(itau + 1, icnr) = vt_stats(dr_off);
      med.drn(itau + 1, icnr) = vt_stats(dr_on);
      med.lk(itau + 1, icnr) = 100 * mean(lock);
    end
  end
  out_(sprintf('\n    %6s %5s | %11s %10s | %15s %15s | %6s', 'tau_c', ...
               'CNR', 'spikes OFF', 'spikes ON', 'disp rms OFF nm', ...
               'disp rms ON nm', 'lock%'));
  ok_sp = true; ok_lk = true;
  for it = 1:numel(S2TAU)
    for icnr = 1:numel(S2CNR)
      cnr = S2CNR(icnr);
      out_(sprintf('    %4.0fus %3ddB | %11.0f %10.0f | %15.0f %15.0f | %6.1f', ...
                   S2TAU(it) * 1e6, cnr, med.spo(it, icnr), ...
                   med.spn(it, icnr), med.dro(it, icnr), med.drn(it, icnr), ...
                   med.lk(it, icnr)));
      key_(sprintf('S2_lock_t%.0f_c%d', S2TAU(it) * 1e6, cnr), ...
           med.lk(it, icnr));
      key_(sprintf('S2_dron_t%.0f_c%d', S2TAU(it) * 1e6, cnr), ...
           med.drn(it, icnr));
      ok_sp = ok_sp && (med.spn(it, icnr) <= med.spo(it, icnr));
      if cnr == 12
        ok_lk = ok_lk && (med.lk(it, icnr) > 75.0);
      end
    end
    out_('');
  end
  out_(sprintf(['  诚实注记: 掉落期间 NCO 飞轮只能外推, 位移连续性无法承诺 ' ...
        '(同 V3); ON 的位移 rms 含掉落期外推误差;\n  lock%% 不到 100 是门控按' ...
        '设计在散斑深衰落中放开 (invalid 标志), 不是缺陷 -- 见 ' ...
        'OPTIMIZATION_GUIDE 门控节.']));
  check_('S2a', '全部 (tau_c x CNR): gate-on 速度尖峰中值 <= OFF (尖峰不恶化)', ...
         ok_sp, 'see table');
  check_('S2b', ['CNR=12dB: lock fraction > 75% (全部 tau_c; 余量在散斑衰落' ...
         '统计内)'], ok_lk, 'see table');
end


% ============================================================ S3 transients
function hist = selector_trace_(K, name, seq, start)
  out_('');
  out_(sprintf('  %s (选档状态机, 每行=一次选档更新, 起始档 %s)', name, start));
  out_(sprintf('    %6s %7s %9s | %7s %8s %16s', 'update', 'f', 'v_peak', ...
               'target', 'applied', 'phi_err(applied)'));
  band = start;
  n = size(seq, 1);
  hist = cell(n, 1);
  for i = 1:n
    f0 = seq(i, 1);
    v = seq(i, 2);
    tgt = select_band(f0, v);
    band = select_band_hysteresis(f0, band, v);
    pe = tracking_error_rad(f0, v, K.BANDS.(band).fn);
    out_(sprintf('    %6d %5.0fk %8.0fmm/s | %7s %8s %15.4gr', i - 1, ...
                 f0 / 1e3, v * 1e3, tgt, band, pe));
    hist{i} = struct('applied', band, 'target', tgt, 'pe', pe);
  end
end

function [x, v] = s3_freq_step_motion_(K, t, ts, f1, f2, vp)
%S3_FREQ_STEP_MOTION_ velocity-continuous frequency step at ts, rest until T_ON.
  td = max(t - K.T_ON, 0.0);
  td_s = ts - K.T_ON;
  th_s = 2 * pi * f1 * td_s;
  pre = t < ts;
  v = zeros(size(t));
  x = zeros(size(t));
  v(pre) = vp * sin(2 * pi * f1 * td(pre));
  v(~pre) = vp * sin(th_s + 2 * pi * f2 * (td(~pre) - td_s));
  x(pre) = vp / (2 * pi * f1) * (1 - cos(2 * pi * f1 * td(pre)));
  x(~pre) = vp / (2 * pi * f1) * (1 - cos(th_s)) + vp / (2 * pi * f2) * ...
            (cos(th_s) - cos(th_s + 2 * pi * f2 * (td(~pre) - td_s)));
end

function [x, v] = s3_vel_step_motion_(K, t, ts, f0, v1, v2)
%S3_VEL_STEP_MOTION_ amplitude step v1->v2 (20 us raised-cos ramp at ts).
  tr = 20e-6;
  td = max(t - K.T_ON, 0.0);
  u = min(max((t - ts) / tr, 0.0), 1.0);
  A = v1 + (v2 - v1) * 0.5 * (1 - cos(pi * u));
  v = A .* sin(2 * pi * f0 * td);
  x = cumsum(v) / K.FS;
end

function r = s3_run_(K, tag, band, xe, v, N, Ne, t, f_pre, f_post, ...
                     Wpre, Wpost, B_fe, lpf, iscen)
  S3CNR = 6.0;
  nseed = 5;
  ph_e = 4 * pi / K.LAMBDA * xe(:);
  zc = fe_slice_(K, exp(1i * ph_e), B_fe, lpf, N);
  [yf, ~, ~, ~, dg] = vt_gear_filter(zc, band, 1e-10, 'always');
  vd = vdisc_h_(K, yf);
  e_pre_c = 100 * (ls_amp_(vd, t, f_pre, Wpre) / ...
                   max(ls_amp_(v, t, f_pre, Wpre), K.TINY) - 1);
  e_post_c = 100 * (ls_amp_(vd, t, f_post, Wpost) / ...
                    max(ls_amp_(v, t, f_post, Wpost), K.TINY) - 1);
  np_c = dg.near_pi_events;
  s2 = 10 ^ (-S3CNR / 10);
  E_pre = zeros(1, nseed); E_post = zeros(1, nseed);
  NP = zeros(1, nseed); LK = zeros(1, nseed);
  for s = 0:nseed-1
    rng = np_rng_new(230000 + iscen * 5000 + s);
    z = fe_slice_(K, exp(1i * ph_e) + ...
                  complex_bandlimited_noise(Ne, K.FS, B_fe, s2, rng), ...
                  B_fe, lpf, N);
    [yf, ~, ~, ~, dg] = vt_gear_filter(z, band, s2, 'auto');
    vd = vdisc_h_(K, yf);
    E_pre(s + 1) = 100 * (ls_amp_(vd, t, f_pre, Wpre) / ...
                          max(ls_amp_(v, t, f_pre, Wpre), K.TINY) - 1);
    E_post(s + 1) = 100 * (ls_amp_(vd, t, f_post, Wpost) / ...
                           max(ls_amp_(v, t, f_post, Wpost), K.TINY) - 1);
    NP(s + 1) = dg.near_pi_events;
    LK(s + 1) = dg.lock_frac;
  end
  out_(sprintf(['    %-34s %6s | %+8.2f%% %+8.2f%% %4d | %+8.2f%% ' ...
                '%+8.2f%% %5.0f %6.1f'], tag, band, e_pre_c, e_post_c, ...
               np_c, vt_stats(E_pre), vt_stats(E_post), vt_stats(NP), ...
               100 * mean(LK)));
  r = struct('e_pre_c', e_pre_c, 'e_post_c', e_post_c, 'np_c', np_c, ...
             'e_pre', vt_stats(E_pre), 'e_post', vt_stats(E_post));
end

function S3_(K)
  header_(sprintf(['S3  瞬态: 频率阶跃 50k->100kHz @20mm/s 与速度阶跃 ' ...
      '5->30m/s @100kHz (CNR=6dB, 5 seeds)\n    换档只发生在选档更新时刻 ' ...
      '(离散状态机); 本节先给选档轨迹, 再给 "阶跃两侧同一档" PLL 实测 ' ...
      '(T1/T2 阶跃前后选档不变),\n    最后实测 "旧档暴露窗" (T3: SLOW 被 ' ...
      '20mm/s->30m/s 阶跃甩在错档上).']));
  selector_trace_(K, 'T1 选档轨迹: 50 kHz -> 100 kHz @ 20 mm/s', ...
      [repmat([50e3, 0.02], 2, 1); repmat([100e3, 0.02], 3, 1)], 'SLOW');
  selector_trace_(K, 'T2 选档轨迹: 5 m/s -> 30 m/s @ 100 kHz', ...
      [repmat([100e3, 5.0], 2, 1); repmat([100e3, 30.0], 3, 1)], 'FAST');
  tr3 = selector_trace_(K, 'T3 选档轨迹: 20 mm/s -> 30 m/s @ 100 kHz (SLOW 起)', ...
      [repmat([100e3, 0.02], 2, 1); repmat([100e3, 30.0], 3, 1)], 'SLOW');

  T = 0.5e-3;
  ts = 0.25e-3;
  [N, Ne, te, t] = grid_(K, T);
  out_(sprintf('\n    %-34s %6s | %8s %8s %4s | %8s %8s %5s %6s', ...
               'scenario', 'gear', 'pre清洁', 'post清洁', 'np', ...
               'pre噪中值', 'post噪中值', 'np中', 'lock%'));

  xe = s3_freq_step_motion_(K, te, ts, 50e3, 100e3, 0.02);
  [~, v] = s3_freq_step_motion_(K, t, ts, 50e3, 100e3, 0.02);
  W1p = (t > 0.10e-3) & (t < 0.24e-3);
  W1q = (t > 0.30e-3) & (t < 0.48e-3);
  [B_fe, lpf] = fe_rule_(K, 0.02);
  r1 = s3_run_(K, 'T1 freq step 50k->100k @20mm/s', 'SLOW', xe, v, N, Ne, ...
               t, 50e3, 100e3, W1p, W1q, B_fe, lpf, 0);

  [xe, ve] = s3_vel_step_motion_(K, te, ts, 100e3, 5.0, 30.0);
  v = ve(K.PAD+1 : K.PAD+N);
  [B_fe, lpf] = fe_rule_(K, 30.0);
  r2 = s3_run_(K, 'T2 vel step 5->30m/s @100k', 'FAST', xe, v, N, Ne, t, ...
               100e3, 100e3, W1p, W1q, B_fe, lpf, 1);

  [xe, ve] = s3_vel_step_motion_(K, te, ts, 100e3, 0.02, 30.0);
  v = ve(K.PAD+1 : K.PAD+N);
  zc = fe_slice_(K, exp(1i * 4 * pi / K.LAMBDA * xe(:)), B_fe, lpf, N);
  [yf, ~, ~, ~, dg] = vt_gear_filter(zc, 'SLOW', 1e-10, 'always');
  vd = vdisc_h_(K, yf);
  e3 = 100 * (ls_amp_(vd, t, 100e3, W1q) / ...
              max(ls_amp_(v, t, 100e3, W1q), K.TINY) - 1);
  out_(sprintf(['    %-33s %6s | %8s %+8.2f%% %4d | (clean only: ' ...
                '暴露窗内旧档的实测破坏)'], ...
               'T3 WRONG gear (SLOW跨 20mm->30m/s)', 'SLOW', '--', e3, ...
               dg.near_pi_events));

  key_('S3_T1_post', r1.e_post_c);
  key_('S3_T2_post', r2.e_post_c);
  key_('S3_T3_post', e3);
  out_(sprintf(['\n  解读: T1/T2 阶跃前后选档不变 (SLOW/FAST), 环路自身跟过' ...
        '阶跃, 幅值误差保持; T3 显示若选档更新慢了,\n  旧档 (SLOW) 在 30 m/s ' ...
        '上幅值误差 %+.0f%% 且 near-pi %d 次 -- 选档更新周期就是唯一暴露窗 ' ...
        '(validate_app A3 结论的实测版).'], e3, dg.near_pi_events));
  check_('S3a', 'T1 (SLOW 跨频率阶跃): 清洁 pre/post |ampErr| < 5%', ...
         abs(r1.e_pre_c) < 5 && abs(r1.e_post_c) < 5, ...
         sprintf('pre %+.2f%%, post %+.2f%%', r1.e_pre_c, r1.e_post_c));
  check_('S3b', 'T2 (FAST 跨 5->30m/s 阶跃): 清洁 post |ampErr| < 10% 且 0 near-pi', ...
         abs(r2.e_post_c) < 10 && r2.np_c == 0, ...
         sprintf('post %+.2f%%, np %d', r2.e_post_c, r2.np_c));
  check_('S3c', ['T3 升档即时性 (选档轨迹): SLOW 起, 20mm/s->30m/s 阶跃后第 ' ...
         '1 次选档更新即 FAST (真 SLOW->FAST 升档; T2 的 FAST->FAST 不构成检验)'], ...
         strcmp(tr3{2}.applied, 'SLOW') && strcmp(tr3{3}.applied, 'FAST'), ...
         sprintf('update1 %s -> update2 %s', tr3{2}.applied, tr3{3}.applied));
  check_('S3d', 'T3 旧档暴露窗: SLOW 在 30 m/s 上 |ampErr| > 50% (升档必须即时生效)', ...
         abs(e3) > 50, sprintf('%+.1f%%', e3));
end


% ============================================================ S4 multi-surface
function S4_(K)
  SEG_CNR = [12, 6, 3];
  SEG_NAME = {'反光膜(强回光)', '黑面(弱回光)', '远距(更弱)'};
  TSEG = 0.15e-3;
  GAP = 20e-6;
  GAPDROP = 10 ^ (-30 / 20);
  nseed = 4;
  band = select_band(100e3, 0.02);
  [B_fe, lpf] = fe_rule_(K, 0.02);
  header_(sprintf(['S4  多表面切换 (反光->黑面->远距, 段CNR=12/6/3dB, 段边界 ' ...
      '%.0fus -30dB 缝隙, gear=%s, gate=auto, %d seeds)\n    -- ' ...
      'validate_ellipse_switching 的表面切换概念移植到 IQ 跟踪域: 噪声底恒定, ' ...
      '回光幅值分段跳变.'], GAP * 1e6, band, nseed));
  T = 3 * TSEG;
  [N, Ne, te, t] = grid_(K, T);
  xe = cos_start_motion_(K, te, 100e3, 0.02);
  [~, v] = cos_start_motion_(K, t, 100e3, 0.02);
  ph_e = 4 * pi / K.LAMBDA * xe(:);
  s2N = 10 ^ (-3 / 10);    % constant receiver noise power; CNR by amplitude
  env = zeros(Ne, 1);
  for i = 1:3
    m = (te >= (i - 1) * TSEG) & (te < i * TSEG);
    env(m) = sqrt(s2N * 10 ^ (SEG_CNR(i) / 10));
  end
  env(te >= 3 * TSEG) = sqrt(s2N * 10 ^ (SEG_CNR(end) / 10));
  for ts = [TSEG, 2 * TSEG]
    env((te >= ts) & (te < ts + GAP)) = ...
        env((te >= ts) & (te < ts + GAP)) * GAPDROP;
  end

  lockv = zeros(3, nseed);
  errv = zeros(3, nseed);
  relock = zeros(2, nseed);
  invp = zeros(2, nseed);
  for s = 0:nseed-1
    rng = np_rng_new(240000 + s);
    z = fe_slice_(K, env .* exp(1i * ph_e) + ...
                  complex_bandlimited_noise(Ne, K.FS, B_fe, s2N, rng), ...
                  B_fe, lpf, N);
    [yf, ~, ~, st, ~] = vt_gear_filter(z, band, s2N, 'auto');
    st = st(:);
    vd = vdisc_h_(K, yf);
    for i = 1:3
      t0s = (i - 1) * TSEG;
      t1s = i * TSEG;
      Wl = (t >= t0s + 70e-6) & (t < t1s);   % post-acquisition window
      lockv(i, s + 1) = 100 * mean(st(Wl) == 2);
      errv(i, s + 1) = 100 * (ls_amp_(vd, t, 100e3, Wl) / ...
                              max(ls_amp_(v, t, 100e3, Wl), K.TINY) - 1);
    end
    bnd = [TSEG, 2 * TSEG];
    for j = 1:2
      ts = bnd(j);
      gw = (t >= ts) & (t < ts + GAP);
      invp(j, s + 1) = 100 * mean(st(gw) ~= 2);
      after = find((t >= ts + GAP) & (st == 2));
      if isempty(after)
        relock(j, s + 1) = Inf;
      else
        relock(j, s + 1) = (t(after(1)) - (ts + GAP)) * 1e6;
      end
    end
  end
  out_(sprintf('\n    %-18s %5s | %10s %12s', 'segment', 'CNR', ...
               'lock% 中值', 'ampErr% 中值'));
  for i = 1:3
    lk = vt_stats(lockv(i, :));
    er = vt_stats(errv(i, :));
    out_(sprintf('    %-18s %3ddB | %10.1f %+12.2f', SEG_NAME{i}, ...
                 SEG_CNR(i), lk, er));
    key_(sprintf('S4_lock_seg%d', i - 1), lk);
    key_(sprintf('S4_err_seg%d', i - 1), er);
  end
  out_(sprintf('\n    %-18s | %17s %14s', 'boundary', 'gap invalid% 中值', ...
               'relock us 中值'));
  BN = {'反光->黑面', '黑面->远距'};
  for j = 1:2
    out_(sprintf('    %-18s | %17.0f %14.1f', BN{j}, ...
                 vt_stats(invp(j, :)), vt_stats(relock(j, :))));
  end
  ok_rl = all(isfinite(relock(:))) && all(relock(:) <= 80.0);
  ok_er = true;
  for i = 1:3
    ok_er = ok_er && abs(vt_stats(errv(i, :))) < 10.0;
  end
  ok_lk = vt_stats(lockv(3, :)) > 80.0;
  out_(sprintf(['\n  解读: 段间 6dB 幅值跳变本身不触发门控 (rel_off=0.08 ' ...
        '容忍), 边界缝隙触发 HOLD->ACQUIRE->LOCK 重捕;\n  SLOW 档重捕时间由 ' ...
        'acq_time=4*tauF=32us + 门控检测延迟决定.']));
  check_('S4a', '每个边界每个 seed 都重捕, relock <= 80 us', ok_rl, ...
         sprintf('medians %.1f / %.1f us', vt_stats(relock(1, :)), ...
                 vt_stats(relock(2, :))));
  check_('S4b', '三段 (12/6/3dB) 幅值误差中值 |err| < 10%', ok_er, ...
         sprintf('%+.1f%%, %+.1f%%, %+.1f%%', vt_stats(errv(1, :)), ...
                 vt_stats(errv(2, :)), vt_stats(errv(3, :))));
  check_('S4c', '最弱段 (远距 3dB) lock% 中值 > 80%', ok_lk, ...
         sprintf('%.1f%%', vt_stats(lockv(3, :))));
end


% ============================================================ S5 worst corner
function S5_(K)
  nseed = 6;
  band = 'FAST';
  tau = 50e-6;
  cnr = 3.0;
  B_fe = K.B_FE_PHYS;
  lpf = true;
  header_(sprintf(['S5  最坏角点: 100kHz/30m/s + 散斑 tau_c=%.0fus + ' ...
      'CNR=%.0fdB (gear=%s fallback, B_FE=86MHz+LPF, gate=auto, %d seeds) ' ...
      '-- 有界诚实报告'], tau * 1e6, cnr, band, nseed));
  T = 0.5e-3;
  [N, Ne, te, t] = grid_(K, T);
  xe = cos_start_motion_(K, te, 100e3, 30.0);
  [~, v] = cos_start_motion_(K, t, 100e3, 30.0);
  ph_e = 4 * pi / K.LAMBDA * xe(:);
  s2 = 10 ^ (-cnr / 10);
  W = t > 0.15e-3;
  B_OUT = 1e6;
  A = struct('err', zeros(1, nseed), 'errl', zeros(1, nseed), ...
             'lock', zeros(1, nseed), 'np', zeros(1, nseed), ...
             'j2', zeros(1, nseed), 'fr', zeros(1, nseed), ...
             'dr', zeros(1, nseed));
  for s = 0:nseed-1
    rng = np_rng_new(250000 + s);
    h_e = make_speckle(Ne, K.FS, tau, rng);
    z = fe_slice_(K, h_e .* exp(1i * ph_e) + ...
                  complex_bandlimited_noise(Ne, K.FS, B_fe, s2, rng), ...
                  B_fe, lpf, N);
    hs = h_e(K.PAD+1 : K.PAD+N);
    ph_ref = ph_e(K.PAD+1 : K.PAD+N) + np_unwrap(angle(hs));
    ph_ref = ph_ref - ph_ref(1);
    [yf, ~, ~, st, dg] = vt_gear_filter(z, band, s2, 'auto');
    st = st(:);
    vd = vdisc_h_(K, yf);
    A.err(s + 1) = 100 * (ls_amp_(vd, t, 100e3, W) / ...
                          max(ls_amp_(v, t, 100e3, W), K.TINY) - 1);
    Wl = W & (st == 2);    % product-meaningful: invalid samples excluded
    A.errl(s + 1) = 100 * (ls_amp_(vd, t, 100e3, Wl) / ...
                           max(ls_amp_(v, t, 100e3, Wl), K.TINY) - 1);
    A.lock(s + 1) = 100 * dg.lock_frac;
    A.np(s + 1) = dg.near_pi_events;
    A.j2(s + 1) = sudden_2pi_jumps_(yf, ph_ref);
    A.fr(s + 1) = abs(fringe_slip_(yf, ph_ref));
    phh = np_unwrap(angle(yf));
    phh = phh - phh(1);
    e = fir_lp_same(K.LAMBDA / (4 * pi) * phh, B_OUT, K.FS, 2049) - ...
        fir_lp_same(K.LAMBDA / (4 * pi) * ph_ref, B_OUT, K.FS, 2049);
    A.dr(s + 1) = 1e9 * std(e - mean(e), 1);
  end
  out_(sprintf('\n    %-34s %10s %10s %10s', 'metric', 'median', 'p10', 'p90'));
  LBL = {'ampErr % (全窗含掉落)', 'err'; 'ampErr % (仅 LOCK 有效样本)', 'errl'; ...
         'lock %', 'lock'; 'near-pi events', 'np'; 'sudden 2pi jumps', 'j2'; ...
         '|net fringe err| (cycles)', 'fr'; 'disp rms err nm (1MHz)', 'dr'};
  for i = 1:size(LBL, 1)
    [m, lo, hi] = vt_stats(A.(LBL{i, 2}));
    out_(sprintf('    %-34s %10.1f %10.1f %10.1f', LBL{i, 1}, m, lo, hi));
  end
  key_('S5_err_med', vt_stats(A.err));
  key_('S5_errl_med', vt_stats(A.errl));
  key_('S5_lock_med', vt_stats(A.lock));
  out_(sprintf(['\n  诚实结论: 最坏角点三重叠加 (fallback 档 phi_err=1.5 rad ' ...
        '+ 散斑掉落 + 3dB 弱光): 全窗幅值被掉落期 NCO 外推稀释 (invalid 期数据' ...
        '本就不该计入);\n  仅取 LOCK 有效样本后幅值刻度有界可用. 净条纹漂移 ' ...
        '10^1..10^2 周/0.5ms -- 位移积分在该角点无效 (与 validate_app A8/N2 ' ...
        '一致),\n  产品须按 overrange + 散斑 invalid 同时上报.']));
  m_errl = vt_stats(A.errl);
  m_lock = vt_stats(A.lock);
  check_('S5a', ['最坏角点 LOCK 有效样本 ampErr 中值 |err| < 40% (有界降级 ' ...
         '-- 实测约 -33%, 全窗则 ~-50%)'], abs(m_errl) < 40.0, ...
         sprintf('%+.1f%%', m_errl));
  check_('S5b', '最坏角点 lock fraction 中值 > 50% (可用数据比例)', ...
         m_lock > 50.0, sprintf('%.1f%%', m_lock));
end


% ======================================================= heterodyne scenarios
function p = h_scene_params_(f0)
  switch f0
    case 50e3
      p = struct('ncyc', 10, 't0', 0.15e-3, 'T', 0.8e-3, 'L', 8192, ...
                 'band', [10e3, 90e3], 'q0', 0.40e-3, 'q1', 0.78e-3);
    case 100e3
      p = struct('ncyc', 15, 't0', 0.10e-3, 'T', 0.5e-3, 'L', 8192, ...
                 'band', [50e3, 150e3], 'q0', 0.28e-3, 'q1', 0.48e-3);
    case 500e3
      p = struct('ncyc', 25, 't0', 0.10e-3, 'T', 0.4e-3, 'L', 4096, ...
                 'band', [0.3e6, 0.7e6], 'q0', 0.17e-3, 'q1', 0.39e-3);
    otherwise   % 5 MHz
      p = struct('ncyc', 40, 't0', 0.10e-3, 'T', 0.3e-3, 'L', 4096, ...
                 'band', [4e6, 6e6], 'q0', 0.13e-3, 'q1', 0.29e-3);
  end
end

function sc = het_scene_(K, f0)
  p = h_scene_params_(f0);
  N = floor(p.T * K.HFS);
  t = (0:N-1).' / K.HFS;
  [x, v] = burst_signal(t, f0, K.H_VAMP, p.ncyc, p.t0);
  ph = 4 * pi / K.HLAM * x + 2 * pi * K.H_DF * t;
  Wm = (t > p.t0) & (t < p.t0 + p.ncyc / f0);
  Wq = (t > p.q0) & (t < p.q1);
  sc = struct('f0', f0, 'N', N, 't', t, 'v', v, 'ph', ph, 'Wm', Wm, ...
              'Wq', Wq, 'p', p);
end

function v = het_vdisc_(K, y)
  v = fm_discriminator(y, K.HFS, K.HLAM);
end

function H = het_hl_mag_(K, f0, fn)
  H = abs(hl_response(f0, K.HFS, fn, K.HZ));
end

function [y, phi, st, dg] = het_run_pll_(K, z, fn, s2)
%HET_RUN_PLL_ shared homodyne PLL core at heterodyne fs/zeta, gate='always'
%   (bit-identical to the heterodyne core's own PLL under this gate policy).
  opts = struct('zeta', K.HZ, 'gate', 'always');
  [y, phi, st, dg] = pll_carrier_regen(z, K.HFS, fn, max(s2, 1e-12), opts);
end

function a = het_asd_(K, v, sel, L, band)
  [P, f] = welch_psd(v(sel), K.HFS, L);
  m = (f >= band(1)) & (f <= band(2));
  a = max(sqrt(median(P(m))), K.TINY);
end

function name = het_pick_mode_(K, modes)
% het_pick_mode_(K, modes) with K.pick_f set by caller
  name = K.HORDER{end};
  for i = 1:numel(K.HORDER)
    if K.pick_f <= modes.(K.HORDER{i}).f_3db
      name = K.HORDER{i};
      return
    end
  end
end

function c = het_clean_(K, sc, fn)
%HET_CLEAN_ R1 clean transfer: raw ratio, corrected err, signal gain vs OFF.
  zc = exp(1i * sc.ph);
  a_true = lockin_amp(sc.v, sc.t, sc.f0, sc.Wm);
  a_off = lockin_amp(het_vdisc_(K, zc), sc.t, sc.f0, sc.Wm);
  y = het_run_pll_(K, zc, fn, 1e-10);
  a_on = lockin_amp(het_vdisc_(K, y), sc.t, sc.f0, sc.Wm);
  H = het_hl_mag_(K, sc.f0, fn);
  c = struct('ratio', a_on / a_true, 'err', 100 * (a_on / H / a_true - 1), ...
             'g_sig', 20 * log10(max(a_on, K.TINY) / max(a_off, K.TINY)), ...
             'H', H);
end

function nr = het_nred_(K, sc, fn, cnr, nseed, seed0)
%HET_NRED_ R2 noise-floor drop vs OFF in the scene quiet window (median).
  s2 = 10 ^ (-cnr / 10);
  p = sc.p;
  vals = zeros(1, nseed);
  for s = 0:nseed-1
    rng = np_rng_new(seed0 + s);
    z = exp(1i * sc.ph) + complex_bandlimited_noise(sc.N, K.HFS, K.HBF, ...
                                                    s2, rng);
    a_off = het_asd_(K, het_vdisc_(K, z), sc.Wq, p.L, p.band);
    y = het_run_pll_(K, z, fn, s2);
    vals(s + 1) = 20 * log10(a_off / ...
                             het_asd_(K, het_vdisc_(K, y), sc.Wq, p.L, p.band));
  end
  nr = vt_stats(vals);
end

function H1_(K)
  H1VR = [0.1, 1.0, 3.0];
  H1F = [50e3, 500e3, 5e6];
  H1CNR = [0, 4, 12];
  nseed = 3;
  header_(sprintf(['H1  外差量程-速度地图: v_range={0.1,1,3}m/s x ' ...
      'f={50k,500k,5M}Hz x CNR={0,4,12}dB\n    (外差档位同时决定测量带宽 ' ...
      'f_3dB=2.058*fn 与动态; 5MHz > f_3dB 时只能 FAST+频响校正; R1-R4 规则, ' ...
      'gate=always)']));
  out_(sprintf(['  硬边界: v_if = %.2f m/s (IF 频偏窗), v_alias = %.2f m/s ' ...
                '(fs 混叠), fn <= fs/50 = %.0fk (离散稳定)'], ...
               het_v_if_limit(), het_v_alias_limit(), K.HFS / 50 / 1e3));
  scs = containers.Map('KeyType', 'double', 'ValueType', 'any');
  for i = 1:numel(H1F)
    scs(H1F(i)) = het_scene_(K, H1F(i));
  end
  ok_cov = true; ok_5m = true;
  g50 = NaN;
  gh = '';
  for icnr = 1:numel(H1CNR)
    gh = [gh, sprintf('%10s', sprintf('gain@%ddB', H1CNR(icnr)))]; %#ok<AGROW>
  end
  out_(sprintf(['\n    %8s %6s %7s %8s %8s %7s %7s %9s %9s |%s'], ...
               'v_range', 'f', 'mode', 'fn', 'f_3dB', '|H_L|', 'raw比', ...
               'corr err', 'fn<=fs/50', gh));
  for ivr = 0:numel(H1VR)-1
    vr = H1VR(ivr + 1);
    modes = het_mode_params(vr);
    for i_f = 0:numel(H1F)-1
      f0 = H1F(i_f + 1);
      Kp = K;
      Kp.pick_f = f0;
      mode = het_pick_mode_(Kp, modes);
      fn = modes.(mode).fn;
      sc = scs(f0);
      c = het_clean_(K, sc, fn);
      gains = zeros(1, numel(H1CNR));
      for icnr = 1:numel(H1CNR)
        cnr = H1CNR(icnr);
        seed0 = 260000 + ivr * 10000 + i_f * 1000 + cnr * 10;
        nr = het_nred_(K, sc, fn, cnr, nseed, seed0);
        gains(icnr) = c.g_sig + nr;
      end
      covered = f0 <= modes.(mode).f_3db;
      if het_fn_discrete_ok(fn, K.HFS), okd = 'ok'; else, okd = 'FAIL'; end
      out_(sprintf(['    %6.1fm %5.0fk %7s %6.1fk %6.1fk %7.4f %7.4f ' ...
                    '%+8.2f%% %9s |%s'], vr, f0 / 1e3, mode, fn / 1e3, ...
                   modes.(mode).f_3db / 1e3, c.H, c.ratio, c.err, okd, ...
                   sprintf('%+9.2f ', gains)));
      key_(sprintf('H1_err_vr%g_f%.0fk', vr, f0 / 1e3), c.err);
      key_(sprintf('H1_gain0_vr%g_f%.0fk', vr, f0 / 1e3), gains(1));
      if covered
        ok_cov = ok_cov && abs(c.err) < 10.0;
      elseif c.H >= 0.1
        ok_5m = ok_5m && abs(c.err) < 15.0;
      end
      if vr == 1.0 && f0 == 50e3
        g50 = gains(1);
      end
    end
    out_('');
  end
  ok_gain = g50 > 10.0;
  out_(sprintf(['  解读: 档内 (f<=f_3dB) 频响校正后幅值刻度保持; 5 MHz 超出' ...
        '所有档的 f_3dB, 只有 FAST 的 |H_L| 足够校正;\n  增益本质是 FM 门限' ...
        '扩展, 高 CNR 时归零 (校正不改变谱线 SNR).']));
  check_('H1a', '档内格点 (f <= f_3dB): 频响校正后 |err| < 10%', ok_cov, ...
         'see table');
  check_('H1b', '5MHz 格点 |H_L|>=0.1 者: 校正后 |err| < 15% (FAST+校正可用)', ...
         ok_5m, 'see table');
  check_('H1c', 'v_range=1, f=50kHz (SLOW) CNR=0dB 线SNR增益 > +10 dB (门限扩展)', ...
         ok_gain, sprintf('%+.1f dB', g50));
end

function H2_(K)
  header_(['H2  超出 f_3dB: 5MHz 三档 raw vs corrected (复现 ' ...
           'validate_heterodyne C24/C26 -- 外差档位=测量带宽, 无残差窗兜底)']);
  modes = het_mode_params(1.0);
  sc = het_scene_(K, 5e6);
  out_(sprintf('\n    %7s %8s %8s %10s %10s %9s', 'mode', 'fn', 'f_3dB', ...
               '|H_L(5M)|', 'raw幅值比', 'corr err'));
  rows = struct();
  for i = 1:numel(K.HORDER)
    name = K.HORDER{i};
    fn = modes.(name).fn;
    c = het_clean_(K, sc, fn);
    rows.(name) = c;
    out_(sprintf('    %7s %6.1fk %6.1fk %10.4f %10.4f %+8.2f%%', name, ...
                 fn / 1e3, modes.(name).f_3db / 1e3, c.H, c.ratio, c.err));
    key_(sprintf('H2_ratio_%s', name), c.ratio);
  end
  check_('H2a', 'SLOW@5MHz 未校正幅值比 < 0.05 (C26 复现: 档位=测量带宽)', ...
         rows.SLOW.ratio < 0.05, sprintf('%.4f', rows.SLOW.ratio));
  check_('H2b', 'FAST@5MHz: 0.1 < raw比 < 0.5 且校正后 |err| < 10% (C24 复现)', ...
         rows.FAST.ratio > 0.1 && rows.FAST.ratio < 0.5 && ...
         abs(rows.FAST.err) < 10.0, ...
         sprintf('比 %.3f, 校正后 %+.2f%%', rows.FAST.ratio, rows.FAST.err));
end

function [err, slips] = h3_one_(K, fn, f_v, vamp, seed)
%H3_ONE_ one bathtub point: corrected amp err + slips at (f_v, vamp).
  t_pre = 0.2e-3;
  T = t_pre + max(8 / f_v, 60e-6);
  N = floor(T * K.HFS);
  t = (0:N-1).' / K.HFS;
  td = max(t - t_pre, 0.0);
  on = double(t >= t_pre);
  sel = t > t_pre + max(3 / f_v, 25e-6);
  x = on .* (vamp / (2 * pi * f_v)) .* (1 - cos(2 * pi * f_v * td));
  v_true = on .* vamp .* sin(2 * pi * f_v * td);
  ph = 4 * pi / K.HLAM * x;
  s2 = 10 ^ (-30 / 10);
  rng = np_rng_new(seed);
  z = exp(1i * ph) + complex_bandlimited_noise(N, K.HFS, K.HBF, s2, rng);
  a_true = ls_amp_(v_true, t, f_v, sel);
  [y, ~, ~, dg] = het_run_pll_(K, z, fn, s2);
  err = 100 * (ls_amp_(het_vdisc_(K, y), t, f_v, sel) / ...
               het_hl_mag_(K, f_v, fn) / a_true - 1);
  slips = dg.near_pi_events;
end

function H3_(K)
  header_(['H3  浴缸谷底夹逼: 每档在 f=fn 处测 0.5*v_pi (应过) 与 2*v_pi ' ...
           '(应败)  (v_pi = pi*lambda*fn/sqrt2 卷绕线谷值, CNR=30dB)']);
  modes = het_mode_params(1.0);
  out_(sprintf('\n    %7s %8s %10s | %19s | %17s', 'mode', 'fn', 'v_pi', ...
               '0.5*v_pi err/slips', '2*v_pi err/slips'));
  ok = true;
  valleys = zeros(1, 3);
  for im = 0:numel(K.HORDER)-1
    name = K.HORDER{im + 1};
    fn = modes.(name).fn;
    v_pi = het_v_pll_limit(fn, fn);
    valleys(im + 1) = v_pi;
    [e1, s1n] = h3_one_(K, fn, fn, 0.5 * v_pi, 265000 + im * 100 + 1);
    [e2, s2n] = h3_one_(K, fn, fn, 2.0 * v_pi, 265000 + im * 100 + 2);
    good1 = (s1n == 0) && (abs(e1) < 25);
    bad2 = (s2n > 0) || (abs(e2) > 25);
    ok = ok && good1 && bad2;
    if good1, t1 = 'pass'; else, t1 = 'FAIL'; end
    if bad2, t2 = 'fail(期望)'; else, t2 = 'PASS?!'; end
    out_(sprintf('    %7s %6.1fk %8.2fmm | %+9.1f%%/%-4d%5s | %+8.1f%%/%-4d%9s', ...
                 name, fn / 1e3, v_pi * 1e3, e1, s1n, t1, e2, s2n, t2));
    key_(sprintf('H3_e1_%s', name), e1);
  end
  check_('H3a', ['三档: 0.5*v_pi 通过 (|err|<25%, 0 slips) 且 2*v_pi 失败 ' ...
         '-- 实测边界夹在卷绕线 2 倍以内'], ok, 'see table');
  check_('H3b', '谷值随档单调上升 (SLOW < MEDIUM < FAST)', ...
         valleys(1) < valleys(2) && valleys(2) < valleys(3), ...
         sprintf('%.2fmm / %.2fmm / %.2fmm', valleys * 1e3));
end

function H4_(K)
  H4CNR = [0, 2, 4, 6, 8];
  nseed = 4;
  modes = het_mode_params(1.0);
  fn = modes.FAST.fn;
  header_(sprintf(['H4  弱回光 PSV 类: FAST@5MHz (fn=%.0fk), CNR 0..8dB 扫描 ' ...
      '(%d seeds) -- 未校正底噪下降 (复现 PSV-500 弱回光实测) 与线 SNR 增益 ' ...
      '(诚实面)'], fn / 1e3, nseed));
  sc = het_scene_(K, 5e6);
  c = het_clean_(K, sc, fn);
  out_(sprintf('\n    %5s | %17s %13s', 'CNR', '底噪下降 dB (raw)', ...
               '线SNR增益 dB'));
  nred = zeros(1, numel(H4CNR));
  for i = 1:numel(H4CNR)
    cnr = H4CNR(i);
    nred(i) = het_nred_(K, sc, fn, cnr, nseed, 270000 + cnr * 100);
    out_(sprintf('    %3ddB | %17.1f %13.1f', cnr, nred(i), ...
                 c.g_sig + nred(i)));
    key_(sprintf('H4_nred_c%d', cnr), nred(i));
  end
  out_(sprintf(['\n  解读: 底噪下降与信号衰减同源于 |H_L| -- 校正恢复刻度但' ...
        '不改变谱线 SNR; 0..8dB 全程在 FM 门限过渡区内,\n  下降量 ~15.2..15.8 ' ...
        'dB 近乎平坦 (非单调, 逐点差在 seed 统计噪声量级), 仅端点呈弱收缩趋势' ...
        ';\n  门限以上 (CNR>=12dB) OFF/ON 同为相位噪声, 下降才真正归零 -- 见 ' ...
        'H1 表 5MHz 行的 gain@12dB 列 (~0 dB).']));
  check_('H4a', 'CNR<=4dB: 未校正底噪下降 > +10 dB (C23 复现)', ...
         all(nred(1:3) > 10.0), ...
         sprintf('0dB:%+.1f, 2dB:%+.1f, 4dB:%+.1f', nred(1), nred(2), nred(3)));
  check_('H4b', ['端点弱收缩: nred(0dB) > nred(8dB) (0..8dB 区间实测近乎平坦, ' ...
         '不断言逐点单调)'], nred(1) > nred(end), ...
         sprintf('%+.1f vs %+.1f dB', nred(1), nred(end)));
end


% ============================================================ X1 cross-compare
function X1_(K, s1_cells, s1_cache)
  header_(['X1  同一运动 (100 kHz, 20 mm/s): 零差 SLOW vs 外差 SLOW -- ' ...
           '诚实的苹果/橘子对照 (非产品排名)']);
  hc = s1_cells{4, 1};                    % (f=100 kHz, v=0.02 m/s)
  g_h = 20 * log10(max(1 + hc.err / 100, 1e-12)) + ...
        s1_cache(ckey_(hc.band, 3, hc.lpf));
  modes = het_mode_params(1.0);
  Kp = K;
  Kp.pick_f = 100e3;
  mode = het_pick_mode_(Kp, modes);
  fn = modes.(mode).fn;
  sc = het_scene_(K, 100e3);
  c = het_clean_(K, sc, fn);
  nr = het_nred_(K, sc, fn, 3, 3, 280000);
  g_t = c.g_sig + nr;
  out_(sprintf('\n    %-26s %22s %22s', '', '零差 (homodyne)', ...
               '外差 (heterodyne)'));
  if hc.lpf, fes = sprintf('%.0f MHz+LPF', hc.B_fe / 1e6);
  else, fes = sprintf('%.0f MHz', hc.B_fe / 1e6); end
  rows = { ...
    '波长 / 采样率', sprintf('1550nm / %.0fMS/s', K.FS / 1e6), ...
        sprintf('%.1fnm / %.0fMS/s', K.HLAM * 1e9, K.HFS / 1e6); ...
    '前端 (噪声 ENBW)', fes, sprintf('%.0f MHz', K.HBF / 1e6); ...
    '档 / fn', sprintf('%s / %.0fk', hc.band, K.BANDS.(hc.band).fn / 1e3), ...
        sprintf('%s / %.1fk', mode, fn / 1e3); ...
    'B_loop', sprintf('%.2f MHz', b_loop(K.BANDS.(hc.band).fn) / 1e6), ...
        sprintf('%.0f kHz', het_b_loop(fn) / 1e3); ...
    '测量带宽', sprintf('%.0f MHz 公共残差窗', K.B_WIN / 1e6), ...
        sprintf('f_3dB = %.0f kHz (档定)', modes.(mode).f_3db / 1e3); ...
    'clean ampErr', sprintf('%+.2f%%', hc.err), ...
        sprintf('%+.2f%% (频响校正后)', c.err); ...
    'SNR gain @CNR=3dB', sprintf('%+.1f dB', g_h), ...
        sprintf('%+.1f dB', g_t)};
  for i = 1:size(rows, 1)
    out_(sprintf('    %-26s %22s %22s', rows{i, 1}, rows{i, 2}, rows{i, 3}));
  end
  out_(['    (零差数字与 validate_tracking V1 的 SLOW +38dB 同一物理, 评估带' ...
        '不同: 此处为 10..100kHz 结构带的静态载波底噪下降)']);
  key_('X1_gain_homodyne', g_h);
  key_('X1_gain_heterodyne', g_t);
  out_('');
  out_('  苹果/橘子注记 (必须读):');
  out_('    - 波长不同: 同一 20 mm/s 在 1550 nm 是 25.8 kHz 多普勒, 在 632.8 nm 是');
  out_('      63.2 kHz -- 相位摆幅差 2.45x, 两环工作点并不相同.');
  out_('    - 前端不同: 零差 40 MHz 噪声带 (fD=25.8kHz << 20MHz, 物理规则不触发 86M');
  out_('      前端) vs 外差 19 MHz, "CNR=3dB" 的');
  out_('      噪声 PSD 完全不同; 增益各自相对自己的 OFF 参考, 不能跨列相减.');
  out_('    - 架构不同: 零差增益含残差窗点击清除 (B_loop < B_win 条件), 换档不改');
  out_('      测量带宽; 外差增益是纯 NCO 的 FM 门限扩展, 换档同时改变测量带宽.');
  out_('    - 结论只有一个是公平的: 两种架构在各自设计域内都给出 >+10dB 量级的');
  out_('      弱光门限扩展, 且幅值刻度保持 -- 选型依据见 OPTIMIZATION_GUIDE 决策树.');
  check_('X1a', '两架构在该工况各自 SNR gain > +10 dB (各自参考系内)', ...
         g_h > 10.0 && g_t > 10.0, ...
         sprintf('homo %+.1f, het %+.1f dB', g_h, g_t));
end


% ==================================== results .mat (plot_scenario_results contract)
function save_contract_mat_(here, KY, CH)
%SAVE_CONTRACT_MAT_ same field contract as the earlier interface stub
%   (map_* / spk_* / bath_*), now filled by the FULL study run (is_stub=0),
%   plus the machine-readable key metrics.  Consumed by
%   plot_scenario_results.m -- do not rename or reshape these fields.
  R = struct();
  R.schema_version = 1;
  R.is_stub = 0;
  R.created = datestr(now, 'yyyy-mm-dd HH:MM:SS');

  C = homodyne_constants();
  Nf = 61;
  Nv = 41;
  R.map_f_hz = logspace(3, log10(3e6), Nf);
  R.map_v_mps = logspace(-3, log10(30), Nv);
  R.map_band_order = {'SLOW', 'MEDIUM', 'FAST'};
  R.map_phi_guard_rad = C.PHI_GUARD;
  R.map_phi_err_rad = zeros(Nv, Nf);
  R.map_band_idx = zeros(Nv, Nf);
  for iv = 1:Nv
    for jf = 1:Nf
      f = R.map_f_hz(jf);
      v = R.map_v_mps(iv);
      band = select_band(f, v);
      R.map_band_idx(iv, jf) = find(strcmp(band, R.map_band_order));
      R.map_phi_err_rad(iv, jf) = ...
          tracking_error_rad(f, v, C.BANDS.(band).fn);
    end
  end

  R.spk_M = 1:6;
  R.spk_F = [0.3567, 0.105];
  R.spk_rho = 0.0;
  R.spk_tau_c_s = 50e-6;
  R.spk_fs_hz = 400e3;
  R.spk_T_s = 1.0;
  R.spk_nseed = 1;
  R.spk_p_theory = zeros(numel(R.spk_F), numel(R.spk_M));
  R.spk_p_mc = nan(numel(R.spk_F), numel(R.spk_M));
  Nmc = floor(R.spk_T_s * R.spk_fs_hz);
  for im = 1:numel(R.spk_M)
    M = R.spk_M(im);
    set_rng(40000 + 97 * M);
    h = make_speckle_multi(Nmc, R.spk_fs_hz, R.spk_tau_c_s, M, R.spk_rho);
    for kf = 1:numel(R.spk_F)
      R.spk_p_theory(kf, im) = fade_prob_theory(R.spk_F(kf), M);
      R.spk_p_mc(kf, im) = joint_fade_fraction(h, R.spk_F(kf));
    end
  end

  P = het_params();
  R.bath_v_range_mps = P.V_RANGE_DEFAULT;
  R.bath_lambda_m = P.LAMBDA;
  R.bath_e_crit_rad = pi;
  R.bath_gear_order = P.ORDER;
  modes = het_mode_params(R.bath_v_range_mps);
  Nb = 121;
  R.bath_f_hz = logspace(2, log10(2e6), Nb);
  R.bath_fn_hz = zeros(1, 3);
  R.bath_v_pll_mps = zeros(3, Nb);
  for ig = 1:numel(P.ORDER)
    fn = modes.(P.ORDER{ig}).fn;
    R.bath_fn_hz(ig) = fn;
    R.bath_v_pll_mps(ig, :) = het_v_pll_limit(R.bath_f_hz, fn);
  end
  R.bath_v_if_mps = het_v_if_limit();
  R.bath_v_alias_mps = het_v_alias_limit();

  R.key_names = {KY.name};
  R.key_values = [KY.val];
  R.checks_ok = double([CH.ok]);
  R.checks_pass = sum(R.checks_ok);
  R.checks_total = numel(R.checks_ok);

  out_mat = fullfile(here, 'results_realistic_scenarios.mat');
  if exist('OCTAVE_VERSION', 'builtin') ~= 0
    save('-v7', out_mat, '-struct', 'R');
  else
    save(out_mat, '-struct', 'R', '-v7');
  end
  fprintf('[plotting contract saved to %s]\n', out_mat);
end
