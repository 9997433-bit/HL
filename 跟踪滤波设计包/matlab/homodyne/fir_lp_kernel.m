function h = fir_lp_kernel(fc, fs, Nt)
%FIR_LP_KERNEL Hann-windowed-sinc linear-phase low-pass kernel, DC-normalised.
% Port of core.py::fir_lp_kernel (single source of truth for the residual
% measurement window).  Returns an Nt x 1 column.
  n = (0:Nt - 1)' - (Nt - 1) / 2;
  u = 2 * fc / fs * n;
  h = ones(Nt, 1);
  nz = u ~= 0;
  h(nz) = sin(pi * u(nz)) ./ (pi * u(nz));
  h = h .* ((2 * fc / fs) * (0.5 * (1 - cos(2 * pi * (0:Nt - 1)' / (Nt - 1)))));
  h = h / sum(h);
end
