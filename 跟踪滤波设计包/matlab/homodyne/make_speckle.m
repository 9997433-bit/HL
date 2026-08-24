function h = make_speckle(N, fs, tau_c, K)
%MAKE_SPECKLE Band-limited complex speckle, Gaussian Doppler spectrum, R(tau_c)=1/e.
% Port of core.py::make_speckle.  Uses the global randn state (seed with
% set_rng first).  Returns an N x 1 column, unit sample mean power.
  if nargin < 4
    K = 0.0;
  end
  Nf = 2 ^ ceil(log2(2 * N));
  f = ((0:Nf - 1)' - floor(Nf / 2)) * (fs / Nf);
  sf = 1.0 / (pi * tau_c * sqrt(2));
  S = exp(-f .^ 2 / (2 * sf ^ 2));
  A = sqrt(S);
  xi = (randn(Nf, 1) + 1i * randn(Nf, 1)) / sqrt(2);
  hf = ifft(ifftshift(A) .* xi);
  h = hf(1:N);
  h = h / sqrt(mean(abs(h) .^ 2));
  if K > 0
    h = (sqrt(K) + h) / sqrt(1 + K);
    h = h / sqrt(mean(abs(h) .^ 2));
  end
end
