function y = iir1_lowpass(x, a)
%IIR1_LOWPASS y[n] = (1-a)x[n] + a y[n-1] via FFT conv with the exact kernel.
%   Port of core.iir1_lowpass.
  x = x(:);
  L = min(numel(x), max(8, ceil(log(1e-16) / log(a))));
  k = (1 - a) * a.^(0:L-1)';
  n = numel(x);
  nfft = 2^ceil(log2(n + L));
  Y = ifft(fft(x, nfft) .* fft(k, nfft));
  Y = Y(1:n);
  if isreal(x)
    y = real(Y);
  else
    y = Y;
  end
end
