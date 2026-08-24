function h = make_speckle(N, fs, tau_c, rng_in, K)
%MAKE_SPECKLE Band-limited complex speckle, Gaussian Doppler spectrum, R(tau_c)=1/e.
%   h = make_speckle(N, fs, tau_c, rng_in, K)
%   Faithful port of core.py make_speckle.  Returns an N-by-1 complex column.
%   rng_in: numeric seed (portable LCG) or function handle f(k) -> k normals.
%   Draw order matches Python: Nf reals first, then Nf imaginaries.
  if nargin < 5
    K = 0.0;
  end
  Nf = 2 ^ ceil(log2(2 * N));
  f = ((0:Nf-1).' - floor(Nf / 2)) * (fs / Nf);
  sf = 1.0 / (pi * tau_c * sqrt(2));
  S = exp(-f .^ 2 / (2 * sf ^ 2));
  A = sqrt(S);
  if isnumeric(rng_in)
    st = lcg_init(rng_in);
    [a, st] = lcg_randn(st, Nf);
    [b, st] = lcg_randn(st, Nf);  %#ok<NASGU>
  else
    a = rng_in(Nf); a = a(:);
    b = rng_in(Nf); b = b(:);
  end
  xi = (a + 1i * b) / sqrt(2);
  hf = ifft(ifftshift(A) .* xi);
  h = hf(1:N);
  h = h / sqrt(mean(abs(h) .^ 2));
  if K > 0
    h = (sqrt(K) + h) / sqrt(1 + K);
    h = h / sqrt(mean(abs(h) .^ 2));
  end
end
