function n = complex_bandlimited_noise(N, fs, B_enbw, power, rh)
%COMPLEX_BANDLIMITED_NOISE Flat two-sided complex Gaussian noise |f|<=B/2.
%   Port of core.complex_bandlimited_noise.  rh is an RNG handle from
%   np_rng_new(seed); the draw order matches numpy exactly (real block then
%   imag block), so with the numpy-exact RNG kernel the noise realization is
%   identical to the Python reference.
  Nf = 2^ceil(log2(2 * N));
  f = ((0:Nf-1)' - floor(Nf / 2)) * (fs / Nf);
  mask = abs(f) <= B_enbw / 2;
  k = sum(mask);
  X = zeros(Nf, 1);
  xr = np_rng_randn(rh, k);
  xi = np_rng_randn(rh, k);
  X(mask) = (xr + 1i * xi) / sqrt(2);
  x = ifft(ifftshift(X));
  i0 = floor((Nf - N) / 2);
  n = x(i0+1:i0+N);
  n = n - mean(n);
  if power > 0
    n = n * sqrt(power / max(mean(abs(n).^2), 1e-300));
  end
end
