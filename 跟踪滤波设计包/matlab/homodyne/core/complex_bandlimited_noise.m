function n = complex_bandlimited_noise(N, fs, B_enbw, power, rng_in)
%COMPLEX_BANDLIMITED_NOISE Flat two-sided complex Gaussian noise, |f| <= B_enbw/2.
%   n = complex_bandlimited_noise(N, fs, B_enbw, power, rng_in)
%   Faithful port of core.py complex_bandlimited_noise.  Returns an N-by-1
%   complex column vector.
%
%   rng_in: either a numeric seed (portable LCG stream, matches the Python
%   golden export bit-for-bit) or a function handle f(k) returning k
%   standard normals (e.g. @(k) randn(k, 1) for MATLAB-native noise).
%   The real vector is drawn first, then the imaginary vector, matching
%   the Python draw order rng.standard_normal(k) + 1j*rng.standard_normal(k).
  Nf = 2 ^ ceil(log2(2 * N));
  f = ((0:Nf-1).' - floor(Nf / 2)) * (fs / Nf);
  mask = abs(f) <= B_enbw / 2;
  X = zeros(Nf, 1);
  k = sum(mask);
  if isnumeric(rng_in)
    st = lcg_init(rng_in);
    [a, st] = lcg_randn(st, k);
    [b, st] = lcg_randn(st, k);  %#ok<NASGU>
  else
    a = rng_in(k); a = a(:);
    b = rng_in(k); b = b(:);
  end
  X(mask) = (a + 1i * b) / sqrt(2);
  x = ifft(ifftshift(X));
  i0 = floor((Nf - N) / 2);
  n = x(i0+1 : i0+N);
  n = n - mean(n);
  if power > 0
    n = n * sqrt(power / max(mean(abs(n) .^ 2), 1e-300));
  end
end
