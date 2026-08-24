function h = make_speckle_multi(N, fs, tau_c, M, rho)
%MAKE_SPECKLE_MULTI M-channel band-limited Rayleigh speckle, (M x N) complex.
% Port of qtec_diversity_design/speckle_multi.py::make_speckle_multi.
% rho is the pairwise complex FIELD correlation E[h_j h_k*] (j ~= k), built
% as h_k = sqrt(rho)*h_common + sqrt(1-rho)*g_k.  Each channel re-normalised
% to unit sample mean power.  Uses the global randn state (set_rng first);
% draw ORDER matches the Python source (common first, then g_1..g_M).
  if nargin < 5 || isempty(rho)
    rho = 0.0;
  end
  if ~(rho >= 0.0 && rho < 1.0)
    error('make_speckle_multi: rho must be in [0, 1)');
  end
  if rho > 0.0
    common = make_speckle(N, fs, tau_c);
  else
    common = [];
  end
  h = zeros(M, N);
  for k = 1:M
    g = make_speckle(N, fs, tau_c);
    if rho > 0.0
      hk = sqrt(rho) * common + sqrt(1.0 - rho) * g;
    else
      hk = g;
    end
    h(k, :) = (hk / sqrt(mean(abs(hk) .^ 2))).';
  end
end
