function Y = iir1_lowpass(x, a)
%IIR1_LOWPASS y[n] = (1-a)x[n] + a y[n-1], as FFT convolution with the exact kernel.
% Port of core.py::iir1_lowpass (zero initial state).  Column in/out.
  x = x(:);
  n = numel(x);
  L = min(n, max(8, ceil(log(1e-16) / log(a))));
  k = (1 - a) * a .^ (0:L - 1)';
  nfft = 2 ^ ceil(log2(n + L));
  Y = ifft(fft(x, nfft) .* fft(k, nfft));
  Y = Y(1:n);
  if isreal(x)
    Y = real(Y);
  end
end
