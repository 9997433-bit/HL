function G = export_golden_core()
%EXPORT_GOLDEN_CORE Fixed-seed smoke tests -> matlab/golden/core_smoke.mat.
%   G = export_golden_core()
%   Runs the deterministic smoke suite over the homodyne core /
%   design_params / ellipse port and saves every result as a numeric field
%   of matlab/golden/core_smoke.mat.  The Python twin
%   (matlab/export_python_golden.py) computes the SAME fields with the
%   SAME portable LCG noise (lcg_init/lcg_randn <-> PortableLCG), so the
%   two golden files agree to rtol=1e-10 (verified by compare_with_python).
%
%   Encoding conventions (shared with the Python exporter):
%     band names   -> gear index, SLOW=1, MEDIUM=2, FAST=3
%     Python None  -> -1
%     booleans     -> 1/0
  homodyne_setup_path();
  G = struct();

  % ---------------------------------------------------------- S1 FIR kernel
  G.fir_kernel = fir_lp_kernel(4e6, 250e6, 1025);

  % ---------------------------------------------------------- S2/S3 burst
  fs_b = 10e6;
  Nb = 4000;
  t_b = (0:Nb-1).' / fs_b;
  [bx, bv, be] = burst_signal(t_b, 1e5, 0.02, 5, 5e-5);
  G.burst_x = bx;
  G.burst_v = bv;
  G.burst_env = be;
  G.lockin_val = lockin_amp(bv, t_b, 1e5, be > 0);
  y_fl = fir_lp(bx, 2e5, fs_b);
  G.fir_lp_y = y_fl(1:1000);

  % ---------------------------------------------------------- S4 H_L(f)
  f_hl = [0, 1e3, 1e4, 1e5, 2e5, 5e5, 1e6, 2e6, 3e6].';
  H = hl_response(f_hl, 250e6, 110e3, 1.2);
  G.hl_slow_re = real(H);  G.hl_slow_im = imag(H);
  H = hl_response(f_hl, 250e6, 530e3, 1.2);
  G.hl_med_re = real(H);   G.hl_med_im = imag(H);
  H = hl_response(f_hl, 250e6, 1.6e6, 1.2);
  G.hl_fast_re = real(H);  G.hl_fast_im = imag(H);

  % ---------------------------------------------------------- S5 gear select
  C = homodyne_constants();
  bidx = @(name) find(strcmp(C.ORDER, name), 1);
  f_nov = [50e3, 150e3, 200e3, 250e3, 500e3, 1e6, 1.5e6, 3e6, 5e6];
  G.selband_nov = zeros(numel(f_nov), 1);
  for i = 1:numel(f_nov)
    G.selband_nov(i) = bidx(select_band(f_nov(i)));
  end
  fv = [100e3, 30.0; 3e6, 0.02; 1e6, 1.0; 200e3, 0.5; 100e3, 0.001; 500e3, 0.05];
  G.selband_v = zeros(size(fv, 1), 1);
  for i = 1:size(fv, 1)
    G.selband_v(i) = bidx(select_band(fv(i, 1), fv(i, 2)));
  end
  hy = {50e3, 'FAST', []; 3e6, 'SLOW', []; 50e3, 'MEDIUM', []; ...
        1e6, 'SLOW', []; 100e3, 'BOGUS', []; 200e3, 'FAST', 0.5};
  G.selband_hyst = zeros(size(hy, 1), 1);
  for i = 1:size(hy, 1)
    G.selband_hyst(i) = bidx(select_band_hysteresis(hy{i, 1}, hy{i, 2}, hy{i, 3}));
  end

  % ---------------------------------------------------------- S6 band specs
  G.specs_slow = spec_vec(band_specs('SLOW'));
  G.specs_med = spec_vec(band_specs('MEDIUM'));
  G.specs_fast = spec_vec(band_specs('FAST'));
  G.loop_misc = [C.B_LOOP_COEF; C.F3DB_COEF; loop_error_mag(1e5, 110e3); ...
                 tracking_error_rad(1e5, 0.5, 530e3); C.PHI_GUARD];
  gf = guard_flags(1e5, 30.0, 'FAST');
  G.guard_fast = [gf.phi_err; double(gf.guard_ok); double(gf.overrange)];
  T = as_struct_table();
  G.table_val = [T.SLOW.fn; T.MEDIUM.Kp; T.FAST.B_loop];

  % ---------------------------------------------------------- S7 cfg structs
  cfgs = {cfg_for_frequency(3e6, 0.02), ...
          cfg_for_frequency(100e3, 30.0), ...
          cfg_for_frequency(150e3), ...
          cfg_for_frequency(3e6, [], 'SLOW', true), ...
          cfg_for_frequency(50e3, [], 'FAST', true)};
  G.cfg_flags = zeros(4 * numel(cfgs), 1);
  for i = 1:numel(cfgs)
    c = cfgs{i};
    G.cfg_flags(4*i-3 : 4*i) = [bidx(c.band); enc(c.phi_err); ...
                                enc(c.guard_ok); enc(c.overrange)];
  end
  cfl = cfg_for_frequency(1e6, [], 'SLOW', true, 'fixed_lp');
  G.cfg_fixed = [cfl.B_win; cfl.NT_win];

  % ---------------------------------------------------------- S8 PLL smoke
  fs = 10e6;
  Npll = 20000;
  sigma = 0.05;
  Nhat = sigma ^ 2;
  t = (0:Npll-1).' / fs;
  ph = (2*pi*200e3) * t + 0.8 * sin((2*pi*5e3) * t);
  env = ones(Npll, 1);
  env(8001:9000) = 0.02;
  st = lcg_init(12345);
  [nr, st] = lcg_randn(st, Npll);
  [ni, st] = lcg_randn(st, Npll);  %#ok<NASGU>
  s2 = sigma / sqrt(2);
  z = (env .* cos(ph) + s2 * nr) + 1i * (env .* sin(ph) + s2 * ni);

  opts = struct('zeta', 1.2, 'tauP', 2e-6, 'tauF', 2e-6, 'gate', 'auto');
  [~, phi_p, state_p, dg] = pll_carrier_regen(z, fs, 530e3, Nhat, opts);
  G.pll_phi_head = phi_p(1:2000);
  G.pll_phi_tail = phi_p(end-1999:end);
  G.pll_state_counts = [sum(state_p == 0); sum(state_p == 1); sum(state_p == 2)];
  G.pll_diag = [dg.near_pi_events; dg.n_hold; dg.n_acquire; ...
                dg.n_lock_entries; dg.n_reacq; dg.lock_frac];
  opts.gate = 'always';
  [~, phi_a] = pll_carrier_regen(z, fs, 530e3, Nhat, opts);
  G.pll_always_phi = phi_a(1:2000);

  % ------------------------------------------------- S9 tracking_filter smoke
  % explicit v_peak=0.02 keeps SLOW: v_peak=[] now defaults to
  % APP_V_PEAK_MAX=30 m/s -> FAST in overrange, where cycle-slip timing
  % amplifies 1-ulp cross-language differences (S7 already covers the
  % []-default selection logic bit-exactly).
  cfg = cfg_for_frequency(200e3, 0.02, 'SLOW', true, 'pll', 'auto');
  [y_t, phi_t, state_t] = tracking_filter(z, fs, cfg, Nhat);
  G.trk_y_re = real(y_t(5001:6000));
  G.trk_y_im = imag(y_t(5001:6000));
  G.trk_phi = phi_t(5001:6000);
  G.trk_state_counts = [sum(state_t == 0); sum(state_t == 1); sum(state_t == 2)];
  fmv = fm_discriminator(y_t, fs, 1550e-9);
  G.trk_fm = fmv(5001:6000);

  % ------------------------------------------------- S10 off / fixed_lp modes
  [~, phi_off] = off_mode(z);
  G.off_phi = phi_off(1:1000);
  y_fx = fixed_lp_mode(z, fs, 4e6, 1025);
  G.fx_y_re = real(y_fx(5001:6000));
  G.fx_y_im = imag(y_fx(5001:6000));

  % ---------------------------------------------------------- S11 iir1 / welch
  i5 = (0:4999).';
  x_iir = sin((2*pi*3e3) * (i5 / fs)) + double(mod(i5, 7) == 0);
  y_iir = iir1_lowpass(x_iir, exp(-1 / (fs * 2e-6)));
  G.iir1_y = y_iir(1:1000);
  [Pw, fw] = welch_psd(z, fs, 1024);
  G.welch_P = Pw;
  G.welch_f = fw;

  % --------------------------------------------------- S12 LCG noise / speckle
  nb_ = complex_bandlimited_noise(4096, 10e6, 2e6, 0.5, 4242);
  G.noise_re = real(nb_(1:500));
  G.noise_im = imag(nb_(1:500));
  sp = make_speckle(4096, 10e6, 1e-4, 999, 0.5);
  G.speckle_re = real(sp(1:500));
  G.speckle_im = imag(sp(1:500));

  % ---------------------------------------------------------- S13 Heydemann fit
  Ne = 6000;
  d0 = 8 * pi / 180;
  st = lcg_init(777);
  [n1, st] = lcg_randn(st, Ne);
  [n2, st] = lcg_randn(st, Ne);  %#ok<NASGU>
  i_e = (0:Ne-1).';
  a_e = (0.85 * 2 * pi) * i_e / Ne;
  u_e = (0.12 + 1.05 * cos(a_e)) + 0.01 * n1;
  v_e = (-0.08 + 0.92 * sin(a_e + d0)) + 0.01 * n2;
  [par, res] = heydemann_fit(u_e, v_e);
  G.hey_par = [par.p; par.q; par.A; par.B; par.delta];
  G.hey_res = [res.rms; res.algebraic_rms; res.arc; res.arc_all; ...
               res.design_cond; double(res.ok)];
  G.hey_theta = res.theta(:);
  [~, ~, z_h] = heydemann_apply(u_e, v_e, par);
  G.hey_z_re = real(z_h(1:500));
  G.hey_z_im = imag(z_h(1:500));
  G.hey_arc_corr = arc_span_corrected(u_e, v_e, par);

  % ---------------------------------------------------------- S14 gated fit
  prev = struct('p', 0.13, 'q', -0.09, 'A', 1.071, 'B', 0.9016, ...
                'delta', d0 + 0.01);
  [gp, gres] = fit_arc_gated(u_e, v_e, prev);
  G.gated_par = [gp.p; gp.q; gp.A; gp.B; gp.delta];
  G.gated_flags = [double(gres.ok); gres.arc];

  % --------------------------------------- S15 segmented / interp / online p,q
  Nl = 12000;
  fs_e = 1000.0;
  st = lcg_init(2024);
  [m1, st] = lcg_randn(st, Nl);
  [m2, st] = lcg_randn(st, Nl);  %#ok<NASGU>
  i_l = (0:Nl-1).';
  a_l = (2 * pi * 6) * i_l / Nl;
  u_l = ((0.12 + 0.05 * i_l / Nl) + 1.05 * cos(a_l)) + 0.008 * m1;
  v_l = (-0.08 + 0.92 * sin(a_l + d0)) + 0.008 * m2;
  [t_c, pars, oks, arcs] = segmented_heydemann(u_l, v_l, fs_e, 2.0);
  G.seg_t_c = t_c;
  G.seg_oks = double(oks(:));
  G.seg_arcs = arcs;
  Kseg = numel(pars);
  [G.seg_p, G.seg_q, G.seg_A, G.seg_B, G.seg_delta] = deal(zeros(Kseg, 1));
  for k = 1:Kseg
    G.seg_p(k) = pars{k}.p;
    G.seg_q(k) = pars{k}.q;
    G.seg_A(k) = pars{k}.A;
    G.seg_B(k) = pars{k}.B;
    G.seg_delta(k) = pars{k}.delta;
  end
  t_q = i_l / fs_e;
  trk = interp_par_track(t_q, t_c, pars);
  G.interp_p = trk.p(1:50:end);
  z_a = apply_par_track(u_l, v_l, trk);
  G.apl_z_re = real(z_a(1:500));
  G.apl_z_im = imag(z_a(1:500));

  gd0 = struct('p', 0.12, 'q', -0.08, 'A', 1.05, 'B', 0.92, 'delta', d0);
  ob = online_bias_tracker_init(gd0, fs_e, 0.1);
  [z_o, ob] = online_bias_tracker_run(ob, u_l, v_l);
  G.obt_pq = [ob.p; ob.q];
  G.obt_z_re = real(z_o(end-499:end));
  G.obt_z_im = imag(z_o(end-499:end));

  % ---------------------------------------------------------------- save
  gdir = fullfile(fileparts(mfilename('fullpath')), 'golden');
  if ~exist(gdir, 'dir')
    mkdir(gdir);
  end
  fname = fullfile(gdir, 'core_smoke.mat');
  save('-v7', fname, '-struct', 'G');
  fprintf('export_golden_core: wrote %s (%d fields)\n', ...
          fname, numel(fieldnames(G)));
end

function x = enc(v)
% Python None (represented as NaN by the MATLAB port) -> -1; bool -> 1/0.
  if isempty(v) || (isnumeric(v) && any(isnan(v)))
    x = -1;
  else
    x = double(v);
  end
end

function w = spec_vec(s)
  w = [s.fn; s.zeta; s.Kp; s.Ki; s.f_target_max; s.B_loop; s.f_3db; ...
       s.a_design; s.B_win; s.ceiling_db; s.sigma_phi_at_cnr; ...
       s.snr_on; s.snr_off; s.rel_on; s.rel_off; s.tauRef; ...
       double(s.reacq); s.tauP; s.tauF];
end
