function y = fir_lp_same(x, fc, fs, Nt)
%FIR_LP_SAME Linear-phase FIR low-pass via FFT convolution, group-delay compensated.
% Port of core.py::fir_lp_same ('same' alignment: the (Nt-1)/2-sample group
% delay is removed by slicing).  Column in/out.
  x = x(:);
  h = fir_lp_kernel(fc, fs, Nt);
  nfft = 2 ^ ceil(log2(numel(x) + Nt));
  y = ifft(fft(x, nfft) .* fft(h, nfft));
  d = floor((Nt - 1) / 2);
  y = y(d + 1:d + numel(x));
  if isreal(x)
    y = real(y);
  end
end
