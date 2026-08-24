function y = iir1_lowpass(x, a)
%IIR1_LOWPASS y[n] = (1-a)x[n] + a y[n-1], done as FFT convolution with the exact kernel.
%   y = iir1_lowpass(x, a)   Faithful port of core.py iir1_lowpass.
%   x treated as a column vector; y is N-by-1 (real if x is real).
  x = x(:);
  n = numel(x);
  L = min(n, max(8, ceil(log(1e-16) / log(a))));
  k = (1 - a) * a .^ (0:L-1).';
  nfft = 2 ^ ceil(log2(n + L));
  Y = ifft(fft(x, nfft) .* fft(k, nfft));
  Y = Y(1:n);
  if isreal(x)
    y = real(Y);
  else
    y = Y;
  end
end
