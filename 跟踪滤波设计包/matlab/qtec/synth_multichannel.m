function out = synth_multichannel(phi, fs, M, cnr_db, varargin)
%SYNTH_MULTICHANNEL M-channel IQ synthesis  z_k = h_k * exp(j(phi + psi_k)) + n_k.
% Port of synth_multichannel.py::synth_multichannel.
%
%   out = synth_multichannel(phi, fs, M, cnr_db, 'name', value, ...)
%
% Options: 'tau_c' [] (-> static unit-amplitude channels), 'rho' 0.0,
% 'B_noise' 20e6, 'psi' [] (-> uniform random in [-pi, pi)).
% Uses the global RNG state (set_rng first); draw order matches the Python
% source (psi -> speckle -> per-channel noise).
% Returns struct with z (M x N complex), h (M x N), psi (M x 1), s2.
  o = struct('tau_c', [], 'rho', 0.0, 'B_noise', 20e6, 'psi', []);
  for k = 1:2:numel(varargin)
    o.(varargin{k}) = varargin{k + 1};
  end
  phi = phi(:).';
  N = numel(phi);
  s2 = 10.0 ^ (-cnr_db / 10.0);
  if isempty(o.psi)
    % np.random.Generator.uniform(-pi, pi, M)
    psi = -pi + 2 * pi * rand(M, 1);
  else
    psi = o.psi(:);
  end
  if isempty(o.tau_c)
    h = ones(M, N);
  else
    h = make_speckle_multi(N, fs, o.tau_c, M, o.rho);
  end
  carrier = exp(1i * phi);
  z = zeros(M, N);
  for k = 1:M
    n = complex_bandlimited_noise(N, fs, o.B_noise, s2);
    z(k, :) = h(k, :) .* carrier * exp(1i * psi(k)) + n.';
  end
  out = struct('z', z, 'h', h, 'psi', psi, 's2', s2);
end
