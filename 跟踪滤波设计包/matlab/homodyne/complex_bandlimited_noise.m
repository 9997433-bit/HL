function n = complex_bandlimited_noise(N, fs, B_enbw, power)
%COMPLEX_BANDLIMITED_NOISE Flat two-sided complex Gaussian noise, |f| <= B_enbw/2.
% Port of core.py::complex_bandlimited_noise.  Uses the global randn state
% (the Python version takes an explicit rng; seed with set_rng(seed) before
% calling for reproducible-in-Octave draws).  Returns an N x 1 column.
  Nf = 2 ^ ceil(log2(2 * N));
  f = ((0:Nf - 1)' - floor(Nf / 2)) * (fs / Nf);
  mask = abs(f) <= B_enbw / 2;
  X = zeros(Nf, 1);
  k = sum(mask);
  X(mask) = (randn(k, 1) + 1i * randn(k, 1)) / sqrt(2);
  x = ifft(ifftshift(X));
  i0 = floor((Nf - N) / 2);
  n = x(i0 + 1:i0 + N);
  n = n - mean(n);
  if power > 0
    n = n * sqrt(power / max(mean(abs(n) .^ 2), 1e-300));
  end
end
