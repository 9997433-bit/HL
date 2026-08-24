function m = ve_metrics(x_est, x_ref, t, f0, sel)
%VE_METRICS Per-segment RMS / amplitude / SNR metric of the ellipse validators.
%   m = ve_metrics(x_est, x_ref, t, f0, sel)
%   Faithful port of validate_ellipse_dynamic.metrics: single-bin complex
%   amplitude at f0 (est vs ref), RMS of the residual after removing the
%   estimated sine (nm), and a Welch line SNR (sig |f-f0|<=3 Hz over floor
%   8..40 Hz offsets, L=4096 @ 2.5 MS/s).  sel is a logical mask.
  c = ve_const();
  ts = t(sel);
  xs = x_est(sel);
  xr = x_ref(sel);
  xs = xs - mean(xs);
  xr = xr - mean(xr);
  c_est = 2 * mean(xs .* exp(-1i * 2 * pi * f0 * ts));
  c_ref = 2 * mean(xr .* exp(-1i * 2 * pi * f0 * ts));
  amp_err = 100 * (abs(c_est) / max(abs(c_ref), 1e-30) - 1);
  sine = real(c_est) * cos(2 * pi * f0 * ts) ...
         - imag(c_est) * sin(2 * pi * f0 * ts);
  e = xs - sine;
  rms = sqrt(mean(e .^ 2)) * 1e9;
  [P, fx] = welch_psd(e, c.FS, 4096);
  off = abs(fx - f0);
  sig = off <= 3;
  flo = (off >= 8) & (off <= 40);
  snr = 10 * log10(max(sum(P(sig)), 1e-30) / ...
                   max(sum(P(flo)) * sum(sig) / max(sum(flo), 1), 1e-30));
  m = struct('rms', rms, 'amp', amp_err, 'snr', snr);
end
