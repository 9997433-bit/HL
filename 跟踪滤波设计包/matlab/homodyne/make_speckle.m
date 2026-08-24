function h = make_speckle(N, fs, tau_c, rh, K)
%MAKE_SPECKLE Band-limited complex speckle, Gaussian Doppler spectrum.
%   Port of core.make_speckle; R(tau_c) = 1/e.  rh from np_rng_new(seed).
  if nargin < 5 || isempty(K), K = 0.0; end
  Nf = 2^ceil(log2(2 * N));
  f = ((0:Nf-1)' - floor(Nf / 2)) * (fs / Nf);
  sf = 1.0 / (pi * tau_c * sqrt(2));
  S = exp(-f.^2 / (2 * sf^2));
  A = sqrt(S);
  xr = np_rng_randn(rh, Nf);
  xi = np_rng_randn(rh, Nf);
  g = (xr + 1i * xi) / sqrt(2);
  hf = ifft(ifftshift(A) .* g);
  h = hf(1:N);
  h = h / sqrt(mean(abs(h).^2));
  if K > 0
    h = (sqrt(K) + h) / sqrt(1 + K);
    h = h / sqrt(mean(abs(h).^2));
  end
end
