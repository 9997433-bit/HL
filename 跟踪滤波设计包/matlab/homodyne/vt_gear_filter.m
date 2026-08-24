function [y_full, y_nco, phi, st, dg] = vt_gear_filter(z, band, Nhat, gate)
%VT_GEAR_FILTER One gear: PLL carrier path + common residual window.
%   Port of validate_tracking.gear_filter.
  dp = design_params();
  if nargin < 4 || isempty(gate), gate = 'auto'; end
  opts = gate_params(band);
  opts.zeta = dp.ZETA;
  opts.gate = gate;
  [y_nco, phi, st, dg] = pll_carrier_regen(z, dp.FS, dp.BANDS.(band).fn, ...
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
