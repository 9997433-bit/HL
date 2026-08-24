function ch = channel_demod(z, fs, band, Nhat, gate, use_residual)
%CHANNEL_DEMOD One diversity channel: homodyne gear path + FM discriminator.
% Port of diversity_combine.py::channel_demod.
% use_residual=true runs the full gear_filter path (PLL carrier + common
% B_WIN residual window); false keeps the pure-NCO carrier path only.
% Returns a struct with fields y, v, phi, state, gs, C, diag (columns).
  if nargin < 5 || isempty(gate)
    gate = 'auto';
  end
  if nargin < 6 || isempty(use_residual)
    use_residual = true;
  end
  P = hd_params();
  gp = hd_gate_params(band);
  fn = P.BANDS.(band).fn;
  z = z(:);
  [y_nco, phi, st, dg] = pll_carrier_regen(z, fs, fn, Nhat, ...
      'zeta', P.ZETA, 'gate', gate, ...
      'tauP', gp.tauP, 'tauF', gp.tauF, ...
      'snr_on', gp.snr_on, 'snr_off', gp.snr_off, ...
      'rel_on', gp.rel_on, 'rel_off', gp.rel_off, ...
      'tauRef', gp.tauRef, 'reacq', gp.reacq);
  if strcmp(gate, 'always')
    gs = ones(numel(z), 1);
  else
    gs = iir1_lowpass(double(st == 2), exp(-1.0 / (fs * P.TAU_G)));
  end
  if use_residual
    rot = exp(-1i * phi);
    rf = fir_lp_same(z .* rot, P.B_WIN, fs, P.NT_WIN);
    resph = angle(rf) .* (abs(rf) > 1e-12);
    y = conj(rot) .* exp(1i * (gs .* resph));
  else
    y = y_nco;
  end
  C = estimate_C(z, fs, Nhat, gp.tauP);
  v = fm_discriminator(y, fs, P.LAMBDA);
  ch = struct('y', y, 'v', v, 'phi', phi, 'state', st, ...
              'gs', gs, 'C', C, 'diag', dg);
end
